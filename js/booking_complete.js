// booking_complete.js - ?덈ℓ ?꾨즺 ?섏씠吏

const bookingId = getQueryParam('id');
const flowData = getFlowData();
const currentUser = getCurrentUser();

// 濡쒓렇 濡쒕뱶 諛??④퀎 ?쒖옉
loadLogState();
recordStageEntry('complete');

if (!bookingId || !flowData) {
    showAlert('?덈ℓ ?뺣낫瑜?李얠쓣 ???놁뒿?덈떎.', 'error');
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

    // 濡쒓렇 ?④퀎 醫낅즺
    recordStageExit('complete', {
        booking_id: bookingId,
        total_price: totalPrice + deliveryFee,
        completion_time: getCollectTimestamp()
    });

    // 결제 완료 시 즉시 세션 정리 (로그인 정보는 유지)
    clearFlowData({ keepUser: true, keepBotType: true });

    // 최종 로그 전송 (메모리 내 logData 기준)
    uploadLog(true, bookingId).then(result => {
        console.log('로그 전송 완료:', result);
    }).catch(error => {
        console.error('로그 전송 실패:', error);
    });
}

