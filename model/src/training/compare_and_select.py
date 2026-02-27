import argparse
import csv
import json
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, roc_auc_score
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM
try:
    import torch
    from torch.utils.data import DataLoader, TensorDataset
except Exception:
    torch = None
    DataLoader = None
    TensorDataset = None

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from model.src.features.feature_pipeline import extract_browser_features, load_json
from model.src.data_prep.split_unified_raw import run_unified_split
from model.src.models.deep_svdd import build_deep_svdd_net, bundle_from_trained_net, score_with_runtime, torch_ready


MODEL_DIR = ROOT_DIR / "model"

DEFAULT_HUMAN_DIR = MODEL_DIR / "data" / "raw" / "train" / "human"
DEFAULT_MACRO_DIR = MODEL_DIR / "data" / "raw" / "validation" / "macro"
DEFAULT_VAL_HUMAN_DIR = MODEL_DIR / "data" / "raw" / "validation" / "human"
DEFAULT_VAL_MACRO_DIR = MODEL_DIR / "data" / "raw" / "validation" / "macro"
DEFAULT_TEST_HUMAN_DIR = MODEL_DIR / "data" / "raw" / "test" / "human"
DEFAULT_TEST_MACRO_DIR = MODEL_DIR / "data" / "raw" / "test" / "macro"
DEFAULT_UNIFIED_HUMAN_DIR = MODEL_DIR / "data" / "raw" / "human"
DEFAULT_UNIFIED_MACRO_DIR = MODEL_DIR / "data" / "raw" / "macro"
DEFAULT_AUTO_SPLIT_OUT_ROOT = MODEL_DIR / "data" / "raw" / "auto_split"
DEFAULT_SERVER_DIR = MODEL_DIR / "data" / "raw" / "server"
DEFAULT_PARAMS_OUT = MODEL_DIR / "artifacts" / "active" / "human_model_params.json"
DEFAULT_THRESHOLDS_OUT = MODEL_DIR / "artifacts" / "active" / "human_model_thresholds.json"
DEFAULT_BENCHMARK_OUT = MODEL_DIR / "reports" / "benchmark" / "model_benchmark_results.csv"
DEFAULT_SELECTION_OUT = MODEL_DIR / "reports" / "benchmark" / "model_selection.json"
DEFAULT_BENCHMARK_JSON_OUT = MODEL_DIR / "reports" / "benchmark" / "model_benchmark_results.json"


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def percentile_threshold(scores: np.ndarray, fpr: float) -> float:
    q = 100 * (1.0 - fpr)
    return float(np.percentile(scores, q))


def threshold_for_max_fpr(human_scores: np.ndarray, fpr_target: float) -> float:
    n = int(human_scores.shape[0])
    if n <= 0:
        return float("inf")
    target = max(0.0, min(1.0, fpr_target))
    allowed_fp = int(np.floor(target * n))
    # For small validation sets, floor(1% * n) can become 0 and over-constrain thresholding.
    # If a positive FPR target is requested, allow at least one FP slot.
    if target > 0.0 and allowed_fp == 0:
        allowed_fp = 1
    allowed_fp = min(allowed_fp, max(0, n - 1))
    sorted_scores = np.sort(human_scores)
    if allowed_fp <= 0:
        return float(sorted_scores[-1])
    idx = max(0, n - allowed_fp - 1)
    return float(sorted_scores[idx])


def normalize_scores(raw: np.ndarray, raw_min: float, raw_max: float) -> np.ndarray:
    if raw_max - raw_min <= 1e-12:
        return np.zeros_like(raw)
    scale = raw_max - raw_min
    # Keep lower bound at 0 for stability, but do not clip upper bound.
    # Upper clipping to 1.0 can collapse separability for some one-class models.
    return np.array([max(0.0, (float(v) - raw_min) / scale) for v in raw], dtype=float)


def safe_auc(is_macro_true: np.ndarray, y_score: np.ndarray) -> float:
    try:
        return float(roc_auc_score(is_macro_true, y_score))
    except Exception:
        return 0.0


def safe_pr_auc(is_macro_true: np.ndarray, y_score: np.ndarray) -> float:
    try:
        return float(average_precision_score(is_macro_true, y_score))
    except Exception:
        return 0.0


def summarize_distribution(scores: np.ndarray) -> Dict[str, float]:
    if scores.size == 0:
        return {
            "min": 0.0,
            "p25": 0.0,
            "p50": 0.0,
            "p75": 0.0,
            "p95": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "std": 0.0,
        }
    return {
        "min": float(np.min(scores)),
        "p25": float(np.percentile(scores, 25)),
        "p50": float(np.percentile(scores, 50)),
        "p75": float(np.percentile(scores, 75)),
        "p95": float(np.percentile(scores, 95)),
        "max": float(np.max(scores)),
        "mean": float(np.mean(scores)),
        "std": float(np.std(scores)),
    }


