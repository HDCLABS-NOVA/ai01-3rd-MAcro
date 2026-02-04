# 🤖 매크로 탐지 시스템 구축 가이드 (단계별 정리)

## 📋 전체 프로세스 요약

```
1. 로그 수집 (정상 + 매크로)
   ↓
2. 특징 추출 (마우스, 클릭, 시간 패턴)
   ↓
3. 모델 학습 (Random Forest, XGBoost 등)
   ↓
4. 모델 평가 (정확도, ROC-AUC)
   ↓
5. 실시간 예측 (FastAPI 통합)
```

---

## 🎯 Step 1: 로그 수집

### 정상 사용자 로그 수집 (200개)

**방법 1: 수동 티켓팅**
```bash
1. 서버 실행
   python main.py

2. 브라우저에서 접속
   http://localhost:8000

3. 200번 수동으로 티켓팅 진행
   → logs/ 폴더에 자동 저장됨

4. 파일명 변경 (라벨링)
   booking_flow_20260203_abc123.json
   → booking_flow_20260203_normal_001.json
```

**방법 2: Chrome Extension (추천)**
```bash
1. Extension 설정
   - Auto-Loop: 200
   - Macro Mode: OFF (정상 모드)
   - Random Seats: ON

2. Start 버튼 클릭
   → 자동으로 200개 로그 수집

3. 파일명에 'normal' 키워드 추가
```

### 매크로 로그 수집 (200개)

**Tampermonkey 스크립트 사용**
```bash
1. macro_ticketing.user.js 확인
   const MACRO_MODE = true;  ← 매크로 모드

2. Tampermonkey 활성화 후 사이트 접속

3. 자동으로 매크로 티켓팅 실행
   → 200번 반복

4. 파일명에 'macro' 키워드 추가
   → booking_flow_20260203_macro_001.json
```

### 로그 정리
```bash
logs/
├── booking_flow_20260203_normal_001.json
├── booking_flow_20260203_normal_002.json
├── ...
├── booking_flow_20260203_normal_200.json
├── booking_flow_20260203_macro_001.json
├── booking_flow_20260203_macro_002.json
├── ...
└── booking_flow_20260203_macro_200.json

✅ 총 400개 로그 파일
```

---

## 🎯 Step 2: ML 라이브러리 설치

```bash
cd c:\Users\katie\Downloads\ai01-3rd-3team-1\ml
pip install -r requirements.txt
```

**설치되는 라이브러리:**
- pandas, numpy (데이터 처리)
- scikit-learn (머신러닝)
- xgboost (고성능 모델)
- matplotlib, seaborn (시각화)
- joblib (모델 저장/로드)

---

## 🎯 Step 3: 모델 학습

```bash
cd c:\Users\katie\Downloads\ai01-3rd-3team-1\ml
python train_model.py
```

**실행 과정:**
1. ✅ 로그 파일 읽기 (400개)
2. ✅ 특징 추출 (25개 특징)
3. ✅ 데이터 분할 (Train 80% / Test 20%)
4. ✅ 여러 모델 학습 및 비교
   - Logistic Regression
   - Random Forest
   - Gradient Boosting
   - XGBoost ⭐
   - SVM
5. ✅ 하이퍼파라미터 튜닝
6. ✅ Feature Importance 분석
7. ✅ 최종 평가 (Confusion Matrix, ROC Curve)
8. ✅ 모델 저장

**생성되는 파일:**
```
ml/
├── models/
│   ├── macro_detector_model.pkl      ← 학습된 모델
│   ├── macro_detector_scaler.pkl     ← 스케일러
│   └── macro_detector_features.pkl   ← 특징 이름
└── outputs/
    ├── feature_importances.png       ← 특징 중요도
    ├── confusion_matrix.png          ← 혼동 행렬
    └── roc_curve.png                 ← ROC 곡선
```

**예상 성능:**
```
정확도: 90-95%
ROC-AUC: 0.95-0.99

주요 특징:
1. mouse_straightness (0.25) - 마우스 직진성
2. click_min_interval (0.18) - 최소 클릭 간격
3. mouse_speed_std (0.15) - 마우스 속도 변화
4. first_click_time (0.12) - 첫 클릭 시간
5. click_interval_std (0.10) - 클릭 간격 변화
```

---

## 🎯 Step 4: 모델 테스트

```bash
python predictor.py
```

**출력 예시:**
```
🔍 매크로 탐지 예측 결과
================================================

📋 로그 정보:
   - Flow ID: flow_20260203_cffb4c
   - User: home@email.com
   - Duration: 33229 ms

🎯 예측:
   ✅ 정상 사용자

📊 확률:
   - 매크로 확률: 15.32%
   - 정상 확률: 84.68%
   - 신뢰도: 69.36%

⚠️ 위험도: 🟢 낮음
================================================
```

---

## 🎯 Step 5: FastAPI 서버 통합

### 5.1 main.py 수정

**상단에 추가:**
```python
# ml 모듈 임포트
import sys
from pathlib import Path

ml_path = Path(__file__).parent / 'ml'
sys.path.insert(0, str(ml_path))

from predictor import load_model, predict_macro

# 서버 시작 시 모델 로드
print("🤖 매크로 탐지 모델 로딩 중...")
macro_model, macro_scaler, macro_features = load_model(
    model_dir='ml/models',
    filename='macro_detector'
)
print("✅ 매크로 탐지 모델 로드 완료!")
```

