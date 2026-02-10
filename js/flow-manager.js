// 예매 플로우 관리 모듈

/**
 * 플로우 데이터 초기화
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
 * 플로우 데이터 가져오기
 */
function getFlowData() {
    const data = sessionStorage.getItem('bookingFlow');
    return data ? JSON.parse(data) : null;
}

/**
 * 플로우 데이터 업데이트
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
 * 플로우 데이터 삭제
 */
function clearFlowData() {
    console.log('🧹 [Flow] 모든 예매 데이터 및 가상 타이머를 초기화합니다.');

    // 1. 기본 플로우 데이터 제거
    sessionStorage.removeItem('bookingFlow');
    sessionStorage.removeItem('captchaVerified');
    sessionStorage.removeItem('bookingLog');

    // 2. 🕒 가상 오픈 시간 데이터 일괄 제거 (vperf_ 로 시작하는 모든 항목)
    const toRemove = [];
    for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        if (key && key.indexOf('vperf_') === 0) {
            toRemove.push(key);
        }
    }
    toRemove.forEach(key => {
        console.log(`🗑️ 가상 타이머 삭제: ${key}`);
        sessionStorage.removeItem(key);
    });
}

/**
 * 예매 단계 순서 정의
 */
const BOOKING_STEPS = [
    'performance',      // 공연 선택
    'performance_detail', // 날짜/시간 선택
    'queue',            // 대기열
    'seat_select',      // 좌석 선택 (보안문자 팝업 포함)
    'discount',         // 할인
    'order_info',       // 배송 정보
    'payment',          // 결제
    'complete'          // 완료
];

/**
 * 현재 단계 인덱스 가져오기
 */
function getCurrentStepIndex(currentPage) {
    return BOOKING_STEPS.indexOf(currentPage);
}

/**
 * 다음 단계로 이동
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
 * 플로우 검증
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
 * 좌석 선택 정보 클리어 (뒤로가기 시 보류 없음)
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
 * 총 가격 계산
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
