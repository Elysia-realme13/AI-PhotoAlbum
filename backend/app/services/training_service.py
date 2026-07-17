"""
训练管理服务层

提供训练任务、数据集、模型管理的完整业务逻辑。
整合数据库操作与 YOLO 训练执行器，提供统一的 API 接口。
"""
import os
import io
import json
import yaml
import uuid
import time
import shutil
import tarfile
import zipfile
import logging
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from app.config.settings import settings
from app.models.training import Dataset, TrainingTask, TrainingMetric
from app.services.trainer import (
    run_training,
    TrainingCallback,
    signal_pause,
    signal_resume,
    signal_stop,
    is_paused as trainer_is_paused,
    is_active as trainer_is_active,
    cleanup_signals,
)

logger = logging.getLogger(__name__)


# ── 目录配置 ─────────────────────────────────────────────────────
TRAINING_DIR = Path(settings.MODELS_DIR) / "training"
DATASETS_DIR = Path(settings.MODELS_DIR) / "datasets"
MODELS_DIR = Path(settings.MODELS_DIR) / "trained"
DATASETS_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ── 全局线程追踪 ────────────────────────────────────────────────
_training_threads: Dict[str, threading.Thread] = {}
_threads_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════
#  Metric Callback
# ══════════════════════════════════════════════════════════════════

class _MetricCallback(TrainingCallback):
    """将训练回调写入数据库"""

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory

    def _get_db(self) -> Session:
        return self.db_session_factory()

    def on_epoch_end(self, task_id: str, epoch: int, metrics: dict):
        """每个 epoch 结束时更新当前轮次"""
        db = self._get_db()
        try:
            task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
            if task:
                task.current_epoch = epoch
                task.updated_at = datetime.now()
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"保存epoch {epoch} 进度失败: {e}")
        finally:
            db.close()

    def on_val_end(self, task_id: str, epoch: int, metrics: dict):
        """验证结束后保存完整指标（包含 mAP50 等）"""
        db = self._get_db()
        try:
            metric_record = TrainingMetric(
                task_id=uuid.UUID(task_id),
                epoch=epoch,
                metrics=metrics,
            )
            db.add(metric_record)

            task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
            if task:
                best = metrics.get("metrics/mAP50", metrics.get("val/mAP50", None))
                if best is not None and (task.best_metric is None or best > task.best_metric):
                    task.best_metric = round(float(best), 6)
                task.updated_at = datetime.now()

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"保存验证指标（epoch {epoch}）失败: {e}")
        finally:
            db.close()

    def on_train_end(self, task_id: str, final_metrics: dict, model_path: str):
        """训练结束处理"""
        db = self._get_db()
        try:
            task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
            if task is None:
                logger.warning(f"训练任务不存在: {task_id}")
                return

            # 如果模型文件存在则复制到 models 目录
            if Path(model_path).exists():
                target_path = MODELS_DIR / f"{task.model_name}.pt"
                shutil.copy2(model_path, str(target_path))
                task.model_path = str(target_path)

                # 导出 ONNX
                try:
                    from ultralytics import YOLO
                    onnx_path = str(target_path.with_suffix(".onnx"))
                    if not Path(onnx_path).exists():
                        model = YOLO(str(target_path))
                        model.export(format="onnx", imgsz=task.config.get("imgsz", 640))
                except Exception as e:
                    logger.warning(f"ONNX 导出失败: {e}")

            # 更新最终状态
            task.status = "completed"
            task.completed_at = datetime.now()
            task.updated_at = datetime.now()

            best = final_metrics.get("metrics/mAP50", final_metrics.get("val/mAP50", None))
            if best is not None:
                task.best_metric = round(float(best), 6)

            db.commit()
            logger.info(f"训练任务完成: {task.task_name}")
        except Exception as e:
            db.rollback()
            logger.error(f"训练结束回调失败: {e}")
        finally:
            db.close()

    def on_log_line(self, task_id: str, line: str):
        """收集日志行"""
        pass


# ══════════════════════════════════════════════════════════════════
#  Dataset Management
# ══════════════════════════════════════════════════════════════════

