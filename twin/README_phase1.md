# Digital Twin Phase-1 (N-CMAPSS DS01-DS07)

Bu fazda yeni model egitimi yoktur. Mevcut `rul_pred` ve `anomaly_score` ciktilariyla replay tabanli Twin runtime calistirilir.

## 1) Ortam

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install streamlit pandas numpy plotly pyyaml scipy scikit-learn shap
```

## 2) Twin input feed olusturma

```powershell
.\.venv\Scripts\python.exe twin/scripts/build_twin_inputs_ncmapss.py --datasets DS01 DS02 DS03 DS04 DS05 DS06 DS07
```

Uretim:
- `twin/inputs/ncmapss_DSxx_twin_feed.csv`
- `twin/inputs/ncmapss_twin_input_audit.json`

## 3) Replay runtime calistirma

```powershell
.\.venv\Scripts\python.exe twin/scripts/run_twin_phase1_replay.py --datasets DS01 DS02 DS03 DS04 DS05 DS06 DS07
```

Uretim:
- `twin/outputs/DSxx/state_timeline.csv`
- `twin/outputs/DSxx/events.csv`
- `twin/outputs/DSxx/summary.json`
- `twin/outputs/phase1_summary.csv`

## 4) UI

```powershell
.\.venv\Scripts\python.exe -m streamlit run twin/app/streamlit_twin_phase1.py
```

UI modulleri:
- `Decision Transition Log`: split ve motor bazli gecis matrisi + event log + decision segmentleri.
- `Lead-time & Missed Alarm Panel`: motor bazli lead/missed alarm metrikleri ve dagilim grafikleri.
- `DS01 SHAP Explainability`: notebook export kaynakli DS01 tahminleri uzerinden SHAP global/local aciklama.

## 5) Politika

Varsayilan politika dosyasi:
- `twin/config/phase1_policy.yaml`

Missed alarm onceligi icin threshold/debounce degerlerini bu dosyada guncelleyebilirsin.
