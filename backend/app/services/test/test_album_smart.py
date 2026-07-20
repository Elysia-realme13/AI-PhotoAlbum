"""
Tests for app.services.album_service.build_smart_filters — 智能相册条件解析

纯函数单测：验证不同 conditions 组合产生的过滤项数量与容错，不依赖真实 DB。
"""
import uuid

from app.services.album_service import build_smart_filters


def test_empty_conditions_no_filters():
    assert build_smart_filters(None) == []
    assert build_smart_filters({}) == []


def test_date_range_produces_two_filters():
    filters = build_smart_filters({"date_from": "2024-01-01", "date_to": "2024-12-31"})
    assert len(filters) == 2


def test_only_tags_produces_one_filter():
    filters = build_smart_filters({"tags": ["cat", "dog"]})
    assert len(filters) == 1


def test_all_condition_types_produce_six_filters():
    filters = build_smart_filters({
        "date_from": "2024-01-01",
        "date_to": "2024-12-31",
        "province": "浙江省",
        "city": "杭州市",
        "tags": ["cat"],
        "face_identity_id": str(uuid.uuid4()),
    })
    assert len(filters) == 6


def test_invalid_date_ignored():
    assert build_smart_filters({"date_from": "not-a-date"}) == []


def test_empty_tags_ignored():
    assert build_smart_filters({"tags": []}) == []
