# AeroTrace Turbofan MRO

Production-focused repository for a turbofan Maintenance, Repair, and Overhaul (MRO) decision-support MVP.
The project combines:

- Remaining Useful Life (RUL) estimation workflows
- Anomaly scoring workflows
- Policy-based maintenance decision engine
- Digital twin interfaces (Streamlit + Web UI)

The objective is to make model outputs operationally actionable for maintenance planning and early risk escalation.

## 1) Repository scope

This release is curated as a clean public repo focused on reproducibility and presentation quality.

Included:
- Data used by the project (`01_data`)
- Notebook and code exports (`02_notebooks_exports`)
- Technical docs, logic definitions, and reports (`03_docs`)
- Figures used in audits/reports (`04_figures`)
- Decision-support engine package and demo outputs (`05_demo`)
- Digital twin app/scripts/config (`08_twin`)
- Frontend web demo (`09_webapp`)

Excluded on purpose:
- Personal/administrative folders (`06_application`, `07_meetings_notes`, `logo`)
- Build/cache outputs (`node_modules`, `dist`, `__pycache__`, `.pytest_cache`, `.DS_Store`)
- Heavy model binary artifacts (`*.pkl`, `*.npz`, `*.ubj`) to keep Git history stable

## 2) High-level architecture

Data and model outputs flow into a policy layer, then into visualization layers:

1. Data preparation and baseline outputs
   - `01_data/`
   - `02_notebooks_exports/`
2. Decision support policy (v2)
   - `05_demo/decision_support_v2_package/src/decision_support/`
3. Twin and web consumption layers
   - `08_twin/app/`
   - `09_webapp/`

Core policy references:
- `03_docs/Decision_Support/MVP_V2/docs/decision_logic_v2.md`
- `03_docs/Decision_Support/MVP_V2/docs/decision_support_schema.md`
- `03_docs/Decision_Support/MVP_V2/configs/decision_support.yaml`

## 3) Directory map

```text
.
├── 00_README/                 # runbooks, summaries, data source notes
├── 01_data/                   # raw + processed datasets + output snapshots
├── 02_notebooks_exports/      # EDA, RUL, anomaly notebooks and scripts
├── 03_docs/                   # decision logic, reports, evidence docs
├── 04_figures/                # report and decision-support figures
├── 05_demo/
│   ├── decision_support_v2_package/
│   │   ├── src/decision_support/
│   │   ├── scripts/
│   │   └── tests/
│   └── decision_support_v2_outputs/
├── 08_twin/
│   ├── app/
│   ├── scripts/
│   ├── config/
│   ├── inputs/
│   └── data/
└── 09_webapp/
    ├── public/data/
    ├── main.js
    ├── style.css
    └── preprocess_data.py
```

## 4) Environment requirements

Recommended baseline:
- Python 3.10+ (3.11 preferred)
- Node.js 18+ and npm
- Git

Optional but useful:
- `pytest` for engine tests
- `streamlit` for twin UI

## 5) Quick start

### 5.1 Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r 00_README/requirements_demo.txt
```

### 5.2 Decision-support engine checks

```bash
cd 05_demo/decision_support_v2_package
pytest tests
```

Run adapter CLI example:

```bash
python scripts/run_decision_support.py \
  --dataset cmapss \
  --config ../../03_docs/Decision_Support/MVP_V2/configs/decision_support.yaml \
  --rul_csv ../../01_data/processed/outputs/FD001/fd001_rul_predictions.csv \
  --anomaly_csv ../../01_data/processed/outputs/FD001/fd001_anomaly_scores.csv \
  --out_csv ../../05_demo/decision_support_v2_outputs/fd001_decision_support_v2.csv
```

### 5.3 Web demo

```bash
cd 09_webapp
npm install
npm run dev
```

Default URL:
- `http://localhost:5173`

Web app documentation:
- `09_webapp/README.md`

### 5.4 Digital twin (Streamlit)

3D twin:

```bash
streamlit run 08_twin/app/streamlit_twin_3d.py
```

Phase-1 twin:

```bash
streamlit run 08_twin/app/streamlit_twin_phase1.py
```

Twin documentation:
- `08_twin/README_08_twin.md`
- `08_twin/README_phase1.md`
- `08_twin/README_phase2_hybrid.md`

## 6) Reproducibility notes

1. Data and notebook logic are included for transparent review.
2. Large training artifacts (`*.pkl`, `*.npz`, `*.ubj`) are excluded from Git to avoid repository bloat.
3. Decision policy behavior is controlled via explicit config and documented schema:
   - `03_docs/Decision_Support/MVP_V2/configs/decision_support.yaml`
   - `03_docs/Decision_Support/MVP_V2/docs/decision_support_schema.md`
4. Audit-style output samples are available in:
   - `05_demo/decision_support_v2_outputs/audit/`
   - `08_twin/data/decision_support_v2_outputs/audit/`

## 7) Key evidence and report entry points

- Feasibility report:
  - `03_docs/mvp_feasibility_proof_report.md`
- Policy logic v2:
  - `03_docs/Decision_Support/MVP_V2/docs/decision_logic_v2.md`
- Decision support schema:
  - `03_docs/Decision_Support/MVP_V2/docs/decision_support_schema.md`
- Final narrative reports:
  - `03_docs/final reports/c-mapss/`

## 8) Data source references

- Data source summary:
  - `00_README/data_sources.md`
- N-CMAPSS retrieval note:
  - `01_data/raw/N-CMAPSS/README_download.md`

## 9) What this repo is optimized for

- Technical review and demonstration
- Method traceability (data -> policy -> action labels)
- Frontend and twin presentation with realistic sample outputs
- Reproducible maintenance decision-support experiments

## 10) Maintainer note

This repository has been renamed and scoped around the product itself:
`AeroTrace Turbofan MRO` (instead of competition-specific naming).
