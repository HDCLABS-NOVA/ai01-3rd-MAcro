# 서버 로그 수집 및 데이터 구조 보고서

작성 기준은 2026-02-25 현재 `main.py`의 서버 미들웨어 로직과 실제 저장 샘플이다. 이 문서는 개발자가 아닌 사람도 읽을 수 있도록, 서버 로그가 언제부터 어떤 방식으로 쌓이고 무엇이 저장되는지 서술형으로 설명한다.

## 1. 서버 로그를 수집하는 이유와 범위

이 시스템의 서버 로그는 "브라우저가 서버 API를 실제로 어떻게 호출했는지"를 남기기 위한 기록이다. 프론트엔드에서 별도로 보내는 사용자 행동 로그(`/api/logs`)만으로는 놓칠 수 있는 요청 패턴, 응답 지연, 빈도 정보까지 함께 확보하기 위해 서버 쪽에서 자동 수집한다.

수집 대상은 `/api/`로 시작하는 모든 요청이다. 즉, 로그인, 대기열 진입, 대기열 상태 조회, 좌석 관련 API, 로그 저장 API 등 경로가 `/api/*`이면 동일한 방식으로 서버 로그 파일이 생성된다. 반대로 `index.html`, `queue.html`, `*.js`, `*.css`처럼 `/api/*`가 아닌 정적 리소스 요청은 서버 로그 파일로 저장하지 않는다.

## 2. 수집 위치와 수집 시점(쉽게 설명)

수집 위치는 FastAPI의 HTTP 미들웨어다. 미들웨어는 요청 처리 전후에 공통 동작을 끼워 넣는 계층으로, 이 프로젝트에서는 `@app.middleware('http')` 구간이 그 역할을 한다.

동작 순서는 다음과 같다. 사용자가 API를 호출하면 미들웨어가 요청 정보를 먼저 확인한다. 그 다음 실제 API 함수가 실행되어 응답을 만든다. 응답이 나온 뒤 미들웨어가 요청/응답 데이터를 조합해 서버 로그 객체를 만들고 파일로 기록한다. 마지막으로 클라이언트에 응답이 전달된다. 즉, "API 응답이 만들어진 직후"가 로그 저장 시점이다.

이 구조의 장점은 API마다 로그 저장 코드를 중복 작성할 필요가 없고, `/api/*` 요청 전체를 동일 기준으로 남길 수 있다는 점이다. 또한 클라이언트가 로그 전송을 실패하더라도 서버 관점의 요청 기록은 별도로 남길 수 있다.

중요한 점은, 서버 로그가 "로그 저장 API를 따로 호출해서" 쌓이는 구조가 아니라는 것이다. 이 프로젝트에서는 `/api/*` 요청이 처리될 때 미들웨어가 자동으로 서버 로그를 생성하고 저장한다. 즉, 서버 로그는 전용 수집 API 호출 방식이 아니라 미들웨어 자동 적재 방식이다.

또한 저장 타이밍은 "예매 전체가 끝난 뒤 1회"가 아니다. `/api/*` 요청 1건이 끝날 때마다 1건씩 저장되므로, 하나의 예매 흐름에서도 로그가 여러 개 쌓인다. 예를 들어 로그인, 대기열 진입(`/api/queue/join`), 대기열 상태 조회(`/api/queue/status`, 폴링으로 다회 호출), 대기열 입장(`/api/queue/enter`), 브라우저 로그 전송(`/api/logs`)이 각각 별도 서버 로그로 남는다.

미들웨어를 개발 지식 없이 이해하면, "모든 민원창구 앞에 있는 공통 접수 데스크"라고 생각하면 된다. 사용자가 어떤 업무를 하러 오든 먼저 접수 데스크를 지나고, 각 창구에서 처리가 끝난 뒤에도 다시 접수 데스크를 거친다. 이때 접수 데스크는 "누가 왔는지, 어떤 업무였는지, 처리에 얼마나 걸렸는지"를 공통 양식으로 적어 둔다.

이 프로젝트에서도 같은 방식으로 동작한다. `/api/*` 요청은 모두 이 공통 구간을 지나므로, 특정 API 하나에 로그 코드가 빠져 있어도 기본 기록은 남는다. 반대로 `/api/*`가 아닌 일반 페이지 파일 요청은 이 기록 대상에서 제외된다. 그래서 운영자가 나중에 문제를 볼 때 "이 요청이 아예 안 왔는지, 왔는데 실패했는지, 느렸는지"를 비교적 쉽게 확인할 수 있다.

## 3. 수집 방법(데이터가 채워지는 방식)

서버는 각 요청에 대해 공통 텔레메트리 값을 생성한다. 예를 들어 요청/응답 시간차로 `latency_ms`를 계산하고, 헤더의 `content-length`를 이용해 `response_size_bytes`를 채운다. IP는 `x-forwarded-for`를 우선 사용하고 없으면 클라이언트 소켓 IP를 사용한다. 원본 IP 외에도 해시(`ip_hash`)와 서브넷(`ip_subnet`)을 함께 저장해 식별성과 개인정보 보호 요구를 동시에 맞추도록 구성했다.

