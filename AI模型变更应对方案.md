# AI 模型变更应对方案

> 当前架构已具备 Provider 模式 + ModelManager + 优雅降级三重机制，
> 此文档分析 6 类变更场景，给出从"最小改动"到"架构升级"的应对策略。

---

## 当前架构的优势与不足

### 已有防护

| 机制 | 作用 | 位置 |
|---|---|---|
| **Provider 模式** | 每个模型独立封装，内部逻辑对外不可见 | `ai_providers/face.py`, `clip.py`, `classifier.py`, `yolo.py`, `llm.py` |
| **ModelManager 单例** | 统一注册/加载/缓存/释放 + 闲置回收 | `ai_providers/manager.py` |
| **延迟导入** | 缺少依赖时不会在 import 阶段崩溃 | `__init__.py` 的 `__getattr__` 模式 |
| **优雅降级** | 模型文件缺失 → 规则后备；API Key 未配置 → 跳过 | `classifier._fallback_classify()`, `llm.is_ready()` |
| **双引擎** | CLIP 同时支持 sentence-transformers 和 transformers | `clip.py` |

### 当前短板

1. **无接口契约** — 每个 Provider 方法名、返回值都不同，替换时需要遍历所有调用点
2. **硬编码模型名** — `"buffalo_l"`, `"clip-ViT-B-32"`, `"gpt-4o"` 散落在代码中
3. **向量维度耦合** — CLIP 换模型后嵌入维度变化，旧向量全部失效
4. **LLM 绑定 OpenAI** — SDK 和数据结构都与 OpenAI 耦合
5. **无版本标记** — 无法区分"旧模型产生的数据"和"新模型产生的数据"

---

## 场景 1：CLIP 模型替换（同能力，不同模型）

### 变更举例
```
CLIP ViT-B-32 (512维) → CLIP ViT-L-14 (768维) → SigLIP → EVA-CLIP → 中文 CLIP
```

### 影响范围
- **嵌入向量维度变化**：`image_vectors.embedding Vector(512)` 字段维度固定，换模型后不兼容
- **相似度阈值失效**：旧阈值 0.2 可能不再适用
- **已有搜索结果变化**：同一查询返回排序不同
- **调用点**：`ClipProvider.embed_image()` / `embed_text()` / `similarity()` / `rank_images()`

### 应对策略

**短期（不改表结构）**：
```python
# clip.py — 在 embed 出口做维度适配
class ClipProvider:
    def __init__(self, model_name="clip-ViT-B-32", target_dim=512):
        self.model_name = model_name
        self.target_dim = target_dim  # 兼容旧表结构
        self._dim_reducer = None      # PCA/线性适配器

    def embed_image(self, image):
        vec = self._raw_embed(image)  # 新模型原始维度（如 768）
        if len(vec) != self.target_dim:
            vec = self._reduce_dim(vec)  # PCA 投影到 512
        return vec.astype(np.float32)
```

**中期（版本标记 + 渐进迁移）**：
```sql
-- image_vectors 表加版本字段
ALTER TABLE image_vectors ADD COLUMN model_version VARCHAR(50) DEFAULT 'clip-vit-b32-v1';

-- 新模型写入新版本标记，查询时优先匹配同版本，无同版本时跨版本降级
```

**长期（迁移到多模型并存）**：
- 配置中声明模型映射表，启动时自动检测模型文件 → 选择对应 Provider
- 后台任务对旧向量做批量重嵌入

**改动量**：短期 0 处 API 改动（仅 Provider 内部），中期 1 处 DB migration + 1 处 schema 字段，长期 2-3 个文件。

---

## 场景 2：LLM 提供商切换（同能力，不同 API）

### 变更举例
```
OpenAI GPT-4o → Anthropic Claude → 本地 Ollama/Llama → vLLM → 国产大模型
```

### 影响范围
- **SDK 不同**：`openai.OpenAI` → `anthropic.Anthropic` → `ollama.Client`
- **图片传入方式不同**：OpenAI 用 `image_url`，Claude 用 `source.type: "base64"`
- **response_format 不同**：OpenAI 支持 `json_object`，部分模型不支持
- **调用点**：`LLMProvider._call_llm()` × `analyze_image()` × `parse_search_intent()` × `detect_subjects()` + ChatAgent 中的 LLM 调用

