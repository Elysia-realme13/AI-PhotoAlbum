"""
Tests for exif_service.py
"""
import pytest
from app.services.exif_service import extract_exif


class TestExtractEXIF:
    def test_non_image_file(self, tmp_path):
        """Non-image file should return defaults without raising"""
        p = tmp_path / "test.txt"
        p.write_text("not an image")
        result = extract_exif(str(p))
        assert result["width"] is None
        assert result["height"] is None

    def test_basic_jpeg(self, synthetic_image, tmp_path):
        """Plain JPEG without EXIF should return basic dimensions"""
        p = tmp_path / "plain.jpg"
        p.write_bytes(synthetic_image)
        result = extract_exif(str(p))
        assert result["width"] == 100
        assert result["height"] == 100

    def test_exif_data(self, synthetic_image_with_exif, tmp_path):
        """JPEG with EXIF should extract metadata"""
        p = tmp_path / "exif.jpg"
        p.write_bytes(synthetic_image_with_exif)
        result = extract_exif(str(p))
        assert result["width"] == 200
        assert result["height"] == 150
        assert result["camera_make"] == "TestCamera"
        assert result["camera_model"] == "TestModel X100"

    def test_nonexistent_file(self):
        """Non-existent file should return defaults"""
        result = extract_exif("/nonexistent/file.jpg")
        assert result["width"] is None
        assert result["height"] is None

    def test_result_structure(self, synthetic_image, tmp_path):
        """Result dict should have all expected keys"""
        p = tmp_path / "test.jpg"
        p.write_bytes(synthetic_image)
        result = extract_exif(str(p))
        expected_keys = {"width", "height", "photo_time", "camera_make",
                         "camera_model", "lens_model", "focal_length",
                         "aperture", "shutter_speed", "iso",
                         "latitude", "longitude", "altitude"}
        assert expected_keys.issubset(result.keys())
