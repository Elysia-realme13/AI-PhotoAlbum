# AI-PhotoAlbum 后端服务模块

本目录包含 AI 智能相册后端的全部业务服务，按功能分为四大类：**图像处理**、**AI 视觉检测**、**人脸管理**、**智能检索**。

---

## 目录结构

```
services/
├── detection_service.py          # YOLO 目标检测服务
├── exif_service.py               # EXIF 元数据提取
├── face_cluster_service.py       # 人脸增量聚类
├── name_confirmation_service.py  # 交互式命名确认
├── search_service.py             # 文本检索（CLIP + 分词）
├── thumbnail.py                  # 缩略图生成
├── README.md                     # 本文件
│
├── agent/                        # Agent 子模块（预留）
├── ai_providers/                 # AI 模型调用抽象层（预留）
```

---

## 1. exif_service.py — EXIF 元数据提取

| 项目 | 说明 |
| --- | --- |
| 依赖 | Pillow, pillow-heif |
| 核心函数 | extract_exif(file_path) -> dict |
| 提取字段 | 拍摄时间、GPS经纬度、相机型号/制造商、镜头、焦距、光圈、快门、ISO、海拔 |
| 特点 | 支持HEIC/HEIF；GPS十进制自动换算；非图片静默降级 |

```python
from app.services.exif_service import extract_exif
info = extract_exif("data/uploads/photo.jpg")
print(info['photo_time'], info['latitude'], info['camera_model'])
```

---

## 2. thumbnail.py — 缩略图生成

| 项目 | 说明 |
| --- | --- |
| 依赖 | Pillow |
| 核心函数 | generate_thumbnail_bytes(image_bytes) -> bytes |
| 参数 | THUMBNAIL_SIZE=(400,400), THUMBNAIL_QUALITY=85 |
| 特点 | 保持宽高比、RGBA自动转RGB、LANCZOS重采样 |

```python
from app.services.thumbnail import generate_thumbnail_bytes
thumb = generate_thumbnail_bytes(original_bytes)
```

---

## 3. detection_service.py — YOLO 目标检测

| 项目 | 说明 |
| --- | --- |
| 模型 | Ultralytics YOLO26n（COCO 80类，约6MB） |
| 依赖 | ultralytics, numpy, Pillow |
| 缓存 | 全局单例模型实例，避免重复加载 |

### 核心函数

| 函数 | 用途 |
| --- | --- |
| detect_objects(image_path) | 从文件路径输入，执行推理 |
| detect_objects_from_bytes(bytes) | 从字节数据输入（上传流程） |
| get_detection_summary(detections) | 按类别去重统计 |
| draw_detections(path, detections, output_path) | 绘制检测框并保存JPEG |

### 返回值格式

```python
{
    "success": True,
    "detections": [{
        "label": "person",       # COCO 类别名称
        "confidence": 0.92,       # 置信度
        "bbox_x": 0.5,            # 归一化中心坐标 (0-1)
        "bbox_y": 0.3,
        "bbox_w": 0.2,            # 归一化宽高 (0-1)
        "bbox_h": 0.4,
        "class_id": 0,            # COCO 类别ID
    }],
    "image_width": 1920,
    "image_height": 1080,
    "total": 3,
    "model": "yolo26n.pt",
}
```

**COCO支持检测的80类示例**：person, car, dog, cat, chair, tv, bottle, book, cell phone ...

```python
from app.services.detection_service import detect_objects, draw_detections
result = detect_objects("data/uploads/test.jpg")
if result['success']:
    draw_detections("data/uploads/test.jpg", result["detections"])
```

---

## 4. face_cluster_service.py — 人脸增量聚类

| 项目 | 说明 |
| --- | --- |
| 向量维度 | 512维（InsightFace feature） |
| 相似度 | 余弦相似度（numpy实现） |
| 阈值 | 默认0.6（DEFAULT_CLUSTER_THRESHOLD） |
| 存储 | Face.face_feature（pgvector Vector(512)）, FaceIdentity 聚类 |

### 核心函数

| 函数 | 用途 |
| --- | --- |
| update_face_clusters(db, photo_id, threshold) | 对新增照片的人脸执行增量聚类 |
| compute_cluster_center(db, cluster_id) | 计算聚类平均embedding向量 |
| compute_all_cluster_centers(db) | 计算所有聚类中心点 |
| get_representative_faces(db, cluster_id, top_k) | 获取置信度最高的代表性人脸 |
| get_unamed_clusters(db, owner_id, top_k) | 获取未命名聚类列表（附头像） |
| get_cluster_face_photos(db, cluster_id) | 获取聚类下所有photo_id |

### 聚类策略

1. 提取新照片中人脸的512维embedding
2. 与所有已有聚类中心计算余弦相似度
3. 若最大相似度 >= 阈值，归入该聚类
4. 否则创建新的FaceIdentity聚类

