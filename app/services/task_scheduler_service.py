import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from contextlib import contextmanager

from app.models.database import (
    ScheduledTask, Booking, BookingNotification, 
    ScheduledTaskStatusEnum, NotificationTypeEnum, NotificationStatusEnum
)
from app.services.notification_service import NotificationService
from app.config import settings

logger = logging.getLogger(__name__)


class TaskSchedulerService:
    """任务调度服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.scheduler = BackgroundScheduler()
        self.notification_service = NotificationService(db)
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """设置调度器"""
        # 添加事件监听器
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        
        # 添加默认任务
        self._add_default_jobs()
    
    def _add_default_jobs(self):
        """添加默认任务"""
        # 每分钟检查一次待发送的通知
        self.scheduler.add_job(
            func=self._process_pending_notifications,
            trigger=IntervalTrigger(minutes=1),
            id="process_pending_notifications",
            name="处理待发送通知",
            replace_existing=True
        )
        
        # 每小时重试失败的通知
        self.scheduler.add_job(
            func=self._retry_failed_notifications,
            trigger=IntervalTrigger(hours=1),
            id="retry_failed_notifications",
            name="重试失败通知",
            replace_existing=True
        )
        
        # 每天凌晨2点清理旧通知
        self.scheduler.add_job(
            func=self._cleanup_old_notifications,
            trigger=IntervalTrigger(hours=24),
            id="cleanup_old_notifications",
            name="清理旧通知",
            replace_existing=True
        )
    
    def start(self):
        """启动调度器"""
        try:
            self.scheduler.start()
            logger.info("任务调度器启动成功")
            
            # 启动时恢复未完成的任务
            self._restore_pending_tasks()
            
        except Exception as e:
            logger.error(f"任务调度器启动失败: {str(e)}")
            raise
    
    def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("任务调度器已停止")
        except Exception as e:
            logger.error(f"任务调度器停止失败: {str(e)}")
    
    def schedule_booking_reminder(self, booking_id: int, reminder_time: datetime) -> bool:
        """
        安排预订提醒任务
        
        Args:
            booking_id: 预订ID
            reminder_time: 提醒时间
            
        Returns:
            bool: 是否成功安排
        """
        # 获取预订信息
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            logger.error(f"预订记录不存在: ID={booking_id}")
            return False
        
        # 生成任务ID
        task_id = f"booking_reminder_{booking_id}_{reminder_time.strftime('%Y%m%d%H%M%S')}"
        
        # 检查任务是否已存在
        existing_task = self.db.query(ScheduledTask).filter(
            ScheduledTask.task_id == task_id,
            ScheduledTask.is_deleted == False
        ).first()
        
        if existing_task:
            logger.info(f"预订提醒任务已存在: {task_id}")
            return True
        
        # 创建任务记录
        task = ScheduledTask(
            task_id=task_id,
            task_type="booking_reminder",
            related_type="booking",
            related_id=booking_id,
            title=f"预订提醒 - {booking.room.name}",
            description=f"为预订 {booking.id} 安排提醒，提醒时间: {reminder_time.strftime('%Y-%m-%d %H:%M:%S')}",
            scheduled_time=reminder_time,
            status=ScheduledTaskStatusEnum.PENDING
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        # 添加到调度器
        try:
            self.scheduler.add_job(
                func=self._send_booking_reminder,
                trigger=DateTrigger(run_date=reminder_time),
                args=[task.id],
                id=task_id,
                name=f"预订提醒 - {booking.room.name}",
                replace_existing=True
            )
            
            logger.info(f"成功安排预订提醒任务: {task_id}, 预订ID: {booking_id}, 提醒时间: {reminder_time}")
            return True
            
        except Exception as e:
            logger.error(f"安排预订提醒任务失败: {str(e)}")
            # 标记任务为失败
            task.status = ScheduledTaskStatusEnum.FAILED
            task.error_message = str(e)
            self.db.commit()
            return False
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        try:
            # 从调度器中移除任务
            self.scheduler.remove_job(task_id)
            
            # 更新数据库中的任务状态
            task = self.db.query(ScheduledTask).filter(
                ScheduledTask.task_id == task_id,
                ScheduledTask.is_deleted == False
            ).first()
            
            if task:
                task.status = ScheduledTaskStatusEnum.CANCELLED
                self.db.commit()
                logger.info(f"成功取消任务: {task_id}")
                return True
            else:
                logger.warning(f"任务不存在: {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"取消任务失败: {task_id}, 错误: {str(e)}")
            return False
    
    def get_pending_tasks(self, limit: int = 100) -> List[ScheduledTask]:
        """
        获取待执行的任务
        
        Args:
            limit: 限制数量
            
        Returns:
            List[ScheduledTask]: 待执行的任务列表
        """
        return self.db.query(ScheduledTask).filter(
            and_(
                ScheduledTask.status == ScheduledTaskStatusEnum.PENDING,
                ScheduledTask.scheduled_time <= datetime.now(),
                ScheduledTask.is_deleted == False
            )
        ).order_by(ScheduledTask.scheduled_time).limit(limit).all()
    
    def get_tasks_by_booking(self, booking_id: int) -> List[ScheduledTask]:
        """
        根据预订ID获取任务列表
        
        Args:
            booking_id: 预订ID
            
        Returns:
            List[ScheduledTask]: 任务列表
        """
        return self.db.query(ScheduledTask).filter(
            and_(
                ScheduledTask.related_type == "booking",
                ScheduledTask.related_id == booking_id,
                ScheduledTask.is_deleted == False
            )
        ).order_by(ScheduledTask.created_at.desc()).all()
    
    def _restore_pending_tasks(self):
        """恢复未完成的任务"""
        pending_tasks = self.db.query(ScheduledTask).filter(
            and_(
                ScheduledTask.status.in_([
                    ScheduledTaskStatusEnum.PENDING,
                    ScheduledTaskStatusEnum.FAILED
                ]),
                ScheduledTask.scheduled_time > datetime.now(),
                ScheduledTask.is_deleted == False
            )
        ).all()
        
        restored_count = 0
        for task in pending_tasks:
            try:
                # 重新添加到调度器
                if task.task_type == "booking_reminder":
                    self.scheduler.add_job(
                        func=self._send_booking_reminder,
                        trigger=DateTrigger(run_date=task.scheduled_time),
                        args=[task.id],
                        id=task.task_id,
                        name=task.title,
                        replace_existing=True
                    )
                    restored_count += 1
                    
            except Exception as e:
                logger.error(f"恢复任务失败: {task.task_id}, 错误: {str(e)}")
        
        logger.info(f"成功恢复 {restored_count} 个待执行任务")
    
    def _send_booking_reminder(self, task_id: int):
        """
        发送预订提醒（由调度器调用）
        
        Args:
            task_id: 任务ID
        """
        with self._get_db_session() as db:
            try:
                # 获取任务信息
                task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if not task:
                    logger.error(f"任务不存在: ID={task_id}")
                    return
                
                # 更新任务状态为执行中
                task.status = ScheduledTaskStatusEnum.RUNNING
                task.executed_time = datetime.now()
                db.commit()
                
                # 获取预订信息
                booking = db.query(Booking).filter(Booking.id == task.related_id).first()
                if not booking:
                    logger.error(f"预订不存在: ID={task.related_id}")
                    task.status = ScheduledTaskStatusEnum.FAILED
                    task.error_message = "预订不存在"
                    db.commit()
                    return
                
                # 检查预订状态是否仍然有效
                if booking.status in ["cancelled", "completed"]:
                    logger.info(f"预订已结束，跳过提醒: 预订ID={booking.id}, 状态={booking.status}")
                    task.status = ScheduledTaskStatusEnum.COMPLETED
                    task.result = "预订已结束，跳过提醒"
                    db.commit()
                    return
                
                # 创建通知
                notification_service = NotificationService(db)
                notification = notification_service.create_notification(
                    booking_id=booking.id,
                    user_id=booking.user_id,
                    notification_type=NotificationTypeEnum.BOOKING_REMINDER,
                    title="预订即将到期提醒",
                    content=f"您预订的{booking.room.name}将在1小时后到期，请及时到店使用。预订时间：{datetime.fromtimestamp(booking.start_time).strftime('%Y-%m-%d %H:%M')} - {datetime.fromtimestamp(booking.end_time).strftime('%H:%M')}。"
                )
                
                # 发送通知
                success = notification_service.send_notification(notification.id)
                
                if success:
                    task.status = ScheduledTaskStatusEnum.COMPLETED
                    task.result = "提醒通知发送成功"
                    logger.info(f"预订提醒任务执行成功: 任务ID={task_id}, 预订ID={booking.id}")
                else:
                    task.status = ScheduledTaskStatusEnum.FAILED
                    task.error_message = "提醒通知发送失败"
                    logger.error(f"预订提醒任务执行失败: 任务ID={task_id}, 预订ID={booking.id}")
                
                db.commit()
                
            except Exception as e:
                logger.error(f"执行预订提醒任务异常: 任务ID={task_id}, 错误={str(e)}")
                
                # 更新任务状态
                try:
                    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                    if task:
                        task.status = ScheduledTaskStatusEnum.FAILED
                        task.error_message = str(e)
                        db.commit()
                except Exception as commit_error:
                    logger.error(f"更新任务状态失败: {str(commit_error)}")
    
    def _process_pending_notifications(self):
        """处理待发送的通知"""
        with self._get_db_session() as db:
            try:
                notification_service = NotificationService(db)
                pending_notifications = notification_service.get_pending_notifications(limit=50)
                
                processed_count = 0
                for notification in pending_notifications:
                    success = notification_service.send_notification(notification.id)
                    if success:
                        processed_count += 1
                
                logger.info(f"处理待发送通知完成: 处理数量={processed_count}")
                
            except Exception as e:
                logger.error(f"处理待发送通知异常: {str(e)}")
    
    def _retry_failed_notifications(self):
        """重试失败的通知"""
        with self._get_db_session() as db:
            try:
                notification_service = NotificationService(db)
                retry_count = notification_service.retry_failed_notifications()
                
                logger.info(f"重试失败通知完成: 重试数量={retry_count}")
                
            except Exception as e:
                logger.error(f"重试失败通知异常: {str(e)}")
    
    def _cleanup_old_notifications(self):
        """清理旧通知"""
        with self._get_db_session() as db:
            try:
                notification_service = NotificationService(db)
                cleanup_count = notification_service.cleanup_old_notifications(days=30)
                
                logger.info(f"清理旧通知完成: 清理数量={cleanup_count}")
                
            except Exception as e:
                logger.error(f"清理旧通知异常: {str(e)}")
    
    def _job_executed(self, event):
        """任务执行完成事件处理"""
        logger.info(f"任务执行完成: {event.job_id}")
    
    def _job_error(self, event):
        """任务执行错误事件处理"""
        logger.error(f"任务执行错误: {event.job_id}, 异常: {event.exception}")
    
    @contextmanager
    def _get_db_session(self):
        """获取数据库会话的上下文管理器"""
        from app.models.database import SessionLocal
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()