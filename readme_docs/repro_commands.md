# Repro Commands (FD001 / FD002) — AeroTrace Pipeline Reproducibility

Bu doküman, **FD001** ve **FD002** için reproducibility zincirini (raw → processed → anomaly → decision-support v1) tek komutla çalıştırma komutlarını ve beklenen çıktıları listeler.

## Önkoşul: Raw veri
FD001 ve FD002 için ham C-MAPSS path'leri:
- `data/raw/CMAPSS/FD001_raw_dataset/train_FD001.txt`
- `data/raw/CMAPSS/FD001_raw_dataset/test_FD001.txt`
- `data/raw/CMAPSS/FD001_raw_dataset/RUL_FD001.txt`
- `data/raw/CMAPSS/FD002_raw_dataset/train_FD002.txt`
- `data/raw/CMAPSS/FD002_raw_dataset/test_FD002.txt`
- `data/raw/CMAPSS/FD002_raw_dataset/RUL_FD002.txt`

RUL notebook export path örnekleri:
- C-MAPSS: `notebooks/RUL/C-MAPSS/FD001/FD001_AllRaws/` ve `notebooks/RUL/C-MAPSS/FD002/FD002_All/`
- N-CMAPSS: `notebooks/RUL/N-CMAPSS/DS01/` ve `notebooks/RUL/N-CMAPSS/DS02/`

## FD001 — tek komutla repro
```bash
python scripts/build_fd001_preprocess.py \
  --raw-dir data/raw/CMAPSS/FD001_raw_dataset \
  --out-train data/processed/CMAPSS/CMAPSS_full_norm/FD001/train_FD001_full_norm.csv \
  --out-test data/processed/CMAPSS/CMAPSS_full_norm/FD001/test_FD001_full_norm.csv \
  --report-json data/processed/outputs/FD001/fd001_preprocess_report.json

python scripts/anomaly_baseline_deviation.py \
  --dataset FD001 \
  --train_csv data/processed/CMAPSS/CMAPSS_full_norm/FD001/train_FD001_full_norm.csv \
  --test_csv data/processed/CMAPSS/CMAPSS_full_norm/FD001/test_FD001_full_norm.csv \
  --config configs/anomaly_thresholds.json \
  --outdir data/processed/outputs/FD001

python scripts/standardize_rul_predictions.py \
  --dataset FD001 --split test \
  --in_csv notebooks/RUL/C-MAPSS/FD001/FD001_AllRaws/predictions_cycle_all_rows.csv \
  --pred_col pred_ensemble \
  --out_csv data/processed/outputs/FD001/fd001_rul_predictions.csv

python scripts/build_decision_support_v1.py \
  --dataset FD001 \
  --rul_csv data/processed/outputs/FD001/fd001_rul_predictions.csv \
  --anomaly_csv data/processed/outputs/FD001/fd001_anomaly_scores.csv \
  --config configs/decision_support_thresholds.json \
  --out_csv data/processed/outputs/FD001/fd001_decision_support.csv \
  --report_json data/processed/outputs/FD001/fd001_decision_support_report.json
```

Beklenen çıktılar:
- `data/processed/CMAPSS/CMAPSS_full_norm/FD001/train_FD001_full_norm.csv`
- `data/processed/CMAPSS/CMAPSS_full_norm/FD001/test_FD001_full_norm.csv`
- `data/processed/outputs/FD001/fd001_preprocess_report.json`
- `data/processed/outputs/FD001/fd001_anomaly_scores.csv`
- `data/processed/outputs/FD001/fd001_rul_predictions.csv`
- `data/processed/outputs/FD001/fd001_decision_support.csv`
- `data/processed/outputs/FD001/fd001_decision_support_report.json`

## FD002 — tek komutla repro
```bash
python scripts/build_fd002_preprocess.py \
  --raw-dir data/raw/CMAPSS/FD002_raw_dataset \
  --out-train data/processed/CMAPSS/CMAPSS_full_norm/FD002/FD002_regimeaware_sensor_zscore_k6_onehot/train_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --out-test data/processed/CMAPSS/CMAPSS_full_norm/FD002/FD002_regimeaware_sensor_zscore_k6_onehot/test_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --report-json data/processed/outputs/FD002/fd002_preprocess_report.json

python scripts/build_fd002_anomaly.py \
  --train_csv data/processed/CMAPSS/CMAPSS_full_norm/FD002/FD002_regimeaware_sensor_zscore_k6_onehot/train_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --test_csv data/processed/CMAPSS/CMAPSS_full_norm/FD002/FD002_regimeaware_sensor_zscore_k6_onehot/test_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --config configs/anomaly_thresholds.json \
  --outdir data/processed/outputs/FD002

python scripts/standardize_rul_predictions.py \
  --dataset FD002 --split test \
  --in_csv notebooks/RUL/C-MAPSS/FD002/FD002_All/fd002_test_predictions_FD002_LOCAL_REGIMEAWARE_SENSOR_ZSCORE_K6_ONEHOT.csv \
  --out_csv data/processed/outputs/FD002/fd002_rul_predictions.csv

python scripts/build_decision_support_v1.py \
  --dataset FD002 \
  --rul_csv data/processed/outputs/FD002/fd002_rul_predictions.csv \
  --anomaly_csv data/processed/outputs/FD002/fd002_anomaly_scores.csv \
  --config configs/decision_support_thresholds.json \
  --out_csv data/processed/outputs/FD002/fd002_decision_support.csv \
  --report_json data/processed/outputs/FD002/fd002_decision_support_report.json
```

Beklenen çıktılar:
- `data/processed/CMAPSS/CMAPSS_full_norm/FD002/FD002_regimeaware_sensor_zscore_k6_onehot/train_FD002_regimeaware_sensor_zscore_k6_onehot.csv`
- `data/processed/CMAPSS/CMAPSS_full_norm/FD002/FD002_regimeaware_sensor_zscore_k6_onehot/test_FD002_regimeaware_sensor_zscore_k6_onehot.csv`
- `data/processed/outputs/FD002/fd002_preprocess_report.json`
- `data/processed/outputs/FD002/fd002_anomaly_scores.csv`
- `data/processed/outputs/FD002/fd002_rul_predictions.csv`
- `data/processed/outputs/FD002/fd002_decision_support.csv`
- `data/processed/outputs/FD002/fd002_decision_support_report.json`
