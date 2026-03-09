# Yönetici Özeti (1 sayfa) — JET-CUBE Turbofan MRO Karar Destek MVP

## Kısa değerlendirme: 6 kritik iyileştirme
- Uçtan uca artefact zinciri: RUL + anomaly + decision-support (FD001–FD004)
- Tek kaynak eşik/policy yönetimi + raporlarda kullanılan değerlerin audit’i
- Leakage-safe yaklaşım ve veri bütünlüğü kontrolleri (duplicate/NaN=0)
- Join anahtarı standardı ile izlenebilirlik: `(dataset_id, split, engine_id, cycle)`
- Repo-relative demo (Streamlit) ile jüriye hızlı gösterim
- Raw veri repo dışı olsa bile “beklenen input” dokümantasyonu ve repro komutları

## Problem
Turbofan motor bakımında (MRO) doğru zamanda doğru aksiyonu almak kritik: **erken bakım** maliyet yaratır, **geç bakım** arıza riskini artırır. Operasyon ekibinin ihtiyacı; motorun yaşam döngüsü boyunca **kalan ömür (RUL)** ve **beklenmedik sapma/anomali** sinyallerini tek bir çerçevede görüp aksiyon alabilmektir.

## Çözüm (MVP yaklaşımı)
Bu MVP; her motor ve çevrim için:
- **RUL tahmini** (`rul_pred`)
- **Baseline deviation anomaly score** (`anomaly_score`, 0–1) — **MVP’de hızlı, açıklanabilir ve audit edilebilir** olduğu için seçildi.

üretir ve bunları tek kaynak eşik/policy ile birleştirerek **decision_label** (karar/öneri) çıktısı verir; bu çıktı operasyonel aksiyona doğrudan bağlanır: **Normal Operation → normal izleme**, **Enhanced Monitoring → sıklaştırılmış izleme**, **Planned Maintenance → planlı bakım planlama**, **Immediate Maintenance → acil bakım**.

## MVP kapsamı (C-MAPSS)
CMAPSS FD001–FD004 için uçtan uca **artefact üretim zinciri** repo içinde mevcuttur:
- `data/outputs/fd00x_rul_predictions.csv`
- `data/outputs/fd00x_anomaly_scores.csv`
- `data/outputs/fd00x_decision_support.csv`
- `data/outputs/fd00x_*_report.json` (audit/kanıt zinciri)

Kanıt formatı (teknik ama güçlü): tüm çıktılar `(dataset_id, split, engine_id, cycle)` anahtarıyla join edilebilir; **duplicate=0 ve NaN=0** koşulları doğrulanır.

## Güven / Audit edilebilirlik
MVP; “sonuç var” değil, “sonuç **kanıtlanabilir**” hedefiyle tasarlanmıştır:
- **Tek kaynak config**: `configs/decision_support_thresholds.json`, `configs/anomaly_thresholds.json`
- Artefact raporlarında **config hash** / kullanılan eşikler (`*_report.json`) ile iz sürülebilirlik
- **Leakage-safe ve data-integrity odaklı protokol**: train-only fit yaklaşımı + join/duplicate/NaN kontrolleri ile pipeline güvenilirliği.
- FD003/FD004 değerlendirme ve reproducibility raporları: `docs/fd003_protocol_fix_report.md`, `docs/fd004_repro_fix_report.md`

## Demo / Görselleştirme
Karar destek çıktıları, repo-relative çalışan bir Streamlit dashboard ile görselleştirilir:
- `app/streamlit_app.py`
- Çalıştırma kılavuzu: `docs/demo_runbook.md`

## Kısıtlar (bilerek)
- **Raw veri repo içinde değildir** (lisans/boyut). Beklenen dosyalar ve edinim bilgisi: `docs/data_sources.md` (ayrıca repro komutları: `docs/repro_commands.md`)
- Raw yoksa ilgili script’ler **FAIL** ederek beklenen raw dosyaları/şemayı açıkça raporlar (repro zinciri).

## Next steps (Phase‑2)
- İş değeri odaklı kalibrasyon: **threshold tuning** (maliyet/false-alarm vs missed-alarm, ARL/MTBF hedefleri) + alarm stabilizasyonu (hysteresis/debounce)
- (Opsiyonel) Daha ileri modelleme: **DL RUL** ve **Autoencoder anomaly** ile planın “ileri” kapsamı