def _binary_stats(
    *,
    human_scores: np.ndarray,
    macro_scores: np.ndarray,
    threshold: float,
) -> Dict[str, Any]:
    is_macro_true = np.concatenate(
        [np.zeros(human_scores.shape[0], dtype=int), np.ones(macro_scores.shape[0], dtype=int)]
    )
    y_score = np.concatenate([human_scores, macro_scores])
    y_pred = (y_score > threshold).astype(int)

    tn = int(np.sum((is_macro_true == 0) & (y_pred == 0)))
    fp = int(np.sum((is_macro_true == 0) & (y_pred == 1)))
    fn = int(np.sum((is_macro_true == 1) & (y_pred == 0)))
    tp = int(np.sum((is_macro_true == 1) & (y_pred == 1)))

    human_fpr = fp / max(1, (fp + tn))
    macro_recall = tp / max(1, (tp + fn))
    precision, recall, f1, _ = precision_recall_fscore_support(
        is_macro_true, y_pred, average="binary", zero_division=0
    )
    return {
        "threshold": float(threshold),
        "human_fpr": float(human_fpr),
        "macro_recall": float(macro_recall),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "auroc": safe_auc(is_macro_true, y_score),
        "pr_auc": safe_pr_auc(is_macro_true, y_score),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def select_threshold_with_constraint(
    *,
    human_scores: np.ndarray,
    macro_scores: np.ndarray,
    fpr_target: float,
    safety_margin: float = 0.0,
) -> float:
    if human_scores.size == 0:
        return float("inf")
    if macro_scores.size == 0:
        return threshold_for_max_fpr(human_scores, fpr_target)

    all_scores = np.unique(np.concatenate([human_scores, macro_scores]))
    if all_scores.size == 0:
        return float("inf")
    span = float(np.max(all_scores) - np.min(all_scores))
    eps = max(1e-12, span * 1e-9)
    # Add a sentinel threshold above all scores so FPR=0 candidate always exists.
    candidates = np.concatenate([all_scores, [float(np.max(all_scores) + eps)]])

    target = max(0.0, min(1.0, fpr_target))
    feasible: List[Tuple[float, float, float, float]] = []
    # tuple: (recall, -fpr, precision, threshold)
    for t in candidates:
        stats = _binary_stats(human_scores=human_scores, macro_scores=macro_scores, threshold=float(t))
        fpr = float(stats["human_fpr"])
        if fpr <= target:
            feasible.append(
                (
                    float(stats["macro_recall"]),
                    -fpr,
                    float(stats["precision"]),
                    float(t),
                )
            )

    if feasible:
        # Max recall first, then lower FPR, then higher precision, then higher threshold (safer).
        best = max(feasible, key=lambda x: (x[0], x[1], x[2], x[3]))
        threshold = float(best[3])
    else:
        threshold = threshold_for_max_fpr(human_scores, target)

    # Optional safety margin: push threshold upward.
    if safety_margin > 0:
        p50 = float(np.percentile(human_scores, 50))
        p95 = float(np.percentile(human_scores, 95))
        band = max(1e-9, p95 - p50)
        threshold = float(threshold + safety_margin * band)

    return threshold


def select_threshold_from_validation_human(
    *,
    human_scores: np.ndarray,
    fpr_target: float,
    safety_margin: float = 0.0,
) -> float:
    if human_scores.size == 0:
        return float("inf")
    target = max(0.0, min(1.0, fpr_target))
    threshold = percentile_threshold(human_scores, target)

    # Optional safety margin: push threshold upward.
    if safety_margin > 0:
        p50 = float(np.percentile(human_scores, 50))
        p95 = float(np.percentile(human_scores, 95))
        band = max(1e-9, p95 - p50)
        threshold = float(threshold + safety_margin * band)

    return float(threshold)


def load_feature_rows(browser_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not browser_dir.exists():
        return rows
    for path in sorted(browser_dir.rglob("*.json")):
        try:
            browser_log = load_json(path)
        except Exception:
            continue
        flow_id = ((browser_log.get("metadata") or {}).get("flow_id")) or ""
        features = extract_browser_features(browser_log)
        row = {
            "path": str(path),
            "flow_id": flow_id,
            "features": features,
        }
        rows.append(row)
    return rows


def _has_json_files(root: Path) -> bool:
    if not root.exists():
        return False
    try:
        next(root.rglob("*.json"))
        return True
    except StopIteration:
        return False


def _macro_group_key(path: Path) -> str:
    try:
        payload = load_json(path)
        metadata = (payload.get("metadata") or {}) if isinstance(payload, dict) else {}
        bot_type = str(metadata.get("bot_type") or "").strip()
        return bot_type if bot_type else "__EMPTY__"
    except Exception:
        return "__PARSE_ERR__"


def _proportional_targets(group_counts: Dict[str, int], target_total: int) -> Dict[str, int]:
    keys = sorted(group_counts.keys())
    total = int(sum(group_counts.values()))
    if total <= 0 or target_total <= 0:
        return {k: 0 for k in keys}

    raw = {k: (float(group_counts[k]) / float(total)) * float(target_total) for k in keys}
    base = {k: int(raw[k]) for k in keys}
    remainder = int(target_total - sum(base.values()))
    order = sorted(keys, key=lambda k: (raw[k] - base[k], k), reverse=True)
    for i in range(remainder):
        base[order[i]] += 1
    return base


def _downsample_macro_eval_sets(auto_split_out_root: Path, target_per_split: int, seed: int) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "target_per_split": int(target_per_split),
        "applied": bool(target_per_split > 0),
        "splits": {},
    }
    if target_per_split <= 0:
        return result

    for split_idx, split in enumerate(["validation", "test"]):
        macro_dir = auto_split_out_root / split / "macro"
        files = sorted(macro_dir.glob("*.json")) if macro_dir.exists() else []
        before = len(files)
        split_info: Dict[str, Any] = {
            "before": before,
            "after": before,
            "removed": 0,
            "group_before": {},
            "group_after": {},
        }

        if before == 0:
            result["splits"][split] = split_info
            continue

        grouped: Dict[str, List[Path]] = defaultdict(list)
        for path in files:
            grouped[_macro_group_key(path)].append(path)
        split_info["group_before"] = {k: len(v) for k, v in sorted(grouped.items())}

        if before > target_per_split:
            targets = _proportional_targets(split_info["group_before"], target_per_split)
            keep_paths: set = set()
            for group_idx, group_name in enumerate(sorted(grouped.keys())):
                paths = grouped[group_name]
                rng = np.random.default_rng(seed + split_idx * 1000 + group_idx)
                idx = np.arange(len(paths))
                rng.shuffle(idx)
                k = int(targets.get(group_name, 0))
                for j in idx[:k]:
                    keep_paths.add(paths[int(j)])

            remove_paths = [p for p in files if p not in keep_paths]
            for p in remove_paths:
                try:
                    p.unlink()
                except Exception:
                    pass
            split_info["removed"] = len(remove_paths)

        after_files = sorted(macro_dir.glob("*.json")) if macro_dir.exists() else []
        after_grouped: Dict[str, int] = defaultdict(int)
        for path in after_files:
            after_grouped[_macro_group_key(path)] += 1

        split_info["after"] = len(after_files)
        split_info["group_after"] = dict(sorted(after_grouped.items()))
        result["splits"][split] = split_info

    return result


def _normalize_prefixes(prefixes: List[str]) -> List[str]:
    out: List[str] = []
    for p in prefixes:
        t = str(p or "").strip()
        if t:
            out.append(t)
    return out


def _drop_prefixed_features(
    rows: List[Dict[str, Any]],
    drop_prefixes: List[str],
) -> List[Dict[str, Any]]:
    prefixes = _normalize_prefixes(drop_prefixes)
    if not prefixes:
        return rows

    filtered_rows: List[Dict[str, Any]] = []
    for row in rows:
        feats = dict((row.get("features") or {}))
        filtered = {
            k: v
            for k, v in feats.items()
            if not any(str(k).startswith(prefix) for prefix in prefixes)
        }
        new_row = dict(row)
        new_row["features"] = filtered
        filtered_rows.append(new_row)
    return filtered_rows


def build_feature_order(rows: List[Dict[str, Any]]) -> List[str]:
    keys = set()
    for row in rows:
        keys.update((row.get("features") or {}).keys())
    return sorted(keys)


def rows_to_matrix(rows: List[Dict[str, Any]], feature_order: List[str]) -> np.ndarray:
    return np.array(
        [
            [float((row.get("features") or {}).get(name, 0.0) or 0.0) for name in feature_order]
            for row in rows
        ],
        dtype=float,
    )


def split_train_val(rows: List[Dict[str, Any]], val_ratio: float, seed: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if len(rows) < 10:
        raise SystemExit(f"Not enough human rows for split: {len(rows)}")
    rng = np.random.default_rng(seed)
    idx = np.arange(len(rows))
    rng.shuffle(idx)
    val_size = max(1, int(round(len(rows) * val_ratio)))
    val_idx = set(idx[:val_size].tolist())
    train_rows = [rows[i] for i in range(len(rows)) if i not in val_idx]
    val_rows = [rows[i] for i in range(len(rows)) if i in val_idx]
    return train_rows, val_rows


def fit_zscore(X_train: np.ndarray) -> Dict[str, Any]:
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std[std == 0] = 1.0
    raw_train = np.abs((X_train - mean) / std).mean(axis=1)
    return {
        "model_type": "zscore",
        "mean": mean,
        "std": std,
        "raw_train": raw_train,
    }


def score_zscore(state: Dict[str, Any], X: np.ndarray) -> np.ndarray:
    mean = state["mean"]
    std = state["std"].copy()
    std[std == 0] = 1.0
    return np.abs((X - mean) / std).mean(axis=1)


def fit_isolation_forest(X_train: np.ndarray, seed: int) -> Dict[str, Any]:
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X_train)
    model = IsolationForest(
        n_estimators=300,
        contamination="auto",
        random_state=seed,
    )
    model.fit(Xs)
    raw_train = -model.decision_function(Xs)
    return {
        "model_type": "isolation_forest",
        "scaler": scaler,
        "model": model,
        "raw_train": raw_train,
    }


def score_isolation_forest(state: Dict[str, Any], X: np.ndarray) -> np.ndarray:
    scaler = state["scaler"]
    model = state["model"]
    Xs = scaler.transform(X)
    return -model.decision_function(Xs)


def fit_oneclass_svm(X_train: np.ndarray) -> Dict[str, Any]:
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X_train)
    model = OneClassSVM(kernel="rbf", gamma="scale", nu=0.05)
    model.fit(Xs)
    raw_train = -model.decision_function(Xs).reshape(-1)
    return {
        "model_type": "oneclass_svm",
        "scaler": scaler,
        "model": model,
        "raw_train": raw_train,
    }


