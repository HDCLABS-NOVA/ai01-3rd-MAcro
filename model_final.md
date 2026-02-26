# 모델 최종 통합 문서 (model + result)

이 문서는 `model.md` 본문과 `hybrid_model/result.md`의 상세 성능 결과를 통합한 최종 버전이다.

---

## 1. 모델 파이프라인 본문 (from model.md)

# 매크로 탐지 모델 파이프라인 정리 (최신 반영)

## 1. 문서 범위
이 문서는 `hybrid_model/data`를 사용해 재학습한 최신 실험 기준으로, 데이터 수집부터 전처리, 피처 엔지니어링, 학습/검증/테스트, 추론 연계까지를 정리한다.

- 실험 모델: `isolation_forest` (one-class)
- 실험 기준 파일:
  - `hybrid_model/reports/benchmark/model_selection_hybrid_if.json`
  - `hybrid_model/result.md`
  - `hybrid_model/artifacts/active/human_model_params.json`
  - `hybrid_model/artifacts/active/human_model_thresholds.json`

---

## 2. 데이터 수집

### 2-1. 브라우저 로그
- 클라이언트가 예매 과정에서 사용자 행동 로그를 수집해 `POST /api/logs`로 전송한다.
- 로그에는 단계별(`perf`, `queue`, `captcha`, `seat`) 클릭, 마우스 궤적, hover, 체류시간, 메타데이터가 포함된다.

### 2-2. 서버 로그
- 서버 로그는 별도 수집 API를 직접 호출하는 방식이 아니라, FastAPI 미들웨어(`@app.middleware("http")`)에서 `/api/*` 요청 응답 후 자동 기록되는 구조다.
- 즉, API 흐름이 진행되는 동안 요청 단위로 계속 누적된다.

---

## 3. 전처리

### 3-1. 데이터 분할
고정 split 데이터를 사용했다.

- train: `hybrid_model/data/auto_split/train/human` (human 535)
- validation:
  - `hybrid_model/data/auto_split/validation/human` (human 115)
  - `hybrid_model/data/auto_split/validation/macro` (macro 272)
- test:
  - `hybrid_model/data/auto_split/test/human` (human 115)
  - `hybrid_model/data/auto_split/test/macro` (macro 272)

### 3-2. 피처 행 구성
- 각 로그 JSON마다 `extract_browser_features()`로 feature row를 생성한다.
- `drop_feature_prefixes=["browser_"]`를 적용한다.
- 누락 feature는 `0.0`으로 채운다.

---

## 4. 피처 엔지니어링 (수정 반영)

구현 파일: `model/src/features/feature_pipeline.py`

### 4-1. 기존 핵심 피처
- 단계별 기본 행동 통계: `*_duration_ms`, `*_click_count`, `*_mouse_points`
- 클릭 템포/분산: `*_avg_click_interval`, `*_std_click_interval`, `*_avg_click_duration`, `*_std_click_duration`
- 마우스 이동: `*_avg_mouse_speed`, `*_std_mouse_speed`, `*_avg_straightness`
- hover 탐색: `*_hover_count`, `*_hover_unique_targets`, `*_hover_revisit_rate`, `*_hover_*`
- 도메인 파생: `queue_position_delta`, `queue_position_updates_count`, `selected_seat_count`, `captcha_status_success` 등

### 4-2. 이번 개선으로 추가된 신규 피처
정상/매크로 분포 겹침을 줄이기 위해 아래 3종을 단계별(`perf`, `queue`, `captcha`, `seat`)로 추가했다.

1. 반응시간 분산  
- 필드: `*_reaction_time_var_ms2`
- 의미: 클릭 시점과 직전 마우스 이동 시점의 차이(반응 지연)의 분산
- 기대효과: 사람/매크로의 반응 리듬 차이를 분산 관점에서 분리

2. 클릭 템포 엔트로피  
- 필드: `*_click_tempo_entropy`
- 의미: 클릭 간격 분포의 엔트로피(정규화)
- 기대효과: 지나치게 일정한 템포(자동화)와 자연스러운 템포 다양성(사람) 분리

3. 마우스 궤적 곡률  
- 필드: `*_mouse_curvature_rad`
- 의미: 연속 이동 벡터의 평균 꺾임 각도(rad)
- 기대효과: 직선적/기계적 궤적과 사람형 궤적 구분 강화

### 4-3. 전체 요약 피처 추가
- `overall_reaction_time_var_ms2`
- `overall_click_tempo_entropy`
- `overall_mouse_curvature_rad`

### 4-4. 최종 feature 차원
- raw feature 수: `119`
- `browser_*` 5개 제외 후 학습 입력: `114`

