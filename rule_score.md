# 실시간 차단 / 하드룰 / 소프트룰 정리 (현재 코드 기준)

기준 파일:
- `main.py`
- `model/src/rules/rule_base.py`

## 1) 실시간 차단이 무엇이고 어디서 적용되는가

현재 서버는 모든 `/api/*` 요청에서 리스크를 계산한다.  
다만 계산 결과를 **즉시 응답(차단/검증요청)으로 강제**하는 것은 아래 엔드포인트에서만 한다.

- `POST /api/booking/start-token`
- `POST /api/queue/join`
- `GET /api/queue/status`
- `POST /api/queue/enter`
- `POST /api/logs`

즉시 반영 규칙:
- `decision=block` -> HTTP `403` + `message` + `risk` 반환
- `decision=challenge` -> HTTP `202` + `challenge_required=true` + `risk` 반환
- `decision=allow` -> 원래 핸들러 응답 유지

그 외 `/api/*` 요청은 리스크 계산/저장은 되지만, 즉시 403/202로 바꾸지 않는다.

## 2) 하드룰(Hard Rule)

현재 하드룰은 1개다.

- `security.blocked == true` 이면 `hard_action = block`

특징:
- 하드룰은 가중합 점수보다 우선한다.
- 하드룰이 `block`이면 모델 점수 계산을 스킵할 수 있다(`model_skipped_by_hard_rule_block`).

현재 코드 흐름상 `security.blocked` 기본값은 `false`로 시작하고, 리스크 계산 이후에만 `true`로 세팅되므로, 일반 요청에서 하드룰이 먼저 트리거되는 경우는 사실상 드물다.

## 3) 소프트룰(Soft Rule)

소프트룰은 점수를 누적해 `rule_score`를 만든다.  
합산 후 `clamp01`로 0~1 범위로 고정한다.

현재 룰 목록:
- `concurrent_sessions_same_device >= 3` -> `+0.35`
- `concurrent_sessions_same_device >= 8` -> `+0.30`
- `concurrent_sessions_same_ip >= 10` -> `+0.35`
- `concurrent_sessions_same_ip >= 20` -> `+0.30`
- `requests_last_1s >= 10` -> `+0.25`
- `requests_last_1s >= 20` -> `+0.25`
- `captcha_required=true` and `captcha_passed=false` -> `+0.30`
- `queue.poll_interval_ms_stats.p50 < 200` and `queue.jump_count > 0` -> `+0.25`
- `queue.poll_interval_ms_stats.p50 < 120` and `queue.jump_count > 0` -> `+0.35`
- `seat.reserve_attempt_count >= 10` -> `+0.20`
- 브라우저 `is_trusted=false` 클릭 수 `>=1` -> `+0.20`
- 브라우저 `is_trusted=false` 클릭 수 `>=3` -> `+0.30`

## 4) 최종 점수와 판정 방식

최종 리스크:

- `risk_score = clamp01(0.8 * model_score + 0.2 * rule_score)`

기본 임계값:
- `allow` 경계: `0.30`
- `challenge` 경계: `0.70`
- 따라서 `risk < 0.30 => allow`, `0.30 <= risk < 0.70 => challenge`, `risk >= 0.70 => block`

운영 보수 모드:
- `RISK_BLOCK_AUTOMATION=false` 기본값
- 하드룰 없는 모델 단독 `block`은 `challenge`로 완화하고
  - `review_required=true`
  - `block_recommended=true`
  로 남긴다.

## 5) 저장되는 산출물

요청마다 스냅샷 저장:
- `model/rule_score/*_rule_score.json`
- `model/model_score/*_model_score.json`

`rule_score` 파일 주요 필드:
- `decision`
- `rule_score`
- `hard_action`
- `soft_rules_triggered[]`
- `hard_rules_triggered[]`
- `risk_score`
- `threshold_allow`, `threshold_challenge`

## 6) 지금 상태(로컬 저장 데이터 기준, 2026-02-25 확인)

