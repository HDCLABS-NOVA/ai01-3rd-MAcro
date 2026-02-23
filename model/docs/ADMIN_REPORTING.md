# 관리자 리포트 파이프라인

`model/src/reporting/build_admin_reports.py`는 세션/계정 단위 리포트를 생성합니다.

## 배치 실행

```bash
python model/src/reporting/build_admin_reports.py \
  --browser-dir model/data/raw/browser \
  --server-dir model/data/raw/server \
  --out-session model/reports/admin/session_reports.json \
  --out-account model/reports/admin/account_reports.json \
  --out-block-dir model/block_report
```

## 배치 출력

- `model/reports/admin/session_reports.json`
  - 세션 단위 리포트
- `model/reports/admin/account_reports.json`
  - 계정 단위 집계 리포트

## 실시간 차단 리포트

서버에서 `POST /api/logs`가 실시간 `block`이면 즉시 저장됩니다.

- 단건 파일: `model/block_report/<YYYYMMDD>/<YYYYMMDD>_block_req_<id>.json`
- 인덱스: `model/block_report/index.jsonl`

## 사후 차단 리포트

배치 리포트 실행 시 아래 조건의 세션을 `model/block_report`에 추가 저장합니다.

- `decision == "block"` 이거나
- `rule_evidence.block_recommended == true`

저장 경로:

- 단건 파일: `model/block_report/posthoc/<YYYYMMDD>/<YYYYMMDD>_posthoc_block_<flow_id>.json`
- 인덱스: `model/block_report/index.jsonl` ( `report_stage: "posthoc"` )

## 공통 리포트 구조(요약)

- `user_id`
- `booking_id`
- `risk_summary.total_score`, `risk_summary.grade`
- `evidence_logs.rule`
- `evidence_logs.model.anomaly_score`, `evidence_logs.model.top_features`
- `evidence_logs.behavior`
- `evidence_logs.trust`
