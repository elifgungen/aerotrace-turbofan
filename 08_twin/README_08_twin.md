# 08_twin - Self-Contained Twin Bundle

Bu klasor, Twin calismasini tek bir yerde toplamak icin olusturuldu.
`08_twin` icinde app + script + config + gerekli veri ciktilari bulunur.

## Icerik
- `08_twin/app/`
  - `streamlit_twin_3d.py`
  - `streamlit_twin_phase1.py`
- `08_twin/scripts/`
  - `run_twin_hybrid_phase2.py`
  - `run_twin_phase1_replay.py`
  - `build_twin_inputs_ncmapss.py`
- `08_twin/config/`
  - `hybrid_phase2_policy.json`
  - `phase1_policy.yaml`
  - `ncmapss_sensor_component_mapping_template.csv`
- `08_twin/data/`
  - `decision_support_v2_outputs/` (DS01-DS07 policy v2 ciktilari)
  - `hybrid_phase2/` (hibrit timeline ciktilari)
- `08_twin/inputs/` (phase1 twin feed dosyalari)
- `08_twin/outputs/` (phase1 replay ciktilari)

## Onkosullar
```powershell
Set-Location "C:\Baran\Havelsan"
.\.venv\Scripts\python.exe -m pip install streamlit plotly pandas numpy scikit-learn pyyaml
```

## Hizli Baslangic (3D UI)
```powershell
Set-Location "C:\Baran\Havelsan"
.\.venv\Scripts\python.exe -m streamlit run 08_twin/app/streamlit_twin_3d.py --server.port 8518
```

Tarayici:
- `http://localhost:8518`

Beklenen UI ibaresi:
- `UI revision: 3d-geo-v2-2026-02-14-08twin`

## Phase-2 Hybrid Ciktilari Yeniden Uretme
Varsayilanlar artik `08_twin/*` yolunu kullanir.

```powershell
Set-Location "C:\Baran\Havelsan"
.\.venv\Scripts\python.exe 08_twin/scripts/run_twin_hybrid_phase2.py
```

Uretilen dosyalar:
- `08_twin/data/hybrid_phase2/hybrid_phase2_summary.csv`
- `08_twin/data/hybrid_phase2/hybrid_phase2_readiness_audit.json`
- `08_twin/data/hybrid_phase2/DSxx/hybrid_timeline.csv`

## Phase-1 Replay Calistirma
```powershell
Set-Location "C:\Baran\Havelsan"
.\.venv\Scripts\python.exe 08_twin/scripts/run_twin_phase1_replay.py
```

Uretilen dosyalar:
- `08_twin/outputs/DSxx/state_timeline.csv`
- `08_twin/outputs/DSxx/events.csv`
- `08_twin/outputs/DSxx/summary.json`
- `08_twin/outputs/phase1_summary.csv`

## Twin Feed Yeniden Build Etme (Opsiyonel)
RUL + anomaly exportlardan `08_twin/inputs` altina yeni feed olusturur.

```powershell
Set-Location "C:\Baran\Havelsan"
.\.venv\Scripts\python.exe 08_twin/scripts/build_twin_inputs_ncmapss.py
```

## 3D UI Kullanim Notlari
- Sidebar > `Data Source`
  - `Hybrid Phase-2 (Recommended)`
  - `Policy V2 Baseline`
- Sidebar > `Cycle Playback`
  - `Prev Cycle` / `Next Cycle`
  - `Cycle (step-by-step)`
  - `Auto Play`
  - `Auto Play Delay (ms)`

## Sorun Giderme
1. Port doluysa:
```powershell
.\.venv\Scripts\python.exe -m streamlit run 08_twin/app/streamlit_twin_3d.py --server.port 8520
```

2. Eski ekran gorunuyorsa cache temizle:
```powershell
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
.\.venv\Scripts\python.exe -m streamlit cache clear
```

3. Hybrid veri bulunamazsa once su komutu calistir:
```powershell
.\.venv\Scripts\python.exe 08_twin/scripts/run_twin_hybrid_phase2.py
```
