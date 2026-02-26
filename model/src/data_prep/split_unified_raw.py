import argparse
import json
import math
import random
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


SPLITS: Sequence[str] = ("train", "validation", "test")
CLASSES: Sequence[str] = ("human", "macro")
DEFAULT_HUMAN_STRATIFY_KEYS = "metadata.user_email"
DEFAULT_MACRO_STRATIFY_KEYS = "metadata.bot_type"
SPLIT_TO_INDEX = {"train": 0, "validation": 1, "test": 2}


def _parse_ratio(value: str, label: str) -> Tuple[float, float, float]:
    parts = [p.strip() for p in str(value).split(":")]
    if len(parts) != 3:
        raise ValueError(f"{label} ratio must have 3 parts like '7:1.5:1.5'")
    try:
        a, b, c = (float(parts[0]), float(parts[1]), float(parts[2]))
    except Exception as exc:
        raise ValueError(f"{label} ratio contains non-numeric values: {value}") from exc
    if a < 0 or b < 0 or c < 0:
        raise ValueError(f"{label} ratio must be non-negative: {value}")
    if (a + b + c) <= 0:
        raise ValueError(f"{label} ratio sum must be > 0: {value}")
    return a, b, c


def _parse_keys(value: str) -> List[str]:
    if value is None:
        return []
    keys = [k.strip() for k in str(value).split(",") if k.strip()]
    seen = set()
    deduped: List[str] = []
    for k in keys:
        if k in seen:
            continue
        seen.add(k)
        deduped.append(k)
    return deduped


def _allocate_counts(total: int, ratio: Tuple[float, float, float]) -> Dict[str, int]:
    if total < 0:
        raise ValueError(f"total must be >= 0, got {total}")
    weights = list(ratio)
    s = sum(weights)
    raw = [(w / s) * total for w in weights]
    base = [math.floor(x) for x in raw]
    remainder = total - sum(base)

    frac_with_idx = sorted(
        [(raw[i] - base[i], i) for i in range(3)],
        key=lambda t: t[0],
        reverse=True,
    )
    for k in range(remainder):
        _, idx = frac_with_idx[k]
        base[idx] += 1

    return {
        "train": int(base[0]),
        "validation": int(base[1]),
        "test": int(base[2]),
    }


def _collect_json_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.glob("*.json") if p.is_file()])


