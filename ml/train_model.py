"""
모델 학습 스크립트 - 매크로 탐지 모델 학습 전체 파이프라인
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import (
    classification_report, confusion_matrix, 
    roc_auc_score, accuracy_score, roc_curve
)

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("⚠️ XGBoost가 설치되지 않았습니다. pip install xgboost로 설치하세요.")

import joblib

from data_loader import load_logs
from feature_extractor import create_feature_dataframe


def prepare_data(df, test_size=0.2, random_state=42):
    """데이터 준비 및 분할"""
    
    # Features와 Label 분리
    X = df.drop('label', axis=1)
    y = df['label']
    
    # Train/Test 분할
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    # 특징 스케일링 (StandardScaler)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print(f"\n✅ 데이터 준비 완료!")
    print(f"📊 Train: {X_train.shape}, Test: {X_test.shape}")
    print(f"👤 Train - Normal: {sum(y_train == 0)}, Macro: {sum(y_train == 1)}")
    print(f"👤 Test - Normal: {sum(y_test == 0)}, Macro: {sum(y_test == 1)}")
    
    return X_train_scaled, X_test_scaled, y_train, y_test, scaler, X.columns


def train_and_evaluate_models(X_train, X_test, y_train, y_test):
    """여러 모델을 학습하고 평가"""
    
    models = {
        'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
        'SVM': SVC(kernel='rbf', probability=True, random_state=42)
    }
    
    if HAS_XGBOOST:
        models['XGBoost'] = XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')
    
    results = {}
    
    for name, model in models.items():
        print(f"\n{'='*60}")
        print(f"🤖 Training: {name}")
        print(f"{'='*60}")
        
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


def tune_best_model(X_train, y_train, model_name='Random Forest'):
    """최고 모델의 하이퍼파라미터 튜닝"""
    
    if model_name == 'XGBoost' and HAS_XGBOOST:
        param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.1],
        }
        model = XGBClassifier(random_state=42, eval_metric='logloss')
    
    elif model_name == 'Random Forest':
        param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [10, 20, None],
            'min_samples_split': [2, 5]
        }
        model = RandomForestClassifier(random_state=42)
    
    elif model_name == 'Gradient Boosting':
        param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [3, 5],
            'learning_rate': [0.01, 0.1]
        }
        model = GradientBoostingClassifier(random_state=42)
    
    else:
        print(f"⚠️ {model_name}에 대한 튜닝은 지원하지 않습니다. 기본 모델을 사용합니다.")
        return None
    
    print(f"\n🔍 Hyperparameter Tuning for {model_name}...")
    
    grid_search = GridSearchCV(
        model, param_grid, cv=3, scoring='roc_auc', n_jobs=-1, verbose=1
    )
    
    grid_search.fit(X_train, y_train)
    
    print(f"\n✅ Best Params: {grid_search.best_params_}")
    print(f"📊 Best ROC-AUC (CV): {grid_search.best_score_:.4f}")
    
    return grid_search.best_estimator_


def analyze_feature_importance(model, feature_names, output_dir='../ml/outputs'):
    """특징 중요도 분석"""
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
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
        top_n = min(15, len(indices))
        plt.bar(range(top_n), importances[indices[:top_n]])
        plt.xticks(range(top_n), [feature_names[i] for i in indices[:top_n]], rotation=45, ha='right')
        plt.xlabel('Features')
        plt.ylabel('Importance')
        plt.title('Top Feature Importances')
        plt.tight_layout()
        
        output_path = Path(output_dir) / 'feature_importances.png'
        plt.savefig(output_path)
        plt.close()
        
        print(f"\n✅ 그래프 저장: {output_path}")


def final_evaluation(model, X_test, y_test, output_dir='../ml/outputs'):
    """최종 모델 평가"""
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    
    print(f"\n{'='*60}")
    print(f"🎯 최종 모델 평가 결과")
    print(f"{'='*60}")
    print(f"\n📊 Accuracy: {accuracy:.4f}")
    print(f"📊 ROC-AUC: {roc_auc:.4f}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['Normal', 'Macro'])}")
    
    # Confusion Matrix 시각화
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=['Normal', 'Macro'], 
                yticklabels=['Normal', 'Macro'])
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('Confusion Matrix')
    
    cm_path = Path(output_dir) / 'confusion_matrix.png'
    plt.savefig(cm_path)
    plt.close()
    print(f"\n✅ 혼동 행렬 저장: {cm_path}")
    
    # ROC Curve
    fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba)
    
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, label=f'ROC Curve (AUC = {roc_auc:.4f})', linewidth=2)
    plt.plot([0, 1], [0, 1], 'k--', label='Random', linewidth=1)
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve')
    plt.legend()
    plt.grid(alpha=0.3)
    
    roc_path = Path(output_dir) / 'roc_curve.png'
    plt.savefig(roc_path)
    plt.close()
    print(f"✅ ROC Curve 저장: {roc_path}")


def save_model(model, scaler, feature_names, output_dir='../ml/models', filename='macro_detector'):
    """모델과 전처리 객체 저장"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 모델 저장
    model_path = output_path / f'{filename}_model.pkl'
    joblib.dump(model, model_path)
    print(f"\n✅ 모델 저장: {model_path}")
    
    # Scaler 저장
    scaler_path = output_path / f'{filename}_scaler.pkl'
    joblib.dump(scaler, scaler_path)
    print(f"✅ Scaler 저장: {scaler_path}")
    
    # Feature names 저장
    features_path = output_path / f'{filename}_features.pkl'
    joblib.dump(list(feature_names), features_path)
    print(f"✅ Features 저장: {features_path}")


