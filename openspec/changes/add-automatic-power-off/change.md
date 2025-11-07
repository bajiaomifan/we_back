# Add Automatic Power-Off Feature

**Status**: ✅ Completed  
**Date**: 2025-11-05  
**Type**: Feature Enhancement  

## Summary

Implemented automatic power-off functionality for chess room booking system. When users open doors for their bookings, the system now automatically schedules power-off tasks to turn off room power after the booking duration plus a 40-minute buffer period.

## Implementation Details

### Core Components

1. **Task Scheduler Service** (`app/services/task_scheduler.py`)
   - Uses APScheduler with SQLAlchemy job store for persistence
   - Manages background power-off tasks
   - Handles task scheduling, cancellation, and execution

2. **Power-Off Service** (`app/services/power_off_service.py`)
   - Executes relay control for power operations
   - Implements retry logic with exponential backoff
   - Provides comprehensive audit logging

3. **Database Schema** (`alembic/versions/001_add_power_off_tables.py`)
   - `power_off_tasks` table for task management
   - `power_off_audit_log` table for operation tracking
   - Proper indexing for performance

4. **API Endpoints** (`app/routers/power_off.py`)
   - GET `/api/v1/power-off/tasks` - List power-off tasks
   - DELETE `/api/v1/power-off/tasks/{booking_id}/{room_id}` - Cancel task
   - GET `/api/v1/power-off/audit-log` - View audit logs
   - GET `/api/v1/power-off/scheduler/status` - Scheduler status

5. **Integration** (`app/routers/rooms.py`)
   - Enhanced door open endpoint with automatic task scheduling
   - Calculates power-off time as booking end + 40 minutes
   - Maintains existing door functionality

### Key Features

- **Automatic Scheduling**: Power-off scheduled when door is opened
- **40-Minute Buffer**: Users get 40 minutes after booking end to leave
- **Retry Logic**: Up to 3 retries with 5-second delays for failed operations
- **Audit Trail**: Complete logging of all power-off operations
- **Task Management**: APIs to view, cancel, and monitor tasks
- **Error Handling**: Comprehensive error handling and recovery

### Security & Reliability

- **Authentication**: All power-off APIs require user authentication
- **Validation**: Validates booking permissions before scheduling
- **Persistence**: Tasks survive service restarts via database storage
- **Monitoring**: Built-in status monitoring and logging
- **Graceful Degradation**: Door operations continue even if scheduling fails

## Files Modified

### New Files
- `app/services/task_scheduler.py` - Background task scheduling
- `app/services/power_off_service.py` - Power-off execution service
- `app/routers/power_off.py` - Power-off management APIs
- `alembic/versions/001_add_power_off_tables.py` - Database migration
- `test_power_off_automation.py` - Comprehensive test suite

### Modified Files
- `app/main.py` - Added scheduler startup/shutdown
- `app/routers/rooms.py` - Integrated automatic scheduling
- `app/models/schemas.py` - Added power-off data models
- `requirements.txt` - Added APScheduler dependency

## Configuration

### Environment Variables
- Database connection configured via existing settings
- Relay controller URL configurable in `PowerOffService`

### Database Migration
```bash
alembic upgrade head
```

## Usage Example

1. User books room 14:00-18:00
2. User opens door at 13:40
3. System schedules power-off for 18:40 (18:00 + 40min buffer)
4. At 18:40, system automatically turns off room power
5. Operation logged to audit trail

## Testing

Comprehensive test suite covering:
- Task scheduling and cancellation
- Power-off execution with retry logic
- Error scenarios and recovery
- Integration with door operations
- Audit logging verification

Run tests:
```bash
python test_power_off_automation.py
```

## Monitoring

### API Endpoints
- View scheduled tasks: `GET /api/v1/power-off/tasks`
- Check scheduler status: `GET /api/v1/power-off/scheduler/status`
- View audit logs: `GET /api/v1/power-off/audit-log`

### Logs
- Task scheduling: `Task scheduled: power_off_{booking_id}_{room_id}`
- Execution results: `Successfully powered off room {room_id}`
- Errors: Detailed error logging with context

## Future Enhancements

- User-configurable buffer times
- Power-off notifications to users
- Different buffer times per room type
- Dashboard for monitoring all power-off operations

## Impact

This enhancement improves energy efficiency and safety by ensuring rooms are automatically powered off after use, while providing users adequate time to vacate the premises. The implementation maintains full backward compatibility and adds comprehensive monitoring capabilities.