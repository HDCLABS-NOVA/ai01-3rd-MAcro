# 모델링 데이터 전처리 및 피처 엔지니어링 상세 가이드

## 1. 문서 목적
이 문서는 현재 저장소의 실제 구현(`model/src`) 기준으로, 로그 데이터가 모델 입력으로 변환되는 과정을 상세히 정리한다.

- 대상 범위: `model` 파이프라인
- 핵심 파일:
  - `model/src/data_prep/*.py`
  - `model/src/features/feature_pipeline.py`
  - `model/src/training/compare_and_select.py`

참고: `hybrid_model`도 구조와 로직이 거의 동일하며, 주 차이는 import 경로와 기본 입출력 루트(`model/...` vs `hybrid_model/...`)다.

---

## 2. 전체 흐름 요약
로그 전처리와 피처 생성은 아래 순서로 진행된다.

1. 원본 로그 수집
2. (선택) unified raw 로그를 train/validation/test로 분할
3. (선택) human queue 체류시간 보정
4. (선택) 큐 프로파일 기반 재분할
5. 브라우저 로그에서 피처 추출
6. 학습용 행(row) 구성, 피처 필터링, 행렬화

---

## 3. 데이터 전처리 상세

## 3-1. 원본 로그 구조와 기본 경로

- 브라우저 로그(행동 로그): `model/data/raw/.../*.json`
- 서버 로그(요청/응답 로그): `model/data/raw/server/*.json`
- ETL 기본 설정 파일: `model/configs/data_paths.yaml`

`data_paths.yaml` 기본값:
- `etl_input_roots`: `model/data/raw/train`, `model/data/raw/validation`, `model/data/raw/test`
- `etl_input_glob`: `**/*.json`
- `etl_output_root`: `model/data/prepared`

즉, 기본 ETL은 이미 split된 폴더를 입력으로 본다.

---

## 3-2. unified raw -> split 분할 (`split_unified_raw.py`)

파일: `model/src/data_prep/split_unified_raw.py`

기본 입력:
- human: `model/data/raw/human`
- macro: `model/data/raw/macro`

기본 출력:
- `model/data/raw/auto_split/{train,validation,test}/{human,macro}`

핵심 로직:

1. 비율 파싱
- human 기본 비율: `7:1.5:1.5`
- macro 기본 비율: `0:5:5`
- `_allocate_counts()`에서 largest remainder 방식으로 정수 개수 배분

2. 계층(stratified) 분할
- human 기본 키: `metadata.user_email`
- macro 기본 키: `metadata.bot_type`
- 키 조합별 그룹을 만든 뒤 그룹 내부에서도 비율 배분
- 전역 보정으로 split 총합이 정확히 target count와 일치하도록 조정

3. 파일 복사 및 검증
- split/class별 폴더로 파일 복사
- class 내부 중복 배정 검사
- `split_manifest.json` 생성

산출물:
- `split_manifest.json`에 입력 개수, 비율, stratify 그룹 분포, split별 파일 리스트 저장

---

## 3-3. 자동 분할 후 macro eval downsample (`compare_and_select.py`)

파일: `model/src/training/compare_and_select.py`

`--disable-auto-split-unified`를 주지 않고 unified dir가 존재하면:
1. `run_unified_split()`을 호출해 auto split 생성
2. validation/test macro를 고정 개수로 downsample
- 옵션: `--auto-split-macro-eval-count` (기본 `115`)
- bot_type 그룹 비율을 유지하도록 비례 샘플링

목적:
- macro eval 셋 크기를 고정해 실험 변동성 감소

---

## 3-4. human queue duration 보정 (`normalize_human_queue_duration.py`)

파일: `model/src/data_prep/normalize_human_queue_duration.py`

기본 대상:
- `model/data/raw/train/human`
- `model/data/raw/validation/human`
- `model/data/raw/test/human`

전략 1: `legacy_short_only` (기본)
- `queue.duration_ms < short_threshold_ms(기본 1200)`이면서
- `total_queue <= 1`, `initial-final position_delta <= 1`인 short outlier를 탐지
- flow_id 기반 deterministic hash로 `wait_duration_ms`를 재생성
- `duration_ms`, `exit_time`, `metadata.total_duration_ms`를 함께 보정

전략 2: `enforce_early_shorter`
- 그룹 단위(기본: `date_perf_total_queue`)에서
- entry_time이 빠른 레코드일수록 wait가 짧도록 단조 증가 타깃 wait를 재할당
- 그룹 최소 샘플 수 옵션(`--min-group-size`) 제공

주의:
- 원본 JSON을 직접 rewrite하므로 `--dry-run` 확인 후 적용 권장

---

## 3-5. 큐 프로파일 재분할 (`rebalance_dataset_splits.py`)

파일: `model/src/data_prep/rebalance_dataset_splits.py`

역할:
- 이미 split된 데이터에서 큐 특성 프로파일 분포를 맞춰 재분배

프로파일 정의:
- `queue_duration_ms`로 `dur_short/long`
- `queue_position_delta`로 `pos_short/long`
- 최종 태그: `dur_<short|long>|pos_<short|long>`

