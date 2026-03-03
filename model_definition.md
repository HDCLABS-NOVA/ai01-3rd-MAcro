# Model Definition (Active)

작성일: 2026-03-03

## 1. 모델 개요
- 활성 모델: `One-Class SVM`
- 문제 정의: 매크로 탐지를 고정 클래스 분류가 아닌, 정상 행동 분포 이탈 탐지 문제로 정의
- 입력: 브라우저 행동 로그(`metadata`, `stages`)
- 출력: 연속 점수(`model_score_raw`, `model_score`, `risk_score`) 및 판정(`allow`, `challenge`, `block`)

## 2. 이상 탐지 모델 선정 이유
### 2.1 정상 사용자 데이터 구조
정상 사용자 데이터 분포 분석 결과, 단일 군집에 가까운 구조가 관찰되었다. 정상 분포를 하나의 경계로 감싸는 경계 기반 이상 탐지 모델이 이론적으로 적합하다고 판단했다.

수집 학습 데이터 군집 분석(KMeans):
- 원 feature 공간
- 전처리: `StandardScaler`
- `k=2`: silhouette `0.8448`, 군집 크기 `763 / 2` (`99.74% / 0.26%`)
- `k=3`: silhouette `0.1139`, 군집 크기 `343 / 420 / 2`
- `k=4`: silhouette `0.1259`, 군집 크기 `310 / 273 / 180 / 2`

해석:
- `k=2`에서 높은 silhouette와 극단적 불균형 분할은 정상 데이터가 사실상 하나의 밀집 영역으로 응집되어 있음을 시사한다.
- 따라서 정상 영역 경계를 학습하는 `One-Class SVM`이 주 모델로 적합하다.

### 2.2 매크로의 다양성과 진화
매크로는 종류가 다양하고 계속 진화하므로, 학습에 포함되지 않은 신규 패턴이 운영에서 등장한다. 이에 따라 다음 원칙을 채택했다.
- "현재 알려진 매크로를 맞추는가"보다
- "정상 분포를 벗어나는 신규 자동화 신호를 잡는가"

### 2.3 Isolation Forest 대비 One-Class SVM 선택 이유
Isolation Forest는 데이터에서 전역적으로 고립되는 극단값(outlier)을 탐지하는 데 강점이 있다.  
하지만 본 데이터에서는 매크로가 단순 극단값이라기보다, 정상 행동과 미묘하게 다른 패턴 차이로 나타나는 경우가 많았다.

One-Class SVM은 정상 데이터의 비선형 경계를 학습하기 때문에 이런 패턴 기반 차이를 더 잘 분리할 수 있었다.  
실제로 동일한 FPR 제약 조건에서 One-Class SVM이 더 높은 macro recall을 보여 최종 모델로 선택했다.

### 2.4 Human FPR <= 0.05 조건 성능 비교 (오프라인 참고)
아래 표는 동일한 `Human FPR <= 0.05` 제약에서 두 모델을 비교한 결과다.  
이 비교는 모델 선택 참고용 오프라인 결과이며, 본 문서의 임계값 결정 원칙(human-only validation)에는 사용하지 않는다.

Validation (human_fpr 제약 충족):

| 모델 | Human FPR | Macro Recall | Precision | F1 | AUROC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| One-Class SVM | 0.0435 | 0.9795 | 0.9871 | 0.9833 | 0.9730 | 0.9634 |
| Isolation Forest | 0.0435 | 0.5538 | 0.9774 | 0.7070 | 0.9508 | 0.9668 |

Test (참고):

| 모델 | Human FPR | Macro Recall | Precision | F1 | AUROC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| One-Class SVM | 0.0435 | 0.8766 | 0.9643 | 0.9184 | 0.9661 | 0.9187 |
| Isolation Forest | 0.0348 | 0.5519 | 0.9551 | 0.6996 | 0.9650 | 0.9389 |

### 2.5 브라우저 로그 데이터 수집 과정 (상세)
브라우저 로그는 "클라이언트 이벤트 수집 -> `/api/logs` 전송" 순서로 처리된다.