### 应对策略：Adapter 模式

```
                     ┌─────────────────────┐
                     │   LLMProvider       │  ← 对外接口不变
                     │   (facade)          │
                     └──────┬──────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐ ┌───────────┐ ┌──────────┐
        │ OpenAI   │ │ Anthropic │ │ Ollama   │
        │ Adapter  │ │ Adapter   │ │ Adapter  │
        └──────────┘ └───────────┘ └──────────┘
```

```python
# llm.py — 改造后
from abc import ABC, abstractmethod

class BaseLLMAdapter(ABC):
    """LLM 适配器抽象接口"""
    @abstractmethod
    def chat_with_image(self, system_prompt: str, image_base64: str,
                        mime_type: str, response_json: bool) -> dict:
        ...

class OpenAIAdapter(BaseLLMAdapter):
    def chat_with_image(self, system_prompt, image_base64, mime_type, response_json):
        # 现有 OpenAI 逻辑
        ...

class AnthropicAdapter(BaseLLMAdapter):
    def chat_with_image(self, system_prompt, image_base64, mime_type, response_json):
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        # Claude 的图片传入方式不同
        msg = client.messages.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": mime_type, "data": image_base64
                    }},
                    {"type": "text", "text": system_prompt}
                ]
            }]
        )
        return json.loads(msg.content[0].text)

class OllamaAdapter(BaseLLMAdapter):
    def chat_with_image(self, system_prompt, image_base64, mime_type, response_json):
        # Ollama 不支持直接传 base64，需先写临时文件或换 API
        ...

class LLMProvider:
    def __init__(self, provider="openai", **kwargs):
        self._adapter = ADAPTER_REGISTRY[provider](**kwargs)  # 工厂模式

    def analyze_image(self, image_path):
        return self._adapter.chat_with_image(ANALYSIS_PROMPT, ...)
```

**配置驱动**（`.env` 或 `settings.py`）：
```bash
LLM_PROVIDER=anthropic          # openai | anthropic | ollama | vllm
LLM_API_KEY=sk-ant-xxx
LLM_MODEL=claude-sonnet-5
LLM_BASE_URL=https://api.anthropic.com
```

**改动量**：1 个 llm.py 改造（新增 3-4 个 Adapter 类）+ 1 行 .env 配置。**API 层完全不需改动**。

---

## 场景 3：人脸模型替换（同能力，不同框架）

### 变更举例
```
InsightFace buffalo_l → MediaPipe Face → YOLO-Face → RetinaFace → SCRFD
```

### 影响范围
- **检测框格式**：`[x1,y1,x2,y2]` vs `[cx,cy,w,h]` vs `[x,y,w,h]`
- **特征向量维度**：InsightFace 512维 vs ArcFace 512维 vs MagFace 256维
- **置信度范围**：0-1 vs logit
- **调用点**：FaceProvider 全部方法 + FaceExpert + FaceClusterer + SimilarFaceRetriever

### 应对策略：接口契约 + 归一化层

```python
# face.py — 定义标准化返回格式
from typing import Protocol

class FaceDetectorProtocol(Protocol):
    """所有人脸检测器必须遵循的接口"""
    def detect_and_extract(self, image: np.ndarray) -> list[dict]:
        """返回统一格式:
        [{
            "bbox": [x1, y1, x2, y2],    # 始终是左上-右下
            "confidence": 0.0-1.0,        # 始终归一化
            "embedding": np.ndarray,       # 始终 np.float32
            "landmark": [[x,y], ...] | None
        }]
        """
        ...

class InsightFaceProvider:
    def detect_and_extract(self, image):
        # 现有逻辑（InsightFace 已输出上述格式，无需转换）
        ...

class MediaPipeFaceProvider:
    def detect_and_extract(self, image):
        raw = self._mp_face_detector.process(image)
        # 转换 MediaPipe 格式 → 统一格式
        return [self._normalize(r) for r in raw.detections]

    def _normalize(self, det):
        # MediaPipe 的 bbox 是 [x, y, w, h] 相对坐标 → [x1, y1, x2, y2] 绝对坐标
        h, w = self._image_shape
        x1 = int(det.location_data.relative_bounding_box.xmin * w)
        y1 = int(det.location_data.relative_bounding_box.ymin * h)
        x2 = int(x1 + det.location_data.relative_bounding_box.width * w)
        y2 = int(y1 + det.location_data.relative_bounding_box.height * h)
        return {"bbox": [x1, y1, x2, y2], "confidence": det.score, ...}
```

