from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import pandas as pd
import yaml

LOGGER = logging.getLogger(__name__)


def load_policy_config(path: str) -> Dict[str, Any]:
    """Load decision-support policy config from YAML."""
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    required = [
        ("policy", "version"),
        ("thresholds", "theta_rul"),
        ("thresholds", "alpha_anomaly"),
        ("stability", "smoothing"),
        ("stability", "hysteresis"),
        ("stability", "persistence"),
    ]
    for parent, key in required:
        if parent not in cfg or key not in cfg[parent]:
            raise ValueError(f"Missing required config field: {parent}.{key}")

    return cfg


def compute_smoothed_score(
    df: pd.DataFrame,
    score_col: str,
    method: str,
    span: int | None = None,
    window: int | None = None,
    group_cols: Sequence[str] | None = None,
    time_col: str | None = None,
) -> pd.Series:
    """Return anomaly score after per-asset smoothing."""
    if score_col not in df.columns:
        raise ValueError(f"Missing score column: {score_col}")

    if group_cols is None:
        group_cols = ["asset_id"] if "asset_id" in df.columns else []

    tmp = df.copy()
    tmp[score_col] = pd.to_numeric(tmp[score_col], errors="coerce")
    tmp["__orig_idx"] = range(len(tmp))

    sort_cols = [c for c in list(group_cols) + ([time_col] if time_col else []) if c in tmp.columns]
    if sort_cols:
        tmp = tmp.sort_values(sort_cols + ["__orig_idx"]).reset_index(drop=True)

    method = method.lower().strip()
    if method == "ema":
        if not span or int(span) < 1:
            raise ValueError("EMA smoothing requires span >= 1.")

        if group_cols:
            smoothed = tmp.groupby(list(group_cols), dropna=False)[score_col].transform(
                lambda s: s.ewm(span=int(span), adjust=False, min_periods=1).mean()
            )
        else:
            smoothed = tmp[score_col].ewm(span=int(span), adjust=False, min_periods=1).mean()

    elif method == "rolling_median":
        if not window or int(window) < 1:
            raise ValueError("Rolling median smoothing requires window >= 1.")

        if group_cols:
            smoothed = tmp.groupby(list(group_cols), dropna=False)[score_col].transform(
                lambda s: s.rolling(window=int(window), min_periods=1).median()
            )
        else:
            smoothed = tmp[score_col].rolling(window=int(window), min_periods=1).median()
    else:
        raise ValueError(f"Unsupported smoothing method: {method}")

    out = pd.Series(index=tmp["__orig_idx"], data=smoothed.values)
    return out.sort_index().reset_index(drop=True)


def calibrate_thresholds(df: pd.DataFrame, cfg: Dict[str, Any]) -> Tuple[float, float, float]:
    """Calibrate/resolve theta, alpha_high and alpha_low from policy config."""
    theta_cfg = cfg["thresholds"]["theta_rul"]
    theta_mode = str(theta_cfg.get("mode", "fixed")).lower().strip()
    if theta_mode != "fixed":
        raise ValueError(f"Unsupported theta mode: {theta_mode}")
    theta = float(theta_cfg["value"])

    alpha_cfg = cfg["thresholds"]["alpha_anomaly"]
    alpha_mode = str(alpha_cfg.get("mode", "quantile")).lower().strip()

    score_col = "anomaly_score_smoothed" if "anomaly_score_smoothed" in df.columns else "anomaly_score_raw"
    scores = pd.to_numeric(df[score_col], errors="coerce").dropna()
    if scores.empty:
        raise ValueError("Cannot calibrate alpha threshold: no anomaly scores available.")

    if alpha_mode == "fixed":
        alpha_high = float(alpha_cfg["value"])
    elif alpha_mode == "quantile":
        q = float(alpha_cfg.get("q", 0.97))
        if q <= 0.0 or q >= 1.0:
            raise ValueError(f"alpha quantile q must be in (0,1), got {q}")
        alpha_high = float(scores.quantile(q))
    else:
        raise ValueError(f"Unsupported alpha mode: {alpha_mode}")

    hyst_cfg = cfg.get("stability", {}).get("hysteresis", {})
    enabled = bool(hyst_cfg.get("enabled", True))
    high_mult = float(hyst_cfg.get("alpha_high_multiplier", 1.0))
    low_mult = float(hyst_cfg.get("alpha_low_multiplier", 0.9))

    if enabled:
        alpha_high = alpha_high * high_mult
        alpha_low = alpha_high * low_mult
    else:
        alpha_low = alpha_high

    if alpha_low > alpha_high:
        raise ValueError(
            f"Invalid hysteresis configuration: alpha_low ({alpha_low}) > alpha_high ({alpha_high})"
        )

    LOGGER.info(
        "Calibrated thresholds | theta=%.6f alpha_high=%.6f alpha_low=%.6f",
        theta,
        alpha_high,
        alpha_low,
    )
    return float(theta), float(alpha_high), float(alpha_low)


