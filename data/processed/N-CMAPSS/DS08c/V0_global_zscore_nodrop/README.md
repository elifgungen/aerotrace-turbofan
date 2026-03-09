# n-CMAPSS DS08c V0 Global Z-Score (NoDrop)

## Normalization
- Method: Global Z-Score
- Parameters fit on: Train data only
- std computation: ddof=1
- Zero-variance handling: std floored to 1.0 (NoDrop)

## Data Summary

| Split | Shape |
|-------|-------|
| Train | (316, 78) |
| Test | (237, 78) |

## Columns
- **Normalized (72)**: All feature columns (W_*, Xs_*)
- **Not normalized**: ['engine_id', 'cycle', 'Fc', 'hs', 'n_samples_in_cycle', 'RUL']
- **Floored columns**: 0

## Files
- `train_DS08c_v0.csv`
- `test_DS08c_v0.csv`
- `scaler_DS08c_v0.json`
