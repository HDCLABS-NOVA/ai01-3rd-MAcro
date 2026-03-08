# Validation/Test 점수 구간별 Macro 비율 분석

## 기준
- 모델: 현재 active runtime 모델 (`main.py`의 `_score_request_risk` 기준 `model_score`)
- 데이터셋: `hybrid_model/data/raw/auto_split`
- 샘플 수:
  - validation: human 115, macro 272 (총 387)
  - test: human 115, macro 272 (총 387)

## 0.1 단위 점수 구간별 Macro 비율

### validation
| score bin | total | macro | macro_ratio |
|---|---:|---:|---:|
| [0.1, 0.2) | 7 | 0 | 0.0000 |
| [0.2, 0.3) | 35 | 0 | 0.0000 |
| [0.3, 0.4) | 44 | 0 | 0.0000 |
| [0.4, 0.5) | 18 | 0 | 0.0000 |
| [0.5, 0.6) | 33 | 26 | 0.7879 |
| [0.6, 0.7) | 250 | 246 | 0.9840 |

### test
| score bin | total | macro | macro_ratio |
|---|---:|---:|---:|
| [0.1, 0.2) | 6 | 0 | 0.0000 |
| [0.2, 0.3) | 39 | 0 | 0.0000 |
| [0.3, 0.4) | 37 | 0 | 0.0000 |
| [0.4, 0.5) | 20 | 0 | 0.0000 |
| [0.5, 0.6) | 30 | 22 | 0.7333 |
| [0.6, 0.7) | 255 | 250 | 0.9804 |

## 정책 구간별 Macro 비율
- 정책 구간: `0~49(정상)`, `50~59(주의)`, `60~100(위험)`
- ratio 기준 구간: `[0.0,0.5)`, `[0.5,0.6)`, `[0.6,1.0]`

### validation
| policy band | total | macro | macro_ratio |
|---|---:|---:|---:|
| [0.0, 0.5) (정상) | 104 | 0 | 0.0000 |
| [0.5, 0.6) (주의) | 33 | 26 | 0.7879 |
| [0.6, 1.0] (위험) | 250 | 246 | 0.9840 |

### test
| policy band | total | macro | macro_ratio |
|---|---:|---:|---:|
| [0.0, 0.5) (정상) | 102 | 0 | 0.0000 |
| [0.5, 0.6) (주의) | 30 | 22 | 0.7333 |
| [0.6, 1.0] (위험) | 255 | 250 | 0.9804 |

## 산출 파일
- `hybrid_model/reports/benchmark/score_bin_macro_ratio_validation_test_active_model.csv`
