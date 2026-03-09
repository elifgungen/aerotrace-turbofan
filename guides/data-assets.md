# Data Assets

This repository bundles both source data and derived artefacts, but not every upstream asset is included.

## Bundled Raw Data

The repository includes the C-MAPSS raw text files for `FD001` through `FD004` under [`data/raw/CMAPSS/`](../data/raw/CMAPSS).

Examples:

- [`data/raw/CMAPSS/FD001_raw_dataset/train_FD001.txt`](../data/raw/CMAPSS/FD001_raw_dataset/train_FD001.txt)
- [`data/raw/CMAPSS/FD004_raw_dataset/RUL_FD004.txt`](../data/raw/CMAPSS/FD004_raw_dataset/RUL_FD004.txt)

For N-CMAPSS, the repository includes a download note rather than the full raw dataset:

- [`data/raw/N-CMAPSS/README_download.md`](../data/raw/N-CMAPSS/README_download.md)

## Bundled Processed Outputs

Derived outputs are available in two main areas:

- [`data/processed/outputs/`](../data/processed/outputs): C-MAPSS and N-CMAPSS artefacts organized by dataset family and dataset id.
- [`demo/decision_support_v2_outputs/`](../demo/decision_support_v2_outputs): flat decision-support exports used by the Streamlit demo and webapp preprocessing workflows.

Examples:

- [`data/processed/outputs/C-MAPSS/FD002/fd002_decision_support.csv`](../data/processed/outputs/C-MAPSS/FD002/fd002_decision_support.csv)
- [`data/processed/outputs/N-CMAPSS/DS03/ncmapss_DS03_decision_support_v2.csv`](../data/processed/outputs/N-CMAPSS/DS03/ncmapss_DS03_decision_support_v2.csv)
- [`demo/decision_support_v2_outputs/ncmapss_DS04_decision_support_v2.csv`](../demo/decision_support_v2_outputs/ncmapss_DS04_decision_support_v2.csv)

## Notebook and Report Artefacts

Model exports, intermediate analysis files, and presentation material are stored here:

- [`notebooks/`](../notebooks)
- [`docs/`](../docs)
- [`figures/`](../figures)

These directories are useful for review and traceability, but they should not be treated as a clean training pipeline contract.

## Practical Guidance

- Use [`demo/decision_support_v2_outputs/`](../demo/decision_support_v2_outputs) when you want flat files that are easy to browse in the Streamlit dashboard.
- Use [`data/processed/outputs/`](../data/processed/outputs) when you want the fuller dataset-family structure.
