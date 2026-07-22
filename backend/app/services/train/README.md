## 文件结构

```
backend/app/services/train/
├── __init__.py                # 包声明
├── requirements.txt           # 训练依赖清单
├── config.py                  # 训练超参数配置（dataclass）
├── data_converter.py          # LVIS → YOLO 格式转换
├── train_lvis.py              # 主训练脚本
├── README.md                  # 本文件：结构说明 + 参数速查
└── TRAINING_GUIDE.md          # 详细指南：环境搭建、GPU 选参、常见问题
```

## 各文件说明

### `config.py`

`TrainConfig` dataclass，集中管理所有超参数（epochs/batch/lr/数据增强等），共约 40 个参数。

### `data_converter.py`

核心格式转换器：

| 阶段 | 说明 |
|---|---|
| 1. 统计类别频率 | 遍历 train 注解，统计每个 LVIS category_id 的实例数 |
| 2. 过滤 + 排序 | 剔除低频类别（默认 <10 实例），按频次取 Top-300 |
| 3. 生成映射表 | `{lvis_cat_id: yolo_class_id}` + `{yolo_id: name}` |
| 4. 写入标签文件 | 每张图片生成 `.txt`，每行 `class_id x_center y_center width height`（归一化） |
| 5. 生成 dataset.yaml | Ultralytics 格式，含 `train/val` 图片路径、`nc`、`names` |

### `train_lvis.py`

主训练入口，执行流程：

```
Step 1/4: 转换 LVIS → YOLO 格式
Step 2/4: 加载预训练模型（自动下载 yolo26n.pt）
Step 3/4: 执行 fine-tuning（调用 model.train()）
Step 4/4: 保存最佳模型到 /data/models/lvis_finetuned/
```

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--model` | `yolo26n.pt` | 预训练模型，也可传 checkpoint 路径 |
| `--epochs` | `100` | 训练轮数 |
| `--batch` | `16` | 批次大小 |
| `--workers` | `8` | 数据加载线程数 |
| `--imgsz` | `640` | 训练图片尺寸 |
| `--lr0` | `0.01` | 初始学习率 |
| `--device` | `""` | 训练设备 (`0` / `0,1` / `cpu` / `""`) |
| `--cache` | `false` | 图片缓存 (`false` / `ram` / `disk`) |
| `--lvis-root` | `data/uploads/lvis` | LVIS 数据集根目录 |
| `--output-dir` | `data/models/lvis_finetuned` | 模型输出目录 |
| `--resume` | `""` | 从 checkpoint 恢复（保持原参数不变） |
| `--pretrained` | `true` | 是否使用预训练权重 |
| `--no-verbose` | `false` | 启用详细进度条（默认简洁单行输出） |

完整参数见 `config.py` 的 `TrainConfig` 类（含数据增强参数）。

## GPU 实战参数对照

> **模型**: yolo26n (2.76M 参数)，LVIS v1 (300 类，118,287 训练图，640×640)

| | RTX 5090 (32 GB) | RTX PRO 6000 (96 GB, 110GB 容器) |
|---|---|---|
| **batch** | 72 | 192 |
| **workers** | 16 ⚠️ 上限 | 16 ⚠️ 上限 |
| **cache** | 无 | 无 |
| **显存** | ~26 GB (81%) | ~81 GB (85%) |
| **内存** | ~40 GB | ~67 GB (110GB 容器) |
| **速度** | ~3.8 it/s | ~1.4 it/s |
| **吞吐量** | ~270 img/s | ~270 img/s |
| **每 epoch** | ~7 min | ~7 min |

> **吞吐量几乎相同** — yolo26n 太小，瓶颈在磁盘 I/O + 图像解码，不在 GPU 算力。提高 batch 的收益主要是梯度更稳定、BN 统计更准。

## 踩坑记录

### 1. workers 上限

| workers | RTX 5090 | RTX PRO 6000 |
|---------|----------|-------------|
| 16 | ✅ 安全 | ✅ 安全 |
| 20 | ⚠️ 93% 显存 (30.3GB) | ❌ 内存飙至 100GB+ |
| 24 | ❌ CUDA OOM (TaskAlignedAssigner) | — |

**结论**: workers=16 是两卡通用安全上限。LVIS 标注数据量大（300 类），每个 worker 多持一份副本。

### 2. `--cache ram` 内存陷阱

LVIS 训练集图片缓存需 ~97GB。容器 cgroup 限制才是真实内存上限（`free` 命令显示的是宿主机内存）：
- RTX 5090 容器 90GB → ❌ OOM
- RTX PRO 6000 容器 110GB → 97GB + 进程开销 > 110GB → ❌ OOM

**只有在 RAM ≥ 128GB 时才用 `--cache ram`**。

### 3. `--resume` 不能改参数

Ultralytics `model.train(resume=True)` 使用原始配置，不能改 batch/epochs/workers。如需换参数续训：

```bash
# ❌ 这样没用（参数会被忽略）
python -m app.services.train.train_lvis --resume last.pt --batch 192

# ✅ 用 --model 传 checkpoint，作为新训练
python -m app.services.train.train_lvis --model weights/last.pt --epochs 27 --batch 192
```

### 4. 日志换行闪烁

默认进度条信息太多，窄终端会换行反复刷新。已默认启用 `verbose=False`（简洁单行输出）。如需恢复详细输出，加 `--no-verbose`。

### 5. GPU 利用率不高 → 换更大模型

yolo26n 计算量太小（2.76M 参数），GPU 瞬间算完只能等数据。换 yolo26m 能让 GPU 利用率飙升到 95%+，mAP 涨 5~8 个点，训练时间只多 1-3 分钟。详见 [TRAINING_GUIDE.md § 10. 模型选型与升级建议](./TRAINING_GUIDE.md#10-模型选型与升级建议)。

## 数据目录

```
data/uploads/lvis/                           ← LVIS 数据集根目录
├── images/
│   ├── train2017/                           ← 训练图片 (118,287 张)
│   └── val2017/                             ← 验证图片 (5,000 张)
├── labels/                                  ← YOLO 格式标签（自动生成）
│   ├── train2017/
│   └── val2017/
└── annotations/
    ├── lvis_v1_train.json                   ← LVIS 训练注解
    └── lvis_v1_val.json                     ← LVIS 验证注解

data/models/lvis_finetuned/                  ← 训练输出
├── dataset.yaml
├── best.pt / last.pt
└── dataset_meta.yaml
```

## 训练命令速查

```bash
cd backend

# ===== RTX 5090 (32GB) =====
nohup python -u -m app.services.train.train_lvis \
  --model yolo26n.pt --device 0 --epochs 100 --batch 72 --workers 16 \
  --lvis-root /path/to/data/uploads/lvis \
  --output-dir /path/to/data/models/lvis_finetuned \
  > train.log 2>&1 &

# ===== RTX PRO 6000 (96GB, 110GB 容器) =====
nohup python -u -m app.services.train.train_lvis \
  --model yolo26n.pt --device 0 --epochs 100 --batch 192 --workers 16 \
  --lvis-root /path/to/data/uploads/lvis \
  --output-dir /path/to/data/models/lvis_finetuned \
  > train.log 2>&1 &

# ===== 用 checkpoint 续训（换参数）=====
nohup python -u -m app.services.train.train_lvis \
  --model lvis_finetune/lvis_yolo26n/weights/last.pt --device 0 \
  --epochs 27 --batch 192 --workers 16 \
  --lvis-root /path/to/data/uploads/lvis \
  --output-dir /path/to/data/models/lvis_finetuned \
  > train.log 2>&1 &

# ===== 监控 =====
tail -f train.log                           # 看训练日志
watch -n 2 nvidia-smi                      # 看 GPU 状态
```

## 迁移训练

跨机器迁移需拷贝：
1. `data/uploads/lvis/` — 数据集
2. `data/models/lvis_finetuned/` — dataset.yaml
3. `backend/lvis_finetune/lvis_yolo26n/weights/` — checkpoint
4. `backend/app/services/train/` — 训练脚本

> dataset.yaml 中的绝对路径需更新为新机器路径。
