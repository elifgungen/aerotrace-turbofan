# Digital Twin Phase-2 Hybrid (Report-Aligned)

Bu faz, `docs/final reports/digital_twin_rul_mvp_target_report_2026-02-13.md` icindeki kararlarla hizali olarak
N-CMAPSS DS01-DS07 policy ciktilari ustunde hibrit risk fuzesi uretir.

## Raporla Kilitli Noktalar
- RMSE protokolu: cycle-level
- Kapsam: DS01-DS07
- Birincil KPI: missed alarm minimizasyonu
- CAP: aktif 125, shadow 130 (config kayitli)
- Contract check: split canonical + duplicate key + NaN/Inf kontrolu

## Uretilen Ciktilar
- `twin/data/hybrid_phase2/DSxx/hybrid_timeline.csv`
- `twin/data/hybrid_phase2/DSxx/summary.json`
- `twin/data/hybrid_phase2/hybrid_phase2_summary.csv`
- `twin/data/hybrid_phase2/hybrid_phase2_readiness_audit.json`

## Calistirma
```powershell
Set-Location "<repo-root>"
.\.venv\Scripts\python.exe twin/scripts/run_twin_hybrid_phase2.py
```

Sadece test split:
```powershell
.\.venv\Scripts\python.exe twin/scripts/run_twin_hybrid_phase2.py --split-mode test_only
```

## Konfig
- `twin/config/hybrid_phase2_policy.json`

Agliklar:
- model_risk: `rul_risk + anomaly_risk`
- policy_risk: karar etiketinden gelen risk
- physics_risk: rul dusus trendi
- uncertainty_risk: lokal volatilite

## Mapping Tablosu (Rapor madde-5)
- `twin/config/ncmapss_sensor_component_mapping_template.csv`
- `W_*` ve `Xs_*` alanlari icin fiziksel birebir adlandirma dis dokuman ile tamamlanmalidir.