**向量维度兼容**：
```python
# 如果新人脸模型输出不同维度（如 256 维），做零填充或 PCA 对齐
def _adapt_embedding(self, vec_256d):
    if self.target_dim == 512:
        return np.pad(vec_256d, (0, 256))  # 不推荐：信息量不变
        # 或者：训练一个轻量 MLP 映射 256→512
```

**改动量**：1 个 face.py（定义 Protocol 接口 + 1-2 个新 Provider）+ 配置 1 行。API 层不改动。

---

## 场景 4：目标检测模型替换（同能力，不同模型）

### 变更举例
```
YOLO26n → YOLO11n → YOLO-NAS → DETR → RT-DETR → EfficientDet
```

### 影响范围
- **YOLO SDK**：ultralytics 只支持 YOLO 系列
- **训练流程**：TrainingManager 调用 YoloProvider.train()
- **推理结果**：不同模型输出格式不同（类别名、置信度阈值）
- **调用点**：YoloProvider + ObjectDetectionExpert

### 应对策略

```python
# yolo.py — 统一检测结果格式
@dataclass
class DetectionResult:
    """所有检测器的统一输出格式"""
    bbox: list[float]        # [x1, y1, x2, y2] 绝对像素坐标
    class_name: str          # "cat", "dog", "car" ...
    confidence: float        # 0.0-1.0
    class_id: int = -1

class YoloProvider:
    def detect(self, image: np.ndarray) -> list[DetectionResult]:
        results = self._model(image)
        return [
            DetectionResult(
                bbox=box.xyxy[0].tolist(),
                class_name=self._model.names[int(box.cls[0])],
                confidence=float(box.conf[0]),
                class_id=int(box.cls[0]),
            )
            for box in results[0].boxes
        ]

class DETRProvider:
    def detect(self, image: np.ndarray) -> list[DetectionResult]:
        # 不同模型，统一输出格式
        raw = self._detr_model(image)
        return [DetectionResult(bbox=..., class_name=..., confidence=...) ...]
```

**训练接口兼容**：训练流程深度绑定 YOLO 的 `data.yaml` 格式。如果换成非 YOLO 模型（如 DETR），训练数据集格式不同，TrainingManager 也需要改动。这是所有场景中**耦合最紧**的部分。

**改动量**：推理更换 1 个 yolo.py（新增 Provider）。训练更换需要重写 `training_manager.py` + `train.py` API，工作量较大。

---

## 场景 5：场景分类模型替换（同能力，不同模型）

### 变更举例
```
EfficientNet-B0 → MobileNetV4 → ConvNeXt → ViT → SwinTransformer
```

### 影响范围
- **输入尺寸**：224×224 → 384×384 → 518×518
- **类别数**：5 类 → N 类（标签映射需要更新）
- **预处理器**：mean/std 归一化参数不同
- **调用点**：SceneClassifier + SceneExpert

### 应对策略

```python
# classifier.py — 模型配置集中管理
MODEL_CONFIGS = {
    "efficientnet_b0": {
        "input_size": 224,
        "mean": [0.485, 0.456, 0.406],
        "std": [0.229, 0.224, 0.225],
        "labels": ["人物", "动物", "风景", "文档", "通用"],
        "labels_en": ["person", "animal", "landscape", "document", "general"],
    },
    "mobilenet_v4": {
        "input_size": 256,
        "mean": [0.5, 0.5, 0.5],
        "std": [0.5, 0.5, 0.5],
        "labels": [...],   # MobileNet 训练时的类别映射
    },
}

class SceneClassifier:
    def __init__(self, model_name="efficientnet_b0"):
        self.config = MODEL_CONFIGS[model_name]  # 从配置读取所有参数
        ...

    def classify(self, image, top_k=3):
        probs = self._run_onnx(image)
        # 标签映射：如果模型输出 1000 类 ImageNet，映射到 5 类
        if self.config.get("label_map"):
            probs = self._map_to_scene_labels(probs)
        ...
```

