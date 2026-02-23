import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from model.src.features.feature_pipeline import extract_browser_features, load_json


DEFAULT_CONFIG_PATH = ROOT_DIR / "model" / "configs" / "data_paths.yaml"
DEFAULT_OUT_ROOT = ROOT_DIR / "model" / "data" / "prepared"


@dataclass
class GroupBuffer:
    rows: List[Dict[str, Any]] = field(default_factory=list)
    fields: set[str] = field(default_factory=set)
    source_files: int = 0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_quotes(value: str) -> str:
    v = value.strip()
    if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
        return v[1:-1]
    return v


def load_paths_config(config_path: Path) -> Dict[str, Any]:
    """
    Lightweight parser for model/configs/data_paths.yaml.
    Supports the subset currently used by this project.
    """
    if not config_path.exists():
        raise SystemExit(f"Config file not found: {config_path}")

    result: Dict[str, Any] = {}
    in_paths = False
    current_list_key: Optional[str] = None

    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))

        if stripped == "paths:":
            in_paths = True
            current_list_key = None
            continue
        if not in_paths:
            continue

        if indent == 2 and stripped.endswith(":"):
            # key: (list or nested)
            key = stripped[:-1].strip()
            current_list_key = key
            if key not in result:
                result[key] = []
            continue

        if indent == 2 and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = _strip_quotes(value.strip())
            if value == "":
                current_list_key = key
                if key not in result:
                    result[key] = []
            else:
                result[key] = value
                current_list_key = None
            continue

        if indent >= 4 and stripped.startswith("- "):
            if current_list_key:
                item = _strip_quotes(stripped[2:].strip())
                result.setdefault(current_list_key, []).append(item)
            continue

    return result


def resolve_input_roots(config_path: Path, config: Dict[str, Any]) -> List[Path]:
    roots: List[Path] = []
    raw_roots = config.get("etl_input_roots") or []
    if isinstance(raw_roots, str):
        raw_roots = [raw_roots]

    project_root = config_path.resolve().parents[2]  # .../<project_root>

    for r in raw_roots:
        p = Path(str(r))
        if p.is_absolute():
            roots.append(p)
        else:
            roots.append((project_root / p).resolve())
    return roots


def resolve_output_root(config_path: Path, config: Dict[str, Any], out_override: str) -> Path:
    if out_override:
        p = Path(out_override)
        return p if p.is_absolute() else (ROOT_DIR / p).resolve()

    raw = str(config.get("etl_output_root") or "")
    if not raw:
        return DEFAULT_OUT_ROOT.resolve()
    p = Path(raw)
    return p if p.is_absolute() else (ROOT_DIR / p).resolve()


def group_key_from_path(path: Path, input_root: Path) -> Tuple[str, str]:
    split = input_root.name
    rel = path.relative_to(input_root)
    if len(rel.parts) == 0:
        return split, "unknown"
    label = rel.parts[0]
    return split, label


def build_row(
    source_path: Path,
    split: str,
    label: str,
    browser_log: Dict[str, Any],
) -> Dict[str, Any]:
    metadata = browser_log.get("metadata", {}) or {}
    features = extract_browser_features(browser_log)

    row: Dict[str, Any] = {
        "split": split,
        "label": label,
        "source_path": str(source_path.as_posix()),
        "flow_id": str(metadata.get("flow_id", "")),
        "session_id": str(metadata.get("session_id", "")),
        "performance_id": str(metadata.get("performance_id", "")),
        "booking_id": str(metadata.get("booking_id", "")),
        "bot_type": str(metadata.get("bot_type", "")),
        "completion_status": str(metadata.get("completion_status", "")),
        "is_completed": 1 if metadata.get("is_completed") else 0,
    }
    row.update(features)
    return row


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fields})


