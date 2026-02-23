// queue.js - 대기열 페이지 (서버 연동)

loadLogState();
recordStageEntry('queue');

const queuePositionEl = document.getElementById('queue-position');
const queueTotalEl = document.getElementById('queue-total');

const flowData = getFlowData();
if (!flowData || !flowData.performanceId) {
  showAlert('예매 흐름 정보가 없습니다. 처음부터 다시 시작해주세요.', 'warning');
  setTimeout(() => navigateTo('index.html'), 800);
}

let queueId = '';
let queueStartedMs = Date.now();
let initialPosition = 0;
let totalQueue = 0;
let queueJumpCount = 0;
let positionUpdates = [];
let pollIntervals = [];
let lastPollEpochMs = 0;

function getLogMeta() {
  try {
    const raw = sessionStorage.getItem('bookingLog');
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    const meta = parsed?.metadata || {};
    return {
      flow_id: meta.flow_id || '',
      session_id: meta.session_id || '',
      user_email: meta.user_email || '',
      bot_type: meta.bot_type || '',
    };
  } catch (e) {
    return {};
  }
}

function getStartToken() {
  return String(sessionStorage.getItem('booking_start_token') || '').trim();
}

function percentile(values, p) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  if (sorted.length === 1) return sorted[0];
  const rank = Math.max(0, Math.min(100, p)) / 100 * (sorted.length - 1);
  const low = Math.floor(rank);
  const high = Math.ceil(rank);
  if (low === high) return sorted[low];
  const w = rank - low;
  return sorted[low] * (1 - w) + sorted[high] * w;
}

function pollStats(values) {
  if (!values.length) return { min: 0, p50: 0, p95: 0 };
  return {
    min: Math.round(Math.min(...values)),
    p50: Math.round(percentile(values, 50)),
    p95: Math.round(percentile(values, 95)),
  };
}

function recordPositionUpdate(queue) {
  positionUpdates.push({
    position: Number(queue.position || 0),
    status: String(queue.state || 'unknown'),
    timestamp: getCollectTimestamp(),
  });
  if (positionUpdates.length > 100) {
    positionUpdates = positionUpdates.slice(-100);
  }
}

async function apiJson(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  let body = {};
  try {
    body = await res.json();
  } catch (e) {
    body = {};
  }
  return { ok: res.ok, status: res.status, body };
}

async function joinQueue() {
  const meta = getLogMeta();
  const payload = {
    performance_id: flowData.performanceId,
    flow_id: meta.flow_id || '',
    session_id: meta.session_id || '',
    user_email: meta.user_email || '',
    bot_type: meta.bot_type || '',
    start_token: getStartToken(),
  };

  const { ok, body } = await apiJson('/api/queue/join', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (!ok || !body.success) {
    throw new Error(body.detail || body.message || '대기열 진입에 실패했습니다.');
  }
  return body.queue;
}

async function getQueueStatus() {
  const { ok, body, status } = await apiJson(`/api/queue/status?queue_id=${encodeURIComponent(queueId)}`, {
    method: 'GET',
  });
  if (!ok || !body.success) {
    if (status === 404 || status === 410) {
      throw new Error('대기열 세션이 만료되었습니다. 다시 진입해주세요.');
    }
    throw new Error(body.detail || body.message || '대기열 상태 조회에 실패했습니다.');
  }
  return body.queue;
}

async function enterQueue() {
  const meta = getLogMeta();
  const payload = {
    queue_id: queueId,
    performance_id: flowData.performanceId,
    flow_id: meta.flow_id || '',
    session_id: meta.session_id || '',
  };

  const { ok, body, status } = await apiJson('/api/queue/enter', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  if (!ok || !body.success) {
    if (status === 409) {
      return { ready: false, queue: body.queue || null };
    }
    throw new Error(body.detail || body.message || '대기열 통과 처리에 실패했습니다.');
  }
  return { ready: true, queue: body.queue || null };
}

function updateQueueUi(queue) {
  if (queuePositionEl) {
    queuePositionEl.textContent = queue.state === 'ready' ? '통과 준비' : String(queue.position ?? '-');
  }
  if (queueTotalEl) {
    const total = Number(queue.total_queue || 0);
    queueTotalEl.textContent = `전체 대기: ${total.toLocaleString()} 명`;
  }
}

async function runQueue() {
  try {
    const joined = await joinQueue();
    queueId = joined.queue_id;
    initialPosition = Number(joined.position || 0);
    totalQueue = Number(joined.total_queue || 0);
    queueJumpCount = Number(joined.jump_count || 0);
    queueStartedMs = Date.now();

    updateQueueUi(joined);
    recordPositionUpdate(joined);

    let queue = joined;
    while (queue.state === 'waiting') {
      const pollAfter = Math.max(200, Number(queue.poll_after_ms || 500));
      await sleep(pollAfter);

      const before = Date.now();
      queue = await getQueueStatus();
      const after = Date.now();
      const interval = lastPollEpochMs > 0 ? before - lastPollEpochMs : 0;
      lastPollEpochMs = before;
      if (interval > 0) pollIntervals.push(interval);
      pollIntervals.push(Math.max(1, after - before));

      queueJumpCount = Number(queue.jump_count || queueJumpCount || 0);
      totalQueue = Number(queue.total_queue || totalQueue || 0);
      updateQueueUi(queue);
      recordPositionUpdate(queue);
    }

    if (queue.state !== 'ready') {
      throw new Error('대기열 상태가 비정상적입니다. 다시 시도해주세요.');
    }

    const entered = await enterQueue();
    if (!entered.ready) {
      throw new Error('아직 입장 가능한 상태가 아닙니다. 다시 시도해주세요.');
    }

    const finalQueue = entered.queue || queue;
    updateQueueUi({ ...finalQueue, state: 'ready', position: 0 });
    recordPositionUpdate({ ...finalQueue, state: 'ready', position: 0 });
    sessionStorage.removeItem('booking_start_token');
    sessionStorage.removeItem('booking_start_token_expires_epoch_ms');

    const waitDurationMs = Math.max(0, Date.now() - queueStartedMs);
    recordStageExit('queue', {
      initial_position: initialPosition,
      final_position: 0,
      total_queue: totalQueue,
      wait_duration_ms: waitDurationMs,
      queue_entry_trigger: 'api_redirect',
      request_polling_interval_ms_stats: pollStats(pollIntervals),
      queue_jump_count: queueJumpCount,
      position_updates: positionUpdates,
    });

    setTimeout(() => navigateTo('seat_select.html'), 300);
  } catch (error) {
    console.error('[Queue] error:', error);
    showAlert(error.message || '대기열 처리 중 오류가 발생했습니다.', 'error');
    setTimeout(() => navigateTo('performance_detail.html?id=' + encodeURIComponent(flowData?.performanceId || '')), 1200);
  }
}

if (flowData && flowData.performanceId) {
  runQueue();
}
