# YOLO26n LVIS Fine-tuning Results

## Model
- **Architecture**: YOLO26n (2.76M parameters)
- **Dataset**: LVIS v1 (300 classes, 118,287 train images)
- **Training**: 73 epochs on RTX 5090 (32GB)

## Final Metrics (Validation Set)

| Metric | Value |
|--------|-------|
| mAP50 | 0.2026 |
| mAP50-95 | 0.1394 |
| Precision | 0.3366 |
| Recall | 0.2510 |

## Training Config
- Batch: 72
- Workers: 16
- Image size: 640
- Learning rate: 0.01 (cosine schedule)
- Optimizer: SGD

## Files
- `best.pt` - Best model weights (epoch 73)
- `results.csv` - Training metrics per epoch
- `results.png` - Training curves
- `confusion_matrix.png` - Confusion matrix

## Hardware
- GPU: NVIDIA RTX 5090 (32GB VRAM)
- Training time: ~7 min/epoch, ~8.5 hours total
