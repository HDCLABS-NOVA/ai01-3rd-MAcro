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

서버 시작 시 콘솔에 다음 메시지가 표시됩니다:
```
✅ 관리자 계정 생성: admin@ticket.com (비밀번호: admin1234)
✅ 관리자 계정 생성: manager@ticket.com (비밀번호: manager1234)
```

### 로그 뷰어 페이지 목록

1. **통합 뷰어**: `http://localhost:8000/viewer.html`
   - 공연 선택과 예매 과정 모두 확인 가능

2. **예매 로그 뷰어**: `http://localhost:8000/viewer_booking.html`
   - 좌석 선택 → 결제 완료까지의 로그 분석

3. **공연 선택 로그 뷰어**: `http://localhost:8000/viewer_performance.html`
   - 공연 페이지 → 대기열 입장 직전까지의 로그 분석

### 관리자 대시보드 페이지

**티켓 오픈 시간 관리**: `http://localhost:8000/admin.html`
- 공연별 티켓 오픈 시간 설정 및 관리
- 실시간 카운트다운 타이머
- 오픈 시간 업데이트 기능


## 📋 사용 방법

### 1. 로그 뷰어 접근

브라우저 주소창에 직접 입력:
```
http://localhost:8000/viewer.html
```

### 2. 자동 로그인 리디렉션

- 로그인하지 않은 상태 → 로그인 페이지로 자동 이동
- 로그인 페이지에 **디버그 정보** 표시됨:
  ```
  🔍 디버그:
  현재 URL: http://localhost:8000/login.html?return=viewer.html
  Return 파라미터: viewer.html
  ```

### 3. 로그인

관리자 계정으로 로그인:
```
이메일: admin@ticket.com
비밀번호: admin1234
```

### 4. 자동 리디렉션

로그인 성공 시 원래 접근하려던 뷰어 페이지로 자동 리디렉션됩니다.

### 5. 비관리자 접근 시도 시

- 로그인하지 않은 경우: "로그인이 필요한 서비스입니다" → 로그인 페이지
- 일반 사용자 계정: "관리자만 접근할 수 있는 페이지입니다" → 메인 페이지

## 🔧 트러블슈팅

### 문제 1: 로그인 후 viewer.html 대신 index.html로 이동

**원인:** 브라우저 캐시 문제

**해결:**
1. **Ctrl + Shift + R** (강제 새로고침)
2. 또는 **Ctrl + Shift + Delete** → 캐시 및 쿠키 삭제
3. 브라우저 재시작

### 문제 2: "Return 파라미터: (없음)" 표시

**원인:** `auth.js` 파일이 캐시됨

**해결:**
1. 브라우저 개발자 도구 열기 (F12)
2. Network 탭 → "Disable cache" 체크
3. 페이지 새로고침 (Ctrl + Shift + R)

### 문제 3: 로그인은 되는데 권한 에러

**원인:** 관리자 이메일이 아님

**확인:**
- 이메일이 정확히 `admin@ticket.com` 또는 `manager@ticket.com`인지 확인
- 대소문자 구분 (모두 소문자)

### 문제 4: 서버 시작 시 관리자 계정이 생성 안 됨

**원인:** `data/users.json` 파일에 이미 계정 존재

**해결:**
```bash
# users.json 확인
cat data/users.json

# 계정이 없으면 서버 재시작
python main.py
```

## 🛡️ 보안 설정

### 현재 구현

- **클라이언트 측 검증**: `js/auth.js`의 `isAdmin()` 함수에서 이메일 기반 검증
- **관리자 이메일 목록**: 하드코딩된 이메일 목록 사용
- **자동 계정 생성**: 서버 시작 시 `main.py`에서 자동 생성

### 프로덕션 환경 권장사항

**중요**: 현재 구현은 개발/데모 용도입니다. 실제 프로덕션 환경에서는 다음과 같이 개선해야 합니다:

1. **서버 측 검증 추가**:
   ```python
   # main.py에 추가
   def is_admin(email: str) -> bool:
       admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
       return email in admin_emails
   
   # 로그 뷰어 API에 데코레이터 추가
   @app.get("/api/logs")
   async def get_logs(current_user: dict = Depends(require_admin)):
       ...
   ```

2. **환경 변수 사용**:
   ```env
   # .env 파일
   ADMIN_EMAILS=admin@ticket.com,manager@ticket.com
   ADMIN_DEFAULT_PASSWORD=your_secure_password
   ```

3. **비밀번호 해시화**:
   ```python
   import bcrypt
   
   # 회원가입 시
   hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
   
   # 로그인 시
   bcrypt.checkpw(password.encode(), stored_hash)
   ```

4. **JWT 토큰 기반 인증**:
   - 로그인 시 관리자 권한 포함된 JWT 토큰 발급
   - 로그 뷰어 API 호출 시 토큰 검증

5. **데이터베이스 역할 관리**:
   - users 테이블에 `role` 컬럼 추가 (admin, user)
   - 로그인 시 역할 확인

## ⚙️ 코드 위치

### 관리자 체크 함수

**파일**: `js/auth.js`

```javascript
// 관리자 여부 확인
function isAdmin() {
    const currentUser = getCurrentUser();
    if (!currentUser) return false;
    
    const adminEmails = ['admin@ticket.com', 'manager@ticket.com'];
    return adminEmails.includes(currentUser.email);
}

// 관리자 권한 필수 체크
function requireAdmin() {
    if (!isLoggedIn()) {
        showAlert('로그인이 필요한 서비스입니다.', 'warning');
        setTimeout(() => {
            const currentPage = window.location.pathname.split('/').pop() || 'viewer.html';
            navigateTo('login.html?return=' + encodeURIComponent(currentPage));
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
```

### 자동 관리자 계정 생성

**파일**: `main.py`

```python
def init_admin_accounts():
    """서버 시작 시 기본 관리자 계정을 생성합니다."""
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    admin_accounts = [
        {
            "email": "admin@ticket.com",
            "password": "admin1234",
            "name": "Administrator",
            "phone": "01000000000"
        },
        {
            "email": "manager@ticket.com",
            "password": "manager1234",
            "name": "Manager",
            "phone": "01000000001"
        }
    ]
    
    users_updated = False
    for admin in admin_accounts:
        existing = any(user['email'] == admin['email'] for user in data['users'])
        if not existing:
            data['users'].append(admin)
            users_updated = True
            print(f"✅ 관리자 계정 생성: {admin['email']} (비밀번호: {admin['password']})")
    
    if users_updated:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# 서버 시작 시 실행
init_admin_accounts()
```

### 뷰어 페이지 보호

각 viewer 페이지 상단에 추가됨:

```javascript
// 관리자 권한 체크
if (!requireAdmin()) {
    throw new Error('Unauthorized access');
}
```

## 🧪 테스트 체크리스트

- [ ] 서버 시작 시 관리자 계정 생성 메시지 확인
- [ ] 비로그인 상태에서 viewer.html 접근 → 로그인 페이지로 리디렉션
- [ ] 로그인 페이지에서 디버그 정보 확인 (Return 파라미터 표시)
- [ ] 관리자 계정으로 로그인 → viewer.html로 자동 리디렉션
- [ ] 일반 사용자 계정으로 viewer.html 접근 → 차단 및 index.html로 리디렉션
- [ ] 로그 뷰어에서 로그 목록 정상 표시
- [ ] 브라우저 캐시 클리어 후 재테스트

## 📞 지원

문제가 계속되면 다음 정보를 제공해주세요:

1. 브라우저 콘솔 로그 (F12 → Console)
2. 로그인 페이지의 디버그 정보 스크린샷
3. 서버 콘솔 출력
4. 사용한 이메일과 어떤 페이지로 리디렉션 되었는지