**API 엔드포인트 추가:**
```python
@app.post("/api/detect_macro")
async def detect_macro(log_data: dict):
    """매크로 탐지 API"""
    
    result = predict_macro(log_data, macro_model, macro_scaler, macro_features)
    
    # 액션 결정
    if result['macro_probability'] >= 0.9:
        action = "block"  # 차단
    elif result['macro_probability'] >= 0.7:
        action = "warn"   # 경고
    else:
        action = "allow"  # 허용
    
    return {
        "success": True,
        "result": result,
        "action": action
    }
```

### 5.2 클라이언트 (JavaScript) 통합

**booking_complete.js에 추가:**
```javascript
async function checkMacro() {
    const logData = JSON.parse(sessionStorage.getItem('bookingLog'));
    
    const response = await fetch('/api/detect_macro', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logData)
    });
    
    const result = await response.json();
    
    if (result.action === 'block') {
        alert('비정상적인 예매 패턴이 감지되었습니다.');
        // 예매 취소
        window.location.href = '/';
    }
}
```

---

## 📊 핵심 특징 (Features) 설명

### 1. 마우스 움직임 특징
```python
mouse_straightness (0-1)
- 정상: 0.3-0.6 (불규칙한 움직임)
- 매크로: 0.9-1.0 (직선 움직임)

mouse_speed_std
- 정상: 높음 (떨림, 속도 변화)
- 매크로: 낮음 (일정한 속도)
```

### 2. 클릭 패턴 특징
```python
click_min_interval (ms)
- 정상: 300-800ms
- 매크로: 5-50ms (비정상적으로 빠름)

click_interval_std
- 정상: 높음 (간격 변화)
- 매크로: 낮음 (일정한 간격)
```

### 3. 시간 특징
```python
first_click_time (ms)
- 정상: 300-800ms (반응 시간)
- 매크로: 5-50ms (즉각 반응)

total_duration_ms
- 정상: 20000-60000ms
- 매크로: 5000-15000ms (빠름)
```

### 4. 행동 패턴 특징
```python
num_hovers
- 정상: 5-20개 (여러 좌석 탐색)
- 매크로: 0-2개 (호버 없음)
```

---

## 🔧 문제 해결

### Q1: 로그 파일을 찾을 수 없습니다
```bash
A: logs/ 폴더 확인
   - 파일명에 'normal' 또는 'macro' 키워드 포함했는지 확인
   - 최소 10개 이상의 로그 파일이 있는지 확인
```

### Q2: 모델 학습이 실패합니다
```bash
A: 라이브러리 설치 확인
   pip install -r ml/requirements.txt

   데이터 확인:
   - 정상 로그: 최소 50개 이상
   - 매크로 로그: 최소 50개 이상
```

### Q3: 정확도가 낮습니다
```bash
A: 데이터 품질 확인
   1. 로그 파일 라벨이 정확한지 확인
   2. 더 많은 로그 수집 (각 200개 이상)
   3. 다양한 패턴의 로그 수집
```

### Q4: 서버 통합 시 에러
```bash
A: 모델 파일 경로 확인
   ml/models/macro_detector_model.pkl
   ml/models/macro_detector_scaler.pkl
   ml/models/macro_detector_features.pkl
   
   모든 파일이 존재하는지 확인
```

---

## 📈 성능 향상 팁

### 1. 더 많은 데이터 수집
```
정상 로그: 500개+
매크로 로그: 500개+
→ 정확도 95%+
```

### 2. 특징 추가
```python
# 추가 가능한 특징들
- 키보드 입력 패턴
- 스크롤 패턴
- 브라우저 이벤트 패턴
- IP/디바이스 패턴
```

### 3. 앙상블 모델
```python
# 여러 모델 결합
VotingClassifier([
    ('xgb', XGBoost),
    ('rf', RandomForest),
    ('gb', GradientBoosting)
])
```

### 4. 딥러닝 모델
```python
# LSTM으로 시계열 패턴 학습
model = Sequential([
    LSTM(64, input_shape=(None, 5)),
    Dense(32, activation='relu'),
    Dense(1, activation='sigmoid')
])
```

---

## 🎉 완료 체크리스트

```
□ 로그 수집 (정상 200개 + 매크로 200개)
□ 파일명 라벨링 (normal/macro 키워드)
□ ML 라이브러리 설치 (requirements.txt)
□ 모델 학습 (train_model.py)
□ 모델 테스트 (predictor.py)
□ 성능 확인 (Accuracy 90%+, ROC-AUC 0.95+)
□ FastAPI 통합 (main.py)
□ 실시간 탐지 테스트
□ 관리자 페이지에 통계 추가
□ 운영 배포
```

---

## 📚 참고 파일

```
📁 ai01-3rd-3team-1/
├── 📄 ML_PIPELINE_GUIDE.md           ← 전체 가이드 (상세)
├── 📄 QUICK_START_GUIDE.md           ← 이 파일 (요약)
├── 📁 ml/
│   ├── 📄 README.md                  ← ML 모듈 사용법
│   ├── 📄 data_loader.py             ← 로그 읽기
│   ├── 📄 feature_extractor.py       ← 특징 추출
│   ├── 📄 train_model.py             ← 모델 학습 ⭐
│   ├── 📄 predictor.py               ← 실시간 예측
│   ├── 📄 server_integration.py      ← FastAPI 통합
│   └── 📄 requirements.txt           ← 필요 라이브러리
└── 📁 logs/                           ← 로그 파일 저장
```

---

**Happy ML Training! 🚀✨**
