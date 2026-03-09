# FD002 Global Z-Score + Regime One-Hot (K=6 KMeans)

## Overview
- **Base Data**: Global z-score normalized FD002
- **Regime Clustering**: KMeans K=6 on (os1, os2, os3)
- **Clustering Fit**: TRAIN ONLY (no data leakage)
- **Added Columns**: regime_0, regime_1, ..., regime_5 (one-hot)

## Files
| File | Description |
|------|-------------|
| `train_FD002_global_zscore_regime_onehot_k6.csv` | Train with regime one-hot |
| `test_FD002_global_zscore_regime_onehot_k6.csv` | Test with regime one-hot |
| `fd002_regime_k6_model.json` | KMeans model (centroids, counts) |

## Column Order
`engine_id, cycle, os1..s21, regime_0..regime_5, RUL`

## Cluster Distribution
### Train
- Cluster 0: 13,458 samples
- Cluster 1: 8,044 samples
- Cluster 2: 8,122 samples
- Cluster 3: 8,002 samples
- Cluster 4: 8,096 samples
- Cluster 5: 8,037 samples

### Test
- Cluster 0: 8,483 samples
- Cluster 1: 5,148 samples
- Cluster 2: 5,063 samples
- Cluster 3: 5,042 samples
- Cluster 4: 5,107 samples
- Cluster 5: 5,148 samples

## Data Leakage Prevention
- KMeans fitted on TRAIN data only
- Test samples assigned using train-fitted centroids

Generated: 2026-01-26
