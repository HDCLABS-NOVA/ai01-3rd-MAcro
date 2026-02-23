# Browser / Server Full Log 구조 문서

본 문서는 **현재 코드 기준으로 실제 수집/저장되는 로그 구조**를 정리한 문서입니다.
- 기준 코드: `js/logger.js`, `js/log_collect.js`, `js/performance_detail.js`, `js/queue.js`, `js/seat_select.js`, `main.py`
- 기준 저장 경로: `model/data/raw/browser/**`, `model/data/raw/server/**`

## 1. 로그 저장 위치와 파일명 규칙

### 1-1. 브라우저 로그
- 저장 API: `POST /api/logs`
- 저장 루트: `model/data/raw/browser/<bot_type>/`
- split 형식 bot_type(`train/human`, `validation/macro` 등)인 경우: `model/data/raw/<split>/<label>/`
- 파일명 형식:
  - `{YYYYMMDD}_{performance_id}_{flow_id}_{payment_status}.json`
  - 예시: `20260223_perf004_flow_20260223_cg5dsh_success.json`
- `payment_status` 결정:
  - `success`, `abandoned`, `failed`

### 1-2. 서버 로그
- 저장 대상: 미들웨어에서 **모든 `/api/*` 요청**
- 저장 루트: `model/data/raw/server/<bot_type>/`
- 파일명 형식:
  - `{YYYYMMDD}_{performance_id}_{flow_id}_{endpoint}_{method}_{request_id}.json`
  - endpoint는 `/api/queue/enter` -> `_api_queue_enter` 형태로 정규화
- 예시:
  - `20260221_perf001_flow_20260221_0a5ddp__api_queue_enter_post_req_d60799293b544d2997869a14700c59ad.json`

## 2. 브라우저 로그 구조 (의미 중심)

브라우저 로그는 2개 최상위 객체를 가집니다.
- `metadata`: 세션/사용자/환경/결과 메타
- `stages`: 단계별 행동 로그

### 2-1. `metadata`
- `flow_id`: 예매 플로우 식별자
- `session_id`: 세션 식별자
- `bot_type`: bot 라벨(없으면 빈 문자열)
- `user_email`: 사용자 이메일
- `user_ip`: 클라이언트 IP(수집 시점 기준)
- `performance_id`, `performance_title`: 공연 식별/이름
- `created_at`, `flow_start_time`, `flow_end_time`: 시간 정보(ISO 문자열)
- `browser_info`:
  - `userAgent`, `platform`, `language`, `webdriver`, `hardwareConcurrency`, `screen(w,h,ratio)`
- `total_duration_ms`: 전체 소요 시간
- `is_completed`: 완료 여부
- `completion_status`: `in_progress` / `success` / `failed` / `abandoned`
- `booking_id`: 예매 번호
- 단계에서 채워지는 선택/결과 메타(옵션):
  - `selected_date`, `selected_time`
  - `final_seats`
  - `seat_grades` (`seat`, `grade`, `price`)
  - `booker_phone`, `booker_email`
  - `booking_flow_started`

### 2-2. `stages` 공통 구조
각 stage는 공통적으로 다음 필드를 가질 수 있습니다.
- `entry_time`, `exit_time`, `duration_ms`
- `mouse_trajectory`: `[[x, y, relative_ms, nx, ny], ...]`
- `clicks`: `[{x,y,nx,ny,timestamp,is_trusted,duration,button,target?}, ...]`
- `viewport` 또는 `viewport_width`/`viewport_height` (수집기 버전에 따라 다름)

### 2-3. stage별 추가 필드
- `perf`:
  - `card_clicks[]`, `date_selections[]`, `time_selections[]`, `actions[]`
- `queue`:
  - `initial_position`, `final_position`, `total_queue`, `wait_duration_ms`
  - `queue_entry_trigger`, `request_polling_interval_ms_stats(min,p50,p95)`
  - `queue_jump_count`, `position_updates[]`
- `captcha`:
  - `status` (예: `verified`)
- `seat`:
  - `selected_seats[]`, `seat_details[]`
  - (logger 경로에서) `hovers[]` 가능
- `discount`:
  - `selected_discount`
- `order_info`:
  - `delivery_type`, `has_phone`, `has_email`
- `payment`:
  - `payment_type`, `completed`, `completed_time`
