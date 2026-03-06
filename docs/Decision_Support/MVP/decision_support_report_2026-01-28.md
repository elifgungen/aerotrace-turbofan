# Decision Support Katmanı — Uygulama ve Kanıt Raporu (2026-01-28)

Bu rapor, repo’daki decision-support katmanının **FD001/FD002 RUL tahminleri + anomaly skorları** ile **MVP seviyesinde çalıştığını**, hangi dosyaların üretildiğini ve nasıl yeniden üretileceğini (repro) özetler.

## 0) Tek Kaynak Config (Audit)

Eşik/policy parametreleri “dokümana gömülü default” yerine tek bir config’ten yönetilir:
- `config/decision_support_thresholds.json`

Runner `--config` ile bu dosyayı okur ve kullanılan değerleri CSV/JSON çıktılara yazar (audit).

## 1) Amaç ve Kapsam

**Amaç:** `(engine_id, cycle)` bazında:
- `rul_pred` (cycle cinsinden kalan ömür tahmini) ve
- `anomaly_score` ([0,1], yüksek=anomali yüksek)

bilgilerini birleştirip **audit edilebilir** ve **deterministik** decision-label (bakım önerisi) üretmek.

**Kapsam (MVP):**
- Headless (script) çalışma; notebook’a bağımlı değil.
- Join doğrulaması (duplicate engelleme).
- V1 “ince kontrat” çıktısı + V2 “zengin/audit” çıktısı.

## 2) Minimal Contract (V1) — Resmi MVP Çıktısı

V1 çıktı dosyaları:
- FD001: `data/outputs/fd001_decision_support.csv`
- FD002: `data/outputs/fd002_decision_support.csv`

V1 kolonları (birebir):
- `engine_id`, `cycle`, `rul_pred`, `anomaly_score`
- `decision_label`
- `reason_codes`
- `reason_text`
- `theta_rul_used`, `alpha_anomaly_used`

V1 label seti (4 durum):
- `Normal Operation`
- `Enhanced Monitoring`
- `Planned Maintenance`
- `Immediate Maintenance`

> Not: V1 policy’de tek eşik vardır: `θ_RUL` ve `α_anomaly`. Varsayılan olarak `theta_rul_used = θ_warn`, `alpha_anomaly_used = α_warn` seçilir (istersen override edebilirsin).

## 3) Zengin Output (V2) — Audit + Operasyonel Stabilizasyon

V2 çıktı dosyaları (dashboard/debug için daha zengin):
- FD001: `demo/demo output/fd001_decision_support_baseline_deviation.csv`
- FD002: `demo/demo output/fd002_decision_support_with_anomaly.csv`

V2, **V1 kolonlarını da içerir** (geriye dönük uyum) ve üzerine şu alanları ekler:
- `policy_version` (`v2`)
- `rul_pred_used`, `anomaly_score_used` (smoothing sonrası)
- `state` (`healthy/watch/degraded/critical`) + `recommended_action`
- `contributing_signals` (detaylı reason listesi; debounce/hysteresis sinyalleri dahil)
- `risk_score` / `risk_driver`
- kullanılan eşikler: `theta_warn_used`, `theta_critical_used`, `alpha_warn_used`, `alpha_critical_used`
- debounce/hysteresis parametreleri: `anom_debounce_*_used`, `alpha_hysteresis_delta_used`

## 4) Implementasyon Dosyaları

**Ana runner (CLI):**
- `demo/decision_support_runner.py`

**Görselleştirme (kanıt plot):**
- `demo/plot_decision_support_examples.py`

**Sentetik/smoke test yardımcıları:**
- `demo/simulate_anomaly_scores.py`
- `demo/smoke_test_decision_support_synthetic.py`

**Karar mantığı dokümanı (spec):**
- `docs/Decision_Support/decision_logic.md`

## 5) Join + Validasyon (Sessiz Hata Engelleyiciler)

Runner şu kontrolleri yapar:
- `engine_id` ve `cycle` zorunlu.
- RUL kolonu `--rul-col` ile seçilir; verilmezse otomatik bulunur (`rul_pred`, `RUL_pred`, `pred_ensemble`, `y_pred`).
- Anomaly varsa join `how="left"` ile yapılır (sessiz satır düşürme yok).
- Duplicate koruması: `validate="one_to_one"` (aynı `(engine_id, cycle)` iki kez gelirse hata).

