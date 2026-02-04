"""
FastAPI 서버 통합 예제 - main.py에 추가할 코드

매크로 탐지 모델을 FastAPI 서버에 통합하는 방법
"""

# ============================================
# main.py 상단에 추가
# ============================================

import sys
from pathlib import Path

# ml 모듈 경로 추가
ml_path = Path(__file__).parent / 'ml'
sys.path.insert(0, str(ml_path))

try:
    from predictor import load_model, predict_macro
    
    # 서버 시작 시 모델 로드 (한 번만)
    print("🤖 매크로 탐지 모델 로딩 중...")
    macro_model, macro_scaler, macro_features = load_model(
        model_dir=str(Path(__file__).parent / 'ml' / 'models'),
        filename='macro_detector'
    )
    print("✅ 매크로 탐지 모델 로드 완료!")
    MACRO_DETECTION_ENABLED = True

except FileNotFoundError:
    print("⚠️ 매크로 탐지 모델을 찾을 수 없습니다.")
    print("   ml/train_model.py를 실행하여 모델을 먼저 학습시켜주세요.")
    MACRO_DETECTION_ENABLED = False

except Exception as e:
    print(f"⚠️ 매크로 탐지 모델 로드 실패: {e}")
    MACRO_DETECTION_ENABLED = False


# ============================================
# main.py에 추가할 API 엔드포인트
# ============================================

@app.post("/api/detect_macro")
async def detect_macro(log_data: dict):
    """
    매크로 탐지 API
    
    Request Body:
        log_data: 로그 데이터 (JSON)
    
    Response:
        {
            "success": true,
            "result": {
                "is_macro": false,
                "macro_probability": 0.15,
                "normal_probability": 0.85,
                "confidence": 0.70
            },
            "action": "allow" | "warn" | "block"
        }
    """
    
    if not MACRO_DETECTION_ENABLED:
        return {
            "success": False,
            "error": "매크로 탐지 모델이 로드되지 않았습니다."
        }
    
    try:
        # 매크로 예측
        result = predict_macro(log_data, macro_model, macro_scaler, macro_features)
        
        # 액션 결정
        action = "allow"
        
        if result['is_macro']:
            if result['macro_probability'] >= 0.9:
                action = "block"  # 차단
                print(f"🚫 매크로 차단! User: {log_data['metadata'].get('user_email')}, Prob: {result['macro_probability']:.2%}")
            elif result['macro_probability'] >= 0.7:
                action = "warn"   # 경고
                print(f"⚠️ 매크로 의심! User: {log_data['metadata'].get('user_email')}, Prob: {result['macro_probability']:.2%}")
        
        # TODO: 데이터베이스에 기록
        # - 사용자별 매크로 탐지 이력 저장
        # - 일정 횟수 이상 탐지 시 계정 차단
        
        return {
            "success": True,
            "result": result,
            "action": action
        }
    
    except Exception as e:
        print(f"❌ 매크로 탐지 에러: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/logs")
