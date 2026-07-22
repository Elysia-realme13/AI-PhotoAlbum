"""
反向地理编码服务 — 离线行政区边界优先，在线 Nominatim 回退

把 GPS 经纬度解析为行政区划 (country/province/city/district) 与详细地址。

设计:
    - **离线优先**：加载 data/geo/china_city.geojson（阿里 DataV 市级行政区边界），
      用「bbox 预筛 + 射线法」做点在多边形内判断，返回中文省/市名。
      无外部依赖、无网络请求、毫秒级，天然规避公共 Nominatim 国内不可达问题。
    - **在线回退**：离线未命中（境外坐标或数据缺失）时，回退到 Nominatim
      (settings.NOMINATIM_URL)，遵守其使用策略（有效 UA + ≤1 req/s 限流）。
    - **模块级内存缓存**：key 为经纬度四舍五入到 3 位小数（约 100m），
      同一地点重复请求直接命中缓存。
    - 任何异常都返回 {}（由调用方决定如何处理），不抛出。

离线边界数据由 scripts/build_china_geojson.py 生成，随仓库分发。
坐标系：EXIF GPS 与 DataV 边界均按 WGS-84 处理，市级包含判断误差可忽略。
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger("app.services.geocode")

# 经纬度 -> 解析结果 缓存
_cache: Dict[str, dict] = {}
# 限流：保证相邻请求间隔 >= GEOCODING_MIN_INTERVAL（仅用于在线回退）
_rate_lock = threading.Lock()
_last_call: float = 0.0

# 离线行政区边界（懒加载）：list[{province, city, bbox, polys}]
_regions: Optional[List[dict]] = None
_regions_lock = threading.Lock()

# Nominatim address 字段 -> PhotoMetadata 列 的候选映射（按优先级取第一个非空）
_CITY_KEYS = ("city", "town", "county", "municipality")
_DISTRICT_KEYS = ("city_district", "district", "suburb", "borough")


def _cache_key(lat: float, lon: float) -> str:
    return f"{round(lat, 3)},{round(lon, 3)}"


# ─────────────────────────── 离线边界查询 ───────────────────────────


def _extract_outer_rings(geom: dict) -> List[list]:
    """从 Polygon / MultiPolygon 提取各面的外环（忽略内环/孔洞）。"""
    t = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        return []
    if t == "Polygon":
        return [coords[0]]
    if t == "MultiPolygon":
        return [poly[0] for poly in coords if poly]
    return []


def _load_regions() -> List[dict]:
    """懒加载离线行政区边界并预计算 bbox。失败/缺失返回空列表。"""
    global _regions
    if _regions is not None:
        return _regions
    with _regions_lock:
        if _regions is not None:
            return _regions
        regions: List[dict] = []
        path = Path(settings.GEO_BOUNDARY_FILE)
        if path.is_file():
            try:
                with open(path, encoding="utf-8") as f:
                    fc = json.load(f)
                for feat in fc.get("features", []):
                    props = feat.get("properties", {})
                    polys = _extract_outer_rings(feat.get("geometry", {}))
                    if not polys:
                        continue
                    xs = [pt[0] for ring in polys for pt in ring]
                    ys = [pt[1] for ring in polys for pt in ring]
                    regions.append(
                        {
                            "province": props.get("province"),
                            "city": props.get("city"),
                            "bbox": (min(xs), min(ys), max(xs), max(ys)),
                            "polys": polys,
                        }
                    )
                logger.info(f"离线行政区边界加载完成：{len(regions)} 个市级面")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"离线行政区边界加载失败：{e}")
                regions = []
        else:
            logger.warning(f"离线行政区边界文件不存在：{path}，将回退在线 Nominatim")
        _regions = regions
        return _regions


def _point_in_ring(x: float, y: float, ring: list) -> bool:
    """射线法：判断点 (x=lon, y=lat) 是否落在多边形环内。"""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _offline_lookup(lat: float, lon: float) -> dict:
    """离线边界反查：命中返回 {country, province, city, address}，未命中返回 {}。"""
    regions = _load_regions()
    if not regions:
        return {}
    for r in regions:
        minx, miny, maxx, maxy = r["bbox"]
        if lon < minx or lon > maxx or lat < miny or lat > maxy:
            continue
        for ring in r["polys"]:
            if _point_in_ring(lon, lat, ring):
                province, city = r["province"], r["city"]
                parts = [p for p in ("中国", province, city) if p]
                return {
                    "country": "中国",
                    "province": province,
                    "city": city,
                    "address": " ".join(parts),
                }
    return {}


# ─────────────────────────── 在线 Nominatim 回退 ───────────────────────────


def _rate_limit() -> None:
    """阻塞直到距上次请求已达最小间隔。"""
    global _last_call
    with _rate_lock:
        wait = settings.GEOCODING_MIN_INTERVAL - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _pick(address: dict, keys: tuple) -> Optional[str]:
    for k in keys:
        val = address.get(k)
        if val:
            return val
    return None


def _parse(data: dict) -> dict:
    """把 Nominatim jsonv2 响应解析为 PhotoMetadata 字段。"""
    address = data.get("address") or {}
    result = {
        "country": address.get("country"),
        "province": address.get("state") or address.get("region"),
        "city": _pick(address, _CITY_KEYS),
        "district": _pick(address, _DISTRICT_KEYS),
        "address": data.get("display_name"),
    }
    return {k: v for k, v in result.items() if v}


def _nominatim_lookup(lat: float, lon: float) -> dict:
    """在线 Nominatim 反查。失败或无结果返回 {}。"""
    _rate_limit()
    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 10,
        "accept-language": settings.GEOCODING_LANG,
    }
    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}
    try:
        resp = httpx.get(settings.NOMINATIM_URL, params=params, headers=headers, timeout=10.0)
        resp.raise_for_status()
        return _parse(resp.json())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"在线反向地理编码失败 ({lat}, {lon}): {e}")
        return {}


def reverse_geocode(lat: float, lon: float) -> dict:
    """
    反向地理编码：GPS -> {country, province, city, district?, address}

    离线边界优先；未命中（境外坐标或离线数据缺失）时回退在线 Nominatim。
    失败或无结果返回 {}。命中缓存则不触发任何查询。
    """
    if lat is None or lon is None:
        return {}

    key = _cache_key(lat, lon)
    if key in _cache:
        return _cache[key]

    result = _offline_lookup(lat, lon)
    if not result:
        result = _nominatim_lookup(lat, lon)

    _cache[key] = result
    return result


__all__ = ["reverse_geocode"]
