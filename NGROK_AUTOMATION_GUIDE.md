# 🚀 Ngrok 원격 서버 자동화 가이드

## 📋 개요

이 가이드는 **ngrok으로 호스팅된 원격 티켓팅 서버**에 Chrome Extension과 VLM을 사용하여 로그를 자동 수집하는 방법을 설명합니다.

### 서버 정보
- **Ngrok URL**: `https://974e36126faa.ngrok-free.app/`
- **목적**: 원격에서 티켓팅 사이트 접속 및 로그 자동 수집

---

## 🏗️ 아키텍처

```
[원격 서버 (Ngrok)]              [로컬 PC (자동화 PC)]
┌──────────────────────┐         ┌──────────────────────────┐
│ FastAPI 서버         │         │ Chrome Browser           │
│ (티켓팅 사이트)       │◄────────│ + SWORD Extension        │
│                      │  HTTPS  │   - 티켓팅 자동화        │
│ 974e36126faa.        │         │   - 로그 수집            │
│ ngrok-free.app       │         │                          │
└──────────────────────┘         │ + LM Studio (VLM)        │
        ▲                        │   localhost:12345        │
        │                        │   - CAPTCHA 해결         │
        │ POST /api/logs         └──────────────────────────┘
        └────────────────────────────────┘
```

---

## ⚙️ 설정 완료 항목

### ✅ 1. Chrome Extension 설정

**파일**: `swords/chrome-extension/manifest.json`

```json
{
  "host_permissions": [
    "http://localhost:*/*",
    "http://192.168.14.118:*/*",
    "https://974e36126faa.ngrok-free.app/*"  // ← ngrok URL 추가됨
  ],
  "content_scripts": [{
    "matches": [
      "file:///*/*",
      "http://localhost:*/*",
      "http://127.0.0.1:*/*",
      "http://192.168.14.118:*/*",
      "https://974e36126faa.ngrok-free.app/*"  // ← ngrok URL 추가됨
    ]
  }]
}
```

### ✅ 2. 사이트 설정

**파일**: `swords/chrome-extension/config/sites.js`

ngrok 호스트명을 감지하여 자동으로 `localhost` 설정을 사용하도록 구성됨:

```javascript
function getSiteConfig(hostname = window.location.hostname) {
  // ngrok URL도 localhost 설정 사용
  if (hostname.includes('ngrok') || hostname.includes('974e36126faa')) {
    return SiteConfig.localhost;
  }
  // ...
}
```

---

## 🚀 사용 방법

### **1단계: LM Studio (VLM) 실행**

로컬 PC에서 LM Studio를 실행하세요:

1. **LM Studio 열기**
2. **모델 로드**: `Qwen2-VL-7B` GGUF 모델
3. **서버 시작**: `http://localhost:12345`
4. **서버 실행 확인**:
   ```bash
   curl http://localhost:12345/v1/models
   ```

### **2단계: Chrome Extension 로드**

1. **Chrome 열기**
2. **주소창**에 `chrome://extensions/` 입력
3. **개발자 모드** 활성화 (우측 상단 토글)
4. **압축해제된 확장 프로그램 로드** 클릭
5. **폴더 선택**: `ai01-3rd-3team-1/swords/chrome-extension`
6. Extension이 로드되면 **활성화** 확인

### **3단계: 원격 서버 접속**

Chrome에서 ngrok URL로 접속:

```
https://974e36126faa.ngrok-free.app/html/index.html
```

**⚠️ Ngrok 경고 페이지가 나타날 수 있음**
- "Visit Site" 버튼 클릭하여 진행

### **4단계: Extension 설정**

1. Extension 아이콘 클릭 (Chrome 우측 상단)
2. **설정**:
   - **좌석 수**: 1-4석 선택
   - **Auto-Resume**: ON (권장)
   - **Random Time**: ON (인간처럼 보이게)
   - **Auto Loop**: ON (여러 번 반복 수집)

### **5단계: 자동화 시작**

1. **티켓팅 플로우 시작**:
   - 공연 목록 페이지에서 **Start** 버튼 클릭
   - 또는 공연 상세 페이지에서 자동 시작

