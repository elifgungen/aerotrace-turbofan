# N-CMAPSS V0 Upload Manifest

Generated: 2026-02-05T15:42:30

## Summary

| Dataset | Verdict | Train Rows | Test Rows | Engines (Train/Test) | Features | Manifest |
|---------|---------|------------|-----------|----------------------|----------|----------|
| DS01 | PASS | 553 | 341 | 6/4 | 72 | ✅ |
| DS02 | PASS | 446 | 202 | 6/3 | 72 | ✅ |
| DS03 | PASS | 663 | 438 | 9/6 | 72 | ✅ |
| DS04 | PASS | 512 | 344 | 6/4 | 72 | ✅ |
| DS05 | PASS | 491 | 327 | 6/4 | 72 | ✅ |
| DS06 | PASS | 475 | 322 | 6/4 | 72 | ✅ |
| DS07 | PASS | 468 | 344 | 6/4 | 72 | ✅ |
| DS08a | PASS | 611 | 383 | 9/6 | 72 | ✅ |
| DS08c | PASS | 316 | 237 | 6/4 | 72 | ✅ |
| DS08d | SKIP | 0 | 0 | 0/0 | 0 | ❌ |

## Statistics
- **Total datasets**: 10
- **Passed**: 9
- **Failed**: 1 (DS08d - source H5 truncated)
- **With manifest.json**: 9/9 ✅

## Manifest Checklist

All passed datasets now include `manifest.json` with:
- [x] Raw input path + SHA256 hash
- [x] Config path + version + SHA256
- [x] CLI command used
- [x] Output file SHA256 hashes (train, test, scaler, README)
- [x] Python version and package versions
- [x] Git commit hash
- [x] Timestamp (ISO 8601)

## REQUIRED Files (for modeling)

For each PASSED dataset, upload these files from `data/processed/ncmapss_norm/<DS>/V0_global_zscore_nodrop/`:

### DS01
- `train_DS01_v0.csv`
- `test_DS01_v0.csv`
- `scaler_DS01_v0.json`
- `README.md`
- `manifest.json`

### DS02
- `train_DS02_v0.csv`
- `test_DS02_v0.csv`
- `scaler_DS02_v0.json`
- `README.md`
- `manifest.json`

### DS03
- `train_DS03_v0.csv`
- `test_DS03_v0.csv`
- `scaler_DS03_v0.json`
- `README.md`
- `manifest.json`

### DS04
- `train_DS04_v0.csv`
- `test_DS04_v0.csv`
- `scaler_DS04_v0.json`
- `README.md`
- `manifest.json`

### DS05
- `train_DS05_v0.csv`
- `test_DS05_v0.csv`
- `scaler_DS05_v0.json`
- `README.md`
- `manifest.json`

### DS06
- `train_DS06_v0.csv`
- `test_DS06_v0.csv`
- `scaler_DS06_v0.json`
- `README.md`
- `manifest.json`

### DS07
- `train_DS07_v0.csv`
- `test_DS07_v0.csv`
- `scaler_DS07_v0.json`
- `README.md`
- `manifest.json`

### DS08a
- `train_DS08a_v0.csv`
- `test_DS08a_v0.csv`
- `scaler_DS08a_v0.json`
- `README.md`
- `manifest.json`

### DS08c
- `train_DS08c_v0.csv`
- `test_DS08c_v0.csv`
- `scaler_DS08c_v0.json`
- `README.md`
- `manifest.json`

## OPTIONAL Files (for debugging)

From `data/interim/ncmapss/<DS>/`:
- `extraction_config.json`
- `README.md`
- `mapping.json`

## FAILED Datasets

- **DS08d**: Step=inspect, Status=SKIP, Reason: Source H5 truncated (-32 bytes); see `data/raw/ncmapss/DS08d_recovery_report.md`

## Export Packages

Ready-to-upload tar.gz packages in `data/exports/ncmapss_v0_packages/`:
- `DS01.tar.gz`
- `DS02.tar.gz`
- `DS03.tar.gz`
- `DS04.tar.gz`
- `DS05.tar.gz`
- `DS06.tar.gz`
- `DS07.tar.gz`
- `DS08a.tar.gz`
- `DS08c.tar.gz`

## Reproduce Commands

```bash
# Regenerate all datasets with manifests
python -m ncmapss_preprocess --all --config config/ncmapss_preprocess_v1.yaml

# Generate manifests for existing outputs only
python generate_manifests.py
```
