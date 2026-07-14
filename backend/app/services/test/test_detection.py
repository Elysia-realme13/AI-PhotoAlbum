"""
Tests for detection_service.py
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.detection_service import (
    COCO_CLASSES, get_detection_summary, draw_detections,
    detect_objects, DEFAULT_MODEL,
)


class TestCOCOClasses:
    def test_length(self):
        """COCO must have exactly 80 classes"""
        assert len(COCO_CLASSES) == 80

    def test_contains_common(self):
        """Known COCO classes"""
        assert "person" in COCO_CLASSES
        assert "car" in COCO_CLASSES
        assert "dog" in COCO_CLASSES
        assert "cat" in COCO_CLASSES

    def test_indices(self):
        """Known class indices"""
        assert COCO_CLASSES[0] == "person"
        assert COCO_CLASSES[2] == "car"


class TestDetectionSummary:
    def test_empty(self):
        assert get_detection_summary([]) == []

    def test_single_category(self, sample_detections):
        summary = get_detection_summary(sample_detections)
        summary_dict = {s["label"]: s for s in summary}
        assert summary_dict["person"]["count"] == 2
        assert summary_dict["person"]["max_confidence"] == 0.92
        assert summary_dict["car"]["count"] == 1

    def test_sorted_by_count(self, sample_detections):
        summary = get_detection_summary(sample_detections)
        counts = [s["count"] for s in summary]
        assert counts == sorted(counts, reverse=True)


class TestDetectObjects:
    def test_file_not_found(self):
        result = detect_objects("/nonexistent/path.jpg")
        assert result["success"] is False
        assert result["error"] is not None
        assert "不存在" in result["error"]

    @patch("app.services.detection_service._get_model")
    def test_model_load_failure(self, mock_get_model, mock_file):
        mock_get_model.return_value = None
        result = detect_objects(mock_file)
        assert result["success"] is False
        assert result["error"] == "YOLO 模型加载失败"

    def test_default_model_name(self):
        assert DEFAULT_MODEL == "yolo26n.pt"


class TestDrawDetections:
    def test_no_detections(self, sample_detections, mock_file, tmp_path):
        out = tmp_path / "out.jpg"
        result = draw_detections(mock_file, [], output_path=str(out))
        assert result is not None  # empty detections = None

    def test_with_detections(self, sample_detections, mock_file, tmp_path):
        out = tmp_path / "out.jpg"
        result = draw_detections(mock_file, sample_detections, output_path=str(out))
        assert result is not None
        # Verify output file exists
        assert (tmp_path / 'out.jpg').exists()


# Note: detect_objects / detect_objects_from_bytes with real model
# require ultralytics installed. The tests above cover error paths.
# Full integration test requires a real YOLO model and image.
