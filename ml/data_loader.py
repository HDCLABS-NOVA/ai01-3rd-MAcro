"""
데이터 로더 - 로그 파일을 읽어서 DataFrame으로 변환
"""

import os
import json
import pandas as pd
from pathlib import Path


def load_logs(logs_dir='../logs', label_by_filename=True):
    """
    로그 파일을 읽어서 리스트로 반환
    
    파일명 형식: [날짜]_[공연ID]_[flow_id]_[결제성공여부].json
    예: 20260204_perf001_flow_20260204_abc123_success.json
    
    Args:
        logs_dir: 로그 파일이 있는 디렉토리 (또는 normal/macro 하위 폴더)
        label_by_filename: 파일명으로 라벨 구분 (normal/macro 키워드 포함)
                          False면 normal/macro 폴더로 구분
    
    Returns:
        list: 로그 데이터 리스트 (각 로그에 'label' 키 추가)
    """
    
    data = []
    
    if label_by_filename:
        # 파일명으로 라벨 구분
        log_files = list(Path(logs_dir).glob('*.json'))
        
        normal_count = 0
        macro_count = 0
        unknown_count = 0
        
        for file in log_files:
            with open(file, 'r', encoding='utf-8') as f:
                try:
                    log = json.load(f)
                    
                    # 파일명에서 라벨 추출
                    # 방법 1: 'normal' 또는 'macro' 키워드 확인 (명시적 라벨링)
                    # 방법 2: '_success' 또는 '_abandoned' 등으로 판단
                    # 방법 3: 메타데이터 확인
                    
                    filename = file.name.lower()
                    
                    # 우선순위 1: 파일명에 명시적 라벨이 있는지 확인
                    if 'normal' in filename:
                        log['label'] = 0
                        normal_count += 1
                    elif 'macro' in filename:
                        log['label'] = 1
                        macro_count += 1
                    else:
                        # 우선순위 2: 기본값은 정상(0)으로 분류
                        # 수집 시 파일명에 'normal' 또는 'macro' 키워드를 추가하는 것을 권장
                        log['label'] = 0
                        unknown_count += 1
                    
                    data.append(log)
                    
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON 파싱 에러 ({file.name}): {e}")
                except Exception as e:
                    print(f"⚠️ 파일 읽기 에러 ({file.name}): {e}")
        
        print(f"✅ 정상 로그: {normal_count}개")
        print(f"🤖 매크로 로그: {macro_count}개")
        if unknown_count > 0:
            print(f"❓ 미분류 로그 (정상으로 처리): {unknown_count}개")
        print(f"📊 총 로그: {len(data)}개")
    
    else:
        # 폴더로 라벨 구분 (normal/, macro/)
        normal_dir = Path(logs_dir) / 'normal'
        macro_dir = Path(logs_dir) / 'macro'
        
        normal_count = 0
        macro_count = 0
        
        # 정상 로그 읽기
        if normal_dir.exists():
            normal_files = list(normal_dir.glob('*.json'))
            for file in normal_files:
                with open(file, 'r', encoding='utf-8') as f:
                    try:
                        log = json.load(f)
                        log['label'] = 0  # 정상 = 0
                        data.append(log)
                        normal_count += 1
                    except Exception as e:
                        print(f"⚠️ 파일 읽기 에러 ({file.name}): {e}")
        else:
            print(f"⚠️ 정상 로그 폴더를 찾을 수 없습니다: {normal_dir}")
        
        # 매크로 로그 읽기
        if macro_dir.exists():
            macro_files = list(macro_dir.glob('*.json'))
            for file in macro_files:
                with open(file, 'r', encoding='utf-8') as f:
                    try:
                        log = json.load(f)
                        log['label'] = 1  # 매크로 = 1
                        data.append(log)
                        macro_count += 1
                    except Exception as e:
                        print(f"⚠️ 파일 읽기 에러 ({file.name}): {e}")
        else:
            print(f"⚠️ 매크로 로그 폴더를 찾을 수 없습니다: {macro_dir}")
        
        print(f"✅ 정상 로그: {normal_count}개")
        print(f"🤖 매크로 로그: {macro_count}개")
        print(f"📊 총 로그: {len(data)}개")
    
    if len(data) == 0:
        print("⚠️ 경고: 로그 파일을 찾을 수 없습니다!")
        print(f"   확인: {logs_dir}")
    
    return data


def load_single_log(filepath):
    """
    단일 로그 파일 로드
    
    Args:
        filepath: 로그 파일 경로
    
    Returns:
        dict: 로그 데이터
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        log = json.load(f)
    
    return log


if __name__ == '__main__':
    # 테스트
    print("=" * 60)
    print("데이터 로더 테스트")
    print("=" * 60)
    
    # 방법 1: 파일명으로 구분
    print("\n[방법 1] 파일명으로 라벨 구분:")
    logs = load_logs('../logs', label_by_filename=True)
    
    if len(logs) > 0:
        print(f"\n첫 번째 로그 샘플:")
        print(f"  Label: {logs[0].get('label')}")
        print(f"  Flow ID: {logs[0]['metadata'].get('flow_id')}")
        print(f"  User: {logs[0]['metadata'].get('user_email')}")
        print(f"  Duration: {logs[0]['metadata'].get('total_duration_ms')} ms")
    
    # 방법 2: 폴더로 구분 (normal/, macro/)
    # print("\n[방법 2] 폴더로 라벨 구분:")
    # logs = load_logs('../logs', label_by_filename=False)
