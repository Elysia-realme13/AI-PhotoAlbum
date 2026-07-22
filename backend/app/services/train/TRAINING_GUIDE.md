# YOLO LVIS 模型训练指南

## 项目概述

使用 YOLO 在 LVIS v1 数据集（300 类，118,287 训练图）上进行目标检测模型微调（fine-tuning）。

## 环境要求

- **Python 3.12 64 位**（32 位无法安装 PyTorch）
- **Linux**（推荐）或 Windows 11
- **NVIDIA GPU**，CUDA 支持

验证 Python 是否为 64 位：
```bash
python -c "import struct; print('64-bit' if struct.calcsize('P') == 8 else '32-bit')"
```

## 1. 安装依赖

```bash
cd backend
uv sync
```

核心依赖：`ultralytics>=8.3.0`、`torch>=2.1.0`、`pycocotools>=2.0.7`、`PyYAML>=6.0` 等。

验证安装：
```bash
python -c "import torch; print(f'PyTorch {torch.__version__}'); print(f'CUDA 可用: {torch.cuda.is_available()}')"
```

## 2. 目录架构

```
<project_root>/
├── backend/
│   ├── app/services/train/                 ← 训练脚本
│   │   ├── config.py                       ← 超参数配置
│   │   ├── data_converter.py               ← LVIS → YOLO 格式转换
│   │   └── train_lvis.py                   ← 主训练脚本
│   └── lvis_finetune/lvis_yolo26n/         ← 训练输出（Ultralytics runs）
│       └── weights/                        ← checkpoint
├── data/
│   ├── uploads/lvis/                       ← LVIS 数据集
│   │   ├── images/train2017/               ← 训练图片 (118,287 张, ~18 GB)
│   │   ├── images/val2017/                 ← 验证图片 (5,000 张, ~1 GB)
│   │   ├── labels/                         ← YOLO 标签（自动生成）
│   │   └── annotations/
│   │       ├── lvis_v1_train.json          ← 训练注解 (~1 GB)
│   │       └── lvis_v1_val.json            ← 验证注解 (~192 MB)
│   └── models/lvis_finetuned/              ← 最终模型输出
│       └── dataset.yaml
└── docker-compose.yml
```

## 3. 训练命令

