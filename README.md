## 📝 最近更新

> **2026-07-22** — 人脸检测全链路修复 + 后端任务异常透明化

### 🔧 人脸检测修复
- **模型路径修正** — `face_detection.py` 加 `INSIGHTFACE_HOME` 指向 `data/insightface_home/`，匹配 Docker volume 映射
- **聚类 owner_id 修复** — `_handle_face_detect` 补传 `owner_id` 给 `update_face_clusters`，身份不再 `owner_id=NULL` 导致前端查不到
- **异常穿透** — 移除吞噬所有异常的 `except Exception`，模型下载/网络超时等真实错误穿透到任务系统，任务中心正确显示“失败”

### 📤 上传体验改进
- **进度条修复** — `store.uploadPhoto` 透传 `onProgress` 回调到 API 层，`UploadDialog` 实时更新进度

### 🧹 其他
- **侧边栏精简** — 搜索导航项（尚待开发）暂注释隐藏

> **2026-07-17** — AI Agent 全面升级 + 自动标签系统

### 🤖 AI Agent 智能化
- **LLM 驱动对话** — 接入 OpenAI 兼容大模型，自然语言理解用户意图
- **Agent 工具集** — 5 个内置工具：搜索照片、创建相册、添加到相册、列出相册、照片统计
- **自动工具调用** — Agent 自主决定调用哪些工具完成用户任务

### 🏷️ 自动标签
- **YOLO 目标检测** — 上传照片自动运行 YOLO11 检测，提取 80 类 COCO 物体标签
- **标签搜索** — AI 助手可基于标签搜索照片："帮我找有猫的照片"

> **2026-07-15** — 前后端 API 全面对齐 + 无障碍修复 + 阻塞性 bug 修复

### 🔗 API 路由对齐
- **Face API 路由重构** — `/api/faces/identities/*`，身份列表/照片/更新/合并/命名 5 端点
- **用户资料端点** — `PATCH /auth/me` 更新昵称/头像 + `POST /auth/change-password` 修改密码
- **照片 EXIF 元数据** — `GET /photos/{id}/metadata` 相机参数/GPS 查询
- **Face API 前后端参数对齐** — name/merge 路由补充 identities 前缀，merge 参数对齐后端 schema

### 🐛 阻塞性修复
- **Docker 构建** — Debian trixie `libgl1-mesa-glx` → `libgl1` 适配
- **Face 模型** — 新增 `face_name` / `face_aliases` 字段 + 启动自动迁移
- **UUID 安全解析** — photo.py 全部 10 处 UUID 转换加 try/except 400 防护

### ♿ 无障碍
- **12 个表单元素** — LoginPage/SettingsPage/SearchPage/ChatInput 全部添加 id 属性
- **Label 关联** — SearchPage 日期选择器 `<label for>` 正确关联

### 🤖 AI 服务层
- **YOLO 目标检测** — Ultralytics YOLO11，支持 80 类 COCO 物体识别
- **人脸增量聚类** — 512 维余弦相似度聚类，自动归并人脸身份
- **CLIP 文本检索** — jieba 分词 + pgvector 向量相似度搜索
- **LangGraph 检索代理** — 实体提取 → 人称识别 → CLIP 检索 → 结果合并流水线
- **对话式 Agent** — 会话管理 + 消息持久化 + 以图搜图

### 🔧 架构改进
- **API 重构** — medias / recycle_bin 路由合并至 photo.py，统一 BaseResponse 响应格式
- **Task 任务系统** — 5 种分析任务类型，上传自动创建，状态追踪
- **时间轴 & 地图 API** — 年/月/日分组 + GPS 坐标筛选
- **Token 查询参数认证** — `<img>` 标签友好，缩略图无需 JS 注入

> **2026-07-14** — 回收站功能

- 软删除恢复、永久删除、剩余天数展示

> **2026-07-13** — 阶段二初步完成

- 批量上传、EXIF 提取、缩略图生成、照片 CRUD、前端上传/预览组件

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
- [x] 前端照片浏览页（网格 + 详情 + Lightbox 灯箱）
- [x] 前端上传组件（拖拽上传 + 进度条）

### Phase 3 — AI 能力集成 ✅ 已完成

