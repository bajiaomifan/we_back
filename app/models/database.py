from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Index, inspect, Numeric, Float, UniqueConstraint, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Mapped, mapped_column
from sqlalchemy.sql import func, text
from datetime import datetime
from typing import Optional
from decimal import Decimal
from enum import Enum

from app.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.NODE_ENV == "development"
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


class BookingStatusEnum(str, Enum):
    """预订状态枚举"""
    PENDING = "pending"          # 待确认
    CONFIRMED = "confirmed"      # 已确认
    USING = "using"              # 使用中
    COMPLETED = "completed"      # 已完成
    CANCELLED = "cancelled"      # 已取消


class RoomStatusEnum(str, Enum):
    """房间状态枚举"""
    AVAILABLE = "available"      # 可用
    OCCUPIED = "occupied"        # 占用
    MAINTENANCE = "maintenance"  # 维护中
    DISABLED = "disabled"        # 禁用


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="用户ID")
    openid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="微信openid")
    unionid: Mapped[Optional[str]] = mapped_column(String(64), index=True, comment="微信unionid")
    nickname: Mapped[Optional[str]] = mapped_column(String(100), comment="用户昵称")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), comment="头像URL")
    phone: Mapped[Optional[str]] = mapped_column(String(20), comment="手机号")
    email: Mapped[Optional[str]] = mapped_column(String(100), comment="邮箱")
    gender: Mapped[Optional[int]] = mapped_column(Integer, default=0, comment="性别：0-未知，1-男，2-女")
    country: Mapped[Optional[str]] = mapped_column(String(50), comment="国家")
    province: Mapped[Optional[str]] = mapped_column(String(50), comment="省份")
    city: Mapped[Optional[str]] = mapped_column(String(50), comment="城市")
    language: Mapped[Optional[str]] = mapped_column(String(20), comment="语言")
    balance: Mapped[int] = mapped_column(Integer, default=0, comment="用户余额（分）")
    total_recharge: Mapped[int] = mapped_column(Integer, default=0, comment="累计充值金额（分）")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否删除")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    audit_logs = relationship("AuditLog", back_populates="user")
    sessions = relationship("UserSession", backref="user")
    
    # 创建索引
    __table_args__ = (
        Index('idx_user_openid_deleted', 'openid', 'is_deleted'),
        Index('idx_user_created_at', 'created_at'),
    )


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="日志ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作类型")
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), comment="资源类型")
    resource_id: Mapped[Optional[str]] = mapped_column(String(50), comment="资源ID")
    old_value: Mapped[Optional[str]] = mapped_column(Text, comment="旧值")
    new_value: Mapped[Optional[str]] = mapped_column(Text, comment="新值")
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), comment="IP地址")
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), comment="用户代理")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="操作描述")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    
    # 关系
    user = relationship("User", back_populates="audit_logs")
    
    # 创建索引
    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_created_at', 'created_at'),
    )


class UserSession(Base):
    """用户会话表"""
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="会话ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, comment="JWT访问令牌")
    refresh_token: Mapped[Optional[str]] = mapped_column(String(500), unique=True, comment="JWT刷新令牌")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="访问令牌过期时间")
    refresh_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="刷新令牌过期时间")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活")
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), comment="IP地址")
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), comment="用户代理")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    
    # 创建索引
    __table_args__ = (
        Index('idx_session_user_token', 'user_id', 'token'),
        Index('idx_session_refresh_token', 'refresh_token'),
        Index('idx_session_expires_at', 'expires_at'),
        Index('idx_session_refresh_expires_at', 'refresh_expires_at'),
    )


class PaymentOrder(Base):
    """支付订单表"""
    __tablename__ = "payment_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="订单ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    openid: Mapped[str] = mapped_column(String(64), nullable=False, comment="用户openid")
    out_trade_no: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="商户订单号")
    body: Mapped[str] = mapped_column(String(128), nullable=False, comment="商品描述")
    total_fee: Mapped[int] = mapped_column(Integer, nullable=False, comment="总金额（分）")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="支付状态")
    transaction_id: Mapped[Optional[str]] = mapped_column(String(32), comment="微信支付订单号")
    prepay_id: Mapped[Optional[str]] = mapped_column(String(64), comment="预支付交易会话标识")
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), comment="客户端IP")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="支付完成时间")
    
    # 关系
    user = relationship("User", backref="payment_orders")
    
    # 创建索引
    __table_args__ = (
        Index('idx_payment_user_id', 'user_id'),
        Index('idx_payment_out_trade_no', 'out_trade_no'),
        Index('idx_payment_transaction_id', 'transaction_id'),
        Index('idx_payment_status', 'status'),
        Index('idx_payment_created_at', 'created_at'),
    )


