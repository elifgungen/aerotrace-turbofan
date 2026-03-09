#!/usr/bin/env python3
"""
Run Phase-1 Digital Twin replay on prebuilt N-CMAPSS twin feeds.

Inputs:
- twin/inputs/ncmapss_DSxx_twin_feed.csv
- twin/config/phase1_policy.yaml

Outputs per dataset:
- twin/outputs/DSxx/state_timeline.csv
- twin/outputs/DSxx/events.csv
- twin/outputs/DSxx/summary.json

Combined:
- twin/outputs/phase1_summary.csv
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import yaml


REQUIRED_COLS = ["dataset_id", "split", "engine_id", "cycle", "rul_pred", "anomaly_score"]
DEFAULT_DATASETS = ["DS01", "DS02", "DS03", "DS04", "DS05", "DS06", "DS07"]
NORMAL = "Normal Operation"
ENHANCED = "Enhanced Monitoring"
PLANNED = "Planned Maintenance"
IMMEDIATE = "Immediate Maintenance"


@dataclass
class EngineState:
    anomaly_on: bool = False
    on_count: int = 0
    off_count: int = 0
    last_decision: str = NORMAL


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Phase-1 replay for N-CMAPSS Twin feeds.")
    p.add_argument(
        "--inputs-root",
        default="twin/inputs",
        help="Folder containing ncmapss_DSxx_twin_feed.csv files.",
    )
    p.add_argument(
        "--outputs-root",
        default="twin/outputs",
        help="Folder where replay outputs are written.",
    )
    p.add_argument(
        "--policy-yaml",
        default="twin/config/phase1_policy.yaml",
        help="Path to policy yaml.",
    )
    p.add_argument(
        "--datasets",
        nargs="+",
        default=DEFAULT_DATASETS,
        help="Dataset IDs to run. Default: DS01..DS07",
    )
    p.add_argument(
        "--split-mode",
        choices=["all", "test_only"],
        default=None,
        help="Override policy split_mode.",
    )
    return p.parse_args()


def load_policy(path: Path) -> Dict:
    if not path.exists():
        raise FileNotFoundError(f"Policy YAML not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Policy YAML must parse to a dictionary.")
    return data


def validate_feed(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{dataset}: missing required columns: {missing}")
    out = df.copy()
    out["dataset_id"] = out["dataset_id"].astype(str).str.strip()
    out["split"] = out["split"].astype(str).str.strip().str.lower()
    out["engine_id"] = pd.to_numeric(out["engine_id"], errors="raise").astype(int)
    out["cycle"] = pd.to_numeric(out["cycle"], errors="raise").astype(int)
    out["rul_pred"] = pd.to_numeric(out["rul_pred"], errors="raise").astype(float)
    out["anomaly_score"] = pd.to_numeric(out["anomaly_score"], errors="raise").astype(float)
    if out.duplicated(subset=["dataset_id", "split", "engine_id", "cycle"]).any():
        dups = int(out.duplicated(subset=["dataset_id", "split", "engine_id", "cycle"]).sum())
        raise ValueError(f"{dataset}: duplicated key rows detected: {dups}")
    return out


def compute_decision(rul_pred: float, anomaly_on: bool, theta_rul: float, immediate_requires_anomaly: bool) -> str:
    rul_low = rul_pred <= theta_rul
    if rul_low and anomaly_on:
        return IMMEDIATE
    if rul_low and not anomaly_on:
        return PLANNED
    if (not rul_low) and anomaly_on:
        return ENHANCED
    if (not immediate_requires_anomaly) and rul_low:
        return IMMEDIATE
    return NORMAL


def run_dataset(df: pd.DataFrame, dataset: str, policy: Dict) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    theta_rul = float(policy["thresholds"]["theta_rul"])
    alpha_high = float(policy["thresholds"]["alpha_high"])
    alpha_low = float(policy["thresholds"]["alpha_low"])
    debounce_on = int(policy["logic"]["debounce_on"])
    debounce_off = int(policy["logic"]["debounce_off"])
    immediate_requires_anomaly = bool(policy["logic"]["immediate_requires_anomaly_on"])
    policy_version = str(policy.get("policy_version", "phase1-v1"))

    # Stable replay order.
    split_rank = {"train": 0, "test": 1}
    replay = df.copy()
    replay["split_rank"] = replay["split"].map(split_rank).fillna(99).astype(int)
    replay = replay.sort_values(["split_rank", "engine_id", "cycle"], kind="stable").drop(
        columns=["split_rank"]
    )

    states: Dict[int, EngineState] = {}
    timeline_rows: List[Dict] = []
    event_rows: List[Dict] = []

    for row in replay.itertuples(index=False):
        engine = int(row.engine_id)
        state = states.setdefault(engine, EngineState())
        prev_anomaly = state.anomaly_on
        prev_decision = state.last_decision

        score = float(row.anomaly_score)
        if not state.anomaly_on:
            if score >= alpha_high:
                state.on_count += 1
            else:
                state.on_count = 0
            if state.on_count >= debounce_on:
                state.anomaly_on = True
                state.off_count = 0
        else:
            if score <= alpha_low:
                state.off_count += 1
            else:
                state.off_count = 0
            if state.off_count >= debounce_off:
                state.anomaly_on = False
                state.on_count = 0

        decision = compute_decision(
            rul_pred=float(row.rul_pred),
            anomaly_on=state.anomaly_on,
            theta_rul=theta_rul,
            immediate_requires_anomaly=immediate_requires_anomaly,
        )
        state.last_decision = decision

        rul_risk = float(np.clip((theta_rul - float(row.rul_pred)) / max(theta_rul, 1e-9), 0.0, 1.0))
        anom_risk = float(
            np.clip(
                (score - alpha_low) / max(alpha_high - alpha_low, 1e-9),
                0.0,
                1.0,
            )
        )
        risk_score = int(round(100.0 * max(rul_risk, anom_risk)))

        alarm_active = decision in {ENHANCED, IMMEDIATE}
        critical_proxy = (float(row.rul_pred) <= theta_rul) and (score >= alpha_high)
        missed_alarm_proxy = bool(critical_proxy and not alarm_active)

        timeline_rows.append(
            {
                "dataset_id": row.dataset_id,
                "split": row.split,
                "engine_id": engine,
                "cycle": int(row.cycle),
                "rul_pred": float(row.rul_pred),
                "anomaly_score": score,
                "anomaly_state": "ON" if state.anomaly_on else "OFF",
                "decision_label": decision,
                "alarm_active": alarm_active,
                "critical_proxy": critical_proxy,
                "missed_alarm_proxy": missed_alarm_proxy,
                "rul_risk": rul_risk,
                "anom_risk": anom_risk,
                "risk_score": risk_score,
                "theta_rul_used": theta_rul,
                "alpha_high_used": alpha_high,
                "alpha_low_used": alpha_low,
                "policy_version": policy_version,
            }
        )

        if (prev_anomaly != state.anomaly_on) or (prev_decision != decision):
            event_rows.append(
                {
                    "dataset_id": row.dataset_id,
                    "split": row.split,
                    "engine_id": engine,
                    "cycle": int(row.cycle),
                    "event_type": "transition",
                    "anomaly_state_prev": "ON" if prev_anomaly else "OFF",
                    "anomaly_state_new": "ON" if state.anomaly_on else "OFF",
                    "decision_prev": prev_decision,
                    "decision_new": decision,
                }
            )

    timeline = pd.DataFrame(timeline_rows)
    events = pd.DataFrame(event_rows)

    # Summary metrics.
    alarm_rate = float((timeline["alarm_active"].mean() if len(timeline) else 0.0) * 100.0)
    immediate_rate = float(((timeline["decision_label"] == IMMEDIATE).mean() if len(timeline) else 0.0) * 100.0)
    missed_count = int(timeline["missed_alarm_proxy"].sum())
    missed_rate = float((timeline["missed_alarm_proxy"].mean() if len(timeline) else 0.0) * 100.0)

    lead_values: List[float] = []
    for _, g in timeline.sort_values(["engine_id", "cycle"]).groupby("engine_id"):
        first_alarm = g.loc[g["alarm_active"], "cycle"]
        first_low = g.loc[g["rul_pred"] <= theta_rul, "cycle"]
        if not first_alarm.empty and not first_low.empty:
            lead_values.append(float(first_low.iloc[0] - first_alarm.iloc[0]))

    summary = {
        "dataset": dataset,
        "rows": int(len(timeline)),
        "engines": int(timeline["engine_id"].nunique()) if len(timeline) else 0,
        "alarm_rate_pct": round(alarm_rate, 4),
        "immediate_rate_pct": round(immediate_rate, 4),
        "missed_alarm_proxy_count": missed_count,
        "missed_alarm_proxy_rate_pct": round(missed_rate, 4),
        "avg_lead_cycles": round(float(np.mean(lead_values)), 4) if lead_values else None,
        "theta_rul_used": theta_rul,
        "alpha_high_used": alpha_high,
        "alpha_low_used": alpha_low,
        "debounce_on_used": debounce_on,
        "debounce_off_used": debounce_off,
        "policy_version": policy_version,
    }
    return timeline, events, summary


def main() -> None:
    args = parse_args()
    policy = load_policy(Path(args.policy_yaml))
    split_mode = args.split_mode or policy.get("split_mode", "all")
    if split_mode not in {"all", "test_only"}:
        raise ValueError(f"Invalid split_mode={split_mode}")

    inputs_root = Path(args.inputs_root)
    outputs_root = Path(args.outputs_root)
    outputs_root.mkdir(parents=True, exist_ok=True)

    summary_rows: List[Dict] = []

    for ds in args.datasets:
        feed_path = inputs_root / f"ncmapss_{ds}_twin_feed.csv"
        if not feed_path.exists():
            raise FileNotFoundError(f"{ds}: twin feed file missing: {feed_path}")

        raw = pd.read_csv(feed_path)
        df = validate_feed(raw, ds)
        if split_mode == "test_only":
            df = df[df["split"] == "test"].copy()

        timeline, events, summary = run_dataset(df, ds, policy)

        ds_out = outputs_root / ds
        ds_out.mkdir(parents=True, exist_ok=True)
        timeline.to_csv(ds_out / "state_timeline.csv", index=False)
        events.to_csv(ds_out / "events.csv", index=False)
        (ds_out / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(
            f"{ds}: rows={summary['rows']} alarm_rate={summary['alarm_rate_pct']}% "
            f"missed_proxy={summary['missed_alarm_proxy_count']}"
        )
        summary_rows.append(summary)

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(outputs_root / "phase1_summary.csv", index=False)
    print(f"summary={outputs_root / 'phase1_summary.csv'}")


if __name__ == "__main__":
    main()


