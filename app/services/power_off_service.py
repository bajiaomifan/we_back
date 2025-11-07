from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import httpx

from app.models.schemas import PowerOffTaskCreate, PowerOffTask, PowerOffTaskStatusEnum
from app.models.database import get_db

logger = logging.getLogger(__name__)

class PowerOffService:
    def __init__(self):
        self.relay_base_url = "http://192.168.1.100"  # Configure based on your relay controller
        
    def execute_power_off(self, db: Session, booking_id: int, room_id: int, retry_count: int = 0) -> bool:
        """
        Execute power-off for a room with retry logic
        
        Args:
            db: Database session
            booking_id: ID of the booking
            room_id: ID of the room
            retry_count: Current retry attempt
            
        Returns:
            bool: True if successful, False otherwise
        """
        max_retries = 3
        retry_delay = 5  # seconds
        
        try:
            # Get room details for relay control
            room_query = text("SELECT id, name, relay_controller_id, relay_port FROM rooms WHERE id = :room_id")
            room_result = db.execute(room_query, {"room_id": room_id}).fetchone()
            
            if not room_result:
                logger.error(f"Room {room_id} not found")
                return False
            
            room = dict(room_result._mapping)
            
            # Execute relay power-off with retry
            success = self._control_relay_with_retry(room['relay_controller_id'], room['relay_port'], False, retry_count, max_retries, retry_delay)
            
            if success:
                # Update task status in database
                self._update_task_status(db, booking_id, room_id, 'completed', datetime.utcnow())
                
                # Log the power-off operation
                self._log_power_off_operation(db, booking_id, room_id, 'success', f'Automatic power-off completed (retry {retry_count})')
                
                logger.info(f"Successfully powered off room {room_id} for booking {booking_id}")
                return True
            else:
                # Log failure
                self._log_power_off_operation(db, booking_id, room_id, 'failed', f'Relay control failed after {retry_count + 1} attempts')
                
                logger.error(f"Failed to power off room {room_id} for booking {booking_id} after {retry_count + 1} attempts")
                return False
                
        except Exception as e:
            logger.error(f"Error executing power-off for booking {booking_id}, room {room_id}: {e}")
            
            # Log error
            try:
                self._log_power_off_operation(db, booking_id, room_id, 'error', f'Exception: {str(e)} (retry {retry_count})')
            except:
                pass
                
            return False
    
    def _control_relay(self, controller_id: str, port: int, turn_on: bool) -> bool:
        """
        Control relay via HTTP request
        
        Args:
            controller_id: ID of the relay controller
            port: Relay port number
            turn_on: True to turn on, False to turn off
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Construct relay control URL
            action = "on" if turn_on else "off"
            url = f"{self.relay_base_url}/relay/{controller_id}/{port}/{action}"
            
            # Send control request
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url)
                response.raise_for_status()
                
            logger.info(f"Relay control successful: {url}")
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error controlling relay: {e}")
            return False
        except Exception as e:
            logger.error(f"Error controlling relay: {e}")
            return False
    
    def _control_relay_with_retry(self, controller_id: str, port: int, turn_on: bool, retry_count: int, max_retries: int, retry_delay: int) -> bool:
        """
        Control relay with retry logic
        
        Args:
            controller_id: ID of the relay controller
            port: Relay port number
            turn_on: True to turn on, False to turn off
            retry_count: Current retry attempt
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        for attempt in range(retry_count, max_retries):
            try:
                success = self._control_relay(controller_id, port, turn_on)
                if success:
                    return True
                    
                # If this is not the last attempt, wait before retrying
                if attempt < max_retries - 1:
                    logger.warning(f"Relay control attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    
            except Exception as e:
                logger.error(f"Relay control attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    
        return False
    
    def _update_task_status(self, db: Session, booking_id: int, room_id: int, status: str, executed_at: datetime):
        """Update power-off task status in database"""
        try:
            update_query = text("""
                UPDATE power_off_tasks 
                SET status = :status, executed_at = :executed_at, updated_at = NOW()
                WHERE booking_id = :booking_id AND room_id = :room_id
            """)
            
            db.execute(update_query, {
                "status": status,
                "executed_at": executed_at,
                "booking_id": booking_id,
                "room_id": room_id
            })
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            db.rollback()
    
    def _log_power_off_operation(self, db: Session, booking_id: int, room_id: int, result: str, details: str):
        """Log power-off operation to audit log"""
        try:
            insert_query = text("""
                INSERT INTO power_off_audit_log (booking_id, room_id, operation_type, result, details, created_at)
                VALUES (:booking_id, :room_id, 'automatic_power_off', :result, :details, NOW())
            """)
            
            db.execute(insert_query, {
                "booking_id": booking_id,
                "room_id": room_id,
                "result": result,
                "details": details
            })
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging power-off operation: {e}")
            db.rollback()
    
    def get_power_off_tasks(self, db: Session, booking_id: Optional[int] = None, room_id: Optional[int] = None) -> list:
        """
        Get power-off tasks with optional filtering
        
        Args:
            db: Database session
            booking_id: Optional booking ID filter
            room_id: Optional room ID filter
            
        Returns:
            list: List of power-off tasks
        """
        try:
            query = text("""
                SELECT id, booking_id, room_id, scheduled_time, executed_at, status, created_at, updated_at
                FROM power_off_tasks
                WHERE (:booking_id IS NULL OR booking_id = :booking_id)
                AND (:room_id IS NULL OR room_id = :room_id)
                ORDER BY created_at DESC
            """)
            
            result = db.execute(query, {
                "booking_id": booking_id,
                "room_id": room_id
            }).fetchall()
            
            tasks = []
            for row in result:
                tasks.append({
                    'id': row.id,
                    'booking_id': row.booking_id,
                    'room_id': row.room_id,
                    'scheduled_time': row.scheduled_time.isoformat() if row.scheduled_time else None,
                    'executed_at': row.executed_at.isoformat() if row.executed_at else None,
                    'status': row.status,
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                    'updated_at': row.updated_at.isoformat() if row.updated_at else None
                })
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting power-off tasks: {e}")
            return []
    
    def get_power_off_audit_log(self, db: Session, booking_id: Optional[int] = None, room_id: Optional[int] = None, limit: int = 100) -> list:
        """
        Get power-off audit log with optional filtering
        
        Args:
            db: Database session
            booking_id: Optional booking ID filter
            room_id: Optional room ID filter
            limit: Maximum number of records to return
            
        Returns:
            list: List of audit log entries
        """
        try:
            query = text("""
                SELECT id, booking_id, room_id, operation_type, result, details, created_at
                FROM power_off_audit_log
                WHERE (:booking_id IS NULL OR booking_id = :booking_id)
                AND (:room_id IS NULL OR room_id = :room_id)
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = db.execute(query, {
                "booking_id": booking_id,
                "room_id": room_id,
                "limit": limit
            }).fetchall()
            
            logs = []
            for row in result:
                logs.append({
                    'id': row.id,
                    'booking_id': row.booking_id,
                    'room_id': row.room_id,
                    'operation_type': row.operation_type,
                    'result': row.result,
                    'details': row.details,
                    'created_at': row.created_at.isoformat() if row.created_at else None
                })
            
            return logs
            
        except Exception as e:
            logger.error(f"Error getting power-off audit log: {e}")
            return []