# 🚀 Ticket Automation System - 설치 가이드

다른 컴퓨터에서 이 프로젝트를 실행하기 위한 완전한 설치 가이드입니다.

---

## 📋 필요한 외부 응용프로그램

### 1️⃣ **Python 3.10 이상**
   - 다운로드: https://www.python.org/downloads/
   - 설치 시 **"Add Python to PATH"** 체크 필수!
   - 확인: `python --version`

### 2️⃣ **Google Chrome 브라우저**
   - 다운로드: https://www.google.com/chrome/
   - Extension 실행을 위해 필요

### 3️⃣ **Git** (선택사항 - 코드 다운로드용)
   - 다운로드: https://git-scm.com/downloads
   - 또는 ZIP 파일로 다운로드 가능

### 4️⃣ **LM Studio** (CAPTCHA VLM 해결용)
   - 다운로드: https://lmstudio.ai/
   - **Vision 모델** 다운로드 필요:
     - 추천: `qwen/Qwen2-VL-7B-Instruct-GGUF` (7B)
     - 또는: `xtuner/llava-phi-3-mini-gguf` (3.8B, 가벼움)

### 5️⃣ **텍스트 에디터** (선택사항)
   - VS Code (추천): https://code.visualstudio.com/
   - 또는 다른 에디터

---

## 📦 프로젝트 설치

### **1단계: 코드 다운로드**

#### 방법 A: Git 사용
```powershell
cd C:\
git clone https://github.com/bbstation09/ai01-3rd-3team.git
cd ai01-3rd-3team
```

#### 방법 B: ZIP 다운로드
1. GitHub에서 프로젝트 ZIP 다운로드
2. 원하는 위치에 압축 해제 (예: `C:\ai01-3rd-3team`)

---

### **2단계: Python 가상환경 설정**

```powershell
# 프로젝트 디렉토리로 이동
cd C:\ai01-3rd-3team

# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
.venv\Scripts\activate

# 메인 서버 패키지 설치
pip install -r requirements.txt

# CAPTCHA 자동화 패키지 설치
pip install -r swords\requirements.txt
```

**설치되는 패키지:**
- FastAPI, Uvicorn (웹 서버)
- Pillow, OpenCV (이미지 처리)
- PyAutoGUI (마우스/키보드 자동화)
- Requests (HTTP 통신)

---

### **3단계: LM Studio 설정**

1. **LM Studio 실행**

2. **Vision 모델 다운로드:**
   - 좌측 메뉴에서 "Search" 클릭
   - "qwen2-vl" 검색
   - `Qwen2-VL-7B-Instruct` 다운로드

3. **로컬 서버 시작:**
   - "Local Server" 탭
   - 다운로드한 모델 선택
   - "Start Server" 클릭
   - 포트: **12345** (기본값)
   - URL: `http://localhost:12345`

---

### **4단계: Chrome Extension 설치**

1. **Chrome 열기**
2. 주소창에 `chrome://extensions/` 입력
3. 우측 상단 **"개발자 모드"** 켜기
4. **"압축해제된 확장 프로그램을 로드합니다"** 클릭
5. 폴더 선택: `C:\ai01-3rd-3team\swords\chrome-extension`
6. Extension 로드 완료!

**Extension ID 확인:**
- 로드된 Extension 카드에서 ID 확인 (예: `bcgdfl...`)
- `manifest.json`에서 필요 시 수정 가능

---

## 🎯 실행 방법

### **메인 웹 서버 시작**

```powershell
cd C:\ai01-3rd-3team
.venv\Scripts\activate
python main.py
```

서버: `http://localhost:8000`

---

### **CAPTCHA API 서버 시작** (별도 터미널)

```powershell
cd C:\ai01-3rd-3team\swords
..\.venv\Scripts\activate
python captcha_api_server.py
```

API 서버: `http://localhost:5000`

---

### **Chrome에서 티켓팅 페이지 열기**

1. Chrome 브라우저 열기
2. 주소: `http://localhost:8000/html/index.html`
3. Extension 아이콘 클릭
4. 설정:
   - **Random Seats**: 체크 (1-4석 랜덤)
   - **Auto-Loop Count**: `10` (테스트용) 또는 `1000` (본격 수집)
5. **"🚀 즉시 실행"** 클릭

---

## 📂 디렉토리 구조

