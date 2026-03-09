#!/usr/bin/env python3
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


POLICY_DEFAULT_ROOT = Path("twin/data/decision_support_v2_outputs")
HYBRID_DEFAULT_ROOT = Path("twin/data/hybrid_phase2")
RE_V2_NCMAPSS = re.compile(r"^ncmapss_(DS\d{2})_decision_support_v2\.csv$", re.IGNORECASE)
APP_REV = "3d-geo-v2-2026-02-14-08twin"


@st.cache_data(show_spinner=False)
def discover_policy_outputs(root_str: str) -> Dict[str, str]:
    root = Path(root_str)
    out: Dict[str, str] = {}
    if not root.exists():
        return out

    for item in root.iterdir():
        if not item.is_file():
            continue
        match = RE_V2_NCMAPSS.match(item.name)
        if not match:
            continue
        out[match.group(1).upper()] = str(item)
    return dict(sorted(out.items()))


@st.cache_data(show_spinner=False)
def discover_hybrid_outputs(root_str: str) -> Dict[str, str]:
    root = Path(root_str)
    out: Dict[str, str] = {}
    if not root.exists():
        return out

    for ds_dir in root.iterdir():
        if not ds_dir.is_dir():
            continue
        ds = ds_dir.name.upper().strip()
        if not re.match(r"^DS\d{2}$", ds):
            continue
        path = ds_dir / "hybrid_timeline.csv"
        if path.exists():
            out[ds] = str(path)

    return dict(sorted(out.items()))


