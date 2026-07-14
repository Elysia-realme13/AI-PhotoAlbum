"""
Tests for face_cluster_service.py (with mocked DB)
"""
import uuid
import pytest
from unittest.mock import MagicMock, patch
from app.services.face_cluster_service import (
    cosine_similarity, compute_cluster_center,
    get_representative_faces, get_unamed_clusters,
    DEFAULT_CLUSTER_THRESHOLD,
)


class TestCosineSimilarity:
    def test_identical(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_opposite(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_512_dim(self):
        """Test with realistic 512-dim vectors"""
        import random
        random.seed(42)
        a = [random.random() for _ in range(512)]
        b = [random.random() for _ in range(512)]
        sim = cosine_similarity(a, b)
        assert -1.0 <= sim <= 1.0

    def test_zero_vector(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert cosine_similarity(a, b) == 0.0

    def test_default_threshold(self):
        assert DEFAULT_CLUSTER_THRESHOLD == 0.6


class TestComputeClusterCenter:
    def test_no_faces(self, mock_db, mock_query):
        mock_query.filter.return_value.all.return_value = []
        result = compute_cluster_center(mock_db, uuid.uuid4())
        assert result is None


class TestGetRepresentativeFaces:
    def test_empty_cluster(self, mock_db, mock_query):
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        result = get_representative_faces(mock_db, uuid.uuid4(), top_k=3)
        assert result == []

    def test_with_faces(self, mock_db, mock_query):
        from app.models.face import Face
        face1 = MagicMock(spec=Face)
        face1.id = 1
        face1.photo_id = uuid.uuid4()
        face1.face_rect = [10, 10, 50, 50]
        face1.confidence = 0.95

        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [face1]
        result = get_representative_faces(mock_db, uuid.uuid4(), top_k=3)
        assert len(result) == 1
        assert result[0]["face_id"] == 1
        assert "thumbnail_url" in result[0]


class TestGetUnamedClusters:
    def test_no_identities(self, mock_db, mock_query):
        mock_query.outerjoin.return_value.filter.return_value.group_by.return_value.having.return_value.order_by.return_value.limit.return_value.all.return_value = []
        result = get_unamed_clusters(mock_db, uuid.uuid4(), min_face_count=1)
        assert result == []
