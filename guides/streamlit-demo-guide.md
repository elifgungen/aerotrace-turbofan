# Streamlit Demo Guide

The repository includes a Streamlit dashboard for inspecting decision-support CSV exports without retraining any models.

## Location

- App source: [`demo/streamlit_dashboard/streamlit_app.py`](../demo/streamlit_dashboard/streamlit_app.py)
- Python requirements: [`demo/streamlit_dashboard/requirements_demo.txt`](../demo/streamlit_dashboard/requirements_demo.txt)

## Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r demo/streamlit_dashboard/requirements_demo.txt
```

## Run the Dashboard

```bash
streamlit run demo/streamlit_dashboard/streamlit_app.py
```

## Default Data Source

By default, the dashboard reads flat CSV exports from:

- [`demo/decision_support_v2_outputs/`](../demo/decision_support_v2_outputs)

This folder currently contains:

- `FD001`
- `DS01` through `DS07`

## Use a Different Outputs Folder

If you want the dashboard to read a different directory, set `JETCUBE_OUTPUTS_DIR` before launching Streamlit.

Example:

```bash
JETCUBE_OUTPUTS_DIR=/absolute/path/to/exports streamlit run demo/streamlit_dashboard/streamlit_app.py
```

The dashboard expects flat filenames such as:

- `fd001_decision_support_v2.csv`
- `ncmapss_DS01_decision_support_v2.csv`

It also supports optional sibling files for anomaly and RUL exports when they follow the same dataset naming pattern.

## Notes

- This dashboard is intended for CSV inspection and explanation, not for full training or pipeline orchestration.
- The application has been updated to normalize the bundled `v2` CSV format into the internal dashboard schema before rendering.
