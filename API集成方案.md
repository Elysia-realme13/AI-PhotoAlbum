# API 集成方案 — AI-PhotoAlbum Phase 3 改造

> 基于 `AI-PhotoAlbum-ai-part/backend/app/services/` 已完成的服务层，
> 对照 `项目（api）/backend/app/api/` 现状，制定 API 层改造方案。

---

## 1. 现状分析

### 1.1 服务层（ai-part）— 全部就绪

```
services/
├── task_manager.py          # 内存任务队列，支持进度追踪 + SSE
├── photo_analysis.py        # AI 分析编排器：主管→专家→CLIP→LLM→DB
├── agent/chat_agent.py      # 对话 Agent：会话管理 + SSE 流式 + 工具调用
├── agent/search_supervisor.py  # 自然语言搜索意图解析
├── agent/search_filter.py      # 元数据过滤（时间/EXIF/标签）
├── agent/search_retriever.py   # CLIP 语义检索 + 人脸聚类 + 人脸相似度
└── training_manager.py      # YOLO 训练生命周期（创建/启动/暂停/恢复）
```

### 1.2 API 层（项目（api））— 部分实现

| 路由 | 文件 | 状态 |
|---|---|---|
| `/api/auth` | auth.py | ✅ 已实现（注册/登录/获取用户） |
| `/api/photos` | photo.py | ⚠️ 已写 CRUD，未对接 AI 分析 |
| `/api/tasks` | tasks.py | ⚠️ 已写 DB 查询，未对接 TaskManager |
| `/api/search` | search.py | 🔴 空壳 |
| `/api/agent` | agent.py | 🔴 空壳 |
| `/api/faces` | face.py | 🔴 空壳 |
| `/api/albums` | album.py | 🔴 空壳 |
| `/api/train` | — | ❌ 不存在 |
| `/api` | system.py | ✅ 已实现（健康检查） |

---

## 2. 核心决策

### 2.1 Task 系统：DB + 内存双写

| | DB Task 模型 | 内存 TaskManager |
|---|---|---|
| 用途 | 持久化历史记录、列表查询 | 实时进度追踪 |
| 生命周期 | 永久保存 | 服务重启丢失 |
| 写入时机 | 上传/重分析时创建 | 同上，同步创建 |
| 读取优先级 | GET /api/tasks 列表 | GET /api/tasks/{id} 详情 |

**流程**：
```
上传照片 → DB 创建 Task 记录 → task_manager.create_task() →
run_in_thread(analyze_photo) → 进度更新写入 task_manager →
查询时：先查 task_manager（实时），未命中再查 DB（历史）
```

### 2.2 响应格式：BaseResponse

沿用 `项目（api）` 已有的 `BaseResponse`，所有新接口统一使用。

---

## 3. 全部端点设计

### 3.1 Photo `/api/photos` — 改造 2 个端点

已有 12 个端点基础可用，需要改动的是上传和重分析：

**POST `/api/photos/upload`（改造）**

上传后链路变化：
```
之前: 保存文件 → 创建 Photo → 创建 DB Task（pending）→ 返回
现在: 保存文件 → 创建 Photo → DB Task + task_manager → analyze_photo_async() → 返回 task_id
```

关键代码变更位置：`app/services/photo_service.py` 的 `upload_single_photo()` 末尾。

```python
# 旧：手动创建 DB Task 记录
# tasks = create_tasks_batch(db, owner_id=owner_id, photo_id=photo.id, task_types=task_types)

# 新：对接 ai-part 分析管道
from app.services import analyze_photo_async
task_id = analyze_photo_async(
    photo_id=str(photo.id),
    image_path=file_path,
    db_session=db,
    user_id=str(owner_id),
)
# 同时写 DB Task 做持久化
from app.crud.task import create_task as create_db_task
from app.models.task import TaskType
create_db_task(db, owner_id=owner_id, task_type=TaskType.photo_analysis, photo_id=photo.id)
```

