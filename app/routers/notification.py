from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.models.database import get_db, User, BookingNotification, ScheduledTask
from app.services.notification_service import NotificationService
from app.services.task_scheduler_service import TaskSchedulerService
from app.middleware.auth import get_current_user
from app.models.schemas import APIResponse, PaginationParams
from app.config import settings

router = APIRouter(prefix="/notifications", tags=["通知管理"])


class NotificationResponse(BaseModel):
    """通知响应模型"""
    id: int
    booking_id: int
    notification_type: str
    title: str
    content: str
    status: str
    send_time: Optional[datetime] = None
    retry_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    """任务响应模型"""
    id: int
    task_id: str
    task_type: str
    title: str
    description: Optional[str] = None
    scheduled_time: datetime
    executed_time: Optional[datetime] = None
    status: str
    result: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """通知列表响应模型"""
    items: List[NotificationResponse]
    total: int
    page: int
    page_size: int


class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    items: List[TaskResponse]
    total: int
    page: int
    page_size: int


@router.get("/my-notifications", response_model=APIResponse)
async def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取当前用户的通知列表"""
    try:
        notification_service = NotificationService(db)
        notifications = notification_service.get_notifications_by_user(
            user_id=current_user.id,
            limit=page_size
        )
        
        # 转换为响应模型
        notification_responses = [
            NotificationResponse(
                id=notification.id,
                booking_id=notification.booking_id,
                notification_type=notification.notification_type,
                title=notification.title,
                content=notification.content,
                status=notification.status,
                send_time=notification.send_time,
                retry_count=notification.retry_count,
                created_at=notification.created_at
            )
            for notification in notifications
        ]
        
        return APIResponse(
            code=0,
            message="获取通知列表成功",
            data={
                "items": notification_responses,
                "total": len(notification_responses),
                "page": page,
                "page_size": page_size
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取通知列表失败: {str(e)}"
        )


@router.get("/booking/{booking_id}", response_model=APIResponse)
async def get_booking_notifications(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取指定预订的通知列表"""
    try:
        notification_service = NotificationService(db)
        notifications = notification_service.get_notifications_by_booking(booking_id)
        
        # 转换为响应模型
        notification_responses = [
            NotificationResponse(
                id=notification.id,
                booking_id=notification.booking_id,
                notification_type=notification.notification_type,
                title=notification.title,
                content=notification.content,
                status=notification.status,
                send_time=notification.send_time,
                retry_count=notification.retry_count,
                created_at=notification.created_at
            )
            for notification in notifications
        ]
        
        return APIResponse(
            code=0,
            message="获取预订通知列表成功",
            data={
                "items": notification_responses,
                "total": len(notification_responses)
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取预订通知列表失败: {str(e)}"
        )


@router.post("/retry-failed", response_model=APIResponse)
async def retry_failed_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重试失败的通知（管理员功能）"""
    try:
        # 检查用户权限（这里简化为检查用户ID，实际应该有角色权限系统）
        if current_user.id != 1:  # 假设ID为1的用户是管理员
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        
        notification_service = NotificationService(db)
        retry_count = notification_service.retry_failed_notifications()
        
        return APIResponse(
            code=0,
            message="重试失败通知成功",
            data={
                "retry_count": retry_count
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重试失败通知失败: {str(e)}"
        )


@router.post("/cleanup-old", response_model=APIResponse)
async def cleanup_old_notifications(
    days: int = Query(30, ge=1, le=365, description="保留天数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清理旧通知记录（管理员功能）"""
    try:
        # 检查用户权限
        if current_user.id != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        
        notification_service = NotificationService(db)
        cleanup_count = notification_service.cleanup_old_notifications(days=days)
        
        return APIResponse(
            code=0,
            message="清理旧通知记录成功",
            data={
                "cleanup_count": cleanup_count
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理旧通知记录失败: {str(e)}"
        )


@router.get("/tasks/booking/{booking_id}", response_model=APIResponse)
async def get_booking_tasks(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取指定预订的任务列表"""
    try:
        task_scheduler = TaskSchedulerService(db)
        tasks = task_scheduler.get_tasks_by_booking(booking_id)
        
        # 转换为响应模型
        task_responses = [
            TaskResponse(
                id=task.id,
                task_id=task.task_id,
                task_type=task.task_type,
                title=task.title,
                description=task.description,
                scheduled_time=task.scheduled_time,
                executed_time=task.executed_time,
                status=task.status,
                result=task.result,
                error_message=task.error_message,
                retry_count=task.retry_count,
                created_at=task.created_at
            )
            for task in tasks
        ]
        
        return APIResponse(
            code=0,
            message="获取预订任务列表成功",
            data={
                "items": task_responses,
                "total": len(task_responses)
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取预订任务列表失败: {str(e)}"
        )


@router.post("/tasks/{task_id}/cancel", response_model=APIResponse)
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消任务"""
    try:
        task_scheduler = TaskSchedulerService(db)
        success = task_scheduler.cancel_task(task_id)
        
        if success:
            return APIResponse(
                code=0,
                message="取消任务成功",
                data={"task_id": task_id}
            )
        else:
            return APIResponse(
                code=1,
                message="取消任务失败，任务可能不存在或已完成",
                data={"task_id": task_id}
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消任务失败: {str(e)}"
        )


@router.get("/status", response_model=APIResponse)
async def get_notification_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取通知系统状态（管理员功能）"""
    try:
        # 检查用户权限
        if current_user.id != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        
        # 统计通知数量
        total_notifications = db.query(BookingNotification).filter(
            BookingNotification.is_deleted == False
        ).count()
        
        pending_notifications = db.query(BookingNotification).filter(
            BookingNotification.is_deleted == False,
            BookingNotification.status.in_(["pending", "retry"])
        ).count()
        
        failed_notifications = db.query(BookingNotification).filter(
            BookingNotification.is_deleted == False,
            BookingNotification.status == "failed"
        ).count()
        
        # 统计任务数量
        total_tasks = db.query(ScheduledTask).filter(
            ScheduledTask.is_deleted == False
        ).count()
        
        pending_tasks = db.query(ScheduledTask).filter(
            ScheduledTask.is_deleted == False,
            ScheduledTask.status == "pending"
        ).count()
        
        failed_tasks = db.query(ScheduledTask).filter(
            ScheduledTask.is_deleted == False,
            ScheduledTask.status == "failed"
        ).count()
        
        return APIResponse(
            code=0,
            message="获取通知系统状态成功",
            data={
                "notifications": {
                    "total": total_notifications,
                    "pending": pending_notifications,
                    "failed": failed_notifications
                },
                "tasks": {
                    "total": total_tasks,
                    "pending": pending_tasks,
                    "failed": failed_tasks
                },
                "config": {
                    "notification_enabled": settings.NOTIFICATION_ENABLED,
                    "scheduler_enabled": settings.SCHEDULER_ENABLED,
                    "booking_reminder_enabled": settings.BOOKING_REMINDER_ENABLED,
                    "booking_reminder_advance_hours": settings.BOOKING_REMINDER_ADVANCE_HOURS
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取通知系统状态失败: {str(e)}"
        )