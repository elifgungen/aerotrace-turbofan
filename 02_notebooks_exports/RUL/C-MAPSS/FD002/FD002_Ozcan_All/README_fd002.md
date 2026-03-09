# FD002 artefact paketi (leakage-free / engine bazlı)

## Input
- Normalized datasets (repo içinde hazır):
  - `01_data/processed/CMAPSS_full_norm/FD002/FD002_global_zscore/train_FD002_full_global_zscore.csv`
  - `01_data/processed/CMAPSS_full_norm/FD002/FD002_global_zscore/test_FD002_full_global_zscore.csv`
- Regime varyantları (opsiyonel):
  - `01_data/processed/CMAPSS_full_norm/FD002/FD002_global_zscore_regime_onehot_k6/`
  - `01_data/processed/CMAPSS_full_norm/FD002/FD002_regimeaware_sensor_zscore_k6_onehot/`

## Preprocess (ham FD002 txt → dataset üretimi)
- Not: Bu repoda **FD002 raw txt dosyaları yok**. (Nasa CMAPSS `train_FD002.txt`, `test_FD002.txt`, `RUL_FD002.txt` harici temin edilmeli.)
- Script: `01_data/scripts/fd002_preprocess.py`
```bash
python 01_data/scripts/fd002_preprocess.py \\
  --train-txt /path/to/train_FD002.txt \\
  --test-txt  /path/to/test_FD002.txt \\
  --rul-txt   /path/to/RUL_FD002.txt \\
  --export-regime-onehot \\
  --export-regimeaware-sensor
```

## Train-only fit / rejim yönetimi (kanıt)
- Global z-score scaler + train-only fit: `01_data/processed/CMAPSS_full_norm/FD002/FD002_global_zscore/fd002_full_global_zscore_scaler.json`
- KMeans rejim modeli (train-only): `01_data/processed/CMAPSS_full_norm/FD002/FD002_global_zscore_regime_onehot_k6/fd002_regime_k6_model.json`
- Per-regime sensor scaler (train-only): `01_data/processed/CMAPSS_full_norm/FD002/FD002_regimeaware_sensor_zscore_k6_onehot/fd002_regimeaware_sensor_scaler_k6.json`

## Tek komutla train + predict (engine GroupKFold)
### BASE (global z-score)
```bash
python 02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/train_fd002_groupkfold_sklearn.py \
  --config 02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/config_FD002_local_BASE.json
```

### Regime one-hot (K=6)
```bash
python 02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/train_fd002_groupkfold_sklearn.py \
  --config 02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/config_FD002_local_regime_onehot_k6.json
```

### Regime-aware sensor z-score + one-hot (K=6)
```bash
python 02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/train_fd002_groupkfold_sklearn.py \
  --config 02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/config_FD002_local_regimeaware_sensor_zscore_k6_onehot.json
```

## Output (bu script üretir)
- Canonical (son koşu overwrite eder):
  - `02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/fd002_oof_predictions.csv` (engine_id, cycle, fold, y_true, y_pred)
  - `02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/fd002_cv_metrics.json` (+ `fd002_cv_metrics.csv`)
  - `02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/fd002_test_predictions.csv` (engine_id, cycle, rul_pred)
  - (opsiyonel) `02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/fd002_test_predictions_labeled.csv`
- Variant-suffixed (EXP_NAME ile):
  - `02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/fd002_oof_predictions_<EXP_NAME>.csv`
  - `02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/fd002_cv_metrics_<EXP_NAME>.json` (+ `.csv`)
  - `02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/fd002_test_predictions_<EXP_NAME>.csv`
- Plot’lar (varsa):
  - `04_figures/rul_predictions/fd002_oof_parity.png` (+ `fd002_oof_parity_<EXP_NAME>.png`)
  - `04_figures/rul_predictions/fd002_oof_lifestory_examples.png` (+ `fd002_oof_lifestory_examples_<EXP_NAME>.png`)

## Leakage kanıtı (engine bazlı split)
- Train sırasında fold başına engine overlap log’u (stdout) + `assert overlap==0`:
  - Script: `02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/train_fd002_groupkfold_sklearn.py`
- OOF üzerinden deterministik doğrulama raporu (engine_id tek fold + fold engine_overlap=0):
  - `02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/fd002_leakage_report_FD002_LOCAL_BASE.json`
  - `02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/fd002_leakage_report_FD002_LOCAL_REGIME_ONEHOT_K6.json`
  - `02_notebooks_exports/RUL/FD002/FD002_Ozcan_All/fd002_leakage_report_FD002_LOCAL_REGIMEAWARE_SENSOR_ZSCORE_K6_ONEHOT.json`
