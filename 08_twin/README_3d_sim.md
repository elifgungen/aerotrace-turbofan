# Twin 3D Simulation MVP

## 1) Hybrid outputs uret (onerilen)
```powershell
Set-Location "<repo-root>"
.\.venv\Scripts\python.exe twin/scripts/run_twin_hybrid_phase2.py
```

## 2) UI calistir (port 8518)
```powershell
Set-Location "<repo-root>"
.\.venv\Scripts\python.exe -m streamlit run twin/app/streamlit_twin_3d.py --server.port 8518
```

## Required packages
```powershell
.\.venv\Scripts\python.exe -m pip install streamlit plotly pandas numpy
```

## Data source modes (sidebar)
- `Hybrid Phase-2 (Recommended)`
  - Root: `twin/data/hybrid_phase2`
  - Uses: `hybrid_risk`, `hybrid_state`, `expected_failure_stage`, `dominant_driver`
- `Policy V2 Baseline`
  - Root: `demo/decision_support_v2_outputs`
  - Uses: `ncmapss_DSxx_decision_support_v2.csv`

## Notes
- 3D geometry is an operational twin visualization (component-level risk coloring).
- Hybrid mode ties 3D coloring to model + policy + trend + volatility risk fusion.
- It is not a full CFD/physics solver.

## If visual looks unchanged
1. Stop Streamlit process.
2. Clear Streamlit cache:
```powershell
.\.venv\Scripts\python.exe -m streamlit cache clear
```
3. Restart app and verify header shows:
- `UI revision: 3d-geo-v2-2026-02-13-1`

## Step-by-step cycle observation
- Sidebar > `Cycle Playback`
  - `Prev Cycle` / `Next Cycle`
  - `Cycle (step-by-step)` slider
  - `Auto Play` + `Auto Play Delay (ms)`
- Header must show `UI revision: 3d-geo-v2-2026-02-13-2`