`flow_id`, `session_id`, `performance_id` 같은 핵심 연계 키는 요청 본문에서 우선 수집하고, 값이 비어 있으면 `x-flow-id`, `x-session-id` 헤더를 보조 입력으로 사용한다. `/api/logs` 요청은 본문의 `metadata`에서 값을 읽고, 그 외 POST/PUT/PATCH 요청은 본문 최상위에서 읽는 방식이다.

대기열 관련 수치는 미들웨어 내부에서 별도 스냅샷 함수로 계산해 `queue` 섹션에 반영한다. 또한 최근 1초/10초/60초 요청량, 최근 10분 로그인 시도 요약 같은 행동 지표를 `behavior`에 함께 적재한다. 이 값들은 단순 감사 로그를 넘어, 매크로 탐지나 이상 징후 분석의 입력값으로 사용된다.

## 4. 표로 보는 서버 로그 데이터 구조

아래 표는 보고서에서 바로 사용할 수 있도록 서버 로그를 "무엇을 수집하는지", "왜 수집하는지" 기준으로 재정리한 것이다.

### 4-1. 핵심 수집 항목 요약

| 수집 항목 | 주요 필드명 | 수집 목적 |
|---|---|---|
| 요청 식별 | `metadata.request_id`, `metadata.event_id` | 개별 API 요청 단위를 고유하게 식별하고 장애/이슈 추적 시 기준점으로 사용 |
| 흐름/세션 연계 | `metadata.flow_id`, `metadata.session_id` | 브라우저 로그와 서버 로그를 연결해 한 사용자의 예매 흐름을 끝까지 추적 |
| 요청 내용 요약 | `request.endpoint`, `request.method`, `request.body_size_bytes`, `request.query_size_bytes` | 어떤 API가 어떤 크기의 요청으로 호출되었는지 파악 |
| 응답 성능/결과 | `response.status_code`, `response.latency_ms`, `response.response_size_bytes` | 실패 응답, 지연 증가, 비정상 응답 크기 등 운영 이상 징후 확인 |
| 네트워크/식별 단서 | `identity.ip_hash`, `identity.ip_subnet`, `identity.user_id_hash` | 동일 IP/계정 기반 반복 호출이나 공격성 패턴 분석 |
| 클라이언트 특성 | `client_fingerprint.user_agent_hash`, `client_fingerprint.accept_language` | 요청 환경의 일관성/변칙 여부를 확인해 자동화 의심 신호 보강 |
| 대기열 상태 | `queue.queue_id`, `queue.position`, `queue.jump_count`, `queue.poll_interval_ms_stats` | 대기열 진행 흐름 및 과도한 폴링/점프 시도 감지 |
| 행동 빈도 | `behavior.requests_last_1s`, `behavior.requests_last_10s`, `behavior.requests_last_60s`, `behavior.unique_endpoints_last_60s` | 짧은 시간 내 과도 호출(봇성 트래픽) 탐지 |
| 로그인 시도 패턴 | `behavior.login_attempts_last_10m`, `behavior.login_fail_count_last_10m`, `behavior.login_unique_accounts_last_10m` | 계정 대입/반복 로그인 시도와 같은 비정상 인증 패턴 확인 |
| 보안 상태 | `security.blocked`, `security.captcha_required`, `security.block_reason` | 차단/추가 인증 판단 결과를 기록해 사후 감사 및 정책 개선에 활용 |

### 4-2. 분석 관점 핵심 필드(운영/탐지용)

| 분류 | 필드명 | 수집 목적 |
|---|---|---|
| 세션 추적 | `metadata.session_id` | 동일 세션에서 반복되는 요청 패턴을 연결해서 확인 |
| 요청 속도 분석 | `behavior.requests_last_1s`, `behavior.requests_last_10s` | 사람 대비 비정상적으로 빠른 요청 빈도 탐지 |
| 엔드포인트 분산 분석 | `behavior.unique_endpoints_last_60s` | 짧은 시간에 다양한 API를 순회하는 자동화 시나리오 식별 |
| 로그인 이상 탐지 | `behavior.login_fail_count_last_10m`, `behavior.login_unique_accounts_last_10m` | 다계정 시도/무차별 로그인 공격 징후 탐지 |
| 대기열 조작 징후 | `queue.jump_count`, `queue.poll_interval_ms_stats` | 지나치게 잦은 폴링, 비정상 재시도, 순번 점프 패턴 확인 |
| 처리 지연 모니터링 | `response.latency_ms` | 특정 시간대/경로에서의 성능 저하 조기 발견 |
| 실패 응답 분석 | `response.status_code` | 특정 API 실패율 급증 구간 탐지 |
| 차단/검증 결과 추적 | `security.blocked`, `security.captcha_required`, `security.block_reason` | 실시간 정책 적용 결과를 사후 검증하고 정책 튜닝 근거로 사용 |

## 5. 결론

이 프로젝트의 서버 로그 수집은 특정 API 하나에 의존하는 방식이 아니라, `/api/*` 전체를 미들웨어에서 공통 수집하는 구조다. 따라서 수집 누락 가능성을 줄이고, 요청-응답-행동 지표를 한 번에 확보할 수 있다. 운영 관점에서는 감사 추적, 장애 분석, 비정상 트래픽 탐지에 모두 유리한 설계다.
