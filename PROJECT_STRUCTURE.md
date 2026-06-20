# Road-Insight 프로젝트 구조

```text
road_insight/
├── README.md
├── PROJECT_STRUCTURE.md
├── .gitignore
├── .env.example
├── Procfile
├── requirements.txt
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── analyzer.py
│   │   ├── hasher.py
│   │   └── pdf_generator.py
│   ├── fonts/
│   ├── models/
│   │   └── best.pt              # Git 제외, 서버에 직접 업로드
│   ├── outputs/
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   ├── public/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   └── .env.local.example
│
├── ml/
│   ├── convert_to_yolo.py
│   ├── train_yolo11_colab.ipynb
│   ├── dataset/
│   │   ├── pothole.yaml
│   │   ├── images/train|val|test
│   │   └── labels/train|val|test
│   ├── data/
│   ├── runs/
│   └── metrics/
│
├── docs/
│   ├── PATCH_NOTES.md
│   ├── DEPLOY_RENDER.md
│   ├── DEPLOY_AWS_EC2.md
│   ├── TRAINING_GUIDE.md
│   ├── IR_CHECKLIST.md
│   └── ir/
│
└── infra/
    ├── nginx/
    ├── systemd/
    └── render/
```

## 기존 구조 대비 변경점

- 기존 루트 `app/`를 `backend/app/`로 이동했습니다.
- 기존 루트 `requirements.txt`는 호환용으로 남기고, 실제 백엔드 의존성은 `backend/requirements.txt`로 이동했습니다.
- `best.pt`는 `backend/models/best.pt` 위치를 기준으로 관리합니다. Git에는 포함하지 않습니다.
- `convert_to_yolo.py`, `dataset/`, `data/`는 `ml/` 아래로 이동했습니다.
- Render, Nginx, systemd 설정은 `infra/` 아래로 분리했습니다.
- 발표/사업계획서/프로토타입 자료는 `docs/ir/`로 모았습니다.
```
