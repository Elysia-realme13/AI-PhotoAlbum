"""
YOLO 训练执行器

封装 ultralytics YOLO 的训练逻辑，支持：
- checkpoint 保存与加载
- 暂停/恢复/停止的信号控制
- 每个 epoch 结束后回调保存指标到数据库
"""
import os
import io
import json
import sys
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import contextlib

logger = logging.getLogger(__name__)


# ── 全局信号管理器（跨线程共享） ─────────────────────────────────
_training_signals: Dict[str, Dict[str, Any]] = {}
_signals_lock = threading.Lock()


def _get_signals(task_id: str) -> Dict[str, Any]:
    """获取或创建任务的信号对象"""
    with _signals_lock:
        if task_id not in _training_signals:
            _training_signals[task_id] = {
                "pause": threading.Event(),
                "stop": threading.Event(),
                "paused": threading.Event(),
                "active": False,
            }
        return _training_signals[task_id]


def _cleanup_signals(task_id: str):
    """清理任务的信号对象"""
    with _signals_lock:
        _training_signals.pop(task_id, None)


# ── 训练回调 ─────────────────────────────────────────────────────
class TrainingCallback:
    """训练过程的回调接口"""

    def on_epoch_end(self, task_id: str, epoch: int, metrics: dict):
        """每个 epoch 结束时的回调
        Args:
            task_id: 训练任务 ID
            epoch: 当前 epoch（从 1 开始）
            metrics: 当前 epoch 的指标字典
        """
        raise NotImplementedError

    def on_train_end(self, task_id: str, final_metrics: dict, model_path: str):
        """训练结束时的回调"""
        raise NotImplementedError

    def on_log_line(self, task_id: str, line: str):
        """训练日志输出回调"""
        raise NotImplementedError


class LogCollector:
    """日志收集器，充当 stdout/stderr 的缓冲区"""

    def __init__(self, task_id: str, callback: Optional[Callable] = None):
        self.task_id = task_id
        self.callback = callback
        self.lines: list = []
        self._buffer = ""

    def write(self, text: str):
        self._buffer += text
        if "\n" in self._buffer:
            lines = self._buffer.split("\n")
            for line in lines[:-1]:
                if line.strip():
                    self.lines.append(line)
                    if self.callback:
                        self.callback(self.task_id, line)
            self._buffer = lines[-1]

    def flush(self):
        if self._buffer.strip():
            self.lines.append(self._buffer)
            if self.callback:
                self.callback(self.task_id, self._buffer)
            self._buffer = ""


# ── 主力训练函数 ─────────────────────────────────────────────────

