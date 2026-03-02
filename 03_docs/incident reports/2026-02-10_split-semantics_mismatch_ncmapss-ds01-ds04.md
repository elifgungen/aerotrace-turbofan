# N-CMAPSS Split-Semantics Audit Raporu

Tarih: 2026-02-10  
Kapsam: DS01, DS02, DS03, DS04 (RUL output mevcut olan set)

## 1) Problem Nasıl Fark Edildi?
Decision-support öncesi RUL ve anomaly çıktıları key-bazlı karşılaştırılırken aşağıdaki semantik fark tespit edildi:

- RUL split seti: `{train, val, test}`
- Anomaly split seti: `{train, test}`

İlk bakışta sadece isim farkı (`val` vs `test`) gibi görünse de,
strict merge key `(dataset_id, split, engine_id, cycle)` ile denetimde satır kaybı olduğu görüldü.

## 2) Kök Neden (Root Cause)
Kök neden, model öğreniminden çok **export split semantiği farkı**:

- `val` satırları canonical train içi holdout segmentini temsil ediyor.
- Anomaly tarafı canonical train/test split'i birebir kullanıyor.
- Bu nedenle RUL `train` satır sayısı anomaly `train` ile birebir aynı olmuyor.

Bu durum, doğrudan leakage kanıtı değildir; semantik hizalama problemidir.

## 3) DS01–DS04 Kanıt Tablosu (Senaryo A/B Audit)

Karar kuralı:
- Eğer `|K_rul_train ∩ K_test| > 0` veya `|K_rul_val ∩ K_test| > 0` ise **Senaryo B**
- Aksi halde **Senaryo A**

| Dataset | Verdict | \|K_rul_train ∩ K_test\| | \|K_rul_val ∩ K_test\| | \|K_rul_test ∩ K_train\| | Train Coverage (RUL train+val -> canonical train) | Test Coverage (RUL test -> canonical test) | Strict Merge Key Loss (RUL-only / Anomaly-only) |
|---|---|---:|---:|---:|---:|---:|---|
| DS01 | A | 0 | 0 | 0 | 100% | 100% | 100 / 100 |
| DS02 | A | 0 | 0 | 0 | 100% | 100% | 82 / 82 |
| DS03 | A | 0 | 0 | 0 | 100% | 100% | 71 / 71 |
| DS04 | A | 0 | 0 | 0 | 100% | 100% | 87 / 87 |

Yorum:
- Leakage göstergesi olan kesişimler `0`.
- Canonical kapsama `%100/%100`.
- Strict merge key kaybı, split etiket semantiği farkından kaynaklanıyor (`val` nedeniyle).

## 4) Senaryo Kararı
Bu çalışma için karar: **Senaryo A**.

Anlamı:
- Model tarafında canonical test sızıntısı kanıtı yok.
- Sorun, export ve split semantiği hizalanmadığı için join katmanında kayıp oluşması.

## 5) Çözüm Stratejisi

### 5.1 Hızlı ve güvenli düzeltme (retrain olmadan)
1. Canonical split'i tek kaynak yap (`train_<DS>_v0.csv`, `test_<DS>_v0.csv`).
2. RUL output split alanını bu kaynağa göre yeniden üret (re-label/re-export).
3. Decision-support merge'inden önce zorunlu audit koş:
   - `(dataset_id, split, engine_id, cycle)` key-loss = 0

### 5.2 Raporlama disiplini
1. Final metrikleri canonical protokolde tekrar raporla.
2. Dokümantasyona split-semantic mapping notunu ekle.

### 5.3 Ne zaman retrain gerekir?
Aşağıdaki durumlardan biri doğrulanırsa:
- `K_rul_train ∩ K_test` veya `K_rul_val ∩ K_test` > 0
- Canonical test kayıtları fit/selection sürecine karışmışsa

## 6) Neden Retrain Değil?
Bu auditte leakage kesişimi bulunmadı ve canonical kapsamalar tam.
Dolayısıyla zorunlu aksiyon modeli yeniden eğitmek değil, split semantiğini canonical kaynağa hizalayıp
RUL export'u yeniden almak.

## 7) Kanıt ve Reprodüksiyon
- Audit script: `AeroTrace/audit_ncmapss_scenario.py`
- JSON çıktıları:
  - `/private/tmp/ds01_scenario_audit.json`
  - `/private/tmp/ds02_scenario_audit.json`
  - `/private/tmp/ds03_scenario_audit.json`
  - `/private/tmp/ds04_scenario_audit.json`

