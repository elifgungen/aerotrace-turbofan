# MVP Sonuçları — Çıktı Yorumlama + Başarı Anlatısı (Jüri Dili)

- Generated at (UTC): `2026-01-31 12:19:08Z`
- Seed: `42`
- Figures: `figures_results`
- DOCX: `ENABLED`

## 0) Yönetici Özeti
Bu MVP; (i) `rul_pred` (kalan ömür tahmini) ve (ii) `anomaly_score` ([0,1]) üretip, bunları tek kaynak eşik/policy ile birleştirerek `decision_label` (operasyonel triage) çıktısı verir.
Kapsam: CMAPSS FD001–FD004 datasetleri için aynı contract ile çıktı üretimi.

| dataset | rul | anomaly | decision | report.json |
| --- | --- | --- | --- | --- |
| FD001 | FOUND | FOUND | FOUND | FOUND |
| FD002 | FOUND | FOUND | FOUND | FOUND |
| FD003 | FOUND | FOUND | FOUND | FOUND |
| FD004 | FOUND | FOUND | FOUND | FOUND |

En güçlü 3 kanıt (kanıtlı):
- Audit: `data/outputs/fd00x_decision_support_report.json` içinde kullanılan eşikler ve config hash raporlanır.
- Contract & integrity: join key `(dataset_id, split, engine_id, cycle)`; duplicate/NaN/Inf sayıları raporlanır.
- Leakage-safe: FD003/FD004 için protokol ve reproducibility raporları mevcutsa referanslanır.

## 1) Artefact Durumu & Sağlık Kontrolü
| dataset | rows | duplicates | NaN/Inf | rul<0 | anom_oob | anom_min/max | θ/α |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FD001 | 13096 | 0 | 0 | 0 | 0 | 0.323/0.999 | 50.000/0.456 |
| FD002 | 33991 | 0 | 0 | 0 | 0 | 0.380/1.000 | 50.000/0.683 |
| FD003 | 16596 | 0 | 0 | 0 | 0 | 0.259/1.000 | 50.000/0.422 |
| FD004 | 41214 | 0 | 0 | 0 | 0 | 0.365/0.926 | 50.000/0.717 |

## 1.1) MVP Closure Checklist (PASS/FAIL)
Bu tablo, ekip içi “bitti mi?” kontrolü için kısa bir PASS/FAIL özetidir. `overall=PASS` olması için: artefact’lar FOUND, duplicate/NaN/Inf=0, audit alanları mevcut, decision-support kural doğrulaması mismatch=0 ve (FD003/FD004) protokol raporları bulunur.

| dataset | artefacts | integrity | audit | leakage_docs | consistency | overall |
| --- | --- | --- | --- | --- | --- | --- |
| FD001 | PASS | PASS | PASS | N/A | PASS | PASS |
| FD002 | PASS | PASS | PASS | N/A | PASS | PASS |
| FD003 | PASS | PASS | PASS | PASS | PASS | PASS |
| FD004 | PASS | PASS | PASS | PASS | PASS | PASS |

## 2) Çıktıları Nasıl Okumalıyız?
- `rul_pred` yüksek → motorun kalan ömrü var; trend olarak düşüş → bakım penceresi yaklaşıyor.
- `anomaly_score` baseline’dan sapma ölçüsüdür; tek başına arıza değildir, alarm sinyali olarak okunur.
- `decision_label` operasyonel triage içindir; otomatik bakım emri değildir (operatöre önceliklendirme sağlar).

## 2.1) 3 Dakikada Doğrulama (Arkadaşların için)
1) Contract & integrity: Bölüm 1 ve 1.1’de duplicate/NaN/Inf=0 ve join key standardı kontrol edilir.
2) Audit: her dataset için `data/outputs/fd00x_decision_support_report.json` içinde `config_sha256` ve `theta/alpha` görülür.
3) Leakage-safe (FD003/FD004): `docs/fd003_protocol_fix_report.md` ve `docs/fd004_repro_fix_report.md` varlığı/özeti kontrol edilir.
4) Reproduce: `docs/repro_commands.md` ve dashboard için `docs/demo_runbook.md` izlenir.

## 3) Dataset bazlı analiz (FD001–FD004)
### FD001
#### 3.1 Özet metrikler
- Split: `test`
- RUL (min/p50/p95/max): `4.867 / 117.295 / 125.000 / 125.000`
- Anomaly (min/p50/p95/max): `0.323 / 0.438 / 0.785 / 0.999`
- Alarm Rate (Enhanced+Immediate): `38.32%`
- Immediate Rate: `4.74%`
- Top-5 reason_codes: `RUL_HIGH` (12475), `ANOM_LOW` (8077), `ANOM_HIGH` (5019), `RUL_LOW` (621)

