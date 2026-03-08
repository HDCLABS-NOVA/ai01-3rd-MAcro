# DB 설계 문서 (운영 최소안, v3)

## 1) 범위
- 현재 기준: **모델 재학습 파이프라인 없음**
- 목적: 실시간 탐지 운영, 리포트 조회, 감사 로그 보존
- 원칙: raw 로그는 JSONB 원문 저장 + 조회용 핵심 컬럼만 분리

---

## 2) 이번 버전에서 제거한 항목
재학습 파이프라인이 없으므로 아래는 스키마에서 제거한다.

1. `ml_feature_rows`
2. `ml_dataset_snapshots`
3. `ml_model_registry`
4. `dataset_split_type` enum

---

## 3) 유지 테이블

1. `users`
2. `performances`
3. `bookings`
4. `browser_logs_raw`
5. `server_logs_raw`
6. `risk_decisions`
7. `risk_reports`

---

## 4) PostgreSQL DDL (최소 운영안)

```sql
-- PostgreSQL 16+
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE risk_decision_type AS ENUM ('allow', 'challenge', 'block');

-- =========================================================
-- 0) 기본 운영 도메인
-- =========================================================
CREATE TABLE users (
    user_id          BIGSERIAL PRIMARY KEY,
    email            TEXT NOT NULL UNIQUE,
    password_hash    TEXT NOT NULL,
    name             TEXT NOT NULL,
    phone            TEXT,
    role             TEXT NOT NULL DEFAULT 'user',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE performances (
    performance_id   TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    category         TEXT NOT NULL,
    venue            TEXT NOT NULL,
    open_time        TIMESTAMPTZ,
    status           TEXT NOT NULL DEFAULT 'upcoming',
    payload_jsonb    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE bookings (
    booking_id       TEXT PRIMARY KEY,
    user_id          BIGINT REFERENCES users(user_id),
    performance_id   TEXT REFERENCES performances(performance_id),
    status           TEXT NOT NULL DEFAULT 'completed',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload_jsonb    JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_bookings_user_id
    ON bookings (user_id);
CREATE INDEX idx_bookings_performance_id
    ON bookings (performance_id);
CREATE INDEX idx_bookings_created_at
    ON bookings (created_at DESC);

-- =========================================================
-- 1) Raw Logs
-- =========================================================
CREATE TABLE browser_logs_raw (
    browser_log_id     BIGSERIAL PRIMARY KEY,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    flow_id            TEXT,
    session_id         TEXT,
    request_id         TEXT,
    performance_id     TEXT,
    user_email         TEXT,
    bot_type           TEXT,
    completion_status  TEXT,
    is_completed       BOOLEAN,
    booking_id         TEXT,
    payload_jsonb      JSONB NOT NULL
);

CREATE INDEX idx_browser_logs_raw_created_at
    ON browser_logs_raw (created_at DESC);
CREATE INDEX idx_browser_logs_raw_flow_id
    ON browser_logs_raw (flow_id);
CREATE INDEX idx_browser_logs_raw_request_id
    ON browser_logs_raw (request_id);
CREATE INDEX idx_browser_logs_raw_bot_type_created
    ON browser_logs_raw (bot_type, created_at DESC);
CREATE INDEX idx_browser_logs_raw_payload_gin
    ON browser_logs_raw USING GIN (payload_jsonb);

CREATE TABLE server_logs_raw (
    server_log_id       BIGSERIAL PRIMARY KEY,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_id            TEXT UNIQUE,
    request_id          TEXT UNIQUE,
    flow_id             TEXT,
    session_id          TEXT,
    performance_id      TEXT,
    endpoint            TEXT,
    method              TEXT,
    status_code         INTEGER,
    ip_hash             TEXT,
    user_agent_hash     TEXT,
    decision_hint       risk_decision_type,
    risk_score_hint     NUMERIC(10,6),
    payload_jsonb       JSONB NOT NULL
);

CREATE INDEX idx_server_logs_raw_created_at
    ON server_logs_raw (created_at DESC);
CREATE INDEX idx_server_logs_raw_request_id
    ON server_logs_raw (request_id);
CREATE INDEX idx_server_logs_raw_flow_id
    ON server_logs_raw (flow_id);
CREATE INDEX idx_server_logs_raw_endpoint_method_created
    ON server_logs_raw (endpoint, method, created_at DESC);
CREATE INDEX idx_server_logs_raw_payload_gin
    ON server_logs_raw USING GIN (payload_jsonb);

-- =========================================================
-- 2) Risk Decision + Report
-- =========================================================
CREATE TABLE risk_decisions (
    risk_decision_id     BIGSERIAL PRIMARY KEY,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_id           TEXT NOT NULL UNIQUE,
    flow_id              TEXT,
    session_id           TEXT,
    user_email           TEXT,
    booking_id           TEXT,
    decision             risk_decision_type NOT NULL,
    risk_score           NUMERIC(10,6),
    rule_score           NUMERIC(10,6),
    model_score          NUMERIC(10,6),
    model_type           TEXT,
    rules_triggered      JSONB NOT NULL DEFAULT '[]'::jsonb,
    hard_rules_triggered JSONB NOT NULL DEFAULT '[]'::jsonb,
    runtime_error        TEXT,
    threshold_allow      NUMERIC(10,6),
    threshold_challenge  NUMERIC(10,6),
    report_id            TEXT
);

CREATE INDEX idx_risk_decisions_created_at
    ON risk_decisions (created_at DESC);
CREATE INDEX idx_risk_decisions_decision_created
    ON risk_decisions (decision, created_at DESC);
CREATE INDEX idx_risk_decisions_flow_id
    ON risk_decisions (flow_id);
CREATE INDEX idx_risk_decisions_booking_id
    ON risk_decisions (booking_id);

CREATE TABLE risk_reports (
    risk_report_id       BIGSERIAL PRIMARY KEY,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    report_id            TEXT NOT NULL UNIQUE,
    request_id           TEXT,
    flow_id              TEXT,
    session_id           TEXT,
    booking_id           TEXT,
    user_email           TEXT,
    decision             risk_decision_type NOT NULL,
    recommendation       risk_decision_type,
    risk_score           NUMERIC(10,6),
    model_score          NUMERIC(10,6),
    rule_score           NUMERIC(10,6),
    suspicion_level      TEXT,
    llm_used             BOOLEAN NOT NULL DEFAULT FALSE,
    llm_model            TEXT,
    report_version       TEXT NOT NULL DEFAULT 'realtime_risk_v1',
    report_jsonb         JSONB NOT NULL,
    llm_jsonb            JSONB
);

CREATE INDEX idx_risk_reports_created_at
    ON risk_reports (created_at DESC);
CREATE INDEX idx_risk_reports_decision_created
    ON risk_reports (decision, created_at DESC);
CREATE INDEX idx_risk_reports_booking_id
    ON risk_reports (booking_id);
CREATE INDEX idx_risk_reports_request_id
    ON risk_reports (request_id);
CREATE INDEX idx_risk_reports_report_json_gin
    ON risk_reports USING GIN (report_jsonb);
```

---

## 5) 연결(FK) 정책
- 현재 버전은 대량 로그 적재 안정성을 위해 `raw/risk` 영역 FK를 최소화한다.
- 즉, `request_id`, `flow_id`, `booking_id`로 논리 조인(soft link)한다.
- 강한 FK가 필요해지면 다음을 추가한다.
  1. `risk_decisions.request_id -> server_logs_raw.request_id`
  2. `risk_reports.request_id -> server_logs_raw.request_id`
  3. `risk_reports.report_id -> risk_decisions.report_id` (정책 합의 시)

---

## 6) 마이그레이션 체크
1. 파일 저장은 유지하고 DB 미러링부터 시작
2. `server_logs_raw`, `browser_logs_raw` 우선 적재
3. 파생 저장기로 `risk_decisions`, `risk_reports` 적재
4. 운영 대시보드/API 조회를 DB로 단계 전환

---

## 7) 추후 재학습 도입 시
- 재학습 파이프라인이 생기면 아래 3개를 다시 추가한다.
  1. `ml_feature_rows`
  2. `ml_dataset_snapshots`
  3. `ml_model_registry`

