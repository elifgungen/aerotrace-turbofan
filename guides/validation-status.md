# Legacy Validation Status

This note records how each legacy `00_README` document was handled during the GitHub documentation cleanup.

## Reviewed Legacy Documents

| Legacy document | Outcome |
| --- | --- |
| `README.md` | Replaced by [`project-overview.md`](./project-overview.md) and the root [`README.md`](../README.md). |
| `executive_summary.md` | Folded into the cleaner public-facing project positioning in [`project-overview.md`](./project-overview.md). |
| `data_sources.md` | Rewritten as [`data-assets.md`](./data-assets.md). |
| `demo_runbook.md` | Rewritten as [`streamlit-demo-guide.md`](./streamlit-demo-guide.md). |
| `mvp_quickstart.md` | Replaced by the focused setup sections in [`webapp-guide.md`](./webapp-guide.md) and [`streamlit-demo-guide.md`](./streamlit-demo-guide.md). |
| `anomaly_pipeline.md` | Not republished as an active guide because the referenced rebuild scripts and configs are not present as a validated public workflow. |
| `repro_commands.md` | Not republished as an active guide for the same reason: the command chain references missing public scripts. |
| `requirements_demo.txt` | Reintroduced only as validated dependency files where needed: [`demo/streamlit_dashboard/requirements_demo.txt`](../demo/streamlit_dashboard/requirements_demo.txt) and [`twin/requirements_twin.txt`](../twin/requirements_twin.txt). |