在 **backend/** 目录执行：

```bash
cd backend

# 基础训练（默认参数：batch=16, workers=8）
python -m app.services.train.train_lvis --device 0

# 指定参数
python -m app.services.train.train_lvis \
  --model yolo26n.pt --epochs 100 --batch 16 --device 0
```

> **后台运行**（推荐，防 SSH 断开）：
> ```bash
> nohup python -u -m app.services.train.train_lvis \
>   --model yolo26n.pt --device 0 --epochs 100 --batch 192 --workers 16 \
>   --lvis-root /path/to/data/uploads/lvis \
>   --output-dir /path/to/data/models/lvis_finetuned \
>   > train.log 2>&1 &
> ```

## 4. GPU 选参与实测对照

> **模型**: yolo26n (2.76M 参数)，LVIS v1，640×640

### 实测参数

| | RTX 5090 (32 GB) | RTX PRO 6000 (96 GB, 110GB 容器) |
|---|---|---|
| **batch** | 72 | 192 |
| **workers** | 16 ⚠️ 上限 | 16 ⚠️ 上限 |
| **cache** | 无 | 无 |
| **显存占用** | ~26 GB (81%) | ~81 GB (85%) |
| **内存占用** | ~40 GB | ~67 GB |
| **速度** | ~3.8 it/s | ~1.4 it/s |
| **图片吞吐** | ~270 img/s | ~270 img/s |
| **每 epoch** | ~7 分钟 | ~7 分钟 |

### 为什么吞吐量相同？

yolo26n 只有 2.76M 参数，计算量极小。**瓶颈在磁盘 I/O + 图像解码**，不在 GPU 算力。更大 batch 的收益主要是梯度估计更稳定、BatchNorm 统计更准确。

### 怎么选 batch？

显存与 batch 大致线性关系：**每张 640×640 图约 0.36 GB 显存**。预留 10-15% 余量：

| GPU 显存 | 推荐 batch |
|----------|-----------|
| 24 GB | 48–56 |
| 32 GB | 64–80 |
| 48 GB | 96–120 |
| 80 GB | 160–200 |
| 96 GB | 192–240 |

### workers 安全上限

LVIS 标注数据量大（300 类），每个 dataloader worker 额外持有一份数据副本：

| workers | RTX 5090 | RTX PRO 6000 (110GB 容器) |
|---------|----------|--------------------------|
| 8 | ✅ | ✅ |
| 16 | ✅ | ✅ |
| 20 | ⚠️ 显存 93% | ❌ 内存 >100GB，逼近 OOM |
| 24 | ❌ CUDA OOM | — |

**结论：workers=16 是两卡通用安全上限。**

## 5. 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--model` | `yolo26n.pt` | 预训练模型，也可是 checkpoint 路径 |
| `--epochs` | `100` | 训练轮数 |
| `--batch` | `16` | 批次大小 |
| `--workers` | `8` | 数据加载线程数 |
| `--imgsz` | `640` | 训练图片尺寸 |
| `--lr0` | `0.01` | 初始学习率 |
| `--device` | `""` | `0` / `0,1` / `cpu` / `""`(自动) |
| `--cache` | `false` | `false` / `ram` / `disk`（见下方说明） |
| `--lvis-root` | `data/uploads/lvis` | LVIS 数据集根目录 |
| `--output-dir` | `data/models/lvis_finetuned` | 模型输出目录 |
| `--resume` | `""` | 从 checkpoint 断点重训（支持覆盖 lr0/batch/workers/imgsz） |
| `--no-verbose` | — | ~~已废弃~~，请用 `--verbose` |
| `--verbose` | `false` | 启用 tqdm 详细进度条（默认关闭，避免窄终端换行） |
| `--ncols` | `0` | 强制 tqdm 进度条宽度（列数），0=自动。配合 `--verbose` 使用 |

完整参数见 `config.py` 的 `TrainConfig` 类（约 40 个，含数据增强）。

## 6. 训练流程

脚本自动执行 4 步：

| 步骤 | 说明 |
|------|------|
| Step 1/4 | 转换 LVIS 注解为 YOLO 格式（过滤低频类别，保留 Top-300） |
| Step 2/4 | 加载预训练模型 |
| Step 3/4 | 执行 fine-tuning |
| Step 4/4 | 保存最佳模型到 `data/models/lvis_finetuned/` |

## 7. 训练输出

```
data/uploads/lvis/labels/                   ← YOLO 格式标签（自动生成）
├── train2017/
└── val2017/

data/models/lvis_finetuned/                 ← 模型输出
├── best.pt / last.pt
├── dataset.yaml
└── dataset_meta.yaml

backend/lvis_finetune/lvis_yolo26n/         ← Ultralytics 训练报告
├── results.png / confusion_matrix.png / ... 
└── weights/
    ├── best.pt / last.pt / epoch*.pt
```

## 8. 监控命令

```bash
# 实时看训练日志
tail -f train.log

# 看 GPU
watch -n 2 nvidia-smi

# 看进程
ps aux | grep train_lvis | grep -v grep
```

## 9. 常见问题

### Q: `--cache ram` 报 OOM？

LVIS 训练集图片缓存需 ~97GB RAM。**注意**：容器/云主机用 `free` 命令看到的可能是宿主机内存，真实 cgroup 限制才是上限。
- 容器 <128GB：**不要用** `--cache ram`
- 容器 ≥128GB：可以用，但会消耗大量内存

警告 `cache='ram' may produce non-deterministic training results` 可忽略，不影响效果。

### Q: 怎么换参数继续训练？

`--resume` 现已支持参数覆盖。脚本会自动修改 checkpoint 内的 `train_args` 并保存为 `resume_modified.pt`，然后用 `resume=True` 恢复训练：

```bash
# ✅ 断点重训并修改学习率
python -m app.services.train.train_lvis --resume last.pt --lr0 0.001 --batch 192
# 输出: 覆盖 checkpoint 参数: lr0: 0.01 → 0.001, batch: 16 → 192

# ✅ 纯断点续训（不改参数）
python -m app.services.train.train_lvis --resume last.pt
```

> 支持覆盖的参数：`lr0`、`batch`、`workers`、`imgsz`。其余参数沿用原 checkpoint 配置。
> optimizer state 和 epoch 计数器均保留，是真正的 resume。
>
> Web 端训练同理：在任务 config 中修改参数后点击恢复，trainer 会自动将新值写入 checkpoint。

### Q: 跨机器迁移训练？

需拷贝 4 个目录：
1. `data/uploads/lvis/` — 数据集
2. `data/models/lvis_finetuned/` — dataset.yaml
3. `backend/lvis_finetune/lvis_yolo26n/weights/` — checkpoint
4. `backend/app/services/train/` — 训练脚本

> dataset.yaml 中的绝对路径需更新为新机器路径。

### Q: 训练日志终端换行闪烁？

tqdm 进度条通过 `\r` 原地刷新，窄终端会换行反复闪烁。已默认 `verbose=False`（简洁单行输出）。

- **CLI 脚本**：加 `--verbose` 开启进度条，配合 `--ncols 80` 限制宽度避免换行
- **Web 训练**：`LogCollector` 已重写为逐字符解析 `\r`，遇到回车符自动丢弃当前行缓冲；同时 `verbose` 设为 `False`

```bash
# 开启进度条 + 限制宽度
python -m app.services.train.train_lvis --verbose --ncols 80
```

### Q: GPU 利用率不高？

yolo26n 参数极少（2.76M），计算瓶颈不在 GPU，考虑换更大模型（见下节）。

## 10. 模型选型与升级建议

> 场景：yolo26n 在 RTX PRO 6000 96GB 上 GPU 利用率仅 50-80%，瓶颈在数据加载。换更大模型能让 GPU 真正跑满。

### 各模型参数对比

| 模型 | 参数量 | 推荐 batch (96GB) | GPU 利用率 | 每 epoch 时长 | mAP 提升 |
|------|--------|------------------|------------|---------------|----------|
| yolo26n（当前） | 2.76M | 192 | 50-80% | ~7 min | 基线 |
| yolo26s | ~7M | 128-160 | 85-95% | ~7-8 min | +3~5 |
| yolo26m | ~16M | 64-96 | 95-100% | ~8-10 min | +5~8 |
| yolo26l | ~25M | 48-64 | 100% | ~10-12 min | +8~10 |

### 换模型的收益

1. **GPU 利用率**：计算量增大后，GPU 不再等数据，利用率飙到 95%+
2. **精度提升**：大模型在复杂场景（密集、遮挡、小目标）上的 mAP 显著高于 nano 版本
3. **训练时间可控**：每 epoch 仅多 1-3 分钟，总训练时间变化不大

### 换模型的代价

1. **模型文件更大**：部署时推理延迟也更高
2. **Batch 需下调**：换大模型后先保守测试，找到显存 90% 的甜点值
3. **需重新调参**：学习率、warmup 等可能需要微调

### 升级命令示例

```bash
# 当前 yolo26n 跑完后，换 yolo26m 对比
nohup python -u -m app.services.train.train_lvis \
  --model yolo26m.pt --device 0 --epochs 27 --batch 64 --workers 16 \
  --lvis-root /path/to/data/uploads/lvis \
  --output-dir /path/to/data/models/lvis_finetuned \
  > train.log 2>&1 &
```

> 启动后观察 `nvidia-smi`：GPU 利用率 ≥95%、显存 ~80GB 为佳。若显存余量多，逐步上调 batch 到 80、96。
