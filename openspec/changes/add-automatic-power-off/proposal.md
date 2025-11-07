## Why
当前开门操作后没有自动关电功能，用户可能忘记关闭电源，造成能源浪费和安全风险。需要添加定时关电功能，在用户预订时长结束后自动关闭房间电源。

## What Changes
- 添加后台任务调度系统
- 实现基于预订时长的自动关电逻辑
- 记录自动关电操作到审计日志
- 添加关电任务状态跟踪
- 提供关电任务管理接口

## Impact
- Affected specs: door-access, scheduling, bookings
- Affected code: app/routers/rooms.py, app/services/booking_service.py, 新增调度器模块
- 新增依赖: 后台任务调度库（如APScheduler或Celery）
- **BREAKING**: 开门操作将触发自动关电任务，改变现有电源管理行为