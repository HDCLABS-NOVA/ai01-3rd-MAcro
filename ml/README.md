# 매크로 탐지 ML 파이프라인

## 📁 디렉토리 구조
```
ml/
├── data_loader.py          # 로그 파일 읽기
├── feature_extractor.py    # 특징 추출
├── train_model.py          # 모델 학습 (메인 스크립트)
├── predictor.py            # 실시간 예측
├── requirements.txt        # 필요한 라이브러리
├── models/                 # 학습된 모델 저장
│   ├── macro_detector_model.pkl
│   ├── macro_detector_scaler.pkl
│   └── macro_detector_features.pkl
└── outputs/                # 결과 그래프 저장
    ├── feature_importances.png
    ├── confusion_matrix.png
    └── roc_curve.png
```

## 🚀 빠른 시작

### 1. 라이브러리 설치
```bash
cd ml
pip install -r requirements.txt
```

### 2. 로그 수집
```bash
# 정상 로그: 200개 이상
# 매크로 로그: 200개 이상
# 총: 400개 이상 권장

# 파일명에 'normal' 또는 'macro' 키워드 포함
# 예: booking_flow_20260203_normal_001.json
#     booking_flow_20260203_macro_001.json
```

### 3. 모델 학습
```bash
cd ml
python train_model.py
```

### 4. 예측 테스트
```bash
python predictor.py
```

## 📊 사용 예제

### 모델 학습
```python
from train_model import main

# 전체 파이프라인 실행
main()
```

### 실시간 예측
```python
import json
from predictor import load_model, predict_macro, print_prediction_result

# 모델 로드
model, scaler, feature_names = load_model()

# 로그 파일 읽기
with open('../logs/booking_flow_20260203_cffb4c.json', 'r') as f:
    log_data = json.load(f)

# 예측
result = predict_macro(log_data, model, scaler, feature_names)

# 결과 출력
print_prediction_result(result, log_data)
```

## 🎯 예상 성능
- 정확도: 90-95%
- ROC-AUC: 0.95-0.99

## 📚 주요 특징
1. **mouse_straightness**: 마우스 직진성 (매크로는 직선 움직임)
2. **click_min_interval**: 최소 클릭 간격 (매크로는 매우 빠름)
3. **mouse_speed_std**: 마우스 속도 변화 (매크로는 일정)
4. **click_interval_std**: 클릭 간격 변화 (매크로는 일정)
5. **num_hovers**: 호버 횟수 (매크로는 호버 없음)