def _load_json_cached(path: Path, cache: Dict[Path, Optional[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    cached = cache.get(path)
    if cached is not None:
        return cached
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            cache[path] = payload
            return payload
    except Exception:
        pass
    cache[path] = {}
    return cache[path]


def _extract_by_dotted(root: Any, dotted: str) -> Any:
    cur = root
    for key in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _extract_group_value(path: Path, payload: Optional[Dict[str, Any]], key: str) -> Any:
    filename = path.name
    stem = path.stem
    parts = stem.split("_")

    if key == "filename":
        return filename
    if key == "filename.stem":
        return stem
    if key == "filename.date":
        return parts[0] if parts and parts[0].isdigit() else None
    if key == "filename.performance_id":
        return parts[1] if len(parts) > 1 else None

    if payload is None:
        return None

    if key.startswith("metadata."):
        return _extract_by_dotted(payload.get("metadata", {}), key[len("metadata.") :])
    if key.startswith("json."):
        return _extract_by_dotted(payload, key[len("json.") :])

    # Backward-compat: treat plain keys as metadata keys first, then top-level.
    metadata = payload.get("metadata", {})
    if isinstance(metadata, dict) and key in metadata:
        return metadata.get(key)
    return payload.get(key)


def _normalize_group_token(value: Any) -> str:
    if value is None:
        return "__NA__"
    if isinstance(value, (int, float, bool)):
        return str(value)
    text = str(value).strip()
    return text if text else "__EMPTY__"


def _build_group_key(path: Path, keys: List[str], cache: Dict[Path, Optional[Dict[str, Any]]]) -> str:
    if not keys:
        return "__all__"
    payload = _load_json_cached(path, cache)
    parts: List[str] = []
    for key in keys:
        value = _extract_group_value(path, payload, key)
        parts.append(f"{key}={_normalize_group_token(value)}")
    return "|".join(parts)


def _allocate_group_counts(
    group_sizes: Dict[str, int],
    ratio: Tuple[float, float, float],
    target_counts: Dict[str, int],
) -> Dict[str, Dict[str, int]]:
    ratio_sum = float(sum(ratio))
    if ratio_sum <= 0:
        raise ValueError("ratio sum must be positive")

    split_names = list(SPLITS)
    group_counts: Dict[str, Dict[str, int]] = {}
    fracs: Dict[str, Dict[str, float]] = {}

    # 1) Per-group proportional allocation with local largest-remainder.
    for group, n in group_sizes.items():
        raws = {
            split: (float(ratio[SPLIT_TO_INDEX[split]]) / ratio_sum) * float(n)
            for split in split_names
        }
        base = {split: int(math.floor(raws[split])) for split in split_names}
        remain = int(n - sum(base.values()))
        frac_order = sorted(
            split_names,
            key=lambda s: (raws[s] - base[s], s),
            reverse=True,
        )
        for i in range(remain):
            base[frac_order[i]] += 1

        group_counts[group] = base
        fracs[group] = {split: float(raws[split] - math.floor(raws[split])) for split in split_names}

    # 2) Global correction so final totals match exact target counts.
    totals = {split: sum(group_counts[g][split] for g in group_counts) for split in split_names}
    deficit = {split: int(target_counts[split] - totals[split]) for split in split_names}

    # Move one sample at a time from oversupplied split to undersupplied split.
    max_iter = sum(abs(v) for v in deficit.values()) * 10 + 100
    iter_cnt = 0
    while any(v != 0 for v in deficit.values()):
        iter_cnt += 1
        if iter_cnt > max_iter:
            raise ValueError(f"failed to resolve stratified allocation deficits: {deficit}")

        need_plus = [s for s in split_names if deficit[s] > 0]
        need_minus = [s for s in split_names if deficit[s] < 0]
        if not need_plus or not need_minus:
            break

        plus = sorted(need_plus, key=lambda s: deficit[s], reverse=True)[0]
        minus = sorted(need_minus, key=lambda s: deficit[s])[0]

        candidates = [g for g in group_counts if group_counts[g][minus] > 0]
        if not candidates:
            raise ValueError(
                "cannot rebalance stratified counts; no movable group from "
                f"{minus} to {plus}"
            )

        best_group = max(candidates, key=lambda g: fracs[g][plus] - fracs[g][minus])
        group_counts[best_group][minus] -= 1
        group_counts[best_group][plus] += 1
        deficit[plus] -= 1
        deficit[minus] += 1

    return group_counts


def _stratified_split(
    *,
    files: List[Path],
    counts: Dict[str, int],
    ratio: Tuple[float, float, float],
    keys: List[str],
    seed: int,
    class_name: str,
) -> Tuple[Dict[str, List[Path]], Dict[str, Any]]:
    total_requested = int(counts["train"] + counts["validation"] + counts["test"])
    if total_requested > len(files):
        raise ValueError(
            f"requested split counts exceed available files for {class_name}: "
            f"requested={total_requested}, available={len(files)}"
        )

    # Backward-compatible path: no stratification keys.
    if not keys:
        shuffled = list(files)
        rnd = random.Random(seed)
        rnd.shuffle(shuffled)
        return _slice_split(shuffled, counts), {
            "keys": [],
            "groups": {"__all__": len(shuffled)},
        }

    json_cache: Dict[Path, Optional[Dict[str, Any]]] = {}
    grouped: Dict[str, List[Path]] = defaultdict(list)
    for p in files:
        gk = _build_group_key(p, keys, json_cache)
        grouped[gk].append(p)

    rnd = random.Random(seed)
    for gk in grouped:
        rnd.shuffle(grouped[gk])

    group_sizes = {gk: len(grouped[gk]) for gk in sorted(grouped.keys())}
    group_alloc = _allocate_group_counts(group_sizes, ratio, counts)

    assignments: Dict[str, List[Path]] = {split: [] for split in SPLITS}
    for gk in sorted(grouped.keys()):
        files_g = grouped[gk]
        alloc = group_alloc[gk]
        n_train = int(alloc["train"])
        n_val = int(alloc["validation"])
        n_test = int(alloc["test"])
        if n_train + n_val + n_test != len(files_g):
            raise ValueError(
                f"group allocation mismatch for {class_name}:{gk} "
                f"({n_train}+{n_val}+{n_test} != {len(files_g)})"
            )
        assignments["train"].extend(files_g[:n_train])
        assignments["validation"].extend(files_g[n_train : n_train + n_val])
        assignments["test"].extend(files_g[n_train + n_val : n_train + n_val + n_test])

    for split in SPLITS:
        got = len(assignments[split])
        want = int(counts[split])
        if got != want:
            raise ValueError(
                f"stratified {class_name} split count mismatch for {split}: "
                f"got={got}, want={want}"
            )

    # Shuffle within each split so one group does not appear as a contiguous block.
    for idx, split in enumerate(SPLITS):
        local_rnd = random.Random(seed + 101 + idx)
        local_rnd.shuffle(assignments[split])

    return assignments, {"keys": list(keys), "groups": group_sizes}


def _slice_split(files: List[Path], counts: Dict[str, int]) -> Dict[str, List[Path]]:
    train_n = counts["train"]
    val_n = counts["validation"]
    test_n = counts["test"]

    if train_n + val_n + test_n > len(files):
        raise ValueError("requested split counts exceed available files")

    train_files = files[0:train_n]
    val_files = files[train_n : train_n + val_n]
    test_files = files[train_n + val_n : train_n + val_n + test_n]
    return {
        "train": train_files,
        "validation": val_files,
        "test": test_files,
    }


def _copy_split(assignments: Dict[str, Dict[str, List[Path]]], out_root: Path) -> None:
    for split in SPLITS:
        for clazz in CLASSES:
            dst = out_root / split / clazz
            dst.mkdir(parents=True, exist_ok=True)
            for src in assignments[clazz][split]:
                shutil.copy2(src, dst / src.name)


def _validate_no_overlap(assignments: Dict[str, Dict[str, List[Path]]]) -> None:
    for clazz in CLASSES:
        seen = set()
        for split in SPLITS:
            for p in assignments[clazz][split]:
                if p.name in seen:
                    raise ValueError(f"duplicate file assigned in {clazz}: {p.name}")
                seen.add(p.name)


def run_unified_split(
    *,
    human_dir: Path,
    macro_dir: Path,
    out_root: Path,
    human_ratio: str,
    macro_ratio: str,
    seed: int,
    human_stratify_keys: str = DEFAULT_HUMAN_STRATIFY_KEYS,
    macro_stratify_keys: str = DEFAULT_MACRO_STRATIFY_KEYS,
    overwrite: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    human_ratio_tuple = _parse_ratio(human_ratio, "human")
    macro_ratio_tuple = _parse_ratio(macro_ratio, "macro")
    human_keys = _parse_keys(human_stratify_keys)
    macro_keys = _parse_keys(macro_stratify_keys)

    human_files = _collect_json_files(human_dir)
    macro_files = _collect_json_files(macro_dir)

    if not human_files:
        raise SystemExit(f"No human json files found in: {human_dir}")
    if not macro_files:
        raise SystemExit(f"No macro json files found in: {macro_dir}")

    human_counts = _allocate_counts(len(human_files), human_ratio_tuple)
    macro_counts = _allocate_counts(len(macro_files), macro_ratio_tuple)

    human_assignments, human_groups = _stratified_split(
        files=human_files,
        counts=human_counts,
        ratio=human_ratio_tuple,
        keys=human_keys,
        seed=seed,
        class_name="human",
    )
    macro_assignments, macro_groups = _stratified_split(
        files=macro_files,
        counts=macro_counts,
        ratio=macro_ratio_tuple,
        keys=macro_keys,
        seed=seed + 17,
        class_name="macro",
    )
    assignments = {"human": human_assignments, "macro": macro_assignments}
    _validate_no_overlap(assignments)

    if out_root.exists():
        if overwrite:
            shutil.rmtree(out_root)
        elif not dry_run:
            raise SystemExit(
                f"Output already exists: {out_root}. "
                "Use overwrite=True or change out_root."
            )

    if not dry_run:
        _copy_split(assignments, out_root)

    manifest = {
        "seed": seed,
        "input": {
            "human_dir": str(human_dir),
            "macro_dir": str(macro_dir),
            "human_total": len(human_files),
            "macro_total": len(macro_files),
        },
        "ratio": {
            "human": human_ratio,
            "macro": macro_ratio,
        },
        "stratify": {
            "human_keys": human_keys,
            "macro_keys": macro_keys,
            "human_groups": human_groups.get("groups", {}),
            "macro_groups": macro_groups.get("groups", {}),
        },
        "counts": {
            "human": human_counts,
            "macro": macro_counts,
        },
        "output_root": str(out_root),
        "files": {
            "human": {
                split: [p.name for p in assignments["human"][split]]
                for split in SPLITS
            },
            "macro": {
                split: [p.name for p in assignments["macro"][split]]
                for split in SPLITS
            },
        },
        "dry_run": bool(dry_run),
    }

    if not dry_run:
        (out_root / "split_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Split unified raw logs into train/validation/test by ratio. "
            "Input dirs: model/data/raw/human and model/data/raw/macro."
        )
    )
    parser.add_argument("--human-dir", default="model/data/raw/human")
    parser.add_argument("--macro-dir", default="model/data/raw/macro")
    parser.add_argument("--out-root", default="model/data/raw/auto_split")
    parser.add_argument("--human-ratio", default="7:1.5:1.5")
    parser.add_argument("--macro-ratio", default="0:5:5")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--human-stratify-keys",
        default=DEFAULT_HUMAN_STRATIFY_KEYS,
        help=(
            "Comma-separated group keys for human stratification. "
            "Examples: metadata.user_email,filename.date,json.metadata.performance_id. "
            "Use empty string to disable."
        ),
    )
    parser.add_argument(
        "--macro-stratify-keys",
        default=DEFAULT_MACRO_STRATIFY_KEYS,
        help=(
            "Comma-separated group keys for macro stratification. "
            "Examples: metadata.bot_type,filename.date. "
            "Use empty string to disable."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete out-root first if it already exists",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    human_dir = Path(args.human_dir)
    macro_dir = Path(args.macro_dir)
    out_root = Path(args.out_root)
    manifest = run_unified_split(
        human_dir=human_dir,
        macro_dir=macro_dir,
        out_root=out_root,
        human_ratio=args.human_ratio,
        macro_ratio=args.macro_ratio,
        seed=int(args.seed),
        human_stratify_keys=str(args.human_stratify_keys),
        macro_stratify_keys=str(args.macro_stratify_keys),
        overwrite=bool(args.overwrite),
        dry_run=bool(args.dry_run),
    )

    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"[{mode}] unified split completed")
    print(f"human count: {manifest['counts']['human']}")
    print(f"macro count: {manifest['counts']['macro']}")
    if not args.dry_run:
        print(f"output: {out_root}")
        print(f"manifest: {out_root / 'split_manifest.json'}")


if __name__ == "__main__":
    main()
