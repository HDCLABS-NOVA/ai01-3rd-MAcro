from typing import Any, Dict, List, Optional

import numpy as np

from model.src.models.deep_svdd import load_runtime_from_bundle, score_with_runtime, torch_ready

_SHAP_MODULE = None
_SHAP_IMPORT_ERROR = ""


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_vector(features: Dict[str, float], order: List[str]) -> np.ndarray:
    return np.array([_safe_float(features.get(name, 0.0), 0.0) for name in order], dtype=float)


def _get_shap_module() -> Optional[Any]:
    global _SHAP_MODULE, _SHAP_IMPORT_ERROR
    if _SHAP_MODULE is not None:
        return _SHAP_MODULE
    if _SHAP_IMPORT_ERROR:
        return None
    try:
        import shap  # type: ignore

        _SHAP_MODULE = shap
        return _SHAP_MODULE
    except Exception as e:
        _SHAP_IMPORT_ERROR = str(e)
        return None


def _baseline_vector(
    vec: np.ndarray,
    params: Dict[str, Any],
    model_artifact: Optional[Dict[str, Any]],
) -> np.ndarray:
    base_vec = np.zeros_like(vec)

    scaler = model_artifact.get("scaler") if isinstance(model_artifact, dict) else None
    if scaler is not None and hasattr(scaler, "mean_"):
        try:
            s_mean = np.array(scaler.mean_, dtype=float)
            if s_mean.shape[0] == vec.shape[0]:
                return s_mean
        except Exception:
            pass

    if "mean" in params:
        try:
            p_mean = np.array(params.get("mean", []), dtype=float)
            if p_mean.shape[0] == vec.shape[0]:
                return p_mean
        except Exception:
            pass

    return base_vec


def _isolation_forest_shap_contributions(
    vec: np.ndarray,
    model_artifact: Optional[Dict[str, Any]],
) -> Optional[np.ndarray]:
    if not isinstance(model_artifact, dict):
        return None

    model = model_artifact.get("model")
    scaler = model_artifact.get("scaler")
    if model is None:
        return None

    shap_mod = _get_shap_module()
    if shap_mod is None:
        return None

    x = vec.reshape(1, -1)
    if scaler is not None:
        x = scaler.transform(x)

    explainer = model_artifact.get("_shap_tree_explainer")
    if explainer is None:
        explainer = shap_mod.TreeExplainer(model)
        model_artifact["_shap_tree_explainer"] = explainer

    shap_values = explainer.shap_values(x)
    shap_arr = np.array(shap_values, dtype=float)
    if shap_arr.ndim == 2:
        shap_row = shap_arr[0]
    elif shap_arr.ndim == 1:
        shap_row = shap_arr
    else:
        return None

    if shap_row.shape[0] != vec.shape[0]:
        return None

    # IsolationForest decision_function is "normality-like".
    # Runtime anomaly score uses -decision_function, so negate SHAP values
    # to obtain "contribution to anomaly/risk increase".
    return -shap_row


def _raw_score_from_vector(
    vec: np.ndarray,
    model_type: str,
    params: Dict[str, Any],
    model_artifact: Optional[Dict[str, Any]],
) -> float:
    if model_type == "zscore" or ("mean" in params and "std" in params and not model_artifact):
        mean = np.array(params.get("mean", []), dtype=float)
        std = np.array(params.get("std", []), dtype=float)
        if mean.shape[0] != vec.shape[0] or std.shape[0] != vec.shape[0] or vec.shape[0] == 0:
            return 0.0
        std = std.copy()
        std[std == 0] = 1.0
        return float(np.abs((vec - mean) / std).mean())

    if model_type in {"isolation_forest", "oneclass_svm", "local_outlier_factor"}:
        if not model_artifact:
            return 0.0
        model = model_artifact.get("model")
        scaler = model_artifact.get("scaler")
        if model is None:
            return 0.0
        x = vec.reshape(1, -1)
        if scaler is not None:
            x = scaler.transform(x)
        if hasattr(model, "decision_function"):
            return -float(model.decision_function(x)[0])
        if hasattr(model, "score_samples"):
            return -float(model.score_samples(x)[0])
    if model_type == "deep_svdd":
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
        return float(score_with_runtime(net, center, np.array(x, dtype=np.float32))[0])
    return 0.0


def top_model_contributors(
    features: Dict[str, float],
    params: Dict[str, Any],
    model_artifact: Optional[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    order = list(params.get("feature_order") or [])
    if not order:
        return []

    model_type = str(params.get("model_type", "zscore"))
    vec = _to_vector(features, order)
    if vec.size == 0:
        return []

    # z-score: exact per-feature raw-score contribution.
    if model_type == "zscore" or ("mean" in params and "std" in params and not model_artifact):
        mean = np.array(params.get("mean", []), dtype=float)
        std = np.array(params.get("std", []), dtype=float)
        if mean.shape[0] != vec.shape[0] or std.shape[0] != vec.shape[0]:
            return []
        std = std.copy()
        std[std == 0] = 1.0
        z_each = np.abs((vec - mean) / std)
        contrib = z_each / max(1, len(order))
        ranked = sorted(
            [
                {
                    "feature": order[i],
                    "value": float(vec[i]),
                    "baseline": float(mean[i]),
                    "normal_mean": float(mean[i]),
                    "contribution": float(contrib[i]),
                    "method": "zscore_exact",
                }
                for i in range(len(order))
            ],
            key=lambda x: x["contribution"],
            reverse=True,
        )
        return ranked[: max(1, int(top_k))]

    # isolation_forest: use SHAP first when available.
    if model_type == "isolation_forest":
        shap_contrib = _isolation_forest_shap_contributions(vec, model_artifact)
        base_vec = _baseline_vector(vec, params, model_artifact)
        if shap_contrib is not None:
            scored = [
                {
                    "feature": order[i],
                    "value": float(vec[i]),
                    "baseline": float(base_vec[i]),
                    "normal_mean": float(base_vec[i]),
                    "contribution": float(shap_contrib[i]),
                    "method": "shap_tree_explainer",
                }
                for i in range(len(order))
            ]
            positive = [s for s in scored if s["contribution"] > 0]
            ranked = sorted(
                positive if positive else scored,
                key=lambda x: abs(x["contribution"]),
                reverse=True,
            )
            return ranked[: max(1, int(top_k))]

    # oneclass_svm / local_outlier_factor / deep_svdd (and IF fallback): leave-one-feature-to-baseline approximation.
    if model_type in {"isolation_forest", "oneclass_svm", "local_outlier_factor", "deep_svdd"}:
        base_vec = _baseline_vector(vec, params, model_artifact)

        raw_orig = _raw_score_from_vector(vec, model_type, params, model_artifact)
        scored: List[Dict[str, Any]] = []
        for i, feature_name in enumerate(order):
            vec_cf = vec.copy()
            vec_cf[i] = base_vec[i]
            raw_cf = _raw_score_from_vector(vec_cf, model_type, params, model_artifact)
            contribution = float(raw_orig - raw_cf)
            scored.append(
                {
                    "feature": feature_name,
                    "value": float(vec[i]),
                    "baseline": float(base_vec[i]),
                    "normal_mean": float(base_vec[i]),
                    "contribution": contribution,
                    "method": "leave_one_out",
                }
            )

        positive = [s for s in scored if s["contribution"] > 0]
        ranked = sorted(
            positive if positive else scored,
            key=lambda x: abs(x["contribution"]),
            reverse=True,
        )
        return ranked[: max(1, int(top_k))]

    return []
