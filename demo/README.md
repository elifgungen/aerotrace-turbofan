# Demo

This directory contains the repository's packaged decision-support demo assets.

## Contents

- [`decision_support_v2_outputs/`](./decision_support_v2_outputs): flat CSV exports used by the demo dashboard and some downstream visualizations.
- [`streamlit_dashboard/`](./streamlit_dashboard): Streamlit application for exploring the bundled CSV outputs.
- [`decision_support_v2_package/`](./decision_support_v2_package): packaged policy-engine implementation and tests.
- [`decision_support_runner.py`](./decision_support_runner.py): runner entrypoint retained with the demo materials.

## Start Here

- If you want to inspect the demo in a browser, open [`streamlit_dashboard/README.md`](./streamlit_dashboard/README.md).
- If you only need the bundled CSV files, browse [`decision_support_v2_outputs/`](./decision_support_v2_outputs).

## Scope

This area is intended for review and packaged execution, not for full retraining of the historical pipelines referenced in older draft notes.
