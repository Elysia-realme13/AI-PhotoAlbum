# Agent 指南 — AI-PhotoAlbum

## 项目概述

AI-PhotoAlbum 是一个 AI 智能相册应用，Monorepo 结构，包含 Python 后端（FastAPI）和 Vue 3 前端。

## 技术栈

- **后端**: FastAPI + SQLAlchemy + PostgreSQL/pgvector + LangChain/LangGraph
- **前端**: Vue 3 + TypeScript + Vite + Element Plus + TailwindCSS + Pinia
- **AI**: InsightFace + CLIP + EfficientNet (ONNX) + OpenAI 兼容 LLM
- **包管理**: uv (Python) / npm (Node.js)
- **部署**: Docker Compose

## 项目结构

```
AI-PhotoAlbum/
├── backend/          # Python 后端 (FastAPI :8000)
│   ├── main.py       # 应用入口
│   └── app/
│       ├── api/      # REST 路由层
│       ├── config/   # 全局配置
│       ├── core/     # 安全/JWT/日志/异常
│       ├── database/ # DB会话 + 文件存储
│       ├── models/   # SQLAlchemy ORM (12张表)
│       ├── schemas/  # Pydantic 请求/响应模型
│       ├── crud/     # 数据库 CRUD 操作
│       ├── services/ # 业务服务 + AI提供者 + Agent
│       └── tasks/    # 异步任务定义
├── frontend/         # Vue 3 前端 (Vite :5173)
│   └── src/
│       ├── views/    # 页面视图 (9个)
│       ├── components/ # 通用组件
│       ├── router/   # 路由 + 守卫
│       ├── stores/   # Pinia 状态
│       ├── api/      # Axios API 封装
│       └── utils/    # 工具函数
├── data/             # 运行时数据（模型/照片/日志）
└── docker-compose.yml
```

## 开发命令

### 后端

```bash
cd backend

# 安装依赖
uv sync

# 启动服务（需要先启动 PostgreSQL）
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 代码检查
uv run ruff check app/

# 代码格式化
uv run ruff format app/

# 运行测试
uv run pytest

# 添加依赖
uv add <package>
uv add --dev <package>
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 开发服务器
npm run dev

# 构建
npm run build
```

### 基础设施

```bash
# 启动 PostgreSQL (端口 5433)
docker compose up -d postgres

# 停止
docker compose down
```

## 数据库

- PostgreSQL 18 + pgvector，端口 5433
- 数据库名: `photo_album`，用户/密码: `album/album`
- 12 张表，启动时自动创建
- pgvector 扩展自动启用

## 认证

- JWT Token 认证
- `/api/auth/register` — 注册
- `/api/auth/login` — 登录
- `/api/auth/me` — 获取当前用户（需 Bearer Token）

## 约定式提交

1. 采用 Git "约定式提交"，使用中文描述
2. 格式：`feat(module): 简短描述` 或 `fix(module): 简短描述`
3. 分类提交，不要一次性提交所有文件

示例：
```
feat(photo): 新增照片上传API和EXIF元数据提取

- 实现单张/批量照片上传
- 使用 piexif 提取 GPS、相机型号等 EXIF 信息
- 添加缩略图生成服务
```
