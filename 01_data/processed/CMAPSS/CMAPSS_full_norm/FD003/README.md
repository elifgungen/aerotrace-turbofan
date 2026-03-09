# FD003 Full Global Z-Score Normalization (No Drop)

## Dataset
- **Source**: C-MAPSS FD003
- **Variant**: Full feature set, global z-score, no column drop

## Statistics
| Split | Rows | Engines |
|-------|------|---------|
| Train | 24,720 | 100 |
| Test | 16,596 | 100 |

## Features
- **Total**: 24 features (3 operating settings + 21 sensors)
- **Normalized**: os1, os2, os3, s1-s21
- **NOT normalized**: engine_id, cycle, RUL

## Std Flooring
- **Zero-variance columns**: 4 detected
- **Columns floored**: ['os3', 's1', 's18', 's19']
- **Action**: std floored to 1.0 (NO DROP)

## Scaler
- **Method**: Global z-score (train-only fit)
- **ddof**: 1 (sample std)
- **Leakage**: None (scaler fit ONLY on train)

## Files
| File | Description |
|------|-------------|
| train_FD003_full_global_zscore_nodrop.csv | Normalized train data |
| test_FD003_full_global_zscore_nodrop.csv | Normalized test data |
| fd003_full_global_zscore_nodrop_scaler.json | Scaler parameters |

## Verification
Run `scripts/verify_fd003_no_leakage_nodrop.py` to verify no data leakage.
