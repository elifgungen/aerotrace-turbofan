# FD004 V2: Regime-Aware Sensor Z-Score (K=6) + One-Hot

## Method
- KMeans K=6 on os1, os2, os3 (train-only fit)
- os1-os3: Kept as V0 global z-score
- s1-s21: Normalized PER REGIME (train-only mean/std per regime)
- One-hot columns: regime_0..regime_5

## Statistics
| Split | Rows | Columns |
|-------|------|---------|
| Train | 61,249 | 33 |
| Test | 41,214 | 33 |

## Cluster Distribution (Train)
{0: 15395, 1: 9224, 2: 9139, 3: 9091, 4: 9238, 5: 9162}
