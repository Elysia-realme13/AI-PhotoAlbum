"""
LVIS dataset converter — converts LVIS JSON annotations to YOLO format.

LVIS annotation format (COCO-style JSON):
  {
    "images": [{"id": int, "file_name": str, "width": int, "height": int}, ...],
    "annotations": [{"id": int, "image_id": int, "category_id": int,
                     "bbox": [x, y, w, h], "area": float, ...}, ...],
    "categories": [{"id": int, "name": str, "synset": str, ...}, ...]
  }

Output YOLO format (per image):
  labels/*.txt — one file per image, each line:
    class_id x_center y_center width height
  All values normalized to [0, 1].
"""

import json
import os
import shutil
from collections import Counter
from typing import List, Tuple, Optional

from tqdm import tqdm
import yaml


def parse_lvis_annotations(ann_path: str) -> dict:
    """Load and return LVIS JSON annotation file"""
    with open(ann_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_category_map(
    categories: List[dict],
    min_instances: int = 10,
    max_categories: int = 300,
    instance_counts: Optional[Counter] = None,
) -> Tuple[dict, dict]:
    """
    Build mapping from LVIS category_id -> YOLO class_id.

    Filters out rare categories (below min_instances) and limits to top-K.

    Args:
        categories: LVIS categories list
        min_instances: minimum annotation count to keep a category
        max_categories: limit to top-K most frequent categories
        instance_counts: Counter of {category_id: count} from annotations

    Returns:
        (lvis_to_yolo: {lvis_cat_id: yolo_class_id},
         yolo_names: {yolo_class_id: category_name})
    """
    if instance_counts is None:
        # All categories equally weighted
        instance_counts = Counter({c["id"]: 1 for c in categories})

    # Filter and sort by frequency
    cat_info = {}
    for c in categories:
        cid = c["id"]
        count = instance_counts.get(cid, 0)
        if count >= min_instances:
            cat_info[cid] = {"name": c["name"], "count": count}

    # Sort by frequency descending, limit
    sorted_cats = sorted(cat_info.items(), key=lambda x: -x[1]["count"])
    sorted_cats = sorted_cats[:max_categories]

    lvis_to_yolo = {}
    yolo_names = {}
    for yolo_id, (lvis_id, info) in enumerate(sorted_cats):
        lvis_to_yolo[lvis_id] = yolo_id
        yolo_names[yolo_id] = info["name"]

    return lvis_to_yolo, yolo_names


def convert_annotations(
    ann_path: str,
    img_dir: str,
    out_label_dir: str,
    lvis_to_yolo: dict,
) -> Counter:
    """
    Convert LVIS annotations to YOLO-format label files.

    For each image with annotations, writes a .txt file with lines:
        class_id x_center y_center width height
    All coordinates normalized to [0, 1].

    Args:
        ann_path: path to LVIS JSON annotation file
        img_dir: path to image directory (for verification)
        out_label_dir: output directory for .txt label files
        lvis_to_yolo: {lvis_cat_id: yolo_class_id} mapping

    Returns:
        Counter of {yolo_class_id: instance_count} for statistics
    """
    os.makedirs(out_label_dir, exist_ok=True)

    data = parse_lvis_annotations(ann_path)
    images = {img["id"]: img for img in data["images"]}
    annotations = data["annotations"]

    # Group annotations by image_id
    from collections import defaultdict
    img_anns = defaultdict(list)
    for ann in annotations:
        img_anns[ann["image_id"]].append(ann)

    class_counter = Counter()

    for img_id, ann_list in tqdm(img_anns.items(), desc=f"Converting {os.path.basename(ann_path)}"):
        img_info = images.get(img_id)
        if not img_info:
            continue

        img_w = img_info["width"]
        img_h = img_info["height"]
        if img_w == 0 or img_h == 0:
            continue

        # Image filename: LVIS uses image ID (zero-padded to 12 digits)
        # e.g. id=391895 → "000000391895"
        if "file_name" in img_info:
            img_name = os.path.splitext(img_info["file_name"])[0]
        else:
            img_name = f"{img_info['id']:012d}"
        label_path = os.path.join(out_label_dir, f"{img_name}.txt")

        lines = []
        for ann in ann_list:
            lvis_cat_id = ann["category_id"]
            yolo_id = lvis_to_yolo.get(lvis_cat_id)
            if yolo_id is None:
                continue  # filtered-out category

            # LVIS bbox: [x, y, width, height] (top-left corner)
            bx, by, bw, bh = ann["bbox"]

            # YOLO format: class_id x_center y_center width height (normalized)
            x_center = (bx + bw / 2) / img_w
            y_center = (by + bh / 2) / img_h
            bw_norm = bw / img_w
            bh_norm = bh / img_h

            # Clamp to [0, 1]
            x_center = max(0, min(1, x_center))
            y_center = max(0, min(1, y_center))
            bw_norm = max(0, min(1, bw_norm))
            bh_norm = max(0, min(1, bh_norm))

            lines.append(f"{yolo_id} {x_center:.6f} {y_center:.6f} {bw_norm:.6f} {bh_norm:.6f}")
            class_counter[yolo_id] += 1

        if lines:
            with open(label_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

    return class_counter


def create_dataset_yaml(
    yolo_names: dict,
    train_img_dir: str,
    val_img_dir: str,
    output_path: str,
) -> str:
    """
    Create a YOLO dataset YAML file.

    The YAML defines:
      - path: root directory (empty, use absolute paths for train/val)
      - train: absolute path to training images
      - val: absolute path to validation images
      - nc: number of classes
      - names: list of class names

    Args:
        yolo_names: {class_id: class_name}
        train_img_dir: absolute path to training images
        val_img_dir: absolute path to validation images
        output_path: where to save the YAML

    Returns:
        output_path
    """
    nc = len(yolo_names)
    names = [yolo_names[i] for i in range(nc)]

    dataset_dict = {
        "path": "",  # not used, train/val are absolute
        "train": train_img_dir,
        "val": val_img_dir,
        "nc": nc,
        "names": names,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(dataset_dict, f, default_flow_style=False, allow_unicode=True)

    print(f"Dataset YAML saved to: {output_path}")
    print(f"  Classes: {nc}")
    print(f"  Names sample: {names[:5]}...")

    return output_path


def prepare_lvis_dataset(
    lvis_root: str,
    train_ann_rel: str,
    val_ann_rel: str,
    train_img_rel: str,
    val_img_rel: str,
    output_label_dir: str,
    output_yaml_path: str,
    min_instances: int = 10,
    max_categories: int = 300,
) -> dict:
    """
    Full pipeline: parse LVIS → filter categories → convert labels → create YAML.

    Args:
        lvis_root: absolute path to LVIS dataset root
        train_ann_rel: train annotation JSON path (relative to lvis_root)
        val_ann_rel: val annotation JSON path (relative to lvis_root)
        train_img_rel: train image directory (relative to lvis_root)
        val_img_rel: val image directory (relative to lvis_root)
        output_label_dir: where to save YOLO labels (absolute)
        output_yaml_path: where to save dataset YAML (absolute)
        min_instances: min instances per category
        max_categories: max categories to include

    Returns:
        {"nc": int, "names": list, "yaml_path": str,
         "train_labels": str, "val_labels": str,
         "train_images": str, "val_images": str}
    """
    train_ann = os.path.join(lvis_root, train_ann_rel)
    val_ann = os.path.join(lvis_root, val_ann_rel)
    train_img_dir = os.path.join(lvis_root, train_img_rel)
    val_img_dir = os.path.join(lvis_root, val_img_rel)
    train_label_dir = os.path.join(output_label_dir, os.path.basename(train_img_rel))
    val_label_dir = os.path.join(output_label_dir, os.path.basename(val_img_rel))

    # Step 1: Parse train annotations to count instances per category
    train_data = parse_lvis_annotations(train_ann)

    instance_counts = Counter()
    for ann in train_data["annotations"]:
        instance_counts[ann["category_id"]] += 1

    # Step 2: Build category mapping
    lvis_to_yolo, yolo_names = build_category_map(
        train_data["categories"],
        min_instances=min_instances,
        max_categories=max_categories,
        instance_counts=instance_counts,
    )

    print(f"Categories: {len(train_data['categories'])} LVIS → "
          f"{len(lvis_to_yolo)} YOLO (filtered)")

    # Step 3: Convert training annotations
    train_counts = convert_annotations(
        train_ann, train_img_dir, train_label_dir, lvis_to_yolo
    )

    # Step 4: Convert validation annotations
    val_counts = convert_annotations(
        val_ann, val_img_dir, val_label_dir, lvis_to_yolo
    )

    # Step 5: Create dataset YAML
    create_dataset_yaml(
        yolo_names,
        train_img_dir,
        val_img_dir,
        output_yaml_path,
    )

    print(f"Training instances converted: {sum(train_counts.values())}")
    print(f"Validation instances converted: {sum(val_counts.values())}")

    return {
        "nc": len(yolo_names),
        "names": [yolo_names[i] for i in range(len(yolo_names))],
        "yaml_path": output_yaml_path,
        "train_labels": train_label_dir,
        "val_labels": val_label_dir,
        "train_images": train_img_dir,
        "val_images": val_img_dir,
    }