`model/rule_score` 집계:
- 총 `207`건
- `decision`: `allow 202`, `challenge 5`, `block 0`
- `hard_action`: `block 0`, `challenge 0`
- `rule_score > 0`: `2`건
- 소프트룰 트리거는 현재 `requests_last_1s>=10` 2건만 확인

관찰:
- 현재 `challenge` 사례 5건은 `rule_score=0`이고 `model_score`로 인해 발생했다.
- 즉, 실제 운영 로그에서는 아직 하드룰 기반 즉시 차단(block) 사례가 확인되지 않는다.

## 7) SHAP / Cumulative SHAP 요약 (active 모델 기준)

분석 기준:
- 모델: `model/artifacts/active/human_model_params.json` (IsolationForest, feature 114개)
- 데이터: `hybrid_model/data/auto_split`의 validation+test
  - human `230`, macro `300`
- 산출 파일:
  - `hybrid_model/reports/benchmark/shap_feature_importance_active_model.csv`
  - `hybrid_model/reports/benchmark/shap_feature_importance_active_model.md`
  - `hybrid_model/reports/benchmark/shap_feature_importance_active_model_cumulative.csv`
  - `hybrid_model/reports/benchmark/shap_feature_importance_active_model_cumulative.md`

Top 10 feature importance (`mean_abs_shap_all`) :
1. `seat_mouse_curvature_rad` (`0.22726720`)
2. `perf_avg_mouse_speed` (`0.21647129`)
3. `seat_details_count` (`0.20397054`)
4. `captcha_trusted_ratio` (`0.19121194`)
5. `perf_mouse_curvature_rad` (`0.18965747`)
6. `captcha_status_success` (`0.18401894`)
7. `perf_avg_straightness` (`0.15797146`)
8. `selected_seat_count` (`0.15734269`)
9. `queue_total_queue` (`0.13798143`)
10. `captcha_click_count` (`0.13371800`)

Cumulative SHAP (`mean_abs_shap_all` 누적 설명력):
- 80% 도달: rank `30` (`seat_avg_click_interval`), cumulative `0.8022`
- 90% 도달: rank `41` (`captcha_std_mouse_speed`), cumulative `0.9009`
- 95% 도달: rank `49` (`captcha_avg_straightness`), cumulative `0.9548`
- 99% 도달: rank `57` (`queue_avg_click_duration`), cumulative `0.9915`

해석 포인트:
- 모델 점수에 기여하는 상위 피처는 규칙 점수(`rule_score`)와 별개로 `model_score` 측 변별력을 제공한다.
- 상위 30개 피처로 전체 설명력의 약 80%를 설명하므로, 피처 축소 또는 경량화 시 우선 후보군으로 활용 가능하다.

## 8) 서버 로그 기반 룰 개선안 (초안, 미구현)

아래 내용은 `rule_base.py` 개선을 위한 설계 초안이며, 현재 코드에는 아직 반영되지 않았다.

### 8-1. 하드룰 제안 (즉시 `block`)

| ID | 조건(서버 로그 기준) | 액션 | 대응하려는 패턴 | 오탐 방지 가드 |
|---|---|---|---|---|
| H1 | `behavior.requests_last_1s >= 25` 또는 `behavior.requests_last_10s >= 120` | `block` | 자동 새로고침/버튼 연타/크롤링 burst | 오픈 직후(예: 2~5초)는 임계치 완화 |
| H2 | `request.endpoint="/api/queue/status"` AND `queue.poll_interval_ms_stats.p50 > 0 AND < 120` AND `queue.jump_count >= 2` | `block` | 사람 속도를 넘는 자동 폴링 | 단일 스파이크가 아니라 2회 이상 반복일 때만 |
| H3 | `request.endpoint in {"/api/queue/status","/api/queue/enter"}` AND `queue.join_epoch_ms == 0` | `block` | 비정상 경로/직접 API 우회 | 정상 대기열 진입 토큰이 있는 요청은 제외 |
| H4 | `behavior.concurrent_sessions_same_ip >= 30` 또는 `behavior.concurrent_sessions_same_device >= 12` | `block` | 다기기·다세션 동시 남용 | 기업망/공용망 예외는 별도 allowlist |
| H5 | `security.captcha_required=true` AND `security.captcha_passed=false` AND `behavior.requests_last_10s >= 40` | `block` | 검증 우회 + 자동 요청 지속 | 캡차 실패 1회만으로는 차단하지 않음 |

