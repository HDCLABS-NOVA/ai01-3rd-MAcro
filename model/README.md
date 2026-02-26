# Model Directory Structure

`model/` is organized by responsibility:

- `src/`: source code for feature extraction, rules, training, serving, and data prep
- `configs/`: runtime and training configuration files
- `schemas/`: browser/server log schema templates
- `data/raw/`: collected browser/server raw logs
- `data/prepared/`: joined/processed datasets
- `artifacts/active/`: currently deployed model params/thresholds/artifact
- `artifacts/runs/`: archived model runs
- `reports/benchmark/`: model comparison and selection reports
- `reports/scoring/`: scoring outputs
- `docs/`: design documentation
- `tests/`: test files

## Entry Commands

- Build ETL prepared dataset from raw split logs:
  - `python model/src/data_prep/build_dataset.py --config model/configs/data_paths.yaml --dataset-id latest`
- Compare and select model:
  - `python model/src/training/compare_and_select.py`
  - If `model/data/raw/human` and `model/data/raw/macro` exist, they are auto-split to `model/data/raw/auto_split` before training.
  - Auto-split is stratified by default:
    - human: `metadata.user_email`
    - macro: `metadata.bot_type`
  - After split, macro validation/test are downsampled to `115` each by default (`--auto-split-macro-eval-count`).
  - Override stratification keys:
    - `python model/src/training/compare_and_select.py --auto-split-human-stratify-keys "metadata.user_email,filename.date" --auto-split-macro-stratify-keys "metadata.bot_type,filename.date"`
  - Disable with `--disable-auto-split-unified`
- Build human-only zscore baseline:
  - `python model/src/training/build_human_model.py`
- Score logs in batch:
  - `python model/src/serving/risk_scorer.py --front-dir model/data/raw/browser --server-dir model/data/raw/server --out model/reports/scoring/risk_scores.csv`
- Join browser and server logs:
  - `python model/src/data_prep/join_logs.py`
- Build admin evidence reports:
  - `python model/src/reporting/build_admin_reports.py --browser-dir model/data/raw/browser --server-dir model/data/raw/server`
