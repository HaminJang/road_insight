# AWS EC2 배포 가이드

## 구조

```text
Nginx :80/:443
├── /       -> Next.js localhost:3000
└── /api/   -> FastAPI localhost:8000
```

## WSL/EC2에서 pull

```bash
cd ~/road_insight
git pull origin main
```

## Backend

```bash
cd ~/road_insight/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Frontend

```bash
cd ~/road_insight/frontend
cp .env.local.example .env.local
npm install
npm run build
npm start
```

## systemd/Nginx

예시는 `infra/systemd/`, `infra/nginx/`를 참고하세요.
