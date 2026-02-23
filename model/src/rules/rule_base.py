from typing import Any, Dict, List, Tuple


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _promote_action(current: str, incoming: str) -> str:
    order = {"none": 0, "challenge": 1, "block": 2}
    return incoming if order.get(incoming, 0) > order.get(current, 0) else current


def _count_untrusted_clicks(browser_log: Dict[str, Any]) -> int:
    if not browser_log:
        return 0
    stages = browser_log.get("stages", {}) or {}
    total = 0
    for stage_data in stages.values():
        clicks = (stage_data or {}).get("clicks", []) or []
        for click in clicks:
            if click.get("is_trusted") is False:
                total += 1
    return total


def evaluate_rules(server_log: Dict[str, Any], browser_log: Dict[str, Any] | None = None) -> Dict[str, Any]:
    behavior = server_log.get("behavior", {}) if server_log else {}
    queue = server_log.get("queue", {}) if server_log else {}
    seat = server_log.get("seat", {}) if server_log else {}
    security = server_log.get("security", {}) if server_log else {}

    soft_score = 0.0
    soft_rules: List[str] = []
    hard_rules: List[str] = []
    hard_action = "none"

    # ---- Hard Rules (immediate gate) ----
    # Policy:
    # 1) Boolean/explicit violation -> block
    # 2) Threshold-based spikes are handled as soft score only.
    if bool(security.get("blocked")):
        hard_action = _promote_action(hard_action, "block")
        hard_rules.append("security.blocked=true")

    req_1s = _safe_float(behavior.get("requests_last_1s"))
    same_ip = _safe_float(behavior.get("concurrent_sessions_same_ip"))
    same_device = _safe_float(behavior.get("concurrent_sessions_same_device"))

    poll = queue.get("poll_interval_ms_stats", {}) if queue else {}
    poll_p50 = _safe_float((poll or {}).get("p50"))
    jump_count = _safe_float(queue.get("jump_count"))

    untrusted_clicks = _count_untrusted_clicks(browser_log or {})

    # ---- Soft Rules (for rule_score) ----
    # Keep only session/request behavior signals. Account-history style signals are excluded.
    if same_device >= 3:
        soft_score += 0.35
        soft_rules.append("concurrent_sessions_same_device>=3")

    if same_device >= 8:
        soft_score += 0.30
        soft_rules.append("concurrent_sessions_same_device>=8")

    if same_ip >= 10:
        soft_score += 0.35
        soft_rules.append("concurrent_sessions_same_ip>=10")

    if same_ip >= 20:
        soft_score += 0.30
        soft_rules.append("concurrent_sessions_same_ip>=20")

    if req_1s >= 10:
        soft_score += 0.25
        soft_rules.append("requests_last_1s>=10")

    if req_1s >= 20:
        soft_score += 0.25
        soft_rules.append("requests_last_1s>=20")

    if security.get("captcha_required") and not security.get("captcha_passed"):
        soft_score += 0.30
        soft_rules.append("captcha_failed")

    if poll_p50 > 0 and poll_p50 < 200 and jump_count > 0:
        soft_score += 0.25
        soft_rules.append("queue_fast_poll_and_jump")

    if poll_p50 > 0 and poll_p50 < 120 and jump_count > 0:
        soft_score += 0.35
        soft_rules.append("queue_fast_poll_and_jump_hard")

    reserve_attempts = _safe_float(seat.get("reserve_attempt_count"))
    if reserve_attempts >= 10:
        soft_score += 0.20
        soft_rules.append("reserve_attempt_count>=10")

    if untrusted_clicks >= 1:
        soft_score += 0.20
        soft_rules.append("browser_untrusted_clicks>=1")
    if untrusted_clicks >= 3:
        soft_score += 0.30
        soft_rules.append("browser_untrusted_clicks>=3")

    return {
        "hard_action": hard_action,
        "hard_rules_triggered": hard_rules,
        "soft_score": clamp01(soft_score),
        "soft_rules_triggered": soft_rules,
        "untrusted_click_count": untrusted_clicks,
    }


def score_rules(server_log: Dict[str, Any]) -> Tuple[float, List[str]]:
    # Backward-compatible helper used by existing scripts.
    result = evaluate_rules(server_log, browser_log=None)
    return float(result.get("soft_score", 0.0)), list(result.get("soft_rules_triggered", []))