- `complete`:
  - `booking_id`, `total_price`, `completion_time`

## 3. 서버 로그 구조 (의미 중심)

서버 로그는 요청 단위로 저장되며 다음 최상위 객체를 가집니다.
- `metadata`, `identity`, `client_fingerprint`
- `request`, `response`
- `session`, `queue`, `seat`, `behavior`, `security`, `risk`

### 3-1. `metadata`
- `event_id`, `request_id`
- `flow_id`, `session_id`
- `received_epoch_ms`
- `server_region`, `environment`

### 3-2. `identity`
- `user_id_hash`, `account_id_hash`, `device_id_hash`, `session_fingerprint_hash`
- `ip_hash`, `ip_raw`, `ip_subnet`
- `asn`, `geo(country, region, city)`

### 3-3. `client_fingerprint`
- `user_agent_hash`, `tls_fingerprint`, `accept_language`, `timezone_offset_min`
- `screen(w,h,ratio)`

### 3-4. `request` / `response`
- request:
  - `endpoint`, `route`, `method`
  - `query_size_bytes`, `body_size_bytes`, `content_type`
  - `headers_whitelist(referer, origin, x_forwarded_for, sec_ch_ua)`
- response:
  - `status_code`, `latency_ms`, `response_size_bytes`
  - `error_code`, `retry_after_ms`

### 3-5. `session`
- `session_created_epoch_ms`, `last_activity_epoch_ms`, `session_age_ms`
- `login_state`, `account_age_days`, `payment_token_hash`

### 3-6. `queue`
- `queue_id`, `join_epoch_ms`, `enter_trigger`, `position`
- `poll_interval_ms_stats(min,p50,p95)`
- `jump_count`

### 3-7. `seat`
- `seat_query_count`, `reserve_attempt_count`, `reserve_fail_codes[]`
- `seat_hold_ms`, `seat_release_ms`

### 3-8. `behavior`
- 요청량: `requests_last_1s`, `requests_last_10s`, `requests_last_60s`
- 다양도: `unique_endpoints_last_60s`
- 로그인 통계: `login_attempts_last_10m`, `login_fail_count_last_10m`, `login_success_count_last_10m`, `login_unique_accounts_last_10m`
- 기타: `retry_count_last_5m`, `concurrent_sessions_same_device`, `concurrent_sessions_same_ip`

### 3-9. `security`
- `captcha_required`, `captcha_passed`, `rate_limited`
- `blocked`, `block_reason`
- block 시점에는 `block_message`가 동적으로 추가될 수 있음

### 3-10. `risk`
- 점수/판정:
  - `risk_score`, `decision(allow|challenge|block)`
- 룰/모델 근거:
  - `rules_triggered[]`, `soft_rules_triggered[]`, `hard_rules_triggered[]`
  - `hard_action`, `rule_score`, `model_score`, `model_type`, `model_ready`, `model_skipped`
- 운영 파라미터:
  - `threshold_allow`, `threshold_challenge`, `review_required`, `block_recommended`
- 런타임 상태:
  - `runtime_error`
  - block 시점에는 `alert_message`, `realtime_report_path`, `realtime_report_error`가 추가될 수 있음

## 4. 실시간 차단/리포트 관련 추가 저장

- 실시간 `block` 발생 시:
  - 서버 로그 `risk.realtime_report_path`에 리포트 경로 기록
  - `model/block_report/`에 리포트 저장
- LLM 리포트 파일:
  - TXT: `{YYYYMMDD}_{booking_id}_llm.txt` (주 저장 경로)
  - JSON: `{YYYYMMDD}_{booking_id}_llm.json` (호환용)

## 4-1. 브라우저 로그 수집 시점 상세

브라우저 로그는 페이지 이동과 사용자 행동 이벤트를 기준으로 채워집니다.

- 초기화:
  - `initLogger()` 또는 `initLogCollector()` 실행 시 `metadata` 기본값 생성
  - 이때 `flow_id`, `session_id`, `created_at`, `browser_info`가 설정됨
- 단계 진입:
  - `recordStageEntry(stage)`에서 `stages.<stage>.entry_time` 생성
  - 마우스 궤적 버퍼(`mouse_trajectory`) 초기화
