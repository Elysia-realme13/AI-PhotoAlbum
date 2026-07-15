# API 测试步骤

> 测试对象：`项目（api）/backend/` — Photo + Tasks + Auth API

---

## 前置条件

### 1. 确认文件存在

```bash
ls backend/app/api/photo.py           # 应存在（非空）
ls backend/app/api/tasks.py           # 应存在（非空）
ls backend/app/api/auth.py            # 应存在（已实现）
ls backend/app/models/task.py         # 应存在（新增 Task 模型）
ls backend/app/schemas/response.py    # 应存在（新增 BaseResponse）
```

### 2. 安装依赖

```bash
cd backend
uv sync
```

### 3. 启动数据库

```bash
# 用项目自带的 docker-compose
docker compose up -d postgres
```

### 4. 创建 .env 文件

```bash
cp backend/.env.example backend/.env
```

如果用 SQLite（跳过 Docker）：
```bash
# 修改 .env 第一行为：
DATABASE_URL=sqlite:///./data/app.db
```

> **响应格式说明**：
> - **照片/任务接口** → 统一返回 `BaseResponse` 格式：`{"code": 200, "msg": "操作成功", "data": ...}`
> - **认证接口** (`/api/auth/*`) → 直接返回 `TokenResponse` / `UserResponse`（**不包含** `code`/`msg` 外层）
> - **异常/错误**（401/422/500）→ 由全局异常处理器返回：`{"error": "...", "detail": {...}}`（**不是** BaseResponse 格式）
> - **健康检查** `/api/health` → 返回纯 `{"status": "ok", "message": "..."}` 

---

## 启动服务

```bash
cd backend
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

看到以下输出表示成功：
```
AI-PhotoAlbum v0.1.0 启动中...
数据库: postgresql://album:album@localhost:5433/photo_album...
数据库表创建/检查完成
```

访问 `http://localhost:8000/docs` 确认 Swagger UI 可用。

---

## 测试步骤

### 步骤 1：健康检查

```bash
curl -s http://localhost:8000/api/health
```

预期：
```json
{"status": "ok", "message": "AI-PhotoAlbum service is running"}
```

---

### 步骤 2：注册用户

```bash
curl -s -X POST http://localhost:8000/api/auth/register -H "Content-Type: application/json" -d '{"username":"testuser","email":"test1@example.com","password":"123456","nickname":"testuser"}'
```

预期：
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-...",
    "username": "testuser",
    "email": "test1@example.com",
    "nickname": "testuser",
    "avatar_url": null,
    "is_active": true,
    "created_at": "2026-07-14T..."
  }
}
```

> 记下 `access_token`，后续所有请求都需要。以下用 `$TOKEN` 代替。

---

### 步骤 3：登录（验证已有用户）

```bash
curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"testuser","password":"123456"}'
```

预期：返回同样的 `access_token` + `user` 结构。

---

### 步骤 4：获取当前用户

```bash
curl -s http://localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN"
```

预期：返回用户信息。

---

### 步骤 5：上传照片

准备一张测试图片（如果没有，用 Python 生成）：

```bash
python -c "from PIL import Image; img = Image.new('RGB', (800, 600), color='blue'); img.save('./test_photo.jpg', 'JPEG'); print('done')"
```

上传：
```bash
curl -s -X POST http://localhost:8000/api/photos/upload -H "Authorization: Bearer $TOKEN" -F "files=@./test_photo.jpg"
```

预期（BaseResponse 格式）：
```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "total_uploaded": 1,
    "total_skipped": 0,
    "skipped_md5": [],
    "photos": [
      {
        "photo": {
          "id": "uuid-...",
          "filename": "abc123.jpg",
          "original_name": "test_photo.jpg",
          "width": 800,
          "height": 600,
          "photo_time": "2026-07-14T...",
          "file_type": "image",
          "file_size": 12345,
          "is_deleted": false,
          "tags": null,
          "quality_score": null
        },
        "task_ids": ["uuid-task-1", "uuid-task-2", ...]
      }
    ]
  }
}
```

> 记下返回的 `photo.id`，以下用 `$PHOTO_ID` 代替。

**关键验证点**：
- [ ] `code` = 200
- [ ] `data.total_uploaded` = 1
- [ ] `data.photos[0].photo.id` 是非空 UUID
- [ ] `data.photos[0].task_ids` 数组非空（AI 分析任务已创建）

---

### 步骤 6：重复上传同一张照片（验证去重）

```bash
curl -s -X POST http://localhost:8000/api/photos/upload -H "Authorization: Bearer $TOKEN" -F "files=@./test_photo.jpg"
```

预期：
```json
{
  "code": 200,
  "data": {
    "total_uploaded": 0,
    "total_skipped": 1,
    "skipped_md5": ["5eb63bbbe01eeed093cb22bb8f5acdc3"],
    "photos": []
  }
}
```

**关键验证点**：
- [ ] MD5 重复的照片被跳过，不创建新记录

---

### 步骤 7：照片列表

```bash
curl -s "http://localhost:8000/api/photos?page=1&page_size=10" -H "Authorization: Bearer $TOKEN"
```

预期：
```json
{
  "code": 200,
  "data": {
    "total": 1,
    "page": 1,
    "page_size": 10,
    "items": [
      {
        "id": "uuid-...",
        "filename": "abc123.jpg",
        "width": 800,
        "height": 600,
        "photo_time": "...",
        "file_type": "image",
        ...
      }
    ]
  }
}
```

**关键验证点**：
- [ ] `data.total` = 1
- [ ] `data.items` 数组包含刚才上传的照片

---

### 步骤 8：照片过滤查询

```bash
# 按文件类型过滤
curl -s "http://localhost:8000/api/photos?file_type=image&page=1" -H "Authorization: Bearer $TOKEN"

