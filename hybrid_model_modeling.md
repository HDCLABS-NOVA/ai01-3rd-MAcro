# hybrid_model 데이터 전처리 및 피처 엔지니어링 상세 가이드

## 1. 문서 목적
이 문서는 `hybrid_model/src` 기준으로, 로그 데이터가 모델 입력으로 변환되는 전처리/피처 엔지니어링 과정을 상세 정리한다.

- 대상 범위: `hybrid_model` 파이프라인
- 핵심 파일:
  - `hybrid_model/src/data_prep/*.py`
  - `hybrid_model/src/features/feature_pipeline.py`
  - `hybrid_model/src/training/compare_and_select.py`

---

## 2. 전체 흐름 요약
처리 순서는 아래와 같다.

1. 원본 로그 수집
2. (선택) unified raw 로그를 train/validation/test로 분할
3. (선택) human queue 체류시간 보정
4. (선택) 큐 프로파일 기반 재분할
5. 브라우저 로그에서 피처 추출
6. 학습용 row 구성, 피처 필터링, 행렬화

---

## 3. 데이터 전처리 상세

## 3-1. 원본 로그 구조와 기본 경로

- 브라우저 로그: `hybrid_model/data/raw/.../*.json`
- 서버 로그: `hybrid_model/data/raw/server/*.json`
- ETL 설정 파일: `hybrid_model/configs/data_paths.yaml`

`data_paths.yaml` 기본값:
- `etl_input_roots`: `hybrid_model/data/raw/train`, `hybrid_model/data/raw/validation`, `hybrid_model/data/raw/test`
- `etl_input_glob`: `**/*.json`
- `etl_output_root`: `hybrid_model/data/prepared`

---

## 3-2. unified raw -> split 분할 (`split_unified_raw.py`)

파일: `hybrid_model/src/data_prep/split_unified_raw.py`

기본 입력:
- human: `hybrid_model/data/raw/human`
- macro: `hybrid_model/data/raw/macro`

기본 출력:
- `hybrid_model/data/raw/auto_split/{train,validation,test}/{human,macro}`

핵심 로직:

1. 비율 기반 split count 계산
- human 기본 비율: `7:1.5:1.5`
- macro 기본 비율: `0:5:5`
- largest remainder 방식으로 정수 개수 배분

2. stratified 분할
- human 기본 키: `metadata.user_email`
- macro 기본 키: `metadata.bot_type`
- 그룹별 비율 배분 + 전역 보정으로 split 총합 정합

3. 산출물
- split 파일 복사
- `split_manifest.json` 생성(비율, 그룹 분포, 파일 목록 포함)

---

## 3-3. auto split 후 macro eval downsample (`compare_and_select.py`)

파일: `hybrid_model/src/training/compare_and_select.py`

auto split 활성 시:
1. `run_unified_split()` 호출
2. validation/test macro를 고정 개수로 downsample

관련 옵션:
- `--auto-split-macro-eval-count` (기본 115)

특징:
- `bot_type` 그룹 비율을 최대한 유지하는 비례 샘플링

---

## 3-4. human queue duration 보정 (`normalize_human_queue_duration.py`)

파일: `hybrid_model/src/data_prep/normalize_human_queue_duration.py`

기본 대상:
- `hybrid_model/data/raw/train/human`
- `hybrid_model/data/raw/validation/human`
- `hybrid_model/data/raw/test/human`

전략:

1. `legacy_short_only` (기본)
- 비정상적으로 짧은 queue outlier를 감지해 wait/duration 재계산
- `exit_time`, `metadata.total_duration_ms`까지 일관 보정

2. `enforce_early_shorter`
- 그룹 내 entry가 빠를수록 wait가 짧도록 단조 증가 방식 재할당

주의:
- 원본 JSON rewrite 방식이므로 `--dry-run` 확인 후 적용 권장

---

## 3-5. 큐 프로파일 재분할 (`rebalance_dataset_splits.py`)

파일: `hybrid_model/src/data_prep/rebalance_dataset_splits.py`

