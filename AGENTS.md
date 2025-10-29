# Agent Rules Standard (AGENTS.md)
# 微信小程序棋牌室预订系统 - 项目指南

## 项目概述

这是一个基于FastAPI和微信小程序的完整棋牌室预订解决方案，支持微信云托管一键部署。项目包含后端API服务和微信小程序前端，实现了店面管理、包间预订、用户管理、支付功能等核心业务。

## 构建和运行命令

### 后端服务
```bash
# 开发环境启动
cd wechat-miniprogram-backend
python run.py

# 生产环境启动
uvicorn app.main:app --host 0.0.0.0 --port 80

# 安装依赖
pip install -r requirements.txt
```

### 前端开发
```bash
# 使用微信开发者工具打开 wechat-miniprogram-frontend 目录
```

## 代码风格指南

### 项目特定规则
- **API响应格式**: 所有API响应必须遵循 `{code, message, data}` 格式
- **数据库模型**: 使用SQLAlchemy 2.0语法，所有模型必须包含 `is_deleted` 软删除字段
- **时间处理**: 使用 `app.utils.time_utils` 中的统一时间处理函数
- **异常处理**: 使用 `app.utils.exceptions.BusinessException` 处理业务异常
- **微信集成**: 微信登录和支付相关功能集中在 `app.services.wechat_service`

### 导入规范
- 使用绝对导入: `from app.models.database import User`
- 导入顺序: 标准库 → 第三方库 → 本地应用导入

### 数据库操作
- 所有查询必须过滤软删除: `User.is_deleted == False`
- 使用依赖注入获取数据库会话
- 表结构变更必须通过Alembic迁移

## 测试设置说明

项目当前未配置测试框架，建议添加pytest进行单元测试和集成测试。

## 项目特定信息

### 微信云托管集成
- 项目专为微信云托管环境优化，自动注入环境变量
- 使用微信云托管提供的数据库连接和身份验证
- 支持微信小程序的X-WX-*头部信息处理

### 自动初始化
- 应用启动时自动创建数据库表
- 自动初始化示例数据（1个店面和6个包间）
- 自动配置API路由和中间件

### 支付系统
- 集成微信支付API
- 支持订单状态自动流转
- 自动退款处理机制

### 文件上传
- 头像上传功能位于 `/api/v1/users/upload-avatar`
- 支持JPEG、PNG、GIF格式，最大10MB
- 上传文件存储在 `uploads` 目录

### 环境配置
- 开发环境使用 `.env` 文件
- 云托管环境使用 `.env.cloud.example` 配置模板
- 关键配置项：JWT_SECRET、WECHAT_APP_ID、WECHAT_APP_SECRET、数据库连接信息