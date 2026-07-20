"""Face detection service using InsightFace (ONNX backend).

Model is stored at the default ~/.insightface/ path,
which is mapped to a Docker volume for persistence.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def detect_faces(image_path: str) -> List[dict]:
    """Detect faces in an image and extract 512-dim embeddings.

    Args:
        image_path: Path to the image file.

    Returns:
        List of dicts:
            [{"bbox": [x1, y1, x2, y2], "embedding": [512 floats], "confidence": 0.99}, ...]

    Raises:
        ImportError: If insightface is not installed.
    """
    import insightface
    from insightface.app import FaceAnalysis
    import cv2

    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))

    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Cannot read image: {image_path}")
        return []

    faces = app.get(img)
    results = []
    for face in faces:
        bbox = face.bbox.tolist()
        embedding = face.embedding.tolist()
        results.append({
            "bbox": [int(round(b)) for b in bbox],
            "embedding": embedding,
            "confidence": round(float(face.det_score), 4),
        })

    logger.info(f"Detected {len(results)} face(s) in {image_path}")
    return results