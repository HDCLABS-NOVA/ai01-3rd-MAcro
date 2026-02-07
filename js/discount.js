// discount.js - 할인 선택 페이지

loadLogState();
recordStageEntry('discount');

const flowData = getFlowData();
if (!flowData || !flowData.selectedSeats || flowData.selectedSeats.length === 0) {
    navigateTo('seat_select.html');
}

let selectedType = 'normal';
let selectedRate = 0;
const basePrice = flowData.seatPrice || 0;

// 가격 표시
function updatePrices() {
    const types = ['normal', 'student', 'disabled', 'senior'];
    const rates = [0, 10, 30, 20];

    types.forEach((type, idx) => {
        const discountedPrice = basePrice * (1 - rates[idx] / 100);
        document.getElementById(`price-${type}`).textContent = formatPrice(Math.floor(discountedPrice));
    });

    updateSummary();
}

function selectDiscount(type, rate, element) {
    document.querySelectorAll('.discount-option').forEach(opt => opt.classList.remove('selected'));
    element.classList.add('selected');

    selectedType = type;
    selectedRate = rate;

    updateFlowData({
        discountType: type,
        discountRate: rate
    });

    updateSummary();
}

function updateSummary() {
    const discountAmount = basePrice * (selectedRate / 100);
    const finalPrice = basePrice - discountAmount;

    document.getElementById('original-price').textContent = formatPrice(basePrice);
    document.getElementById('discount-amount').textContent = selectedRate > 0 ? '-' + formatPrice(Math.floor(discountAmount)) : '없음';
    document.getElementById('final-price').textContent = formatPrice(Math.floor(finalPrice));

    calculateTotalPrice();
}

function confirmDiscount() {
    recordStageExit('discount', {
        selected_discount: selectedType
    });

    navigateTo('order_info.html');
}

updatePrices();