@st.cache_data(show_spinner=False)
def load_policy_dataset(path_str: str) -> pd.DataFrame:
    df = pd.read_csv(path_str)
    required = {
        "dataset_id",
        "split",
        "asset_id",
        "t",
        "rul_pred",
        "anomaly_score_smoothed",
        "decision_label",
        "reason_codes",
        "theta_rul_used",
        "alpha_high_used",
        "alpha_low_used",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    out = df.rename(columns={"asset_id": "engine_id", "t": "cycle"}).copy()
    out["dataset_id"] = out["dataset_id"].astype(str).str.upper().str.strip()
    out["split"] = out["split"].astype(str).str.lower().str.strip()
    out["engine_id"] = pd.to_numeric(out["engine_id"], errors="coerce").astype(int)
    out["cycle"] = pd.to_numeric(out["cycle"], errors="coerce").astype(int)

    for col in [
        "rul_pred",
        "anomaly_score_smoothed",
        "theta_rul_used",
        "alpha_high_used",
        "alpha_low_used",
    ]:
        out[col] = pd.to_numeric(out[col], errors="coerce").astype(float)

    return out.sort_values(["split", "engine_id", "cycle"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_hybrid_dataset(path_str: str) -> pd.DataFrame:
    df = pd.read_csv(path_str)
    required = {
        "dataset_id",
        "split",
        "engine_id",
        "cycle",
        "rul_pred",
        "anomaly_score_smoothed",
        "decision_label",
        "reason_codes",
        "theta_rul_used",
        "alpha_high_used",
        "alpha_low_used",
        "hybrid_risk",
        "hybrid_state",
        "dominant_driver",
        "expected_failure_stage",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    out = df.copy()
    out["dataset_id"] = out["dataset_id"].astype(str).str.upper().str.strip()
    out["split"] = out["split"].astype(str).str.lower().str.strip()
    out["engine_id"] = pd.to_numeric(out["engine_id"], errors="coerce").astype(int)
    out["cycle"] = pd.to_numeric(out["cycle"], errors="coerce").astype(int)

    numeric_cols = [
        "rul_pred",
        "anomaly_score_smoothed",
        "theta_rul_used",
        "alpha_high_used",
        "alpha_low_used",
        "hybrid_risk",
        "model_risk",
        "policy_risk",
        "trend_risk",
        "volatility_risk",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype(float)

    if "reason_codes" not in out.columns:
        out["reason_codes"] = ""

    return out.sort_values(["split", "engine_id", "cycle"]).reset_index(drop=True)


def normalize_risk(row: pd.Series) -> Dict[str, float]:
    theta = max(float(row["theta_rul_used"]), 1e-9)
    rul = float(row["rul_pred"])
    alpha_low = float(row["alpha_low_used"])
    alpha_high = float(row["alpha_high_used"])
    anom = float(row["anomaly_score_smoothed"])

    rul_risk = float(np.clip((theta - rul) / theta, 0.0, 1.0))
    anom_den = max(alpha_high - alpha_low, 1e-9)
    anom_risk = float(np.clip((anom - alpha_low) / anom_den, 0.0, 1.0))
    return {"rul_risk": rul_risk, "anom_risk": anom_risk}


def component_healths(row: pd.Series, use_hybrid: bool) -> Dict[str, float]:
    risk = normalize_risk(row)
    rul_risk = risk["rul_risk"]
    anom_risk = risk["anom_risk"]

    weights = {
        "Fan": (0.35, 0.15),
        "LPC": (0.50, 0.25),
        "HPC": (0.65, 0.40),
        "Combustor": (0.55, 0.70),
        "HPT": (0.70, 0.65),
        "LPT": (0.75, 0.45),
        "Nozzle": (0.40, 0.25),
    }

    out: Dict[str, float] = {}
    for name, (w_rul, w_anom) in weights.items():
        out[name] = float(np.clip(w_rul * rul_risk + w_anom * anom_risk, 0.0, 1.0))

    if not use_hybrid:
        reason_codes = str(row.get("reason_codes", ""))
        decision = str(row.get("decision_label", "Normal Operation"))
        base_boost = 0.0
        if "ANOM_ON" in reason_codes:
            base_boost += 0.08
        if "RUL_LOW" in reason_codes:
            base_boost += 0.08
        if decision == "Immediate Maintenance":
            base_boost += 0.12
        elif decision == "Planned Maintenance":
            base_boost += 0.06

        for k in out:
            out[k] = float(np.clip(out[k] + base_boost, 0.0, 1.0))
        return out

    hybrid_risk = float(np.clip(float(row.get("hybrid_risk", 0.0)), 0.0, 1.0))
    dominant_driver = str(row.get("dominant_driver", "")).lower().strip()
    stage = str(row.get("expected_failure_stage", ""))

    scale = 0.78 + 0.45 * hybrid_risk
    for k in out:
        out[k] = float(np.clip(out[k] * scale, 0.0, 1.0))

    driver_boosts = {
        "model": ["HPC", "HPT"],
        "policy": ["Combustor", "LPT"],
        "physics": ["HPT", "LPT", "Nozzle"],
        "uncertainty": ["Fan", "LPC"],
    }
    for comp in driver_boosts.get(dominant_driver, []):
        out[comp] = float(np.clip(out[comp] + 0.10 * hybrid_risk, 0.0, 1.0))

    if "Immediate Failure Risk" in stage:
        for comp in out:
            out[comp] = float(np.clip(out[comp] + 0.08, 0.0, 1.0))
    elif "RUL Degradation Path" in stage:
        for comp in ["HPT", "LPT", "Nozzle"]:
            out[comp] = float(np.clip(out[comp] + 0.09, 0.0, 1.0))
    elif "Anomaly Persistence Gate" in stage:
        for comp in ["HPC", "Combustor"]:
            out[comp] = float(np.clip(out[comp] + 0.08, 0.0, 1.0))

    return out


def add_tapered_surface(
    fig: go.Figure,
    *,
    name: str,
    z0: float,
    z1: float,
    r0: float,
    r1: float,
    health: float,
    opacity: float = 0.96,
) -> None:
    z_vals = np.linspace(z0, z1, 24)
    theta_vals = np.linspace(0.0, 2.0 * np.pi, 52)
    zz, tt = np.meshgrid(z_vals, theta_vals, indexing="ij")
    rr = r0 + (r1 - r0) * ((zz - z0) / max(z1 - z0, 1e-9))

    xx = rr * np.cos(tt)
    yy = rr * np.sin(tt)
    cc = np.full_like(xx, fill_value=float(health), dtype=float)

    fig.add_surface(
        x=xx,
        y=yy,
        z=zz,
        surfacecolor=cc,
        cmin=0.0,
        cmax=1.0,
        colorscale=[
            [0.0, "#16a34a"],
            [0.45, "#facc15"],
            [0.70, "#fb923c"],
            [1.0, "#dc2626"],
        ],
        showscale=False,
        opacity=opacity,
        name=name,
        hovertemplate=f"{name}<br>risk=%{{surfacecolor:.2f}}<extra></extra>",
    )


def add_annulus_disk(
    fig: go.Figure,
    *,
    name: str,
    z: float,
    r_inner: float,
    r_outer: float,
    health: float,
) -> None:
    r_vals = np.linspace(max(r_inner, 1e-6), r_outer, 18)
    theta_vals = np.linspace(0.0, 2.0 * np.pi, 60)
    rr, tt = np.meshgrid(r_vals, theta_vals, indexing="ij")

    xx = rr * np.cos(tt)
    yy = rr * np.sin(tt)
    zz = np.full_like(xx, fill_value=float(z), dtype=float)
    cc = np.full_like(xx, fill_value=float(health), dtype=float)

    fig.add_surface(
        x=xx,
        y=yy,
        z=zz,
        surfacecolor=cc,
        cmin=0.0,
        cmax=1.0,
        colorscale=[
            [0.0, "#16a34a"],
            [0.45, "#facc15"],
            [0.70, "#fb923c"],
            [1.0, "#dc2626"],
        ],
        showscale=False,
        opacity=0.88,
        name=name,
        hovertemplate=f"{name}<br>risk=%{{surfacecolor:.2f}}<extra></extra>",
    )


def add_blade_crown(
    fig: go.Figure,
    *,
    z: float,
    r_inner: float,
    r_outer: float,
    n_blades: int,
    color: str,
) -> None:
    angles = np.linspace(0.0, 2.0 * np.pi, int(max(n_blades, 3)), endpoint=False)
    for a in angles:
        x_vals = [r_inner * np.cos(a), r_outer * np.cos(a)]
        y_vals = [r_inner * np.sin(a), r_outer * np.sin(a)]
        z_vals = [z, z]
        fig.add_trace(
            go.Scatter3d(
                x=x_vals,
                y=y_vals,
                z=z_vals,
                mode="lines",
                line=dict(color=color, width=3),
                hoverinfo="skip",
                showlegend=False,
            )
        )


def build_engine_figure(row: pd.Series, selected_cycle: int, use_hybrid: bool) -> go.Figure:
    healths = component_healths(row, use_hybrid=use_hybrid)
    inlet_risk = float(np.clip(0.9 * healths["Fan"], 0.0, 1.0))

    geometry = [
        ("Inlet", 0.0, 1.2, 2.15, 2.05, inlet_risk),
        ("Fan", 1.2, 2.4, 2.05, 1.85, healths["Fan"]),
        ("LPC", 2.4, 4.0, 1.85, 1.55, healths["LPC"]),
        ("HPC", 4.0, 5.5, 1.55, 1.20, healths["HPC"]),
        ("Combustor", 5.5, 6.8, 1.20, 1.35, healths["Combustor"]),
        ("HPT", 6.8, 8.1, 1.35, 1.05, healths["HPT"]),
        ("LPT", 8.1, 9.2, 1.05, 0.85, healths["LPT"]),
        ("Nozzle", 9.2, 10.2, 0.85, 0.55, healths["Nozzle"]),
    ]

    fig = go.Figure()
    for name, z0, z1, r0, r1, risk in geometry:
        add_tapered_surface(fig, name=name, z0=z0, z1=z1, r0=r0, r1=r1, health=risk)

    crowns = [
        ("Fan Disk", 1.8, 0.20, 1.70, 20, healths["Fan"]),
        ("LPC Disk", 3.2, 0.22, 1.45, 16, healths["LPC"]),
        ("HPC Disk", 4.8, 0.24, 1.10, 14, healths["HPC"]),
        ("HPT Disk", 7.3, 0.22, 1.00, 14, healths["HPT"]),
        ("LPT Disk", 8.6, 0.20, 0.80, 12, healths["LPT"]),
    ]
    for disk_name, zc, r_in, r_out, n_blades, risk in crowns:
        add_annulus_disk(fig, name=disk_name, z=zc, r_inner=r_in, r_outer=r_out, health=risk)
        blade_color = "#1f2937" if risk < 0.6 else "#7f1d1d"
        add_blade_crown(fig, z=zc, r_inner=max(0.35, r_in + 0.08), r_outer=r_out, n_blades=n_blades, color=blade_color)

    add_annulus_disk(
        fig,
        name="Combustor Liner",
        z=6.15,
        r_inner=0.35,
        r_outer=1.05,
        health=healths["Combustor"],
    )

    fig.add_trace(
        go.Scatter3d(
            x=[0.0, 0.0],
            y=[0.0, 0.0],
            z=[0.0, 10.2],
            mode="lines",
            line=dict(color="#111827", width=7),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    add_tapered_surface(
        fig,
        name="Center Body",
        z0=8.9,
        z1=10.2,
        r0=0.35,
        r1=0.08,
        health=healths["Nozzle"],
        opacity=0.82,
    )

    labels = [
        ("Fan", 2.35, 1.9),
        ("LPC", 1.95, 3.3),
        ("HPC", 1.60, 4.8),
        ("Combustor", 1.45, 6.2),
        ("HPT", 1.35, 7.45),
        ("LPT", 1.15, 8.65),
        ("Nozzle", 0.95, 9.65),
    ]
    for text, x_pos, z_pos in labels:
        fig.add_trace(
            go.Scatter3d(
                x=[x_pos],
                y=[0.0],
                z=[z_pos],
                mode="text",
                text=[text],
                textfont=dict(size=11, color="#111827"),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        height=700,
        margin=dict(l=0, r=0, t=30, b=0),
        title=f"Engine 3D Health Map - cycle={selected_cycle}",
        scene=dict(
            xaxis=dict(visible=False, range=[-2.6, 2.6]),
            yaxis=dict(visible=False, range=[-2.6, 2.6]),
            zaxis=dict(visible=False, range=[-0.2, 10.4]),
            aspectmode="manual",
            aspectratio=dict(x=1.2, y=1.2, z=2.0),
            camera=dict(eye=dict(x=2.3, y=1.8, z=1.15)),
            bgcolor="#f8fafc",
        ),
    )
    return fig


def build_trend_figure(engine_df: pd.DataFrame, selected_cycle: int, use_hybrid: bool) -> go.Figure:
    g = engine_df[engine_df["cycle"] <= selected_cycle].copy()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=g["cycle"],
            y=g["rul_pred"],
            mode="lines",
            name="rul_pred",
            line=dict(width=2, color="#2563eb"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=g["cycle"],
            y=g["anomaly_score_smoothed"],
            mode="lines",
            name="anomaly_score_smoothed",
            yaxis="y2",
            line=dict(width=2, color="#0ea5e9"),
        )
    )

    if use_hybrid and "hybrid_risk" in g.columns:
        fig.add_trace(
            go.Scatter(
                x=g["cycle"],
                y=g["hybrid_risk"],
                mode="lines",
                name="hybrid_risk",
                yaxis="y2",
                line=dict(width=2, color="#ef4444"),
            )
        )

    fig.add_vline(x=selected_cycle, line_dash="dot", line_color="#111827")
    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis=dict(title="RUL"),
        yaxis2=dict(title="Anomaly / Hybrid", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
    )
    return fig


def build_component_risk_history_figure(engine_df: pd.DataFrame, use_hybrid: bool, selected_cycle: int) -> go.Figure:
    rows: List[Dict[str, float]] = []
    for item in engine_df.sort_values("cycle").itertuples(index=False):
        row_s = pd.Series(item._asdict())
        comp = component_healths(row_s, use_hybrid=use_hybrid)
        rec: Dict[str, float] = {"cycle": float(getattr(item, "cycle"))}
        for k, v in comp.items():
            rec[k] = float(v)
        rec["avg_component_risk"] = float(np.mean(list(comp.values())))
        rows.append(rec)

    hist = pd.DataFrame(rows)
    fig = go.Figure()

    component_order = ["Fan", "LPC", "HPC", "Combustor", "HPT", "LPT", "Nozzle"]
    for name in component_order:
        if name not in hist.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=hist["cycle"],
                y=hist[name],
                mode="lines",
                name=name,
                line=dict(width=1.8),
                opacity=0.82,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=hist["cycle"],
            y=hist["avg_component_risk"],
            mode="lines",
            name="avg_component_risk",
            line=dict(width=3, color="#111827", dash="dot"),
        )
    )

    fig.add_vline(x=selected_cycle, line_dash="dot", line_color="#111827")
    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis=dict(title="Component Risk", range=[0.0, 1.02]),
        xaxis=dict(title="Cycle"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
    )
    return fig


def source_label(value: str) -> str:
    if value == "hybrid_phase2":
        return "Hybrid Phase-2 (Recommended)"
    return "Policy V2 Baseline"


st.set_page_config(page_title="AeroTrace - Twin 3D", layout="wide")
st.title("AeroTrace - 3D Twin Simulation")
st.caption(f"UI revision: {APP_REV}")

source_mode = st.sidebar.selectbox(
    "Data Source",
    options=["hybrid_phase2", "policy_v2"],
    format_func=source_label,
    index=0,
)

if source_mode == "hybrid_phase2":
    root = Path(st.sidebar.text_input("Hybrid Outputs Root", str(HYBRID_DEFAULT_ROOT)))
    files = discover_hybrid_outputs(str(root))
else:
    root = Path(st.sidebar.text_input("Policy Outputs Root", str(POLICY_DEFAULT_ROOT)))
    files = discover_policy_outputs(str(root))

if not files:
    if source_mode == "hybrid_phase2":
        st.error(
            "No hybrid outputs found. Run: .\\.venv\\Scripts\\python.exe twin/scripts/run_twin_hybrid_phase2.py"
        )
    else:
        st.error(f"No policy file found under: {root}")
    st.stop()

dataset = st.sidebar.selectbox("Dataset", list(files.keys()))
source_path = files[dataset]

if source_mode == "hybrid_phase2":
    df = load_hybrid_dataset(source_path)
else:
    df = load_policy_dataset(source_path)

df = df[df["dataset_id"] == dataset].copy()
if df.empty:
    st.error("No rows for selected dataset.")
    st.stop()

split = st.sidebar.selectbox("Split", sorted(df["split"].unique().tolist()))
view = df[df["split"] == split].copy()
engines = sorted(view["engine_id"].unique().tolist())
engine = st.sidebar.selectbox("Engine", engines)

engine_df = view[view["engine_id"] == engine].sort_values("cycle").copy()
if engine_df.empty:
    st.error("No rows for selected engine.")
    st.stop()

cycle_values = engine_df["cycle"].astype(int).tolist()
cycle_idx_map = {int(c): idx for idx, c in enumerate(cycle_values)}

cycle_state_key = f"cycle_state::{source_mode}::{dataset}::{split}::{engine}"
play_state_key = f"cycle_play::{source_mode}::{dataset}::{split}::{engine}"
delay_key = f"cycle_delay::{source_mode}::{dataset}::{split}::{engine}"
delay_options = [120, 250, 400, 600, 900, 1300]

if cycle_state_key not in st.session_state or int(st.session_state[cycle_state_key]) not in cycle_idx_map:
    st.session_state[cycle_state_key] = int(cycle_values[-1])
if play_state_key not in st.session_state:
    st.session_state[play_state_key] = False
if delay_key not in st.session_state or int(st.session_state[delay_key]) not in delay_options:
    st.session_state[delay_key] = 600

st.sidebar.markdown("### Cycle Playback")
pb1, pb2 = st.sidebar.columns(2)
if pb1.button("Prev Cycle", use_container_width=True):
    idx = max(cycle_idx_map[int(st.session_state[cycle_state_key])] - 1, 0)
    st.session_state[cycle_state_key] = int(cycle_values[idx])
    st.session_state[play_state_key] = False
if pb2.button("Next Cycle", use_container_width=True):
    idx = min(cycle_idx_map[int(st.session_state[cycle_state_key])] + 1, len(cycle_values) - 1)
    st.session_state[cycle_state_key] = int(cycle_values[idx])
    st.session_state[play_state_key] = False

st.sidebar.select_slider("Cycle (step-by-step)", options=cycle_values, key=cycle_state_key)
st.sidebar.toggle("Auto Play", key=play_state_key)
st.sidebar.select_slider("Auto Play Delay (ms)", options=delay_options, key=delay_key)

cycle = int(st.session_state[cycle_state_key])
row_idx = int(cycle_idx_map[cycle])
row = engine_df[engine_df["cycle"] == cycle].iloc[-1]

use_hybrid = source_mode == "hybrid_phase2" and "hybrid_risk" in row.index

st.caption(f"Source: `{source_path}`")
st.caption(f"Cycle step: {row_idx + 1}/{len(cycle_values)}")

if use_hybrid:
    h1, h2, h3, h4, h5, h6 = st.columns(6)
    h1.metric("Decision", str(row["decision_label"]))
    h2.metric("Hybrid State", str(row.get("hybrid_state", "-")))
    h3.metric("Hybrid Risk", f"{float(row.get('hybrid_risk', np.nan)):.3f}")
    h4.metric("RUL", f"{float(row['rul_pred']):.2f}")
    h5.metric("Anomaly", f"{float(row['anomaly_score_smoothed']):.4f}")
    h6.metric("Driver", str(row.get("dominant_driver", "-")))
else:
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Decision", str(row["decision_label"]))
    h2.metric("RUL", f"{float(row['rul_pred']):.2f}")
    h3.metric("Anomaly", f"{float(row['anomaly_score_smoothed']):.4f}")
    h4.metric("Reason Codes", str(row.get("reason_codes", "")))

healths = component_healths(row, use_hybrid=use_hybrid)
overall_component_risk = float(np.mean(list(healths.values())))

caption = (
    f"Component risk index={overall_component_risk:.3f} | "
    f"theta={float(row['theta_rul_used']):.2f}, "
    f"alpha_low/high={float(row['alpha_low_used']):.4f}/{float(row['alpha_high_used']):.4f}"
)
if use_hybrid:
    caption += (
        f" | hybrid_risk={float(row.get('hybrid_risk', np.nan)):.3f}"
        f" | stage={str(row.get('expected_failure_stage', '-'))}"
    )
st.caption(caption)

col_3d, col_side = st.columns([2.6, 1.0])
with col_3d:
    st.plotly_chart(build_engine_figure(row, cycle, use_hybrid=use_hybrid), use_container_width=True)

with col_side:
    st.subheader("Component Risk")
    risk_df = pd.DataFrame(
        {"component": list(healths.keys()), "risk_score": [round(v, 3) for v in healths.values()]}
    ).sort_values("risk_score", ascending=False)
    st.dataframe(risk_df, use_container_width=True, hide_index=True)

    st.subheader("Cycle Delta")
    if row_idx == 0:
        st.info("No previous cycle to compare.")
    else:
        prev_cycle = int(cycle_values[row_idx - 1])
        prev_row = engine_df[engine_df["cycle"] == prev_cycle].iloc[-1]
        prev_healths = component_healths(prev_row, use_hybrid=use_hybrid)
        delta_df = pd.DataFrame(
            {
                "component": list(healths.keys()),
                "prev": [round(float(prev_healths[k]), 3) for k in healths.keys()],
                "current": [round(float(healths[k]), 3) for k in healths.keys()],
                "delta": [round(float(healths[k] - prev_healths[k]), 3) for k in healths.keys()],
            }
        ).sort_values("delta", ascending=False)
        st.dataframe(delta_df, use_container_width=True, hide_index=True)

    if use_hybrid:
        st.subheader("Hybrid Decomposition")
        decomp = {
            "model_risk": float(row.get("model_risk", np.nan)),
            "policy_risk": float(row.get("policy_risk", np.nan)),
            "physics_risk": float(row.get("trend_risk", np.nan)),
            "uncertainty_risk": float(row.get("volatility_risk", np.nan)),
        }
        st.dataframe(pd.DataFrame([decomp]), use_container_width=True, hide_index=True)

    st.subheader("Legend")
    st.markdown("- `0.00-0.45` low\n- `0.45-0.70` warning\n- `0.70-1.00` critical")

if use_hybrid:
    st.subheader("Expected Failure Stage")
    f1, f2, f3 = st.columns(3)
    f1.metric("Stage", str(row.get("expected_failure_stage", "-")))
    f2.metric("Dominant Driver", str(row.get("dominant_driver", "-")))
    f3.metric("Missed Alarm Proxy", "Yes" if bool(row.get("missed_alarm_proxy", False)) else "No")

st.subheader("Cycle Trend (up to selected cycle)")
st.plotly_chart(build_trend_figure(engine_df, cycle, use_hybrid=use_hybrid), use_container_width=True)

st.subheader("Component Risk Timeline")
st.plotly_chart(
    build_component_risk_history_figure(engine_df, use_hybrid=use_hybrid, selected_cycle=cycle),
    use_container_width=True,
)

if use_hybrid:
    st.subheader("Hybrid Timeline Snapshot")
    cols = [
        "cycle",
        "decision_label",
        "hybrid_state",
        "hybrid_risk",
        "dominant_driver",
        "expected_failure_stage",
        "critical_proxy",
        "missed_alarm_proxy",
    ]
    cols = [c for c in cols if c in engine_df.columns]
    st.dataframe(engine_df[engine_df["cycle"] <= cycle][cols].tail(20), use_container_width=True, hide_index=True)


# Auto Play: step-by-step replay
if st.session_state.get(play_state_key, False) and len(cycle_values) > 1:
    cur_idx = int(cycle_idx_map[int(cycle)])
    if cur_idx >= len(cycle_values) - 1:
        st.session_state[play_state_key] = False
    else:
        st.session_state[cycle_state_key] = int(cycle_values[cur_idx + 1])
        time.sleep(float(st.session_state[delay_key]) / 1000.0)
        st.rerun()
