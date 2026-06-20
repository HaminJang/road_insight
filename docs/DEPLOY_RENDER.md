# Render 배포 가이드

## 권장 방식

- Frontend: Vercel
- Backend: Render Web Service

## Render 설정

Root Directory:

```text
backend
```

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Environment Variables:

```text
YOLO_MODEL_PATH=models/best.pt
MODEL_VERSION=road-insight-yolo11n-pothole-v1
DETECTION_CONF=0.6
IOU_THRESHOLD=0.5
MAX_DETECTIONS=20
MAX_UPLOAD_BYTES=10485760
ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app,http://localhost:3000
```

주의: `best.pt`는 GitHub에 올리지 말고 Render 서버에 별도 업로드하거나 배포 시 안전한 방식으로 배치하세요.
