from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from decision_support.policy_engine import apply_policy


def _base_cfg() -> dict:
    return {
        "policy": {"version": "v2"},
        "thresholds": {
            "theta_rul": {"mode": "fixed", "value": 30},
            "alpha_anomaly": {"mode": "fixed", "value": 0.8, "q": 0.97},
        },
        "stability": {
            "smoothing": {"method": "ema", "span": 1, "window": 1},
            "hysteresis": {
                "enabled": True,
                "alpha_high_multiplier": 1.0,
                "alpha_low_multiplier": 0.9,
            },
            "persistence": {"min_cycles_on": 3},
        },
        "outputs": {"include_reason_text": True},
    }


def _run(scores: list[float]) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "asset_id": [1] * len(scores),
            "t": list(range(1, len(scores) + 1)),
            "rul_pred": [40.0] * len(scores),
            "anomaly_score_raw": scores,
        }
    )
    return apply_policy(df, _base_cfg(), id_cols=["asset_id"], time_col="t")


def test_s1_single_spike_does_not_turn_on_alarm() -> None:
    out = _run([0.20, 0.81, 0.82, 0.70, 0.69])

    assert (out["anomaly_state"] == "ON").sum() == 0
    assert (out["decision_label"] == "Enhanced Monitoring").sum() == 0


def test_s2_three_consecutive_high_scores_turn_alarm_on() -> None:
    out = _run([0.10, 0.81, 0.82, 0.83])

    assert out.loc[out["t"] == 4, "anomaly_state"].item() == "ON"
    assert out.loc[out["t"] == 4, "decision_label"].item() == "Enhanced Monitoring"


def test_s3_on_state_turns_off_below_alpha_low_without_flip_flop() -> None:
    out = _run([0.81, 0.82, 0.83, 0.75, 0.70, 0.74])

    assert out.loc[out["t"] == 3, "anomaly_state"].item() == "ON"
    assert out.loc[out["t"] == 4, "anomaly_state"].item() == "ON"
    assert out.loc[out["t"] == 5, "anomaly_state"].item() == "OFF"
    assert out.loc[out["t"] == 6, "anomaly_state"].item() == "OFF"

    reason_t5 = out.loc[out["t"] == 5, "reason_codes"].item()
    assert "STATE_CHANGE_ON_TO_OFF" in reason_t5
