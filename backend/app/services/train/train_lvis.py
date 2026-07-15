"""
YOLO LVIS fine-tuning script.

Usage:
    cd /path/to/project/root
    python -m app.services.train.train_lvis
    python -m app.services.train.train_lvis --model yolo26s.pt --epochs 50

This script:
  1. Converts LVIS annotations to YOLO format (/data/uploads/lvis → /data/models/lvis_finetuned/labels)
  2. Creates dataset YAML for Ultralytics YOLO
  3. Loads pretrained YOLO model
  4. Fine-tunes on LVIS dataset
  5. Saves model to /data/models/lvis_finetuned/
"""

import argparse
import os
import sys
from pathlib import Path


def get_project_root() -> str:
    """Get project root (where data/ lives)"""
    # Walk up from this file until we find data/ directory
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "data").is_dir() and (current / "backend").is_dir():
            return str(current)
        current = current.parent
    return str(Path.cwd())


def resolve_paths(config, project_root: str):
    """Resolve all relative paths in config to absolute"""
    def _abs(p):
        return p if os.path.isabs(p) else os.path.join(project_root, p)

    config.lvis_root = _abs(config.lvis_root)
    config.output_dir = _abs(config.output_dir)
    # Also resolve model_dir
    models_dir = os.path.join(project_root, "data", "models")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(config.output_dir, exist_ok=True)
    return config