---

## 5. 학습

구현 파일: `model/src/training/compare_and_select.py`

- 학습 데이터: human train만 사용(one-class 학습)
- 모델: `IsolationForest(n_estimators=300, contamination="auto", random_state=42)`
- 스케일링: `StandardScaler`
- 스코어 정규화: 학습 분포의 `raw_min`, `raw_max` 기반
  - `raw_min=-0.15623300749120594`
  - `raw_max=0.11109434566253529`

---

## 6. 검증/테스트 성능 (최신)

### 6-1. 모델 선택 기준 성능 (`fpr_target=0.01`)
`model_selection_hybrid_if.json` 기준.

- 선택 threshold: `0.746057`
- Validation:
  - AUROC/PR-AUC: `0.9578 / 0.9664`
  - human FPR: `0.0087`
  - macro recall: `0.0919`
  - precision/F1: `0.9615 / 0.1678`
- Test:
  - AUROC/PR-AUC: `0.9732 / 0.9716`
  - human FPR: `0.0087`
  - macro recall: `0.0809`
  - precision/F1: `0.9565 / 0.1492`

설명:
- 이 기준은 "human 오탐 최소화(약 1%)"를 우선 보장하는 보수적 운영점이다.

### 6-2. 임계값 스윕 기준 성능 (운영 튜닝 관점)
`hybrid_model/result.md` 기준, threshold를 0.05 단위로 낮춰 평가.

1. F1 최대 운영점  
- threshold: `0.446057`
- Validation: human FPR `0.1478`, macro recall `0.9926`, F1 `0.9660`
- Test: human FPR `0.1304`, macro recall `0.9926`, F1 `0.9695`

2. `human_fpr<=0.05` 제약 운영점  
- threshold: `0.596057`
- Validation: human FPR `0.0435`, macro recall `0.6507`, F1 `0.7797`
- Test: human FPR `0.0261`, macro recall `0.6654`, F1 `0.7939`

---

## 7. 모델 해석 (SHAP / Cumulative SHAP)

### 7-1. SHAP Feature Importance (active 모델 기준)
이번 실험에서는 active IsolationForest 모델(입력 feature 114개)을 대상으로 SHAP을 계산해, 어떤 feature가 모델 점수 형성에 크게 기여하는지 확인했다. 평가 데이터는 `hybrid_model/data/auto_split`의 validation+test를 합친 구간(human 230, macro 300)이며, scaled feature 기준으로 `shap.TreeExplainer(IsolationForest)`를 적용했다. SHAP 결과에서 상위 기여 feature는 `seat_mouse_curvature_rad`(0.22726720), `perf_avg_mouse_speed`(0.21647129), `seat_details_count`(0.20397054), `captcha_trusted_ratio`(0.19121194), `perf_mouse_curvature_rad`(0.18965747) 순으로 나타났다. 즉, 이번에 추가한 곡률 기반 feature가 최상위권에 위치했고, 속도/궤적/행동 성공 여부 신호가 함께 상위권에 분포하면서 단일 지표가 아닌 복합 행동 패턴으로 human/macro를 분리하고 있음을 확인할 수 있다.

### 7-2. Cumulative SHAP
Cumulative SHAP은 `mean_abs_shap_all`을 내림차순으로 정렬해 누적 설명력을 본 지표다. 현재 결과에서는 상위 30개 feature에서 누적 설명력 80%(cumulative 0.8022)에 도달하고, 상위 41개에서 90%(0.9009), 상위 49개에서 95%(0.9548), 상위 57개에서 99%(0.9915)에 도달한다. 이는 전체 설명력이 특정 소수 feature에만 과도하게 몰려 있지 않으면서도, 상위 feature 집합이 모델 의사결정을 대부분 설명한다는 뜻이다. 실무적으로는 상위 30~50개 feature를 우선 관리 대상으로 두고, 나머지 하위 feature를 단계적으로 축소하는 경량화 실험을 설계할 수 있다.

---

## 8. 운영 임계값 해석

- 현재 active threshold 파일(`human_model_thresholds.json`)은 FPR 중심(보수적) 값이다.
- F1 최대 운영을 쓰려면 `human_model_thresholds_optimal_f1_0_446057.json` 같은 별도 threshold를 적용해야 한다.
- 즉, 운영 목적에 따라 threshold 정책을 분리해야 한다.
  - 오탐 최소화 우선: 보수 threshold
  - 탐지율/재현율 우선: F1 최대 threshold

---

## 9. 추론 연계 (서버)

구현 파일: `main.py`

- 기본 위험도 가중치:
  - model: `0.8`
  - rule: `0.2`
