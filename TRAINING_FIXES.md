# YOLO LVIS 训练问题与修改记录

## 问题 1：ModuleNotFoundError: No module named 'app'

**错误信息**：
```
ModuleNotFoundError: No module named 'app'
```

**原因**：在**项目根目录**执行 `uv run python -m app.services.train.train_lvis`，但 `app` 包位于 `backend/` 子目录下，Python 无法找到。

**解决**：切换到 `backend/` 目录再执行：
```powershell
cd F:\AI-PhotoAlbum-ai-VLM\backend
uv run python -m app.services.train.train_lvis ...
```

---

## 问题 2：KeyError: 'file_name'（代码修改）

**错误信息**：
```
File "backend\app\services\train\data_converter.py", line 127, in convert_annotations
    img_name = os.path.splitext(img_info["file_name"])[0]
KeyError: 'file_name'
```

**原因**：LVIS v1 注解的 `images` 字段结构如下：
```json
{"id": 391895, "coco_url": "...", "width": 640, "height": 360, ...}
```
不包含 `file_name` 字段，脚本直接访问 `img_info["file_name"]` 导致 KeyError。

**修改文件**：`backend/app/services/train/data_converter.py` 第 127 行

**修改内容**：增加 fallback 逻辑，当 `file_name` 不存在时，从 `id` 推导 12 位零填充文件名（对应 COCO 图片命名规则，如 `id=391895` → `000000391895`）：

```python
# 修改前
img_name = os.path.splitext(img_info["file_name"])[0]

# 修改后
if "file_name" in img_info:
    img_name = os.path.splitext(img_info["file_name"])[0]
else:
    img_name = f"{img_info['id']:012d}"
```

---

## 问题 3：TypeError: 'optimize=auto' is of invalid type str（代码修改）

**错误信息**：
```
TypeError: 'optimize=auto' is of invalid type str. 'optimize' must be a bool
(i.e. 'optimize=True' or 'optimize=False')
```

**原因**：ultralytics 8.x 要求 `optimize` 参数为布尔值，而 `config.py` 中默认值设为字符串 `"auto"`，类型不匹配。

**修改文件**：`backend/app/services/train/config.py` 第 67 行

**修改内容**：
```python
# 修改前
optimize: str = "auto"

# 修改后
optimize: bool = False
```

---

## 问题 4：PyTorch CPU 版被误装，CUDA 不可用

**错误信息**：
```
ValueError: Invalid CUDA 'device=0' requested.
torch.cuda.is_available(): False
torch.cuda.device_count(): 0
```

**原因**：
- `uv pip install -r requirements.txt` 或清华镜像安装时，装入了 CPU 版 PyTorch（`torch-2.13.0+cpu`）
- 国内镜像（清华/阿里云）的 `torch` 默认是 CPU 版；PEP 440 规则下 `2.13.0` > `2.13.0+cu128`，pip 会优先选 CPU 版

**解决**：用 PyTorch 官方 wheel 源强制安装 CUDA 版（需加 `--force-reinstall --no-cache-dir`）：
```powershell
# 先安装 pip（uv 环境默认没有 pip）
uv pip install pip

# 用 PyTorch 官方 wheel 源安装 CUDA 版（不能用国内镜像作主源）
& ".venv\Scripts\python.exe" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128 --force-reinstall --no-cache-dir
```

**验证**：
```powershell
uv run python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
# 期望输出：2.13.0+cu128 / True
```

---

## 问题 5：YOLO 训练报 No labels found（代码修改）

**错误信息**：
```
FileNotFoundError: [Errno 2] No such file or directory: '...\train2017.cache'
ValueError: train: No labels found in ...\train2017.cache
```

**原因**：
- 标签文件生成到了 `data/models/lvis_finetuned/labels/train/`
- 但 Ultralytics YOLO 期望标签在图片目录的同级 `labels/` 下，即 `data/uploads/lvis/labels/train/`
- YOLO 通过图片路径自动推导标签路径（将路径中的 `images` 替换为 `labels`），两者不在同一根目录下导致找不到

**修改文件**：`backend/app/services/train/train_lvis.py` 第 123 行

**修改内容**：
```python
# 修改前
label_dir = os.path.join(config.output_dir, "labels")

# 修改后（标签与图片同根目录，YOLO 才能自动找到）
label_dir = os.path.join(config.lvis_root, "labels")
```

---

## 问题 6：YOLO 扫描显示 0 images, N backgrounds（标签目录名不匹配）

