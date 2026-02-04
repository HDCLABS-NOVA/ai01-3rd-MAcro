"""
예측 모듈 - 학습된 모델을 사용하여 실시간 매크로 탐지
"""

import joblib
import pandas as pd
from pathlib import Path
from feature_extractor import extract_all_features


def load_model(model_dir='../ml/models', filename='macro_detector'):
    """
    저장된 모델 로드
    
    Args:
        model_dir: 모델이 저장된 디렉토리
        filename: 모델 파일명 (확장자 제외)
    
    Returns:
        tuple: (model, scaler, feature_names)
    """
    model_path = Path(model_dir)
    
    model = joblib.load(model_path / f'{filename}_model.pkl')
    scaler = joblib.load(model_path / f'{filename}_scaler.pkl')
    feature_names = joblib.load(model_path / f'{filename}_features.pkl')
    
    print(f"✅ 모델 로드 완료!")
    print(f"   - Model: {type(model).__name__}")
    print(f"   - Features: {len(feature_names)}개")
    
    return model, scaler, feature_names


def predict_macro(log_data, model, scaler, feature_names):
    """
    실시간 매크로 예측
    
    Args:
        log_data: 로그 데이터 (dict)
        model: 학습된 모델
        scaler: 스케일러
        feature_names: 특징 이름 리스트
    
    Returns:
        dict: 예측 결과
            - is_macro: 매크로 여부 (bool)
            - macro_probability: 매크로 확률 (float)
            - normal_probability: 정상 확률 (float)
            - confidence: 신뢰도 (float, 0-1)
    """
    
    # 특징 추출
    features = extract_all_features(log_data)
    
    # DataFrame으로 변환
    features_df = pd.DataFrame([features])
    
    # label 컬럼 제거 (있는 경우)
    if 'label' in features_df.columns:
        features_df = features_df.drop('label', axis=1)
    
    # 필요한 컬럼만 선택 (학습 시 사용한 컬럼 순서대로)
    # 누락된 컬럼이 있으면 0으로 채우기
    for col in feature_names:
        if col not in features_df.columns:
            features_df[col] = 0
    
    features_df = features_df[feature_names]
    
    # 스케일링
    features_scaled = scaler.transform(features_df)
    
    # 예측
    prediction = model.predict(features_scaled)[0]
    probability = model.predict_proba(features_scaled)[0]
    
    # 신뢰도 계산 (확률의 차이)
    confidence = abs(probability[1] - probability[0])
    
    result = {
        'is_macro': bool(prediction),
        'macro_probability': float(probability[1]),
        'normal_probability': float(probability[0]),
        'confidence': float(confidence)
    }
    
    return result


def batch_predict(log_files, model, scaler, feature_names):
    """
    여러 로그 파일에 대해 일괄 예측
    
    Args:
        log_files: 로그 파일 경로 리스트
        model: 학습된 모델
        scaler: 스케일러
        feature_names: 특징 이름 리스트
    
    Returns:
        list: 예측 결과 리스트
    """
    import json
    
    results = []
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            result = predict_macro(log_data, model, scaler, feature_names)
            result['filename'] = log_file
            
            results.append(result)
        
        except Exception as e:
            print(f"⚠️ 예측 실패 ({log_file}): {e}")
    
    return results


def print_prediction_result(result, log_data=None):
    """예측 결과를 보기 좋게 출력"""
    
    print("\n" + "=" * 60)
    print("🔍 매크로 탐지 예측 결과")
    print("=" * 60)
    
    if log_data:
        metadata = log_data.get('metadata', {})
        print(f"\n📋 로그 정보:")
        print(f"   - Flow ID: {metadata.get('flow_id', 'N/A')}")
        print(f"   - User: {metadata.get('user_email', 'N/A')}")
        print(f"   - Duration: {metadata.get('total_duration_ms', 0)} ms")
    
    print(f"\n🎯 예측:")
    
    if result['is_macro']:
        print(f"   ⚠️ 매크로 탐지!")
    else:
        print(f"   ✅ 정상 사용자")
    
    print(f"\n📊 확률:")
    print(f"   - 매크로 확률: {result['macro_probability']:.2%}")
    print(f"   - 정상 확률: {result['normal_probability']:.2%}")
    print(f"   - 신뢰도: {result['confidence']:.2%}")
    
    # 위험도 평가
    if result['macro_probability'] > 0.9:
        risk_level = "🔴 매우 높음"
    elif result['macro_probability'] > 0.7:
        risk_level = "🟠 높음"
    elif result['macro_probability'] > 0.5:
        risk_level = "🟡 보통"
    else:
        risk_level = "🟢 낮음"
    
    print(f"\n⚠️ 위험도: {risk_level}")
    
    print("=" * 60)


if __name__ == '__main__':
    import json
    import sys
    from pathlib import Path
    
    print("=" * 60)
    print("🤖 매크로 탐지 예측 테스트")
    print("=" * 60)
    
    # 모델 로드
    try:
        model, scaler, feature_names = load_model('../ml/models', 'macro_detector')
    except FileNotFoundError:
        print("\n⚠️ 모델 파일을 찾을 수 없습니다!")
        print("   먼저 train_model.py를 실행하여 모델을 학습시켜주세요.")
        sys.exit(1)
    
    # 테스트 로그 파일 찾기
    log_dir = Path('../logs')
    log_files = list(log_dir.glob('*.json'))[:5]  # 최근 5개 파일
    
    if len(log_files) == 0:
        print("\n⚠️ 테스트할 로그 파일을 찾을 수 없습니다!")
        sys.exit(1)
    
    print(f"\n📁 테스트 파일 수: {len(log_files)}개")
    
    # 일괄 예측
    results = batch_predict([str(f) for f in log_files], model, scaler, feature_names)
    
    # 결과 출력
    macro_count = sum(1 for r in results if r['is_macro'])
    normal_count = len(results) - macro_count
    
    print(f"\n📊 예측 결과 요약:")
    print(f"   - 정상: {normal_count}개")
    print(f"   - 매크로: {macro_count}개")
    
    # 상세 결과
    print(f"\n📋 상세 결과:")
    for i, result in enumerate(results, 1):
        filename = Path(result['filename']).name
        status = "🤖 매크로" if result['is_macro'] else "👤 정상"
        prob = result['macro_probability']
        
        print(f"{i}. {filename[:50]:50s} | {status} ({prob:.1%})")
