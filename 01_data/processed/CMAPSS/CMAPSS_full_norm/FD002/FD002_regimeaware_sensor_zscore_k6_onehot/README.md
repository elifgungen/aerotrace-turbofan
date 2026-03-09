# FD002 Regime-Aware Sensor Z-Score (KMeans K=6)

## Overview
- **Regime Clustering**: KMeans K=6 on (os1, os2, os3) - TRAIN ONLY
- **Sensor Scaling**: Per-regime z-score for s1..s21
- **OS Columns**: UNCHANGED (global z-score values preserved)
- **One-Hot**: regime_0..regime_5 columns added

## Why Per-Regime Sensor Scaling?
Different operating conditions cause different sensor baselines. By normalizing sensors
within each regime, we remove condition-dependent bias and expose true degradation signal.

## Data Leakage Prevention
- KMeans fitted on TRAIN data only
- Per-regime mean/std computed on TRAIN data only
- Test samples use train-fitted centroids and scaler parameters

## Files
| File | Description |
|------|-------------|
| `train_FD002_regimeaware_sensor_zscore_k6_onehot.csv` | Train with regime-scaled sensors |
| `test_FD002_regimeaware_sensor_zscore_k6_onehot.csv` | Test with regime-scaled sensors |
| `fd002_regimeaware_sensor_scaler_k6.json` | Centroids + per-regime sensor mean/std |

## Column Order
`engine_id, cycle, os1, os2, os3, s1..s21, regime_0..regime_5, RUL`

## Cluster Distribution
### Train
- Regime 0: 13,458 samples
- Regime 1: 8,044 samples
- Regime 2: 8,122 samples
- Regime 3: 8,002 samples
- Regime 4: 8,096 samples
- Regime 5: 8,037 samples

### Test
- Regime 0: 8,483 samples
- Regime 1: 5,148 samples
- Regime 2: 5,063 samples
- Regime 3: 5,042 samples
- Regime 4: 5,107 samples
- Regime 5: 5,148 samples

Generated: 2026-01-26
