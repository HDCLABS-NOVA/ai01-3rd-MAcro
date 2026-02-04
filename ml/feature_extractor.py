"""
특징 추출기 - 로그 데이터에서 ML 모델을 위한 특징(Features) 추출
"""

import numpy as np
import pandas as pd


def extract_timing_features(log):
    """시간 관련 특징 추출"""
    features = {}
    
    metadata = log.get('metadata', {})
    stages = log.get('stages', {})
    
    # 전체 플로우 시간
    features['total_duration_ms'] = metadata.get('total_duration_ms', 0)
    
    # 각 단계별 시간
    features['perf_duration'] = stages.get('perf', {}).get('duration_ms', 0)
    features['queue_duration'] = stages.get('queue', {}).get('duration_ms', 0)
    features['seat_duration'] = stages.get('seat', {}).get('duration_ms', 0)
    features['discount_duration'] = stages.get('discount', {}).get('duration_ms', 0)
    features['order_duration'] = stages.get('order_info', {}).get('duration_ms', 0)
    features['payment_duration'] = stages.get('payment', {}).get('duration_ms', 0)
    
    return features


def extract_mouse_features(log):
    """마우스 움직임 특징 추출"""
    features = {}
    
    stages = log.get('stages', {})
    
    # perf 단계 마우스 궤적
    perf_traj = stages.get('perf', {}).get('mouse_trajectory', [])
    
    if len(perf_traj) > 1:
        # 마우스 이동 거리 계산
        total_distance = 0
        speeds = []
        
        for i in range(1, len(perf_traj)):
            x1, y1 = perf_traj[i-1][0], perf_traj[i-1][1]
            x2, y2 = perf_traj[i][0], perf_traj[i][1]
            
            # 거리 계산
            distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            total_distance += distance
            
            # 속도 계산
            time_diff = perf_traj[i][2] - perf_traj[i-1][2]  # ms
            if time_diff > 0:
                speed = distance / time_diff  # pixels/ms
                speeds.append(speed)
        
        features['mouse_total_distance'] = total_distance
        features['mouse_num_moves'] = len(perf_traj)
        features['mouse_avg_distance'] = total_distance / len(perf_traj)
        
        # 직진성 (Straightness) 계산
        # 시작점과 끝점 직선 거리 / 실제 이동 거리
        x_start, y_start = perf_traj[0][0], perf_traj[0][1]
        x_end, y_end = perf_traj[-1][0], perf_traj[-1][1]
        straight_dist = np.sqrt((x_end - x_start)**2 + (y_end - y_start)**2)
        features['mouse_straightness'] = straight_dist / total_distance if total_distance > 0 else 0
        
        # 속도 통계
        if len(speeds) > 0:
            features['mouse_avg_speed'] = np.mean(speeds)
            features['mouse_speed_std'] = np.std(speeds)  # 속도 변화 (떨림 지표)
            features['mouse_max_speed'] = np.max(speeds)
            features['mouse_min_speed'] = np.min(speeds)
        else:
            features['mouse_avg_speed'] = 0
            features['mouse_speed_std'] = 0
            features['mouse_max_speed'] = 0
            features['mouse_min_speed'] = 0
    else:
        # 마우스 움직임이 없는 경우
        features['mouse_total_distance'] = 0
        features['mouse_num_moves'] = 0
        features['mouse_avg_distance'] = 0
        features['mouse_straightness'] = 0
        features['mouse_avg_speed'] = 0
        features['mouse_speed_std'] = 0
        features['mouse_max_speed'] = 0
        features['mouse_min_speed'] = 0
    
    # seat 단계 마우스 궤적
    seat_traj = stages.get('seat', {}).get('mouse_trajectory', [])
    features['seat_mouse_moves'] = len(seat_traj)
    
    return features


