# Baseline Deviation Anomaly Pipeline (FD003 / FD004) — v1

Bu doküman, FD003/FD004 için **baseline deviation** anomali skor hattının nasıl koşturulacağını ve hangi artefact’ların üretileceğini tanımlar.

## Kapsam (bu PR)
- Decision-support entegrasyonu: **YOK**
- RUL runner’ları: **DEĞİŞMEDİ**

## Input gereksinimleri (processed)
Aşağıdaki dosyalar **zorunludur** (yoksa FAIL):
- `data/processed/train_FD003_full_norm.csv`
- `data/processed/test_FD003_full_norm.csv`
- `data/processed/train_FD004_full_norm.csv`
- `data/processed/test_FD004_full_norm.csv`

Minimum kolonlar:
- `engine_id` (int)
- `cycle` (int)
- sensör kolonları: allowlist’ten en az 1 tanesi (default allowlist `configs/anomaly_thresholds.json` içinde)

Not:
- `dataset_id` kolonunu script otomatik ekler (FD003/FD004).
- `engine_id` ve `cycle` asla feature listesine girmez.

## Config (tek kaynak)
- `configs/anomaly_thresholds.json`
  - `baseline_n`: per-engine baseline window (ilk N cycle)
  - `eps`: z-score denom stabilizasyonu
  - `mapping_mode`: `sigmoid`
  - `sigmoid_k`: sigmoid eğimi
  - `mapping_fit_on`: `train` (train-only fit kuralı)
  - `smooth_window`: rolling mean (per engine)
  - `sensor_allowlist`: kullanılacak sensörler (kesişim alınıp eksikler raporlanır)

## Repro komutları

### FD003
```bash
python scripts/anomaly_baseline_deviation.py --dataset FD003 --train_csv data/processed/train_FD003_full_norm.csv --test_csv data/processed/test_FD003_full_norm.csv --config configs/anomaly_thresholds.json --outdir data/outputs
python scripts/validate_anomaly_artifacts.py --dataset FD003 --train_csv data/processed/train_FD003_full_norm.csv --test_csv data/processed/test_FD003_full_norm.csv --scores_csv data/outputs/fd003_anomaly_scores.csv --report_json data/outputs/fd003_anomaly_report.json --mapping_json data/outputs/fd003_anomaly_mapping_params.json
```

Beklenen çıktı dosyaları:
- `data/outputs/fd003_anomaly_scores.csv`
- `data/outputs/fd003_anomaly_report.json`
- `data/outputs/fd003_anomaly_mapping_params.json`

### FD004
```bash
python scripts/anomaly_baseline_deviation.py --dataset FD004 --train_csv data/processed/train_FD004_full_norm.csv --test_csv data/processed/test_FD004_full_norm.csv --config configs/anomaly_thresholds.json --outdir data/outputs
python scripts/validate_anomaly_artifacts.py --dataset FD004 --train_csv data/processed/train_FD004_full_norm.csv --test_csv data/processed/test_FD004_full_norm.csv --scores_csv data/outputs/fd004_anomaly_scores.csv --report_json data/outputs/fd004_anomaly_report.json --mapping_json data/outputs/fd004_anomaly_mapping_params.json
```

Beklenen çıktı dosyaları:
- `data/outputs/fd004_anomaly_scores.csv`
- `data/outputs/fd004_anomaly_report.json`
- `data/outputs/fd004_anomaly_mapping_params.json`

## Output kontratı (scores CSV)
Her dataset için tek bir CSV yazılır (train+test satırları birlikte):
- kolonlar: `dataset_id`, `split`, `engine_id`, `cycle`, `anomaly_score`
- `split` değerleri: `train` / `test`
- join key uniqueness: `(dataset_id, split, engine_id, cycle)` unique olmalı
- `anomaly_score` 0–1 aralığında olmalı
