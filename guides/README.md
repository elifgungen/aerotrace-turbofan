# HAVELSAN JET CUBE — Turbofan MVP (Jet-Cube)

Bu repo, **CFM56-7B sınıfı turbofan motorlar** için:
- **Kestirimci bakım (Predictive Maintenance)**
- **Karar-destek odaklı dijital ikiz yaklaşımı**

temelli bir MVP kurgusunu **NASA C-MAPSS / (N-)CMAPSS** gibi açık/sentetik veri setleriyle göstermeyi hedefler.

## Pipeline nasıl çalışır?
Bu MVP, otomatik bakım kararı vermez; **insan bakım mühendisine karar desteği** sağlar.

Uçtan uca akış:
1. **Veri**: `data/raw/` altına veri seti konur.
2. **Önişleme** (`notebooks/02_preprocess_fd001.ipynb`): ham veriden temiz/özellikli tablo üretir → `data/processed/`
3. **Model çıktıları**
   - **RUL tahmini** (`notebooks/03_rul_baseline_fd001.ipynb`): `fd001_rul_predictions.csv` → `data/outputs/`
   - **Anomali skoru** (`notebooks/04_anomaly_fd001.ipynb`): `fd001_anomaly_scores.csv` → `data/outputs/`
4. **Karar destek** (`notebooks/05_decision_support.ipynb`)
   - Girdi: `data/processed/fd001_processed.csv` + `data/outputs/*.csv`
   - Çıktı: `data/outputs/fd001_decision_support.csv`

## Hafta 1 (Elif) — Beklenen somut çıktılar
- Dummy veriyle çalışan **decision-support notebook’u** (`notebooks/05_decision_support.ipynb`)
- Repo’da herkesin uyacağı **net teknik akış** (bu dosya + `docs/weekly_updates.md`)
- Sonraki haftalarda eklenecek modeller için hazır iskelet (`data/`, `notebooks/`, `docs/`)

## Klasör yapısı
```
jet-cube-turbofan-mvp/
  data/
    raw/
    processed/
    outputs/
  notebooks/
  docs/
```

## Hızlı başlangıç
1. `notebooks/00_setup.ipynb` ile dizinleri ve bağımlılıkları hazırla.
2. `notebooks/05_decision_support.ipynb` çalıştır:
   - Hafta 1 için dummy CSV üretir
   - Karar-destek çıktısını `data/outputs/` altına yazar

## Documentation
Decision-support logic is defined in [docs/decision_logic.md](docs/decision_logic.md) and implemented in `notebooks/05_decision_support.ipynb`.
