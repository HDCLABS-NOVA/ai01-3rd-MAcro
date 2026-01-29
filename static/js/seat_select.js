// 좌석 선택 페이지(index.html) JavaScript
// 템플릿에서 다음 변수들을 전역으로 설정해야 함:
// sessionId, perfId, selectedDate, selectedTime, prices, mode, selectedSection, selectedGrade

let seats = {};
let selectedSeats = [];
let pageStartTime = Date.now();
let mouseTrajectory = [];
let clicks = [];
let hovers = [];
let lastActionTime = Date.now();

// 구역별 좌석 정의
const sectionConfig = {
  'VIP-L': { rows: ['A', 'B', 'C', 'D'], cols: [1, 20], grade: 'VIP' },
  'VIP-C': { rows: ['A', 'B', 'C', 'D'], cols: [21, 40], grade: 'VIP' },
  'VIP-R': { rows: ['A', 'B', 'C', 'D'], cols: [41, 60], grade: 'VIP' },
  'R-L': { rows: ['E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'], cols: [1, 20], grade: 'R' },
  'R-C': { rows: ['E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'], cols: [21, 40], grade: 'R' },
  'R-R': { rows: ['E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'], cols: [41, 60], grade: 'R' },
  'S-L': { rows: ['M', 'N', 'O', 'P'], cols: [1, 30], grade: 'S' },
  'S-R': { rows: ['M', 'N', 'O', 'P'], cols: [31, 60], grade: 'S' }
};

// 마우스 궤적 수집 시작 (LogCollector 사용 - 압축 포맷 30ms)
LogCollector.initMouseTracking(mouseTrajectory, 30, pageStartTime, false);

