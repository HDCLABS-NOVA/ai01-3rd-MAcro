# Two-Model Threshold Comparison (human FPR <= 0.03)

## 1) 데이터 사용 기준
- 기준 데이터셋: `model/data/prepared/latest`
- 메타 정보: `model/data/prepared/latest/dataset_manifest.json`
- 이번 비교에 사용한 평가셋:
  - `test/human`: 115건
  - `test/macro`: 272건

## 2) 전처리 및 피처 엔지니어링 기준
1. 브라우저 로그를 `feature_pipeline`에서 단계별(`perf/queue/captcha/seat`) 통계 피처로 변환
   - 예: 클릭 간격 평균/표준편차, 마우스 속도 평균/표준편차, straightness, curvature(rad), hover dwell 통계, click-to-hover ratio
   - 참고 코드: `model/src/features/feature_pipeline.py`
2. 단계 피처 외에 overall/메타 피처 포함
   - 예: `overall_click_tempo_entropy`, `overall_mouse_curvature_rad`, `total_duration_ms`, `selected_seat_count` 등
3. 비교 시점에는 이미 생성된 `prepared/latest/test/*/features.jsonl`을 그대로 사용
   - 즉, 추가 재가공 없이 모델별 `feature_order`에 맞춰 벡터화
4. 모델별 입력 정렬/스케일
   - One-Class SVM:
     - params: `model/artifacts/active/human_model_params.json`
     - artifact: `model/artifacts/active/human_model_oneclass_svm.joblib`
   - Isolation Forest:
     - params: `model/artifacts/runs/20260226T085803Z_isolation_forest/human_model_params.json`
     - artifact: `model/artifacts/active/human_model_isolation_forest.joblib`
5. 점수 산출식(현재 런타임 로직 기준)
   - `raw_anomaly = -decision_function(x)`
   - `normalized = max(0, (raw_anomaly - raw_min) / (raw_max - raw_min))`
   - `model_score = normalized / (1 + normalized)`  (squash)

## 3) 임계값 탐색 규칙
- 후보 threshold: 두 클래스(test human+macro) score 유니크값 전체 + `{1.0, 0.0}`
- 제약 조건: `human_fpr <= 0.03`
- 최적값 선택: 제약 만족 후보 중 `macro_f1` 최대
  - tie-break: `macro_recall` > `macro_precision` > 낮은 `human_fpr`

## 4) 결과 표 (최적 threshold)

| model | optimal_threshold | human_fpr | macro_recall | macro_precision | macro_f1 | tp | fp | tn | fn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| one_class_svm | 0.639498 | 0.026087 | 0.650735 | 0.983333 | 0.783186 | 177 | 3 | 112 | 95 |
| isolation_forest | 0.375094 | 0.026087 | 0.573529 | 0.981132 | 0.723898 | 156 | 3 | 112 | 116 |

## 5) 요약
- 동일 제약(`human_fpr <= 0.03`)에서 One-Class SVM이 Isolation Forest 대비 `macro_recall`, `macro_f1`이 더 높게 나왔음.
- 두 모델 모두 최적 지점에서 precision은 약 0.98 수준으로 높게 유지됨.
