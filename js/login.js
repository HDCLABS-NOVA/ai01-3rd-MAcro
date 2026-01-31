// login.js - 로그인 페이지

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
            navigateTo(returnUrl);
        }, 1000);
    } catch (error) {
        showAlert(error.message, 'error');
    }
});
