"""
Tests for app.services.geocode_service — 反向地理编码

patch httpx.get，验证地址字段映射、缓存命中、无坐标/异常兜底。
不发起真实网络请求。
"""
from unittest.mock import MagicMock, patch

import httpx

import app.services.geocode_service as geo


def _resp(json_data: dict) -> MagicMock:
    r = MagicMock()
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    return r


def setup_function(_func):
    """每个用例前清空缓存与限流状态，避免相互影响"""
    geo._cache.clear()
    geo._last_call = 0.0


def test_reverse_geocode_parses_address():
    sample = {
        "display_name": "西湖区, 杭州市, 浙江省, 中国",
        "address": {
            "country": "中国",
            "state": "浙江省",
            "city": "杭州市",
            "city_district": "西湖区",
        },
    }
    with patch("app.services.geocode_service.httpx.get", return_value=_resp(sample)):
        result = geo.reverse_geocode(30.25, 120.15)

    assert result == {
        "country": "中国",
        "province": "浙江省",
        "city": "杭州市",
        "district": "西湖区",
        "address": "西湖区, 杭州市, 浙江省, 中国",
    }


def test_reverse_geocode_city_fallback_to_county():
    sample = {
        "display_name": "某县, 某省, 中国",
        "address": {"country": "中国", "state": "某省", "county": "某县"},
    }
    with patch("app.services.geocode_service.httpx.get", return_value=_resp(sample)):
        result = geo.reverse_geocode(28.0, 118.0)

    assert result["city"] == "某县"
    assert "district" not in result


def test_reverse_geocode_uses_cache():
    sample = {"display_name": "x", "address": {"country": "中国", "state": "省", "city": "市"}}
    with patch("app.services.geocode_service.httpx.get", return_value=_resp(sample)) as mock_get:
        geo.reverse_geocode(31.0, 121.0)
        geo.reverse_geocode(31.0, 121.0)  # 命中缓存
    mock_get.assert_called_once()


def test_reverse_geocode_none_coords_returns_empty():
    assert geo.reverse_geocode(None, None) == {}


def test_reverse_geocode_error_returns_empty():
    with patch("app.services.geocode_service.httpx.get", side_effect=httpx.HTTPError("fail")):
        assert geo.reverse_geocode(1.0, 2.0) == {}
