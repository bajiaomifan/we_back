from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
import xml.etree.ElementTree as ET

from app.models.database import get_db, User
from app.models.schemas import (
    RechargeCreate, RechargeResponse, RechargeListResponse, 
    RechargeFilterParams, RechargeActivityResponse, RechargeActivityListResponse,
    BalanceTransactionResponse, BalanceTransactionListResponse, 
    BalanceTransactionFilterParams, UserBalanceResponse,
    PaginationParams, APIResponse
)
from app.services.recharge_service import RechargeService
from app.middleware.auth import get_current_user, get_client_ip

router = APIRouter(
    prefix="/api/v1/recharge",
    tags=["会员充值"]
)


@router.get("/activities", response_model=RechargeActivityListResponse)
async def get_recharge_activities(db: Session = Depends(get_db)):
    """获取充值活动列表"""
    recharge_service = RechargeService(db)
    activities = recharge_service.get_recharge_activities()
    
    return RechargeActivityListResponse(
        code=0,
        message="success",
        data=[RechargeActivityResponse.from_orm(activity) for activity in activities]
    )


@router.post("/order", response_model=APIResponse)
async def create_recharge_order(
    recharge_data: RechargeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建充值订单"""
    recharge_service = RechargeService(db)
    result = recharge_service.create_recharge_order(current_user.id, recharge_data)
    
    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result['message']
        )
    
    return APIResponse(
        code=0,
        message=result['message'],
        data=result['data']
    )


@router.post("/pay/{order_id}", response_model=APIResponse)
async def pay_recharge_order(
    order_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """支付充值订单"""
    recharge_service = RechargeService(db)
    client_ip = get_client_ip(request)
    
    result = await recharge_service.create_payment_for_recharge(order_id, client_ip)
    
    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result['message']
        )
    
    return APIResponse(
        code=0,
        message=result['message'],
        data=result['data']
    )


@router.get("/orders", response_model=RechargeListResponse)
async def get_my_recharge_orders(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    status: Optional[str] = Query(None, description="充值状态"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的充值订单列表"""
    recharge_service = RechargeService(db)
    
    pagination = PaginationParams(page=page, size=size)
    filters = RechargeFilterParams(
        status=status,
        start_date=start_date,
        end_date=end_date
    )
    
    orders = recharge_service.get_user_recharge_orders(
        current_user.id, 
        filters, 
        pagination
    )
    
    return RechargeListResponse(
        code=0,
        message="success",
        data=[RechargeResponse.from_orm(order) for order in orders],
        pagination={
            "page": page,
            "size": size,
            "total": len(orders)
        }
    )


@router.get("/balance", response_model=APIResponse)
async def get_user_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户余额信息"""
    recharge_service = RechargeService(db)
    balance_info = recharge_service.get_user_balance(current_user.id)
    
    if not balance_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return APIResponse(
        code=0,
        message="success",
        data=balance_info
    )


@router.get("/transactions", response_model=BalanceTransactionListResponse)
async def get_balance_transactions(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    transaction_type: Optional[str] = Query(None, description="交易类型"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取余额变动记录"""
    recharge_service = RechargeService(db)
    
    pagination = PaginationParams(page=page, size=size)
    filters = BalanceTransactionFilterParams(
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date
    )
    
    transactions = recharge_service.get_user_balance_transactions(
        current_user.id,
        filters,
        pagination
    )
    
    return BalanceTransactionListResponse(
        code=0,
        message="success",
        data=[BalanceTransactionResponse.from_orm(transaction) for transaction in transactions],
        pagination={
            "page": page,
            "size": size,
            "total": len(transactions)
        }
    )


@router.post("/payment/callback", response_model=APIResponse)
async def recharge_payment_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """充值支付回调处理"""
    try:
        # 获取回调数据（这里需要根据微信支付的实际回调格式调整）
        import xml.etree.ElementTree as ET
        
        body = await request.body()
        if not body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="回调数据为空"
            )
        
        # 解析XML回调数据
        root = ET.fromstring(body)
        
        # 提取关键信息
        order_no_elem = root.find(".//out_trade_no")
        transaction_id_elem = root.find(".//transaction_id")
        result_code_elem = root.find(".//result_code")
        
        order_no = order_no_elem.text if order_no_elem is not None else None
        transaction_id = transaction_id_elem.text if transaction_id_elem is not None else None
        result_code = result_code_elem.text if result_code_elem is not None else None
        
        if not order_no or not transaction_id or result_code != "SUCCESS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="回调数据格式错误"
            )
        
        # 处理支付成功
        recharge_service = RechargeService(db)
        result = recharge_service.handle_payment_success(order_no, transaction_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        return APIResponse(
            code=0,
            message="success",
            data=result['data']
        )
        
    except ET.ParseError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="XML解析失败"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理回调失败: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理回调失败: {str(e)}"
        )