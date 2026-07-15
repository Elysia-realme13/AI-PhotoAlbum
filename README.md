## 📝 最近更新

> **2026-07-13** — 阶段二初步完成

### 🚀 新增功能（阶段二：上传 & 分析）
- **批量照片上传** — 支持多文件上传，自动存储与去重
- **EXIF 元数据提取** — 自动解析拍摄时间、GPS 坐标、相机型号等信息
- **缩略图自动生成** — 上传后自动生成缩略图，提升浏览体验
- **照片 CRUD 完整实现** — 列表查询、分页、排序、删除等基础操作
- **前端上传交互** — 拖拽上传、进度展示、上传完成回调刷新
- **图片预览组件** — 照片网格/列表双视图切换、灯箱预览

### 🔧 工程改进
- **Docker 依赖锁定** — 修改 `Dockerfile` 中 pip/npm 依赖安装方式，固定版本号，避免依赖浮动导致构建不一致
- **前后端 Docker 构建优化** — 统一依赖安装策略，确保开发/生产环境一致性

> **2026-07-14** — 回收站功能

### 🗑️ 新增功能（回收站）
- **软删除恢复** — 照片删除后进入回收站，支持一键恢复
- **永久删除** — 支持单张/批量彻底删除照片及关联文件
- **自动清理** — 7 天过期自动清理，后台定时任务每小时检查
- **回收站页面** — 缩略图网格展示、剩余天数角标、清空回收站
- **错误提示优化** — 前端请求拦截器区分多种错误类型，提示更友好

---

# AI-PhotoAlbum — AI 智能相册

<div align="center">

**让每一张照片都成为值得珍藏的记忆**

基于 FastAPI + Vue 3 + LangGraph + PostgreSQL/pgvector 的 AI 智能相册应用

</div>

---

## 🎯 最终成果愿景

一个功能完整的 **AI 智能相册**，用户只需上传照片，系统自动完成：

```
拍照上传 → AI 自动分析 → 智能归类 → 随心检索 → 美好回忆
```

| 能力 | 说明 |
|------|------|
| 📷 **智能分析** | 自动提取 EXIF 元数据、人脸检测与聚类、场景分类、CLIP 图文嵌入 |
| 🗺️ **足迹地图** | 基于 GPS 自动生成旅行足迹，按省份/城市/景区浏览照片 |
| 👤 **人物相册** | 人脸自动聚类，一键查看某个人的所有照片 |
| 🏷️ **智能标签** | AI 自动识别照片内容并打标签（风景、美食、宠物、自拍…） |
| 🔍 **以文搜图** | 用自然语言搜索照片："我和女朋友在海边的自拍" |
| 🤖 **AI 助手** | 对话式交互，帮你找照片、写文案、回忆旅行 |
| 📊 **年度报告** | 自动生成年度出行统计，照片墙、足迹时间轴、出行里程 |
| 🎫 **票据识别** | 自动识别火车票/机票，提取行程信息（可选） |

---

## 📋 开发进度

### Phase 1 — 项目骨架 ✅ 已完成

- [x] Monorepo 目录结构搭建
- [x] Docker Compose 基础设施编排（PostgreSQL + pgvector + MinIO）
- [x] 后端 FastAPI 脚手架（配置/日志/异常/中间件/JWT 认证）
- [x] 数据库模型设计（12 张表）+ 自动建表
- [x] 用户注册/登录 API（JWT Token）
- [x] 前端 Vue 3 脚手架（路由/布局/状态管理/Element Plus/TailwindCSS）
- [x] 登录/注册页面 + 首页骨架 + 7 个功能页面占位

### Phase 2 — 照片核心 ✅ 已完成

- [x] 照片上传 API（批量上传 + MD5 去重，支持 JPG/PNG/HEIC/GIF/WebP）
- [x] EXIF 元数据提取（通过异步任务系统执行）
- [x] 照片列表/详情（分页 + 文件类型/时间范围/排序筛选）
- [x] 照片属性修改（PATCH）、批量获取（POST batch）
- [x] 软删除 + 恢复（回收站机制）
- [x] 媒体文件服务（原始图 + 缩略图，inline / attachment）
- [x] 时间轴 API（年/月/日分组 + 封面图）
- [x] 地图视图 API（GPS 坐标筛选）
- [x] AI 分析任务系统（Task 模型 + CRUD + 状态统计）
- [x] 照片重新分析 API（reanalyze，按类型触发 AI 任务）
- [ ] 前端照片浏览页（瀑布流 + Lightbox 灯箱）
- [ ] 前端上传组件（拖拽上传 + 进度条）