### 8-2. 소프트룰 제안 (점수 누적)

| ID | 조건(서버 로그 기준) | 가중치(예시) | 대응하려는 패턴 | 오탐 방지 가드 |
|---|---|---:|---|---|
| S1 | `behavior.requests_last_1s >= 10` | `+0.20` | 단기 burst 요청 | 이벤트 오픈 구간 가중치 감산 |
| S2 | `behavior.requests_last_10s >= 40` | `+0.15` | 연속 과호출 | 단일 endpoint 대기열 API는 별도 임계 |
| S3 | `behavior.requests_last_60s >= 180` | `+0.10` | 지속적 과트래픽 | 정상 탐색 트래픽 상한선 기반 조정 |
| S4 | `behavior.unique_endpoints_last_60s <= 2` AND `behavior.requests_last_60s >= 100` | `+0.10` | 자동화 반복 루프 | 정상 결제 단계는 제외 |
| S5 | `queue.poll_interval_ms_stats.p50 > 0 AND < 200` AND `queue.jump_count > 0` | `+0.20` | 빠른 queue 폴링 | 짧은 세션 1회는 경고만 |
| S6 | `queue.poll_interval_ms_stats.p50 > 0 AND < 120` AND `queue.jump_count > 0` | `+0.25` | 매크로성 폴링 | H2와 중복 시 hard 우선 |
| S7 | `behavior.concurrent_sessions_same_ip >= 10` | `+0.20` | 동시 접속 남용 | NAT 환경 고려해 점진 가중 |
| S8 | `behavior.concurrent_sessions_same_device >= 3` | `+0.15` | 동일 기기 다중 세션 | 로그인 상태/쿠키 리셋 패턴 함께 확인 |
| S9 | `behavior.login_fail_count_last_10m >= 5` AND `behavior.login_unique_accounts_last_10m >= 3` | `+0.15` | 계정 탐색/사전 공격 | 장애 시간대 로그인 실패 급증 예외 |
| S10 | `security.captcha_required=true` AND `security.captcha_passed=false` | `+0.20` | 검증 실패 지속 | 최초 실패는 낮은 가중으로 시작 |

### 8-3. 약관 위반 기준과 룰 매핑

- 매크로/봇/자동화 사용: `H1`, `H2`, `S1`, `S2`, `S5`, `S6`
- 과도한 새로고침·연타 트래픽: `H1`, `S1`, `S2`, `S3`
- 다수 기기·세션 동시 접속 남용: `H4`, `S7`, `S8`
- 비정상 접속·우회 시도: `H3`, `H5`, `S9`, `S10`
- 스크래핑/자동 수집 접근: `H1`, `S3`, `S4`
- 비정상 경로 예매: `H3` (핵심)

### 8-4. 서버 로그만으로는 약한 영역 (추가 집계 필요)

아래는 요청 단위 로그만으로 즉시 판정하기 어렵고, 계정/기간 집계가 필요한 항목이다.

- 짧은 시간 내 다량 예매 + 반복 취소
- 암표/전매 목적의 구매 패턴

권장 추가 집계 필드(향후):
- `bookings_count_24h`
- `cancellations_count_24h`
- `cancellation_ratio_24h`
- `distinct_performance_booked_24h`
- `distinct_ip_10m_by_account`
- `distinct_user_agent_10m_by_account`

### 8-5. 적용 순서 권장

1. `S*` 소프트룰만 먼저 반영해 운영 로그를 1~2주 수집  
2. 오탐이 낮은 `H3`(비정상 경로)부터 하드룰 적용  
3. `H1/H2/H5`는 시간대별 임계치(오픈 직후 vs 일반 시간) 분리 적용  
4. `H4/S7/S8`은 동시세션 집계 정확도 검증 후 적용  