1. 수집 초기화
- `performance_detail` 진입 시 `initLogCollector(performance_id, performance_title)`를 호출해 수집을 시작한다.
- 초기 `metadata`에는 `flow_id`, `session_id`, `bot_type`, `user_email`, `user_ip`, `created_at`, `flow_start_time`, `browser_info`(userAgent/platform/language/webdriver/hardwareConcurrency/screen) 등이 기록된다.
- 예매 플로우 단위 추적을 위해 `booking_flow_started`를 설정해 흐름 ID를 고정한다.

2. 단계(stage) 단위 로그 생성
- 각 페이지에서 `recordStageEntry(stage)`와 `recordStageExit(stage, extra)`를 호출해 단계별 로그를 닫는다.
- 주요 학습 stage는 `perf`, `queue`, `captcha`, `seat` 4개다.
- 좌석 선택 페이지에서는 `seat_captcha` -> `captcha`, `seat_pick` -> `seat`로 정규화해 저장한다.
- 각 stage에는 `entry_time`, `exit_time`, `duration_ms`, `viewport`, `mouse_trajectory`, `clicks`가 저장되고, `extra`로 선택 좌석/캡차 상태/대기열 정보가 병합된다.
- `discount`, `order_info`, `payment`, `complete` 단계도 기록되지만, active 모델 피처 추출 시 핵심 4개 stage(`perf/queue/captcha/seat`)를 중심으로 사용한다.

3. 사용자 행동 이벤트 수집 규칙
- 마우스 이동: `pointermove`를 100ms 간격으로 샘플링해 `[x, y, relative_ms, nx, ny]` 형태로 `mouse_trajectory`에 누적한다.
- 클릭: `pointerdown` 시각과 `pointerup` 시각 차이로 클릭 지속시간(`duration`)을 계산하고, `x/y`, 정규화 좌표(`nx/ny`), `timestamp`, `is_trusted`, `button`을 `clicks`에 저장한다.
- 메타데이터는 `updateMetadata(...)`로 단계 진행 중 업데이트된다(예: 선택 좌석/날짜/시간/결제 관련 상태).

4. 완료/이탈 처리
- 예매 완료 시 `uploadLog(true, booking_id)`로 최종 로그를 전송하고 `completion_status=success`를 기록한다.
- 완료 전 페이지 이탈 시 `beforeunload`에서 `sendBeacon('/api/logs', ...)`를 사용해 `completion_status=abandoned` 로그를 전송한다.

## 3. 데이터 전처리
### 3.1 입력 정규화
로그 파싱 시 안전 변환을 적용한다.
- 수치형: 파싱 실패 시 `0.0`
- 불린형: 문자열/숫자 표현을 공통 불린값으로 변환

### 3.2 단계 분해
예매 흐름을 4개 stage로 분해한다.
- `perf`, `queue`, `captcha`, `seat`

각 stage에서 다음 이벤트를 수집한다.
- `clicks`
- `mouse_trajectory`
- `hover_events`, `hover_summary`

## 4. 피처 엔지니어링
### 4.1 Stage 피처
각 stage에 대해 동일 템플릿 피처를 생성한다.
- 기본량: duration, click count, mouse points
- 클릭 통계: 평균/표준편차, trusted ratio
- 템포 통계: click interval 평균/표준편차, click tempo entropy
- 반응성: 반응시간 분산
- 마우스 이동: 평균/표준편차 속도, 직진성, 곡률
- 호버 통계: count, unique target, dwell 통계(p50/p95 포함), revisit rate, hover-to-click
- 파생 비율: click-to-hover ratio

### 4.2 Overall/메타 피처
- overall 집계: `overall_reaction_time_var_ms2`, `overall_click_tempo_entropy`, `overall_mouse_curvature_rad`
- 메타/상태: `total_duration_ms`, `selected_seat_count`, `seat_details_count`, `is_completed`, `completion_status_success`, `captcha_status_success`, `perf_actions_count`
- queue 요약: `queue_position_delta`, `queue_total_queue`, `queue_position_updates_count`
- 브라우저 정보: webdriver/hardware/screen 계열

### 4.3 파생 피처(생성 로직)
아래 항목은 원시 이벤트(`clicks`, `mouse_trajectory`, `hover_events`)에서 계산한 파생 피처다.

