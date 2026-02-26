import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _parse_iso(value: str) -> datetime:
    v = str(value or "").strip()
    if not v:
        raise ValueError("empty datetime")
    # Support trailing Z and +09:00 style offsets.
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    return datetime.fromisoformat(v)


def _format_like(source: str, dt: datetime) -> str:
    # Keep offset style; milliseconds precision is enough for logs.
    if "." in source:
        return dt.isoformat(timespec="milliseconds")
    return dt.isoformat(timespec="seconds")


def _deterministic_wait_ms(
    flow_id: str,
    *,
    base_wait_ms: int,
    slot_ms: int,
    step_cap: int,
    jitter_ms: int,
) -> int:
    key = flow_id or "unknown_flow"
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
    steps = h % (max(0, step_cap) + 1)
    jitter = (h // 13) % (max(0, jitter_ms) + 1) if jitter_ms > 0 else 0
    return base_wait_ms + (steps * slot_ms) + int(jitter)


def _should_rewrite(queue: Dict[str, Any], old_duration_ms: int, short_threshold_ms: int) -> bool:
    if old_duration_ms <= 0 or old_duration_ms >= short_threshold_ms:
        return False
    total_queue = _safe_int(queue.get("total_queue"), 0)
    initial_pos = _safe_int(queue.get("initial_position"), 0)
    final_pos = _safe_int(queue.get("final_position"), 0)
    pos_delta = max(0, initial_pos - final_pos)
    # Old short-queue pattern: very short duration with queue size/position ~= 1
    return total_queue <= 1 and pos_delta <= 1


def _rewrite_file(
    path: Path,
    *,
    base_wait_ms: int,
    slot_ms: int,
    step_cap: int,
    jitter_ms: int,
    short_threshold_ms: int,
    dry_run: bool,
) -> Tuple[bool, int, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    stages = data.get("stages") or {}
    queue = stages.get("queue") or {}
    metadata = data.get("metadata") or {}

    old_duration_ms = _safe_int(queue.get("duration_ms"), 0)
    if not _should_rewrite(queue, old_duration_ms, short_threshold_ms):
        return False, old_duration_ms, old_duration_ms

    old_wait_ms = _safe_int(queue.get("wait_duration_ms"), max(0, old_duration_ms - 40))
    old_overhead_ms = max(20, old_duration_ms - old_wait_ms)

    flow_id = str(metadata.get("flow_id", "") or "")
    new_wait_ms = _deterministic_wait_ms(
        flow_id,
        base_wait_ms=base_wait_ms,
        slot_ms=slot_ms,
        step_cap=step_cap,
        jitter_ms=jitter_ms,
    )
    new_duration_ms = new_wait_ms + old_overhead_ms
    delta_ms = new_duration_ms - old_duration_ms

    queue["wait_duration_ms"] = int(new_wait_ms)
    queue["duration_ms"] = int(new_duration_ms)

    entry_time = str(queue.get("entry_time", "") or "")
    exit_time = str(queue.get("exit_time", "") or "")
    if entry_time and exit_time:
        try:
            dt_entry = _parse_iso(entry_time)
            dt_exit = dt_entry + timedelta(milliseconds=int(new_duration_ms))
            queue["exit_time"] = _format_like(exit_time, dt_exit)
        except Exception:
            # Keep original timestamps if parsing fails.
            pass

    old_total = _safe_int(metadata.get("total_duration_ms"), 0)
    if old_total > 0:
        metadata["total_duration_ms"] = int(max(1, old_total + delta_ms))

    stages["queue"] = queue
    data["stages"] = stages
    data["metadata"] = metadata

    if not dry_run:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, old_duration_ms, new_duration_ms


def _extract_date_token(path: Path) -> str:
    name = path.name
    token = name.split("_", 1)[0]
    if len(token) == 8 and token.isdigit():
        return token
    return "unknown_date"


def _extract_perf_token(path: Path, metadata: Dict[str, Any]) -> str:
    perf = str(metadata.get("performance_id", "") or "").strip()
    if perf:
        return perf
    parts = path.name.split("_")
    if len(parts) >= 2:
        return parts[1]
    return "unknown_perf"


def _build_early_group_key(
    path: Path,
    metadata: Dict[str, Any],
    total_queue: int,
    *,
    mode: str,
) -> Tuple[Any, ...]:
    if mode == "all":
        return ("ALL",)
    if mode == "total_queue":
        return (total_queue,)
    if mode == "performance":
        return (_extract_perf_token(path, metadata),)
    # default: date_perf_total_queue
    return (
        _extract_date_token(path),
        _extract_perf_token(path, metadata),
        total_queue,
    )


def _collect_early_rows(
    split_roots: List[Path],
    *,
    group_mode: str,
) -> Tuple[List[Dict[str, Any]], int]:
    rows: List[Dict[str, Any]] = []
    parse_fail = 0
    for root in split_roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                stages = data.get("stages") or {}
                queue = stages.get("queue") or {}
                metadata = data.get("metadata") or {}
                entry_time = str(queue.get("entry_time", "") or "").strip()
                if not entry_time:
                    continue
                entry_dt = _parse_iso(entry_time)
                old_duration_ms = _safe_int(queue.get("duration_ms"), 0)
                old_wait_ms = _safe_int(queue.get("wait_duration_ms"), old_duration_ms)
                if old_duration_ms <= 0 or old_wait_ms <= 0:
                    continue
                total_queue = _safe_int(queue.get("total_queue"), 0)
                group_key = _build_early_group_key(
                    path,
                    metadata,
                    total_queue,
                    mode=group_mode,
                )
                rows.append(
                    {
                        "path": path,
                        "entry_dt": entry_dt,
                        "group_key": group_key,
                        "old_wait_ms": old_wait_ms,
                    }
                )
            except Exception:
                parse_fail += 1
    return rows, parse_fail


def _rewrite_file_to_target_wait(
    path: Path,
    *,
    target_wait_ms: int,
    dry_run: bool,
) -> Tuple[bool, int, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    stages = data.get("stages") or {}
    queue = stages.get("queue") or {}
    metadata = data.get("metadata") or {}

    old_duration_ms = _safe_int(queue.get("duration_ms"), 0)
    old_wait_ms = _safe_int(queue.get("wait_duration_ms"), old_duration_ms)
    if old_duration_ms <= 0 or old_wait_ms <= 0:
        return False, old_wait_ms, old_wait_ms

    old_overhead_ms = max(20, old_duration_ms - old_wait_ms)
    new_wait_ms = int(max(1, target_wait_ms))
    new_duration_ms = int(new_wait_ms + old_overhead_ms)

    if new_wait_ms == old_wait_ms and new_duration_ms == old_duration_ms:
        return False, old_wait_ms, new_wait_ms

    queue["wait_duration_ms"] = int(new_wait_ms)
    queue["duration_ms"] = int(new_duration_ms)

    entry_time = str(queue.get("entry_time", "") or "")
    exit_time = str(queue.get("exit_time", "") or "")
    if entry_time and exit_time:
        try:
            dt_entry = _parse_iso(entry_time)
            dt_exit = dt_entry + timedelta(milliseconds=int(new_duration_ms))
            queue["exit_time"] = _format_like(exit_time, dt_exit)
        except Exception:
            pass

    old_total = _safe_int(metadata.get("total_duration_ms"), 0)
    delta_ms = new_duration_ms - old_duration_ms
    if old_total > 0:
        metadata["total_duration_ms"] = int(max(1, old_total + delta_ms))

    stages["queue"] = queue
    data["stages"] = stages
    data["metadata"] = metadata
    if not dry_run:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, old_wait_ms, new_wait_ms


def _enforce_early_shorter(
    split_roots: List[Path],
    *,
    dry_run: bool,
    min_group_size: int,
    group_mode: str,
) -> None:
    rows, parse_fail = _collect_early_rows(
        split_roots,
        group_mode=group_mode,
    )
    if not rows:
        print("No queue rows eligible for early-entry normalization.")
        return

    grouped: Dict[Tuple[str, str, int], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["group_key"]].append(row)

    changed = 0
    before_sum = 0
    after_sum = 0
    groups_applied = 0
    changed_by_dir: Dict[str, int] = {}

    for key in sorted(grouped.keys()):
        items = grouped[key]
        if len(items) < max(2, int(min_group_size)):
            continue
        items.sort(key=lambda x: (x["entry_dt"], str(x["path"].name)))

        old_waits = [int(x["old_wait_ms"]) for x in items]
        min_wait = int(min(old_waits))
        max_wait = int(max(old_waits))
        n = len(items)

        min_required_span = max(1, n - 1)
        span = max_wait - min_wait
        if span < min_required_span:
            max_wait = min_wait + min_required_span
            span = max_wait - min_wait

        prev_target = None
        for idx, row in enumerate(items):
            ratio = (idx / (n - 1)) if n > 1 else 0.0
            target_wait = int(round(min_wait + (span * ratio)))
            if prev_target is not None and target_wait <= prev_target:
                target_wait = prev_target + 1
            prev_target = target_wait

            touched, old_wait_ms, new_wait_ms = _rewrite_file_to_target_wait(
                row["path"],
                target_wait_ms=target_wait,
                dry_run=dry_run,
            )
            if touched:
                changed += 1
                before_sum += int(old_wait_ms)
                after_sum += int(new_wait_ms)
                changed_by_dir[str(row["path"].parent)] = changed_by_dir.get(str(row["path"].parent), 0) + 1
        groups_applied += 1

    mode = "DRY-RUN" if dry_run else "APPLY"
    print(
        f"[{mode}][EARLY] scanned={len(rows)} parse_fail={parse_fail} "
        f"group_mode={group_mode} groups={len(grouped)} "
        f"groups_applied={groups_applied} changed={changed}"
    )
    if changed > 0:
        print(f"avg_wait_before={before_sum/changed:.2f}ms avg_wait_after={after_sum/changed:.2f}ms")
    for k in sorted(changed_by_dir.keys()):
        print(f"{k}: {changed_by_dir[k]}")


def _collect_files(split_roots: List[Path]) -> List[Path]:
    out: List[Path] = []
    for root in split_roots:
        if not root.exists():
            continue
        out.extend(sorted(root.glob("*.json")))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize short queue dwell-time in human logs.")
    parser.add_argument(
        "--human-dirs",
        nargs="*",
        default=[
            "model/data/raw/train/human",
            "model/data/raw/validation/human",
            "model/data/raw/test/human",
        ],
        help="Human split dirs to rewrite",
    )
    parser.add_argument("--base-wait-ms", type=int, default=3000)
    parser.add_argument("--slot-ms", type=int, default=350)
    parser.add_argument("--step-cap", type=int, default=3)
    parser.add_argument("--jitter-ms", type=int, default=120)
    parser.add_argument("--short-threshold-ms", type=int, default=1200)
    parser.add_argument(
        "--strategy",
        choices=["legacy_short_only", "enforce_early_shorter"],
        default="legacy_short_only",
        help=(
            "legacy_short_only: rewrite only old short-queue outliers; "
            "enforce_early_shorter: enforce earlier queue entry -> shorter wait per (date, performance, total_queue)."
        ),
    )
    parser.add_argument(
        "--min-group-size",
        type=int,
        default=2,
        help="Minimum records per group for enforce_early_shorter strategy",
    )
    parser.add_argument(
        "--early-group-mode",
        choices=["all", "total_queue", "performance", "date_perf_total_queue"],
        default="date_perf_total_queue",
        help=(
            "Grouping key for enforce_early_shorter strategy. "
            "Use 'all' to enforce globally without per-group separation."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    split_roots = [Path(p) for p in args.human_dirs]
    if args.strategy == "enforce_early_shorter":
        _enforce_early_shorter(
            split_roots=split_roots,
            dry_run=bool(args.dry_run),
            min_group_size=int(args.min_group_size),
            group_mode=str(args.early_group_mode),
        )
        return

    files = _collect_files(split_roots)
    if not files:
        print("No human log files found.")
        return

    changed = 0
    before_sum = 0
    after_sum = 0
    changed_by_dir: Dict[str, int] = {}

    for p in files:
        touched, old_ms, new_ms = _rewrite_file(
            p,
            base_wait_ms=args.base_wait_ms,
            slot_ms=args.slot_ms,
            step_cap=args.step_cap,
            jitter_ms=args.jitter_ms,
            short_threshold_ms=args.short_threshold_ms,
            dry_run=args.dry_run,
        )
        if touched:
            changed += 1
            before_sum += old_ms
            after_sum += new_ms
            changed_by_dir[str(p.parent)] = changed_by_dir.get(str(p.parent), 0) + 1

    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"[{mode}] scanned={len(files)} changed={changed}")
    if changed > 0:
        print(f"avg_queue_duration_before={before_sum/changed:.2f}ms after={after_sum/changed:.2f}ms")
    for k in sorted(changed_by_dir.keys()):
        print(f"{k}: {changed_by_dir[k]}")


if __name__ == "__main__":
    main()