#### 3.2 Grafikler
![](figures_results/fd001_engine_49_timeline.png)
![](figures_results/fd001_distributions.png)
![](figures_results/fd001_decision_counts.png)

#### 3.3 Ne görüyoruz? (kanıtlı yorum)
- Bu dataset’te decision_label dağılımı: Normal=8077 (%61.68), Enhanced=4398 (%33.58), Planned=0 (%0.00), Immediate=621 (%4.74).
- RUL dağılımı (min/p50/p95/max): 4.867 / 117.295 / 125.000 / 125.000; bu dağılım bakım penceresine yaklaşımı cycle bazında izlemeyi mümkün kılar.
- Anomali dağılımı (min/p50/p95/max): 0.323 / 0.438 / 0.785 / 0.999; anomaly_score yüksekliği baseline sapmasının arttığını gösterir (tek başına arıza değildir).
- Eşikler (audit): θ_RUL=50.000 ve α_anomaly=0.456. Bu eşikler aynı dataset/split içinde sabit tutulur ve grafikte çizgilerle gösterilir.
- RUL<=θ oranı: %4.74. Bu bölgede Planned/Immediate oranı %100.00; RUL>θ iken aynı oran %0.00 (operasyonel triage mantığıyla tutarlı ayrışma).
- anomaly>=α oranı: %38.32. anomaly>=α iken alarm (Enhanced/Immediate) oranı %100.00; anomaly<α iken %0.00 (anomali sinyalinin alarm yoğunluğuna etkisi).
- Anomali üst kuyruk (p95=0.785) üzerinde Enhanced Monitoring oranı %40.15. Bu, yüksek sapma dönemlerinde izleme modunun daha sık tetiklendiğine dair gözlemdir.
- Top reason_codes: `RUL_HIGH` (12475), `ANOM_LOW` (8077), `ANOM_HIGH` (5019), `RUL_LOW` (621).
- Seçili örnek engine: engine_id=49 (en uzun timeline; tie-break seed=42). Timeline figüründe işaretlenen cycle=23 çevresinde label geçişleri ve eşik çizgileri birlikte okunur.

### FD002
#### 3.1 Özet metrikler
- Split: `test`
- RUL (min/p50/p95/max): `0.360 / 116.071 / 125.000 / 125.000`
- Anomaly (min/p50/p95/max): `0.380 / 0.531 / 0.636 / 1.000`
- Alarm Rate (Enhanced+Immediate): `1.57%`
- Immediate Rate: `0.10%`
- Top-5 reason_codes: `ANOM_LOW` (33458), `RUL_HIGH` (31678), `RUL_LOW` (2313), `ANOM_HIGH` (533)

#### 3.2 Grafikler
![](figures_results/fd002_engine_65_timeline.png)
![](figures_results/fd002_distributions.png)
![](figures_results/fd002_decision_counts.png)

#### 3.3 Ne görüyoruz? (kanıtlı yorum)
- Bu dataset’te decision_label dağılımı: Normal=31180 (%91.73), Enhanced=498 (%1.47), Planned=2278 (%6.70), Immediate=35 (%0.10).
- RUL dağılımı (min/p50/p95/max): 0.360 / 116.071 / 125.000 / 125.000; bu dağılım bakım penceresine yaklaşımı cycle bazında izlemeyi mümkün kılar.
- Anomali dağılımı (min/p50/p95/max): 0.380 / 0.531 / 0.636 / 1.000; anomaly_score yüksekliği baseline sapmasının arttığını gösterir (tek başına arıza değildir).
- Eşikler (audit): θ_RUL=50.000 ve α_anomaly=0.683. Bu eşikler aynı dataset/split içinde sabit tutulur ve grafikte çizgilerle gösterilir.
- RUL<=θ oranı: %6.80. Bu bölgede Planned/Immediate oranı %100.00; RUL>θ iken aynı oran %0.00 (operasyonel triage mantığıyla tutarlı ayrışma).
- anomaly>=α oranı: %1.57. anomaly>=α iken alarm (Enhanced/Immediate) oranı %100.00; anomaly<α iken %0.00 (anomali sinyalinin alarm yoğunluğuna etkisi).
- Anomali üst kuyruk (p95=0.636) üzerinde Enhanced Monitoring oranı %29.29. Bu, yüksek sapma dönemlerinde izleme modunun daha sık tetiklendiğine dair gözlemdir.
- Top reason_codes: `ANOM_LOW` (33458), `RUL_HIGH` (31678), `RUL_LOW` (2313), `ANOM_HIGH` (533).
- Seçili örnek engine: engine_id=65 (en uzun timeline; tie-break seed=42). Timeline figüründe işaretlenen cycle=118 çevresinde label geçişleri ve eşik çizgileri birlikte okunur.

