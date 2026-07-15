# YOLO LVIS 模型训练指南

## 项目概述

使用 YOLO 在 LVIS 数据集上进行目标检测模型微调（fine-tuning）。

## 环境要求

- **Python 3.12 64 位**（32 位无法安装 PyTorch）
- **Windows 11 / Linux**
- **NVIDIA GPU（推荐）**，CUDA 支持

验证 Python 是否为 64 位：
```powershell
python -c "import struct; print('64-bit' if struct.calcsize('P') == 8 else '32-bit')"
```

## 1. 安装 64 位 Python

如果当前是 32 位，使用 winget 安装 64 位：
```powershell
winget install Python.Python.3.12 --architecture x64
```

## 2. 安装依赖

```bash
cd F:\AI-PhotoAlbum-ai-VLM\backend\app\services\train
pip install -r requirements.txt
```

核心依赖：`ultralytics>=8.3.0`、`torch>=2.1.0`、`pycocotools>=2.0.7`、`PyYAML>=6.0` 等。

验证安装：
```powershell
python -c "import torch; print(f'PyTorch {torch.__version__}'); print(f'CUDA 可用: {torch.cuda.is_available()}')"
```

## 3. 目录架构

```
F:/AI-PhotoAlbum-ai-VLM/                    ← 项目根目录（脚本自动定位）
├── backend/
│   └── app/services/train/                 ← 训练脚本
│       ├── __init__.py
│       ├── requirements.txt
│       ├── config.py                       ← 超参数配置
│       ├── data_converter.py               ← LVIS → YOLO 格式转换
│       └── train_lvis.py                   ← 主训练脚本
├── frontend/
├── data/
│   ├── uploads/lvis/                       ← LVIS 数据集根目录
│   │   ├── images/                         ← 图片（YOLO 要求含 images 子目录）
│   │   │   ├── train2017/                  ← 训练图片 (100,170 张, 18 GB)
│   │   │   └── val2017/                    ← 验证图片 (19,809 张, 1 GB)
│   │   ├── labels/                         ← YOLO 格式标签（自动生成）
│   │   │   ├── train2017/                  ← 训练标签
│   │   │   └── val2017/                    ← 验证标签
│   │   └── annotations/
│   │       ├── lvis_v1_train.json          ← 训练注解 (1 GB)
│   │       └── lvis_v1_val.json            ← 验证注解 (192 MB)
│   └── models/lvis_finetuned/              ← 训练输出（自动生成）
│       ├── dataset.yaml                    ← YOLO 数据集描述
│       ├── best.pt                         ← 最佳模型权重
│       ├── last.pt                         ← 最后一个 epoch 权重
│       └── dataset_meta.yaml               ← 训练元信息
└── docker-compose.yml
```

### 创建目录命令：
```powershell
mkdir -p "F:/AI-PhotoAlbum-ai-VLM/data/uploads/lvis/images/train2017"
mkdir -p "F:/AI-PhotoAlbum-ai-VLM/data/uploads/lvis/images/val2017"
mkdir -p "F:/AI-PhotoAlbum-ai-VLM/data/uploads/lvis/annotations"
```

> **注意**：`data/` 必须放在项目根目录，不能放在 `train/` 下面。脚本 `get_project_root()` 会向上查找同时包含 `data/` 和 `backend/` 的目录。

## 4. 下载数据集

需要下载 **4 个文件**：