def _generate_run_id(cfg: Dict[str, Any]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = json.dumps(cfg, sort_keys=True, ensure_ascii=True)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    return f"ds-{timestamp}-{digest}"


def _decision_from_matrix(
    rul_pred: float,
    theta: float,
    anomaly_state: str,
) -> Tuple[str, str, str, str]:
    rul_low = bool(rul_pred <= theta)
    is_on = anomaly_state == "ON"

    if (not rul_low) and (not is_on):
        return (
            "Normal Operation",
            "RUL_HIGH|ANOM_OFF",
            "Rutin izleme",
            "RUL > theta ve anomaly_state OFF; rutin operasyon devam.",
        )
    if (not rul_low) and is_on:
        return (
            "Enhanced Monitoring",
            "RUL_HIGH|ANOM_ON",
            "İzleme artır + teşhis",
            "RUL yüksek ancak anomaly_state ON; izleme/teşhis artırılmalı.",
        )
    if rul_low and (not is_on):
        return (
            "Planned Maintenance",
            "RUL_LOW|ANOM_OFF",
            "Planlı bakım/inspection",
            "RUL <= theta; planlı bakım penceresine girildi.",
        )
    return (
        "Immediate Maintenance",
        "RUL_LOW|ANOM_ON",
        "Acil bakım kararı için yükselt",
        "RUL <= theta ve anomaly_state ON; acil bakım değerlendirmesi gerekli.",
    )


def apply_policy(
    df: pd.DataFrame,
    cfg: Dict[str, Any],
    id_cols: Sequence[str],
    time_col: str,
) -> pd.DataFrame:
    """Apply v2 policy engine and return deterministic, audit-friendly output."""
    if not id_cols:
        raise ValueError("id_cols cannot be empty.")

    required_cols = list(id_cols) + [time_col, "rul_pred", "anomaly_score_raw"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Input DataFrame missing required columns: {missing}")

    out = df.copy()
    out["rul_pred"] = pd.to_numeric(out["rul_pred"], errors="coerce")
    out["anomaly_score_raw"] = pd.to_numeric(out["anomaly_score_raw"], errors="coerce")

    smooth_cfg = cfg["stability"]["smoothing"]
    out["anomaly_score_smoothed"] = compute_smoothed_score(
        out,
        score_col="anomaly_score_raw",
        method=str(smooth_cfg.get("method", "ema")),
        span=int(smooth_cfg.get("span", 7)),
        window=int(smooth_cfg.get("window", 7)),
        group_cols=id_cols,
        time_col=time_col,
    )

    theta, alpha_high, alpha_low = calibrate_thresholds(out, cfg)
    run_id = _generate_run_id(cfg)
    policy_version = str(cfg.get("policy", {}).get("version", "v2"))
    min_cycles_on = int(cfg["stability"]["persistence"].get("min_cycles_on", 3))
    include_reason_text = bool(cfg.get("outputs", {}).get("include_reason_text", True))

    out = out.sort_values(list(id_cols) + [time_col]).reset_index(drop=True)

    # Initialize audit/state columns.
    out["anomaly_state"] = "OFF"
    out["decision_label"] = ""
    out["reason_codes"] = ""
    out["reason_text"] = ""
    out["recommended_action_text"] = ""
    out["theta_rul_used"] = theta
    out["alpha_high_used"] = alpha_high
    out["alpha_low_used"] = alpha_low
    out["policy_version"] = policy_version
    out["run_id"] = run_id
    out["persistence_counter"] = 0
    out["prev_state"] = "OFF"
    out["new_state"] = "OFF"
    out["smoothing_params"] = json.dumps(
        {
            "method": str(smooth_cfg.get("method", "ema")),
            "span": int(smooth_cfg.get("span", 7)),
            "window": int(smooth_cfg.get("window", 7)),
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    out["persistence_params"] = json.dumps(
        {"min_cycles_on": min_cycles_on}, ensure_ascii=True, sort_keys=True
    )

    for _, grp in out.groupby(list(id_cols), sort=False):
        state = "OFF"
        persistence_counter = 0

        for idx in grp.index:
            score = out.at[idx, "anomaly_score_smoothed"]
            prev_state = state

            candidate_on = pd.notna(score) and float(score) >= alpha_high
            candidate_off = pd.notna(score) and float(score) <= alpha_low

            if state == "OFF":
                if candidate_on:
                    persistence_counter += 1
                    if persistence_counter >= min_cycles_on:
                        state = "ON"
                else:
                    persistence_counter = 0
            else:  # state == ON
                if candidate_off:
                    state = "OFF"
                    persistence_counter = 0
                elif candidate_on:
                    persistence_counter = max(persistence_counter, min_cycles_on)
                # hysteresis band: keep current state as-is

            decision_label, base_reason, action_text, base_text = _decision_from_matrix(
                rul_pred=float(out.at[idx, "rul_pred"]),
                theta=theta,
                anomaly_state=state,
            )

            reason_codes: List[str] = [base_reason]
            if candidate_on and state == "OFF":
                reason_codes.append("PERSISTENCE_PENDING")
            if prev_state != state:
                reason_codes.append(f"STATE_CHANGE_{prev_state}_TO_{state}")

            reason_text = base_text
            if "PERSISTENCE_PENDING" in reason_codes:
                reason_text += f" ON için {min_cycles_on} ardışık cycle şartı henüz tamamlanmadı."

            out.at[idx, "anomaly_state"] = state
            out.at[idx, "decision_label"] = decision_label
            out.at[idx, "reason_codes"] = "|".join(reason_codes)
            out.at[idx, "reason_text"] = reason_text if include_reason_text else ""
            out.at[idx, "recommended_action_text"] = action_text
            out.at[idx, "persistence_counter"] = int(persistence_counter)
            out.at[idx, "prev_state"] = prev_state
            out.at[idx, "new_state"] = state

    ordered_cols = (
        list(id_cols)
        + [
            time_col,
            "rul_pred",
            "anomaly_score_raw",
            "anomaly_score_smoothed",
            "anomaly_state",
            "decision_label",
            "reason_codes",
            "reason_text",
            "recommended_action_text",
            "theta_rul_used",
            "alpha_high_used",
            "alpha_low_used",
            "policy_version",
            "run_id",
            "persistence_counter",
            "prev_state",
            "new_state",
            "smoothing_params",
            "persistence_params",
        ]
    )

    return out[ordered_cols].sort_values(list(id_cols) + [time_col]).reset_index(drop=True)