**POST `/api/photos/{id}/reanalyze`（改造）**

同样改为调用 `analyze_photo_async()`。

---

### 3.2 Tasks `/api/tasks` — 改造 3 个端点

**核心变化**：查询时优先读内存 TaskManager，DB 做后备。

| 端点 | 改动 |
|---|---|
| `GET /api/tasks` | 列表从 DB 查（需要持久化分页），每条附带 task_manager 实时状态 |
| `GET /api/tasks/{id}` | 优先 task_manager.get_task()，未命中查 DB |
| `GET /api/tasks/stats` | DB 统计 |
| `POST /api/tasks/{id}/retry` | 重新调用 analyze_photo_async |
| `DELETE /api/tasks/{id}` | task_manager.cancel_task() + DB 更新状态 |

---

### 3.3 Search `/api/search` — 全新实现 4 个端点

#### POST `/api/search`
统一搜索入口。

```
Request Body:
{
  "query": "去年10月在草丛边依偎的小猫",   // 自然语言或关键词
  "date_from": "2025-01-01",              // 可选
  "date_to": "2025-12-31",                // 可选
  "tags": ["cat"],                        // 可选
  "face_id": "uuid",                      // 可选
  "camera": "iPhone",                     // 可选
  "quality_min": 0.5,                     // 可选
  "top_k": 50
}

处理流程:
  1. SearchSupervisor.parse_query(query)
     → {time_range, subjects, scene, actions, search_text}
  2. SearchFilter 元数据过滤
     → 候选 photo_id 列表
  3. SearchRetriever.search_all(db, user_id, search_text, top_k)
     → CLIP 向量余弦相似度排序
  4. 返回结果（附 photo 缩略信息）

Response:
{
  "code": 200, "msg": "操作成功",
  "data": {
    "total": 23,
    "items": [
      {
        "photo_id": "uuid",
        "score": 0.87,
        "rank": 1,
        "filename": "...",
        "photo_time": "...",
        "thumbnail_url": "..."
      }
    ],
    "parsed_query": {
      "time_range": {"start": "2025-10-01", "end": "2025-10-31"},
      "subjects": ["cat"],
      "scene": "grass",
      "actions": ["snuggling"],
      "search_text": "grass cat snuggling"
    },
    "elapsed_ms": 234
  }
}
```

#### POST `/api/search/similar`
以图搜图。

```
Request: multipart/form-data { file }  或  { photo_id: "uuid" }
处理:   CLIP 提取查询图向量 → pgvector HNSW 检索 image_vectors 表
返回:   [{photo_id, score, rank, ...}]
```

#### POST `/api/search/faces`
人脸相似度搜索。

```
Request: { face_id: 123 }  或  { photo_id: "uuid" }（自动检测该图最大人脸）
处理:   SimilarFaceRetriever.find_similar_faces()
返回:   [{face_id, photo_id, score, ...}]
```

#### POST `/api/search/parse`
查询解析（调试 / 前端关键词高亮预览）。

```
Request:  { query: "去年夏天的海边" }
Response: { time_range, subjects, scene, actions, search_text }
```

---

### 3.4 Agent `/api/agent` — 全新实现 6 个端点

ChatAgent 服务已实现完整的会话管理 + SSE 流式 + 4 个工具函数。

| 端点 | 对应服务方法 |
|---|---|
| `POST /api/agent/sessions` | `chat_agent.create_session(db, user_id, title)` |
| `GET /api/agent/sessions` | `chat_agent.list_sessions(db, user_id, limit, offset)` |
| `GET /api/agent/sessions/{id}` | `chat_agent.get_session(db, id)` + `get_messages(db, id)` |
| `DELETE /api/agent/sessions/{id}` | `chat_agent.delete_session(db, id)` |
| `POST /api/agent/chat` | `chat_agent.chat_stream(db, session_id, message)` — **SSE** |

#### POST `/api/agent/chat` SSE 流式响应