| 文件 | 大小 | 来源 |
|------|------|------|
| `lvis_v1_train.json` | ~1 GB | [LVIS 官网](https://www.lvisdataset.org/dataset) |
| `lvis_v1_val.json` | ~192 MB | [LVIS 官网](https://www.lvisdataset.org/dataset) |
| `train2017.zip` | ~18 GB | [COCO 官网](http://images.cocodataset.org/zips/train2017.zip) |
| `val2017.zip` | ~1 GB | [COCO 官网](http://images.cocodataset.org/zips/val2017.zip) |

> LVIS 注解文件是 HTTPS，浏览器直接下载。
> COCO 图片是 HTTP，浏览器可能拦截，用以下方式下载。

### 下载方式

**方法一：Python 下载（推荐）**
```powershell
python -c "import urllib.request; urllib.request.urlretrieve('http://images.cocodataset.org/zips/train2017.zip', r'F:\AI-PhotoAlbum-ai-VLM\data\coco_train2017.zip')"
python -c "import urllib.request; urllib.request.urlretrieve('http://images.cocodataset.org/zips/val2017.zip', r'F:\AI-PhotoAlbum-ai-VLM\data\coco_val2017.zip')"
```

**方法二：curl.exe（Windows 自带）**
```powershell
curl.exe -L -o "F:\AI-PhotoAlbum-ai-VLM\data\coco_train2017.zip" "http://images.cocodataset.org/zips/train2017.zip"
curl.exe -L -o "F:\AI-PhotoAlbum-ai-VLM\data\coco_val2017.zip" "http://images.cocodataset.org/zips/val2017.zip"
```

**方法三：国内清华镜像（速度更快）**
```powershell
Invoke-WebRequest -Uri "https://mirrors.tuna.tsinghua.edu.cn/coco/train2017.zip" -OutFile "F:\AI-PhotoAlbum-ai-VLM\data\coco_train2017.zip"
```

### 解压
```powershell
# PowerShell Expand-Archive
Expand-Archive -Path "F:\AI-PhotoAlbum-ai-VLM\data\coco_train2017.zip" -DestinationPath "F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis\"
Expand-Archive -Path "F:\AI-PhotoAlbum-ai-VLM\data\coco_val2017.zip" -DestinationPath "F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis\"

# 或使用 7-Zip
7z x "F:\AI-PhotoAlbum-ai-VLM\data\coco_train2017.zip" -o"F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis"
7z x "F:\AI-PhotoAlbum-ai-VLM\data\coco_val2017.zip" -o"F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis"
```

注解文件 `lvis_v1_train.json` 和 `lvis_v1_val.json` 直接放入：
```
F:\AI-PhotoAlbum-ai-VLM\data\uploads\lvis\annotations\
```

## 5. 训练命令

在 **backend/** 目录执行：

```powershell
cd F:\AI-PhotoAlbum-ai-VLM\backend

# 基础训练（默认参数）
uv run python -m app.services.train.train_lvis --device 0

# 自定义参数
uv run python -m app.services.train.train_lvis --model yolo26s.pt --epochs 50 --batch 8 --device 0

# 从 checkpoint 恢复
uv run python -m app.services.train.train_lvis --resume "F:\AI-PhotoAlbum-ai-VLM\backend\runs\detect\lvis_yolo26s\weights\last.pt" --device 0
```

## 6. GPU 指定

`--device` 参数用法：

| 参数值 | 说明 |
|--------|------|
| `--device 0` | 使用 GPU 0（独显） |
| `--device 0,1` | 多 GPU 并行 |
| `--device cpu` | 使用 CPU |
| 不传或 `""` | 自动选择 |

> Windows 上 PyTorch CUDA 只能识别 NVIDIA 独显（核显不支持 CUDA），所以 `--device 0` 就是独显，无需额外配置。

## 7. 训练流程

脚本自动执行 4 步：

| 步骤 | 说明 |
|------|------|
| Step 1/4 | 转换 LVIS 注解为 YOLO 格式（过滤低频类别，保留 Top-300） |
| Step 2/4 | 加载预训练模型（自动下载 yolo26n.pt） |
| Step 3/4 | 执行 fine-tuning |
| Step 4/4 | 保存最佳模型到 `data/models/lvis_finetuned/` |

## 8. 可调参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--model` | `yolo26n.pt` | 预训练模型（可选 yolo26s.pt / yolo26n.pt） |
| `--epochs` | `100` | 训练轮数 |
| `--batch` | `16` | 批次大小 |
| `--imgsz` | `640` | 训练图片尺寸 |
| `--lr0` | `0.01` | 初始学习率 |
| `--device` | `""` | 训练设备 |
| `--min-instances` | `10` | 类别最少实例数（低于此值过滤） |
| `--max-categories` | `300` | 最多训练类别数 |
| `--resume` | `""` | 从 checkpoint 恢复 |

完整参数见 `config.py` 的 `TrainConfig` 类（约 40 个参数，含数据增强等）。

## 9. 训练输出

```
data/uploads/lvis/labels/                   ← YOLO 格式标签（自动生成）
├── train2017/                              ← 训练标签
└── val2017/                                ← 验证标签

data/models/lvis_finetuned/                 ← 模型输出
├── best.pt                                 ← 最佳模型权重
├── last.pt                                 ← 最后一个 epoch 权重
├── model.onnx                              ← ONNX 导出
├── dataset.yaml                            ← 数据集描述
└── dataset_meta.yaml                       ← 训练元信息

backend/runs/detect/lvis_yolo26s/           ← 训练报告（自动生成）
├── results.png                             ← 训练曲线
├── confusion_matrix.png                    ← 混淆矩阵
├── F1_curve.png                            ← F1 曲线
├── PR_curve.png                            ← PR 曲线
└── weights/
    ├── best.pt                             ← 最佳权重
    └── last.pt                             ← 最新权重
```