- [x] 任务基础设施（Task 模型、CRUD、5 种任务类型、上传自动创建）
- [x] YOLO 目标检测服务（80 类 COCO，画框标注）
- [x] 人脸增量聚类服务（余弦相似度，FaceIdentity 自动归并）
- [x] 交互式命名确认服务（pending 会话机制）
- [x] Face API 全部端点（身份列表/照片/更新/合并/命名绑定）
- [x] InsightFace 人脸检测 + 512 维特征提取
- [x] LLM 图片描述生成（description + narrative + quality/memory 评分）
- [x] TaskManager 异步任务队列（APScheduler + Worker 轮询）
- [x] 反向地理编码（Nominatim GPS → 省/市/区 + 地址）
- [x] Search API 语义检索（jieba + pgvector cosine 相似度）
- [x] Agent API 对话（会话 CRUD + 消息持久化 + 以图搜图）
- [ ] ONNX 模型管理（下载/加载/释放）
- [ ] EfficientNet 场景分类（人物/动物/风景/文档/通用 5 类）
- [ ] CLIP ViT-B-32 图文向量嵌入（当前为预留接口）
- [ ] AI 分析进度前端展示

### Phase 4 — 相册与人物 🚧 进行中

- [x] 相册 CRUD API（手动创建/编辑/删除）
- [x] 相册照片管理 API（添加/移除照片，分页查询）
- [x] 前端相册页面（列表视图 + 删除功能）
- [ ] 智能相册（按时间/地点/标签/人物条件自动聚合）
- [x] 人物管理 API（人脸列表/详情/合并/重命名/隐藏）
- [x] 照片标签系统（AI 自动标签 + 手动编辑）
- [x] 前端相册浏览页（网格 + 详情）
- [x] 前端人物浏览页（人物卡片 + 照片列表）

### Phase 5 — 搜索与 Agent 🚧 进行中

- [x] jieba 分词 + 词性标注（名词提取）
- [x] CLIP 文本检索服务（pgvector cosine 相似度查询）
- [x] LangGraph 混合检索代理（实体识别人称识别 CLIP 检索 结果合并）
- [x] 对话式检索 Agent（会话 CRUD + 消息持久化）
- [x] SSE 流式对话 API
- [x] Agent 工具集（search_photos / get_detail / get_faces / get_locations）
- [x] 前端 AI 对话页面（聊天气泡 + Markdown 渲染 + 照片卡片）

### Phase 6 — 足迹地图与收尾 🚧 进行中

- [ ] 足迹数据查询 API（时间轴/城市统计/景区统计）
- [x] 前端足迹地图页面（Leaflet + 照片聚合标记）
- [x] 首页 Dashboard（统计卡片 + 最近照片 + 热度图）
- [x] 全局搜索页面
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
│       │   ├── photo.py            # ✅ 照片 CRUD + 软删除/恢复/清理
│       │   └── album.py            # ✅ 相册 CRUD + 照片关联管理
│       │
│       ├── api/                    # REST API 路由
│       │   ├── deps.py             # 依赖注入（认证/DB会话）
│       │   ├── auth.py             # ✅ POST /auth/register, /auth/login, GET /auth/me
│       │   ├── system.py           # ✅ GET /api/health
      │       │   ├── photo.py            # ✅ 照片 CRUD + 上传 + 文件 + 回收站
      │       │   ├── tasks.py            # ✅ 异步任务查询 + 统计
      │       │   ├── album.py            # ✅ 相册管理 CRUD
      │       │   ├── face.py             # ✅ 人脸管理（身份列表/照片/更新/合并/命名）
      │       │   ├── search.py           # ✅ 智能搜索（语义/关键词/标签）
      │       │   └── agent.py            # ✅ Agent 对话（会话/消息/以图搜图）
│       │
      │       ├── services/               # 业务服务层
      │       │   ├── photo_service.py    # ✅ 照片上传编排
      │       │   ├── exif_service.py     # ✅ EXIF 元数据提取
      │       │   ├── thumbnail.py        # ✅ 缩略图生成
      │       │   ├── detection_service.py # ✅ YOLO 目标检测
      │       │   ├── face_cluster_service.py  # ✅ 人脸增量聚类
      │       │   ├── name_confirmation_service.py  # ✅ 命名确认
      │       │   ├── search_service.py   # ✅ CLIP 检索 + jieba 分词
      │       │   └── agent/              # ✅ LangGraph 检索代理 + 对话
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
│       │   ├── photo.ts            # ✅ 照片/上传/回收站 API 封装
│       │   ├── album.ts            # ✅ 相册管理 API 封装
│       │   ├── face.ts             # ✅ 人脸 API 封装
│       │   ├── agent.ts            # ✅ Agent 对话 API 封装
│       │   ├── search.ts           # ✅ 搜索 API 封装
│       │   └── map.ts              # ✅ 足迹地图 API 封装
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
│           ├── AlbumPage.vue       # ✅ 相册管理（列表 + 删除）
│           ├── FacePage.vue        # ✅ 人物相册
│           ├── MapPage.vue         # ✅ 足迹地图
│           ├── SearchPage.vue      # ✅ 智能搜索
│           ├── AgentChat.vue       # ✅ AI 助手
│           ├── SettingsPage.vue    # ✅ 系统设置
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