class RechargeOrder(Base):
    """充值订单表"""
    __tablename__ = "recharge_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="充值订单ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    openid: Mapped[str] = mapped_column(String(64), nullable=False, comment="用户openid")
    order_no: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="充值订单号")
    amount: Mapped[int] = mapped_column(Integer, nullable=False, comment="充值金额（分）")
    bonus_amount: Mapped[int] = mapped_column(Integer, default=0, comment="赠送金额（分）")
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False, comment="到账总额（分）")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="充值状态")
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), comment="支付方式")
    payment_order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("payment_orders.id"), comment="关联的支付订单ID")
    transaction_id: Mapped[Optional[str]] = mapped_column(String(32), comment="微信支付订单号")
    prepay_id: Mapped[Optional[str]] = mapped_column(String(64), comment="预支付交易会话标识")
    description: Mapped[Optional[str]] = mapped_column(String(255), comment="充值说明")
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), comment="客户端IP")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否删除")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="支付完成时间")
    
    # 关系
    user = relationship("User", backref="recharge_orders")
    payment_order = relationship("PaymentOrder", backref="recharge_orders")
    
    # 创建索引
    __table_args__ = (
        Index('idx_recharge_user_id', 'user_id'),
        Index('idx_recharge_order_no', 'order_no'),
        Index('idx_recharge_status', 'status'),
        Index('idx_recharge_created_at', 'created_at'),
        Index('idx_recharge_deleted', 'is_deleted'),
    )


class RechargeActivity(Base):
    """充值活动表"""
    __tablename__ = "recharge_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="活动ID")
    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="活动标题")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="活动描述")
    recharge_amount: Mapped[int] = mapped_column(Integer, nullable=False, comment="充值金额（分）")
    bonus_amount: Mapped[int] = mapped_column(Integer, nullable=False, comment="赠送金额（分）")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序顺序")
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="开始时间")
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="结束时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 创建索引
    __table_args__ = (
        Index('idx_recharge_activity_active', 'is_active'),
        Index('idx_recharge_activity_sort', 'sort_order'),
    )


class BalanceTransaction(Base):
    """余额变动记录表"""
    __tablename__ = "balance_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="记录ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="交易类型：recharge-充值，consume-消费，refund-退款")
    amount: Mapped[int] = mapped_column(Integer, nullable=False, comment="变动金额（分）")
    balance_before: Mapped[int] = mapped_column(Integer, nullable=False, comment="变动前余额（分）")
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False, comment="变动后余额（分）")
    related_type: Mapped[Optional[str]] = mapped_column(String(20), comment="关联类型：recharge_order-充值订单，booking-预订")
    related_id: Mapped[Optional[int]] = mapped_column(Integer, comment="关联ID")
    description: Mapped[Optional[str]] = mapped_column(String(255), comment="变动说明")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    
    # 关系
    user = relationship("User", backref="balance_transactions")
    
    # 创建索引
    __table_args__ = (
        Index('idx_balance_user_id', 'user_id'),
        Index('idx_balance_type', 'transaction_type'),
        Index('idx_balance_created_at', 'created_at'),
        Index('idx_balance_related', 'related_type', 'related_id'),
    )


class Store(Base):
    """店面表"""
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="店面ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="店面名称")
    address: Mapped[str] = mapped_column(String(255), nullable=False, comment="店面地址")
    phone: Mapped[str] = mapped_column(String(20), nullable=False, comment="联系电话")
    business_hours: Mapped[str] = mapped_column(String(100), default="24小时营业", comment="营业时间")
    rating: Mapped[float] = mapped_column(Float, default=5.0, comment="评分")
    image_url: Mapped[Optional[str]] = mapped_column(String(255), comment="店面图片URL")
    latitude: Mapped[Optional[float]] = mapped_column(Float, comment="纬度")
    longitude: Mapped[Optional[float]] = mapped_column(Float, comment="经度")
    features: Mapped[Optional[str]] = mapped_column(Text, comment="店面特色（JSON格式）")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="店面描述")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否营业")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    rooms = relationship("Room", back_populates="store")
    
    # 创建索引
    __table_args__ = (
        Index('idx_store_name', 'name'),
        Index('idx_store_is_active', 'is_active'),
    )


