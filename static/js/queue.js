// 대기열 페이지 JavaScript

// 페이지 초기화 시 호출 필요 (template에서 전역변수 설정 필요)
// const perfId, selectedDate, selectedTime, totalQueue, initialPosition

let isReady = false;

// ============== LogCollector 사용 ==============
// 대기열 로그 데이터 초기화
const logData = LogCollector.initQueueLog(
  typeof perfId !== 'undefined' ? perfId : '',
  typeof selectedDate !== 'undefined' ? selectedDate : '',
  typeof selectedTime !== 'undefined' ? selectedTime : '',
  typeof totalQueue !== 'undefined' ? totalQueue : 0,
  typeof initialPosition !== 'undefined' ? initialPosition : 0
);
const startTime = Date.now();

function updateQueue() {
  fetch('/api/queue/status')
    .then(res => res.json())
    .then(data => {
      if (data.status === 'ready') {
        isReady = true;

        // 로그 기록
        logData.queue_end_time = new Date().toISOString();
        logData.final_position = 0;
        logData.wait_duration_ms = Date.now() - startTime;
        logData.position_updates.push({
          position: 0,
          status: 'ready',
          timestamp: new Date().toISOString()
        });

        document.getElementById('position').textContent = '0';
        document.getElementById('progressFill').style.width = '100%';
        document.getElementById('progressPercent').textContent = '100%';
        document.getElementById('estimatedTime').textContent = '입장 가능!';
        document.getElementById('loadingDots').style.display = 'none';

        // 자동 입장 (버튼 없이)
        setTimeout(() => {
          enterBooking();
        }, 800);
      } else if (data.status === 'waiting') {
        const position = data.position;
        const total = typeof totalQueue !== 'undefined' ? totalQueue : 100;
        const progress = Math.round((1 - position / total) * 100);

        // 위치 변화 로그
        logData.position_updates.push({
          position: position,
          progress: progress,
          estimated_minutes: data.estimated_minutes,
          timestamp: new Date().toISOString()
        });

        document.getElementById('position').textContent = position.toLocaleString();
        document.getElementById('progressFill').style.width = progress + '%';
        document.getElementById('progressPercent').textContent = progress + '%';
        document.getElementById('estimatedTime').textContent = `약 ${data.estimated_minutes}분`;
      }
    })
    .catch(err => console.error('Error:', err));
}

function enterBooking() {
  const pId = typeof perfId !== 'undefined' ? perfId : '';
  const sDate = typeof selectedDate !== 'undefined' ? selectedDate : '';
  const sTime = typeof selectedTime !== 'undefined' ? selectedTime : '';

  // queue 단계 데이터 추가
  const queueStageData = {
    exit_time: new Date().toISOString(),
    duration_ms: Date.now() - new Date(logData.queue_start_time).getTime(),
    initial_position: logData.initial_position,
    final_position: 0,
    total_queue: logData.total_queue,
    wait_duration_ms: logData.wait_duration_ms,
    position_updates: logData.position_updates,
    mouse_trajectory: logData.mouse_trajectory
  };

  LogCollector.addStageToFlow('queue', queueStageData);

  // 다음 페이지로 이동
  window.location.href = `/captcha/${pId}?date=${sDate}&time=${sTime}`;
}

// 1초마다 대기열 업데이트
setInterval(updateQueue, 1000);

// DOM 로드 후 초기화
document.addEventListener('DOMContentLoaded', function () {
  updateQueue();

  // 이탈 감지
  window.addEventListener('beforeunload', function () {
    const flowLog = LogCollector.completeFlow('failed_abandoned', null, null);
    if (flowLog) {
      navigator.sendBeacon('/api/flow-log', JSON.stringify(flowLog));
    }
  });
});