def run_training(
    task_id: str,
    dataset_yaml_path: str,
    output_dir: str,
    config: dict,
    callback: TrainingCallback,
    checkpoint_path: Optional[str] = None,
):
    """执行 YOLO 训练（在独立线程中运行）

    Args:
        task_id: 训练任务 ID
        dataset_yaml_path: 数据集 YAML 配置文件路径
        output_dir: 模型和日志输出目录
        config: 训练超参数字典
        callback: 训练回调实例
        checkpoint_path: 已有 checkpoint 路径（断点续训时使用）
    """
    signals = _get_signals(task_id)
    signals["active"] = True
    signals["pause"].clear()
    signals["stop"].clear()
    signals["paused"].clear()

    try:
        # ── 导入 YOLO ──────────────────────────────────────────
        from ultralytics import YOLO

        # ── 构造输出目录 ────────────────────────────────────────
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 拆分 project/name
        project_dir = str(output_path.parent)
        task_name = output_path.name

        # ── 构建训练参数 ────────────────────────────────────────
        train_kwargs = {
            "data": dataset_yaml_path,
            "epochs": config.get("epochs", 100),
            "batch": config.get("batch", 16),
            "imgsz": config.get("imgsz", 640),
            "lr0": config.get("lr0", 0.01),
            "optimizer": config.get("optimizer", "AdamW"),
            "momentum": config.get("momentum", 0.937),
            "weight_decay": config.get("weight_decay", 0.0005),
            "warmup_epochs": config.get("warmup_epochs", 3.0),
            "device": config.get("device", ""),
            "workers": config.get("workers", 8),
            "seed": config.get("seed", 0),
            "patience": config.get("patience", 50),
            "project": str(project_dir),
            "name": task_name,
            "exist_ok": True,
            "verbose": True,
            "val": True,
            "amp": True,
        }

        # 可选增强
        if config.get("multi_scale"):
            train_kwargs["multi_scale"] = 0.5
        if config.get("mixup", 0) > 0:
            train_kwargs["mixup"] = config["mixup"]
        if config.get("mosaic", 1.0) != 1.0:
            train_kwargs["mosaic"] = config["mosaic"]
        if config.get("copy_paste", 0) > 0:
            train_kwargs["copy_paste"] = config["copy_paste"]
        if config.get("save_period", -1) > 0:
            train_kwargs["save_period"] = config["save_period"]

        # ── 设备检测 ────────────────────────────────────────────
        device = config.get("device", "")
        if not device:
            try:
                import torch
                device = "0" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        train_kwargs["device"] = device

        # ── 加载预训练模型或 checkpoint ─────────────────────────
        pretrained = config.get("pretrained_model", "yolo26n.pt")


        # 将裸文件名解析到 data/models 目录，避免 YOLO 下载到当前工作目录
        if "/" not in pretrained and "\\" not in pretrained and not pretrained.startswith("http"):
            _pt_dir = Path("./data/models").resolve()
            _pt_dir.mkdir(parents=True, exist_ok=True)
            pretrained = str(_pt_dir / pretrained)
        
        if checkpoint_path and Path(checkpoint_path).exists():
            logger.info(f"[训练器] 从 checkpoint 恢复训练: {checkpoint_path}")
            model = YOLO(checkpoint_path)
            train_kwargs["resume"] = True
            # 读取保存的 epoch 信息
            ckpt = torch.load(checkpoint_path, map_location="cpu")
            start_epoch = ckpt.get("epoch", 0) if isinstance(ckpt, dict) else 0
            del ckpt
        else:
            start_epoch = 0
            logger.info(f"[训练器] 加载预训练模型: {pretrained}")
            model = YOLO(pretrained)
            # 确保加载预训练权重
            if Path(pretrained).exists() or "/" in pretrained:
                pass  # 直接加载
            else:
                # 尝试从 ultralytics 仓库加载
                pass

        # ── 注册 ultralytics 回调 ──────────────────────────────
        # 使用 ultralytics 内置回调系统拦截 epoch 事件
        _epoch_counter = [start_epoch]
        _stop_flag = [False]

        def _on_epoch_end(trainer):
            """每个 epoch 结束时的回调"""
            nonlocal _epoch_counter
            _epoch_counter[0] = getattr(trainer, "epoch", _epoch_counter[0] + 1)
            epoch = _epoch_counter[0]

            # 提取指标
            metrics = {}
            try:
                if hasattr(trainer, "metrics") and trainer.metrics:
                    for k, v in trainer.metrics.items():
                        try:
                            val = float(v)
                            metrics[k] = round(val, 6)
                        except (TypeError, ValueError):
                            pass
            except Exception:
                pass

            # 更新数据库中的 current_epoch
            try:
                callback.on_epoch_end(task_id, epoch, metrics)
            except Exception as cb_err:
                logger.error(f"[训练器] 指标回调失败: {cb_err}")

            # 检查停止信号（立即退出）
            if signals["stop"].is_set():
                logger.warning(f"[训练器] 收到停止信号，epoch {epoch} 后终止训练")
                _stop_flag[0] = True
                # 抛出异常来终止训练
                raise SystemExit("训练已被用户停止")

            # 检查暂停信号
            if signals["pause"].is_set():
                logger.info(f"[训练器] 收到暂停信号，epoch {epoch} 后暂停")
                # 手动保存 checkpoint
                try:
                    ckpt_path = str(output_path / "weights" / "last.pt")
                    if Path(ckpt_path).exists():
                        import shutil
                        pause_ckpt = str(output_path / "weights" / "pause_checkpoint.pt")
                        shutil.copy2(ckpt_path, pause_ckpt)
                        callback.on_log_line(
                            task_id,
                            f"[暂停] checkpoint 已保存: {pause_ckpt}"
                        )
                except Exception as ckpt_err:
                    logger.error(f"[训练器] 保存暂停 checkpoint 失败: {ckpt_err}")

                signals["paused"].set()

                # 等待恢复信号
                while signals["pause"].is_set():
                    if signals["stop"].is_set():
                        _stop_flag[0] = True
                        raise SystemExit("训练已被用户停止")
                    time.sleep(0.5)

                logger.info(f"[训练器] 恢复训练 (epoch {epoch + 1})")

        def _on_train_end(trainer):
            """训练结束时的回调"""
            final_metrics = {}
            try:
                if hasattr(trainer, "metrics") and trainer.metrics:
                    for k, v in trainer.metrics.items():
                        try:
                            val = float(v)
                            final_metrics[k] = round(val, 6)
                        except (TypeError, ValueError):
                            pass
            except Exception:
                pass

            save_dir = getattr(trainer, "save_dir", output_path)
            best_path = str(save_dir / "weights" / "best.pt")
            if not Path(best_path).exists():
                best_path = str(save_dir / "weights" / "last.pt")

            try:
                callback.on_train_end(task_id, final_metrics, best_path)
            except Exception as cb_err:
                logger.error(f"[训练器] 训练结束回调失败: {cb_err}")

        def _on_val_end(trainer):
            """每个 epoch 验证结束后提取指标并保存"""
            nonlocal _epoch_counter
            epoch = getattr(trainer, "epoch", _epoch_counter[0])
            metrics = {}
            try:
                if hasattr(trainer, "metrics") and trainer.metrics:
                    for k, v in trainer.metrics.items():
                        try:
                            val = float(v)
                            metrics[k] = round(val, 6)
                        except (TypeError, ValueError):
                            pass
            except Exception:
                pass
            logger.info(f"[训练器] 验证结束回调: epoch={epoch}, task_id={task_id}, metrics_keys={list(metrics.keys())}")
            try:
                callback.on_val_end(task_id, epoch, metrics)
            except Exception as cb_err:
                logger.error(f"[训练器] 验证指标回调失败: {cb_err}")

        # 注册回调
        model.add_callback("on_train_epoch_end", _on_epoch_end)
        model.add_callback("on_val_end", _on_val_end)
        model.add_callback("on_train_end", _on_train_end)

        # 启动训练
        logger.info(f"[训练器] 开始训练 task={task_id}, 设备={device}")

        try:
            log_collector = LogCollector(task_id, callback=callback.on_log_line)
            with contextlib.redirect_stdout(log_collector), contextlib.redirect_stderr(log_collector):
                results = model.train(**train_kwargs)

            # 由于 on_train_end 已在回调中处理，这里不做重复处理
            logger.info(f"[训练器] 训练正常完成 task={task_id}")

        except SystemExit:
            if _stop_flag[0]:
                logger.info(f"[训练器] 训练被用户停止 (task={task_id})")
            else:
                raise

    except Exception as e:
        logger.error(f"[训练器] 训练异常终止: {e}", exc_info=True)
        raise
    finally:
        # 清理信号
        signals["active"] = False
        signals["pause"].clear()
        signals["stop"].clear()
        signals["paused"].clear()
        # 解绑回调
        try:
            model.reset_callbacks()
        except Exception:
            pass


