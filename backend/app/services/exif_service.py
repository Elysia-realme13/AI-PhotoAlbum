"""
EXIF 元数据提取服务
使用 Pillow 提取照片的拍摄时间、GPS 坐标、相机参数等信息
"""
from datetime import datetime
from pathlib import Path
from typing import Optional
from PIL import Image
from PIL.ExifTags import GPSTAGS

# 注册 HEIC/HEIF 支持
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


def _convert_gps_to_decimal(gps_info: dict) -> Optional[tuple[float, float]]:
    """
    将 EXIF GPS 信息转换为十进制度数

    Args:
        gps_info: EXIF GPS IFD 字典

    Returns:
        (latitude, longitude) 或 None
    """
    try:
        def _to_degrees(value) -> float:
            """将 EXIF 中的有理数元组转为度数"""
            if isinstance(value, tuple) and len(value) == 2:
                num, den = value
                return float(num) / float(den) if den != 0 else 0.0
            return float(value)

        lat = _to_degrees(gps_info[2][0]) + _to_degrees(gps_info[2][1]) / 60.0 + _to_degrees(gps_info[2][2]) / 3600.0
        lon = _to_degrees(gps_info[4][0]) + _to_degrees(gps_info[4][1]) / 60.0 + _to_degrees(gps_info[4][2]) / 3600.0

        # 南纬 / 西经为负
        if gps_info.get(1) == 'S':
            lat = -lat
        if gps_info.get(3) == 'W':
            lon = -lon

        return (round(lat, 6), round(lon, 6))
    except (KeyError, IndexError, TypeError, ZeroDivisionError):
        return None


def _parse_exif_datetime(value) -> Optional[datetime]:
    """
    解析 EXIF 日期时间字符串

    Args:
        value: EXIF 日期时间值

    Returns:
        datetime 对象或 None
    """
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), '%Y:%m:%d %H:%M:%S')
    except (ValueError, TypeError):
        return None


def extract_exif(file_path: str) -> dict:
    """
    从图片文件提取 EXIF 信息

    Args:
        file_path: 图片文件路径

    Returns:
        包含 EXIF 信息的字典:
        {
            'width': int,
            'height': int,
            'photo_time': datetime | None,
            'camera_make': str | None,
            'camera_model': str | None,
            'lens_model': str | None,
            'focal_length': float | None,
            'aperture': float | None,
            'shutter_speed': str | None,
            'iso': int | None,
            'latitude': float | None,
            'longitude': float | None,
            'altitude': float | None,
        }
    """
    result = {
        'width': None,
        'height': None,
        'photo_time': None,
        'camera_make': None,
        'camera_model': None,
        'lens_model': None,
        'focal_length': None,
        'aperture': None,
        'shutter_speed': None,
        'iso': None,
        'latitude': None,
        'longitude': None,
        'altitude': None,
    }

    try:
        img = Image.open(file_path)
        result['width'] = img.width
        result['height'] = img.height

        exif = img.getexif()
        if not exif:
            return result

        # ── 拍摄时间 ──────────────────────────────
        # 0x9003 = DateTimeOriginal
        date_original = exif.get(0x9003)
        if date_original:
            result['photo_time'] = _parse_exif_datetime(date_original)

        # 0x0132 = ModifyDate (fallback)
        if not result['photo_time']:
            modify_date = exif.get(0x0132)
            if modify_date:
                result['photo_time'] = _parse_exif_datetime(modify_date)

        # ── 相机制造商 / 型号 ─────────────────────
        # 0x010F = Make, 0x0110 = Model
        make = exif.get(0x010F)
        model = exif.get(0x0110)
        if make:
            result['camera_make'] = str(make).strip('\x00').strip()
        if model:
            result['camera_model'] = str(model).strip('\x00').strip()

        # ── Exif IFD: 拍摄参数 ───────────────────
        # 0x8769 = ExifOffset
        exif_ifd = exif.get_ifd(0x8769)
        if exif_ifd:
            # 焦距 (0x920A = FocalLength)
            focal = exif_ifd.get(0x920A)
            if focal and isinstance(focal, tuple) and len(focal) == 2 and focal[1] != 0:
                result['focal_length'] = round(float(focal[0]) / float(focal[1]), 1)

            # 光圈 (0x829D = FNumber)
            fnumber = exif_ifd.get(0x829D)
            if fnumber and isinstance(fnumber, tuple) and len(fnumber) == 2 and fnumber[1] != 0:
                result['aperture'] = round(float(fnumber[0]) / float(fnumber[1]), 1)

            # 快门速度 (0x829A = ExposureTime)
            exposure = exif_ifd.get(0x829A)
            if exposure and isinstance(exposure, tuple) and len(exposure) == 2:
                if exposure[1] != 0:
                    result['shutter_speed'] = f"{exposure[0]}/{exposure[1]}"

            # ISO (0x8827 = ISOSpeedRatings)
            iso = exif_ifd.get(0x8827)
            if iso is not None:
                try:
                    result['iso'] = int(iso)
                except (ValueError, TypeError):
                    pass

            # 镜头型号 (0xA434 = LensModel)
            lens = exif_ifd.get(0xA434)
            if lens:
                result['lens_model'] = str(lens).strip('\x00').strip()

        # ── GPS IFD: 位置信息 ────────────────────
        # 0x8825 = GPSInfo
        gps_ifd = exif.get_ifd(0x8825)
        if gps_ifd and 2 in gps_ifd and 4 in gps_ifd:
            coords = _convert_gps_to_decimal(gps_ifd)
            if coords:
                result['latitude'] = coords[0]
                result['longitude'] = coords[1]

            # 海拔 (0x0006 = GPSAltitude)
            altitude = gps_ifd.get(6)
            if altitude and isinstance(altitude, tuple) and len(altitude) == 2 and altitude[1] != 0:
                result['altitude'] = round(float(altitude[0]) / float(altitude[1]), 1)

    except Exception:
        # 非图片文件或损坏的图片，返回默认值
        pass

    return result
