# 🎫 티켓 예매 시스템 (Ticket Booking System)

사용자 행동 분석 및 봇 탐지를 위한 **로깅 기능이 강화된 티켓 예매 시스템**입니다.  
실제 예매 사이트와 유사한 UI/UX를 제공하며, 마우스 궤적, 클릭, 입력 등 모든 사용자 행동을 상세히 기록합니다.

---

## 🌟 주요 기능

### 📊 **사용자 행동 로깅**
- **마우스 궤적 추적**: 100ms마다 위치 기록
- **클릭 이벤트**: 모든 클릭의 좌표, 시간, 대상 요소 저장
- **입력 패턴**: 타이핑 속도, 붙여넣기 감지
- **화면 해상도 정규화**: 다양한 기기에서 일관된 분석 가능
- **호버링 분석**: 각 좌석/요소별 호버링 시간 및 떨림(tremor) 분석

### 🎭 **완전한 예매 플로우**
1. **로그인/회원가입** - 사용자 인증
2. **공연 선택** - 다양한 카테고리의 공연 목록
3. **대기열** - 실감나는 대기 시스템
4. **좌석 선택** - 인터랙티브 좌석 맵 (35% 확률로 선점 충돌)
5. **할인 선택** - 다양한 할인 옵션
6. **예매자 정보 입력** - 직접 입력 가능
7. **결제** - 카드/간편결제 선택
8. **완료** - 예매 완료 화면

### 🎬 **관리자 대시보드**
- **티켓 오픈 시간 관리**: 공연별 판매 오픈 시간 설정
- **실시간 카운트다운**: 티켓 오픈까지 남은 시간 표시
- **로그 뷰어**: 수집된 사용자 행동 데이터 시각화
  - 마우스 궤적 캔버스 렌더링
  - 클릭 포인트 표시
  - 호버링 히트맵
  - 떨림(tremor) 분석 그래프

### 🛡️ **봇 탐지용 데이터**
- 마우스 이동 패턴 분석
- 클릭 타이밍 및 빈도
- 입력 속도 (타이핑 vs 붙여넣기)
- 페이지별 체류 시간
- 좌석 선택 시 호버링 행동

---

## 🚀 빠른 시작

### 1️⃣ 필수 요구사항

- **Python**: 3.8 이상
- **브라우저**: Chrome, Firefox, Edge 등 최신 브라우저

### 2️⃣ 설치

```bash
# 저장소 클론
git clone https://github.com/bbstation09/ai01-3rd-3team.git
cd dev_final

# 의존성 설치
pip install -r requirements.txt
```

### 3️⃣ 서버 실행

```bash
python main.py
```

서버가 시작되면 다음 메시지가 표시됩니다:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
✅ 관리자 계정 생성: admin@ticket.com (비밀번호: admin1234)
✅ 관리자 계정 생성: manager@ticket.com (비밀번호: manager1234)
```

### 4️⃣ 접속

브라우저에서 다음 주소로 접속:
```
http://localhost:8000
```

---

## 📁 프로젝트 구조

```
dev_final/
├── main.py                      # FastAPI 백엔드 서버
├── requirements.txt             # Python 의존성
│
├── data/                        # 데이터 저장소
│   ├── users.json              # 사용자 계정 정보
│   └── performances.json       # 공연 정보 및 오픈 시간
│
├── logs/                        # 사용자 행동 로그 (JSON)
│
├── css/                         # 스타일시트
│   ├── styles.css              # 공통 스타일
│   ├── seat_select.css         # 좌석 선택 스타일
│   └── admin.css               # 관리자 대시보드 스타일
│
├── js/                          # JavaScript 로직
│   ├── auth.js                 # 인증 및 권한 관리
│   ├── logger.js               # 로깅 시스템
│   ├── seat_select.js          # 좌석 선택 로직
│   ├── admin.js                # 관리자 대시보드
│   └── ...                     # 각 페이지별 스크립트
│
├── HTML 페이지들
│   ├── login.html              # 로그인
│   ├── signup.html             # 회원가입
│   ├── index.html              # 공연 선택
│   ├── queue.html              # 대기열
│   ├── seat_select.html        # 좌석 선택
│   ├── discount.html           # 할인 선택
│   ├── order_info.html         # 예매자 정보
│   ├── payment.html            # 결제
│   ├── booking_complete.html   # 예매 완료
│   ├── admin.html              # 관리자 대시보드
│   ├── viewer.html             # 통합 로그 뷰어
│   ├── viewer_booking.html     # 예매 과정 로그 뷰어
│   └── viewer_performance.html # 공연 선택 로그 뷰어
│
└── 문서 (*.md)
    ├── README.md                    # 👈 이 파일
    ├── ACCESS_LINKS.md              # 접속 링크 모음
    ├── ADMIN_ACCESS_GUIDE.md        # 관리자 가이드
    ├── TICKET_OPEN_TIME_GUIDE.md    # 오픈 시간 관리 가이드
    └── CHANGELOG_2026-01-30.md      # 변경 로그
