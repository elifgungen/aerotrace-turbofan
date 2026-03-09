# N-CMAPSS Anomaly Çalışma Raporu

Tarih: 2026-02-10  
Kapsam: DS01, DS02, DS03, DS04, DS05, DS06, DS07

## 1) Yöntem ve Input Contract
Anomaly skorları Mahalanobis (LedoitWolf) yaklaşımı ile üretildi.
Model girdisi yalnızca scaler `feature_columns` (72 kolon) olacak şekilde kısıtlandı.

Contract özet:
- Çıktı kolonları: `dataset_id, split, engine_id, cycle, anomaly_score, anomaly_raw`
- `split` yalnızca `train/test`
- `anomaly_score` aralığı `[0,1]`
- Key duplicate yok (`dataset_id, split, engine_id, cycle`)
- `NaN / Inf` yok

## 2) Output Doğrulama Sonuçları (DS01-DS07)
Aşağıdaki kontrollerin tamamı **PASS**:
- Zorunlu kolonlar mevcut
- Split değerleri doğru (`train/test`)
- Duplicate key yok
- Score aralığı ihlali yok
- NaN/Inf yok

### Dataset Bazlı Özet
| Dataset | Toplam Satır | Train | Test | Train Mean Score | Test Mean Score | Contract |
|---|---:|---:|---:|---:|---:|---|
| DS01 | 894 | 553 | 341 | 0.0347 | 0.0286 | PASS |
| DS02 | 648 | 446 | 202 | 0.0169 | 0.3967 | PASS |
| DS03 | 1101 | 663 | 438 | 0.0380 | 0.0573 | PASS |
| DS04 | 856 | 512 | 344 | 0.0320 | 0.0581 | PASS |
| DS05 | 818 | 491 | 327 | 0.0328 | 0.0458 | PASS |
| DS06 | 797 | 475 | 322 | 0.0325 | 0.0913 | PASS |
| DS07 | 812 | 468 | 344 | 0.0219 | 0.0426 | PASS |

Not: DS02 test dağılımı belirgin biçimde daha yüksek anomal görünüyor; bu teknik olarak mümkün bir domain-shift sinyalidir, ayrıca threshold kalibrasyonunda dikkate alınmalıdır.

## 3) Senaryo A/B Audit (RUL Split Semantiği) — DS01-DS04
Audit scripti: `/Users/elifgungen/Downloads/JET-CUBE/audit_ncmapss_scenario.py`

Karar kuralı:
- Eğer `|K_rul_train ∩ K_test| > 0` veya `|K_rul_val ∩ K_test| > 0` ise **Senaryo B**
- Aksi halde **Senaryo A**

### Sonuç
| Dataset | VERDICT | \\|K_rul_train ∩ K_test\\| | \\|K_rul_val ∩ K_test\\| | \\|K_rul_test ∩ K_train\\| | Train Coverage | Test Coverage |
|---|---|---:|---:|---:|---:|---:|
| DS01 | A | 0 | 0 | 0 | 100% | 100% |
| DS02 | A | 0 | 0 | 0 | 100% | 100% |
| DS03 | A | 0 | 0 | 0 | 100% | 100% |
| DS04 | A | 0 | 0 | 0 | 100% | 100% |

Yorum:
- Mevcut bulgu **Senaryo A** ile uyumlu: canonical test key'leri RUL train/val'e sızmıyor.
- Bu nedenle retrain zorunluluğu görünmüyor.
- Sorun, model öğreniminden çok RUL export split semantiği (`val`) ile anomaly split semantiği (`test`) uyumsuzluğudur.

## 4) Merge Uyum Etkisi (RUL + Anomaly)
RUL split seti: `{train, val, test}`  
Anomaly split seti: `{train, test}`

Bu nedenle strict join key `(dataset_id, split, engine_id, cycle)` ile birleşimde:
- `val` satırları doğrudan eşleşmez,
- train splitinde satır kaybı olur.

## 5) Karar ve Öneri
### Retrain gerekli mi?
- Mevcut kanıta göre (DS01-DS04): **Hayır, zorunlu değil.**

### Minimum gerekli aksiyonlar
1. RUL output split alanını canonical train/test semantiğine göre yeniden üret (re-label/re-export).
2. Decision-support birleşiminden önce key audit çalıştır:
   - `(dataset_id, split, engine_id, cycle)` için kayıp satır = 0
3. Final metrikleri canonical protokole göre raporla.

## 6) Kanıt Dosyaları
- Anomaly outputs: `/Users/elifgungen/Downloads/N-CMAPSS 2/OUTPUTS/ncmapss_DS*_anomaly_scores.csv`
- Senaryo audit JSON'ları:
  - `/private/tmp/ds01_scenario_audit.json`
  - `/private/tmp/ds02_scenario_audit.json`
  - `/private/tmp/ds03_scenario_audit.json`
  - `/private/tmp/ds04_scenario_audit.json`

