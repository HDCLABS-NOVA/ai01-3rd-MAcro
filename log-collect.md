# Log Collect: 웹 기반 고정밀 사용자 행동 분석 시스템
(Web-based High-Precision User Behavior Analysis System)

## 📌 개요
**Log Collect**는 티켓 예매 과정에서 발생하는 사용자의 모든 상호작용(Interaction)을 정밀하게 수집하고 분석하는 시스템입니다. 단순한 클릭 로그를 넘어, 마우스 궤적(Trajectory), 체류 시간, 미세 떨림(Micro-tremor) 등의 행동 데이터를 수집하여 **사용자 경험(UX) 최적화** 및 **비정상 행위(Bot) 탐지**에 활용합니다.

---

## 🚀 핵심 기능 (Key Features)

### 1. 고정밀 실시간 마우스 트래킹 (High-Resolution Mouse Tracking)
- **50ms 단위 좌표 수집:** 사용자의 마우스 움직임을 0.05초 간격으로 샘플링하여 부드러운 궤적 데이터 확보
- **제로 디펜던시(Zero Dependency):** 외부 라이브러리 없이 순수 JavaScript(Vanilla JS)로 구현된 경량화 로깅 모듈
- **데이터 무결성 보장:** 네트워크 불안정 상황을 대비한 `SessionStorage` 기반의 데이터 캐싱 및 자동 재전송 메커니즘

### 2. 사용자 여정 리플레이 (Customer Journey Replay)
- **Canvas API 기반 시각화:** 수집된 대량의 좌표 데이터를 HTML5 Canvas를 통해 끊김 없이 시각화
- **단계별 행동 분석:** 좌석 선택 → 할인 적용 → 결제까지 이어지는 전 과정을 단계별로 재생 및 분석
- **히트맵(Heatmap) 효과:** 클릭 빈도가 높거나 체류 시간이 긴 영역을 시각적으로 강조

### 3. 마이크로 인터랙션 분석 (Micro-interaction & Tremor Analysis)
- **미세 떨림(Tremor) 감지:** 호버링(Hover) 구간의 마우스 좌표 분산을 10배 확대하여 분석
- **봇(Bot) vs 휴먼(Human) 식별:** 기계적인 직선 움직임과 인간의 자연스러운 떨림 패턴을 비교 분석하여 비정상 접근 탐지
- **고민 구간(Hesitation) 추적:** 사용자가 결정을 망설이는 구간을 식별하여 UI/UX 개선 포인트 도출

---

## 🛠 기술 스택 (Tech Stack)

### Client Side
- **Language:** HTML5, CSS3, JavaScript (ES6+)
- **Core Logic:** `logger.js` (자체 제작 로깅 모듈)
- **Visualization:** HTML5 Canvas API

### Server Side
- **Framework:** Python FastAPI
- **Storage:** JSON File System (NoSQL 구조)
- **API:** RESTful API (`/api/logs`, `/api/performances`)

---

## 📊 기대 효과
1. **보안 강화:** 매크로 및 봇(Bot)을 통한 부정 예매 시도 사전 탐지 및 차단
2. **UX 개선:** 사용자의 이탈 구간과 행동 패턴을 분석하여 예매 프로세스 최적화
3. **데이터 기반 의사결정:** 직관적인 시각화 도구를 통해 기획자 및 마케터에게 인사이트 제공
