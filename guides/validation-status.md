# Legacy Validation Status

This note records how each legacy `00_README` document was handled during the GitHub documentation cleanup.

## Reviewed Legacy Documents

| Legacy document | Outcome |
| --- | --- |
| `README.md` | Replaced by [`project-overview.md`](./project-overview.md) and the root [`README.md`](../README.md). |
| `executive_summary.md` | Folded into the cleaner public-facing project positioning in [`project-overview.md`](./project-overview.md). |
| `data_sources.md` | Rewritten as [`data-assets.md`](./data-assets.md). |
| `demo_runbook.md` | Rewritten into [`demo/streamlit_dashboard/README.md`](../demo/streamlit_dashboard/README.md). |
| `mvp_quickstart.md` | Replaced by focused component docs in [`webapp/README.md`](../webapp/README.md) and [`demo/streamlit_dashboard/README.md`](../demo/streamlit_dashboard/README.md). |
| `anomaly_pipeline.md` | Not republished as an active guide because the referenced rebuild scripts and configs are not present as a validated public workflow. |
| `repro_commands.md` | Not republished as an active guide for the same reason: the command chain references missing public scripts. |
| `requirements_demo.txt` | Reintroduced only as validated dependency files where needed: [`demo/streamlit_dashboard/requirements_demo.txt`](../demo/streamlit_dashboard/requirements_demo.txt) and [`twin/requirements_twin.txt`](../twin/requirements_twin.txt). |
