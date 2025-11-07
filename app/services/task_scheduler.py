from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from sqlalchemy.orm import Session
import logging

from app.models.database import get_db
from app.services.power_off_service import PowerOffService

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        # Configure jobstores with SQLAlchemy for persistence
        jobstores = {
            'default': SQLAlchemyJobStore(url='mysql+pymysql://root:password@localhost/chess_booking')
        }
        
        # Configure executors
        executors = {
            'default': ThreadPoolExecutor(20),
        }
        
        # Configure job defaults
        job_defaults = {
            'coalesce': False,
            'max_instances': 3,
            'misfire_grace_time': 30
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )
        self.power_off_service = PowerOffService()
        
    def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            logger.info("Task scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start task scheduler: {e}")
            raise
    
    def shutdown(self):
        """Shutdown the scheduler"""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("Task scheduler shutdown successfully")
        except Exception as e:
            logger.error(f"Failed to shutdown task scheduler: {e}")
    
    def schedule_power_off(self, booking_id: int, room_id: int, power_off_time: datetime) -> str:
        """
        Schedule a power-off task for a booking
        
        Args:
            booking_id: ID of the booking
            room_id: ID of the room
            power_off_time: When to power off the room
            
        Returns:
            job_id: The scheduled job ID
        """
        job_id = f"power_off_{booking_id}_{room_id}"
        
        try:
            # Remove any existing job for this booking
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Removed existing power-off job: {job_id}")
            
            # Schedule new power-off job
            self.scheduler.add_job(
                func=self._execute_power_off,
                trigger=DateTrigger(run_date=power_off_time),
                args=[booking_id, room_id],
                id=job_id,
                name=f"Power off room {room_id} for booking {booking_id}",
                replace_existing=True
            )
            
            logger.info(f"Scheduled power-off job {job_id} for {power_off_time}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to schedule power-off job {job_id}: {e}")
            raise
    
    def cancel_power_off(self, booking_id: int, room_id: int) -> bool:
        """
        Cancel a scheduled power-off task
        
        Args:
            booking_id: ID of the booking
            room_id: ID of the room
            
        Returns:
            bool: True if job was cancelled, False if not found
        """
        job_id = f"power_off_{booking_id}_{room_id}"
        
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Cancelled power-off job: {job_id}")
                return True
            else:
                logger.warning(f"Power-off job not found: {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to cancel power-off job {job_id}: {e}")
            return False
    
    def get_scheduled_jobs(self) -> list:
        """Get all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'args': job.args
            })
        return jobs
    
    def _execute_power_off(self, booking_id: int, room_id: int):
        """
        Execute the power-off operation
        
        Args:
            booking_id: ID of the booking
            room_id: ID of the room
        """
        try:
            # Get database session
            db = next(get_db())
            
            # Execute power-off
            success = self.power_off_service.execute_power_off(db, booking_id, room_id)
            
            if success:
                logger.info(f"Successfully executed power-off for booking {booking_id}, room {room_id}")
            else:
                logger.error(f"Failed to execute power-off for booking {booking_id}, room {room_id}")
                
        except Exception as e:
            logger.error(f"Error executing power-off for booking {booking_id}, room {room_id}: {e}")
        finally:
            db.close()

# Global scheduler instance
task_scheduler = TaskScheduler()