**错误信息**：
```
train: Scanning ...train2017... 0 images, 118287 backgrounds, 0 corrupt
ValueError: train: No labels found in ...\train2017.cache
```

**原因**：
- Ultralytics YOLO 自动推导标签路径时，要求**标签子目录名与图片子目录名完全一致**
- 图片目录：`data/uploads/lvis/train2017/` → YOLO 期望标签：`data/uploads/lvis/labels/train2017/`
- 但 `data_converter.py` 硬编码输出到 `labels/train/` 和 `labels/val/`，导致目录名不匹配

**修改文件**：`backend/app/services/train/data_converter.py` 第 247-248 行

**修改内容**：使用图片目录名（`train_img_rel`/`val_img_rel`）替代硬编码字符串：
```python
# 修改前
train_label_dir = os.path.join(output_label_dir, "train")
val_label_dir = os.path.join(output_label_dir, "val")

# 修改后（自动匹配图片目录名）
train_label_dir = os.path.join(output_label_dir, train_img_rel)
val_label_dir = os.path.join(output_label_dir, val_img_rel)
```

**临时修复**（已生成的标签目录需手动重命名）：
```powershell
Rename-Item "F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis\labels\train" "train2017"
Rename-Item "F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis\labels\val" "val2017"
```

---

## 问题 7：Ultralytics img2label_paths 要求图片路径含 \images\ 子目录（目录结构调整）

**错误信息**：
```
train: Scanning ...train2017... 0 images, 118287 backgrounds, 0 corrupt
ValueError: train: No labels found in ...\train2017.cache
```

**原因**：
- Ultralytics 的 `img2label_paths` 函数通过将路径中的 `\images\` 替换为 `\labels\` 来推导标签路径
- 原目录结构中图片直接放在 `train2017/` 下，路径不含 `\images\`，导致推导失败
- 标签被错误地推导为 `train2017/xxx.txt`（与图片同目录），而不是 `labels/train2017/xxx.txt`

**修改文件**：
- `backend/app/services/train/config.py`：更新图片目录路径
- `backend/app/services/train/data_converter.py`：标签目录使用 basename

**目录结构调整**：
```
# 修改前
data/uploads/lvis/
├── train2017/          ← 图片直接在这里
├── val2017/
└── labels/train2017/   ← 标签在这里

# 修改后（YOLO 标准结构）
data/uploads/lvis/
├── images/
│   ├── train2017/      ← 图片移到 images/ 下
│   └── val2017/
└── labels/
    ├── train2017/      ← 标签保持在这里
    └── val2017/
```

**代码修改**：
```python
# config.py：train_img_dir 和 val_img_dir
train_img_dir: str = "images/train2017"   # 原来是 "train2017"
val_img_dir: str = "images/val2017"        # 原来是 "val2017"

# data_converter.py：label_dir 使用 basename
train_label_dir = os.path.join(output_label_dir, os.path.basename(train_img_rel))
val_label_dir = os.path.join(output_label_dir, os.path.basename(val_img_rel))
```

**目录移动命令**：
```powershell
New-Item -ItemType Directory -Path "F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis\images" -Force
Move-Item "F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis\train2017" "F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis\images\train2017"
Move-Item "F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis\val2017" "F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis\images\val2017"
```

---

## 问题 8：resume 恢复训练时从第 1 轮重新开始（代码修改）

**错误现象**：
- 指定 `--resume <checkpoint>` 后，训练仍然从 epoch 1 开始，而不是继续之前的轮次
- 显示 `Epochs: 100`、`Batch: 16` 等 config 默认值，而非原始训练参数

**原因**：
- 脚本仅用 `YOLO(checkpoint_path)` 加载权重，但 `model.train(...)` 没有传 `resume=True`
- Ultralytics 必须显式传 `resume=True` 才能从 checkpoint 恢复训练状态（包括 epoch 计数、优化器状态等）

**修改文件**：`backend/app/services/train/train_lvis.py`

**修改内容**：
```python
# 修改前
results = model.train(data=yaml_path, epochs=config.epochs, ...)

# 修改后
if args.resume:
    # 恢复训练：使用 checkpoint 中的原始参数
    results = model.train(resume=True)
else:
    # 新训练：使用 config 参数
    results = model.train(data=yaml_path, epochs=config.epochs, ...)
```

**同时修改**：摘要打印逻辑，resume 时显示 checkpoint 路径而非 config 默认值：
```python
if args.resume:
    print(f"  Mode:        Resume")
    print(f"  Checkpoint:  {args.resume}")
else:
    print(f"  Mode:        New training")
    print(f"  Model:       {config.model_name}")
    print(f"  Epochs:      {config.epochs}")
    print(f"  Batch:       {config.batch}")
