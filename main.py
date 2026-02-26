from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
import re
import time
import uuid
import hashlib
import threading
import urllib.request
import urllib.error
from datetime import datetime, timedelta
import ctypes

import numpy as np

try:
    import joblib
except Exception:
    joblib = None

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    try:
        load_dotenv()
    except Exception:
        pass

app = FastAPI(title="Ticket Booking System")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# logs 디렉토리 생성
LOGS_DIR = os.path.join("model", "data", "raw")
BROWSER_LOGS_DIR = os.path.join(LOGS_DIR, "browser")
SERVER_LOGS_DIR = os.path.join(LOGS_DIR, "server")
BLOCK_REPORT_DIR = os.path.join("model", "block_report")
BLOCK_REPORT_INDEX_JSONL = os.path.join(BLOCK_REPORT_DIR, "index.jsonl")
RULE_SCORE_DIR = os.path.join("model", "rule_score")
MODEL_SCORE_DIR = os.path.join("model", "model_score")
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(BROWSER_LOGS_DIR, exist_ok=True)
os.makedirs(SERVER_LOGS_DIR, exist_ok=True)
os.makedirs(BLOCK_REPORT_DIR, exist_ok=True)
os.makedirs(RULE_SCORE_DIR, exist_ok=True)
os.makedirs(MODEL_SCORE_DIR, exist_ok=True)

try:
    from model.src.features.feature_pipeline import (
        extract_browser_features as _extract_browser_features_runtime,
    )
    from model.src.rules.rule_base import evaluate_rules as _evaluate_rules_runtime
    from model.src.serving.model_explain import (
        top_model_contributors as _model_top_contributors_runtime,
    )
except Exception:
    _extract_browser_features_runtime = None
    _evaluate_rules_runtime = None
    _model_top_contributors_runtime = None

# data 디렉토리 생성
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
RESTRICTED_FILE = os.path.join(DATA_DIR, "restricted_users.json")
HISTORY_FILE = os.path.join(DATA_DIR, "restriction_history.json")

# 사용자 파일이 없으면 초기화
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"users": []}, f, ensure_ascii=False, indent=2)

# 제한 사용자 파일이 없으면 초기화
if not os.path.exists(RESTRICTED_FILE):
    with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
        json.dump({"restricted_users": []}, f, ensure_ascii=False, indent=2)

# 제한 이력 파일이 없으면 초기화
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump({"history": []}, f, ensure_ascii=False, indent=2)

# 기본 관리자 계정 생성
def init_admin_accounts():
    """서버 시작 시 기본 관리자 계정을 생성합니다."""
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 관리자 계정 정보
    admin_accounts = [
        {
            "email": "admin@ticket.com",
            "password": "admin1234",  # 실제 환경에서는 해시화 필요
            "name": "Administrator",
            "phone": "01000000000"
        },
        {
            "email": "manager@ticket.com",
            "password": "manager1234",
            "name": "Manager",
            "phone": "01000000001"
        }
    ]
    
    users_updated = False
    for admin in admin_accounts:
        # 이미 존재하는지 확인
        existing = any(user['email'] == admin['email'] for user in data['users'])
        if not existing:
            data['users'].append(admin)
            users_updated = True
            print(f"관리자 계정 생성: {admin['email']} (비밀번호: {admin['password']})")
    
    if users_updated:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# 관리자 계정 초기화 실행
init_admin_accounts()

# ---- Server log helpers ----
REQUEST_HISTORY = {}
LOGIN_HISTORY = {}
RISK_PARAMS_PATH = os.path.join("model", "artifacts", "active", "human_model_params.json")
RISK_THRESHOLDS_PATH = os.path.join("model", "artifacts", "active", "human_model_thresholds.json")
RISK_DEFAULT_WEIGHTS = {
    "rule": float(os.getenv("RISK_WEIGHT_RULE", "0.2")),
    "model": float(os.getenv("RISK_WEIGHT_MODEL", "0.8")),
}
RISK_ALLOW_THRESHOLD_ENV = os.getenv("RISK_ALLOW_THRESHOLD")
RISK_CHALLENGE_THRESHOLD_ENV = os.getenv("RISK_CHALLENGE_THRESHOLD")
RISK_DECISION_THRESHOLDS_DEFAULT = {"allow": 0.30, "challenge": 0.70}
# Decision mode:
# - risk_weighted (default): decision from weighted risk score (model/rule).
# - model_threshold_fixed: decision from model_score with fixed model threshold.
RISK_DECISION_MODE = os.getenv("RISK_DECISION_MODE", "risk_weighted").strip().lower()
if RISK_DECISION_MODE not in {"risk_weighted", "model_threshold_fixed"}:
    RISK_DECISION_MODE = "risk_weighted"
# Fixed model threshold source (used when RISK_DECISION_MODE=model_threshold_fixed):
# 1) RISK_MODEL_FIXED_THRESHOLD (direct numeric override)
# 2) RISK_MODEL_FIXED_THRESHOLD_KEY in thresholds json
# 3) thresholds json key "model_fixed_threshold"
RISK_MODEL_FIXED_THRESHOLD_ENV = os.getenv("RISK_MODEL_FIXED_THRESHOLD")
RISK_MODEL_FIXED_THRESHOLD_KEY = os.getenv("RISK_MODEL_FIXED_THRESHOLD_KEY", "").strip()
# Start conservatively: block only for hard signals unless explicitly enabled.
RISK_BLOCK_AUTOMATION = os.getenv("RISK_BLOCK_AUTOMATION", "false").strip().lower() in {"1", "true", "yes", "on"}
RISK_RUNTIME_CACHE: Dict[str, Any] = {
    "params_mtime": None,
    "thresholds_mtime": None,
    "params": None,
    "thresholds": None,
    "model_artifact": None,
    "artifact_path": "",
    "error": "",
}

# 실시간 차단/챌린지 응답을 즉시 적용할 API 경로/메서드
# (예매 시작 ~ 대기열 ~ 로그 제출 구간)
RISK_REALTIME_ENFORCE_RULES = {
    "/api/booking/start-token": {"POST"},
    "/api/queue/join": {"POST"},
    "/api/queue/status": {"GET"},
    "/api/queue/enter": {"POST"},
    "/api/logs": {"POST"},
}