2. **자동 실행 단계**:
   ```
   공연 선택 → 날짜/시간 선택 → 대기열 통과 → 
   구역 선택 → 좌석 선택 → CAPTCHA 해결 → 
   할인 선택 → 배송 정보 → 결제 → 완료
   ```

3. **CAPTCHA 자동 해결**:
   - VLM이 자동으로 CAPTCHA 이미지 분석
   - 정답 입력 및 제출
   - 실패 시 재시도

4. **로그 자동 전송**:
   - 각 단계별 마우스 트래킹 데이터 수집
   - 완료 시 원격 서버 `/api/logs`로 자동 전송

---

## 📊 로그 확인 방법

### **방법 1: 원격 서버에서 직접 확인**

원격 서버 관리자 계정으로 로그인:
```
https://974e36126faa.ngrok-free.app/html/viewer_booking.html
```

**로그인 정보**:
- Email: `admin@example.com`
- Password: `admin123`

### **방법 2: API로 확인**

```bash
# 로그 목록 조회
curl https://974e36126faa.ngrok-free.app/api/logs

# 특정 로그 다운로드
curl https://974e36126faa.ngrok-free.app/api/logs/[filename]
```

---

## 🔧 트러블슈팅

### ❌ **Extension이 작동하지 않음**

**확인사항**:
1. Extension이 활성화되어 있는지 확인
2. `manifest.json`에 ngrok URL이 올바르게 추가되었는지 확인
3. Chrome Extension 재로드:
   - `chrome://extensions/`
   - Extension 카드에서 **새로고침** 🔄 클릭

### ❌ **VLM CAPTCHA 해결 실패**

**확인사항**:
1. LM Studio가 실행 중인지 확인
2. 모델이 올바르게 로드되었는지 확인
3. `localhost:12345` 접근 가능한지 확인:
   ```bash
   curl http://localhost:12345/v1/models
   ```

### ❌ **로그가 서버로 전송되지 않음**

**확인사항**:
1. 네트워크 연결 확인
2. Ngrok URL이 유효한지 확인 (ngrok URL은 시간이 지나면 변경됨)
3. Chrome 개발자 도구 (F12) → Console 탭에서 에러 확인
4. Chrome 개발자 도구 → Network 탭에서 `/api/logs` 요청 확인

### ❌ **"Access Denied" 또는 CORS 에러**

**해결방법**:
1. Ngrok 경고 페이지에서 "Visit Site" 클릭
2. 서버 측에서 CORS 설정 확인
3. Extension manifest의 `host_permissions` 재확인

---

## 📝 주의사항

### ⚠️ **Ngrok URL 변경**

- Ngrok 무료 버전은 세션이 종료되면 URL이 변경됩니다
- **URL이 변경되면**:
  1. `manifest.json` 업데이트
  2. `sites.js` 업데이트 (선택사항, hostname.includes('ngrok') 조건이 있어 자동 감지됨)
  3. Chrome Extension 재로드

### ⚠️ **보안**

- 이 도구는 **연구/교육 목적**으로만 사용하세요
- 실제 티켓팅 사이트에서 무단 사용 금지
- 로그에는 민감한 정보가 포함될 수 있으니 주의하세요

### ⚠️ **성능**

- 원격 서버는 네트워크 지연이 있을 수 있습니다
- 로컬 테스트보다 느릴 수 있습니다
- Auto-Loop 설정 시 적절한 간격을 두세요

---

## 📚 추가 리소스

- **SETUP_GUIDE.md**: 전체 프로젝트 설정 가이드
- **CAPTCHA_README.md**: VLM CAPTCHA 해결 시스템 상세 가이드
- **chrome-extension/ARCHITECTURE.md**: Extension FSM 아키텍처 문서

---

## 🎯 자동화 성공 체크리스트

- [ ] LM Studio 실행 중 (localhost:12345)
- [ ] Chrome Extension 로드 및 활성화
- [ ] Ngrok URL 접속 성공
- [ ] Extension 설정 완료 (좌석 수, Auto-Resume 등)
- [ ] Start 버튼 클릭 후 자동화 시작
- [ ] CAPTCHA 자동 해결 확인
- [ ] 로그가 원격 서버로 전송 확인

---

**Happy Automating! 🎫🤖**
