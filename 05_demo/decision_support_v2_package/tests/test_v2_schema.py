from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "05_demo" / "decision_support_runner.py"


def _first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError(f"No policy config found in candidates: {paths}")


POLICY_CFG = _first_existing(
    [
        ROOT / "configs" / "decision_support.yaml",
        ROOT.parents[1] / "03_docs" / "Decision_Support" / "MVP_V2" / "configs" / "decision_support.yaml",
    ]
)


def test_runner_v2_schema_and_suffix_output(tmp_path: Path) -> None:
    pred = pd.DataFrame(
        {
            "dataset_id": ["FD001"] * 6,
            "split": ["test"] * 6,
            "engine_id": [1] * 6,
            "cycle": [1, 2, 3, 4, 5, 6],
            "rul_pred": [90.0, 80.0, 70.0, 25.0, 20.0, 15.0],
        }
    )
    anomaly = pd.DataFrame(
        {
            "dataset_id": ["FD001"] * 6,
            "split": ["test"] * 6,
            "engine_id": [1] * 6,
            "cycle": [1, 2, 3, 4, 5, 6],
            "anomaly_score": [0.2, 0.9, 0.91, 0.92, 0.5, 0.4],
        }
    )

    pred_csv = tmp_path / "pred.csv"
    anomaly_csv = tmp_path / "anomaly.csv"
    out_csv = tmp_path / "fd001_decision_support.csv"

    pred.to_csv(pred_csv, index=False)
    anomaly.to_csv(anomaly_csv, index=False)

    cmd = [
        sys.executable,
        str(RUNNER),
        "--pred",
        str(pred_csv),
        "--out",
        str(out_csv),
        "--anomaly",
        str(anomaly_csv),
        "--rul-col",
        "rul_pred",
        "--anomaly-col",
        "anomaly_score",
        "--policy-config",
        str(POLICY_CFG),
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    # v1 output remains at original path, v2 is suffix-based.
    assert out_csv.exists()
    v2_csv = tmp_path / "fd001_decision_support_v2.csv"
    assert v2_csv.exists()

    v2 = pd.read_csv(v2_csv)

    required = {
        "asset_id",
        "t",
        "rul_pred",
        "anomaly_score_raw",
        "anomaly_score_smoothed",
        "anomaly_state",
        "decision_label",
        "reason_codes",
        "reason_text",
        "policy_version",
        "run_id",
        "theta_rul_used",
        "alpha_high_used",
        "alpha_low_used",
        "persistence_counter",
        "prev_state",
        "new_state",
        "smoothing_params",
        "persistence_params",
    }
    assert required.issubset(set(v2.columns))
    assert (v2["policy_version"] == "v2").all()
    assert v2["run_id"].str.match(r"^ds-\d{8}T\d{6}Z-[0-9a-f]{10}$").all()
