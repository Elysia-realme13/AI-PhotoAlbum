"""Vector generation tasks"""
import logging
from app.database.session import SessionLocal
logger = logging.getLogger(__name__)

def process_photo_vector(photo_id: str, image_path: str) -> bool:
    from app.services.photo_vector_service import generate_photo_vector
    db = SessionLocal()
    try:
        result = generate_photo_vector(db, photo_id, image_path)
        return result is not None
    except Exception as e:
        logger.error(f"task failed: photo={photo_id}, {e}")
        return False
    finally:
        db.close()

def run_batch_vector_generation(batch_size: int = 10, max_count: int = None) -> dict:
    from app.services.photo_vector_service import batch_generate_vectors
    db = SessionLocal()
    try:
        stats = batch_generate_vectors(db, batch_size=batch_size, max_count=max_count)
        return stats
    except Exception as e:
        logger.error(f"batch failed: {e}")
        return {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}
    finally:
        db.close()

__all__ = ["process_photo_vector", "run_batch_vector_generation"]
