# 리스크 스코어링 설계 (하이브리드: 룰 + 사람-전용 이상탐지)

## 목표
서버 + 클라이언트 텔레메트리를 결합해 `risk_score` (0~1)를 만들고 `allow/challenge/block` 의사결정에 사용한다.

## 데이터 소스
1. **클라이언트(프론트)**: `log_structure.json`
2. **서버**: `server_log_structure.json`

## 스코어 구성 요소
### 1) 룰 점수 (R)
명확한 악성 신호를 룰로 빠르게 잡는다.

초기 룰(임계값 예시):
- `concurrent_sessions_same_device >= 3` => +0.35
- `concurrent_sessions_same_ip >= 10` 그리고 같은 subnet => +0.35
- `requests_last_1s >= 10` 이 3회 이상 반복 => +0.25
- `captcha_required = true` 이고 `captcha_passed = false` 3회 => +0.30
- `queue.poll_interval_ms_stats.p50 < 200` 그리고 `queue.jump_count > 0` => +0.25
- `seat.reserve_attempt_count >= 10` 그리고 동일 실패 코드 반복 => +0.20

룰 점수는 1.0을 넘지 않도록 캡한다.

### 2) 모델 점수 (M)
사람 데이터만으로 학습한 이상탐지 모델의 점수.

모델 출력은 0~1로 정규화되어야 한다:
- 예: IsolationForest anomaly_score -> min-max 정규화
- 예: Autoencoder reconstruction error -> human-only validation으로 캘리브레이션

### 3) 컨텍스트 점수 (C)
분포 이동을 완화하기 위한 보정값.

예시:
- 오픈 직후/피크 시간대 => -0.05 (오탐 완화)
- 서버 지연 급증 => -0.05
- 의심 ASN 반복 => +0.05

## 최종 리스크 점수
`risk_score = clamp(wR*R + wM*M + wC*C, 0, 1)`

초기 가중치:
- wR = 0.5
- wM = 0.4
- wC = 0.1

## 의사결정 정책
- `risk_score < 0.30` => allow
- `0.30 <= risk_score < 0.70` => challenge
- `risk_score >= 0.70` => block

## 사람 로그 기반 임계값 (현재 데이터 기준)
`logs/real_human` 기준으로 산출된 모델 임계값:
- FPR 0.5%: `0.7277`
- FPR 1.0%: `0.3623`
- FPR 2.0%: `0.2809`
- FPR 5.0%: `0.2096`

운영 기본 매핑(초기값):
- `allow` 임계값 = FPR 1.0% (0.3623)
- `challenge` 임계값 = FPR 0.5% (0.7277)

## 운영 노트
- 애매한 구간은 차단보다 **challenge 우선**이 안전하다.
- 이벤트 타입/트래픽 상황에 따라 임계값을 재조정해야 한다.
- 감사/분석을 위해 `risk.rules_triggered[]`를 기록한다.

---

# 다음 단계
1. 사람 전용 이상탐지 모델(예: IsolationForest/Autoencoder) 구축
2. 룰 엔진 + 모델 스코어러 구현
3. 기존 로그로 백테스트
4. FPR 목표를 기준으로 임계값/가중치 튜닝

# 실행 가이드
0. 모델 비교 후 자동 선택(권장)
   - `py model\src\training\compare_and_select.py --human-dir logs\real_human --macro-dir logs\macro_v2 --server-dir model\data\raw\server`
   - 생성 파일:
     - `model/reports/benchmark/model_benchmark_results.csv`
     - `model/reports/benchmark/model_selection.json`
     - `model/artifacts/active/human_model_params.json` (선택된 모델)
     - `model/artifacts/active/human_model_thresholds.json`
     - `model/artifacts/active/model_manifest.json`

1. 모델 파라미터 생성
   - `py model\src\training\build_human_model.py`
   - 생성 파일: `model/artifacts/active/human_model_params.json`, `model/artifacts/active/human_model_thresholds.json`, `model/reports/scoring/human_only_scores.csv`

2. 단일 로그 스코어링
   - `py model\src\serving\risk_scorer.py --front-log <front_log.json> --server-log <server_log.json>`

3. 배치 스코어링 (CSV 출력)
   - `py model\src\serving\risk_scorer.py --front-dir logs\real_human --server-dir model\data\raw\server --out model\reports\scoring\risk_scores.csv`
   - 컨텍스트가 있으면: `--context-log <context.json>`

4. 서버 런타임 연동(main.py)
   - `POST /api/logs` 처리 시 서버 로그 생성 직전에 룰+모델 리스크를 계산해 `risk` 필드에 저장
   - 상태 확인: `GET /api/risk/runtime-status`
   - 운영 튜닝(환경변수):
     - `RISK_WEIGHT_RULE` (기본 `0.5`)
     - `RISK_WEIGHT_MODEL` (기본 `0.4`)
     - `RISK_ALLOW_THRESHOLD` (기본 `0.30`)
     - `RISK_CHALLENGE_THRESHOLD` (기본 `0.70`)

