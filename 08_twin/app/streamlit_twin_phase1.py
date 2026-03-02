
#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score

try:
    import shap

    SHAP_AVAILABLE = True
    SHAP_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover
    SHAP_AVAILABLE = False
    SHAP_IMPORT_ERROR = str(exc)


POLICY_DEFAULT_ROOT = Path("08_twin/data/decision_support_v2_outputs")
RUL_ROOT = Path("02_notebooks_exports/RUL/N-CMAPSS")
RUL_DS0104_ROOT = RUL_ROOT / "DS01-DS04"
DECISION_LABELS_ALARM = {"Enhanced Monitoring", "Immediate Maintenance"}
RE_V2_NCMAPSS = re.compile(r"^ncmapss_(DS\d{2})_decision_support_v2\.csv$", re.IGNORECASE)


@st.cache_data(show_spinner=False)
def read_csv_cached(path_str: str) -> pd.DataFrame:
    return pd.read_csv(path_str)


def parse_reason_codes(value: object) -> List[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    text = str(value).strip()
    if not text:
        return []
    return [token.strip() for token in text.split("|") if token.strip()]


@st.cache_data(show_spinner=False)
def discover_policy_outputs(root_str: str) -> Dict[str, str]:
    root = Path(root_str)
    found: Dict[str, str] = {}
    if not root.exists():
        return found

    for item in root.iterdir():
        if not item.is_file():
            continue
        m = RE_V2_NCMAPSS.match(item.name)
        if not m:
            continue
        dataset = m.group(1).upper()
        found[dataset] = str(item)

    return dict(sorted(found.items()))


@st.cache_data(show_spinner=False)
def load_policy_dataset(path_str: str) -> pd.DataFrame:
    df = pd.read_csv(path_str)
    required = {
        "dataset_id",
        "split",
        "asset_id",
        "t",
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
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required policy columns: {missing}")

    out = df.rename(columns={"asset_id": "engine_id", "t": "cycle"}).copy()
    out["dataset_id"] = out["dataset_id"].astype(str).str.upper().str.strip()
    out["split"] = out["split"].astype(str).str.lower().str.strip()
    out["engine_id"] = pd.to_numeric(out["engine_id"], errors="raise").astype(int)
    out["cycle"] = pd.to_numeric(out["cycle"], errors="raise").astype(int)
    out["rul_pred"] = pd.to_numeric(out["rul_pred"], errors="coerce").astype(float)
    out["anomaly_score_raw"] = pd.to_numeric(out["anomaly_score_raw"], errors="coerce").astype(float)
    out["anomaly_score_smoothed"] = pd.to_numeric(out["anomaly_score_smoothed"], errors="coerce").astype(float)
    out["theta_rul_used"] = pd.to_numeric(out["theta_rul_used"], errors="coerce").astype(float)
    out["alpha_high_used"] = pd.to_numeric(out["alpha_high_used"], errors="coerce").astype(float)
    out["alpha_low_used"] = pd.to_numeric(out["alpha_low_used"], errors="coerce").astype(float)
    out["persistence_counter"] = pd.to_numeric(out["persistence_counter"], errors="coerce").fillna(0).astype(int)

    key_cols = ["dataset_id", "split", "engine_id", "cycle"]
    dup_count = int(out.duplicated(key_cols).sum())
    if dup_count:
        raise ValueError(f"Duplicate rows found for canonical key {key_cols}: {dup_count}")

    return out


def decision_segments(engine_df: pd.DataFrame) -> List[Tuple[int, int, str]]:
    if engine_df.empty:
        return []

    g = engine_df.sort_values("cycle").copy()
    labels = g["decision_label"].astype(str).tolist()
    cycles = g["cycle"].astype(int).tolist()

    segments: List[Tuple[int, int, str]] = []
    start_cycle = cycles[0]
    current_label = labels[0]
    for idx in range(1, len(cycles)):
        if labels[idx] != current_label:
            segments.append((start_cycle, cycles[idx - 1], current_label))
            start_cycle = cycles[idx]
            current_label = labels[idx]
    segments.append((start_cycle, cycles[-1], current_label))
    return segments


def compute_alarm_kpis(df_scope: pd.DataFrame, window_n: int, end_cycle: Optional[int]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    if df_scope.empty:
        return None, None, "MISSING: empty input"
    if "decision_label" not in df_scope.columns:
        return None, None, "MISSING: decision_label not found"

    dfp = df_scope.copy()
    if end_cycle is not None and "cycle" in dfp.columns:
        dfp = dfp[pd.to_numeric(dfp["cycle"], errors="coerce") <= int(end_cycle)]
        dfp = dfp.sort_values("cycle")

    if window_n and window_n > 0 and len(dfp) > window_n:
        dfp = dfp.tail(int(window_n))

    total = int(len(dfp))
    if total == 0:
        return np.nan, np.nan, "MISSING: no rows in scope"

    labels = dfp["decision_label"].astype(str)
    enhanced = int((labels == "Enhanced Monitoring").sum())
    immediate = int((labels == "Immediate Maintenance").sum())
    return float((enhanced + immediate) / total), float(immediate / total), None


def compute_transitions(df_engine: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[str]]:
    if df_engine.empty:
        return pd.DataFrame(), "MISSING: empty engine data"

    g = df_engine.sort_values("cycle").copy()
    g["decision_label"] = g["decision_label"].astype(str)
    prev = g["decision_label"].shift(1)
    changed = g[prev.notna() & (g["decision_label"] != prev)].copy()

    if changed.empty:
        return pd.DataFrame(columns=["cycle", "from_label", "to_label"]), None

    out = pd.DataFrame(
        {
            "cycle": changed["cycle"].astype(int).to_list(),
            "from_label": prev.loc[changed.index].astype(str).to_list(),
            "to_label": changed["decision_label"].astype(str).to_list(),
        }
    )
    return out, None


def compute_trend(df_engine: pd.DataFrame, window_n: int, end_cycle: Optional[int]) -> Tuple[Optional[Dict[str, float]], Optional[str]]:
    if df_engine.empty:
        return None, "MISSING: empty engine data"

    g = df_engine.copy()
    g["cycle"] = pd.to_numeric(g["cycle"], errors="coerce")
    g["rul_pred"] = pd.to_numeric(g["rul_pred"], errors="coerce")
    g["anomaly_score_smoothed"] = pd.to_numeric(g["anomaly_score_smoothed"], errors="coerce")
    g = g.dropna(subset=["cycle", "rul_pred", "anomaly_score_smoothed"]).sort_values("cycle")

    if end_cycle is not None:
        g = g[g["cycle"] <= int(end_cycle)]
    if window_n > 0 and len(g) > window_n:
        g = g.tail(int(window_n))
    if len(g) < 2:
        return None, "MISSING: need >=2 points"

    x = g["cycle"].to_numpy(dtype=float)
    rul = g["rul_pred"].to_numpy(dtype=float)
    anom = g["anomaly_score_smoothed"].to_numpy(dtype=float)

    return {
        "rul_slope": float(np.polyfit(x, rul, 1)[0]),
        "anom_slope": float(np.polyfit(x, anom, 1)[0]),
    }, None


def derive_policy_snapshot(row: pd.Series) -> Dict[str, object]:
    decision_label = str(row.get("decision_label", "UNKNOWN"))
    reason_codes = parse_reason_codes(row.get("reason_codes", ""))
    reason_set = set(reason_codes)

    rul_low = "RUL_LOW" in reason_set
    anom_on = "ANOM_ON" in reason_set

    if rul_low and anom_on:
        primary_driver = "BOTH"
    elif rul_low:
        primary_driver = "RUL"
    elif anom_on:
        primary_driver = "ANOMALY"
    else:
        primary_driver = "NONE"

    if primary_driver == "BOTH":
        confidence = "High"
    elif primary_driver in {"RUL", "ANOMALY"}:
        confidence = "Medium"
    else:
        confidence = "Low"

    theta = float(row.get("theta_rul_used", np.nan))
    alpha_high = float(row.get("alpha_high_used", np.nan))
    alpha_low = float(row.get("alpha_low_used", np.nan))
    rul = float(row.get("rul_pred", np.nan))
    anom = float(row.get("anomaly_score_smoothed", np.nan))

    rul_risk = float(np.clip((theta - rul) / max(theta, 1e-9), 0.0, 1.0)) if np.isfinite(theta) and np.isfinite(rul) else 0.0
    anom_risk = float(np.clip((anom - alpha_low) / max(alpha_high - alpha_low, 1e-9), 0.0, 1.0)) if np.isfinite(alpha_high) and np.isfinite(alpha_low) and np.isfinite(anom) else 0.0
    risk_score = int(round(100.0 * max(rul_risk, anom_risk)))

    short_why = (
        f"RUL={rul:.2f}, theta={theta:.2f}, anomaly_smoothed={anom:.4f}, "
        f"alpha_low/high={alpha_low:.4f}/{alpha_high:.4f} -> {decision_label}"
    )

    action = str(row.get("recommended_action_text", "")).strip()
    if not action:
        action = {
            "Normal Operation": "Routine monitoring",
            "Enhanced Monitoring": "Increase monitoring and diagnostics",
            "Planned Maintenance": "Schedule maintenance",
            "Immediate Maintenance": "Escalate immediate maintenance",
        }.get(decision_label, "Review")

    return {
        "decision_label": decision_label,
        "recommended_action": action,
        "primary_driver": primary_driver,
        "risk_score": risk_score,
        "confidence": confidence,
        "short_why": short_why,
        "reason_codes": reason_codes,
        "reason_text": str(row.get("reason_text", "")),
    }


def infer_failure_expectation(engine_df: pd.DataFrame, row: pd.Series, selected_cycle: int) -> Dict[str, object]:
    required_cols = ["rul_pred", "anomaly_score_smoothed", "theta_rul_used", "alpha_high_used", "alpha_low_used"]
    if any(c not in engine_df.columns for c in required_cols):
        return {
            "stage": "Data Contract / Mapping",
            "expected_issue": "Column mismatch or incomplete mapping",
            "why": "Required policy columns are missing.",
            "severity": "High",
            "evidence": {"missing_cols": [c for c in required_cols if c not in engine_df.columns]},
        }

    if engine_df[required_cols].isna().any(axis=1).any():
        return {
            "stage": "Ingest / Data Quality",
            "expected_issue": "NaN values may create unstable decisions",
            "why": "At least one required policy signal has NaN values.",
            "severity": "High",
            "evidence": {
                "nan_rows": int(engine_df[required_cols].isna().any(axis=1).sum()),
            },
        }

    rul = float(row["rul_pred"])
    theta = float(row["theta_rul_used"])
    anom = float(row["anomaly_score_smoothed"])
    alpha_h = float(row["alpha_high_used"])
    alpha_l = float(row["alpha_low_used"])
    decision = str(row.get("decision_label", ""))
    reasons = set(parse_reason_codes(row.get("reason_codes", "")))

    transitions, _ = compute_transitions(engine_df)
    recent_window = engine_df[(engine_df["cycle"] >= selected_cycle - 20) & (engine_df["cycle"] <= selected_cycle)]
    recent_trans, _ = compute_transitions(recent_window)

    rul_margin = rul - theta
    anom_margin_high = anom - alpha_h
    anom_margin_low = anom - alpha_l

    if "PERSISTENCE_PENDING" in reasons:
        return {
            "stage": "Anomaly Persistence Gate",
            "expected_issue": "Delayed alarm activation risk",
            "why": "Anomaly spike exists but persistence rule blocks ON state.",
            "severity": "Medium",
            "evidence": {
                "rul_margin": round(rul_margin, 3),
                "anom_margin_high": round(anom_margin_high, 5),
                "persistence_counter": int(row.get("persistence_counter", 0)),
            },
        }

    if decision == "Planned Maintenance" and str(row.get("anomaly_state", "OFF")) == "OFF":
        return {
            "stage": "RUL Degradation Path",
            "expected_issue": "Wear-out driven failure progression",
            "why": "RUL already below threshold while anomaly channel is OFF.",
            "severity": "High",
            "evidence": {
                "rul_margin": round(rul_margin, 3),
                "anom_margin_low": round(anom_margin_low, 5),
            },
        }

    if decision == "Immediate Maintenance":
        return {
            "stage": "Immediate Failure Risk",
            "expected_issue": "Near-term critical failure risk",
            "why": "Both low-RUL and anomaly-ON conditions are active.",
            "severity": "Critical",
            "evidence": {
                "rul_margin": round(rul_margin, 3),
                "anom_margin_high": round(anom_margin_high, 5),
            },
        }

    if len(recent_trans) >= 3:
        return {
            "stage": "Threshold Volatility",
            "expected_issue": "Flip-flop / unstable decision behavior",
            "why": "Too many decision transitions in the recent window.",
            "severity": "Medium",
            "evidence": {
                "recent_transition_count_20": int(len(recent_trans)),
                "total_transition_count": int(len(transitions)),
            },
        }

    return {
        "stage": "Stable Monitoring",
        "expected_issue": "No immediate policy-level failure signal",
        "why": "Current thresholds and state transitions look stable.",
        "severity": "Low",
        "evidence": {
            "rul_margin": round(rul_margin, 3),
            "anom_margin_high": round(anom_margin_high, 5),
            "anom_margin_low": round(anom_margin_low, 5),
        },
    }


def build_timeline_figure(engine_df: pd.DataFrame, selected_cycle: int, anomaly_col: str) -> go.Figure:
    label_colors = {
        "Normal Operation": "rgba(46, 204, 113, 0.10)",
        "Enhanced Monitoring": "rgba(241, 196, 15, 0.12)",
        "Planned Maintenance": "rgba(230, 126, 34, 0.12)",
        "Immediate Maintenance": "rgba(231, 76, 60, 0.12)",
    }

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=engine_df["cycle"],
            y=engine_df["rul_pred"],
            mode="lines",
            name="rul_pred",
            line=dict(width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=engine_df["cycle"],
            y=engine_df[anomaly_col],
            mode="lines",
            name=anomaly_col,
            yaxis="y2",
            line=dict(width=2),
        )
    )

    for start_cycle, end_cycle, label in decision_segments(engine_df):
        fig.add_vrect(
            x0=start_cycle - 0.5,
            x1=end_cycle + 0.5,
            fillcolor=label_colors.get(label, "rgba(149,165,166,0.10)"),
            opacity=1.0,
            layer="below",
            line_width=0,
        )

    theta = float(engine_df["theta_rul_used"].iloc[0])
    alpha_h = float(engine_df["alpha_high_used"].iloc[0])
    alpha_l = float(engine_df["alpha_low_used"].iloc[0])

    fig.add_hline(y=theta, line_dash="dash", line_color="orange")
    fig.add_hline(y=alpha_h, line_dash="dot", line_color="red", yref="y2")
    fig.add_hline(y=alpha_l, line_dash="dot", line_color="green", yref="y2")

    fig.add_vline(x=selected_cycle, line_dash="dot", line_color="black")

    fig.update_layout(
        height=520,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h"),
        xaxis=dict(title="cycle"),
        yaxis=dict(title="RUL"),
        yaxis2=dict(
            title=anomaly_col,
            overlaying="y",
            side="right",
            range=[0.0, 1.0],
        ),
    )
    return fig

def apply_light_fe(df: pd.DataFrame, base_cols: List[str], roll_w: int = 3, slope_w: int = 5) -> pd.DataFrame:
    out = df.sort_values(["engine_id", "cycle"]).copy()
    grouped = out.groupby("engine_id", sort=False)
    block: Dict[str, pd.Series] = {}
    for col in base_cols:
        series = grouped[col]
        block[f"{col}__delta1"] = series.diff().fillna(0.0)
        block[f"{col}__roll_mean{roll_w}"] = series.transform(lambda s: s.rolling(roll_w, min_periods=1).mean())
        block[f"{col}__roll_std{roll_w}"] = series.transform(lambda s: s.rolling(roll_w, min_periods=1).std().fillna(0.0))
        block[f"{col}__slope{slope_w}"] = series.transform(lambda s: s.diff().rolling(slope_w, min_periods=1).mean().fillna(0.0))
    return pd.concat([out, pd.DataFrame(block, index=out.index)], axis=1)


def first_existing(paths: List[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


def resolve_shap_paths(dataset: str) -> Optional[Dict[str, Path]]:
    ds = dataset.upper()

    feature_candidates = [
        RUL_DS0104_ROOT / ds,
        RUL_ROOT / ds,
        RUL_ROOT / "DS05-DS06" / ds,
        RUL_ROOT / "DSO3" if ds == "DS03" else Path("__none__"),
    ]
    feature_dir = first_existing([p for p in feature_candidates if p.exists()])
    if feature_dir is None:
        return None

    train_path = feature_dir / f"train_{ds}_v0.csv"
    test_path = feature_dir / f"test_{ds}_v0.csv"
    scaler_path = feature_dir / f"scaler_{ds}_v0.json"
    if not (train_path.exists() and test_path.exists() and scaler_path.exists()):
        return None

    pred_candidates = [
        RUL_DS0104_ROOT / "OUTPUTS" / f"ncmapss_{ds}_rul_predictions_autogluon.csv",
        RUL_ROOT / ds / f"ncmapss_{ds}_rul_predictions_autogluon_FIXED.csv",
        RUL_ROOT / "DS05-DS06" / f"ncmapss_{ds}_rul_predictions_autogluon_FIXED.csv",
        RUL_ROOT / "DSO3" / f"ncmapss_{ds}_rul_predictions_autogluon_FIXED.csv" if ds == "DS03" else Path("__none__"),
    ]
    pred_path = first_existing([p for p in pred_candidates if p.exists()])
    if pred_path is None:
        return None

    artifact_candidates = [
        RUL_DS0104_ROOT / "OUTPUTS" / f"ncmapss_{ds}_autogluon_artifacts",
        RUL_ROOT / ds / f"ncmapss_{ds}_autogluon_artifacts",
        RUL_ROOT / "DS05-DS06" / f"ncmapss_{ds}_autogluon_artifacts",
        RUL_ROOT / "DSO3" / f"ncmapss_{ds}_autogluon_artifacts" if ds == "DS03" else Path("__none__"),
    ]
    artifact_path = first_existing([p for p in artifact_candidates if p.exists()])
    if artifact_path is None:
        return None

    return {
        "train": train_path,
        "test": test_path,
        "scaler": scaler_path,
        "pred": pred_path,
        "artifact": artifact_path,
    }


@st.cache_data(show_spinner=True)
def compute_shap_bundle(dataset: str) -> Dict:
    if not SHAP_AVAILABLE:
        return {"status": "unavailable", "message": f"SHAP import failed: {SHAP_IMPORT_ERROR}"}

    paths = resolve_shap_paths(dataset)
    if not paths:
        return {"status": "unavailable", "message": f"No compatible model/artifact bundle found for {dataset}."}

    scaler_payload = json.loads(Path(paths["scaler"]).read_text(encoding="utf-8"))
    base_features = scaler_payload.get("feature_columns", [])
    if not isinstance(base_features, list) or not base_features:
        return {"status": "error", "message": "feature_columns not found in scaler JSON."}

    feature_cols = list(base_features)
    for col in base_features:
        feature_cols.extend([f"{col}__delta1", f"{col}__roll_mean3", f"{col}__roll_std3", f"{col}__slope5"])

    train_df = pd.read_csv(paths["train"])
    train_df["split"] = "train"
    test_df = pd.read_csv(paths["test"])
    test_df["split"] = "test"

    train_fe = apply_light_fe(train_df, base_features)
    test_fe = apply_light_fe(test_df, base_features)
    full = pd.concat([train_fe, test_fe], ignore_index=True, sort=False)
    full = full[["split", "engine_id", "cycle"] + feature_cols].copy()

    pred_df = pd.read_csv(paths["pred"])
    pred_df["split"] = pred_df["split"].astype(str).str.lower().replace({"val": "train"})
    pred_df["engine_id"] = pd.to_numeric(pred_df["engine_id"], errors="coerce").astype("Int64")
    pred_df["cycle"] = pd.to_numeric(pred_df["cycle"], errors="coerce").astype("Int64")
    pred_df = pred_df.groupby(["split", "engine_id", "cycle"], as_index=False)["rul_pred"].mean()

    merged = pred_df.merge(full, on=["split", "engine_id", "cycle"], how="left")
    valid_mask = ~merged[feature_cols].isna().any(axis=1)
    merged = merged[valid_mask].copy().reset_index(drop=True)
    if merged.empty:
        return {"status": "error", "message": "No valid merged rows for SHAP."}

    X = merged[feature_cols].astype(float)
    y = merged["rul_pred"].astype(float)

    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X, y)

    y_hat = model.predict(X)
    rmse = float(np.sqrt(mean_squared_error(y, y_hat)))
    r2 = float(r2_score(y, y_hat))

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X, check_additivity=False)
    if isinstance(shap_values, list):
        shap_values = shap_values[0]
    shap_values = np.asarray(shap_values, dtype=np.float32)

    mean_abs = np.mean(np.abs(shap_values), axis=0)
    top_global = pd.DataFrame({"feature": feature_cols, "mean_abs_shap": mean_abs}).sort_values(
        "mean_abs_shap", ascending=False
    )

    merged["shap_row_idx"] = np.arange(len(merged), dtype=int)

    return {
        "status": "ok",
        "rows": merged[["split", "engine_id", "cycle", "rul_pred", "shap_row_idx"]],
        "feature_cols": feature_cols,
        "shap_values": shap_values,
        "global_top": top_global.reset_index(drop=True),
        "coverage_pct": float(100.0 * valid_mask.mean()),
        "proxy_rmse": rmse,
        "proxy_r2": r2,
        "n_rows": int(len(merged)),
        "artifact_path": str(paths["artifact"]),
    }


def render_policy_why(view: pd.DataFrame, engine_df: pd.DataFrame, current_row: pd.Series, selected_cycle: int) -> None:
    st.subheader("Policy Why")

    snapshot = derive_policy_snapshot(current_row)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Decision", str(snapshot["decision_label"]))
    c2.metric("Recommended Action", str(snapshot["recommended_action"]))
    c3.metric("Primary Driver", str(snapshot["primary_driver"]))
    c4.metric("Risk Score", f"{int(snapshot['risk_score'])}/100")
    c5.metric("Confidence", str(snapshot["confidence"]))

    st.caption(str(snapshot["short_why"]))

    detail = st.toggle("Show full reason details", value=True, key="policy_detail_toggle")
    if detail:
        st.code(
            "\n".join(
                [
                    f"reason_codes: {current_row.get('reason_codes', '')}",
                    f"reason_text: {current_row.get('reason_text', '')}",
                    f"policy_version: {current_row.get('policy_version', '')}",
                    f"run_id: {current_row.get('run_id', '')}",
                    f"persistence_counter: {current_row.get('persistence_counter', '')}",
                ]
            ),
            language="text",
        )

    st.markdown("**Top reason codes (selected split)**")
    exploded = view["reason_codes"].astype(str).str.split("|").explode().str.strip()
    exploded = exploded[exploded != ""]
    if exploded.empty:
        st.info("No reason codes found.")
    else:
        rc_df = exploded.value_counts().head(8).reset_index()
        rc_df.columns = ["reason_code", "count"]
        st.dataframe(rc_df, use_container_width=True)

    st.subheader("Ask the Twin")
    q = st.selectbox(
        "Preset questions",
        options=[
            "What is current health state?",
            "What is the biggest decision driver right now?",
            "What is alarm density in last 50 cycles?",
            "When did decision transitions happen?",
            "Do recent trends indicate rising risk?",
        ],
        index=0,
        key="ask_twin_select",
    )

    if q == "What is current health state?":
        st.success(f"{snapshot['decision_label']} -> {snapshot['recommended_action']} | confidence={snapshot['confidence']}")
        st.caption(str(snapshot["short_why"]))

    elif q == "What is the biggest decision driver right now?":
        st.info(f"Primary driver: {snapshot['primary_driver']}")
        st.caption("Reason codes: " + (", ".join(snapshot["reason_codes"]) if snapshot["reason_codes"] else "MISSING"))

    elif q == "What is alarm density in last 50 cycles?":
        alarm_rate, immediate_rate, err = compute_alarm_kpis(engine_df, window_n=50, end_cycle=selected_cycle)
        if err:
            st.warning(err)
        else:
            k1, k2 = st.columns(2)
            k1.metric("Alarm Rate (last 50)", f"{alarm_rate * 100:.2f}%")
            k2.metric("Immediate Rate (last 50)", f"{immediate_rate * 100:.2f}%")

    elif q == "When did decision transitions happen?":
        trans, err = compute_transitions(engine_df)
        if err:
            st.warning(err)
        elif trans.empty:
            st.info("No transitions found.")
        else:
            st.dataframe(trans.tail(12), use_container_width=True)

    elif q == "Do recent trends indicate rising risk?":
        trend, err = compute_trend(engine_df, window_n=30, end_cycle=selected_cycle)
        if err:
            st.warning(err)
        else:
            rul_bad = trend["rul_slope"] < -1e-6
            anom_bad = trend["anom_slope"] > 1e-6
            if rul_bad and anom_bad:
                verdict = "Risk increasing"
            elif (not rul_bad) and (not anom_bad):
                verdict = "Risk stable/decreasing"
            else:
                verdict = "Mixed signals"
            st.success(verdict)
            st.caption(f"rul_slope={trend['rul_slope']:.6f}, anomaly_slope={trend['anom_slope']:.6f}")

    st.subheader("Transitions & KPI")
    trans, _ = compute_transitions(engine_df)
    if trans.empty:
        st.info("No transition points for selected engine.")
    else:
        st.dataframe(trans, use_container_width=True)

    matrix_df = view.sort_values(["engine_id", "cycle"]).copy()
    matrix_df["prev_decision"] = matrix_df.groupby("engine_id")["decision_label"].shift(1)
    matrix_df = matrix_df[matrix_df["prev_decision"].notna() & (matrix_df["prev_decision"] != matrix_df["decision_label"])].copy()
    if not matrix_df.empty:
        st.caption("Decision transition matrix (selected split)")
        st.dataframe(pd.crosstab(matrix_df["prev_decision"], matrix_df["decision_label"]), use_container_width=True)

    alarm_rate, immediate_rate, _ = compute_alarm_kpis(view, window_n=0, end_cycle=selected_cycle)
    k1, k2, k3 = st.columns(3)
    k1.metric("Alarm Rate (split)", "-" if alarm_rate is None else f"{alarm_rate * 100:.2f}%")
    k2.metric("Immediate Rate (split)", "-" if immediate_rate is None else f"{immediate_rate * 100:.2f}%")
    k3.metric("Anomaly ON Rate (split)", f"{(view['anomaly_state'].astype(str) == 'ON').mean() * 100:.2f}%")

def render_failure_expectation(engine_df: pd.DataFrame, current_row: pd.Series, selected_cycle: int) -> None:
    st.subheader("Expected Failure Stage")
    info = infer_failure_expectation(engine_df, current_row, selected_cycle)

    c1, c2 = st.columns(2)
    c1.metric("Stage", str(info["stage"]))
    c2.metric("Severity", str(info["severity"]))

    st.markdown(f"**Expected issue:** {info['expected_issue']}")
    st.caption(str(info["why"]))

    evidence = info.get("evidence", {})
    if evidence:
        st.dataframe(pd.DataFrame([evidence]), use_container_width=True)


def render_model_why(dataset: str, split: str, engine: int, selected_cycle: int) -> None:
    st.subheader("Model Why (SHAP)")
    shap_bundle = compute_shap_bundle(dataset)
    if shap_bundle.get("status") != "ok":
        st.info(shap_bundle.get("message", "SHAP is not available for this dataset."))
        return

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Coverage %", round(float(shap_bundle["coverage_pct"]), 2))
    s2.metric("Proxy RMSE", round(float(shap_bundle["proxy_rmse"]), 4))
    s3.metric("Proxy R2", round(float(shap_bundle["proxy_r2"]), 4))
    s4.metric("Rows", int(shap_bundle["n_rows"]))

    st.caption(f"artifact: {shap_bundle['artifact_path']}")

    top_global = shap_bundle["global_top"].head(15)
    fig_global = go.Figure(
        data=[
            go.Bar(
                x=top_global["mean_abs_shap"],
                y=top_global["feature"],
                orientation="h",
                marker_color="teal",
            )
        ]
    )
    fig_global.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20), yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_global, use_container_width=True)

    rows = shap_bundle["rows"].copy()
    rows["split"] = rows["split"].astype(str).str.lower()
    local = rows[(rows["split"] == split) & (rows["engine_id"] == int(engine))].sort_values("cycle")

    if local.empty:
        st.warning("No SHAP rows found for selected split/engine.")
        return

    cycle_options = local["cycle"].astype(int).tolist()
    default_cycle = int(selected_cycle) if int(selected_cycle) in cycle_options else int(cycle_options[-1])
    cycle_pick = st.select_slider("Cycle for local SHAP", options=cycle_options, value=default_cycle, key="shap_cycle_pick")

    selected = local[local["cycle"] == int(cycle_pick)].iloc[-1]
    idx = int(selected["shap_row_idx"])

    feature_cols = shap_bundle["feature_cols"]
    shap_values = np.asarray(shap_bundle["shap_values"], dtype=float)
    row_shap = shap_values[idx]

    order = np.argsort(np.abs(row_shap))[::-1][:12]
    local_df = pd.DataFrame(
        {
            "feature": [feature_cols[i] for i in order],
            "shap_value": [float(row_shap[i]) for i in order],
        }
    ).sort_values("shap_value")

    colors = ["crimson" if v < 0 else "seagreen" for v in local_df["shap_value"]]
    fig_local = go.Figure(
        data=[
            go.Bar(
                x=local_df["shap_value"],
                y=local_df["feature"],
                orientation="h",
                marker_color=colors,
            )
        ]
    )
    fig_local.add_vline(x=0, line_dash="dot", line_color="gray")
    fig_local.update_layout(height=380, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_local, use_container_width=True)