```
ai01-3rd-3team/
├── .venv/                    # Python 가상환경
├── swords/                   # 티켓 자동화 시스템
│   ├── chrome-extension/     # Chrome 확장 프로그램
│   │   ├── manifest.json
│   │   ├── popup/
│   │   ├── states/           # FSM 상태들
│   │   └── utils/
│   ├── modules/              # VLM, 색상 관리 등
│   ├── captcha_api_server.py # CAPTCHA 해결 API
│   ├── requirements.txt      # Python 의존성
│   ├── CAPTCHA_README.md
│   └── EXTENSION_GUIDE.md
├── html/                     # 테스트 웹 페이지
├── logs/                     # 자동 수집된 로그 (생성됨)
├── main.py                   # 메인 FastAPI 서버
├── requirements.txt          # 서버 의존성
└── SETUP_GUIDE.md           # 이 파일!
```

---

## ✅ 설치 확인 체크리스트

- [ ] Python 3.10+ 설치 완료
- [ ] Chrome 브라우저 설치 완료
- [ ] LM Studio 다운로드 및 Vision 모델 로드
- [ ] 가상환경 생성 및 패키지 설치
- [ ] Chrome Extension 로드 완료
- [ ] 메인 서버 실행: `http://localhost:8000`
- [ ] CAPTCHA API 서버 실행: `http://localhost:5000`
- [ ] LM Studio 서버 실행: `http://localhost:12345`
- [ ] Extension에서 자동화 시작 가능

---

## 🛠️ 문제 해결

### Python을 찾을 수 없음
```
'python'은(는) 내부 또는 외부 명령...
```
→ Python 재설치 시 **"Add to PATH"** 체크

### 가상환경 활성화 안됨
```
.venv\Scripts\activate : 이 시스템에서 스크립트를 실행할 수 없습니다
```
→ PowerShell 관리자 모드:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### LM Studio 연결 실패
```
Error: VLM failed to process
```
→ LM Studio에서:
1. 모델이 로드되어 있는지 확인
2. Local Server가 시작되어 있는지 확인
3. 포트가 12345인지 확인

### Extension 주입 실패
```
Error: Script injection failed
```
→ Chrome Extensions 페이지에서:
1. Extension 재로드
2. 페이지 새로고침
3. 콘솔 로그 확인 (F12)

### 포트 충돌
```
Address already in use
```
→ 다른 프로세스가 포트 사용 중:
- 포트 8000: 다른 웹 서버가 실행 중
- 포트 5000: 다른 프로세스 종료 필요

**포트 확인 (Windows):**
```powershell
netstat -ano | findstr :8000
netstat -ano | findstr :5000
```

**프로세스 종료:**
```powershell
taskkill /PID [프로세스ID] /F
```

---

## 🌐 환경 변수 (선택사항)

### GROQ API 사용 시 (LM Studio 대안)

`swords\modules\vlm_handler.py` 파일에서:

```python
USE_PROVIDER = "GROQ"  # "LM_STUDIO"에서 변경
```

환경 변수 설정:
```powershell
$env:GROQ_API_KEY = "your-api-key-here"
```

GROQ API Key: https://console.groq.com/keys

---

## 📊 시스템 요구사항

### 최소 사양
- **OS**: Windows 10/11
- **RAM**: 8GB
- **저장공간**: 5GB (LM Studio 모델 포함 10GB)
- **CPU**: x64 프로세서

### 권장 사양
- **OS**: Windows 11
- **RAM**: 16GB 이상
- **저장공간**: 20GB
- **GPU**: NVIDIA GPU (LM Studio 가속용)
- **CPU**: 멀티코어 프로세서

---

## 🚀 다음 단계

1. ✅ 모든 응용프로그램 설치
2. ✅ Python 패키지 설치
3. ✅ LM Studio 모델 다운로드
4. ✅ Chrome Extension 로드
5. ✅ 서버 3개 실행 (Main, CAPTCHA API, LM Studio)
6. ✅ 자동화 시작!

**성공적인 설치를 기원합니다! 🎉**

---

## 📞 추가 도움말

- **CAPTCHA 시스템**: `swords/CAPTCHA_README.md`
- **Extension 가이드**: `swords/EXTENSION_GUIDE.md`
- **프로젝트 링크**: `ACCESS_LINKS.md`