**改动量**：1 个 classifier.py（新增 MODEL_CONFIGS）+ 模型文件替换。API 层完全不动。

---

## 场景 6：新增能力（以前没有，现在要加）

### 变更举例
```
新增: OCR 文字识别 / 视频关键帧提取 / 图像超分 / 智能裁剪 / NSFW 检测
```

### 影响范围
- **新 Provider**：`ai_providers/ocr.py` / `video.py` / `super_resolution.py`
- **新 Expert**：`agent/expert_ocr.py`（如果要加入检测管道）
- **新 API 端点**：`/api/ocr` / `/api/video`
- **新 DB 表**：OCR 结果表 / 视频帧表

### 应对策略：插件式注册

```python
# 在 ai_providers/__init__.py 中追加即可，无需改动现有代码
_MODULES = {
    ...
    "OCRProvider": "app.services.ai_providers.ocr",       # 新增
    "VideoProcessor": "app.services.ai_providers.video",   # 新增
}
```

Pipeline 如果有兴趣注册机制，新增 Expert 也可以热插拔：
```python
# photo_analysis.py
class PhotoAnalysisPipeline:
    def __init__(self):
        self._expert_registry = {
            "face": FaceExpert,
            "object": ObjectDetectionExpert,
            "scene": SceneExpert,
            "ocr": OCRExpert,              # 新增，一行注册
        }
```

**改动量**：新增 Provider（1 个文件）+ 新增 API 路由（1 个文件）+ `__init__.py` 注册（1 行）。现有代码完全不动。

---

## 总结：改动量矩阵

| 场景 | Provider 层 | 服务层 | API 层 | DB |
|---|---|---|---|---|
| **1. CLIP 换模型** | 🟡 内部适配 | 🟢 不动 | 🟢 不动 | 🟡 加版本字段 |
| **2. LLM 换厂商** | 🟡 新增 Adapter | 🟢 不动 | 🟢 不动 | 🟢 不动 |
| **3. 人脸换模型** | 🟡 新增 Provider | 🟢 不动 | 🟢 不动 | 🟢 不动 |
| **4. 检测换模型** | 🟡 新增 Provider | 🟢 推理不动 🔴 训练需重写 | 🟢 不动 | 🟢 不动 |
| **5. 分类换模型** | 🟡 配置化参数 | 🟢 不动 | 🟢 不动 | 🟢 不动 |
| **6. 新增能力** | 🟢 新增文件 | 🟢 注册一行 | 🟡 新增路由 | 🟡 新增表 |

> 🟢 = 不动 &nbsp;&nbsp; 🟡 = 少量改动 &nbsp;&nbsp; 🔴 = 需要较大重写

## 架构改进路线图

```
当前 ──────────────────────────────────────────────► 目标

   Provider 模式              →    + Protocol/ABC 接口契约
   硬编码模型名                →    + 配置驱动模型选择
   无版本标记                  →    + embedding.model_version 字段
   无配置中心                  →    + settings.AI_MODELS 配置块
   LLM 绑定 OpenAI            →    + Adapter 模式（多厂商）
   YOLO 训练强耦合             →    + 训练接口抽象（低优先级）
```

### 推荐优先实施的 3 项改进

| 优先级 | 改进 | 工作量 | 原因 |
|---|---|---|---|
| **P0** | LLM Adapter 模式 | 2h | OpenAI API 随时可能被替换，影响面最大 |
| **P1** | 配置驱动模型选择 | 1h | 将所有硬编码模型名收拢到 settings，一键切换 |
| **P2** | 向量版本标记 | 1h | DB migration + Schema 字段，为模型升级做准备 |
