// 유틸리티 함수 모음

/**
 * UUID 생성
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * 랜덤 ID 생성
 */
function generateRandomId(prefix = '', length = 8) {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return prefix + result;
}

/**
 * 날짜 포맷팅 (YYYY-MM-DD)
 */
function formatDate(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * ISO 형식 시간 생성
 */
function getISOTimestamp() {
    return new Date().toISOString();
}

/**
 * 날짜 한글 포맷팅 (YYYY년 MM월 DD일)
 */
function formatDateKorean(dateStr) {
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    return `${year}년 ${month}월 ${day}일`;
}

/**
 * 요일 가져오기
 */
function getDayOfWeek(dateStr) {
    const days = ['일', '월', '화', '수', '목', '금', '토'];
    const date = new Date(dateStr);
    return days[date.getDay()];
}

/**
 * 가격 포맷팅
 */
function formatPrice(price) {
    return price.toLocaleString('ko-KR') + '원';
}

/**
 * 예매번호 생성 (m + 8자리 숫자)
 */
function generateBookingNumber() {
    const num = Math.floor(10000000 + Math.random() * 90000000);
    return 'M' + num;
}

/**
 * 사용자 IP 주소 가져오기 (외부 API 사용)
 */
async function getUserIP() {
    try {
        const response = await fetch('https://api.ipify.org?format=json');
        const data = await response.json();
        return data.ip;
    } catch (error) {
        console.error('IP 조회 실패:', error);
        return '0.0.0.0';
    }
}

/**
 * Query String에서 파라미터 가져오기
 */
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

/**
 * 페이지 이동
 */
function navigateTo(url) {
    window.location.href = url;
}

/**
 * 로딩 표시
 */
function showLoading() {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'global-loading';
    loadingDiv.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
  `;
    loadingDiv.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loadingDiv);
}

/**
 * 로딩 숨기기
 */
function hideLoading() {
    const loadingDiv = document.getElementById('global-loading');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

/**
 * 알림 표시
 */
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    alertDiv.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    max-width: 400px;
    animation: slideIn 0.3s ease-out;
  `;

    document.body.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => alertDiv.remove(), 300);
    }, 3000);
}

/**
 * 뒤로가기 방지
 */
function preventBackNavigation() {
    history.pushState(null, null, location.href);
    window.onpopstate = function () {
        history.go(1);
        showAlert('이전 단계로 돌아갈 수 없습니다.', 'warning');
    };
}

/**
 * Sleep 함수
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
