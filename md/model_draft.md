# 모델 정의서 및 성능 평가서 (초안)

작성일: 2026-02-24  
대상 프로젝트: `ai01-3rd-3team-1`

## 1. 목적

티켓팅 과정에서 사용자 행동 로그를 기반으로 자동화(매크로) 의심 세션을 탐지하고,  
`allow / challenge / block` 의사결정을 지원한다.

- 1차: 룰 기반 점수(`rule_score`)
- 2차: 모델 기반 이상치 점수(`model_score`)
- 최종: 결합 위험 점수(`risk_score`)

---

## 2. 현재 운영 구조

### 2.1 입력 로그

- 브라우저 로그: `model/data/raw/browser/...`
- 서버 로그: `model/data/raw/server/...`

### 2.2 점수 산식

`main.py` 기준:

- `model_score = clamp01((raw_score - raw_min) / (raw_max - raw_min))`
- `rule_score = clamp01(soft_rule_sum)`
- `risk_score = clamp01(0.8 * model_score + 0.2 * rule_score)`  
  (`RISK_WEIGHT_MODEL`, `RISK_WEIGHT_RULE` 환경변수로 조정 가능)

### 2.3 판정 정책

- 기본 임계값(정책 고정):  
  - `risk < 0.30` -> `allow`
  - `0.30 <= risk < 0.70` -> `challenge`
  - `risk >= 0.70` -> `block`
- 하드룰(`security.blocked=true`) 발생 시 즉시 `block` 우선
- `RISK_BLOCK_AUTOMATION=false`면 모델 단독 `block`은 `challenge`로 강등 가능

---

## 3. 데이터 정의 및 스플릿 정책

## 3.1 통합 원천 폴더

- Human: `model/data/raw/human`
- Macro: `model/data/raw/macro`

## 3.2 자동 스플릿 정책

`model/src/data_prep/split_unified_raw.py`, `compare_and_select.py` 기준:

- Human 비율: `7:1.5:1.5` (train/validation/test)
- Macro 비율: `0:5:5` (train 미사용, val/test만)
- 기본 seed: `42`
- Stratify:
  - Human: `metadata.user_email`
  - Macro: `metadata.bot_type`
- 평가 안정화:
  - val/test macro를 기본 `115`개로 다운샘플 (`--auto-split-macro-eval-count=115`)

즉, **완전 랜덤이 아니라 seed 기반의 계층화(stratified) 랜덤 분할**이다.

---

## 4. 모델 정의

## 4.1 현재 활성 포인터(문서 시점)

`model/artifacts/active/model_manifest.json`:

- `selected_model`: `isolation_forest`
- `params_path`: `human_model_params_unified_compare.json`
- `thresholds_path`: `human_model_thresholds_unified_compare.json`

## 4.2 학습 피처

- 소스: browser behavior feature
- 총 피처 수: `99`
- 대표 그룹:
  - `captcha_*` 23개
  - `perf_*` 23개
  - `queue_*` 25개
  - `seat_*` 23개
  - 기타: `booking_flow_started`, `completion_status_success`, `is_completed`, `selected_seat_count`, `total_duration_ms`
- `drop_feature_prefixes`: `["browser_"]`

## 4.3 Isolation Forest 하이퍼파라미터

`compare_and_select.py` 기준:

- `n_estimators=300`
- `contamination="auto"`
- `random_state=seed`

---

## 5. 성능 평가 결과

> 아래 결과는 서로 다른 평가 세트/실험 파일에서 가져온 값이다.  
> 운영 의사결정 시에는 **동일 split 조건**에서 비교해야 한다.

## 5.1 활성 선택 리포트 기준 (엄격 설정, fpr_target=1%)

출처: `model/reports/benchmark/model_selection_unified_compare.json`

- split_mode: `explicit_train_val_test`
- 카운트:
  - train human: 535
  - val human: 115
  - val macro(eval): 272
  - test human: 115
  - test macro: 272
- 선택 임계값: `0.8537569681`

검증(Validation):

- Human FPR: `0.87%`
- Macro Recall: `1.84%`
- Macro Precision: `83.33%`
- F1: `3.60%`
- AUROC: `0.9522`

테스트(Test):

- Human FPR: `2.61%`
- Macro Recall: `2.21%`
- Macro Precision: `66.67%`
- F1: `4.27%`
- AUROC: `0.9281`

해석:

- FPR 제약을 강하게 둔 운영점이라 recall이 거의 죽는 상태.

