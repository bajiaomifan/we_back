## Context
当前开门系统缺乏自动关电功能，用户可能忘记关闭电源，造成能源浪费和安全风险。需要实现基于预订时长的自动关电机制，确保在用户预订时长结束后自动关闭房间电源。

## Goals / Non-Goals
- Goals: 
  - 实现基于预订时长的自动关电
  - 提供可靠的后台任务调度
  - 确保关电操作的审计跟踪
  - 支持任务管理和状态查询
- Non-Goals:
  - 实现复杂的任务依赖关系
  - 支持动态调整关电时间
  - 实现分布式任务队列

## Decisions
- Decision: 使用内存任务调度器（APScheduler）而非分布式队列
  - Rationale: 简单部署，适合单实例微信云托管环境
  - Alternatives considered: Celery + Redis, RQ
- Decision: 关电时间 = 预订结束时间 + 40分钟缓冲
  - Rationale: 给用户40分钟的离场缓冲时间
  - Alternatives considered: 预订结束时间立即关电，用户自定义缓冲时间
- Decision: 使用数据库存储任务状态
  - Rationale: 持久化任务状态，支持服务重启后恢复
  - Alternatives considered: 内存存储，Redis存储

## Risks / Trade-offs
- [Risk] 服务重启可能导致任务丢失 → Mitigation: 数据库持久化任务状态
- [Risk] 外部设备故障导致关电失败 → Mitigation: 重试机制和错误日志
- [Risk] 时间计算错误 → Mitigation: 充分的测试和验证逻辑
- [Trade-off] 简单性 vs 功能性 → 选择简单可靠的实现

## Migration Plan
1. 添加PowerOffTask数据库模型
2. 实现TaskScheduler后台服务
3. 修改door open endpoint添加任务调度
4. 实现power-off执行逻辑
5. 添加任务管理API端点
6. 部署和测试
7. 回滚计划：如出现问题可禁用自动关电功能

## Open Questions
- 是否需要支持用户手动延长使用时间？
- 关电失败时是否需要通知用户？
- 是否需要支持不同房间的不同缓冲时间设置？