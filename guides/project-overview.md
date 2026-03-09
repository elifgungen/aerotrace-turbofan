# Project Overview

AeroTrace Turbofan is a public showcase repository for a turbofan maintenance decision-support stack. The repository packages data artefacts, reporting material, a browser-based exploration app, and digital twin components into one reviewable bundle.

## What the Repository Contains

- C-MAPSS and N-CMAPSS derived outputs for remaining useful life, anomaly scoring, and maintenance triage.
- A web application under [`webapp/`](../webapp) for fleet-level and engine-level inspection.
- A Streamlit-based decision-support dashboard under [`demo/streamlit_dashboard/`](../demo/streamlit_dashboard).
- Digital twin scripts and Streamlit interfaces under [`twin/`](../twin).
- Supporting reports, exports, and evidence files under [`docs/`](../docs), [`notebooks/`](../notebooks), and [`figures/`](../figures).

## Recommended Review Paths

- For a fast product tour, read [`README.md`](../README.md) and then open [`guides/webapp-guide.md`](./webapp-guide.md).
- For CSV-based inspection of decision-support outputs, use [`guides/streamlit-demo-guide.md`](./streamlit-demo-guide.md).
- For simulation-oriented workflows, use [`guides/digital-twin-guide.md`](./digital-twin-guide.md).
- For data inventory and coverage, use [`guides/data-assets.md`](./data-assets.md).

## Scope Notes

- The repository is optimized for inspection and demonstration rather than full end-to-end retraining.
- Some historical reports refer to older internal layouts or non-public scripts; those are not used as the active guide source.
- The active guide set is limited to workflows that can be traced to files currently present in the repository.
