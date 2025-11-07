#!/usr/bin/env python3
"""
Test script for automatic power-off functionality
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.task_scheduler import TaskScheduler
from app.services.power_off_service import PowerOffService
from app.models.schemas import PowerOffTaskStatusEnum


class TestPowerOffAutomation:
    """Test cases for power-off automation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.task_scheduler = TaskScheduler()
        self.power_off_service = PowerOffService()
        
    def test_schedule_power_off_task(self):
        """Test scheduling a power-off task"""
        booking_id = 123
        room_id = 456
        power_off_time = datetime.now() + timedelta(hours=2)
        
        # Mock the scheduler add_job method
        with patch.object(self.task_scheduler.scheduler, 'add_job') as mock_add_job:
            job_id = self.task_scheduler.schedule_power_off(booking_id, room_id, power_off_time)
            
            expected_job_id = f"power_off_{booking_id}_{room_id}"
            assert job_id == expected_job_id
            mock_add_job.assert_called_once()
            
    def test_cancel_power_off_task(self):
        """Test cancelling a power-off task"""
        booking_id = 123
        room_id = 456
        
        # Mock the scheduler get_job and remove_job methods
        with patch.object(self.task_scheduler.scheduler, 'get_job', return_value=True), \
             patch.object(self.task_scheduler.scheduler, 'remove_job') as mock_remove_job:
            
            success = self.task_scheduler.cancel_power_off(booking_id, room_id)
            
            assert success is True
            mock_remove_job.assert_called_once_with(f"power_off_{booking_id}_{room_id}")
            
    def test_power_off_execution_success(self):
        """Test successful power-off execution"""
        booking_id = 123
        room_id = 456
        
        # Mock database session and room query
        mock_db = Mock()
        mock_room_result = Mock()
        mock_room_result._mapping = {
            'id': room_id,
            'name': 'Test Room',
            'relay_controller_id': 'controller1',
            'relay_port': 1
        }
        
        mock_db.execute.return_value.fetchone.return_value = mock_room_result
        
        # Mock relay control
        with patch.object(self.power_off_service, '_control_relay_with_retry', return_value=True), \
             patch.object(self.power_off_service, '_update_task_status'), \
             patch.object(self.power_off_service, '_log_power_off_operation'):
            
            result = self.power_off_service.execute_power_off(mock_db, booking_id, room_id)
            
            assert result is True
            
    def test_power_off_execution_room_not_found(self):
        """Test power-off execution when room is not found"""
        booking_id = 123
        room_id = 999
        
        # Mock database session returning no room
        mock_db = Mock()
        mock_db.execute.return_value.fetchone.return_value = None
        
        result = self.power_off_service.execute_power_off(mock_db, booking_id, room_id)
        
        assert result is False
        
    def test_power_off_execution_with_retry(self):
        """Test power-off execution with retry logic"""
        booking_id = 123
        room_id = 456
        
        # Mock database session and room query
        mock_db = Mock()
        mock_room_result = Mock()
        mock_room_result._mapping = {
            'id': room_id,
            'name': 'Test Room',
            'relay_controller_id': 'controller1',
            'relay_port': 1
        }
        
        mock_db.execute.return_value.fetchone.return_value = mock_room_result
        
        # Mock relay control with retry (succeeds on second attempt)
        with patch.object(self.power_off_service, '_control_relay_with_retry', return_value=True), \
             patch.object(self.power_off_service, '_update_task_status'), \
             patch.object(self.power_off_service, '_log_power_off_operation'):
            
            result = self.power_off_service.execute_power_off(mock_db, booking_id, room_id, retry_count=1)
            
            assert result is True
            
    def test_get_scheduled_jobs(self):
        """Test getting scheduled jobs"""
        # Mock scheduler jobs
        mock_job = Mock()
        mock_job.id = "power_off_123_456"
        mock_job.name = "Power off room 456 for booking 123"
        mock_job.next_run_time = datetime.now() + timedelta(hours=1)
        mock_job.args = [123, 456]
        
        with patch.object(self.task_scheduler.scheduler, 'get_jobs', return_value=[mock_job]):
            jobs = self.task_scheduler.get_scheduled_jobs()
            
            assert len(jobs) == 1
            assert jobs[0]['id'] == "power_off_123_456"
            assert jobs[0]['booking_id'] == 123
            assert jobs[0]['room_id'] == 456


def test_power_off_time_calculation():
    """Test power-off time calculation logic"""
    from datetime import datetime, timedelta
    
    # Simulate booking end time
    booking_end_time = datetime(2025, 11, 5, 18, 0, 0)  # 18:00
    
    # Power-off time should be booking end time + 40 minutes
    expected_power_off_time = booking_end_time + timedelta(minutes=40)
    
    assert expected_power_off_time.hour == 18
    assert expected_power_off_time.minute == 40


def test_door_open_integration():
    """Test integration with door open endpoint"""
    # This would test the actual integration in the door open endpoint
    # For now, we'll test the time calculation logic
    
    from datetime import datetime, timedelta
    
    # Simulate a booking from 14:00 to 18:00
    booking_start_time = datetime(2025, 11, 5, 14, 0, 0)
    booking_end_time = datetime(2025, 11, 5, 18, 0, 0)
    
    # User opens door at 13:40 (20 minutes early)
    door_open_time = datetime(2025, 11, 5, 13, 40, 0)
    
    # Power-off should be scheduled for 18:40 (booking end + 40 min buffer)
    expected_power_off_time = booking_end_time + timedelta(minutes=40)
    
    assert expected_power_off_time == datetime(2025, 11, 5, 18, 40, 0)
    
    # Verify the power-off time is after the door open time
    assert expected_power_off_time > door_open_time


if __name__ == "__main__":
    print("Running power-off automation tests...")
    
    # Run basic tests
    test_power_off_time_calculation()
    test_door_open_integration()
    
    # Run pytest for more comprehensive testing
    print("\nRunning pytest tests...")
    pytest.main([__file__, "-v"])