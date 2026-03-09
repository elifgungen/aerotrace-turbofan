from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "05_demo" / "decision_support_runner.py"

EXPECTED_V1_COLUMNS = [
    "engine_id",
    "cycle",
    "rul_pred",
    "anomaly_score",
    "decision_label",
    "reason_codes",
    "reason_text",
    "theta_rul_used",
    "alpha_anomaly_used",
]


def test_runner_v1_backward_compatible_columns(tmp_path: Path) -> None:
    pred = pd.DataFrame(
        {
            "engine_id": [1, 1, 1, 2],
            "cycle": [1, 2, 3, 1],
            "rul_pred": [100.0, 80.0, 60.0, 120.0],
        }
    )
    anomaly = pd.DataFrame(
        {
            "engine_id": [1, 1, 1, 2],
            "cycle": [1, 2, 3, 1],
            "anomaly_score": [0.10, 0.20, 0.30, 0.05],
        }
    )

    pred_csv = tmp_path / "pred.csv"
    anomaly_csv = tmp_path / "anomaly.csv"
    out_csv = tmp_path / "fd001_decision_support.csv"
    out_v1_csv = tmp_path / "fd001_decision_support_contract.csv"

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
        "--emit-v1",
        str(out_v1_csv),
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    assert out_csv.exists()
    assert out_v1_csv.exists()

    got = pd.read_csv(out_v1_csv)

    assert list(got.columns) == EXPECTED_V1_COLUMNS
    assert len(got) == len(pred)
