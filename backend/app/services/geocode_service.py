"""
反向地理编码服务 — 基于在线 Nominatim (OpenStreetMap)

把 GPS 经纬度解析为行政区划 (country/province/city/district) 与详细地址。

设计:
    - 免费公共端点，无需 API Key。遵守 Nominatim 使用策略：
      有效 User-Agent + ≤1 req/s（GEOCODING_MIN_INTERVAL 限流）。
    - 模块级内存缓存：key 为经纬度四舍五入到 3 位小数（约 100m），
      同一地点重复请求直接命中缓存，既省流量也避免触发限流。
    - 任何网络/解析异常都返回 {}（由调用方决定如何处理），不抛出。

生产环境可将 settings.NOMINATIM_URL 指向自建 Nominatim 实例以摆脱公共限流。
"""

import logging
import threading
import time
from typing import Dict, Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger("app.services.geocode")

# 经纬度 -> 解析结果 缓存
_cache: Dict[str, dict] = {}
# 限流：保证相邻请求间隔 >= GEOCODING_MIN_INTERVAL
_rate_lock = threading.Lock()
_last_call: float = 0.0

# Nominatim address 字段 -> PhotoMetadata 列 的候选映射（按优先级取第一个非空）
_CITY_KEYS = ("city", "town", "county", "municipality")
_DISTRICT_KEYS = ("city_district", "district", "suburb", "borough")


def _cache_key(lat: float, lon: float) -> str:
    return f"{round(lat, 3)},{round(lon, 3)}"


def _rate_limit() -> None:
    """阻塞直到距上次请求已达最小间隔"""
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
    """把 Nominatim jsonv2 响应解析为 PhotoMetadata 字段"""
    address = data.get("address") or {}
    result = {
        "country": address.get("country"),
        "province": address.get("state") or address.get("region"),
        "city": _pick(address, _CITY_KEYS),
        "district": _pick(address, _DISTRICT_KEYS),
        "address": data.get("display_name"),
    }
    # 去除 None，仅保留有值字段
    return {k: v for k, v in result.items() if v}


def reverse_geocode(lat: float, lon: float) -> dict:
    """
    反向地理编码：GPS -> {country, province, city, district, address}

    失败或无结果返回 {}。命中缓存则不触发网络请求与限流。
    """
    if lat is None or lon is None:
        return {}

    key = _cache_key(lat, lon)
    if key in _cache:
        return _cache[key]

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
        parsed = _parse(resp.json())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"反向地理编码失败 ({lat}, {lon}): {e}")
        return {}

    _cache[key] = parsed
    return parsed


__all__ = ["reverse_geocode"]
