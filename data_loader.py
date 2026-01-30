"""
🤖 매크로 탐지 ML 학습 데이터 로더

이 스크립트는 로그 파일들을 읽어서 ML 학습용 데이터셋을 생성합니다.
파일명에는 레이블 정보가 없으며, JSON 내부 데이터만으로 판단합니다.
"""

import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

# 경로 설정
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
LABEL_FILE = BASE_DIR / "bot_labels.json"


def load_labels() -> Dict[str, Dict]:
    """
    bot_labels.json 파일에서 레이블 정보 로드
    
    Returns:
        dict: {filename: {is_bot, bot_type, confidence, ...}}
    """
    if not LABEL_FILE.exists():
        return {}
    
    with open(LABEL_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get("labels", {})


def load_log_file(filepath: Path) -> Dict:
    """
    개별 로그 파일 로드
    
    Args:
        filepath: 로그 파일 경로
    
    Returns:
        dict: 로그 데이터
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_features(log_data: Dict) -> Dict:
    """
    로그 데이터에서 ML 학습용 특징 추출
    
    Args:
        log_data: 로그 JSON 데이터
    
    Returns:
        dict: 추출된 특징들
    """
    metadata = log_data.get("metadata", {})
    stages = log_data.get("stages", {})
    
    features = {
        # 메타데이터
        "total_duration_ms": metadata.get("total_duration_ms", 0),
        "is_completed": metadata.get("is_completed", False),
        
        # 브라우저 정보
        "webdriver": metadata.get("browser_info", {}).get("webdriver", False),
        "hardware_concurrency": metadata.get("browser_info", {}).get("hardwareConcurrency", 0),
        "device_memory": metadata.get("browser_info", {}).get("deviceMemory", 0),
        
        # 공연 선택 단계
        "perf_duration_ms": stages.get("perf", {}).get("duration_ms", 0),
        "perf_trajectory_points": len(stages.get("perf", {}).get("mouse_trajectory", [])),
        
        # 대기열 단계
        "queue_duration_ms": stages.get("queue", {}).get("duration_ms", 0),
        "queue_wait_ms": stages.get("queue", {}).get("wait_duration_ms", 0),
        "queue_initial_position": stages.get("queue", {}).get("initial_position", 0),
        "queue_bypassed": "queue" not in stages,  # 대기열 단계가 없으면 우회
        
        # 캡챠 단계
        "captcha_duration_ms": stages.get("captcha", {}).get("duration_ms", 0),
        "captcha_attempts": stages.get("captcha", {}).get("attempts", 0),
        "captcha_solve_time_ms": stages.get("captcha", {}).get("time_to_solve_ms", 0),
        
        # 구역 선택 단계
        "section_duration_ms": stages.get("section", {}).get("duration_ms", 0),
        "section_clicks": len(stages.get("section", {}).get("clicks", [])),
        
        # 좌석 선택 단계
        "booking_duration_ms": stages.get("booking", {}).get("duration_ms", 0),
        "booking_seat_clicks": len(stages.get("booking", {}).get("seat_clicks", [])),
        "booking_keyboard_events": len(stages.get("booking", {}).get("keyboard_events", [])),
        "booking_scroll_events": len(stages.get("booking", {}).get("scroll_events", [])),
        "final_seats_count": len(metadata.get("final_seats", [])),
    }
    
    # 클릭 간격 분석 (좌석 선택)
    seat_clicks = stages.get("booking", {}).get("seat_clicks", [])
    if len(seat_clicks) >= 2:
        intervals = []
        for i in range(1, len(seat_clicks)):
            try:
                t1 = pd.to_datetime(seat_clicks[i-1]["timestamp"])
                t2 = pd.to_datetime(seat_clicks[i]["timestamp"])
                interval = (t2 - t1).total_seconds()
                intervals.append(interval)
            except:
                pass
        
        if intervals:
            features["avg_click_interval"] = sum(intervals) / len(intervals)
            features["click_interval_std"] = pd.Series(intervals).std()
            features["click_interval_min"] = min(intervals)
            features["click_interval_max"] = max(intervals)
        else:
            features["avg_click_interval"] = 0
            features["click_interval_std"] = 0
            features["click_interval_min"] = 0
            features["click_interval_max"] = 0
    else:
        features["avg_click_interval"] = 0
        features["click_interval_std"] = 0
        features["click_interval_min"] = 0
        features["click_interval_max"] = 0
    
    # is_trusted 분석
    all_clicks = seat_clicks + stages.get("section", {}).get("clicks", [])
    if all_clicks:
        trusted_count = sum(1 for c in all_clicks if c.get("is_trusted", True))
        features["click_trusted_ratio"] = trusted_count / len(all_clicks)
    else:
        features["click_trusted_ratio"] = 1.0
    
    return features


def load_dataset(include_bot_analysis: bool = False) -> Tuple[pd.DataFrame, pd.Series]:
    """
    전체 데이터셋 로드 및 특징 추출
    
    Args:
        include_bot_analysis: JSON에 bot_analysis 필드가 있는 경우 포함할지 여부
    
    Returns:
        tuple: (features_df, labels_series)
    """
    labels_dict = load_labels()
    
    all_features = []
    all_labels = []
    all_filenames = []
    
    # 모든 JSON 파일 처리
    for log_file in LOGS_DIR.glob("*.json"):
        filename = log_file.name
        
        try:
            # 로그 데이터 로드
            log_data = load_log_file(log_file)
            
            # 특징 추출
            features = extract_features(log_data)
            features["filename"] = filename
            
            # bot_analysis가 JSON 내부에 있으면 제거 (실전 시뮬레이션)
            if not include_bot_analysis and "bot_analysis" in log_data:
                del log_data["bot_analysis"]
            
            # 레이블 확인
            if filename in labels_dict:
                # bot_labels.json에 있음 (봇)
                label = 1
            elif log_data.get("bot_analysis", {}).get("is_bot"):
                # JSON 내부에 bot_analysis가 있음 (봇)
                label = 1
            else:
                # 정상 사용자
                label = 0
            
            all_features.append(features)
            all_labels.append(label)
            all_filenames.append(filename)
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # DataFrame 생성
    df = pd.DataFrame(all_features)
    labels = pd.Series(all_labels, name="is_bot")
    
    print(f"✅ 총 {len(df)}개 로그 로드 완료")
    print(f"   - 정상: {(labels == 0).sum()}개")
    print(f"   - 봇: {(labels == 1).sum()}개")
    
    return df, labels


def get_label_info(filename: str) -> Dict:
    """
    특정 파일의 레이블 정보 조회
    
    Args:
        filename: 로그 파일명
    
    Returns:
        dict: 레이블 정보 (없으면 빈 dict)
    """
    labels = load_labels()
    return labels.get(filename, {})


if __name__ == "__main__":
    # 사용 예시
    print("=" * 60)
    print("🤖 매크로 탐지 데이터셋 로더")
    print("=" * 60)
    
    # 데이터셋 로드
    X, y = load_dataset(include_bot_analysis=False)
    
    print(f"\n📊 데이터셋 정보:")
    print(f"   - Shape: {X.shape}")
    print(f"   - Features: {list(X.columns)[:5]}...")
    print(f"\n🎯 클래스 분포:")
    print(f"   - 정상: {(y == 0).sum()} ({(y == 0).sum() / len(y) * 100:.1f}%)")
    print(f"   - 봇: {(y == 1).sum()} ({(y == 1).sum() / len(y) * 100:.1f}%)")
    
    # 샘플 출력
    print(f"\n📋 첫 5개 샘플:")
    print(X.head())
