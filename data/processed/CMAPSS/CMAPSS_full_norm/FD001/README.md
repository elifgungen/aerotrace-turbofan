# FD001 Full Normalized Data (Z-Score)

## Overview
This folder contains z-score normalized sensor data for the FD001 CMAPSS dataset.
**No sensors are dropped** - all s1..s21 are included.

## Key Points
- **No sensor dropped**: All 21 sensors (s1..s21) and 3 operating conditions (os1..os3) are included
- **Scaler fit only on train**: No data leakage
- **Zero variance columns kept**: Normalized values set to 0.0

## Generation Method
- **Normalization**: Z-score (mean=0, std=1 for non-zero-variance columns)
- **Formula**: `x_norm = (x - mean) / std`
- **Zero-variance policy**: Keep column, set normalized value to 0.0
- **Source Script**: `scripts/normalize_fd001_full_raw.py`

## Input Files
- `data/raw/CMAPSSData/train_FD001.txt`
- `data/raw/CMAPSSData/test_FD001.txt`
- `data/raw/CMAPSSData/RUL_FD001.txt`

## Output Files
| File | Description |
|------|-------------|
| `train_FD001_full_norm.csv` | Normalized training data with RUL |
| `test_FD001_full_norm.csv` | Normalized test data with RUL |
| `fd001_full_scaler_zscore.json` | Scaler parameters (mean, std per feature) |
| `README.md` | This documentation |

## Column Order
`engine_id, cycle, os1, os2, os3, s1, s2, ..., s21, RUL`

## Zero Variance Columns
The following columns have zero variance (normalized to 0.0):
- os3, s1, s10, s18, s19

## Preserved Columns (Not Normalized)
- `engine_id`: Engine identifier (integer)
- `cycle`: Operating cycle number (integer)
- `RUL`: Remaining Useful Life (integer)

## Date Generated
2026-01-22
