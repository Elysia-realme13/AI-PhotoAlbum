"""
pytest fixtures: mock DB session, synthetic test image, sample detection data
"""
import io
import uuid
import pytest
from unittest.mock import MagicMock, Mock, patch
from PIL import Image


@pytest.fixture
def mock_db():
    """Mock SQLAlchemy Session for service tests"""
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    db.flush = MagicMock()
    return db


@pytest.fixture
def synthetic_image():
    """Generate a small RGB test image (100x100)"""
    img = Image.new("RGB", (100, 100), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@pytest.fixture
def synthetic_image_with_exif():
    """Generate a test image with EXIF data"""
    img = Image.new("RGB", (200, 150), color=(255, 0, 0))
    # Pillow's EXIF requires specific handling
    from PIL.ExifTags import Base as ExifBase
    exif_data = img.getexif()
    # DateTimeOriginal, Make, Model
    exif_data[0x9003] = "2024:06:15 14:30:00"
    exif_data[0x010F] = "TestCamera"
    exif_data[0x0110] = "TestModel X100"
    # FocalLength, FNumber
    exif_data[0x920A] = (500, 10)  # 50.0mm
    exif_data[0x829D] = (28, 10)   # F2.8
    exif_data[0x8827] = 400        # ISO
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_data.tobytes())
    return buf.getvalue()


@pytest.fixture
def sample_detections():
    """Sample YOLO detection results for testing"""
    return [
        {"label": "person", "confidence": 0.92, "bbox_x": 0.5, "bbox_y": 0.3,
         "bbox_w": 0.2, "bbox_h": 0.4, "class_id": 0},
        {"label": "car", "confidence": 0.85, "bbox_x": 0.7, "bbox_y": 0.6,
         "bbox_w": 0.3, "bbox_h": 0.2, "class_id": 2},
        {"label": "dog", "confidence": 0.78, "bbox_x": 0.3, "bbox_y": 0.5,
         "bbox_w": 0.15, "bbox_h": 0.2, "class_id": 16},
        {"label": "person", "confidence": 0.65, "bbox_x": 0.8, "bbox_y": 0.4,
         "bbox_w": 0.18, "bbox_h": 0.35, "class_id": 0},
    ]


@pytest.fixture
def sample_uuid():
    return str(uuid.uuid4())


@pytest.fixture
def mock_query(mock_db):
    """Helper: create a mock query chain (query.filter.filter...all/ first)"""
    q = MagicMock()
    mock_db.query.return_value = q
    return q


@pytest.fixture
def mock_file(tmp_path):
    """Create a temporary test file"""
    p = tmp_path / "test_photo.jpg"
    img = Image.new("RGB", (100, 100))
    img.save(str(p), "JPEG")
    return str(p)
