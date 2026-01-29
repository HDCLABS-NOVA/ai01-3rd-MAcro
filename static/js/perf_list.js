// 공연 목록 페이지 JavaScript
// 템플릿에서 performances 변수를 전역으로 설정해야 함

// ============== LogCollector 사용 ==============
// 로그 데이터 초기화
const logData = LogCollector.initPerfListLog();

let currentPerfId = null;
let selectedDate = null;
let selectedTime = null;

function openModal(perfId) {
  currentPerfId = perfId;
  logData.performance_id = perfId;

  // performances는 템플릿에서 전역으로 설정됨
  const perf = performances.find(p => p.id === perfId);

  // 카드 클릭 로그
  logData.card_clicks.push({
    performance_id: perfId,
    performance_title: perf.title,
    timestamp: new Date().toISOString()
  });
  logData.actions.push({
    action: 'card_click',
    target: perfId,
    timestamp: new Date().toISOString()
  });

  document.getElementById('modalTitle').textContent = perf.title;

  // 날짜 옵션
  const dateContainer = document.getElementById('dateOptions');
  dateContainer.innerHTML = perf.dates.map(d =>
    `<div class="date-option" onclick="selectDate(this, '${d}')">${d}</div>`
  ).join('');

  // 시간 옵션
  const timeContainer = document.getElementById('timeOptions');
  timeContainer.innerHTML = perf.times.map(t =>
    `<div class="time-option" onclick="selectTime(this, '${t}')">${t}</div>`
  ).join('');

  selectedDate = null;
  selectedTime = null;
  document.getElementById('btnConfirm').disabled = true;

  document.getElementById('modalOverlay').classList.add('active');
}

function closeModal() {
  document.getElementById('modalOverlay').classList.remove('active');
  logData.actions.push({
    action: 'modal_close',
    timestamp: new Date().toISOString()
  });
}

function selectDate(el, date) {
  document.querySelectorAll('.date-option').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  selectedDate = date;

  logData.date_selections.push({
    date: date,
    timestamp: new Date().toISOString()
  });
  logData.actions.push({
    action: 'date_select',
    target: date,
    timestamp: new Date().toISOString()
  });

  checkSelection();
}

function selectTime(el, time) {
  document.querySelectorAll('.time-option').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  selectedTime = time;

  logData.time_selections.push({
    time: time,
    timestamp: new Date().toISOString()
  });
  logData.actions.push({
    action: 'time_select',
    target: time,
    timestamp: new Date().toISOString()
  });

  checkSelection();
}

function checkSelection() {
  document.getElementById('btnConfirm').disabled = !(selectedDate && selectedTime);
}

function goToQueue() {
  // 공연 정보 조회
  const perf = performances.find(p => p.id === currentPerfId);
  if (!perf) {
    alert('공연 정보를 찾을 수 없습니다.');
    return;
  }

  // 1. Flow 로그 초기화 (예매 시도 시작)
  const userId = typeof user !== 'undefined' && user ? user.user_id : '';
  const userEmail = typeof user !== 'undefined' && user ? user.email : '';

  LogCollector.initFlowLog(
    currentPerfId,
    perf.title,
    selectedDate,
    selectedTime,
    userId,
    userEmail
  );

  // 2. perf 단계 데이터 추가
  logData.page_exit_time = new Date().toISOString();
  logData.selected_date = selectedDate;
  logData.selected_time = selectedTime;
  logData.actions.push({
    action: 'booking_start',
    target: currentPerfId,
    date: selectedDate,
    time: selectedTime,
    timestamp: new Date().toISOString()
  });

  const perfStageData = {
    exit_time: new Date().toISOString(),
    duration_ms: Date.now() - new Date(logData.page_entry_time).getTime(),
    card_clicks: logData.card_clicks,
    date_selections: logData.date_selections,
    time_selections: logData.time_selections,
    actions: logData.actions,
    mouse_trajectory: logData.mouse_trajectory
  };

  LogCollector.addStageToFlow('perf', perfStageData);

  // 3. 다음 페이지로 이동
  window.location.href = `/queue/${currentPerfId}?date=${selectedDate}&time=${selectedTime}`;
}

// 모달 외부 클릭 시 닫기
document.addEventListener('DOMContentLoaded', function () {
  const modalOverlay = document.getElementById('modalOverlay');
  if (modalOverlay) {
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === e.currentTarget) closeModal();
    });
  }
});
