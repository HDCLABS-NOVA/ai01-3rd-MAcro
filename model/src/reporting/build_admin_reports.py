import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    try:
        load_dotenv(dotenv_path=ROOT_DIR / ".env")
    except Exception:
        pass

from model.src.features.feature_pipeline import build_server_index, extract_browser_features, load_json
from model.src.models.deep_svdd import load_runtime_from_bundle, score_with_runtime, torch_ready
from model.src.rules.rule_base import evaluate_rules
from model.src.serving.model_explain import top_model_contributors

LLM_REPORT_ENABLED = os.getenv("LLM_REPORT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
LLM_REPORT_MODEL = os.getenv("LLM_REPORT_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
LLM_REPORT_TIMEOUT_SEC = int(os.getenv("LLM_REPORT_TIMEOUT_SEC", "20"))
LLM_REPORT_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def sanitize_filename_part(value: Any, fallback: str = "unknown") -> str:
    cleaned = "".join(ch for ch in str(value or "") if ch.isalnum() or ch in {"_", "-"})
    return cleaned or fallback


def resolve_openai_api_key() -> str:
    return str(os.getenv("OPENAI_API_KEY") or os.getenv("OPENAIAPIKEY") or "").strip()


def mask_email(email: str) -> str:
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


def build_ui_fields_fallback(report_seed: Dict[str, Any]) -> Dict[str, Any]:
    risk_summary = report_seed.get("risk_summary", {}) if isinstance(report_seed, dict) else {}
    ui_seed = report_seed.get("ui_metric_seed", {}) if isinstance(report_seed, dict) else {}
    reasons = report_seed.get("rule_evidence", []) if isinstance(report_seed, dict) else []
    if not isinstance(reasons, list):
        reasons = []
    reasons = [str(r).strip() for r in reasons if str(r).strip()][:5]

    risk_score = clamp01(safe_float((risk_summary or {}).get("total_score"), 0.0))
    bot_score_100 = round(risk_score * 100.0, 1)
    level = "low"
    if bot_score_100 >= 70:
        level = "high"
    elif bot_score_100 >= 30:
        level = "medium"
    status_title = "정상 사용자"
    if level == "medium":
        status_title = "주의 사용자"
    elif level == "high":
        status_title = "매크로 의심 사용자"

    speed_variability_pct = max(0.0, safe_float((ui_seed or {}).get("speed_variability_pct"), 0.0))
    path_curvature_rad = max(0.0, safe_float((ui_seed or {}).get("path_curvature_rad"), 0.0))
    hover_sections_count = max(0, int(safe_float((ui_seed or {}).get("hover_sections_count"), 0.0)))

    narrative = "의심 요인: " + ", ".join(reasons[:3]) + "." if reasons else "의심 요인이 명확하게 관찰되지 않았습니다."
    return {
        "status_title_ko": status_title,
        "bot_score": {"value": bot_score_100, "max": 100},
        "speed_variability": {"value": round(speed_variability_pct, 2), "unit": "%", "judgement_ko": "정상"},
        "path_curvature": {"value": round(path_curvature_rad, 3), "unit": "rad", "judgement_ko": "자연스러움"},
        "hover_sections": {"value": hover_sections_count, "unit": "개", "judgement_ko": "발견"},
        "suspicion_reasons": reasons,
        "suspicion_narrative_ko": narrative,
    }


def build_markdown_report_fallback(
    *,
    report_seed: Dict[str, Any],
    ui_fields: Dict[str, Any],
    summary_ko: str,
    suspicion_level: str,
) -> str:
    ident = report_seed.get("report_identity", {}) if isinstance(report_seed, dict) else {}
    report_id = str((ident or {}).get("report_id", "")).strip() or "UNKNOWN_REPORT"
    target_masked = str((ident or {}).get("target_masked_user", "")).strip() or "unknown"
    score_100 = safe_float((ui_fields.get("bot_score", {}) or {}).get("value"))
    level_map = {"low": "낮음", "medium": "중간", "high": "높음"}
    level_ko = level_map.get(str(suspicion_level).lower(), "중간")
    status_title = str(ui_fields.get("status_title_ko", "")).strip() or "판정 결과"
    reasons = ui_fields.get("suspicion_reasons", [])
    if not isinstance(reasons, list):
        reasons = []
    reasons = [str(x).strip() for x in reasons if str(x).strip()][:5]
    narrative = str(ui_fields.get("suspicion_narrative_ko", "")).strip() or "추가 의심 요인은 관찰되지 않았습니다."
    speed = ui_fields.get("speed_variability", {}) or {}
    curve = ui_fields.get("path_curvature", {}) or {}
    hover = ui_fields.get("hover_sections", {}) or {}
    lines = [
        "[ Header Area: 정량적 지표 ]",
        f"ID: {report_id} / 대상: {target_masked}",
        f"스코어: [ {round(max(0.0, min(100.0, score_100)), 1)} / 100 ] / 판정: {status_title} (위험도 {level_ko})",
        "",
        "[ Analysis Summary: 모델 분석 요약 ]",
        f"- 속도 변동성: {round(safe_float(speed.get('value')), 2)}{str(speed.get('unit', '%'))} ({str(speed.get('judgement_ko', '정상'))})",
        f"- 경로 곡선성: {round(safe_float(curve.get('value')), 3)}{str(curve.get('unit', 'rad'))} ({str(curve.get('judgement_ko', '자연스러움'))})",
        f"- 호버 구간: {int(safe_float(hover.get('value')))}{str(hover.get('unit', '개'))} ({str(hover.get('judgement_ko', '발견'))})",
    ]
    if reasons:
        lines.append("- 주요 의심 요인:")
        lines.extend([f"  - {r}" for r in reasons])
    lines.extend(
        [
            "",
            "[ AI Insights: 생성 요약 ]",
            summary_ko.strip() or "근거 기반 분석 결과, 자동화 의심 정황이 확인되었습니다.",
            narrative,
        ]
    )
    return "\n".join(lines).strip()


def generate_llm_report_payload(*, report_seed: Dict[str, Any]) -> Dict[str, Any]:
    fallback_ui_fields = build_ui_fields_fallback(report_seed)
    fallback_markdown = build_markdown_report_fallback(
        report_seed=report_seed,
        ui_fields=fallback_ui_fields,
        summary_ko="",
        suspicion_level="medium",
    )
    if not LLM_REPORT_ENABLED:
        return {
            "enabled": False,
            "used": False,
            "reason": "llm_report_disabled",
            "ui_fields": fallback_ui_fields,
            "markdown_report": fallback_markdown,
        }
    api_key = resolve_openai_api_key()
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
        "당신은 티켓팅 매크로 탐지 리포트 작성 보조 시스템입니다. "
        "입력 데이터를 근거로 관리자용 한국어 요약을 JSON으로만 출력하세요. "
        "추측을 금지하고 근거 기반으로 작성하세요."
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
        "- markdown_report는 관리자 화면에서 바로 보여줄 수 있도록 Markdown 형태(섹션/불릿 포함)로 작성하세요.\n"
        "- suspicion_narrative_ko는 2~4문장 줄글로 작성하세요.\n"
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
        choices = parsed.get("choices", []) if isinstance(parsed, dict) else []
        message = (choices[0].get("message", {}) or {}) if choices and isinstance(choices[0], dict) else {}
        content = str(message.get("content", "")).strip()
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
        confidence = clamp01(safe_float(result.get("confidence"), 0.0))
        ui_fields_raw = result.get("ui_fields", {})
        if not isinstance(ui_fields_raw, dict):
            ui_fields_raw = {}
        ui_fields = {
            "status_title_ko": str(ui_fields_raw.get("status_title_ko", fallback_ui_fields.get("status_title_ko", ""))).strip() or str(fallback_ui_fields.get("status_title_ko", "")),
            "bot_score": {
                "value": round(max(0.0, min(100.0, safe_float((ui_fields_raw.get("bot_score", {}) or {}).get("value"), safe_float((fallback_ui_fields.get("bot_score", {}) or {}).get("value"), 0.0)))), 1),
                "max": 100,
            },
            "speed_variability": {
                "value": round(max(0.0, safe_float((ui_fields_raw.get("speed_variability", {}) or {}).get("value"), safe_float((fallback_ui_fields.get("speed_variability", {}) or {}).get("value"), 0.0))), 2),
                "unit": "%",
                "judgement_ko": str(
                    (ui_fields_raw.get("speed_variability", {}) or {}).get(
                        "judgement_ko",
                        (fallback_ui_fields.get("speed_variability", {}) or {}).get("judgement_ko", "정상"),
                    )
                ).strip(),
            },
            "path_curvature": {
                "value": round(max(0.0, safe_float((ui_fields_raw.get("path_curvature", {}) or {}).get("value"), safe_float((fallback_ui_fields.get("path_curvature", {}) or {}).get("value"), 0.0))), 3),
                "unit": "rad",
                "judgement_ko": str(
                    (ui_fields_raw.get("path_curvature", {}) or {}).get(
                        "judgement_ko",
                        (fallback_ui_fields.get("path_curvature", {}) or {}).get("judgement_ko", "자연스러움"),
                    )
                ).strip(),
            },
            "hover_sections": {
                "value": max(0, int(safe_float((ui_fields_raw.get("hover_sections", {}) or {}).get("value"), safe_float((fallback_ui_fields.get("hover_sections", {}) or {}).get("value"), 0.0)))),
                "unit": "개",
                "judgement_ko": str(
                    (ui_fields_raw.get("hover_sections", {}) or {}).get(
                        "judgement_ko",
                        (fallback_ui_fields.get("hover_sections", {}) or {}).get("judgement_ko", "발견"),
                    )
                ).strip(),
            },
            "suspicion_reasons": [str(x).strip() for x in (ui_fields_raw.get("suspicion_reasons", reasons) or []) if str(x).strip()][:5],
            "suspicion_narrative_ko": str(ui_fields_raw.get("suspicion_narrative_ko", fallback_ui_fields.get("suspicion_narrative_ko", ""))).strip(),
        }
        summary_ko = str(result.get("summary_ko", "")).strip()
        markdown_report = str(result.get("markdown_report", "")).strip()
        if not markdown_report:
            markdown_report = build_markdown_report_fallback(
                report_seed=report_seed,
                ui_fields=ui_fields,
                summary_ko=summary_ko,
                suspicion_level=level,
            )

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


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def resolve_artifact_path(artifact_path: str, params_path: str) -> Optional[Path]:
    if not artifact_path:
        return None
    p = Path(artifact_path)
    if p.is_absolute() and p.exists():
        return p

    rel_from_params = (Path(params_path).resolve().parent / p).resolve()
    if rel_from_params.exists():
        return rel_from_params

    rel_from_cwd = (Path.cwd() / p).resolve()
    if rel_from_cwd.exists():
        return rel_from_cwd
    return None


def resolve_thresholds(
    thresholds: Dict[str, Any],
    allow_override: Optional[str],
    challenge_override: Optional[str],
) -> Dict[str, float]:
    allow = safe_float(thresholds.get("risk_allow"), 0.30)
    challenge = safe_float(thresholds.get("risk_challenge"), 0.70)

    if allow_override is not None and allow_override != "":
        allow = safe_float(allow_override, allow)
    if challenge_override is not None and challenge_override != "":
        challenge = safe_float(challenge_override, challenge)

    allow = clamp01(allow)
    challenge = clamp01(challenge)
    if challenge <= allow:
        challenge = min(1.0, allow + 0.05)
    return {"allow": allow, "challenge": challenge}


def decision_from_risk(risk: float, thresholds: Dict[str, float]) -> str:
    if risk < thresholds["allow"]:
        return "allow"
    if risk < thresholds["challenge"]:
        return "challenge"
    return "block"


def model_score_from_features(
    features: Dict[str, float],
    params: Dict[str, Any],
    model_artifact: Optional[Dict[str, Any]],
) -> float:
    order = params["feature_order"]
    raw_min = float(params["raw_min"])
    raw_max = float(params["raw_max"])
    model_type = params.get("model_type", "zscore")
    vec = np.array([float(features.get(name, 0.0) or 0.0) for name in order], dtype=float)

    if model_type == "zscore" or ("mean" in params and "std" in params and not model_artifact):
        mean = np.array(params["mean"], dtype=float)
        std = np.array(params["std"], dtype=float)
        std[std == 0] = 1.0
        raw = float(np.abs((vec - mean) / std).mean())
    elif model_type in ("isolation_forest", "oneclass_svm"):
        if not model_artifact:
            return 0.0
        model = model_artifact.get("model")
        scaler = model_artifact.get("scaler")
        if model is None:
            return 0.0
        x = vec.reshape(1, -1)
        if scaler is not None:
            x = scaler.transform(x)
        raw = -float(model.decision_function(x)[0])
    elif model_type == "deep_svdd":
        if not model_artifact or not torch_ready():
            return 0.0
        bundle = model_artifact.get("model")
        scaler = model_artifact.get("scaler")
        if not isinstance(bundle, dict):
            return 0.0
        x = vec.reshape(1, -1)
        if scaler is not None:
            x = scaler.transform(x)
        runtime = model_artifact.get("_deep_svdd_runtime")
        if runtime is None:
            try:
                runtime = load_runtime_from_bundle(bundle)
            except Exception:
                return 0.0
            model_artifact["_deep_svdd_runtime"] = runtime
        net, center = runtime
        raw = float(score_with_runtime(net, center, np.array(x, dtype=np.float32))[0])
    else:
        return 0.0

    if raw_max - raw_min <= 1e-12:
        return 0.0
    return clamp01((raw - raw_min) / (raw_max - raw_min))


def find_server_for_flow(flow_id: str, server_index: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not flow_id:
        return None
    return server_index.get(flow_id)


def behavior_evidence(features: Dict[str, float]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []

    def add_if(cond: bool, code: str, desc: str, metric: str, value: float, severity: str) -> None:
        if cond:
            flags.append(
                {
                    "code": code,
                    "description": desc,
                    "metric": metric,
                    "value": round(value, 6),
                    "severity": severity,
                }
            )

    perf_click_interval = safe_float(features.get("perf_avg_click_interval"))
    seat_click_interval = safe_float(features.get("seat_avg_click_interval"))
    perf_straightness = safe_float(features.get("perf_avg_straightness"))
    seat_straightness = safe_float(features.get("seat_avg_straightness"))
    perf_click_to_hover = safe_float(features.get("perf_click_to_hover_ratio"))
    seat_click_to_hover = safe_float(features.get("seat_click_to_hover_ratio"))
    perf_click_std = safe_float(features.get("perf_std_click_interval"))
    seat_click_std = safe_float(features.get("seat_std_click_interval"))
    seat_duration = safe_float(features.get("seat_duration_ms"))

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
        perf_straightness >= 0.97,
        "perf_high_straightness",
        "공연 단계 마우스 궤적이 지나치게 직선적입니다.",
        "perf_avg_straightness",
        perf_straightness,
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
        perf_click_to_hover >= 5.0,
        "perf_low_hover",
        "공연 단계 hover 대비 클릭 비율이 비정상적으로 높습니다.",
        "perf_click_to_hover_ratio",
        perf_click_to_hover,
        "medium",
    )
    add_if(
        seat_click_to_hover >= 5.0,
        "seat_low_hover",
        "좌석 단계 hover 대비 클릭 비율이 비정상적으로 높습니다.",
        "seat_click_to_hover_ratio",
        seat_click_to_hover,
        "high",
    )
    add_if(
        perf_click_std >= 0 and perf_click_std < 35 and safe_float(features.get("perf_click_count")) >= 4,
        "perf_uniform_click_rhythm",
        "공연 단계 클릭 리듬이 지나치게 일정합니다.",
        "perf_std_click_interval",
        perf_click_std,
        "medium",
    )
    add_if(
        seat_click_std >= 0 and seat_click_std < 35 and safe_float(features.get("seat_click_count")) >= 4,
        "seat_uniform_click_rhythm",
        "좌석 단계 클릭 리듬이 지나치게 일정합니다.",
        "seat_std_click_interval",
        seat_click_std,
        "high",
    )
    add_if(
        seat_duration > 0 and seat_duration < 900,
        "seat_short_duration",
        "좌석 선택 소요 시간이 매우 짧습니다.",
        "seat_duration_ms",
        seat_duration,
        "medium",
    )

    return flags[:6]


def calc_confidence(
    decision: str,
    risk_score: float,
    hard_action: str,
    hard_rules: List[str],
    soft_rules: List[str],
    behavior_flags: List[Dict[str, Any]],
    model_ready: bool,
) -> float:
    confidence = 0.20
    confidence += 0.25 if decision in {"challenge", "block"} else 0.0
    confidence += 0.15 if risk_score >= 0.70 else (0.08 if risk_score >= 0.50 else 0.0)
    confidence += 0.15 if hard_action != "none" else 0.0
    confidence += min(0.15, 0.03 * len(soft_rules))
    confidence += min(0.10, 0.03 * len(behavior_flags))
    if not model_ready:
        confidence -= 0.10
    if hard_action == "block" and len(hard_rules) > 0:
        confidence += 0.10
    return clamp01(confidence)


def account_key(browser_log: Dict[str, Any], server_log: Optional[Dict[str, Any]]) -> str:
    identity = (server_log or {}).get("identity", {}) or {}
    user_hash = str(identity.get("user_id_hash", "")).strip()
    if user_hash:
        return user_hash

    metadata = browser_log.get("metadata", {}) or {}
    email = str(metadata.get("user_email", "")).strip()
    if email:
        return sha256_text(email)

    session_id = str(metadata.get("session_id", "")).strip()
    if session_id:
        return f"session:{session_id}"

    flow_id = str(metadata.get("flow_id", "")).strip()
    if flow_id:
        return f"flow:{flow_id}"
    return "unknown"


@dataclass
class SessionReport:
    account_key: str
    user_id: str
    booking_id: str
    flow_id: str
    browser_log_path: str
    server_log_found: bool
    decision: str
    recommendation: str
    confidence: float
    risk_score: float
    rule_score: float
    model_score: float
    account_age_days: int
    is_verified: bool
    past_successful_orders: int
    device_change_count: int
    rule_evidence: Dict[str, Any]
    model_evidence: Dict[str, Any]
    behavior_evidence: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_key": self.account_key,
            "user_id": self.user_id,
            "booking_id": self.booking_id,
            "flow_id": self.flow_id,
            "browser_log_path": self.browser_log_path,
            "server_log_found": self.server_log_found,
            "decision": self.decision,
            "recommendation": self.recommendation,
            "confidence": round(self.confidence, 6),
            "risk_score": round(self.risk_score, 6),
            "rule_score": round(self.rule_score, 6),
            "model_score": round(self.model_score, 6),
            "account_age_days": int(self.account_age_days),
            "is_verified": bool(self.is_verified),
            "past_successful_orders": int(self.past_successful_orders),
            "device_change_count": int(self.device_change_count),
            "rule_evidence": self.rule_evidence,
            "model_evidence": self.model_evidence,
            "behavior_evidence": self.behavior_evidence,
        }


def _risk_grade(score: float) -> str:
    if score >= 0.70:
        return "High"
    if score >= 0.30:
        return "Medium"
    return "Low"


def save_posthoc_block_reports(session_reports: List[SessionReport], out_block_dir: Path) -> Dict[str, int]:
    out_block_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    posthoc_dir = out_block_dir / "posthoc" / date_str
    posthoc_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_block_dir / "index.jsonl"

    candidates = [
        s
        for s in session_reports
        if s.decision == "block" or bool((s.rule_evidence or {}).get("block_recommended", False))
    ]

    written = 0
    llm_written = 0
    for s in candidates:
        report_key = s.flow_id or hashlib.sha256(s.browser_log_path.encode("utf-8")).hexdigest()[:12]
        safe_booking_id = sanitize_filename_part(s.booking_id, fallback="nobooking")
        report_id = f"{safe_booking_id}_REPORT"
        report_path = posthoc_dir / f"{date_str}_{safe_booking_id}_posthoc_{report_key}.json"
        llm_report_path = posthoc_dir / f"{date_str}_{safe_booking_id}_posthoc_{report_key}_llm.json"

        rule_entries = list((s.rule_evidence or {}).get("hard_rules_triggered", []) or []) + list(
            (s.rule_evidence or {}).get("soft_rules_triggered", []) or []
        )
        top_features: List[str] = []
        model_top = ((s.model_evidence or {}).get("top_features", []) or [])
        for m in model_top:
            text = str(m).strip()
            if text and text not in top_features:
                top_features.append(text)
        for b in s.behavior_evidence:
            desc = str(b.get("description", "")).strip()
            if desc and desc not in top_features:
                top_features.append(desc)
        model_top_contributions = list((s.model_evidence or {}).get("top_feature_contributions", []) or [])

        speed_variability_pct = 0.0
        path_curvature_rad = 0.0
        for b in s.behavior_evidence:
            metric = str(b.get("metric", "")).strip()
            value = safe_float(b.get("value"), 0.0)
            if speed_variability_pct <= 0.0 and metric in {"seat_std_mouse_speed", "perf_std_mouse_speed"}:
                speed_variability_pct = max(0.0, value)
            if path_curvature_rad <= 0.0 and metric in {"seat_avg_straightness", "perf_avg_straightness"}:
                straightness = max(0.0, min(1.0, value))
                path_curvature_rad = (1.0 - straightness) * float(np.pi)

        risk_grade = _risk_grade(s.risk_score)
        recommendation = (
            "block_review" if bool((s.rule_evidence or {}).get("block_recommended", False)) else "block"
        )
        target_masked_user = mask_email(s.user_id)
        created_at = datetime.utcnow().isoformat() + "Z"
        llm_seed = {
            "report_identity": {
                "report_id": report_id,
                "booking_id": s.booking_id,
                "target_masked_user": target_masked_user,
            },
            "decision": s.decision,
            "risk_summary": {
                "total_score": round(s.risk_score, 6),
                "grade": risk_grade,
            },
            "rule_evidence": rule_entries,
            "behavior_evidence": s.behavior_evidence,
            "model_evidence": {
                "anomaly_score": round(s.model_score, 6),
                "top_features": top_features[:3],
                "top_feature_contributions": model_top_contributions,
                "model_ready": bool((s.model_evidence or {}).get("model_ready", True)),
                "model_skipped": False,
            },
            "request_context": {
                "request_id": "",
                "flow_id": s.flow_id,
                "session_id": "",
                "endpoint": "/posthoc",
                "method": "POSTHOC",
                "bot_type": "",
                "browser_log_path": s.browser_log_path,
                "server_log_found": bool(s.server_log_found),
            },
            "ui_metric_seed": {
                "bot_score_100": round(max(0.0, min(1.0, s.risk_score)) * 100.0, 1),
                "speed_variability_pct": round(speed_variability_pct, 2),
                "path_curvature_rad": round(path_curvature_rad, 3),
                "hover_sections_count": 0,
            },
        }
        llm_analysis = generate_llm_report_payload(report_seed=llm_seed)
        llm_ui_fields = llm_analysis.get("ui_fields", build_ui_fields_fallback(llm_seed))

        llm_report_payload = {
            "report_type": "posthoc_block_llm_v1",
            "created_at_iso": created_at,
            "report_id": report_id,
            "booking_id": s.booking_id,
            "flow_id": s.flow_id,
            "target_masked_user": target_masked_user,
            "decision": s.decision,
            "llm_analysis": llm_analysis,
            "ui_fields": llm_ui_fields,
            "markdown_report": str(llm_analysis.get("markdown_report", "")).strip(),
        }
        llm_report_error = ""
        try:
            llm_report_path.write_text(json.dumps(llm_report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            llm_written += 1
        except Exception as e:
            llm_report_error = str(e)

        report = {
            "report_type": "posthoc_block_v1",
            "created_at_iso": created_at,
            "report_id": report_id,
            "user_id": s.user_id,
            "target_masked_user": target_masked_user,
            "booking_id": s.booking_id,
            "flow_id": s.flow_id,
            "decision": s.decision,
            "recommendation": recommendation,
            "confidence": round(s.confidence, 6),
            "risk_summary": {
                "total_score": round(s.risk_score, 6),
                "grade": risk_grade,
            },
            "evidence_logs": {
                "rule": rule_entries,
                "model": {
                    "anomaly_score": round(s.model_score, 6),
                    "top_features": top_features[:3],
                    "top_feature_contributions": model_top_contributions,
                },
                "behavior": {
                    "avg_click_interval": "",
                    "device_change_count": int(s.device_change_count),
                },
                "trust": {
                    "account_age_days": int(s.account_age_days),
                    "is_verified": bool(s.is_verified),
                    "past_successful_orders": int(s.past_successful_orders),
                },
            },
            "request_context": {
                "browser_log_path": s.browser_log_path,
                "server_log_found": bool(s.server_log_found),
            },
            "actions": {
                "realtime_enforced": False,
                "response_status_code": None,
                "posthoc_generated": True,
            },
            "ui_fields": llm_ui_fields,
            "llm_analysis": llm_analysis,
            "markdown_report": str(llm_analysis.get("markdown_report", "")).strip(),
            "llm_report_path": str(llm_report_path).replace("\\", "/"),
            "llm_report_error": llm_report_error,
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        index_entry = {
            "created_at_iso": report["created_at_iso"],
            "request_id": "",
            "report_id": report_id,
            "user_id": s.user_id,
            "booking_id": s.booking_id,
            "flow_id": s.flow_id,
            "decision": s.decision,
            "risk_score": round(s.risk_score, 6),
            "report_stage": "posthoc",
            "report_path": str(report_path).replace("\\", "/"),
            "llm_report_path": str(llm_report_path).replace("\\", "/"),
        }
        with index_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(index_entry, ensure_ascii=False) + "\n")
        written += 1

    return {"candidates": len(candidates), "written": written, "llm_written": llm_written}


def build_account_reports(session_reports: List[SessionReport]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[SessionReport]] = defaultdict(list)
    for s in session_reports:
        grouped[s.account_key].append(s)

    account_reports: List[Dict[str, Any]] = []
    for key, rows in grouped.items():
        rows_sorted = sorted(rows, key=lambda r: r.risk_score, reverse=True)
        n = len(rows_sorted)
        risks = [r.risk_score for r in rows_sorted]
        avg_risk = sum(risks) / max(1, n)
        max_risk = max(risks) if risks else 0.0
        high_risk_count = sum(1 for x in risks if x >= 0.70)
        challenge_count = sum(1 for r in rows_sorted if r.decision == "challenge")
        block_count = sum(1 for r in rows_sorted if r.decision == "block")

        top_soft_rules: Dict[str, int] = defaultdict(int)
        top_hard_rules: Dict[str, int] = defaultdict(int)
        top_behavior: Dict[str, int] = defaultdict(int)
        for r in rows_sorted:
            for rr in r.rule_evidence.get("soft_rules_triggered", []):
                top_soft_rules[rr] += 1
            for rr in r.rule_evidence.get("hard_rules_triggered", []):
                top_hard_rules[rr] += 1
            for b in r.behavior_evidence:
                top_behavior[str(b.get("code", ""))] += 1

        account_risk = clamp01(0.60 * max_risk + 0.40 * avg_risk)
        confidence = clamp01(
            0.30
            + min(0.30, n * 0.03)
            + (0.15 if high_risk_count >= 2 else 0.0)
            + (0.15 if block_count >= 1 else 0.0)
            + (0.10 if challenge_count >= 3 else 0.0)
        )

        recommendation = "allow"
        if block_count >= 1 or high_risk_count >= 3:
            recommendation = "block_review"
        elif challenge_count >= 2 or high_risk_count >= 1:
            recommendation = "challenge"

        account_reports.append(
            {
                "account_key": key,
                "session_count": n,
                "account_risk": round(account_risk, 6),
                "confidence": round(confidence, 6),
                "recommendation": recommendation,
                "summary": {
                    "avg_risk": round(avg_risk, 6),
                    "max_risk": round(max_risk, 6),
                    "high_risk_count": high_risk_count,
                    "challenge_count": challenge_count,
                    "block_count": block_count,
                },
                "top_rule_evidence": {
                    "soft": sorted(top_soft_rules.items(), key=lambda x: x[1], reverse=True)[:5],
                    "hard": sorted(top_hard_rules.items(), key=lambda x: x[1], reverse=True)[:5],
                },
                "top_behavior_evidence": sorted(top_behavior.items(), key=lambda x: x[1], reverse=True)[:5],
                "recent_high_risk_flows": [r.flow_id for r in rows_sorted[:5]],
            }
        )

    return sorted(account_reports, key=lambda x: x["account_risk"], reverse=True)


def parse_args() -> argparse.Namespace:
    model_dir = ROOT_DIR / "model"
    parser = argparse.ArgumentParser(description="Build admin reports with separated evidences.")
    parser.add_argument("--browser-dir", default=str(model_dir / "data" / "raw" / "browser"))
    parser.add_argument("--server-dir", default=str(model_dir / "data" / "raw" / "server"))
    parser.add_argument("--params", default=str(model_dir / "artifacts" / "active" / "human_model_params.json"))
    parser.add_argument("--thresholds", default=str(model_dir / "artifacts" / "active" / "human_model_thresholds.json"))
    parser.add_argument("--out-session", default=str(model_dir / "reports" / "admin" / "session_reports.json"))
    parser.add_argument("--out-account", default=str(model_dir / "reports" / "admin" / "account_reports.json"))
    parser.add_argument("--out-block-dir", default=str(model_dir / "block_report"))
    parser.add_argument("--w-rule", type=float, default=0.2)
    parser.add_argument("--w-model", type=float, default=0.8)
    parser.add_argument("--allow-threshold", default="")
    parser.add_argument("--challenge-threshold", default="")
    parser.add_argument("--block-automation", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    browser_dir = Path(args.browser_dir)
    server_dir = Path(args.server_dir)
    out_session = Path(args.out_session)
    out_account = Path(args.out_account)
    out_block_dir = Path(args.out_block_dir)
    out_session.parent.mkdir(parents=True, exist_ok=True)
    out_account.parent.mkdir(parents=True, exist_ok=True)
    out_block_dir.mkdir(parents=True, exist_ok=True)

    params = json.loads(Path(args.params).read_text(encoding="utf-8"))
    thresholds_raw = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
    thresholds = resolve_thresholds(
        thresholds=thresholds_raw,
        allow_override=args.allow_threshold,
        challenge_override=args.challenge_threshold,
    )

    model_artifact = None
    artifact_path = resolve_artifact_path(str(params.get("model_artifact", "")), args.params)
    if artifact_path:
        model_artifact = joblib.load(artifact_path)

    server_index = build_server_index(server_dir)
    session_reports: List[SessionReport] = []

    browser_paths = sorted(browser_dir.rglob("*.json"))
    for browser_path in browser_paths:
        try:
            browser_log = load_json(browser_path)
        except Exception:
            continue

        flow_id = str(((browser_log.get("metadata") or {}).get("flow_id")) or "")
        server_log = find_server_for_flow(flow_id, server_index)
        features = extract_browser_features(browser_log)

        rule_eval = evaluate_rules(server_log or {}, browser_log=browser_log)
        rule_score = safe_float(rule_eval.get("soft_score"))
        hard_action = str(rule_eval.get("hard_action", "none"))
        model_score = 0.0
        model_top_contributions: List[Dict[str, Any]] = []
        model_top_features: List[str] = []
        if hard_action != "block":
            model_score = model_score_from_features(features, params, model_artifact=model_artifact)
            model_top_contributions = top_model_contributors(
                features=features,
                params=params,
                model_artifact=model_artifact,
                top_k=5,
            )
            model_top_features = [
                str(item.get("feature", "")).strip()
                for item in model_top_contributions
                if str(item.get("feature", "")).strip()
            ]

        risk_score = clamp01(args.w_model * model_score + args.w_rule * rule_score)
        decision = decision_from_risk(risk_score, thresholds)
        if hard_action == "block":
            decision = "block"
            risk_score = max(risk_score, thresholds["challenge"], 0.95)

        review_required = False
        block_recommended = False
        if decision == "block" and not args.block_automation and hard_action != "block":
            decision = "challenge"
            review_required = True
            block_recommended = True

        behavior_flags = behavior_evidence(features)
        confidence = calc_confidence(
            decision=decision,
            risk_score=risk_score,
            hard_action=hard_action,
            hard_rules=list(rule_eval.get("hard_rules_triggered", [])),
            soft_rules=list(rule_eval.get("soft_rules_triggered", [])),
            behavior_flags=behavior_flags,
            model_ready=(model_artifact is not None or params.get("model_type") == "zscore"),
        )

        model_evidence = {
            "model_type": params.get("model_type", "unknown"),
            "model_score": round(model_score, 6),
            "top_features": model_top_features[:3],
            "top_feature_contributions": model_top_contributions,
            "risk_allow_threshold": round(thresholds["allow"], 6),
            "risk_challenge_threshold": round(thresholds["challenge"], 6),
            "model_ready": bool(model_artifact is not None or params.get("model_type") == "zscore"),
        }
        rule_evidence = {
            "hard_action": hard_action,
            "hard_rules_triggered": rule_eval.get("hard_rules_triggered", []),
            "soft_rules_triggered": rule_eval.get("soft_rules_triggered", []),
            "rule_score": round(rule_score, 6),
            "review_required": review_required,
            "block_recommended": block_recommended,
        }
        recommendation = "allow"
        if decision == "challenge":
            recommendation = "challenge"
        elif decision == "block":
            recommendation = "block"

        browser_meta = (browser_log.get("metadata") or {}) if isinstance(browser_log, dict) else {}
        identity = (server_log.get("identity") or {}) if isinstance(server_log, dict) else {}
        session_ctx = (server_log.get("session") or {}) if isinstance(server_log, dict) else {}
        behavior_ctx = (server_log.get("behavior") or {}) if isinstance(server_log, dict) else {}

        user_id = (
            str(browser_meta.get("user_email", "")).strip()
            or str(identity.get("user_id_hash", "")).strip()
            or account_key(browser_log, server_log)
        )
        booking_id = str(browser_meta.get("booking_id", "")).strip()
        account_age_days = int(safe_float(session_ctx.get("account_age_days"), 0.0))
        is_verified = str(session_ctx.get("login_state", "")).strip().lower() in {"logged_in", "member"}
        past_successful_orders = int(safe_float(session_ctx.get("past_successful_orders"), 0.0))
        device_change_count = int(safe_float(behavior_ctx.get("concurrent_sessions_same_device"), 0.0))

        session_reports.append(
            SessionReport(
                account_key=account_key(browser_log, server_log),
                user_id=user_id,
                booking_id=booking_id,
                flow_id=flow_id,
                browser_log_path=str(browser_path),
                server_log_found=server_log is not None,
                decision=decision,
                recommendation=recommendation,
                confidence=confidence,
                risk_score=risk_score,
                rule_score=rule_score,
                model_score=model_score,
                account_age_days=account_age_days,
                is_verified=is_verified,
                past_successful_orders=past_successful_orders,
                device_change_count=device_change_count,
                rule_evidence=rule_evidence,
                model_evidence=model_evidence,
                behavior_evidence=behavior_flags,
            )
        )

    session_payload = [s.to_dict() for s in session_reports]
    account_payload = build_account_reports(session_reports)
    posthoc_stats = save_posthoc_block_reports(session_reports, out_block_dir=out_block_dir)

    out_session.write_text(json.dumps(session_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_account.write_text(json.dumps(account_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"session_reports={len(session_payload)}")
    print(f"account_reports={len(account_payload)}")
    print(f"posthoc_block_candidates={posthoc_stats['candidates']}")
    print(f"posthoc_block_written={posthoc_stats['written']}")
    if "llm_written" in posthoc_stats:
        print(f"posthoc_block_llm_written={posthoc_stats['llm_written']}")
    print(f"Wrote: {out_session}")
    print(f"Wrote: {out_account}")
    print(f"Wrote: {out_block_dir}")


if __name__ == "__main__":
    main()

