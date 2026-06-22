from pydantic import BaseModel, Field
from typing import Optional


class DetectionItem(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]
    area_ratio: float
    risk_score: float


class DamageDetection(BaseModel):
    """
    Legacy single-detection summary kept for frontend compatibility.
    It represents the highest-risk detection in the image.
    """
    detected: bool
    confidence: float
    area_ratio: float
    damage_score: float
    bbox: Optional[list[float]] = None


class AnalysisResponse(BaseModel):
    success: bool
    hash: str
    timestamp: str

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_accuracy_m: Optional[float] = None

    # Existing frontend compatibility.
    detection: DamageDetection

    # Improved multi-object detection result.
    detections: list[DetectionItem] = Field(default_factory=list)
    detection_count: int = 0

    # Model reproducibility metadata.
    model_version: str
    threshold: float

    message: str