class Room(Base):
    """包间表"""
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="包间ID")
    store_id: Mapped[int] = mapped_column(Integer, ForeignKey("stores.id"), nullable=False, comment="店面ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="包间名称")
    capacity: Mapped[str] = mapped_column(String(20), nullable=False, comment="容量（如：4-6人）")
    price: Mapped[float] = mapped_column(Float, nullable=False, comment="每小时价格")
    unit: Mapped[str] = mapped_column(String(10), default="小时", comment="计费单位")
    discount: Mapped[Optional[float]] = mapped_column(Float, comment="折扣（0.8表示8折）")
    images: Mapped[Optional[str]] = mapped_column(Text, comment="包间图片URLs（JSON格式）")
    features: Mapped[Optional[str]] = mapped_column(Text, comment="包间特色（JSON格式）")
    facilities: Mapped[Optional[str]] = mapped_column(Text, comment="包间设施（JSON格式）")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="包间描述")
    booking_rules: Mapped[Optional[str]] = mapped_column(Text, comment="预订须知（JSON格式）")
    rating: Mapped[float] = mapped_column(Float, default=5.0, comment="评分")
    review_count: Mapped[int] = mapped_column(Integer, default=0, comment="评价数量")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否可用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    store = relationship("Store", back_populates="rooms")
    bookings = relationship("Booking", back_populates="room")
    reviews = relationship("Review", back_populates="room")
    
    # 创建索引
    __table_args__ = (
        Index('idx_room_store_id', 'store_id'),
        Index('idx_room_is_available', 'is_available'),
        Index('idx_room_price', 'price'),
    )


class BookingTimeSlot(Base):
    """预订时间段详情表 - 用于存储每个小时的占用情况"""
    __tablename__ = "booking_time_slots"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="时间段ID")
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), nullable=False, comment="预订ID")
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False, comment="包间ID")
    date: Mapped[datetime] = mapped_column(Date, nullable=False, comment="日期")
    hour: Mapped[int] = mapped_column(Integer, nullable=False, comment="小时（0-23）")
    timestamp_start: Mapped[int] = mapped_column(Integer, nullable=False, comment="该小时开始时间戳")
    timestamp_end: Mapped[int] = mapped_column(Integer, nullable=False, comment="该小时结束时间戳")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    
    # 关系
    booking = relationship("Booking", back_populates="time_slots")
    room = relationship("Room")
    
    # 创建索引
    __table_args__ = (
        Index('idx_booking_time_slot_room_date_hour', 'room_id', 'date', 'hour'),
        Index('idx_booking_time_slot_booking_id', 'booking_id'),
        Index('idx_booking_time_slot_timestamp', 'timestamp_start', 'timestamp_end'),
        # 确保同一包间同一小时不能重复预订
        UniqueConstraint('room_id', 'date', 'hour', name='uk_room_date_hour'),
    )


class Booking(Base):
    """预订表"""
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="预订ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False, comment="包间ID")
    booking_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="预订日期")
    start_time: Mapped[int] = mapped_column(Integer, nullable=False, comment="开始时间戳（10位秒级）")
    end_time: Mapped[int] = mapped_column(Integer, nullable=False, comment="结束时间戳（10位秒级）")
    duration: Mapped[int] = mapped_column(Integer, nullable=False, comment="时长（小时）")
    contact_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="联系人姓名")
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False, comment="联系电话")
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注信息")
    original_amount: Mapped[float] = mapped_column(Float, nullable=False, comment="原始金额")
    discount_amount: Mapped[float] = mapped_column(Float, default=0, comment="优惠金额")
    final_amount: Mapped[float] = mapped_column(Float, nullable=False, comment="最终金额")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="状态：pending,confirmed,using,completed,cancelled")
    payment_order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("payment_orders.id"), comment="关联支付订单ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    user = relationship("User", backref="bookings")
    room = relationship("Room", back_populates="bookings")
    payment_order = relationship("PaymentOrder", backref="booking")
    time_slots = relationship("BookingTimeSlot", back_populates="booking", cascade="all, delete-orphan")
    
    # 创建索引
    __table_args__ = (
        Index('idx_booking_user_id', 'user_id'),
        Index('idx_booking_room_id', 'room_id'),
        Index('idx_booking_date', 'booking_date'),
        Index('idx_booking_status', 'status'),
        Index('idx_booking_created_at', 'created_at'),
    )