async def save_log(log_data: dict):
    """
    로그 저장 API (기존 코드에 매크로 탐지 추가)
    """
    
    try:
        # 기존 로그 저장 로직
        timestamp = datetime.now().strftime("%Y%m%d")
        metadata = log_data.get('metadata', {})
        
        performance_title = metadata.get('performance_title', 'UNKNOWN').replace(' ', '')[:10]
        flow_id = metadata.get('flow_id', '')
        completion_status = metadata.get('completion_status', 'unknown')
        
        filename = f"{timestamp}_{performance_title}_{flow_id}_{completion_status}.json"
        filepath = logs_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 로그 저장 성공: {filename}")
        
        # ⭐ 매크로 탐지 추가
        macro_result = None
        if MACRO_DETECTION_ENABLED and metadata.get('is_completed', False):
            try:
                result = predict_macro(log_data, macro_model, macro_scaler, macro_features)
                macro_result = result
                
                # 매크로로 판단되면 추가 처리
                if result['is_macro'] and result['macro_probability'] >= 0.8:
                    print(f"⚠️ 매크로 탐지! User: {metadata.get('user_email')}, Prob: {result['macro_probability']:.2%}")
                    
                    # TODO: 데이터베이스에 기록
                    # TODO: 이메일/알림 전송
                    # TODO: 계정 플래그 설정
                
            except Exception as e:
                print(f"⚠️ 매크로 탐지 실패: {e}")
        
        return {
            "success": True,
            "filename": filename,
            "macro_detection": macro_result
        }
    
    except Exception as e:
        print(f"❌ 로그 저장 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# 사용자 통계 API 추가
# ============================================

@app.get("/api/admin/macro_stats")
async def get_macro_stats():
    """
    매크로 탐지 통계 API (관리자용)
    
    Response:
        {
            "total_logs": 100,
            "normal_count": 85,
            "macro_count": 15,
            "macro_rate": 0.15,
            "recent_detections": [...]
        }
    """
    
    if not MACRO_DETECTION_ENABLED:
        return {
            "success": False,
            "error": "매크로 탐지 모델이 로드되지 않았습니다."
        }
    
    try:
        from predictor import batch_predict
        
        # logs 폴더의 모든 로그 파일 읽기
        log_files = list(logs_dir.glob('*.json'))
        
        if len(log_files) == 0:
            return {
                "success": True,
                "total_logs": 0,
                "normal_count": 0,
                "macro_count": 0,
                "macro_rate": 0.0,
                "recent_detections": []
            }
        
        # 일괄 예측
        results = batch_predict(
            [str(f) for f in log_files],
            macro_model,
            macro_scaler,
            macro_features
        )
        
        # 통계 계산
        total = len(results)
        macro_count = sum(1 for r in results if r['is_macro'])
        normal_count = total - macro_count
        macro_rate = macro_count / total if total > 0 else 0
        
        # 최근 매크로 탐지 (확률 높은 순)
        macro_detections = [r for r in results if r['is_macro']]
        macro_detections.sort(key=lambda x: x['macro_probability'], reverse=True)
        recent_detections = macro_detections[:10]  # 상위 10개
        
        return {
            "success": True,
            "total_logs": total,
            "normal_count": normal_count,
            "macro_count": macro_count,
            "macro_rate": macro_rate,
            "recent_detections": recent_detections
        }
    
    except Exception as e:
        print(f"❌ 통계 조회 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# 클라이언트 측 (JavaScript) 통합 예제
# ============================================

"""
// booking_complete.js 또는 flow-manager.js에 추가

async function finalizeLogWithMacroDetection() {
    // 기존 로그 완료 로직
    await finalizeLog(true, bookingId);
    
    // 매크로 탐지 실행
    const logData = JSON.parse(sessionStorage.getItem('bookingLog'));
    
    try {
        const response = await fetch('/api/detect_macro', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(logData)
        });
        
        const result = await response.json();
        
        if (result.success && result.action === 'block') {
            // 매크로로 판단되어 차단
            alert('비정상적인 예매 패턴이 감지되었습니다. 예매가 취소됩니다.');
            // TODO: 예매 취소 로직
            window.location.href = '/';
        } else if (result.action === 'warn') {
            // 의심 단계 (경고만)
            console.warn('매크로 의심 탐지:', result.result);
        }
    } catch (error) {
        console.error('매크로 탐지 에러:', error);
    }
}
"""


# ============================================
# 관리자 페이지에 통계 표시
# ============================================

"""
// admin.html 또는 viewer.html에 추가

async function loadMacroStats() {
    try {
        const response = await fetch('/api/admin/macro_stats');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('total-logs').textContent = data.total_logs;
            document.getElementById('normal-count').textContent = data.normal_count;
            document.getElementById('macro-count').textContent = data.macro_count;
            document.getElementById('macro-rate').textContent = (data.macro_rate * 100).toFixed(1) + '%';
            
            // 최근 탐지 목록 표시
            const list = document.getElementById('recent-detections');
            list.innerHTML = '';
            
            data.recent_detections.forEach(detection => {
                const li = document.createElement('li');
                li.textContent = `${detection.filename}: ${(detection.macro_probability * 100).toFixed(1)}%`;
                list.appendChild(li);
            });
        }
    } catch (error) {
        console.error('통계 로드 에러:', error);
    }
}

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', loadMacroStats);
"""
