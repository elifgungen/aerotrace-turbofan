# Digital Twin Phase-2 Hybrid (Report-Aligned)

Bu faz, `03_docs/final reports/digital_twin_rul_mvp_target_report_2026-02-13.md` icindeki kararlarla hizali olarak
N-CMAPSS DS01-DS07 policy ciktilari ustunde hibrit risk fuzesi uretir.

## Raporla Kilitli Noktalar
- RMSE protokolu: cycle-level
- Kapsam: DS01-DS07
- Birincil KPI: missed alarm minimizasyonu
- CAP: aktif 125, shadow 130 (config kayitli)
- Contract check: split canonical + duplicate key + NaN/Inf kontrolu

## Uretilen Ciktilar
- `08_twin/data/hybrid_phase2/DSxx/hybrid_timeline.csv`
- `08_twin/data/hybrid_phase2/DSxx/summary.json`
- `08_twin/data/hybrid_phase2/hybrid_phase2_summary.csv`
- `08_twin/data/hybrid_phase2/hybrid_phase2_readiness_audit.json`

## Calistirma
```powershell
Set-Location "C:\Baran\Havelsan"
.\.venv\Scripts\python.exe 08_twin/scripts/run_twin_hybrid_phase2.py
```

Sadece test split:
```powershell
.\.venv\Scripts\python.exe 08_twin/scripts/run_twin_hybrid_phase2.py --split-mode test_only
```

## Konfig
- `08_twin/config/hybrid_phase2_policy.json`

Agliklar:
- model_risk: `rul_risk + anomaly_risk`
- policy_risk: karar etiketinden gelen risk
- physics_risk: rul dusus trendi
- uncertainty_risk: lokal volatilite

## Mapping Tablosu (Rapor madde-5)
- `08_twin/config/ncmapss_sensor_component_mapping_template.csv`
- `W_*` ve `Xs_*` alanlari icin fiziksel birebir adlandirma dis dokuman ile tamamlanmalidir.