```

---

## 🔗 주요 접속 링크

### 일반 사용자
- **메인 페이지**: http://localhost:8000
- **로그인**: http://localhost:8000/login.html
- **회원가입**: http://localhost:8000/signup.html
- **공연 선택**: http://localhost:8000/index.html

### 관리자 (로그인 필요)
- **관리자 대시보드**: http://localhost:8000/admin.html
- **통합 로그 뷰어**: http://localhost:8000/viewer.html
- **예매 과정 로그**: http://localhost:8000/viewer_booking.html
- **공연 선택 로그**: http://localhost:8000/viewer_performance.html

> 💡 **관리자 계정**:
> - 이메일: `admin@ticket.com` / 비밀번호: `admin1234`
> - 이메일: `manager@ticket.com` / 비밀번호: `manager1234`

---

## 🎯 사용 시나리오

### 시나리오 1: 일반 사용자 예매
```
1. 회원가입 → 로그인
2. 공연 선택 (예: "아이유 콘서트")
3. 대기열 통과 (자동)
4. 좌석 선택 (35% 확률로 선점 충돌 발생)
5. 할인 선택
6. 예매자 정보 입력
7. 결제 진행
8. 예매 완료 ✅

→ 모든 과정이 logs/에 JSON으로 저장됨
```

### 시나리오 2: 관리자 오픈 시간 설정
```
1. admin@ticket.com 로그인
2. http://localhost:8000/admin.html 접속
3. 원하는 공연 카드 선택
4. 티켓 오픈 날짜/시간 설정
5. 💾 저장 버튼 클릭
6. 실시간 카운트다운 확인 ✅
```

### 시나리오 3: 로그 분석
```
1. 관리자 로그인
2. http://localhost:8000/viewer.html 접속
3. 로그 파일 선택
4. 마우스 궤적, 클릭, 호버링 데이터 시각화 확인
5. 봇 의심 패턴 분석 ✅
```

---

## 📊 로깅 시스템

### 수집되는 데이터

#### 1. 메타데이터
```json
{
  "flow_id": "unique_session_id",
  "user_email": "user@example.com",
  "performance_id": "perf001",
  "start_time": "2026-02-03T09:00:00+09:00",
  "end_time": "2026-02-03T09:05:30+09:00",
  "total_duration_ms": 330000,
  "payment_success": true
}
```

#### 2. 스테이지별 데이터
- **performance_select**: 공연 선택 단계
- **queue**: 대기열 단계
- **seat_select**: 좌석 선택 단계
- **discount**: 할인 선택 단계
- **order_info**: 예매자 정보 단계
- **payment**: 결제 단계

각 스테이지마다:
- 마우스 궤적 (정규화된 좌표)
- 클릭 이벤트 (좌표, 시간, 대상)
- 입력 이벤트 (타이핑 vs 붙여넣기)
- 체류 시간
- 뷰포트 크기

#### 3. 좌석 호버링 데이터
```json
{
  "A-1": {
    "hover_count": 5,
    "total_hover_time_ms": 2500,
    "tremor_variance": 12.5
  }
}
```

### 로그 파일 형식
```
logs/[날짜]_[공연ID]_[flow_id]_[성공여부].json

