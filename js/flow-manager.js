// ?덈ℓ ?뚮줈??愿由?紐⑤뱢

/**
 * ?뚮줈???곗씠??珥덇린??
 */
function initFlow(performanceData) {
    const flowData = {
        performanceId: performanceData.id,
        performanceTitle: performanceData.title,
        venue: performanceData.venue,
        selectedDate: '',
        selectedTime: '',
        selectedSection: '',
        selectedGrade: '',
        selectedSeats: [],
        seatPrice: 0,
        discountType: 'normal',
        discountRate: 0,
        deliveryType: '',
        totalPrice: 0,
        startTime: getISOTimestamp()
    };

    sessionStorage.setItem('bookingFlow', JSON.stringify(flowData));
    return flowData;
}

/**
 * ?뚮줈???곗씠??媛?몄삤湲?
 */
function getFlowData() {
    const data = sessionStorage.getItem('bookingFlow');
    return data ? JSON.parse(data) : null;
}

/**
 * ?뚮줈???곗씠???낅뜲?댄듃
 */
function updateFlowData(updates) {
    const flowData = getFlowData();
    if (flowData) {
        Object.assign(flowData, updates);
        sessionStorage.setItem('bookingFlow', JSON.stringify(flowData));
    }
    return flowData;
}

/**
 * ?뚮줈???곗씠????젣
 */
function clearFlowData(options = {}) {
    const keepUser = options.keepUser !== false;
    const keepBotType = options.keepBotType !== false;

    const preserved = {};
    if (keepUser) preserved.currentUser = sessionStorage.getItem('currentUser');
    if (keepBotType) preserved.bot_type = sessionStorage.getItem('bot_type');

    // 결제 완료 후 재진입 시 카운트다운/토큰 상태가 남지 않도록 전체 세션 정리
    sessionStorage.clear();

    if (preserved.currentUser) sessionStorage.setItem('currentUser', preserved.currentUser);
    if (preserved.bot_type) sessionStorage.setItem('bot_type', preserved.bot_type);
}

/**
 * ?덈ℓ ?④퀎 ?쒖꽌 ?뺤쓽
 */
const BOOKING_STEPS = [
    'performance',      // 怨듭뿰 ?좏깮
    'performance_detail', // ?좎쭨/?쒓컙 ?좏깮
    'queue',            // ?湲곗뿴
    'seat_select',      // 醫뚯꽍 ?좏깮 (蹂댁븞臾몄옄 ?앹뾽 ?ы븿)
    'discount',         // ?좎씤
    'order_info',       // 諛곗넚 ?뺣낫
    'payment',          // 寃곗젣
    'complete'          // ?꾨즺
];

/**
 * ?꾩옱 ?④퀎 ?몃뜳??媛?몄삤湲?
 */
function getCurrentStepIndex(currentPage) {
    return BOOKING_STEPS.indexOf(currentPage);
}

/**
 * ?ㅼ쓬 ?④퀎濡??대룞
 */
function goToNextStep(currentPage) {
    const currentIndex = getCurrentStepIndex(currentPage);
    if (currentIndex >= 0 && currentIndex < BOOKING_STEPS.length - 1) {
        const nextStep = BOOKING_STEPS[currentIndex + 1];
        const pageMap = {
            'performance': 'index.html',
            'performance_detail': 'performance_detail.html',
            'queue': 'queue.html',
            'seat_select': 'seat_select.html',
            'discount': 'discount.html',
            'order_info': 'order_info.html',
            'payment': 'payment.html',
            'complete': 'booking_complete.html'
        };

        navigateTo(pageMap[nextStep]);
    }
}

/**
 * ?뚮줈??寃利?
 */
function validateFlow(requiredFields) {
    const flowData = getFlowData();
    if (!flowData) return false;

    for (const field of requiredFields) {
        if (!flowData[field]) {
            return false;
        }
    }

    return true;
}

/**
 * 醫뚯꽍 ?좏깮 ?뺣낫 ?대━??(?ㅻ줈媛湲???蹂대쪟 ?놁쓬)
 */
function clearSeatSelections() {
    const flowData = getFlowData();
    if (flowData) {
        flowData.selectedSection = '';
        flowData.selectedGrade = '';
        flowData.selectedSeats = [];
        flowData.seatPrice = 0;
        sessionStorage.setItem('bookingFlow', JSON.stringify(flowData));
    }
}

/**
 * 珥?媛寃?怨꾩궛
 */
function calculateTotalPrice() {
    const flowData = getFlowData();
    if (!flowData) return 0;

    const basePrice = flowData.seatPrice * flowData.selectedSeats.length;
    const discount = basePrice * (flowData.discountRate / 100);
    const totalPrice = basePrice - discount;

    updateFlowData({ totalPrice });

    return totalPrice;
}

