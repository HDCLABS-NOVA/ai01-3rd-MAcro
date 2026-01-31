// 인증 및 사용자 관리 모듈

/**
 * 회원가입
 */
async function signup(userData) {
    // 입력 검증
    if (!userData.name || !userData.phone || !userData.email || !userData.password) {
        throw new Error('모든 필수 항목을 입력해주세요.');
    }

    // 이메일 형식 검증
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(userData.email)) {
        throw new Error('올바른 이메일 형식이 아닙니다.');
    }

    // 전화번호 형식 검증 (숫자만)
    const phoneRegex = /^[0-9]{10,11}$/;
    if (!phoneRegex.test(userData.phone.replace(/-/g, ''))) {
        throw new Error('올바른 전화번호 형식이 아닙니다.');
    }

    try {
        // 서버에 회원가입 요청
        const response = await fetch('/api/auth/signup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: userData.email,
                password: userData.password,
                name: userData.name,
                phone: userData.phone
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '회원가입에 실패했습니다.');
        }

        return {
            success: true,
            message: data.message,
            user: data.user
        };
    } catch (error) {
        throw new Error(error.message || '회원가입에 실패했습니다.');
    }
}

/**
 * 로그인
 */
async function login(email, password) {
    try {
        // 서버에 로그인 요청
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '로그인에 실패했습니다.');
        }

        // 세션 정보 저장
        const session = {
            email: data.user.email,
            name: data.user.name,
            phone: data.user.phone,
            loginTime: getISOTimestamp()
        };

        sessionStorage.setItem('currentUser', JSON.stringify(session));

        return {
            success: true,
            message: data.message,
            user: data.user
        };
    } catch (error) {
        throw new Error(error.message || '로그인에 실패했습니다.');
    }
}

/**
 * 로그아웃
 */
function logout() {
    sessionStorage.removeItem('currentUser');
    localStorage.removeItem('bookingFlow');
    navigateTo('index.html');
}

/**
 * 현재 사용자 정보 가져오기
 */
function getCurrentUser() {
    const sessionData = sessionStorage.getItem('currentUser');
    return sessionData ? JSON.parse(sessionData) : null;
}

/**
 * 로그인 확인
 */
function isLoggedIn() {
    return getCurrentUser() !== null;
}

/**
 * 로그인 필수 체크 (미로그인 시 로그인 페이지로 이동)
 */
function requireLogin() {
    if (!isLoggedIn()) {
        showAlert('로그인이 필요한 서비스입니다.', 'warning');
        setTimeout(() => {
            navigateTo('login.html');
        }, 1000);
        return false;
    }
    return true;
}

/**
 * 관리자 여부 확인
 */
function isAdmin() {
    const currentUser = getCurrentUser();
    if (!currentUser) return false;

    // 관리자 이메일 목록 (실제 환경에서는 서버에서 관리해야 함)
    const adminEmails = ['admin@ticket.com', 'manager@ticket.com'];
    return adminEmails.includes(currentUser.email);
}

/**
 * 관리자 권한 필수 체크 (비관리자는 접근 불가)
 */
function requireAdmin() {
    if (!isLoggedIn()) {
        showAlert('로그인이 필요한 서비스입니다.', 'warning');
        setTimeout(() => {
            navigateTo('login.html?return=' + encodeURIComponent(window.location.pathname));
        }, 1000);
        return false;
    }

    if (!isAdmin()) {
        showAlert('관리자만 접근할 수 있는 페이지입니다.', 'error');
        setTimeout(() => {
            navigateTo('index.html');
        }, 1500);
        return false;
    }

    return true;
}

/**
 * 헤더에 사용자 정보 표시
 */
function updateUserMenu() {
    const userMenuDiv = document.querySelector('.user-menu');
    if (!userMenuDiv) return;

    const currentUser = getCurrentUser();

    if (currentUser) {
        userMenuDiv.innerHTML = `
      <span>${currentUser.name}님</span>
      <button class="btn btn-secondary" onclick="logout()">로그아웃</button>
    `;
    } else {
        userMenuDiv.innerHTML = `
      <a href="login.html" class="btn btn-outline">로그인</a>
      <a href="signup.html" class="btn btn-primary">회원가입</a>
    `;
    }
}

// 페이지 로드 시 사용자 메뉴 업데이트
document.addEventListener('DOMContentLoaded', updateUserMenu);
