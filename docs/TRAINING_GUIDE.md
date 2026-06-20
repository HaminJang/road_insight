# YOLO11 학습 가이드

## 1. AI Hub 데이터 배치

```text
ml/data/raw/       # AI Hub JSON
ml/data/images/    # 원본 이미지
```

## 2. YOLO 데이터셋 변환

```bash
python ml/convert_to_yolo.py   --json-dir ml/data/raw   --image-dir ml/data/images   --output-dir ml/dataset   --include-negative
```

## 3. Colab 학습

`ml/train_yolo11_colab.ipynb`를 Colab에서 열어 실행합니다.

핵심 설정:

```python
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
model.train(data='/content/road_insight/ml/dataset/pothole.yaml', epochs=100, imgsz=640)
```

## 4. 배포

학습 후 `best.pt`를 다운로드해 서버의 아래 위치에 업로드합니다.

```text
backend/models/best.pt
```
