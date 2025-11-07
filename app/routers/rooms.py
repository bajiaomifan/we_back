# app/routers/rooms.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
import httpx

from app.models.database import get_db, User
from app.models.schemas import (
    StoreResponse, RoomResponse, RoomListResponse, RoomFilterParams,
    AvailabilityResponse, PaginationParams, APIResponse,
    RoomAvailabilityResponse, RoomAvailabilityParams,
    DoorOpenRequest, DoorOpenResponse
)
from app.services.room_service import RoomService
from app.services.booking_service import BookingService
from app.middleware.auth import get_current_user, get_client_ip
from app.services.user_service import UserService
from app.services.task_scheduler import task_scheduler
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/api/v1/rooms",
    tags=["rooms"]
)


@router.get("/store", response_model=StoreResponse)
async def get_store_info(db: Session = Depends(get_db)):
    """获取店面信息"""
    room_service = RoomService(db)
    store = room_service.get_store_info()
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="店面信息不存在"
        )
    
    return store


@router.get("", response_model=RoomListResponse)
async def get_rooms(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    store_id: Optional[int] = Query(None, description="店面ID"),
    min_price: Optional[float] = Query(None, ge=0, description="最低价格"),
    max_price: Optional[float] = Query(None, ge=0, description="最高价格"),
    is_available: Optional[bool] = Query(None, description="是否可用"),
    db: Session = Depends(get_db)
):
    """获取包间列表"""
    pagination = PaginationParams(page=page, size=size)
    filters = RoomFilterParams(
        store_id=store_id,
        min_price=min_price,
        max_price=max_price,
        is_available=is_available
    )
    
    room_service = RoomService(db)
    return room_service.get_rooms(pagination, filters)


@router.get("/search", response_model=RoomListResponse)
async def search_rooms(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: Session = Depends(get_db)
):
    """搜索包间"""
    pagination = PaginationParams(page=page, size=size)
    
    room_service = RoomService(db)
    return room_service.search_rooms(keyword, pagination)


@router.get("/recommended", response_model=list[RoomResponse])
async def get_recommended_rooms(
    limit: int = Query(6, ge=1, le=20, description="返回数量"),
    db: Session = Depends(get_db)
):
    """获取推荐包间"""
    room_service = RoomService(db)
    return room_service.get_recommended_rooms(limit)


@router.get("/availability", response_model=RoomAvailabilityResponse)
async def get_room_availability_new(
    room_id: int = Query(..., description="包间ID"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)，默认今天"),
    days: int = Query(3, ge=1, le=7, description="查询天数，默认3天"),
    db: Session = Depends(get_db)
):
    """获取包间可用性数据（新版，支持多天查询）"""
    try:
        print(f"路由层: 查询包间可用性 room_id={room_id}, start_date={start_date}, days={days}")
        
        room_service = RoomService(db)
        
        # 验证包间是否存在
        room = room_service.get_room_by_id(room_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="包间不存在"
            )
        
        # 获取可用性数据
        availability_data = room_service.get_room_availability_extended(
            room_id=room_id,
            start_date=start_date,
            days=days
        )
        return availability_data
        
    except HTTPException:
        raise
    except ValueError as e:
        print(f"路由层: ValueError - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"路由层: 未知错误 - {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"内部服务器错误: {str(e)}"
        )


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room_detail(
    room_id: int,
    db: Session = Depends(get_db)
):
    """获取包间详情"""
    room_service = RoomService(db)
    room = room_service.get_room_by_id(room_id)
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="包间不存在"
        )
    
    return room