```
Request:  { session_id?: "uuid", message: "帮我找去年在海边的照片" }
Response: text/event-stream

事件类型:
  data: {"type":"text","content":"好的"}       // 逐 token
  data: {"type":"text","content":"，我来"}      //
  data: {"type":"info","content":"正在查询..."} // 工具调用中
  data: {"type":"text","content":"找到了3张"}   //
  data: {"type":"done"}                        // 完成

Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

ChatAgent 的 4 个 tool functions（`search_photos`, `get_photo_detail`, `get_photo_faces`, `get_user_albums`）需要在 API 层注入 user_id 上下文，使 `search_photos` 能真正执行搜索（当前实现只做 parse，缺少 user_id）。

---

### 3.5 Face `/api/faces` — 全新实现 8 个端点

| 端点 | 说明 |
|---|---|
| `GET /api/faces/identities` | 人物列表（分页，按 face_count 排序） |
| `GET /api/faces/identities/{id}` | 人物详情 + 代表性人脸照片 |
| `PUT /api/faces/identities/{id}` | 修改名称 / 隐藏 |
| `DELETE /api/faces/identities/{id}` | 删除人物（解绑人脸，不删照片） |
| `POST /api/faces/merge` | 合并人物 `{source_ids, target_id}` |
| `POST /api/faces/cluster` | 手动触发 `FaceClusterer.cluster_faces(db, user_id)` |
| `GET /api/faces/identities/{id}/photos` | 该人物的所有照片（分页） |
| `POST /api/faces/search` | 人脸相似度搜索（同 search/faces，快捷入口） |

---

### 3.6 Training `/api/train` — 全新模块，需注册路由

| 端点 | 对应服务方法 |
|---|---|
| `POST /api/train` | `training_manager.create_run(user_id, zip_path, name, config)` → 返回 run_id |
| `POST /api/train/{run_id}/start` | `training_manager.start_training(run_id)` → 返回 task_id |
| `POST /api/train/{run_id}/pause` | `training_manager.pause_training(run_id)` |
| `POST /api/train/{run_id}/resume` | `training_manager.resume_training(run_id)` → 返回新 task_id |
| `GET /api/train` | `training_manager.list_runs(user_id, limit, offset)` |
| `GET /api/train/{run_id}` | `training_manager.get_run(run_id)` |
| `DELETE /api/train/{run_id}` | `training_manager.delete_run(run_id)` |

需新增文件：`app/api/train.py` + `app/schemas/train.py`，并在 `main.py` 注册路由。

---

### 3.7 Album `/api/albums` — 标准 CRUD

无 AI 依赖，标准 REST：

| 端点 | 说明 |
|---|---|
| `POST /api/albums` | 创建相册 |
| `GET /api/albums` | 列表 |
| `GET /api/albums/{id}` | 详情 + photo_count |
| `PUT /api/albums/{id}` | 更新 |
| `DELETE /api/albums/{id}` | 删除 |
| `POST /api/albums/{id}/photos` | 添加照片 |
| `DELETE /api/albums/{id}/photos` | 移除照片 |
| `GET /api/albums/{id}/photos` | 相册照片列表 |
| `POST /api/albums/smart` | 创建智能相册 |

---

## 4. 需要改动的文件清单

### 4.1 改造现有文件

| 文件 | 改动内容 |
|---|---|
| `app/api/photo.py` | 上传/重分析 → 对接 `analyze_photo_async()`；去掉手动创建 Task |
| `app/api/tasks.py` | 查询优先读 `task_manager`，回退 DB；retry/cancel 双写 |
| `app/services/photo_service.py` | `upload_single_photo()` 末尾调用分析管道 |

### 4.2 全新实现

| 文件 | 内容 | 预估行数 |
|---|---|---|
| `app/api/search.py` | 4 个搜索端点 | ~150 行 |
| `app/api/agent.py` | 6 个对话端点（含 SSE） | ~200 行 |
| `app/api/face.py` | 8 个人脸端点 | ~180 行 |
| `app/api/train.py` | 7 个训练端点 | ~150 行 |
| `app/api/album.py` | 9 个相册端点 | ~200 行 |
| `app/schemas/search.py` | 搜索请求/响应 | ~60 行 |
| `app/schemas/train.py` | 训练请求/响应 | ~50 行 |

### 4.3 配置变更

| 文件 | 改动 |
|---|---|
| `main.py` | 新增 `from app.api.train import router as train_router`，注册路由 |
| `app/models/__init__.py` | 已注册 Task（✅ 完成） |
| `pyproject.toml` | 追加依赖：`insightface`, `sentence-transformers`, `scikit-learn`, `ultralytics`（见 ai-part README） |

---

## 5. 测试策略

### 5.1 单元测试

```bash
# Mock 服务层，测试 API 路由层逻辑
cd backend
PYTHONPATH=. python -m pytest tests/test_search_api.py -v
PYTHONPATH=. python -m pytest tests/test_agent_api.py -v
```

### 5.2 集成测试

```bash
# 启动完整服务（PostgreSQL + AI 模型）
docker compose up -d postgres
cd backend && uv run uvicorn main:app --reload