- 행동 수집:
  - `pointermove` 샘플링으로 `mouse_trajectory` 누적
  - `pointerdown/pointerup` 또는 클릭 이벤트로 `clicks[]` 누적
  - seat 페이지에서는 `trackHover()` 호출 시 `hovers[]`가 추가될 수 있음
- 단계 종료:
  - `recordStageExit(stage, extra)`에서 `exit_time`, `duration_ms`, `mouse_trajectory` 확정
  - `extra`로 단계별 세부 필드(`selected_seats`, `position_updates` 등) 병합
- 최종 업로드:
  - `uploadLog()` / `finalizeLog()`에서 `flow_end_time`, `total_duration_ms`, `completion_status`, `booking_id`를 마감 후 `POST /api/logs`

## 4-2. 브라우저 stage별 실제 생성 주체

- `perf`:
  - 생성: `js/performance_detail.js`
  - `selected_date`, `selected_time`는 metadata로 반영
  - `card_clicks`, `date_selections`, `time_selections`, `actions`를 `recordStageExit('perf', ...)`로 저장
- `queue`:
  - 생성: `js/queue.js`
  - 대기열 API 결과를 기반으로 `initial_position`, `final_position`, `queue_jump_count`, `position_updates`, `request_polling_interval_ms_stats` 기록
- `captcha` + `seat`:
  - 생성: `js/seat_select.js`
  - 캡차 검증 성공 시 `captcha.status='verified'`로 stage 종료
  - 좌석 선택 완료 시 `selected_seats`, `seat_details` 저장
  - `final_seats`, `seat_grades`는 metadata에도 반영
- `discount`:
  - 생성: `js/discount.js`
  - `selected_discount` 저장
- `order_info`:
  - 생성: `js/order_info.js`
  - `delivery_type`, `has_phone`, `has_email`
  - `booker_phone`, `booker_email`는 metadata에 반영
- `payment`:
  - 생성: `js/payment.js`
  - `payment_type`, `completed`, `completed_time` 저장
- `complete`:
  - 생성: `js/booking_complete.js`
  - `booking_id`, `total_price`, `completion_time` 저장 후 업로드 트리거

## 4-3. 서버 로그 수집 시점 상세

서버 로그는 `main.py` 미들웨어에서 `/api/*` 요청마다 생성됩니다.

- 요청 전처리:
  - 본문이 JSON이면 파싱하여 `flow_id`, `session_id`, `performance_id`, `user_email`, `bot_type` 추출 시도
  - `/api/logs` 본문은 `browser_payload`로 보관됨
- 응답 후 생성:
  - `call_next(request)` 이후 `server_log` 객체 구성
  - `request`, `response`, `behavior`, `queue snapshot` 등을 계산해 채움
- 리스크 평가:
  - `_score_request_risk(browser_payload, server_log)` 호출
  - 결과를 `risk.*`에 상세 저장 (`rule_score`, `model_score`, `threshold_*` 포함)
- block/challenge 반영:
  - `decision == block`이면 `security.blocked=true`, `block_reason`, `block_message` 설정
  - `decision == challenge`이면 `security.captcha_required=true`
- 저장:
  - 최종 `server_log`를 파일로 저장
  - block이면 LLM 리포트 생성 함수 실행 후 `risk.realtime_report_path` 등 추가 가능

## 4-4. 실시간 판정 응답 흐름(현재 구현 기준)

실시간으로 응답이 바뀌는 엔드포인트는 아래와 같습니다.

- `POST /api/booking/start-token`
- `POST /api/queue/join`
- `GET /api/queue/status`
- `POST /api/queue/enter`
- `POST /api/logs`

응답 규칙:

- `risk.decision == block`:
  - HTTP `403`
  - 본문: `decision='block'`, `message`, `risk`
- `risk.decision == challenge`:
  - HTTP `202`
  - 본문: `decision='challenge'`, `challenge_required=true`, `risk`
- 그 외:
  - 원래 API 응답 유지

프론트 처리:

- `/api/logs`, `/api/booking/start-token`, `/api/queue/*` 호출 결과가 `403 + decision=block`이면
  - 팝업 문구: `비정상적인 접근으로 일시적으로 서비스 접속이 제한되었습니다.`

## 4-5. 동적/옵션 필드 정리

상황에 따라만 생기는 필드는 아래와 같습니다.