특징:
- 현재 스크립트는 데이터 수를 고정값으로 가정
  - human 765
  - macro 544
- human: train 555 / val 105 / test 105
- macro: val 272 / test 272

---

## 3-6. ETL 데이터셋 빌드 (`build_dataset.py`)

파일: `model/src/data_prep/build_dataset.py`

주요 처리:

1. 입력 스캔
- 설정 파일의 `etl_input_roots` + `etl_input_glob`로 JSON 탐색
- JSON 파싱 실패는 `quality_report`에 기록

2. 브라우저 로그 판별
- payload가 dict이고 `stages` 키가 있어야 유효 브라우저 로그로 처리

3. row 생성
- 메타 필드:
  - `split`, `label`, `source_path`, `flow_id`, `session_id`,
    `performance_id`, `booking_id`, `bot_type`, `completion_status`, `is_completed`
- 피처:
  - `extract_browser_features()` 결과 전체

4. 그룹 산출
- 경로 기반 `(split, label)` 그룹으로 묶어 파일 생성
  - `features.jsonl`
  - `features.csv`

5. 전체 산출
- `all_features.jsonl`, `all_features.csv`
- `feature_schema.json`
- `quality_report.json`
- `dataset_manifest.json`

---

## 3-7. 브라우저/서버 로그 조인 (`join_logs.py`)

파일: `model/src/data_prep/join_logs.py`

역할:
- 브라우저 로그와 서버 로그를 `flow_id` 우선, 없으면 `session_id`로 매칭
- 조인 결과를 분석 편의용으로 저장:
  - `model/data/prepared/joined_logs.json`
  - `model/data/prepared/joined_logs.csv`

비고:
- 현재 모델 학습 입력은 browser-only가 기본이므로, 이 조인 결과는 주로 분석/검증 용도다.

---

## 4. 피처 엔지니어링 상세

구현 파일: `model/src/features/feature_pipeline.py`

## 4-1. 기본 설계 원칙

1. 결측/이상치 안전 처리
- `safe_float`, `safe_bool`, `safe_mean/std/var/percentile`로 기본값 처리
- 계산 불가 시 `0.0` 또는 안정값 반환

2. 단계별 공통 추출
- `perf`, `queue`, `captcha`, `seat` 4개 stage에 동일한 규칙 적용

3. 브라우저 단독 + 서버 결합 모두 지원
- 기본 학습은 browser-only
- 필요 시 `extract_combined_features()`로 서버 피처 추가 가능

---

## 4-2. 시간/궤적 파생 계산식

### 클릭 시각 추출
- 우선순위:
  1. `click.timestamp`
  2. `click.relative_ms_from_entry`
  3. `click.event_time_epoch_ms`
- 추출 후 오름차순 정렬

### 클릭 간격
- `click_intervals[i] = click_ts[i] - click_ts[i-1]`

### 클릭 템포 엔트로피 (`*_click_tempo_entropy`)
- 유효 간격(`>0`)만 사용
- bin: `[40, 80, 160, 320, 640, 1280, 2560, inf]` ms
- 정규화 엔트로피:
  - `H = -sum(p_i log2 p_i)`
  - `H_norm = H / log2(num_bins)`

### 마우스 속도 (`*_avg_mouse_speed`, `*_std_mouse_speed`)
- trajectory 연속점 `(x,y,t)`에서
  - `dist = sqrt((dx)^2 + (dy)^2)`
  - `speed = dist / dt` (`dt > 0`)

### 궤적 직진성 (`*_avg_straightness`)
- `direct_distance / path_length`
- 점 2개 미만이면 1.0

### 궤적 곡률 (`*_mouse_curvature_rad`)
- 3점 단위 연속 벡터 각도 `acos(cos_theta)`의 절댓값 평균
- 유효 turn이 없으면 0.0

### 반응시간 분산 (`*_reaction_time_var_ms2`)
- 각 click 시각 기준, 직전 mouse move 시각을 bisect로 탐색
- latency = `click_ts - latest_move_ts_before_click` (`>=0`)
- latency 분산 사용

---

## 4-3. hover 파생 피처 (`_extract_hover_features`)

입력:
- `stage_data.hover_events`
- `stage_data.hover_summary`

생성 피처:
- `hover_count`
- `hover_unique_targets`
- `hover_avg_dwell_ms`
- `hover_std_dwell_ms`
- `hover_p50_dwell_ms`
- `hover_p95_dwell_ms`
- `hover_revisit_rate`
- `hover_to_click_ms_p50`
- `hover_trusted_ratio`
- `hover_unique_grades`

fallback 규칙:
- `hover_events`가 부족하면 `hover_summary` 값을 사용
- revisit_rate가 summary에 없으면
  - `(hover_count - unique_targets) / hover_count`로 계산

추가 파생:
- `click_to_hover_ratio = click_count / hover_count` (`hover_count==0`이면 0)

---

## 4-4. stage별 피처 목록

각 stage(`perf/queue/captcha/seat`)마다 아래 25개 피처가 생성된다.

