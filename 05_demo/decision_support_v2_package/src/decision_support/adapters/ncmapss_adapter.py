from __future__ import annotations

import argparse
import logging
from pathlib import Path

from decision_support.adapters._common import AdapterResult, merge_and_standardize

LOGGER = logging.getLogger(__name__)


def run_ncmapss_adapter(
    rul_csv: str,
    anomaly_csv: str,
    config_path: str,
    out_csv: str | None = None,
) -> AdapterResult:
    if out_csv is None:
        stem = Path(rul_csv).stem.replace("_rul_predictions_autogluon_FIXED", "")
        out_csv = f"OUTPUTS/{stem}_decision_support_v2.csv"

    return merge_and_standardize(
        rul_csv=rul_csv,
        anomaly_csv=anomaly_csv,
        config_path=config_path,
        out_csv=out_csv,
        dataset_tag="ncmapss",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run v2 decision support adapter for N-CMAPSS")
    parser.add_argument("--config", required=True, help="Path to configs/decision_support.yaml")
    parser.add_argument("--rul_csv", required=True, help="RUL predictions CSV")
    parser.add_argument("--anomaly_csv", required=True, help="Anomaly scores CSV")
    parser.add_argument("--out_csv", default=None, help="Optional output CSV path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")
    result = run_ncmapss_adapter(
        rul_csv=args.rul_csv,
        anomaly_csv=args.anomaly_csv,
        config_path=args.config,
        out_csv=args.out_csv,
    )
    LOGGER.info("Output written: %s", result.output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