### Phase 3 — AI 能力集成 🚧 进行中

- [x] 任务基础设施（Task 模型、CRUD、5 种任务类型、上传自动创建）
- [ ] ONNX 模型管理（下载/加载/释放）
- [ ] InsightFace 人脸检测 + 512 维特征提取
- [ ] 人脸聚类（DBSCAN + pgvector HNSW 向量检索）
- [ ] EfficientNet 场景分类（人物/动物/风景/文档/通用 5 类）
- [ ] CLIP ViT-B-32 图文向量嵌入
- [ ] LLM 图片描述生成（description + narrative + quality/memory 评分）
- [ ] TaskManager 异步任务队列（APScheduler）
- [ ] AI 分析进度前端展示

### Phase 4 — 相册与人物 🚧 待开发

- [ ] 相册 CRUD API（手动创建/编辑/删除）
- [ ] 智能相册（按时间/地点/标签/人物条件自动聚合）
- [ ] 人物管理 API（人脸列表/详情/合并/重命名/隐藏）
- [ ] 照片标签系统（AI 自动标签 + 手动编辑）
- [ ] 前端相册浏览页（网格 + 详情）
- [ ] 前端人物浏览页（人物卡片 + 照片列表）

### Phase 5 — 搜索与 Agent 🚧 待开发

- [ ] 多条件搜索 API（时间范围/地点/标签/人物/文件名）
- [ ] CLIP 以文搜图（自然语言 → 向量相似度 → 照片）
- [ ] LangGraph Agent 系统（Supervisor 路由 + 多 Agent 协作）
- [ ] Agent 工具集（search_photos / get_detail / get_faces / get_locations）
- [ ] SSE 流式对话 API
- [ ] 前端 AI 对话页面（聊天气泡 + Markdown 渲染 + 照片卡片）

### Phase 6 — 足迹地图与收尾 🚧 待开发

- [ ] 反向地理编码（GPS → 省/市/区 + 地址）
- [ ] 足迹数据查询 API（时间轴/城市统计/景区统计）
- [ ] 前端足迹地图页面（Leaflet + 照片聚合标记）
- [ ] 首页 Dashboard（统计卡片 + 最近照片 + 热度图）
- [ ] 全局搜索页面
- [ ] Playwright E2E 测试
- [ ] 部署文档 + Docker 镜像构建

---

## 🏗️ 项目结构

