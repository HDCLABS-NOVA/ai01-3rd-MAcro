// 예매자 정보 페이지(step3_booker) JavaScript
// 템플릿에서 perfId, selectedDate, selectedTime, selectedSeats, discountType, finalPrice 변수 설정 필요

let selectedDelivery = 'pickup';
let deliveryFee = 0;
let pageStartTime = Date.now();

function selectDelivery(el, type, fee) {
  document.querySelectorAll('.delivery-option').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  el.querySelector('input').checked = true;
  selectedDelivery = type;
  deliveryFee = fee;

  const basePrice = typeof finalPrice !== 'undefined' ? finalPrice : 0;
  document.getElementById('deliveryFee').textContent = fee.toLocaleString() + '원';
  document.getElementById('totalAmount').textContent = (basePrice + fee).toLocaleString() + '원';
}

function goNext() {
  const pId = typeof perfId !== 'undefined' ? perfId : '';
  const sDate = typeof selectedDate !== 'undefined' ? selectedDate : '';
  const sTime = typeof selectedTime !== 'undefined' ? selectedTime : '';
  const seats = typeof selectedSeats !== 'undefined' ? selectedSeats : '';
  const discount = typeof discountType !== 'undefined' ? discountType : 'normal';

  // order_info 단계 데이터 추가
  const orderInfoStageData = {
    exit_time: new Date().toISOString(),
    duration_ms: Date.now() - pageStartTime,
    delivery_type: selectedDelivery
  };

  LogCollector.addStageToFlow('order_info', orderInfoStageData);

  // 다음 페이지로 이동
  window.location.href = `/step4/${pId}?date=${sDate}&time=${sTime}&seats=${seats}&discount=${discount}&delivery=${selectedDelivery}`;
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
    const flowLog = LogCollector.completeFlow('failed_abandoned', null, null);
    if (flowLog) {
      navigator.sendBeacon('/api/flow-log', JSON.stringify(flowLog));
    }
  });
});
