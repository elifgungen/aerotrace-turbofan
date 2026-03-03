# Anomali Pipeline — AeroTrace

Bu doküman, AeroTrace'in **baseline deviation** anomali skor pipeline'ını tanımlar.

---

## Yöntem: Baseline Deviation Anomaly

Her motor için:
1. İlk N çevrim "sağlıklı baseline" olarak kabul edilir
2. Sonraki çevrimlerde sensör değerlerinin baseline'dan sapması ölçülür
3. Sapma skoru sigmoid mapping ile [0, 1] aralığına normalize edilir
4. Smoothing (EMA/rolling mean) uygulanır

Sonuç: Her `(engine_id, cycle)` için `anomaly_score ∈ [0, 1]`

---

## C-MAPSS Pipeline (FD001–FD004)

### Input Gereksinimleri
İşlenmiş CSV dosyaları (normalize edilmiş):
- `data/processed/.../train_FD00x_*.csv`
- `data/processed/.../test_FD00x_*.csv`

Minimum kolonlar: `engine_id`, `cycle`, sensör kolonları (allowlist'ten)

### Config (tek kaynak)
`configs/anomaly_thresholds.json`:
- `baseline_n`: Per-engine baseline window (ilk N çevrim)
- `eps`: Z-score denom stabilizasyonu
- `mapping_mode`: `sigmoid`
- `sigmoid_k`: Sigmoid eğimi
- `mapping_fit_on`: `train` (train-only fit kuralı)
- `smooth_window`: Rolling mean (per engine)
- `sensor_allowlist`: Kullanılacak sensörler

### Repro Komutları

```bash
# FD001
python scripts/anomaly_baseline_deviation.py \
  --dataset FD001 \
  --train_csv data/processed/.../train_FD001_*.csv \
  --test_csv data/processed/.../test_FD001_*.csv \
  --config configs/anomaly_thresholds.json \
  --outdir data/outputs

# FD002–FD004 için aynı pattern
```

### Çıktılar
Her dataset için:
- `fd00x_anomaly_scores.csv` — Anomali skorları
- `fd00x_anomaly_report.json` — Audit raporu
- `fd00x_anomaly_mapping_params.json` — Sigmoid mapping parametreleri

---

## N-CMAPSS Pipeline (DS01–DS07)

### Input Gereksinimleri
```
notebooks/Anomaly/N-CMAPSS/data/DS0x/
├── train_DS0x_v0.csv
├── test_DS0x_v0.csv
├── scaler_DS0x_v0.json
└── manifest.json
```

### Repro Komutu

```bash
python notebooks/Anomaly/N-CMAPSS/scripts/compute_anomaly_ncmapss.py
```

### Çıktılar
```
notebooks/Anomaly/N-CMAPSS/OUTPUTS/
├── ncmapss_DS01_anomaly_scores.csv
├── ncmapss_DS02_anomaly_scores.csv
├── ...
└── ncmapss_DS07_anomaly_scores.csv
```

---

## Karar Destek Entegrasyonu

Anomali skorları, karar destek pipeline'ına girdi olarak beslenir:

```
anomaly_scores.csv + rul_predictions.csv
        │
        ▼  (policy_engine.py)
  decision_support.csv
        │
        ▼  (preprocess_all_datasets.py)
  webapp JSON (fleet_summary.json + engine_*.json)
```

Karar matrisi:
- `anomaly_score > α_high` → anomali ON
- `rul < θ` → RUL düşük
- Bu iki koşulun kombinasyonu → 4 seviyeli karar etiketi

---

## Output Kontratı

Her dataset CSV çıktısında:
- Kolonlar: `dataset_id`, `split`, `engine_id`, `cycle`, `anomaly_score`
- `split`: `train` / `test`
- Join key uniqueness: `(dataset_id, split, engine_id, cycle)` unique
- `anomaly_score`: [0, 1] aralığında
- Train-only fit: Mapping parametreleri sadece train verisinden öğrenilir