## 6) Üretim Komutları (Repro)

### FD001 — V2 + V1 birlikte

```bash
python demo/decision_support_runner.py \
  --pred notebooks/RUL/C-MAPSS/FD001/FD001_AllRaws/predictions_cycle_all_rows.csv \
  --rul-col pred_ensemble \
  --anomaly notebooks/Anomaly/jet-cube-turbofan-mvp/outputs/fd001_anomaly_scores.csv \
  --out "demo/demo output/fd001_decision_support_baseline_deviation.csv" \
  --emit-v1 "data/outputs/fd001_decision_support.csv" \
  --config "config/decision_support_thresholds.json" \
  --report-json "demo/demo output/fd001_decision_support_baseline_deviation_report.json"
```

### FD002 — V2 + V1 birlikte

```bash
python demo/decision_support_runner.py \
  --pred notebooks/RUL/C-MAPSS/FD002/FD002_All/fd002_test_predictions_FD002_LOCAL_REGIMEAWARE_SENSOR_ZSCORE_K6_ONEHOT.csv \
  --rul-col rul_pred \
  --anomaly notebooks/Anomaly/jet-cube-turbofan-mvp/outputs/anomaly/FD002/fd002_anomaly_test.csv \
  --out "demo/demo output/fd002_decision_support_with_anomaly.csv" \
  --emit-v1 "data/outputs/fd002_decision_support.csv" \
  --config "config/decision_support_thresholds.json" \
  --report-json "demo/demo output/fd002_decision_support_with_anomaly_report.json"
```

## 7) Kanıt Artefact’ları (Rapor + Plot)

**Runner raporları (eşikler + state dağılımı + kalibrasyon):**
- `demo/demo output/fd001_decision_support_baseline_deviation_report.json`
- `demo/demo output/fd002_decision_support_with_anomaly_report.json`

**Örnek timeline plot’lar (RUL + anomaly + state geçişleri):**
- `figures/decision_support/fd001_baseline_engine_73_timeline.png`
- `figures/decision_support/fd001_baseline_engine_49_timeline.png`
- `figures/decision_support/fd002_engine_1_timeline.png`
- `figures/decision_support/fd002_engine_159_timeline.png`

Plot üretme:
```bash
python demo/plot_decision_support_examples.py \
  --ds "demo/demo output/fd001_decision_support_baseline_deviation.csv" \
  --pred "notebooks/RUL/C-MAPSS/FD001/FD001_AllRaws/predictions_cycle_all_rows.csv" \
  --rul-col pred_ensemble \
  --anomaly "notebooks/Anomaly/jet-cube-turbofan-mvp/outputs/fd001_anomaly_scores.csv" \
  --out-dir "figures/decision_support" \
  --tag fd001_baseline --n 2
```

## 8) Kabul Checklist (Evet/Hayır + Kanıt)

- [x] V1 minimal contract üretildi (FD001): `data/outputs/fd001_decision_support.csv`
- [x] V1 minimal contract üretildi (FD002): `data/outputs/fd002_decision_support.csv`
- [x] Deterministik label + reason_codes + reason_text var (V1 dosyalarında)
- [x] Kullanılan eşikler çıktılandı (V1: `theta_rul_used`, `alpha_anomaly_used`; V2: warn/critical ayrı)
- [x] Duplicate key koruması var (`validate="one_to_one"`, runner içinde)
- [x] Kanıt raporu mevcut (FD001/FD002 JSON): `demo/demo output/*_report.json`
- [x] Görsel kanıt mevcut (timeline PNG): `figures/decision_support/*.png`

## 9) Bilinen Sınırlılıklar / Notlar

- V1 policy tek eşik kullanır; V2 warn/critical + debounce/hysteresis içerir. V1 dosyası “resmi kontrat”tır; V2 operasyonel debug/demoya uygundur.
- α (anomaly) kalibrasyonu “first N cycle healthy proxy” ile ARL hedeflerine göre yapılır; gerçek saha etiketleri yoksa bu MVP için pratik bir yaklaşımdır (raporda `alpha_calibration` altında görünür).
