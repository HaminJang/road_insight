"""
AI Hub road-damage JSON to YOLO dataset converter.

Key improvements over the MVP script:
- Creates train/val/test splits.
- Keeps negative/background images by writing empty label files.
- Validates normalized YOLO bboxes.
- Copies images into YOLO-standard folders.
- Generates dataset/pothole.yaml automatically.

Example:
    python ml/convert_to_yolo.py \
        --json-dir ml/data/raw \
        --image-dir ml/data/images \
        --output-dir ml/dataset \
        --include-negative
"""

import argparse
import json
import os
import random
import shutil
from pathlib import Path
from typing import Any


POTHOLE_CATEGORY_ID = 8
CLASS_MAP = {POTHOLE_CATEGORY_ID: 0}
CLASS_NAMES = {0: "pothole"}


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def convert_bbox_to_yolo(bbox: list[float], img_width: int, img_height: int):
    x, y, w, h = bbox
    x_center = (x + w / 2) / img_width
    y_center = (y + h / 2) / img_height
    w_norm = w / img_width
    h_norm = h / img_height
    return x_center, y_center, w_norm, h_norm


def valid_yolo_bbox(values: tuple[float, float, float, float]) -> bool:
    x_center, y_center, w_norm, h_norm = values

    if w_norm <= 0 or h_norm <= 0:
        return False

    return all(0.0 <= value <= 1.0 for value in values)


def get_image_record(data: dict[str, Any]) -> dict[str, Any]:
    images = data.get("images")

    if isinstance(images, list):
        if not images:
            raise ValueError("JSON images list is empty")
        return images[0]

    if isinstance(images, dict):
        return images

    raise ValueError("JSON does not contain a valid images field")


def make_image_index(image_dir: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}

    if not image_dir.exists():
        return index

    for path in image_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            index[path.name] = path
            index[path.stem] = path

    return index


def find_image_path(img_filename: str, image_index: dict[str, Path]) -> Path | None:
    candidate = image_index.get(img_filename)
    if candidate:
        return candidate

    stem = Path(img_filename).stem
    return image_index.get(stem)


def parse_yolo_lines(json_path: Path, include_negative: bool) -> tuple[str, list[str], bool]:
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    image_record = get_image_record(data)
    img_width = int(image_record["width"])
    img_height = int(image_record["height"])
    img_filename = image_record["file_name"]

    annotations = data.get("annotations", [])
    yolo_lines: list[str] = []

    for ann in annotations:
        category_id = ann.get("category_id")
        if category_id not in CLASS_MAP:
            continue

        class_id = CLASS_MAP[category_id]
        yolo_bbox = convert_bbox_to_yolo(ann["bbox"], img_width, img_height)

        if not valid_yolo_bbox(yolo_bbox):
            continue

        x_c, y_c, w, h = yolo_bbox
        yolo_lines.append(f"{class_id} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}")

    has_pothole = len(yolo_lines) > 0

    if not has_pothole and not include_negative:
        return img_filename, [], False

    return img_filename, yolo_lines, True


def split_items(items: list[tuple[Path, str, list[str]]], seed: int):
    rng = random.Random(seed)
    shuffled = items[:]
    rng.shuffle(shuffled)

    total = len(shuffled)
    train_end = int(total * 0.8)
    val_end = int(total * 0.9)

    return {
        "train": shuffled[:train_end],
        "val": shuffled[train_end:val_end],
        "test": shuffled[val_end:],
    }


def prepare_output_dirs(output_dir: Path):
    for split in ["train", "val", "test"]:
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)


def write_yaml(output_dir: Path):
    yaml_text = """path: .
train: images/train
val: images/val
test: images/test

nc: 1
names:
  0: pothole
"""
    (output_dir / "pothole.yaml").write_text(yaml_text, encoding="utf-8")


def convert_dataset(
    json_dir: Path,
    image_dir: Path,
    output_dir: Path,
    include_negative: bool,
    seed: int,
):
    json_files = sorted(json_dir.rglob("*.json"))
    image_index = make_image_index(image_dir)

    items: list[tuple[Path, str, list[str]]] = []
    missing_images = 0
    skipped = 0

    for json_path in json_files:
        try:
            img_filename, yolo_lines, keep = parse_yolo_lines(json_path, include_negative)
        except Exception as exc:
            print(f"[WARN] JSON 파싱 실패: {json_path} ({exc})")
            skipped += 1
            continue

        if not keep:
            skipped += 1
            continue

        image_path = find_image_path(img_filename, image_index)
        if not image_path:
            missing_images += 1
            print(f"[WARN] 이미지 파일을 찾지 못했습니다: {img_filename}")
            continue

        items.append((image_path, img_filename, yolo_lines))

    prepare_output_dirs(output_dir)
    splits = split_items(items, seed)

    for split_name, split_items_list in splits.items():
        for image_path, img_filename, yolo_lines in split_items_list:
            image_dst = output_dir / "images" / split_name / image_path.name
            label_dst = output_dir / "labels" / split_name / f"{Path(img_filename).stem}.txt"

            shutil.copy2(image_path, image_dst)
            label_dst.write_text("\n".join(yolo_lines) + ("\n" if yolo_lines else ""), encoding="utf-8")

    write_yaml(output_dir)

    print("변환 완료")
    print(f"전체 JSON: {len(json_files)}개")
    print(f"변환 대상 이미지: {len(items)}개")
    print(f"누락 이미지: {missing_images}개")
    print(f"스킵 JSON: {skipped}개")
    for split_name, split_items_list in splits.items():
        positive = sum(1 for _, _, lines in split_items_list if lines)
        negative = len(split_items_list) - positive
        print(f"{split_name}: {len(split_items_list)}개 / positive {positive} / negative {negative}")
    print(f"YOLO YAML: {output_dir / 'pothole.yaml'}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-dir", default="ml/data/raw")
    parser.add_argument("--image-dir", default="ml/data/images")
    parser.add_argument("--output-dir", default="ml/dataset")
    parser.add_argument("--include-negative", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    convert_dataset(
        json_dir=Path(args.json_dir),
        image_dir=Path(args.image_dir),
        output_dir=Path(args.output_dir),
        include_negative=args.include_negative,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
