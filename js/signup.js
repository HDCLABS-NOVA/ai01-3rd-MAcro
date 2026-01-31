// signup.js - 회원가입 페이지

const form = document.getElementById('signup-form');

form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const password = document.getElementById('password').value;
    const passwordConfirm = document.getElementById('password-confirm').value;

    if (password !== passwordConfirm) {
        showAlert('비밀번호가 일치하지 않습니다.', 'error');
        return;
    }

    const userData = {
        name: document.getElementById('name').value,
        birthdate: document.getElementById('birthdate').value,
        phone: document.getElementById('phone').value,
        email: document.getElementById('email').value,
        password: password
    };

    try {
        const result = await signup(userData);
        showAlert(result.message, 'success');

        setTimeout(() => {
            navigateTo('login.html');
        }, 1500);
    } catch (error) {
        showAlert(error.message, 'error');
    }
});
