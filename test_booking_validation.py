"""
测试开门预订验证功能
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.services.booking_service import BookingService
from app.models.database import BookingStatusEnum

class TestDoorAccessValidation:
    """测试开门权限验证"""
    
    def test_valid_booking_allows_access(self):
        """测试有效预订允许开门"""
        # 模拟数据库会话
        mock_db = Mock()
        booking_service = BookingService(mock_db)
        
        # 模拟当前时间
        current_time = datetime.now()
        
        # 模拟有效预订
        mock_booking = Mock()
        mock_booking.start_time = current_time
        mock_booking.end_time = current_time + timedelta(hours=2)
        
        # 模拟数据库查询返回有效预订
        mock_query = Mock()
        mock_query.filter.return_value.join.return_value.filter.return_value.first.return_value = mock_booking
        mock_db.query.return_value = mock_query
        
        # 执行验证
        result = booking_service.validate_door_access(user_id=1, door_id=1)
        
        # 验证结果
        assert result['valid'] == True
        assert 'booking' in result
        assert result['message'] == '验证通过，可以开门'
    
    def test_no_booking_denies_access(self):
        """测试无预订拒绝开门"""
        mock_db = Mock()
        booking_service = BookingService(mock_db)
        
        # 模拟数据库查询返回None（无预订）
        mock_query = Mock()
        mock_query.filter.return_value.join.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # 执行验证
        result = booking_service.validate_door_access(user_id=1, door_id=1)
        
        # 验证结果
        assert result['valid'] == False
        assert result['reason'] == 'no_booking'
        assert '您当前没有有效预订，无法开门' in result['message']
    
    def test_too_early_denies_access(self):
        """测试超过1小时提前时间拒绝开门"""
        mock_db = Mock()
        booking_service = BookingService(mock_db)
        
        # 模拟未来2小时的预订
        current_time = datetime.now()
        future_booking = Mock()
        future_booking.start_time = current_time + timedelta(hours=2)
        future_booking.end_time = current_time + timedelta(hours=4)
        
        mock_query = Mock()
        mock_query.filter.return_value.join.return_value.filter.return_value.first.return_value = future_booking
        mock_db.query.return_value = mock_query
        
        # 执行验证
        result = booking_service.validate_door_access(user_id=1, door_id=1)
        
        # 验证结果
        assert result['valid'] == False
        assert result['reason'] == 'too_early'
        assert '距离预订时间超过1小时，无法开门' in result['message']
    
    def test_expired_booking_denies_access(self):
        """测试过期预订拒绝开门"""
        mock_db = Mock()
        booking_service = BookingService(mock_db)
        
        # 模拟已过期的预订
        current_time = datetime.now()
        expired_booking = Mock()
        expired_booking.start_time = current_time - timedelta(hours=3)
        expired_booking.end_time = current_time - timedelta(hours=1)
        
        mock_query = Mock()
        mock_query.filter.return_value.join.return_value.filter.return_value.first.return_value = expired_booking
        mock_db.query.return_value = mock_query
        
        # 执行验证
        result = booking_service.validate_door_access(user_id=1, door_id=1)
        
        # 验证结果
        assert result['valid'] == False
        assert result['reason'] == 'expired'
        assert '您的预订已过期，无法开门' in result['message']

if __name__ == "__main__":
    pytest.main([__file__])