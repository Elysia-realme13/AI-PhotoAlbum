# 训练结果图对比（三个模型）

按模型区分存放，每个目录含完整官方图：`results.png`（训练曲线）、`confusion_matrix(_normalized).png`（混淆矩阵）、`Box{PR,F1,P,R}_curve.png`（PR/F1/P/R 曲线）、`results.csv`（原始指标）。

## 目录说明

| 目录 | 模型 | 轮数 | mAP50 | mAP50-95 | 说明 |
|------|------|:---:|:---:|:---:|------|
| `yolo26n/` | YOLO26n | 73 | 0.203 | 0.139 | 早期 nano 模型，精度基线最低 |
| `yolo26m_run1/` | YOLO26m Run1 | 47 | 0.272 | 0.185 | Ep1-24 默认增强(峰值0.194)，Ep25起激进增强导致负优化 |
| `yolo26m_run2_ep84/` | YOLO26m Run2 | 84 | **0.308** | **0.216** | 从头训练+中等增强，单调上升，当前最优 |

## 怎么看训练结果（推荐顺序）

1. **`results.png`（最直观）**：一图看全部指标随 epoch 变化——loss 下降、mAP 上升、是否过拟合。
   直接对比三个模型的 results.png 即可看出精度演进：0.139 → 0.185 → 0.216。
2. **`BoxPR_curve.png`**：PR 曲线，越靠右上越好，曲线下面积≈mAP50。
3. **`BoxF1_curve.png`**：F1 峰值点对应最佳置信度阈值，部署设阈值用。
4. `confusion_matrix_normalized.png`：看每类召回率（300类，关注对角线亮度）。

## 关键结论

- **Run2（yolo26m_run2_ep84）为当前最优**：mAP50-95=0.216，比 Run1 峰值(0.194)高 +0.022，且训练曲线健康单调上升。
- Run1 的 results.png 可清晰看到 Ep25 后激进增强导致的曲线掉头（负优化教训）。
- 对应模型权重见上级目录：`yolo26m_lvis_run2_ep84.pt`（Run2）、`yolo26m_lvis_ep24_original.pt`（Run1 Ep24）。

> 注：Run2 图基于 Ep84（训练尚未跑满 100 轮时的快照），后续跑完会更新。
