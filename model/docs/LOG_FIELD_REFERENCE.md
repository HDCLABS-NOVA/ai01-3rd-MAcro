# 브라우저/서버 로그 필드 레퍼런스

이 문서는 브라우저 로그와 서버 로그의 필드를 한글로 정리한 참고 문서입니다.
각 행은 스키마 필드 경로 기준이며, 예시값은 현재 저장된 샘플 로그에서 가능한 경우 채웠습니다.

## 기준 파일
- 브라우저 로그 필드: `model/schemas/browser_log_structure.json`
- 서버 로그 필드: `model/schemas/server_log_structure.json`
- 브라우저 로그 필드 샘플: `model/data/raw/browser/real_human/20260215_perf001_flow_20260215_pml9ds_success.json`
- 서버 로그 필드 샘플: `model/data/raw/server/20260215/20260215_req_c69643e9b5cf480997bdca9441b331d1.json`

## 요약
- 브라우저 필드 수: **335**
- 서버 필드 수: **100**
- 전체 필드 수: **435**

## 브라우저 로그 필드
- 스키마 파일: `model/schemas/browser_log_structure.json`
- 필드 수: **335**

| 필드 경로 | 타입 | 설명 | 예시값 |
|---|---|---|---|
| `schema_version` | value | 2.0.0 | `` |
| `notes` | object | 객체 | `` |
| `notes.time_standard` | value | All *_epoch_ms fields use Unix epoch milliseconds (UTC) | `` |
| `notes.event_ordering` | value | event_seq must be strictly increasing within a flow_id | `` |
| `notes.label_usage` | value | metadata.label.bot_type is training metadata only and must be excluded from model input features | `` |
| `notes.hover_collection` | value | Collect hover only in perf/seat stages with throttling and short-dwell filtering to reduce noise | `` |
| `metadata` | object | 객체 | `{"flow_id": "flow_20260215_pml9ds", "session_id": "sess_gy833sc", "bot_type": "", "user_email": "test_kim@email.com",...` |
| `metadata.flow_id` | string | Unique flow ID, format: flow_YYYYMMDD_random | `flow_20260215_pml9ds` |
| `metadata.session_id` | string | Session ID, format: sess_random | `sess_gy833sc` |
| `metadata.created_at` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:23.238+09:00` |
| `metadata.flow_start_epoch_ms` | number | 숫자 | `` |
| `metadata.flow_end_epoch_ms` | number | 숫자 | `` |
| `metadata.flow_start_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:23.238+09:00` |
| `metadata.flow_end_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:47.637+09:00` |
| `metadata.total_duration_ms` | number | 숫자 | `24399` |
| `metadata.is_completed` | boolean | 불리언 | `True` |
| `metadata.completion_status` | string | 'success', 'failed', 'abandoned' | `success` |
| `metadata.performance_id` | string | 문자열 | `perf001` |
| `metadata.performance_title` | string | 문자열 | `아이유 콘서트 <The Golden Hour>` |
| `metadata.ticket_open_expected_at` | datetime | ISO8601 타임스탬프 | `` |
| `metadata.ticket_open_detected_at` | datetime | ISO8601 타임스탬프 | `` |
| `metadata.open_detect_source` | string | 'dom_mutation', 'api_response', 'websocket', 'manual_refresh' | `` |
| `metadata.open_to_first_action_ms` | number | 숫자 | `` |
| `metadata.selected_date` | string | YYYY-MM-DD | `2026-02-15` |
| `metadata.selected_time` | string | HH:mm | `18:00` |
| `metadata.final_seats` | array<scalar> | 스칼라 배열 | `["VIP-A4"]` |
| `metadata.final_seats[0]` | string | Seat ID | `VIP-A4` |
| `metadata.seat_grades` | array<object> | 객체 배열 | `[{"seat": "VIP-A4", "grade": "VIP", "price": 180000}]` |
| `metadata.seat_grades[]` | object | 객체 | `{"seat": "VIP-A4", "grade": "VIP", "price": 180000}` |
| `metadata.seat_grades[].seat` | string | 문자열 | `VIP-A4` |
| `metadata.seat_grades[].grade` | string | 문자열 | `VIP` |
| `metadata.seat_grades[].price` | number | 숫자 | `180000` |
| `metadata.booking_id` | string | 문자열 | `M55076056` |
| `metadata.privacy` | object | 객체 | `` |
| `metadata.privacy.user_id_hash` | string | stable hash | `` |
| `metadata.privacy.session_fingerprint_hash` | string | 문자열 | `` |
| `metadata.privacy.user_ip_hash` | string | 문자열 | `` |
| `metadata.privacy.user_email_hash` | string | 문자열 | `` |
| `metadata.privacy.booker_phone_hash` | string | 문자열 | `` |
| `metadata.privacy.booker_email_hash` | string | 문자열 | `` |
| `metadata.privacy.hash_salt_version` | string | 문자열 | `` |
| `metadata.browser_info` | object | 객체 | `{"userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safa...` |
| `metadata.browser_info.userAgent` | string | 문자열 | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36` |
| `metadata.browser_info.platform` | string | 문자열 | `Win32` |
| `metadata.browser_info.language` | string | 문자열 | `ko-KR` |
| `metadata.browser_info.timezone_offset_min` | number | 숫자 | `` |
| `metadata.browser_info.webdriver` | boolean | 불리언 | `False` |
| `metadata.browser_info.hardwareConcurrency` | number | 숫자 | `16` |
| `metadata.browser_info.deviceMemory` | number | 숫자 | `` |
| `metadata.browser_info.maxTouchPoints` | number | 숫자 | `` |
| `metadata.browser_info.screen` | object | 객체 | `{"w": 1440, "h": 900, "ratio": 1.3333333730697632}` |
| `metadata.browser_info.screen.w` | number | 숫자 | `1440` |
| `metadata.browser_info.screen.h` | number | 숫자 | `900` |
| `metadata.browser_info.screen.ratio` | number | 숫자 | `1.3333333730697632` |
| `metadata.label` | object | 객체 | `` |
| `metadata.label.bot_type` | string | 'human', 'macro_v2', 'unknown' | `` |
| `metadata.label.label_source` | string | 'manual', 'simulated', 'heuristic' | `` |
| `metadata.label.is_training_label` | boolean | 불리언 | `` |
| `metadata.label.exclude_from_features` | boolean | always true | `` |
| `event_stream` | array<object> | 객체 배열 | `` |
| `event_stream[]` | object | 객체 | `` |
| `event_stream[].event_seq` | number | 숫자 | `` |
| `event_stream[].stage` | string | 'perf', 'queue', 'captcha', 'seat', 'discount', 'order_info', 'payment', 'complete' | `` |
| `event_stream[].event_type` | string | e.g., mousemove, click, hover_enter, hover_leave, keydown, api_call | `` |
| `event_stream[].target` | string | 문자열 | `` |
| `event_stream[].target_id` | string | 문자열 | `` |
| `event_stream[].event_time_epoch_ms` | number | 숫자 | `` |
| `event_stream[].event_time_iso` | datetime | ISO8601 타임스탬프 | `` |
| `event_stream[].relative_ms_from_flow_start` | number | 숫자 | `` |
| `event_stream[].client_server_offset_ms` | number | 숫자 | `` |
| `event_stream[].input_source` | string | 'mouse', 'keyboard', 'touch', 'script' | `` |
| `event_stream[].is_trusted` | boolean | 불리언 | `` |
| `event_stream[].x` | number | 숫자 | `` |
| `event_stream[].y` | number | 숫자 | `` |
| `event_stream[].nx` | number | 0~1 | `` |
| `event_stream[].ny` | number | 0~1 | `` |
| `event_stream[].extra` | object | 객체 | `` |
| `network` | object | 객체 | `` |
| `network.requests` | array<object> | 객체 배열 | `` |
| `network.requests[]` | object | 객체 | `` |
| `network.requests[].event_seq` | number | 숫자 | `` |
| `network.requests[].stage` | string | 문자열 | `` |
| `network.requests[].request_id` | string | 문자열 | `` |
| `network.requests[].endpoint` | string | 문자열 | `` |
| `network.requests[].method` | string | 문자열 | `` |
| `network.requests[].req_epoch_ms` | number | 숫자 | `` |
| `network.requests[].res_epoch_ms` | number | 숫자 | `` |
| `network.requests[].latency_ms` | number | 숫자 | `` |
| `network.requests[].status_code` | number | 숫자 | `` |
| `network.requests[].error_code` | string | 문자열 | `` |
| `network.requests[].retry_count` | number | 숫자 | `` |
| `network.requests[].response_size_bytes` | number | 숫자 | `` |
| `network.requests[].queue_position` | number | 숫자 | `` |
| `network.requests[].seat_id` | string | 문자열 | `` |
| `network.requests[].seat_grade` | string | 문자열 | `` |
| `stages` | object | 객체 | `{"perf": {"entry_time": "2026-02-15T18:32:23.238+09:00", "mouse_trajectory": [[542.25, 560.25, 29, "0.2510", "0.5112"...` |
| `stages.perf` | object | 객체 | `{"entry_time": "2026-02-15T18:32:23.238+09:00", "mouse_trajectory": [[542.25, 560.25, 29, "0.2510", "0.5112"], [1398....` |
| `stages.perf.entry_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:23.238+09:00` |
| `stages.perf.entry_epoch_ms` | number | 숫자 | `` |
| `stages.perf.mouse_trajectory` | array<array> | 중첩 배열 | `[[542.25, 560.25, 29, "0.2510", "0.5112"], [1398.75, 429.75, 139, "0.6476", "0.3921"], [1404, 429, 611, "0.6500", "0....` |
| `stages.perf.mouse_trajectory[][0][0]` | number | x coordinate, browser native - int or float | `` |
| `stages.perf.mouse_trajectory[][0][1]` | number | y coordinate, browser native - int or float | `` |
| `stages.perf.mouse_trajectory[][0][2]` | number | relative timestamp in ms | `` |
| `stages.perf.mouse_trajectory[][0][3]` | number | normalized x: 0~1 | `` |
| `stages.perf.mouse_trajectory[][0][4]` | number | normalized y: 0~1 | `` |
| `stages.perf.clicks` | array<object> | 객체 배열 | `[{"x": 1018.5, "y": 773.25, "nx": "0.4715", "ny": "0.7055", "timestamp": 6141, "is_trusted": true, "duration": 52, "b...` |
| `stages.perf.clicks[]` | object | 객체 | `{"x": 1018.5, "y": 773.25, "nx": "0.4715", "ny": "0.7055", "timestamp": 6141, "is_trusted": true, "duration": 52, "bu...` |
| `stages.perf.clicks[].event_seq` | number | 숫자 | `` |
| `stages.perf.clicks[].x` | number | browser native - int or float | `1018.5` |
| `stages.perf.clicks[].y` | number | browser native - int or float | `773.25` |
| `stages.perf.clicks[].nx` | number | 숫자 | `0.4715` |
| `stages.perf.clicks[].ny` | number | 숫자 | `0.7055` |
| `stages.perf.clicks[].timestamp` | number | relative timestamp | `6141` |
| `stages.perf.clicks[].event_time_epoch_ms` | number | 숫자 | `` |
| `stages.perf.clicks[].is_trusted` | boolean | 불리언 | `True` |
| `stages.perf.clicks[].duration` | number | mousedown to mouseup duration in ms | `52` |
| `stages.perf.clicks[].button` | number | 숫자 | `0` |
| `stages.perf.clicks[].is_integer` | boolean | 불리언 | `False` |
| `stages.perf.hover_events` | array<object> | 객체 배열 | `` |
| `stages.perf.hover_events[]` | object | 객체 | `` |
| `stages.perf.hover_events[].event_seq` | number | 숫자 | `` |
| `stages.perf.hover_events[].target` | string | 문자열 | `` |
| `stages.perf.hover_events[].target_id` | string | 문자열 | `` |
| `stages.perf.hover_events[].enter_epoch_ms` | number | 숫자 | `` |
| `stages.perf.hover_events[].leave_epoch_ms` | number | 숫자 | `` |
| `stages.perf.hover_events[].dwell_ms` | number | 숫자 | `` |
| `stages.perf.hover_events[].x` | number | 숫자 | `` |
| `stages.perf.hover_events[].y` | number | 숫자 | `` |
| `stages.perf.hover_events[].nx` | number | 숫자 | `` |
| `stages.perf.hover_events[].ny` | number | 숫자 | `` |
| `stages.perf.hover_events[].is_trusted` | boolean | 불리언 | `` |
| `stages.perf.hover_summary` | object | 객체 | `` |
| `stages.perf.hover_summary.hover_count` | number | 숫자 | `` |
| `stages.perf.hover_summary.unique_targets` | number | 숫자 | `` |
| `stages.perf.hover_summary.avg_dwell_ms` | number | 숫자 | `` |
| `stages.perf.hover_summary.p50_dwell_ms` | number | 숫자 | `` |
| `stages.perf.hover_summary.p95_dwell_ms` | number | 숫자 | `` |
| `stages.perf.hover_summary.hover_to_click_ms_p50` | number | 숫자 | `` |
| `stages.perf.hover_summary.revisit_rate` | number | 0~1 | `` |
| `stages.perf.viewport` | object | 객체 | `{"w": 2160, "h": 1096}` |
| `stages.perf.viewport.w` | number | 숫자 | `2160` |
| `stages.perf.viewport.h` | number | 숫자 | `1096` |
| `stages.perf.exit_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:30.839+09:00` |
| `stages.perf.exit_epoch_ms` | number | 숫자 | `` |
| `stages.perf.duration_ms` | number | 숫자 | `7601` |
| `stages.perf.actions` | array<object> | 객체 배열 | `[{"action": "card_click", "target": "perf001", "timestamp": "2026-02-15T18:32:30.839+09:00"}, {"action": "date_select...` |
| `stages.perf.actions[]` | object | 객체 | `{"action": "card_click", "target": "perf001", "timestamp": "2026-02-15T18:32:30.839+09:00"}` |
| `stages.perf.actions[].event_seq` | number | 숫자 | `` |
| `stages.perf.actions[].action` | string | page_enter, ui_open_detected, card_click, date_select, time_select, booking_start | `card_click` |
| `stages.perf.actions[].target` | string | 문자열 | `perf001` |
| `stages.perf.actions[].target_id` | string | 문자열 | `` |
| `stages.perf.actions[].event_time_epoch_ms` | number | 숫자 | `` |
| `stages.perf.actions[].event_time_iso` | datetime | ISO8601 타임스탬프 | `` |
| `stages.perf.actions[].relative_ms_from_entry` | number | 숫자 | `` |
| `stages.perf.actions[].reaction_ms_from_ui_open` | number | 숫자 | `` |
| `stages.perf.actions[].is_trusted` | boolean | 불리언 | `` |
| `stages.queue` | object | 객체 | `{"entry_time": "2026-02-15T18:32:30.872+09:00", "mouse_trajectory": [], "clicks": [], "viewport": {"w": 2160, "h": 10...` |
| `stages.queue.entry_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:30.872+09:00` |
| `stages.queue.entry_epoch_ms` | number | 숫자 | `` |
| `stages.queue.mouse_trajectory` | array | 배열(아이템 스키마 미정) | `[]` |
| `stages.queue.clicks` | array | 배열(아이템 스키마 미정) | `[]` |
| `stages.queue.hover_events` | array<object> | 객체 배열 | `` |
| `stages.queue.hover_events[]` | object | 객체 | `` |
| `stages.queue.hover_events[].event_seq` | number | 숫자 | `` |
| `stages.queue.hover_events[].seat_id` | string | 문자열 | `` |
| `stages.queue.hover_events[].grade` | string | 문자열 | `` |
| `stages.queue.hover_events[].target` | string | 문자열 | `` |
| `stages.queue.hover_events[].target_id` | string | 문자열 | `` |
| `stages.queue.hover_events[].enter_epoch_ms` | number | 숫자 | `` |
| `stages.queue.hover_events[].leave_epoch_ms` | number | 숫자 | `` |
| `stages.queue.hover_events[].dwell_ms` | number | 숫자 | `` |
| `stages.queue.hover_events[].x` | number | 숫자 | `` |
| `stages.queue.hover_events[].y` | number | 숫자 | `` |
| `stages.queue.hover_events[].nx` | number | 숫자 | `` |
| `stages.queue.hover_events[].ny` | number | 숫자 | `` |
| `stages.queue.hover_events[].is_trusted` | boolean | 불리언 | `` |
| `stages.queue.hover_summary` | object | 객체 | `` |
| `stages.queue.hover_summary.hover_count` | number | 숫자 | `` |
| `stages.queue.hover_summary.unique_targets` | number | 숫자 | `` |
| `stages.queue.hover_summary.unique_grades` | number | 숫자 | `` |
| `stages.queue.hover_summary.avg_dwell_ms` | number | 숫자 | `` |
| `stages.queue.hover_summary.p50_dwell_ms` | number | 숫자 | `` |
| `stages.queue.hover_summary.p95_dwell_ms` | number | 숫자 | `` |
| `stages.queue.hover_summary.hover_to_click_ms_p50` | number | 숫자 | `` |
| `stages.queue.hover_summary.revisit_rate` | number | 0~1 | `` |
| `stages.queue.viewport` | object | 객체 | `{"w": 2160, "h": 1096}` |
| `stages.queue.viewport.w` | number | 숫자 | `2160` |
| `stages.queue.viewport.h` | number | 숫자 | `1096` |
| `stages.queue.exit_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:34.875+09:00` |
| `stages.queue.exit_epoch_ms` | number | 숫자 | `` |
| `stages.queue.duration_ms` | number | 숫자 | `4003` |
| `stages.queue.initial_position` | number | 숫자 | `25` |
| `stages.queue.final_position` | number | 숫자 | `0` |
| `stages.queue.total_queue` | number | 숫자 | `8000` |
| `stages.queue.wait_duration_ms` | number | 숫자 | `3999` |
| `stages.queue.queue_entry_trigger` | string | 'booking_start_click', 'api_redirect', 'auto' | `` |
| `stages.queue.request_polling_interval_ms_stats` | object | 객체 | `` |
| `stages.queue.request_polling_interval_ms_stats.min` | number | 숫자 | `` |
| `stages.queue.request_polling_interval_ms_stats.p50` | number | 숫자 | `` |
| `stages.queue.request_polling_interval_ms_stats.p95` | number | 숫자 | `` |
| `stages.queue.queue_jump_count` | number | 숫자 | `` |
| `stages.queue.position_updates` | array<object> | 객체 배열 | `[{"position": 0, "status": "ready", "timestamp": "2026-02-15T18:32:34.875+09:00"}]` |
| `stages.queue.position_updates[]` | object | 객체 | `{"position": 0, "status": "ready", "timestamp": "2026-02-15T18:32:34.875+09:00"}` |
| `stages.queue.position_updates[].event_seq` | number | 숫자 | `` |
| `stages.queue.position_updates[].position` | number | 숫자 | `0` |
| `stages.queue.position_updates[].status` | string | 문자열 | `ready` |
| `stages.queue.position_updates[].timestamp` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:34.875+09:00` |
| `stages.queue.position_updates[].event_time_epoch_ms` | number | 숫자 | `` |
| `stages.captcha` | object | 객체 | `{"entry_time": "2026-02-15T18:32:35.916+09:00", "mouse_trajectory": [[1170, 825.75, 5651, "0.5417", "0.7534"]], "clic...` |
| `stages.captcha.entry_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:35.916+09:00` |
| `stages.captcha.entry_epoch_ms` | number | 숫자 | `` |
| `stages.captcha.mouse_trajectory` | array | 배열(아이템 스키마 미정) | `[[1170, 825.75, 5651, "0.5417", "0.7534"]]` |
| `stages.captcha.clicks` | array | 배열(아이템 스키마 미정) | `[{"x": 1089, "y": 687, "nx": "0.5042", "ny": "0.6268", "timestamp": 1155, "is_trusted": true, "duration": 17, "button...` |
| `stages.captcha.viewport` | object | 객체 | `{"w": 2160, "h": 1096}` |
| `stages.captcha.viewport.w` | number | 숫자 | `2160` |
| `stages.captcha.viewport.h` | number | 숫자 | `1096` |
| `stages.captcha.exit_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:41.588+09:00` |
| `stages.captcha.exit_epoch_ms` | number | 숫자 | `` |
| `stages.captcha.duration_ms` | number | 숫자 | `5672` |
| `stages.captcha.challenge_type` | string | 문자열 | `` |
| `stages.captcha.attempt_count` | number | 숫자 | `` |
| `stages.captcha.status` | string | e.g., 'verified', 'failed', 'skipped' | `verified` |
| `stages.seat` | object | 객체 | `{"entry_time": "2026-02-15T18:32:41.588+09:00", "mouse_trajectory": [], "clicks": [{"x": 531, "y": 489, "nx": "0.2458...` |
| `stages.seat.entry_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:41.588+09:00` |
| `stages.seat.entry_epoch_ms` | number | 숫자 | `` |
| `stages.seat.mouse_trajectory` | array | 배열(아이템 스키마 미정) | `[]` |
| `stages.seat.clicks` | array | 배열(아이템 스키마 미정) | `[{"x": 531, "y": 489, "nx": "0.2458", "ny": "0.4462", "timestamp": 558, "is_trusted": true, "duration": 42, "button":...` |
| `stages.seat.viewport` | object | 객체 | `{"w": 2160, "h": 1096}` |
| `stages.seat.viewport.w` | number | 숫자 | `2160` |
| `stages.seat.viewport.h` | number | 숫자 | `1096` |
| `stages.seat.exit_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:42.738+09:00` |
| `stages.seat.exit_epoch_ms` | number | 숫자 | `` |
| `stages.seat.duration_ms` | number | 숫자 | `1150` |
| `stages.seat.seat_map_snapshot` | array<object> | 객체 배열 | `` |
| `stages.seat.seat_map_snapshot[]` | object | 객체 | `` |
| `stages.seat.seat_map_snapshot[].captured_epoch_ms` | number | 숫자 | `` |
| `stages.seat.seat_map_snapshot[].grade` | string | 문자열 | `` |
| `stages.seat.seat_map_snapshot[].color` | string | hex or rgba | `` |
| `stages.seat.seat_map_snapshot[].available_count` | number | 숫자 | `` |
| `stages.seat.seat_map_snapshot[].total_count` | number | 숫자 | `` |
| `stages.seat.seat_attempts` | array<object> | 객체 배열 | `` |
| `stages.seat.seat_attempts[]` | object | 객체 | `` |
| `stages.seat.seat_attempts[].event_seq` | number | 숫자 | `` |
| `stages.seat.seat_attempts[].seat_id` | string | 문자열 | `` |
| `stages.seat.seat_attempts[].x` | number | 숫자 | `` |
| `stages.seat.seat_attempts[].y` | number | 숫자 | `` |
| `stages.seat.seat_attempts[].nx` | number | 숫자 | `` |
| `stages.seat.seat_attempts[].ny` | number | 숫자 | `` |
| `stages.seat.seat_attempts[].grade` | string | 문자열 | `` |
| `stages.seat.seat_attempts[].color` | string | 문자열 | `` |
| `stages.seat.seat_attempts[].availability_before` | string | 'available', 'occupied', 'unknown' | `` |
| `stages.seat.seat_attempts[].click_epoch_ms` | number | 숫자 | `` |
| `stages.seat.seat_attempts[].result` | string | 'selected', 'failed', 'already_taken', 'blocked' | `` |
| `stages.seat.seat_attempts[].response_latency_ms` | number | 숫자 | `` |
| `stages.seat.range_selection` | object | 객체 | `` |
| `stages.seat.range_selection.strategy` | string | 'manual', 'color_scan', 'id_pattern', 'section_filter' | `` |
| `stages.seat.range_selection.filters` | object | 객체 | `` |
| `stages.seat.range_selection.filters.min_price` | number | 숫자 | `` |
| `stages.seat.range_selection.filters.max_price` | number | 숫자 | `` |
| `stages.seat.range_selection.filters.preferred_grades` | array<scalar> | 스칼라 배열 | `` |
| `stages.seat.range_selection.filters.preferred_grades[0]` | string | 문자열 | `` |
| `stages.seat.range_selection.filters.sections` | array<scalar> | 스칼라 배열 | `` |
| `stages.seat.range_selection.filters.sections[0]` | string | 문자열 | `` |
| `stages.seat.range_selection.filters.rows` | array<scalar> | 스칼라 배열 | `` |
| `stages.seat.range_selection.filters.rows[0]` | string | 문자열 | `` |
| `stages.seat.range_selection.scan_duration_ms` | number | 숫자 | `` |
| `stages.seat.range_selection.candidate_count` | number | 숫자 | `` |
| `stages.seat.selected_seats` | array<scalar> | 스칼라 배열 | `["VIP-A4"]` |
| `stages.seat.selected_seats[0]` | string | 문자열 | `VIP-A4` |
| `stages.seat.seat_details` | array<object> | 객체 배열 | `[{"id": "VIP-A4", "grade": "VIP", "price": 180000}]` |
| `stages.seat.seat_details[]` | object | 객체 | `{"id": "VIP-A4", "grade": "VIP", "price": 180000}` |
| `stages.seat.seat_details[].id` | string | 문자열 | `VIP-A4` |
| `stages.seat.seat_details[].grade` | string | 문자열 | `VIP` |
| `stages.seat.seat_details[].price` | number | 숫자 | `180000` |
| `stages.seat.first_seat_click_to_confirm_ms` | number | 숫자 | `` |
| `stages.discount` | object | 객체 | `{"entry_time": "2026-02-15T18:32:42.802+09:00", "mouse_trajectory": [[1327.5, 894, 531, "0.6146", "0.8157"]], "clicks...` |
| `stages.discount.entry_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:42.802+09:00` |
| `stages.discount.entry_epoch_ms` | number | 숫자 | `` |
| `stages.discount.mouse_trajectory` | array | 배열(아이템 스키마 미정) | `[[1327.5, 894, 531, "0.6146", "0.8157"]]` |
| `stages.discount.clicks` | array | 배열(아이템 스키마 미정) | `[{"x": 1218.75, "y": 1009.5, "nx": "0.5642", "ny": "0.9211", "timestamp": 1010, "is_trusted": true, "duration": 22, "...` |
| `stages.discount.viewport` | object | 객체 | `{"w": 2160, "h": 1096}` |
| `stages.discount.viewport.w` | number | 숫자 | `2160` |
| `stages.discount.viewport.h` | number | 숫자 | `1096` |
| `stages.discount.exit_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:43.814+09:00` |
| `stages.discount.exit_epoch_ms` | number | 숫자 | `` |
| `stages.discount.duration_ms` | number | 숫자 | `1012` |
| `stages.discount.selected_discount` | string | 문자열 | `normal` |
| `stages.order_info` | object | 객체 | `{"entry_time": "2026-02-15T18:32:43.851+09:00", "mouse_trajectory": [[1305.75, 1040.25, 1161, "0.6045", "0.9491"]], "...` |
| `stages.order_info.entry_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:43.851+09:00` |
| `stages.order_info.entry_epoch_ms` | number | 숫자 | `` |
| `stages.order_info.mouse_trajectory` | array | 배열(아이템 스키마 미정) | `[[1305.75, 1040.25, 1161, "0.6045", "0.9491"]]` |
| `stages.order_info.clicks` | array | 배열(아이템 스키마 미정) | `[{"x": 1322.25, "y": 1009.5, "nx": "0.6122", "ny": "0.9211", "timestamp": 819, "is_trusted": true, "duration": 23, "b...` |
| `stages.order_info.viewport` | object | 객체 | `{"w": 2160, "h": 1096}` |
| `stages.order_info.viewport.w` | number | 숫자 | `2160` |
| `stages.order_info.viewport.h` | number | 숫자 | `1096` |
| `stages.order_info.exit_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:45.024+09:00` |
| `stages.order_info.exit_epoch_ms` | number | 숫자 | `` |
| `stages.order_info.duration_ms` | number | 숫자 | `1173` |
| `stages.order_info.delivery_type` | string | 문자열 | `pickup` |
| `stages.order_info.has_phone` | boolean | 불리언 | `True` |
| `stages.order_info.has_email` | boolean | 불리언 | `True` |
| `stages.payment` | object | 객체 | `{"entry_time": "2026-02-15T18:32:45.060+09:00", "mouse_trajectory": [], "clicks": [{"x": 1273.5, "y": 1039.5, "nx": "...` |
| `stages.payment.entry_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:45.060+09:00` |
| `stages.payment.entry_epoch_ms` | number | 숫자 | `` |
| `stages.payment.mouse_trajectory` | array | 배열(아이템 스키마 미정) | `[]` |
| `stages.payment.clicks` | array | 배열(아이템 스키마 미정) | `[{"x": 1273.5, "y": 1039.5, "nx": "0.5896", "ny": "0.9484", "timestamp": 245, "is_trusted": true, "duration": 30, "bu...` |
| `stages.payment.viewport` | object | 객체 | `{"w": 2160, "h": 1096}` |
| `stages.payment.viewport.w` | number | 숫자 | `2160` |
| `stages.payment.viewport.h` | number | 숫자 | `1096` |
| `stages.payment.exit_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:47.558+09:00` |
| `stages.payment.exit_epoch_ms` | number | 숫자 | `` |
| `stages.payment.duration_ms` | number | 숫자 | `2498` |
| `stages.payment.payment_type` | string | 문자열 | `card` |
| `stages.payment.completed` | boolean | 불리언 | `True` |
| `stages.payment.completed_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:47.558+09:00` |
| `stages.payment.completed_epoch_ms` | number | 숫자 | `` |
| `stages.complete` | object | 객체 | `{"entry_time": "2026-02-15T18:32:47.619+09:00", "mouse_trajectory": [], "clicks": [], "viewport": {"w": 2160, "h": 10...` |
| `stages.complete.entry_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:47.619+09:00` |
| `stages.complete.entry_epoch_ms` | number | 숫자 | `` |
| `stages.complete.mouse_trajectory` | array | 배열(아이템 스키마 미정) | `[]` |
| `stages.complete.clicks` | array | 배열(아이템 스키마 미정) | `[]` |
| `stages.complete.viewport` | object | 객체 | `{"w": 2160, "h": 1096}` |
| `stages.complete.viewport.w` | number | 숫자 | `2160` |
| `stages.complete.viewport.h` | number | 숫자 | `1096` |
| `stages.complete.exit_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:47.636+09:00` |
| `stages.complete.exit_epoch_ms` | number | 숫자 | `` |
| `stages.complete.duration_ms` | number | 숫자 | `17` |
| `stages.complete.booking_id` | string | 문자열 | `M55076056` |
| `stages.complete.total_price` | number | 숫자 | `180000` |
| `stages.complete.completion_time` | datetime | ISO8601 타임스탬프 | `2026-02-15T18:32:47.636+09:00` |
| `stages.complete.completion_epoch_ms` | number | 숫자 | `` |

## 서버 로그 필드
- 스키마 파일: `model/schemas/server_log_structure.json`
- 필드 수: **100**

| 필드 경로 | 타입 | 설명 | 예시값 |
|---|---|---|---|
| `schema_version` | value | 1.0.0 | `` |
| `notes` | object | 객체 | `` |
| `notes.purpose` | value | Server-side telemetry for macro detection. Complements client logs. | `` |
| `notes.pii_policy` | value | Store hashes, not raw identifiers. Keep raw IP only if legally allowed. | `` |
| `notes.time_standard` | value | All *_epoch_ms fields use Unix epoch milliseconds (UTC). | `` |
| `metadata` | object | 객체 | `{"event_id": "evt_326b89572c2b4a7a866a78d97fe72e1f", "request_id": "req_c69643e9b5cf480997bdca9441b331d1", "flow_id":...` |
| `metadata.event_id` | string | unique per server log event | `evt_326b89572c2b4a7a866a78d97fe72e1f` |
| `metadata.request_id` | string | trace id / correlation id | `req_c69643e9b5cf480997bdca9441b331d1` |
| `metadata.flow_id` | string | join with client flow_id if available | `flow_20260215_pml9ds` |
| `metadata.session_id` | string | 문자열 | `sess_gy833sc` |
| `metadata.received_epoch_ms` | number | 숫자 | `1771147967646` |
| `metadata.server_region` | string | 문자열 | `` |
| `metadata.environment` | string | prod, staging | `local` |
| `identity` | object | 객체 | `{"user_id_hash": "b583484ee949120ba7b0db64f1c0b8e7b48dd95a56097ba99508b79c1bb4375d", "account_id_hash": "", "device_i...` |
| `identity.user_id_hash` | string | 문자열 | `b583484ee949120ba7b0db64f1c0b8e7b48dd95a56097ba99508b79c1bb4375d` |
| `identity.account_id_hash` | string | 문자열 | `` |
| `identity.device_id_hash` | string | 문자열 | `` |
| `identity.session_fingerprint_hash` | string | 문자열 | `` |
| `identity.ip_hash` | string | 문자열 | `12ca17b49af2289436f303e0166030a21e525d266e209267433801a8fd4071a0` |
| `identity.ip_raw` | string | optional | `127.0.0.1` |
| `identity.ip_subnet` | string | e.g., /24 or /56 | `127.0.0.0/24` |
| `identity.asn` | string | 문자열 | `` |
| `identity.geo` | object | 객체 | `{"country": "", "region": "", "city": ""}` |
| `identity.geo.country` | string | 문자열 | `` |
| `identity.geo.region` | string | 문자열 | `` |
| `identity.geo.city` | string | 문자열 | `` |
| `client_fingerprint` | object | 객체 | `{"user_agent_hash": "816147bedd84317a66534e444e60842858f0f2a3b3fa43710b4ef836da4252d2", "tls_fingerprint": "", "accep...` |
| `client_fingerprint.user_agent_hash` | string | 문자열 | `816147bedd84317a66534e444e60842858f0f2a3b3fa43710b4ef836da4252d2` |
| `client_fingerprint.tls_fingerprint` | string | 문자열 | `` |
| `client_fingerprint.accept_language` | string | 문자열 | `ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7` |
| `client_fingerprint.timezone_offset_min` | number | 숫자 | `0` |
| `client_fingerprint.screen` | object | 객체 | `{"w": 0, "h": 0, "ratio": 0}` |
| `client_fingerprint.screen.w` | number | 숫자 | `0` |
| `client_fingerprint.screen.h` | number | 숫자 | `0` |
| `client_fingerprint.screen.ratio` | number | 숫자 | `0` |
| `request` | object | 객체 | `{"endpoint": "/api/logs", "route": "/api/logs", "method": "POST", "query_size_bytes": 0, "body_size_bytes": 5658, "co...` |
| `request.endpoint` | string | 문자열 | `/api/logs` |
| `request.route` | string | 문자열 | `/api/logs` |
| `request.method` | string | 문자열 | `POST` |
| `request.query_size_bytes` | number | 숫자 | `0` |
| `request.body_size_bytes` | number | 숫자 | `5658` |
| `request.content_type` | string | 문자열 | `application/json` |
| `request.headers_whitelist` | object | 객체 | `{"referer": "http://localhost:8000/booking_complete.html?id=M55076056", "origin": "http://localhost:8000", "x_forward...` |
| `request.headers_whitelist.referer` | string | 문자열 | `http://localhost:8000/booking_complete.html?id=M55076056` |
| `request.headers_whitelist.origin` | string | 문자열 | `http://localhost:8000` |
| `request.headers_whitelist.x_forwarded_for` | string | 문자열 | `` |
| `request.headers_whitelist.sec_ch_ua` | string | 문자열 | `"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"` |
| `response` | object | 객체 | `{"status_code": 200, "latency_ms": 9, "response_size_bytes": 150, "error_code": "", "retry_after_ms": 0}` |
| `response.status_code` | number | 숫자 | `200` |
| `response.latency_ms` | number | 숫자 | `9` |
| `response.response_size_bytes` | number | 숫자 | `150` |
| `response.error_code` | string | 문자열 | `` |
| `response.retry_after_ms` | number | 숫자 | `0` |
| `session` | object | 객체 | `{"session_created_epoch_ms": 0, "last_activity_epoch_ms": 1771147967646, "session_age_ms": 0, "login_state": "guest",...` |
| `session.session_created_epoch_ms` | number | 숫자 | `0` |
| `session.last_activity_epoch_ms` | number | 숫자 | `1771147967646` |
| `session.session_age_ms` | number | 숫자 | `0` |
| `session.login_state` | string | 'guest', 'logged_in' | `guest` |
| `session.account_age_days` | number | 숫자 | `0` |
| `session.payment_token_hash` | string | 문자열 | `` |
| `queue` | object | 객체 | `{"queue_id": "", "join_epoch_ms": 0, "enter_trigger": "", "position": 0, "poll_interval_ms_stats": {"min": 0, "p50": ...` |
| `queue.queue_id` | string | 문자열 | `` |
| `queue.join_epoch_ms` | number | 숫자 | `0` |
| `queue.enter_trigger` | string | 'booking_start_click', 'api_redirect', 'auto' | `` |
| `queue.position` | number | 숫자 | `0` |
| `queue.poll_interval_ms_stats` | object | 객체 | `{"min": 0, "p50": 0, "p95": 0}` |
| `queue.poll_interval_ms_stats.min` | number | 숫자 | `0` |
| `queue.poll_interval_ms_stats.p50` | number | 숫자 | `0` |
| `queue.poll_interval_ms_stats.p95` | number | 숫자 | `0` |
| `queue.jump_count` | number | 숫자 | `0` |
| `seat` | object | 객체 | `{"seat_query_count": 0, "reserve_attempt_count": 0, "reserve_fail_codes": [], "seat_hold_ms": 0, "seat_release_ms": 0}` |
| `seat.seat_query_count` | number | 숫자 | `0` |
| `seat.reserve_attempt_count` | number | 숫자 | `0` |
| `seat.reserve_fail_codes` | array<scalar> | 스칼라 배열 | `[]` |
| `seat.reserve_fail_codes[0]` | string | 문자열 | `` |
| `seat.seat_hold_ms` | number | 숫자 | `0` |
| `seat.seat_release_ms` | number | 숫자 | `0` |
| `behavior` | object | 객체 | `{"requests_last_1s": 1, "requests_last_10s": 1, "requests_last_60s": 2, "unique_endpoints_last_60s": 2, "login_attemp...` |
| `behavior.requests_last_1s` | number | 숫자 | `1` |
| `behavior.requests_last_10s` | number | 숫자 | `1` |
| `behavior.requests_last_60s` | number | 숫자 | `2` |
| `behavior.unique_endpoints_last_60s` | number | 숫자 | `2` |
| `behavior.login_attempts_last_10m` | number | 숫자 | `1` |
| `behavior.login_fail_count_last_10m` | number | 숫자 | `0` |
| `behavior.login_success_count_last_10m` | number | 숫자 | `1` |
| `behavior.login_unique_accounts_last_10m` | number | 숫자 | `1` |
| `behavior.retry_count_last_5m` | number | 숫자 | `0` |
| `behavior.concurrent_sessions_same_device` | number | 숫자 | `0` |
| `behavior.concurrent_sessions_same_ip` | number | 숫자 | `0` |
| `security` | object | 객체 | `{"captcha_required": false, "captcha_passed": false, "rate_limited": false, "blocked": false, "block_reason": ""}` |
| `security.captcha_required` | boolean | 불리언 | `False` |
| `security.captcha_passed` | boolean | 불리언 | `False` |
| `security.rate_limited` | boolean | 불리언 | `False` |
| `security.blocked` | boolean | 불리언 | `False` |
| `security.block_reason` | string | 문자열 | `` |
| `risk` | object | 객체 | `{"risk_score": 0, "decision": "allow", "rules_triggered": []}` |
| `risk.risk_score` | number | 0~1 | `0` |
| `risk.decision` | string | 'allow', 'challenge', 'block' | `allow` |
| `risk.rules_triggered` | array<scalar> | 스칼라 배열 | `[]` |
| `risk.rules_triggered[0]` | string | 문자열 | `` |