# App
st.set_page_config(page_title="AeroTrace - Twin Phase-1", layout="wide")
st.title("AeroTrace - Digital Twin (Policy-Driven)")

policy_root = Path(st.sidebar.text_input("Policy Outputs Root", str(POLICY_DEFAULT_ROOT)))
anomaly_mode = st.sidebar.selectbox("Anomaly signal", ["anomaly_score_smoothed", "anomaly_score_raw"], index=0)

policy_files = discover_policy_outputs(str(policy_root))
if not policy_files:
    st.error(f"No decision_support_v2 files found under: {policy_root}")
    st.stop()

dataset = st.sidebar.selectbox("Dataset", list(policy_files.keys()))
source_path = policy_files[dataset]

try:
    policy_df = load_policy_dataset(source_path)
except Exception as exc:
    st.error(f"Failed to load policy dataset: {exc}")
    st.stop()

policy_df = policy_df[policy_df["dataset_id"] == dataset].copy()
if policy_df.empty:
    st.error(f"No rows for dataset={dataset} in selected file.")
    st.stop()

split_values = sorted(policy_df["split"].unique().tolist())
split = st.sidebar.selectbox("Split", split_values)
view = policy_df[policy_df["split"] == split].copy()
if view.empty:
    st.error("No rows for selected split.")
    st.stop()

