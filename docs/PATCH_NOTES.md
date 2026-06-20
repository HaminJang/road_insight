# Patch Notes

## v0.2 IR Demo Restructure

- 프로젝트를 `backend/`, `frontend/`, `ml/`, `docs/`, `infra/`로 재구성했습니다.
- YOLO 분석 결과를 단일 bbox에서 `detections[]` 다중 객체 구조로 확장했습니다.
- confidence threshold 기본값을 0.6으로 통일했습니다.
- 위험도 점수를 신뢰도·면적·위치 위험도 조합으로 개선했습니다.
- GPS 정확도를 프론트, API, PDF에 연결했습니다.
- PDF에 bbox 오버레이 이미지와 탐지 객체 목록을 추가했습니다.
- “공식 증거/법적 효력” 표현을 “신고 보조 리포트/무결성 검증” 중심으로 완화했습니다.
- Render/EC2 배포 설정 예시를 추가했습니다.