역할:
- queue 관련 프로파일 분포를 기준으로 split을 재구성

프로파일:
- `queue_duration_ms` 기반 `dur_short/long`
- `queue_position_delta` 기반 `pos_short/long`
- 조합: `dur_<...>|pos_<...>`

---

## 3-6. ETL 데이터셋 빌드 (`build_dataset.py`)

파일: `hybrid_model/src/data_prep/build_dataset.py`

주요 처리:

1. 입력 스캔
- `etl_input_roots` + `etl_input_glob` 사용
- JSON 파싱 실패는 quality report에 기록

2. row 구성
- 메타 필드:
  - `split`, `label`, `source_path`, `flow_id`, `session_id`,
    `performance_id`, `booking_id`, `bot_type`, `completion_status`, `is_completed`
- 피처 필드:
  - `extract_browser_features()` 결과 전체

3. 출력
- 그룹별: `features.jsonl`, `features.csv`
- 전체: `all_features.jsonl`, `all_features.csv`
- 메타/품질:
  - `feature_schema.json`
  - `quality_report.json`
  - `dataset_manifest.json`

---

## 3-7. 브라우저/서버 로그 조인 (`join_logs.py`)

파일: `hybrid_model/src/data_prep/join_logs.py`

조인 기준:
- `flow_id` 우선
- 없으면 `session_id` fallback

출력:
- `hybrid_model/data/prepared/joined_logs.json`
- `hybrid_model/data/prepared/joined_logs.csv`

비고:
- 학습은 기본 browser-only이므로 조인 결과는 분석/점검 용도 성격이 강함

---

## 4. 피처 엔지니어링 상세

구현 파일: `hybrid_model/src/features/feature_pipeline.py`

## 4-1. 기본 원칙

1. 결측 안전 처리
- `safe_float`, `safe_bool`, `safe_mean/std/var/percentile`

2. 4개 stage 공통 추출
- `perf`, `queue`, `captcha`, `seat`

3. browser-only / browser+server 모두 지원
- 기본은 browser-only
- 필요 시 `extract_combined_features()` 사용

---

## 4-2. 핵심 계산식

### 클릭 타임스탬프
- 우선순위:
  1. `timestamp`
  2. `relative_ms_from_entry`
  3. `event_time_epoch_ms`

### 클릭 템포 엔트로피 (`*_click_tempo_entropy`)
- 클릭 간격(`>0`)을 로그 스케일 bin에 할당
- bin: `[40, 80, 160, 320, 640, 1280, 2560, inf]`
- 정규화 entropy 계산

### 마우스 속도 (`*_avg_mouse_speed`, `*_std_mouse_speed`)
- 연속 궤적 점 간 `dist/dt` (`dt>0`)

### 궤적 직진성 (`*_avg_straightness`)
- 시작~끝 직선거리 / 전체 경로거리

### 궤적 곡률 (`*_mouse_curvature_rad`)
- 3점 기반 연속 방향 전환각 절댓값 평균(rad)

### 반응시간 분산 (`*_reaction_time_var_ms2`)
- click 시각 대비 직전 move 시각 latency의 분산

---

## 4-3. hover 파생 피처

`hover_events` + `hover_summary`를 결합해 생성:

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

추가:
- `click_to_hover_ratio = click_count / hover_count` (`hover_count==0`이면 0)

---

## 4-4. stage별 피처 개수

각 stage마다 25개 피처 생성:
- duration/click/mouse 기초 통계
- click interval/tempo/reaction 계열
- mouse speed/straightness/curvature 계열
- hover 계열 + click_to_hover_ratio

총 stage 피처:
- `25 x 4 = 100`

---

## 4-5. stage 통합/메타/브라우저 피처

추가 피처:

1. overall 통합(3)
- `overall_reaction_time_var_ms2`
- `overall_click_tempo_entropy`
- `overall_mouse_curvature_rad`

