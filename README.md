# AeroTrace Turbofan

AeroTrace Turbofan is a public showcase repository for a turbofan maintenance, repair, and overhaul decision-support stack. The project combines remaining useful life estimation, anomaly scoring, rule-based maintenance triage, and digital twin visualization into a single reproducible package for evaluation and demonstration.

The repository is organized to make the final MVP outputs inspectable without requiring full model retraining. It is intended for technical reviewers, demo audiences, and collaborators who need to trace how maintenance recommendations are produced from the underlying datasets.

## Overview

The end-to-end workflow brings together four connected capabilities:

1. Remaining useful life estimation on C-MAPSS and N-CMAPSS datasets.
2. Unsupervised anomaly scoring to detect abnormal sensor behavior.
3. A deterministic decision-support policy that converts model outputs into four maintenance triage levels.
4. Browser-based and digital twin interfaces for operational review.

## Repository Structure

| Path | Description |
| --- | --- |
| `data/` | Raw, processed, and curated data assets used by the MVP. |
| `notebooks/` | Notebook exports, model artefacts, and dataset-specific result files. |
| `docs/` | Narrative reports, architecture notes, review notes, and final evaluation material. |
| `figures/` | Supporting visuals used in reports and presentations. |
| `demo/` | Decision-support package, scripts, and generated outputs. |
| `twin/` | Digital twin inputs and simulation-oriented assets. |
| `webapp/` | Interactive web application for dataset exploration, fleet review, and engine-level analysis. |

## Quick Start

Choose the path that matches the review goal:

- For the interactive browser experience, open [`webapp/README.md`](./webapp/README.md) and run the Vite application locally.
- For decision-support logic and packaged outputs, inspect [`demo/`](./demo) together with the reports under [`docs/`](./docs).

## Maintenance Triage Logic

The MVP exposes a four-level maintenance recommendation layer:

| Condition | Outcome |
| --- | --- |
| Low anomaly, healthy RUL | `Normal Operation` |
| Elevated anomaly, healthy RUL | `Enhanced Monitoring` |
| Low anomaly, limited RUL | `Planned Maintenance` |
| Elevated anomaly, limited RUL | `Immediate Maintenance` |

This policy is intentionally deterministic and traceable so that every recommendation can be audited against the source metrics and thresholds.

## Key Characteristics

- Supports both C-MAPSS and N-CMAPSS scenarios.
- Keeps the maintenance engineer in the loop instead of automating final approval.
- Ships with ready-to-inspect outputs for demos, reviews, and evidence-based presentations.
- Includes a modern web front end and digital twin assets for operational storytelling.

## Notes

- Documentation in the repository is primarily in Turkish, with technical terms preserved in English where useful.
- Large training binaries are intentionally excluded from version control to keep the public history reviewable.
