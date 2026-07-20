"""
Tests for app.tasks.dispatcher — 任务分发器

沿用本目录 MagicMock DB 约定（模型使用 PG UUID/pgvector，不建真实 SQLite 表）。
通过 patch update_task_status / _get_photo / 底层服务，验证状态流转与领取范围。
"""
import uuid
from unittest.mock import MagicMock, patch

from app.models.task import Task, TaskStatus, TaskType
from app.tasks import dispatcher


def _make_task(task_type: TaskType) -> Task:
    t = Task(task_type=task_type, status=TaskStatus.pending, photo_id=uuid.uuid4())
    t.id = uuid.uuid4()
    return t


def _fake_update(db, task, status, result=None, error_message=None):
    """就地改写任务状态，模拟 crud.update_task_status"""
    task.status = status
    if result is not None:
        task.result = result
    if error_message is not None:
        task.error_message = error_message
    return task


def _db_returning(tasks):
    """构造 MagicMock DB，使任务查询链返回给定列表"""
    db = MagicMock()
    chain = db.query.return_value.filter.return_value.order_by.return_value.limit.return_value
    chain.all.return_value = tasks
    return db


class TestHandledTypes:
    def test_capable_and_placeholder_types_registered(self):
        """已具备能力的类型 + 占位类型均已注册"""
        keys = set(dispatcher.TASK_HANDLERS.keys())
        assert keys == {
            TaskType.object_detection,
            TaskType.image_embedding,
            TaskType.exif_extract,
            TaskType.geocode,
            TaskType.face_detect,
            TaskType.image_description,
            TaskType.quality_assessment,
        }

    def test_placeholder_types_exposed(self):
        """占位类型集合与未接入模型的三类任务一致"""
        assert dispatcher.PLACEHOLDER_TASK_TYPES == {
            TaskType.face_detect,
            TaskType.image_description,
            TaskType.quality_assessment,
        }


class TestRunPendingTasks:
    def test_all_handlers_complete(self):
        tasks = [
            _make_task(TaskType.object_detection),
            _make_task(TaskType.image_embedding),
            _make_task(TaskType.exif_extract),
        ]
        db = _db_returning(tasks)
        photo = MagicMock()
        photo.id = uuid.uuid4()
        photo.file_path = "x.jpg"
        photo.metadata_info = None

        with patch.object(dispatcher, "update_task_status", side_effect=_fake_update), \
             patch.object(dispatcher, "_get_photo", return_value=photo), \
             patch("app.services.tag_service.generate_tags_for_photo",
                   return_value=MagicMock(tags=["person", "car"])), \
             patch("app.services.photo_vector_service.has_vector", return_value=False), \
             patch("app.services.photo_vector_service.generate_photo_vector",
                   return_value=object()), \
             patch("app.services.exif_service.extract_exif",
                   return_value={"camera_make": "X", "width": 100}), \
             patch("app.crud.photo.create_photo_metadata"), \
             patch("app.crud.photo.update_processed_tasks"):
            stats = dispatcher.run_pending_tasks(db, limit=10)

        assert stats == {"completed": 3, "failed": 0, "total": 3}
        assert all(t.status == TaskStatus.completed for t in tasks)
        assert tasks[0].result == {"labels": ["person", "car"], "count": 2}
        assert tasks[1].result == {"vector": True}
        assert tasks[2].result == {"applied": True}

    def test_handler_exception_marks_failed(self):
        good = _make_task(TaskType.object_detection)
        bad = _make_task(TaskType.object_detection)
        db = _db_returning([good, bad])
        photo = MagicMock()

        with patch.object(dispatcher, "update_task_status", side_effect=_fake_update), \
             patch.object(dispatcher, "_get_photo", return_value=photo), \
             patch("app.services.tag_service.generate_tags_for_photo",
                   side_effect=[MagicMock(tags=["dog"]), RuntimeError("boom")]):
            stats = dispatcher.run_pending_tasks(db, limit=10)

        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert good.status == TaskStatus.completed
        assert bad.status == TaskStatus.failed
        assert bad.error_message == "boom"

    def test_no_pending_returns_zero(self):
        db = _db_returning([])
        stats = dispatcher.run_pending_tasks(db, limit=10)
        assert stats == {"completed": 0, "failed": 0, "total": 0}


class TestPlaceholderHandlers:
    def test_placeholder_tasks_complete_as_skipped(self):
        """占位任务被领取后置 completed，result 标注 skipped/未接入"""
        tasks = [
            _make_task(TaskType.face_detect),
            _make_task(TaskType.image_description),
            _make_task(TaskType.quality_assessment),
        ]
        db = _db_returning(tasks)

        with patch.object(dispatcher, "update_task_status", side_effect=_fake_update):
            stats = dispatcher.run_pending_tasks(db, limit=10)

        assert stats == {"completed": 3, "failed": 0, "total": 3}
        assert all(t.status == TaskStatus.completed for t in tasks)
        for t in tasks:
            assert t.result["skipped"] is True
            assert t.result["reason"]

    def test_placeholder_reason_matches_task_type(self):
        task = _make_task(TaskType.image_description)
        handler = dispatcher.TASK_HANDLERS[TaskType.image_description]
        result = handler(MagicMock(), task)
        assert result == {
            "skipped": True,
            "reason": dispatcher._PLACEHOLDER_REASONS[TaskType.image_description],
        }


class TestGeocodeHandler:
    def test_geocode_applies_result(self):
        task = _make_task(TaskType.geocode)
        db = MagicMock()
        photo = MagicMock()
        photo.id = uuid.uuid4()
        photo.metadata_info = MagicMock(latitude=30.2, longitude=120.1, city=None)

        with patch.object(dispatcher, "_get_photo", return_value=photo), \
             patch("app.services.geocode_service.reverse_geocode",
                   return_value={"province": "浙江省", "city": "杭州市"}), \
             patch("app.crud.photo.create_photo_metadata") as mock_create, \
             patch("app.crud.photo.update_processed_tasks"):
            result = dispatcher._handle_geocode(db, task)

        assert result == {"applied": True, "city": "杭州市"}
        mock_create.assert_called_once()

    def test_geocode_skips_without_gps(self):
        task = _make_task(TaskType.geocode)
        photo = MagicMock()
        photo.metadata_info = None

        with patch.object(dispatcher, "_get_photo", return_value=photo), \
             patch("app.crud.photo.update_processed_tasks"):
            result = dispatcher._handle_geocode(MagicMock(), task)

        assert result == {"applied": False, "reason": "no_gps"}

    def test_geocode_skips_when_city_present(self):
        task = _make_task(TaskType.geocode)
        photo = MagicMock()
        photo.metadata_info = MagicMock(latitude=30.2, longitude=120.1, city="杭州市")

        with patch.object(dispatcher, "_get_photo", return_value=photo):
            result = dispatcher._handle_geocode(MagicMock(), task)

        assert result == {"applied": False, "reason": "already"}
