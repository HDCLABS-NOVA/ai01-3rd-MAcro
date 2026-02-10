// 로깅 시스템 - 사용자 행동 추적 및 로그 생성

let logData = null;
let currentStage = null;
let stageStartTime = null;
let mouseTrajectory = [];
let lastMouseMoveTime = 0;

/**
 * 로거 초기화
 */
async function initLogger(performanceId = '', performanceTitle = '') {
    const currentUser = getCurrentUser();
    const userIP = await getUserIP();

    const now = getISOTimestamp();
    const flowId = `flow_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}_${generateRandomId('', 6)}`;
    const sessionId = `sess_${generateRandomId('', 7)}`;

    const botType = sessionStorage.getItem('bot_type') || '';

    logData = {
        metadata: {
            flow_id: flowId,
            session_id: sessionId,
            bot_type: botType, // 🏷️ Persist bot type
            user_id: currentUser?.userId || '',
            user_email: currentUser?.email || '',
            user_ip: userIP,
            created_at: now,
            performance_id: performanceId,
            performance_title: performanceTitle,
            selected_date: '',
            selected_time: '',
            flow_start_time: now,
            flow_end_time: '',
            total_duration_ms: 0,
            is_completed: false,
            completion_status: 'in_progress',
            final_seats: [],
            booking_id: '',
            browser_info: collectBrowserInfo()
        },
        stages: {}
    };

    // sessionStorage에 저장
    saveLogToSession();

    return flowId;
}

/**
 * 로그 데이터를 sessionStorage에 저장
 */
function saveLogToSession() {
    if (logData) {
        sessionStorage.setItem('bookingLog', JSON.stringify(logData));
    }
}

/**
 * sessionStorage에서 로그 데이터 불러오기
 */
function loadLogFromSession() {
    const saved = sessionStorage.getItem('bookingLog');
    if (saved) {
        logData = JSON.parse(saved);
        return true;
    }
    return false;
}

/**
 * 단계 진입 기록
 */
function logStageEntry(stageName) {
    if (!logData) {
        loadLogFromSession();
    }

    if (!logData) {
        // 예매 완료 페이지이거나 이미 전송된 경우 에러 무시
        if (window.location.pathname.includes('booking_complete.html')) return;
        console.warn('로그 데이터가 아직 초기화되지 않았습니다.');
        return;
    }

    currentStage = stageName;
    stageStartTime = Date.now();
    mouseTrajectory = [];

    if (!logData.stages[stageName]) {
        logData.stages[stageName] = {
            entry_time: getISOTimestamp(),
            exit_time: '',
            duration_ms: 0,
            mouse_trajectory: [],
            clicks: [],
            viewport_width: window.innerWidth,
            viewport_height: window.innerHeight
        };
    } else {
        logData.stages[stageName].entry_time = getISOTimestamp();
    }

    saveLogToSession();
}

/**
 * 단계 종료 기록
 */
function logStageExit(stageName, additionalData = {}) {
    if (!logData || !logData.stages[stageName]) return;

    const now = getISOTimestamp();
    const entryTime = new Date(logData.stages[stageName].entry_time);
    const duration = Date.now() - new Date(entryTime).getTime();

    logData.stages[stageName].exit_time = now;
    logData.stages[stageName].duration_ms = duration;
    logData.stages[stageName].mouse_trajectory = mouseTrajectory;

    // 추가 데이터 병합
    Object.assign(logData.stages[stageName], additionalData);

    currentStage = null;
    mouseTrajectory = [];

    saveLogToSession();
}

/**
 * 마우스 이동 추적
 */
function trackMouseMove(event) {
    const now = Date.now();

    // 샘플링: 100ms마다 기록 (사람다움을 측정하기 좋은 간격)
    if (now - lastMouseMoveTime < 100) return;

    lastMouseMoveTime = now;

    const relativeTime = stageStartTime ? now - stageStartTime : 0;
    const nx = event.clientX / window.innerWidth;
    const ny = event.clientY / window.innerHeight;
    mouseTrajectory.push([
        event.clientX,
        event.clientY,
        relativeTime,
        nx.toFixed(4),
        ny.toFixed(4),
        event.pointerType || 'mouse'
    ]);
}

