# 로그인 및 CAPTCHA 처리 디버깅 노트

## 문제 분석

### 발견된 문제

#### 1. 로그인 문제
- **로그인 폼 대기 부족**: 로그인 페이지로 리다이렉트될 때 폼이 로드되기 전에 입력 시도
- **sessionStorage 저장 대기 부족**: 로그인 성공 후 sessionStorage 저장 완료 전에 다음 단계 진행
- **로그인 체크 방식 불안정**: `"login" in page.url`만으로는 리다이렉트 중간 상태를 놓칠 수 있음

#### 2. CAPTCHA 순서 문제 ⭐ NEW
- **잘못된 순서**: CAPTCHA 처리를 좌석 선택보다 먼저 시도
- **실제 동작**: 좌석 선택 페이지 로드 후 0.5초 뒤 CAPTCHA 팝업이 나타남
- **결과**: 좌석 로딩 대기 중인데 화면에 CAPTCHA가 떠 있음

## 해결 방법

### 1. 로그인 함수 강화

```python
def _login(self, page: Page) -> bool:
    # 1. 로그인 폼이 나타날 때까지 대기
    page.wait_for_selector("#login-form", state="visible", timeout=self.default_timeout)
    time.sleep(1)  # 페이지 안정화
    
    # 2. 입력 필드 채우기 (각 입력마다 0.5초 대기)
    email_input = page.locator("#email")
    email_input.fill(self.login_email)
    time.sleep(0.5)
    
    password_input = page.locator("#password")
    password_input.fill(self.login_password)
    time.sleep(0.5)
    
    # 3. 로그인 버튼 클릭 (type='submit' 사용)
    login_btn = page.locator("button[type='submit']").filter(has_text="로그인")
    login_btn.click(timeout=10000)
    
    # 4. 로그인 성공 대기 (alert 표시 + 리다이렉트)
    time.sleep(3)
    
    # 5. sessionStorage 확인
    is_logged_in = page.evaluate("""
        () => {
            const user = sessionStorage.getItem('currentUser');
            return user !== null;
        }
    """)
    
    return is_logged_in
```

### 2. CAPTCHA 순서 수정 ⭐ NEW

**변경 전 (잘못된 순서):**
```python
# Step 8: CAPTCHA 처리
self._handle_captcha(page)

# Step 9: 좌석 선택
self._select_seat(page)
```

**변경 후 (올바른 순서):**
```python
# Step 8: 좌석 선택 페이지 로딩
print("📍 Step 8: 좌석 선택 페이지 로딩...")
time.sleep(2)  # 페이지 로드 및 CAPTCHA 팝업 대기 (0.5초 후 팝업)

# Step 9: CAPTCHA 처리 (좌석 페이지의 팝업)
print("📍 Step 9: CAPTCHA 처리...")
self._handle_captcha(page)

# Step 10: 좌석 선택
print("📍 Step 10: 좌석 선택...")
self._select_seat(page)
```

### 3. 좌석 선택 대기 시간 조정

**변경 전:**
```python
time.sleep(3)  # 좌석 동적 생성 대기
```

**변경 후:**
```python
time.sleep(1)  # CAPTCHA 통과 후이므로 짧게
```

이유: CAPTCHA를 먼저 처리했으므로 좌석은 이미 생성되어 있음

### 2. 로그인 체크 개선

**변경 전:**
```python
if "login" in page.url:
    self._login(page)
```

**변경 후:**
```python
time.sleep(2)  # 리다이렉트 대기

# URL 또는 로그인 폼 존재 여부로 확인
if "login" in page.url or page.locator("#login-form").is_visible(timeout=3000):
    self._login(page)
```

### 3. 두 번의 로그인 체크

1. **Step 6**: 예매 시작 버튼 클릭 후
   - `requireLogin()` 함수가 로그인 페이지로 리다이렉트
   - 로그인 성공 → index.html로 돌아감
   - 다시 공연 선택부터 시작

2. **Step 7**: 대기열 통과 후 좌석 선택 전
   - 세션이 만료되었을 경우를 대비
   - 로그인 성공 → 다시 공연 선택부터 시작
   - 대기열 5초 대기 추가