engines = sorted(view["engine_id"].astype(int).unique().tolist())
engine = st.sidebar.selectbox("Engine", engines)
engine_df = view[view["engine_id"] == engine].sort_values("cycle").copy()
if engine_df.empty:
    st.error("No rows for selected engine.")
    st.stop()

cycle_min = int(engine_df["cycle"].min())
cycle_max = int(engine_df["cycle"].max())
selected_cycle = st.sidebar.slider("Cycle", min_value=cycle_min, max_value=cycle_max, value=cycle_max)

row_pick = engine_df[engine_df["cycle"] == int(selected_cycle)]
if row_pick.empty:
    current_row = engine_df.iloc[-1]
else:
    current_row = row_pick.iloc[-1]

# Header summary
h1, h2, h3, h4 = st.columns(4)
h1.metric("Rows (split)", int(len(view)))
h2.metric("Engines (split)", int(view["engine_id"].nunique()))
h3.metric("Policy Version", str(view["policy_version"].iloc[0]))
h4.metric("Run ID", str(view["run_id"].iloc[0]))

st.caption(f"Policy source: {source_path}")

st.subheader(f"Engine Timeline - {dataset} / split={split} / engine={engine}")
fig = build_timeline_figure(engine_df, selected_cycle=int(selected_cycle), anomaly_col=anomaly_mode)
st.plotly_chart(fig, use_container_width=True)

policy_tab, model_tab = st.tabs(["Policy Why", "Model Why (SHAP)"])

with policy_tab:
    render_policy_why(view=view, engine_df=engine_df, current_row=current_row, selected_cycle=int(selected_cycle))
    render_failure_expectation(engine_df=engine_df, current_row=current_row, selected_cycle=int(selected_cycle))

with model_tab:
    render_model_why(dataset=dataset, split=split, engine=int(engine), selected_cycle=int(selected_cycle))

st.subheader("Policy Snapshot")
st.json(
    {
        "dataset": dataset,
        "split": split,
        "engine": int(engine),
        "cycle": int(current_row["cycle"]),
        "decision_label": str(current_row.get("decision_label", "")),
        "anomaly_state": str(current_row.get("anomaly_state", "")),
        "theta_rul_used": float(current_row.get("theta_rul_used", np.nan)),
        "alpha_high_used": float(current_row.get("alpha_high_used", np.nan)),
        "alpha_low_used": float(current_row.get("alpha_low_used", np.nan)),
        "policy_version": str(current_row.get("policy_version", "")),
        "run_id": str(current_row.get("run_id", "")),
    }
)