def score_oneclass_svm(state: Dict[str, Any], X: np.ndarray) -> np.ndarray:
    scaler = state["scaler"]
    model = state["model"]
    Xs = scaler.transform(X)
    return -model.decision_function(Xs).reshape(-1)


def fit_local_outlier_factor(X_train: np.ndarray) -> Dict[str, Any]:
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X_train)
    model = LocalOutlierFactor(
        n_neighbors=35,
        contamination="auto",
        novelty=True,
    )
    model.fit(Xs)
    raw_train = -model.decision_function(Xs).reshape(-1)
    return {
        "model_type": "local_outlier_factor",
        "scaler": scaler,
        "model": model,
        "raw_train": raw_train,
    }


def score_local_outlier_factor(state: Dict[str, Any], X: np.ndarray) -> np.ndarray:
    scaler = state["scaler"]
    model = state["model"]
    Xs = scaler.transform(X)
    return -model.decision_function(Xs).reshape(-1)


def fit_deep_svdd(X_train: np.ndarray, seed: int) -> Dict[str, Any]:
    if not torch_ready() or torch is None or DataLoader is None or TensorDataset is None:
        raise RuntimeError("deep_svdd requires torch. Please install PyTorch (CPU or GPU).")

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X_train).astype(np.float32)

    torch.manual_seed(seed)
    np.random.seed(seed)

    n_samples, input_dim = Xs.shape
    hidden_dim = max(24, min(128, input_dim * 2))
    latent_dim = max(8, min(32, max(8, input_dim // 2)))

    net = build_deep_svdd_net(input_dim=input_dim, hidden_dim=hidden_dim, latent_dim=latent_dim)
    net.train()

    x_tensor = torch.from_numpy(Xs)
    with torch.no_grad():
        init_embed = net(x_tensor)
        center = init_embed.mean(dim=0)
        eps = 1e-3
        center = torch.where(center.abs() < eps, torch.full_like(center, eps), center)

    batch_size = max(16, min(128, n_samples))
    loader = DataLoader(TensorDataset(x_tensor), batch_size=batch_size, shuffle=True, drop_last=False)
    optimizer = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-6)

    epochs = 60
    for _ in range(epochs):
        for (xb,) in loader:
            optimizer.zero_grad(set_to_none=True)
            z = net(xb)
            loss = ((z - center) ** 2).sum(dim=1).mean()
            loss.backward()
            optimizer.step()

    net.eval()
    with torch.no_grad():
        train_embed = net(x_tensor)
        raw_train = ((train_embed - center) ** 2).sum(dim=1).cpu().numpy()

    center_np = center.detach().cpu().numpy().astype(np.float32)
    model_bundle = bundle_from_trained_net(
        net=net.cpu(),
        center=center_np,
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        latent_dim=latent_dim,
    )
    return {
        "model_type": "deep_svdd",
        "scaler": scaler,
        "model": model_bundle,
        "runtime_net": net.cpu(),
        "runtime_center": center_np,
        "raw_train": raw_train,
    }


def score_deep_svdd(state: Dict[str, Any], X: np.ndarray) -> np.ndarray:
    if not torch_ready() or torch is None:
        raise RuntimeError("deep_svdd scoring requires torch.")
    scaler = state["scaler"]
    Xs = scaler.transform(X).astype(np.float32)
    net = state.get("runtime_net")
    center = state.get("runtime_center")
    if net is None or center is None:
        from model.src.models.deep_svdd import load_runtime_from_bundle

        net, center = load_runtime_from_bundle(state["model"])
        state["runtime_net"] = net
        state["runtime_center"] = center
    return score_with_runtime(net, np.array(center, dtype=np.float32), Xs)


def fit_candidate(model_type: str, X_train: np.ndarray, seed: int) -> Dict[str, Any]:
    if model_type == "zscore":
        return fit_zscore(X_train)
    if model_type == "isolation_forest":
        return fit_isolation_forest(X_train, seed=seed)
    if model_type == "oneclass_svm":
        return fit_oneclass_svm(X_train)
    if model_type == "local_outlier_factor":
        return fit_local_outlier_factor(X_train)
    if model_type == "deep_svdd":
        return fit_deep_svdd(X_train, seed=seed)
    raise ValueError(f"Unsupported model_type: {model_type}")


def score_candidate(state: Dict[str, Any], X: np.ndarray) -> np.ndarray:
    model_type = state["model_type"]
    if model_type == "zscore":
        return score_zscore(state, X)
    if model_type == "isolation_forest":
        return score_isolation_forest(state, X)
    if model_type == "oneclass_svm":
        return score_oneclass_svm(state, X)
    if model_type == "local_outlier_factor":
        return score_local_outlier_factor(state, X)
    if model_type == "deep_svdd":
        return score_deep_svdd(state, X)
    raise ValueError(f"Unsupported model_type: {model_type}")


@dataclass
class EvalResult:
    model_type: str
    threshold: float
    human_fpr: float
    macro_recall: float
    precision: float
    recall: float
    f1: float
    auroc: float
    pr_auc: float
    tp: int
    tn: int
    fp: int
    fn: int
    human_score_dist: Dict[str, float]
    macro_score_dist: Dict[str, float]


def evaluate_candidate(
    model_type: str,
    state: Dict[str, Any],
    X_human_val: np.ndarray,
    X_macro_eval: np.ndarray,
    fpr_target: float,
    threshold_safety_margin: float = 0.0,
    threshold_policy: str = "validation_human_percentile",
) -> EvalResult:
    raw_train = state["raw_train"].reshape(-1)
    raw_min = float(np.min(raw_train))
    raw_max = float(np.max(raw_train))

    human_scores = normalize_scores(score_candidate(state, X_human_val).reshape(-1), raw_min, raw_max)
    macro_scores = normalize_scores(score_candidate(state, X_macro_eval).reshape(-1), raw_min, raw_max)

    if threshold_policy == "validation_human_percentile":
        # No leakage: decide threshold using validation human only.
        threshold = select_threshold_from_validation_human(
            human_scores=human_scores,
            fpr_target=fpr_target,
            safety_margin=threshold_safety_margin,
        )
    elif threshold_policy == "validation_macro_constrained":
        threshold = select_threshold_with_constraint(
            human_scores=human_scores,
            macro_scores=macro_scores,
            fpr_target=fpr_target,
            safety_margin=threshold_safety_margin,
        )
    else:
        raise ValueError(f"Unsupported threshold_policy: {threshold_policy}")
    stats = _binary_stats(human_scores=human_scores, macro_scores=macro_scores, threshold=threshold)

    return EvalResult(
        model_type=model_type,
        threshold=float(threshold),
        human_fpr=float(stats["human_fpr"]),
        macro_recall=float(stats["macro_recall"]),
        precision=float(stats["precision"]),
        recall=float(stats["recall"]),
        f1=float(stats["f1"]),
        auroc=float(stats["auroc"]),
        pr_auc=float(stats["pr_auc"]),
        tp=int(stats["tp"]),
        tn=int(stats["tn"]),
        fp=int(stats["fp"]),
        fn=int(stats["fn"]),
        human_score_dist=summarize_distribution(human_scores),
        macro_score_dist=summarize_distribution(macro_scores),
    )


def pick_best(results: List[EvalResult], fpr_target: float) -> EvalResult:
    compliant = [r for r in results if r.human_fpr <= fpr_target]
    if compliant:
        return sorted(
            compliant,
            key=lambda r: (r.macro_recall, r.pr_auc, r.auroc, -r.human_fpr),
            reverse=True,
        )[0]

    return sorted(
        results,
        key=lambda r: (r.macro_recall - max(0.0, r.human_fpr - fpr_target), r.pr_auc, -r.human_fpr),
        reverse=True,
    )[0]


def save_benchmark_csv(path: Path, results: List[EvalResult]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "model_type",
                "threshold",
                "human_fpr",
                "macro_recall",
                "precision",
                "recall",
                "f1",
                "auroc",
                "pr_auc",
                "tp",
                "tn",
                "fp",
                "fn",
                "human_score_mean",
                "human_score_std",
                "human_score_p50",
                "human_score_p95",
                "macro_score_mean",
                "macro_score_std",
                "macro_score_p50",
                "macro_score_p95",
            ],
        )
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "model_type": r.model_type,
                    "threshold": f"{r.threshold:.8f}",
                    "human_fpr": f"{r.human_fpr:.8f}",
                    "macro_recall": f"{r.macro_recall:.8f}",
                    "precision": f"{r.precision:.8f}",
                    "recall": f"{r.recall:.8f}",
                    "f1": f"{r.f1:.8f}",
                    "auroc": f"{r.auroc:.8f}",
                    "pr_auc": f"{r.pr_auc:.8f}",
                    "tp": r.tp,
                    "tn": r.tn,
                    "fp": r.fp,
                    "fn": r.fn,
                    "human_score_mean": f"{r.human_score_dist.get('mean', 0.0):.8f}",
                    "human_score_std": f"{r.human_score_dist.get('std', 0.0):.8f}",
                    "human_score_p50": f"{r.human_score_dist.get('p50', 0.0):.8f}",
                    "human_score_p95": f"{r.human_score_dist.get('p95', 0.0):.8f}",
                    "macro_score_mean": f"{r.macro_score_dist.get('mean', 0.0):.8f}",
                    "macro_score_std": f"{r.macro_score_dist.get('std', 0.0):.8f}",
                    "macro_score_p50": f"{r.macro_score_dist.get('p50', 0.0):.8f}",
                    "macro_score_p95": f"{r.macro_score_dist.get('p95', 0.0):.8f}",
                }
            )


