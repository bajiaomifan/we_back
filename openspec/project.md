# Project Context

## Purpose
微信小程序棋牌室预订系统后端服务，为微信小程序提供完整的棋牌室预订、用户管理、支付和评价功能。系统支持店面管理、包间预订、微信支付集成、用户评价等核心业务功能，专为棋牌室经营场景设计。

## Tech Stack
- **后端框架**: FastAPI 0.104.1 (Python 3.13)
- **数据库**: MySQL with SQLAlchemy 2.0.23 ORM
- **身份验证**: JWT (python-jose[cryptography] 3.3.0)
- **密码加密**: Passlib[bcrypt] 1.7.4
- **数据验证**: Pydantic 2.5.0 + Pydantic Settings 2.1.0
- **HTTP客户端**: httpx 0.25.2 (异步请求)
- **文件处理**: Pillow 10.1.0, aiofiles 23.2.1
- **数据库迁移**: Alembic 1.13.1
- **部署环境**: 微信云托管 + Docker
- **API文档**: FastAPI自动生成Swagger/OpenAPI

## Project Conventions

### Code Style
- **Python代码**: 遵循PEP 8规范，使用4空格缩进
- **命名规范**: 
  - 类名使用PascalCase (如 `WechatService`, `UserResponse`)
  - 函数和变量使用snake_case (如 `get_openid_by_code`, `user_id`)
  - 常量使用UPPER_CASE (如 `JWT_SECRET`, `DB_HOST`)
- **类型注解**: 所有函数参数和返回值必须使用类型注解
- **文档字符串**: 使用中文编写详细的docstring，包含参数说明和返回值
- **错误处理**: 统一使用HTTPException，返回标准化的错误响应格式

### Architecture Patterns
- **分层架构**: 
  - `routers/` - API路由层，处理HTTP请求
  - `services/` - 业务逻辑层，包含核心业务处理
  - `models/` - 数据模型层，数据库表结构和Pydantic模型
  - `middleware/` - 中间件层，CSRF保护、身份验证
  - `utils/` - 工具函数层，通用工具类
- **依赖注入**: 使用FastAPI的Depends系统进行依赖管理
- **配置管理**: 使用Pydantic Settings统一管理环境变量配置
- **数据库模式**: 使用SQLAlchemy 2.0的异步模式，支持连接池

### Testing Strategy
- **测试框架**: pytest (需添加到requirements.txt)
- **测试覆盖**: 
  - 单元测试覆盖services层核心业务逻辑
  - 集成测试覆盖API端点
  - 数据库测试使用内存SQLite或测试数据库
- **测试环境**: 使用独立的测试数据库配置
- **Mock策略**: 对外部API调用(如微信API)使用mock

### Git Workflow
- **分支策略**: 
  - `main` - 生产环境分支
  - `develop` - 开发环境分支
  - `feature/*` - 功能开发分支
  - `hotfix/*` - 紧急修复分支
- **提交规范**: 使用中文提交信息，格式为 `类型: 简短描述`
  - `feat: 添加微信支付功能`
  - `fix: 修复预订时间验证问题`
  - `docs: 更新API文档`
  - `refactor: 重构用户服务层`

## Domain Context

### 业务领域
- **棋牌室经营**: 包间按时段预订，支持不同规格和价格的棋牌室
- **微信生态**: 基于微信小程序的用户体系，支持微信登录和微信支付
- **预订管理**: 复杂的时间段冲突检测，支持72小时可用性查询
- **评价体系**: 用户可对预订体验进行评价，支持图片上传和商家回复

### 核心业务概念
- **店面(Store)**: 棋牌室经营场所，包含地址、营业时间、设施等信息
- **包间(Room)**: 具体的棋牌室包间，有容量、价格、图片等属性
- **预订(Booking)**: 用户预订包间的记录，包含时间段、联系人、支付状态
- **评价(Review)**: 用户完成预订后可进行的评价，包含评分和内容
- **支付(Payment)**: 微信支付集成，支持预订费用的在线支付

### 数据模型关系
- User 1:N Booking (用户可以有多个预订)
- Room 1:N Booking (包间可以有多个预订)
- Booking 1:1 Payment (每个预订对应一个支付订单)
- Booking 1:1 Review (每个完成预订可以有一个评价)
- Store 1:N Room (每个店面有多个包间)

## Important Constraints

### 技术约束
- **微信云托管**: 必须在微信云托管环境中运行，依赖特定的环境变量
- **数据库**: 必须使用MySQL，不支持其他数据库
- **异步编程**: 所有数据库操作和外部API调用必须使用async/await
- **文件上传**: 限制文件大小10MB，仅支持图片格式(jpeg/png/gif)
- **API版本**: 所有API路径使用 `/api/v1` 前缀

### 业务约束
- **预订规则**: 
  - 只能预订未来时间，不能预订过去时间
  - 预订时间段不能重叠
  - 支持最长72小时的可用性查询
- **支付要求**: 
  - 必须使用微信支付
  - 金额单位为分，必须为整数
  - 订单号必须唯一且符合格式要求
- **用户认证**: 
  - 必须通过微信登录获取openid
  - JWT token有效期为2小时，refresh token为7天

### 安全约束
- **CSRF保护**: 除特定豁免路径外，所有API都需要CSRF验证
- **数据验证**: 所有用户输入必须通过Pydantic模型验证
- **敏感信息**: 微信AppSecret、数据库密码等必须通过环境变量配置
- **HTML转义**: 用户生成的内容必须进行HTML转义防止XSS

## External Dependencies

### 微信服务
- **微信登录API**: `https://api.weixin.qq.com/sns/jscode2session` - 获取用户openid
- **微信用户信息API**: `https://api.weixin.qq.com/sns/userinfo` - 获取用户详细信息
- **微信支付API**: 统一下单接口，用于创建支付订单
- **微信云托管**: 提供运行环境和自动注入的环境变量

### 数据库服务
- **MySQL数据库**: 存储所有业务数据，通过云托管环境变量配置连接
- **数据库表**: users, stores, rooms, bookings, payments, reviews, audit_logs等

### 文件存储
- **本地文件系统**: 上传的图片文件存储在本地uploads目录
- **静态文件服务**: 通过FastAPI StaticFiles提供文件访问

### 监控和日志
- **微信云托管日志**: 应用日志输出到云托管日志系统
- **健康检查**: `/health` 端点用于服务状态监控
- **API文档**: `/docs` 和 `/redoc` 提供交互式API文档
