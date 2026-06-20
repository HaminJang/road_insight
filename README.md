# Road-Insight

Road-Insight는 스마트폰으로 촬영한 도로 이미지를 YOLO11 기반 객체탐지로 분석하고, GPS·SHA-256 해시·AI 탐지 결과를 포함한 신고 보조 PDF 리포트를 생성하는 PWA 서비스입니다.

## 구조

```text
road_insight/
├── backend/    # FastAPI + YOLO11 inference + PDF generation
├── frontend/   # Next.js PWA
├── ml/         # AI Hub -> YOLO 변환, Colab 학습, metrics
├── docs/       # 배포/학습/IR 문서
└── infra/      # Render, Nginx, systemd 배포 설정
```

## 빠른 실행

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# backend/models/best.pt를 직접 배치한 뒤 실행
uvicorn app.main:app --reload
```

확인 URL:

```text
http://127.0.0.1:8000/healthz
http://127.0.0.1:8000/docs
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

확인 URL:

```text
http://localhost:3000
```

## 모델 파일

`backend/models/best.pt`는 GitHub에 올리지 않습니다. Colab에서 학습한 모델을 서버에 직접 업로드하세요.

## 주요 기능

- YOLO11 다중 객체 탐지 결과 `detections[]` 반환
- confidence threshold 기본값 0.6
- 위험도 점수: AI 신뢰도 + 파손 면적 + 화면 내 위치 위험도
- GPS 정확도 수집 및 PDF 표시
- bbox 오버레이 미리보기
- SHA-256 기반 원본 이미지 무결성 검증
- PDF 문구를 법적 과장 없이 신고 보조 리포트로 정리