# 按时间范围过滤
curl -s "http://localhost:8000/api/photos?date_from=2026-01-01&date_to=2026-12-31" -H "Authorization: Bearer $TOKEN"

# 按排序
curl -s "http://localhost:8000/api/photos?sort_by=file_size&order=asc" -H "Authorization: Bearer $TOKEN"
```

---

### 步骤 9：照片详情

```bash
curl -s http://localhost:8000/api/photos/$PHOTO_ID -H "Authorization: Bearer $TOKEN"
```

预期：
```json
{
  "code": 200,
  "data": {
    "id": "uuid-...",
    "filename": "abc123.jpg",
    "file_path": "./data/uploads/abc123.jpg",
    "width": 800,
    "height": 600,
    "metadata": { ... },
    "description": null,
    "faces": []
  }
}
```

**关键验证点**：
- [ ] `data.metadata` 非空（包含 EXIF 信息如果图片有的话）
- [ ] 响应结构包含 `description` 和 `faces` 字段

---

### 步骤 10：获取原图文件

```bash
# 浏览器内嵌显示（查看响应头，HEAD 请求不支持，用 -D 获取头信息）
curl -s -o /dev/null -D - http://localhost:8000/api/photos/$PHOTO_ID/file -H "Authorization: Bearer $TOKEN"

# 下载
curl -s http://localhost:8000/api/photos/$PHOTO_ID/file?download=true -H "Authorization: Bearer $TOKEN" -o ./downloaded_photo.jpg
```

**关键验证点**：
- [ ] `Content-Type` = `image/jpeg`
- [ ] `Content-Disposition` 包含 `inline`（或 `attachment` 当 ?download=true）
- [ ] 下载的文件与上传的一致

---

### 步骤 11：缩略图（当前回退到原图）

```bash
curl -s -o /dev/null -D - http://localhost:8000/api/photos/$PHOTO_ID/thumbnail?size=medium -H "Authorization: Bearer $TOKEN"
```

**关键验证点**：
- [ ] 返回 200（即使暂时回退到原图）

---

### 步骤 12：修改照片属性

```bash
curl -s -X PATCH http://localhost:8000/api/photos/$PHOTO_ID -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"original_name":"vacation_beach.jpg"}'
```

预期：`data.original_name` 变为 `"vacation_beach.jpg"`。

---

### 步骤 13：软删除

```bash
curl -s -X DELETE "http://localhost:8000/api/photos/$PHOTO_ID?permanent=false" -H "Authorization: Bearer $TOKEN"
```

预期：
```json
{"code": 200, "msg": "照片已移入回收站", "data": {..., "is_deleted": true}}
```

验证回收站：
```bash
# 注意：当前版本 GET /api/photos 的 is_deleted 查询参数尚未实现（硬编码为 False），
# 暂时通过查看照片详情来验证 is_deleted 状态：
curl -s http://localhost:8000/api/photos/$PHOTO_ID -H "Authorization: Bearer $TOKEN"
```
- [ ] 响应中 `data.is_deleted` = `true`（确认已进入回收站）
- [ ] 照片列表 `GET /api/photos` 中不再出现该照片

---

### 步骤 14：恢复照片

```bash
curl -s -X POST http://localhost:8000/api/photos/$PHOTO_ID/restore -H "Authorization: Bearer $TOKEN"
```

预期：
```json
{"code": 200, "msg": "照片已恢复", "data": {..., "is_deleted": false}}
```

---

### 步骤 15：任务列表

```bash
curl -s http://localhost:8000/api/tasks -H "Authorization: Bearer $TOKEN"
```

预期：
```json
{
  "code": 200,
  "data": {
    "total": 5,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "id": "uuid-...",
        "photo_id": "uuid-...",
        "task_type": "face_detect",
        "status": "pending",
        "progress": {},
        "result": {},
        "error_message": null,
        "created_at": "..."
      },
      ...
    ]
  }
}
```

**关键验证点**：
- [ ] 上传时创建的 AI 分析任务出现在列表中
- [ ] `task_type` 包含 `face_detect`, `image_description`, `image_embedding`, `quality_assessment`, `exif_extract`

---

### 步骤 16：任务筛选

```bash
# 按状态筛选
curl -s "http://localhost:8000/api/tasks?status=pending" -H "Authorization: Bearer $TOKEN"

