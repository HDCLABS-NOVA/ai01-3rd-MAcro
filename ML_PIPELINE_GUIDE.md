# 🤖 매크로 탐지 ML 파이프라인 완벽 가이드

## 📋 목차
1. [개요](#개요)
2. [단계 1: 로그 수집 (Data Collection)](#단계-1-로그-수집)
3. [단계 2: 데이터 전처리 (Preprocessing)](#단계-2-데이터-전처리)
4. [단계 3: 특징 엔지니어링 (Feature Engineering)](#단계-3-특징-엔지니어링)
5. [단계 4: 모델 학습 (Model Training)](#단계-4-모델-학습)
6. [단계 5: 모델 평가 및 배포 (Evaluation & Deployment)](#단계-5-모델-평가-및-배포)
7. [실전 예제 코드](#실전-예제-코드)

---

## 개요

### 🎯 목표
정상 사용자와 매크로 사용자의 **행동 패턴 차이**를 학습하여, 실시간으로 매크로를 탐지하는 시스템 구축

### 📊 현재 시스템 상태
- ✅ **로그 수집 시스템**: 완벽하게 구축됨 (`logger.js`, `flow-manager.js`)
- ✅ **자동 수집 도구**: Chrome Extension + Tampermonkey
- ✅ **로그 데이터 구조**: 잘 설계됨 (JSON 형식)
- ⏳ **ML 파이프라인**: 이제 구축할 단계

### 🔑 핵심 아이디어
```
정상 사용자:
- 반응 시간: 300-800ms
- 마우스 움직임: 불규칙, 떨림 있음
- 클릭 간격: 500-800ms
- 호버 행동: 있음

매크로 사용자:
- 반응 시간: 5-50ms (비정상적으로 빠름)
- 마우스 움직임: 직선, 떨림 없음
- 클릭 간격: 20-50ms (일정함)
- 호버 행동: 없음
```

---

## 단계 1: 로그 수집

### 1.1 정상 사용자 로그 수집

#### 방법 1: Chrome Extension 사용 (추천)
```bash
1. 서버 실행
   cd C:\Users\katie\Downloads\ai01-3rd-3team-1
   python main.py

2. Chrome Extension 실행
   - Extension 아이콘 클릭
   - 설정:
     * Auto-Loop: 200  # 200개 로그
     * Random Seats: ON
     * Macro Mode: OFF  # ⭐ 정상 모드
   - Start 버튼 클릭

3. 결과
   → logs/ 폴더에 200개 정상 로그 파일 생성
   → 파일명: booking_flow_YYYYMMDD_*.json
```

#### 방법 2: Tampermonkey 스크립트 사용
```javascript
// macro_ticketing.user.js 파일 수정
const MACRO_MODE = false;  // ⭐ 정상 모드

// Tampermonkey에서 스크립트 활성화 후
// 브라우저에서 수동으로 100번 티켓팅 진행
```

### 1.2 매크로 사용자 로그 수집

#### Chrome Extension 사용
```bash
Extension 설정:
- Auto-Loop: 200  # 200개 로그
- Random Seats: ON
- Macro Mode: ON  # ⭐ 매크로 모드
- Start 버튼 클릭

결과:
→ logs/ 폴더에 200개 매크로 로그 파일 생성
```

#### Tampermonkey 스크립트 사용
```javascript
// macro_ticketing.user.js 파일 수정
const MACRO_MODE = true;  // ⭐ 매크로 모드

// Tampermonkey에서 스크립트 활성화
// 자동으로 매크로 로그 수집
```

### 1.3 로그 파일 구조
```json
{
  "metadata": {
    "flow_id": "flow_20260203_cffb4c",
    "user_email": "home@email.com",
    "total_duration_ms": 33229,
    "is_completed": true,
    "final_seats": ["R석-E30"]
  },
  "stages": {
    "perf": {
      "duration_ms": 3254,
      "mouse_trajectory": [...],  // 마우스 궤적
      "clicks": [...]              // 클릭 이벤트
    },
    "seat": {
      "duration_ms": 6528,
      "selected_seats": ["R석-E30"],
      "mouse_trajectory": [...],
      "clicks": [...]
    },
    "payment": {
      "duration_ms": 5068,
      "payment_type": "card",
      "completed": true
    }
  }
}
```

### 1.4 로그 정리 및 라벨링

#### 수집 목표
```
정상 로그: 200-500개
매크로 로그: 200-500개
총: 400-1000개 (최소 400개 권장)
```

#### 로그 파일 정리
```bash
# 로그 폴더 구조 생성
mkdir logs/normal      # 정상 사용자 로그
mkdir logs/macro       # 매크로 사용자 로그

# 수동으로 분류하거나, 파일명에 라벨 포함
# 예: booking_flow_20260203_normal_001.json
#     booking_flow_20260203_macro_001.json
```

---

## 단계 2: 데이터 전처리

### 2.1 Python 환경 설정
```bash
# 필요한 라이브러리 설치
pip install pandas numpy scikit-learn matplotlib seaborn
pip install xgboost lightgbm
pip install imbalanced-learn
```

### 2.2 로그 파일 읽기
```python
# data_loader.py
import os
import json
import pandas as pd
from pathlib import Path

def load_logs(normal_dir='logs/normal', macro_dir='logs/macro'):
    """로그 파일을 읽어서 DataFrame으로 변환"""
    
    data = []
    
    # 정상 로그 읽기
    normal_files = list(Path(normal_dir).glob('*.json'))
    for file in normal_files:
        with open(file, 'r', encoding='utf-8') as f:
            log = json.load(f)
            log['label'] = 0  # 정상 = 0
            data.append(log)
    
    # 매크로 로그 읽기
    macro_files = list(Path(macro_dir).glob('*.json'))
    for file in macro_files:
        with open(file, 'r', encoding='utf-8') as f:
            log = json.load(f)
            log['label'] = 1  # 매크로 = 1
            data.append(log)
    
    print(f"✅ 정상 로그: {len(normal_files)}개")
    print(f"🤖 매크로 로그: {len(macro_files)}개")
    print(f"📊 총 로그: {len(data)}개")
    
    return data

# 사용 예시
logs = load_logs()
```

---

## 단계 3: 특징 엔지니어링

### 3.1 핵심 특징 (Features) 목록

#### 1️⃣ 시간 기반 특징
```python
def extract_timing_features(log):
    """시간 관련 특징 추출"""
    features = {}
    
    # 전체 플로우 시간
    features['total_duration_ms'] = log['metadata']['total_duration_ms']
    
    # 각 단계별 시간
    stages = log['stages']
    features['perf_duration'] = stages.get('perf', {}).get('duration_ms', 0)
    features['seat_duration'] = stages.get('seat', {}).get('duration_ms', 0)
    features['order_duration'] = stages.get('order_info', {}).get('duration_ms', 0)
    features['payment_duration'] = stages.get('payment', {}).get('duration_ms', 0)
    
    return features
```

#### 2️⃣ 마우스 움직임 특징
```python
import numpy as np

def extract_mouse_features(log):
    """마우스 움직임 특징 추출"""
    features = {}
    
    # perf 단계 마우스 궤적
    perf_traj = log['stages'].get('perf', {}).get('mouse_trajectory', [])
    
    if len(perf_traj) > 0:
        # 마우스 이동 거리 계산
        total_distance = 0
        for i in range(1, len(perf_traj)):
            x1, y1 = perf_traj[i-1][0], perf_traj[i-1][1]
            x2, y2 = perf_traj[i][0], perf_traj[i][1]
            distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            total_distance += distance
        
        features['mouse_total_distance'] = total_distance
        features['mouse_num_moves'] = len(perf_traj)
        features['mouse_avg_distance'] = total_distance / len(perf_traj) if len(perf_traj) > 0 else 0
        
        # 직진성 (Straightness) 계산
        # 시작점과 끝점 직선 거리 / 실제 이동 거리
        if len(perf_traj) >= 2:
            x_start, y_start = perf_traj[0][0], perf_traj[0][1]
            x_end, y_end = perf_traj[-1][0], perf_traj[-1][1]
            straight_dist = np.sqrt((x_end - x_start)**2 + (y_end - y_start)**2)
            features['mouse_straightness'] = straight_dist / total_distance if total_distance > 0 else 0
        else:
            features['mouse_straightness'] = 0
        
        # 속도 변화 (가속도)
        speeds = []
        for i in range(1, len(perf_traj)):
            time_diff = perf_traj[i][2] - perf_traj[i-1][2]  # ms
            if time_diff > 0:
                x1, y1 = perf_traj[i-1][0], perf_traj[i-1][1]
                x2, y2 = perf_traj[i][0], perf_traj[i][1]
                distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                speed = distance / time_diff  # pixels/ms
                speeds.append(speed)
        
        if len(speeds) > 0:
            features['mouse_avg_speed'] = np.mean(speeds)
            features['mouse_speed_std'] = np.std(speeds)  # 속도 변화 (떨림)
        else:
            features['mouse_avg_speed'] = 0
            features['mouse_speed_std'] = 0
    else:
        features['mouse_total_distance'] = 0
        features['mouse_num_moves'] = 0
        features['mouse_avg_distance'] = 0
        features['mouse_straightness'] = 0
        features['mouse_avg_speed'] = 0
        features['mouse_speed_std'] = 0
    
    return features
```

#### 3️⃣ 클릭 패턴 특징
```python
def extract_click_features(log):
    """클릭 패턴 특징 추출"""
    features = {}
    
    # perf 단계 클릭
    perf_clicks = log['stages'].get('perf', {}).get('clicks', [])
    
    if len(perf_clicks) > 0:
        # 클릭 간격
        click_intervals = []
        for i in range(1, len(perf_clicks)):
            interval = perf_clicks[i]['timestamp'] - perf_clicks[i-1]['timestamp']
            click_intervals.append(interval)
        
        if len(click_intervals) > 0:
            features['click_avg_interval'] = np.mean(click_intervals)
            features['click_interval_std'] = np.std(click_intervals)
            features['click_min_interval'] = np.min(click_intervals)
        else:
            features['click_avg_interval'] = 0
            features['click_interval_std'] = 0
            features['click_min_interval'] = 0
        
        # isTrusted 비율
        trusted_count = sum(1 for c in perf_clicks if c.get('is_trusted', True))
        features['click_trusted_ratio'] = trusted_count / len(perf_clicks)
        
        # 정수 좌표 비율 (매크로는 정수 좌표가 많음)
        integer_count = sum(1 for c in perf_clicks if c['x'] == int(c['x']) and c['y'] == int(c['y']))
        features['click_integer_ratio'] = integer_count / len(perf_clicks)
        
        features['click_count'] = len(perf_clicks)
    else:
        features['click_avg_interval'] = 0
        features['click_interval_std'] = 0
        features['click_min_interval'] = 0
        features['click_trusted_ratio'] = 1.0
        features['click_integer_ratio'] = 0
        features['click_count'] = 0
    
    return features
```

#### 4️⃣ 좌석 선택 패턴
```python
def extract_seat_features(log):
    """좌석 선택 패턴 특징 추출"""
    features = {}
    
    seat_stage = log['stages'].get('seat', {})
    
    # 좌석 선택 시간
    features['seat_select_duration'] = seat_stage.get('duration_ms', 0)
    
    # 선택된 좌석 수
    selected_seats = seat_stage.get('selected_seats', [])
    features['num_seats_selected'] = len(selected_seats)
    
    # 호버 이벤트 수 (정상 사용자는 여러 좌석을 호버함)
    hovers = seat_stage.get('hovers', [])
    features['num_hovers'] = len(hovers)
    
    # 마우스 움직임 (seat 단계)
    seat_traj = seat_stage.get('mouse_trajectory', [])
    features['seat_mouse_moves'] = len(seat_traj)
    
    return features
```

#### 5️⃣ 종합 특징 추출
```python
def extract_all_features(log):
    """모든 특징을 추출"""
    features = {}
    
    # 라벨
    features['label'] = log.get('label', 0)
    
    # 시간 특징
    features.update(extract_timing_features(log))
    
    # 마우스 특징
    features.update(extract_mouse_features(log))
    
    # 클릭 특징
    features.update(extract_click_features(log))
    
    # 좌석 특징
    features.update(extract_seat_features(log))
    
    return features

# 전체 로그에 대해 특징 추출
def create_feature_dataframe(logs):
    """로그 데이터를 특징 DataFrame으로 변환"""
    features_list = []
    
    for log in logs:
        features = extract_all_features(log)
        features_list.append(features)
    
    df = pd.DataFrame(features_list)
    
    print(f"✅ Features 생성 완료!")
    print(f"📊 Shape: {df.shape}")
    print(f"📋 Columns: {list(df.columns)}")
    
    return df

# 사용 예시
logs = load_logs()
df = create_feature_dataframe(logs)
```

### 3.2 데이터 탐색 (EDA)
```python
import matplotlib.pyplot as plt
import seaborn as sns

def explore_data(df):
    """데이터 탐색 및 시각화"""
    
    # 1. 클래스 분포
    print("=== 클래스 분포 ===")
    print(df['label'].value_counts())
    
    # 2. 기본 통계
    print("\n=== 기본 통계 ===")
    print(df.describe())
    
    # 3. 상관관계 히트맵
    plt.figure(figsize=(12, 10))
    correlation = df.corr()
    sns.heatmap(correlation, annot=False, cmap='coolwarm')
    plt.title('Feature Correlation Heatmap')
    plt.tight_layout()
    plt.savefig('correlation_heatmap.png')
    
    # 4. 주요 특징 분포 비교
    key_features = [
        'total_duration_ms',
        'mouse_straightness',
        'click_avg_interval',
        'click_min_interval',
        'mouse_speed_std'
    ]
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    for i, feature in enumerate(key_features):
        if feature in df.columns:
            df[df['label'] == 0][feature].hist(bins=30, alpha=0.5, label='Normal', ax=axes[i])
            df[df['label'] == 1][feature].hist(bins=30, alpha=0.5, label='Macro', ax=axes[i])
            axes[i].set_title(feature)
            axes[i].legend()
    
    plt.tight_layout()
    plt.savefig('feature_distributions.png')
    
    print("\n✅ 그래프 저장 완료: correlation_heatmap.png, feature_distributions.png")

# 사용 예시
explore_data(df)
```

---

## 단계 4: 모델 학습

### 4.1 데이터 분할
```python
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

def prepare_data(df):
    """데이터 준비 및 분할"""
    
    # Features와 Label 분리
    X = df.drop('label', axis=1)
    y = df['label']
    
    # Train/Test 분할 (80:20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # 특징 스케일링 (StandardScaler)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print(f"✅ 데이터 준비 완료!")
    print(f"📊 Train: {X_train.shape}, Test: {X_test.shape}")
    print(f"👤 Train Normal: {sum(y_train == 0)}, Macro: {sum(y_train == 1)}")
    print(f"👤 Test Normal: {sum(y_test == 0)}, Macro: {sum(y_test == 1)}")
    
    return X_train_scaled, X_test_scaled, y_train, y_test, scaler, X.columns

# 사용 예시
X_train, X_test, y_train, y_test, scaler, feature_names = prepare_data(df)
```

### 4.2 여러 모델 학습 및 비교
```python
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, accuracy_score

def train_and_evaluate_models(X_train, X_test, y_train, y_test):
    """여러 모델을 학습하고 평가"""
    
    models = {
        'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
        'XGBoost': XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss'),
        'SVM': SVC(kernel='rbf', probability=True, random_state=42)
    }
    
    results = {}
    
    for name, model in models.items():
        print(f"\n{'='*50}")
        print(f"🤖 Training: {name}")
        print(f"{'='*50}")
        
        # 학습
        model.fit(X_train, y_train)
        
        # 예측
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # 평가
        accuracy = accuracy_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        
        print(f"\n📊 Accuracy: {accuracy:.4f}")
        print(f"📊 ROC-AUC: {roc_auc:.4f}")
        print(f"\n{classification_report(y_test, y_pred, target_names=['Normal', 'Macro'])}")
        
        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred)
        print(f"\n혼동 행렬:")
        print(f"              Predicted Normal  Predicted Macro")
        print(f"Actual Normal       {cm[0][0]:4d}            {cm[0][1]:4d}")
        print(f"Actual Macro        {cm[1][0]:4d}            {cm[1][1]:4d}")
        
        results[name] = {
            'model': model,
            'accuracy': accuracy,
            'roc_auc': roc_auc,
            'y_pred': y_pred,
            'y_pred_proba': y_pred_proba
        }
    
    # 최고 성능 모델 선택
    best_model_name = max(results, key=lambda x: results[x]['roc_auc'])
    print(f"\n🏆 Best Model: {best_model_name} (ROC-AUC: {results[best_model_name]['roc_auc']:.4f})")
    
    return results, best_model_name

# 사용 예시
results, best_model_name = train_and_evaluate_models(X_train, X_test, y_train, y_test)
```

### 4.3 최적의 모델 하이퍼파라미터 튜닝
```python
from sklearn.model_selection import GridSearchCV

def tune_best_model(X_train, y_train, model_name='XGBoost'):
    """최고 모델의 하이퍼파라미터 튜닝"""
    
    if model_name == 'XGBoost':
        param_grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.1, 0.2],
            'subsample': [0.8, 1.0]
        }
        model = XGBClassifier(random_state=42, eval_metric='logloss')
    
    elif model_name == 'Random Forest':
        param_grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [10, 20, 30, None],
            'min_samples_split': [2, 5, 10]
        }
        model = RandomForestClassifier(random_state=42)
    
    print(f"🔍 Hyperparameter Tuning for {model_name}...")
    
    grid_search = GridSearchCV(
        model, param_grid, cv=5, scoring='roc_auc', n_jobs=-1, verbose=1
    )
    
    grid_search.fit(X_train, y_train)
    
    print(f"\n✅ Best Params: {grid_search.best_params_}")
    print(f"📊 Best ROC-AUC (CV): {grid_search.best_score_:.4f}")
    
    return grid_search.best_estimator_

# 사용 예시
best_model = tune_best_model(X_train, y_train, model_name='XGBoost')
```

### 4.4 특징 중요도 분석
```python
def analyze_feature_importance(model, feature_names):
    """특징 중요도 분석"""
    
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        
        # 중요도 정렬
        indices = np.argsort(importances)[::-1]
        
        print("\n📊 Feature Importances (Top 10):")
        for i in range(min(10, len(indices))):
            idx = indices[i]
            print(f"{i+1}. {feature_names[idx]:30s}: {importances[idx]:.4f}")
        
        # 시각화
        plt.figure(figsize=(10, 6))
        plt.bar(range(min(10, len(indices))), importances[indices[:10]])
        plt.xticks(range(min(10, len(indices))), [feature_names[i] for i in indices[:10]], rotation=45, ha='right')
        plt.xlabel('Features')
        plt.ylabel('Importance')
        plt.title('Top 10 Feature Importances')
        plt.tight_layout()
        plt.savefig('feature_importances.png')
        print("\n✅ 그래프 저장: feature_importances.png")

# 사용 예시
analyze_feature_importance(best_model, feature_names)
```

---

## 단계 5: 모델 평가 및 배포

### 5.1 최종 모델 평가
```python
def final_evaluation(model, X_test, y_test):
    """최종 모델 평가"""
    
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    
    print(f"\n{'='*50}")
    print(f"🎯 최종 모델 평가 결과")
    print(f"{'='*50}")
    print(f"\n📊 Accuracy: {accuracy:.4f}")
    print(f"📊 ROC-AUC: {roc_auc:.4f}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['Normal', 'Macro'])}")
    
    # Confusion Matrix 시각화
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('Confusion Matrix')
    plt.savefig('confusion_matrix.png')
    print("\n✅ 혼동 행렬 저장: confusion_matrix.png")
    
    # ROC Curve
    from sklearn.metrics import roc_curve
    fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba)
    
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, label=f'ROC Curve (AUC = {roc_auc:.4f})')
    plt.plot([0, 1], [0, 1], 'k--', label='Random')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve')
    plt.legend()
    plt.savefig('roc_curve.png')
    print("✅ ROC Curve 저장: roc_curve.png")

# 사용 예시
final_evaluation(best_model, X_test, y_test)
```

### 5.2 모델 저장
```python
import joblib

def save_model(model, scaler, feature_names, filename='macro_detector'):
    """모델과 전처리 객체 저장"""
    
    # 모델 저장
    joblib.dump(model, f'{filename}_model.pkl')
    print(f"✅ 모델 저장: {filename}_model.pkl")
    
    # Scaler 저장
    joblib.dump(scaler, f'{filename}_scaler.pkl')
    print(f"✅ Scaler 저장: {filename}_scaler.pkl")
    
    # Feature names 저장
    joblib.dump(list(feature_names), f'{filename}_features.pkl')
    print(f"✅ Features 저장: {filename}_features.pkl")

# 사용 예시
save_model(best_model, scaler, feature_names, filename='macro_detector')
```

### 5.3 실시간 추론 함수
```python
def load_model(filename='macro_detector'):
    """저장된 모델 로드"""
    model = joblib.load(f'{filename}_model.pkl')
    scaler = joblib.load(f'{filename}_scaler.pkl')
    feature_names = joblib.load(f'{filename}_features.pkl')
    
    return model, scaler, feature_names

def predict_macro(log_data, model, scaler, feature_names):
    """실시간 매크로 예측"""
    
    # 특징 추출
    features = extract_all_features(log_data)
    
    # DataFrame으로 변환
    features_df = pd.DataFrame([features])
    
    # 필요한 컬럼만 선택 (학습 시 사용한 컬럼 순서대로)
    features_df = features_df[feature_names]
    
    # 스케일링
    features_scaled = scaler.transform(features_df)
    
    # 예측
    prediction = model.predict(features_scaled)[0]
    probability = model.predict_proba(features_scaled)[0]
    
    result = {
        'is_macro': bool(prediction),
        'macro_probability': float(probability[1]),
        'normal_probability': float(probability[0])
    }
    
    return result

# 사용 예시
model, scaler, feature_names = load_model('macro_detector')

# 새로운 로그 데이터에 대해 예측
with open('logs/booking_flow_20260203_cffb4c.json', 'r') as f:
    new_log = json.load(f)
    result = predict_macro(new_log, model, scaler, feature_names)
    
    print(f"\n🔍 예측 결과:")
    print(f"매크로 여부: {'🤖 매크로' if result['is_macro'] else '👤 정상'}")
    print(f"매크로 확률: {result['macro_probability']:.2%}")
    print(f"정상 확률: {result['normal_probability']:.2%}")
```

### 5.4 FastAPI 서버에 통합
```python
# main.py에 추가할 코드

# 모델 로드 (서버 시작 시 한 번만)
macro_model, macro_scaler, macro_features = load_model('macro_detector')

@app.post("/api/detect_macro")
async def detect_macro(log_data: dict):
    """매크로 탐지 API"""
    
    try:
        # 매크로 예측
        result = predict_macro(log_data, macro_model, macro_scaler, macro_features)
        
        # 매크로로 판단되면 경고
        if result['is_macro'] and result['macro_probability'] > 0.8:
            # 로그 저장 후 계정 플래그 처리
            print(f"⚠️ 매크로 탐지! User: {log_data['metadata'].get('user_email')}")
            # TODO: 계정 경고/차단 로직
        
        return {
            "success": True,
            "result": result
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

---

## 실전 예제 코드

### 전체 파이프라인 실행 스크립트
```python
# train_macro_detector.py
"""
매크로 탐지 모델 학습 전체 파이프라인
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, accuracy_score, roc_curve
import joblib

# ========================================
# 1. 데이터 로드
# ========================================
print("=" * 60)
print("Step 1: 데이터 로드")
print("=" * 60)

# 로그 파일 읽기 (정상 + 매크로)
logs = load_logs(normal_dir='logs/normal', macro_dir='logs/macro')

# ========================================
# 2. 특징 추출
# ========================================
print("\n" + "=" * 60)
print("Step 2: 특징 추출")
print("=" * 60)

df = create_feature_dataframe(logs)
print(df.head())

# ========================================
# 3. 데이터 탐색 (EDA)
# ========================================
print("\n" + "=" * 60)
print("Step 3: 데이터 탐색 (EDA)")
print("=" * 60)

explore_data(df)

# ========================================
# 4. 데이터 준비
# ========================================
print("\n" + "=" * 60)
print("Step 4: 데이터 준비")
print("=" * 60)

X_train, X_test, y_train, y_test, scaler, feature_names = prepare_data(df)

# ========================================
# 5. 모델 학습 및 비교
# ========================================
print("\n" + "=" * 60)
print("Step 5: 모델 학습 및 비교")
print("=" * 60)

results, best_model_name = train_and_evaluate_models(X_train, X_test, y_train, y_test)

# ========================================
# 6. 하이퍼파라미터 튜닝
# ========================================
print("\n" + "=" * 60)
print("Step 6: 하이퍼파라미터 튜닝")
print("=" * 60)

best_model = tune_best_model(X_train, y_train, model_name=best_model_name)

# ========================================
# 7. 특징 중요도 분석
# ========================================
print("\n" + "=" * 60)
print("Step 7: 특징 중요도 분석")
print("=" * 60)

analyze_feature_importance(best_model, feature_names)

# ========================================
# 8. 최종 평가
# ========================================
print("\n" + "=" * 60)
print("Step 8: 최종 평가")
print("=" * 60)

final_evaluation(best_model, X_test, y_test)

# ========================================
# 9. 모델 저장
# ========================================
print("\n" + "=" * 60)
print("Step 9: 모델 저장")
print("=" * 60)

save_model(best_model, scaler, feature_names, filename='models/macro_detector')

print("\n" + "=" * 60)
print("✅ 모든 단계 완료!")
print("=" * 60)
```

---

## 📊 예상 결과

### 기대 성능
```
정상 로그: 200개
매크로 로그: 200개

예상 정확도: 90-95%
예상 ROC-AUC: 0.95-0.99

주요 특징:
1. mouse_straightness (매크로는 직선 움직임)
2. click_min_interval (매크로는 매우 빠름)
3. mouse_speed_std (매크로는 일정한 속도)
4. click_interval_std (매크로는 일정한 간격)
5. num_hovers (매크로는 호버 없음)
```

---

## 🎯 다음 단계

1. **로그 수집**: Chrome Extension으로 정상/매크로 로그 각 200개 수집
2. **특징 추출 코드 작성**: 위의 코드를 `feature_extractor.py`로 저장
3. **모델 학습**: `train_macro_detector.py` 실행
4. **성능 평가**: 정확도, ROC-AUC 확인
5. **서버 통합**: FastAPI에 `/api/detect_macro` 엔드포인트 추가
6. **실시간 탐지**: 새로운 예매 로그를 실시간으로 분석

---

## 💡 추가 개선 아이디어

### 1. 앙상블 모델
```python
# 여러 모델의 예측을 결합 (Voting, Stacking)
from sklearn.ensemble import VotingClassifier

ensemble = VotingClassifier(
    estimators=[
        ('xgb', XGBClassifier()),
        ('rf', RandomForestClassifier()),
        ('gb', GradientBoostingClassifier())
    ],
    voting='soft'  # 확률 기반 투표
)
```

### 2. 딥러닝 모델
```python
# LSTM으로 시계열 패턴 학습 (마우스 궤적)
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# 마우스 궤적을 시퀀스로 사용
model = Sequential([
    LSTM(64, input_shape=(None, 5)),  # (x, y, t, nx, ny)
    Dense(32, activation='relu'),
    Dense(1, activation='sigmoid')
])
```

### 3. 이상 탐지 (Anomaly Detection)
```python
# 정상 데이터만으로 학습 → 매크로를 이상치로 탐지
from sklearn.ensemble import IsolationForest

iso_forest = IsolationForest(contamination=0.1)
iso_forest.fit(X_train[y_train == 0])  # 정상 데이터만
```

---

## 📚 참고 자료

- Scikit-learn Documentation: https://scikit-learn.org/
- XGBoost Documentation: https://xgboost.readthedocs.io/
- Feature Engineering Guide: https://machinelearningmastery.com/discover-feature-engineering-how-to-engineer-features-and-how-to-get-good-at-it/

---

**Happy ML Training! 🚀✨**
