# Validation Status

This guide separates three things that are easy to blur together in a repository like this:

- committed artifact evidence,
- report-level claims,
- and runtime behavior that was not rerun during this documentation review.

## What is directly evidenced in the repository

### 1. Prepared decision-support outputs are committed

The repository clearly contains ready-to-review outputs for:

- C-MAPSS `FD001` to `FD004` under [`../data/processed/outputs/C-MAPSS/`](../data/processed/outputs/C-MAPSS)
- N-CMAPSS `DS01` to `DS07` under [`../data/processed/outputs/N-CMAPSS/`](../data/processed/outputs/N-CMAPSS)
- Flat demo exports under [`../demo/decision_support_v2_outputs/`](../demo/decision_support_v2_outputs)

These are tangible, inspectable outputs rather than placeholders.

### 2. The review interfaces are populated with data

The web app has committed preprocessed JSON assets for 11 datasets under [`../webapp/public/data/`](../webapp/public/data), and the dataset index is present at [`../webapp/public/data/datasets.json`](../webapp/public/data/datasets.json).

The twin area also contains prepared data:

- policy-oriented inputs under [`../twin/data/decision_support_v2_outputs/`](../twin/data/decision_support_v2_outputs)
- hybrid output folders for `DS01` to `DS07` under [`../twin/data/hybrid_phase2/`](../twin/data/hybrid_phase2)

### 3. Packaged policy code and tests exist

The repository includes a packaged decision-support module and test files under [`../demo/decision_support_v2_package/`](../demo/decision_support_v2_package):

- [`../demo/decision_support_v2_package/src/decision_support/policy_engine.py`](../demo/decision_support_v2_package/src/decision_support/policy_engine.py)
- [`../demo/decision_support_v2_package/tests/test_policy_engine.py`](../demo/decision_support_v2_package/tests/test_policy_engine.py)
- [`../demo/decision_support_v2_package/tests/test_runner_backward_compat.py`](../demo/decision_support_v2_package/tests/test_runner_backward_compat.py)
- [`../demo/decision_support_v2_package/tests/test_v2_schema.py`](../demo/decision_support_v2_package/tests/test_v2_schema.py)

The presence of those tests is directly verifiable. Their current pass/fail status was not rerun during this documentation pass because `pytest` is not installed in the current shell environment.

## What the reports support

Several committed reports provide useful evidence, but they should be read carefully:

- [`../docs/mvp_feasibility_proof_report.md`](../docs/mvp_feasibility_proof_report.md)
- [`../docs/Decision_Support/MVP/decision_support_report_2026-01-28.md`](../docs/Decision_Support/MVP/decision_support_report_2026-01-28.md)
- [`../demo/decision_support_v2_outputs/audit/ncmapss_batch_generation_report.json`](../demo/decision_support_v2_outputs/audit/ncmapss_batch_generation_report.json)
- [`../data/processed/N-CMAPSS/_UPLOAD_MANIFEST.md`](../data/processed/N-CMAPSS/_UPLOAD_MANIFEST.md)

These files support the following high-level statements:

- benchmark-based outputs were generated and committed,
- multiple N-CMAPSS datasets were processed in batch form,
- decision-support policies were compared across versions,
- and parts of the twin workflow were summarized in committed outputs.

## What was not rerun here

- The demo dashboard was not launched.
- The web app was not built or served.
- The twin apps were not run.
- The packaged tests were not executed because `pytest` is unavailable in the current shell.

## Caveats that matter

- Some reports still use historical local paths, so they are better treated as evidence summaries than as copy-paste runbooks.
- The repository is stronger as an inspection and demo package than as a single-command reproduction pipeline.
- Curated evaluation boxplots are committed under [`../evaluation/`](../evaluation/README.md) and referenced from [`data-assets.md`](./data-assets.md). This documentation pass records those artifacts only; runtime regeneration of the figures was not rerun.

## Current validation picture by area

| Area | What can be stated confidently | Main caveat |
| --- | --- | --- |
| Data assets | Raw C-MAPSS and processed N-CMAPSS artifacts are committed | Full raw N-CMAPSS archive is documented, not vendored |
| Decision-support outputs | Prepared CSV outputs are present for active datasets | Generation commands are not uniformly turnkey from the root |
| Demo dashboard | Streamlit app and expected input folder are documented | No runtime check was performed in this review |
| Web app | Front-end code and preprocessed dataset JSON are committed | No build/run check was performed in this review |
| Twin workflows | Scripts, apps, and hybrid outputs are present | Summary evidence is thinner than the folder inventory suggests |
| Tests | Test files exist for the packaged policy module | `pytest` was unavailable in the shell, so pass status was not reconfirmed |

## Practical interpretation for a new reader

If you are evaluating the repository today, the safest conclusions are:

- this is a documentation-friendly inspection repository with substantial committed outputs,
- the decision-support layer is not just described in prose but represented in committed CSV, JSON, and packaged code,
- the web app and twin areas are populated enough to understand the intended end-to-end story,
- and stronger claims about readiness should be read as report-level claims unless you rerun the relevant components yourself.

For the folder-by-folder asset inventory, continue to [`data-assets.md`](./data-assets.md).