```

---

## 问题 9：save_period 默认值过高，中断后无法恢复（代码修改）

**现象**：训练 2 轮后按 Ctrl+C 中断，但找不到 checkpoint 文件用于恢复

**原因**：
- `config.py` 中 `save_period=10`，每 10 个 epoch 才保存一次 checkpoint
- 训练不到 10 轮就中断时，没有可用的 checkpoint

**修改文件**：`backend/app/services/train/config.py`

**修改内容**：
```python
# 修改前
save_period: int = 10

# 修改后（每 epoch 保存一次，确保中断后可恢复）
save_period: int = 1
```

---

## 问题 10：Windows 共享内存不足导致 dataloader 报错（可选修改）

**错误信息**：
```
RuntimeError: Couldn't open shared file mapping: <torch_xxx>, error code: <1455>
```

**原因**：
- `config.py` 中 `workers=8`，Windows 系统的分页文件（虚拟内存）不足以支持 8 个 dataloader 工作进程的共享内存
- 该错误发生在后台 worker 进程，**不会中断训练**，但可能导致部分批次数据加载回退到主进程

**可选修改**（如训练未被打断可不改）：

**修改文件**：`backend/app/services/train/config.py`

**修改内容**：
```python
# 当前值
workers: int = 8

# 推荐值（根据稳定性需求选择）
workers: int = 4   # 折中方案，速度较快且较稳定
workers: int = 2   # 保守方案，几乎不会报共享内存错误
workers: int = 0   # 单进程加载，最慢但最稳定
```

> **注**：此问题为非致命错误，训练可正常完成。如遇到训练意外中断，可尝试降低 workers 值。

---

## 问题 11：保存路径与模型名不统一（代码修改）

**现象**：
- 使用 `--model yolo26s.pt` 训练，但保存目录为 `lvis_yolo26n/`
- 容易引起混淆，以为训练的是 nano 模型

**原因**：
- `config.py` 中 `name` 默认值为 `"lvis_yolo26n"`，与 `model_name` 独立
- 两者没有自动关联

**修改文件**：`backend/app/services/train/train_lvis.py`

**修改内容**：在 config 解析后自动从模型名推导保存目录名：
```python
# 自动推导保存目录名：yolo26s.pt → lvis_yolo26s
if not args.resume:
    model_base = os.path.splitext(os.path.basename(config.model_name))[0]
    config.name = f"lvis_{model_base}"
```

**效果**：
| 模型参数 | 保存目录 |
|----------|----------|
| `yolo26n.pt` | `lvis_yolo26n/` |
| `yolo26s.pt` | `lvis_yolo26s/` |
| `yolo26m.pt` | `lvis_yolo26m/` |

> **注**：恢复训练时不会重新推导，使用 checkpoint 中的原始路径。

---

## 最终可用的训练命令

### 环境准备（首次运行）

```powershell
cd F:\AI-PhotoAlbum-ai-VLM\backend

# 安装训练依赖
uv pip install -r app/services/train/requirements.txt

# 安装 CUDA 版 PyTorch（RTX 4080 / CUDA 13.3）
uv pip install pip
& ".venv\Scripts\python.exe" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128 --force-reinstall --no-cache-dir
```

### 启动训练

```powershell
cd F:\AI-PhotoAlbum-ai-VLM\backend
uv run python -m app.services.train.train_lvis --model yolo26s.pt --epochs 10 --batch 8 --device 0
```

### 恢复训练（中断后继续）

```powershell
cd F:\AI-PhotoAlbum-ai-VLM\backend
uv run python -m app.services.train.train_lvis --resume "F:\AI-PhotoAlbum-ai-VLM\backend\runs\detect\lvis_finetune\lvis_yolo26n\weights\last.pt" --device 0
```

> **注**：恢复训练时无需指定 `--model`、`--epochs`、`--batch` 等参数，它们会从 checkpoint 中自动读取。

## 常用参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--model` | `yolo26n.pt` | 预训练模型（其他可选 yolo26s.pt / yolo26m.pt） |
| `--epochs` | `100` | 训练轮数 |
| `--batch` | `16` | 批次大小（显存不足时减小到 8 或 4） |
| `--device` | 自动 | `0` = GPU 0，`cpu` = CPU |
| `--lvis-root` | `data/uploads/lvis` | 数据根目录（默认即可） |
| `--max-categories` | `300` | 最多训练类别数 |
| `--resume` | 无 | 从 checkpoint 恢复训练 |
