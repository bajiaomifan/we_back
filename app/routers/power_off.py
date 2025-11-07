from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.models.database import get_db, User
from app.models.schemas import (
    PowerOffTaskListResponse, PowerOffAuditLogListResponse,
    PowerOffAuditLogResponse, APIResponse
)
from app.services.power_off_service import PowerOffService
from app.middleware.auth import get_current_user
from app.services.task_scheduler import task_scheduler

router = APIRouter(
    prefix="/api/v1/power-off",
    tags=["power-off"]
)


@router.get("/tasks", response_model=PowerOffTaskListResponse)
async def get_power_off_tasks(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    booking_id: Optional[int] = Query(None, description="预订ID"),
    room_id: Optional[int] = Query(None, description="房间ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取关电任务列表"""
    power_off_service = PowerOffService()
    
    # 获取任务列表
    tasks = power_off_service.get_power_off_tasks(db, booking_id, room_id)
    
    # 简单分页处理
    total = len(tasks)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paginated_tasks = tasks[start_idx:end_idx]
    
    return PowerOffTaskListResponse(
        tasks=paginated_tasks,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.delete("/tasks/{booking_id}/{room_id}")
async def cancel_power_off_task(
    booking_id: int,
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消关电任务"""
    try:
        # 取消调度任务
        success = task_scheduler.cancel_power_off(booking_id, room_id)
        
        if success:
            return APIResponse(
                code=0,
                message="关电任务已取消",
                data=None
            )
        else:
            return APIResponse(
                code=404,
                message="未找到要取消的关电任务",
                data=None
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消关电任务失败: {str(e)}"
        )


@router.get("/audit-log", response_model=PowerOffAuditLogListResponse)
async def get_power_off_audit_log(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    booking_id: Optional[int] = Query(None, description="预订ID"),
    room_id: Optional[int] = Query(None, description="房间ID"),
    limit: int = Query(100, ge=1, le=1000, description="最大返回记录数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取关电审计日志"""
    power_off_service = PowerOffService()
    
    # 获取审计日志
    logs = power_off_service.get_power_off_audit_log(db, booking_id, room_id, limit)
    
    # 简单分页处理
    total = len(logs)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paginated_logs = logs[start_idx:end_idx]
    
    return PowerOffAuditLogListResponse(
        logs=paginated_logs,
        total=total
    )


@router.get("/scheduler/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user)
):
    """获取任务调度器状态"""
    try:
        jobs = task_scheduler.get_scheduled_jobs()
        
        return APIResponse(
            code=0,
            message="任务调度器状态获取成功",
            data={
                "scheduler_running": task_scheduler.scheduler.running,
                "total_jobs": len(jobs),
                "jobs": jobs
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取调度器状态失败: {str(e)}"
        )