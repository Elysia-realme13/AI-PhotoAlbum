"""
Tests for thumbnail.py
"""
import io
import pytest
from PIL import Image
from app.services.thumbnail import (
    generate_thumbnail_bytes, get_image_dimensions,
    get_image_dimensions_from_bytes,
)


class TestGenerateThumbnail:
    def test_thumbnail_size(self, synthetic_image):
        thumb = generate_thumbnail_bytes(synthetic_image)
        img = Image.open(io.BytesIO(thumb))
        # Should be within (400, 400) and maintain aspect ratio
        assert img.width <= 400
        assert img.height <= 400

    def test_output_format(self, synthetic_image):
        thumb = generate_thumbnail_bytes(synthetic_image)
        img = Image.open(io.BytesIO(thumb))
        assert img.format == "JPEG"

    def test_rgba_conversion(self):
        """RGBA image should be converted to RGB"""
        img = Image.new("RGBA", (300, 300), (255, 0, 0, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        thumb = generate_thumbnail_bytes(buf.getvalue())
        thumb_img = Image.open(io.BytesIO(thumb))
        assert thumb_img.mode == "RGB"


class TestGetDimensions:
    def test_from_file(self, synthetic_image, tmp_path):
        p = tmp_path / "test.jpg"
        p.write_bytes(synthetic_image)
        w, h = get_image_dimensions(str(p))
        assert w == 100
        assert h == 100

    def test_from_bytes(self, synthetic_image):
        w, h = get_image_dimensions_from_bytes(synthetic_image)
        assert w == 100
        assert h == 100
