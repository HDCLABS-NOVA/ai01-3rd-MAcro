# 관리자 로그 뷰어 접근 가이드

## 🔐 관리자 권한 설정

로그 뷰어 페이지는 관리자만 접근할 수 있습니다.

### 기본 관리자 계정

서버 시작 시 자동으로 생성되는 관리자 계정:

**계정 1:**
- 이메일: `admin@ticket.com`
- 비밀번호: `admin1234`
- 이름: Administrator

**계정 2:**
- 이메일: `manager@ticket.com`
- 비밀번호: `manager1234`
- 이름: Manager

### 로그 뷰어 페이지 목록

1. **통합 뷰어**: `viewer.html`
   - 공연 선택과 예매 과정 모두 확인 가능

2. **예매 로그 뷰어**: `viewer_booking.html`
   - 좌석 선택 → 결제 완료까지의 로그 분석

3. **공연 선택 로그 뷰어**: `viewer_performance.html`
   - 공연 페이지 → 대기열 입장 직전까지의 로그 분석

## 📋 사용 방법

### 1. 로그인

관리자 계정으로 로그인:
```
이메일: admin@ticket.com
비밀번호: admin1234
```

서버 시작 시 콘솔에 다음 메시지가 표시됩니다:
```
✅ 관리자 계정 생성: admin@ticket.com (비밀번호: admin1234)
✅ 관리자 계정 생성: manager@ticket.com (비밀번호: manager1234)
```

### 3. 로그 뷰어 접근

브라우저 주소창에 직접 입력:
- `http://localhost:8000/viewer.html`
- `http://localhost:8000/viewer_booking.html`
- `http://localhost:8000/viewer_performance.html`

### 4. 비관리자 접근 시도 시

- 로그인하지 않은 경우: "로그인이 필요한 서비스입니다" 메시지와 함께 로그인 페이지로 이동
- 일반 사용자 계정으로 접근 시: "관리자만 접근할 수 있는 페이지입니다" 메시지와 함께 메인 페이지로 이동

## 🛡️ 보안 설정

### 현재 구현

- **클라이언트 측 검증**: `js/auth.js`의 `isAdmin()` 함수에서 이메일 기반 검증
- **관리자 이메일 목록**: 하드코딩된 이메일 목록 사용

### 프로덕션 환경 권장사항

**중요**: 현재 구현은 개발/데모 용도입니다. 실제 프로덕션 환경에서는 다음과 같이 개선해야 합니다:

1. **서버 측 검증 추가**:
   ```python
   # main.py에 추가
   def is_admin(email: str) -> bool:
       admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
       return email in admin_emails
   ```

2. **환경 변수 사용**:
   ```
   # .env 파일
   ADMIN_EMAILS=admin@ticket.com,manager@ticket.com
   ```

3. **JWT 토큰 기반 인증**:
   - 로그인 시 관리자 권한 포함된 JWT 토큰 발급
   - 로그 뷰어 API 호출 시 토큰 검증

4. **데이터베이스 역할 관리**:
   - users 테이블에 `role` 컬럼 추가 (admin, user)
   - 로그인 시 역할 확인

## ⚙️ 코드 위치

### 관리자 체크 함수

**파일**: `js/auth.js`

```javascript
// 관리자 이메일 목록 수정
function isAdmin() {
    const currentUser = getCurrentUser();
    if (!currentUser) return false;
    
    const adminEmails = ['admin@ticket.com', 'manager@ticket.com'];
    return adminEmails.includes(currentUser.email);
}
```

### 뷰어 페이지 보호

각 viewer 페이지 상단에 추가됨:

```javascript
// 관리자 권한 체크
if (!requireAdmin()) {
    throw new Error('Unauthorized access');
}
```

## 🧪 테스트

1. **관리자 접근 테스트**:
   - `admin@ticket.com`으로 로그인
   - `viewer.html` 접근 → 성공

2. **일반 사용자 접근 테스트**:
   - 일반 이메일로 로그인
   - `viewer.html` 접근 → 차단 및 메인 페이지로 리디렉션

3. **비로그인 접근 테스트**:
   - 로그아웃 상태
   - `viewer.html` 접근 → 차단 및 로그인 페이지로 리디렉션
