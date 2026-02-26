# Unified Raw Split Policy

## Goal
- Keep `human FPR` low and `macro recall` high by reducing split leakage and distribution drift.
- Build train/validation/test from:
  - `model/data/raw/human`
  - `model/data/raw/macro`

## Default Rules
1. Human split is stratified by `metadata.user_email`.
2. Macro split is stratified by `metadata.bot_type`.
3. Ratios:
   - Human: `7:1.5:1.5` (train:validation:test)
   - Macro: `0:5:5` (validation:test only)
4. Post-process for evaluation stability:
   - Macro validation and test are downsampled to `115` each by default in `compare_and_select.py`.
   - Override with `--auto-split-macro-eval-count`.
5. Split counts are matched to exact target totals after stratified allocation.
6. No file overlap across train/validation/test.

## Why These Rules
- `human` currently has a small number of repeated user identities, so random split can bias FPR.
- `macro` currently mixes multiple bot types, so validation/test must keep similar type composition.

## Commands
- Run unified split directly:
```bash
python model/src/data_prep/split_unified_raw.py \
  --human-dir model/data/raw/human \
  --macro-dir model/data/raw/macro \
  --out-root model/data/raw/auto_split \
  --human-ratio 7:1.5:1.5 \
  --macro-ratio 0:5:5 \
  --seed 42 \
  --overwrite
```

- Run training with auto-split:
```bash
python model/src/training/compare_and_select.py
```

- Override stratification keys if needed:
```bash
python model/src/training/compare_and_select.py \
  --auto-split-human-stratify-keys "metadata.user_email,filename.date" \
  --auto-split-macro-stratify-keys "metadata.bot_type,filename.date"
```