- 기본 의사결정 임계값:
  - allow: `0.30`
  - challenge: `0.70`

주의:
- 서버(`main.py`)는 기본적으로 `model/artifacts/active/*`를 읽는다.
- 이번 실험 산출물은 `hybrid_model/artifacts/active/*`에 있으므로, 실제 운영 반영 시 경로 통일(복사 또는 코드 경로 변경)이 필요하다.

---

## 2. Threshold Sweep 상세 결과 (from hybrid_model/result.md)

# Threshold Sweep Result (Isolation Forest)

## 설정
- 데이터: `hybrid_model/data` (고정 split: `hybrid_model/data/auto_split`)
- 모델: `isolation_forest`
- 기준 임계값(start): `0.746057`
- 스윕 방식: 임계값을 `0.05(=5%p)`씩 낮춤, 마지막 `0.0` 포함
- 검증 샘플 수: human `115`, macro `272`
- 테스트 샘플 수: human `115`, macro `272`

## 최적 성능 지표
- AUROC/PR-AUC (threshold 무관):
  - Validation: `0.9578` / `0.9664`
  - Test: `0.9732` / `0.9716`

| 기준 | split | threshold | human_fpr | macro_recall | precision | f1 | tp | fp | tn | fn |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F1 최대 | Validation | 0.446057 | 0.1478 | 0.9926 | 0.9408 | 0.9660 | 270 | 17 | 98 | 2 |
| F1 최대 | Test | 0.446057 | 0.1304 | 0.9926 | 0.9474 | 0.9695 | 270 | 15 | 100 | 2 |
| human_fpr<=0.05에서 recall 최대 | Validation | 0.596057 | 0.0435 | 0.6507 | 0.9725 | 0.7797 | 177 | 5 | 110 | 95 |
| human_fpr<=0.05에서 recall 최대 threshold 적용 | Test | 0.596057 | 0.0261 | 0.6654 | 0.9837 | 0.7939 | 181 | 3 | 112 | 91 |

## Validation (Threshold ↓ by 0.05)
| threshold | human_fpr | macro_recall | precision | f1 | tp | fp | tn | fn |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.746057 | 0.0087 | 0.0919 | 0.9615 | 0.1678 | 25 | 1 | 114 | 247 |
| 0.696057 | 0.0261 | 0.2390 | 0.9559 | 0.3824 | 65 | 3 | 112 | 207 |
| 0.646057 | 0.0348 | 0.4228 | 0.9664 | 0.5882 | 115 | 4 | 111 | 157 |
| 0.596057 | 0.0435 | 0.6507 | 0.9725 | 0.7797 | 177 | 5 | 110 | 95 |
| 0.546057 | 0.0609 | 0.8272 | 0.9698 | 0.8929 | 225 | 7 | 108 | 47 |
| 0.496057 | 0.0870 | 0.9485 | 0.9627 | 0.9556 | 258 | 10 | 105 | 14 |
| 0.446057 | 0.1478 | 0.9926 | 0.9408 | 0.9660 | 270 | 17 | 98 | 2 |
| 0.396057 | 0.1913 | 1.0000 | 0.9252 | 0.9611 | 272 | 22 | 93 | 0 |
| 0.346057 | 0.2348 | 1.0000 | 0.9097 | 0.9527 | 272 | 27 | 88 | 0 |
| 0.296057 | 0.2522 | 1.0000 | 0.9037 | 0.9494 | 272 | 29 | 86 | 0 |
| 0.246057 | 0.2870 | 1.0000 | 0.8918 | 0.9428 | 272 | 33 | 82 | 0 |
| 0.196057 | 0.3565 | 1.0000 | 0.8690 | 0.9299 | 272 | 41 | 74 | 0 |
| 0.146057 | 0.5130 | 1.0000 | 0.8218 | 0.9022 | 272 | 59 | 56 | 0 |
| 0.096057 | 0.7913 | 1.0000 | 0.7493 | 0.8567 | 272 | 91 | 24 | 0 |
| 0.046057 | 0.9913 | 1.0000 | 0.7047 | 0.8267 | 272 | 114 | 1 | 0 |
| 0.000000 | 1.0000 | 1.0000 | 0.7028 | 0.8255 | 272 | 115 | 0 | 0 |

