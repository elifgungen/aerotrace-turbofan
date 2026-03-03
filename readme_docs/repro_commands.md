# Repro Commands (FD001 / FD002) — AeroTrace Pipeline Reproducibility

Bu doküman, **FD001** ve **FD002** için reproducibility zincirini (raw → processed → anomaly → decision-support v1) tek komutla çalıştırma komutlarını ve beklenen çıktıları listeler.

## Önkoşul: Raw veri
Raw CMAPSS dosyaları repo’da varsayılan olarak yoksa, aşağıdaki path’lere yerleştirin:
- `data/raw/CMAPSSData/train_FD001.txt`
- `data/raw/CMAPSSData/test_FD001.txt`
- `data/raw/CMAPSSData/RUL_FD001.txt`
- `data/raw/CMAPSSData/train_FD002.txt`
- `data/raw/CMAPSSData/test_FD002.txt`
- `data/raw/CMAPSSData/RUL_FD002.txt`

## FD001 — tek komutla repro
```bash
python scripts/build_fd001_preprocess.py \
  --raw-dir data/raw/CMAPSSData \
  --out-train data/processed/train_FD001_full_norm.csv \
  --out-test data/processed/test_FD001_full_norm.csv \
  --report-json data/outputs/fd001_preprocess_report.json

python scripts/anomaly_baseline_deviation.py \
  --dataset FD001 \
  --train_csv data/processed/train_FD001_full_norm.csv \
  --test_csv data/processed/test_FD001_full_norm.csv \
  --config configs/anomaly_thresholds.json \
  --outdir data/outputs

python scripts/standardize_rul_predictions.py \
  --dataset FD001 --split test \
  --in_csv notebooks/RUL/FD001/FD001_Ozcan_AllRaws/predictions_cycle_all_rows.csv \
  --pred_col pred_ensemble \
  --out_csv data/outputs/fd001_rul_predictions.csv

python scripts/build_decision_support_v1.py \
  --dataset FD001 \
  --rul_csv data/outputs/fd001_rul_predictions.csv \
  --anomaly_csv data/outputs/fd001_anomaly_scores.csv \
  --config configs/decision_support_thresholds.json \
  --out_csv data/outputs/fd001_decision_support.csv \
  --report_json data/outputs/fd001_decision_support_report.json
```

Beklenen çıktılar:
- `data/processed/train_FD001_full_norm.csv`
- `data/processed/test_FD001_full_norm.csv`
- `data/outputs/fd001_preprocess_report.json`
- `data/outputs/fd001_anomaly_scores.csv`
- `data/outputs/fd001_anomaly_report.json`
- `data/outputs/fd001_anomaly_mapping_params.json`
- `data/outputs/fd001_rul_predictions.csv`
- `data/outputs/fd001_decision_support.csv`
- `data/outputs/fd001_decision_support_report.json`

## FD002 — tek komutla repro
```bash
python scripts/build_fd002_preprocess.py \
  --raw-dir data/raw/CMAPSSData \
  --out-train data/processed/train_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --out-test data/processed/test_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --report-json data/outputs/fd002_preprocess_report.json

python scripts/build_fd002_anomaly.py \
  --train_csv data/processed/train_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --test_csv data/processed/test_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --config configs/anomaly_thresholds.json \
  --outdir data/outputs

python scripts/standardize_rul_predictions.py \
  --dataset FD002 --split test \
  --in_csv notebooks/RUL/FD002/FD002_Ozcan_All/fd002_test_predictions_FD002_LOCAL_REGIMEAWARE_SENSOR_ZSCORE_K6_ONEHOT.csv \
  --out_csv data/outputs/fd002_rul_predictions.csv

python scripts/build_decision_support_v1.py \
  --dataset FD002 \
  --rul_csv data/outputs/fd002_rul_predictions.csv \
  --anomaly_csv data/outputs/fd002_anomaly_scores.csv \
  --config configs/decision_support_thresholds.json \
  --out_csv data/outputs/fd002_decision_support.csv \
  --report_json data/outputs/fd002_decision_support_report.json
```

Beklenen çıktılar:
- `data/processed/train_FD002_regimeaware_sensor_zscore_k6_onehot.csv`
- `data/processed/test_FD002_regimeaware_sensor_zscore_k6_onehot.csv`
- `data/outputs/fd002_preprocess_report.json`
- `data/outputs/fd002_anomaly_scores.csv`
- `data/outputs/fd002_anomaly_report.json`
- `data/outputs/fd002_anomaly_mapping_params.json`
- `data/outputs/fd002_rul_predictions.csv`
- `data/outputs/fd002_decision_support.csv`
- `data/outputs/fd002_decision_support_report.json`

