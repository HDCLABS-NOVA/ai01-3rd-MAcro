// 캡챠(보안문자) 페이지 JavaScript
// 템플릿에서 perfId, selectedDate, selectedTime 변수를 전역으로 설정해야 함

const pageStartTime = Date.now();
let captchaCode = '';
let captchaStartTime = 0;
let attemptCount = 0;

function generateCaptcha() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
  captchaCode = '';
  for (let i = 0; i < 6; i++) {
    captchaCode += chars[Math.floor(Math.random() * chars.length)];
  }
  document.getElementById('captchaText').textContent = captchaCode;
  captchaStartTime = Date.now();
}

function refreshCaptcha() {
  generateCaptcha();
  document.getElementById('captchaInput').value = '';
  document.getElementById('errorMsg').classList.remove('show');
}

function verifyCaptcha() {
  const input = document.getElementById('captchaInput').value.toUpperCase();
  attemptCount++;

  const pId = typeof perfId !== 'undefined' ? perfId : '';
  const sDate = typeof selectedDate !== 'undefined' ? selectedDate : '';
  const sTime = typeof selectedTime !== 'undefined' ? selectedTime : '';

  if (input === captchaCode) {
    // captcha 단계 데이터 추가
    const captchaStageData = {
      exit_time: new Date().toISOString(),
      duration_ms: Date.now() - pageStartTime,
      attempts: attemptCount,
      time_to_solve_ms: Date.now() - captchaStartTime
    };

    LogCollector.addStageToFlow('captcha', captchaStageData);

    // 성공 - 구역 선택 페이지로 이동
    window.location.href = `/section/${pId}?date=${sDate}&time=${sTime}`;
  } else {
    // 실패
    document.getElementById('errorMsg').classList.add('show');
    document.getElementById('captchaInput').value = '';
    document.getElementById('captchaInput').focus();

    // 3회 실패 시 새 캡챠
    if (attemptCount >= 3) {
      attemptCount = 0;
      setTimeout(refreshCaptcha, 1000);
    }
  }
}

// 타이머
let timeLeft = 180;
function updateTimer() {
  const m = Math.floor(timeLeft / 60);
  const s = timeLeft % 60;
  document.getElementById('timer').textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;

  if (timeLeft > 0) {
    timeLeft--;
    setTimeout(updateTimer, 1000);
  } else {
    alert('시간이 초과되었습니다. 다시 시도해주세요.');
    location.href = '/performances';
  }
}

// DOM 로드 후 초기화
document.addEventListener('DOMContentLoaded', function () {
  generateCaptcha();
  updateTimer();
  document.getElementById('captchaInput').focus();

  // 엔터키 처리
  document.getElementById('captchaInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') verifyCaptcha();
  });

  // 이탈 감지
  window.addEventListener('beforeunload', function () {
    const flowLog = LogCollector.completeFlow('failed_abandoned', null, null);
    if (flowLog) {
      navigator.sendBeacon('/api/flow-log', JSON.stringify(flowLog));
    }
  });
});