```
AI-PhotoAlbum/
│
├── docker-compose.yml              # 基础设施编排（PG + MinIO）
├── README.md                       # 本文件
│
├── backend/                        # Python 后端 (FastAPI :8000)
│   ├── main.py                     # 应用入口 + 生命周期管理
│   ├── pyproject.toml              # 依赖管理 (uv)
│   ├── .env / .env.example         # 环境变量配置
│   ├── Dockerfile                  # 容器构建
│   │
│   └── app/
│       ├── config/
│       │   └── settings.py         # 全局配置（pydantic-settings）
│       │
│       ├── core/
│       │   ├── security.py         # JWT Token + 密码哈希
│       │   ├── logger.py           # 统一日志
│       │   └── exceptions.py       # 全局异常处理
│       │
│       ├── database/
│       │   ├── session.py          # SQLAlchemy 会话 + 引擎
│       │   └── storage.py          # 本地文件存储
│       │
│       ├── models/                 # ORM 模型（12 张表）
│       │   ├── user.py             # 用户表
│       │   ├── photo.py            # 照片 + EXIF 元数据
│       │   ├── face.py             # 人脸检测 + 身份聚类
│       │   ├── description.py      # AI 描述 + CLIP 向量 + 标签
│       │   ├── album.py            # 相册 + 关联表
│       │   └── agent.py            # Agent 会话 + 消息
│       │
│       ├── schemas/                # Pydantic 请求/响应模型
│       │   ├── user.py             # 注册/登录/用户信息
│       │   ├── photo.py            # 照片/元数据/AI描述
│       │   ├── album.py            # 相册
│       │   ├── face.py             # 人脸身份
│       │   └── agent.py            # 对话/消息
│       │
│       ├── crud/
│       │   ├── user.py             # 用户 CRUD + 认证逻辑
│       │   └── photo.py            # ✅ 照片 CRUD + 软删除/恢复/清理
│       │
│       ├── api/                    # REST API 路由
│       │   ├── deps.py             # 依赖注入（认证/DB会话）
│       │   ├── auth.py             # ✅ POST /auth/register, /auth/login, GET /auth/me
│       │   ├── system.py           # ✅ GET /api/health
│       │   ├── photo.py            # ✅ 照片 CRUD + 上传
│       │   ├── medias.py           # ✅ 媒体文件服务（上传/缩略图/下载）
│       │   ├── recycle_bin.py      # ✅ 回收站（列表/恢复/清空/永久删除）
│       │   ├── album.py            # 🚧 相册管理
│       │   ├── face.py             # 🚧 人脸管理
│       │   ├── search.py           # 🚧 智能搜索
│       │   ├── agent.py            # 🚧 Agent 对话
│       │   └── tasks.py            # 🚧 任务状态
│       │
│       ├── services/               # 业务服务层
│       │   ├── exif_service.py      # ✅ EXIF 元数据提取
│       │   ├── thumbnail.py         # ✅ 缩略图生成
│       │   ├── agent/              # 🚧 LangGraph Agent
│       │   └── ai_providers/       # 🚧 AI 模型封装
│       │       ├── face.py         # InsightFace
│       │       ├── ocr.py          # PaddleOCR
│       │       ├── classifier.py   # 场景分类
│       │       └── clip.py         # CLIP 嵌入
│       │
│       ├── tasks/                  # 🚧 异步任务
│       └── middleware/
│           └── __init__.py         # 请求日志中间件
│
├── frontend/                       # Vue 3 前端 (Vite :5173)
│   ├── index.html
│   ├── package.json                # Element Plus + Pinia + TailwindCSS
│   ├── vite.config.ts              # Vite 配置 + API 代理
│   ├── nginx.conf                  # 生产 Nginx 配置
│   ├── Dockerfile                  # 多阶段构建
│   │
│   └── src/
│       ├── main.ts                 # 应用入口
│       ├── App.vue                 # 根组件
│       ├── main.css                # TailwindCSS 入口
│       │
│       ├── router/
│       │   └── index.ts            # 路由配置 + 登录守卫
│       │
│       ├── stores/
│       │   ├── user.ts             # 用户状态（Pinia）
│       │   └── photo.ts            # ✅ 照片状态管理
│       │
│       ├── api/
│       │   ├── auth.ts             # ✅ 认证 API 封装
│       │   └── photo.ts            # ✅ 照片/上传/回收站 API 封装
│       │
│       ├── utils/
│       │   └── request.ts          # Axios + Token 拦截器
│       │
│       ├── types/
│       │   └── photo.ts            # 照片类型定义
│       │
│       ├── layouts/
│       │   └── MainLayout.vue      # 主布局（Header + Sidebar + 内容区）
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppHeader.vue   # 顶部导航栏
│       │   │   └── AppSidebar.vue  # 侧边菜单栏
│       │   └── photo/
│       │       ├── PhotoCard.vue   # ✅ 照片卡片
│       │       ├── PhotoGrid.vue   # ✅ 照片网格/列表视图
│       │       └── UploadDialog.vue # ✅ 上传对话框（拖拽+进度）
│       │
│       └── views/                  # 页面视图
│           ├── LoginPage.vue       # ✅ 登录/注册（Tab 切换）
│           ├── HomePage.vue        # ✅ 首页（统计卡片 + 最近照片）
│           ├── PhotosPage.vue      # ✅ 照片浏览 + 上传
│           ├── RecycleBinPage.vue  # ✅ 回收站（恢复/彻底删除/清空）
│           ├── AlbumPage.vue       # 🚧 相册管理
│           ├── FacePage.vue        # 🚧 人物相册
│           ├── MapPage.vue         # 🚧 足迹地图
│           ├── SearchPage.vue      # 🚧 智能搜索
│           ├── AgentChat.vue       # 🚧 AI 助手
│           ├── SettingsPage.vue    # 🚧 系统设置
│           └── NotFound.vue        # ✅ 404 页面
│
├── data/                           # 运行时数据（挂载卷）
│   ├── models/                     # AI 模型文件
│   │   ├── buffalo_l/              # InsightFace 人脸模型
│   │   ├── clip-ViT-B-32/         # CLIP 图文模型
│   │   └── photo-cls/              # 场景分类模型
│   ├── uploads/                    # 用户上传照片
│   ├── thumbnails/                 # 缩略图缓存
│   └── logs/                       # 应用日志
│
└── tests/                          # 测试目录
```

---

