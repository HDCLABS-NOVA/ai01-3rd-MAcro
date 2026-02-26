// 濡쒓퉭 ?쒖뒪??- ?ъ슜???됰룞 異붿쟻 諛?濡쒓렇 ?앹꽦

let logData = null;
let currentStage = null;
let stageStartTime = null;
let mouseTrajectory = [];
let lastMouseMoveTime = 0;
let mouseDownTime = 0;  // 클릭 지속 시간 측정용

/**
 * 濡쒓굅 珥덇린??
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
            bot_type: botType, // ?뤇截?Persist bot type
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

    // sessionStorage?????
    saveLogToSession();

    return flowId;
}

/**
 * 濡쒓렇 ?곗씠?곕? sessionStorage?????
 */
function saveLogToSession() {
    if (logData) {
        sessionStorage.setItem('bookingLog', JSON.stringify(logData));
    }
}

/**
 * sessionStorage?먯꽌 濡쒓렇 ?곗씠??遺덈윭?ㅺ린
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
 * ?④퀎 吏꾩엯 湲곕줉
 */
function logStageEntry(stageName) {
    if (!logData) {
        loadLogFromSession();
    }

    if (!logData) {
        // ?덈ℓ ?꾨즺 ?섏씠吏?닿굅???대? ?꾩넚??寃쎌슦 ?먮윭 臾댁떆
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
 * ?④퀎 醫낅즺 湲곕줉
 */
function logStageExit(stageName, additionalData = {}) {
    if (!logData || !logData.stages[stageName]) return;

    const now = getISOTimestamp();
    const entryTime = new Date(logData.stages[stageName].entry_time);
    const duration = Date.now() - new Date(entryTime).getTime();

    logData.stages[stageName].exit_time = now;
    logData.stages[stageName].duration_ms = duration;
    logData.stages[stageName].mouse_trajectory = mouseTrajectory;

    // 異붽? ?곗씠??蹂묓빀
    Object.assign(logData.stages[stageName], additionalData);

    currentStage = null;
    mouseTrajectory = [];

    saveLogToSession();
}

/**
 * 留덉슦???대룞 異붿쟻
 */
function trackMouseMove(event) {
    const now = Date.now();

    // ?섑뵆留? 100ms留덈떎 湲곕줉 (?щ엺?ㅼ???痢≪젙?섍린 醫뗭? 媛꾧꺽)
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
        ny.toFixed(4)
    ]);
}

/**
 * ?몃쾭(癒몃Т由? ?대깽??異붿쟻
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

// ?대┃ 吏???쒓컙 痢≪젙???꾪븳 蹂??
let lastMouseDownTime = 0;

/**
 * mousedown ?쒖젏 湲곕줉
 */
function handleMouseDown(event) {
    lastMouseDownTime = Date.now();
}

/**
 * ?대┃ ?대깽??異붿쟻 (mouseup ???몄텧?섍굅??click ???몄텧)
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
    lastMouseDownTime = 0; // 珥덇린??
    saveLogToSession();
}



/**
 * 硫뷀??곗씠???낅뜲?댄듃
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
 * 理쒖쥌 濡쒓렇 ?꾨즺 泥섎━ 諛??쒕쾭 ?꾩넚
 */
async function finalizeLog(isSuccess = true, bookingId = '') {
    if (!logData) {
        loadLogFromSession();
    }

    if (!logData) {
        if (window.location.pathname.includes('booking_complete.html')) return;
        console.warn('?꾩넚??濡쒓렇 ?곗씠?곌? ?놁뒿?덈떎.');
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

    // ?쒕쾭濡??꾩넚
    await sendLogToServer();
}

/**
 * ?쒕쾭濡?濡쒓렇 ?꾩넚
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
        const decision = String(result?.decision || result?.risk?.decision || '').toLowerCase();
        if (response.status === 403 && decision === 'block') {
            alert('비정상적인 접근으로 일시적으로 서비스 접속이 제한되었습니다');
            return result;
        }

        if (result.success) {
            console.log('濡쒓렇 ????깃났:', result.filename);
            // 濡쒓렇 ?꾩넚 ???몄뀡 ?ㅽ넗由ъ? ?뺣━
            sessionStorage.removeItem('bookingLog');
        } else {
            console.error('濡쒓렇 ????ㅽ뙣:', result);
        }

        return result;
    } catch (error) {
        console.error('濡쒓렇 ?꾩넚 ?먮윭:', error);
        // ?ㅽ뙣 ??濡쒖뺄??蹂듭궗蹂????
        localStorage.setItem('failedLog_' + Date.now(), JSON.stringify(logData));
    }
}

/**
 * ?섏씠吏 留덉슦??異붿쟻 ?쒖꽦??
 */
function enableMouseTracking() {
    document.addEventListener('mousemove', trackMouseMove);
    // mousedown 시간 기록 (click_duration 측정)
    document.addEventListener('mousedown', () => { mouseDownTime = Date.now(); });
}

/**
 * ?섏씠吏 留덉슦??異붿쟻 鍮꾪솢?깊솕
 */
function disableMouseTracking() {
    document.removeEventListener('pointermove', trackMouseMove);
    document.removeEventListener('pointerdown', handleMouseDown);
}