# 按类型筛选
curl -s "http://localhost:8000/api/tasks?task_type=face_detect" -H "Authorization: Bearer $TOKEN"

# 按照片筛选
curl -s "http://localhost:8000/api/tasks?photo_id=$PHOTO_ID" -H "Authorization: Bearer $TOKEN"
```

---

### 步骤 17：任务统计

```bash
curl -s http://localhost:8000/api/tasks/stats -H "Authorization: Bearer $TOKEN"
```

预期：
```json
{
  "code": 200,
  "data": {
    "total": 5,
    "pending": 5,
    "running": 0,
    "completed": 0,
    "failed": 0
  }
}
```

---

### 步骤 18：单个任务详情

```bash
# 用步骤 15 返回的任意 task_id，替换下面 <TASK_ID>
curl -s http://localhost:8000/api/tasks/<TASK_ID> -H "Authorization: Bearer $TOKEN"
```

---

### 步骤 19：边界条件测试

```bash
# 未登录访问
curl -s http://localhost:8000/api/photos
# 预期: 401 Unauthorized

# 无效 Token
curl -s http://localhost:8000/api/photos -H "Authorization: Bearer invalid_token_here"
# 预期: 401

# 不存在的照片
curl -s http://localhost:8000/api/photos/00000000-0000-0000-0000-000000000000 -H "Authorization: Bearer $TOKEN"
# 预期: {"code": 404, "msg": "照片不存在", "data": null}

# 无效分页参数
curl -s "http://localhost:8000/api/photos?page=0" -H "Authorization: Bearer $TOKEN"
# 预期: 422 Validation Error

# 上传时不上传文件
curl -s -X POST http://localhost:8000/api/photos/upload -H "Authorization: Bearer $TOKEN"
# 预期: 422 Validation Error
```

---

### 步骤 20：批量获取照片

```bash
curl -s -X POST http://localhost:8000/api/photos/batch -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "{\"photo_ids\": [\"$PHOTO_ID\"]}"
```

预期：返回该照片的列表项。

---

### 步骤 21：时间轴

```bash
curl -s "http://localhost:8000/api/photos/timeline/list?group_by=month" -H "Authorization: Bearer $TOKEN"
```

预期：
```json
{
  "code": 200,
  "data": [
    {"date": "2026-07", "count": 1, "cover_photo": {...}}
  ]
}
```

---

## 一键测试脚本

### 脚本内容

保存以下内容为 `test_api.sh`（放在项目根目录）：

```bash
#!/bin/bash
BASE="http://localhost:8000/api"
TOKEN="<从步骤2获取的access_token>"

echo "=== 1. 健康检查 ==="
curl -s http://localhost:8000/api/health | python -m json.tool

echo "=== 2. 上传照片 ==="
UPLOAD=$(curl -s -X POST $BASE/photos/upload -H "Authorization: Bearer $TOKEN" -F "files=@./test_photo.jpg")
echo $UPLOAD | python -m json.tool
PHOTO_ID=$(echo $UPLOAD | python -c "import sys,json; d=json.load(sys.stdin); print(d['data']['photos'][0]['photo']['id'])")
echo "PHOTO_ID=$PHOTO_ID"

echo "=== 3. 照片列表 ==="
curl -s "$BASE/photos?page=1&page_size=5" -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin); print(f'total={d[\"data\"][\"total\"]}')"

echo "=== 4. 照片详情 ==="
curl -s $BASE/photos/$PHOTO_ID -H "Authorization: Bearer $TOKEN" | python -m json.tool

echo "=== 5. 任务统计 ==="
curl -s $BASE/tasks/stats -H "Authorization: Bearer $TOKEN" | python -m json.tool

echo "=== 6. 软删除 ==="
curl -s -X DELETE "$BASE/photos/$PHOTO_ID?permanent=false" -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin); print(f'msg={d[\"msg\"]}')"

