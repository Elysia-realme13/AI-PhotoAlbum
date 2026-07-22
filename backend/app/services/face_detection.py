"""
人脸检测服务 — InsightFace 封装
若 insightface 未安装，返回 None，由调用方降级处理
"""
import logging
from typing import Optional, List
import os

logger = logging.getLogger(__name__)

_model = None


def _load_model():
    """懒加载 InsightFace 模型"""
    global _model
    if _model is not None:
        return _model
    try:
        # 模型文件实际路径：backend/../data/insightface_home/
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _home = os.path.join(_root, 'data', 'insightface_home')
        if os.path.isdir(_home):
            os.environ['INSIGHTFACE_HOME'] = _home.replace('\\', '/')
        import insightface
        _model = insightface.app.FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        _model.prepare(ctx_id=-1)
        logger.info("InsightFace buffalo_l 模型加载完成")
        return _model
    except ImportError:
        logger.warning("insightface 未安装，人脸检测不可用。安装: uv add insightface onnxruntime")
        return None


def detect_faces(image_path: str) -> Optional[List[dict]]:
    """
    检测图片中的人脸

    Args:
        image_path: 图片文件路径

    Returns:
        人脸列表，每人脸包含:
        - embedding: 512维特征向量
        - bbox: [x1, y1, x2, y2] 归一化到 0-1
        - confidence: 检测置信度
        如果模型未安装，返回 None
    """
    model = _load_model()
    if model is None:
        return None

    import cv2
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"无法读取图片: {image_path}")
        return []

    h, w = img.shape[:2]
    faces = model.get(img)

    results = []
    for face in faces:
        x1, y1, x2, y2 = face.bbox.astype(float)
        results.append({
            "embedding": face.embedding.tolist() if hasattr(face, 'embedding') else None,
            "bbox": [round(x1 / w, 4), round(y1 / h, 4), round(x2 / w, 4), round(y2 / h, 4)],
            "confidence": round(float(face.det_score), 4),
        })

    return results
