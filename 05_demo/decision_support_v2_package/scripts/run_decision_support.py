#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from decision_support.adapters.cmapss_adapter import run_cmapss_adapter
from decision_support.adapters.ncmapss_adapter import run_ncmapss_adapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Run decision support v2 for C-MAPSS or N-CMAPSS")
    parser.add_argument("--config", default="configs/decision_support.yaml", help="Policy YAML path")
    parser.add_argument("--dataset", choices=["cmapss", "ncmapss"], required=True)
    parser.add_argument("--rul_csv", required=True)
    parser.add_argument("--anomaly_csv", required=True)
    parser.add_argument("--out_csv", default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")

    if args.dataset == "cmapss":
        result = run_cmapss_adapter(
            rul_csv=args.rul_csv,
            anomaly_csv=args.anomaly_csv,
            config_path=args.config,
            out_csv=args.out_csv,
        )
    else:
        result = run_ncmapss_adapter(
            rul_csv=args.rul_csv,
            anomaly_csv=args.anomaly_csv,
            config_path=args.config,
            out_csv=args.out_csv,
        )

    print(
        f"dataset={args.dataset} rows={result.rows} out={result.output_path} "
        f"join_keys={','.join(result.join_keys)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
