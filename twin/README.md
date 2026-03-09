# Digital Twin

This directory contains the repository's digital twin applications, scripts, configs, and prepared inputs.

## Contents

- [`app/`](./app): Streamlit interfaces for the Phase 1 and 3D twin views.
- [`scripts/`](./scripts): data-preparation and replay scripts.
- [`config/`](./config): policy and mapping configuration files.
- [`inputs/`](./inputs): prepared Phase 1 twin feeds.
- [`data/`](./data): bundled policy inputs and hybrid outputs.
- [`requirements_twin.txt`](./requirements_twin.txt): Python dependencies for the twin workflows.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r twin/requirements_twin.txt
```

## Common Workflows

Phase 1 replay:

```bash
python twin/scripts/build_twin_inputs_ncmapss.py --datasets DS01 DS02 DS03 DS04 DS05 DS06 DS07
python twin/scripts/run_twin_phase1_replay.py --datasets DS01 DS02 DS03 DS04 DS05 DS06 DS07
streamlit run twin/app/streamlit_twin_phase1.py
```

Phase 2 hybrid:

```bash
python twin/scripts/run_twin_hybrid_phase2.py
streamlit run twin/app/streamlit_twin_3d.py --server.port 8518
```

## Additional Notes

- High-detail implementation notes remain in [`README_phase1.md`](./README_phase1.md), [`README_phase2_hybrid.md`](./README_phase2_hybrid.md), and [`README_3d_sim.md`](./README_3d_sim.md).
- This `README.md` is the GitHub-facing entry point for the twin area.
