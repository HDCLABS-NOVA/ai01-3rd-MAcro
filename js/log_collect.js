/**
 * log_collect.js - ML 留ㅽ겕濡??먯?瑜??꾪븳 ?듯빀 濡쒓렇 ?섏쭛 紐⑤뱢
 * 
 * ???뚯씪? ?ъ씠?몄쓽 鍮꾩쫰?덉뒪 濡쒖쭅怨?遺꾨━?섏뼱 ?덉쑝硫? 
 * ?ъ슜???됱쐞(留덉슦?? ?대┃) 諛??섍꼍 ?뺣낫瑜??낅┰?곸쑝濡??섏쭛?⑸땲??
 */

// --- 1. ?꾩뿭 ?곹깭 諛??좏떥由ы떚 ---
let logData = null;
let currentStage = null;
let stageStartTime = null;
let mouseTrajectory = [];
let lastMouseMoveTime = 0;
let lastMouseDownTime = 0;

// ?낅┰?곸씤 ??꾩뒪?ы봽 諛?ID ?앹꽦 ?⑥닔 (KST)
const getCollectTimestamp = () => {
  const now = new Date();
  // KST濡?蹂??(UTC+9)
  const kstOffset = 9 * 60; // 9?쒓컙??遺꾩쑝濡?
  const kstTime = new Date(now.getTime() + (kstOffset * 60 * 1000));

  // ISO 8601 ?뺤떇?쇰줈 諛섑솚 (YYYY-MM-DDTHH:mm:ss.sss+09:00)
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

// --- 2. ?섍꼍 ?뺣낫 ?섏쭛湲?(Collector) ---
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

// --- 3. ?듭떖 濡쒓굅 (Logger) ---
async function initLogCollector(perfId = '', perfTitle = '') {
  const env = await collectEnvironmentInfo();
  const now = getCollectTimestamp();

  // ?몄뀡 ?뺣낫 ?뺤씤 (湲곗〈 auth.js ?섏〈???쒓굅瑜??꾪빐 吏곸젒 ?묎렐)
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

// ?덈ℓ ?쒖옉 ?쒖젏??flow_id瑜??뺤젙 (?덈ℓ??1媛?濡쒓렇 蹂댁옣??
function startBookingFlow(perfId = '', perfTitle = '') {
  if (!logData && !loadLogState()) return;
  if (!logData.metadata) logData.metadata = {};
  if (logData.metadata.booking_flow_started) return;

  if (perfId) logData.metadata.performance_id = perfId;
  if (perfTitle) logData.metadata.performance_title = perfTitle;

  logData.metadata.flow_id = `flow_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}_${generateCollectId('', 6)}`;
  logData.metadata.session_id = `sess_${generateCollectId('', 7)}`;
  logData.metadata.booking_flow_started = true;

  saveLogState();
}

// --- 4. ?④퀎 諛??됰룞 異붿쟻 (Tracker) ---
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

// 留덉슦??諛??대┃ ?대깽??由ъ뒪??
function setupEventListeners() {
  document.addEventListener('pointermove', (e) => {
    const now = Date.now();
    if (now - lastMouseMoveTime < 100) return; // 100ms ?섑뵆留?
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

  document.addEventListener('pointerdown', () => { lastMouseDownTime = Date.now(); });

  document.addEventListener('pointerup', (e) => {
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
      button: e.button
    };

    if (!logData.stages[currentStage].clicks) logData.stages[currentStage].clicks = [];
    logData.stages[currentStage].clicks.push(clickData);
    saveLogState();
  });
}

// --- 5. ?쒕쾭 ?꾩넚 諛?珥덇린??---
async function uploadLog(isSuccess = true, bookingId = '') {
  if (!logData && !loadLogState()) return;

  const flowStart = new Date(logData.metadata.flow_start_time);
  logData.metadata.flow_end_time = getCollectTimestamp();
  logData.metadata.total_duration_ms = Date.now() - flowStart.getTime();
  logData.metadata.is_completed = isSuccess;
  logData.metadata.booking_id = bookingId;

  // ??completion_status 異붽? (?덈ℓ ?꾨즺 ?섏씠吏?먯꽌留?success)
  logData.metadata.completion_status = isSuccess ? "success" : "failed";

  try {
    const response = await fetch('/api/logs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(logData)
    });
    const result = await response.json();
    const decision = String(result?.decision || result?.risk?.decision || '').toLowerCase();
    if (response.status === 403 && decision === 'block') {
      alert('비정상적인 접근으로 일시적으로 서비스 접속이 제한되었습니다');
      return result;
    }
    if (result.success) {
      console.log('[Collect] 濡쒓렇 ?꾩넚 ?꾨즺:', result.filename);
      sessionStorage.removeItem('bookingLog');
    }
  } catch (error) {
    console.error('[Collect] ?꾩넚 ?ㅽ뙣:', error);
  }
}

// --- 6. ?섏씠吏 ?댄깉 ???먮룞 濡쒓렇 ?꾩넚 (?ㅽ뙣 泥섎━) ---
window.addEventListener('beforeunload', () => {
  // booking_complete.html???꾨땶 寃쎌슦?먮쭔 ?ㅽ뙣濡??꾩넚
  if (!window.location.pathname.includes('booking_complete.html')) {
    const currentLog = loadLogState();
    if (currentLog && !currentLog.metadata.completion_status) {
      // ?숆린 諛⑹떇?쇰줈 ?꾩넚 (?섏씠吏 ?몃줈???꾩뿉 ?꾩넚)
      const flowStart = new Date(currentLog.metadata.flow_start_time);
      currentLog.metadata.flow_end_time = getCollectTimestamp();
      currentLog.metadata.total_duration_ms = Date.now() - flowStart.getTime();
      currentLog.metadata.is_completed = false;
      currentLog.metadata.completion_status = "abandoned";

      // sendBeacon ?ъ슜 (?섏씠吏 ?몃줈???쒖뿉???꾩넚 蹂댁옣)
      navigator.sendBeacon('/api/logs', JSON.stringify(currentLog));
    }
  }
});

// 珥덇린???ㅽ뻾
setupEventListeners();

