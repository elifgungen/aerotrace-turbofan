# MVP Submission Checklist

## Reproducibility
- Policy config: `configs/decision_support.yaml`
- Runner entrypoint: `demo/decision_support_runner.py`
- Output paths: `*_decision_support.csv` (v1), `*_decision_support_v2.csv` (v2)
- Her v2 satırında audit alanları bulunur: `policy_version`, `run_id`, `theta_rul_used`, `alpha_high_used`, `alpha_low_used`

## Backward Compatibility
- V1 davranışı korunmuştur (legacy yol değişmemiştir).
- Regresyon testi: `tests/test_runner_backward_compat.py` PASS.

## V2 Schema
- V2 minimum şema testi: `tests/test_v2_schema.py` PASS.
- Detaylı şema dokümanı: `docs/decision_support_schema.md`.

## Human-in-the-loop Disclaimer
- Bu katman otomatik bakım icrası yapmaz.
- Çıktılar karar destek amaçlıdır; nihai aksiyon insan onayına tabidir.

## Reference Docs
- `docs/decision_logic_v2.md`
- `docs/decision_support_schema.md`
- `docs/decision_support_existing_summary.md`
- `configs/decision_support.yaml`
