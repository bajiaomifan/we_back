import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.database import (
    BookingNotification, ScheduledTask, Booking, User, 
    NotificationTypeEnum, NotificationStatusEnum, ScheduledTaskStatusEnum
)
from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_notification(
        self,
        booking_id: int,
        user_id: int,
        notification_type: str,
        title: str,
        content: str,
        max_retries: int = 3
    ) -> BookingNotification:
        """
        创建通知记录
        
        Args:
            booking_id: 预订ID
            user_id: 用户ID
            notification_type: 通知类型
            title: 通知标题
            content: 通知内容
            max_retries: 最大重试次数
            
        Returns:
            BookingNotification: 创建的通知记录
        """
        notification = BookingNotification(
            booking_id=booking_id,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            content=content,
            status=NotificationStatusEnum.PENDING,
            max_retries=max_retries
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        logger.info(f"创建通知记录成功: ID={notification.id}, 类型={notification_type}, 预订ID={booking_id}")
        return notification
    
    def send_notification(self, notification_id: int) -> bool:
        """
        发送通知
        
        Args:
            notification_id: 通知ID
            
        Returns:
            bool: 发送是否成功
        """
        notification = self.db.query(BookingNotification).filter(
            BookingNotification.id == notification_id,
            BookingNotification.is_deleted == False
        ).first()
        
        if not notification:
            logger.error(f"通知记录不存在: ID={notification_id}")
            return False
        
        try:
            # 获取用户信息
            user = self.db.query(User).filter(User.id == notification.user_id).first()
            if not user:
                logger.error(f"用户不存在: ID={notification.user_id}")
                return self._mark_notification_failed(notification, "用户不存在")
            
            # 根据通知类型发送不同的通知
            success = False
            if notification.notification_type == NotificationTypeEnum.BOOKING_REMINDER:
                success = self._send_booking_reminder(notification, user)
            elif notification.notification_type == NotificationTypeEnum.BOOKING_EXPIRED:
                success = self._send_booking_expired(notification, user)
            elif notification.notification_type == NotificationTypeEnum.BOOKING_CANCELLED:
                success = self._send_booking_cancelled(notification, user)
            else:
                logger.error(f"不支持的通知类型: {notification.notification_type}")
                return self._mark_notification_failed(notification, f"不支持的通知类型: {notification.notification_type}")
            
            if success:
                # 标记为已发送
                notification.status = NotificationStatusEnum.SENT
                notification.send_time = datetime.now()
                self.db.commit()
                
                logger.info(f"通知发送成功: ID={notification_id}, 类型={notification.notification_type}")
                return True
            else:
                return self._mark_notification_failed(notification, "发送失败")
                
        except Exception as e:
            logger.error(f"发送通知异常: ID={notification_id}, 错误={str(e)}")
            return self._mark_notification_failed(notification, str(e))
    
    def _mark_notification_failed(self, notification: BookingNotification, error_message: str) -> bool:
        """标记通知为失败状态"""
        notification.status = NotificationStatusEnum.FAILED
        notification.error_message = error_message
        notification.retry_count += 1
        
        # 如果未达到最大重试次数，标记为重试状态
        if notification.retry_count < notification.max_retries:
            notification.status = NotificationStatusEnum.RETRY
        
        self.db.commit()
        return False
    
    def _send_booking_reminder(self, notification: BookingNotification, user: User) -> bool:
        """
        发送预订提醒通知
        
        Args:
            notification: 通知记录
            user: 用户信息
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 获取预订信息
            booking = self.db.query(Booking).filter(Booking.id == notification.booking_id).first()
            if not booking:
                logger.error(f"预订记录不存在: ID={notification.booking_id}")
                return False
            
            # 这里应该调用微信小程序的订阅消息API
            # 由于这是示例代码，我们只记录日志
            logger.info(f"发送预订提醒通知 - 用户: {user.nickname}, 预订ID: {booking.id}, 内容: {notification.content}")
            
            # 在实际实现中，这里应该调用微信API发送订阅消息
            # 例如：
            # result = wechat_service.send_subscription_message(
            #     openid=user.openid,
            #     template_id=settings.WECHAT_BOOKING_REMINDER_TEMPLATE,
            #     data={
            #         "thing1": {"value": booking.room.name},
            #         "time2": {"value": datetime.fromtimestamp(booking.start_time).strftime("%Y-%m-%d %H:%M")},
            #         "thing3": {"value": booking.contact_name}
            #     }
            # )
            # return result.get("errcode") == 0
            
            return True
            
        except Exception as e:
            logger.error(f"发送预订提醒通知异常: {str(e)}")
            return False
    
    def _send_booking_expired(self, notification: BookingNotification, user: User) -> bool:
        """
        发送预订到期通知
        
        Args:
            notification: 通知记录
            user: 用户信息
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 获取预订信息
            booking = self.db.query(Booking).filter(Booking.id == notification.booking_id).first()
            if not booking:
                logger.error(f"预订记录不存在: ID={notification.booking_id}")
                return False
            
            # 这里应该调用微信小程序的订阅消息API
            logger.info(f"发送预订到期通知 - 用户: {user.nickname}, 预订ID: {booking.id}, 内容: {notification.content}")
            
            return True
            
        except Exception as e:
            logger.error(f"发送预订到期通知异常: {str(e)}")
            return False
    
    def _send_booking_cancelled(self, notification: BookingNotification, user: User) -> bool:
        """
        发送预订取消通知
        
        Args:
            notification: 通知记录
            user: 用户信息
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 获取预订信息
            booking = self.db.query(Booking).filter(Booking.id == notification.booking_id).first()
            if not booking:
                logger.error(f"预订记录不存在: ID={notification.booking_id}")
                return False
            
            # 这里应该调用微信小程序的订阅消息API
            logger.info(f"发送预订取消通知 - 用户: {user.nickname}, 预订ID: {booking.id}, 内容: {notification.content}")
            
            return True
            
        except Exception as e:
            logger.error(f"发送预订取消通知异常: {str(e)}")
            return False
    
    def get_pending_notifications(self, limit: int = 100) -> List[BookingNotification]:
        """
        获取待发送的通知
        
        Args:
            limit: 限制数量
            
        Returns:
            List[BookingNotification]: 待发送的通知列表
        """
        return self.db.query(BookingNotification).filter(
            and_(
                BookingNotification.status.in_([
                    NotificationStatusEnum.PENDING,
                    NotificationStatusEnum.RETRY
                ]),
                BookingNotification.is_deleted == False,
                or_(
                    BookingNotification.retry_count < BookingNotification.max_retries,
                    BookingNotification.retry_count == 0
                )
            )
        ).order_by(BookingNotification.created_at).limit(limit).all()
    
    def get_notifications_by_booking(self, booking_id: int) -> List[BookingNotification]:
        """
        根据预订ID获取通知列表
        
        Args:
            booking_id: 预订ID
            
        Returns:
            List[BookingNotification]: 通知列表
        """
        return self.db.query(BookingNotification).filter(
            and_(
                BookingNotification.booking_id == booking_id,
                BookingNotification.is_deleted == False
            )
        ).order_by(BookingNotification.created_at.desc()).all()
    
    def get_notifications_by_user(self, user_id: int, limit: int = 50) -> List[BookingNotification]:
        """
        根据用户ID获取通知列表
        
        Args:
            user_id: 用户ID
            limit: 限制数量
            
        Returns:
            List[BookingNotification]: 通知列表
        """
        return self.db.query(BookingNotification).filter(
            and_(
                BookingNotification.user_id == user_id,
                BookingNotification.is_deleted == False
            )
        ).order_by(BookingNotification.created_at.desc()).limit(limit).all()
    
    def retry_failed_notifications(self) -> int:
        """
        重试失败的通知
        
        Returns:
            int: 重试的通知数量
        """
        # 获取需要重试的通知
        notifications = self.db.query(BookingNotification).filter(
            and_(
                BookingNotification.status == NotificationStatusEnum.FAILED,
                BookingNotification.retry_count < BookingNotification.max_retries,
                BookingNotification.is_deleted == False
            )
        ).all()
        
        retry_count = 0
        for notification in notifications:
            # 标记为重试状态
            notification.status = NotificationStatusEnum.RETRY
            retry_count += 1
        
        self.db.commit()
        
        logger.info(f"标记 {retry_count} 个通知为重试状态")
        return retry_count
    
    def cleanup_old_notifications(self, days: int = 30) -> int:
        """
        清理旧的通知记录
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的通知数量
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 软删除旧通知
        notifications = self.db.query(BookingNotification).filter(
            and_(
                BookingNotification.created_at < cutoff_date,
                BookingNotification.is_deleted == False
            )
        ).all()
        
        cleanup_count = 0
        for notification in notifications:
            notification.is_deleted = True
            cleanup_count += 1
        
        self.db.commit()
        
        logger.info(f"软删除 {cleanup_count} 个旧通知记录")
        return cleanup_count