// order_info.js - 예매 정보 입력 페이지

loadLogState();
recordStageEntry('order_info');

const flowData = getFlowData();
const currentUser = getCurrentUser();

if (!flowData) {
    navigateTo('index.html');
}

// 예매자 정보 자동 입력 (회원 정보에서 가져오기)
document.getElementById('booker-name').value = currentUser.name;
document.getElementById('booker-phone').value = currentUser.phone || '';
document.getElementById('booker-email').value = currentUser.email || '';

// 핸드폰 번호 자동 포맷팅 (하이픈 자동 삽입) - 사용자가 하이픈 제거 입력을 원하므로 비활성화
/*
const phoneInput = document.getElementById('booker-phone');
phoneInput.addEventListener('input', function (e) {
    let value = e.target.value.replace(/[^0-9]/g, ''); // 숫자만 추출

    if (value.length <= 3) {
        e.target.value = value;
    } else if (value.length <= 7) {
        e.target.value = value.slice(0, 3) + '-' + value.slice(3);
    } else if (value.length <= 11) {
        e.target.value = value.slice(0, 3) + '-' + value.slice(3, 7) + '-' + value.slice(7);
    } else {
        // 11자리 초과 시 자르기
        e.target.value = value.slice(0, 3) + '-' + value.slice(3, 7) + '-' + value.slice(7, 11);
    }
});
*/

let selectedDelivery = 'pickup';

function selectDelivery(type, element) {
    document.querySelectorAll('.payment-method').forEach(opt => opt.classList.remove('selected'));
    element.classList.add('selected');

    selectedDelivery = type;

    if (type === 'delivery') {
        document.getElementById('delivery-address').style.display = 'block';
    } else {
        document.getElementById('delivery-address').style.display = 'none';
    }

    updateFlowData({ deliveryType: type });
}

function confirmOrderInfo() {
    // 핸드폰 번호 자동 보정 및 검증
    const phoneRaw = document.getElementById('booker-phone').value.trim();
    if (!phoneRaw) {
        showAlert('휴대폰 번호를 입력해주세요.', 'warning');
        return;
    }

    // 허용된 형식만 체크 (하이픈 포함 또는 숫자만)
    const phoneWithHyphen = /^010-\d{4}-\d{4}$/;  // 010-1234-5678
    const phoneDigitsOnly = /^010\d{8}$/;         // 01012345678

    let phone;
    if (phoneWithHyphen.test(phoneRaw)) {
        // 하이픈 포함 형식 → 그대로 사용
        phone = phoneRaw;
    } else if (phoneDigitsOnly.test(phoneRaw)) {
        // 숫자만 → 하이픈 추가
        phone = phoneRaw.slice(0, 3) + '-' + phoneRaw.slice(3, 7) + '-' + phoneRaw.slice(7);
    } else {
        // 허용되지 않는 형식
        showAlert('올바른 형식으로 입력해주세요.\\n예) 010-1234-5678 또는 01012345678', 'warning');
        return;
    }

    // 이메일 검증
    const email = document.getElementById('booker-email').value.trim();
    if (!email) {
        showAlert('이메일을 입력해주세요.', 'warning');
        return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showAlert('올바른 이메일 형식이 아닙니다.', 'warning');
        return;
    }

    // 배송 주소 검증
    if (selectedDelivery === 'delivery') {
        const zipcode = document.getElementById('zipcode').value;
        const address = document.getElementById('address').value;
        const addressDetail = document.getElementById('address-detail').value;

        if (!zipcode || !address || !addressDetail) {
            showAlert('배송 주소를 입력해주세요.', 'warning');
            return;
        }

        updateFlowData({
            deliveryAddress: {
                zipcode,
                address,
                addressDetail
            }
        });
    }

    // 예매자 연락처 정보 저장
    updateFlowData({
        bookerPhone: phone,
        bookerEmail: email
    });

    // 메타데이터에도 추가
    updateMetadata({
        booker_phone: phone,
        booker_email: email
    });

    recordStageExit('order_info', {
        delivery_type: selectedDelivery,
        has_phone: true,
        has_email: true
    });

    navigateTo('payment.html');
}
