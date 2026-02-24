# 변경 로그 - 2026년 2월 13일 ~ 2월 15일

## 📊 로그 뷰어 대규모 개선

### 1️⃣ 좌표 정규화 버그 수정
**파일**: `viewer.html`

#### 문제
- 로그 파일의 viewport 데이터가 `viewport.w` / `viewport.h` 형식으로 저장됨
- viewer.html은 `viewport_width` / `viewport_height` 키를 찾아 기본값 1920x1080으로 폴백
- 실제 viewport가 2466x1328인 경우, 궤적은 `1920`으로 나누고 클릭은 정규화 좌표(`nx`)를 직접 사용
- **결과**: 핑크 점(클릭)과 파란선(궤적)이 어긋남

#### 수정
```javascript
// 변경 전
const srcWidth = stageData.viewport_width || 1920;
const srcHeight = stageData.viewport_height || 1080;

// 변경 후 - 두 가지 형식 모두 지원
const srcWidth = stageData.viewport_width || (stageData.viewport && stageData.viewport.w) || 1920;
const srcHeight = stageData.viewport_height || (stageData.viewport && stageData.viewport.h) || 1080;
```

---

### 2️⃣ 상위 네비게이션 추가 (로그뷰어 / 매크로 탐지 분석 리포트)
**파일**: `viewer.html`

#### 변경사항
- admin 대시보드 스타일의 상위 헤더 네비게이션 추가
- **📊 로그뷰어** / **📋 매크로 탐지 분석 리포트** 두 섹션으로 분리
- 🏠 메인으로 버튼 추가

#### 구조
```
┌───────────────────────────────────────────┐
│  📊 로그 분석 시스템                        │
│  [📊 로그뷰어]  [📋 매크로 탐지 분석 리포트]  [🏠 메인] │
└───────────────────────────────────────────┘
```

#### 리포트 섹션
- 현재 플레이스홀더 상태
- 봇 의심자 분류 기준 확정 후 내용 추가 예정

---

### 3️⃣ 검색 기능 추가
**파일**: `viewer.html`

#### 검색 조건
| 필터 | 검색 대상 |
|:---|:---|
| 전체 | 아이디, 예매번호, 예매자 정보, flow_id |
| 아이디 | `metadata.user_email` |
| 예매번호 | `metadata.booking_id` |
| 예매자명 | `metadata.booker_email`, `metadata.booker_phone` |

#### 동작
- 입력 시 실시간 필터링 (oninput)
- 공연창/예매창 두 탭 동시 필터링
- 검색 결과 건수 표시: `🔍 "검색어" 검색 결과: 공연창 N건, 예매창 N건`

---

### 4️⃣ 로그 목록 정보 확장
**파일**: `viewer.html`

#### 공연창 로그 항목
- **추가**: 아이디 필드 표시

#### 예매창 로그 항목
- **추가**: 아이디, 예매번호 필드 표시

---

### 5️⃣ JavaScript 오류 수정
**파일**: `viewer.html`

#### 수정 내역
- `const hovers` 재할당 오류 → `tempHovers` 사용 패턴으로 변경
- `const startTime/endTime` 재할당 오류 → `let` 선언으로 변경
- `analyzeBotBehavior` 함수 try-catch 에러 핸들링 추가
- 화면 하단 JS 에러 콘솔 추가 (디버깅용)

---

### 6️⃣ 관리자 대시보드 활성화
**파일**: `admin.html`, `js/auth.js`

#### 변경사항
- `admin.html`: `js/utils.js`, `js/auth.js` 스크립트 연결 및 관리자 권한 체크 추가
- `js/auth.js`: 관리자용 ⚙️ 관리자 대시보드 바로가기 버튼 추가

---

## 📋 수정된 파일 목록

| 파일 | 변경 내용 |
|:---|:---|
| `viewer.html` | 좌표 버그 수정, 상위 네비게이션, 검색, JS 오류 수정 |
| `admin.html` | 스크립트 연결 및 권한 체크 |
| `js/auth.js` | 관리자 버튼 추가 |

---

## ✅ 테스트 체크리스트

- [x] 클릭(핑크 점)과 궤적(파란선)이 정확히 겹침
- [x] 로그뷰어 ↔ 리포트 섹션 전환
- [x] 검색 필터링 (아이디/예매번호/예매자명)
- [x] 검색 결과 실시간 업데이트
- [x] 관리자 대시보드 접근 가능
- [x] JavaScript 오류 없음

---

**작성일**: 2026년 2월 15일
**브랜치**: `issue-GB`
**커밋**: `6c40fd5`, `773477c`
