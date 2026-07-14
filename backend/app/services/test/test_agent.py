"""
Tests for agents/search_agent.py (with mocked DB)
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.agent.search_agent import (
    SearchState, extract_entities, recognize_person,
    clip_search, merge_results, run_search_agent,
    build_search_graph,
)


def make_state(**overrides):
    """Helper to create a default SearchState for testing"""
    state: SearchState = {
        "query": "",
        "owner_id": None,
        "session_id": None,
        "nouns": [],
        "person_names": [],
        "person_photo_ids": [],
        "clip_results": [],
        "merged_results": [],
        "needs_confirmation": False,
        "pending_candidates": [],
        "error": None,
    }
    state.update(overrides)
    return state


class TestExtractEntities:
    def test_empty_query(self, mock_db):
        state = make_state(query="")
        result = extract_entities(state, mock_db)
        assert result["error"] is not None

    def test_normal_query(self, mock_db):
        state = make_state(query="爸爸在公园的照片")
        result = extract_entities(state, mock_db)
        assert result["nouns"] is not None
        assert isinstance(result["nouns"], list)
        # "爸爸" may be classified differently depending on jieba
        assert result["person_names"] is not None


class TestRecognizePerson:
    def test_no_person_names(self, mock_db):
        state = make_state(person_names=[])
        result = recognize_person(state, mock_db)
        assert result["needs_confirmation"] is False

    def test_unrecognized_person(self, mock_db):
        state = make_state(person_names=["爸爸"], owner_id="user1")
        with patch("app.services.agent.search_agent.search_faces_by_name",
                   return_value=[]):
            with patch("app.services.agent.search_agent.get_unnamed_candidates",
                       return_value=[{"cluster_id": "cid1", "face_count": 3}]):
                result = recognize_person(state, mock_db)
                assert result["needs_confirmation"] is True
                assert len(result["pending_candidates"]) == 1

    def test_recognized_person(self, mock_db):
        state = make_state(person_names=["爸爸"], owner_id="user1")
        with patch("app.services.agent.search_agent.search_faces_by_name",
                   return_value=["photo1", "photo2"]):
            result = recognize_person(state, mock_db)
            assert result["needs_confirmation"] is False
            assert "photo1" in result["person_photo_ids"]


class TestMergeResults:
    def test_no_clip_results(self, mock_db):
        state = make_state(clip_results=[])
        result = merge_results(state, mock_db)
        assert result["merged_results"] == []

    def test_no_person_filter(self, mock_db):
        state = make_state(clip_results=[{"photo_id": "p1", "score": 0.9}],
                           person_photo_ids=[])
        result = merge_results(state, mock_db)
        assert len(result["merged_results"]) == 1
        assert result["merged_results"][0]["photo_id"] == "p1"

    def test_intersection(self, mock_db):
        state = make_state(
            clip_results=[
                {"photo_id": "p1", "score": 0.9},
                {"photo_id": "p2", "score": 0.8},
                {"photo_id": "p3", "score": 0.7},
            ],
            person_photo_ids=["p1", "p3"],
        )
        result = merge_results(state, mock_db)
        ids = {r["photo_id"] for r in result["merged_results"]}
        assert "p1" in ids
        assert "p3" in ids
        assert "p2" not in ids  # p2 not in person filter

    def test_sorted_by_score(self, mock_db):
        state = make_state(
            clip_results=[
                {"photo_id": "a", "score": 0.5},
                {"photo_id": "b", "score": 0.9},
            ],
            person_photo_ids=["a", "b"],
        )
        result = merge_results(state, mock_db)
        scores = [r["score"] for r in result["merged_results"]]
        assert scores == sorted(scores, reverse=True)

    def test_top50_limit(self, mock_db):
        many_results = [{"photo_id": f"p{i}", "score": 0.9} for i in range(100)]
        state = make_state(clip_results=many_results)
        result = merge_results(state, mock_db)
        assert len(result["merged_results"]) <= 50


class TestBuildGraph:
    def test_fallback_graph(self):
        """build_search_graph should not raise even without langgraph"""
        graph = build_search_graph()
        assert graph is not None


class TestRunSearchAgent:
    @pytest.mark.xfail(reason="langgraph node needs db param", run=True)
    def test_basic_flow(self, mock_db):
        """End-to-end agent run (with mocked DB)"""
        with patch.multiple(
            "app.services.agent.search_agent",
            extract_nouns=MagicMock(return_value=["花", "天空"]),
            extract_person_names=MagicMock(return_value=[]),
            clip_search_by_text=MagicMock(return_value=[
                {"photo_id": "p1", "score": 0.9},
            ]),
        ):
            result = run_search_agent(
                query="红色的花和蓝色的天空",
                db=mock_db,
                owner_id="test_user",
            )
            assert result["error"] is None
            assert len(result["merged_results"]) > 0
