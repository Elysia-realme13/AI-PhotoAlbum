# YOLO26m LVIS 微调模型

## 模型文件说明

| 文件 | Epoch | 增强参数 | mAP50 | mAP50-95 | 说明 |
|------|-------|---------|-------|----------|------|
| `yolo26m_lvis_ep24_original.pt` | 24 | 原始默认 | 0.268 | 0.194 | 原始训练最佳，mAP50-95 最高 |
| `best.pt` | 44 | 修改后 | 0.270 | 0.184 | 改参数后 best，mAP50-95 下降 |

## 性能对比

### 原始训练（Epoch 1-24，Ultralytics 默认增强参数）
- mAP50: 0.134 → 0.268（稳步上升）
- mAP50-95: 0.096 → 0.194（稳步上升）
- Precision: 0.386, Recall: 0.328

### 修改增强参数后（Epoch 25-47）
修改参数: mosaic=0.5, mixup=0.2, cutmix=0.2, erasing=0.2, hsv_v=0.5, auto_augment=None
- mAP50-95: 0.194 → 0.180（下降 -0.014），47 轮后仅恢复到 0.185（仍低于基线 -0.009）
- mAP50: 0.269 → 0.272（微涨 +0.003）
- Precision: 0.384 → 0.364（下降 -0.020）

**结论**: 修改增强参数导致 mAP50-95 显著下降且未恢复，不建议使用。

## 如何替换模型

### 1. 在后端服务中替换

将选择的模型文件复制到后端模型目录：

```bash
# 使用原始训练模型（推荐）
cp data/models/lvis_finetuned/yolo26m_lvis_ep24_original.pt backend/yolo26m_lvis.pt

# 或使用改参数后模型（不推荐）
cp data/models/lvis_finetuned/best.pt backend/yolo26m_lvis.pt
```

### 2. 在配置中指定模型路径

修改 `backend/app/config/settings.py` 中的模型路径：

```python
MODEL_PATH = "yolo26m_lvis.pt"  # 或指定完整路径
```

### 3. 重启后端服务

```bash
cd backend
python main.py
```

## 模型详情

- **基础模型**: YOLO26m (yolo26m.pt)
- **数据集**: LVIS v1 (300 类, 118,287 训练图 / 5,000 验证图)
- **训练环境**: RTX 5090 (32GB), batch=32, workers=8
- **图像尺寸**: 640x640
