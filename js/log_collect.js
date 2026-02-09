/**
 * log_collect.js - ML 매크로 탐지를 위한 통합 로그 수집 모듈
 * 
 * 이 파일은 사이트의 비즈니스 로직과 분리되어 있으며, 
 * 사용자 행위(마우스, 클릭) 및 환경 정보를 독립적으로 수집합니다.
 */

// --- 1. 전역 상태 및 유틸리티 ---
let logData = null;
let currentStage = null;
let stageStartTime = null;
let mouseTrajectory = [];
let lastMouseMoveTime = 0;
let lastMouseDownTime = 0;

// 독립적인 타임스탬프 및 ID 생성 함수 (KST)
const getCollectTimestamp = () => {
  const now = new Date();
  // KST로 변환 (UTC+9)
  const kstOffset = 9 * 60; // 9시간을 분으로
  const kstTime = new Date(now.getTime() + (kstOffset * 60 * 1000));

  // ISO 8601 형식으로 반환 (YYYY-MM-DDTHH:mm:ss.sss+09:00)
  const year = kstTime.getUTCFullYear();
  const month = String(kstTime.getUTCMonth() + 1).padStart(2, '0');
  const day = String(kstTime.getUTCDate()).padStart(2, '0');
  const hours = String(kstTime.getUTCHours()).padStart(2, '0');
  const minutes = String(kstTime.getUTCMinutes()).padStart(2, '0');
  const seconds = String(kstTime.getUTCSeconds()).padStart(2, '0');
  const ms = String(kstTime.getUTCMilliseconds()).padStart(3, '0');

  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}.${ms}+09:00`;
};
const generateCollectId = (prefix, len) => prefix + Math.random().toString(36).substr(2, len);

// --- 2. 환경 정보 수집기 (Collector) ---
async function collectEnvironmentInfo() {
  let ip = '0.0.0.0';
  try {
    const res = await fetch('https://api.ipify.org?format=json');
    const data = await res.json();
    ip = data.ip;
  } catch (e) { }

  return {
    browser: {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      webdriver: navigator.webdriver,
      hardwareConcurrency: navigator.hardwareConcurrency,
      screen: {
        w: screen.width,
        h: screen.height,
        ratio: window.devicePixelRatio
      }
    },
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    ip: ip
  };
}

// --- 3. 핵심 로거 (Logger) ---
async function initLogCollector(perfId = '', perfTitle = '') {
  const env = await collectEnvironmentInfo();
  const now = getCollectTimestamp();

  // 세션 정보 확인 (기존 auth.js 의존성 제거를 위해 직접 접근)
  const userSession = JSON.parse(sessionStorage.getItem('currentUser') || '{}');
  const botType = sessionStorage.getItem('bot_type') || '';

  logData = {
    metadata: {
      flow_id: `flow_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}_${generateCollectId('', 6)}`,
      session_id: `sess_${generateCollectId('', 7)}`,
      bot_type: botType,
      user_email: userSession.email || '',
      user_ip: env.ip,
      performance_id: perfId,
      performance_title: perfTitle,
      created_at: now,
      flow_start_time: now,
      browser_info: env.browser,
      total_duration_ms: 0,
      is_completed: false
    },
    stages: {}
  };

  saveLogState();
}

function saveLogState() {
  if (logData) sessionStorage.setItem('bookingLog', JSON.stringify(logData));
}

function loadLogState() {
  const saved = sessionStorage.getItem('bookingLog');
  if (saved) {
    logData = JSON.parse(saved);
    return true;
  }
  return false;
}

// --- 4. 단계 및 행동 추적 (Tracker) ---
function recordStageEntry(stageName) {
  if (!logData && !loadLogState()) return;

  currentStage = stageName;
  stageStartTime = Date.now();
  mouseTrajectory = [];

  if (!logData.stages[stageName]) {
    logData.stages[stageName] = {
      entry_time: getCollectTimestamp(),
      mouse_trajectory: [],
      clicks: [],
      viewport: { w: window.innerWidth, h: window.innerHeight }
    };
  }
  saveLogState();
}

function recordStageExit(stageName, extra = {}) {
  if (!logData || !logData.stages[stageName]) return;

  const entryTime = new Date(logData.stages[stageName].entry_time);
  logData.stages[stageName].exit_time = getCollectTimestamp();
  logData.stages[stageName].duration_ms = Date.now() - entryTime.getTime();
  logData.stages[stageName].mouse_trajectory = mouseTrajectory;

  Object.assign(logData.stages[stageName], extra);
  saveLogState();
}

function updateMetadata(data) {
  if (!logData && !loadLogState()) return;
  Object.assign(logData.metadata, data);
  saveLogState();
}

// 마우스 및 클릭 이벤트 리스너
function setupEventListeners() {
  document.addEventListener('mousemove', (e) => {
    const now = Date.now();
    if (now - lastMouseMoveTime < 100) return; // 100ms 샘플링
    lastMouseMoveTime = now;

    const relTime = stageStartTime ? now - stageStartTime : 0;
    mouseTrajectory.push([
      e.clientX,
      e.clientY,
      relTime,
      (e.clientX / window.innerWidth).toFixed(4),
      (e.clientY / window.innerHeight).toFixed(4)
    ]);
  });

  document.addEventListener('mousedown', () => { lastMouseDownTime = Date.now(); });

  document.addEventListener('mouseup', (e) => {
    if (!logData || !currentStage) return;

    const clickDuration = lastMouseDownTime > 0 ? Date.now() - lastMouseDownTime : 0;
    const clickData = {
      x: e.clientX,
      y: e.clientY,
      nx: (e.clientX / window.innerWidth).toFixed(4),
      ny: (e.clientY / window.innerHeight).toFixed(4),
      timestamp: stageStartTime ? Date.now() - stageStartTime : 0,
      is_trusted: e.isTrusted,
      duration: clickDuration,
      button: e.button,
      is_integer: Number.isInteger(e.clientX) && Number.isInteger(e.clientY)
    };

    if (!logData.stages[currentStage].clicks) logData.stages[currentStage].clicks = [];
    logData.stages[currentStage].clicks.push(clickData);
    saveLogState();
  });
}

// --- 5. 서버 전송 및 초기화 ---
async function uploadLog(isSuccess = true, bookingId = '') {
  if (!logData && !loadLogState()) return;

  const flowStart = new Date(logData.metadata.flow_start_time);
  logData.metadata.flow_end_time = getCollectTimestamp();
  logData.metadata.total_duration_ms = Date.now() - flowStart.getTime();
  logData.metadata.is_completed = isSuccess;
  logData.metadata.booking_id = bookingId;

  // ✅ completion_status 추가 (예매 완료 페이지에서만 success)
  logData.metadata.completion_status = isSuccess ? "success" : "failed";

  try {
    const response = await fetch('/api/logs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(logData)
    });
    const result = await response.json();
    if (result.success) {
      console.log('[Collect] 로그 전송 완료:', result.filename);
      sessionStorage.removeItem('bookingLog');
    }
  } catch (error) {
    console.error('[Collect] 전송 실패:', error);
  }
}

// --- 6. 페이지 이탈 시 자동 로그 전송 (실패 처리) ---
window.addEventListener('beforeunload', () => {
  // booking_complete.html이 아닌 경우에만 실패로 전송
  if (!window.location.pathname.includes('booking_complete.html')) {
    const currentLog = loadLogState();
    if (currentLog && !currentLog.metadata.completion_status) {
      // 동기 방식으로 전송 (페이지 언로드 전에 전송)
      const flowStart = new Date(currentLog.metadata.flow_start_time);
      currentLog.metadata.flow_end_time = getCollectTimestamp();
      currentLog.metadata.total_duration_ms = Date.now() - flowStart.getTime();
      currentLog.metadata.is_completed = false;
      currentLog.metadata.completion_status = "abandoned";

      // sendBeacon 사용 (페이지 언로드 시에도 전송 보장)
      navigator.sendBeacon('/api/logs', JSON.stringify(currentLog));
    }
  }
});

// 초기화 실행
setupEventListeners();
