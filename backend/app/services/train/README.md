## 完成结构

```
backend/app/services/train/
├── __init__.py                # 包声明
├── requirements.txt           # 训练依赖清单
├── config.py                  # 训练超参数配置（dataclass）
├── data_converter.py          # LVIS → YOLO 格式转换
└── train_lvis.py              # 主训练脚本
```

## 各文件说明

### `requirements.txt`

```
ultralytics>=8.3.0    # YOLO 模型框架
torch>=2.1.0          # 深度学习框架
pycocotools>=2.0.7    # COCO/LVIS 注解解析
numpy, Pillow, tqdm   # 数据处理
PyYAML>=6.0           # 数据集 YAML 生成
```

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
Step 2/4: 加载预训练模型（自动下载 yolo11n.pt）
Step 3/4: 执行 fine-tuning（调用 model.train()）
Step 4/4: 保存最佳模型到 /data/models/lvis_finetuned/
```

**使用方法**：

使用前先下载数据集！！！
https://www.lvisdataset.org/dataset

```bash
cd /path/to/project

# 基础训练
uv run python -m app.services.train.train_lvis

# 自定义参数
uv run python -m app.services.train.train_lvis \
  --model yolo11s.pt \
  --epochs 50 \
  --batch 8 \
  --device 0

# 从 checkpoint 恢复
uv run python -m app.services.train.train_lvis \
  --resume /data/models/lvis_finetuned/weights/last.pt
```

**数据目录约定**：

```
/data/uploads/lvis/                         ← LVIS 原始数据集
├── train2017/                              ← 训练图片
├── val2017/                                ← 验证图片
└── annotations/
    ├── lvis_v1_train.json                  ← LVIS 训练注解
    └── lvis_v1_val.json                    ← LVIS 验证注解

/data/models/lvis_finetuned/                ← 训练输出
├── labels/train/                           ← YOLO 格式标签
├── labels/val/
├── dataset.yaml                            ← YOLO 数据集描述
├── best.pt                                 ← 最佳模型权重
├── last.pt                                 ← 最后一个 epoch 权重
└── dataset_meta.yaml                       ← 训练元信息
```