## Test (Threshold ↓ by 0.05)
| threshold | human_fpr | macro_recall | precision | f1 | tp | fp | tn | fn |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.746057 | 0.0087 | 0.0809 | 0.9565 | 0.1492 | 22 | 1 | 114 | 250 |
| 0.696057 | 0.0087 | 0.2316 | 0.9844 | 0.3750 | 63 | 1 | 114 | 209 |
| 0.646057 | 0.0174 | 0.4632 | 0.9844 | 0.6300 | 126 | 2 | 113 | 146 |
| 0.596057 | 0.0261 | 0.6654 | 0.9837 | 0.7939 | 181 | 3 | 112 | 91 |
| 0.546057 | 0.0609 | 0.8713 | 0.9713 | 0.9186 | 237 | 7 | 108 | 35 |
| 0.496057 | 0.0783 | 0.9559 | 0.9665 | 0.9612 | 260 | 9 | 106 | 12 |
| 0.446057 | 0.1304 | 0.9926 | 0.9474 | 0.9695 | 270 | 15 | 100 | 2 |
| 0.396057 | 0.1565 | 1.0000 | 0.9379 | 0.9680 | 272 | 18 | 97 | 0 |
| 0.346057 | 0.2174 | 1.0000 | 0.9158 | 0.9561 | 272 | 25 | 90 | 0 |
| 0.296057 | 0.2696 | 1.0000 | 0.8977 | 0.9461 | 272 | 31 | 84 | 0 |
| 0.246057 | 0.3043 | 1.0000 | 0.8860 | 0.9396 | 272 | 35 | 80 | 0 |
| 0.196057 | 0.3739 | 1.0000 | 0.8635 | 0.9267 | 272 | 43 | 72 | 0 |
| 0.146057 | 0.5130 | 1.0000 | 0.8218 | 0.9022 | 272 | 59 | 56 | 0 |
| 0.096057 | 0.7913 | 1.0000 | 0.7493 | 0.8567 | 272 | 91 | 24 | 0 |
| 0.046057 | 0.9913 | 1.0000 | 0.7047 | 0.8267 | 272 | 114 | 1 | 0 |
| 0.000000 | 1.0000 | 1.0000 | 0.7028 | 0.8255 | 272 | 115 | 0 | 0 |

## SHAP Feature Importance (Active Model)
- 기준 모델: `model/artifacts/active/human_model_params.json` (IsolationForest, feature 114개)
- 평가 데이터: `hybrid_model/data/auto_split`의 validation+test
  - human `230`, macro `300`
- 계산 방식: `shap.TreeExplainer(IsolationForest)` (scaled feature 기준)
- decision_function 평균:
  - human: `0.096996`
  - macro: `-0.013984`

### Top 10 (mean |SHAP|, 전체 기준)
| rank | feature | mean_abs_shap_all |
|---:|---|---:|
| 1 | seat_mouse_curvature_rad | 0.22726720 |
| 2 | perf_avg_mouse_speed | 0.21647129 |
| 3 | seat_details_count | 0.20397054 |
| 4 | captcha_trusted_ratio | 0.19121194 |
| 5 | perf_mouse_curvature_rad | 0.18965747 |
| 6 | captcha_status_success | 0.18401894 |
| 7 | perf_avg_straightness | 0.15797146 |
| 8 | selected_seat_count | 0.15734269 |
| 9 | queue_total_queue | 0.13798143 |
| 10 | captcha_click_count | 0.13371800 |

## Cumulative SHAP 요약
- 80% 누적 설명력: rank `30` (`seat_avg_click_interval`), cumulative `0.8022`
- 90% 누적 설명력: rank `41` (`captcha_std_mouse_speed`), cumulative `0.9009`
- 95% 누적 설명력: rank `49` (`captcha_avg_straightness`), cumulative `0.9548`
- 99% 누적 설명력: rank `57` (`queue_avg_click_duration`), cumulative `0.9915`

- 상세 파일:
  - `hybrid_model/reports/benchmark/shap_feature_importance_active_model.csv`
  - `hybrid_model/reports/benchmark/shap_feature_importance_active_model.md`
  - `hybrid_model/reports/benchmark/shap_feature_importance_active_model_cumulative.csv`
  - `hybrid_model/reports/benchmark/shap_feature_importance_active_model_cumulative.md`

## 요약
- Validation AUROC/PR-AUC (threshold 무관): `0.9578` / `0.9664`
- Test AUROC/PR-AUC (threshold 무관): `0.9732` / `0.9716`
- Validation F1 최대: threshold `0.446057`, F1 `0.9660`, human_fpr `0.1478`
- Validation human_fpr<=0.05 조건에서 recall 최대: threshold `0.596057`, recall `0.6507`, FPR `0.0435`
- Test F1 최대: threshold `0.446057`, F1 `0.9695`, human_fpr `0.1304`
- SHAP Top feature: `seat_mouse_curvature_rad`, `perf_avg_mouse_speed`, `seat_details_count`
- 누적 SHAP 기준 전체 설명력 80%는 상위 `30`개 feature에서 확보
