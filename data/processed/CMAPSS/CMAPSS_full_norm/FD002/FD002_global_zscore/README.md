# FD002 Full Global Z-Score Normalized Data (Paper-Parity)

## Overview
- **Method**: Global Z-Score (single mean/std across entire train set)
- **Sensors**: All 21 sensors (s1..s21) + 3 operating conditions (os1..os3) KEPT
- **Drop Policy**: NO SENSOR DROPPED - zero-variance columns set to 0.0
- **Scaler Fit**: Train ONLY (no data leakage)
- **RUL**: Uncapped (no piecewise linear)

## Statistics
- Train: 53,759 rows
- Test: 33,991 rows
- Zero-variance columns: None

## Files
| File | Description |
|------|-------------|
| `train_FD002_full_global_zscore.csv` | Normalized train data with RUL |
| `test_FD002_full_global_zscore.csv` | Normalized test data with RUL |
| `fd002_full_global_zscore_scaler.json` | Scaler parameters (mean, std per feature) |

## Column Order
`engine_id, cycle, os1, os2, os3, s1, s2, ..., s21, RUL`

Generated: 2026-01-26