function initSeats() {
  const grid = document.getElementById('seatGrid');
  grid.innerHTML = '';

  const config = sectionConfig[selectedSection] || { rows: ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P'], cols: [1, 60], grade: 'R' };
  const rows = config.rows;
  const colStart = config.cols[0];
  const colEnd = config.cols[1];
  const sectionGrade = config.grade;

  rows.forEach(row => {
    const rowDiv = document.createElement('div');
    rowDiv.className = 'seat-row';

    const label = document.createElement('span');
    label.className = 'row-label';
    label.textContent = row;
    rowDiv.appendChild(label);

    for (let i = colStart; i <= colEnd; i++) {
      const seatId = `${sectionGrade}-${row}${i}`;

      const seat = document.createElement('button');
      seat.className = `seat ${sectionGrade.toLowerCase()}`;
      seat.dataset.seatId = seatId;
      seat.dataset.grade = sectionGrade;
      seat.textContent = i;

      seat.onclick = () => toggleSeat(seat, seatId, sectionGrade);
      seat.onmouseenter = () => logHover(seatId, true);
      seat.onmouseleave = () => logHover(seatId, false);

      seats[seatId] = { element: seat, grade: sectionGrade, status: 'available' };
      rowDiv.appendChild(seat);
    }

    const labelRight = document.createElement('span');
    labelRight.className = 'row-label';
    labelRight.textContent = row;
    rowDiv.appendChild(labelRight);

    grid.appendChild(rowDiv);
  });

  // 앞좌석 우선 판매완료 (앞행 + 중앙좌석 우선)
  const allSeatIds = Object.keys(seats);
  const soldRatio = 0.25 + Math.random() * 0.15; // 25~40% 매진
  const targetSoldCount = Math.floor(allSeatIds.length * soldRatio);

  // 행별 가중치 (앞좌석일수록 높음)
  const rowWeights = { 'A': 10, 'B': 9, 'C': 9, 'D': 8, 'E': 7, 'F': 6, 'G': 5, 'H': 4, 'I': 4, 'J': 3, 'K': 3, 'L': 2, 'M': 2, 'N': 1, 'O': 1, 'P': 1 };

  // 좌석번호 가중치 (중앙일수록 높음)
  function getSeatNumWeight(seatNum) {
    const center = 30;
    const distance = Math.abs(seatNum - center);
    return Math.max(1, 10 - distance * 0.25);
  }

  // 가중치 기반 좌석 정렬
  const weightedSeats = allSeatIds.map(seatId => {
    const row = seatId.match(/-([A-P])/)[1];
    const seatNum = parseInt(seatId.match(/(\d+)$/)[1]);
    const weight = rowWeights[row] * getSeatNumWeight(seatNum) * (0.5 + Math.random());
    return { seatId, weight };
  }).sort((a, b) => b.weight - a.weight);

  // 높은 가중치부터 매진 처리
  for (let i = 0; i < targetSoldCount && i < weightedSeats.length; i++) {
    const seatId = weightedSeats[i].seatId;
    seats[seatId].status = 'sold';
    seats[seatId].element.classList.add('sold');
  }
}

function toggleSeat(el, seatId, grade) {
  if (seats[seatId].status === 'sold') return;

  const now = Date.now();
  const timeDelta = now - lastActionTime;
  lastActionTime = now;

  const rect = el.getBoundingClientRect();
  const clickX = rect.left + rect.width / 2;
  const clickY = rect.top + rect.height / 2;
  // 클릭 메트릭 가져오기 (매크로 탐지)
  const clickMetrics = LogCollector.getClickMetrics(clickX, clickY);

  const clickData = {
    x: Math.floor(clickX),
    y: Math.floor(clickY),
    nx: parseFloat((clickX / window.innerWidth).toFixed(4)),
    ny: parseFloat((clickY / window.innerHeight).toFixed(4)),
    target: seatId,
    timestamp: now - pageStartTime,
    ...clickMetrics // is_trusted, click_duration, is_integer 추가
  };
  clicks.push(clickData);

  // 마우스 궤적에도 클릭 추가 (압축 포맷)
  mouseTrajectory.push([
    Math.floor(clickX),
    Math.floor(clickY),
    now - pageStartTime
  ]);

  logAction('seat_click', seatId, rect.left, rect.top, timeDelta);

  // 좌석 선택 취소는 이선좌 체크 안함
  if (selectedSeats.includes(seatId)) {
    selectedSeats = selectedSeats.filter(s => s !== seatId);
    el.classList.remove('selected');
  } else {
    // 30% 확률로 이선좌 발생
    if (Math.random() < 0.3) {
      seats[seatId].status = 'sold';
      el.classList.add('sold');
      el.classList.remove('selected');
      showSeatTakenAlert(seatId);
      logAction('seat_taken', seatId, rect.left, rect.top, 0);
      return;
    }

    if (selectedSeats.length >= 4) {
      alert('최대 4석까지 선택 가능합니다.');
      return;
    }
    selectedSeats.push(seatId);
    el.classList.add('selected');
  }

  updateSelectedUI();
}

// 이선좌 알림 표시
function showSeatTakenAlert(seatId) {
  // 기존 알림 제거
  const existing = document.querySelector('.seat-taken-modal');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.className = 'seat-taken-modal';
  modal.innerHTML = `
        <div class="seat-taken-content">
            <div class="seat-taken-icon">😢</div>
            <div class="seat-taken-title">이미 선점된 좌석입니다</div>
            <div class="seat-taken-msg">${seatId} 좌석은 다른 고객님이 먼저 선택하셨습니다.<br>다른 좌석을 선택해 주세요.</div>
            <button class="seat-taken-btn" onclick="this.closest('.seat-taken-modal').remove()">확인</button>
        </div>
    `;
  document.body.appendChild(modal);

  // 3초 후 자동 닫힘
  setTimeout(() => {
    if (modal.parentNode) modal.remove();
  }, 3000);
}

function updateSelectedUI() {
  const container = document.getElementById('selectedSeats');
  const btn = document.getElementById('btnBook');

  if (selectedSeats.length === 0) {
    container.innerHTML = '<span class="no-seat">좌석을 선택해주세요 (최대 4석)</span>';
    btn.disabled = true;
    btn.textContent = '좌석을 선택해주세요';
  } else {
    container.innerHTML = selectedSeats.map(s =>
      `<span class="selected-seat-tag">
                <span class="seat-name">${s}</span>
                <button class="seat-cancel" onclick="cancelSeat('${s}')" title="좌석 취소">✕</button>
            </span>`
    ).join('');
    btn.disabled = false;
    btn.textContent = `좌석 선택 완료 (${selectedSeats.length}석)`;
  }

  updatePrice();
}

// 사이드바에서 좌석 취소
function cancelSeat(seatId) {
  if (!selectedSeats.includes(seatId)) return;

  // 좌석 배열에서 제거
  selectedSeats = selectedSeats.filter(s => s !== seatId);

  // 좌석 그리드에서 selected 클래스 제거
  if (seats[seatId]) {
    seats[seatId].element.classList.remove('selected');
  }

  // 행동 로그 기록
  logAction('seat_cancel_sidebar', seatId, 0, 0, 0);

  updateSelectedUI();
}

function updatePrice() {
  let total = 0;
  selectedSeats.forEach(seatId => {
    const grade = seats[seatId].grade;
    total += prices[grade] || 0;
  });

  document.getElementById('seatCount').textContent = selectedSeats.length + '석';
  document.getElementById('totalPrice').textContent = total.toLocaleString() + '원';
}

function goToCheckout() {
  // seat 단계 데이터 추가
  const seatStageData = {
    exit_time: new Date().toISOString(),
    duration_ms: Date.now() - pageStartTime,
    selected_seats: selectedSeats,
    section: selectedSection,
    grade: selectedGrade,
    clicks: clicks,
    hovers: hovers,
    seat_taken_events: [],  // 이선좌 이벤트 (필요 시 추가)
    mouse_trajectory: mouseTrajectory
  };

  LogCollector.addStageToFlow('seat', seatStageData);

  // 다음 페이지로 이동
  const seatsParam = selectedSeats.join(',');
  window.location.href = `/step2/${perfId}?date=${selectedDate}&time=${selectedTime}&seats=${seatsParam}`;
}

async function saveSessionLog() {
  const sessionData = {
    session_id: sessionId,
    page: 'seat_selection',
    mode: mode,
    selected_seats: selectedSeats,
    page_entry_time: new Date(pageStartTime).toISOString(),
    page_exit_time: new Date().toISOString(),
    total_duration_ms: Date.now() - pageStartTime,
    mouse_trajectory: mouseTrajectory,
    clicks: clicks,
    hovers: hovers
  };

  // Legacy session log 제거 - Flow 기반 로그만 사용
  // await LogCollector.sendSessionLog(sessionData);
}

async function logAction(action, targetId, x = 0, y = 0, timeDelta = 0, extra = {}) {
  await fetch('/api/log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      action: action,
      target_id: targetId,
      x: x,
      y: y,
      time_delta: timeDelta,
      extra: extra
    })
  });
}

