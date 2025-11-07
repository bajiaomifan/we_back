## Why
当前开门操作缺乏安全控制，任何人都可以调用开门API，无法追踪开门行为，存在严重的安全隐患。需要添加预订关联检查，确保只有当前有效预订的用户才能开门。

## What Changes
- 添加用户身份验证到开门API
- 实现预订状态检查逻辑
- 添加1小时提前开门时间限制
- 记录开门操作审计日志
- 返回详细的错误信息

## Impact
- Affected specs: door-access, bookings
- Affected code: app/routers/rooms.py, app/services/booking_service.py, app/middleware/auth.py
- **BREAKING**: 开门API现在需要身份验证，无有效预订的用户将无法开门