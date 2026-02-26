// performance_detail.js - 공연 상세 페이지

let currentPerformance = null;

async function loadPerformance() {
  const perfId = getQueryParam('id');
  if (!perfId) {
    navigateTo('index.html');
    return;
  }

  try {
    const response = await fetch('data/performances.json');
    const data = await response.json();
    currentPerformance = data.performances.find(p => p.id === perfId);

    if (!currentPerformance) {
      throw new Error('공연을 찾을 수 없습니다.');
    }

    displayPerformance();

    // 로그 초기화
    await initLogger(currentPerformance.id, currentPerformance.title);
    logStageEntry('perf');
    enableMouseTracking();
  } catch (error) {
    console.error(error);
    showAlert('공연 정보를 불러오는데 실패했습니다.', 'error');
    setTimeout(() => navigateTo('index.html'), 2000);
  }
}

function displayPerformance() {
  const detailDiv = document.getElementById('perf-detail');

  // ✅ 추가: 오픈 시간 체크
  const openTime = currentPerformance.open_time ? new Date(currentPerformance.open_time) : null;
  const now = new Date();
  const isOpen = !openTime || openTime <= now;

  // 오픈 시간 안내 메시지
  const openTimeAlert = !isOpen ? `
        <div class="alert alert-warning" style="margin-bottom: var(--spacing-lg);">
            <h3 style="margin-bottom: var(--spacing-sm); display: flex; align-items: center; gap: 8px;">
                🔒 티켓 오픈 예정
            </h3>
            <p style="margin-bottom: var(--spacing-sm);">
                <strong>오픈 시간:</strong> ${formatOpenTimeDisplay(openTime)}
            </p>
            <div class="countdown-timer-detail" id="countdown-detail" data-open-time="${openTime.toISOString()}"></div>
            <p style="margin-top: var(--spacing-sm); font-size: 14px; opacity: 0.9;">
                오픈 시간 이후에 날짜와 시간을 선택할 수 있습니다.
            </p>
        </div>
    ` : '';

  detailDiv.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1.5fr; gap: var(--spacing-xl); margin-bottom: var(--spacing-xl);">
          <div class="card">
            <div style="width: 100%; height: 400px; background: #667eea; border-radius: var(--border-radius); display: flex; align-items: center; justify-content: center; font-size: 80px;">
              ${getCategoryIcon(currentPerformance.category)}
            </div>
          </div>
          
          <div>
            <h1 class="page-title">${currentPerformance.title}</h1>
            <p class="page-subtitle">${currentPerformance.description}</p>
            
            ${openTimeAlert}
            
            <div class="card mt-lg">
              <div style="margin-bottom: var(--spacing-md);">
                <strong>📍 장소:</strong> ${currentPerformance.venue}
              </div>
              <div style="margin-bottom: var(--spacing-md);">
                <strong>🎭 카테고리:</strong> ${getCategoryName(currentPerformance.category)}
              </div>
              <div>
                <strong>💰 가격:</strong> ${formatPrice(currentPerformance.grades[currentPerformance.grades.length - 1].price)} ~ ${formatPrice(currentPerformance.grades[0].price)}
              </div>
            </div>


            <div class="card mt-lg">
              <h3 style="margin-bottom: var(--spacing-md);">날짜 선택</h3>
              <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: var(--spacing-sm);" id="date-selection">
                ${currentPerformance.dates.map(date => `
                  <button class="btn btn-outline date-btn" data-date="${date}" ${!isOpen ? 'disabled' : ''}>
                    ${formatDateKorean(date)}<br>
                    <small>(${getDayOfWeek(date)})</small>
                  </button>
                `).join('')}
              </div>
            </div>


            <div class="card mt-lg" id="time-selection-section" style="display: none;">
              <h3 style="margin-bottom: var(--spacing-md);">시간 선택</h3>
              <div style="display: flex; gap: var(--spacing-sm); flex-wrap: wrap;" id="time-selection">
                ${currentPerformance.times.map(time => `
                  <button class="btn btn-outline time-btn" data-time="${time}" ${!isOpen ? 'disabled' : ''}>
                    ${time}
                  </button>
                `).join('')}
              </div>
            </div>

            ${getBookingButton(isOpen, openTime)}
          </div>
        </div>
      `;

  // ✅ 추가: 오픈 후에만 이벤트 리스너 추가
  if (isOpen) {
    attachEventListeners();
  }

  // ✅ 추가: 오픈 전이면 카운트다운 시작
  if (!isOpen) {
    startDetailCountdown();
  }
}

// ✅ 추가: 예매 버튼 생성 함수
function getBookingButton(isOpen, openTime) {
  if (!isOpen && openTime) {
    // 오픈 전: 항상 표시하되 비활성화 + 오픈 시간 표시 + onclick 없음
    const year = openTime.getFullYear();
    const month = openTime.getMonth() + 1;
    const day = openTime.getDate();
    const hours = openTime.getHours();
    const minutes = String(openTime.getMinutes()).padStart(2, '0');
    const ampm = hours >= 12 ? '오후' : '오전';
    const displayHours = hours > 12 ? hours - 12 : (hours === 0 ? 12 : hours);

    return `
      <button id="start-booking-btn" class="btn btn-primary btn-lg btn-block mt-xl" disabled style="cursor: not-allowed; opacity: 0.7;">
        🔒 티켓 오픈: ${year}.${month}.${day} ${ampm} ${displayHours}:${minutes}
      </button>
    `;
  } else {
    // 오픈 후: 날짜/시간 선택 후 표시 + onclick 없음 (이벤트 리스너 사용)
    return `
      <button id="start-booking-btn" class="btn btn-primary btn-lg btn-block mt-xl" style="display: none;">
        예매 시작
      </button>
    `;
  }
}

// ✅ 추가: 이벤트 리스너 등록 함수 (오픈 후에만 호출)
function attachEventListeners() {
  // 날짜 버튼 이벤트 리스너
  document.querySelectorAll('.date-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      const date = this.dataset.date;
      selectDate(date);
    });
  });

  // 시간 버튼 이벤트 리스너
  document.querySelectorAll('.time-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      const time = this.dataset.time;
      selectTime(time);
    });
  });

  // 예매 시작 버튼 이벤트 리스너
  const bookingBtn = document.getElementById('start-booking-btn');
  if (bookingBtn) {
    bookingBtn.addEventListener('click', startBooking);
  }
}


let selectedDate = '';
let selectedTime = '';


function selectDate(date) {
  // ✅ 추가: 오픈 시간 체크
  if (!isCurrentlyOpen()) {
    showAlert('티켓 오픈 시간 이후에 선택 가능합니다.', 'warning');
    return;
  }

  selectedDate = date;

  // 날짜 버튼 스타일 업데이트
  document.querySelectorAll('.date-btn').forEach(btn => {
    btn.classList.remove('btn-primary');
    btn.classList.add('btn-outline');
  });
  event.target.classList.remove('btn-outline');
  event.target.classList.add('btn-primary');

  // 시간 선택 섹션 표시
  document.getElementById('time-selection-section').style.display = 'block';

  // 로그 기록
  trackClick(event, { action: 'date_select', target: date });
}

function selectTime(time) {
  // ✅ 추가: 오픈 시간 체크
  if (!isCurrentlyOpen()) {
    showAlert('티켓 오픈 시간 이후에 선택 가능합니다.', 'warning');
    return;
  }

  selectedTime = time;

  // 시간 버튼 스타일 업데이트
  document.querySelectorAll('.time-btn').forEach(btn => {
    btn.classList.remove('btn-primary');
    btn.classList.add('btn-outline');
  });
  event.target.classList.remove('btn-outline');
  event.target.classList.add('btn-primary');

  // 예매 시작 버튼 표시
  document.getElementById('start-booking-btn').style.display = 'block';

  // 로그 기록
  trackClick(event, { action: 'time_select', target: time });
}

function startBooking() {
  if (!requireLogin()) return;

  // ✅ 추가: 오픈 시간 체크
  if (!isCurrentlyOpen()) {
    showAlert('티켓 오픈 시간 이후에 예매 가능합니다.', 'warning');
    return;
  }

  if (!selectedDate || !selectedTime) {
    showAlert('날짜와 시간을 선택해주세요.', 'warning');
    return;
  }

  // 플로우  데이터 초기화
  initFlow(currentPerformance);
  updateFlowData({
    selectedDate: selectedDate,
    selectedTime: selectedTime
  });

  // 메타데이터 업데이트
  updateMetadata({
    selected_date: selectedDate,
    selected_time: selectedTime
  });

  // 로그 단계 종료
  logStageExit('perf', {
    card_clicks: [{
      performance_id: currentPerformance.id,
      performance_title: currentPerformance.title,
      timestamp: getISOTimestamp()
    }],
    date_selections: [{ date: selectedDate, timestamp: getISOTimestamp() }],
    time_selections: [{ time: selectedTime, timestamp: getISOTimestamp() }],
    actions: [
      { action: 'card_click', target: currentPerformance.id, timestamp: getISOTimestamp() },
      { action: 'date_select', target: selectedDate, timestamp: getISOTimestamp() },
      { action: 'time_select', target: selectedTime, timestamp: getISOTimestamp() },
      { action: 'booking_start', target: currentPerformance.id, date: selectedDate, time: selectedTime, timestamp: getISOTimestamp() }
    ]
  });

  disableMouseTracking();
  navigateTo('queue.html');
}

function getCategoryIcon(category) {
  const icons = { concert: '🎤', musical: '🎭', sports: '⚽', exhibition: '🖼️' };
  return icons[category] || '🎫';
}

function getCategoryName(category) {
  const names = { concert: '콘서트', musical: '뮤지컬', sports: '스포츠', exhibition: '전시' };
  return names[category] || '공연';
}

// ✅ 추가: 현재 오픈 여부 체크 함수
function isCurrentlyOpen() {
  if (!currentPerformance || !currentPerformance.open_time) {
    return true; // open_time이 없으면 항상 오픈
  }

  const openTime = new Date(currentPerformance.open_time);
  const now = new Date();

  return now >= openTime;
}

// ✅ 추가: 오픈 시간 포맷 함수
function formatOpenTimeDisplay(date) {
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const ampm = hours >= 12 ? '오후' : '오전';
  const displayHours = hours > 12 ? hours - 12 : (hours === 0 ? 12 : hours);
  const dayOfWeek = getDayOfWeek(`${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`);

  return `${year}년 ${month}월 ${day}일 (${dayOfWeek}) ${ampm} ${displayHours}:${minutes}`;
}

// ✅ 추가: 상세 페이지 카운트다운 타이머
function startDetailCountdown() {
  const countdownEl = document.getElementById('countdown-detail');
  if (!countdownEl) return;

  const updateCountdown = () => {
    const openTime = new Date(countdownEl.dataset.openTime);
    const now = new Date();
    const diff = openTime - now;

    if (diff <= 0) {
      // ✅ 변경: 새로고침 대신 동적 UI 업데이트
      countdownEl.textContent = '🎉 판매 시작!';
      countdownEl.style.background = '#10b981';
      clearInterval(window.detailCountdownInterval);

      // ✅ 동적으로 페이지 활성화
      setTimeout(() => {
        activateBookingPage();
      }, 1000);
    } else {
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      let text = '⏰ 오픈까지: ';
      if (days > 0) text += `${days}일 `;
      text += `${hours}시간 ${minutes}분 ${seconds}초`;

      countdownEl.textContent = text;

      // 1시간 미만이면 색상 변경
      if (diff < 3600000) {
        countdownEl.style.background = '#ef4444';
        countdownEl.style.animation = 'pulse 2s infinite';
      }
    }
  };

  updateCountdown(); // 즉시 실행
  window.detailCountdownInterval = setInterval(updateCountdown, 1000);
}

// ✅ 추가: 오픈 시 페이지 동적 활성화 함수
function activateBookingPage() {
  // 1. 안내 메시지 제거
  const alertBox = document.querySelector('.alert-warning');
  if (alertBox) {
    alertBox.style.transition = 'opacity 0.5s';
    alertBox.style.opacity = '0';
    setTimeout(() => alertBox.remove(), 500);
  }

  // 2. 날짜 버튼 활성화
  document.querySelectorAll('.date-btn').forEach(btn => {
    btn.removeAttribute('disabled');
  });

  // 3. 시간 버튼 활성화
  document.querySelectorAll('.time-btn').forEach(btn => {
    btn.removeAttribute('disabled');
  });

  // 4. 예매 버튼 변경
  const bookingBtn = document.getElementById('start-booking-btn');
  if (bookingBtn) {
    bookingBtn.removeAttribute('disabled');
    bookingBtn.style.cursor = 'pointer';
    bookingBtn.style.opacity = '1';
    bookingBtn.textContent = '예매 시작';
    bookingBtn.style.display = 'none'; // 날짜/시간 선택 후 표시되도록
  }

  // 5. 이벤트 리스너 추가
  attachEventListeners();

  // 6. 성공 메시지 표시
  showAlert('🎉 티켓 판매가 시작되었습니다! 날짜와 시간을 선택해 주세요.', 'success');
}

loadPerformance();