## 9) 임계값 산정 템플릿 (운영 적용용)

### 9-1. 산정 원칙

- 임계값이 필요한 신호는 기본적으로 `soft rule`로 시작한다.
- `hard rule`은 아래 3가지를 동시에 만족할 때만 승격한다.
  - 극단 임계값(`P99.9` 이상 또는 보안 위반성 이벤트)
  - 짧은 시간 반복(`N회 / T초`)
  - 보조 신호 동반(예: `jump_count`, `captcha_failed`)

### 9-2. 임계값 계산 절차

1. 기준 로그 구간 수집: 최근 7~14일, 정상 트래픽 중심  
2. 구간 분리:
   - 엔드포인트별(`queue/status`, `queue/enter`, `auth/login` 등)
   - 시간대별(오픈 직후 0~5분 / 일반 시간)
3. 분포 통계 계산: `P95`, `P99`, `P99.5`, `P99.9`, 평균, 표준편차, MAD  
4. 초기값 설정:
   - `soft_threshold`: 보통 `P99` 근처
   - `hard_candidate`: 보통 `P99.9` + 반복조건
5. 검증셋(human/macro)으로 FPR/Recall 확인 후 최종 조정

### 9-3. 권장 초기 산식

- `soft_threshold = max(P99, median + 6*MAD)`
- `hard_threshold = max(P99.9, soft_threshold + margin)`
- `hard_trigger = (metric >= hard_threshold) AND (hit_count_in_Ts >= N)`

권장 초기값:
- `T`(반복창): 10초 또는 30초
- `N`(반복횟수): 2~3회
- `margin`: soft 대비 10~30% 상향

### 9-4. 룰별 임계값 시트 (작성 템플릿)

| Rule ID | 핵심 지표 | 분리 구간(필수) | soft 초기값 입력칸 | hard 후보 입력칸 | 반복 조건(N/T) | 검증 지표(FPR/Recall) | 최종 결정 |
|---|---|---|---|---|---|---|---|
| H1/S1/S2/S3 | `requests_last_1s`, `requests_last_10s`, `requests_last_60s` | endpoint + 오픈/일반 | `____` | `____` | `N=__ / T=__s` | `FPR __ / Recall __` | soft/hard |
| H2/S5/S6 | `queue.poll_interval_ms_stats.p50`, `queue.jump_count` | `queue/status` 전용 | `p50<____` | `p50<____` | `N=__ / T=__s` | `FPR __ / Recall __` | soft/hard |
| H3 | `queue.join_epoch_ms`, 경로 일관성 | `queue/status, queue/enter` | 해당 없음 | 정책성 하드룰 | 반복 불필요 | 오탐 케이스 수 | hard |
| H4/S7/S8 | `concurrent_sessions_same_ip`, `concurrent_sessions_same_device` | account/ip 기준 | `____` | `____` | `N=__ / T=__s` | `FPR __ / Recall __` | soft/hard |
| H5/S10 | `captcha_required`, `captcha_passed`, `requests_last_10s` | captcha 구간 | `req10s>=____` | `req10s>=____` | `N=__ / T=__s` | `FPR __ / Recall __` | soft/hard |
| S4 | `unique_endpoints_last_60s` + 고빈도 요청 | endpoint 분포 구간 | `uniq<=____` | 필요 시 없음 | 선택 | `FPR __ / Recall __` | soft |
| S9 | `login_fail_count_last_10m`, `login_unique_accounts_last_10m` | 로그인 API 전용 | `fail>=____` | 필요 시 없음 | 선택 | `FPR __ / Recall __` | soft |

### 9-5. 운영 체크리스트

- 오픈 직후 임계값 별도 운영 여부 (`yes/no`)
- NAT/공유망/사내망 allowlist 반영 여부
- `challenge` 전환 비율 목표치(예: 0.5~2%)
- `block` 정책 적용 전 shadow 모드 기간(예: 1~2주)
- 주간 재튜닝 주기(예: 매주 1회)