```python
from app.services.face_cluster_service import update_face_clusters
update_face_clusters(db, photo_id="...", threshold=0.6, owner_id="...")
```

---

## 5. name_confirmation_service.py — 交互式命名确认

| 项目 | 说明 |
| --- | --- |
| 存储 | 内存字典（生产建议Redis） |
| TTL | 默认10分钟 |
| 接口 | 仿Redis命令：setex / get / delete |

### 核心函数

| 函数 | 用途 |
| --- | --- |
| create_pending(session_id, query, candidates) | 创建待确认会话 |
| get_pending(session_id, query) | 查询待确认状态 |
| confirm_name(db, session_id, query, cluster_id, name, aliases) | 确认并绑定称呼 |
| clear_pending(session_id, query) | 清除pending |
| find_clusters_by_name(db, owner_id, name) | 根据称呼查找已命名聚类 |

### 命名流程

1. 搜索请求触发人称识别，未匹配时系统返回候选聚类
2. 前端展示候选人的代表性头像，用户选择
3. 确认后系统绑定称呼到FaceIdentity，更新所有Face记录

```python
from app.services.name_confirmation_service import confirm_name
confirm_name(db, session_id="u001", query="爸爸",
            cluster_id="uuid...", name="爸爸", aliases=["老爸"])
```

---

## 6. search_service.py — 文本检索服务

| 项目 | 说明 |
| --- | --- |
| 分词 | jieba.posseg 词性标注（仅提取名词） |
| 向量检索 | pgvector <=> cosine距离算子 |
| 降级方案 | ImageDescription.tags / description 文本LIKE匹配 |
| 人称识别 | 正则匹配亲属称谓和中文姓名 |

### 核心函数

| 函数 | 用途 |
| --- | --- |
| extract_nouns(text) | jieba分词 + 过滤名词词性（n/nr/ns/nt...） |
| extract_person_names(text) | 正则提取亲属称谓和中文人名 |
| clip_search_by_text(db, query, top_k, owner_id) | 文本->CLIP向量->pgvector检索 |
| search_faces_by_name(db, person_name, owner_id) | 按人称查找聚类photo_id |
| get_unnamed_candidates(db, owner_id, top_k) | 获取未命名候选聚类 |

### CLIP检索流程

1. 用户输入 -> jieba词性标注 -> 提取名词
2. embedding模型 -> 512维向量
3. pgvector: SELECT ... ORDER BY embedding <=> query_vector
4. 返回Top-K photo_id + cosine_similarity

```python
from app.services.search_service import extract_nouns, clip_search_by_text
nouns = extract_nouns("红色的花和蓝色的天空")  # ["花", "天空"]
results = clip_search_by_text(db, "花 天空", top_k=20)
```

---

## 检索代理集成

以上服务通过 agents/search_agent.py（LangGraph图）串联为完整链路：

```
extract_entities -> recognize_person -> clip_search -> merge_results
                      | (pending)         |
                      v                   v
                返回候选              返回结果
```

### 端到端调用

```python
from app.agents.search_agent import run_search_agent

result = run_search_agent(
    query="找爸爸在公园的照片",
    db=db_session,
    owner_id="user_uuid",
)

if result['needs_confirmation']:
    candidates = result['pending_candidates']
else:
    photos = result['merged_results']
```

---

## 依赖汇总

| 服务 | 依赖 | 安装命令 |
| --- | --- | --- |
| detection_service | ultralytics, numpy, Pillow | uv add ultralytics |
| exif_service | Pillow, pillow-heif | 已内置 |
| thumbnail | Pillow | 已内置 |
| face_cluster_service | numpy, pgvector | 已内置 |
| name_confirmation_service | 无额外依赖 | - |
| search_service | jieba, pgvector | uv add jieba |
| agents/search_agent | langgraph | uv add langgraph |

> pgvector 和 Pillow 已在 pyproject.toml 中。
> YOLO模型权重（yolo26n.pt）首次调用时自动下载。
> CLIP embedding 模型需额外部署（ai_providers/embedding.py 预留）。
> 人脸 embedding 由 InsightFace 在 ai_providers/ 中提取。

---

## 测试脚本

```bash
# YOLO检测测试
cd backend
uv run python scripts/test_yolo.py data/uploads/test.jpg

# 直接调用服务
uv run python -c "
import sys; sys.path.insert(0, '.')
from app.services.detection_service import detect_objects
r = detect_objects('../data/uploads/test1.jpg')
print(f'检测到 {r[\'total\']} 个物体')
"
```

---

## 代码规范

- 类型注解（Python 3.11+）
- Google-style docstring
- __all__ 显式导出
- 异常不吞没，降级有清晰日志
- 全局资源（模型/存储）使用模块级变量+懒加载