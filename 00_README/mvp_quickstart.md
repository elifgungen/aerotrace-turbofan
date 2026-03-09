# MVP Quickstart (≤3 dk) — JET-CUBE Karar Destek Demo

Bu quickstart yalnızca hazır artefact’ları okur; eğitim/yeniden üretim yapmaz.

## 1) Kurulum

Repo kökünde:

```bash
pip install -r requirements_demo.txt
```

## 2) Demo çalıştırma (Streamlit)

```bash
streamlit run app/streamlit_app.py
```

Uygulama `data/outputs/` altındaki `fd001..fd004` decision-support artefact’larını otomatik keşfeder.
Dosya yoksa UI’da hangi path’in beklendiğini açıkça gösterir.

## 3) Artefact’lar nerede?

Canonical çıktı klasörü: `data/outputs/`

Beklenen ana dosyalar:
- `data/outputs/fd001_decision_support.csv`
- `data/outputs/fd002_decision_support.csv`
- `data/outputs/fd003_decision_support.csv`
- `data/outputs/fd004_decision_support.csv`

Opsiyonel ama (varsa) otomatik keşfedilen eşleşen dosyalar:
- `data/outputs/fd00x_rul_predictions.csv`
- `data/outputs/fd00x_anomaly_scores.csv`

## 4) Repro komutları nerede?

Uçtan uca üretim/repro komutları: `docs/repro_commands.md`

Raw veri repo içinde değilse edinim/versiyon ve beklenen dosya isimleri: `docs/data_sources.md`