def parse_args():
    """Parse command-line arguments (overrides config defaults)"""
    parser = argparse.ArgumentParser(description="Fine-tune YOLO on LVIS dataset")

    # Model
    parser.add_argument("--model", default="yolo26n.pt",
                        help="Pretrained YOLO model (e.g. yolo26n.pt, yolo26s.pt)")

    # Training
    parser.add_argument("--epochs", type=int, default=100,
                        help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16,
                        help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Training image size")
    parser.add_argument("--lr0", type=float, default=0.01,
                        help="Initial learning rate")
    parser.add_argument("--device", default="",
                        help='Training device: "0" for GPU 0, "cpu" for CPU, "" for auto')

    # Data
    parser.add_argument("--lvis-root", default="data/uploads/lvis",
                        help="LVIS dataset root directory")
    parser.add_argument("--output-dir", default="data/models/lvis_finetuned",
                        help="Output directory for trained model")
    parser.add_argument("--min-instances", type=int, default=10,
                        help="Minimum instances per LVIS category to include")
    parser.add_argument("--max-categories", type=int, default=300,
                        help="Maximum number of categories to train on")

    # Resume
    parser.add_argument("--resume", default="",
                        help="Resume from a previous checkpoint path")
    parser.add_argument("--pretrained", action="store_true", default=True,
                        help="Use pretrained weights")

    return parser.parse_args()


def main():
    """Entry point for YOLO LVIS fine-tuning"""
    args = parse_args()
    project_root = get_project_root()

    # ── Import config ──────────────────────────────────────
    sys.path.insert(0, os.path.join(project_root, "backend"))
    from app.services.train.config import TrainConfig, DataMeta
    from app.services.train.data_converter import prepare_lvis_dataset

    config = TrainConfig(
        model_name=args.model,
        lvis_root=args.lvis_root,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        lr0=args.lr0,
        device=args.device,
        min_instances=args.min_instances,
        max_categories=args.max_categories,
    )
    config = resolve_paths(config, project_root)

    # Auto-derive save directory name from model name
    # yolo26n.pt → lvis_yolo26n, yolo26s.pt → lvis_yolo26s
    if not args.resume:
        model_base = os.path.splitext(os.path.basename(config.model_name))[0]
        config.name = f"lvis_{model_base}"

    print("=" * 60)
    print(f"YOLO LVIS Fine-tuning")
    print(f"  Project root: {project_root}")
    print(f"  LVIS data:   {config.lvis_root}")
    print(f"  Output dir:  {config.output_dir}")
    if args.resume:
        print(f"  Mode:        Resume")
        print(f"  Checkpoint:  {args.resume}")
    else:
        print(f"  Mode:        New training")
        print(f"  Model:       {config.model_name}")
        print(f"  Epochs:      {config.epochs}")
        print(f"  Batch:       {config.batch}")
    print(f"  Image size:  {config.imgsz}")
    print("=" * 60)

    # ── Step 1: Convert LVIS to YOLO format ────────────────
    # Labels must be in <img_root>/labels/ for YOLO to find them
    label_dir = os.path.join(config.lvis_root, "labels")
    yaml_path = os.path.join(config.output_dir, "dataset.yaml")

    if not os.path.exists(config.lvis_root):
        print(f"\n[ERROR] LVIS dataset not found at: {config.lvis_root}")
        print("Please download LVIS dataset and place it at the specified path.")
        print("  LVIS v1: https://www.lvisdataset.org/dataset")
        sys.exit(1)

    print(f"\n[Step 1/4] Converting LVIS annotations to YOLO format...")
    data_meta = prepare_lvis_dataset(
        lvis_root=config.lvis_root,
        train_ann_rel=config.train_ann,
        val_ann_rel=config.val_ann,
        train_img_rel=config.train_img_dir,
        val_img_rel=config.val_img_dir,
        output_label_dir=label_dir,
        output_yaml_path=yaml_path,
        min_instances=config.min_instances,
        max_categories=config.max_categories,
    )

    # ── Step 2: Load pretrained YOLO model ─────────────────
    print(f"\n[Step 2/4] Loading pretrained YOLO model: {config.model_name}...")
    from ultralytics import YOLO

    if args.resume:
        print(f"  Resuming from checkpoint: {args.resume}")
        model = YOLO(args.resume)
    else:
        model = YOLO(config.model_name)

    # ── Step 3: Fine-tune on LVIS ──────────────────────────
    print(f"\n[Step 3/4] Starting fine-tuning...")
    print(f"  Dataset: {data_meta['nc']} classes, {os.path.basename(yaml_path)}")

    if args.resume:
        # Resume: use checkpoint's original training params
        results = model.train(resume=True)
    else:
        # Fresh training: use config params
        results = model.train(
            data=yaml_path,
            epochs=config.epochs,
            batch=config.batch,
            imgsz=config.imgsz,
            lr0=config.lr0,
            lrf=config.lrf,
            warmup_epochs=config.warmup_epochs,
            weight_decay=config.weight_decay,
            cos_lr=config.cos_lr,
            device=config.device,
            workers=config.workers,
            patience=config.patience,
            project=config.project,
            name=config.name,
            exist_ok=config.exist_ok,
            pretrained=config.pretrained,
            optimize=config.optimize,
            save_period=config.save_period,
            val=config.val,
            amp=config.amp,
            # Augmentation
            hsv_h=config.hsv_h,
            hsv_s=config.hsv_s,
            hsv_v=config.hsv_v,
            degrees=config.degrees,
            translate=config.translate,
            scale=config.scale,
            shear=config.shear,
            perspective=config.perspective,
            flipud=config.flipud,
            fliplr=config.fliplr,
            mosaic=config.mosaic,
            mixup=config.mixup,
        )

    # ── Step 4: Export and save model ──────────────────────
    print(f"\n[Step 4/4] Saving fine-tuned model...")

    # Ultralytics saves to runs/detect/train*/weights/best.pt
    # Copy to our output directory
    import shutil

    # Find the latest training run
    runs_dir = os.path.join(project_root, "runs", "detect")
    if os.path.exists(runs_dir):
        train_dirs = sorted(
            [d for d in os.listdir(runs_dir) if d.startswith(config.name)],
            key=lambda d: os.path.getmtime(os.path.join(runs_dir, d)),
        )
        if train_dirs:
            latest_run = os.path.join(runs_dir, train_dirs[-1])
            best_pt = os.path.join(latest_run, "weights", "best_pt.pt")
            last_pt = os.path.join(latest_run, "weights", "last_pt.pt")
            # Actually check for pt file (Ultralytics saves as best.pt)
            best_pt = os.path.join(latest_run, "weights", "best.pt")
            last_pt = os.path.join(latest_run, "weights", "last.pt")

            for src_name, dst_name in [("best.pt", "best.pt"), ("last.pt", "last.pt")]:
                src = os.path.join(latest_run, "weights", src_name)
                if os.path.exists(src):
                    dst = os.path.join(config.output_dir, dst_name)
                    shutil.copy2(src, dst)
                    print(f"  Saved: {dst}")

    # Also export the model
    try:
        export_path = os.path.join(config.output_dir, "model.onnx")
        model.export(format="onnx", imgsz=config.imgsz)
        # Move ONNX file to output dir
        onnx_src = os.path.join(project_root, config.model_name.replace(".pt", ".onnx"))
        if os.path.exists(onnx_src):
            shutil.move(onnx_src, os.path.join(config.output_dir, "model.onnx"))
            print(f"  Exported: {export_path}")
    except Exception as e:
        print(f"  ONNX export skipped: {e}")

    # Save dataset meta alongside the model
    meta_path = os.path.join(config.output_dir, "dataset_meta.yaml")
    import yaml
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump({
            "nc": data_meta["nc"],
            "names": data_meta["names"],
            "source": "LVIS v1",
            "model": config.model_name,
            "epochs": config.epochs,
        }, f, default_flow_style=False, allow_unicode=True)

    print(f"\n{'=' * 60}")
    print(f"Fine-tuning complete!")
    print(f"  Model:  {config.output_dir}/best.pt")
    print(f"  YAML:   {yaml_path}")
    print(f"  Meta:   {meta_path}")
    print(f"  Labels: {label_dir}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