- 브라우저 로그:
  - `stages.<stage>.hovers[]` (hover 추적이 실제 호출된 경우)
  - metadata의 일부 비즈니스 필드 (`booker_phone`, `seat_grades`, `delivery_address` 등)는 사용자 흐름에 따라 존재
- 서버 로그:
  - `security.block_message` (block일 때)
  - `risk.alert_message` (block일 때)
  - `risk.realtime_report_path`, `risk.realtime_report_error` (리포트 생성 시)

## 4-6. 해석할 때 자주 헷갈리는 포인트

- `flow_id` 기준:
  - 브라우저 로그는 예매 플로우 단위(1개 파일)
  - 서버 로그는 요청 단위(다수 파일)
  - 분석 시 `flow_id`로 조인
- `completion_status`:
  - 브라우저 로그 최종 상태
  - `success`가 아니면 결제 완료 플로우가 아님
- `risk_score`:
  - 서버 요청 단위 점수
  - 동일 flow라도 API마다 값이 다를 수 있음
- `decision`:
  - `allow/challenge/block`은 각 서버 요청에서 독립적으로 계산됨
  - 실시간 정책이 켜진 엔드포인트에서만 즉시 403/202로 강제 반영됨

## 4-7. 운영 점검 체크리스트

로그 품질 점검 시 최소 확인 항목:

- 브라우저:
  - `metadata.flow_id`, `session_id`, `performance_id`, `completion_status` 존재 여부
  - `stages.perf/queue/captcha/seat`의 `entry_time`/`exit_time` 정합성
  - `clicks[].timestamp` 증가 여부, `mouse_trajectory` 길이
- 서버:
  - 요청별 `metadata.request_id` 고유성
  - `request.endpoint`와 파일명의 endpoint 일치성
  - `risk.model_ready=true` 여부, `runtime_error` 비어있는지
  - block 케이스에서 `security.blocked=true`, `risk.realtime_report_path` 생성 여부

---

## 5. 브라우저 로그 전 필드 경로 (실파일 기준 자동 추출)