### FD003
#### 3.1 Özet metrikler
- Split: `test`
- RUL (min/p50/p95/max): `3.964 / 120.802 / 125.000 / 125.000`
- Anomaly (min/p50/p95/max): `0.259 / 0.412 / 0.977 / 1.000`
- Alarm Rate (Enhanced+Immediate): `45.84%`
- Immediate Rate: `3.62%`
- Top-5 reason_codes: `RUL_HIGH` (15996), `ANOM_LOW` (8989), `ANOM_HIGH` (7607), `RUL_LOW` (600)

#### 3.2 Grafikler
![](figures_results/fd003_engine_24_timeline.png)
![](figures_results/fd003_distributions.png)
![](figures_results/fd003_decision_counts.png)

#### 3.3 Ne görüyoruz? (kanıtlı yorum)
- Bu dataset’te decision_label dağılımı: Normal=8989 (%54.16), Enhanced=7007 (%42.22), Planned=0 (%0.00), Immediate=600 (%3.62).
- RUL dağılımı (min/p50/p95/max): 3.964 / 120.802 / 125.000 / 125.000; bu dağılım bakım penceresine yaklaşımı cycle bazında izlemeyi mümkün kılar.
- Anomali dağılımı (min/p50/p95/max): 0.259 / 0.412 / 0.977 / 1.000; anomaly_score yüksekliği baseline sapmasının arttığını gösterir (tek başına arıza değildir).
- Eşikler (audit): θ_RUL=50.000 ve α_anomaly=0.422. Bu eşikler aynı dataset/split içinde sabit tutulur ve grafikte çizgilerle gösterilir.
- RUL<=θ oranı: %3.62. Bu bölgede Planned/Immediate oranı %100.00; RUL>θ iken aynı oran %0.00 (operasyonel triage mantığıyla tutarlı ayrışma).
- anomaly>=α oranı: %45.84. anomaly>=α iken alarm (Enhanced/Immediate) oranı %100.00; anomaly<α iken %0.00 (anomali sinyalinin alarm yoğunluğuna etkisi).
- Anomali üst kuyruk (p95=0.977) üzerinde Enhanced Monitoring oranı %48.80. Bu, yüksek sapma dönemlerinde izleme modunun daha sık tetiklendiğine dair gözlemdir.
- Top reason_codes: `RUL_HIGH` (15996), `ANOM_LOW` (8989), `ANOM_HIGH` (7607), `RUL_LOW` (600).
- Seçili örnek engine: engine_id=24 (en uzun timeline; tie-break seed=42). Timeline figüründe işaretlenen cycle=24 çevresinde label geçişleri ve eşik çizgileri birlikte okunur.

### FD004
#### 3.1 Özet metrikler
- Split: `test`
- RUL (min/p50/p95/max): `1.939 / 120.512 / 125.000 / 125.000`
- Anomaly (min/p50/p95/max): `0.365 / 0.532 / 0.644 / 0.926`
- Alarm Rate (Enhanced+Immediate): `0.95%`
- Immediate Rate: `0.13%`
- Top-5 reason_codes: `ANOM_LOW` (40822), `RUL_HIGH` (39529), `RUL_LOW` (1685), `ANOM_HIGH` (392)

#### 3.2 Grafikler
![](figures_results/fd004_engine_25_timeline.png)
![](figures_results/fd004_distributions.png)
![](figures_results/fd004_decision_counts.png)

#### 3.3 Ne görüyoruz? (kanıtlı yorum)
- Bu dataset’te decision_label dağılımı: Normal=39189 (%95.09), Enhanced=340 (%0.82), Planned=1633 (%3.96), Immediate=52 (%0.13).
- RUL dağılımı (min/p50/p95/max): 1.939 / 120.512 / 125.000 / 125.000; bu dağılım bakım penceresine yaklaşımı cycle bazında izlemeyi mümkün kılar.
- Anomali dağılımı (min/p50/p95/max): 0.365 / 0.532 / 0.644 / 0.926; anomaly_score yüksekliği baseline sapmasının arttığını gösterir (tek başına arıza değildir).
- Eşikler (audit): θ_RUL=50.000 ve α_anomaly=0.717. Bu eşikler aynı dataset/split içinde sabit tutulur ve grafikte çizgilerle gösterilir.
- RUL<=θ oranı: %4.09. Bu bölgede Planned/Immediate oranı %100.00; RUL>θ iken aynı oran %0.00 (operasyonel triage mantığıyla tutarlı ayrışma).
- anomaly>=α oranı: %0.95. anomaly>=α iken alarm (Enhanced/Immediate) oranı %100.00; anomaly<α iken %0.00 (anomali sinyalinin alarm yoğunluğuna etkisi).
- Anomali üst kuyruk (p95=0.644) üzerinde Enhanced Monitoring oranı %16.50. Bu, yüksek sapma dönemlerinde izleme modunun daha sık tetiklendiğine dair gözlemdir.
- Top reason_codes: `ANOM_LOW` (40822), `RUL_HIGH` (39529), `RUL_LOW` (1685), `ANOM_HIGH` (392).
- Seçili örnek engine: engine_id=25 (en uzun timeline; tie-break seed=42). Timeline figüründe işaretlenen cycle=468 çevresinde label geçişleri ve eşik çizgileri birlikte okunur.