1. `<stage>_duration_ms`
2. `<stage>_click_count`
3. `<stage>_mouse_points`
4. `<stage>_avg_click_duration`
5. `<stage>_std_click_duration`
6. `<stage>_trusted_ratio`
7. `<stage>_avg_click_interval`
8. `<stage>_std_click_interval`
9. `<stage>_reaction_time_var_ms2`
10. `<stage>_click_tempo_entropy`
11. `<stage>_avg_mouse_speed`
12. `<stage>_std_mouse_speed`
13. `<stage>_avg_straightness`
14. `<stage>_mouse_curvature_rad`
15. `<stage>_hover_count`
16. `<stage>_hover_unique_targets`
17. `<stage>_hover_avg_dwell_ms`
18. `<stage>_hover_std_dwell_ms`
19. `<stage>_hover_p50_dwell_ms`
20. `<stage>_hover_p95_dwell_ms`
21. `<stage>_hover_revisit_rate`
22. `<stage>_hover_to_click_ms_p50`
23. `<stage>_hover_trusted_ratio`
24. `<stage>_hover_unique_grades`
25. `<stage>_click_to_hover_ratio`

총합:
- stage 피처 25 x 4 = 100개

---

## 4-5. stage 통합/메타 피처

추가 피처:

1. stage 통합 통계(3개)
- `overall_reaction_time_var_ms2`
- `overall_click_tempo_entropy`
- `overall_mouse_curvature_rad`

2. 도메인/메타 피처(11개)
- `total_duration_ms`
- `selected_seat_count`
- `seat_details_count`
- `is_completed`
- `booking_flow_started`
- `completion_status_success`
- `perf_actions_count`
- `queue_position_delta`
- `queue_total_queue`
- `queue_position_updates_count`
- `captcha_status_success`

3. 브라우저 fingerprint 피처(5개)
- `browser_webdriver`
- `browser_hardware_concurrency`
- `browser_screen_ratio`
- `browser_screen_w`
- `browser_screen_h`

브라우저 전용 raw 피처 수:
- `100 + 3 + 11 + 5 = 119`

---

## 4-6. 서버 피처 (선택)

`extract_server_features()`는 아래 7개를 생성한다.

- `srv_latency_ms`
- `srv_status_code`
- `srv_body_size_bytes`
- `srv_requests_last_1s`
- `srv_requests_last_10s`
- `srv_requests_last_60s`
- `srv_unique_endpoints_last_60s`

`extract_combined_features()`를 쓰면
- `browser(119) + server(7) = 최대 126개`

현재 학습 기본값은 browser-only다.

---

## 5. 학습 직전 피처 필터링과 행렬화

파일: `model/src/training/compare_and_select.py`

1. `load_feature_rows()`
- JSON마다 `extract_browser_features()` 호출
- row 구조: `path`, `flow_id`, `features`

2. prefix 기반 제거
- `--drop-feature-prefixes`로 시작 문자열 일치 피처 제거
- train/val/test 모두 동일하게 적용

3. feature order 생성
- 전체 row의 key union을 정렬해 `feature_order` 구성

4. 행렬화
- `rows_to_matrix()`에서 `feature_order` 순으로 벡터화
- 없는 피처는 0.0으로 채움

---

## 6. 현재 active 모델 기준 실제 사용 피처

파일: `model/artifacts/active/human_model_params.json`

현재 기록값:
- `feature_order` 길이: `113`
- `drop_feature_prefixes`: `["browser_", "queue_duration_ms"]`

해석:
- raw 119개 중
  - `browser_` 계열 5개 제외
  - `queue_duration_ms` 1개 제외
- 최종 113개 사용

---

## 7. 재현용 실행 예시

### 7-1. unified raw 분할
```bash
python model/src/data_prep/split_unified_raw.py \
  --human-dir model/data/raw/human \
  --macro-dir model/data/raw/macro \
  --out-root model/data/raw/auto_split \
  --human-ratio 7:1.5:1.5 \
  --macro-ratio 0:5:5 \
  --seed 42 \
  --overwrite
```

### 7-2. human queue 보정(legacy)
```bash
python model/src/data_prep/normalize_human_queue_duration.py \
  --strategy legacy_short_only
```

### 7-3. ETL 피처 데이터셋 생성
```bash
python model/src/data_prep/build_dataset.py \
  --config model/configs/data_paths.yaml \
  --dataset-id latest
```

### 7-4. 모델 학습/선정
```bash
python model/src/training/compare_and_select.py \
  --drop-feature-prefixes browser_ queue_duration_ms
```

---

## 8. 운영 시 체크포인트

1. `queue_duration_ms` 보정 여부
- 보정 스크립트 적용 전/후 데이터가 섞이지 않게 split 기준 통일 필요

2. auto split 재현성
- `seed`, stratify key, ratio를 manifest와 함께 고정 관리

3. feature drift 감시
- `feature_schema.json`의 필드 변화 여부를 버전 단위로 기록

4. 학습/서빙 피처 일치성
- `human_model_params.json.feature_order`와 런타임 추출 피처명이 정확히 일치해야 함