LLM_REPORT_ENABLED = os.getenv("LLM_REPORT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
LLM_REPORT_MODEL = os.getenv("LLM_REPORT_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
LLM_REPORT_TIMEOUT_SEC = int(os.getenv("LLM_REPORT_TIMEOUT_SEC", "20"))
LLM_REPORT_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")

# ---- Seat F2 macro bridge ----
SEAT_F2_MACRO_ENABLED = os.getenv("SEAT_F2_MACRO_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
SEAT_F2_MACRO_MAX_RETRIES = int(os.getenv("SEAT_F2_MACRO_MAX_RETRIES", "50"))
SEAT_F2_MACRO_GRADE = os.getenv("SEAT_F2_MACRO_GRADE", "전체").strip() or "전체"
SEAT_F2_MACRO_REQUIRE_BROWSER_FOCUS = os.getenv("SEAT_F2_MACRO_REQUIRE_BROWSER_FOCUS", "true").strip().lower() in {"1", "true", "yes", "on"}
SEAT_F2_MACRO_BROWSER_KEYWORDS = [
    "chrome",
    "edge",
    "firefox",
    "localhost:8000",
    "seat_select",
    "ticket",
]
SEAT_F2_MACRO_LOCK = threading.Lock()
SEAT_F2_MACRO_STATE: Dict[str, Any] = {
    "running": False,
    "last_started_iso": "",
    "last_finished_iso": "",
    "last_success": None,
    "last_error": "",
}

try:
    import sys as _sys
    _macro_dir = os.path.join(os.path.dirname(__file__), "macro")
    if _macro_dir not in _sys.path:
        _sys.path.insert(0, _macro_dir)
    from macsearcher import search_and_click as _seat_f2_macro_search_and_click
except Exception as _seat_macro_import_error:
    _seat_f2_macro_search_and_click = None
    SEAT_F2_MACRO_STATE["last_error"] = f"macro_import_error:{_seat_macro_import_error}"

# ---- Queue helpers ----
PERFORMANCE_DETAIL_OPEN_OFFSET_SEC = int(os.getenv("PERFORMANCE_DETAIL_OPEN_OFFSET_SEC", "5"))
QUEUE_BASE_WAIT_MS = int(os.getenv("QUEUE_BASE_WAIT_MS", "3000"))
QUEUE_SLOT_MS = int(os.getenv("QUEUE_SLOT_MS", "350"))
QUEUE_JOIN_DELAY_STEP_MS = int(os.getenv("QUEUE_JOIN_DELAY_STEP_MS", "700"))
QUEUE_JOIN_DELAY_CAP_STEPS = int(os.getenv("QUEUE_JOIN_DELAY_CAP_STEPS", "8"))
QUEUE_JOIN_DELAY_PENALTY_MS = int(os.getenv("QUEUE_JOIN_DELAY_PENALTY_MS", "350"))
QUEUE_SINCE_OPEN_STEP_MS = int(os.getenv("QUEUE_SINCE_OPEN_STEP_MS", "1000"))
QUEUE_SINCE_OPEN_CAP_STEPS = int(os.getenv("QUEUE_SINCE_OPEN_CAP_STEPS", "10"))
QUEUE_SINCE_OPEN_PENALTY_MS = int(os.getenv("QUEUE_SINCE_OPEN_PENALTY_MS", "300"))
QUEUE_READY_TTL_MS = int(os.getenv("QUEUE_READY_TTL_MS", "90000"))
QUEUE_ENTRY_TTL_MS = int(os.getenv("QUEUE_ENTRY_TTL_MS", "300000"))
QUEUE_REQUIRE_START_TOKEN = os.getenv("QUEUE_REQUIRE_START_TOKEN", "true").strip().lower() in {"1", "true", "yes", "on"}
BOOKING_START_TOKEN_TTL_MS = int(os.getenv("BOOKING_START_TOKEN_TTL_MS", "120000"))
QUEUE_POLL_MIN_MS = int(os.getenv("QUEUE_POLL_MIN_MS", "300"))
QUEUE_ENFORCE_SEAT_GATE = os.getenv("QUEUE_ENFORCE_SEAT_GATE", "true").strip().lower() in {"1", "true", "yes", "on"}
QUEUE_TICKET_COOKIE = "queue_entry_ticket"
QUEUE_DISPLAY_START_MIN = int(os.getenv("QUEUE_DISPLAY_START_MIN", "2400"))
QUEUE_DISPLAY_START_MAX = int(os.getenv("QUEUE_DISPLAY_START_MAX", "4200"))
QUEUE_DISPLAY_MID1_MIN = int(os.getenv("QUEUE_DISPLAY_MID1_MIN", "450"))
QUEUE_DISPLAY_MID1_MAX = int(os.getenv("QUEUE_DISPLAY_MID1_MAX", "950"))
QUEUE_DISPLAY_MID2_MIN = int(os.getenv("QUEUE_DISPLAY_MID2_MIN", "20"))
QUEUE_DISPLAY_MID2_MAX = int(os.getenv("QUEUE_DISPLAY_MID2_MAX", "120"))
QUEUE_DISPLAY_TOTAL_EXTRA_MIN = int(os.getenv("QUEUE_DISPLAY_TOTAL_EXTRA_MIN", "200"))
QUEUE_DISPLAY_TOTAL_EXTRA_MAX = int(os.getenv("QUEUE_DISPLAY_TOTAL_EXTRA_MAX", "1600"))

QUEUE_STATE_BY_ID: Dict[str, Dict[str, Any]] = {}
QUEUE_IDS_BY_PERF: Dict[str, List[str]] = {}
QUEUE_ENTRY_TICKETS: Dict[str, Dict[str, Any]] = {}
BOOKING_START_TOKENS: Dict[str, Dict[str, Any]] = {}
BOOKING_OPEN_EPOCH_BY_PERF: Dict[str, int] = {}
QUEUE_NEXT_READY_SLOT_BY_PERF: Dict[str, int] = {}
QUEUE_LOCK = threading.Lock()


def _seat_f2_macro_state_snapshot() -> Dict[str, Any]:
    with SEAT_F2_MACRO_LOCK:
        return {
            "enabled": bool(SEAT_F2_MACRO_ENABLED),
            "running": bool(SEAT_F2_MACRO_STATE.get("running")),
            "last_started_iso": str(SEAT_F2_MACRO_STATE.get("last_started_iso", "")),
            "last_finished_iso": str(SEAT_F2_MACRO_STATE.get("last_finished_iso", "")),
            "last_success": SEAT_F2_MACRO_STATE.get("last_success"),
            "last_error": str(SEAT_F2_MACRO_STATE.get("last_error", "")),
        }


def _get_active_window_title() -> str:
    if os.name != "nt":
        return ""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        return str(buff.value or "").strip()
    except Exception:
        return ""


def _is_browser_window_focused() -> bool:
    title = _get_active_window_title().lower()
    if not title:
        return False
    return any(keyword in title for keyword in SEAT_F2_MACRO_BROWSER_KEYWORDS)


def _seat_f2_macro_worker(grade: str) -> None:
    success = False
    error_msg = ""
    try:
        if _seat_f2_macro_search_and_click is None:
            raise RuntimeError("seat_f2_macro_unavailable")
        if SEAT_F2_MACRO_REQUIRE_BROWSER_FOCUS and not _is_browser_window_focused():
            active_title = _get_active_window_title()
            raise RuntimeError(f"active_window_not_browser:{active_title or 'unknown'}")
        stop_flag = [False]
        success = bool(
            _seat_f2_macro_search_and_click(
                grade,
                max_retries=max(1, int(SEAT_F2_MACRO_MAX_RETRIES)),
                stop_flag=stop_flag,
            )
        )
        if not success:
            error_msg = "seat_not_selected_or_confirm_button_not_found"
    except Exception as e:
        error_msg = str(e)
    finally:
        with SEAT_F2_MACRO_LOCK:
            SEAT_F2_MACRO_STATE["running"] = False
            SEAT_F2_MACRO_STATE["last_finished_iso"] = datetime.utcnow().isoformat() + "Z"
            SEAT_F2_MACRO_STATE["last_success"] = bool(success)
            SEAT_F2_MACRO_STATE["last_error"] = error_msg


def _start_seat_f2_macro(grade: str) -> Dict[str, Any]:
    if not SEAT_F2_MACRO_ENABLED:
        return {
            "success": False,
            "message": "좌석 F2 매크로가 비활성화되어 있습니다.",
            "state": _seat_f2_macro_state_snapshot(),
        }
    if _seat_f2_macro_search_and_click is None:
        return {
            "success": False,
            "message": "좌석 F2 매크로 모듈을 불러오지 못했습니다.",
            "state": _seat_f2_macro_state_snapshot(),
        }

    already_running = False
    with SEAT_F2_MACRO_LOCK:
        if SEAT_F2_MACRO_STATE.get("running"):
            already_running = True
        else:
            SEAT_F2_MACRO_STATE["running"] = True
            SEAT_F2_MACRO_STATE["last_started_iso"] = datetime.utcnow().isoformat() + "Z"
            SEAT_F2_MACRO_STATE["last_error"] = ""
            SEAT_F2_MACRO_STATE["last_success"] = None

    if already_running:
        return {
            "success": False,
            "message": "이미 F2 매크로가 실행 중입니다.",
            "state": _seat_f2_macro_state_snapshot(),
        }

    t = threading.Thread(target=_seat_f2_macro_worker, args=(grade,), daemon=True)
    t.start()
    return {
        "success": True,
        "message": "F2 매크로 실행을 시작했습니다.",
        "state": _seat_f2_macro_state_snapshot(),
    }


def _hash_value(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _deterministic_int_from_key(key: str, min_value: int, max_value: int) -> int:
    lo = int(min(min_value, max_value))
    hi = int(max(min_value, max_value))
    if lo == hi:
        return lo
    h = int(hashlib.sha256(str(key).encode("utf-8")).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


def _ip_subnet(ip: str) -> str:
    parts = ip.split('.') if ip else []
    if len(parts) == 4:
        return '.'.join(parts[:3]) + '.0/24'
    return ""


def _extract_ip_key(request: Request) -> str:
    xff = request.headers.get('x-forwarded-for', '')
    if xff:
        first_ip = xff.split(',')[0].strip()
        if first_ip:
            return first_ip
    if request.client and request.client.host:
        return request.client.host
    return 'unknown'


def _should_enforce_realtime_decision(request: Request) -> bool:
    """현재 요청에 대해 block/challenge 응답을 즉시 반환할지 판단한다."""
    path = str(request.url.path or "").strip()
    method = str(request.method or "").upper()
    allowed_methods = RISK_REALTIME_ENFORCE_RULES.get(path, set())
    return method in allowed_methods


def _update_behavior(ip_key: str, endpoint: str, now_ms: int) -> Dict[str, int]:
    hist = REQUEST_HISTORY.setdefault(ip_key, [])
    hist.append((now_ms, endpoint))

    cutoff = now_ms - 60000
    while hist and hist[0][0] < cutoff:
        hist.pop(0)

    c1 = 0
    c10 = 0
    c60 = 0
    endpoints = set()
    for ts, ep in hist:
        dt = now_ms - ts
        if dt <= 1000:
            c1 += 1
        if dt <= 10000:
            c10 += 1
        if dt <= 60000:
            c60 += 1
            endpoints.add(ep)

    return {
        'requests_last_1s': c1,
        'requests_last_10s': c10,
        'requests_last_60s': c60,
        'unique_endpoints_last_60s': len(endpoints)
    }


def _prune_login_history(ip_key: str, now_ms: int):
    hist = LOGIN_HISTORY.setdefault(ip_key, [])
    cutoff = now_ms - (10 * 60 * 1000)  # 10 minutes
    while hist and hist[0]['ts'] < cutoff:
        hist.pop(0)
    return hist


def _record_login_attempt(ip_key: str, email: str, success: bool, now_ms: int):
    hist = _prune_login_history(ip_key, now_ms)
    hist.append({
        'ts': now_ms,
        'email': email or '',
        'success': bool(success)
    })


def _get_login_summary(ip_key: str, now_ms: int) -> Dict[str, int]:
    hist = _prune_login_history(ip_key, now_ms)
    attempts = len(hist)
    fail_count = sum(1 for h in hist if not h.get('success'))
    success_count = attempts - fail_count
    unique_accounts = len(set(h.get('email', '') for h in hist if h.get('email')))
    return {
        'login_attempts_last_10m': attempts,
        'login_fail_count_last_10m': fail_count,
        'login_success_count_last_10m': success_count,
        'login_unique_accounts_last_10m': unique_accounts,
    }


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _sanitize_filename_part(value: Any, fallback: str = "unknown") -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '', str(value or ""))
    return cleaned or fallback


def _now_ms() -> int:
    return int(time.time() * 1000)


def _save_score_snapshots(
    *,
    request: Request,
    metadata: Dict[str, Any],
    performance_id: Any,
    flow_id: Any,
    session_id: Any,
    bot_type: str,
    risk_payload: Dict[str, Any],
) -> Dict[str, str]:
    created_at = datetime.utcnow().isoformat() + "Z"
    date_str = datetime.now().strftime("%Y%m%d")
    safe_perf_id = _sanitize_filename_part(performance_id, fallback="unknownperf")
    safe_flow_id = _sanitize_filename_part(flow_id, fallback="noflow")
    safe_session_id = _sanitize_filename_part(session_id, fallback="nosession")
    safe_endpoint = _sanitize_filename_part(str(request.url.path).replace("/", "_"), fallback="api")
    safe_method = _sanitize_filename_part(str(request.method).lower(), fallback="req")
    safe_request_id = _sanitize_filename_part(
        str((metadata or {}).get("request_id", "")).strip(),
        fallback=f"req_{uuid.uuid4().hex}",
    )
    base_name = (
        f"{date_str}_{safe_perf_id}_{safe_flow_id}_{safe_session_id}_"
        f"{safe_endpoint}_{safe_method}_{safe_request_id}"
    )

    rule_score_path = os.path.join(RULE_SCORE_DIR, f"{base_name}_rule_score.json")
    model_score_path = os.path.join(MODEL_SCORE_DIR, f"{base_name}_model_score.json")

    common = {
        "created_at_iso": created_at,
        "request_id": str((metadata or {}).get("request_id", "")),
        "event_id": str((metadata or {}).get("event_id", "")),
        "performance_id": str(performance_id or ""),
        "flow_id": str(flow_id or ""),
        "session_id": str(session_id or ""),
        "endpoint": str(request.url.path),
        "method": str(request.method),
        "bot_type": str(bot_type or ""),
        "decision": str((risk_payload or {}).get("decision", "allow")),
    }

    rule_doc = {
        "type": "rule_score_v1",
        **common,
        "rule_score": round(_safe_float((risk_payload or {}).get("rule_score")), 6),
        "hard_action": str((risk_payload or {}).get("hard_action", "none")),
        "rules_triggered": list((risk_payload or {}).get("rules_triggered", []) or []),
        "soft_rules_triggered": list((risk_payload or {}).get("soft_rules_triggered", []) or []),
        "hard_rules_triggered": list((risk_payload or {}).get("hard_rules_triggered", []) or []),
        "risk_score": round(_safe_float((risk_payload or {}).get("risk_score")), 6),
        "threshold_allow": round(_safe_float((risk_payload or {}).get("threshold_allow")), 6),
        "threshold_challenge": round(_safe_float((risk_payload or {}).get("threshold_challenge")), 6),
    }

    model_doc = {
        "type": "model_score_v1",
        **common,
        "model_type": str((risk_payload or {}).get("model_type", "none")),
        "model_score": round(_safe_float((risk_payload or {}).get("model_score")), 6),
        "model_ready": bool((risk_payload or {}).get("model_ready", False)),
        "model_skipped": bool((risk_payload or {}).get("model_skipped", False)),
        "runtime_error": str((risk_payload or {}).get("runtime_error", "")),
        "risk_score": round(_safe_float((risk_payload or {}).get("risk_score")), 6),
        "threshold_allow": round(_safe_float((risk_payload or {}).get("threshold_allow")), 6),
        "threshold_challenge": round(_safe_float((risk_payload or {}).get("threshold_challenge")), 6),
    }

    with open(rule_score_path, "w", encoding="utf-8") as f:
        json.dump(rule_doc, f, ensure_ascii=False, indent=2)
    with open(model_score_path, "w", encoding="utf-8") as f:
        json.dump(model_doc, f, ensure_ascii=False, indent=2)

    return {
        "rule_score_path": rule_score_path,
        "model_score_path": model_score_path,
    }


def _percentile(values: List[int], p: float) -> int:
    if not values:
        return 0
    vals = sorted(values)
    if len(vals) == 1:
        return int(vals[0])
    rank = (max(0.0, min(100.0, p)) / 100.0) * (len(vals) - 1)
    low = int(rank)
    high = min(len(vals) - 1, low + 1)
    w = rank - low
    return int(round(vals[low] * (1.0 - w) + vals[high] * w))


def _penalty_steps(elapsed_ms: int, step_ms: int, cap_steps: int) -> int:
    elapsed = max(0, int(elapsed_ms))
    step = max(1, int(step_ms))
    steps = int(elapsed // step)
    cap = int(cap_steps)
    if cap > 0:
        return int(min(cap, steps))
    return int(steps)


def _cleanup_start_tokens_locked(now_ms: int) -> None:
    for token, token_state in list(BOOKING_START_TOKENS.items()):
        if int(token_state.get("expires_epoch_ms", 0)) <= now_ms:
            BOOKING_START_TOKENS.pop(token, None)


def _issue_start_token_locked(
    *,
    performance_id: str,
    flow_id: str,
    session_id: str,
    user_email: str,
    bot_type: str,
    now_ms: int,
) -> Dict[str, Any]:
    token = f"bst_{uuid.uuid4().hex}"
    open_epoch_ms = int(BOOKING_OPEN_EPOCH_BY_PERF.get(performance_id, 0) or 0)
    if open_epoch_ms <= 0:
        open_epoch_ms = int(now_ms)
        BOOKING_OPEN_EPOCH_BY_PERF[performance_id] = open_epoch_ms
    token_state = {
        "token": token,
        "performance_id": performance_id,
        "flow_id": flow_id,
        "session_id": session_id,
        "user_email": str(user_email or ""),
        "bot_type": str(bot_type or ""),
        "open_epoch_ms": open_epoch_ms,
        "issued_epoch_ms": now_ms,
        "expires_epoch_ms": now_ms + BOOKING_START_TOKEN_TTL_MS,
    }
    BOOKING_START_TOKENS[token] = token_state
    return token_state


def _get_valid_start_token_state_locked(
    *,
    token: str,
    performance_id: str,
    flow_id: str,
    session_id: str,
    now_ms: int,
) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    _cleanup_start_tokens_locked(now_ms)
    token_state = BOOKING_START_TOKENS.get(token)
    if not token_state:
        return None
    if int(token_state.get("expires_epoch_ms", 0)) <= now_ms:
        BOOKING_START_TOKENS.pop(token, None)
        return None
    if str(token_state.get("performance_id", "")) != performance_id:
        return None
    if str(token_state.get("flow_id", "")) != flow_id:
        return None
    if str(token_state.get("session_id", "")) != session_id:
        return None
    return token_state


def _is_valid_start_token_locked(
    *,
    token: str,
    performance_id: str,
    flow_id: str,
    session_id: str,
    now_ms: int,
) -> bool:
    return _get_valid_start_token_state_locked(
        token=token,
        performance_id=performance_id,
        flow_id=flow_id,
        session_id=session_id,
        now_ms=now_ms,
    ) is not None


def _cleanup_queue_locked(now_ms: int) -> None:
    _cleanup_start_tokens_locked(now_ms)
    for ticket, state in list(QUEUE_ENTRY_TICKETS.items()):
        if int(state.get("expires_epoch_ms", 0)) <= now_ms:
            QUEUE_ENTRY_TICKETS.pop(ticket, None)

    for qid, queue_state in list(QUEUE_STATE_BY_ID.items()):
        state = str(queue_state.get("state", ""))
        if state in {"entered", "left", "expired"}:
            keep_until = int(queue_state.get("cleanup_after_epoch_ms", 0))
            if keep_until > 0 and now_ms >= keep_until:
                perf_id = str(queue_state.get("performance_id", ""))
                queue_ids = QUEUE_IDS_BY_PERF.get(perf_id, [])
                if qid in queue_ids:
                    queue_ids.remove(qid)
                QUEUE_STATE_BY_ID.pop(qid, None)

    # Clear stale per-performance slot pointers when no active queue remains.
    for perf_id in list(QUEUE_NEXT_READY_SLOT_BY_PERF.keys()):
        has_active = False
        for qid in QUEUE_IDS_BY_PERF.get(perf_id, []):
            q = QUEUE_STATE_BY_ID.get(qid)
            if not q:
                continue
            _refresh_queue_state_locked(q, now_ms)
            if str(q.get("state", "")) in {"waiting", "ready"}:
                has_active = True
                break
        if not has_active and QUEUE_NEXT_READY_SLOT_BY_PERF.get(perf_id, 0) <= now_ms:
            QUEUE_NEXT_READY_SLOT_BY_PERF.pop(perf_id, None)
            BOOKING_OPEN_EPOCH_BY_PERF.pop(perf_id, None)


def _refresh_queue_state_locked(queue_state: Dict[str, Any], now_ms: int) -> None:
    state = str(queue_state.get("state", "waiting"))
    if state == "waiting" and now_ms >= int(queue_state.get("ready_epoch_ms", 0)):
        queue_state["state"] = "ready"
    elif state == "ready":
        ready_epoch_ms = int(queue_state.get("ready_epoch_ms", 0))
        if ready_epoch_ms > 0 and now_ms >= ready_epoch_ms + QUEUE_READY_TTL_MS:
            queue_state["state"] = "expired"
            queue_state["cleanup_after_epoch_ms"] = now_ms + 300000


def _find_active_queue_locked(performance_id: str, flow_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    for qid in QUEUE_IDS_BY_PERF.get(performance_id, []):
        q = QUEUE_STATE_BY_ID.get(qid)
        if not q:
            continue
        if str(q.get("flow_id", "")) != str(flow_id):
            continue
        if str(q.get("session_id", "")) != str(session_id):
            continue
        if str(q.get("state", "")) in {"waiting", "ready"}:
            return q
    return None


def _queue_position_locked(queue_state: Dict[str, Any], now_ms: int) -> int:
    _refresh_queue_state_locked(queue_state, now_ms)
    if str(queue_state.get("state", "")) != "waiting":
        return 0

    perf_id = str(queue_state.get("performance_id", ""))
    target_qid = str(queue_state.get("queue_id", ""))
    position = 0
    for qid in QUEUE_IDS_BY_PERF.get(perf_id, []):
        q = QUEUE_STATE_BY_ID.get(qid)
        if not q:
            continue
        _refresh_queue_state_locked(q, now_ms)
        if str(q.get("state", "")) != "waiting":
            continue
        position += 1
        if str(q.get("queue_id", "")) == target_qid:
            return position
    return max(0, position)


def _queue_total_locked(performance_id: str, now_ms: int) -> int:
    total = 0
    for qid in QUEUE_IDS_BY_PERF.get(performance_id, []):
        q = QUEUE_STATE_BY_ID.get(qid)
        if not q:
            continue
        _refresh_queue_state_locked(q, now_ms)
        if str(q.get("state", "")) in {"waiting", "ready"}:
            total += 1
    return total


def _queue_display_position_locked(queue_state: Dict[str, Any], now_ms: int, fallback_position: int) -> int:
    _refresh_queue_state_locked(queue_state, now_ms)
    if str(queue_state.get("state", "")) != "waiting":
        return 0

    start = int(queue_state.get("display_position_start", 0) or 0)
    mid1 = int(queue_state.get("display_position_mid1", 0) or 0)
    mid2 = int(queue_state.get("display_position_mid2", 0) or 0)
    if start <= 0:
        return max(1, int(fallback_position))

    # Ensure a monotonic shape: start > mid1 > mid2 >= 1
    mid1 = min(mid1, max(2, start - 1))
    mid2 = min(mid2, max(1, mid1 - 1))
    mid1 = max(2, mid1)
    mid2 = max(1, mid2)

    join_epoch = int(queue_state.get("join_epoch_ms", 0))
    ready_epoch = int(queue_state.get("ready_epoch_ms", 0))
    total_wait = max(1, ready_epoch - join_epoch)
    elapsed = max(0, min(total_wait, now_ms - join_epoch))
    progress = elapsed / total_wait

    if progress < 0.55:
        t = progress / 0.55
        pos = start + (mid1 - start) * t
    elif progress < 0.90:
        t = (progress - 0.55) / 0.35
        pos = mid1 + (mid2 - mid1) * t
    else:
        t = (progress - 0.90) / 0.10
        pos = mid2 + (1 - mid2) * t

    return max(1, int(round(pos)))


def _queue_display_total_locked(queue_state: Dict[str, Any], fallback_total: int) -> int:
    display_total = int(queue_state.get("display_total_queue", 0) or 0)
    if display_total <= 0:
        return max(1, int(fallback_total))
    return max(1, max(display_total, int(fallback_total)))


def _queue_poll_stats_locked(queue_state: Dict[str, Any]) -> Dict[str, int]:
    intervals = list(queue_state.get("poll_intervals_ms", []) or [])
    return {
        "min": int(min(intervals)) if intervals else 0,
        "p50": _percentile(intervals, 50.0),
        "p95": _percentile(intervals, 95.0),
    }


def _queue_snapshot_for_log(
    *,
    request: Request,
    flow_id: str,
    session_id: str,
    request_payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    queue_id = ""
    if request_payload:
        queue_id = str(request_payload.get("queue_id", "")).strip()
    if not queue_id:
        queue_id = str(request.query_params.get("queue_id", "")).strip()

    now_ms = _now_ms()
    with QUEUE_LOCK:
        _cleanup_queue_locked(now_ms)

        queue_state = None
        if queue_id:
            queue_state = QUEUE_STATE_BY_ID.get(queue_id)
        elif flow_id:
            for q in QUEUE_STATE_BY_ID.values():
                if str(q.get("flow_id", "")) == str(flow_id) and str(q.get("session_id", "")) == str(session_id):
                    queue_state = q
                    break

        if not queue_state:
            return {
                "queue_id": "",
                "join_epoch_ms": 0,
                "enter_trigger": "",
                "position": 0,
                "poll_interval_ms_stats": {"min": 0, "p50": 0, "p95": 0},
                "jump_count": 0,
            }

        _refresh_queue_state_locked(queue_state, now_ms)
        actual_position = int(_queue_position_locked(queue_state, now_ms))
        display_position = int(_queue_display_position_locked(queue_state, now_ms, actual_position))
        return {
            "queue_id": str(queue_state.get("queue_id", "")),
            "join_epoch_ms": int(queue_state.get("join_epoch_ms", 0)),
            "enter_trigger": str(queue_state.get("enter_trigger", "")),
            "position": display_position,
            "actual_position": actual_position,
            "poll_interval_ms_stats": _queue_poll_stats_locked(queue_state),
            "jump_count": int(queue_state.get("jump_count", 0)),
        }


def _validate_entry_ticket(ticket: str) -> bool:
    if not ticket:
        return False
    now_ms = _now_ms()
    with QUEUE_LOCK:
        _cleanup_queue_locked(now_ms)
        state = QUEUE_ENTRY_TICKETS.get(ticket)
        if not state:
            return False
        return int(state.get("expires_epoch_ms", 0)) > now_ms


def _queue_status_payload_locked(queue_state: Dict[str, Any], now_ms: int) -> Dict[str, Any]:
    _refresh_queue_state_locked(queue_state, now_ms)
    perf_id = str(queue_state.get("performance_id", ""))
    state = str(queue_state.get("state", "waiting"))
    actual_position = int(_queue_position_locked(queue_state, now_ms))
    actual_total = int(_queue_total_locked(perf_id, now_ms))
    position = int(_queue_display_position_locked(queue_state, now_ms, actual_position))
    total = int(_queue_display_total_locked(queue_state, actual_total))

    poll_after_ms = 0
    if state == "waiting":
        remain_to_ready = max(0, int(queue_state.get("ready_epoch_ms", 0)) - now_ms)
        poll_after_ms = max(QUEUE_POLL_MIN_MS, min(1500, remain_to_ready if remain_to_ready > 0 else QUEUE_POLL_MIN_MS))

    return {
        "queue_id": str(queue_state.get("queue_id", "")),
        "performance_id": perf_id,
        "flow_id": str(queue_state.get("flow_id", "")),
        "session_id": str(queue_state.get("session_id", "")),
        "state": state,
        "position": position,
        "total_queue": total,
        "actual_position": actual_position,
        "actual_total_queue": actual_total,
        "join_epoch_ms": int(queue_state.get("join_epoch_ms", 0)),
        "ready_epoch_ms": int(queue_state.get("ready_epoch_ms", 0)),
        "poll_after_ms": int(poll_after_ms),
        "jump_count": int(queue_state.get("jump_count", 0)),
        "poll_interval_ms_stats": _queue_poll_stats_locked(queue_state),
    }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _resolve_artifact_path(artifact_path: str) -> str:
    if not artifact_path:
        return ""
    if os.path.isabs(artifact_path) and os.path.exists(artifact_path):
        return artifact_path

    from_params = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(RISK_PARAMS_PATH)), artifact_path))
    if os.path.exists(from_params):
        return from_params

    from_cwd = os.path.abspath(artifact_path)
    if os.path.exists(from_cwd):
        return from_cwd
    return ""


def _load_risk_runtime() -> Optional[Dict[str, Any]]:
    cache = RISK_RUNTIME_CACHE
    try:
        if not os.path.exists(RISK_PARAMS_PATH):
            cache["error"] = f"missing params: {RISK_PARAMS_PATH}"
            return None

        params_mtime = os.path.getmtime(RISK_PARAMS_PATH)
        thresholds_exists = os.path.exists(RISK_THRESHOLDS_PATH)
        thresholds_mtime = os.path.getmtime(RISK_THRESHOLDS_PATH) if thresholds_exists else None

        needs_reload = (
            cache["params"] is None
            or cache["params_mtime"] != params_mtime
            or cache["thresholds_mtime"] != thresholds_mtime
        )
        if not needs_reload:
            return {
                "params": cache["params"],
                "thresholds": cache["thresholds"] or {},
                "model_artifact": cache["model_artifact"],
                "artifact_path": cache["artifact_path"],
                "error": cache["error"],
            }

        with open(RISK_PARAMS_PATH, "r", encoding="utf-8") as f:
            params = json.load(f)

        thresholds: Dict[str, Any] = {}
        if thresholds_exists:
            with open(RISK_THRESHOLDS_PATH, "r", encoding="utf-8") as f:
                thresholds = json.load(f)

        model_artifact = None
        artifact_path = _resolve_artifact_path(str(params.get("model_artifact", "")))
        if artifact_path:
            if joblib is None:
                cache["error"] = "joblib unavailable; model artifact not loaded"
            else:
                model_artifact = joblib.load(artifact_path)

        cache["params_mtime"] = params_mtime
        cache["thresholds_mtime"] = thresholds_mtime
        cache["params"] = params
        cache["thresholds"] = thresholds
        cache["model_artifact"] = model_artifact
        cache["artifact_path"] = artifact_path
        cache["error"] = ""
        return {
            "params": params,
            "thresholds": thresholds,
            "model_artifact": model_artifact,
            "artifact_path": artifact_path,
            "error": "",
        }
    except Exception as e:
        cache["error"] = str(e)
        return None


def _model_score_from_features_runtime(
    features: Dict[str, float],
    params: Dict[str, Any],
    model_artifact: Optional[Dict[str, Any]],
) -> float:
    order = params.get("feature_order") or []
    if not order:
        return 0.0

    raw_min = _safe_float(params.get("raw_min"), 0.0)
    raw_max = _safe_float(params.get("raw_max"), 0.0)
    model_type = str(params.get("model_type", "zscore"))

    vec = np.array([_safe_float(features.get(name, 0.0), 0.0) for name in order], dtype=float)
    raw_score = 0.0

    if model_type == "zscore" or ("mean" in params and "std" in params and not model_artifact):
        mean = np.array(params.get("mean", [0.0] * len(order)), dtype=float)
        std = np.array(params.get("std", [1.0] * len(order)), dtype=float)
        if mean.shape[0] != vec.shape[0] or std.shape[0] != vec.shape[0]:
            return 0.0
        std[std == 0] = 1.0
        raw_score = float(np.abs((vec - mean) / std).mean())
    elif model_type in ("isolation_forest", "oneclass_svm"):
        if not model_artifact:
            return 0.0
        model = model_artifact.get("model") if isinstance(model_artifact, dict) else None
        scaler = model_artifact.get("scaler") if isinstance(model_artifact, dict) else None
        if model is None:
            return 0.0
        x = vec.reshape(1, -1)
        if scaler is not None:
            x = scaler.transform(x)
        if hasattr(model, "decision_function"):
            raw_score = -float(model.decision_function(x)[0])
        elif hasattr(model, "score_samples"):
            raw_score = -float(model.score_samples(x)[0])
        else:
            return 0.0
    else:
        return 0.0

    if raw_max - raw_min <= 1e-12:
        return 0.0
    return _clamp01((raw_score - raw_min) / (raw_max - raw_min))


def _resolve_decision_thresholds() -> Dict[str, float]:
    # 운영 단순화를 위해 risk 임계값은 정책 고정값(기본 0.30/0.70)을 사용한다.
    # 모델 파일(threshold json) 값에는 의존하지 않는다.
    allow = RISK_DECISION_THRESHOLDS_DEFAULT["allow"]
    challenge = RISK_DECISION_THRESHOLDS_DEFAULT["challenge"]

    # ENV가 있으면 정책값을 오버라이드할 수 있다.
    if RISK_ALLOW_THRESHOLD_ENV is not None:
        allow = _safe_float(RISK_ALLOW_THRESHOLD_ENV, allow)
    if RISK_CHALLENGE_THRESHOLD_ENV is not None:
        challenge = _safe_float(RISK_CHALLENGE_THRESHOLD_ENV, challenge)

    allow = _clamp01(allow)
    challenge = _clamp01(challenge)
    if challenge <= allow:
        challenge = min(1.0, allow + 0.05)
    return {"allow": allow, "challenge": challenge}


def _resolve_model_fixed_threshold(thresholds_raw: Optional[Dict[str, Any]]) -> Optional[float]:
    if RISK_MODEL_FIXED_THRESHOLD_ENV is not None and str(RISK_MODEL_FIXED_THRESHOLD_ENV).strip() != "":
        return _clamp01(_safe_float(RISK_MODEL_FIXED_THRESHOLD_ENV))

    threshold_map = thresholds_raw or {}
    candidate_keys: List[str] = []
    if RISK_MODEL_FIXED_THRESHOLD_KEY:
        candidate_keys.append(RISK_MODEL_FIXED_THRESHOLD_KEY)
    candidate_keys.append("model_fixed_threshold")

    for key in candidate_keys:
        if key in threshold_map:
            return _clamp01(_safe_float(threshold_map.get(key)))
    return None


def _decision_from_risk_runtime(risk_score: float, thresholds: Dict[str, float]) -> str:
    if risk_score < thresholds["allow"]:
        return "allow"
    if risk_score < thresholds["challenge"]:
        return "challenge"
    return "block"


def _score_request_risk(browser_log: Optional[Dict[str, Any]], server_log: Dict[str, Any]) -> Dict[str, Any]:
    rule_score = 0.0
    soft_rules: List[str] = []
    hard_rules: List[str] = []
    hard_action = "none"

    if _evaluate_rules_runtime is not None:
        try:
            rule_eval = _evaluate_rules_runtime(server_log or {}, browser_log or {})
            rule_score = _safe_float(rule_eval.get("soft_score"))
            soft_rules = list(rule_eval.get("soft_rules_triggered", []))
            hard_rules = list(rule_eval.get("hard_rules_triggered", []))
            hard_action = str(rule_eval.get("hard_action", "none"))
        except Exception:
            rule_score, soft_rules, hard_rules, hard_action = 0.0, [], [], "none"

    model_score = 0.0
    model_type = "none"
    runtime_error = ""
    runtime = None
    model_skipped = hard_action == "block"

    if model_skipped:
        runtime_error = "model_skipped_by_hard_rule_block"
    else:
        runtime = _load_risk_runtime()
        if runtime:
            params = runtime.get("params") or {}
            model_type = str(params.get("model_type", "zscore"))
            runtime_error = runtime.get("error", "")

            if browser_log and _extract_browser_features_runtime is not None:
                try:
                    features = _extract_browser_features_runtime(browser_log)
                    model_score = _model_score_from_features_runtime(
                        features=features,
                        params=params,
                        model_artifact=runtime.get("model_artifact"),
                    )
                except Exception as e:
                    runtime_error = str(e)

    thresholds = _resolve_decision_thresholds()
    decision_mode = RISK_DECISION_MODE
    runtime_thresholds_raw = (runtime or {}).get("thresholds") or {}
    model_fixed_threshold = None

    # 점수 스케일 안정화를 위해 개별 점수를 먼저 0~1로 정규화(clamp)한다.
    model_score = _clamp01(_safe_float(model_score))
    rule_score = _clamp01(_safe_float(rule_score))

    if decision_mode == "model_threshold_fixed":
        model_fixed_threshold = _resolve_model_fixed_threshold(runtime_thresholds_raw)
        if model_fixed_threshold is None:
            if runtime_error:
                runtime_error = f"{runtime_error};model_fixed_threshold_missing"
            else:
                runtime_error = "model_fixed_threshold_missing"
            decision_mode = "risk_weighted"

    if decision_mode == "model_threshold_fixed" and model_fixed_threshold is not None:
        # In fixed mode, make decision directly from model_score.
        risk_score = model_score
        decision = "allow" if model_score < model_fixed_threshold else "block"
        thresholds = {"allow": model_fixed_threshold, "challenge": model_fixed_threshold}
    else:
        risk_score = _clamp01(
            RISK_DEFAULT_WEIGHTS["model"] * model_score
            + RISK_DEFAULT_WEIGHTS["rule"] * rule_score
        )
        decision = _decision_from_risk_runtime(risk_score, thresholds=thresholds)

    # Hard rules override weighted decision.
    if hard_action == "block":
        decision = "block"
        risk_score = max(risk_score, thresholds["challenge"], 0.95)

    review_required = False
    block_recommended = False
    if decision == "block" and not RISK_BLOCK_AUTOMATION and hard_action != "block":
        # Conservative rollout mode: prefer challenge + manual review for model-only blocks.
        decision = "challenge"
        review_required = True
        block_recommended = True

    return {
        "risk_score": risk_score,
        "decision": decision,
        "rules_triggered": soft_rules + hard_rules,
        "soft_rules_triggered": soft_rules,
        "hard_rules_triggered": hard_rules,
        "hard_action": hard_action,
        "rule_score": rule_score,
        "model_score": model_score,
        "model_type": model_type,
        "model_ready": (runtime is not None) and (not model_skipped),
        "model_skipped": model_skipped,
        "decision_mode": decision_mode,
        "model_fixed_threshold": model_fixed_threshold,
        "runtime_error": runtime_error,
        "threshold_allow": thresholds["allow"],
        "threshold_challenge": thresholds["challenge"],
        "review_required": review_required,
        "block_recommended": block_recommended,
    }


def _runtime_behavior_evidence(
    browser_log: Optional[Dict[str, Any]],
    server_log: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    features: Dict[str, float] = {}

    if browser_log and _extract_browser_features_runtime is not None:
        try:
            features = _extract_browser_features_runtime(browser_log)
        except Exception:
            features = {}

    def add_if(cond: bool, code: str, description: str, metric: str, value: float, severity: str) -> None:
        if cond:
            evidence.append(
                {
                    "code": code,
                    "description": description,
                    "metric": metric,
                    "value": round(_safe_float(value), 6),
                    "severity": severity,
                }
            )

    if features:
        seat_click_interval = _safe_float(features.get("seat_avg_click_interval"))
        perf_click_interval = _safe_float(features.get("perf_avg_click_interval"))
        seat_straightness = _safe_float(features.get("seat_avg_straightness"))
        perf_straightness = _safe_float(features.get("perf_avg_straightness"))
        seat_click_std = _safe_float(features.get("seat_std_click_interval"))
        perf_click_std = _safe_float(features.get("perf_std_click_interval"))
        seat_click_hover_ratio = _safe_float(features.get("seat_click_to_hover_ratio"))
        perf_click_hover_ratio = _safe_float(features.get("perf_click_to_hover_ratio"))
        seat_duration = _safe_float(features.get("seat_duration_ms"))

        add_if(
            seat_click_interval > 0 and seat_click_interval < 120,
            "seat_fast_click_interval",
            "좌석 단계 평균 클릭 간격이 매우 짧습니다.",
            "seat_avg_click_interval",
            seat_click_interval,
            "high",
        )
        add_if(
            perf_click_interval > 0 and perf_click_interval < 150,
            "perf_fast_click_interval",
            "공연 단계 평균 클릭 간격이 매우 짧습니다.",
            "perf_avg_click_interval",
            perf_click_interval,
            "medium",
        )
        add_if(
            seat_straightness >= 0.97,
            "seat_high_straightness",
            "좌석 단계 마우스 궤적이 지나치게 직선적입니다.",
            "seat_avg_straightness",
            seat_straightness,
            "high",
        )
        add_if(
            perf_straightness >= 0.97,
            "perf_high_straightness",
            "공연 단계 마우스 궤적이 지나치게 직선적입니다.",
            "perf_avg_straightness",
            perf_straightness,
            "medium",
        )
        add_if(
            seat_click_std >= 0 and seat_click_std < 35 and _safe_float(features.get("seat_click_count")) >= 4,
            "seat_uniform_click_rhythm",
            "좌석 단계 클릭 리듬이 지나치게 일정합니다.",
            "seat_std_click_interval",
            seat_click_std,
            "high",
        )
        add_if(
            perf_click_std >= 0 and perf_click_std < 35 and _safe_float(features.get("perf_click_count")) >= 4,
            "perf_uniform_click_rhythm",
            "공연 단계 클릭 리듬이 지나치게 일정합니다.",
            "perf_std_click_interval",
            perf_click_std,
            "medium",
        )
        add_if(
            seat_click_hover_ratio >= 5.0,
            "seat_low_hover",
            "좌석 단계 hover 대비 클릭 비율이 비정상적으로 높습니다.",
            "seat_click_to_hover_ratio",
            seat_click_hover_ratio,
            "high",
        )
        add_if(
            perf_click_hover_ratio >= 5.0,
            "perf_low_hover",
            "공연 단계 hover 대비 클릭 비율이 비정상적으로 높습니다.",
            "perf_click_to_hover_ratio",
            perf_click_hover_ratio,
            "medium",
        )
        add_if(
            seat_duration > 0 and seat_duration < 900,
            "seat_short_duration",
            "좌석 선택 소요 시간이 매우 짧습니다.",
            "seat_duration_ms",
            seat_duration,
            "medium",
        )

    behavior = (server_log or {}).get("behavior", {}) or {}
    add_if(
        _safe_float(behavior.get("requests_last_1s")) >= 20,
        "srv_burst_1s",
        "1초 요청 수가 과도하게 높습니다.",
        "requests_last_1s",
        _safe_float(behavior.get("requests_last_1s")),
        "high",
    )
    add_if(
        _safe_float(behavior.get("requests_last_10s")) >= 60,
        "srv_burst_10s",
        "10초 요청 수가 과도하게 높습니다.",
        "requests_last_10s",
        _safe_float(behavior.get("requests_last_10s")),
        "high",
    )
    add_if(
        _safe_float(behavior.get("concurrent_sessions_same_ip")) >= 20,
        "srv_many_sessions_same_ip",
        "동일 IP 동시 세션 수가 비정상적으로 높습니다.",
        "concurrent_sessions_same_ip",
        _safe_float(behavior.get("concurrent_sessions_same_ip")),
        "high",
    )

    return evidence[:8]


def _realtime_report_confidence(
    decision: str,
    risk_score: float,
    hard_action: str,
    hard_rules: List[str],
    soft_rules: List[str],
    behavior_evidence: List[Dict[str, Any]],
    model_ready: bool,
) -> float:
    confidence = 0.30
    confidence += 0.25 if decision == "block" else 0.0
    confidence += 0.20 if hard_action == "block" else (0.10 if hard_action == "challenge" else 0.0)
    confidence += 0.15 if risk_score >= 0.90 else (0.10 if risk_score >= 0.70 else 0.0)
    confidence += min(0.15, 0.03 * len(hard_rules))
    confidence += min(0.10, 0.02 * len(soft_rules))
    confidence += min(0.10, 0.02 * len(behavior_evidence))
    if not model_ready:
        confidence -= 0.10
    return _clamp01(confidence)


def _resolve_openai_api_key() -> str:
    return str(os.getenv("OPENAI_API_KEY") or os.getenv("OPENAIAPIKEY") or "").strip()


def _mask_email(email: str) -> str:
    value = str(email or "").strip()
    if "@" not in value:
        return value
    local, domain = value.split("@", 1)
    if not local:
        return f"***@{domain}"
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "*" * max(2, len(local) - 2)
    return f"{masked_local}@{domain}"


def _compact_text(text: Any, max_len: int = 80) -> str:
    value = " ".join(str(text or "").split()).strip()
    if not value:
        return ""
    if len(value) <= max_len:
        return value
    return value[:max_len].rstrip(" .,;:") + "..."


def _build_realtime_block_user_message(
    *,
    llm_analysis: Dict[str, Any],
    rule_entries: List[str],
) -> str:
    # 사용자 노출 문구는 과도한 내부 규칙 노출 없이 간결하게 유지
    default_message = "비정상적인 접근 패턴이 감지되어 요청이 차단되었습니다."
    if not isinstance(llm_analysis, dict):
        return default_message

    candidates: List[str] = []
    summary_ko = _compact_text(llm_analysis.get("summary_ko", ""), max_len=90)
    if summary_ko:
        candidates.append(summary_ko)

    ui_fields = llm_analysis.get("ui_fields", {}) or {}
    if isinstance(ui_fields, dict):
        reasons = ui_fields.get("suspicion_reasons", []) or []
        if isinstance(reasons, list):
            for r in reasons[:2]:
                s = _compact_text(r, max_len=60)
                if s:
                    candidates.append(s)

    top_reasons = llm_analysis.get("top_reasons", []) or []
    if isinstance(top_reasons, list):
        for r in top_reasons[:2]:
            s = _compact_text(r, max_len=60)
            if s:
                candidates.append(s)

    if not candidates:
        for r in rule_entries[:2]:
            s = _compact_text(r, max_len=60)
            if s:
                candidates.append(s)

    for reason in candidates:
        # 내부 룰 식별자/임계값 표현은 사용자 메시지에서 제외
        if re.search(r"[<>=]|requests_last_|concurrent_sessions_|queue_|browser_", reason):
            continue
        if reason.endswith("차단되었습니다.") or reason.endswith("차단되었습니다"):
            return reason if reason.endswith(".") else reason + "."
        if reason.endswith("요청이 차단되었습니다."):
            return reason
        if reason.endswith("."):
            return f"{reason} 요청이 차단되었습니다."
        return f"{reason}로 요청이 차단되었습니다."

    return default_message


def _build_ui_fields_fallback(report_seed: Dict[str, Any]) -> Dict[str, Any]:
    risk_summary = report_seed.get("risk_summary", {}) if isinstance(report_seed, dict) else {}
    ui_seed = report_seed.get("ui_metric_seed", {}) if isinstance(report_seed, dict) else {}
    rule_evidence = report_seed.get("rule_evidence", []) if isinstance(report_seed, dict) else []
    behavior_evidence = report_seed.get("behavior_evidence", []) if isinstance(report_seed, dict) else []

    risk_score = _clamp01(_safe_float((risk_summary or {}).get("total_score"), 0.0))
    bot_score_100 = round(risk_score * 100.0, 1)

    suspicion_level = "low"
    if bot_score_100 >= 70:
        suspicion_level = "high"
    elif bot_score_100 >= 30:
        suspicion_level = "medium"

    status_title_ko = "정상 사용자"
    if suspicion_level == "medium":
        status_title_ko = "주의 사용자"
    elif suspicion_level == "high":
        status_title_ko = "매크로 의심 사용자"

    speed_variability_pct = max(0.0, _safe_float((ui_seed or {}).get("speed_variability_pct"), 0.0))
    path_curvature_rad = max(0.0, _safe_float((ui_seed or {}).get("path_curvature_rad"), 0.0))
    hover_sections_count = max(0, int(_safe_float((ui_seed or {}).get("hover_sections_count"), 0.0)))

    speed_judgement = "정상"
    if speed_variability_pct < 20:
        speed_judgement = "주의"
    if speed_variability_pct < 8:
        speed_judgement = "의심"

    curvature_judgement = "자연스러움"
    if path_curvature_rad < 0.8:
        curvature_judgement = "주의"
    if path_curvature_rad < 0.4:
        curvature_judgement = "의심"

    hover_judgement = "발견"
    if hover_sections_count <= 2:
        hover_judgement = "부족"
    if hover_sections_count == 0:
        hover_judgement = "미발견"

    reasons: List[str] = []
    for r in rule_evidence:
        s = str(r).strip()
        if s:
            reasons.append(s)
    for item in behavior_evidence:
        if isinstance(item, dict):
            s = str(item.get("description", "")).strip()
            if s:
                reasons.append(s)
    reasons = reasons[:5]

    if reasons:
        narrative = "의심 요인: " + ", ".join(reasons[:3]) + "."
    else:
        narrative = "의심 요인이 명확하게 관찰되지 않았습니다."

    return {
        "status_title_ko": status_title_ko,
        "bot_score": {
            "value": bot_score_100,
            "max": 100,
        },
        "speed_variability": {
            "value": round(speed_variability_pct, 2),
            "unit": "%",
            "judgement_ko": speed_judgement,
        },
        "path_curvature": {
            "value": round(path_curvature_rad, 3),
            "unit": "rad",
            "judgement_ko": curvature_judgement,
        },
        "hover_sections": {
            "value": hover_sections_count,
            "unit": "개",
            "judgement_ko": hover_judgement,
        },
        "suspicion_reasons": reasons,
        "suspicion_narrative_ko": narrative,
    }


def _build_markdown_report_fallback(
    *,
    report_seed: Dict[str, Any],
    ui_fields: Dict[str, Any],
    summary_ko: str,
    suspicion_level: str,
) -> str:
    ident = report_seed.get("report_identity", {}) if isinstance(report_seed, dict) else {}
    report_id = str((ident or {}).get("report_id", "")).strip() or "UNKNOWN_REPORT"
    target_masked = str((ident or {}).get("target_masked_user", "")).strip() or "unknown"
    risk_summary = report_seed.get("risk_summary", {}) if isinstance(report_seed, dict) else {}
    score_100 = _safe_float((ui_fields.get("bot_score", {}) or {}).get("value"), _safe_float(risk_summary.get("total_score")) * 100.0)
    level = str(suspicion_level).lower()
    if level not in {"low", "medium", "high"}:
        level = "medium"

    verdict_map = {
        "low": "✅ 정상 (매크로 징후 낮음)",
        "medium": "⚠️ 경고 (추가 확인 필요)",
        "high": "🚨 위험 (매크로 확률 매우 높음)",
    }
    verdict_text = verdict_map.get(level, verdict_map["medium"])
    status_title = str(ui_fields.get("status_title_ko", "")).strip() or "판정 결과"
    reasons = ui_fields.get("suspicion_reasons", [])
    if not isinstance(reasons, list):
        reasons = []
    reasons = [str(x).strip() for x in reasons if str(x).strip()][:5]
    if not reasons:
        reasons = [str(x).strip() for x in (report_seed.get("rule_evidence", []) or []) if str(x).strip()][:3]
    narrative = str(ui_fields.get("suspicion_narrative_ko", "")).strip()
    if not narrative:
        narrative = (
            "해당 세션은 정상 범위 지표를 보여 추가 의심 요인이 뚜렷하지 않습니다."
            if level == "low"
            else ("일부 지표가 정상 범위를 벗어나 추가 확인이 필요합니다." if level == "medium" else "다수 지표가 정상 범위를 벗어나 위험도가 높습니다.")
        )
    speed = ui_fields.get("speed_variability", {}) or {}
    curve = ui_fields.get("path_curvature", {}) or {}
    hover = ui_fields.get("hover_sections", {}) or {}
    separator = "--------------------------------------------------"
    lines = [
        f"[ Header Area: 정량적 지표 ] {separator}",
        f"ID: {report_id} / 대상: {target_masked}",
        f"스코어: [ {round(max(0.0, min(100.0, score_100)), 1)} / 100 ] / 판정: {verdict_text}",
        separator,
        "",
        f"[ Analysis Summary: 모델 분석 요약 ] {separator}",
        f"● 반응 속도(변동성): {round(_safe_float(speed.get('value')), 2)}{str(speed.get('unit', '%'))} ({str(speed.get('judgement_ko', '정상'))})",
        f"● 궤적 곡선성: {round(_safe_float(curve.get('value')), 3)}{str(curve.get('unit', 'rad'))} ({str(curve.get('judgement_ko', '자연스러움'))})",
        f"● 호버 구간: {int(_safe_float(hover.get('value')))}{str(hover.get('unit', '개'))} ({str(hover.get('judgement_ko', '발견'))})",
    ]
    if reasons:
        lines.append("● 주요 의심 요인:")
        lines.extend([f"  - {r}" for r in reasons[:3]])
    lines.append(separator)

    summary_text = summary_ko.strip()
    if not summary_text:
        summary_text = (
            "해당 세션은 정상 사용자 범위 내 지표를 보였습니다."
            if level == "low"
            else ("일부 자동화 의심 신호가 관찰되어 추가 확인이 권장됩니다." if level == "medium" else "자동화 의심 신호가 다수 관찰되어 위험도가 높습니다.")
        )

    lines.extend(
        [
            "",
            f"[ AI Insights: GPT 생성 종합 리포트 ] {separator}",
            f"\"{summary_text} {narrative}\"",
            separator,
        ]
    )
    return "\n".join(lines).strip()


def _generate_llm_report_payload(*, report_seed: Dict[str, Any]) -> Dict[str, Any]:
    fallback_ui_fields = _build_ui_fields_fallback(report_seed)
    fallback_level = "low"
    fallback_score = _clamp01(_safe_float(((report_seed.get("risk_summary", {}) or {}).get("total_score")), 0.0))
    if fallback_score >= 0.70:
        fallback_level = "high"
    elif fallback_score >= 0.30:
        fallback_level = "medium"
    fallback_markdown = _build_markdown_report_fallback(
        report_seed=report_seed,
        ui_fields=fallback_ui_fields,
        summary_ko="",
        suspicion_level=fallback_level,
    )
    api_key = _resolve_openai_api_key()
    if not LLM_REPORT_ENABLED:
        return {
            "enabled": False,
            "used": False,
            "reason": "llm_report_disabled",
            "ui_fields": fallback_ui_fields,
            "markdown_report": fallback_markdown,
        }
    if not api_key:
        return {
            "enabled": True,
            "used": False,
            "reason": "missing_openai_api_key",
            "ui_fields": fallback_ui_fields,
            "markdown_report": fallback_markdown,
        }

    model_input = {
        "report_identity": report_seed.get("report_identity", {}),
        "decision": report_seed.get("decision", "block"),
        "risk_summary": report_seed.get("risk_summary", {}),
        "rule_evidence": report_seed.get("rule_evidence", []),
        "behavior_evidence": report_seed.get("behavior_evidence", []),
        "model_evidence": report_seed.get("model_evidence", {}),
        "request_context": report_seed.get("request_context", {}),
        "ui_metric_seed": report_seed.get("ui_metric_seed", {}),
    }

    system_prompt = (
        "당신은 티켓팅 매크로 탐지 전문 리포트 작성 시스템입니다. "
        "입력된 행동 분석 데이터를 바탕으로 관리자가 즉시 판단할 수 있는 "
        "정확하고 구체적인 한국어 보안 리포트를 JSON으로만 출력하세요. "
        "모든 수치는 입력 데이터에서 직접 인용해야 하며, 추측이나 일반론적 문구를 금지합니다. "
        "판정 근거는 반드시 feature 이름과 수치를 명시하세요."
    )
    user_prompt = (
        "다음 JSON을 분석해 관리자 리포트용 결과를 작성하세요.\n"
        "반드시 JSON 객체만 출력하고 키는 아래 형식만 사용하세요:\n"
        "{"
        "\"summary_ko\": string, "
        "\"suspicion_level\": \"low|medium|high\", "
        "\"top_reasons\": string[], "
        "\"recommended_action\": \"allow|challenge|block\", "
        "\"confidence\": number(0~1), "
        "\"markdown_report\": string, "
        "\"ui_fields\": {"
        "\"status_title_ko\": string, "
        "\"bot_score\": {\"value\": number, \"max\": 100}, "
        "\"speed_variability\": {\"value\": number, \"unit\": \"%\", \"judgement_ko\": string}, "
        "\"path_curvature\": {\"value\": number, \"unit\": \"rad\", \"judgement_ko\": string}, "
        "\"hover_sections\": {\"value\": number, \"unit\": \"개\", \"judgement_ko\": string}, "
        "\"suspicion_reasons\": string[], "
        "\"suspicion_narrative_ko\": string"
        "}"
        "}\n"
        "규칙:\n"
        "- ui_metric_seed의 수치와 크게 벗어나지 않게 작성하세요.\n"
        "- model_evidence.top_feature_contributions를 우선 근거로 사용하세요. "
        "각 항목의 feature/value/normal_mean/contribution을 직접 인용해 설명하세요.\n"
        "- markdown_report는 아래 템플릿 형식을 반드시 그대로 사용하세요.\n"
        "  [ Header Area: 정량적 지표 ] --------------------------------------------------\n"
        "  ID: {report_id} / 대상: {masked_user}\n"
        "  스코어: [ {bot_score} / 100 ] / 판정: {이모지 포함 판정 문구}\n"
        "  --------------------------------------------------\n"
        "  \n"
        "  [ Analysis Summary: 모델 분석 요약 ] --------------------------------------------------\n"
        "  ● 반응 속도(변동성): {speed_variability_pct}% ({정상/의심/위험})\n"
        "  ● 궤적 곡선성: {path_curvature_rad}rad ({자연스러움/기계적/매우 기계적})\n"
        "  ● 호버 구간: {hover_sections_count}개 ({미발견/소수 발견/다수 발견})\n"
        "  ● 호버 미세 떨림(dwell std): {hover_std_dwell_ms}ms / 평균 정지: {hover_avg_dwell_ms}ms\n"
        "  ● 주요 기여 피처: top_feature_contributions 1~3위를 'feature(기여도: contribution)' 형식으로 나열 (기여 있을 때만)\n"
        "  ● 주요 의심 요인: rule_evidence, behavior_evidence 기반으로 (있을 때만)\n"
        "  --------------------------------------------------\n"
        "  \n"
        "  [ AI Insights: GPT 생성 종합 리포트 ] --------------------------------------------------\n"
        "  다음 3가지를 반드시 포함하는 3~5문장 줄글:\n"
        "  1) [수치 근거] speed_variability_pct, path_curvature_rad, bot_score_100 등 핵심 수치를 직접 인용\n"
        "  2) [판정 근거] top_feature_contributions 중 가장 영향력 높은 피처와 그 수치(value, normal_mean 대비)가 판정에 미친 영향 설명\n"
        "  3) [권장 조치] recommended_action(allow/challenge/block) 결정 이유를 한 문장으로 명시\n"
        "  --------------------------------------------------\n"
        "  - 판정 문구는 반드시 다음 중 하나를 사용하세요:\n"
        "    low (0~30): ✅ 정상 (매크로 징후 낮음)\n"
        "    medium (30~70): ⚠️ 의심 (추가 확인 필요)\n"
        "    high (70~100): 🚨 경고 (매크로 확률 매우 높음)\n"
        "- low 판정에서 '자동화 의심 정황이 확인되었습니다' 같은 모순 문구를 금지합니다.\n"
        "- suspicion_narrative_ko도 동일하게 수치 인용 + 판정 근거 + 권장 조치 3요소를 포함하세요.\n"
        "- Analysis Summary의 주요 기여 피처가 없으면 해당 항목을 생략하세요.\n"
        "- 호버 미세 떨림(hover_std_dwell_ms) 해석 규칙:\n"
        "  인간은 호버 시 손 떨림으로 std > 30ms 이상이 자연스러pc.\n"
        "  매크로는 정확하게 제어되어 std ≈0ms(또는 매우 낙음) 로 나타남.\n"
        "  hover_std_dwell_ms 값을 반드시 인급하고 '자연스러움 / 의심 / 강한 의심' 중 하나로 판정.\n"
        f"입력: {json.dumps(model_input, ensure_ascii=False)}"
    )

    request_body = {
        "model": LLM_REPORT_MODEL,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        req = urllib.request.Request(
            url=f"{LLM_REPORT_API_BASE}/chat/completions",
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=max(5, LLM_REPORT_TIMEOUT_SEC)) as resp:
            raw = resp.read().decode("utf-8")
        parsed = json.loads(raw)

        content = ""
        choices = parsed.get("choices", []) if isinstance(parsed, dict) else []
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message", {}) or {}
            msg_content = message.get("content", "")
            if isinstance(msg_content, list):
                parts: List[str] = []
                for item in msg_content:
                    if isinstance(item, dict):
                        parts.append(str(item.get("text", "")))
                    else:
                        parts.append(str(item))
                content = "".join(parts).strip()
            else:
                content = str(msg_content).strip()

        result = json.loads(content) if content else {}
        if not isinstance(result, dict):
            result = {}

        level = str(result.get("suspicion_level", "medium")).strip().lower()
        if level not in {"low", "medium", "high"}:
            level = "medium"

        action = str(result.get("recommended_action", "challenge")).strip().lower()
        if action not in {"allow", "challenge", "block"}:
            action = "challenge"

        reasons = result.get("top_reasons", [])
        if not isinstance(reasons, list):
            reasons = []
        reasons = [str(x).strip() for x in reasons if str(x).strip()][:5]

        confidence = _clamp01(_safe_float(result.get("confidence"), 0.0))

        ui_fields_raw = result.get("ui_fields", {})
        if not isinstance(ui_fields_raw, dict):
            ui_fields_raw = {}

        ui_status = str(ui_fields_raw.get("status_title_ko", fallback_ui_fields.get("status_title_ko", ""))).strip()
        if not ui_status:
            ui_status = str(fallback_ui_fields.get("status_title_ko", ""))

        ui_bot_raw = ui_fields_raw.get("bot_score", {})
        if not isinstance(ui_bot_raw, dict):
            ui_bot_raw = {}
        bot_value = max(0.0, min(100.0, _safe_float(ui_bot_raw.get("value"), _safe_float((fallback_ui_fields.get("bot_score", {}) or {}).get("value"), 0.0))))

        ui_speed_raw = ui_fields_raw.get("speed_variability", {})
        if not isinstance(ui_speed_raw, dict):
            ui_speed_raw = {}
        speed_value = max(0.0, _safe_float(ui_speed_raw.get("value"), _safe_float((fallback_ui_fields.get("speed_variability", {}) or {}).get("value"), 0.0)))
        speed_judgement = str(ui_speed_raw.get("judgement_ko", (fallback_ui_fields.get("speed_variability", {}) or {}).get("judgement_ko", "정상"))).strip() or "정상"

        ui_curve_raw = ui_fields_raw.get("path_curvature", {})
        if not isinstance(ui_curve_raw, dict):
            ui_curve_raw = {}
        curve_value = max(0.0, _safe_float(ui_curve_raw.get("value"), _safe_float((fallback_ui_fields.get("path_curvature", {}) or {}).get("value"), 0.0)))
        curve_judgement = str(ui_curve_raw.get("judgement_ko", (fallback_ui_fields.get("path_curvature", {}) or {}).get("judgement_ko", "자연스러움"))).strip() or "자연스러움"

        ui_hover_raw = ui_fields_raw.get("hover_sections", {})
        if not isinstance(ui_hover_raw, dict):
            ui_hover_raw = {}
        hover_value = max(0, int(_safe_float(ui_hover_raw.get("value"), _safe_float((fallback_ui_fields.get("hover_sections", {}) or {}).get("value"), 0.0))))
        hover_judgement = str(ui_hover_raw.get("judgement_ko", (fallback_ui_fields.get("hover_sections", {}) or {}).get("judgement_ko", "발견"))).strip() or "발견"

        ui_reasons = ui_fields_raw.get("suspicion_reasons", reasons)
        if not isinstance(ui_reasons, list):
            ui_reasons = reasons
        ui_reasons = [str(x).strip() for x in ui_reasons if str(x).strip()][:5]
        if not ui_reasons:
            ui_reasons = list((fallback_ui_fields.get("suspicion_reasons", []) or []))[:5]

        narrative = str(ui_fields_raw.get("suspicion_narrative_ko", "")).strip()
        if not narrative:
            narrative = str(fallback_ui_fields.get("suspicion_narrative_ko", "")).strip()

        summary_ko = str(result.get("summary_ko", "")).strip()
        markdown_report = str(result.get("markdown_report", "")).strip()
        if not markdown_report:
            markdown_report = _build_markdown_report_fallback(
                report_seed=report_seed,
                ui_fields=ui_fields_raw if isinstance(ui_fields_raw, dict) else fallback_ui_fields,
                summary_ko=summary_ko,
                suspicion_level=level,
            )

        ui_fields = {
            "status_title_ko": ui_status,
            "bot_score": {
                "value": round(bot_value, 1),
                "max": 100,
            },
            "speed_variability": {
                "value": round(speed_value, 2),
                "unit": "%",
                "judgement_ko": speed_judgement,
            },
            "path_curvature": {
                "value": round(curve_value, 3),
                "unit": "rad",
                "judgement_ko": curve_judgement,
            },
            "hover_sections": {
                "value": hover_value,
                "unit": "개",
                "judgement_ko": hover_judgement,
            },
            "suspicion_reasons": ui_reasons,
            "suspicion_narrative_ko": narrative,
        }

        return {
            "enabled": True,
            "used": True,
            "provider": "openai",
            "model": LLM_REPORT_MODEL,
            "summary_ko": summary_ko,
            "suspicion_level": level,
            "top_reasons": reasons,
            "recommended_action": action,
            "confidence": round(confidence, 6),
            "ui_fields": ui_fields,
            "markdown_report": markdown_report,
        }
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            detail = str(e)
        return {
            "enabled": True,
            "used": False,
            "error": f"http_error:{e.code}",
            "detail": detail[:500],
            "ui_fields": fallback_ui_fields,
            "markdown_report": fallback_markdown,
        }
    except Exception as e:
        return {
            "enabled": True,
            "used": False,
            "error": str(e),
            "ui_fields": fallback_ui_fields,
            "markdown_report": fallback_markdown,
        }


def _build_realtime_block_report(
    *,
    request: Request,
    server_log: Dict[str, Any],
    browser_log: Optional[Dict[str, Any]],
    server_log_path: str,
    bot_folder: str,
) -> Dict[str, str]:
    # 함수명은 기존 호환을 위해 유지하지만, 내부적으로는 allow/challenge/block 모두 처리한다.
    risk = (server_log or {}).get("risk", {}) or {}
    decision = str(risk.get("decision", "allow")).strip().lower()
    if decision not in {"allow", "challenge", "block"}:
        decision = "challenge"

    hard_rules = list(risk.get("hard_rules_triggered", []) or [])
    soft_rules = list(risk.get("soft_rules_triggered", []) or [])
    rule_entries = hard_rules + soft_rules
    behavior_evidence = _runtime_behavior_evidence(browser_log, server_log)

    identity = (server_log or {}).get("identity", {}) or {}
    metadata = (server_log or {}).get("metadata", {}) or {}
    session = (server_log or {}).get("session", {}) or {}
    behavior = (server_log or {}).get("behavior", {}) or {}
    browser_meta = (browser_log or {}).get("metadata", {}) or {}

    user_id = (
        str(browser_meta.get("user_email", "")).strip()
        or str(identity.get("user_id_hash", "")).strip()
        or "unknown"
    )
    booking_id = str(browser_meta.get("booking_id", "")).strip()

    confidence = _realtime_report_confidence(
        decision=decision,
        risk_score=_safe_float(risk.get("risk_score")),
        hard_action=str(risk.get("hard_action", "none")),
        hard_rules=hard_rules,
        soft_rules=soft_rules,
        behavior_evidence=behavior_evidence,
        model_ready=bool(risk.get("model_ready", False)),
    )

    features: Dict[str, float] = {}
    if browser_log and _extract_browser_features_runtime is not None:
        try:
            features = _extract_browser_features_runtime(browser_log)
        except Exception:
            features = {}

    model_top_contributions: List[Dict[str, Any]] = []
    if (
        features
        and _model_top_contributors_runtime is not None
        and not bool(risk.get("model_skipped", False))
    ):
        try:
            runtime = _load_risk_runtime()
            if runtime:
                params = runtime.get("params") or {}
                model_top_contributions = _model_top_contributors_runtime(
                    features=features,
                    params=params,
                    model_artifact=runtime.get("model_artifact"),
                    top_k=5,
                )
        except Exception:
            model_top_contributions = []

    model_top_feature_names = [
        str(item.get("feature", "")).strip()
        for item in model_top_contributions
        if str(item.get("feature", "")).strip()
    ]

    seat_click_interval = _safe_float(features.get("seat_avg_click_interval"))
    perf_click_interval = _safe_float(features.get("perf_avg_click_interval"))
    avg_click_interval = seat_click_interval if seat_click_interval > 0 else perf_click_interval
    seat_speed_std = _safe_float(features.get("seat_std_mouse_speed"))
    perf_speed_std = _safe_float(features.get("perf_std_mouse_speed"))
    speed_variability_pct = seat_speed_std if seat_speed_std > 0 else perf_speed_std
    seat_straightness = _safe_float(features.get("seat_avg_straightness"), -1.0)
    perf_straightness = _safe_float(features.get("perf_avg_straightness"), -1.0)
    straightness = seat_straightness if seat_straightness >= 0 else perf_straightness
    if straightness < 0:
        straightness = 1.0
    straightness = max(0.0, min(1.0, straightness))
    path_curvature_rad = (1.0 - straightness) * float(np.pi)
    seat_hover_count = int(_safe_float(features.get("seat_hover_count"), 0.0))
    perf_hover_count = int(_safe_float(features.get("perf_hover_count"), 0.0))
    hover_sections_count = seat_hover_count if seat_hover_count > 0 else perf_hover_count

    top_features: List[str] = []
    for item in behavior_evidence:
        desc = str(item.get("description", "")).strip()
        if desc and desc not in top_features:
            top_features.append(desc)
    for name in model_top_feature_names:
        if name not in top_features:
            top_features.append(name)
    if not top_features:
        top_features = rule_entries[:2]

    total_score = round(_safe_float(risk.get("risk_score")), 6)
    if total_score >= 0.70:
        grade = "High"
    elif total_score >= 0.30:
        grade = "Medium"
    else:
        grade = "Low"

    account_age_days = int(_safe_float(session.get("account_age_days")))
    is_verified = str(session.get("login_state", "")).strip().lower() in {"logged_in", "member"}
    past_successful_orders = int(_safe_float(session.get("past_successful_orders"), 0.0))
    device_change_count = int(_safe_float(behavior.get("concurrent_sessions_same_device"), 0.0))

    created_at = datetime.utcnow().isoformat() + "Z"
    request_id = str(metadata.get("request_id", "")).strip() or f"req_{uuid.uuid4().hex}"
    safe_request_id = _sanitize_filename_part(request_id, fallback=f"req_{uuid.uuid4().hex}")
    date_str = datetime.now().strftime("%Y%m%d")
    safe_booking_id = _sanitize_filename_part(booking_id, fallback="nobooking")
    safe_decision = _sanitize_filename_part(decision, fallback="challenge")
    report_id = f"{safe_booking_id}_{safe_request_id}_{safe_decision}_REPORT"
    masked_email = _mask_email(str(browser_meta.get("user_email", "")).strip() or user_id)
    report_filename = f"{date_str}_{safe_booking_id}_{safe_request_id}_{safe_decision}.json"
    report_path = os.path.join(BLOCK_REPORT_DIR, report_filename)
    llm_report_filename_json = f"{date_str}_{safe_booking_id}_{safe_request_id}_{safe_decision}_llm.json"
    llm_report_json_path = os.path.join(BLOCK_REPORT_DIR, llm_report_filename_json)
    llm_report_filename_txt = f"{date_str}_{safe_booking_id}_{safe_request_id}_{safe_decision}_llm.txt"
    llm_report_path = os.path.join(BLOCK_REPORT_DIR, llm_report_filename_txt)

    llm_seed = {
        "report_identity": {
            "report_id": report_id,
            "booking_id": booking_id,
            "target_masked_user": masked_email,
        },
        "decision": decision,
        "risk_summary": {
            "total_score": total_score,
            "grade": grade,
        },
        "rule_evidence": rule_entries,
        "behavior_evidence": behavior_evidence,
        "model_evidence": {
            "anomaly_score": round(_safe_float(risk.get("model_score")), 6),
            "top_features": (model_top_feature_names[:3] if model_top_feature_names else top_features[:3]),
            "top_feature_contributions": model_top_contributions,
            "model_ready": bool(risk.get("model_ready", False)),
            "model_skipped": bool(risk.get("model_skipped", False)),
        },
        "request_context": {
            "request_id": request_id,
            "flow_id": str(metadata.get("flow_id", "")),
            "session_id": str(metadata.get("session_id", "")),
            "endpoint": str((server_log.get("request", {}) or {}).get("endpoint", request.url.path)),
            "method": str((server_log.get("request", {}) or {}).get("method", request.method)),
            "bot_type": bot_folder,
        },
        "ui_metric_seed": {
            "bot_score_100": round(total_score * 100.0, 1),
            "speed_variability_pct": round(max(0.0, speed_variability_pct), 2),
            "path_curvature_rad": round(max(0.0, path_curvature_rad), 3),
            "hover_sections_count": max(0, hover_sections_count),
            "hover_std_dwell_ms": round(max(0.0, _safe_float(features.get("seat_hover_std_dwell_ms") or features.get("perf_hover_std_dwell_ms"))), 2),
            "hover_avg_dwell_ms": round(max(0.0, _safe_float(features.get("seat_hover_avg_dwell_ms") or features.get("perf_hover_avg_dwell_ms"))), 2),
        },
    }
    llm_analysis = _generate_llm_report_payload(report_seed=llm_seed)
    llm_ui_fields = llm_analysis.get("ui_fields", _build_ui_fields_fallback(llm_seed))
    if decision == "block":
        user_message = _build_realtime_block_user_message(
            llm_analysis=llm_analysis,
            rule_entries=rule_entries,
        )
    elif decision == "challenge":
        user_message = "의심 신호가 감지되어 추가 확인이 필요합니다."
    else:
        user_message = "정상 범위로 판단되었습니다."

    recommended_action = str(llm_analysis.get("recommended_action", decision)).strip().lower()
    if recommended_action not in {"allow", "challenge", "block"}:
        recommended_action = decision

    llm_report_payload = {
        "report_type": "realtime_risk_llm_v1",
        "created_at_iso": created_at,
        "report_id": report_id,
        "request_id": request_id,
        "booking_id": booking_id,
        "flow_id": str(metadata.get("flow_id", "")),
        "session_id": str(metadata.get("session_id", "")),
        "target_masked_user": masked_email,
        "decision": decision,
        "user_message": user_message,
        "llm_analysis": llm_analysis,
        "ui_fields": llm_ui_fields,
        "markdown_report": str(llm_analysis.get("markdown_report", "")).strip(),
    }
    llm_report_error = ""
    markdown_report_text = str(llm_analysis.get("markdown_report", "")).strip()
    try:
        with open(llm_report_json_path, "w", encoding="utf-8") as f:
            json.dump(llm_report_payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        llm_report_error = f"json_write_error:{e}"

    try:
        llm_txt_lines = [
            f"report_id: {report_id}",
            f"created_at_iso: {created_at}",
            f"booking_id: {booking_id}",
            f"flow_id: {str(metadata.get('flow_id', ''))}",
            f"session_id: {str(metadata.get('session_id', ''))}",
            f"decision: {decision}",
            "",
            f"user_message: {user_message}",
            "",
            "=== LLM REPORT ===",
            markdown_report_text or "(markdown_report is empty)",
        ]
        with open(llm_report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(llm_txt_lines))
    except Exception as e:
        if llm_report_error:
            llm_report_error += f"; txt_write_error:{e}"
        else:
            llm_report_error = f"txt_write_error:{e}"

    report = {
        "report_type": "realtime_risk_v1",
        "created_at_iso": created_at,
        "report_id": report_id,
        "user_id": user_id,
        "target_masked_user": masked_email,
        "booking_id": booking_id,
        "flow_id": str(metadata.get("flow_id", "")),
        "session_id": str(metadata.get("session_id", "")),
        "decision": decision,
        "recommendation": recommended_action,
        "confidence": round(confidence, 6),
        "risk_summary": {
            "total_score": total_score,
            "grade": grade,
        },
        "evidence_logs": {
            "rule": rule_entries,
            "model": {
                "anomaly_score": round(_safe_float(risk.get("model_score")), 6),
                "top_features": (model_top_feature_names[:3] if model_top_feature_names else top_features[:3]),
                "top_feature_contributions": model_top_contributions,
            },
            "behavior": {
                "avg_click_interval": f"{round(avg_click_interval, 2)}ms" if avg_click_interval > 0 else "",
                "device_change_count": device_change_count,
            },
            "trust": {
                "account_age_days": account_age_days,
                "is_verified": bool(is_verified),
                "past_successful_orders": past_successful_orders,
            },
        },
        "request_context": {
            "request_id": request_id,
            "event_id": str(metadata.get("event_id", "")),
            "method": str((server_log.get("request", {}) or {}).get("method", request.method)),
            "endpoint": str((server_log.get("request", {}) or {}).get("endpoint", request.url.path)),
            "bot_type": bot_folder,
            "server_log_path": server_log_path,
        },
        "actions": {
            "realtime_enforced": decision in {"challenge", "block"},
            "response_status_code": 403 if decision == "block" else (202 if decision == "challenge" else 200),
        },
        "user_message": user_message,
        "ui_fields": llm_ui_fields,
        "llm_analysis": llm_analysis,
        "markdown_report": markdown_report_text,
        "llm_report_path": llm_report_path,
        "llm_report_json_path": llm_report_json_path,
        "llm_report_error": llm_report_error,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    index_entry = {
        "created_at_iso": created_at,
        "request_id": request_id,
        "report_id": report_id,
        "user_id": user_id,
        "booking_id": booking_id,
        "flow_id": str(metadata.get("flow_id", "")),
        "decision": decision,
        "risk_score": total_score,
        "report_path": report_path,
        "llm_report_path": llm_report_path,
        "llm_report_json_path": llm_report_json_path,
    }
    with open(BLOCK_REPORT_INDEX_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(index_entry, ensure_ascii=False) + "\n")

    return {
        "report_path": report_path,
        "llm_report_path": llm_report_path,
        "llm_report_json_path": llm_report_json_path,
        "user_message": user_message,
    }


@app.middleware('http')
async def server_log_middleware(request: Request, call_next):
    if QUEUE_ENFORCE_SEAT_GATE and request.method == "GET" and request.url.path.endswith("/seat_select.html"):
        ticket = str(request.cookies.get(QUEUE_TICKET_COOKIE, "") or "").strip()
        if not _validate_entry_ticket(ticket):
            return RedirectResponse(url="/queue.html?reason=queue_required", status_code=302)

    # Collect and store server logs for all /api/* requests.
    # Real-time enforcement is applied to booking flow endpoints.
    if not request.url.path.startswith('/api/'):
        return await call_next(request)

    enforce_decision = _should_enforce_realtime_decision(request)

    start = time.time()
    body_bytes = b""
    browser_payload = None
    flow_id = None
    session_id = None
    performance_id = None
    user_email = None
    bot_type = None
    request_payload: Optional[Dict[str, Any]] = None

    if request.method in ('POST', 'PUT', 'PATCH'):
        try:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    data = json.loads(body_bytes)
                    if isinstance(data, dict):
                        request_payload = data
                        if request.url.path == '/api/logs':
                            browser_payload = data
                            meta = data.get('metadata', {})
                            flow_id = meta.get('flow_id')
                            session_id = meta.get('session_id')
                            performance_id = meta.get('performance_id')
                            user_email = meta.get('user_email')
                            bot_type = meta.get('bot_type')
                        else:
                            flow_id = data.get('flow_id') or flow_id
                            session_id = data.get('session_id') or session_id
                            performance_id = data.get('performance_id') or performance_id
                            user_email = data.get('user_email') or data.get('email') or user_email
                            bot_type = data.get('bot_type') or bot_type
                except Exception:
                    pass

            async def receive():
                return {'type': 'http.request', 'body': body_bytes}
            request._receive = receive
        except Exception:
            body_bytes = b""

    response = await call_next(request)

    try:
        now_ms = int(time.time() * 1000)
        ip_key = _extract_ip_key(request)
        behavior = _update_behavior(ip_key, request.url.path, now_ms)

        latency_ms = int((time.time() - start) * 1000)
        status_code = response.status_code
        try:
            response_size_bytes = int(response.headers.get('content-length') or 0)
        except Exception:
            response_size_bytes = 0

        ip_raw = '' if ip_key == 'unknown' else ip_key
        ip_hash = _hash_value(ip_raw)
        ip_subnet = _ip_subnet(ip_raw)
        ua = request.headers.get('user-agent', '')
        ua_hash = _hash_value(ua)
        accept_lang = request.headers.get('accept-language', '')

        login_summary = _get_login_summary(ip_key, now_ms)

        if not flow_id:
            flow_id = request.headers.get('x-flow-id', '')
        if not session_id:
            session_id = request.headers.get('x-session-id', '')

        request_id = f"req_{uuid.uuid4().hex}"
        event_id = f"evt_{uuid.uuid4().hex}"

        server_log = {
            'metadata': {
                'event_id': event_id,
                'request_id': request_id,
                'flow_id': flow_id or '',
                'session_id': session_id or '',
                'received_epoch_ms': now_ms,
                'server_region': '',
                'environment': 'local'
            },
            'identity': {
                'user_id_hash': _hash_value(user_email) if user_email else '',
                'account_id_hash': '',
                'device_id_hash': '',
                'session_fingerprint_hash': '',
                'ip_hash': ip_hash,
                'ip_raw': ip_raw,
                'ip_subnet': ip_subnet,
                'asn': '',
                'geo': {'country': '', 'region': '', 'city': ''}
            },
            'client_fingerprint': {
                'user_agent_hash': ua_hash,
                'tls_fingerprint': '',
                'accept_language': accept_lang,
                'timezone_offset_min': 0,
                'screen': {'w': 0, 'h': 0, 'ratio': 0}
            },
            'request': {
                'endpoint': request.url.path,
                'route': request.url.path,
                'method': request.method,
                'query_size_bytes': len(request.url.query or ''),
                'body_size_bytes': len(body_bytes),
                'content_type': request.headers.get('content-type', ''),
                'headers_whitelist': {
                    'referer': request.headers.get('referer', ''),
                    'origin': request.headers.get('origin', ''),
                    'x_forwarded_for': request.headers.get('x-forwarded-for', ''),
                    'sec_ch_ua': request.headers.get('sec-ch-ua', '')
                }
            },
            'response': {
                'status_code': status_code,
                'latency_ms': latency_ms,
                'response_size_bytes': response_size_bytes,
                'error_code': '',
                'retry_after_ms': 0
            },
            'session': {
                'session_created_epoch_ms': 0,
                'last_activity_epoch_ms': now_ms,
                'session_age_ms': 0,
                'login_state': 'guest',
                'account_age_days': 0,
                'payment_token_hash': ''
            },
            'queue': {
                'queue_id': '',
                'join_epoch_ms': 0,
                'enter_trigger': '',
                'position': 0,
                'poll_interval_ms_stats': {'min': 0, 'p50': 0, 'p95': 0},
                'jump_count': 0
            },
            'seat': {
                'seat_query_count': 0,
                'reserve_attempt_count': 0,
                'reserve_fail_codes': [],
                'seat_hold_ms': 0,
                'seat_release_ms': 0
            },
            'behavior': {
                'requests_last_1s': behavior['requests_last_1s'],
                'requests_last_10s': behavior['requests_last_10s'],
                'requests_last_60s': behavior['requests_last_60s'],
                'unique_endpoints_last_60s': behavior['unique_endpoints_last_60s'],
                'login_attempts_last_10m': login_summary['login_attempts_last_10m'],
                'login_fail_count_last_10m': login_summary['login_fail_count_last_10m'],
                'login_success_count_last_10m': login_summary['login_success_count_last_10m'],
                'login_unique_accounts_last_10m': login_summary['login_unique_accounts_last_10m'],
                'retry_count_last_5m': 0,
                'concurrent_sessions_same_device': 0,
                'concurrent_sessions_same_ip': 0
            },
            'security': {
                'captcha_required': False,
                'captcha_passed': False,
                'rate_limited': False,
                'blocked': False,
                'block_reason': ''
            }
        }

        queue_snapshot = _queue_snapshot_for_log(
            request=request,
            flow_id=str(flow_id or ""),
            session_id=str(session_id or ""),
            request_payload=request_payload,
        )
        server_log['queue'].update(queue_snapshot)

        risk_result = _score_request_risk(browser_payload, server_log)
        risk_payload = {
            'risk_score': round(_safe_float(risk_result.get('risk_score')), 6),
            'decision': str(risk_result.get('decision', 'allow')),
            'rules_triggered': risk_result.get('rules_triggered', []),
            'soft_rules_triggered': risk_result.get('soft_rules_triggered', []),
            'hard_rules_triggered': risk_result.get('hard_rules_triggered', []),
            'hard_action': str(risk_result.get('hard_action', 'none')),
            'rule_score': round(_safe_float(risk_result.get('rule_score')), 6),
            'model_score': round(_safe_float(risk_result.get('model_score')), 6),
            'model_type': str(risk_result.get('model_type', 'none')),
            'model_ready': bool(risk_result.get('model_ready', False)),
            'model_skipped': bool(risk_result.get('model_skipped', False)),
            'runtime_error': str(risk_result.get('runtime_error', '')),
            'threshold_allow': round(_safe_float(risk_result.get('threshold_allow')), 6),
            'threshold_challenge': round(_safe_float(risk_result.get('threshold_challenge')), 6),
            'review_required': bool(risk_result.get('review_required', False)),
            'block_recommended': bool(risk_result.get('block_recommended', False)),
        }

        if risk_payload['decision'] == 'block':
            server_log['security']['blocked'] = True
            server_log['security']['block_reason'] = 'abnormal_access_detected'
            server_log['security']['block_message'] = '비정상적인 접근'
            risk_payload['alert_message'] = '비정상적인 접근'
            print(
                f"[SECURITY][BLOCK] 비정상적인 접근 감지 "
                f"(request_id={request_id}, flow_id={flow_id or ''}, risk_score={risk_payload.get('risk_score')})"
            )
        elif risk_payload['decision'] == 'challenge':
            server_log['security']['captcha_required'] = True

        date_str = datetime.now().strftime('%Y%m%d')
        raw_bot_type = str(bot_type or '').strip()
        if not raw_bot_type:
            folder_name = 'real_human'
        else:
            folder_name = re.sub(r'[^a-zA-Z0-9_\-]', '', raw_bot_type) or 'real_human'

        bot_dir = os.path.join(SERVER_LOGS_DIR, folder_name)
        os.makedirs(bot_dir, exist_ok=True)
        safe_perf_id = _sanitize_filename_part(performance_id, fallback="unknownperf")
        safe_flow_id = _sanitize_filename_part(flow_id, fallback="noflow")
        safe_endpoint = _sanitize_filename_part(str(request.url.path).replace('/', '_'), fallback="api")
        safe_method = _sanitize_filename_part(str(request.method).lower(), fallback="req")
        safe_request_id = _sanitize_filename_part(request_id, fallback=f"req_{uuid.uuid4().hex}")

        filename = (
            f"{date_str}_{safe_perf_id}_{safe_flow_id}_"
            f"{safe_endpoint}_{safe_method}_{safe_request_id}.json"
        )
        filepath = os.path.join(bot_dir, filename)

        try:
            score_paths = _save_score_snapshots(
                request=request,
                metadata=server_log.get("metadata", {}) or {},
                performance_id=performance_id,
                flow_id=flow_id,
                session_id=session_id,
                bot_type=folder_name,
                risk_payload=risk_payload,
            )
            risk_payload.update(score_paths)
        except Exception as score_error:
            risk_payload["score_snapshot_error"] = str(score_error)

        should_build_risk_report = (request.url.path == '/api/logs') or (risk_payload['decision'] == 'block')
        if should_build_risk_report:
            try:
                # 리포트 함수는 risk 컨텍스트를 사용하므로 호출 직전에만 주입한다.
                server_log['risk'] = dict(risk_payload)
                report_result = _build_realtime_block_report(
                    request=request,
                    server_log=server_log,
                    browser_log=browser_payload,
                    server_log_path=filepath,
                    bot_folder=folder_name,
                )
                realtime_report_path = str((report_result or {}).get("report_path", "")).strip()
                if realtime_report_path:
                    risk_payload['realtime_report_path'] = realtime_report_path
                llm_report_path = str((report_result or {}).get("llm_report_path", "")).strip()
                if llm_report_path:
                    risk_payload['llm_report_path'] = llm_report_path
                llm_report_json_path = str((report_result or {}).get("llm_report_json_path", "")).strip()
                if llm_report_json_path:
                    risk_payload['llm_report_json_path'] = llm_report_json_path

                user_message = str((report_result or {}).get("user_message", "")).strip()
                if user_message and risk_payload['decision'] == 'block':
                    server_log['security']['block_message'] = user_message
                    risk_payload['alert_message'] = user_message
            except Exception as report_error:
                risk_payload['realtime_report_error'] = str(report_error)
            finally:
                # 서버 원본 로그에는 risk 필드를 남기지 않는다.
                server_log.pop('risk', None)

        server_log.pop('risk', None)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(server_log, f, ensure_ascii=False, indent=2)

        # Enforce real action on booking flow endpoints.
        if enforce_decision and risk_payload['decision'] == 'block':
            return JSONResponse(
                status_code=403,
                content={
                    'success': False,
                    'decision': 'block',
                    'message': str(server_log.get('security', {}).get('block_message') or '비정상적인 접근으로 요청이 차단되었습니다.'),
                    'risk': risk_payload,
                },
            )
        if enforce_decision and risk_payload['decision'] == 'challenge':
            return JSONResponse(
                status_code=202,
                content={
                    'success': False,
                    'decision': 'challenge',
                    'message': 'additional verification required',
                    'challenge_required': True,
                    'risk': risk_payload,
                },
            )
    except Exception:
        pass

    return response

# Pydantic 모델 정의
class SignupData(BaseModel):
    email: str
    password: str
    name: str
    phone: str
    birthdate: Optional[str] = None

class LoginData(BaseModel):
    email: str
    password: str

class LogData(BaseModel):
    metadata: Dict[str, Any]
    stages: Dict[str, Any]

class QueueJoinData(BaseModel):
    performance_id: str
    flow_id: str
    session_id: str
    user_email: Optional[str] = ""
    bot_type: Optional[str] = ""
    start_token: Optional[str] = ""


class BookingStartTokenData(BaseModel):
    performance_id: str
    flow_id: str
    session_id: str
    user_email: Optional[str] = ""
    bot_type: Optional[str] = ""


class QueueEnterData(BaseModel):
    queue_id: str
    performance_id: Optional[str] = ""
    flow_id: Optional[str] = ""
    session_id: Optional[str] = ""

class RestrictUser(BaseModel):
    email: str
    level: int  # 1, 2, 3
    reason: str
    restricted_by: str = "admin@ticket.com"

class CancelBooking(BaseModel):
    filename: str
    reason: str = ""
    cancelled_by: str = "admin@ticket.com"

# API 엔드포인트

# 회원가입
@app.post("/api/auth/signup")
async def signup(signup_data: SignupData):
    """새 사용자를 등록합니다."""
    try:
        # 사용자 파일 읽기
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users_db = json.load(f)
        
        # 이메일 중복 체크
        if any(user['email'] == signup_data.email for user in users_db['users']):
            raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
        
        # 새 사용자 추가
        new_user = {
            "email": signup_data.email,
            "password": signup_data.password,  # 실제로는 해시 처리 필요
            "name": signup_data.name,
            "phone": signup_data.phone,
            "birthdate": signup_data.birthdate,
            "created_at": datetime.now().isoformat()
        }
        users_db['users'].append(new_user)
        
        # 파일에 저장
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_db, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": "회원가입이 완료되었습니다.",
            "user": {
                "email": new_user['email'],
                "name": new_user['name']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 실패: {str(e)}")

# 로그인
@app.post("/api/auth/login")
async def login(login_data: LoginData, request: Request):
    """사용자 로그인을 처리합니다."""
    try:
        now_ms = int(time.time() * 1000)
        ip_key = _extract_ip_key(request)

        # 사용자 파일 읽기
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users_db = json.load(f)
        
        # 사용자 찾기
        user = next((u for u in users_db['users'] if u['email'] == login_data.email), None)
        
        if not user:
            _record_login_attempt(ip_key, login_data.email, False, now_ms)
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
        
        if user['password'] != login_data.password:  # 실제로는 해시 비교 필요
            _record_login_attempt(ip_key, login_data.email, False, now_ms)
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

        _record_login_attempt(ip_key, login_data.email, True, now_ms)
        
        # 제한 상태 확인
        restriction = None
        try:
            with open(RESTRICTED_FILE, 'r', encoding='utf-8') as f:
                restricted_db = json.load(f)
            restricted_user = next((r for r in restricted_db['restricted_users'] if r['email'] == user['email']), None)
            if restricted_user:
                # 만료 체크 (영구 제한은 expires_at이 null)
                if restricted_user.get('expires_at'):
                    expires_at = datetime.fromisoformat(restricted_user['expires_at'])
                    if datetime.now().astimezone() > expires_at:
                        # 만료됨 - 자동 해제
                        restricted_db['restricted_users'] = [r for r in restricted_db['restricted_users'] if r['email'] != user['email']]
                        with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
                            json.dump(restricted_db, f, ensure_ascii=False, indent=2)
                    else:
                        restriction = {
                            "level": restricted_user['level'],
                            "reason": restricted_user['reason'],
                            "expires_at": restricted_user['expires_at'],
                            "restricted_at": restricted_user['restricted_at']
                        }
                else:
                    # 영구 제한
                    restriction = {
                        "level": restricted_user['level'],
                        "reason": restricted_user['reason'],
                        "expires_at": None,
                        "restricted_at": restricted_user['restricted_at']
                    }
        except:
            pass

        return {
            "success": True,
            "message": "로그인 성공",
            "user": {
                "email": user['email'],
                "name": user['name'],
                "phone": user['phone']
            },
            "restriction": restriction
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 실패: {str(e)}")


@app.post("/api/booking/start-token")
async def booking_start_token(token_data: BookingStartTokenData):
    performance_id = _sanitize_filename_part(token_data.performance_id, fallback="")
    flow_id = _sanitize_filename_part(token_data.flow_id, fallback="")
    session_id = _sanitize_filename_part(token_data.session_id, fallback="")
    if not performance_id or not flow_id or not session_id:
        raise HTTPException(status_code=400, detail="performance_id, flow_id, session_id are required")

    now_ms = _now_ms()
    with QUEUE_LOCK:
        _cleanup_queue_locked(now_ms)
        token_state = _issue_start_token_locked(
            performance_id=performance_id,
            flow_id=flow_id,
            session_id=session_id,
            user_email=str(token_data.user_email or ""),
            bot_type=str(token_data.bot_type or ""),
            now_ms=now_ms,
        )

    return {
        "success": True,
        "start_token": token_state["token"],
        "expires_epoch_ms": int(token_state["expires_epoch_ms"]),
    }


@app.post("/api/queue/join")
async def queue_join(queue_data: QueueJoinData):
    performance_id = _sanitize_filename_part(queue_data.performance_id, fallback="")
    flow_id = _sanitize_filename_part(queue_data.flow_id, fallback="")
    session_id = _sanitize_filename_part(queue_data.session_id, fallback="")
    start_token = str(queue_data.start_token or "").strip()
    if not performance_id or not flow_id or not session_id:
        raise HTTPException(status_code=400, detail="performance_id, flow_id, session_id are required")

    now_ms = _now_ms()
    with QUEUE_LOCK:
        _cleanup_queue_locked(now_ms)
        start_token_state: Optional[Dict[str, Any]] = None

        if QUEUE_REQUIRE_START_TOKEN:
            start_token_state = _get_valid_start_token_state_locked(
                token=start_token,
                performance_id=performance_id,
                flow_id=flow_id,
                session_id=session_id,
                now_ms=now_ms,
            )
            if not start_token_state:
                raise HTTPException(status_code=403, detail="invalid or missing booking start token")

        existing = _find_active_queue_locked(performance_id, flow_id, session_id)
        if existing:
            payload = _queue_status_payload_locked(existing, now_ms)
            return {
                "success": True,
                "rejoined": True,
                "queue": payload,
            }

        base_wait_ms = max(0, int(QUEUE_BASE_WAIT_MS))
        slot_ms = max(1, int(QUEUE_SLOT_MS))
        join_delay_step_ms = max(1, int(QUEUE_JOIN_DELAY_STEP_MS))
        join_delay_cap_steps = max(0, int(QUEUE_JOIN_DELAY_CAP_STEPS))
        join_delay_penalty_unit_ms = max(0, int(QUEUE_JOIN_DELAY_PENALTY_MS))
        since_open_step_ms = max(1, int(QUEUE_SINCE_OPEN_STEP_MS))
        since_open_cap_steps = max(0, int(QUEUE_SINCE_OPEN_CAP_STEPS))
        since_open_penalty_unit_ms = max(0, int(QUEUE_SINCE_OPEN_PENALTY_MS))

        start_issued_epoch_ms = int((start_token_state or {}).get("issued_epoch_ms", now_ms))
        open_epoch_ms = int((start_token_state or {}).get("open_epoch_ms", start_issued_epoch_ms))

        # 핵심 정책: 대기열 페이지 진입 시각(now_ms) 기준으로
        # 오픈(open_epoch_ms) 대비 늦게 진입할수록 대기 페널티를 누적한다.
        since_open_ms = max(0, now_ms - open_epoch_ms)
        since_open_steps = _penalty_steps(
            elapsed_ms=since_open_ms,
            step_ms=since_open_step_ms,
            cap_steps=since_open_cap_steps,
        )
        since_open_penalty_ms = int(since_open_steps * since_open_penalty_unit_ms)

        # token 발급 후 join 지연은 관측 지표로는 남기되,
        # 실제 ready 계산은 queue 진입 시각 기반 정책을 우선한다.
        join_delay_ms = max(0, now_ms - start_issued_epoch_ms)
        join_delay_steps = _penalty_steps(
            elapsed_ms=join_delay_ms,
            step_ms=join_delay_step_ms,
            cap_steps=join_delay_cap_steps,
        )
        join_delay_penalty_ms = int(join_delay_steps * join_delay_penalty_unit_ms)

        # 빠르게 진입할수록(shorter since_open_ms) shorter wait가 되도록 구성.
        earliest_ready_ms = now_ms + base_wait_ms + since_open_penalty_ms
        next_slot_ms = int(QUEUE_NEXT_READY_SLOT_BY_PERF.get(performance_id, 0))
        ready_epoch_ms = max(earliest_ready_ms, next_slot_ms)
        wait_ms = max(0, ready_epoch_ms - now_ms)

        queue_id = f"q_{uuid.uuid4().hex}"
        seed_base = f"{performance_id}|{flow_id}|{session_id}|{queue_id}"
        disp_start = _deterministic_int_from_key(
            f"{seed_base}:start",
            QUEUE_DISPLAY_START_MIN,
            QUEUE_DISPLAY_START_MAX,
        )
        disp_mid1 = _deterministic_int_from_key(
            f"{seed_base}:mid1",
            QUEUE_DISPLAY_MID1_MIN,
            QUEUE_DISPLAY_MID1_MAX,
        )
        disp_mid2 = _deterministic_int_from_key(
            f"{seed_base}:mid2",
            QUEUE_DISPLAY_MID2_MIN,
            QUEUE_DISPLAY_MID2_MAX,
        )
        # Strict descending steps for UI readability.
        disp_mid1 = min(disp_mid1, max(2, disp_start - 1))
        disp_mid2 = min(disp_mid2, max(1, disp_mid1 - 1))
        disp_total = disp_start + _deterministic_int_from_key(
            f"{seed_base}:total_extra",
            QUEUE_DISPLAY_TOTAL_EXTRA_MIN,
            QUEUE_DISPLAY_TOTAL_EXTRA_MAX,
        )

        queue_state = {
            "queue_id": queue_id,
            "performance_id": performance_id,
            "flow_id": flow_id,
            "session_id": session_id,
            "user_email": str(queue_data.user_email or ""),
            "bot_type": str(queue_data.bot_type or ""),
            "state": "waiting",
            "join_epoch_ms": now_ms,
            "ready_epoch_ms": ready_epoch_ms,
            "open_epoch_ms": open_epoch_ms,
            "start_issued_epoch_ms": start_issued_epoch_ms,
            "since_open_ms": since_open_ms,
            "since_open_steps": since_open_steps,
            "since_open_penalty_ms": since_open_penalty_ms,
            "join_delay_ms": join_delay_ms,
            "join_delay_steps": join_delay_steps,
            "join_delay_penalty_ms": join_delay_penalty_ms,
            "display_position_start": int(disp_start),
            "display_position_mid1": int(disp_mid1),
            "display_position_mid2": int(disp_mid2),
            "display_total_queue": int(disp_total),
            "enter_trigger": "booking_start_click",
            "jump_count": 0,
            "poll_intervals_ms": [],
            "last_poll_epoch_ms": 0,
            "entry_ticket": "",
            "cleanup_after_epoch_ms": 0,
        }
        QUEUE_STATE_BY_ID[queue_id] = queue_state
        QUEUE_IDS_BY_PERF.setdefault(performance_id, []).append(queue_id)
        QUEUE_NEXT_READY_SLOT_BY_PERF[performance_id] = ready_epoch_ms + slot_ms

        payload = _queue_status_payload_locked(queue_state, now_ms)
        payload["estimated_wait_ms"] = wait_ms
        return {
            "success": True,
            "rejoined": False,
            "queue": payload,
        }


@app.get("/api/queue/status")
async def queue_status(queue_id: str):
    qid = _sanitize_filename_part(queue_id, fallback="")
    if not qid:
        raise HTTPException(status_code=400, detail="queue_id is required")

    now_ms = _now_ms()
    with QUEUE_LOCK:
        _cleanup_queue_locked(now_ms)
        queue_state = QUEUE_STATE_BY_ID.get(qid)
        if not queue_state:
            raise HTTPException(status_code=404, detail="queue not found")

        last_poll = int(queue_state.get("last_poll_epoch_ms", 0))
        if last_poll > 0:
            interval = max(0, now_ms - last_poll)
            if interval > 0:
                intervals = queue_state.setdefault("poll_intervals_ms", [])
                intervals.append(interval)
                if len(intervals) > 120:
                    del intervals[:-120]
            if 0 < interval < max(120, int(QUEUE_POLL_MIN_MS * 0.5)):
                queue_state["jump_count"] = int(queue_state.get("jump_count", 0)) + 1
        queue_state["last_poll_epoch_ms"] = now_ms

        payload = _queue_status_payload_locked(queue_state, now_ms)
        return {"success": True, "queue": payload}


@app.post("/api/queue/enter")
async def queue_enter(queue_data: QueueEnterData):
    qid = _sanitize_filename_part(queue_data.queue_id, fallback="")
    if not qid:
        raise HTTPException(status_code=400, detail="queue_id is required")

    now_ms = _now_ms()
    with QUEUE_LOCK:
        _cleanup_queue_locked(now_ms)
        queue_state = QUEUE_STATE_BY_ID.get(qid)
        if not queue_state:
            raise HTTPException(status_code=404, detail="queue not found")

        if queue_data.performance_id and str(queue_data.performance_id) != str(queue_state.get("performance_id", "")):
            raise HTTPException(status_code=403, detail="performance mismatch")
        if queue_data.flow_id and str(queue_data.flow_id) != str(queue_state.get("flow_id", "")):
            raise HTTPException(status_code=403, detail="flow mismatch")
        if queue_data.session_id and str(queue_data.session_id) != str(queue_state.get("session_id", "")):
            raise HTTPException(status_code=403, detail="session mismatch")

        _refresh_queue_state_locked(queue_state, now_ms)
        state = str(queue_state.get("state", "waiting"))

        if state == "waiting":
            queue_state["jump_count"] = int(queue_state.get("jump_count", 0)) + 1
            payload = _queue_status_payload_locked(queue_state, now_ms)
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "message": "queue not ready",
                    "queue": payload,
                },
            )

        if state in {"expired", "left"}:
            raise HTTPException(status_code=410, detail="queue expired")

        ticket = str(queue_state.get("entry_ticket", "")).strip()
        if not ticket or not _validate_entry_ticket(ticket):
            ticket = f"qt_{uuid.uuid4().hex}"
            queue_state["entry_ticket"] = ticket
            QUEUE_ENTRY_TICKETS[ticket] = {
                "queue_id": qid,
                "performance_id": str(queue_state.get("performance_id", "")),
                "flow_id": str(queue_state.get("flow_id", "")),
                "session_id": str(queue_state.get("session_id", "")),
                "issued_epoch_ms": now_ms,
                "expires_epoch_ms": now_ms + QUEUE_ENTRY_TTL_MS,
            }

        queue_state["state"] = "entered"
        queue_state["enter_trigger"] = "api_redirect"
        queue_state["cleanup_after_epoch_ms"] = now_ms + 300000

        ticket_state = QUEUE_ENTRY_TICKETS.get(ticket, {})
        payload = _queue_status_payload_locked(queue_state, now_ms)
        response = JSONResponse(
            content={
                "success": True,
                "queue": payload,
                "entry_ticket_expires_epoch_ms": int(ticket_state.get("expires_epoch_ms", 0)),
                "redirect_url": "seat_select.html",
            }
        )
        response.set_cookie(
            key=QUEUE_TICKET_COOKIE,
            value=ticket,
            max_age=max(1, int(QUEUE_ENTRY_TTL_MS / 1000)),
            httponly=True,
            samesite="lax",
            secure=False,
            path="/",
        )
        return response


@app.post("/api/logs")
async def save_log(log_data: LogData):
    """예매 로그 데이터를 저장합니다."""
    try:
        # 메타데이터에서 필요한 정보 추출
        metadata = log_data.metadata
        
        # flow_id 추출 (필수)
        flow_id = metadata.get("flow_id", f"flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # 공연 ID 추출
        performance_id = metadata.get("performance_id", "UNKNOWN")
        
        # 날짜 형식: YYYYMMDD
        date_str = datetime.now().strftime('%Y%m%d')
        
        # 결제 성공 여부 판단
        # is_completed와 completion_status를 우선 사용
        is_completed = metadata.get("is_completed", False)
        completion_status = metadata.get("completion_status", "unknown")
        
        # 결제 성공 여부 결정 로직
        if is_completed and completion_status == "success":
            payment_status = "success"
        elif completion_status == "abandoned":
            payment_status = "abandoned"
        elif completion_status == "failed":
            payment_status = "failed"
        else:
            # 하위 호환성: booking_id 또는 payment_success 필드로 판단
            booking_id = metadata.get("booking_id", "")
            payment_success = metadata.get("payment_success", False)
            
            # booking_id가 있으면 성공으로 간주 (기존 로그 호환)
            if booking_id and booking_id.strip() != "":
                payment_status = "success"
            elif payment_success:
                payment_status = "success"
            else:
                payment_status = "failed"
        
        # bot_type 기반 저장 경로 분기
        # - 기본: model/data/raw/browser/<bot_type>
        # - split 타입(train|validation|test): model/data/raw/<split>/<label>
        raw_bot_type = str(metadata.get("bot_type", "")).strip().replace("\\", "/")
        safe_parts = [
            re.sub(r"[^a-zA-Z0-9_\-]", "", p.strip())
            for p in raw_bot_type.split("/")
            if p and p.strip()
        ]
        safe_parts = [p for p in safe_parts if p]

        if not safe_parts:
            current_logs_dir = os.path.join(BROWSER_LOGS_DIR, "real_human")
        elif len(safe_parts) >= 2 and safe_parts[0] in {"train", "validation", "test"}:
            current_logs_dir = os.path.join(LOGS_DIR, safe_parts[0], safe_parts[1])
        else:
            current_logs_dir = os.path.join(BROWSER_LOGS_DIR, safe_parts[0])

        os.makedirs(current_logs_dir, exist_ok=True)

        # 파일명 형식: [날짜]_[공연ID]_[flow_id]_[결제성공여부].json
        # 예: 20260204_perf001_flow_20260204_abc123_success.json
        
        # 파일명 안전하게 처리 (특수문자 제거)
        def sanitize_filename(s):
            return re.sub(r'[^a-zA-Z0-9_\-]', '', str(s))
            
        safe_perf_id = sanitize_filename(performance_id)
        safe_flow_id = sanitize_filename(flow_id)
        
        filename = f"{date_str}_{safe_perf_id}_{safe_flow_id}_{payment_status}.json"
        filepath = os.path.join(current_logs_dir, filename)
        
        # JSON 파일로 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data.model_dump(), f, ensure_ascii=False, indent=2)
        
        print(f"로그 저장 성공: {filename}")
        
        return {
            "success": True,
            "filename": filename,
            "message": "로그가 성공적으로 저장되었습니다."
        }
    except Exception as e:
        import traceback
        error_msg = f"로그 저장 실패: {str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        with open("server_error.txt", "a", encoding="utf-8") as err_file:
            err_file.write(f"[{datetime.now()}] {error_msg}\n")
        raise HTTPException(status_code=500, detail=f"로그 저장 실패: {str(e)}")

@app.get("/api/logs")
async def get_logs():
    """저장된 모든 브라우저 로그 파일 목록을 반환합니다."""
    try:
        log_files = []
        for root, dirs, files in os.walk(BROWSER_LOGS_DIR):
            for f in files:
                if f.endswith('.json'):
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, BROWSER_LOGS_DIR)
                    rel = rel.replace('\\', '/')
                    log_files.append(rel)
        log_files.sort(reverse=True)
        return {
            "success": True,
            "count": len(log_files),
            "files": log_files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 목록 조회 실패: {str(e)}")

@app.get("/api/logs/{filename:path}")
async def get_log_file(filename: str):
    """특정 로그 파일의 내용을 반환합니다."""
    try:
        base_dir = os.path.abspath(BROWSER_LOGS_DIR)
        filepath = os.path.abspath(os.path.join(BROWSER_LOGS_DIR, filename))
        if not filepath.startswith(base_dir + os.sep) and filepath != base_dir:
            raise HTTPException(status_code=400, detail="잘못된 파일 경로입니다.")
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="로그 파일을 찾을 수 없습니다.")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        return {
            "success": True,
            "filename": filename,
            "data": log_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 파일 조회 실패: {str(e)}")


@app.get("/api/risk/runtime-status")
async def risk_runtime_status():
    runtime = _load_risk_runtime()
    thresholds = _resolve_decision_thresholds()
    threshold_source = "policy_fixed"
    model_fixed_threshold = None

    runtime_thresholds_raw = (runtime or {}).get("thresholds") or {}
    if RISK_DECISION_MODE == "model_threshold_fixed":
        model_fixed_threshold = _resolve_model_fixed_threshold(runtime_thresholds_raw)
        if model_fixed_threshold is not None:
            thresholds = {"allow": model_fixed_threshold, "challenge": model_fixed_threshold}
            threshold_source = "model_threshold_fixed"
        else:
            threshold_source = "model_threshold_fixed_missing_fallback_policy"

    if runtime is None:
        return {
            "success": False,
            "ready": False,
            "params_path": os.path.abspath(RISK_PARAMS_PATH),
            "thresholds_path": os.path.abspath(RISK_THRESHOLDS_PATH),
            "threshold_source": threshold_source,
            "decision_mode": RISK_DECISION_MODE,
            "model_fixed_threshold": model_fixed_threshold,
            "decision_thresholds": thresholds,
            "artifact_path": "",
            "error": RISK_RUNTIME_CACHE.get("error", ""),
        }

    params = runtime.get("params") or {}
    return {
        "success": True,
        "ready": True,
        "model_type": params.get("model_type", "zscore"),
        "params_path": os.path.abspath(RISK_PARAMS_PATH),
        "thresholds_path": os.path.abspath(RISK_THRESHOLDS_PATH),
        "threshold_source": threshold_source,
        "decision_mode": RISK_DECISION_MODE,
        "model_fixed_threshold": model_fixed_threshold,
        "artifact_path": runtime.get("artifact_path", ""),
        "weights": RISK_DEFAULT_WEIGHTS,
        "decision_thresholds": thresholds,
        "block_automation": RISK_BLOCK_AUTOMATION,
        "error": runtime.get("error", ""),
    }

# ============================================
# 공연 오픈 시간 관리 API (새로 추가)
# ============================================

PERFORMANCES_FILE = os.path.join(DATA_DIR, "performances.json")

class PerformanceUpdate(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    category: Optional[str] = None
    venue: Optional[str] = None
    dates: Optional[List[str]] = None
    times: Optional[List[str]] = None
    description: Optional[str] = None
    open_time: Optional[str] = None
    status: Optional[str] = None



class PerformanceCreate(BaseModel):
    id: str
    title: str
    category: str
    venue: str
    dates: List[str]
    times: List[str]
    grades: List[Dict[str, Any]]
    image: str
    description: str
    open_time: str
    status: str = "upcoming"

@app.get("/api/performances")
async def get_performances():
    """모든 공연 목록을 반환합니다."""
    try:
        if not os.path.exists(PERFORMANCES_FILE):
            return {"success": True, "performances": []}
        
        with open(PERFORMANCES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return {
            "success": True,
            "count": len(data.get("performances", [])),
            "performances": data.get("performances", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공연 목록 조회 실패: {str(e)}")

@app.get("/api/performances/{performance_id}")
async def get_performance(performance_id: str):
    """특정 공연의 정보를 반환합니다."""
    try:
        if not os.path.exists(PERFORMANCES_FILE):
            raise HTTPException(status_code=404, detail="공연 데이터를 찾을 수 없습니다.")
        
        with open(PERFORMANCES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        performance = next((p for p in data.get("performances", []) if p["id"] == performance_id), None)
        
        if not performance:
            raise HTTPException(status_code=404, detail="해당 공연을 찾을 수 없습니다.")
        
        performance_out = dict(performance)
        if PERFORMANCE_DETAIL_OPEN_OFFSET_SEC >= 0:
            virtual_open_dt = datetime.utcnow() + timedelta(seconds=PERFORMANCE_DETAIL_OPEN_OFFSET_SEC)
            performance_out["open_time"] = virtual_open_dt.replace(microsecond=0).isoformat() + "Z"
            performance_out["status"] = "upcoming"
            performance_out["open_time_source"] = "server_relative"

        return {
            "success": True,
            "performance": performance_out
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공연 조회 실패: {str(e)}")

@app.put("/api/admin/performances/{performance_id}")
async def update_performance(performance_id: str, update_data: PerformanceUpdate):
    """공연 정보를 업데이트합니다. (ID 변경 포함)"""
    try:
        if not os.path.exists(PERFORMANCES_FILE):
            raise HTTPException(status_code=404, detail="공연 데이터를 찾을 수 없습니다.")
        
        with open(PERFORMANCES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 대상 공연 찾기
        target_idx = -1
        for idx, p in enumerate(data.get("performances", [])):
            if p["id"] == performance_id:
                target_idx = idx
                break
        
        if target_idx == -1:
            raise HTTPException(status_code=404, detail="해당 공연을 찾을 수 없습니다.")
        
        performance = data["performances"][target_idx]
        
        # ID는 수정 불가 (코드 제거)

        # 나머지 필드 업데이트

        # 나머지 필드 업데이트
        if update_data.title is not None:
            performance["title"] = update_data.title
        if update_data.category is not None:
            performance["category"] = update_data.category
        if update_data.venue is not None:
            performance["venue"] = update_data.venue
        if update_data.dates is not None:
            performance["dates"] = update_data.dates
        if update_data.times is not None:
            performance["times"] = update_data.times
        if update_data.description is not None:
            performance["description"] = update_data.description
        if update_data.open_time is not None:
            performance["open_time"] = update_data.open_time
        if update_data.status is not None:
            performance["status"] = update_data.status
        
        # 파일 저장
        with open(PERFORMANCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return {
            "success": True,
            "message": "공연 정보가 업데이트되었습니다.",
            "performance": performance
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공연 업데이트 실패: {str(e)}")

@app.post("/api/admin/performances")
async def create_performance(performance_data: PerformanceCreate):
    """새 공연을 추가합니다."""
    try:
        if not os.path.exists(PERFORMANCES_FILE):
            data = {"performances": []}
        else:
            with open(PERFORMANCES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # ID 중복 체크
        if any(p["id"] == performance_data.id for p in data.get("performances", [])):
            raise HTTPException(status_code=400, detail="이미 존재하는 공연 ID입니다.")
        
        # 새 공연 추가
        new_performance = performance_data.model_dump()
        data.setdefault("performances", []).append(new_performance)
        
        # 파일 저장
        with open(PERFORMANCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return {
            "success": True,
            "message": "새 공연이 추가되었습니다.",
            "performance": new_performance
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공연 추가 실패: {str(e)}")

@app.delete("/api/admin/performances/{performance_id}")
async def delete_performance(performance_id: str):
    """공연을 삭제합니다."""
    try:
        if not os.path.exists(PERFORMANCES_FILE):
            raise HTTPException(status_code=404, detail="공연 데이터를 찾을 수 없습니다.")
        
        with open(PERFORMANCES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        original_count = len(data.get("performances", []))
        data["performances"] = [p for p in data.get("performances", []) if p["id"] != performance_id]
        
        if len(data["performances"]) == original_count:
            raise HTTPException(status_code=404, detail="해당 공연을 찾을 수 없습니다.")
        
        # 파일 저장
        with open(PERFORMANCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return {
            "success": True,
            "message": "공연이 삭제되었습니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공연 삭제 실패: {str(e)}")


# ============================================
# 예매 제한 관리 API
# ============================================

RESTRICTION_DURATIONS = {
    1: timedelta(days=90),    # 1차: 3개월
    2: timedelta(days=180),   # 2차: 6개월
    3: None                   # 3차: 영구
}

@app.post("/api/admin/restrict-user")
async def restrict_user(data: RestrictUser):
    """사용자에게 예매 제한을 부여합니다."""
    try:
        if data.level not in [1, 2, 3]:
            raise HTTPException(status_code=400, detail="제한 단계는 1, 2, 3 중 하나여야 합니다.")

        with open(RESTRICTED_FILE, 'r', encoding='utf-8') as f:
            restricted_db = json.load(f)

        # 이미 제한된 사용자인지 확인
        existing = next((r for r in restricted_db['restricted_users'] if r['email'] == data.email), None)
        if existing:
            # 단계 업데이트
            existing['level'] = data.level
            existing['reason'] = data.reason
            existing['restricted_at'] = datetime.now().astimezone().isoformat()
            existing['restricted_by'] = data.restricted_by
            duration = RESTRICTION_DURATIONS.get(data.level)
            existing['expires_at'] = (datetime.now().astimezone() + duration).isoformat() if duration else None
        else:
            # 새로 제한
            now = datetime.now().astimezone()
            duration = RESTRICTION_DURATIONS.get(data.level)
            restricted_db['restricted_users'].append({
                "email": data.email,
                "level": data.level,
                "reason": data.reason,
                "restricted_at": now.isoformat(),
                "expires_at": (now + duration).isoformat() if duration else None,
                "restricted_by": data.restricted_by
            })

        with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
            json.dump(restricted_db, f, ensure_ascii=False, indent=2)

        # 이력 기록
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_db = json.load(f)
            history_db['history'].append({
                "action": "restrict",
                "email": data.email,
                "level": data.level,
                "reason": data.reason,
                "by": data.restricted_by,
                "timestamp": datetime.now().astimezone().isoformat()
            })
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history_db, f, ensure_ascii=False, indent=2)
        except:
            pass

        level_names = {1: "1차 (3개월)", 2: "2차 (6개월)", 3: "3차 (영구)"}
        return {
            "success": True,
            "message": f"{data.email}에게 {level_names[data.level]} 예매 제한이 적용되었습니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"제한 적용 실패: {str(e)}")


@app.post("/api/admin/unrestrict-user")
async def unrestrict_user(data: dict):
    """사용자의 예매 제한을 해제합니다."""
    try:
        email = data.get('email')
        reason = data.get('reason', '')
        unrestricted_by = data.get('unrestricted_by', 'admin')
        if not email:
            raise HTTPException(status_code=400, detail="이메일이 필요합니다.")
        if not reason:
            raise HTTPException(status_code=400, detail="해제 사유를 입력해주세요.")

        with open(RESTRICTED_FILE, 'r', encoding='utf-8') as f:
            restricted_db = json.load(f)

        original_len = len(restricted_db['restricted_users'])
        restricted_db['restricted_users'] = [r for r in restricted_db['restricted_users'] if r['email'] != email]

        if len(restricted_db['restricted_users']) == original_len:
            raise HTTPException(status_code=404, detail="해당 사용자는 제한 목록에 없습니다.")

        with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
            json.dump(restricted_db, f, ensure_ascii=False, indent=2)

        # 해제 이력 기록
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_db = json.load(f)
            history_db['history'].append({
                "action": "unrestrict",
                "email": email,
                "reason": reason,
                "by": unrestricted_by,
                "timestamp": datetime.now().astimezone().isoformat()
            })
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history_db, f, ensure_ascii=False, indent=2)
        except:
            pass

        return {"success": True, "message": f"{email}의 예매 제한이 해제되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"제한 해제 실패: {str(e)}")


@app.get("/api/admin/restriction-history")
async def get_restriction_history():
    """제한/해제 이력을 반환합니다."""
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history_db = json.load(f)

        # 사용자 이름 매핑
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users_db = json.load(f)
        name_map = {u['email']: u.get('name', '-') for u in users_db.get('users', [])}

        # 현재 제한 상태 매핑
        with open(RESTRICTED_FILE, 'r', encoding='utf-8') as f:
            restricted_db = json.load(f)
        restricted_emails = {r['email']: r for r in restricted_db.get('restricted_users', [])}

        # 이메일별 그룹핑
        grouped = {}
        for h in history_db.get('history', []):
            email = h.get('email', '')
            if email not in grouped:
                grouped[email] = {
                    "email": email,
                    "name": name_map.get(email, '-'),
                    "currently_restricted": email in restricted_emails,
                    "current_level": restricted_emails.get(email, {}).get('level', None),
                    "history": []
                }
            grouped[email]['history'].append(h)

        # 최신순 정렬
        result = sorted(grouped.values(), key=lambda x: x['history'][-1]['timestamp'] if x['history'] else '', reverse=True)
        return {"users": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이력 조회 실패: {str(e)}")


@app.get("/api/admin/cancelled-bookings")
async def get_cancelled_bookings():
    """취소된 예매 목록을 반환합니다."""
    try:
        # 사용자 이름 매핑
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users_db = json.load(f)
        name_map = {u['email']: u.get('name', '-') for u in users_db.get('users', [])}

        cancelled = []
        for filename in os.listdir(LOGS_DIR):
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(LOGS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    log = json.load(f)
                meta = log.get('metadata', {})
                if meta.get('cancelled'):
                    cancelled.append({
                        "filename": filename,
                        "email": meta.get('user_email', '-'),
                        "name": name_map.get(meta.get('user_email', ''), '-'),
                        "booking_id": meta.get('booking_id', '-'),
                        "performance_title": meta.get('performance_title', '-'),
                        "selected_date": meta.get('selected_date', '-'),
                        "selected_time": meta.get('selected_time', '-'),
                        "cancelled_by": meta.get('cancelled_by', '-'),
                        "cancel_reason": meta.get('cancel_reason', '-'),
                        "cancelled_at": meta.get('cancelled_at', '')
                    })
            except:
                continue

        cancelled.sort(key=lambda x: x['cancelled_at'], reverse=True)
        return {"bookings": cancelled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"취소 내역 조회 실패: {str(e)}")


@app.get("/api/admin/restricted-users")
async def get_restricted_users():
    """제한된 사용자 목록을 반환합니다."""
    try:
        with open(RESTRICTED_FILE, 'r', encoding='utf-8') as f:
            restricted_db = json.load(f)

        # 만료된 제한 자동 제거
        now = datetime.now().astimezone()
        active = []
        for r in restricted_db['restricted_users']:
            if r.get('expires_at'):
                if datetime.fromisoformat(r['expires_at']) > now:
                    active.append(r)
            else:
                active.append(r)  # 영구 제한

        # 변경사항 저장
        if len(active) != len(restricted_db['restricted_users']):
            restricted_db['restricted_users'] = active
            with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
                json.dump(restricted_db, f, ensure_ascii=False, indent=2)

        return {"restricted_users": active}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"제한 목록 조회 실패: {str(e)}")


@app.get("/api/admin/check-restriction/{email}")
async def check_restriction(email: str):
    """특정 사용자의 제한 상태를 확인합니다."""
    try:
        with open(RESTRICTED_FILE, 'r', encoding='utf-8') as f:
            restricted_db = json.load(f)

        restricted_user = next((r for r in restricted_db['restricted_users'] if r['email'] == email), None)

        if not restricted_user:
            return {"restricted": False}

        # 만료 체크
        if restricted_user.get('expires_at'):
            if datetime.now().astimezone() > datetime.fromisoformat(restricted_user['expires_at']):
                # 만료됨 - 자동 해제
                restricted_db['restricted_users'] = [r for r in restricted_db['restricted_users'] if r['email'] != email]
                with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
                    json.dump(restricted_db, f, ensure_ascii=False, indent=2)
                return {"restricted": False}

        return {
            "restricted": True,
            "level": restricted_user['level'],
            "reason": restricted_user['reason'],
            "restricted_at": restricted_user['restricted_at'],
            "expires_at": restricted_user.get('expires_at')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"제한 확인 실패: {str(e)}")


@app.post("/api/admin/cancel-booking")
async def cancel_booking(data: CancelBooking):
    """예매를 취소합니다 (로그 파일의 status를 cancelled로 변경)."""
    try:
        filepath = os.path.join(LOGS_DIR, data.filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="로그 파일을 찾을 수 없습니다.")

        with open(filepath, 'r', encoding='utf-8') as f:
            log_data = json.load(f)

        # metadata에 취소 정보 추가
        log_data['metadata']['cancelled'] = True
        log_data['metadata']['cancelled_at'] = datetime.now().astimezone().isoformat()
        log_data['metadata']['cancel_reason'] = data.reason
        log_data['metadata']['cancelled_by'] = data.cancelled_by

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": f"예매가 취소되었습니다: {data.filename}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예매 취소 실패: {str(e)}")


# ===== 마이페이지 API =====

@app.get("/api/mypage/bookings/{email}")
async def get_user_bookings(email: str):
    """사용자의 예매 내역을 조회합니다."""
    try:
        bookings = []
        # 브라우저 로그 디렉토리의 모든 하위 디렉토리를 탐색
        for root, dirs, files in os.walk(BROWSER_LOGS_DIR):
            for filename in files:
                if not filename.endswith('.json'):
                    continue
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        log = json.load(f)
                    meta = log.get('metadata', {})
                    # 해당 이메일의 완료된 예매만
                    if meta.get('user_email') != email:
                        continue
                    # is_completed가 True이거나 completion_status가 success인 경우
                    if not meta.get('is_completed') and meta.get('completion_status') != 'success':
                        continue

                    stages = log.get('stages', {})
                    discount = stages.get('discount', {})
                    order_info = stages.get('order_info', {})
                    payment = stages.get('payment', {})

                    booking = {
                        "filename": os.path.relpath(filepath, BROWSER_LOGS_DIR).replace('\\', '/'),
                        "performance_title": meta.get('performance_title', '-'),
                        "selected_date": meta.get('selected_date', '-'),
                        "selected_time": meta.get('selected_time', '-'),
                        "booking_id": meta.get('booking_id', '-'),
                        "cancelled": meta.get('cancelled', False),
                        "cancel_reason": meta.get('cancel_reason', ''),
                        "final_seats": meta.get('final_seats', []),
                        "seat_grades": meta.get('seat_grades', []),
                        "payment_type": payment.get('payment_type', '-'),
                        "selected_discount": discount.get('selected_discount', 'disabled'),
                        "delivery_type": order_info.get('delivery_type', 'pickup'),
                        "delivery_address": meta.get('delivery_address', ''),
                        "delivery_status": meta.get('delivery_status', '준비중'),
                        "created_at": meta.get('created_at', '')
                    }
                    bookings.append(booking)
                except:
                    continue

        # 최신순 정렬
        bookings.sort(key=lambda x: x['created_at'], reverse=True)
        return {"bookings": bookings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예매 내역 조회 실패: {str(e)}")


class UpdateDelivery(BaseModel):
    filename: str
    delivery_address: str


class SeatF2MacroTrigger(BaseModel):
    grade: Optional[str] = None


@app.post("/api/mypage/update-delivery")
async def update_delivery(data: UpdateDelivery):
    """배송지 주소를 수정합니다."""
    try:
        filepath = os.path.join(LOGS_DIR, data.filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="예매 정보를 찾을 수 없습니다.")

        with open(filepath, 'r', encoding='utf-8') as f:
            log_data = json.load(f)

        log_data['metadata']['delivery_address'] = data.delivery_address

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": "배송지가 수정되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배송지 수정 실패: {str(e)}")


@app.post("/api/macro/f2")
async def trigger_seat_f2_macro(payload: Optional[SeatF2MacroTrigger] = None):
    """좌석 선택 페이지에서 F2 매크로(자동 좌석 탐색)를 실행한다."""
    grade = SEAT_F2_MACRO_GRADE
    if payload and payload.grade is not None:
        grade = str(payload.grade).strip() or grade
    return _start_seat_f2_macro(grade)


@app.get("/api/macro/f2/status")
async def get_seat_f2_macro_status():
    """좌석 F2 매크로 실행 상태를 반환한다."""
    return _seat_f2_macro_state_snapshot()


# ---- Block Report API ----
@app.get("/api/reports")
async def list_reports():
    """block_report 디렉토리의 LLM 리포트 목록 반환 (최신순)"""
    try:
        entries = []
        index_path = BLOCK_REPORT_INDEX_JSONL
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
        entries.sort(key=lambda x: x.get("created_at_iso", ""), reverse=True)
        return {"reports": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/{filename}")
async def get_report(filename: str):
    """특정 LLM 리포트 JSON 반환"""
    import re
    # 경로 탐색 방지: 영숫자·언더스코어·하이픈·점 만 허용
    base = filename.replace(".json", "")
    if not re.fullmatch(r"[\w\-]+", base):
        raise HTTPException(status_code=400, detail="invalid filename")
    path = os.path.join(BLOCK_REPORT_DIR, base + ".json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="report not found")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 정적 파일 서빙 (HTML, CSS, JS)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
