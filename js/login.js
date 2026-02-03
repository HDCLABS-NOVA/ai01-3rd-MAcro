// login.js - 로그인 페이지

// 디버그 정보 표시
document.addEventListener('DOMContentLoaded', () => {
    const currentUrlSpan = document.getElementById('current-url');
    const returnParamSpan = document.getElementById('return-param');

    if (currentUrlSpan) {
        currentUrlSpan.textContent = window.location.href;
    }
    if (returnParamSpan) {
        const returnUrl = getQueryParam('return');
        returnParamSpan.textContent = returnUrl || '(없음 - index.html로 이동)';
    }
});

const form = document.getElementById('login-form');

form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    try {
        const result = await login(email, password);
        showAlert(result.message, 'success');

        setTimeout(() => {
            // 이전 페이지로 돌아가기 (또는 메인 페이지)
            const returnUrl = getQueryParam('return') || 'index.html';
            console.log('Return URL:', returnUrl);
            console.log('Current search:', window.location.search);
            navigateTo(returnUrl);
        }, 1000);
    } catch (error) {
        showAlert(error.message, 'error');
    }
});
