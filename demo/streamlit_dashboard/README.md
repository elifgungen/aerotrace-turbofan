# Streamlit Dashboard

This Streamlit app reads bundled decision-support CSV exports and renders dataset, engine, and cycle-level inspection views.

## Files

- App: [`streamlit_app.py`](./streamlit_app.py)
- Dependencies: [`requirements_demo.txt`](./requirements_demo.txt)

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r demo/streamlit_dashboard/requirements_demo.txt
```

## Run

```bash
streamlit run demo/streamlit_dashboard/streamlit_app.py
```

## Default Input Folder

The app auto-detects outputs from:

- `demo/decision_support_v2_outputs`

You can override this by setting `JETCUBE_OUTPUTS_DIR` before launch.

Example:

```bash
JETCUBE_OUTPUTS_DIR=/absolute/path/to/exports streamlit run demo/streamlit_dashboard/streamlit_app.py
```

## Supported File Naming

The dashboard expects flat files such as:

- `fd001_decision_support_v2.csv`
- `ncmapss_DS01_decision_support_v2.csv`
- matching `*_anomaly_scores.csv`
- matching `*_rul_predictions*.csv`

## Notes

- The dashboard normalizes the bundled `v2` CSV schema before rendering.
- This app is for inspection of prepared outputs; it does not retrain models.