def upload_dataset(file_bytes: bytes, filename: str, db: Session) -> Dataset:
    """上传并解压数据集压缩包

    支持格式: zip / tar / tar.gz / tgz / tar.bz2 / 7z / rar
    """
    stem = Path(filename).stem
    if filename.lower().endswith(".tar.gz"):
        stem = Path(filename.replace(".tar.gz", "")).name
    elif filename.lower().endswith(".tar.bz2"):
        stem = Path(filename.replace(".tar.bz2", "")).name

    # 检测重复文件名
    existing = db.query(Dataset).filter(Dataset.name == stem).first()
    if existing:
        raise ValueError(f"数据集 '{stem}' 已存在，请勿重复上传")
    dataset_dir = DATASETS_DIR / f"{stem}_{uuid.uuid4().hex[:8]}"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    ext = filename.lower().rsplit(".", 1)[-1]
    if ".tar.gz" in filename.lower() or ".tgz" in filename.lower():
        ext = "tar.gz"
    elif ".tar.bz2" in filename.lower():
        ext = "tar.bz2"

    if ext == "zip":
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            zf.extractall(str(dataset_dir))
    elif ext in ("tar", "tar.gz", "tgz", "tar.bz2"):
        mode = "r:gz" if ext in ("tar.gz", "tgz") else "r:bz2" if ext == "tar.bz2" else "r:"
        with tarfile.open(fileobj=io.BytesIO(file_bytes), mode=mode) as tf:
            tf.extractall(str(dataset_dir))
    elif ext == "7z":
        try:
            import py7zr
            with py7zr.SevenZipFile(io.BytesIO(file_bytes), mode="r") as szf:
                szf.extractall(str(dataset_dir))
        except ImportError:
            raise ValueError("解压 .7z 需要 py7zr 库: pip install py7zr")
    elif ext == "rar":
        try:
            import rarfile
            with rarfile.RarFile(io.BytesIO(file_bytes)) as rf:
                rf.extractall(str(dataset_dir))
        except ImportError:
            raise ValueError("解压 .rar 需要 rarfile 库: pip install rarfile")
    else:
        raise ValueError(f"不支持的格式 .{ext}，支持 zip/tar/tar.gz/tgz/tar.bz2/7z/rar")


    images_dir = dataset_dir / "images"
    labels_dir = dataset_dir / "labels"

    if not images_dir.exists():
        for sub in dataset_dir.iterdir():
            if sub.is_dir() and (sub / "images").exists():
                images_dir = sub / "images"
                labels_dir = sub / "labels"
                break

    image_count = 0
    class_set = set()
    if labels_dir.exists():
        for label_file in labels_dir.rglob("*.txt"):
            if label_file.name == "classes.txt":
                continue
            try:
                with open(label_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            cls_id = int(line.split()[0])
                            class_set.add(cls_id)
            except (ValueError, IndexError):
                continue

    if images_dir.exists():
        image_count = sum(1 for _ in images_dir.rglob("*") if _.suffix.lower() in
                          {".jpg", ".jpeg", ".png", ".bmp", ".webp"})

    class_names = []
    classes_file = dataset_dir / "classes.txt"
    if classes_file.exists():
        with open(classes_file, "r") as f:
            class_names = [line.strip() for line in f if line.strip()]
    else:
        class_names = [f"class_{i}" for i in sorted(class_set)]

    total_size = sum(f.stat().st_size for f in dataset_dir.rglob("*") if f.is_file())

    dataset = Dataset(
        name=stem,
        path=str(dataset_dir),
        image_count=image_count,
        class_names=class_names if class_names else [],
        class_count=len(class_names) or len(class_set),
        file_size=total_size,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    logger.info(f"数据集上传完成: {dataset.name} ({dataset.image_count} 张图片)")
    return dataset


def create_dataset_yaml(dataset: Dataset, val_split: float = 0.2,
                        use_existing_split: bool = False) -> str:
    """为数据集创建 YOLO 格式的 data.yaml 文件"""
    dataset_path = Path(dataset.path)
    images_dir = dataset_path / "images"
    labels_dir = dataset_path / "labels"

    if not images_dir.exists():
        for sub in dataset_path.iterdir():
            if sub.is_dir() and (sub / "images").exists():
                images_dir = sub / "images"
                labels_dir = sub / "labels"
                break

    train_img_dir = images_dir / "train" if (images_dir / "train").exists() else images_dir
    val_img_dir = images_dir / "val" if (images_dir / "val").exists() else None
    train_lbl_dir = labels_dir / "train" if (labels_dir / "train").exists() else labels_dir
    val_lbl_dir = labels_dir / "val" if (labels_dir / "val").exists() else None

    if not use_existing_split and not val_img_dir and val_split > 0:
        import random
        random.seed(42)
        all_images = sorted(train_img_dir.iterdir()) if train_img_dir.exists() else []
        random.shuffle(all_images)
        split_idx = max(1, int(len(all_images) * (1 - val_split)))
        train_images = all_images[:split_idx]
        val_images = all_images[split_idx:]
        val_img_path = images_dir / "val"
        val_lbl_path = labels_dir / "val"
        val_img_path.mkdir(parents=True, exist_ok=True)
        val_lbl_path.mkdir(parents=True, exist_ok=True)
        for img_file in val_images:
            label_file = labels_dir / f"{img_file.stem}.txt"
            if label_file.exists():
                shutil.move(str(label_file), str(val_lbl_path / label_file.name))
            shutil.move(str(img_file), str(val_img_path / img_file.name))
        train_img_dir = images_dir / "train"
        train_lbl_dir = labels_dir / "train"
        train_img_dir.mkdir(parents=True, exist_ok=True)
        train_lbl_dir.mkdir(parents=True, exist_ok=True)
        for img_file in train_images:
            label_file = labels_dir / f"{img_file.stem}.txt"
            if label_file.exists():
                shutil.move(str(label_file), str(train_lbl_dir / label_file.name))
            shutil.move(str(img_file), str(train_img_dir / img_file.name))
        val_img_dir = val_img_path
        val_lbl_dir = val_lbl_path

    class_names = dataset.class_names
    nc = len(class_names) or 1
    data_dict = {"nc": nc, "names": class_names, "train": str(train_img_dir.resolve())}
    if val_img_dir and val_img_dir.exists():
        data_dict["val"] = str(val_img_dir.resolve())

    yaml_path = str(dataset_path / "data.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_dict, f, default_flow_style=False, allow_unicode=True)

    logger.info(f"数据集 YAML 已创建: {yaml_path} (nc={nc})")
    return yaml_path


def get_dataset_preview(dataset_id: str, db: Session) -> Dict[str, Any]:
    """获取数据集预览信息"""
    dataset = db.query(Dataset).filter(Dataset.id == uuid.UUID(dataset_id)).first()
    if not dataset:
        return {"error": "数据集不存在"}
    dataset_path = Path(dataset.path)
    images_dir = dataset_path / "images"
    sample_images = []
    sample_image_urls = []
    if not images_dir.exists():
        for sub in dataset_path.iterdir():
            if sub.is_dir() and (sub / "images").exists():
                images_dir = sub / "images"
                break
    if images_dir.exists():
        search_dirs = [images_dir]
        for sd in images_dir.iterdir():
            if sd.is_dir():
                search_dirs.append(sd)
        for sd in search_dirs:
            for img_file in sorted(sd.iterdir())[:10]:
                if img_file.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                    sample_images.append(str(img_file))
                    rel_path = str(img_file.relative_to(dataset_path))
                    sample_image_urls.append(f"/api/datasets/{dataset_id}/image?path={rel_path}")
    return {
        "id": dataset_id,
        "name": dataset.name,
        "class_names": dataset.class_names,
        "sample_images": sample_images,
        "sample_image_urls": sample_image_urls,
        "image_count": dataset.image_count,
    }


def delete_dataset(dataset_id: str, db: Session) -> bool:
    """删除数据集（包括文件）"""
    dataset = db.query(Dataset).filter(Dataset.id == uuid.UUID(dataset_id)).first()
    if not dataset:
        return False
    task_count = db.query(TrainingTask).filter(
        TrainingTask.dataset_id == uuid.UUID(dataset_id)).count()
    if task_count > 0:
        db.query(TrainingTask).filter(
            TrainingTask.dataset_id == uuid.UUID(dataset_id)
        ).update({"dataset_id": None})
    dataset_path = Path(dataset.path)
    if dataset_path.exists():
        shutil.rmtree(str(dataset_path), ignore_errors=True)
    db.delete(dataset)
    db.commit()
    return True


# ══════════════════════════════════════════════════════════════════
#  Training Task Management
# ══════════════════════════════════════════════════════════════════

def create_task(task_name: str, model_name: str, config: dict, db: Session,
                description: Optional[str] = None,
                dataset_id: Optional[str] = None) -> TrainingTask:
    """创建训练任务"""
    existing = db.query(TrainingTask).filter(TrainingTask.model_name == model_name).first()
    if existing:
        raise ValueError(f"模型名称 '{model_name}' 已被使用")
    task = TrainingTask(
        task_name=task_name,
        model_name=model_name,
        description=description,
        dataset_id=uuid.UUID(dataset_id) if dataset_id else None,
        status="pending",
        config=config,
        total_epochs=config.get("epochs", 100),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info(f"训练任务已创建: {task_name}")
    return task


def create_task_with_dataset(
    task_name: str,
    model_name: str,
    config: dict,
    file_bytes: bytes,
    filename: str,
    db: Session,
    description: Optional[str] = None,
) -> TrainingTask:
    """一键上传数据集并创建训练任务

    与先调用 upload_dataset 再调用 create_task 等效，
    但保证在一次请求中完成，前端无需先切换到“数据集管理”上传。
    """
    dataset = upload_dataset(file_bytes, filename, db)
    task = create_task(
        task_name=task_name,
        model_name=model_name,
        config=config,
        db=db,
        description=description,
        dataset_id=str(dataset.id),
    )
    return task



def start_training(task_id: str, db_factory):
    """异步启动训练任务"""
    db = db_factory()
    try:
        task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
        if not task:
            logger.error(f"训练任务不存在: {task_id}")
            return
        if task.status not in ("pending", "paused", "failed"):
            logger.warning(f"任务状态不允许启动: {task.status}")
            return
        config = task.config or {}
        if task.dataset_id:
            dataset = db.query(Dataset).filter(Dataset.id == task.dataset_id).first()
            if not dataset:
                raise ValueError("关联的数据集不存在")
            dataset_yaml = create_dataset_yaml(
                dataset,
                val_split=config.get("val_split", 0.2),
                use_existing_split=config.get("use_dataset_split", False),
            )
        else:
            raise ValueError("训练任务未关联数据集")
        output_dir = TRAINING_DIR / f"{task.model_name}_{uuid.uuid4().hex[:8]}"
        output_dir.mkdir(parents=True, exist_ok=True)
        task.log_path = str(output_dir / "train.log")
        task.checkpoint_path = str(output_dir / "weights" / "last.pt")
        task.status = "running"
        if not task.started_at:
            task.started_at = datetime.now()
        task.updated_at = datetime.now()
        db.commit()
        callback = _MetricCallback(db_factory)
        checkpoint_path = None
        if task.checkpoint_path and Path(task.checkpoint_path).exists():
            checkpoint_path = task.checkpoint_path
        elif config.get("resume_from_checkpoint"):
            checkpoint_path = config["resume_from_checkpoint"]

        def _run():
            try:
                run_training(
                    task_id=task_id,
                    dataset_yaml_path=dataset_yaml,
                    output_dir=str(output_dir),
                    config=config,
                    callback=callback,
                    checkpoint_path=checkpoint_path,
                )
            except Exception as e:
                logger.error(f"训练执行异常: {e}", exc_info=True)
                try:
                    db2 = db_factory()
                    t = db2.query(TrainingTask).filter(
                        TrainingTask.id == uuid.UUID(task_id)).first()
                    if t and t.status == "running":
                        t.status = "failed"
                        db2.commit()
                    db2.close()
                except Exception as db_err:
                    logger.error(f"更新失败状态出错: {db_err}")
            finally:
                with _threads_lock:
                    _training_threads.pop(task_id, None)
                cleanup_signals(task_id)

        thread = threading.Thread(target=_run, daemon=True, name=f"train-{task_id[:8]}")
        with _threads_lock:
            _training_threads[task_id] = thread
        thread.start()
        logger.info(f"训练任务已启动: {task.task_name}")
    except Exception as e:
        logger.error(f"启动训练失败: {e}", exc_info=True)
        try:
            task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
            if task:
                task.status = "failed"
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


def pause_training(task_id: str):
    """暂停训练"""
    signal_pause(task_id)
    db = None
    try:
        from app.database.session import SessionLocal
        db = SessionLocal()
        task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
        if task:
            task.status = "paused"
            db.commit()
    except Exception as e:
        logger.error(f"暂停更新状态失败: {e}")
    finally:
        if db:
            db.close()


def resume_training(task_id: str, db_factory):
    """恢复被暂停的训练"""
    if trainer_is_active(task_id):
        signal_resume(task_id)
        db = db_factory()
        try:
            task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
            if task:
                task.status = "running"
                task.updated_at = datetime.now()
                db.commit()
        finally:
            db.close()
    else:
        start_training(task_id, db_factory)


def stop_training(task_id: str):
    """立即停止训练"""
    signal_stop(task_id)
    db = None
    try:
        from app.database.session import SessionLocal
        db = SessionLocal()
        task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
        if task:
            task.status = "failed"
            task.updated_at = datetime.now()
            db.commit()
    except Exception as e:
        logger.error(f"停止更新状态失败: {e}")
    finally:
        if db:
            db.close()


def get_task_status(task_id: str, db: Session) -> Dict[str, Any]:
    """获取任务状态"""
    task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
    if not task:
        return {"error": "任务不存在"}
    return {
        "id": str(task.id),
        "status": task.status,
        "current_epoch": task.current_epoch,
        "total_epochs": task.total_epochs,
        "best_metric": task.best_metric,
        "is_paused": trainer_is_paused(task_id) if task.status == "paused" else False,
        "is_active": trainer_is_active(task_id),
    }


def get_task_metrics(task_id: str, db: Session) -> List[Dict[str, Any]]:
    """获取任务的所有指标数据"""
    metrics = (db.query(TrainingMetric)
               .filter(TrainingMetric.task_id == uuid.UUID(task_id))
               .order_by(TrainingMetric.epoch).all())
    result = []
    for m in metrics:
        result.append({
            "id": str(m.id),
            "task_id": str(m.task_id),
            "epoch": m.epoch,
            "metrics": m.metrics,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return result


def delete_training_task(task_id: str, db: Session) -> bool:
    """删除训练任务（包括模型文件）"""
    task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
    if not task:
        return False
    if task.status == "running":
        stop_training(task_id)
        time.sleep(0.5)
    if task.model_path and Path(task.model_path).exists():
        model_path = Path(task.model_path)
        onnx_path = model_path.with_suffix(".onnx")
        if onnx_path.exists():
            onnx_path.unlink()
        model_path.unlink()
    if task.checkpoint_path and Path(task.checkpoint_path).exists():
        chk_dir = Path(task.checkpoint_path).parent.parent
        if chk_dir.exists() and chk_dir.name.startswith(task.model_name):
            shutil.rmtree(str(chk_dir), ignore_errors=True)
    if task.log_path and Path(task.log_path).exists():
        Path(task.log_path).unlink(missing_ok=True)
    db.delete(task)
    db.commit()
    cleanup_signals(task_id)
    return True


# ══════════════════════════════════════════════════════════════════
#  Model Management
# ══════════════════════════════════════════════════════════════════

def _resolve_model_file(model_name: str) -> Optional[str]:
    """查找模型文件，优先检查 MODELS_DIR 中的 .pt 文件"""
    candidate = MODELS_DIR / f"{model_name}.pt"
    return str(candidate) if candidate.exists() else None


def get_models(db: Session) -> List[Dict[str, Any]]:
    """获取所有训练完成的模型列表"""
    tasks = (db.query(TrainingTask)
             .filter(TrainingTask.status.in_(["completed", "failed", "running", "paused"]))
             .order_by(TrainingTask.completed_at.desc()).all())
    default_model = _get_default_model()
    models = []
    for task in tasks:
        file_path = task.model_path or _resolve_model_file(task.model_name)
        file_size = Path(file_path).stat().st_size if (
            file_path and Path(file_path).exists()) else 0
        mAP50 = mAP50_95 = recall = precision = None
        last_metric = (db.query(TrainingMetric)
                       .filter(TrainingMetric.task_id == task.id)
                       .order_by(TrainingMetric.epoch.desc()).first())
        if last_metric:
            m = last_metric.metrics or {}
            mAP50 = m.get("metrics/mAP50", m.get("val/mAP50", None))
            mAP50_95 = m.get("metrics/mAP50-95", m.get("val/mAP50-95", None))
            recall = m.get("metrics/recall", m.get("val/recall", None))
            precision = m.get("metrics/precision", m.get("val/precision", None))
        dataset_name = None
        class_count = None
        if task.dataset_id:
            ds = db.query(Dataset).filter(Dataset.id == task.dataset_id).first()
            if ds:
                dataset_name = ds.name
                class_count = ds.class_count
        duration = None
        if task.started_at and task.completed_at:
            duration = (task.completed_at - task.started_at).total_seconds()
        models.append({
            "id": str(task.id),
            "model_name": task.model_name,
            "task_name": task.task_name,
            "status": task.status,
            "file_size": file_size,
            "file_path": task.model_path,
            "best_metric": task.best_metric,
            "mAP50": mAP50,
            "mAP50_95": mAP50_95,
            "recall": recall,
            "precision": precision,
            "class_count": class_count,
            "dataset_name": dataset_name,
            "config": task.config,
            "is_default": task.model_name == default_model,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration_seconds": duration,
        })
    return models


def get_model_detail(model_name: str, db: Session) -> Dict[str, Any]:
    """获取模型详情"""
    task = db.query(TrainingTask).filter(TrainingTask.model_name == model_name).first()
    if not task:
        return {"error": "模型不存在"}
    metrics = get_task_metrics(str(task.id), db)
    file_path = task.model_path or _resolve_model_file(task.model_name)
    file_size = Path(file_path).stat().st_size if (
        file_path and Path(file_path).exists()) else 0
    dataset_name = None
    class_count = None
    if task.dataset_id:
        ds = db.query(Dataset).filter(Dataset.id == task.dataset_id).first()
        if ds:
            dataset_name = ds.name
            class_count = ds.class_count
    duration = None
    if task.started_at and task.completed_at:
        duration = (task.completed_at - task.started_at).total_seconds()
    return {
        "model": {
            "id": str(task.id),
            "model_name": task.model_name,
            "task_name": task.task_name,
            "status": task.status,
            "file_size": file_size,
            "file_path": task.model_path,
            "best_metric": task.best_metric,
            "config": task.config,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "dataset_name": dataset_name,
            "class_count": class_count,
            "duration_seconds": duration,
        },
        "task_detail": {
            "id": str(task.id),
            "task_name": task.task_name,
            "model_name": task.model_name,
            "description": task.description,
            "status": task.status,
            "config": task.config,
            "current_epoch": task.current_epoch,
            "total_epochs": task.total_epochs,
            "best_metric": task.best_metric,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        },
        "metrics": metrics,
    }


def export_model(model_name: str, format: str = "pt") -> Optional[str]:
    """导出模型（支持 pt / onnx）"""
    pt_path = MODELS_DIR / f"{model_name}.pt"
    onnx_path = MODELS_DIR / f"{model_name}.onnx"
    if format == "pt":
        return str(pt_path) if pt_path.exists() else None
    if format == "onnx":
        if onnx_path.exists():
            return str(onnx_path)
        if pt_path.exists():
            try:
                from ultralytics import YOLO
                model = YOLO(str(pt_path))
                model.export(format="onnx")
                return str(onnx_path) if onnx_path.exists() else None
            except Exception as e:
                logger.error(f"导出 ONNX 失败: {e}")
                return None
    return None


def import_model(file_bytes: bytes, filename: str, model_name: str, db: Session) -> bool:
    """导入已有的模型文件"""
    ext = Path(filename).suffix
    if ext not in (".pt", ".pth", ".onnx"):
        raise ValueError(f"不支持的模型格式: {ext}")
    target_path = MODELS_DIR / f"{model_name}{ext}"
    with open(str(target_path), "wb") as f:
        f.write(file_bytes)
    task = TrainingTask(
        task_name=f"导入模型 - {model_name}",
        model_name=model_name,
        description=f"从文件 {filename} 导入",
        status="completed",
        config={"imported": True, "source": filename},
        model_path=str(target_path),
        current_epoch=0,
        total_epochs=0,
        completed_at=datetime.now(),
    )
    db.add(task)
    db.commit()
    logger.info(f"模型导入完成: {model_name}")
    return True


def delete_model(model_name: str, db: Session) -> bool:
    """删除模型及对应的训练任务"""
    task = db.query(TrainingTask).filter(TrainingTask.model_name == model_name).first()
    if not task:
        return False
    # 如果删除的是默认模型，清除默认设置
    if _get_default_model() == model_name:
        config_path = Path(settings.MODELS_DIR) / ".default_model"
        if config_path.exists():
            config_path.unlink()
    pt_path = MODELS_DIR / f"{model_name}.pt"
    onnx_path = MODELS_DIR / f"{model_name}.onnx"
    if pt_path.exists():
        pt_path.unlink()
    if onnx_path.exists():
        onnx_path.unlink()
    db.delete(task)
    db.commit()
    return True


def set_default_model(model_name: str) -> bool:
    """设置默认检测模型"""
    # 允许传入空字符串来清除默认设置
    if not model_name:
        config_path = Path(settings.MODELS_DIR) / ".default_model"
        if config_path.exists():
            config_path.unlink()
        logger.info("默认模型已清除，将使用 YOLOv26 预训练模型")
        return True

    config_dir = Path(settings.MODELS_DIR)
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / ".default_model"
    with open(str(config_path), "w") as f:
        f.write(model_name)
    logger.info(f"默认模型已设置为: {model_name}")
    return True


def _get_default_model() -> Optional[str]:
    """获取当前默认检测模型名称"""
    config_path = Path(settings.MODELS_DIR) / ".default_model"
    if config_path.exists():
        return config_path.read_text().strip()
    return None


def reset_default_model() -> bool:
    """将默认模型重置为 YOLOv26 预训练模型"""
    return set_default_model("")


# ══════════════════════════════════════════════════════════════════
#  Storage Management
# ══════════════════════════════════════════════════════════════════

def _format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_storage_info() -> Dict[str, Any]:
    """获取磁盘空间信息"""
    models_size = sum(f.stat().st_size for f in MODELS_DIR.rglob("*") if f.is_file()
                      ) if MODELS_DIR.exists() else 0
    datasets_size = sum(f.stat().st_size for f in DATASETS_DIR.rglob("*") if f.is_file()
                        ) if DATASETS_DIR.exists() else 0
    logs_size = sum(f.stat().st_size for f in Path("./data/logs").rglob("*") if f.is_file()
                    ) if Path("./data/logs").exists() else 0
    total = models_size + datasets_size + logs_size
    return {
        "models_size": models_size,
        "datasets_size": datasets_size,
        "logs_size": logs_size,
        "total_size": total,
        "models_size_display": _format_size(models_size),
        "datasets_size_display": _format_size(datasets_size),
        "logs_size_display": _format_size(logs_size),
        "total_size_display": _format_size(total),
    }


def clean_failed_temp_files() -> Dict[str, Any]:
    """清理失败的训练任务产生的临时文件"""
    cleaned_count = 0
    cleaned_size = 0
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        if TRAINING_DIR.exists():
            for task_dir in TRAINING_DIR.iterdir():
                if task_dir.is_dir():
                    dir_size = sum(f.stat().st_size for f in task_dir.rglob("*") if f.is_file())
                    shutil.rmtree(str(task_dir), ignore_errors=True)
                    cleaned_count += 1
                    cleaned_size += dir_size
                    logger.info(f"已清理临时文件: {task_dir}")
    finally:
        db.close()
    return {
        "cleaned_count": cleaned_count,
        "cleaned_size": cleaned_size,
        "cleaned_size_display": _format_size(cleaned_size),
    }


__all__ = [
    "upload_dataset", "create_dataset_yaml", "get_dataset_preview", "delete_dataset",
    "create_task", "create_task_with_dataset", "start_training", "pause_training", "resume_training", "stop_training",
    "get_task_status", "get_task_metrics", "delete_training_task",
    "get_models", "get_model_detail", "export_model", "import_model",
    "delete_model", "set_default_model", "get_storage_info", "clean_failed_temp_files",
]
