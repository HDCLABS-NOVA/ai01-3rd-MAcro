import json
import math
from bisect import bisect_right
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y", "on"}:
            return True
        if v in {"0", "false", "no", "n", "off"}:
            return False
    return default


def safe_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def safe_std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = safe_mean(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def safe_var(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = safe_mean(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def safe_percentile(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0]
    p = max(0.0, min(100.0, percentile))
    rank = (p / 100.0) * (len(vals) - 1)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return vals[low]
    w = rank - low
    return vals[low] * (1.0 - w) + vals[high] * w


def extract_click_timestamps(clicks: List[Dict[str, Any]]) -> List[float]:
    click_ts: List[float] = []
    for c in clicks:
        if c.get("timestamp") is not None:
            click_ts.append(safe_float(c.get("timestamp")))
        elif c.get("relative_ms_from_entry") is not None:
            click_ts.append(safe_float(c.get("relative_ms_from_entry")))
        elif c.get("event_time_epoch_ms") is not None:
            click_ts.append(safe_float(c.get("event_time_epoch_ms")))
    return sorted(click_ts)


def click_tempo_entropy(click_intervals: List[float]) -> float:
    valid = [v for v in click_intervals if v > 0.0]
    if not valid:
        return 0.0
    # Log-like binning keeps both very-fast and slow tempos separable.
    bins = [40.0, 80.0, 160.0, 320.0, 640.0, 1280.0, 2560.0, float("inf")]
    counts = [0 for _ in bins]
    for v in valid:
        for i, upper in enumerate(bins):
            if v <= upper:
                counts[i] += 1
                break
    total = float(sum(counts))
    if total <= 0.0:
        return 0.0
    entropy = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = float(c) / total
        entropy -= p * math.log2(p)
    max_entropy = math.log2(float(len(counts)))
    if max_entropy <= 0.0:
        return 0.0
    return entropy / max_entropy


def trajectory_curvature_rad(trajectory: List[List[Any]]) -> float:
    if len(trajectory) < 3:
        return 0.0
    angle_sum = 0.0
    turn_count = 0
    for i in range(1, len(trajectory) - 1):
        p0 = trajectory[i - 1]
        p1 = trajectory[i]
        p2 = trajectory[i + 1]
        x0 = safe_float(p0[0])
        y0 = safe_float(p0[1])
        x1 = safe_float(p1[0])
        y1 = safe_float(p1[1])
        x2 = safe_float(p2[0])
        y2 = safe_float(p2[1])
        v1x = x1 - x0
        v1y = y1 - y0
        v2x = x2 - x1
        v2y = y2 - y1
        n1 = math.sqrt(v1x * v1x + v1y * v1y)
        n2 = math.sqrt(v2x * v2x + v2y * v2y)
        if n1 <= 1e-9 or n2 <= 1e-9:
            continue
        cos_theta = (v1x * v2x + v1y * v2y) / (n1 * n2)
        cos_theta = max(-1.0, min(1.0, cos_theta))
        angle_sum += abs(math.acos(cos_theta))
        turn_count += 1
    if turn_count <= 0:
        return 0.0
    return angle_sum / float(turn_count)


def reaction_time_latencies_ms(click_ts: List[float], trajectory: List[List[Any]]) -> List[float]:
    if not click_ts or not trajectory:
        return []
    move_ts = sorted(
        [
            safe_float(p[2])
            for p in trajectory
            if isinstance(p, list) and len(p) >= 3 and p[2] is not None
        ]
    )
    if not move_ts:
        return []
    latencies: List[float] = []
    for ts in click_ts:
        idx = bisect_right(move_ts, ts) - 1
        if idx < 0:
            continue
        dt = ts - move_ts[idx]
        if dt >= 0.0:
            latencies.append(dt)
    return latencies


def trajectory_speeds(trajectory: List[List[Any]]) -> List[float]:
    speeds: List[float] = []
    if len(trajectory) < 2:
        return speeds
    for i in range(1, len(trajectory)):
        p1 = trajectory[i - 1]
        p2 = trajectory[i]
        x1 = safe_float(p1[0])
        y1 = safe_float(p1[1])
        t1 = safe_float(p1[2])
        x2 = safe_float(p2[0])
        y2 = safe_float(p2[1])
        t2 = safe_float(p2[2])
        dt = t2 - t1
        if dt <= 0:
            continue
        dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        speeds.append(dist / dt)
    return speeds


def trajectory_straightness(trajectory: List[List[Any]]) -> float:
    if len(trajectory) < 2:
        return 1.0
    sx = safe_float(trajectory[0][0])
    sy = safe_float(trajectory[0][1])
    ex = safe_float(trajectory[-1][0])
    ey = safe_float(trajectory[-1][1])
    direct = math.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)
    total = 0.0
    for i in range(1, len(trajectory)):
        p1 = trajectory[i - 1]
        p2 = trajectory[i]
        x1 = safe_float(p1[0])
        y1 = safe_float(p1[1])
        x2 = safe_float(p2[0])
        y2 = safe_float(p2[1])
        total += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if total <= 0:
        return 1.0
    return direct / total


def _extract_hover_features(stage_data: Dict[str, Any]) -> Dict[str, float]:
    hover_events = stage_data.get("hover_events", []) or []
    hover_summary = stage_data.get("hover_summary", {}) or {}

    dwell_values: List[float] = []
    target_ids: List[str] = []
    trusted_flags: List[float] = []

    for ev in hover_events:
        dwell = safe_float(ev.get("dwell_ms"))
        if dwell > 0:
            dwell_values.append(dwell)

        target = str(
            ev.get("target_id")
            or ev.get("seat_id")
            or ev.get("target")
            or ""
        ).strip()
        if target:
            target_ids.append(target)

        trusted_flags.append(1.0 if ev.get("is_trusted") else 0.0)

    hover_count = float(len(hover_events))
    if hover_count <= 0:
        hover_count = safe_float(hover_summary.get("hover_count"))

    unique_targets = float(len(set(target_ids))) if target_ids else safe_float(hover_summary.get("unique_targets"))

    avg_dwell = safe_mean(dwell_values) if dwell_values else safe_float(hover_summary.get("avg_dwell_ms"))
    std_dwell = safe_std(dwell_values) if dwell_values else 0.0
    p50_dwell = safe_percentile(dwell_values, 50.0) if dwell_values else safe_float(hover_summary.get("p50_dwell_ms"))
    p95_dwell = safe_percentile(dwell_values, 95.0) if dwell_values else safe_float(hover_summary.get("p95_dwell_ms"))

    if hover_count > 0 and unique_targets > 0 and not hover_summary.get("revisit_rate"):
        revisit_rate = max(0.0, (hover_count - unique_targets) / hover_count)
    else:
        revisit_rate = safe_float(hover_summary.get("revisit_rate"))

    return {
        "hover_count": hover_count,
        "hover_unique_targets": unique_targets,
        "hover_avg_dwell_ms": avg_dwell,
        "hover_std_dwell_ms": std_dwell,
        "hover_p50_dwell_ms": p50_dwell,
        "hover_p95_dwell_ms": p95_dwell,
        "hover_revisit_rate": revisit_rate,
        "hover_to_click_ms_p50": safe_float(hover_summary.get("hover_to_click_ms_p50")),
        "hover_trusted_ratio": safe_mean(trusted_flags),
        "hover_unique_grades": safe_float(hover_summary.get("unique_grades")),
    }


def _extract_stage_features(stage_name: str, stage_data: Dict[str, Any]) -> Dict[str, float]:
    features: Dict[str, float] = {}
    clicks = [c for c in (stage_data.get("clicks", []) or []) if isinstance(c, dict)]
    trajectory = stage_data.get("mouse_trajectory", []) or []

    durations = [safe_float(c.get("duration")) for c in clicks]
    trusted_flags = [1.0 if safe_bool(c.get("is_trusted")) else 0.0 for c in clicks]

    click_ts = extract_click_timestamps(clicks)
    click_intervals = [click_ts[i] - click_ts[i - 1] for i in range(1, len(click_ts))]

    speeds = trajectory_speeds(trajectory)
    reaction_latencies = reaction_time_latencies_ms(click_ts, trajectory)

    features[f"{stage_name}_duration_ms"] = safe_float(stage_data.get("duration_ms"))
    features[f"{stage_name}_click_count"] = float(len(clicks))
    features[f"{stage_name}_mouse_points"] = float(len(trajectory))
    features[f"{stage_name}_avg_click_duration"] = safe_mean(durations)
    features[f"{stage_name}_std_click_duration"] = safe_std(durations)
    features[f"{stage_name}_trusted_ratio"] = safe_mean(trusted_flags)
    features[f"{stage_name}_avg_click_interval"] = safe_mean(click_intervals)
    features[f"{stage_name}_std_click_interval"] = safe_std(click_intervals)
    features[f"{stage_name}_reaction_time_var_ms2"] = safe_var(reaction_latencies)
    features[f"{stage_name}_click_tempo_entropy"] = click_tempo_entropy(click_intervals)
    features[f"{stage_name}_avg_mouse_speed"] = safe_mean(speeds)
    features[f"{stage_name}_std_mouse_speed"] = safe_std(speeds)
    features[f"{stage_name}_avg_straightness"] = trajectory_straightness(trajectory)
    features[f"{stage_name}_mouse_curvature_rad"] = trajectory_curvature_rad(trajectory)

    hover = _extract_hover_features(stage_data)
    for key, value in hover.items():
        features[f"{stage_name}_{key}"] = value

    hover_count = hover.get("hover_count", 0.0)
    features[f"{stage_name}_click_to_hover_ratio"] = float(len(clicks)) / hover_count if hover_count > 0 else 0.0
    return features


def extract_browser_features(browser_log: Dict[str, Any]) -> Dict[str, float]:
    stages = browser_log.get("stages", {}) or {}
    metadata = browser_log.get("metadata", {}) or {}
    perf = stages.get("perf", {}) or {}
    queue = stages.get("queue", {}) or {}
    captcha = stages.get("captcha", {}) or {}
    seat = stages.get("seat", {}) or {}
    browser_info = metadata.get("browser_info", {}) or {}
    screen = browser_info.get("screen", {}) or {}

    features: Dict[str, float] = {}
    features.update(_extract_stage_features("perf", perf))
    features.update(_extract_stage_features("queue", queue))
    features.update(_extract_stage_features("captcha", captcha))
    features.update(_extract_stage_features("seat", seat))

    key_stages = ["perf", "queue", "captcha", "seat"]
    features["overall_reaction_time_var_ms2"] = safe_mean(
        [safe_float(features.get(f"{name}_reaction_time_var_ms2")) for name in key_stages]
    )
    features["overall_click_tempo_entropy"] = safe_mean(
        [safe_float(features.get(f"{name}_click_tempo_entropy")) for name in key_stages]
    )
    features["overall_mouse_curvature_rad"] = safe_mean(
        [safe_float(features.get(f"{name}_mouse_curvature_rad")) for name in key_stages]
    )

    features["total_duration_ms"] = safe_float(metadata.get("total_duration_ms"))
    features["selected_seat_count"] = float(len(seat.get("selected_seats", []) or []))
    features["seat_details_count"] = float(len(seat.get("seat_details", []) or []))
    features["is_completed"] = 1.0 if metadata.get("is_completed") else 0.0
    features["booking_flow_started"] = 1.0 if metadata.get("booking_flow_started") else 0.0
    features["completion_status_success"] = 1.0 if str(metadata.get("completion_status", "")).lower() == "success" else 0.0
    features["perf_actions_count"] = float(len(perf.get("actions", []) or []))
    features["queue_position_delta"] = safe_float(queue.get("initial_position")) - safe_float(queue.get("final_position"))
    features["queue_total_queue"] = safe_float(queue.get("total_queue"))
    features["queue_position_updates_count"] = float(len(queue.get("position_updates", []) or []))
    features["captcha_status_success"] = 1.0 if str(captcha.get("status", "")).lower() in {"success", "verified", "passed", "pass"} else 0.0
    features["browser_webdriver"] = 1.0 if safe_bool(browser_info.get("webdriver")) else 0.0
    features["browser_hardware_concurrency"] = safe_float(browser_info.get("hardwareConcurrency"))
    features["browser_screen_ratio"] = safe_float(screen.get("ratio"))
    features["browser_screen_w"] = safe_float(screen.get("w"))
    features["browser_screen_h"] = safe_float(screen.get("h"))
    return features


def extract_server_features(server_log: Optional[Dict[str, Any]]) -> Dict[str, float]:
    if not server_log:
        return {
            "srv_latency_ms": 0.0,
            "srv_status_code": 0.0,
            "srv_body_size_bytes": 0.0,
            "srv_requests_last_1s": 0.0,
            "srv_requests_last_10s": 0.0,
            "srv_requests_last_60s": 0.0,
            "srv_unique_endpoints_last_60s": 0.0,
        }

    response = server_log.get("response", {})
    request = server_log.get("request", {})
    behavior = server_log.get("behavior", {})
    return {
        "srv_latency_ms": safe_float(response.get("latency_ms")),
        "srv_status_code": safe_float(response.get("status_code")),
        "srv_body_size_bytes": safe_float(request.get("body_size_bytes")),
        "srv_requests_last_1s": safe_float(behavior.get("requests_last_1s")),
        "srv_requests_last_10s": safe_float(behavior.get("requests_last_10s")),
        "srv_requests_last_60s": safe_float(behavior.get("requests_last_60s")),
        "srv_unique_endpoints_last_60s": safe_float(behavior.get("unique_endpoints_last_60s")),
    }


def build_server_index(server_root: Path) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    if not server_root.exists():
        return index
    for path in server_root.rglob("*.json"):
        try:
            data = load_json(path)
        except Exception:
            continue
        flow_id = (data.get("metadata", {}) or {}).get("flow_id")
        if not flow_id:
            continue
        # Keep latest event for each flow_id.
        current = index.get(flow_id)
        current_ts = safe_float((current or {}).get("metadata", {}).get("received_epoch_ms")) if current else -1.0
        next_ts = safe_float((data.get("metadata", {}) or {}).get("received_epoch_ms"))
        if current is None or next_ts >= current_ts:
            index[flow_id] = data
    return index


def extract_combined_features(browser_log: Dict[str, Any], server_log: Optional[Dict[str, Any]]) -> Dict[str, float]:
    features = extract_browser_features(browser_log)
    features.update(extract_server_features(server_log))
    return features
