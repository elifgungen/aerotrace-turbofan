# Evaluation Assets

This folder contains curated evaluation artifacts for the AeroTrace turbofan models. It is the canonical location for GitHub-friendly performance visuals and the summary tables that support them.

## Contents

- Boxplots:
  - `absolute_error_boxplot_by_dataset_cmapss.png`
  - `absolute_error_boxplot_by_dataset_ncmapss.png`
  - `per_engine_mae_boxplot_by_dataset_cmapss.png`
  - `per_engine_mae_boxplot_by_dataset_ncmapss.png`
  - `final_cycle_abs_error_boxplot_by_dataset_cmapss.png`
  - `final_cycle_abs_error_boxplot_by_dataset_ncmapss.png`
- Overview figures:
  - `true_vs_pred_scatter_cmapss.png`
  - `true_vs_pred_scatter_ncmapss.png`
  - `residual_histogram_by_dataset_cmapss.png`
  - `residual_histogram_by_dataset_ncmapss.png`
- Supporting summaries:
  - `evaluation_metrics_by_dataset_*.csv`
  - `evaluation_engine_metrics_*.csv`
  - `evaluation_rows_*.csv`
  - `evaluation_manifest.json`

## How to use this folder

- Start with the absolute error boxplots for dataset-level comparison.
- Use the per-engine MAE boxplots to see variability across engines within each dataset.
- Use the final-cycle absolute error boxplots when you want to focus on end-of-life prediction behavior.
- Use the scatter and residual plots as companion views, not as replacements for the boxplots.

These files are review artifacts, not raw training outputs.
