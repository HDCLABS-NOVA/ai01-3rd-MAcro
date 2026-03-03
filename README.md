# Ticket Booking Bot Detection Project

티켓 예매 웹 서비스와 이상 탐지 기반 매크로 탐지 시스템을 함께 포함한 프로젝트입니다.  
브라우저 행동 로그를 수집하고, 활성 모델(One-Class SVM)로 위험 점수를 계산해 `allow / challenge / block` 정책에 연결합니다.

## 1. 주요 기능
- 예매 플로우: 공연 선택 -> 대기열 -> 좌석 선택 -> 결제 -> 완료
- 행동 로그 수집: 클릭/마우스 궤적/호버/메타데이터 수집 후 `/api/logs` 전송
- 리스크 평가: 규칙 기반 점수 + 모델 점수 결합
- 운영/관리: 관리자 공연 관리, 사용자 제한/해제, 리포트 조회, 마이페이지 예매 조회
- 분석 리포트: 차단/챌린지 이벤트에 대한 리포트 생성(옵션으로 LLM 요약)

## 2. 기술 스택
- Backend: `FastAPI`, `Uvicorn`, `Pydantic`
- Frontend: `HTML/CSS/Vanilla JS`
- ML: `scikit-learn`, `numpy`, `joblib`, `shap`, `torch(optional)`
- Storage: 파일 기반 JSON(`data/`, `model/data/raw/`, `model/*`)
- Automation: `Node.js + Puppeteer` (시뮬레이션 스크립트)

## 3. 프로젝트 구조
```text
.
├─ main.py                         # FastAPI 서버 + 미들웨어 + 리스크 런타임
├─ *.html, css/, js/               # 프론트엔드 페이지/스타일/스크립트
├─ data/                           # 사용자/제재 등 운영 데이터(JSON)
├─ model/                          # 서빙 코드, 리포트, active 아티팩트
├─ hybrid_model/                   # 학습/평가 파이프라인 및 벤치마크 결과
├─ automation/                     # Puppeteer 기반 매크로/휴먼 시뮬레이터
├─ macro/                          # 좌석 선택 보조 매크로(F2) 관련 코드
└─ docs (*.md)                     # 모델/아키텍처/API 문서
```

## 4. 빠른 시작
### 4.1 요구사항
- Python `3.11+` 권장
- Windows 환경 기준 스크립트 포함(`server.bat`)

### 4.2 설치
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4.3 실행
```bash
python main.py
```
또는
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4.4 접속
- 서비스: `http://localhost:8000`
- 관리자 뷰어: `http://localhost:8000/viewer.html`

기본 관리자 계정(개발용):
- `admin@ticket.com / admin1234`
- `manager@ticket.com / manager1234`

## 5. 활성 모델(운영 기준)
- Active 모델: `One-Class SVM`
- Active 파라미터: `model/artifacts/active/human_model_params.json`
- Active 아티팩트: `model/artifacts/active/human_model_oneclass_svm.joblib`
- 운영 판정 구간:
  - `model_score < 0.50`: `allow`
  - `0.50 <= model_score < 0.60`: `challenge`
  - `model_score >= 0.60`: `block`

추가 상세는 `model_definition.md`를 참고하세요.

## 6. 주요 API
전체 목록은 `API_SPEC_v1.md` 참고.

- Auth: `/api/auth/signup`, `/api/auth/login`
- Queue: `/api/booking/start-token`, `/api/queue/join`, `/api/queue/status`, `/api/queue/enter`
- Logs: `/api/logs` (POST/GET), `/api/logs/{filename}`
- Risk 상태: `/api/risk/runtime-status`
- Admin: `/api/admin/*` (공연/제재/취소 관리)
- MyPage: `/api/mypage/bookings/{email}`, `/api/mypage/update-delivery`
- Report: `/api/reports`, `/api/reports/{filename}`
- Macro: `/api/macro/f2`, `/api/macro/f2/status`

## 7. 주요 환경변수
`.env` 또는 시스템 환경변수로 설정합니다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `RISK_ALLOW_THRESHOLD` | `0.50` | allow/challenge 경계 override |
| `RISK_CHALLENGE_THRESHOLD` | `0.60` | challenge/block 경계 override |
| `RISK_DECISION_MODE` | `risk_weighted` | `risk_weighted` 또는 `model_threshold_fixed` |
| `RISK_MODEL_FIXED_THRESHOLD` | 없음 | fixed mode에서 모델 임계값 직접 지정 |
| `RISK_MODEL_SCORE_SCALING` | `auto` | `auto`, `minmax`, `logistic_p95` |
| `RISK_BLOCK_AUTOMATION` | `false` | 실시간 차단 강제 여부 |
| `LLM_REPORT_ENABLED` | `true` | LLM 리포트 생성 활성화 |
| `OPENAI_API_KEY` | 없음 | LLM 리포트 생성 시 필요 |
| `QUEUE_REQUIRE_START_TOKEN` | `true` | 큐 진입 시 start token 강제 여부 |
| `SEAT_F2_MACRO_ENABLED` | `true` | 좌석 F2 보조 매크로 API 활성화 |

## 8. 관련 문서
- `model_definition.md`: 활성 모델 정의서(전처리/피처/학습/검증/추론)
- `active_model.md`: active 모델 전처리/피처 요약
- `architecture.md`: 시스템 아키텍처
- `API_SPEC_v1.md`: API 명세
- `DB.md`: 데이터 저장 구조

## 9. 참고 사항
- 본 프로젝트는 파일 기반 저장 구조를 사용합니다.
- 일부 계정/비밀번호 로직은 개발 편의 중심 구현이며, 운영 환경에서는 보안 강화(해시/권한/비밀관리)가 필요합니다.