| Field Path | Type | 의미(설명) |
|---|---|---|
| `$` | object | 브라우저 로그 전체 루트 객체 |
| `metadata` | object | 예매 플로우 메타데이터 묶음 |
| `metadata.booking_flow_started` | boolean | 예매 플로우 시작 플래그 |
| `metadata.booking_id` | string | 최종 예매 번호 |
| `metadata.bot_type` | string | 로그 라벨/봇 타입(저장 폴더 분기에 사용) |
| `metadata.browser_info` | object | 브라우저/기기 환경 정보 |
| `metadata.browser_info.hardwareConcurrency` | number | 논리 CPU 코어 수 |
| `metadata.browser_info.language` | string | 브라우저 언어 |
| `metadata.browser_info.platform` | string | 플랫폼 문자열(예: Win32) |
| `metadata.browser_info.screen` | object | 화면 해상도/비율 정보 |
| `metadata.browser_info.screen.h` | number | 화면 높이(px) |
| `metadata.browser_info.screen.ratio` | number | devicePixelRatio |
| `metadata.browser_info.screen.w` | number | 화면 너비(px) |
| `metadata.browser_info.userAgent` | string | User-Agent 원문 |
| `metadata.browser_info.webdriver` | boolean | 자동화(WebDriver) 탐지 플래그 |
| `metadata.completion_status` | string | 완료 상태(success/failed/abandoned 등) |
| `metadata.created_at` | string | 로그 객체 생성 시각(ISO) |
| `metadata.flow_end_time` | string | 예매 플로우 종료 시각(ISO) |
| `metadata.flow_id` | string | 예매 플로우 식별자(브라우저-서버 조인 키) |
| `metadata.flow_start_time` | string | 예매 플로우 시작 시각(ISO) |
| `metadata.is_completed` | boolean | 플로우 완료 여부 |
| `metadata.performance_id` | string | 공연 ID |
| `metadata.performance_title` | string | 공연명 |
| `metadata.session_id` | string | 브라우저 세션 식별자 |
| `metadata.total_duration_ms` | number | 플로우 전체 소요 시간(ms) |
| `metadata.user_email` | string | 사용자 이메일(해당 세션 주체) |
| `stages` | object | 단계별 행동 로그 묶음 |
| `stages.captcha` | object | 캡차 단계 객체 |
| `stages.captcha.clicks` | array | 캡차 단계 클릭 이벤트 배열 |
| `stages.captcha.clicks[]` | object | 캡차 단계 클릭 이벤트 객체 |
| `stages.captcha.clicks[].button` | number | 캡차 마우스 버튼 코드(0=좌클릭 등) |
| `stages.captcha.clicks[].duration` | number | 캡차 클릭 지속시간(ms, down-up) |
| `stages.captcha.clicks[].is_trusted` | boolean | 캡차 사용자 직접 입력 여부(isTrusted) |
| `stages.captcha.clicks[].nx` | number | 캡차 클릭 X 정규화 좌표(0~1) |
| `stages.captcha.clicks[].ny` | number | 캡차 클릭 Y 정규화 좌표(0~1) |
| `stages.captcha.clicks[].target` | string | 캡차 클릭 대상 식별자 |
| `stages.captcha.clicks[].timestamp` | number | 캡차 진입 후 상대 클릭 시각(ms) |
| `stages.captcha.clicks[].x` | number | 캡차 클릭 X 좌표(px) |
| `stages.captcha.clicks[].y` | number | 캡차 클릭 Y 좌표(px) |
| `stages.captcha.duration_ms` | number | 캡차 단계 체류 시간(ms) |
| `stages.captcha.entry_time` | string | 캡차 단계 진입 시각 |
| `stages.captcha.exit_time` | string | 캡차 단계 종료 시각 |
| `stages.captcha.mouse_trajectory` | array | 캡차 단계 마우스 궤적 배열 |
| `stages.captcha.mouse_trajectory[]` | array | 캡차 단계 마우스 궤적 포인트(배열형) |
| `stages.captcha.mouse_trajectory[][]` | number | 캡차 궤적 원소 값(x/y/상대시각/nx/ny 중 하나) |
| `stages.captcha.status` | string | 캡차 검증 결과 상태 |
| `stages.perf` | object | 공연 상세 단계 객체 |
| `stages.perf.actions` | array | 공연 상세 단계 사용자 액션 배열(card_click/date_select/time_select 등) |
| `stages.perf.actions[]` | string | 공연 상세 단계 액션 문자열 항목 |
| `stages.perf.clicks` | array | 공연 상세 단계 클릭 이벤트 배열 |
| `stages.perf.clicks[]` | object | 공연 상세 단계 클릭 이벤트 객체 |
| `stages.perf.clicks[].button` | number | 공연 상세 마우스 버튼 코드(0=좌클릭 등) |
| `stages.perf.clicks[].duration` | number | 공연 상세 클릭 지속시간(ms, down-up) |
| `stages.perf.clicks[].is_trusted` | boolean | 공연 상세 사용자 직접 입력 여부(isTrusted) |
| `stages.perf.clicks[].nx` | number | 공연 상세 클릭 X 정규화 좌표(0~1) |
| `stages.perf.clicks[].ny` | number | 공연 상세 클릭 Y 정규화 좌표(0~1) |
| `stages.perf.clicks[].target` | string | 공연 상세 클릭 대상 식별자 |
| `stages.perf.clicks[].timestamp` | number | 공연 상세 진입 후 상대 클릭 시각(ms) |
| `stages.perf.clicks[].x` | number | 공연 상세 클릭 X 좌표(px) |
| `stages.perf.clicks[].y` | number | 공연 상세 클릭 Y 좌표(px) |
| `stages.perf.duration_ms` | number | 공연 상세 단계 체류 시간(ms) |
| `stages.perf.entry_time` | string | 공연 상세 단계 진입 시각 |
| `stages.perf.exit_time` | string | 공연 상세 단계 종료 시각 |
| `stages.perf.mouse_trajectory` | array | 공연 상세 단계 마우스 궤적 배열 |
| `stages.perf.mouse_trajectory[]` | array | 공연 상세 단계 마우스 궤적 포인트(배열형) |
| `stages.perf.mouse_trajectory[][]` | number | 공연 상세 궤적 원소 값(x/y/상대시각/nx/ny 중 하나) |
| `stages.queue` | object | 대기열 단계 객체 |
| `stages.queue.clicks` | array | 대기열 단계 클릭 이벤트 배열 |
| `stages.queue.duration_ms` | number | 대기열 단계 체류 시간(ms) |
| `stages.queue.entry_time` | string | 대기열 단계 진입 시각 |
| `stages.queue.exit_time` | string | 대기열 단계 종료 시각 |
| `stages.queue.final_position` | number | 대기열 종료 시 순번(보통 0) |
| `stages.queue.initial_position` | number | 대기열 진입 시 초기 순번 |
| `stages.queue.mouse_trajectory` | array | 대기열 단계 마우스 궤적 배열 |
| `stages.queue.position_updates` | array | 대기열 위치 업데이트 이력 배열 |
| `stages.queue.position_updates[]` | object | 대기열 위치 업데이트 항목 객체 |
| `stages.queue.position_updates[].pos` | number | 업데이트 시점의 순번 |
| `stages.queue.position_updates[].t` | number | 업데이트 상대 시각/틱 |
| `stages.queue.total_queue` | number | 대기열 전체 인원 |
| `stages.seat` | object | 좌석 선택 단계 객체 |
| `stages.seat.clicks` | array | 좌석 선택 단계 클릭 이벤트 배열 |
| `stages.seat.clicks[]` | object | 좌석 선택 단계 클릭 이벤트 객체 |
| `stages.seat.clicks[].button` | number | 좌석 선택 마우스 버튼 코드(0=좌클릭 등) |
| `stages.seat.clicks[].duration` | number | 좌석 선택 클릭 지속시간(ms, down-up) |
| `stages.seat.clicks[].is_trusted` | boolean | 좌석 선택 사용자 직접 입력 여부(isTrusted) |
| `stages.seat.clicks[].nx` | number | 좌석 선택 클릭 X 정규화 좌표(0~1) |
| `stages.seat.clicks[].ny` | number | 좌석 선택 클릭 Y 정규화 좌표(0~1) |
| `stages.seat.clicks[].target` | string | 좌석 선택 클릭 대상 식별자 |
| `stages.seat.clicks[].timestamp` | number | 좌석 선택 진입 후 상대 클릭 시각(ms) |
| `stages.seat.clicks[].x` | number | 좌석 선택 클릭 X 좌표(px) |
| `stages.seat.clicks[].y` | number | 좌석 선택 클릭 Y 좌표(px) |
| `stages.seat.duration_ms` | number | 좌석 선택 단계 체류 시간(ms) |
| `stages.seat.entry_time` | string | 좌석 선택 단계 진입 시각 |
| `stages.seat.exit_time` | string | 좌석 선택 단계 종료 시각 |
| `stages.seat.mouse_trajectory` | array | 좌석 선택 단계 마우스 궤적 배열 |
| `stages.seat.mouse_trajectory[]` | array | 좌석 선택 단계 마우스 궤적 포인트(배열형) |
| `stages.seat.mouse_trajectory[][]` | number | 좌석 선택 궤적 원소 값(x/y/상대시각/nx/ny 중 하나) |
| `stages.seat.seat_details` | array | 선택 좌석 상세 정보 배열 |
| `stages.seat.seat_details[]` | object | 선택 좌석 상세 객체 |
| `stages.seat.seat_details[].grade` | string | 좌석 등급 |
| `stages.seat.seat_details[].id` | string | 좌석 ID |
| `stages.seat.seat_details[].price` | number | 좌석 가격 |
| `stages.seat.selected_seats` | array | 선택 좌석 ID 배열 |
| `stages.seat.selected_seats[]` | string | 선택 좌석 ID |

