# Digital Twin Guide

The `twin/` directory contains the repository's simulation-oriented tooling, including replay scripts and Streamlit interfaces.

## Location

- Twin workspace: [`twin/`](../twin)
- Requirements: [`twin/requirements_twin.txt`](../twin/requirements_twin.txt)
- Main reference note: [`twin/README_twin.md`](../twin/README_twin.md)

## Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r twin/requirements_twin.txt
```

## Phase 1 Replay

Build or refresh input feeds:

```bash
python twin/scripts/build_twin_inputs_ncmapss.py --datasets DS01 DS02 DS03 DS04 DS05 DS06 DS07
```

Run the replay:

```bash
python twin/scripts/run_twin_phase1_replay.py --datasets DS01 DS02 DS03 DS04 DS05 DS06 DS07
```

Launch the Phase 1 UI:

```bash
streamlit run twin/app/streamlit_twin_phase1.py
```

## Phase 2 Hybrid

Generate hybrid outputs:

```bash
python twin/scripts/run_twin_hybrid_phase2.py
```

Launch the 3D Streamlit view:

```bash
streamlit run twin/app/streamlit_twin_3d.py --server.port 8518
```

## Key Bundled Data

- Policy inputs: [`twin/data/decision_support_v2_outputs/`](../twin/data/decision_support_v2_outputs)
- Phase 1 feeds: [`twin/inputs/`](../twin/inputs)
- Hybrid outputs: [`twin/data/hybrid_phase2/`](../twin/data/hybrid_phase2)
- Config files: [`twin/config/`](../twin/config)

## Notes

- The twin area already ships with prepared inputs and policy files, so you can review it without rebuilding everything first.
- The twin README files in `twin/` are still useful as implementation notes, but this guide is the curated GitHub entry point.