def make_field_order(all_fields: set[str]) -> List[str]:
    lead = [
        "split",
        "label",
        "source_path",
        "flow_id",
        "session_id",
        "performance_id",
        "booking_id",
        "bot_type",
        "completion_status",
        "is_completed",
    ]
    tail = sorted([f for f in all_fields if f not in lead])
    return lead + tail


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ETL prepared dataset from raw browser logs.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to model/configs/data_paths.yaml",
    )
    parser.add_argument(
        "--dataset-id",
        default="latest",
        help="Output dataset id directory name under etl_output_root (default: latest)",
    )
    parser.add_argument(
        "--out-root",
        default="",
        help="Optional override for etl_output_root",
    )
    parser.add_argument(
        "--glob",
        default="",
        help="Optional override for etl_input_glob",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    paths_cfg = load_paths_config(config_path)

    input_roots = resolve_input_roots(config_path, paths_cfg)
    if not input_roots:
        raise SystemExit("No etl_input_roots found in config.")

    glob_pattern = str(args.glob or paths_cfg.get("etl_input_glob") or "**/*.json")
    output_root = resolve_output_root(config_path, paths_cfg, args.out_root)
    dataset_dir = output_root / args.dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)

    groups: Dict[Tuple[str, str], GroupBuffer] = defaultdict(GroupBuffer)
    all_rows: List[Dict[str, Any]] = []
    all_fields: set[str] = set()

    scanned_files = 0
    loaded_json = 0
    parsed_rows = 0
    skipped_non_browser = 0
    skipped_parse_error = 0
    errors: List[Dict[str, str]] = []

    for root in input_roots:
        if not root.exists():
            continue
        if "**" in glob_pattern or "/" in glob_pattern or "\\" in glob_pattern:
            candidates = root.glob(glob_pattern)
        else:
            candidates = root.rglob(glob_pattern)

        for path in sorted(candidates):
            if path.suffix.lower() != ".json":
                continue
            scanned_files += 1

            split, label = group_key_from_path(path, root)
            rel_path = path.resolve().relative_to(ROOT_DIR.resolve())

            try:
                data = load_json(path)
                loaded_json += 1
            except Exception as e:
                skipped_parse_error += 1
                if len(errors) < 200:
                    errors.append({"path": str(rel_path.as_posix()), "error": f"json_load_error: {e}"})
                continue

            if not isinstance(data, dict) or "stages" not in data:
                skipped_non_browser += 1
                continue

            try:
                row = build_row(rel_path, split, label, data)
            except Exception as e:
                skipped_parse_error += 1
                if len(errors) < 200:
                    errors.append({"path": str(rel_path.as_posix()), "error": f"feature_extract_error: {e}"})
                continue

            key = (split, label)
            groups[key].rows.append(row)
            groups[key].fields.update(row.keys())
            groups[key].source_files += 1

            all_rows.append(row)
            all_fields.update(row.keys())
            parsed_rows += 1

    group_manifest: Dict[str, Any] = {}
    for (split, label), buffer in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
        if not buffer.rows:
            continue
        group_dir = dataset_dir / split / label
        field_order = make_field_order(buffer.fields)
        jsonl_path = group_dir / "features.jsonl"
        csv_path = group_dir / "features.csv"

        write_jsonl(jsonl_path, buffer.rows)
        write_csv(csv_path, buffer.rows, field_order)

        group_manifest[f"{split}/{label}"] = {
            "rows": len(buffer.rows),
            "features_count": len(field_order),
            "jsonl": str(jsonl_path.relative_to(ROOT_DIR).as_posix()),
            "csv": str(csv_path.relative_to(ROOT_DIR).as_posix()),
        }

    # Write combined files.
    if all_rows:
        all_fields_order = make_field_order(all_fields)
        write_jsonl(dataset_dir / "all_features.jsonl", all_rows)
        write_csv(dataset_dir / "all_features.csv", all_rows, all_fields_order)
    else:
        all_fields_order = []

    feature_schema = {
        "created_at_utc": _utc_now_iso(),
        "dataset_id": args.dataset_id,
        "feature_count": len(all_fields_order),
        "fields": all_fields_order,
    }
    (dataset_dir / "feature_schema.json").write_text(
        json.dumps(feature_schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    quality_report = {
        "created_at_utc": _utc_now_iso(),
        "dataset_id": args.dataset_id,
        "scanned_files": scanned_files,
        "loaded_json": loaded_json,
        "parsed_rows": parsed_rows,
        "skipped_non_browser": skipped_non_browser,
        "skipped_parse_error": skipped_parse_error,
        "error_samples": errors,
    }
    (dataset_dir / "quality_report.json").write_text(
        json.dumps(quality_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "created_at_utc": _utc_now_iso(),
        "dataset_id": args.dataset_id,
        "config_path": str(config_path.relative_to(ROOT_DIR).as_posix()),
        "input_roots": [str(p.relative_to(ROOT_DIR).as_posix()) if p.exists() else str(p) for p in input_roots],
        "glob": glob_pattern,
        "output_root": str(output_root.relative_to(ROOT_DIR).as_posix()),
        "dataset_dir": str(dataset_dir.relative_to(ROOT_DIR).as_posix()),
        "groups": group_manifest,
        "totals": {
            "groups": len(group_manifest),
            "rows": parsed_rows,
            "feature_count": len(all_fields_order),
        },
    }
    (dataset_dir / "dataset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[ETL] dataset_dir={dataset_dir}")
    print(f"[ETL] scanned={scanned_files} loaded={loaded_json} parsed={parsed_rows}")
    print(f"[ETL] groups={len(group_manifest)} feature_count={len(all_fields_order)}")
    print(f"[ETL] wrote: {dataset_dir / 'dataset_manifest.json'}")


if __name__ == "__main__":
    main()
