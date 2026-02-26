// 로깅 시스템 - 사용자 행동 추적 및 로그 생성

let logData = null;
let currentStage = null;
let stageStartTime = null;
let mouseTrajectory = [];
let lastMouseMoveTime = 0;
let mouseDownTime = 0;  // 클릭 지속 시간 측정용

/**
 * 로거 초기화
 */
async function initLogger(performanceId = '', performanceTitle = '') {
    const currentUser = getCurrentUser();
    const userIP = await getUserIP();

    const now = getISOTimestamp();
    const flowId = `flow_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}_${generateRandomId('', 6)}`;
    const sessionId = `sess_${generateRandomId('', 7)}`;

    logData = {
        metadata: {
            flow_id: flowId,
            session_id: sessionId,
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
        console.error('로그 데이터가 초기화되지 않았습니다.');
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
    // mouse_trajectory는 trackMouseMove에서 실시간으로 업데이트되므로 여기서 덮어쓰지 않음
    // logData.stages[stageName].mouse_trajectory = mouseTrajectory;

    // 추가 데이터 병합
    Object.assign(logData.stages[stageName], additionalData);

    currentStage = null;
    mouseTrajectory = [];

    saveLogToSession();
}

/**
 * 마우스 이동 추적
 */
let currentHoverTarget = null; // 현재 호버 중인 중요 요소 타겟 (예: 좌석 ID)
let lastMouseLogTime = 0; // trackMouseMove에서 사용할 새로운 변수

function setHoverTarget(target) {
    currentHoverTarget = target;
}

function trackMouseMove(event) {
    if (!logData || !currentStage) return;

    const now = Date.now();
    // 50ms 간격으로 쓰기 (스로틀링)
    if (now - lastMouseLogTime < 50) return;

    lastMouseLogTime = now;

    // 좌표, 시간, 그리고 현재 호버 타겟(있다면) 저장
    // [x, y, time, target]
    const point = [
        event.clientX,
        event.clientY,
        stageStartTime ? now - stageStartTime : 0
    ];

    if (currentHoverTarget) {
        point.push(currentHoverTarget);
    }

    // 1. 전역 변수 배열에 추가 (logStageExit에서 덮어쓸 때 사용됨)
    mouseTrajectory.push(point);

    // 2. logData 객체에도 직접 추가 (실시간 업데이트용)
    if (logData.stages[currentStage].mouse_trajectory) {
        logData.stages[currentStage].mouse_trajectory.push(point);
    }

    // 3. 주기적으로 세션 스토리지에 저장 (1초마다) - 데이터 유실 방지
    if (now - lastSessionSaveTime > 1000) {
        saveLogToSession();
        lastSessionSaveTime = now;
    }
}
let lastSessionSaveTime = 0;

/**
 * 클릭 이벤트 추적
 */
function trackClick(event, targetInfo = {}) {
    if (!logData || !currentStage) return;

    const clickTs = stageStartTime ? Date.now() - stageStartTime : 0;
    const duration = mouseDownTime > 0 ? Date.now() - mouseDownTime : 0;
    mouseDownTime = 0;

    // 클릭 직전 궤적에서 최대 이동 속도 계산 (매크로 감지 핵심 신호)
    // 매크로: 순간이동 → 한 샘플(50ms)에 수백px 이동 → 속도 수천px/s
    // 사람: 최대 ~1000px/s
    let maxVelocityPx = 0;
    const traj = logData.stages[currentStage]?.mouse_trajectory || [];
    if (traj.length >= 2) {
        for (let i = 1; i < traj.length; i++) {
            const dx = traj[i][0] - traj[i - 1][0];
            const dy = traj[i][1] - traj[i - 1][1];
            const dt = traj[i][2] - traj[i - 1][2]; // ms
            if (dt > 0) {
                const v = Math.sqrt(dx * dx + dy * dy) / dt * 1000; // px/s
                if (v > maxVelocityPx) maxVelocityPx = v;
            }
        }
    }

    const clickData = {
        x: event.clientX,
        y: event.clientY,
        nx: (event.clientX / window.innerWidth).toFixed(4),
        ny: (event.clientY / window.innerHeight).toFixed(4),
        timestamp: clickTs,
        is_trusted: event.isTrusted,
        click_duration: duration,          // mousedown→mouseup 실측(ms)
        max_velocity_before: Math.round(maxVelocityPx), // 클릭 전 최대 속도(px/s)
        traj_points_before: traj.filter(p => p[2] < clickTs).length, // 클릭 전 궤적 포인트 수
        is_integer: Number.isInteger(event.clientX) && Number.isInteger(event.clientY),
        ...targetInfo
    };

    if (!logData.stages[currentStage].clicks) {
        logData.stages[currentStage].clicks = [];
    }

    logData.stages[currentStage].clicks.push(clickData);
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
        console.error('로그 데이터가 없습니다.');
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
    document.addEventListener('mousemove', trackMouseMove);
    // mousedown 시간 기록 (click_duration 측정)
    document.addEventListener('mousedown', () => { mouseDownTime = Date.now(); });
}

/**
 * 페이지 마우스 추적 비활성화
 */
function disableMouseTracking() {
    document.removeEventListener('mousemove', trackMouseMove);
}