def main():
    """전체 파이프라인 실행"""
    
    print("=" * 60)
    print("🤖 매크로 탐지 모델 학습 파이프라인")
    print("=" * 60)
    
    # ========================================
    # 1. 데이터 로드
    # ========================================
    print("\n" + "=" * 60)
    print("Step 1: 데이터 로드")
    print("=" * 60)
    
    logs = load_logs('../logs', label_by_filename=True)
    
    if len(logs) < 10:
        print("\n⚠️ 경고: 로그 파일이 너무 적습니다 (최소 10개 필요)")
        print("   로그 파일을 더 수집한 후 다시 시도하세요.")
        return
    
    # ========================================
    # 2. 특징 추출
    # ========================================
    print("\n" + "=" * 60)
    print("Step 2: 특징 추출")
    print("=" * 60)
    
    df = create_feature_dataframe(logs)
    
    # ========================================
    # 3. 데이터 준비
    # ========================================
    print("\n" + "=" * 60)
    print("Step 3: 데이터 준비")
    print("=" * 60)
    
    X_train, X_test, y_train, y_test, scaler, feature_names = prepare_data(df)
    
    # ========================================
    # 4. 모델 학습 및 비교
    # ========================================
    print("\n" + "=" * 60)
    print("Step 4: 모델 학습 및 비교")
    print("=" * 60)
    
    results, best_model_name = train_and_evaluate_models(X_train, X_test, y_train, y_test)
    
    # ========================================
    # 5. 하이퍼파라미터 튜닝 (선택사항)
    # ========================================
    print("\n" + "=" * 60)
    print("Step 5: 하이퍼파라미터 튜닝")
    print("=" * 60)
    
    tuned_model = tune_best_model(X_train, y_train, model_name=best_model_name)
    
    if tuned_model is not None:
        best_model = tuned_model
    else:
        best_model = results[best_model_name]['model']
    
    # ========================================
    # 6. 특징 중요도 분석
    # ========================================
    print("\n" + "=" * 60)
    print("Step 6: 특징 중요도 분석")
    print("=" * 60)
    
    analyze_feature_importance(best_model, feature_names)
    
    # ========================================
    # 7. 최종 평가
    # ========================================
    print("\n" + "=" * 60)
    print("Step 7: 최종 평가")
    print("=" * 60)
    
    final_evaluation(best_model, X_test, y_test)
    
    # ========================================
    # 8. 모델 저장
    # ========================================
    print("\n" + "=" * 60)
    print("Step 8: 모델 저장")
    print("=" * 60)
    
    save_model(best_model, scaler, feature_names)
    
    print("\n" + "=" * 60)
    print("✅ 모든 단계 완료!")
    print("=" * 60)
    print("\n📊 다음 파일들이 생성되었습니다:")
    print("   - ml/models/macro_detector_model.pkl")
    print("   - ml/models/macro_detector_scaler.pkl")
    print("   - ml/models/macro_detector_features.pkl")
    print("   - ml/outputs/feature_importances.png")
    print("   - ml/outputs/confusion_matrix.png")
    print("   - ml/outputs/roc_curve.png")


if __name__ == '__main__':
    main()
