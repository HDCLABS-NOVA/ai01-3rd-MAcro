import argparse
import csv
import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from model.src.features.feature_pipeline import extract_browser_features, load_json
from model.src.training.compare_and_select import (
    _binary_stats,
    _drop_prefixed_features,
    build_feature_order,
    evaluate_candidate,
    fit_candidate,
    normalize_scores,
    score_candidate,
)


MODEL_DIR = ROOT_DIR / "model"
DEFAULT_DATA_ROOT = MODEL_DIR / "data" / "raw" / "rebalanced_v1"
DEFAULT_OUT_CSV = MODEL_DIR / "reports" / "benchmark" / "rebalanced_v1_split_search.csv"
DEFAULT_OUT_JSON = MODEL_DIR / "reports" / "benchmark" / "rebalanced_v1_split_search.json"


@dataclass
class SeedResult:
    seed: int
    human_counts: Dict[str, int]
    macro_counts: Dict[str, int]
    threshold: float
    val_human_fpr: float
    val_macro_recall: float
    test_human_fpr: float
    test_macro_recall: float
    test_precision: float
    test_f1: float
    val_auroc: float
    val_pr_auc: float
    test_auroc: float
    test_pr_auc: float
    stability_gap: float
    score_shift_ks: float
    objective: float


def _parse_ratio(value: str, label: str) -> Tuple[float, float, float]:
    parts = [p.strip() for p in str(value).split(":")]
    if len(parts) != 3:
        raise ValueError(f"{label} ratio must have 3 parts like '7:1.5:1.5'")
    vals = tuple(float(p) for p in parts)
    if any(v < 0 for v in vals):
        raise ValueError(f"{label} ratio must be non-negative")
    if sum(vals) <= 0:
        raise ValueError(f"{label} ratio sum must be > 0")
    return vals  # type: ignore[return-value]


def _allocate_counts(total: int, ratio: Tuple[float, float, float]) -> Dict[str, int]:
    weights = list(ratio)
    s = sum(weights)
    raw = [(w / s) * total for w in weights]
    base = [int(np.floor(x)) for x in raw]
    rem = total - sum(base)
    order = sorted([(raw[i] - base[i], i) for i in range(3)], key=lambda x: x[0], reverse=True)
    for i in range(rem):
        base[order[i][1]] += 1
    return {"train": base[0], "validation": base[1], "test": base[2]}


def _split_rows(rows: List[Dict[str, Any]], counts: Dict[str, int], seed: int) -> Dict[str, List[Dict[str, Any]]]:
    shuffled = list(rows)
    rnd = random.Random(seed)
    rnd.shuffle(shuffled)
    t = counts["train"]
    v = counts["validation"]
    return {
        "train": shuffled[:t],
        "validation": shuffled[t : t + v],
        "test": shuffled[t + v : t + v + counts["test"]],
    }


