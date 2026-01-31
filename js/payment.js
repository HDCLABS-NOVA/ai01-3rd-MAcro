// payment.js - 결제 페이지

loadLogFromSession();
logStageEntry('payment');

const flowData = getFlowData();
if (!flowData) {
    navigateTo('index.html');
}

const totalPrice = calculateTotalPrice();
const deliveryFee = flowData.deliveryType === 'delivery' ? 3000 : 0;
const finalPrice = totalPrice + deliveryFee;

document.getElementById('ticket-price').textContent = formatPrice(totalPrice);
document.getElementById('total-price').textContent = formatPrice(finalPrice);

if (deliveryFee > 0) {
    document.getElementById('delivery-fee-row').style.display = 'flex';
}

let selectedPaymentType = 'card';

function selectPayment(type, element) {
    document.querySelectorAll('.payment-method').forEach(opt => opt.classList.remove('selected'));
    element.classList.add('selected');
    selectedPaymentType = type;
}

async function processPayment() {
    showLoading();

    // 시뮬레이션: 결제 처리
    await sleep(2000);

    const bookingId = generateBookingNumber();

    logStageExit('payment', {
        payment_type: selectedPaymentType,
        completed: true,
        completed_time: getISOTimestamp()
    });

    // 최종 로그 완료
    await finalizeLog(true, bookingId);

    hideLoading();

    navigateTo(`booking_complete.html?id=${bookingId}`);
}
