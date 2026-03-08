# Three Model Comparison (No Test Leakage Thresholding)

## threshold 정책 (변경)
- **Train**: 모델 학습
- **Validation human**: threshold 결정 (`p95`, 즉 목표 FPR 5%)
- **Test**: 성능 측정만 수행

이제 threshold는 **test를 보지 않고** 결정됩니다.

## 평가 조건
- 데이터 split: `model/data/raw/auto_split_h70_m0001_valmacro`
  - human: `train/validation/test = 535/115/115`
  - macro(test): `272`
- 공통 설정
  - seed: `42`
  - 제외 피처: `browser_*`, `queue_duration_ms`
  - feature 수: `113`

## 결과 (Validation human p95 threshold)
| Model | Threshold (val p95) | Train FPR | Val FPR | Test FPR | Test Macro Recall | Test Macro Precision | Test F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Isolation Forest | 0.599867 | 0.0561 | 0.0522 | 0.0261 | 0.3603 | 0.9703 | 0.5255 |
| One-Class SVM | 1.376491 | 0.0000 | 0.0522 | 0.0522 | 1.0000 | 0.9784 | 0.9891 |
| Deep AutoEncoder | 0.059414 | 0.0467 | 0.0522 | 0.0609 | 0.4743 | 0.9485 | 0.6324 |

## 해석
- 요청하신 원칙대로 threshold를 test와 분리하면, 비교가 누수 없이 공정해집니다.
- 이 조건에서 `One-Class SVM`이 가장 높은 recall/precision을 보입니다.
- `Isolation Forest`는 FPR은 낮지만 recall이 낮습니다.
- `Deep AutoEncoder`는 recall은 IF보다 높지만 test FPR이 5%를 약간 초과합니다.

## 결과 파일
- 통합: `hybrid/three_model_comparison_h70_m0001_val_human_p95.json`
- 기존 비교(다른 정책):
  - `hybrid/three_model_comparison_h70_m0001_no_queue_duration.json`
  - `hybrid/three_model_comparison_h70_m0001_no_queue_duration.json`는 test 기반 최적화가 일부 포함되어, 현재 문서 기준에서는 참고용입니다.

## OCSVM 추가 비교 (macro/A vs macro/B vs A100+B100)

요청하신 추가 실험은 아래 조건으로 진행했습니다.

- 모델: `One-Class SVM`만 사용
- Train: human only (`535`)
- Validation: human only (`115`), threshold는 `validation human p95`
- Test human: `115` 고정
- macro 소스: `hybrid_model/data/macro` (`macro/A=272`, `macro/B=272`)
- 공통 설정: seed `42`, 제외 피처 `browser_*`, `queue_duration_ms`, feature 수 `113`

| Scenario | Test Macro 구성 | Threshold (val p95) | Train FPR | Val FPR | Test FPR | Test Macro Recall | Test Macro Precision | Test F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| test1 | macro/A only (`272`) | 1.376491 | 0.0000 | 0.0522 | 0.0522 | 1.0000 | 0.9784 | 0.9891 |
| test2 | macro/B only (`272`) | 1.376491 | 0.0000 | 0.0522 | 0.0522 | 0.9890 | 0.9782 | 0.9835 |
| test3 | macro/A `100` + macro/B `100` | 1.376491 | 0.0000 | 0.0522 | 0.0522 | 0.9950 | 0.9707 | 0.9827 |

### 해석
- 세 시나리오 모두 human 쪽 FPR은 동일합니다(동일 threshold 적용).
- 성능은 `macro/A only`가 가장 높고, `macro/B only`가 약간 낮습니다.
- `A100+B100 mixed`는 recall은 높지만(0.9950), macro 표본 수가 `200`이라 precision/F1은 `A only` 대비 소폭 낮습니다.

### 추가 결과 파일
- `hybrid/one-class-svm/ocsvm_macroA_macroB_three_tests_valhumanp95.json`

## OCSVM SHAP Feature Importance

동일 조건(Train human only, threshold=validation human p95, 제외 피처=`browser_*`,`queue_duration_ms`)에서
`One-Class SVM`에 대해 SHAP(KernelExplainer) 기반 global 중요도를 계산했습니다.

- 계산 설정(근사):
  - background: train human `30` 샘플
  - explain 대상: test human `60` + macro `60`
  - `nsamples=100`
- threshold: `1.3764911557197184`

### 글로벌 중요도 Top 10 (`mean_abs_shap_all`)
| Rank | Feature | mean_abs_shap_all |
|---:|---|---:|
| 1 | `seat_mouse_curvature_rad` | 0.1151 |
| 2 | `perf_mouse_curvature_rad` | 0.0783 |
| 3 | `perf_avg_mouse_speed` | 0.0767 |
| 4 | `perf_avg_click_duration` | 0.0552 |
| 5 | `seat_details_count` | 0.0318 |
| 6 | `seat_avg_mouse_speed` | 0.0312 |
| 7 | `selected_seat_count` | 0.0302 |
| 8 | `overall_mouse_curvature_rad` | 0.0299 |
| 9 | `perf_avg_straightness` | 0.0298 |
| 10 | `captcha_avg_mouse_speed` | 0.0272 |

### 단일 피처 지배도
| 항목 | 비중 |
|---|---:|
| Top1 feature share | 12.59% |
| Top5 features share | 39.06% |

해석:
- 한 피처가 중요도 대부분을 독점하는 구조는 아닙니다(Top1 12.6%).
- 다만 상위 몇 개 피처(곡률/속도/클릭시간 관련)가 함께 강하게 기여합니다.

### SHAP 결과 파일
- 요약 JSON: `hybrid/analysis/ocsvm_shap_feature_importance_valhumanp95.json`
- Top15 CSV: `hybrid/analysis/ocsvm_shap_top15_valhumanp95.csv`

## Behavior Axis Drop Test (OCSVM)

요청하신 검증으로, 아래 마우스 동역학 축 피처를 전부 제거 후 재학습/재평가했습니다.

- 제거 축:
  - 모든 `*curvature*`
  - 모든 `*mouse_speed*`
  - 모든 `*straightness*`
- 공통 조건은 기존과 동일:
  - Train = human only
  - Threshold = validation human p95
  - Test = human + macro
  - 제외 피처 기본: `browser_*`, `queue_duration_ms`

제거된 피처 수: `17` (113 -> 96)

| Metric | Baseline | Axis Drop | Delta (Drop - Base) |
|---|---:|---:|---:|
| Feature Count | 113 | 96 | -17 |
| Test AUROC | 0.9708 | 0.9667 | -0.0041 |
| Test PR-AUC | 0.9714 | 0.9691 | -0.0023 |
| Test Macro Recall | 0.9945 | 0.9522 | -0.0423 |
| Test Macro Precision | 0.9890 | 0.9923 | +0.0033 |
| Test F1 | 0.9918 | 0.9719 | -0.0199 |
| Test Human FPR | 0.0522 | 0.0348 | -0.0174 |

해석:
- AUC는 소폭 하락에 그쳐 완전 붕괴는 아닙니다.
- 다만 recall/F1 하락이 분명해, 모델이 해당 동역학 축에 의미 있게 의존하고 있습니다.
- 즉 단일 규칙 1개 의존이라기보다, 여러 축 중 동역학 축이 성능에 크게 기여하는 구조입니다.

### Axis Drop 결과 파일
- `hybrid/analysis/ocsvm_behavior_axis_drop_test.json`
