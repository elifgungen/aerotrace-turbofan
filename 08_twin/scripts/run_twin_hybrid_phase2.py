#!/usr/bin/env python3
"""
Run Phase-2 hybrid twin fusion on N-CMAPSS decision-support outputs.

Input:
- 08_twin/data/decision_support_v2_outputs/ncmapss_DSxx_decision_support_v2.csv

Output per dataset:
- 08_twin/data/hybrid_phase2/DSxx/hybrid_timeline.csv
- 08_twin/data/hybrid_phase2/DSxx/summary.json

Combined outputs:
- 08_twin/data/hybrid_phase2/hybrid_phase2_summary.csv
- 08_twin/data/hybrid_phase2/hybrid_phase2_readiness_audit.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


DEFAULT_DATASETS = ["DS01", "DS02", "DS03", "DS04", "DS05", "DS06", "DS07"]
RE_V2_NCMAPSS = re.compile(r"^ncmapss_(DS\d{2})_decision_support_v2\.csv$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run hybrid phase-2 twin fusion.")
    parser.add_argument("--policy-root", default="08_twin/data/decision_support_v2_outputs")
    parser.add_argument("--out-root", default="08_twin/data/hybrid_phase2")
    parser.add_argument("--config", default="08_twin/config/hybrid_phase2_policy.json")
    parser.add_argument("--datasets", nargs="+", default=DEFAULT_DATASETS)
    parser.add_argument("--split-mode", choices=["all", "test_only"], default="all")
    return parser.parse_args()


def load_config(path: Path) -> Dict:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Config must be a JSON object.")
    return payload


def discover_policy_file(policy_root: Path, dataset: str) -> Path:
    target = policy_root / f"ncmapss_{dataset}_decision_support_v2.csv"
    if target.exists():
        return target

    matches: List[Path] = []
    for item in policy_root.iterdir():
        if not item.is_file():
            continue
        match = RE_V2_NCMAPSS.match(item.name)
        if not match:
            continue
        if match.group(1).upper() == dataset:
            matches.append(item)

    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(f"{dataset}: decision-support v2 file missing under {policy_root}")
    raise RuntimeError(f"{dataset}: multiple matching policy files: {matches}")


def validate_and_normalize(df: pd.DataFrame, dataset: str, config: Dict) -> Tuple[pd.DataFrame, Dict[str, object]]:
    contract = config["contract"]
    required_columns = list(contract["required_columns"])
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"{dataset}: missing required columns: {missing}")

    out = df.rename(columns={"asset_id": "engine_id", "t": "cycle"}).copy()
    out["dataset_id"] = out["dataset_id"].astype(str).str.upper().str.strip()
    out["split"] = out["split"].astype(str).str.lower().str.strip()
    out["engine_id"] = pd.to_numeric(out["engine_id"], errors="raise").astype(int)
    out["cycle"] = pd.to_numeric(out["cycle"], errors="raise").astype(int)

    numeric_cols = [
        "rul_pred",
        "anomaly_score_raw",
        "anomaly_score_smoothed",
        "theta_rul_used",
        "alpha_high_used",
        "alpha_low_used",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").astype(float)

    key_cols = ["dataset_id", "split", "engine_id", "cycle"]
    duplicates = int(out.duplicated(key_cols).sum())
    if duplicates:
        raise ValueError(f"{dataset}: duplicated canonical keys detected: {duplicates}")

    nonfinite_counts: Dict[str, int] = {}
    for col in numeric_cols:
        values = out[col].to_numpy(dtype=float)
        bad = int((~np.isfinite(values)).sum())
        if bad > 0:
            nonfinite_counts[col] = bad

    allowed_splits = set(contract.get("allowed_splits", ["train", "test"]))
    split_values = sorted(out["split"].dropna().astype(str).unique().tolist())
    canonical_split_ok = set(split_values).issubset(allowed_splits)
    if bool(contract.get("require_canonical_split", True)) and not canonical_split_ok:
        raise ValueError(f"{dataset}: non-canonical split values: {split_values}")

    dataset_values = set(out["dataset_id"].astype(str).unique().tolist())
    dataset_match_ok = dataset_values == {dataset}
    if not dataset_match_ok:
        raise ValueError(f"{dataset}: unexpected dataset_id values in file: {sorted(dataset_values)}")

    return out.sort_values(["split", "engine_id", "cycle"]).reset_index(drop=True), {
        "rows": int(len(out)),
        "duplicates": duplicates,
        "split_values": split_values,
        "canonical_split_ok": canonical_split_ok,
        "nonfinite_counts": nonfinite_counts,
    }


def policy_risk(decision_label: str) -> float:
    mapping = {
        "Normal Operation": 0.15,
        "Enhanced Monitoring": 0.45,
        "Planned Maintenance": 0.72,
        "Immediate Maintenance": 0.95,
    }
    return float(mapping.get(str(decision_label), 0.50))


def infer_stage(row: pd.Series) -> str:
    reason_codes = str(row.get("reason_codes", ""))
    decision = str(row.get("decision_label", ""))
    anomaly_state = str(row.get("anomaly_state", "OFF"))

    if "PERSISTENCE_PENDING" in reason_codes:
        return "Anomaly Persistence Gate"
    if decision == "Immediate Maintenance":
        return "Immediate Failure Risk"
    if decision == "Planned Maintenance" and anomaly_state == "OFF":
        return "RUL Degradation Path"
    if float(row.get("volatility_risk", 0.0)) >= 0.7:
        return "Threshold Volatility"
    return "Stable Monitoring"


def classify_state(hybrid_risk: float, warning_th: float, critical_th: float) -> str:
    if hybrid_risk >= critical_th:
        return "critical"
    if hybrid_risk >= warning_th:
        return "warning"
    return "normal"


def run_engine_group(group: pd.DataFrame, config: Dict) -> pd.DataFrame:
    fusion = config["fusion"]
    trend_window = int(fusion["trend_window"])
    trend_drop_ref = float(fusion["trend_drop_ref_per_cycle"])
    rul_std_ref = float(fusion["rul_std_ref"])
    anom_std_ref = float(fusion["anom_std_ref"])

    g = group.sort_values("cycle").copy()

    theta = g["theta_rul_used"].astype(float)
    rul = g["rul_pred"].astype(float)
    alpha_low = g["alpha_low_used"].astype(float)
    alpha_high = g["alpha_high_used"].astype(float)
    anom = g["anomaly_score_smoothed"].astype(float)

    denom_rul = theta.clip(lower=1e-9)
    g["rul_risk"] = np.clip((theta - rul) / denom_rul, 0.0, 1.0)

    denom_anom = (alpha_high - alpha_low).clip(lower=1e-9)
    g["anom_risk"] = np.clip((anom - alpha_low) / denom_anom, 0.0, 1.0)

    g["policy_risk"] = g["decision_label"].astype(str).map(policy_risk).astype(float)

    g["rul_drop_per_cycle"] = -g["rul_pred"].diff().fillna(0.0)
    g["rul_drop_smoothed"] = (
        g["rul_drop_per_cycle"].rolling(window=trend_window, min_periods=3).mean().fillna(0.0)
    )
    g["trend_risk"] = np.clip(g["rul_drop_smoothed"] / max(trend_drop_ref, 1e-9), 0.0, 1.0)

    g["rul_std"] = g["rul_pred"].rolling(window=trend_window, min_periods=3).std().fillna(0.0)
    g["anom_std"] = g["anomaly_score_smoothed"].rolling(window=trend_window, min_periods=3).std().fillna(0.0)

    g["volatility_risk"] = np.clip(
        0.5 * (g["rul_std"] / max(rul_std_ref, 1e-9)) +
        0.5 * (g["anom_std"] / max(anom_std_ref, 1e-9)),
        0.0,
        1.0,
    )

    rul_inside = float(fusion["rul_weight_inside_model"])
    anom_inside = float(fusion["anomaly_weight_inside_model"])
    inside_sum = max(rul_inside + anom_inside, 1e-9)
    rul_inside /= inside_sum
    anom_inside /= inside_sum

    g["model_risk"] = rul_inside * g["rul_risk"] + anom_inside * g["anom_risk"]

    w_model = float(fusion["model_weight"])
    w_policy = float(fusion["policy_weight"])
    w_physics = float(fusion["physics_weight"])
    w_unc = float(fusion["uncertainty_weight"])
    w_total = max(w_model + w_policy + w_physics + w_unc, 1e-9)
    w_model /= w_total
    w_policy /= w_total
    w_physics /= w_total
    w_unc /= w_total

    g["hybrid_risk"] = (
        w_model * g["model_risk"]
        + w_policy * g["policy_risk"]
        + w_physics * g["trend_risk"]
        + w_unc * g["volatility_risk"]
    )

    g["reason_codes"] = g["reason_codes"].astype(str)
    boost = float(fusion.get("persistence_pending_boost", 0.0))
    g.loc[g["reason_codes"].str.contains("PERSISTENCE_PENDING", na=False), "hybrid_risk"] += boost

    critical_floor = float(fusion["critical_floor_on_immediate"])
    immediate_mask = g["decision_label"].astype(str).eq("Immediate Maintenance")
    g.loc[immediate_mask, "hybrid_risk"] = np.maximum(g.loc[immediate_mask, "hybrid_risk"], critical_floor)
    g["hybrid_risk"] = np.clip(g["hybrid_risk"], 0.0, 1.0)

    warning_th = float(config["thresholds"]["warning"])
    critical_th = float(config["thresholds"]["critical"])
    g["hybrid_state"] = [classify_state(v, warning_th, critical_th) for v in g["hybrid_risk"].tolist()]

    critical_proxy = (g["rul_pred"] <= g["theta_rul_used"]) & (
        (g["anomaly_score_smoothed"] >= g["alpha_high_used"]) | (g["anomaly_state"].astype(str) == "ON")
    )
    g["critical_proxy"] = critical_proxy
    g["hybrid_alarm_active"] = g["hybrid_state"].isin(["warning", "critical"])
    g["missed_alarm_proxy"] = g["critical_proxy"] & (g["hybrid_state"] != "critical")
    g["early_alarm_proxy"] = (~g["critical_proxy"]) & (g["hybrid_state"] == "critical")

    g["dominant_driver"] = np.select(
        [
            (g["model_risk"] >= g["policy_risk"]) & (g["model_risk"] >= g["trend_risk"]) & (g["model_risk"] >= g["volatility_risk"]),
            (g["policy_risk"] >= g["model_risk"]) & (g["policy_risk"] >= g["trend_risk"]) & (g["policy_risk"] >= g["volatility_risk"]),
            (g["trend_risk"] >= g["model_risk"]) & (g["trend_risk"] >= g["policy_risk"]) & (g["trend_risk"] >= g["volatility_risk"]),
        ],
        ["model", "policy", "physics"],
        default="uncertainty",
    )
    g["expected_failure_stage"] = g.apply(infer_stage, axis=1)

    return g


def build_dataset_hybrid(df: pd.DataFrame, config: Dict, split_mode: str) -> pd.DataFrame:
    work = df.copy()
    if split_mode == "test_only":
        work = work[work["split"] == "test"].copy()

    outputs: List[pd.DataFrame] = []
    for (_, _, _), group in work.groupby(["dataset_id", "split", "engine_id"], sort=False):
        outputs.append(run_engine_group(group, config))

    if not outputs:
        return pd.DataFrame()
    return pd.concat(outputs, axis=0, ignore_index=True).sort_values(["split", "engine_id", "cycle"]).reset_index(drop=True)


def summarize_dataset(hybrid_df: pd.DataFrame, dataset: str, config: Dict) -> Dict[str, object]:
    if hybrid_df.empty:
        return {
            "dataset": dataset,
            "rows": 0,
            "engines": 0,
            "hybrid_alarm_rate_pct": 0.0,
            "hybrid_critical_rate_pct": 0.0,
            "critical_proxy_rate_pct": 0.0,
            "missed_alarm_proxy_rate_pct": 0.0,
            "critical_detection_recall_pct": 0.0,
            "early_alarm_proxy_rate_pct": 0.0,
            "avg_hybrid_risk": 0.0,
            "warning_threshold": float(config["thresholds"]["warning"]),
            "critical_threshold": float(config["thresholds"]["critical"]),
            "config_version": str(config.get("version", "unknown")),
        }

    critical_proxy_count = int(hybrid_df["critical_proxy"].sum())
    detected_critical_count = int((hybrid_df["critical_proxy"] & (hybrid_df["hybrid_state"] == "critical")).sum())
    recall = float(100.0 * detected_critical_count / critical_proxy_count) if critical_proxy_count > 0 else 0.0

    return {
        "dataset": dataset,
        "rows": int(len(hybrid_df)),
        "engines": int(hybrid_df["engine_id"].nunique()),
        "hybrid_alarm_rate_pct": round(float(hybrid_df["hybrid_alarm_active"].mean() * 100.0), 4),
        "hybrid_critical_rate_pct": round(float((hybrid_df["hybrid_state"] == "critical").mean() * 100.0), 4),
        "critical_proxy_rate_pct": round(float(hybrid_df["critical_proxy"].mean() * 100.0), 4),
        "missed_alarm_proxy_rate_pct": round(float(hybrid_df["missed_alarm_proxy"].mean() * 100.0), 4),
        "critical_detection_recall_pct": round(recall, 4),
        "early_alarm_proxy_rate_pct": round(float(hybrid_df["early_alarm_proxy"].mean() * 100.0), 4),
        "avg_hybrid_risk": round(float(hybrid_df["hybrid_risk"].mean()), 6),
        "warning_threshold": float(config["thresholds"]["warning"]),
        "critical_threshold": float(config["thresholds"]["critical"]),
        "config_version": str(config.get("version", "unknown")),
    }


def main() -> None:
    args = parse_args()

    config = load_config(Path(args.config))
    policy_root = Path(args.policy_root)
    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    datasets = [str(x).strip().upper() for x in args.datasets if str(x).strip()]
    if not datasets:
        raise ValueError("No dataset specified.")

    readiness_rows: List[Dict[str, object]] = []
    summary_rows: List[Dict[str, object]] = []

    for ds in datasets:
        policy_file = discover_policy_file(policy_root, ds)
        raw_df = pd.read_csv(policy_file)

        normalized_df, checks = validate_and_normalize(raw_df, ds, config)
        hybrid_df = build_dataset_hybrid(normalized_df, config=config, split_mode=args.split_mode)

        dataset_dir = out_root / ds
        dataset_dir.mkdir(parents=True, exist_ok=True)

        keep_cols = [
            "dataset_id",
            "split",
            "engine_id",
            "cycle",
            "rul_pred",
            "anomaly_score_raw",
            "anomaly_score_smoothed",
            "anomaly_state",
            "decision_label",
            "reason_codes",
            "theta_rul_used",
            "alpha_high_used",
            "alpha_low_used",
            "model_risk",
            "policy_risk",
            "trend_risk",
            "volatility_risk",
            "hybrid_risk",
            "hybrid_state",
            "hybrid_alarm_active",
            "critical_proxy",
            "missed_alarm_proxy",
            "early_alarm_proxy",
            "dominant_driver",
            "expected_failure_stage",
            "policy_version",
            "run_id",
        ]
        hybrid_out = hybrid_df[keep_cols].copy()
        hybrid_out.to_csv(dataset_dir / "hybrid_timeline.csv", index=False)

        summary = summarize_dataset(hybrid_out, ds, config)
        (dataset_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8-sig")

        ready = len(checks.get("nonfinite_counts", {})) == 0 and bool(checks.get("canonical_split_ok", False))
        readiness_rows.append(
            {
                "dataset": ds,
                "policy_file": str(policy_file),
                "rows": int(checks["rows"]),
                "split_values": checks["split_values"],
                "duplicates": int(checks["duplicates"]),
                "nonfinite_counts": checks["nonfinite_counts"],
                "canonical_split_ok": bool(checks["canonical_split_ok"]),
                "ready": bool(ready),
            }
        )
        summary_rows.append(summary)

        print(
            f"{ds}: rows={summary['rows']} engines={summary['engines']} "
            f"missed_alarm_proxy_rate={summary['missed_alarm_proxy_rate_pct']}%"
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(out_root / "hybrid_phase2_summary.csv", index=False)

    readiness_payload = {
        "overall_ready": bool(all(x["ready"] for x in readiness_rows)),
        "config_version": str(config.get("version", "unknown")),
        "split_mode": args.split_mode,
        "datasets": readiness_rows,
    }
    (out_root / "hybrid_phase2_readiness_audit.json").write_text(
        json.dumps(readiness_payload, indent=2, ensure_ascii=False),
        encoding="utf-8-sig",
    )

    if not readiness_payload["overall_ready"]:
        raise SystemExit("Hybrid phase-2 completed with readiness failures. Check audit JSON.")


if __name__ == "__main__":
    main()


