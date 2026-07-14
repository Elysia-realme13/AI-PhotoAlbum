"""
Tests for name_confirmation_service.py (with mocked DB)
"""
import uuid
import pytest
from unittest.mock import MagicMock, patch
from app.services.name_confirmation_service import (
    create_pending, get_pending, clear_pending,
    confirm_name, find_clusters_by_name,
)


class TestPendingManagement:
    def test_create_and_get(self):
        session_id = "test_user"
        query = "帮我找爸爸的照片"
        candidates = [{"cluster_id": str(uuid.uuid4()), "face_count": 5}]

        create_pending(session_id, query, candidates)
        pending = get_pending(session_id, query)
        assert pending is not None
        assert pending["status"] == "pending"
        assert len(pending["candidates"]) == 1

    def test_get_nonexistent(self):
        assert get_pending("no_such", "no query") is None

    def test_clear(self):
        session_id = "user_clear"
        query = "test"
        create_pending(session_id, query, [{"cluster_id": str(uuid.uuid4())}])
        clear_pending(session_id, query)
        assert get_pending(session_id, query) is None


class TestConfirmName:
    def test_no_pending(self, mock_db):
        result = confirm_name(mock_db, "nosession", "noquery",
                              str(uuid.uuid4()), "爸爸")
        assert result is False

    def test_success_flow(self, mock_db):
        from app.models.face import FaceIdentity, Face
        cid = str(uuid.uuid4())

        # Create pending first
        create_pending("user1", "where is dad", [{"cluster_id": cid}])

        # Mock DB returns
        mock_identity = MagicMock(spec=FaceIdentity)
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_identity]

        # Mock face query
        mock_face = MagicMock(spec=Face)
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_face]

        result = confirm_name(mock_db, "user1", "where is dad", cid, "爸爸", ["老爸"])
        assert result is True
        assert mock_identity.identity_name == "爸爸"


class TestFindClustersByName:
    def test_no_match(self, mock_db, mock_query):
        mock_query.filter.return_value.all.return_value = []
        result = find_clusters_by_name(mock_db, uuid.uuid4(), "爸爸")
        assert result == []
