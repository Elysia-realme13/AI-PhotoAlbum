"""CLIP embedding: image + text to 512d vector"""
import io, logging
from typing import List, Optional, Union
logger = logging.getLogger(__name__)
_model = None
_processor = None
MODEL_NAME = "OFA-Sys/chinese-clip-vit-base-patch16"

def _load_model():
    global _model, _processor
    if _model is not None:
        return True
    try:
        from transformers import ChineseCLIPProcessor, ChineseCLIPModel
        logger.info(f"[CLIP] 开始加载模型: {MODEL_NAME}（首次下载约需 1-3 分钟）")
        _model = ChineseCLIPModel.from_pretrained(MODEL_NAME)
        _processor = ChineseCLIPProcessor.from_pretrained(MODEL_NAME)
        logger.info(f"[CLIP] 模型加载完成: {MODEL_NAME}")
        return True
    except ImportError:
        logger.error("缺少 transformers/torch，请执行: uv add transformers torch")
        return False
    except Exception as e:
        logger.error(f"[CLIP] 模型加载失败: {e}")
        return False
def get_image_embedding(image_source: Union[str, bytes]) -> Optional[List[float]]:
    if not _load_model():
        return None
    try:
        from PIL import Image
        if isinstance(image_source, str):
            img = Image.open(image_source).convert("RGB")
        elif isinstance(image_source, bytes):
            img = Image.open(io.BytesIO(image_source)).convert("RGB")
        else:
            raise TypeError(type(image_source))
        inputs = _processor(images=img, return_tensors="pt")
        outputs = _model.get_image_features(**inputs)
        vec = outputs[0].detach().numpy()
        if vec.ndim > 1:
            vec = vec.flatten()
        return vec.tolist()
    except Exception as e:
        logger.error(f"Image encoding failed: {e}")
        return None

def get_text_embedding(text: str) -> Optional[List[float]]:
    if not _load_model():
        return None
    try:
        inputs = _processor(text=[text], return_tensors="pt", padding=True)
        outputs = _model.get_text_features(**inputs)
        vec = outputs[0].detach().numpy()
        if vec.ndim > 1:
            vec = vec.flatten()
        return vec.tolist()
    except Exception as e:
        logger.error(f"Text encoding failed: {e}")
        return None

def get_embedding(text: str) -> Optional[List[float]]:
    return get_text_embedding(text)

__all__ = ["get_image_embedding", "get_text_embedding", "get_embedding"]
