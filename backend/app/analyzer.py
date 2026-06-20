import io
import os
from typing import Any

import numpy as np
from PIL import Image
from ultralytics import YOLO


# =========================
# 1. Model / threshold settings
# =========================

MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "models/best.pt")
MODEL_VERSION = os.getenv(
    "MODEL_VERSION",
    "road-insight-yolo11n-pothole-v1"
)

DETECTION_CONF = float(os.getenv("DETECTION_CONF", "0.6"))
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.5"))
MAX_DETECTIONS = int(os.getenv("MAX_DETECTIONS", "20"))

model = YOLO(MODEL_PATH)


# =========================
# 2. Utility functions
# =========================

def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def get_class_name(class_id: int) -> str:
    """
    Convert YOLO class id into a readable class name.
    For a single-class pothole model, class_id is usually 0.
    """
    try:
        names = model.names

        if isinstance(names, dict):
            return names.get(class_id, f"class_{class_id}")

        if isinstance(names, list) and class_id < len(names):
            return names[class_id]

        return f"class_{class_id}"
    except Exception:
        if class_id == 0:
            return "pothole"
        return f"class_{class_id}"


def calculate_center_weight(
    bbox: list[float],
    image_width: int,
    image_height: int
) -> float:
    """
    Give a higher weight to detections near the center/lower part of the image.
    This approximates whether the road damage is close to a likely vehicle path.
    """
    x1, y1, x2, y2 = bbox

    center_x = ((x1 + x2) / 2) / image_width
    center_y = ((y1 + y2) / 2) / image_height

    # Closer to horizontal center is more risky.
    x_weight = 1.0 - min(abs(center_x - 0.5) / 0.5, 1.0)

    # Lower in the image is more likely to be in the vehicle path.
    y_weight = clamp((center_y - 0.35) / 0.65, 0.0, 1.0)

    center_weight = 0.6 * x_weight + 0.4 * y_weight

    return round(center_weight, 4)


def calculate_risk_score(
    confidence: float,
    area_ratio: float,
    bbox: list[float],
    image_width: int,
    image_height: int
) -> float:
    """
    Road-risk score.

    Previous MVP formula:
        confidence * area_ratio * 1000

    Improved MVP formula:
        AI confidence + damage area + position risk
    """
    # If a box covers 5% or more of the image, cap area risk at maximum.
    area_score = min(area_ratio / 0.05, 1.0)

    center_weight = calculate_center_weight(
        bbox=bbox,
        image_width=image_width,
        image_height=image_height
    )

    risk_score = (
        45 * confidence +
        35 * area_score +
        20 * center_weight
    )

    return round(min(risk_score, 100.0), 2)


# =========================
# 3. Image quality check
# =========================

def check_image_quality(image_bytes: bytes) -> tuple[bool, str]:
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    brightness = np.array(img).mean()

    if brightness < 50:
        return False, "조명이 부족합니다. 밝은 곳에서 촬영해주세요"

    if brightness > 220:
        return False, "역광입니다. 햇빛을 등지고 촬영해주세요"

    return True, "ok"


# =========================
# 4. YOLO analysis main function
# =========================

def analyze_image(image_bytes: bytes) -> dict[str, Any]:
    """
    Analyze one image and return both a legacy single-result summary and
    an improved multi-detection result list.
    """

    ok, message = check_image_quality(image_bytes)

    if not ok:
        return {
            "detected": False,
            "confidence": 0.0,
            "area_ratio": 0.0,
            "damage_score": 0.0,
            "bbox": None,
            "detections": [],
            "detection_count": 0,
            "model_version": MODEL_VERSION,
            "threshold": DETECTION_CONF,
            "message": message
        }

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_width, image_height = img.size
    image_area = image_width * image_height

    results = model.predict(
        source=img,
        conf=DETECTION_CONF,
        iou=IOU_THRESHOLD,
        max_det=MAX_DETECTIONS,
        verbose=False
    )

    detections: list[dict[str, Any]] = []

    for result in results:
        if result.boxes is None:
            continue

        for box in result.boxes:
            confidence = float(box.conf[0])

            # model.predict(conf=DETECTION_CONF) already filters this,
            # but keep this guard for consistency.
            if confidence < DETECTION_CONF:
                continue

            class_id = int(box.cls[0]) if box.cls is not None else 0
            class_name = get_class_name(class_id)

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            # Clamp boxes to image bounds.
            x1 = clamp(float(x1), 0.0, float(image_width))
            y1 = clamp(float(y1), 0.0, float(image_height))
            x2 = clamp(float(x2), 0.0, float(image_width))
            y2 = clamp(float(y2), 0.0, float(image_height))

            bbox = [x1, y1, x2, y2]

            box_width = max(x2 - x1, 0.0)
            box_height = max(y2 - y1, 0.0)
            box_area = box_width * box_height
            area_ratio = box_area / image_area if image_area > 0 else 0.0

            risk_score = calculate_risk_score(
                confidence=confidence,
                area_ratio=area_ratio,
                bbox=bbox,
                image_width=image_width,
                image_height=image_height
            )

            detections.append({
                "class_id": class_id,
                "class_name": class_name,
                "confidence": round(confidence, 4),
                "bbox": [round(v, 2) for v in bbox],
                "area_ratio": round(area_ratio, 4),
                "risk_score": risk_score
            })

    # Highest-risk detections first.
    detections.sort(
        key=lambda item: (item["risk_score"], item["confidence"]),
        reverse=True
    )

    detected = len(detections) > 0
    primary = detections[0] if detected else None

    message = (
        f"도로 위험 요소 {len(detections)}건 감지됨"
        if detected else
        "포트홀 미감지"
    )

    return {
        # Legacy summary for existing frontend compatibility.
        "detected": detected,
        "confidence": primary["confidence"] if primary else 0.0,
        "area_ratio": primary["area_ratio"] if primary else 0.0,
        "damage_score": primary["risk_score"] if primary else 0.0,
        "bbox": primary["bbox"] if primary else None,

        # Improved multi-object output.
        "detections": detections,
        "detection_count": len(detections),

        # Reproducibility metadata.
        "model_version": MODEL_VERSION,
        "threshold": DETECTION_CONF,

        # User-facing message.
        "message": message
    }