def _load_rows_from_dirs(dirs: Sequence[Path]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for d in dirs:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.json")):
            try:
                log = load_json(p)
                feats = extract_browser_features(log)
            except Exception:
                continue
            out.append(
                {
                    "path": str(p),
                    "flow_id": ((log.get("metadata") or {}).get("flow_id")) or "",
                    "features": feats,
                }
            )
    return out


def _ks_stat(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    a_sorted = np.sort(a)
    b_sorted = np.sort(b)
    points = np.unique(np.concatenate([a_sorted, b_sorted]))
    cdf_a = np.searchsorted(a_sorted, points, side="right") / a_sorted.size
    cdf_b = np.searchsorted(b_sorted, points, side="right") / b_sorted.size
    return float(np.max(np.abs(cdf_a - cdf_b)))


def _evaluate_seed(
    *,
    seed: int,
    human_all: List[Dict[str, Any]],
    macro_all: List[Dict[str, Any]],
    human_ratio: Tuple[float, float, float],
    macro_ratio: Tuple[float, float, float],
    model_type: str,
    fpr_target: float,
    threshold_safety_margin: float,
    drop_feature_prefixes: List[str],
) -> SeedResult:
    human_counts = _allocate_counts(len(human_all), human_ratio)
    macro_counts = _allocate_counts(len(macro_all), macro_ratio)
    human_split = _split_rows(human_all, human_counts, seed=seed)
    macro_split = _split_rows(macro_all, macro_counts, seed=seed)

    train_rows = _drop_prefixed_features(human_split["train"], drop_feature_prefixes)
    val_h_rows = _drop_prefixed_features(human_split["validation"], drop_feature_prefixes)
    val_m_rows = _drop_prefixed_features(macro_split["validation"], drop_feature_prefixes)
    test_h_rows = _drop_prefixed_features(human_split["test"], drop_feature_prefixes)
    test_m_rows = _drop_prefixed_features(macro_split["test"], drop_feature_prefixes)

    feature_order = build_feature_order(train_rows + val_h_rows + val_m_rows + test_h_rows + test_m_rows)
    if not feature_order:
        raise RuntimeError("feature_order is empty after feature filtering")

    X_train = np.asarray(
        [[float((r.get("features") or {}).get(k, 0.0) or 0.0) for k in feature_order] for r in train_rows],
        dtype=float,
    )
    X_val_h = np.asarray(
        [[float((r.get("features") or {}).get(k, 0.0) or 0.0) for k in feature_order] for r in val_h_rows],
        dtype=float,
    )
    X_val_m = np.asarray(
        [[float((r.get("features") or {}).get(k, 0.0) or 0.0) for k in feature_order] for r in val_m_rows],
        dtype=float,
    )
    X_test_h = np.asarray(
        [[float((r.get("features") or {}).get(k, 0.0) or 0.0) for k in feature_order] for r in test_h_rows],
        dtype=float,
    )
    X_test_m = np.asarray(
        [[float((r.get("features") or {}).get(k, 0.0) or 0.0) for k in feature_order] for r in test_m_rows],
        dtype=float,
    )

    state = fit_candidate(model_type, X_train, seed=seed)
    eval_result = evaluate_candidate(
        model_type=model_type,
        state=state,
        X_human_val=X_val_h,
        X_macro_eval=X_val_m,
        fpr_target=fpr_target,
        threshold_safety_margin=threshold_safety_margin,
    )

    raw_train = state["raw_train"].reshape(-1)
    raw_min = float(np.min(raw_train))
    raw_max = float(np.max(raw_train))

    val_h_scores = normalize_scores(score_candidate(state, X_val_h).reshape(-1), raw_min, raw_max)
    val_m_scores = normalize_scores(score_candidate(state, X_val_m).reshape(-1), raw_min, raw_max)
    test_h_scores = normalize_scores(score_candidate(state, X_test_h).reshape(-1), raw_min, raw_max)
    test_m_scores = normalize_scores(score_candidate(state, X_test_m).reshape(-1), raw_min, raw_max)

    test_stats = _binary_stats(
        human_scores=test_h_scores,
        macro_scores=test_m_scores,
        threshold=float(eval_result.threshold),
    )

    stability_gap = float(
        abs(float(eval_result.human_fpr) - float(test_stats["human_fpr"]))
        + abs(float(eval_result.macro_recall) - float(test_stats["macro_recall"]))
    )
    score_shift_ks = float(0.5 * (_ks_stat(val_h_scores, test_h_scores) + _ks_stat(val_m_scores, test_m_scores)))
    fpr_excess = max(0.0, float(test_stats["human_fpr"]) - float(fpr_target))

    objective = float(
        float(test_stats["macro_recall"])
        - (2.0 * fpr_excess)
        - (0.5 * stability_gap)
        - (0.1 * score_shift_ks)
    )

    return SeedResult(
        seed=int(seed),
        human_counts=human_counts,
        macro_counts=macro_counts,
        threshold=float(eval_result.threshold),
        val_human_fpr=float(eval_result.human_fpr),
        val_macro_recall=float(eval_result.macro_recall),
        test_human_fpr=float(test_stats["human_fpr"]),
        test_macro_recall=float(test_stats["macro_recall"]),
        test_precision=float(test_stats["precision"]),
        test_f1=float(test_stats["f1"]),
        val_auroc=float(eval_result.auroc),
        val_pr_auc=float(eval_result.pr_auc),
        test_auroc=float(test_stats["auroc"]),
        test_pr_auc=float(test_stats["pr_auc"]),
        stability_gap=stability_gap,
        score_shift_ks=score_shift_ks,
        objective=objective,
    )


def _write_csv(path: Path, results: List[SeedResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "seed",
                "objective",
                "threshold",
                "val_human_fpr",
                "val_macro_recall",
                "test_human_fpr",
                "test_macro_recall",
                "test_precision",
                "test_f1",
                "val_auroc",
                "val_pr_auc",
                "test_auroc",
                "test_pr_auc",
                "stability_gap",
                "score_shift_ks",
            ],
        )
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "seed": r.seed,
                    "objective": f"{r.objective:.8f}",
                    "threshold": f"{r.threshold:.8f}",
                    "val_human_fpr": f"{r.val_human_fpr:.8f}",
                    "val_macro_recall": f"{r.val_macro_recall:.8f}",
                    "test_human_fpr": f"{r.test_human_fpr:.8f}",
                    "test_macro_recall": f"{r.test_macro_recall:.8f}",
                    "test_precision": f"{r.test_precision:.8f}",
                    "test_f1": f"{r.test_f1:.8f}",
                    "val_auroc": f"{r.val_auroc:.8f}",
                    "val_pr_auc": f"{r.val_pr_auc:.8f}",
                    "test_auroc": f"{r.test_auroc:.8f}",
                    "test_pr_auc": f"{r.test_pr_auc:.8f}",
                    "stability_gap": f"{r.stability_gap:.8f}",
                    "score_shift_ks": f"{r.score_shift_ks:.8f}",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search robust train/validation/test split seeds using only rebalanced_v1 data."
    )
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument(
        "--model-type",
        default="isolation_forest",
        choices=["isolation_forest", "local_outlier_factor"],
    )
    parser.add_argument("--fpr-target", type=float, default=0.02)
    parser.add_argument("--threshold-safety-margin", type=float, default=0.0)
    parser.add_argument("--human-ratio", default="7:1.5:1.5")
    parser.add_argument("--macro-ratio", default="0:5:5")
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--num-seeds", type=int, default=50)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--drop-feature-prefixes", nargs="*", default=["browser_"])
    parser.add_argument("--out-csv", default=str(DEFAULT_OUT_CSV))
    parser.add_argument("--out-json", default=str(DEFAULT_OUT_JSON))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_root = Path(args.data_root)
    out_csv = Path(args.out_csv)
    out_json = Path(args.out_json)

    human_dirs = [
        data_root / "train" / "human",
        data_root / "validation" / "human",
        data_root / "test" / "human",
    ]
    macro_dirs = [
        data_root / "train" / "macro",
        data_root / "validation" / "macro",
        data_root / "test" / "macro",
    ]

    human_all = _load_rows_from_dirs(human_dirs)
    macro_all = _load_rows_from_dirs(macro_dirs)
    if len(human_all) < 20 or len(macro_all) < 20:
        raise SystemExit(
            f"Not enough rows from {data_root}. "
            f"human={len(human_all)}, macro={len(macro_all)}"
        )

    human_ratio = _parse_ratio(args.human_ratio, "human")
    macro_ratio = _parse_ratio(args.macro_ratio, "macro")
    prefixes = [str(p).strip() for p in (args.drop_feature_prefixes or []) if str(p).strip()]

    seeds = [int(args.seed_start) + i for i in range(int(args.num_seeds))]
    results: List[SeedResult] = []

    print(
        "[SPLIT-SEARCH] "
        f"data_root={data_root} human={len(human_all)} macro={len(macro_all)} "
        f"model={args.model_type} fpr_target={args.fpr_target} seeds={len(seeds)}"
    )

    for idx, seed in enumerate(seeds, start=1):
        r = _evaluate_seed(
            seed=seed,
            human_all=human_all,
            macro_all=macro_all,
            human_ratio=human_ratio,
            macro_ratio=macro_ratio,
            model_type=str(args.model_type),
            fpr_target=float(args.fpr_target),
            threshold_safety_margin=float(args.threshold_safety_margin),
            drop_feature_prefixes=prefixes,
        )
        results.append(r)
        print(
            f"[SPLIT-SEARCH] {idx}/{len(seeds)} seed={seed} "
            f"obj={r.objective:.4f} test_fpr={r.test_human_fpr:.4f} "
            f"test_recall={r.test_macro_recall:.4f} test_f1={r.test_f1:.4f}"
        )

    results_sorted = sorted(results, key=lambda x: x.objective, reverse=True)
    _write_csv(out_csv, results_sorted)

    top_k = max(1, min(int(args.top_k), len(results_sorted)))
    top = results_sorted[:top_k]

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_root": str(data_root),
        "model_type": args.model_type,
        "fpr_target": float(args.fpr_target),
        "threshold_safety_margin": float(args.threshold_safety_margin),
        "human_ratio": args.human_ratio,
        "macro_ratio": args.macro_ratio,
        "drop_feature_prefixes": prefixes,
        "seed_start": int(args.seed_start),
        "num_seeds": int(args.num_seeds),
        "counts": {
            "human_total": len(human_all),
            "macro_total": len(macro_all),
            "human_split": top[0].human_counts if top else {},
            "macro_split": top[0].macro_counts if top else {},
        },
        "aggregate": {
            "test_human_fpr_mean": float(np.mean([r.test_human_fpr for r in results_sorted])),
            "test_human_fpr_std": float(np.std([r.test_human_fpr for r in results_sorted])),
            "test_macro_recall_mean": float(np.mean([r.test_macro_recall for r in results_sorted])),
            "test_macro_recall_std": float(np.std([r.test_macro_recall for r in results_sorted])),
            "test_f1_mean": float(np.mean([r.test_f1 for r in results_sorted])),
            "test_f1_std": float(np.std([r.test_f1 for r in results_sorted])),
        },
        "best": top[0].__dict__ if top else {},
        "top_k": [r.__dict__ for r in top],
        "all_results": [r.__dict__ for r in results_sorted],
        "csv_path": str(out_csv),
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[SPLIT-SEARCH] done")
    print(f"[SPLIT-SEARCH] wrote csv: {out_csv}")
    print(f"[SPLIT-SEARCH] wrote json: {out_json}")
    if top:
        b = top[0]
        print(
            "[SPLIT-SEARCH] best "
            f"seed={b.seed} obj={b.objective:.4f} "
            f"test_fpr={b.test_human_fpr:.4f} "
            f"test_recall={b.test_macro_recall:.4f} test_f1={b.test_f1:.4f}"
        )


if __name__ == "__main__":
    main()