## 🛠️ 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **后端框架** | FastAPI + Uvicorn | 高性能异步 Web 框架 |
| **AI 编排** | LangChain + LangGraph | 多 Agent 协作对话系统 |
| **数据库** | PostgreSQL 18 + pgvector | 关系型 + 向量检索（HNSW） |
| **ORM** | SQLAlchemy 2.0 | 异步兼容 ORM |
| **认证** | JWT (python-jose) + bcrypt | Token 认证 + 密码哈希 |
| **前端框架** | Vue 3 (Composition API) + TypeScript | 渐进式前端框架 |
| **构建工具** | Vite 6 | 极速开发服务器 + 构建 |
| **UI 组件库** | Element Plus | 企业级 Vue 3 组件库 |
| **CSS 框架** | TailwindCSS 3 | 实用优先的 CSS |
| **状态管理** | Pinia | Vue 3 官方状态管理 |
| **HTTP 客户端** | Axios | 请求拦截 + Token 管理 |
| **AI 模型** | ONNX Runtime | 跨平台模型推理 |
| **人脸识别** | InsightFace (buffalo_l) | 512 维人脸特征 |
| **图像嵌入** | CLIP ViT-B-32 | 图文语义对齐 |
| **包管理** | uv (Python) / npm (Node.js) | 快速依赖管理 |
| **容器化** | Docker Compose | 一键部署 |

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### 1. 启动 PostgreSQL

```bash
cd AI-PhotoAlbum
docker compose up -d postgres
```
 
一键启动全部服务（PostgreSQL + pgvector + MinIO + 后端 + 前端）。
- 后端 API：`http://localhost:8000`
- 前端页面：`http://localhost:3000`
- API 文档：`http://localhost:8000/docs`
- MinIO 控制台：`http://localhost:9001`

> PostgreSQL 运行在 `localhost:5433`（避免与本地 PG 冲突）
 
### 2. 配置并启动后端
 
```bash
cd backend

# 复制配置文件
cp .env.example .env

# 安装依赖
uv sync

# 启动开发服务器
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端运行在 `http://localhost:8000`，API 文档在 `http://localhost:8000/docs`。

### 3. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端运行在 `http://localhost:5173`，自动代理 `/api` 到后端 `:8000`。

### 4. 验证

```bash
# 健康检查
curl http://localhost:8000/api/health
# → {"status":"ok","message":"AI-PhotoAlbum service is running"}

# 注册用户
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","email":"demo@test.com","password":"123456"}'

# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"123456"}'
```

### 完整部署（Docker Compose）

```bash
cd AI-PhotoAlbum
docker compose up -d
```

访问：
- 前端：`http://localhost:3000`
- 后端 API 文档：`http://localhost:8000/docs`
- MinIO 控制台：`http://localhost:9001`

---

## 📊 数据库模型

| 业务域 | 表名 | 说明 |
|--------|------|------|
| 用户 | `users` | 用户账户信息 |
| 照片 | `photos` | 照片主表（含软删除） |
| | `photo_metadata` | EXIF 元数据（GPS/相机参数） |
| | `image_descriptions` | AI 生成的描述/标签/评分 |
| | `image_vectors` | CLIP 512 维向量嵌入 |
| 人脸 | `faces` | 人脸检测结果 + 特征向量 |
| | `face_identities` | 人脸身份聚类 |
| 相册 | `albums` | 相册（手动/智能/条件） |
| | `album_photos` | 相册-照片关联 |
| 标签 | `photo_tags` | 标签字典 |
| | `photo_tag_relations` | 照片-标签关联 |
| Agent | `agent_sessions` | 对话会话 |
| | `agent_messages` | 对话消息记录 |

---

## 📝 开发约定

### 后端

```bash
cd backend

# 代码检查
uv run ruff check app/

# 代码格式化
uv run ruff format app/

# 运行测试
uv run pytest
```

### 前端

```bash
cd frontend

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [API 集成方案](./API集成方案.md) | Phase 3 API 层改造设计，基于 ai-part 服务层对照现状制定方案 |
| [API 测试步骤](./API测试步骤.md) | 23 项端点测试手册 + 一键回归脚本 + 响应格式说明 |
| [AI 模型变更应对方案](./AI模型变更应对方案.md) | Provider 切换、模型升级、兼容降级等 6 类场景应对策略 |

---

## 📄 许可证

本项目参考了以下开源项目的设计：
- [VisAgent](https://github.com/example/visagent) — YOLO 检测智能体平台
- [TrailSnap](https://github.com/LC044/TrailSnap) — AI 智能相册「行影集」