@router.get("/{room_id}/availability", response_model=AvailabilityResponse)
async def get_room_availability(
    room_id: int,
    date: str = Query(..., description="查询日期 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """获取包间可用时间段"""
    room_service = RoomService(db)
    availability = room_service.get_room_availability(room_id, date)
    
    if not availability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="包间不存在或日期格式错误"
        )
    
    return availability


@router.get("/{room_id}/reviews")
async def get_room_reviews(
    room_id: int,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=50, description="每页大小"),
    db: Session = Depends(get_db)
):
    """获取包间评价列表"""
    pagination = PaginationParams(page=page, size=size)
    
    room_service = RoomService(db)
    return room_service.get_room_reviews(room_id, pagination)
@router.post("/doors", response_model=DoorOpenResponse)
async def open_door(
    request: DoorOpenRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送开门指令到外部设备
    
    需要用户身份验证和有效预订才能开门。用户只能在预订时间前1小时内到预订结束时间内开门。
    
    Args:
        request: 开门请求，包含门ID
        current_user: 当前认证用户
        db: 数据库会话
    
    Returns:
        DoorOpenResponse: 开门操作响应
    
    Raises:
        HTTPException: 当用户无有效预订或超过时间限制时返回403错误
        HTTPException: 当外部设备通信失败时返回502错误
        HTTPException: 当服务器内部错误时返回500错误
    """
    try:
        # 验证用户开门权限
        booking_service = BookingService(db)
        validation_result = booking_service.validate_door_access(current_user.id, request.door_id)
        
        if not validation_result['valid']:
            # 记录失败的开门尝试
            user_service = UserService(db)
            user_service.create_audit_log(
                user_id=current_user.id,
                action="door_access_denied",
                resource_type="door",
                resource_id=str(request.door_id),
                description=f"开门被拒绝: {validation_result['message']}",
                ip_address=get_client_ip(http_request)
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=validation_result['message']
            )
        
        # 调度自动关电任务
        booking_info = validation_result['booking']
        if booking_info:
            # 计算关电时间：预订结束时间 + 40分钟缓冲
            booking_end_time = datetime.fromtimestamp(booking_info['end_time'])
            power_off_time = booking_end_time + timedelta(minutes=40)
            
            # 调度关电任务
            try:
                job_id = task_scheduler.schedule_power_off(
                    booking_id=booking_info['id'],
                    room_id=request.door_id,
                    power_off_time=power_off_time
                )
                print(f"已调度自动关电任务: {job_id}, 执行时间: {power_off_time}")
            except Exception as e:
                print(f"调度关电任务失败: {e}")
                # 不影响开门操作，只记录错误
        
        # 首先发送门关闭请求
        door_off_url = f"https://3e.upon.ltd/relays/{request.door_id}/off"
        async with httpx.AsyncClient() as client:
            # 发送POST请求关闭门
            door_response = await client.post(door_off_url)
            door_response.raise_for_status()  # 如果响应状态码不是2xx，抛出异常
            
            # 解析门关闭响应
            door_result = door_response.json()
            
            # 验证响应格式
            if "relay_id" not in door_result or "status" not in door_result:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="外部设备响应格式错误"
                )
            
            # 门ID到网关ID的映射
            door_to_gateway = {
                9: 7,
                10: 6,
                11: 8,
                12: 5,
                14: 1,
                15: 2,
                16: 3
            }
            
            # 获取对应的网关ID
            gateway_id = door_to_gateway.get(request.door_id)
            if gateway_id is not None:
                # 检查网关状态
                status_url = f"https://3e.upon.ltd/relays/{gateway_id}/status"
                try:
                    status_response = await client.get(status_url)
                    status_response.raise_for_status()
                    
                    status_result = status_response.json()
                    current_status = status_result.get("status", False)
                    
                    # 如果网关是关闭状态，发送开启指令
                    if not current_status:
                        open_url = f"https://3e.upon.ltd/relays/{gateway_id}/on"
                        await client.post(open_url)
                        # 记录网关被开启，但主要返回门关闭响应
                        print(f"网关 {gateway_id} 已开启")
                
                except httpx.HTTPError as e:
                    # 网关状态检查或开启失败，记录错误但继续返回门关闭响应
                    print(f"网关操作失败: {str(e)}")
            
            # 记录成功的开门操作
            user_service = UserService(db)
            user_service.create_audit_log(
                user_id=current_user.id,
                action="door_opened",
                resource_type="door",
                resource_id=str(request.door_id),
                description=f"用户 {current_user.nickname} 成功开启门 {request.door_id}",
                ip_address=get_client_ip(http_request)
            )
            
            return DoorOpenResponse(**door_result)
            
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"外部设备通信失败: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"内部服务器错误: {str(e)}"
        )