- 클릭 간격: `*_avg_click_interval`, `*_std_click_interval`
  - 클릭 timestamp 차분(`t_i - t_(i-1)`)의 평균/표준편차
- 반응시간 분산: `*_reaction_time_var_ms2`
  - 각 클릭 직전 마지막 마우스 이동 시점과 클릭 시점 차이(latency)의 분산
- 클릭 템포 엔트로피: `*_click_tempo_entropy`
  - 클릭 간격을 구간 binning 후 엔트로피를 정규화(0~1)
- 마우스 속도 통계: `*_avg_mouse_speed`, `*_std_mouse_speed`
  - 인접 trajectory 점의 거리/시간(`dist/dt`) 기반
- 궤적 직진성: `*_avg_straightness`
  - 시작-끝 직선거리 / 실제 이동거리
- 궤적 곡률: `*_mouse_curvature_rad`
  - 연속 3점에서의 방향 전환 각도의 평균(rad)
- 호버 파생:
  - `*_hover_unique_targets`, `*_hover_avg_dwell_ms`, `*_hover_std_dwell_ms`
  - `*_hover_p50_dwell_ms`, `*_hover_p95_dwell_ms`, `*_hover_revisit_rate`
  - `*_hover_to_click_ms_p50`, `*_hover_trusted_ratio`, `*_hover_unique_grades`
- 클릭-호버 비율: `*_click_to_hover_ratio`
  - `click_count / hover_count` (hover가 0이면 0)
- stage 통합 파생(overall):
  - `overall_reaction_time_var_ms2`
  - `overall_click_tempo_entropy`
  - `overall_mouse_curvature_rad`
  - 4개 핵심 stage(`perf`, `queue`, `captcha`, `seat`) 평균으로 계산
- 상태/요약 파생:
  - `completion_status_success`, `captcha_status_success`, `queue_position_delta` 등
  - 단, `queue_position_delta` 등 일부는 아래 공통 필터링에서 제거된다.

### 4.4 공통 필터링
학습/검증/추론 동일 규칙으로 피처를 제거한다.
- prefix drop: `browser_`
- name drop:
  - `booking_flow_started`
  - `queue_duration_ms`
  - `queue_position_delta`
  - `queue_position_updates_count`
  - `queue_total_queue`

최종 피처 수: `109`

## 5. 학습
### 5.1 학습 입력
- 정상(human) 데이터만 사용(one-class 학습)
- 고정 `feature_order` 기준 벡터화
- 누락 피처는 `0.0`으로 채움

### 5.2 모델 학습
- 알고리즘: One-Class SVM (`RBF`, `gamma=scale`, `nu=0.05`)
- 스케일러: `StandardScaler` 적용 후 학습

### 5.3 원시 점수 정의
- `raw_score = -decision_function(x)`
- 값이 클수록 비정상 성향이 큼
- 학습 분포 기준값 `raw_min`, `raw_max`를 함께 유지

## 6. 검증 (수정 원칙: Human-only)
기존처럼 validation 단계에 macro를 포함하면 임계값이 macro 샘플에 과적합될 수 있어, 검증 원칙을 human-only로 고정한다.

### 6.1 검증 데이터
- validation은 정상(human) 데이터만 사용
- macro 데이터는 validation 단계에 사용하지 않음

### 6.2 검증 지표
human-only 검증에서 기본 지표는 다음을 사용한다.
- Human FPR
- Human score distribution (p50, p95, max 등)

## 7. Human FPR <= 0.05 조건의 임계값 탐색
목표: `Human FPR <= 0.05`를 만족하면서 탐지 민감도를 최대화하는 임계값을 선택한다.

human-only 조건에서의 선택 규칙:
1. validation human 점수(`raw_score` 또는 정규화 점수)를 오름차순 정렬한다.
2. 허용 FP 수를 계산한다.
   - `allowed_fp = floor(0.05 * N)` (`N`은 validation human 샘플 수)
3. `FPR <= 0.05`를 만족하는 임계값 중 가장 낮은 임계값을 선택한다.
   - 실무적으로는 `95th percentile` 기준과 동일한 효과
   - 동일 성능 구간에서는 더 보수적인(안전한) 값 선택 가능

