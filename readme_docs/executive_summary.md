# Yönetici Özeti (1 sayfa) — AeroTrace Turbofan MRO Karar Destek Platformu

> **AeroTrace** by **AeroLith Systems** · v2.0

## Problem

Turbofan motor bakımında (MRO) doğru zamanda doğru aksiyonu almak kritik: **erken bakım** maliyet yaratır, **geç bakım** arıza riskini artırır. Operasyon ekibinin ihtiyacı; motorun yaşam döngüsü boyunca **kalan ömür (RUL)** ve **beklenmedik sapma/anomali** sinyallerini tek bir çerçevede görüp aksiyon alabilmektir.

## Çözüm

AeroTrace; her motor ve çevrim için:
- **RUL tahmini** — Gradient Boosting tabanlı ensemble model
- **Baseline deviation anomaly score** (0–1) — Mahalanobis distance + sigmoid mapping

üretir ve bunları insan-onaylı eşik politikası ile birleştirerek **4 seviyeli bakım kararı** çıktısı verir:

| Karar | Aksiyon |
|-------|---------|
| **Normal Operation** | Normal izleme |
| **Enhanced Monitoring** | Sıklaştırılmış izleme + teşhis |
| **Planned Maintenance** | Planlı bakım/inspection |
| **Immediate Maintenance** | Acil bakım değerlendirmesi |

**Nihai karar bakım mühendisinde kalır** — sistem otonom karar vermez, destek sağlar.

## Kapsam (11 senaryo)

### C-MAPSS (FD001–FD004)
NASA C-MAPSS — 4 senaryo, toplam 707 motor. Uçtan uca artefact üretim zinciri repo içinde mevcuttur.

### N-CMAPSS (DS01–DS07)
NASA N-CMAPSS — 7 senaryo, gerçekçi uçuş profilleri. Anomali ve karar destek pipeline'ı ile tam entegrasyon.

## Kilit Yetenekler

1. **Uçtan uca artefact zinciri:** RUL + anomaly + decision-support (11 senaryo)
2. **Tek kaynak eşik/policy yönetimi:** Tüm eşikler config dosyasından yönetilir
3. **Leakage-safe yaklaşım:** Train-only fit, duplicate/NaN kontrolleri
4. **İzlenebilirlik:** Her satır `(dataset_id, split, engine_id, cycle)` anahtarıyla join edilebilir
5. **Audit:** `policy_version`, `reason_codes`, `reason_text` ile geriye dönük denetlenebilirlik
6. **Web uygulaması:** Plotly.js tabanlı interaktif dashboard, 3D Digital Twin, Jüri Demo modu

## Demo / Görselleştirme

Ana platform: **AeroTrace Web Uygulaması** (`webapp/`)
- Statik hosting (Vercel CDN) — sunucu veya veritabanı gerektirmez
- 6 interaktif sayfa: Filo Görünümü, Motor Detay, 3D Digital Twin, Audit & Kanıt
- **Jüri Demo Modu:** 6 adımlı rehberli sunum
- **Live:** [https://dist-ebon-nine.vercel.app](https://dist-ebon-nine.vercel.app)

Alternatif (eski): Streamlit dashboard (`demo/streamlit_dashboard/`)

## Güven / Audit Edilebilirlik

- **Tek kaynak config:** `decision_support_thresholds.json`, `anomaly_thresholds.json`
- **Artefact raporlarında:** config hash, kullanılan eşikler, run_id ile iz sürülebilirlik
- **Data integrity:** Join key uniqueness, duplicate=0, NaN=0 kontrolleri
- **Reproducibility:** Tüm pipeline adımları belgelenmiş repro komutlarıyla tekrarlanabilir

## Kısıtlar (bilerek)

- Raw veri repo içinde değildir (lisans/boyut). Edinim bilgisi: `readme_docs/data_sources.md`
- Model inference süresi demo'da simüle edilir (gerçek zamanlı motor verisi bağlantısı yoktur)
- Eşik kalibrasyonu iş değeri odaklı optimizasyon gerektirir (Phase-2)

## Sonraki Adımlar (Phase-2)

- İş değeri odaklı eşik kalibrasyonu (maliyet/false-alarm vs missed-alarm)
- Alarm stabilizasyonu (hysteresis/debounce)
- Gerçek zamanlı veri bağlantısı (API + veritabanı katmanı)
- Daha ileri modelleme: DL-based RUL ve Autoencoder anomali (opsiyonel)