# 端到端测试
PYTHONPATH=. python -m pytest tests/test_integration.py -v
```

### 5.3 手动测试（Swagger UI）

访问 `http://localhost:8000/docs`，按以下顺序验证：

1. `POST /api/auth/register` → 注册 → 获取 token → Authorize
2. `POST /api/photos/upload` → 上传 3-5 张照片 → 记下返回的 photo_id
3. `GET /api/tasks` → 确认分析任务已创建
4. `GET /api/tasks/{id}` → 轮询直到 status=completed
5. `GET /api/photos/{id}` → 验证 AI 描述/标签/人脸已写入
6. `POST /api/search` → `{"query": "猫"}` → 验证返回结果
7. `POST /api/agent/chat` → 发消息测试 SSE 流式对话

### 5.4 curl 快速验证

```bash
# 上传照片
curl -X POST http://localhost:8000/api/photos/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@cat.jpg"

# 轮询进度
curl http://localhost:8000/api/tasks/$TASK_ID \
  -H "Authorization: Bearer $TOKEN"

# 搜索
curl -X POST http://localhost:8000/api/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"猫","top_k":10}'
```

---

## 6. 实施顺序

```
Phase 1 (P0) — 核心闭环 — 预计 2h
  ├── 改造 photo_service.upload_single_photo() 对接 analyze_photo_async
  ├── 改造 photo.py upload/reanalyze 端点
  └── 改造 tasks.py 端点（task_manager + DB 双写）

Phase 2 (P1) — AI 搜索 + 对话 — 预计 2h
  ├── 全新实现 search.py（4 个端点）
  └── 全新实现 agent.py（6 个端点 + SSE）

Phase 3 (P2) — 人脸 + 训练 — 预计 2h
  ├── 全新实现 face.py（8 个端点）
  ├── 全新实现 train.py（7 个端点）
  └── main.py 注册 training 路由

Phase 4 (P3) — 收尾 — 预计 1h
  ├── 全新实现 album.py（9 个端点）
  └── 全链路测试 + 问题修复
```

---

## 7. 风险点

| 风险 | 缓解措施 |
|---|---|
| ai-part 服务层依赖 `insightface`/`torch` 等重库 | 安装时仅取 CPU 版本；模型文件自动下载或规则后备 |
| TaskManager 内存存储，服务重启丢失 | DB + 内存双写，列表从 DB 查，详情优先内存 |
| ChatAgent 的 tool function `search_photos` 未真正执行搜索 | 注入 user_id + db session，对接 SearchRetriever |
| YOLO 训练需要 CUDA/GPU | 训练仅在云上执行，本地保留推理；TrainingManager 已支持检查点恢复 |
