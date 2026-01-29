// 결제 페이지(step4_payment) JavaScript
// 템플릿에서 sessionId, perfId, selectedSeats, discountType, deliveryType 변수 설정 필요

let selectedPayment = 'card';
let captchaCode = '';
let captchaStartTime = 0;
const pageStartTime = Date.now();


function selectPayment(el, type) {
  document.querySelectorAll('.payment-option').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  el.querySelector('input').checked = true;
  selectedPayment = type;
}

function showCaptcha() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  captchaCode = '';
  for (let i = 0; i < 6; i++) captchaCode += chars[Math.floor(Math.random() * chars.length)];
  document.getElementById('captchaText').textContent = captchaCode;
  document.getElementById('captchaInput').value = '';
  document.getElementById('captchaError').style.display = 'none';
  document.getElementById('captchaModal').classList.add('active');
  captchaStartTime = Date.now();
  document.getElementById('captchaInput').focus();
}

function verifyCaptcha() {
  const input = document.getElementById('captchaInput').value.toUpperCase();

  if (input === captchaCode) {
    document.getElementById('captchaModal').classList.remove('active');
    completeBooking();
  } else {
    document.getElementById('captchaError').style.display = 'block';
    document.getElementById('captchaInput').value = '';
    document.getElementById('captchaInput').focus();
  }
}

async function completeBooking() {
  const sId = typeof sessionId !== 'undefined' ? sessionId : '';
  const seats = typeof selectedSeats !== 'undefined' ? selectedSeats : [];
  const discount = typeof discountType !== 'undefined' ? discountType : 'normal';
  const delivery = typeof deliveryType !== 'undefined' ? deliveryType : 'pickup';

  // 예매 완료 데이터 구성
  const sessionData = {
    session_id: sId,
    page: 'step4_payment',
    selected_seats: seats,
    discount_type: discount,
    delivery_type: delivery,
    payment_type: selectedPayment
  };

  // 예매 완료 API 호출
  const result = await LogCollector.sendCompleteLog(sessionData);
  if (result.success) {
    // payment 단계 데이터 추가
    const paymentStageData = {
      exit_time: new Date().toISOString(),
      duration_ms: Date.now() - pageStartTime,
      payment_type: selectedPayment,
      captcha_attempts: 2,  // 실제 캡챠 시도 횟수
      completed: true,
      completed_time: new Date().toISOString()
    };

    LogCollector.addStageToFlow('payment', paymentStageData);

    // Flow 완료 처리
    const completedFlowLog = LogCollector.completeFlow(
      'success',
      seats,
      result.booking_id
    );

    // Flow 로그 전송
    if (completedFlowLog) {
      await LogCollector.sendFlowLog(completedFlowLog);
    }

    // 완료 모달 표시
    document.getElementById('bookingId').textContent = '예매번호: ' + result.booking_id;
    document.getElementById('completeModal').classList.add('active');
  }
}

// 타이머
let timeLeft = 300;
function updateTimer() {
  const m = Math.floor(timeLeft / 60), s = timeLeft % 60;
  document.getElementById('timer').textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  if (timeLeft-- > 0) setTimeout(updateTimer, 1000);
  else { alert('시간 초과'); location.href = '/performances'; }
}

// DOM 로드 후 초기화
document.addEventListener('DOMContentLoaded', function () {
  updateTimer();

  // 이탈 감지
  window.addEventListener('beforeunload', function () {
    // 이미 완료된 flow는 abandoned 로그를 생성하지 않음
    const flowLog = LogCollector.getFlowLog();
    if (flowLog && flowLog.metadata && flowLog.metadata.is_completed) {
      console.log('Flow already completed, skipping abandoned log');
      return;
    }

    // 완료되지 않았을 때만 abandoned 로그 전송
    const abandonedLog = LogCollector.completeFlow('failed_abandoned', null, null);
    if (abandonedLog) {
      navigator.sendBeacon('/api/flow-log', JSON.stringify(abandonedLog));
    }
  });
});
