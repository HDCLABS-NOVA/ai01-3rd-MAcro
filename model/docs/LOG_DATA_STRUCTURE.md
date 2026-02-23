# Browser/Server 로그 데이터 구조 설명

이 문서는 현재 코드(`main.py`)와 실제 저장 샘플을 기준으로 `browser` 로그와 `server` 로그의 구조를 설명합니다.

## 1) 저장 위치 및 파일명 규칙

### Browser 로그
- 저장 경로: `model/data/raw/browser/<bot_type>/`
- 파일명: `YYYYMMDD_<performance_id>_<flow_id>_<payment_status>.json`
- 예시: `20260215_perf002_flow_20260215_ao62r9_success.json`
- 저장 단위: **예매 1건(플로우 1개)**

### Server 로그
- 저장 경로: `model/data/raw/server/<bot_type>/`
- 파일명: `YYYYMMDD_req_<uuid>.json`
- 예시: `20260215_req_15bb99f0606b4a1eb83ff25b34fbc584.json`
- 저장 단위: 현재 기준 **`/api/*` 요청 1건당 1개**

## 2) Browser 로그 구조

Browser 로그는 프론트엔드 상호작용(마우스, 클릭, 단계 전환, 예매 결과)을 담는 **행동 중심 로그**입니다.

최상위 키:
- `metadata`
- `stages`

### `metadata`
주요 필드:
- 식별/조인: `flow_id`, `session_id`, `performance_id`
- 상태: `is_completed`, `completion_status`, `booking_id`
- 결과: `selected_date`, `selected_time`, `final_seats`, `seat_grades`
- 시간: `created_at`, `flow_start_time`, `flow_end_time`, `total_duration_ms`
- 환경: `browser_info`

샘플에서 확인된 참고 사항:
- `bot_type`이 비어 있으면 서버 저장 시 `real_human` 폴더로 분류됩니다.
- `booker_phone`, `booker_email`, `user_email`, `user_ip`처럼 원문 값이 포함될 수 있습니다.

### `stages`
단계별 객체를 포함합니다.
- `perf`
- `queue`
- `captcha`
- `seat`
- `discount`
- `order_info`
- `payment`
- `complete`

각 단계 공통 필드(대부분):
- `entry_time`, `exit_time`, `duration_ms`
- `mouse_trajectory`
- `clicks`
- `viewport`

단계별 핵심 예시:
- `perf`: `actions`, `date_selections`, `time_selections`
- `queue`: `initial_position`, `final_position`, `wait_duration_ms`, `position_updates`
- `seat`: `selected_seats`, `seat_details`
- `payment`: `payment_type`, `completed`, `completed_time`
- `complete`: `booking_id`, `total_price`

## 3) Server 로그 구조

Server 로그는 요청/응답, IP/UA 해시, 요청 빈도 등 **네트워크/세션 중심 로그**입니다.

최상위 키:
- `metadata`
- `identity`
- `client_fingerprint`
- `request`
- `response`
- `session`
- `queue`
- `seat`
- `behavior`
- `security`
- `risk`

### 섹션별 핵심

`metadata`
- `event_id`, `request_id`
- `flow_id`, `session_id` (브라우저 로그와 조인에 중요)
- `received_epoch_ms`

`identity`
- `ip_hash`, `ip_subnet`
- `user_id_hash` (브라우저 메타의 `user_email`에서 해시될 수 있음)
- `ip_raw`는 로컬/개발환경에서는 `127.0.0.1`처럼 기록될 수 있음

`request` / `response`
- `endpoint`, `method`, `body_size_bytes`, `content_type`
- `status_code`, `latency_ms`, `response_size_bytes`

`behavior`
- 트래픽 빈도: `requests_last_1s`, `requests_last_10s`, `requests_last_60s`, `unique_endpoints_last_60s`
- 고정 슬롯: `retry_count_last_5m`, `concurrent_sessions_same_device`, `concurrent_sessions_same_ip`
- 최신 코드 반영 필드:
  - `login_attempts_last_10m`
  - `login_fail_count_last_10m`
  - `login_success_count_last_10m`
  - `login_unique_accounts_last_10m`

`risk`
- `risk_score`, `decision`, `rules_triggered`
- `realtime_report_path` (실시간 `block` 시 즉시 생성된 리포트 파일 경로)
- 현재 기본값은 `0`, `allow`, `[]`

## 4) Browser vs Server 차이 (핵심)

- Browser 로그:
  - 사용자 행동의 미시적 신호(좌표, 클릭 길이, 단계 체류시간)
  - 예매 플로우 단위 저장
- Server 로그:
  - 요청 패턴/네트워크 신호(엔드포인트, 지연, 요청 밀도)
  - API 요청 단위 관측 후 `/api/*` 전 구간 파일 저장

즉, Browser는 "어떻게 행동했는가", Server는 "어떤 요청 패턴이었는가"를 설명합니다.

## 5) 조인(연결) 기준

권장 조인 키 우선순위:
1. `flow_id`
2. `session_id`
3. 시간 근접(`metadata.received_epoch_ms` vs 브라우저 `flow_end_time`)

실무적으로는 `flow_id`를 가장 안정적인 기본 키로 사용합니다.

## 6) 템플릿 스키마 파일과의 관계

- 브라우저 템플릿: `model/schemas/browser.schema.json`
- 서버 템플릿: `model/schemas/server.schema.json`

주의:
- 템플릿은 확장 가능한 "목표 스키마"이고,
- 실제 저장 로그는 운영 코드/프론트 구현에 따라 일부 필드만 채워질 수 있습니다.
- 따라서 모델링 시에는 "필드 존재 여부 체크 + 결측 처리"가 필요합니다.
