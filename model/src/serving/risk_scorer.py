import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from model.src.features.feature_pipeline import build_server_index, extract_browser_features, load_json
from model.src.models.deep_svdd import load_runtime_from_bundle, score_with_runtime, torch_ready
from model.src.serving.model_explain import top_model_contributors
from model.src.rules.rule_base import evaluate_rules


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


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


@dataclass
class ScoreResult:
    browser_log: str
    flow_id: str
    decision: str
    risk_score: float
    rule_score: float
    model_score: float
    hard_action: str
    soft_rules_triggered: str
    hard_rules_triggered: str
    model_top_features: str
    review_required: bool
    block_recommended: bool


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
        z = np.abs((vec - mean) / std)
        raw = float(z.mean())
    elif model_type in ("isolation_forest", "oneclass_svm", "local_outlier_factor"):
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

    if raw_max - raw_min == 0:
        return 0.0
    return clamp01((raw - raw_min) / (raw_max - raw_min))


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


def find_server_for_flow(
    flow_id: str,
    server_log: Optional[Dict[str, Any]],
    server_index: Optional[Dict[str, Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    if server_log is not None:
        return server_log
    if server_index is None:
        return None
    return server_index.get(flow_id)


def score_one(
    browser_path: Path,
    params: Dict[str, Any],
    model_artifact: Optional[Dict[str, Any]],
    server_log: Optional[Dict[str, Any]],
    server_index: Optional[Dict[str, Dict[str, Any]]],
    thresholds: Dict[str, float],
    w_rule: float,
    w_model: float,
    block_automation: bool,
) -> ScoreResult:
    browser_log = load_json(browser_path)
    flow_id = ((browser_log.get("metadata") or {}).get("flow_id")) or ""

    matched_server = find_server_for_flow(flow_id, server_log, server_index)
    features = extract_browser_features(browser_log)

    rule_eval = evaluate_rules(matched_server or {}, browser_log=browser_log)
    r_score = safe_float(rule_eval.get("soft_score"))
    hard_action = str(rule_eval.get("hard_action", "none"))
    m_score = 0.0
    model_top_features: List[str] = []
    if hard_action != "block":
        m_score = model_score_from_features(features, params, model_artifact=model_artifact)
        model_top_features = [
            str(item.get("feature", "")).strip()
            for item in top_model_contributors(
                features=features,
                params=params,
                model_artifact=model_artifact,
                top_k=5,
            )
            if str(item.get("feature", "")).strip()
        ]

    risk = clamp01(w_model * m_score + w_rule * r_score)
    decision = decision_from_risk(risk, thresholds)

    if hard_action == "block":
        decision = "block"
        risk = max(risk, thresholds["challenge"], 0.95)

    review_required = False
    block_recommended = False
    if decision == "block" and not block_automation and hard_action != "block":
        decision = "challenge"
        review_required = True
        block_recommended = True

    return ScoreResult(
        browser_log=str(browser_path),
        flow_id=flow_id,
        decision=decision,
        risk_score=risk,
        rule_score=r_score,
        model_score=m_score,
        hard_action=hard_action,
        soft_rules_triggered="|".join(rule_eval.get("soft_rules_triggered", []) or []),
        hard_rules_triggered="|".join(rule_eval.get("hard_rules_triggered", []) or []),
        model_top_features="|".join(model_top_features),
        review_required=review_required,
        block_recommended=block_recommended,
    )


def parse_args() -> argparse.Namespace:
    root_dir = Path(__file__).resolve().parents[3]
    model_dir = root_dir / "model"

    parser = argparse.ArgumentParser(description="Hybrid risk scoring (rule + model)")
    parser.add_argument("--front-log", default="", help="Path to one browser log")
    parser.add_argument("--front-dir", default="", help="Path to browser log directory (batch)")
    parser.add_argument("--server-log", default="", help="Path to one server log (optional)")
    parser.add_argument(
        "--server-dir",
        default=str(model_dir / "data" / "raw" / "server"),
        help="Path to server log dir (optional)",
    )
    parser.add_argument(
        "--params",
        default=str(model_dir / "artifacts" / "active" / "human_model_params.json"),
        help="Path to model params",
    )
    parser.add_argument(
        "--thresholds",
        default=str(model_dir / "artifacts" / "active" / "human_model_thresholds.json"),
        help="Path to threshold file",
    )
    parser.add_argument("--out", default="", help="Output CSV for batch mode")
    parser.add_argument("--w-rule", type=float, default=0.2)
    parser.add_argument("--w-model", type=float, default=0.8)
    parser.add_argument("--allow-threshold", default="", help="Risk allow threshold override")
    parser.add_argument("--challenge-threshold", default="", help="Risk challenge threshold override")
    parser.add_argument(
        "--block-automation",
        action="store_true",
        help="Enable automatic block for model-only high-risk sessions",
    )
    return parser.parse_args()


def resolve_front_logs(front_log: str, front_dir: str) -> List[Path]:
    if front_log and front_dir:
        raise SystemExit("Use either --front-log or --front-dir, not both.")
    if front_log:
        return [Path(front_log)]
    if front_dir:
        return sorted(Path(front_dir).rglob("*.json"))
    raise SystemExit("Provide --front-log or --front-dir.")


def main() -> None:
    args = parse_args()
    front_logs = resolve_front_logs(args.front_log, args.front_dir)
    if not front_logs:
        raise SystemExit("No browser logs found.")

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
        try:
            model_artifact = joblib.load(artifact_path)
        except Exception as e:
            raise SystemExit(f"Failed to load model artifact: {artifact_path} ({e})")

    one_server_log = load_json(Path(args.server_log)) if args.server_log else None
    server_index = None if one_server_log else build_server_index(Path(args.server_dir))

    rows: List[ScoreResult] = []
    for browser_path in front_logs:
        try:
            rows.append(
                score_one(
                    browser_path=browser_path,
                    params=params,
                    model_artifact=model_artifact,
                    server_log=one_server_log,
                    server_index=server_index,
                    thresholds=thresholds,
                    w_rule=args.w_rule,
                    w_model=args.w_model,
                    block_automation=args.block_automation,
                )
            )
        except Exception as e:
            print(f"skip {browser_path}: {e}")

    if not rows:
        raise SystemExit("No score rows produced.")

    if args.out:
        out_path = Path(args.out)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "browser_log",
                    "flow_id",
                    "decision",
                    "risk_score",
                    "rule_score",
                    "model_score",
                    "hard_action",
                    "soft_rules_triggered",
                    "hard_rules_triggered",
                    "model_top_features",
                    "review_required",
                    "block_recommended",
                ],
            )
            writer.writeheader()
            for r in rows:
                writer.writerow(
                    {
                        "browser_log": r.browser_log,
                        "flow_id": r.flow_id,
                        "decision": r.decision,
                        "risk_score": f"{r.risk_score:.8f}",
                        "rule_score": f"{r.rule_score:.8f}",
                        "model_score": f"{r.model_score:.8f}",
                        "hard_action": r.hard_action,
                        "soft_rules_triggered": r.soft_rules_triggered,
                        "hard_rules_triggered": r.hard_rules_triggered,
                        "model_top_features": r.model_top_features,
                        "review_required": str(r.review_required).lower(),
                        "block_recommended": str(r.block_recommended).lower(),
                    }
                )
        print(f"Wrote: {out_path}")
    else:
        for r in rows[:5]:
            print(
                json.dumps(
                    {
                        "browser_log": r.browser_log,
                        "flow_id": r.flow_id,
                        "decision": r.decision,
                        "risk_score": round(r.risk_score, 6),
                        "rule_score": round(r.rule_score, 6),
                        "model_score": round(r.model_score, 6),
                        "hard_action": r.hard_action,
                        "soft_rules_triggered": r.soft_rules_triggered.split("|")
                        if r.soft_rules_triggered
                        else [],
                        "hard_rules_triggered": r.hard_rules_triggered.split("|")
                        if r.hard_rules_triggered
                        else [],
                        "model_top_features": r.model_top_features.split("|") if r.model_top_features else [],
                        "review_required": r.review_required,
                        "block_recommended": r.block_recommended,
                    },
                    ensure_ascii=False,
                )
            )
        print(f"rows={len(rows)}")


if __name__ == "__main__":
    main()