## 주요 타이밍

| 단계 | 대기 시간 | 이유 |
|------|-----------|------|
| 예매 시작 버튼 클릭 후 | 2초 | 리다이렉트 완료 대기 |
| 로그인 폼 나타남 | 1초 | 페이지 안정화 |
| 이메일/비밀번호 입력 | 각 0.5초 | 입력 완료 확인 |
| 로그인 버튼 클릭 후 | 3초 | alert + 리다이렉트 + sessionStorage 저장 |
| 대기열 통과 후 | 2초 | 로그인 체크 전 안정화 |
| 로그인 후 대기열 재진입 | 5초 | 대기열 통과 대기 |

## 테스트 시나리오

### ✅ 시나리오 1: 로그인 안 된 상태 (최초 실행)
```
1. 메인 페이지 접속
2. 공연 선택 → 날짜 → 시간 → 예매 시작
3. 로그인 페이지로 리다이렉트 (Step 6)
4. 로그인 폼 대기 (1초)
5. test1@email.com / 11111111 입력
6. 로그인 성공 (3초 대기)
7. sessionStorage 확인 ✓
8. index.html로 리다이렉트됨
9. 다시 공연 선택 → 날짜 → 시간 → 예매 시작
10. 대기열 진입 (5초 대기)
11. 좌석 선택 페이지
```

### ✅ 시나리오 2: 세션 만료 (대기열 후)
```
1-9. (시나리오 1과 동일)
10. 대기열 통과
11. 로그인 체크 (Step 7-1)
12. 로그인 페이지 감지
13. 로그인 수행
14. 다시 공연 선택부터
15. 대기열 대기 (5초)
16. 좌석 선택 페이지
```

### ✅ 시나리오 3: 이미 로그인됨
```
1. 메인 페이지 접속
2. 공연 선택 → 날짜 → 시간 → 예매 시작
3. 로그인 체크 (2초 대기)
4. 로그인 폼 없음 → 계속 진행
5. 대기열 진입
6. 로그인 체크 (2초 대기)
7. 로그인 폼 없음 → 계속 진행
8. CAPTCHA → 좌석 선택
```

## 디버깅 팁

### 로그인이 계속 실패하는 경우
1. 스크린샷 확인: `error_*.png`
2. 로그 확인:
   - "⏳ 로그인 페이지 로딩 대기 중..." - 폼 대기
   - "📧 이메일 입력: test1@email.com" - 이메일 입력 성공
   - "🔑 비밀번호 입력" - 비밀번호 입력 성공
   - "🔘 로그인 버튼 클릭" - 버튼 클릭 성공
   - "✅ 로그인 성공 (세션 확인됨)" - sessionStorage 확인 ✓
3. 서버 로그 확인: `/api/auth/login` 응답 확인

### 로그인은 성공하는데 계속 반복되는 경우
1. sessionStorage가 제대로 저장되는지 확인
2. 브라우저 컨텍스트가 유지되는지 확인
3. 로그인 후 3초 대기가 충분한지 확인

### 대기열에서 멈추는 경우
1. queue.html은 3-5초 후 자동으로 seat_select.html로 이동
2. Step 7-2에서 대기열 5초 대기 추가
3. 너무 짧으면 좌석 페이지 진입 전에 다음 단계 시도

## 코드 변경 요약

### `_login()` 함수
- 로그인 폼 명시적 대기 추가
- 각 입력마다 0.5초 대기
- 로그인 성공 후 3초 대기 (alert + 리다이렉트)
- sessionStorage 확인으로 로그인 성공 검증

### Step 6 (예매 시작 후 로그인 체크)
- 2초 리다이렉트 대기 추가
- URL + 로그인 폼 존재 여부 체크

### Step 7 (좌석 선택 전 로그인 체크)
- 2초 리다이렉트 대기 추가
- URL + 로그인 폼 존재 여부 체크
- 로그인 후 대기열 5초 대기 추가
- try-except로 로그인 폼 없으면 계속 진행
