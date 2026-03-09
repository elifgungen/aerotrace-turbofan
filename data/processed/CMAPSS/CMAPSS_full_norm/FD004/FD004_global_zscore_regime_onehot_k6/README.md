# FD004 V1: Global Z-Score + Regime One-Hot (K=6)

## Method
- Base: V0 global z-score normalized data
- KMeans K=6 on os1, os2, os3 (train-only fit)
- One-hot columns: regime_0..regime_5

## Statistics
| Split | Rows | Columns |
|-------|------|---------|
| Train | 61,249 | 33 |
| Test | 41,214 | 33 |

## Cluster Distribution (Train)
{0: 15395, 1: 9224, 2: 9139, 3: 9091, 4: 9238, 5: 9162}
