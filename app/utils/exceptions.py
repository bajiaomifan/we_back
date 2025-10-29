from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BusinessException(Exception):
    """业务异常基类"""
    
    def __init__(
        self, 
        message: str, 
        code: int = status.HTTP_400_BAD_REQUEST,
        data: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(self.message)


class AuthenticationError(BusinessException):
    """认证异常"""
    
    def __init__(self, message: str = "认证失败"):
        super().__init__(
            message=message,
            code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(BusinessException):
    """授权异常"""
    
    def __init__(self, message: str = "权限不足"):
        super().__init__(
            message=message,
            code=status.HTTP_403_FORBIDDEN
        )


class ResourceNotFoundError(BusinessException):
    """资源不存在异常"""
    
    def __init__(self, message: str = "资源不存在"):
        super().__init__(
            message=message,
            code=status.HTTP_404_NOT_FOUND
        )


class ValidationError(BusinessException):
    """参数验证异常"""
    
    def __init__(self, message: str = "参数验证失败"):
        super().__init__(
            message=message,
            code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class PaymentError(BusinessException):
    """支付异常"""
    
    def __init__(self, message: str = "支付失败"):
        super().__init__(
            message=message,
            code=status.HTTP_400_BAD_REQUEST
        )


class DatabaseError(BusinessException):
    """数据库异常"""
    
    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(
            message=message,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )