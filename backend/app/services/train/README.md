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
| `--resume` | `""` | 从 checkpoint 断点重训（支持覆盖 lr0/batch/workers/imgsz） |
| `--pretrained` | `true` | 是否使用预训练权重 |
| `--verbose` | `false` | 启用 tqdm 详细进度条（默认关闭，避免窄终端换行） |
| `--ncols` | `0` | 强制 tqdm 进度条宽度（列数），0=自动检测。配合 `--verbose` 使用 |

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

### 3. `--resume` 断点重训与参数覆盖

脚本已支持在断点重训时覆盖学习率等参数。原理：加载 checkpoint 后修改其内嵌的 `train_args` 字典，保存为 `resume_modified.pt`，再用 `resume=True` 恢复训练。

```bash
# ✅ 现在可以直接改参数断点重训
python -m app.services.train.train_lvis --resume last.pt --lr0 0.001 --batch 192
# 输出: 覆盖 checkpoint 参数: lr0: 0.01 → 0.001, batch: 16 → 192

# 也可以不改参数，纯断点续训
python -m app.services.train.train_lvis --resume last.pt
```

> 支持覆盖的参数：`lr0`、`batch`、`workers`、`imgsz`。其余参数沿用原 checkpoint 配置。

### 4. 日志换行闪烁

tqdm 进度条通过 `\r` 原地刷新，窄终端会换行反复闪烁。已默认 `verbose=False`（简洁单行输出）。

- CLI 脚本：加 `--verbose` 开启进度条，配合 `--ncols 80` 限制宽度避免换行
- Web 训练（trainer.py）：`LogCollector` 已重写为逐字符解析 `\r`，遇到回车符自动丢弃当前行缓冲；同时 `verbose` 设为 `False`，彻底消除进度条换行问题

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

# ===== 断点重训（可直接改参数）=====
nohup python -u -m app.services.train.train_lvis \
  --resume lvis_finetune/lvis_yolo26n/weights/last.pt --device 0 \
  --lr0 0.001 --batch 192 --workers 16 \
  --lvis-root /path/to/data/uploads/lvis \
  --output-dir /path/to/data/models/lvis_finetuned \
  > train.log 2>&1 &

# ===== 开启进度条（限制宽度防换行）=====
python -m app.services.train.train_lvis --verbose --ncols 80

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
