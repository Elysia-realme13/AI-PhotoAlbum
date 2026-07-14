"""
Tests for search_service.py
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.search_service import (
    extract_nouns, extract_person_names, is_person_query,
    search_faces_by_name,
)


class TestExtractNouns:
    def test_simple_nouns(self):
        """Basic noun extraction"""
        nouns = extract_nouns("红色的花和蓝色的天空")
        # Should extract "花" and "天空" (nouns), skip "红色的"/"蓝色的" (adj)
        assert len(nouns) > 0, f"Expected nouns, got {nouns}"
        assert "天空" in nouns or "天" in nouns

    def test_empty_text(self):
        assert extract_nouns("") == []

    def test_only_stopwords(self):
        """Text with only stopwords should return empty or minimal"""
        result = extract_nouns("的 了 是 在")
        assert isinstance(result, list)


class TestExtractPersonNames:
    def test_common_kinship(self):
        names = extract_person_names("爸爸的照片")
        assert "爸爸" in names

    def test_multiple_persons(self):
        names = extract_person_names("妈妈 爸爸")
        assert "妈妈" in names or "爸爸" in names

    def test_no_person(self):
        names = extract_person_names("red flower blue sky")
        assert names == []

    def test_full_family(self):
        text = "爷爷 奶奶 外公 外婆 哥哥 姐姐 弟弟 妹妹"
        names = extract_person_names(text)
        for expected in ["爷爷", "奶奶", "哥哥", "姐姐", "弟弟", "妹妹"]:
            assert expected in names


class TestIsPersonQuery:
    def test_with_person(self):
        assert is_person_query(["花", "天空"], ["爸爸"]) is True

    def test_without_person(self):
        assert is_person_query(["花", "天空"], []) is False


class TestSearchFacesByName:
    def test_no_match(self, mock_db):
        with patch("app.services.name_confirmation_service.find_clusters_by_name",
                   return_value=[]):
            result = search_faces_by_name(mock_db, "爸爸", "user1")
            assert result == []

    def test_with_match(self, mock_db):
        fake_clusters = [{"photo_ids": ["pid1", "pid2"]}]
        with patch("app.services.name_confirmation_service.find_clusters_by_name",
                   return_value=fake_clusters):
            result = search_faces_by_name(mock_db, "爸爸", "user1")
            assert "pid1" in result
            assert "pid2" in result
            assert len(result) == 2