def extract_click_features(log):
    """클릭 패턴 특징 추출"""
    features = {}
    
    stages = log.get('stages', {})
    
    # perf 단계 클릭
    perf_clicks = stages.get('perf', {}).get('clicks', [])
    
    if len(perf_clicks) > 0:
        features['click_count'] = len(perf_clicks)
        
        # 클릭 간격
        if len(perf_clicks) > 1:
            click_intervals = []
            for i in range(1, len(perf_clicks)):
                interval = perf_clicks[i]['timestamp'] - perf_clicks[i-1]['timestamp']
                click_intervals.append(interval)
            
            features['click_avg_interval'] = np.mean(click_intervals)
            features['click_interval_std'] = np.std(click_intervals)
            features['click_min_interval'] = np.min(click_intervals)
            features['click_max_interval'] = np.max(click_intervals)
        else:
            features['click_avg_interval'] = 0
            features['click_interval_std'] = 0
            features['click_min_interval'] = 0
            features['click_max_interval'] = 0
        
        # isTrusted 비율
        trusted_count = sum(1 for c in perf_clicks if c.get('is_trusted', True))
        features['click_trusted_ratio'] = trusted_count / len(perf_clicks)
        
        # 정수 좌표 비율 (매크로는 정수 좌표가 많음)
        integer_count = sum(1 for c in perf_clicks 
                           if c['x'] == int(c['x']) and c['y'] == int(c['y']))
        features['click_integer_ratio'] = integer_count / len(perf_clicks)
        
        # 첫 번째 클릭 시간 (빠른 반응 = 매크로)
        features['first_click_time'] = perf_clicks[0]['timestamp']
    else:
        features['click_count'] = 0
        features['click_avg_interval'] = 0
        features['click_interval_std'] = 0
        features['click_min_interval'] = 0
        features['click_max_interval'] = 0
        features['click_trusted_ratio'] = 1.0
        features['click_integer_ratio'] = 0
        features['first_click_time'] = 0
    
    return features


def extract_seat_features(log):
    """좌석 선택 패턴 특징 추출"""
    features = {}
    
    stages = log.get('stages', {})
    seat_stage = stages.get('seat', {})
    
    # 좌석 선택 시간
    features['seat_select_duration'] = seat_stage.get('duration_ms', 0)
    
    # 선택된 좌석 수
    selected_seats = seat_stage.get('selected_seats', [])
    features['num_seats_selected'] = len(selected_seats)
    
    # 호버 이벤트 수 (정상 사용자는 여러 좌석을 호버함)
    hovers = seat_stage.get('hovers', [])
    features['num_hovers'] = len(hovers)
    
    return features


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


def create_feature_dataframe(logs):
    """
    로그 데이터를 특징 DataFrame으로 변환
    
    Args:
        logs: 로그 데이터 리스트
    
    Returns:
        pd.DataFrame: 특징 DataFrame
    """
    features_list = []
    
    for log in logs:
        try:
            features = extract_all_features(log)
            features_list.append(features)
        except Exception as e:
            print(f"⚠️ 특징 추출 에러: {e}")
            # 에러가 발생한 로그는 건너뛰기
            continue
    
    df = pd.DataFrame(features_list)
    
    print(f"\n✅ Features 생성 완료!")
    print(f"📊 Shape: {df.shape}")
    print(f"📋 Columns: {list(df.columns)}")
    
    # 결측치 확인
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print(f"\n⚠️ 결측치 발견:")
        print(missing[missing > 0])
        
        # 결측치를 0으로 채우기
        df = df.fillna(0)
        print("   → 결측치를 0으로 대체했습니다.")
    
    return df


if __name__ == '__main__':
    # 테스트
    from data_loader import load_logs
    
    print("=" * 60)
    print("특징 추출기 테스트")
    print("=" * 60)
    
    # 로그 로드
    logs = load_logs('../logs', label_by_filename=True)
    
    if len(logs) > 0:
        # 특징 DataFrame 생성
        df = create_feature_dataframe(logs)
        
        print(f"\n📊 데이터프레임 미리보기:")
        print(df.head())
        
        print(f"\n📊 기본 통계:")
        print(df.describe())
        
        print(f"\n📊 클래스 분포:")
        print(df['label'].value_counts())
