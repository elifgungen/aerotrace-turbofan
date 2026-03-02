# C-MAPSS Mevcut Decision-Support Özeti

Kaynaklar:
- `03_docs/Decision_Support/C-MAPSS/decision_logic.md`
- `05_demo/decision_support_runner.py`
- `03_docs/Decision_Support/C-MAPSS/data/outputs/fd001_decision_support.csv`
- `03_docs/Decision_Support/C-MAPSS/data/outputs/fd002_decision_support.csv`

## 1) Mevcut karar sınıfları (label)
V1 (4-sınıf) karar etiketleri:
- `Normal Operation`
- `Enhanced Monitoring`
- `Planned Maintenance`
- `Immediate Maintenance`

Runner içinde ayrıca V2 genişletilmiş state alanı var (`healthy/watch/degraded/critical`), fakat resmi minimal CSV kontratı V1 etiketleriyle üretiliyor.

## 2) Eşikler (θ_RUL, α_anomaly)
V1 eşik kurgusu:
- `theta_rul_used`: tek RUL eşiği (default: `theta_warn`)
- `alpha_anomaly_used`: tek anomaly eşiği (default: `alpha_warn`)

Gözlenen C-MAPSS örnekleri:
- `theta_rul_used = 50.0`
- `alpha_anomaly_used` dataset’e göre kalibre edilmiş (örn. FD001: `0.450324`, FD002: `0.790924`).

Not: `05_demo/decision_support_runner.py` içinde V2 için `theta_warn/theta_critical` ve `alpha_warn/alpha_critical` da var; ancak V1 CSV’de tek eşik çifti (`theta_rul_used`, `alpha_anomaly_used`) raporlanıyor.

## 3) Karar matrisi (2x2)
Mevcut V1 karar matrisi, iki boolean üzerinden çalışıyor:
- `RUL_low = (rul_pred <= theta_rul_used)`
- `ANOM_high = (anomaly_score >= alpha_anomaly_used)`

2x2 hücreler:
- `RUL_high & ANOM_low` -> `Normal Operation`
- `RUL_high & ANOM_high` -> `Enhanced Monitoring`
- `RUL_low & ANOM_low` -> `Planned Maintenance`
- `RUL_low & ANOM_high` -> `Immediate Maintenance`

## 4) Çıktı kolonları (decision_support.csv)
`fd001_decision_support.csv` / `fd002_decision_support.csv` kolonları:
- `engine_id`
- `cycle`
- `rul_pred`
- `anomaly_score`
- `decision_label`
- `reason_codes`
- `reason_text`
- `theta_rul_used`
- `alpha_anomaly_used`

## 5) Join key ve kolon bağlama bulgusu
Mevcut implementasyonun temel join anahtarı:
- `engine_id`, `cycle`

Ancak repo içindeki bazı CSV setlerinde (`split`, `dataset_id` birlikte bulunduğunda) sadece `engine_id+cycle` kullanımı duplicate/join patlaması oluşturabiliyor. Bu nedenle yeni adaptör katmanında join key otomatik keşfi gereklidir; mümkün olduğunda `dataset_id`, `split`, `engine_id`, `cycle` kombinasyonu tercih edilmelidir.

## 6) Legacy (v1) constraints
- Legacy v1 path, anomaly join öncesi duplicate kontrolünü `engine_id+cycle` üzerinde yapar.
- Bazı C-MAPSS anomaly dosyalarında aynı `engine_id+cycle` kombinasyonu farklı `split` altında tekrar edebilir.
- Bu durumda v1 path bilinçli olarak hata verir (duplicate key), sonuç üretmez.
- Bu davranış geriye uyumluluk nedeniyle bilerek korunmuştur; v1 mantığı değiştirilmemiştir.
- v2 adapter path join key keşfi yapar (`dataset_id/split/engine_id/cycle`) ve bu ayrımı doğru ele alır.
- C-MAPSS/N-CMAPSS yeni çalıştırmalar için önerilen yol: `--policy-config` ile v2 üretimidir.
