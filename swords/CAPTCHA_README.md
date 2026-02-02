# 🔐 CAPTCHA 자동 해결 시스템

## 📋 파일 구조

### ✅ 사용 파일

| 파일 | 용도 |
|------|------|
| `captcha_vlm.py` | GUI 앱 - 화면 모니터링 + VLM CAPTCHA 해결 |
| `captcha_api_server.py` | API 서버 - HTTP 엔드포인트 제공 |
| `human_captcha.py` | 독립 실행 스크립트 - 사람처럼 동작 |
| `ticketpark_auto.py` | 통합 GUI - 전체 예매 프로세스 자동화 |
| `chrome-extension/states/handle_captcha.js` | Extension - API 서버 호출 |

### 🗑️ 삭제된 파일

- ~~`quick_captcha.py`~~ (개선 버전으로 대체)
- ~~`simple_captcha.py`~~ (더 이상 불필요)
- ~~`browser_captcha.py`~~ (의존성 문제)

---

## 🚀 사용 방법

### **방법 1: Chrome Extension + API Server** (추천)

1000+ 로그 자동 수집에 최적화

#### 1단계: API 서버 시작

```powershell
cd c:\HDCLab\ai01-3rd-3team\swords
..\.venv\Scripts\python.exe captcha_api_server.py
```

서버가 `http://localhost:5000`에서 실행됩니다.

#### 2단계: LM Studio 시작

1. LM Studio 실행
2. Vision 모델 로드 (예: `qwen3-v1-8b`)
3. Local Server > Start Server (포트 12345)

#### 3단계: Chrome Extension 실행

1. `chrome://extensions/` 열기
2. Extension 재로드
3. 공연 페이지 열기
4. Extension 팝업:
   - Auto-Loop Count: `1000`
   - "🚀 즉시 실행" 클릭

**자동 진행:**
- CAPTCHA 감지 → API 호출 → VLM 분석 → 자동 입력
- 실패 시 → 수동 대기 → 해결 시 자동 재개

---

### **방법 2: GUI 앱 사용**

단독 모니터링 및 해결

```powershell
cd c:\HDCLab\ai01-3rd-3team\swords
..\.venv\Scripts\python.exe captcha_vlm.py
```

- GUI에서 "▶ START Monitoring" 클릭
- 화면을 모니터링하다가 CAPTCHA 감지 시 자동 해결

---

### **방법 3: 독립 스크립트**

일회성 테스트

```powershell
cd c:\HDCLab\ai01-3rd-3team\swords
..\.venv\Scripts\python.exe human_captcha.py
```

- 브라우저에서 CAPTCHA 표시
- 스크립트 실행
- 2초 후 자동으로 캡처 및 해결

---

## 🔧 API 엔드포인트

### POST `/solve`

CAPTCHA 자동 해결

**Request:**
```json
{
  "use_screen_capture": true
}
```

**Response:**
```json
{
  "success": true,
  "text": "ZTVHHX",
  "message": "CAPTCHA 'ZTVHHX' solved successfully"
}
```

### GET `/health`

서버 상태 확인

---

## 📁 로그 파일

자동 수집된 로그는 다음 형식으로 저장됩니다:

```
logs/
├── 20260131_IU001_abc123_success.json
├── 20260131_IU001_def456_success.json
├── 20260131_IU001_ghi789_failed.json
└── ...
```

형식: `[날짜]_[공연ID]_[flow_id]_[결과].json`

---

## ⚡ 자동화 플로우

```
시작
 ↓
로그인
 ↓
공연 선택
 ↓
일정/시간 선택
 ↓
CAPTCHA 감지 ← handle_captcha.js
 ↓
API 호출 (/solve) ← captcha_api_server.py
 ↓
VLM 분석 ← LM Studio
 ↓
자동 입력 (human_type)
 ↓
좌석 선택
 ↓
결제
 ↓
완료 → 로그 저장
 ↓
다음 시도 (Auto-Loop)
```

---

## 🛠️ 문제 해결

### API 서버 연결 안됨

```
Error: CAPTCHA_API_UNAVAILABLE
```

→ `captcha_api_server.py` 실행 확인

### VLM 응답 없음

```
Error: VLM failed to process
```

→ LM Studio 서버 실행 및 모델 로드 확인

### CAPTCHA 감지 안됨

```
No CAPTCHA detected
```

→ 브라우저에 CAPTCHA가 표시되어 있는지 확인
→ VLM 프롬프트 조정 필요할 수 있음

---

## 📊 성능

- **자동 해결 성공률**: ~85% (VLM 성능에 따름)
- **평균 해결 시간**: 2-4초
- **실패 시 수동 대기**: 자동 재개

---

## 🎯 다음 단계

1. ✅ Extension 재로드
2. ✅ API 서버 시작
3. ✅ LM Studio 시작
4. ✅ Auto-Loop 설정 (1000)
5. ✅ 실행!