let hoverStart = {};
function logHover(seatId, isEnter) {
  if (isEnter) {
    hoverStart[seatId] = Date.now();
  } else if (hoverStart[seatId]) {
    const duration = Date.now() - hoverStart[seatId];
    hovers.push({ target: seatId, duration: duration, timestamp: Date.now() - pageStartTime });
    delete hoverStart[seatId];
  }
}

document.addEventListener('mousemove', (e) => {
  const now = Date.now();
  if (!window.lastTrajectoryTime || now - window.lastTrajectoryTime >= 50) {
    mouseTrajectory.push({
      x: e.clientX,
      y: e.clientY,
      nx: e.clientX / window.innerWidth,
      ny: e.clientY / window.innerHeight,
      timestamp: now - pageStartTime
    });
    window.lastTrajectoryTime = now;
  }
});

let timeLeft = 600;
function updateTimer() {
  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;
  document.getElementById('timer').textContent =
    `${minutes}:${seconds.toString().padStart(2, '0')}`;

  if (timeLeft > 0) {
    timeLeft--;
    setTimeout(updateTimer, 1000);
  } else {
    alert('예매 시간이 초과되었습니다.');
    location.href = '/performances';
  }
}

function autoReserve() {
  fetch('/api/auto-reserve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `perf_id=${perfId}`
  }).then(res => res.json()).then(data => {
    if (data.success && data.seat_id && seats[data.seat_id]) {
      if (!selectedSeats.includes(data.seat_id)) {
        seats[data.seat_id].status = 'sold';
        seats[data.seat_id].element.classList.add('sold');
      }
    }
  });
}

// DOM 로드 후 초기화
document.addEventListener('DOMContentLoaded', function () {
  initSeats();
  updateTimer();
  setInterval(autoReserve, 10000);
  logAction('page_enter', 'seat_selection_page');

  // 이탈 감지
  window.addEventListener('beforeunload', function () {
    const flowLog = LogCollector.completeFlow('failed_abandoned', null, null);
    if (flowLog) {
      navigator.sendBeacon('/api/flow-log', JSON.stringify(flowLog));
    }
  });
});
