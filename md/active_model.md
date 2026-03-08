# Active 모델 전처리 및 피처 엔지니어링

## 1) 현재 Active 모델 요약

- active 모델 타입: `oneclass_svm`
- active 파라미터 파일: `model/artifacts/active/human_model_params.json`
- active 아티팩트 파일: `model/artifacts/active/human_model_oneclass_svm.joblib`
- 선택 리포트: `hybrid_model/reports/benchmark/if_ocsvm_profilemix_inferred_fpr005_selection.json`
- feature 개수: `109`개 (`feature_order` 기준)

학습/선택 리포트 기준(선택 시점):
- threshold policy: `macro_constrained`
- model selection policy: `validation_macro`
- FPR target: `0.05`

---

## 2) 입력 로그 전처리

브라우저 로그(JSON) 1건마다 아래 순서로 전처리됩니다.

1. 안전 캐스팅
- `safe_float`, `safe_bool`로 누락/비정상 값을 `0.0` 또는 `False`로 정규화

2. 단계(stage) 분리
- `perf`, `queue`, `captcha`, `seat` 4개 stage를 각각 처리

3. 이벤트 파싱
- 클릭 이벤트(`clicks`)
- 마우스 궤적(`mouse_trajectory`)
- 호버 이벤트(`hover_events`, `hover_summary`)

4. 통계 계산
- 평균/표준편차/분산/백분위수(`p50`, `p95`) 등 수치 피처 계산

---

## 3) 피처 엔지니어링 (브라우저 기준)

### 3-1. Stage 공통 피처 (`perf_*`, `queue_*`, `captcha_*`, `seat_*`)

각 stage마다 동일한 구조로 생성:

- 기본 활동량
  - `*_duration_ms`
  - `*_click_count`
  - `*_mouse_points`
- 클릭 특성
  - `*_avg_click_duration`, `*_std_click_duration`
  - `*_trusted_ratio`
  - `*_avg_click_interval`, `*_std_click_interval`
  - `*_reaction_time_var_ms2`
  - `*_click_tempo_entropy`
- 마우스 이동 특성
  - `*_avg_mouse_speed`, `*_std_mouse_speed`
  - `*_avg_straightness`
  - `*_mouse_curvature_rad`
- 호버 특성
  - `*_hover_count`, `*_hover_unique_targets`
  - `*_hover_avg_dwell_ms`, `*_hover_std_dwell_ms`
  - `*_hover_p50_dwell_ms`, `*_hover_p95_dwell_ms`
  - `*_hover_revisit_rate`
  - `*_hover_to_click_ms_p50`
  - `*_hover_trusted_ratio`
  - `*_hover_unique_grades`
- 클릭/호버 비율
  - `*_click_to_hover_ratio`

### 3-2. 전체(Overall) 피처

4개 stage 평균으로 생성:

- `overall_reaction_time_var_ms2`
- `overall_click_tempo_entropy`
- `overall_mouse_curvature_rad`

### 3-3. 메타 피처

로그 metadata/stage 요약에서 생성:

- `total_duration_ms`
- `selected_seat_count`
- `seat_details_count`
- `is_completed`
- `completion_status_success`
- `perf_actions_count`
- `captcha_status_success`
- (원본 생성은 되지만 현재 active에서 제거되는 항목은 아래 4장 참고)

---

## 4) Active 모델에서 제거한 피처

학습/평가/배포 전 구간에 동일하게 제거:

### 4-1. prefix 제거
- `browser_*`
  - `browser_webdriver`
  - `browser_hardware_concurrency`
  - `browser_screen_ratio`
  - `browser_screen_w`
  - `browser_screen_h`

### 4-2. 이름 지정 제거
- `booking_flow_started`
- `queue_duration_ms`
- `queue_position_delta`
- `queue_position_updates_count`
- `queue_total_queue`

즉, 추론 시에도 이 피처들은 `feature_order`에 없어서 사용되지 않습니다.

---

## 5) 벡터화/스케일링/스코어링

## 5-1. 벡터화

- `feature_order` 순서대로 고정 벡터 생성
- 누락 피처는 `0.0`으로 채움

## 5-2. 스케일링

- `human_model_oneclass_svm.joblib` 내부 `StandardScaler`로 변환

## 5-3. 원시 이상치 점수(raw)

- One-Class SVM 출력 사용:
  - `raw_score = -decision_function(x)`

## 5-4. 정규화 점수(model_score_raw)

- 파라미터의 `raw_min`, `raw_max`로 min-max:
  - `max(0, (raw_score - raw_min) / (raw_max - raw_min))`
- upper clip은 하지 않음(1 초과 가능)

## 5-5. 최종 `model_score`

- 서버 런타임에서 추가 squash 적용:
  - `model_score = raw / (1 + raw)` (0~1 범위로 완만히 압축)

---

## 6) 운영 의사결정 임계값

- 기본 정책 임계값:
  - `allow`: `0.50`
  - `challenge`: `0.60`
- 이 값은 환경변수로 override 가능:
  - `RISK_ALLOW_THRESHOLD`
  - `RISK_CHALLENGE_THRESHOLD`

참고:
- `human_model_thresholds.json` 파일은 존재하지만,
- 현재 런타임 기본 decision 흐름은 정책 고정값(`0.50/0.60`)을 우선 사용합니다.

---

## 7) 한 줄 정리

현재 active 모델은 `oneclass_svm`이며, 브라우저/큐 메타 일부(`browser_*`, queue 관련 4개 + `booking_flow_started`)를 제외한 109개 행동 피처를 사용해 이상치 점수를 계산합니다.
