# 로그 수집 구조 (Browser / Server)

기준 코드: `js/log_collect.js`, `js/logger.js`, `main.py`

## Browser 로그

| 유형 | 주요 항목 | 수집 목적 |
|---|---|---|
| 플로우/세션 메타 | `flow_id`, `session_id`, `performance_id`, `bot_type`, `created_at`, `flow_start_time`, `flow_end_time` | 사용자 예매 흐름을 단위 세션으로 묶어 추적하고, 브라우저 로그와 서버 로그를 연계하기 위함 |
| 사용자/환경 컨텍스트 | `user_email`, `user_ip`, `browser_info(userAgent/platform/language/webdriver/hardware/screen)` | 사용자 접속 환경과 자동화 의심 신호를 함께 확보해 행위 해석 정확도를 높이기 위함 |
| 단계 공통 행동 데이터 | `stages.<stage>.entry_time`, `exit_time`, `duration_ms`, `mouse_trajectory`, `clicks`, `viewport` | 단계별 체류 시간, 마우스/클릭 패턴을 수집해 사람/매크로 행위 차이를 분석하기 위함 |
| 단계별 업무 이벤트 | `perf`(공연/회차 선택), `queue`(대기열 위치/변동), `captcha`(검증 상태), `seat`(좌석 선택), `payment`(결제 진행), `complete`(완료 결과) | 예매 퍼널 전 구간의 실제 상호작용을 기록해 이상 구간 탐지 및 원인 분석에 활용하기 위함 |
| 예매 결과/종료 상태 | `completion_status(success/failed/abandoned)`, `is_completed`, `total_duration_ms`, `booking_id`, `final_seats`, `seat_grades` | 성공/실패/중도이탈 결과를 정량화하고 리스크 판정 및 운영 리포트의 근거로 사용하기 위함 |

## Server 로그

| 유형 | 주요 항목 | 수집 목적 |
|---|---|---|
| 요청 식별/상관관계 | `metadata.event_id`, `request_id`, `flow_id`, `session_id`, `received_epoch_ms`, `environment` | API 요청 단위 식별자와 플로우 식별자를 연결해 요청별 추적성과 감사 가능성을 확보하기 위함 |
| 사용자/네트워크 식별 | `identity.user_id_hash`, `ip_hash`, `ip_raw`, `ip_subnet`, `geo` | 동일 사용자/IP 기반 반복 패턴과 우회 시도를 식별하고, 개인정보는 해시 중심으로 관리하기 위함 |
| 클라이언트 지문 | `client_fingerprint.user_agent_hash`, `accept_language`, `tls_fingerprint`, `screen` | 비정상 조합/환경 변조 신호를 확인해 자동화 탐지 신뢰도를 보강하기 위함 |
| 요청 메타 | `request.endpoint`, `route`, `method`, `query_size_bytes`, `body_size_bytes`, `headers_whitelist` | 어떤 API를 어떤 형태로 호출했는지 표준화해 트래픽 이상과 악성 패턴을 빠르게 찾기 위함 |
| 응답 메타 | `response.status_code`, `latency_ms`, `response_size_bytes`, `error_code` | 장애/지연/비정상 응답을 조기에 감지하고 운영 상태를 모니터링하기 위함 |
| 세션/업무 컨텍스트 | `session.*`, `queue.*`, `seat.*` | 요청 당시 세션 상태, 대기열 상태, 좌석 처리 상태를 함께 기록해 행위 문맥을 보존하기 위함 |
| 행동 통계 | `behavior.requests_last_1s/10s/60s`, `unique_endpoints_last_60s`, `login_*_last_10m` | 단시간 과호출, 반복 로그인, 엔드포인트 스캐닝 등 비정상 트래픽 패턴을 수치로 탐지하기 위함 |
| 보안 통제 결과 | `security.captcha_required`, `captcha_passed`, `blocked`, `block_reason`, `block_message` | 요청별 보안 조치 결과를 남겨 정책 효과 검증, 사후 분석, 사용자 대응 근거로 사용하기 위함 |
| 리스크 평가 연계(실시간) | `risk_score`, `decision`, `rules_triggered`, `model_score` (판정/응답/리포트 생성 시 활용) | 실시간 차단/챌린지 판단과 리포트 생성을 위한 근거를 제공하기 위함 |

> 참고: 현재 구현(`main.py`) 기준으로 `risk` 상세는 서버 원본 로그 저장 직전에 제거되며, 실시간 응답/리포트 생성 과정에서 활용됩니다.