def build_deploy_params(
    model_type: str,
    state: Dict[str, Any],
    feature_order: List[str],
    human_dir: Path,
    params_out: Path,
    drop_feature_prefixes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    raw_train = state["raw_train"].reshape(-1)
    raw_min = float(np.min(raw_train))
    raw_max = float(np.max(raw_train))

    params: Dict[str, Any] = {
        "version": "human_only_selected_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_type": model_type,
        "feature_source": "browser_only",
        "feature_order": feature_order,
        "drop_feature_prefixes": _normalize_prefixes(drop_feature_prefixes or []),
        "raw_min": raw_min,
        "raw_max": raw_max,
        "browser_dir": str(human_dir),
    }

    if model_type == "zscore":
        params["mean"] = state["mean"].tolist()
        params["std"] = state["std"].tolist()
        return params

    artifact_path = params_out.parent / f"human_model_{model_type}.joblib"
    joblib.dump(
        {
            "model_type": model_type,
            "model": state["model"],
            "scaler": state["scaler"],
            "feature_order": feature_order,
        },
        artifact_path,
    )
    params["model_artifact"] = str(artifact_path)
    return params


def build_thresholds_from_human_scores(human_scores: np.ndarray) -> Dict[str, float]:
    thresholds = {
        "fpr_0_5pct": percentile_threshold(human_scores, 0.005),
        "fpr_1pct": percentile_threshold(human_scores, 0.01),
        "fpr_2pct": percentile_threshold(human_scores, 0.02),
        "fpr_5pct": percentile_threshold(human_scores, 0.05),
    }
    thresholds["allow"] = thresholds["fpr_1pct"]
    thresholds["challenge"] = thresholds["fpr_0_5pct"]
    return {k: float(v) for k, v in thresholds.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare anomaly models and select best one for deployment.")
    parser.add_argument("--human-dir", default=str(DEFAULT_HUMAN_DIR), help="Train human browser log dir")
    parser.add_argument("--macro-dir", default=str(DEFAULT_MACRO_DIR), help="Legacy macro eval dir (fallback mode)")
    parser.add_argument("--val-human-dir", default=str(DEFAULT_VAL_HUMAN_DIR), help="Validation human dir")
    parser.add_argument("--val-macro-dir", default=str(DEFAULT_VAL_MACRO_DIR), help="Validation macro dir")
    parser.add_argument("--test-human-dir", default=str(DEFAULT_TEST_HUMAN_DIR), help="Test human dir")
    parser.add_argument("--test-macro-dir", default=str(DEFAULT_TEST_MACRO_DIR), help="Test macro dir")
    parser.add_argument(
        "--disable-auto-split-unified",
        action="store_true",
        help=(
            "Disable automatic unified split. "
            "By default, if model/data/raw/human and model/data/raw/macro exist, "
            "they are split and used for train/validation/test."
        ),
    )
    parser.add_argument("--unified-human-dir", default=str(DEFAULT_UNIFIED_HUMAN_DIR), help="Unified human raw dir")
    parser.add_argument("--unified-macro-dir", default=str(DEFAULT_UNIFIED_MACRO_DIR), help="Unified macro raw dir")
    parser.add_argument(
        "--auto-split-out-root",
        default=str(DEFAULT_AUTO_SPLIT_OUT_ROOT),
        help="Output root for auto split dataset",
    )
    parser.add_argument(
        "--auto-split-human-ratio",
        default="7:1.5:1.5",
        help="Human split ratio train:validation:test",
    )
    parser.add_argument(
        "--auto-split-macro-ratio",
        default="0:5:5",
        help="Macro split ratio train:validation:test",
    )
    parser.add_argument(
        "--auto-split-macro-eval-count",
        type=int,
        default=115,
        help=(
            "If > 0, downsample auto-split macro validation/test each to this fixed count "
            "after split generation."
        ),
    )
    parser.add_argument(
        "--auto-split-human-stratify-keys",
        default="metadata.user_email",
        help=(
            "Comma-separated keys for human stratified split "
            "(e.g. metadata.user_email,filename.date). "
            "Empty string disables stratification."
        ),
    )
    parser.add_argument(
        "--auto-split-macro-stratify-keys",
        default="metadata.bot_type",
        help=(
            "Comma-separated keys for macro stratified split "
            "(e.g. metadata.bot_type,filename.date). "
            "Empty string disables stratification."
        ),
    )
    parser.add_argument(
        "--server-dir",
        default=str(DEFAULT_SERVER_DIR),
        help="Server log dir (deprecated, ignored in browser-only model features)",
    )
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Validation ratio for human split")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--fpr-target", type=float, default=0.01, help="Target FPR for thresholding")
    parser.add_argument(
        "--threshold-policy",
        default="validation_human_percentile",
        choices=["validation_human_percentile", "validation_macro_constrained"],
        help=(
            "Threshold selection policy. "
            "'validation_human_percentile' uses validation human only (recommended, no test leakage). "
            "'validation_macro_constrained' uses validation human+macro optimization."
        ),
    )
    parser.add_argument(
        "--threshold-safety-margin",
        type=float,
        default=0.0,
        help="Optional safety margin multiplier for threshold scan (0 disables)",
    )
    parser.add_argument(
        "--candidates",
        nargs="+",
        default=["zscore", "isolation_forest", "oneclass_svm", "local_outlier_factor", "deep_svdd"],
        help="Candidate model types",
    )
    parser.add_argument("--params-out", default=str(DEFAULT_PARAMS_OUT), help="Selected model params output json")
    parser.add_argument(
        "--thresholds-out",
        default=str(DEFAULT_THRESHOLDS_OUT),
        help="Selected model threshold output json",
    )
    parser.add_argument(
        "--benchmark-out",
        default=str(DEFAULT_BENCHMARK_OUT),
        help="Benchmark result csv output",
    )
    parser.add_argument(
        "--selection-out",
        default=str(DEFAULT_SELECTION_OUT),
        help="Selected model summary json output",
    )
    parser.add_argument(
        "--benchmark-json-out",
        default=str(DEFAULT_BENCHMARK_JSON_OUT),
        help="Benchmark result json output",
    )
    parser.add_argument(
        "--drop-feature-prefixes",
        nargs="*",
        default=[],
        help="Drop any feature whose name starts with one of these prefixes (e.g. browser_)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    human_dir = Path(args.human_dir)
    macro_dir = Path(args.macro_dir)
    val_human_dir = Path(args.val_human_dir) if str(args.val_human_dir).strip() else Path("")
    val_macro_dir = Path(args.val_macro_dir) if str(args.val_macro_dir).strip() else Path("")
    test_human_dir = Path(args.test_human_dir) if str(args.test_human_dir).strip() else Path("")
    test_macro_dir = Path(args.test_macro_dir) if str(args.test_macro_dir).strip() else Path("")
    params_out = Path(args.params_out)
    thresholds_out = Path(args.thresholds_out)
    benchmark_out = Path(args.benchmark_out)
    selection_out = Path(args.selection_out)
    benchmark_json_out = Path(args.benchmark_json_out)
    drop_feature_prefixes = _normalize_prefixes(list(args.drop_feature_prefixes or []))
    unified_human_dir = Path(args.unified_human_dir)
    unified_macro_dir = Path(args.unified_macro_dir)
    auto_split_out_root = Path(args.auto_split_out_root)

    auto_split_used = False
    auto_split_manifest: Dict[str, Any] = {}
    auto_split_manifest_path = ""
    auto_split_macro_downsample: Dict[str, Any] = {}
    if not bool(args.disable_auto_split_unified):
        if _has_json_files(unified_human_dir) and _has_json_files(unified_macro_dir):
            auto_split_manifest = run_unified_split(
                human_dir=unified_human_dir,
                macro_dir=unified_macro_dir,
                out_root=auto_split_out_root,
                human_ratio=str(args.auto_split_human_ratio),
                macro_ratio=str(args.auto_split_macro_ratio),
                seed=int(args.seed),
                human_stratify_keys=str(args.auto_split_human_stratify_keys),
                macro_stratify_keys=str(args.auto_split_macro_stratify_keys),
                overwrite=True,
                dry_run=False,
            )

            auto_split_macro_downsample = _downsample_macro_eval_sets(
                auto_split_out_root,
                target_per_split=int(args.auto_split_macro_eval_count),
                seed=int(args.seed),
            )
            auto_split_manifest["macro_eval_downsample"] = auto_split_macro_downsample

            manifest_path = auto_split_out_root / "split_manifest.json"
            if manifest_path.exists():
                try:
                    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
                    on_disk["macro_eval_downsample"] = auto_split_macro_downsample
                    manifest_path.write_text(json.dumps(on_disk, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass

            auto_split_manifest_path = str((auto_split_out_root / "split_manifest.json").resolve())
            auto_split_used = True

            human_dir = auto_split_out_root / "train" / "human"
            val_human_dir = auto_split_out_root / "validation" / "human"
            val_macro_dir = auto_split_out_root / "validation" / "macro"
            test_human_dir = auto_split_out_root / "test" / "human"
            test_macro_dir = auto_split_out_root / "test" / "macro"
            macro_dir = val_macro_dir
            print(
                "[AUTO-SPLIT] "
                f"used unified dirs -> {auto_split_out_root} "
                f"human={auto_split_manifest.get('counts', {}).get('human', {})} "
                f"macro={auto_split_manifest.get('counts', {}).get('macro', {})} "
                f"macro_eval={auto_split_macro_downsample.get('splits', {})}"
            )

    params_out.parent.mkdir(parents=True, exist_ok=True)
    thresholds_out.parent.mkdir(parents=True, exist_ok=True)
    benchmark_out.parent.mkdir(parents=True, exist_ok=True)
    selection_out.parent.mkdir(parents=True, exist_ok=True)
    benchmark_json_out.parent.mkdir(parents=True, exist_ok=True)

    # Train: always human-only.
    human_rows_all = load_feature_rows(human_dir)
    use_explicit_validation = bool(val_human_dir and val_macro_dir and val_human_dir.exists() and val_macro_dir.exists())
    use_test_set = bool(test_human_dir and test_macro_dir and test_human_dir.exists() and test_macro_dir.exists())

    if use_explicit_validation:
        human_train_rows = human_rows_all
        human_val_rows = load_feature_rows(val_human_dir)
        macro_rows = load_feature_rows(val_macro_dir)
    else:
        macro_rows = load_feature_rows(macro_dir)
        if len(human_rows_all) < 10:
            raise SystemExit(f"Not enough human rows: {len(human_rows_all)}")
        human_train_rows, human_val_rows = split_train_val(human_rows_all, val_ratio=args.val_ratio, seed=args.seed)

    if len(human_rows_all) < 10:
        raise SystemExit(f"Not enough human rows: {len(human_rows_all)}")
    if len(human_val_rows) < 5:
        raise SystemExit(f"Not enough validation human rows: {len(human_val_rows)}")
    if len(macro_rows) < 5:
        raise SystemExit(f"Not enough macro rows: {len(macro_rows)}")

    test_human_rows: List[Dict[str, Any]] = []
    test_macro_rows: List[Dict[str, Any]] = []
    if use_test_set:
        test_human_rows = load_feature_rows(test_human_dir)
        test_macro_rows = load_feature_rows(test_macro_dir)
        if len(test_human_rows) < 5 or len(test_macro_rows) < 5:
            use_test_set = False

    # Apply identical feature filtering across train/val/test.
    human_rows_all = _drop_prefixed_features(human_rows_all, drop_feature_prefixes)
    human_train_rows = _drop_prefixed_features(human_train_rows, drop_feature_prefixes)
    human_val_rows = _drop_prefixed_features(human_val_rows, drop_feature_prefixes)
    macro_rows = _drop_prefixed_features(macro_rows, drop_feature_prefixes)
    test_human_rows = _drop_prefixed_features(test_human_rows, drop_feature_prefixes)
    test_macro_rows = _drop_prefixed_features(test_macro_rows, drop_feature_prefixes)

    feature_order = build_feature_order(human_rows_all + human_val_rows + macro_rows + test_human_rows + test_macro_rows)
    if not feature_order:
        raise SystemExit(
            "No features left after applying feature filters. "
            f"drop_feature_prefixes={drop_feature_prefixes}"
        )

    X_human_train = rows_to_matrix(human_train_rows, feature_order)
    X_human_val = rows_to_matrix(human_val_rows, feature_order)
    X_macro_eval = rows_to_matrix(macro_rows, feature_order)
    X_test_human = rows_to_matrix(test_human_rows, feature_order) if use_test_set else np.zeros((0, len(feature_order)))
    X_test_macro = rows_to_matrix(test_macro_rows, feature_order) if use_test_set else np.zeros((0, len(feature_order)))

    results: List[EvalResult] = []
    fitted_states: Dict[str, Dict[str, Any]] = {}
    test_metrics_by_model: Dict[str, Dict[str, Any]] = {}
    for model_type in args.candidates:
        state = fit_candidate(model_type, X_human_train, seed=args.seed)
        fitted_states[model_type] = state
        result = evaluate_candidate(
            model_type=model_type,
            state=state,
            X_human_val=X_human_val,
            X_macro_eval=X_macro_eval,
            fpr_target=args.fpr_target,
            threshold_safety_margin=float(args.threshold_safety_margin),
            threshold_policy=str(args.threshold_policy),
        )
        results.append(result)
        if use_test_set:
            raw_train = state["raw_train"].reshape(-1)
            raw_min = float(np.min(raw_train))
            raw_max = float(np.max(raw_train))
            test_h_scores = normalize_scores(score_candidate(state, X_test_human).reshape(-1), raw_min, raw_max)
            test_m_scores = normalize_scores(score_candidate(state, X_test_macro).reshape(-1), raw_min, raw_max)
            test_stats = _binary_stats(
                human_scores=test_h_scores,
                macro_scores=test_m_scores,
                threshold=result.threshold,
            )
            test_stats["human_score_dist"] = summarize_distribution(test_h_scores)
            test_stats["macro_score_dist"] = summarize_distribution(test_m_scores)
            test_metrics_by_model[model_type] = test_stats

        print(
            "[EVAL] "
            f"model={result.model_type} "
            f"ROC-AUC={result.auroc:.4f} "
            f"PR-AUC={result.pr_auc:.4f} "
            f"FPR={result.human_fpr:.4f} "
            f"threshold={result.threshold:.4f}"
        )
        print(
            "[EVAL] "
            f"model={result.model_type} "
            "Score Distribution "
            f"human(min/p50/p95/max)={result.human_score_dist['min']:.4f}/"
            f"{result.human_score_dist['p50']:.4f}/"
            f"{result.human_score_dist['p95']:.4f}/"
            f"{result.human_score_dist['max']:.4f} "
            f"macro(min/p50/p95/max)={result.macro_score_dist['min']:.4f}/"
            f"{result.macro_score_dist['p50']:.4f}/"
            f"{result.macro_score_dist['p95']:.4f}/"
            f"{result.macro_score_dist['max']:.4f}"
        )
        if use_test_set and model_type in test_metrics_by_model:
            tm = test_metrics_by_model[model_type]
            print(
                "[TEST] "
                f"model={model_type} "
                f"ROC-AUC={tm['auroc']:.4f} "
                f"PR-AUC={tm['pr_auc']:.4f} "
                f"FPR={tm['human_fpr']:.4f} "
                f"Recall={tm['macro_recall']:.4f}"
            )

    best = pick_best(results, fpr_target=args.fpr_target)
    save_benchmark_csv(benchmark_out, results)

    X_human_full = rows_to_matrix(human_rows_all, feature_order)
    best_full_state = fit_candidate(best.model_type, X_human_full, seed=args.seed)
    raw_human_full = best_full_state["raw_train"].reshape(-1)
    full_min = float(np.min(raw_human_full))
    full_max = float(np.max(raw_human_full))
    human_full_scores = normalize_scores(raw_human_full, full_min, full_max)

    deploy_params = build_deploy_params(
        model_type=best.model_type,
        state=best_full_state,
        feature_order=feature_order,
        human_dir=human_dir,
        params_out=params_out,
        drop_feature_prefixes=drop_feature_prefixes,
    )
    deploy_params["raw_min"] = full_min
    deploy_params["raw_max"] = full_max
    deploy_thresholds = build_thresholds_from_human_scores(human_full_scores)

    params_out.write_text(json.dumps(deploy_params, ensure_ascii=False, indent=2), encoding="utf-8")
    thresholds_out.write_text(json.dumps(deploy_thresholds, ensure_ascii=False, indent=2), encoding="utf-8")

    selection = {
        "selected_model": best.model_type,
        "fpr_target": args.fpr_target,
        "threshold_policy": str(args.threshold_policy),
        "threshold_safety_margin": float(args.threshold_safety_margin),
        "split_mode": "explicit_train_val_test" if use_explicit_validation else "train_split_internal_validation",
        "human_total": len(human_rows_all),
        "human_train": len(human_train_rows),
        "human_val": len(human_val_rows),
        "macro_eval": len(macro_rows),
        "test_human": len(test_human_rows),
        "test_macro": len(test_macro_rows),
        "best_metrics": {
            "threshold": best.threshold,
            "human_fpr": best.human_fpr,
            "macro_recall": best.macro_recall,
            "precision": best.precision,
            "recall": best.recall,
            "f1": best.f1,
            "auroc": best.auroc,
            "pr_auc": best.pr_auc,
            "score_distribution": {
                "human": best.human_score_dist,
                "macro": best.macro_score_dist,
            },
            "tp": best.tp,
            "tn": best.tn,
            "fp": best.fp,
            "fn": best.fn,
        },
        "best_test_metrics": test_metrics_by_model.get(best.model_type, {}),
        "candidates": [r.model_type for r in results],
        "drop_feature_prefixes": drop_feature_prefixes,
        "auto_split_unified": {
            "used": auto_split_used,
            "unified_human_dir": str(unified_human_dir),
            "unified_macro_dir": str(unified_macro_dir),
            "output_root": str(auto_split_out_root),
            "manifest_path": auto_split_manifest_path,
            "counts": auto_split_manifest.get("counts", {}),
            "ratios": auto_split_manifest.get("ratio", {}),
            "macro_eval_downsample": auto_split_manifest.get("macro_eval_downsample", {}),
        },
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    selection_out.write_text(json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8")

    benchmark_json = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "fpr_target": float(args.fpr_target),
        "threshold_policy": str(args.threshold_policy),
        "threshold_safety_margin": float(args.threshold_safety_margin),
        "split_mode": "explicit_train_val_test" if use_explicit_validation else "train_split_internal_validation",
        "counts": {
            "train_human": len(human_train_rows),
            "val_human": len(human_val_rows),
            "val_macro": len(macro_rows),
            "test_human": len(test_human_rows),
            "test_macro": len(test_macro_rows),
        },
        "auto_split_unified": {
            "used": auto_split_used,
            "unified_human_dir": str(unified_human_dir),
            "unified_macro_dir": str(unified_macro_dir),
            "output_root": str(auto_split_out_root),
            "manifest_path": auto_split_manifest_path,
            "counts": auto_split_manifest.get("counts", {}),
            "ratios": auto_split_manifest.get("ratio", {}),
            "macro_eval_downsample": auto_split_manifest.get("macro_eval_downsample", {}),
        },
        "drop_feature_prefixes": drop_feature_prefixes,
        "models": [
            {
                "model_type": r.model_type,
                "validation": {
                    "threshold": r.threshold,
                    "human_fpr": r.human_fpr,
                    "macro_recall": r.macro_recall,
                    "precision": r.precision,
                    "recall": r.recall,
                    "f1": r.f1,
                    "auroc": r.auroc,
                    "pr_auc": r.pr_auc,
                    "tp": r.tp,
                    "tn": r.tn,
                    "fp": r.fp,
                    "fn": r.fn,
                    "score_distribution": {
                        "human": r.human_score_dist,
                        "macro": r.macro_score_dist,
                    },
                },
                "test": test_metrics_by_model.get(r.model_type, {}),
            }
            for r in results
        ],
        "selected_model": best.model_type,
    }
    benchmark_json_out.write_text(json.dumps(benchmark_json, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_path = params_out.parent / "model_manifest.json"
    manifest = {
        "active": True,
        "selected_model": best.model_type,
        "params_path": str(params_out.resolve()),
        "thresholds_path": str(thresholds_out.resolve()),
        "selection_report_path": str(selection_out.resolve()),
        "benchmark_report_path": str(benchmark_out.resolve()),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"_{best.model_type}"
    run_dir = MODEL_DIR / "artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    to_copy = [
        params_out,
        thresholds_out,
        benchmark_out,
        benchmark_json_out,
        selection_out,
        manifest_path,
    ]
    artifact_raw = str(deploy_params.get("model_artifact", "")).strip()
    if artifact_raw:
        artifact_path = Path(artifact_raw)
        if artifact_path.exists() and artifact_path.is_file():
            to_copy.append(artifact_path)

    for src in to_copy:
        if src.exists():
            shutil.copy2(src, run_dir / src.name)

    print(
        f"split_mode={'explicit_train_val_test' if use_explicit_validation else 'train_split_internal_validation'} "
        f"train_human={len(human_train_rows)} val_human={len(human_val_rows)} val_macro={len(macro_rows)} "
        f"test_human={len(test_human_rows)} test_macro={len(test_macro_rows)}"
    )
    if drop_feature_prefixes:
        print(f"dropped_feature_prefixes={','.join(drop_feature_prefixes)}")
    print(f"feature_count={len(feature_order)}")
    print(f"selected_model={best.model_type}")
    print(
        "[BEST] "
        f"ROC-AUC={best.auroc:.4f} PR-AUC={best.pr_auc:.4f} "
        f"FPR={best.human_fpr:.4f} threshold={best.threshold:.4f}"
    )
    print(f"threshold_policy={args.threshold_policy}")
    print(
        "[BEST] Score Distribution "
        f"human(min/p50/p95/max)={best.human_score_dist['min']:.4f}/"
        f"{best.human_score_dist['p50']:.4f}/"
        f"{best.human_score_dist['p95']:.4f}/"
        f"{best.human_score_dist['max']:.4f} "
        f"macro(min/p50/p95/max)={best.macro_score_dist['min']:.4f}/"
        f"{best.macro_score_dist['p50']:.4f}/"
        f"{best.macro_score_dist['p95']:.4f}/"
        f"{best.macro_score_dist['max']:.4f}"
    )
    print(f"Wrote: {benchmark_out}")
    print(f"Wrote: {benchmark_json_out}")
    print(f"Wrote: {selection_out}")
    print(f"Wrote: {params_out}")
    print(f"Wrote: {thresholds_out}")
    print(f"Wrote: {manifest_path}")
    print(f"Archived run: {run_dir}")


if __name__ == "__main__":
    main()
