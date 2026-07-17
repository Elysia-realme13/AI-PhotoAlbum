"""
Tests for thumbnail.py
"""
import io

from PIL import Image

from app.config.settings import settings
from app.services.thumbnail import (
    generate_thumbnail_bytes,
    get_image_dimensions,
    get_image_dimensions_from_bytes,
    optimize_image_bytes,
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


class TestOptimizeImage:
    def _jpeg(self, w: int, h: int, exif_bytes: bytes | None = None) -> bytes:
        img = Image.new("RGB", (w, h), (120, 80, 40))
        buf = io.BytesIO()
        if exif_bytes:
            img.save(buf, format="JPEG", quality=95, exif=exif_bytes)
        else:
            img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    def test_large_image_downscaled(self):
        """最长边超限时应缩到 <= MAX_IMAGE_LONG_EDGE"""
        long_edge = settings.MAX_IMAGE_LONG_EDGE
        data = self._jpeg(long_edge * 2, long_edge, )
        out, w, h = optimize_image_bytes(data)
        assert max(w, h) <= long_edge
        img = Image.open(io.BytesIO(out))
        assert max(img.size) <= long_edge
        assert img.format == "JPEG"

    def test_small_image_not_upscaled(self):
        """小图不放大，尺寸保持"""
        data = self._jpeg(100, 100)
        out, w, h = optimize_image_bytes(data)
        assert (w, h) == (100, 100)

    def test_exif_preserved(self):
        """重编码后 EXIF 应完整保留"""
        exif = Image.Exif()
        exif[0x010F] = "TestMake"  # Make
        data = self._jpeg(3000, 2000, exif.tobytes())
        out, _w, _h = optimize_image_bytes(data)
        img = Image.open(io.BytesIO(out))
        assert img.getexif().get(0x010F) == "TestMake"

    def test_gif_skipped(self):
        """GIF（可能为动图）不处理，原样返回"""
        img = Image.new("P", (200, 200))
        buf = io.BytesIO()
        img.save(buf, format="GIF")
        raw = buf.getvalue()
        out, w, h = optimize_image_bytes(raw)
        assert out == raw
        assert (w, h) == (200, 200)
