from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from fastapi import HTTPException, status

from app.models.database import (
    User, RechargeOrder, RechargeActivity, BalanceTransaction, 
    PaymentOrder, get_db
)
from app.models.schemas import (
    RechargeCreate, RechargeResponse, RechargeFilterParams,
    BalanceTransactionResponse, BalanceTransactionFilterParams,
    RechargeStatusEnum, TransactionTypeEnum, PaginationParams
)
from app.services.payment_service import PaymentService
import secrets
import string


class RechargeService:
    """充值服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_order_no(self) -> str:
        """生成充值订单号"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = ''.join(secrets.choice(string.digits) for _ in range(6))
        return f"RC{timestamp}{random_str}"
    
    def get_recharge_activities(self) -> List[RechargeActivity]:
        """获取可用的充值活动列表"""
        return self.db.query(RechargeActivity).filter(
            and_(
                RechargeActivity.is_active == True,
                or_(
                    RechargeActivity.start_time.is_(None),
                    RechargeActivity.start_time <= datetime.now()
                ),
                or_(
                    RechargeActivity.end_time.is_(None),
                    RechargeActivity.end_time >= datetime.now()
                )
            )
        ).order_by(RechargeActivity.sort_order.asc()).all()
    
    def calculate_bonus(self, amount: int, activity_id: Optional[int] = None) -> int:
        """计算充值赠送金额"""
        if not activity_id:
            return 0
        
        activity = self.db.query(RechargeActivity).filter(
            and_(
                RechargeActivity.id == activity_id,
                RechargeActivity.is_active == True,
                RechargeActivity.recharge_amount <= amount
            )
        ).first()
        
        if activity:
            return activity.bonus_amount
        
        return 0
    
    def create_recharge_order(self, user_id: int, recharge_data: RechargeCreate) -> Dict[str, Any]:
        """创建充值订单"""
        try:
            # 获取用户信息
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {'success': False, 'message': '用户不存在'}
            
            # 计算赠送金额
            amount = recharge_data.amount  # 已经是分
            bonus_amount = self.calculate_bonus(amount, recharge_data.activity_id)
            total_amount = amount + bonus_amount
            
            # 创建充值订单
            recharge_order = RechargeOrder(
                user_id=user_id,
                openid=user.openid,
                order_no=self.generate_order_no(),
                amount=amount,
                bonus_amount=bonus_amount,
                total_amount=total_amount,
                status=RechargeStatusEnum.PENDING,
                description=recharge_data.description
            )
            
            self.db.add(recharge_order)
            self.db.commit()
            self.db.refresh(recharge_order)
            
            return {
                'success': True,
                'message': '充值订单创建成功',
                'data': {
                    'order_id': recharge_order.id,
                    'order_no': recharge_order.order_no,
                    'amount': amount,
                    'bonus_amount': bonus_amount,
                    'total_amount': total_amount
                }
            }
            
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'message': f'创建充值订单失败: {str(e)}'}
    
    async def create_payment_for_recharge(self, recharge_order_id: int, client_ip: str) -> Dict[str, Any]:
        """为充值订单创建支付"""
        try:
            # 获取充值订单
            recharge_order = self.db.query(RechargeOrder).filter(
                and_(
                    RechargeOrder.id == recharge_order_id,
                    RechargeOrder.is_deleted == False
                )
            ).first()
            
            if not recharge_order:
                return {'success': False, 'message': '充值订单不存在'}
            
            if recharge_order.status != RechargeStatusEnum.PENDING:
                return {'success': False, 'message': '充值订单状态不正确'}
            
            # 创建支付订单
            payment_service = PaymentService(self.db)
            payment_data = {
                'body': f'棋牌室充值{recharge_order.total_amount / 100}元',
                'out_trade_no': recharge_order.order_no,
                'total_fee': recharge_order.total_amount,  # 已经是分
                'openid': recharge_order.openid
            }
            
            # 调用支付服务创建支付订单
            payment_result = await payment_service.create_unified_order(payment_data, client_ip)
            
            if payment_result['success']:
                # 更新充值订单的支付信息
                recharge_order.payment_order_id = payment_result['data']['payment_order_id']
                recharge_order.prepay_id = payment_result['data']['prepay_id']
                self.db.commit()
                
                return {
                    'success': True,
                    'message': '支付创建成功',
                    'data': payment_result['data']
                }
            else:
                return payment_result
                
        except Exception as e:
            return {'success': False, 'message': f'创建支付失败: {str(e)}'}
    
    def handle_payment_success(self, order_no: str, transaction_id: str) -> Dict[str, Any]:
        """处理支付成功回调"""
        try:
            # 获取充值订单
            recharge_order = self.db.query(RechargeOrder).filter(
                and_(
                    RechargeOrder.order_no == order_no,
                    RechargeOrder.is_deleted == False
                )
            ).first()
            
            if not recharge_order:
                return {'success': False, 'message': '充值订单不存在'}
            
            if recharge_order.status != RechargeStatusEnum.PENDING:
                return {'success': False, 'message': '订单状态已处理'}
            
            # 获取用户信息
            user = self.db.query(User).filter(User.id == recharge_order.user_id).first()
            if not user:
                return {'success': False, 'message': '用户不存在'}
            
            # 更新充值订单状态
            recharge_order.status = RechargeStatusEnum.PAID
            recharge_order.transaction_id = transaction_id
            recharge_order.paid_at = datetime.now()
            
            # 更新用户余额和累计充值
            balance_before = user.balance
            user.balance += recharge_order.total_amount
            user.total_recharge += recharge_order.amount
            balance_after = user.balance
            
            # 创建余额变动记录
            balance_transaction = BalanceTransaction(
                user_id=user.id,
                transaction_type=TransactionTypeEnum.RECHARGE,
                amount=recharge_order.total_amount,
                balance_before=balance_before,
                balance_after=balance_after,
                related_type='recharge_order',
                related_id=recharge_order.id,
                description=f'充值{recharge_order.amount / 100}元，赠送{recharge_order.bonus_amount / 100}元'
            )
            
            self.db.add(balance_transaction)
            self.db.commit()
            
            return {
                'success': True,
                'message': '充值成功',
                'data': {
                    'user_balance': user.balance,
                    'recharge_amount': recharge_order.amount,
                    'bonus_amount': recharge_order.bonus_amount
                }
            }
            
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'message': f'处理支付成功失败: {str(e)}'}
    
    def get_user_recharge_orders(
        self, 
        user_id: int, 
        filters: Optional[RechargeFilterParams] = None,
        pagination: Optional[PaginationParams] = None
    ) -> List[RechargeOrder]:
        """获取用户充值订单列表"""
        query = self.db.query(RechargeOrder).filter(
            and_(
                RechargeOrder.user_id == user_id,
                RechargeOrder.is_deleted == False
            )
        )
        
        # 应用过滤条件
        if filters:
            if filters.status:
                query = query.filter(RechargeOrder.status == filters.status)
            if filters.start_date:
                query = query.filter(RechargeOrder.created_at >= filters.start_date)
            if filters.end_date:
                query = query.filter(RechargeOrder.created_at <= filters.end_date)
        
        # 排序和分页
        query = query.order_by(desc(RechargeOrder.created_at))
        
        if pagination:
            offset = (pagination.page - 1) * pagination.size
            query = query.offset(offset).limit(pagination.size)
        
        return query.all()
    
    def get_user_balance_transactions(
        self,
        user_id: int,
        filters: Optional[BalanceTransactionFilterParams] = None,
        pagination: Optional[PaginationParams] = None
    ) -> List[BalanceTransaction]:
        """获取用户余额变动记录"""
        query = self.db.query(BalanceTransaction).filter(
            BalanceTransaction.user_id == user_id
        )
        
        # 应用过滤条件
        if filters:
            if filters.transaction_type:
                query = query.filter(BalanceTransaction.transaction_type == filters.transaction_type)
            if filters.start_date:
                query = query.filter(BalanceTransaction.created_at >= filters.start_date)
            if filters.end_date:
                query = query.filter(BalanceTransaction.created_at <= filters.end_date)
        
        # 排序和分页
        query = query.order_by(desc(BalanceTransaction.created_at))
        
        if pagination:
            offset = (pagination.page - 1) * pagination.size
            query = query.offset(offset).limit(pagination.size)
        
        return query.all()
    
    def get_user_balance(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户余额信息"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        return {
            'balance': user.balance,
            'total_recharge': user.total_recharge
        }