# Streamlit Demo Runbook — JET-CUBE Decision Support (FD001–FD004)

Bu demo **sadece yerel artefact dosyalarını** okur; eğitim/yeniden üretim yapmaz.

## 1) Kurulum

```bash
pip install -r requirements_demo.txt
```

## 2) Çalıştırma

Repo kök dizininde:

```bash
streamlit run demo/streamlit_dashboard/streamlit_app.py
```

## 3) Input gereksinimleri (canonical)

Uygulama varsayılan olarak şu dizinleri sırayla dener:
- `demo/data/outputs/`
- `demo/decision_support_v2_outputs/`

Bu dizinler altında şu dosyaları otomatik keşfeder:

- `fd001_decision_support.csv`
- `fd002_decision_support.csv`
- `fd003_decision_support.csv`
- `fd004_decision_support.csv`

Opsiyonel olarak (varsa keşfedilir):

- `data/outputs/fd00x_anomaly_scores.csv`
- `data/outputs/fd00x_rul_predictions.csv`

`*_decision_support.csv` minimum şema:

- `dataset_id, split, engine_id, cycle`
- `rul_pred, anomaly_score`
- `decision_label, reason_codes, reason_text`
- `theta_rul_used, alpha_anomaly_used`

Dosyalardan biri yoksa uygulama UI’da hangi path’in beklendiğini net şekilde yazar.

## 4) Ekran / Panel açıklaması (beklenen)

- **Sol sidebar**:
  - Dataset seçimi (FD001–FD004)
  - Keşfedilen dosyaların repo-relative path listesi
- **Timeline**:
  - `rul_pred` (line)
  - `anomaly_score` (sağ eksen, 0–1)
  - `decision_label` değişimleri cycle boyunca renkli arka-plan şeritleriyle işaretlenir
- **Why? paneli**:
  - Seçili `cycle` için `reason_codes` ve `reason_text`
  - Seçili engine için top-5 `reason_codes` frekansı
- **Özet metrikleri**:
  - Satır sayısı
  - `decision_label` dağılımı (count)
  - `anomaly_score` ve `rul_pred` için min/p50/p95/max