## 5.2 IF 임계값/FPR 타깃 스윕 (val/test macro=115 조건)

출처: `model/reports/benchmark/if_fpr_target_sweep_1_to_10_step_0.5_with_macro_precision.csv`

| fpr_target(%) | threshold | test_human_fpr(%) | test_macro_recall(%) | test_macro_precision(%) | test_f1(%) |
|---:|---:|---:|---:|---:|---:|
| 1.0 | 0.8670 | 0.870 | 0.000 | 0.000 | 0.000 |
| 3.0 | 0.6496 | 3.478 | 40.000 | 92.000 | 55.758 |
| 5.0 | 0.5959 | 5.217 | 71.304 | 93.182 | 80.788 |
| 7.0 | 0.5690 | 6.957 | 84.348 | 92.381 | 88.182 |
| 10.0 | 0.5028 | 10.435 | 96.522 | 90.244 | 93.277 |

해석:

- `human FPR`을 낮추면 `macro recall`이 급격히 감소한다.
- 실무 운영점 후보:
  - 보수형: target 3~5%
  - 공격형: target 7% 이상

## 5.3 모델 대안 비교 (참고 실험, fpr_target=5%)

출처: `model/artifacts/experiments/compare_fpr5/model_benchmark.json`  
조건: train_human=535, val/test_human=115, val/test_macro=115

| 모델 | test_human_fpr(%) | test_macro_recall(%) | test_macro_precision(%) | test_f1(%) |
|---|---:|---:|---:|---:|
| IsolationForest | 5.217 | 71.304 | 93.182 | 80.788 |
| OneClassSVM | 3.478 | 100.000 | 96.639 | 98.291 |
| DeepSVDD | 6.087 | 100.000 | 94.262 | 97.046 |

해석:

- 동일 조건에서는 OneClassSVM/DeepSVDD가 매우 우수하게 나옴.
- 다만 이는 실험 결과이며, 운영 반영 전에는 홀드아웃 재검증이 필요.

---

## 6. 운영 관점 정리

## 6.1 강점

- 룰 + 모델 결합으로 설명성과 탐지 유연성 동시 확보
- 스플릿 stratify 도입으로 분포 왜곡 완화
- macro val/test 샘플 수 고정(115)으로 실험 비교 가능성 개선

## 6.2 주의사항

- `model_manifest.json`과 런타임 로더 경로(`human_model_params.json`)가 다를 수 있어  
  **실제 서버 적용 모델과 벤치마크 보고 모델이 불일치할 위험**이 있음.
- `main.py`는 판정 임계값을 정책 고정(0.30/0.70)으로 사용하며,  
  모델 threshold 파일(`human_model_thresholds*.json`)을 판정 경계로 직접 쓰지 않음.
- 따라서 성능 보고 시:
  - 모델 이상치 임계값(학습/평가용)
  - 운영 risk 임계값(실시간 판정용)
  를 분리해서 관리해야 함.

---

## 7. 권장 후속 작업

1. 운영 기준 통일  
   `model_manifest` 기반으로 런타임 로딩 경로를 일원화.

2. 운영점 확정  
   목표 KPI를 먼저 결정:
   - 예: `test human FPR <= 5%`를 만족하며 `macro recall` 최대화.

3. 재현 가능한 평가 리포트 자동화  
   동일 seed/split으로 다음 항목을 항상 함께 출력:
   - Human FPR
   - Macro Recall
   - Macro Precision
   - Macro F1
   - Confusion Matrix

4. 실시간 정책 분리 문서화  
   - 모델 threshold(탐지 민감도)
   - risk threshold(운영 액션 경계)
   - `RISK_BLOCK_AUTOMATION` 적용 여부

---

## 8. 참고 파일

- 활성 포인터: `model/artifacts/active/model_manifest.json`
- 활성 파라미터(포인터): `model/artifacts/active/human_model_params_unified_compare.json`
- 활성 임계값(포인터): `model/artifacts/active/human_model_thresholds_unified_compare.json`
- 런타임 로더 기본 파라미터: `model/artifacts/active/human_model_params.json`
- 런타임 로더 기본 임계값: `model/artifacts/active/human_model_thresholds.json`
- 선택 리포트: `model/reports/benchmark/model_selection_unified_compare.json`
- IF FPR 스윕: `model/reports/benchmark/if_fpr_target_sweep_1_to_10_step_0.5_with_macro_precision.csv`
- 다중 모델 비교(fpr=5%): `model/artifacts/experiments/compare_fpr5/model_benchmark.json`

