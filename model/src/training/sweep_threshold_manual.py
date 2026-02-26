import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from model.src.training.compare_and_select import (
    _binary_stats,
    _drop_prefixed_features,
    build_feature_order,
    fit_candidate,
    load_feature_rows,
    normalize_scores,
    rows_to_matrix,
    score_candidate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manual threshold sweep for one-class models (direct threshold tuning)."
    )
    parser.add_argument("--model-type", default="isolation_forest", choices=["isolation_forest", "oneclass_svm", "deep_svdd", "zscore"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-human-dir", default="model/data/raw/auto_split/train/human")
    parser.add_argument("--val-human-dir", default="model/data/raw/auto_split/validation/human")
    parser.add_argument("--val-macro-dir", default="model/data/raw/auto_split/validation/macro")
    parser.add_argument("--test-human-dir", default="model/data/raw/auto_split/test/human")
    parser.add_argument("--test-macro-dir", default="model/data/raw/auto_split/test/macro")
    parser.add_argument(
        "--drop-feature-prefixes",
        nargs="*",
        default=[],
        help="Drop any feature whose name starts with one of these prefixes (e.g. browser_)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Evaluate one fixed threshold only. If omitted, sweep mode is used.",
    )
    parser.add_argument(
        "--threshold-start",
        type=float,
        default=None,
        help="Sweep start threshold (requires --threshold-end and --threshold-step).",
    )
    parser.add_argument(
        "--threshold-end",
        type=float,
        default=None,
        help="Sweep end threshold (requires --threshold-start and --threshold-step).",
    )
    parser.add_argument(
        "--threshold-step",
        type=float,
        default=None,
        help="Sweep step threshold (requires --threshold-start and --threshold-end).",
    )
    parser.add_argument(
        "--max-val-fpr",
        type=float,
        default=None,
        help="Optional cap (0~1). Report best recall among rows with val_human_fpr <= cap.",
    )
    parser.add_argument(
        "--out-csv",
        default="model/reports/benchmark/manual_threshold_sweep.csv",
    )
    parser.add_argument(
        "--out-json",
        default="model/reports/benchmark/manual_threshold_sweep_summary.json",
    )
    return parser.parse_args()


def _candidate_thresholds(
    *,
    val_h_scores: np.ndarray,
    val_m_scores: np.ndarray,
    fixed_threshold: float | None,
    start: float | None,
    end: float | None,
    step: float | None,
) -> np.ndarray:
    if fixed_threshold is not None:
        return np.array([float(fixed_threshold)], dtype=float)

    if start is not None or end is not None or step is not None:
        if start is None or end is None or step is None:
            raise SystemExit("threshold sweep range requires --threshold-start, --threshold-end, --threshold-step together")
        if step <= 0:
            raise SystemExit("--threshold-step must be > 0")
        count = int(np.floor((end - start) / step)) + 1
        if count <= 0:
            raise SystemExit("invalid threshold range")
        return np.array([start + i * step for i in range(count)], dtype=float)

    # Default: use all unique decision boundaries from validation scores.
    all_scores = np.unique(np.concatenate([val_h_scores, val_m_scores]))
    if all_scores.size == 0:
        return np.array([1.0], dtype=float)
    span = float(np.max(all_scores) - np.min(all_scores))
    eps = max(1e-12, span * 1e-9)
    return np.concatenate([all_scores, [float(np.max(all_scores) + eps)]])


def main() -> None:
    args = parse_args()
    out_csv = Path(args.out_csv)
    out_json = Path(args.out_json)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    train_h = load_feature_rows(Path(args.train_human_dir))
    val_h = load_feature_rows(Path(args.val_human_dir))
    val_m = load_feature_rows(Path(args.val_macro_dir))
    test_h = load_feature_rows(Path(args.test_human_dir))
    test_m = load_feature_rows(Path(args.test_macro_dir))

    if len(train_h) < 10 or len(val_h) < 5 or len(val_m) < 5:
        raise SystemExit("Not enough rows for threshold sweep.")

    drop_prefixes = list(args.drop_feature_prefixes or [])
    train_h = _drop_prefixed_features(train_h, drop_prefixes)
    val_h = _drop_prefixed_features(val_h, drop_prefixes)
    val_m = _drop_prefixed_features(val_m, drop_prefixes)
    test_h = _drop_prefixed_features(test_h, drop_prefixes)
    test_m = _drop_prefixed_features(test_m, drop_prefixes)

    feature_order = build_feature_order(train_h + val_h + val_m + test_h + test_m)
    X_train = rows_to_matrix(train_h, feature_order)
    X_val_h = rows_to_matrix(val_h, feature_order)
    X_val_m = rows_to_matrix(val_m, feature_order)
    X_test_h = rows_to_matrix(test_h, feature_order)
    X_test_m = rows_to_matrix(test_m, feature_order)

    state = fit_candidate(args.model_type, X_train, seed=int(args.seed))
    raw_train = state["raw_train"].reshape(-1)
    raw_min = float(np.min(raw_train))
    raw_max = float(np.max(raw_train))

    val_h_scores = normalize_scores(score_candidate(state, X_val_h).reshape(-1), raw_min, raw_max)
    val_m_scores = normalize_scores(score_candidate(state, X_val_m).reshape(-1), raw_min, raw_max)
    test_h_scores = normalize_scores(score_candidate(state, X_test_h).reshape(-1), raw_min, raw_max)
    test_m_scores = normalize_scores(score_candidate(state, X_test_m).reshape(-1), raw_min, raw_max)

    thresholds = _candidate_thresholds(
        val_h_scores=val_h_scores,
        val_m_scores=val_m_scores,
        fixed_threshold=args.threshold,
        start=args.threshold_start,
        end=args.threshold_end,
        step=args.threshold_step,
    )

    rows: List[Dict[str, Any]] = []
    for t in thresholds:
        val_stats = _binary_stats(human_scores=val_h_scores, macro_scores=val_m_scores, threshold=float(t))
        test_stats = _binary_stats(human_scores=test_h_scores, macro_scores=test_m_scores, threshold=float(t))
        rows.append(
            {
                "threshold": float(t),
                "val_human_fpr": float(val_stats["human_fpr"]),
                "val_macro_recall": float(val_stats["macro_recall"]),
                "val_macro_precision": float(val_stats["precision"]),
                "val_f1": float(val_stats["f1"]),
                "test_human_fpr": float(test_stats["human_fpr"]),
                "test_macro_recall": float(test_stats["macro_recall"]),
                "test_macro_precision": float(test_stats["precision"]),
                "test_f1": float(test_stats["f1"]),
                "test_tp": int(test_stats["tp"]),
                "test_fp": int(test_stats["fp"]),
                "test_fn": int(test_stats["fn"]),
                "test_tn": int(test_stats["tn"]),
            }
        )

    rows_sorted = sorted(
        rows,
        key=lambda r: (r["val_f1"], r["val_macro_recall"], r["val_macro_precision"], -r["val_human_fpr"]),
        reverse=True,
    )

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows_sorted[0].keys()))
        writer.writeheader()
        writer.writerows(rows_sorted)

    best_val_f1 = rows_sorted[0]
    best_under_cap = None
    if args.max_val_fpr is not None:
        cap = float(args.max_val_fpr)
        feasible = [r for r in rows_sorted if r["val_human_fpr"] <= cap]
        if feasible:
            best_under_cap = max(
                feasible,
                key=lambda r: (r["val_macro_recall"], r["val_macro_precision"], r["val_f1"], -r["val_human_fpr"]),
            )

    summary = {
        "model_type": args.model_type,
        "seed": int(args.seed),
        "counts": {
            "train_human": len(train_h),
            "val_human": len(val_h),
            "val_macro": len(val_m),
            "test_human": len(test_h),
            "test_macro": len(test_m),
        },
        "drop_feature_prefixes": drop_prefixes,
        "threshold_count": len(rows),
        "best_by_val_f1": best_val_f1,
        "best_under_val_fpr_cap": best_under_cap,
    }
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote: {out_csv}")
    print(f"Wrote: {out_json}")
    print("[BEST_BY_VAL_F1]", best_val_f1)
    if args.max_val_fpr is not None:
        print("[BEST_UNDER_VAL_FPR_CAP]", best_under_cap)


if __name__ == "__main__":
    main()