echo "=== 7. 恢复 ==="
curl -s -X POST $BASE/photos/$PHOTO_ID/restore -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin); print(f'msg={d[\"msg\"]}')"

echo "=== 完成 ==="
```

### 使用步骤

#### 1. 获取 Token

在运行脚本前，需要先拿到有效的 `access_token`。两种方式：

**方式 A — 手动获取（推荐）**：先按上方步骤 2 注册用户，将返回的 `access_token` 值填入脚本：
```
TOKEN="eyJhbGciOiJI..."
```

**方式 B — 自动获取**：将脚本中 `TOKEN` 那一行替换为：
```bash
TOKEN=$(curl -s -X POST $BASE/auth/login -H "Content-Type: application/json" -d '{"username":"testuser","password":"123456"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

#### 2. 准备测试图片

```bash
python -c "from PIL import Image; img = Image.new('RGB', (800, 600), color='blue'); img.save('./test_photo.jpg', 'JPEG'); print('done')"
```

#### 3. 确认服务运行

```bash
# 另开终端启动后端
cd backend
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. 执行脚本

```bash
bash test_api.sh
```

### 前置条件检查清单

- [ ] 后端服务已启动，监听 `localhost:8000`
- [ ] 已通过步骤 2 注册用户，`TOKEN` 已填入脚本
- [ ] 项目根目录下有 `test_photo.jpg` 测试图片
- [ ] 已安装 `python`（用于 JSON 格式化输出）

> **说明**：该脚本覆盖 7 个核心步骤的快速回归测试。完整 23 项测试仍需按上方步骤 1-21 逐项执行。

---

## 测试检查清单

| # | 测试项 | 预期 |
|---|---|---|
| 1 | `GET /api/health` | 200, `{"status":"ok"}` |
| 2 | `POST /api/auth/register` | 201, 返回 token + user |
| 3 | `POST /api/auth/login` | 200, 返回 token + user |
| 4 | `GET /api/auth/me` | 200, 返回 user |
| 5 | `POST /api/photos/upload` | 200, `data.total_uploaded>0`, `task_ids` 非空 |
| 6 | 重复上传同一文件 | 200, `total_skipped=1`（MD5 去重） |
| 7 | `GET /api/photos` | 200, 分页结构正确 |
| 8 | `GET /api/photos?file_type=image` | 200, 过滤生效 |
| 9 | `GET /api/photos/{id}` | 200, 含 metadata + description + faces |
| 10 | `GET /api/photos/{id}/file` | 200, Content-Type: image/jpeg |
| 11 | `GET /api/photos/{id}/thumbnail` | 200, 回退到原图 |
| 12 | `PATCH /api/photos/{id}` | 200, 属性已更新 |
| 13 | `DELETE /api/photos/{id}` (软) | 200, is_deleted=true |
| 14 | 软删除后查详情验证 `is_deleted` | `data.is_deleted`=true, 列表不再出现 |
| 15 | `POST /api/photos/{id}/restore` | 200, is_deleted=false |
| 16 | `GET /api/tasks` | 200, 任务列表 |
| 17 | `GET /api/tasks?status=pending` | 200, 状态过滤 |
| 18 | `GET /api/tasks/stats` | 200, 统计数字正确 |
| 19 | `GET /api/tasks/{id}` | 200, 任务详情 |
| 20 | 未登录访问 | 401 |
| 21 | 无效 photo_id | 200, code=404 |
| 22 | `POST /api/photos/batch` | 200, 批量返回 |
| 23 | `GET /api/photos/timeline/list` | 200, 时间轴分组 |

---

## 修复记录

> 以下 bug 在全量 API 测试中发现并已修复。

### Bug 1: 时间轴查询 `min(uuid)` 报错

- **文件**: `backend/app/crud/photo.py:250`
- **现象**: `GET /api/photos/timeline/list` 返回 500 错误
- **原因**: PostgreSQL 的 `min()` 不支持 UUID 类型 — `function min(uuid) does not exist`
- **修复**: `func.min(Photo.id)` → `func.array_agg(Photo.id)`，取数组首项作为 `cover_photo_id`
- **状态**: ✅ 已修复，步骤 21 测试通过

### Bug 2: `schemas/__init__.py` 类名引用错误

- **文件**: `backend/app/schemas/__init__.py`
- **现象**: 导入了不存在的 `PhotoResponse`、`PhotoListResponse`
- **修复**: 
  - `PhotoResponse` → `PhotoDetailResponse`
  - `PhotoListResponse` → `PhotoListItem`
  - 补全 `photo`、`task`、`response` 三个模块的重导出
- **状态**: ✅ 已修复