### 📦 AI 模型文件说明

人脸检测（InsightFace）、目标检测（YOLO）等 AI 模型在首次调用时**自动下载**到 `data/` 目录下。如需手动下载或恢复：

```bash
# InsightFace buffalo_l（人脸检测 + 512 维特征提取）
# 下载地址：https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
# 解压到：data/insightface_home/models/buffalo_l/
# 包含 5 个 ONNX 文件：det_10g.onnx, 1k3d68.onnx, 2d106det.onnx, genderage.onnx, w600k_r50.onnx

# YOLO 模型（目标检测）
# 首次调用 Ultralytics 时自动下载到 backend/.venv/Lib/site-packages/ultralytics/ 缓存目录
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
- **OpenAI 兼容 API Key**（DeepSeek / SiliconFlow / OpenAI 等）

### ⚠️ 启动前必须配置 API Key

```bash
# 1. 复制环境变量模板
cp backend/.env.example backend/.env

# 2. 编辑 backend/.env，填入你的 API Key
# 支持 OpenAI / DeepSeek / SiliconFlow 等兼容接口
OPENAI_API_KEY=your-api-key-here      # ← 改成你的真实 Key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# 3. 如果用 Docker Compose，同步到根目录
cp backend/.env .env
```

> 获取 Key：[OpenAI](https://platform.openai.com) | [DeepSeek](https://platform.deepseek.com) | [SiliconFlow](https://cloud.siliconflow.cn)

### 端口一览

| 端口 | 服务 | 说明 |
|:---:|------|------|
| `8000` | 后端 FastAPI | 开发模式直接运行，生产用 Docker |
| `5173` | 前端 Vite 开发服务器 | `npm run dev` |
| `5433` | PostgreSQL | 避免与本地 PG 冲突 |
| `9000` | MinIO S3 API | 对象存储（可选） |
| `9001` | MinIO 控制台 | Web 管理界面 |

### 方式一：开发模式（推荐日常使用）

```bash
# 1. 只启动数据库
docker compose up -d

# 2. 启动后端（热重载，改代码即时生效）
cd backend
uv sync                              # 仅首次
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 3. 另开终端，启动前端（热重载）
cd frontend
npm install                          # 仅首次
npm run dev
```

访问 `http://localhost:5173`

### 方式二：Docker Compose 全栈部署

```bash
cd AI-PhotoAlbum
docker compose --profile production up -d --build
```

| 服务 | 地址 |
|------|------|
| 前端 | `http://localhost:3000` |
| API 文档 | `http://localhost:8000/docs` |

### 验证

```bash
# 健康检查
curl http://localhost:8000/api/health
# → {"status":"ok","message":"AI-PhotoAlbum service is running"}

# 注册用户
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","email":"demo@test.com","password":"123456"}'

# 登录获取 Token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"123456"}'
```

---

## 📊 数据库模型

| 业务域 | 表名 | 说明 |
|--------|------|------|
| 用户 | `users` | 用户账户信息 |
| 照片 | `photos` | 照片主表（含软删除） |
| | `photo_metadata` | EXIF 元数据（GPS/相机参数） |
| | `image_descriptions` | AI 生成的描述/标签/评分 |
| | `image_vectors` | CLIP 512 维向量嵌入 |
| | `object_detections` | YOLO 目标检测结果 |
| 人脸 | `faces` | 人脸检测结果 + 特征向量 |
| | `face_identities` | 人脸身份聚类 |
| 相册 | `albums` | 相册（手动/智能/条件） |
| | `album_photos` | 相册-照片关联 |
| 标签 | `photo_tags` | 标签字典 |
| | `photo_tag_relations` | 照片-标签关联 |
| 任务 | `tasks` | AI 分析任务（5 种类型） |
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

## 📄 许可证

本项目参考了以下开源项目的设计：
- [VisAgent](https://github.com/example/visagent) — YOLO 检测智能体平台
- [TrailSnap](https://github.com/LC044/TrailSnap) — AI 智能相册「行影集」