---

## 6. 서버 로그 전 필드 경로 (실파일 기준 자동 추출)

| Field Path | Type | 의미(설명) |
|---|---|---|
| `$` | object | 서버 요청 단위 로그 전체 루트 객체 |
| `behavior` | object | 요청 빈도/행동 통계 |
| `behavior.concurrent_sessions_same_device` | number | 동일 기기 동시 세션 수 |
| `behavior.concurrent_sessions_same_ip` | number | 동일 IP 동시 세션 수 |
| `behavior.login_attempts_last_10m` | number | 최근 10분 로그인 시도 수 |
| `behavior.login_fail_count_last_10m` | number | 최근 10분 로그인 실패 수 |
| `behavior.login_success_count_last_10m` | number | 최근 10분 로그인 성공 수 |
| `behavior.login_unique_accounts_last_10m` | number | 최근 10분 로그인 시도 계정 수 |
| `behavior.requests_last_10s` | number | 최근 10초 요청 수 |
| `behavior.requests_last_1s` | number | 최근 1초 요청 수 |
| `behavior.requests_last_60s` | number | 최근 60초 요청 수 |
| `behavior.retry_count_last_5m` | number | 최근 5분 재시도 수 |
| `behavior.unique_endpoints_last_60s` | number | 최근 60초 고유 endpoint 수 |
| `client_fingerprint` | object | 클라이언트 지문 정보 묶음 |
| `client_fingerprint.accept_language` | string | Accept-Language 헤더 값 |
| `client_fingerprint.screen` | object | 화면 정보 묶음(옵션) |
| `client_fingerprint.screen.h` | number | 화면 높이(px) |
| `client_fingerprint.screen.ratio` | number | 디바이스 픽셀 비율 |
| `client_fingerprint.screen.w` | number | 화면 너비(px) |
| `client_fingerprint.timezone_offset_min` | number | 타임존 오프셋(분) |
| `client_fingerprint.tls_fingerprint` | string | TLS 지문(옵션) |
| `client_fingerprint.user_agent_hash` | string | User-Agent 해시 |
| `identity` | object | 사용자/네트워크 식별 정보 묶음 |
| `identity.account_id_hash` | string | 계정 ID 해시(옵션) |
| `identity.asn` | string | ASN 정보(옵션) |
| `identity.device_id_hash` | string | 기기 ID 해시(옵션) |
| `identity.geo` | object | 지리 정보 묶음 |
| `identity.geo.city` | string | 도시 정보(옵션) |
| `identity.geo.country` | string | 국가 코드/이름(옵션) |
| `identity.geo.region` | string | 지역 정보(옵션) |
| `identity.ip_hash` | string | IP 해시 |
| `identity.ip_raw` | string | 원본 IP 문자열 |
| `identity.ip_subnet` | string | IP 대역(/24) |
| `identity.session_fingerprint_hash` | string | 세션 지문 해시(옵션) |
| `identity.user_id_hash` | string | 사용자 식별 해시(이메일 등 기반) |
| `metadata` | object | 요청 식별/수집 시점 메타데이터 |
| `metadata.environment` | string | 실행 환경(local/prod 등) |
| `metadata.event_id` | string | 이벤트 ID(서버 생성) |
| `metadata.flow_id` | string | 브라우저와 조인되는 플로우 ID |
| `metadata.received_epoch_ms` | number | 서버 수신 시각(epoch ms) |
| `metadata.request_id` | string | 요청 ID(서버 생성, 파일명에 포함) |
| `metadata.server_region` | string | 서버 리전 정보(미사용 시 빈값) |
| `metadata.session_id` | string | 세션 ID |
| `queue` | object | 대기열 상태 스냅샷 |
| `queue.enter_trigger` | string | 대기열 통과 트리거 |
| `queue.join_epoch_ms` | number | 대기열 진입 시각(epoch ms) |
| `queue.jump_count` | number | 비정상 점프 감지 카운트 |
| `queue.poll_interval_ms_stats` | object | 폴링 간격 통계 객체 |
| `queue.poll_interval_ms_stats.min` | number | 폴링 간격 최소값(ms) |
| `queue.poll_interval_ms_stats.p50` | number | 폴링 간격 중앙값(ms) |
| `queue.poll_interval_ms_stats.p95` | number | 폴링 간격 95퍼센타일(ms) |
| `queue.position` | number | 현재 순번 |
| `queue.queue_id` | string | 대기열 ID |
| `request` | object | 요청 메타데이터 |
| `request.body_size_bytes` | number | 요청 본문 크기(bytes) |
| `request.content_type` | string | 요청 Content-Type |
| `request.endpoint` | string | 요청 엔드포인트 경로 |
| `request.headers_whitelist` | object | 선별 저장 헤더 묶음 |
| `request.headers_whitelist.origin` | string | Origin 헤더 |
| `request.headers_whitelist.referer` | string | Referer 헤더 |
| `request.headers_whitelist.sec_ch_ua` | string | Sec-CH-UA 헤더 |
| `request.headers_whitelist.x_forwarded_for` | string | X-Forwarded-For 헤더 |
| `request.method` | string | HTTP 메서드 |
| `request.query_size_bytes` | number | 쿼리스트링 크기(bytes) |
| `request.route` | string | 라우팅 경로(현재 endpoint와 동일) |
| `response` | object | 응답 메타데이터 |
| `response.error_code` | string | 내부 에러 코드(옵션) |
| `response.latency_ms` | number | 요청-응답 지연(ms) |
| `response.response_size_bytes` | number | 응답 크기(bytes) |
| `response.retry_after_ms` | number | 재시도 대기(ms, 옵션) |
| `response.status_code` | number | HTTP 상태 코드 |
| `risk` | object | 리스크 스코어링 결과 |
| `risk.block_recommended` | boolean | 자동 차단 대신 권고 차단 플래그 |
| `risk.decision` | string | 판정 결과(allow/challenge/block) |
| `risk.hard_action` | string | 하드 룰 판정 결과(none/challenge/block) |
| `risk.hard_rules_triggered` | array | 트리거된 하드 룰 목록 |
| `risk.model_ready` | boolean | 모델 로딩/준비 완료 여부 |
| `risk.model_score` | number | 모델 이상치 점수(정규화) |
| `risk.model_skipped` | boolean | 모델 점수 계산 스킵 여부 |
| `risk.model_type` | string | 사용 모델 이름 |
| `risk.review_required` | boolean | 관리자 검토 필요 플래그 |
| `risk.risk_score` | number | 최종 리스크 점수(0~1) |
| `risk.rule_score` | number | 룰 기반 점수(정규화) |
| `risk.rules_triggered` | array | 트리거된 룰 목록(통합) |
| `risk.rules_triggered[]` | string | 트리거된 룰 항목 문자열 |
| `risk.runtime_error` | string | 리스크 계산 중 런타임 에러 메시지 |
| `risk.soft_rules_triggered` | array | 트리거된 소프트 룰 목록 |
| `risk.soft_rules_triggered[]` | string | 소프트 룰 항목 문자열 |
| `risk.threshold_allow` | number | allow 경계 임계값 |
| `risk.threshold_challenge` | number | challenge 경계 임계값 |
| `seat` | object | 좌석 API 관련 상태 스냅샷 |
| `seat.reserve_attempt_count` | number | 좌석 선점 시도 횟수 |
| `seat.reserve_fail_codes` | array | 좌석 선점 실패 코드 배열 |
| `seat.seat_hold_ms` | number | 좌석 홀드 시간(ms) |
| `seat.seat_query_count` | number | 좌석 조회 요청 수 |
| `seat.seat_release_ms` | number | 좌석 해제 시간(ms) |
| `security` | object | 보안 제어 상태 |
| `security.block_reason` | string | 차단 사유 코드 |
| `security.blocked` | boolean | 차단 여부 |
| `security.captcha_passed` | boolean | 추가 인증 통과 여부 |
| `security.captcha_required` | boolean | 추가 인증 필요 여부 |
| `security.rate_limited` | boolean | 속도 제한 적용 여부 |
| `session` | object | 세션/계정 컨텍스트 정보 |
| `session.account_age_days` | number | 계정 나이(일) |
| `session.last_activity_epoch_ms` | number | 마지막 활동 시각(epoch ms) |
| `session.login_state` | string | 로그인 상태(guest/member 등) |
| `session.payment_token_hash` | string | 결제 토큰 해시(옵션) |
| `session.session_age_ms` | number | 세션 경과 시간(ms) |
| `session.session_created_epoch_ms` | number | 세션 생성 시각(epoch ms, 옵션) |

---

## 6-1. 동적 필드(상황별 추가) 의미

| Field Path | Type | 의미(설명) |
|---|---|---|
| `security.block_message` | string | 실시간 block 시 사용자 응답에 사용되는 메시지 |
| `risk.alert_message` | string | 차단/경고 요약 메시지 |
| `risk.realtime_report_path` | string | 실시간 차단 리포트(JSON) 파일 경로 |
| `risk.realtime_report_error` | string | 리포트 생성 실패 시 에러 메시지 |

---

## 7. 참고
- 위 표의 경로 목록은 현재 저장된 JSON 파일들에서 자동 추출한 결과입니다.
- `Meaning` 열은 현재 코드 로직 기준으로 작성했으며, 신규 필드 추가 시 함께 갱신해야 합니다.
