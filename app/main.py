import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.analyzer import analyze_image
from app.hasher import generate_hash
from app.pdf_generator import generate_evidence_pdf
from app.schemas import AnalysisResponse, DamageDetection, DetectionItem


MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def parse_allowed_origins() -> list[str]:
    raw = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,"
        "https://road-insight-dzokqr3c4-haminjangs-projects.vercel.app,"
        "https://road-insight.vercel.app"
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="Road-Insight API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://road-insight-dzokqr3c4-haminjangs-projects.vercel.app",
        "https://road-insight.vercel.app"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Road-Insight API 정상 작동 중"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


async def read_and_validate_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="JPEG, PNG, WebP 이미지만 업로드할 수 있습니다."
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(status_code=400, detail="빈 이미지 파일입니다.")

    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="이미지 파일 크기가 너무 큽니다."
        )

    return image_bytes


def build_detection_items(result: dict) -> list[DetectionItem]:
    return [
        DetectionItem(
            class_id=item["class_id"],
            class_name=item["class_name"],
            confidence=item["confidence"],
            bbox=item["bbox"],
            area_ratio=item["area_ratio"],
            risk_score=item["risk_score"]
        )
        for item in result.get("detections", [])
    ]


def build_analysis_id(hash_value: str, timestamp: str) -> str:
    compact_time = timestamp.replace("-", "").replace(":", "").replace(".", "")
    compact_time = compact_time.replace("+", "").replace("T", "")[:14]
    return f"RI-{compact_time}-{hash_value[:8]}"


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    gps_accuracy_m: Optional[float] = Form(None)
):
    image_bytes = await read_and_validate_image(file)
    hash_value = generate_hash(image_bytes)
    timestamp = datetime.now(timezone.utc).isoformat()
    result = analyze_image(image_bytes)

    detection_items = build_detection_items(result)

    return AnalysisResponse(
        success=True,
        hash=hash_value,
        timestamp=timestamp,
        latitude=latitude,
        longitude=longitude,
        gps_accuracy_m=gps_accuracy_m,

        detection=DamageDetection(
            detected=result["detected"],
            confidence=result["confidence"],
            area_ratio=result["area_ratio"],
            damage_score=result["damage_score"],
            bbox=result["bbox"]
        ),

        detections=detection_items,
        detection_count=result.get("detection_count", len(detection_items)),

        model_version=result.get("model_version", "unknown"),
        threshold=result.get("threshold", 0.0),

        message=result["message"]
    )


@app.post("/generate-pdf")
async def generate_pdf(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    gps_accuracy_m: Optional[float] = Form(None)
):
    image_bytes = await read_and_validate_image(file)
    hash_value = generate_hash(image_bytes)
    timestamp = datetime.now(timezone.utc).isoformat()
    result = analyze_image(image_bytes)
    analysis_id = build_analysis_id(hash_value, timestamp)

    pdf_bytes = generate_evidence_pdf(
        image_bytes=image_bytes,
        hash_value=hash_value,
        timestamp=timestamp,
        latitude=latitude,
        longitude=longitude,
        gps_accuracy_m=gps_accuracy_m,
        confidence=result["confidence"],
        damage_score=result["damage_score"],
        detected=result["detected"],
        bbox=result["bbox"],
        detections=result.get("detections", []),
        detection_count=result.get("detection_count", 0),
        model_version=result.get("model_version", "unknown"),
        threshold=result.get("threshold", 0.0),
        analysis_id=analysis_id
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=road_insight_{timestamp[:10]}.pdf"
        }
    )
