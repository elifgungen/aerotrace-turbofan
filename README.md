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
- Data used by the project (`data`)
- Notebook and code exports (`notebooks`)
- Technical docs, logic definitions, and reports (`docs`)
- Figures used in audits/reports (`figures`)
- Decision-support engine package and demo outputs (`demo`)
- Digital twin app/scripts/config (`twin`)
- Frontend web demo (`webapp`)

Excluded on purpose:
- Personal/administrative folders (`06_application`, `07_meetings_notes`, `logo`)
- Build/cache outputs (`node_modules`, `dist`, `__pycache__`, `.pytest_cache`, `.DS_Store`)
- Heavy model binary artifacts (`*.pkl`, `*.npz`, `*.ubj`) to keep Git history stable

## 2) High-level architecture

Data and model outputs flow into a policy layer, then into visualization layers:

1. Data preparation and baseline outputs
   - `data/`
   - `notebooks/`
2. Decision support policy (v2)
   - `demo/decision_support_v2_package/src/decision_support/`
3. Twin and web consumption layers
   - `twin/app/`
   - `webapp/`

Core policy references:
- `docs/Decision_Support/MVP_V2/docs/decision_logic_v2.md`
- `docs/Decision_Support/MVP_V2/docs/decision_support_schema.md`
- `docs/Decision_Support/MVP_V2/configs/decision_support.yaml`

## 3) Directory map

```text
.
├── readme_docs/                 # runbooks, summaries, data source notes
├── data/                   # raw + processed datasets + output snapshots
├── notebooks/      # EDA, RUL, anomaly notebooks and scripts
├── docs/                   # decision logic, reports, evidence docs
├── figures/                # report and decision-support figures
├── demo/
│   ├── decision_support_v2_package/
│   │   ├── src/decision_support/
│   │   ├── scripts/
│   │   └── tests/
│   └── decision_support_v2_outputs/
├── twin/
│   ├── app/
│   ├── scripts/
│   ├── config/
│   ├── inputs/
│   └── data/
└── webapp/
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
pip install -r readme_docs/requirements_demo.txt
```

### 5.2 Decision-support engine checks

```bash
cd demo/decision_support_v2_package
pytest tests
```

Run adapter CLI example:

```bash
python scripts/run_decision_support.py \
  --dataset cmapss \
  --config ../../docs/Decision_Support/MVP_V2/configs/decision_support.yaml \
  --rul_csv ../../data/processed/outputs/FD001/fd001_rul_predictions.csv \
  --anomaly_csv ../../data/processed/outputs/FD001/fd001_anomaly_scores.csv \
  --out_csv ../../demo/decision_support_v2_outputs/fd001_decision_support_v2.csv
```

### 5.3 Web demo

```bash
cd webapp
npm install
npm run dev
```

Default URL:
- `http://localhost:5173`

Live deployment (Vercel):
- `https://09webapp.vercel.app`

Web app documentation:
- `webapp/README.md`

### 5.4 Digital twin (Streamlit)

3D twin:

```bash
streamlit run twin/app/streamlit_twin_3d.py
```

Phase-1 twin:

```bash
streamlit run twin/app/streamlit_twin_phase1.py
```

Twin documentation:
- `twin/README_twin.md`
- `twin/README_phase1.md`
- `twin/README_phase2_hybrid.md`

## 6) Reproducibility notes

1. Data and notebook logic are included for transparent review.
2. Large training artifacts (`*.pkl`, `*.npz`, `*.ubj`) are excluded from Git to avoid repository bloat.
3. Decision policy behavior is controlled via explicit config and documented schema:
   - `docs/Decision_Support/MVP_V2/configs/decision_support.yaml`
   - `docs/Decision_Support/MVP_V2/docs/decision_support_schema.md`
4. Audit-style output samples are available in:
   - `demo/decision_support_v2_outputs/audit/`
   - `twin/data/decision_support_v2_outputs/audit/`

## 7) Key evidence and report entry points

- Feasibility report:
  - `docs/mvp_feasibility_proof_report.md`
- Policy logic v2:
  - `docs/Decision_Support/MVP_V2/docs/decision_logic_v2.md`
- Decision support schema:
  - `docs/Decision_Support/MVP_V2/docs/decision_support_schema.md`
- Final narrative reports:
  - `docs/final reports/c-mapss/`

## 8) Data source references

- Data source summary:
  - `readme_docs/data_sources.md`
- C-MAPSS raw snapshots in this repo:
  - `data/raw/CMAPSS/FD001_raw_dataset/{train_FD001.txt,test_FD001.txt,RUL_FD001.txt}`
  - `data/raw/CMAPSS/FD002_raw_dataset/{train_FD002.txt,test_FD002.txt,RUL_FD002.txt}`
  - `data/raw/CMAPSS/FD003_raw_dataset/{train_FD003.txt,test_FD003.txt,RUL_FD003.txt}`
  - `data/raw/CMAPSS/FD004_raw_dataset/{train_FD004.txt,test_FD004.txt,RUL_FD004.txt}`
- N-CMAPSS retrieval note:
  - `data/raw/N-CMAPSS/README_download.md`
- Processed decision-support outputs:
  - `data/processed/outputs/FD001/`
  - `data/processed/outputs/FD002/`
  - `data/processed/outputs/FD003/`
  - `data/processed/outputs/FD004/`
- RUL notebook exports:
  - `notebooks/RUL/C-MAPSS/FD001/FD001_AllRaws/`
  - `notebooks/RUL/C-MAPSS/FD002/FD002_All/`
  - `notebooks/RUL/N-CMAPSS/DS01/`
  - `notebooks/RUL/N-CMAPSS/DS02/`

## 9) What this repo is optimized for

- Technical review and demonstration
- Method traceability (data -> policy -> action labels)
- Frontend and twin presentation with realistic sample outputs
- Reproducible maintenance decision-support experiments

## 10) Maintainer note

This repository has been renamed and scoped around the product itself:
`AeroTrace Turbofan MRO` (instead of competition-specific naming).
