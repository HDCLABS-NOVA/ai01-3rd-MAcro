import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from model.src.features.feature_pipeline import (
    extract_browser_features,
    load_json,
)


MODEL_DIR = ROOT_DIR / "model"

BROWSER_DIR = MODEL_DIR / "data" / "raw" / "train" / "human"
OUT_PARAMS = MODEL_DIR / "artifacts" / "active" / "human_model_params.json"
OUT_THRESHOLDS = MODEL_DIR / "artifacts" / "active" / "human_model_thresholds.json"
OUT_SCORES = MODEL_DIR / "reports" / "scoring" / "human_only_scores.csv"


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def percentile_threshold(scores: np.ndarray, fpr: float) -> float:
    q = 100 * (1.0 - fpr)
    return float(np.percentile(scores, q))


def build_rows() -> List[Dict[str, Any]]:
    if not BROWSER_DIR.exists():
        raise SystemExit(f"Browser log dir not found: {BROWSER_DIR}")

    rows: List[Dict[str, Any]] = []

    for browser_path in sorted(BROWSER_DIR.rglob("*.json")):
        try:
            browser_log = load_json(browser_path)
        except Exception:
            continue

        flow_id = ((browser_log.get("metadata") or {}).get("flow_id")) or ""
        features = extract_browser_features(browser_log)

        row: Dict[str, Any] = {
            "browser_log": str(browser_path),
            "flow_id": flow_id,
        }
        row.update(features)
        rows.append(row)
    return rows


def main() -> None:
    OUT_PARAMS.parent.mkdir(parents=True, exist_ok=True)
    OUT_THRESHOLDS.parent.mkdir(parents=True, exist_ok=True)
    OUT_SCORES.parent.mkdir(parents=True, exist_ok=True)

    rows = build_rows()
    if not rows:
        raise SystemExit("No human rows found for model build.")

    feature_order = sorted([k for k in rows[0].keys() if k not in ("browser_log", "flow_id")])

    X = np.array(
        [[float(r.get(name, 0.0) or 0.0) for name in feature_order] for r in rows],
        dtype=float,
    )

    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0

    z = np.abs((X - mean) / std)
    raw_score = z.mean(axis=1)

    raw_min = float(raw_score.min())
    raw_max = float(raw_score.max())
    if raw_max - raw_min == 0:
        norm_score = np.zeros_like(raw_score)
    else:
        norm_score = np.array([clamp01((v - raw_min) / (raw_max - raw_min)) for v in raw_score], dtype=float)

    thresholds = {
        "fpr_0_5pct": percentile_threshold(norm_score, 0.005),
        "fpr_1pct": percentile_threshold(norm_score, 0.01),
        "fpr_2pct": percentile_threshold(norm_score, 0.02),
        "fpr_5pct": percentile_threshold(norm_score, 0.05),
    }
    thresholds["allow"] = thresholds["fpr_1pct"]
    thresholds["challenge"] = thresholds["fpr_0_5pct"]

    params = {
        "version": "human_only_zscore_v3_browser_only",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_type": "zscore",
        "feature_source": "browser_only",
        "feature_order": feature_order,
        "mean": mean.tolist(),
        "std": std.tolist(),
        "raw_min": raw_min,
        "raw_max": raw_max,
        "browser_dir": str(BROWSER_DIR),
    }

    OUT_PARAMS.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_THRESHOLDS.write_text(json.dumps(thresholds, ensure_ascii=False, indent=2), encoding="utf-8")

    with OUT_SCORES.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["browser_log", "flow_id", "anomaly_score"])
        writer.writeheader()
        for i, row in enumerate(rows):
            writer.writerow(
                {
                    "browser_log": row["browser_log"],
                    "flow_id": row["flow_id"],
                    "anomaly_score": f"{float(norm_score[i]):.8f}",
                }
            )

    print(f"Built human-only model rows: {len(rows)}")
    print(f"Wrote: {OUT_PARAMS}")
    print(f"Wrote: {OUT_THRESHOLDS}")
    print(f"Wrote: {OUT_SCORES}")
    print(f"Thresholds: {thresholds}")


if __name__ == "__main__":
    main()
