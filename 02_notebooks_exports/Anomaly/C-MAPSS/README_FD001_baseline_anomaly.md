# FD001 — Baseline-Deviation Anomaly Score (decision-support input)

Bu klasördeki hedef: FD001 için **engine_id + cycle** bazında açıklanabilir bir `anomaly_score` üretip
decision-support (α–θ) katmanına bağlamak.

## Yöntem (MVP / explainable)
- Her engine için baseline: ilk `N=20` cycle
- Her sensör için: `mu = mean(first N)`, `sigma = std(first N) + eps`
- Z-score: `z = (x - mu) / sigma`
- Tek skora indirgeme: `score_raw = sqrt(mean(z^2))` (RMS z-score)
- 0–1 mapping: sigmoid `1/(1+exp(-k*(score_raw - c)))` (`c=median(score_raw)`, `k=1`)
- Opsiyonel: rolling mean smoothing (varsayılan `window=5`)
- Opsiyonel explainability: `top_sensors` ve `top_abs_z` (top-3 |z|)

## Script (repo-relative)
- `02_notebooks_exports/Anomaly/jet-cube-turbofan-mvp/fd001_baseline_deviation_anomaly.py`

### Minimal output (decision-support contract)
```bash
python 02_notebooks_exports/Anomaly/jet-cube-turbofan-mvp/fd001_baseline_deviation_anomaly.py --minimal
```

Üretilen dosyalar (default):
- `02_notebooks_exports/Anomaly/jet-cube-turbofan-mvp/outputs/fd001_anomaly_scores.csv` (engine_id, cycle, anomaly_score)
- `02_notebooks_exports/Anomaly/jet-cube-turbofan-mvp/outputs/fd001_anomaly_mapping_params.json`
- `02_notebooks_exports/Anomaly/jet-cube-turbofan-mvp/outputs/fd001_test_with_preds_and_anomaly.csv` (opsiyonel join)

## Decision-support ile test
FD001 RUL prediction + anomaly_score birleşimi ile:
```bash
python 05_demo/decision_support_runner.py \
  --pred 02_notebooks_exports/RUL/FD001/FD001_Ozcan_AllRaws/predictions_cycle_all_rows.csv \
  --rul-col pred_ensemble \
  --anomaly 02_notebooks_exports/Anomaly/jet-cube-turbofan-mvp/outputs/fd001_anomaly_scores.csv \
  --out "05_demo/demo output/fd001_decision_support_baseline_deviation.csv" \
  --theta-warn 50 --theta-critical 20 \
  --smooth-window 5 \
  --alpha-target-arl-warn 200 --alpha-target-arl-critical 1000 \
  --calib-healthy-first-n 20 \
  --anom-debounce-warn-up 3 --anom-debounce-critical-up 2 --anom-debounce-down 3 \
  --alpha-hysteresis-delta 0.05 \
  --report-json "05_demo/demo output/fd001_decision_support_baseline_deviation_report.json"
```