/**
 * 호버(머무름) 이벤트 추적
 */
function trackHover(event, targetInfo = {}) {
    if (!logData || !currentStage) return;

    const hoverData = {
        target: targetInfo.target || event.target.id || event.target.className,
        x: event.clientX,
        y: event.clientY,
        timestamp: stageStartTime ? Date.now() - stageStartTime : 0,
        ...targetInfo
    };

    if (!logData.stages[currentStage].hovers) {
        logData.stages[currentStage].hovers = [];
    }

    logData.stages[currentStage].hovers.push(hoverData);
    saveLogToSession();
}

// 클릭 지속 시간 측정을 위한 변수
let lastMouseDownTime = 0;

/**
 * mousedown 시점 기록
 */
function handleMouseDown(event) {
    lastMouseDownTime = Date.now();
}

/**
 * 클릭 이벤트 추적 (mouseup 시 호출되거나 click 시 호출)
 */
function trackClick(event, targetInfo = {}) {
    if (!logData || !currentStage) return;

    const clickDuration = lastMouseDownTime > 0 ? Date.now() - lastMouseDownTime : 0;

    const clickData = {
        x: event.clientX,
        y: event.clientY,
        nx: (event.clientX / window.innerWidth).toFixed(4),
        ny: (event.clientY / window.innerHeight).toFixed(4),
        timestamp: stageStartTime ? Date.now() - stageStartTime : 0,
        is_trusted: event.isTrusted,
        duration: clickDuration,
        button: event.button, // 0: 좌클릭, 2: 우클릭
        is_integer: Number.isInteger(event.clientX) && Number.isInteger(event.clientY),
        pointer_type: event.pointerType || 'mouse',
        ...targetInfo
    };

    if (!logData.stages[currentStage].clicks) {
        logData.stages[currentStage].clicks = [];
    }

    logData.stages[currentStage].clicks.push(clickData);
    lastMouseDownTime = 0; // 초기화
    saveLogToSession();
}



/**
 * 메타데이터 업데이트
 */
function updateMetadata(updates) {
    if (!logData) {
        loadLogFromSession();
    }

    if (logData) {
        Object.assign(logData.metadata, updates);
        saveLogToSession();
    }
}

/**
 * 최종 로그 완료 처리 및 서버 전송
 */
async function finalizeLog(isSuccess = true, bookingId = '') {
    if (!logData) {
        loadLogFromSession();
    }

    if (!logData) {
        if (window.location.pathname.includes('booking_complete.html')) return;
        console.warn('전송할 로그 데이터가 없습니다.');
        return;
    }

    const now = getISOTimestamp();
    const flowStart = new Date(logData.metadata.flow_start_time);
    const totalDuration = Date.now() - flowStart.getTime();

    logData.metadata.flow_end_time = now;
    logData.metadata.total_duration_ms = totalDuration;
    logData.metadata.is_completed = isSuccess;
    logData.metadata.completion_status = isSuccess ? 'success' : 'abandoned';
    logData.metadata.booking_id = bookingId;

    // 서버로 전송
    await sendLogToServer();
}

/**
 * 서버로 로그 전송
 */
async function sendLogToServer() {
    try {
        const response = await fetch('/api/logs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(logData)
        });

        const result = await response.json();

        if (result.success) {
            console.log('로그 저장 성공:', result.filename);
            // 로그 전송 후 세션 스토리지 정리
            sessionStorage.removeItem('bookingLog');
        } else {
            console.error('로그 저장 실패:', result);
        }

        return result;
    } catch (error) {
        console.error('로그 전송 에러:', error);
        // 실패 시 로컬에 복사본 저장
        localStorage.setItem('failedLog_' + Date.now(), JSON.stringify(logData));
    }
}

/**
 * 페이지 마우스 추적 활성화
 */
function enableMouseTracking() {
    document.addEventListener('pointermove', trackMouseMove);
    document.addEventListener('pointerdown', handleMouseDown);
}

/**
 * 페이지 마우스 추적 비활성화
 */
function disableMouseTracking() {
    document.removeEventListener('pointermove', trackMouseMove);
    document.removeEventListener('pointerdown', handleMouseDown);
}
