#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import hashlib
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def _cli_has(flag: str) -> bool:
    return flag in sys.argv


def _read_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256_file(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


__VERSION__ = "2026-01-28"


def _read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    unnamed = [c for c in df.columns if str(c).lower().startswith("unnamed")]
    if unnamed:
        df = df.drop(columns=unnamed)
    return df


def _infer_rul_col(df: pd.DataFrame, user_col: Optional[str]) -> str:
    if user_col:
        if user_col not in df.columns:
            raise ValueError(f"--rul-col={user_col} not found in predictions CSV.")
        return user_col

    for c in ["rul_pred", "RUL_pred", "pred_ensemble", "y_pred"]:
        if c in df.columns:
            return c
    raise ValueError("Could not infer RUL prediction column. Use --rul-col.")


def _require_cols(df: pd.DataFrame, cols: List[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing required columns: {missing}")


@dataclass(frozen=True)
class Thresholds:
    theta_warn: float
    theta_critical: float
    alpha_warn: Optional[float]
    alpha_critical: Optional[float]


def _quantile_thresholds(
    rul_series: pd.Series,
    anomaly_series: Optional[pd.Series],
    theta_warn_q: float,
    theta_critical_q: float,
    alpha_warn_q: float,
    alpha_critical_q: float,
) -> Thresholds:
    theta_warn = float(rul_series.quantile(theta_warn_q))
    theta_critical = float(rul_series.quantile(theta_critical_q))
    if anomaly_series is None:
        return Thresholds(theta_warn=theta_warn, theta_critical=theta_critical, alpha_warn=None, alpha_critical=None)
    alpha_warn = float(anomaly_series.quantile(alpha_warn_q))
    alpha_critical = float(anomaly_series.quantile(alpha_critical_q))
    return Thresholds(
        theta_warn=theta_warn,
        theta_critical=theta_critical,
        alpha_warn=alpha_warn,
        alpha_critical=alpha_critical,
    )


def _smooth_by_engine(df: pd.DataFrame, col: str, window: int) -> pd.Series:
    if window <= 1:
        return df[col]
    return (
        df.sort_values(["engine_id", "cycle"])
        .groupby("engine_id")[col]
        .transform(lambda s: s.rolling(window=window, min_periods=1).mean())
    )


def _clamp(x: float, lo: float, hi: float) -> float:
    return float(min(max(x, lo), hi))


def _threshold_from_target_fpr(values: pd.Series, target_fpr: float) -> float:
    target_fpr = float(target_fpr)
    if not (0.0 < target_fpr < 1.0):
        raise ValueError(f"target_fpr must be in (0,1), got {target_fpr}")
    # P(value >= threshold) ~= target_fpr  => threshold = quantile(1 - target_fpr)
    return float(values.quantile(1.0 - target_fpr))


def _target_fpr_from_arl(target_arl: float) -> float:
    target_arl = float(target_arl)
    if target_arl <= 1.0:
        raise ValueError(f"target_arl must be > 1, got {target_arl}")
    # Geometric approximation: ARL ≈ 1 / FPR
    return float(1.0 / target_arl)


def _risk_score(
    rul: float,
    anomaly: Optional[float],
    th: Thresholds,
) -> Tuple[int, str]:
    # Higher score => higher risk. Driver indicates which component dominates.
    # If anomaly is missing, risk is based on RUL only.
    eps = 1e-9

    rul_den = max(th.theta_warn - th.theta_critical, eps)
    rul_risk = _clamp((th.theta_warn - rul) / rul_den, 0.0, 1.0)

    if anomaly is None or th.alpha_warn is None or th.alpha_critical is None:
        score = int(round(100.0 * rul_risk))
        return score, "RUL"

    anom_den = max(th.alpha_critical - th.alpha_warn, eps)
    anom_risk = _clamp((anomaly - th.alpha_warn) / anom_den, 0.0, 1.0)

    if abs(anom_risk - rul_risk) < 1e-6:
        driver = "TIE"
    else:
        driver = "ANOMALY" if anom_risk > rul_risk else "RUL"
    score = int(round(100.0 * max(rul_risk, anom_risk)))
    return score, driver


@dataclass
class DebounceState:
    warn_active: bool = False
    critical_active: bool = False
    up_warn: int = 0
    up_critical: int = 0
    down_warn: int = 0
    down_critical: int = 0


def _update_debounce(
    st: DebounceState,
    anomaly: float,
    th: Thresholds,
    debounce_warn_up: int,
    debounce_critical_up: int,
    debounce_down: int,
    hysteresis_delta: float,
) -> DebounceState:
    # Update upward counters
    if anomaly >= float(th.alpha_critical):
        st.up_critical += 1
    else:
        st.up_critical = 0

    if anomaly >= float(th.alpha_warn):
        st.up_warn += 1
    else:
        st.up_warn = 0

    # Latch on if sustained
    if st.up_critical >= debounce_critical_up:
        st.critical_active = True
    if st.up_warn >= debounce_warn_up:
        st.warn_active = True

    # Downward (hysteresis) counters
    crit_down_thr = float(th.alpha_critical) - float(hysteresis_delta)
    warn_down_thr = float(th.alpha_warn) - float(hysteresis_delta)

    if st.critical_active:
        if anomaly <= crit_down_thr:
            st.down_critical += 1
        else:
            st.down_critical = 0
        if st.down_critical >= debounce_down:
            st.critical_active = False
            st.down_critical = 0

    if st.warn_active:
        if anomaly <= warn_down_thr:
            st.down_warn += 1
        else:
            st.down_warn = 0
        if st.down_warn >= debounce_down:
            st.warn_active = False
            st.down_warn = 0

    # Critical dominates warn
    if st.critical_active:
        st.warn_active = True

    return st


def _decision_for_row(
    rul: float,
    anomaly: Optional[float],
    th: Thresholds,
    allow_missing_anomaly: bool,
    debounce_state: Optional[DebounceState],
    debounce_warn_up: int,
    debounce_critical_up: int,
    debounce_down: int,
    hysteresis_delta: float,
) -> Tuple[str, str, str, List[str], Optional[DebounceState]]:
    signals: List[str] = []

    rul_below_warn = bool(rul <= th.theta_warn)
    rul_below_critical = bool(rul <= th.theta_critical)
    if rul_below_warn:
        signals.append("RUL_BELOW_THETA_WARN")
    else:
        signals.append("RUL_ABOVE_THETA_WARN")
    if rul_below_critical:
        signals.append("RUL_BELOW_THETA_CRITICAL")

    # Missing anomaly path
    if anomaly is None or th.alpha_warn is None or th.alpha_critical is None:
        signals.append("ANOMALY_MISSING")
        if not allow_missing_anomaly:
            return (
                "degrading",
                "Schedule Inspection",
                "Insufficient anomaly data; defaulting to a conservative inspection recommendation.",
                signals,
                debounce_state,
            )

        if rul_below_critical:
            return (
                "critical",
                "Immediate Maintenance",
                "Predicted remaining life is critically low; urgent action recommended.",
                signals,
                debounce_state,
            )
        if rul_below_warn:
            return (
                "degraded",
                "Planned Maintenance",
                "RUL is below θ_warn; plan maintenance/inspection soon.",
                signals,
                debounce_state,
            )
        return (
            "healthy",
            "Monitor",
            "Plenty of remaining life; continue routine monitoring.",
            signals,
            debounce_state,
        )

    # Anomaly present
    if debounce_state is None:
        debounce_state = DebounceState()
    raw_warn = bool(anomaly >= th.alpha_warn)
    raw_critical = bool(anomaly >= th.alpha_critical)
    if raw_critical:
        signals.append("ANOMALY_ABOVE_ALPHA_CRITICAL_RAW")
        signals.append("ANOMALY_ABOVE_ALPHA_WARN_RAW")
    elif raw_warn:
        signals.append("ANOMALY_ABOVE_ALPHA_WARN_RAW")
    else:
        signals.append("ANOMALY_BELOW_ALPHA_WARN")

    debounce_state = _update_debounce(
        debounce_state,
        anomaly=float(anomaly),
        th=th,
        debounce_warn_up=debounce_warn_up,
        debounce_critical_up=debounce_critical_up,
        debounce_down=debounce_down,
        hysteresis_delta=hysteresis_delta,
    )

    if raw_warn and not debounce_state.warn_active and not debounce_state.critical_active:
        signals.append("ANOMALY_SPIKE_BELOW_DEBOUNCE")
    if debounce_state.warn_active and not debounce_state.critical_active:
        signals.append("ANOMALY_ABOVE_ALPHA_WARN")
    if debounce_state.critical_active:
        signals.append("ANOMALY_ABOVE_ALPHA_CRITICAL")

    # V2 state machine (4 states): healthy / watch / degraded / critical
    if rul_below_critical or debounce_state.critical_active:
        return (
            "critical",
            "Immediate Maintenance",
            "RUL and/or anomaly evidence indicates high urgency; immediate action recommended.",
            signals,
            debounce_state,
        )
    if rul_below_warn:
        return (
            "degraded",
            "Planned Maintenance",
            "RUL is below θ_warn; plan maintenance/inspection soon.",
            signals,
            debounce_state,
        )

    if debounce_state.warn_active or "ANOMALY_SPIKE_BELOW_DEBOUNCE" in signals:
        return (
            "watch",
            "Enhanced Monitoring",
            "Anomaly evidence is elevated while RUL is still high; increase monitoring and run diagnostics.",
            signals,
            debounce_state,
        )

    return ("healthy", "Monitor", "No threshold breach detected; continue routine monitoring.", signals, debounce_state)


def _v1_label_and_reason(
    rul_used: float,
    anomaly_used: Optional[float],
    theta_rul_used: float,
    alpha_anomaly_used: Optional[float],
) -> Tuple[str, str, str]:
    rul_low = bool(rul_used <= theta_rul_used)
    if anomaly_used is None or alpha_anomaly_used is None:
        anom_high = False
        codes = "RUL_LOW" if rul_low else "RUL_HIGH"
    else:
        anom_high = bool(anomaly_used >= float(alpha_anomaly_used))
        codes = "|".join(
            [
                "RUL_LOW" if rul_low else "RUL_HIGH",
                "ANOM_HIGH" if anom_high else "ANOM_LOW",
            ]
        )

    if (not rul_low) and (not anom_high):
        return (
            "Normal Operation",
            codes,
            "RUL is above θ_RUL and anomaly is below α_anomaly; continue normal operation.",
        )
    if (not rul_low) and anom_high:
        return (
            "Enhanced Monitoring",
            codes,
            "RUL is above θ_RUL but anomaly is above α_anomaly; increase monitoring and run diagnostics.",
        )
    if rul_low and (not anom_high):
        return (
            "Planned Maintenance",
            codes,
            "RUL is below θ_RUL while anomaly is not high; plan maintenance/inspection soon.",
        )
    return (
        "Immediate Maintenance",
        codes,
        "RUL is below θ_RUL and anomaly is above α_anomaly; immediate maintenance is recommended.",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Decision support (α–θ) runner for FD001/FD002 outputs.")
    ap.add_argument("--pred", required=True, help="Predictions CSV with (engine_id, cycle, RUL_pred column).")
    ap.add_argument("--out", required=True, help="Output decision-support CSV.")
    ap.add_argument("--config", default=None, help="Optional JSON config for thresholds/policy (single source of truth).")
    ap.add_argument(
        "--emit-v1",
        default=None,
        help=(
            "Optional path to also write the MVP-minimal (v1) contract CSV: "
            "engine_id,cycle,rul_pred,anomaly_score,decision_label,reason_codes,reason_text,theta_rul_used,alpha_anomaly_used."
        ),
    )
    ap.add_argument("--rul-col", default=None, help="Name of the RUL prediction column (auto if omitted).")
    ap.add_argument("--anomaly", default=None, help="Optional anomaly CSV with (engine_id, cycle, anomaly_score).")
    ap.add_argument("--anomaly-col", default="anomaly_score", help="Anomaly score column name.")
    ap.add_argument("--smooth-window", type=int, default=1, help="Rolling mean window per engine (>=1).")
    ap.add_argument("--cap", type=float, default=125.0, help="RUL cap used upstream; used only for clipping.")
    ap.add_argument(
        "--theta-rul",
        type=float,
        default=None,
        help="V1 policy single θ_RUL threshold (used only for --emit-v1). Defaults to θ_warn.",
    )
    ap.add_argument(
        "--alpha-anomaly",
        type=float,
        default=None,
        help="V1 policy single α_anomaly threshold (used only for --emit-v1). Defaults to α_warn.",
    )
    ap.add_argument("--theta-warn", type=float, default=None, help="Fixed θ_warn. If omitted, uses quantiles.")
    ap.add_argument("--theta-critical", type=float, default=None, help="Fixed θ_critical. If omitted, uses quantiles.")
    ap.add_argument("--alpha-warn", type=float, default=None, help="Fixed α_warn (requires anomaly).")
    ap.add_argument("--alpha-critical", type=float, default=None, help="Fixed α_critical (requires anomaly).")
    ap.add_argument("--alpha-hysteresis-delta", type=float, default=0.0, help="Hysteresis delta for anomaly de-escalation.")
    ap.add_argument("--anom-debounce-warn-up", type=int, default=3, help="Consecutive cycles needed to latch WARN (anomaly).")
    ap.add_argument("--anom-debounce-critical-up", type=int, default=2, help="Consecutive cycles needed to latch CRITICAL (anomaly).")
    ap.add_argument("--anom-debounce-down", type=int, default=3, help="Consecutive cycles needed to de-latch (anomaly).")
    ap.add_argument("--theta-warn-q", type=float, default=0.30, help="Quantile for θ_warn (default 0.30).")
    ap.add_argument("--theta-critical-q", type=float, default=0.10, help="Quantile for θ_critical (default 0.10).")
    ap.add_argument("--alpha-warn-q", type=float, default=0.90, help="Quantile for α_warn (default 0.90).")
    ap.add_argument("--alpha-critical-q", type=float, default=0.97, help="Quantile for α_critical (default 0.97).")
    ap.add_argument("--alpha-target-fpr-warn", type=float, default=None, help="Calibrate α_warn to target per-cycle FPR.")
    ap.add_argument("--alpha-target-fpr-critical", type=float, default=None, help="Calibrate α_critical to target per-cycle FPR.")
    ap.add_argument("--alpha-target-arl-warn", type=float, default=None, help="Alternative to FPR: target ARL (cycles) for α_warn.")
    ap.add_argument("--alpha-target-arl-critical", type=float, default=None, help="Alternative to FPR: target ARL (cycles) for α_critical.")
    ap.add_argument(
        "--calib-healthy-first-n",
        type=int,
        default=30,
        help="Proxy 'healthy' region for calibrating α: first N cycles per engine.",
    )
    ap.add_argument(
        "--calibration-scope",
        choices=["all_rows", "last_cycle_per_engine"],
        default="last_cycle_per_engine",
        help="Which rows to use when computing quantile thresholds.",
    )
    ap.add_argument(
        "--allow-missing-anomaly",
        action="store_true",
        help="If anomaly is missing, apply RUL-only logic instead of defaulting to degrading.",
    )
    ap.add_argument("--report-json", default=None, help="Optional JSON report output path.")
    args = ap.parse_args()

    cfg: Dict[str, Any] = {}
    config_sha256: Optional[str] = None
    if args.config:
        cfg = _read_json(args.config)
        config_sha256 = _sha256_file(args.config)

        def _maybe_override(key: str, flag: str, cast_fn, attr: str) -> None:
            if _cli_has(flag):
                return
            if key not in cfg:
                return
            setattr(args, attr, cast_fn(cfg[key]))

        _maybe_override("cap", "--cap", float, "cap")
        _maybe_override("smooth_window", "--smooth-window", int, "smooth_window")

        _maybe_override("theta_warn", "--theta-warn", float, "theta_warn")
        _maybe_override("theta_critical", "--theta-critical", float, "theta_critical")
        _maybe_override("theta_rul", "--theta-rul", float, "theta_rul")

        _maybe_override("alpha_warn", "--alpha-warn", float, "alpha_warn")
        _maybe_override("alpha_critical", "--alpha-critical", float, "alpha_critical")
        _maybe_override("alpha_anomaly", "--alpha-anomaly", float, "alpha_anomaly")
        _maybe_override("alpha_hysteresis_delta", "--alpha-hysteresis-delta", float, "alpha_hysteresis_delta")

        _maybe_override("anom_debounce_warn_up", "--anom-debounce-warn-up", int, "anom_debounce_warn_up")
        _maybe_override("anom_debounce_critical_up", "--anom-debounce-critical-up", int, "anom_debounce_critical_up")
        _maybe_override("anom_debounce_down", "--anom-debounce-down", int, "anom_debounce_down")

        _maybe_override("alpha_target_fpr_warn", "--alpha-target-fpr-warn", float, "alpha_target_fpr_warn")
        _maybe_override("alpha_target_fpr_critical", "--alpha-target-fpr-critical", float, "alpha_target_fpr_critical")
        _maybe_override("alpha_target_arl_warn", "--alpha-target-arl-warn", float, "alpha_target_arl_warn")
        _maybe_override("alpha_target_arl_critical", "--alpha-target-arl-critical", float, "alpha_target_arl_critical")

        _maybe_override("calib_healthy_first_n", "--calib-healthy-first-n", int, "calib_healthy_first_n")
        if not _cli_has("--calibration-scope") and "calibration_scope" in cfg:
            args.calibration_scope = str(cfg["calibration_scope"])

        if not _cli_has("--allow-missing-anomaly") and bool(cfg.get("allow_missing_anomaly", False)):
            args.allow_missing_anomaly = True

    pred_df = _read_csv(args.pred)
    pred_input_rows = int(len(pred_df))
    _require_cols(pred_df, ["engine_id", "cycle"], "predictions")
    rul_col = _infer_rul_col(pred_df, args.rul_col)
    pred_duplicate_keys = int(pred_df.duplicated(subset=["engine_id", "cycle"]).sum())
    if pred_duplicate_keys:
        raise ValueError(f"predictions has duplicate (engine_id,cycle) keys: {pred_duplicate_keys}")

    df = pred_df[["engine_id", "cycle", rul_col]].rename(columns={rul_col: "RUL_pred"}).copy()
    df["RUL_pred"] = pd.to_numeric(df["RUL_pred"], errors="coerce").astype(float)
    df["RUL_pred"] = df["RUL_pred"].clip(lower=0.0, upper=float(args.cap))
    df["engine_id"] = pd.to_numeric(df["engine_id"], errors="raise").astype(int)
    df["cycle"] = pd.to_numeric(df["cycle"], errors="raise").astype(int)

    anomaly_series: Optional[pd.Series] = None
    anomaly_input_rows: Optional[int] = None
    anomaly_duplicate_keys: Optional[int] = None
    if args.anomaly:
        an_df = _read_csv(args.anomaly)
        anomaly_input_rows = int(len(an_df))
        _require_cols(an_df, ["engine_id", "cycle", args.anomaly_col], "anomaly")
        anomaly_duplicate_keys = int(an_df.duplicated(subset=["engine_id", "cycle"]).sum())
        if anomaly_duplicate_keys:
            raise ValueError(f"anomaly has duplicate (engine_id,cycle) keys: {anomaly_duplicate_keys}")
        an_df = an_df[["engine_id", "cycle", args.anomaly_col]].rename(columns={args.anomaly_col: "anomaly_score"})
        an_df["engine_id"] = pd.to_numeric(an_df["engine_id"], errors="raise").astype(int)
        an_df["cycle"] = pd.to_numeric(an_df["cycle"], errors="raise").astype(int)
        an_df["anomaly_score"] = pd.to_numeric(an_df["anomaly_score"], errors="coerce").astype(float)
        df = df.merge(an_df, on=["engine_id", "cycle"], how="left", validate="one_to_one")
        anomaly_series = df["anomaly_score"].dropna()
    else:
        df["anomaly_score"] = np.nan

    df["RUL_used"] = _smooth_by_engine(df, "RUL_pred", args.smooth_window)
    df["ANOM_used"] = _smooth_by_engine(df, "anomaly_score", args.smooth_window) if args.anomaly else np.nan

    merged_rows = int(len(df))
    merged_missing_anomaly = int(df["anomaly_score"].isna().sum()) if args.anomaly else merged_rows

    # Choose calibration series
    if args.calibration_scope == "last_cycle_per_engine":
        base = df.sort_values(["engine_id", "cycle"]).groupby("engine_id").tail(1)
    else:
        base = df

    if args.theta_warn is not None and args.theta_critical is not None:
        th = Thresholds(
            theta_warn=float(args.theta_warn),
            theta_critical=float(args.theta_critical),
            alpha_warn=float(args.alpha_warn) if args.alpha_warn is not None else None,
            alpha_critical=float(args.alpha_critical) if args.alpha_critical is not None else None,
        )
    else:
        th = _quantile_thresholds(
            rul_series=base["RUL_used"],
            anomaly_series=base["ANOM_used"].dropna() if args.anomaly else None,
            theta_warn_q=float(args.theta_warn_q),
            theta_critical_q=float(args.theta_critical_q),
            alpha_warn_q=float(args.alpha_warn_q),
            alpha_critical_q=float(args.alpha_critical_q),
        )

    # Optional α calibration by target FPR/ARL (proxy healthy region)
    calib_stats: Dict[str, Any] = {}
    if args.anomaly:
        alpha_warn = th.alpha_warn
        alpha_critical = th.alpha_critical

        if args.alpha_warn is not None:
            alpha_warn = float(args.alpha_warn)
        if args.alpha_critical is not None:
            alpha_critical = float(args.alpha_critical)

        # If targets are provided, calibrate on first N cycles per engine (proxy healthy window).
        # This is MVP-safe when no ground-truth maintenance events exist.
        target_warn_fpr = args.alpha_target_fpr_warn
        if target_warn_fpr is None and args.alpha_target_arl_warn is not None:
            target_warn_fpr = _target_fpr_from_arl(args.alpha_target_arl_warn)

        target_crit_fpr = args.alpha_target_fpr_critical
        if target_crit_fpr is None and args.alpha_target_arl_critical is not None:
            target_crit_fpr = _target_fpr_from_arl(args.alpha_target_arl_critical)

        if target_warn_fpr is not None or target_crit_fpr is not None:
            healthy = (
                df.sort_values(["engine_id", "cycle"])
                .groupby("engine_id")
                .head(int(args.calib_healthy_first_n))
            )
            values = healthy["ANOM_used"].dropna()
            if values.empty:
                raise ValueError("No anomaly values available for α calibration.")

            if target_warn_fpr is not None:
                alpha_warn = _threshold_from_target_fpr(values, float(target_warn_fpr))
            if target_crit_fpr is not None:
                alpha_critical = _threshold_from_target_fpr(values, float(target_crit_fpr))

            if alpha_warn is not None and alpha_critical is not None and alpha_critical < alpha_warn:
                # Enforce ordering
                alpha_critical = alpha_warn

            calib_stats = {
                "alpha_mode": str(cfg.get("alpha_mode", "target_fpr_or_arl_on_healthy_first_n")) if cfg else "target_fpr_or_arl_on_healthy_first_n",
                "alpha_fit_on": str(cfg.get("alpha_fit_on", "healthy_first_n_cycles_per_engine")) if cfg else "healthy_first_n_cycles_per_engine",
                "calib_healthy_first_n": int(args.calib_healthy_first_n),
                "target_fpr_warn": float(target_warn_fpr) if target_warn_fpr is not None else None,
                "target_fpr_critical": float(target_crit_fpr) if target_crit_fpr is not None else None,
            }
            # Empirical achieved rates on calibration window (per-cycle)
            calib_stats["achieved_fpr_warn"] = float((values >= float(alpha_warn)).mean()) if alpha_warn is not None else None
            calib_stats["achieved_fpr_critical"] = float((values >= float(alpha_critical)).mean()) if alpha_critical is not None else None

        th = Thresholds(
            theta_warn=float(th.theta_warn),
            theta_critical=float(th.theta_critical),
            alpha_warn=float(alpha_warn) if alpha_warn is not None else None,
            alpha_critical=float(alpha_critical) if alpha_critical is not None else None,
        )

    out_rows: List[Dict[str, Any]] = []
    df_sorted = df.sort_values(["engine_id", "cycle"]).reset_index(drop=True)
    engine_states: Dict[int, DebounceState] = {}

    theta_rul_used = float(args.theta_rul) if args.theta_rul is not None else float(th.theta_warn)
    alpha_anomaly_used: Optional[float] = None
    if args.anomaly:
        alpha_anomaly_used = float(args.alpha_anomaly) if args.alpha_anomaly is not None else float(th.alpha_warn)

    policy_version = str(cfg.get("policy_version", "v2")) if cfg else "v2"

    for r in df_sorted.itertuples(index=False):
        anomaly_val = None if (math.isnan(r.ANOM_used) or not args.anomaly) else float(r.ANOM_used)
        st = engine_states.get(int(r.engine_id)) if args.anomaly else None
        state, action, rationale, signals, st2 = _decision_for_row(
            rul=float(r.RUL_used),
            anomaly=anomaly_val,
            th=th,
            allow_missing_anomaly=bool(args.allow_missing_anomaly),
            debounce_state=st,
            debounce_warn_up=int(args.anom_debounce_warn_up),
            debounce_critical_up=int(args.anom_debounce_critical_up),
            debounce_down=int(args.anom_debounce_down),
            hysteresis_delta=float(args.alpha_hysteresis_delta),
        )
        if args.anomaly and st2 is not None:
            engine_states[int(r.engine_id)] = st2

        risk, driver = _risk_score(float(r.RUL_used), anomaly_val, th)
        decision_label, v1_reason_codes, v1_reason_text = _v1_label_and_reason(
            rul_used=float(r.RUL_used),
            anomaly_used=anomaly_val if args.anomaly else None,
            theta_rul_used=float(theta_rul_used),
            alpha_anomaly_used=alpha_anomaly_used,
        )
        out_rows.append(
            {
                "engine_id": int(r.engine_id),
                "cycle": int(r.cycle),
                # Canonicalized inputs (for auditability + dashboard joins)
                "rul_pred": float(r.RUL_pred),
                "rul_pred_used": float(r.RUL_used),
                "anomaly_score": ("" if math.isnan(r.anomaly_score) else float(r.anomaly_score)),
                "anomaly_score_used": ("" if math.isnan(r.ANOM_used) else float(r.ANOM_used)),
                # V1 (minimal contract) fields
                "decision_label": decision_label,
                "reason_codes": v1_reason_codes,
                "reason_text": v1_reason_text,
                "theta_rul_used": float(theta_rul_used),
                "alpha_anomaly_used": ("" if alpha_anomaly_used is None else float(alpha_anomaly_used)),
                # V2 extensions
                "policy_version": policy_version,
                "state": state,
                "recommended_action": action,
                "rationale": rationale,
                "contributing_signals": json.dumps(signals, ensure_ascii=False),
                "risk_score": int(risk),
                "risk_driver": driver,
                "theta_warn_used": float(th.theta_warn),
                "theta_critical_used": float(th.theta_critical),
                "alpha_warn_used": float(th.alpha_warn) if th.alpha_warn is not None else "",
                "alpha_critical_used": float(th.alpha_critical) if th.alpha_critical is not None else "",
                "smooth_window_used": int(args.smooth_window),
                "anom_debounce_warn_up_used": int(args.anom_debounce_warn_up),
                "anom_debounce_critical_up_used": int(args.anom_debounce_critical_up),
                "anom_debounce_down_used": int(args.anom_debounce_down),
                "alpha_hysteresis_delta_used": float(args.alpha_hysteresis_delta),
            }
        )

    out_df = pd.DataFrame(out_rows).sort_values(["engine_id", "cycle"]).reset_index(drop=True)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)

    if args.emit_v1:
        v1 = out_df[["engine_id", "cycle", "rul_pred_used", "anomaly_score_used"]].rename(
            columns={"rul_pred_used": "rul_pred", "anomaly_score_used": "anomaly_score"}
        )
        v1["decision_label"] = out_df["decision_label"]
        v1["reason_codes"] = out_df["reason_codes"]
        v1["reason_text"] = out_df["reason_text"]
        v1["theta_rul_used"] = out_df["theta_rul_used"]
        v1["alpha_anomaly_used"] = out_df["alpha_anomaly_used"]
        v1 = v1[
            [
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
        ].sort_values(["engine_id", "cycle"])

        p = Path(args.emit_v1)
        p.parent.mkdir(parents=True, exist_ok=True)
        v1.to_csv(p, index=False)

    if args.report_json:
        created_at_utc = datetime.now(timezone.utc).isoformat()
        rep = {
            "config_path": args.config,
            "config_sha256": config_sha256,
            "config_policy_version": (str(cfg.get("policy_version")) if cfg and "policy_version" in cfg else None),
            "pred_path": args.pred,
            "anomaly_path": args.anomaly,
            "out_path": str(out_path),
            "created_at_utc": created_at_utc,
            "code_version": __VERSION__,
            "rows": int(len(out_df)),
            "unique_engines": int(out_df["engine_id"].nunique()),
            "states": out_df["state"].value_counts().to_dict(),
            "theta_warn_used": float(th.theta_warn),
            "theta_critical_used": float(th.theta_critical),
            "alpha_warn_used": th.alpha_warn,
            "alpha_critical_used": th.alpha_critical,
            "smooth_window_used": int(args.smooth_window),
            "anom_debounce_warn_up": int(args.anom_debounce_warn_up),
            "anom_debounce_critical_up": int(args.anom_debounce_critical_up),
            "anom_debounce_down": int(args.anom_debounce_down),
            "alpha_hysteresis_delta": float(args.alpha_hysteresis_delta),
            "calibration_scope": args.calibration_scope,
            "alpha_calibration": calib_stats,
            "data_summary": {
                "pred_input_rows": pred_input_rows,
                "pred_duplicate_keys": pred_duplicate_keys,
                "anomaly_input_rows": anomaly_input_rows,
                "anomaly_duplicate_keys": anomaly_duplicate_keys,
                "merged_rows": merged_rows,
                "merged_missing_anomaly_rows": merged_missing_anomaly,
                "output_rows": int(len(out_df)),
                "output_duplicate_keys": int(out_df.duplicated(subset=["engine_id", "cycle"]).sum()),
            },
            "anomaly_summary": {
                "anomaly_score_min": (None if anomaly_series is None or anomaly_series.empty else float(anomaly_series.min())),
                "anomaly_score_max": (None if anomaly_series is None or anomaly_series.empty else float(anomaly_series.max())),
                "anomaly_used_min": (None if not args.anomaly else float(df["ANOM_used"].dropna().min())),
                "anomaly_used_max": (None if not args.anomaly else float(df["ANOM_used"].dropna().max())),
            },
            "quantiles": {
                "theta_warn_q": float(args.theta_warn_q),
                "theta_critical_q": float(args.theta_critical_q),
                "alpha_warn_q": float(args.alpha_warn_q),
                "alpha_critical_q": float(args.alpha_critical_q),
            },
            "v1_thresholds": {
                "theta_rul_used": float(theta_rul_used),
                "alpha_anomaly_used": alpha_anomaly_used,
            },
            "policy_version": str(cfg.get("policy_version")) if cfg and "policy_version" in cfg else "v2",
        }
        rp = Path(args.report_json)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
