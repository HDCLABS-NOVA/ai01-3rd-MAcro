import argparse
import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from sklearn.model_selection import train_test_split

try:
    from model.src.features.feature_pipeline import extract_browser_features
except ModuleNotFoundError:
    import sys

    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from model.src.features.feature_pipeline import extract_browser_features


@dataclass
class Row:
    path: Path
    profile: str


def _load_rows(paths: List[Path]) -> List[Row]:
    rows: List[Row] = []
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        feats = extract_browser_features(data)
        qd = float(feats.get("queue_duration_ms", 0.0) or 0.0)
        qp = float(feats.get("queue_position_delta", 0.0) or 0.0)
        dur_tag = "short" if qd < 1500 else "long"
        pos_tag = "short" if qp <= 5 else "long"
        profile = f"dur_{dur_tag}|pos_{pos_tag}"
        rows.append(Row(path=p, profile=profile))
    return rows


def _split_human(rows: List[Row], seed: int) -> Dict[str, List[Row]]:
    if len(rows) != 765:
        raise SystemExit(f"Expected 765 human logs, got {len(rows)}")

    labels = [r.profile for r in rows]
    idx = list(range(len(rows)))
    train_idx, temp_idx = train_test_split(
        idx,
        train_size=555,
        random_state=seed,
        shuffle=True,
        stratify=labels,
    )
    temp_labels = [labels[i] for i in temp_idx]
    val_rel, test_rel = train_test_split(
        list(range(len(temp_idx))),
        train_size=105,
        random_state=seed,
        shuffle=True,
        stratify=temp_labels,
    )
    val_idx = [temp_idx[i] for i in val_rel]
    test_idx = [temp_idx[i] for i in test_rel]

    return {
        "train": [rows[i] for i in train_idx],
        "validation": [rows[i] for i in val_idx],
        "test": [rows[i] for i in test_idx],
    }


def _split_macro(rows: List[Row], seed: int) -> Dict[str, List[Row]]:
    if len(rows) != 544:
        raise SystemExit(f"Expected 544 macro logs, got {len(rows)}")
    labels = [r.profile for r in rows]
    idx = list(range(len(rows)))
    val_idx, test_idx = train_test_split(
        idx,
        train_size=272,
        random_state=seed,
        shuffle=True,
        stratify=labels,
    )
    return {
        "validation": [rows[i] for i in val_idx],
        "test": [rows[i] for i in test_idx],
    }


def _copy_rows(rows: List[Row], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for r in rows:
        shutil.copy2(r.path, out_dir / r.path.name)


def _profile_counts(rows: List[Row]) -> Dict[str, int]:
    c: Dict[str, int] = {}
    for r in rows:
        c[r.profile] = c.get(r.profile, 0) + 1
    return c


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebalance raw split directories by queue profiles.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-root", default="model/data/raw/rebalanced_v1")
    args = parser.parse_args()

    root = Path("model/data/raw")
    out_root = Path(args.out_root)
    if out_root.exists():
        shutil.rmtree(out_root)
    (out_root / "train" / "macro").mkdir(parents=True, exist_ok=True)

    human_paths = []
    for split in ["train", "validation", "test"]:
        human_paths.extend(sorted((root / split / "human").glob("*.json")))

    macro_paths = []
    for split in ["validation", "test"]:
        macro_paths.extend(sorted((root / split / "macro").glob("*.json")))

    human_rows = _load_rows(human_paths)
    macro_rows = _load_rows(macro_paths)

    random.Random(args.seed).shuffle(human_rows)
    random.Random(args.seed).shuffle(macro_rows)

    human_split = _split_human(human_rows, seed=args.seed)
    macro_split = _split_macro(macro_rows, seed=args.seed)

    _copy_rows(human_split["train"], out_root / "train" / "human")
    _copy_rows(human_split["validation"], out_root / "validation" / "human")
    _copy_rows(human_split["test"], out_root / "test" / "human")
    _copy_rows(macro_split["validation"], out_root / "validation" / "macro")
    _copy_rows(macro_split["test"], out_root / "test" / "macro")

    manifest = {
        "seed": args.seed,
        "out_root": str(out_root),
        "human": {
            "train_count": len(human_split["train"]),
            "validation_count": len(human_split["validation"]),
            "test_count": len(human_split["test"]),
            "train_profile_counts": _profile_counts(human_split["train"]),
            "validation_profile_counts": _profile_counts(human_split["validation"]),
            "test_profile_counts": _profile_counts(human_split["test"]),
            "train_files": [r.path.name for r in sorted(human_split["train"], key=lambda x: x.path.name)],
            "validation_files": [r.path.name for r in sorted(human_split["validation"], key=lambda x: x.path.name)],
            "test_files": [r.path.name for r in sorted(human_split["test"], key=lambda x: x.path.name)],
        },
        "macro": {
            "train_count": 0,
            "validation_count": len(macro_split["validation"]),
            "test_count": len(macro_split["test"]),
            "validation_profile_counts": _profile_counts(macro_split["validation"]),
            "test_profile_counts": _profile_counts(macro_split["test"]),
            "validation_files": [r.path.name for r in sorted(macro_split["validation"], key=lambda x: x.path.name)],
            "test_files": [r.path.name for r in sorted(macro_split["test"], key=lambda x: x.path.name)],
        },
    }
    (out_root / "split_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote rebalanced split at: {out_root}")
    print("Human profile counts:")
    print(" train     ", manifest["human"]["train_profile_counts"])
    print(" validation", manifest["human"]["validation_profile_counts"])
    print(" test      ", manifest["human"]["test_profile_counts"])
    print("Macro profile counts:")
    print(" validation", manifest["macro"]["validation_profile_counts"])
    print(" test      ", manifest["macro"]["test_profile_counts"])


if __name__ == "__main__":
    main()