## 4) Neden MVP Başarılı? (kanıtlı argümanlar)
### A) Contract & Data Integrity
- Join key standardı: `(dataset_id, split, engine_id, cycle)`
- FD001: duplicates=0 NaN/Inf=0 rul<0=0 anom_oob=0
- FD002: duplicates=0 NaN/Inf=0 rul<0=0 anom_oob=0
- FD003: duplicates=0 NaN/Inf=0 rul<0=0 anom_oob=0
- FD004: duplicates=0 NaN/Inf=0 rul<0=0 anom_oob=0

### B) Auditability
- FD001: config=`configs/decision_support_thresholds.json` sha256=`3274ceced0f57dd28bb3dce81d7647324d27f5d51991a29cc1ca7c33e996b895` θ=50.0 α=0.4560538176011786
- FD002: config=`configs/decision_support_thresholds.json` sha256=`3274ceced0f57dd28bb3dce81d7647324d27f5d51991a29cc1ca7c33e996b895` θ=50.0 α=0.6826815249047569
- FD003: config=`configs/decision_support_thresholds.json` sha256=`3274ceced0f57dd28bb3dce81d7647324d27f5d51991a29cc1ca7c33e996b895` θ=50.0 α=0.4217709250924709
- FD004: config=`configs/decision_support_thresholds.json` sha256=`3274ceced0f57dd28bb3dce81d7647324d27f5d51991a29cc1ca7c33e996b895` θ=50.0 α=0.7172891631892632

### C) Leakage-safe yaklaşım
- FD003: FOUND `docs/fd003_protocol_fix_report.md` (keywords: GroupKFold, test, OOF, leak)
  Özet: Test holdout’un model seçimi/early-stopping için kullanılmadığı ve CV’nin engine bazlı yapıldığı protokol raporlanır.
- FD004: FOUND `docs/fd004_repro_fix_report.md` (keywords: BASE, A, B, repo-relative, train-only)
  Özet: Varyant kapsamı ve reproducibility (path, train-only fit, raporlama) tutarlılık raporu ile izlenebilir.

### D) Decision-support consistency
- Verifier: FOUND `scripts/build_decision_support_v1.py`; seed=42 ile 50 satır örnek üzerinde doğrulama.
  - FD001: checked=50 decision_label_mismatches=0 reason_codes_mismatches=0
  - FD002: checked=50 decision_label_mismatches=0 reason_codes_mismatches=0
  - FD003: checked=50 decision_label_mismatches=0 reason_codes_mismatches=0
  - FD004: checked=50 decision_label_mismatches=0 reason_codes_mismatches=0

## 5) Sınırlamalar ve Riskler (dürüst)
- Raw veri repo dışı (lisans/boyut): `docs/data_sources.md` + repro komutları `docs/repro_commands.md`
- Threshold tuning saha hedeflerine göre kalibre edilecek (maliyet/false-alarm vs missed-alarm, ARL/MTBF).
- Dashboard bir decision-support demonstratörüdür; otomatik bakım emri değildir.
- Drift riski: gerçek telemetri geldiğinde izleme/yeniden kalibrasyon gerekir.

## 6) Sonuç ve Next steps
- Saha hedefleriyle threshold calibration (cost/ARL/MTBF) planı oluştur.
- Alarm stabilizasyonu: hysteresis/debounce parametrelerinin operasyonel kalibrasyonu.
- Gerçek telemetri ingest (Phase‑2): aynı arayüzle canlı veri akışına geçiş.
- İzleme: drift + veri kalitesi kontrolleri (contract + audit) rutinleştir.
- (Opsiyonel) DL-RUL / Autoencoder anomaly PoC: core value decision-support’u desteklemek için.