class Review(Base):
    """评价表"""
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="评价ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False, comment="包间ID")
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), nullable=False, comment="预订ID")
    rating: Mapped[int] = mapped_column(Integer, nullable=False, comment="评分（1-5）")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="评价内容")
    images: Mapped[Optional[str]] = mapped_column(Text, comment="评价图片URLs（JSON格式）")
    reply: Mapped[Optional[str]] = mapped_column(Text, comment="商家回复")
    reply_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="回复时间")
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否匿名")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    user = relationship("User", backref="reviews")
    room = relationship("Room", back_populates="reviews")
    booking = relationship("Booking", backref="review")
    
    # 创建索引
    __table_args__ = (
        Index('idx_review_user_id', 'user_id'),
        Index('idx_review_room_id', 'room_id'),
        Index('idx_review_booking_id', 'booking_id'),
        Index('idx_review_rating', 'rating'),
        Index('idx_review_created_at', 'created_at'),
    )


class NotificationTypeEnum(str, Enum):
    """通知类型枚举"""
    BOOKING_REMINDER = "booking_reminder"  # 预订提醒
    BOOKING_EXPIRED = "booking_expired"    # 预订到期
    BOOKING_CANCELLED = "booking_cancelled"  # 预订取消


class NotificationStatusEnum(str, Enum):
    """通知状态枚举"""
    PENDING = "pending"      # 待发送
    SENT = "sent"           # 已发送
    FAILED = "failed"       # 发送失败
    RETRY = "retry"         # 重试中


class BookingNotification(Base):
    """预订通知表"""
    __tablename__ = "booking_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="通知ID")
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), nullable=False, comment="预订ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="通知类型")
    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="通知标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="通知内容")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="通知状态")
    send_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="发送时间")
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="重试次数")
    max_retries: Mapped[int] = mapped_column(Integer, default=3, comment="最大重试次数")
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否删除")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    booking = relationship("Booking", backref="notifications")
    user = relationship("User", backref="notifications")
    
    # 创建索引
    __table_args__ = (
        Index('idx_notification_booking_id', 'booking_id'),
        Index('idx_notification_user_id', 'user_id'),
        Index('idx_notification_type', 'notification_type'),
        Index('idx_notification_status', 'status'),
        Index('idx_notification_created_at', 'created_at'),
        Index('idx_notification_deleted', 'is_deleted'),
    )