이 정책을 점수 체계로 변환할 때, high-risk 경계(60점, 즉 `risk_score=0.60`)는 임의값이 아니라 validation human 점수 분포의 상위 5% 지점을 반영한 값으로 정의한다.

주의:
- 이 단계에서도 macro 데이터는 사용하지 않는다.
- macro 평가는 최종 오프라인 참고용으로만 분리해 수행한다(임계값 결정에는 미사용).

## 8. 추론
### 8.1 점수 계산
1. 입력 피처를 학습과 동일 순서로 벡터화
2. scaler 변환
3. `raw_score = -decision_function(x)`
4. min-max 정규화
   - `scaled = max(0, (raw_score - raw_min) / (raw_max - raw_min))`
5. 서비스 점수 변환
   - `model_score_raw = max(0, scaled)`
   - `model_score = model_score_raw / (1 + model_score_raw)`
6. 리스크 점수 정의
   - `risk_score = model_score` (가중 결합 없음)

### 8.2 최종 판정
현재 운영 판정 band:
- `risk_score < 0.50` -> `allow`
- `0.50 <= risk_score < 0.60` -> `challenge`
- `risk_score >= 0.60` -> `block`

구간 설정 이유:
- `0.60`(60점): validation human 분포 상위 5% 지점에 맞춘 경계값이다. 즉, 운영 목표 `Human FPR <= 0.05`를 점수 정책으로 구현한 결과다.
- `0.50`: `block` 직전 위험 신호를 조기 분리하기 위한 완충 구간 시작점이다. 0.50~0.60을 `challenge`로 두어 즉시 차단 대신 추가 검증/리뷰를 수행한다.

## 9. 운영 유의사항
- 검증과 임계값 탐색은 반드시 human-only 원칙을 유지한다.
- macro 데이터는 모델/임계값 선택에 사용하지 않고, 배포 전후 참고 평가로만 분리 관리한다.
- 판정 band 조정 시에는 human FPR 재검증을 함께 수행한다.

## 10. Active 모델 Top Feature (기여도 비율)
아래 표는 현재 active `One-Class SVM`(109개 피처)에 대해, 추론 설명 로직과 동일한 `leave-one-feature-to-baseline` 방식으로 계산한 전역 중요도다.

- 기준 데이터: `test_human 115` + `test_macro 154` (총 269 샘플)
- baseline: `StandardScaler.mean_`
- 기여도 정의: 각 피처를 baseline으로 되돌렸을 때의 raw anomaly score 변화량 절대값
- 비율 정의: `share_of_total_pct = mean_abs_contribution_all / (모든 피처 mean_abs_contribution_all 합)`
- 요약: Top1 `8.80%`, Top5 누적 `31.60%`

| 순위 | Feature | 기여도 비율(%) | mean_abs_contribution(all) |
|---:|---|---:|---:|
| 1 | `perf_avg_mouse_speed` | 8.80 | 0.047023 |
| 2 | `perf_mouse_curvature_rad` | 8.62 | 0.046075 |
| 3 | `captcha_avg_mouse_speed` | 4.77 | 0.025473 |
| 4 | `perf_avg_click_duration` | 4.75 | 0.025353 |
| 5 | `seat_mouse_curvature_rad` | 4.66 | 0.024875 |
| 6 | `captcha_click_count` | 4.58 | 0.024478 |
| 7 | `perf_avg_straightness` | 3.92 | 0.020932 |
| 8 | `perf_mouse_points` | 3.67 | 0.019622 |
| 9 | `seat_avg_mouse_speed` | 3.18 | 0.016977 |
| 10 | `overall_mouse_curvature_rad` | 3.16 | 0.016870 |
| 11 | `seat_details_count` | 2.81 | 0.015024 |
| 12 | `selected_seat_count` | 2.81 | 0.015024 |
| 13 | `queue_avg_mouse_speed` | 2.77 | 0.014797 |
| 14 | `captcha_status_success` | 2.04 | 0.010919 |
| 15 | `captcha_trusted_ratio` | 2.04 | 0.010919 |
