// booking_complete.js - 예매 완료 페이지

const bookingId = getQueryParam('id');
const flowData = getFlowData();
const currentUser = getCurrentUser();

if (!bookingId || !flowData) {
    showAlert('예매 정보를 찾을 수 없습니다.', 'error');
    setTimeout(() => navigateTo('index.html'), 2000);
} else {
    document.getElementById('booking-number').textContent = bookingId;
    document.getElementById('perf-title').textContent = flowData.performanceTitle;
    document.getElementById('perf-date').textContent = formatDateKorean(flowData.selectedDate);
    document.getElementById('perf-time').textContent = flowData.selectedTime;
    document.getElementById('perf-venue').textContent = flowData.venue;
    document.getElementById('perf-seats').textContent = flowData.selectedSeats.map(s => s.split('-')[1]).join(', ');

    const totalPrice = calculateTotalPrice();
    const deliveryFee = flowData.deliveryType === 'delivery' ? 3000 : 0;
    document.getElementById('perf-price').textContent = formatPrice(totalPrice + deliveryFee);

    document.getElementById('user-email').textContent = currentUser.email;

    // 예매 완료 후 플로우 데이터 정리
    setTimeout(() => {
        clearFlowData();
    }, 5000);
}
