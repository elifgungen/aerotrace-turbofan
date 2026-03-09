# FD001 Normalized Data (Z-Score)

## Overview
This folder contains z-score normalized sensor data for the FD001 CMAPSS dataset.

## Generation Method
- **Scaler Fit**: Only on training data (no data leakage)
- **Normalization Formula**: `x_norm = (x - mean) / std`
- **Source Script**: `scripts/normalize_fd001.py`

## Input Files
- `data/processed/CMAPSS_kept/FD001/train_FD001_kept.txt`
- `data/processed/CMAPSS_kept/FD001/test_FD001_kept.txt`
- `data/processed/CMAPSS_kept/FD001/RUL_FD001.txt`

## Output Files
| File | Description |
|------|-------------|
| `train_FD001_norm.csv` | Normalized training data with RUL labels |
| `test_FD001_norm.csv` | Normalized test data with RUL labels |
| `fd001_scaler_zscore.json` | Scaler parameters (mean, std per feature) |
| `README.md` | This documentation |

## Column Order
`engine_id, cycle, os1, os2, s2, s3, s4, s7, s8, s9, s11, s12, s13, s14, s15, s17, s20, s21, RUL`

## Dropped Columns (Zero Variance)
The following columns were dropped due to zero standard deviation:
- os3

## Preserved Columns (Not Normalized)
- `engine_id`: Engine identifier (integer)
- `cycle`: Operating cycle number (integer)
- `RUL`: Remaining Useful Life (integer)

## Date Generated
2026-01-22
