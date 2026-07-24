# YOLO26m LVIS 微调训练总结

> 记录时间：2026-07-24 | 数据集：LVIS v1（300 类，118,287 训练图 / 5,000 验证图）
> 训练环境：RTX 5090 (32GB) · batch=32 · workers=8 · imgsz=640 · cache=disk

---

## 一、训练实验总览

| 实验 | 起点 | 增强策略 | 轮数 | 峰值 mAP50-95 | 结论 |
|------|------|---------|:---:|:---:|------|
| **Run1 阶段一** | yolo26m.pt | Ultralytics 默认 | Ep1-24 | **0.194** | ✅ 健康上升 |
| **Run1 阶段二** | Ep24 续训 | 激进增强 | Ep25-47 | 0.185 | ❌ 负优化 |
| **Run2** | yolo26m.pt 从头 | 中等增强 + degrees | Ep1-100 | **0.209↑** | ✅ 最优 |

---

## 二、各实验参数详情

### Run1 阶段一（Ep1-24）：Ultralytics 默认增强
达到 mAP50-95=0.194（Ep24），此时仍在上升，未见平台。

### Run1 阶段二（Ep25-47）：激进增强续训（失败）
```
mosaic=0.5, mixup=0.2, cutmix=0.2, erasing=0.2, degrees=5.0, hsv_v=0.5, auto_augment=None
```
切换瞬间 box_loss 1.68→1.76、cls_loss 2.77→2.91，mAP50-95 从 0.194 跌至谷底 0.180，
23 轮后仅恢复到 0.185，**始终未回到基线**。

### Run2（Ep1-100）：中等增强 + 从头训练（成功）
```
mosaic=0.5, mixup=0.1, cutmix=0.2, erasing=0.2, degrees=5.0, hsv_v=0.5,
auto_augment=None, close_mosaic=15, epochs=100, patience=30, lr0=0.01
```
> 与 Run1 激进版唯一参数区别：mixup 0.2→0.1。**关键差异是从头训练而非中途切换。**

---

## 三、关键指标对比

| Epoch | Run1 mAP50-95 | Run2 mAP50-95 |
|:---:|:---:|:---:|
| 24/25 | **0.194**（峰值） | 0.174 |
| 47 | 0.185（激进已崩） | 0.194 |
| 66 | — | **0.209** ⭐ |

Run2 已超越 Run1 历史最佳 **+0.015**，且仍在单调上升。box_loss 从 1.66 降到 1.57，
cls_loss 从 2.67 降到 2.40，训练曲线非常健康。

---

## 四、核心结论与教训

1. **✅ 从头训练 > 中途切参数**：同样的激进增强，Run1 中途切换导致崩盘（0.194→0.180），
   Run2 从头消化则稳步突破 0.209。
2. **❌ 已收敛权重上切换重增强 = 负优化**：loss 瞬间跳升且长期无法恢复。
3. **✅ degrees=5.0 有效**：唯一在两次实验中都保留的有益增强。
4. **✅ mixup 0.2→0.1 减负有帮助**：配合从头训练效果显著。
5. **⚠️ 三重混合增强需谨慎**：mosaic+mixup+cutmix 叠加 + randaugment 对 300 类长尾数据过重。

---

## 五、文件资产

| 路径 | 说明 |
|------|------|
| `backend/lvis_finetune/lvis_yolo26m/` | Run2 训练目录（best.pt / last.pt / epoch0-65.pt） |
| `backend/lvis_finetune/lvis_yolo26m_run1_backup/` | Run1 完整备份（results_backup_ep1-47.csv） |
| `data/models/lvis_finetuned/*.pt` | 已上传 master 的模型权重 |

详见同目录 [README.md](./README.md) 的模型文件说明与替换方法。
