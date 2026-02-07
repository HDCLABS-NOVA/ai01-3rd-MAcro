// booking_complete.js - 예매 완료 페이지

const bookingId = getQueryParam('id');
const flowData = getFlowData();
const currentUser = getCurrentUser();

// 로그 로드 및 단계 시작
loadLogState();
recordStageEntry('complete');

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

    // 로그 단계 종료
    recordStageExit('complete', {
        booking_id: bookingId,
        total_price: totalPrice + deliveryFee,
        completion_time: getCollectTimestamp()
    });

    // 🔥 핵심: 최종 로그 전송 (성공)
    uploadLog(true, bookingId).then(result => {
        console.log('✅ 로그 전송 완료:', result);
    }).catch(error => {
        console.error('❌ 로그 전송 실패:', error);
    });

    // 예매 완료 후 플로우 데이터 정리
    setTimeout(() => {
        clearFlowData();
        // sessionStorage.removeItem('bookingLog'); // logger.js에서 전송 성공 시 이미 삭제함
    }, 5000);
}