def signal_pause(task_id: str):
    """发送暂停信号"""
    signals = _get_signals(task_id)
    signals["pause"].set()
    logger.info(f"[信号] 已发送暂停信号 (task={task_id})")


def signal_resume(task_id: str):
    """发送恢复信号"""
    signals = _get_signals(task_id)
    signals["pause"].clear()
    signals["paused"].clear()
    logger.info(f"[信号] 已发送恢复信号 (task={task_id})")


def signal_stop(task_id: str):
    """发送停止信号"""
    signals = _get_signals(task_id)
    signals["stop"].set()
    signals["pause"].clear()
    logger.info(f"[信号] 已发送停止信号 (task={task_id})")


def is_paused(task_id: str) -> bool:
    """检查训练是否已处于暂停状态"""
    signals = _get_signals(task_id)
    return signals["paused"].is_set()


def is_active(task_id: str) -> bool:
    """检查训练是否正在进行"""
    signals = _get_signals(task_id)
    return signals.get("active", False)


def cleanup_signals(task_id: str):
    """清理任务信号"""
    _cleanup_signals(task_id)


__all__ = [
    "run_training",
    "signal_pause",
    "signal_resume",
    "signal_stop",
    "is_paused",
    "is_active",
    "cleanup_signals",
    "TrainingCallback",
    "LogCollector",
]
