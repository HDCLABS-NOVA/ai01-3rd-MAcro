# test/macro vs val/macro 비교

데이터 소스: `model/data/prepared/latest/all_features.csv`  
비교 대상: `bot_type = val/macro (n=272)` vs `bot_type = test/macro (n=272)`

## 비교 기준

- 평균 클릭 간격: `perf_avg_click_interval`, `seat_avg_click_interval`
- 클릭 간격 분산: 원본에 분산 컬럼이 없어 `std_click_interval^2`를 분산 proxy로 사용
- 세션 총 시간: `total_duration_ms`
- 마우스 이동 직선성: `perf_avg_straightness`, `seat_avg_straightness`
- 통계 검정: Mann-Whitney U (two-sided), 효과크기 보조지표로 Cliff's delta

## 결과 요약

| 지표 | val/macro 평균 | test/macro 평균 | 변화율 (test-val) | p-value | Cliff's delta |
|---|---:|---:|---:|---:|---:|
| perf 평균 클릭 간격 (ms) | 194.62 | 175.24 | -9.96% | 9.175e-07 | 0.243 |
| seat 평균 클릭 간격 (ms) | 327.34 | 263.76 | -19.42% | 7.385e-11 | 0.323 |
| perf 클릭 간격 분산 proxy (`perf_std_click_interval^2`) | 4,077.25 | 1,086.09 | -73.36% | 1.670e-33 | 0.598 |
| seat 클릭 간격 분산 proxy (`seat_std_click_interval^2`) | 55,738.24 | 22,228.67 | -60.12% | 1.702e-27 | 0.536 |
| 세션 총 시간 (ms) | 17,963.77 | 16,341.53 | -9.03% | 8.099e-29 | 0.552 |
| perf 마우스 직선성 | 0.7524 | 0.6882 | -8.53% | 4.119e-08 | 0.272 |
| seat 마우스 직선성 | 0.5487 | 0.4447 | -18.95% | 4.366e-08 | 0.271 |

## 해석

- `test/macro`는 `val/macro` 대비 클릭 간격이 더 짧아 전체적으로 더 빠르게 동작한다.
- `test/macro`는 클릭 간격 분산(proxy)도 크게 낮아 리듬이 더 일정하다.
- 세션 총 시간도 `test/macro`가 더 짧다.
- 직선성은 `test/macro`가 더 낮다(경로가 상대적으로 덜 직선적).
- 위 핵심 지표들은 모두 유의미한 차이를 보였다(`p < 0.001` 수준).

## 참고 (queue 구간)

`queue_avg_click_interval`, `queue_std_click_interval`, `queue_avg_straightness`는 두 그룹 모두 상수에 가까웠다.

- `queue_avg_click_interval = 0` (양쪽 동일)
- `queue_std_click_interval = 0` (양쪽 동일)
- `queue_avg_straightness = 1` (양쪽 동일)

즉, 현재 차이는 주로 `perf`/`seat`/`total_duration` 구간에서 발생한다.