예시:
logs/20260203_perf001_flow_abc123_success.json
logs/20260203_perf002_flow_xyz789_fail.json
```

---

## 🛠️ 기술 스택

### Backend
- **FastAPI**: 고성능 Python 웹 프레임워크
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증

### Frontend
- **HTML5**: 시맨틱 마크업
- **CSS3**: 모던 스타일링 (Flexbox, Grid, Animations)
- **Vanilla JavaScript**: 프레임워크 없이 순수 JS
- **Canvas API**: 마우스 궤적 시각화

### Data Storage
- **JSON 파일 기반**: 간단하고 실용적인 저장소
  - `data/users.json`: 사용자 정보
  - `data/performances.json`: 공연 정보
  - `logs/*.json`: 행동 로그

---

## 🎨 UI/UX 특징

### 디자인 철학
- **실제 예매 사이트와 유사**: 인터파크, 예스24 스타일
- **모던하고 깔끔한 인터페이스**: 그라데이션, 그림자 효과
- **반응형 디자인**: 모바일, 태블릿, 데스크톱 지원
- **마이크로 인터랙션**: 호버 효과, 애니메이션

### 색상 팔레트
- **Primary**: #667eea (보라)
- **Secondary**: #764ba2 (진보라)
- **Success**: #10b981 (그린)
- **Warning**: #f59e0b (오렌지)
- **Danger**: #ef4444 (레드)

---

## 🔐 보안 및 권한

### 인증 시스템
- **세션 기반**: `localStorage`에 사용자 정보 저장
- **관리자 권한**: 이메일 기반 검증
  - `admin@ticket.com`
  - `manager@ticket.com`

### 관리자 페이지 보호
- 클라이언트 측 권한 체크 (`js/auth.js`)
- 비인가 접근 시 자동 리디렉션

> ⚠️ **주의**: 현재 구현은 개발/데모 용도입니다.  
> 프로덕션 환경에서는 다음이 필요합니다:
> - 서버 측 권한 검증
> - JWT 토큰 기반 인증
> - 비밀번호 해시화 (bcrypt)
> - HTTPS 사용

---

## 📈 로드맵 (향후 개발)

### Phase 1 (완료 ✅)
- [x] 기본 예매 플로우
- [x] 로깅 시스템
- [x] 로그 뷰어
- [x] 관리자 대시보드
- [x] 티켓 오픈 시간 관리

### Phase 2 (예정)
- [ ] 자동 오픈 시간 상태 변경
- [ ] 실시간 좌석 점유 시뮬레이션
- [ ] 대시보드에서 신규 공연 추가 UI
- [ ] 봇 탐지 알고리즘 고도화
- [ ] 통계 대시보드 (일별 예매 현황 등)

### Phase 3 (검토 중)
- [ ] 데이터베이스 연동 (PostgreSQL)
- [ ] 실시간 WebSocket 통신
- [ ] 머신러닝 기반 봇 분류
- [ ] A/B 테스트 기능
- [ ] 다국어 지원

---

## 📖 문서

- **[ACCESS_LINKS.md](ACCESS_LINKS.md)**: 모든 접속 링크 모음
- **[ADMIN_ACCESS_GUIDE.md](ADMIN_ACCESS_GUIDE.md)**: 관리자 페이지 가이드
- **[TICKET_OPEN_TIME_GUIDE.md](TICKET_OPEN_TIME_GUIDE.md)**: 오픈 시간 관리 매뉴얼
- **[CHANGELOG_2026-01-30.md](CHANGELOG_2026-01-30.md)**: 변경 로그

---

## 🐛 문제 해결

### 포트 충돌 (Port 8000 already in use)
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID [프로세스ID] /F

# 서버 재시작
python main.py
```

### 로그 파일이 생성되지 않음
- 브라우저 콘솔(F12) 확인
- `logs/` 디렉토리 권한 확인
- 네트워크 탭에서 API 응답 확인

### 관리자 페이지 접근 불가
- 관리자 계정으로 로그인 했는지 확인
- 브라우저 캐시 삭제 (Ctrl + Shift + Delete)
- `ADMIN_ACCESS_GUIDE.md` 참조

---

## 🤝 기여

이 프로젝트는 **AI 교육 프로그램의 팀 프로젝트**입니다.

### 팀 정보
- **팀명**: bbstation09/ai01-3rd-3team
- **프로젝트 기간**: 2026년 1월 ~ 2월

---

## 📝 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.

---

## 📞 연락처

문제가 발생하거나 질문이 있으시면:
1. 브라우저 콘솔 로그 확인
2. 서버 로그 확인
3. 관련 문서 참조

---

**Last Updated**: 2026-02-03  
**Version**: 1.1.0  
**Status**: Active Development 🚀