2. 도메인/메타(11)
- `total_duration_ms`, `selected_seat_count`, `seat_details_count`
- `is_completed`, `booking_flow_started`, `completion_status_success`
- `perf_actions_count`, `queue_position_delta`, `queue_total_queue`,
  `queue_position_updates_count`, `captcha_status_success`

3. 브라우저 fingerprint(5)
- `browser_webdriver`
- `browser_hardware_concurrency`
- `browser_screen_ratio`
- `browser_screen_w`
- `browser_screen_h`

browser raw 피처 수:
- `100 + 3 + 11 + 5 = 119`

---

## 4-6. 서버 피처(선택)

`extract_server_features()`:
- `srv_latency_ms`
- `srv_status_code`
- `srv_body_size_bytes`
- `srv_requests_last_1s`
- `srv_requests_last_10s`
- `srv_requests_last_60s`
- `srv_unique_endpoints_last_60s`

`extract_combined_features()` 사용 시 최대:
- `119 + 7 = 126`

---

## 5. 학습 직전 피처 필터링/행렬화

파일: `hybrid_model/src/training/compare_and_select.py`

1. `load_feature_rows()`
- 로그마다 `extract_browser_features()` 호출

2. macro bot_type 필터(옵션)
- `--macro-bot-types` 지정 시 validation/test macro를 bot_type 기준 필터링

3. 피처 제거
- prefix 제거: `--drop-feature-prefixes`
- exact name 제거: `--drop-feature-names` (기본 `["queue_duration_ms"]`)
- 내부 함수: `_drop_selected_features()`

4. 행렬화
- `feature_order`(union+sort) 생성
- 미존재 피처는 0.0으로 채워 `rows_to_matrix()`

---

## 6. hybrid_model 선택 정책/옵션 차이(중요)

`hybrid_model`의 `compare_and_select.py`는 아래 정책 옵션을 제공한다.

1. threshold policy
- `--threshold-policy`
- choices: `human_percentile`, `macro_constrained`

2. model selection policy
- `--model-selection-policy`
- choices: `validation_human_only`, `validation_macro`

3. macro subtype 제어
- `--macro-bot-types`로 특정 bot_type만 평가 가능

즉, `model` 대비 검증/선정 정책 제어가 더 세분화되어 있다.

---

## 7. 현재 active hybrid_model 기준 실제 사용 피처

파일: `hybrid_model/artifacts/active/human_model_params.json`

현재 값:
- `model_type`: `oneclass_svm`
- `feature_order` 길이: `113`
- `drop_feature_prefixes`: `["browser_"]`
- `drop_feature_names`: `["queue_duration_ms"]`

해석:
- raw 119개에서 `browser_*` 5개와 `queue_duration_ms` 1개를 제외해 113개 사용

---

## 8. 재현용 실행 예시

### 8-1. unified split
```bash
python hybrid_model/src/data_prep/split_unified_raw.py \
  --human-dir hybrid_model/data/raw/human \
  --macro-dir hybrid_model/data/raw/macro \
  --out-root hybrid_model/data/raw/auto_split \
  --human-ratio 7:1.5:1.5 \
  --macro-ratio 0:5:5 \
  --seed 42 \
  --overwrite
```

### 8-2. queue 보정
```bash
python hybrid_model/src/data_prep/normalize_human_queue_duration.py \
  --strategy legacy_short_only
```

### 8-3. ETL 데이터셋 생성
```bash
python hybrid_model/src/data_prep/build_dataset.py \
  --config hybrid_model/configs/data_paths.yaml \
  --dataset-id latest
```

### 8-4. 모델 학습/선정
```bash
python hybrid_model/src/training/compare_and_select.py \
  --threshold-policy human_percentile \
  --model-selection-policy validation_human_only \
  --drop-feature-prefixes browser_ \
  --drop-feature-names queue_duration_ms
```

---

## 9. 운영 체크포인트

1. queue 보정 여부와 split 버전 일치 관리
2. auto split seed/ratio/stratify key를 manifest로 고정
3. `feature_schema.json`으로 피처 스키마 drift 모니터링
4. `human_model_params.json.feature_order`와 서빙 피처명 정합성 점검