class ScheduledTaskStatusEnum(str, Enum):
    """定时任务状态枚举"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消


class ScheduledTask(Base):
    """定时任务表"""
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="任务ID")
    task_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="任务唯一标识")
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="任务类型")
    related_type: Mapped[Optional[str]] = mapped_column(String(50), comment="关联类型")
    related_id: Mapped[Optional[int]] = mapped_column(Integer, comment="关联ID")
    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="任务标题")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="任务描述")
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="计划执行时间")
    executed_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="实际执行时间")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="任务状态")
    result: Mapped[Optional[str]] = mapped_column(Text, comment="执行结果")
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息")
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="重试次数")
    max_retries: Mapped[int] = mapped_column(Integer, default=3, comment="最大重试次数")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否删除")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 创建索引
    __table_args__ = (
        Index('idx_task_task_id', 'task_id'),
        Index('idx_task_type', 'task_type'),
        Index('idx_task_related', 'related_type', 'related_id'),
        Index('idx_task_scheduled_time', 'scheduled_time'),
        Index('idx_task_status', 'status'),
        Index('idx_task_deleted', 'is_deleted'),
    )


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """创建所有表并添加缺失字段"""
    # 获取数据库元数据
    metadata = Base.metadata
    
    # 检查表是否存在并创建缺失表
    metadata.create_all(bind=engine)
    
    # 添加缺失字段
    add_missing_columns()

def add_missing_columns():
    """检查并添加缺失字段到现有表"""
    from sqlalchemy import inspect, text
    
    inspector = inspect(engine)
    
    # 需要检查的字段映射 {表名: [字段列表]}
    required_columns = {
        "user_sessions": ["refresh_token", "refresh_expires_at"],
        "payment_orders": ["prepay_id", "paid_at"]
    }
    
    with engine.begin() as conn:
        # 处理bookings表的时间字段迁移
        if inspector.has_table("bookings"):
            migrate_booking_time_fields(conn, inspector)
        
        for table_name, columns in required_columns.items():
            # 检查表是否存在
            if not inspector.has_table(table_name):
                continue
                
            # 获取现有字段
            existing_columns = [col["name"] for col in inspector.get_columns(table_name)]
            
            # 添加缺失字段
            for column in columns:
                if column not in existing_columns:
                    # 根据表名和字段确定添加语句
                    if table_name == "user_sessions":
                        if column == "refresh_token":
                            conn.execute(text(
                                "ALTER TABLE user_sessions ADD COLUMN refresh_token VARCHAR(500)"
                            ))
                        elif column == "refresh_expires_at":
                            conn.execute(text(
                                "ALTER TABLE user_sessions ADD COLUMN refresh_expires_at TIMESTAMP"
                            ))
                    elif table_name == "payment_orders":
                        if column == "prepay_id":
                            conn.execute(text(
                                "ALTER TABLE payment_orders ADD COLUMN prepay_id VARCHAR(64)"
                            ))
                        elif column == "paid_at":
                            conn.execute(text(
                                "ALTER TABLE payment_orders ADD COLUMN paid_at TIMESTAMP"
                            ))

def migrate_booking_time_fields(conn, inspector):
    """迁移 bookings 表的时间字段从字符串到时间戳"""
    from sqlalchemy import text
    from datetime import datetime
    
    # 检查 start_time 和 end_time 字段的类型
    columns = inspector.get_columns("bookings")
    start_time_col = None
    end_time_col = None
    
    for col in columns:
        if col["name"] == "start_time":
            start_time_col = col
        elif col["name"] == "end_time":
            end_time_col = col
    
    # 如果字段是 VARCHAR 类型，需要迁移
    if (start_time_col and "VARCHAR" in str(start_time_col["type"]).upper()) or \
       (end_time_col and "VARCHAR" in str(end_time_col["type"]).upper()):
        
        print("🔄 检测到 bookings 表的时间字段需要迁移...")
        
        try:
            # 步骤1：添加新的时间戳字段
            conn.execute(text("""
                ALTER TABLE bookings 
                ADD COLUMN start_time_timestamp INTEGER,
                ADD COLUMN end_time_timestamp INTEGER
            """))
            
            # 步骤2：将现有数据转换为时间戳（使用示例时间）
            # 注意：这里使用示例时间戳，实际部署时需要根据实际数据调整
            current_timestamp = int(datetime.now().timestamp())
            conn.execute(text(f"""
                UPDATE bookings 
                SET start_time_timestamp = {current_timestamp},
                    end_time_timestamp = {current_timestamp + 4 * 3600}
                WHERE start_time_timestamp IS NULL
            """))
            
            # 步骤3：删除旧字段
            conn.execute(text("ALTER TABLE bookings DROP COLUMN start_time"))
            conn.execute(text("ALTER TABLE bookings DROP COLUMN end_time"))
            
            # 步骤4：重命名新字段
            conn.execute(text("ALTER TABLE bookings RENAME COLUMN start_time_timestamp TO start_time"))
            conn.execute(text("ALTER TABLE bookings RENAME COLUMN end_time_timestamp TO end_time"))
            
            # 步骤5：设置为非空
            conn.execute(text("ALTER TABLE bookings MODIFY COLUMN start_time INTEGER NOT NULL"))
            conn.execute(text("ALTER TABLE bookings MODIFY COLUMN end_time INTEGER NOT NULL"))
            
            print("✅ bookings 表时间字段迁移完成")
            
        except Exception as e:
            print(f"⚠️ bookings 表时间字段迁移失败: {e}")
            # 如果迁移失败，尝试回滚变更
            try:
                conn.execute(text("ALTER TABLE bookings DROP COLUMN IF EXISTS start_time_timestamp"))
                conn.execute(text("ALTER TABLE bookings DROP COLUMN IF EXISTS end_time_timestamp"))
            except:
                pass

def validate_tables():
    """验证表结构是否正确"""
    inspector = inspect(engine)
    required_tables = ["users", "audit_logs", "user_sessions", "payment_orders"]
    
    # 检查表是否存在
    missing_tables = [table for table in required_tables if not inspector.has_table(table)]
    if missing_tables:
        raise RuntimeError(f"缺失表: {', '.join(missing_tables)}")
    
    # 检查user_sessions表的字段
    if inspector.has_table("user_sessions"):
        session_columns = [col["name"] for col in inspector.get_columns("user_sessions")]
        required_columns = ["refresh_token", "refresh_expires_at"]
        missing_columns = [col for col in required_columns if col not in session_columns]
        
        if missing_columns:
            raise RuntimeError(f"user_sessions表缺失字段: {', '.join(missing_columns)}")
    
    # 检查payment_orders表的字段
    if inspector.has_table("payment_orders"):
        payment_columns = [col["name"] for col in inspector.get_columns("payment_orders")]
        required_columns = ["prepay_id", "paid_at"]
        missing_columns = [col for col in required_columns if col not in payment_columns]
        
        if missing_columns:
            raise RuntimeError(f"payment_orders表缺失字段: {', '.join(missing_columns)}")
    
    return "所有表结构验证通过"


def init_room_sample_data():
    """初始化棋牌室示例数据（仅在表为空时执行）"""
    from sqlalchemy.orm import sessionmaker
    import json
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 检查是否已有数据
        existing_store = session.query(Store).first()
        if existing_store:
            print("ℹ️ 棋牌室数据已存在，跳过初始化")
            return
        
        print("📄 开始初始化棋牌室示例数据...")
        
        # 插入店面数据
        store = Store(
            name="星辉棋牌室",
            address="北京市朝阳区三里屯街道111号",
            phone="010-12345678",
            business_hours="24小时营业",
            rating=4.8,
            image_url="https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=300&fit=crop",
            latitude=39.9042,
            longitude=116.4074,
            features=json.dumps(["免费WiFi", "空调", "免费茶水", "24小时营业"]),
            description="星辉棋牌室是一家现代化的休闲娱乐场所，提供多种规格的包间供您选择。",
            is_active=True
        )
        session.add(store)
        session.flush()
        
        # 插入包间数据
        rooms_data = [
            {
                "name": "豪华大包间",
                "capacity": "6-8人",
                "price": 88.0,
                "discount": 0.8,
                "images": json.dumps([
                    "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=300&h=200&fit=crop",
                    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=300&h=200&fit=crop"
                ]),
                "features": json.dumps(["超大空间", "豪华装修", "独立洗手间"]),
                "facilities": json.dumps([
                    {"name": "空调", "icon": "❄️"},
                    {"name": "WiFi", "icon": "📶"},
                    {"name": "茶水", "icon": "🍵"},
                    {"name": "洗手间", "icon": "😽"}
                ]),
                "description": "豪华大包间装修精美，空间宽敞，适合朋友聚会或商务接待。",
                "booking_rules": json.dumps([
                    "请提前15分钟到店，逾期可能影响使用时间",
                    "如需取消或改期，请提前2小时联系商家",
                    "包间内禁止吸烟，请保持环境整洁",
                    "如有特殊需求，请在备注中说明"
                ]),
                "rating": 4.9,
                "review_count": 23
            },
            {
                "name": "标准包间A",
                "capacity": "4-6人",
                "price": 58.0,
                "discount": None,
                "images": json.dumps([
                    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=300&h=200&fit=crop"
                ]),
                "features": json.dumps(["标准配置", "舒适环境"]),
                "facilities": json.dumps([
                    {"name": "空调", "icon": "❄️"},
                    {"name": "WiFi", "icon": "📶"},
                    {"name": "茶水", "icon": "🍵"}
                ]),
                "description": "标准包间设施齐全，环境舒适，性价比高。",
                "booking_rules": json.dumps([
                    "请提前15分钟到店，逾期可能影响使用时间",
                    "如需取消或改期，请提前2小时联系商家",
                    "包间内禁止吸烟，请保持环境整洁"
                ]),
                "rating": 4.7,
                "review_count": 15
            },
            {
                "name": "标准包间B",
                "capacity": "4-6人",
                "price": 58.0,
                "discount": None,
                "images": json.dumps([
                    "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=300&h=200&fit=crop"
                ]),
                "features": json.dumps(["标准配置", "舒适环境"]),
                "facilities": json.dumps([
                    {"name": "空调", "icon": "❄️"},
                    {"name": "WiFi", "icon": "📶"},
                    {"name": "茶水", "icon": "🍵"}
                ]),
                "description": "标准包间设施齐全，环境舒适，性价比高。",
                "booking_rules": json.dumps([
                    "请提前15分钟到店，逾期可能影响使用时间",
                    "如需取消或改期，请提前2小时联系商家",
                    "包间内禁止吸烟，请保持环境整洁"
                ]),
                "rating": 4.6,
                "review_count": 12,
                "is_available": False  # 暂不可用
            },
            {
                "name": "精品小包间",
                "capacity": "2-4人",
                "price": 38.0,
                "discount": 0.9,
                "images": json.dumps([
                    "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=300&h=200&fit=crop"
                ]),
                "features": json.dumps(["温馨私密", "经济实惠"]),
                "facilities": json.dumps([
                    {"name": "空调", "icon": "❄️"},
                    {"name": "WiFi", "icon": "📶"},
                    {"name": "茶水", "icon": "🍵"}
                ]),
                "description": "精品小包间温馨私密，适合情侣约会或小聚。",
                "booking_rules": json.dumps([
                    "请提前15分钟到店，逾期可能影响使用时间",
                    "如需取消或改期，请提前2小时联系商家",
                    "包间内禁止吸烟，请保持环境整洁"
                ]),
                "rating": 4.8,
                "review_count": 8
            },
            {
                "name": "VIP至尊包间",
                "capacity": "8-12人",
                "price": 128.0,
                "discount": None,
                "images": json.dumps([
                    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=300&h=200&fit=crop",
                    "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=300&h=200&fit=crop"
                ]),
                "features": json.dumps(["超大空间", "顶级装修", "专属服务", "独立音响"]),
                "facilities": json.dumps([
                    {"name": "空调", "icon": "❄️"},
                    {"name": "WiFi", "icon": "📶"},
                    {"name": "茶水", "icon": "🍵"},
                    {"name": "洗手间", "icon": "😽"},
                    {"name": "音响", "icon": "🔊"},
                    {"name": "投影", "icon": "📽️"}
                ]),
                "description": "VIP至尊包间空间超大，装修豪华，提供专属服务。",
                "booking_rules": json.dumps([
                    "请提前15分钟到店，逾期可能影响使用时间",
                    "如需取消或改期，请提前2小时联系商家",
                    "包间内禁止吸烟，请保持环境整洁",
                    "如有特殊需求，请在备注中说明"
                ]),
                "rating": 5.0,
                "review_count": 5
            },
            {
                "name": "商务包间",
                "capacity": "6-8人",
                "price": 78.0,
                "discount": None,
                "images": json.dumps([
                    "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=300&h=200&fit=crop"
                ]),
                "features": json.dumps(["商务风格", "投影设备", "会议桌"]),
                "facilities": json.dumps([
                    {"name": "空调", "icon": "❄️"},
                    {"name": "WiFi", "icon": "📶"},
                    {"name": "茶水", "icon": "🍵"},
                    {"name": "投影", "icon": "📽️"},
                    {"name": "白板", "icon": "📋"}
                ]),
                "description": "商务包间设计简约大方，配备投影设备，适合商务会议。",
                "booking_rules": json.dumps([
                    "请提前15分钟到店，逾期可能影响使用时间",
                    "如需取消或改期，请提前2小时联系商家",
                    "包间内禁止吸烟，请保持环境整洁"
                ]),
                "rating": 4.5,
                "review_count": 7
            }
        ]
        
        # 创建包间记录
        for room_data in rooms_data:
            room = Room(
                store_id=store.id,
                **room_data
            )
            session.add(room)
        
        session.commit()
        print(f"✅ 成功创建 1 个店面和 {len(rooms_data)} 个包间")
        
    except Exception as e:
        session.rollback()
        print(f"⚠️ 初始化棋牌室数据时出错: {str(e)}")
        raise
    finally:
        session.close()