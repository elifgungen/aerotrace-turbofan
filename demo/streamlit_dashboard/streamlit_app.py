from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


RE_DECISION_SUPPORT = re.compile(
    r"^(?P<ds>fd\d{3}|ncmapss_DS\d{2})_decision_support(?:_v2)?\.csv$",
    re.IGNORECASE,
)
RE_ANOMALY = re.compile(r"^(?P<ds>fd\d{3}|ncmapss_DS\d{2})_anomaly_scores\.csv$", re.IGNORECASE)
RE_RUL = re.compile(r"^(?P<ds>fd\d{3}|ncmapss_DS\d{2})_rul_predictions.*\.csv$", re.IGNORECASE)


CANONICAL_DECISION_SUPPORT_COLS = [
    "dataset_id",
    "split",
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

KEY_COLS = ["dataset_id", "split", "engine_id", "cycle"]

LABEL_COLORS = {
    "Normal Operation": "rgba(46, 204, 113, 0.10)",
    "Enhanced Monitoring": "rgba(241, 196, 15, 0.12)",
    "Planned Maintenance": "rgba(230, 126, 34, 0.12)",
    "Immediate Maintenance": "rgba(231, 76, 60, 0.12)",
}

LABEL_MARKER_COLORS = {
    "Normal Operation": "rgba(46, 204, 113, 0.95)",
    "Enhanced Monitoring": "rgba(241, 196, 15, 0.95)",
    "Planned Maintenance": "rgba(230, 126, 34, 0.95)",
    "Immediate Maintenance": "rgba(231, 76, 60, 0.95)",
}


@dataclass(frozen=True)
class DatasetFiles:
    dataset_id: str
    decision_support_csv: Path
    anomaly_scores_csv: Optional[Path]
    rul_predictions_csv: Optional[Path]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def outputs_dir_candidates() -> List[Path]:
    root = repo_root()
    return [
        root / "data" / "outputs",
        root / "decision_support_v2_outputs",
    ]


def resolve_default_outputs_dir() -> Path:
    env_path = os.getenv("JETCUBE_OUTPUTS_DIR")
    if env_path:
        return Path(env_path).expanduser()

    for candidate in outputs_dir_candidates():
        if candidate.exists():
            return candidate
    return outputs_dir_candidates()[0]


def _safe_relpath(p: Path) -> str:
    try:
        return str(p.relative_to(repo_root()))
    except Exception:
        return str(p)


def normalize_dataset_id(raw: str) -> str:
    token = str(raw).strip()
    if not token:
        return "UNKNOWN"
    upper = token.upper()
    if upper.startswith("NCMAPSS_"):
        return upper.replace("NCMAPSS_", "")
    return upper


def expected_paths_for_dataset(outdir: Path, dataset_id: str) -> Dict[str, Path]:
    ds_lower = dataset_id.lower()
    return {
        "decision_support.csv": outdir / f"{ds_lower}_decision_support.csv",
        "rul_predictions.csv": outdir / f"{ds_lower}_rul_predictions.csv",
        "anomaly_scores.csv": outdir / f"{ds_lower}_anomaly_scores.csv",
        "decision_support_report.json": outdir / f"{ds_lower}_decision_support_report.json",
    }


@st.cache_data(show_spinner=False)
def discover_datasets(outputs_path: str) -> Dict[str, DatasetFiles]:
    outdir = Path(outputs_path)
    datasets: Dict[str, Dict[str, Path]] = {}

    if not outdir.exists():
        return {}

    for child in outdir.iterdir():
        if not child.is_file():
            continue
        name = child.name
        m = RE_DECISION_SUPPORT.match(name)
        if m:
            ds = normalize_dataset_id(m.group("ds"))
            datasets.setdefault(ds, {})["decision_support"] = child
            continue
        m = RE_ANOMALY.match(name)
        if m:
            ds = normalize_dataset_id(m.group("ds"))
            datasets.setdefault(ds, {})["anomaly"] = child
            continue
        m = RE_RUL.match(name)
        if m:
            ds = normalize_dataset_id(m.group("ds"))
            datasets.setdefault(ds, {})["rul"] = child
            continue

    result: Dict[str, DatasetFiles] = {}
    for ds, parts in datasets.items():
        if "decision_support" not in parts:
            continue
        result[ds] = DatasetFiles(
            dataset_id=ds,
            decision_support_csv=parts["decision_support"],
            anomaly_scores_csv=parts.get("anomaly"),
            rul_predictions_csv=parts.get("rul"),
        )

    return dict(sorted(result.items(), key=lambda kv: kv[0]))


def _read_json_if_exists(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _required_missing_columns(df: pd.DataFrame, required: Iterable[str]) -> List[str]:
    cols = set(df.columns)
    return [c for c in required if c not in cols]


@st.cache_data(show_spinner=False)
def load_decision_support(csv_path: str) -> pd.DataFrame:
    p = Path(csv_path)
    df = pd.read_csv(
        p,
        low_memory=False,
    )

    # Backward-compat: normalize v2 exports into the canonical schema used by the dashboard.
    if "asset_id" in df.columns:
        rename_map = {
            "asset_id": "engine_id",
            "t": "cycle",
            "anomaly_score_smoothed": "anomaly_score",
            "alpha_high_used": "alpha_anomaly_used",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        if "anomaly_score" not in df.columns and "anomaly_score_raw" in df.columns:
            df["anomaly_score"] = df["anomaly_score_raw"]

    # Backward-compat: exports may not carry dataset_id/split columns.
    dataset_match = RE_DECISION_SUPPORT.match(p.name)
    inferred_dataset = normalize_dataset_id(dataset_match.group("ds")) if dataset_match else "UNKNOWN"
    if "dataset_id" not in df.columns:
        df["dataset_id"] = inferred_dataset
    if "split" not in df.columns:
        df["split"] = "test"

    df["dataset_id"] = df["dataset_id"].astype("string").fillna(inferred_dataset).map(normalize_dataset_id)
    df["split"] = df["split"].astype("string").fillna("test")
    df.loc[df["split"].str.strip() == "", "split"] = "test"
    if "engine_id" in df.columns:
        df["engine_id"] = pd.to_numeric(df["engine_id"], errors="coerce").astype("Int64")
    if "cycle" in df.columns:
        df["cycle"] = pd.to_numeric(df["cycle"], errors="coerce").astype("Int64")
    for col in ["rul_pred", "anomaly_score", "theta_rul_used", "alpha_anomaly_used"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def available_dataset_ids(datasets: Dict[str, DatasetFiles]) -> List[str]:
    return sorted(datasets.keys())


def decision_segments(df_engine: pd.DataFrame) -> List[Tuple[int, int, str]]:
    if df_engine.empty:
        return []

    df_sorted = df_engine.sort_values("cycle", kind="mergesort").reset_index(drop=True)
    labels = df_sorted["decision_label"].astype("string").fillna("UNKNOWN").tolist()
    cycles = df_sorted["cycle"].astype(int).tolist()

    segments: List[Tuple[int, int, str]] = []
    start_cycle = cycles[0]
    current_label = labels[0]

    for i in range(1, len(cycles)):
        if labels[i] != current_label:
            end_cycle = cycles[i - 1]
            segments.append((start_cycle, end_cycle, current_label))
            start_cycle = cycles[i]
            current_label = labels[i]

    segments.append((start_cycle, cycles[-1], current_label))
    return segments


def parse_reason_codes(value: object) -> List[str]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    s = str(value).strip()
    if not s:
        return []
    return [part.strip() for part in s.split("|") if part.strip()]


def format_quantiles(series: pd.Series) -> Dict[str, float]:
    x = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    if x.size == 0:
        return {"min": float("nan"), "p50": float("nan"), "p95": float("nan"), "max": float("nan")}
    return {
        "min": float(np.min(x)),
        "p50": float(np.quantile(x, 0.50)),
        "p95": float(np.quantile(x, 0.95)),
        "max": float(np.max(x)),
    }


def _single_value_or_nan(series: pd.Series) -> float:
    vals = pd.to_numeric(series, errors="coerce").dropna().unique()
    if len(vals) == 0:
        return float("nan")
    if len(vals) == 1:
        return float(vals[0])
    return float(np.median(vals))


def get_current_row(
    df_engine: pd.DataFrame,
    selected_cycle: int,
    default_max: bool = True,
) -> Tuple[Optional[pd.Series], Optional[str]]:
    if df_engine.empty:
        return None, "MISSING: engine data is empty"
    if "cycle" not in df_engine.columns:
        return None, "MISSING: cycle column not found"

    dfp = df_engine.dropna(subset=["cycle"]).copy()
    if dfp.empty:
        return None, "MISSING: no valid cycle values"
    dfp["cycle"] = pd.to_numeric(dfp["cycle"], errors="coerce").astype("Int64")

    exact = dfp[dfp["cycle"] == int(selected_cycle)]
    if not exact.empty:
        return exact.iloc[0], None

    if default_max:
        row = dfp.loc[dfp["cycle"].idxmax()]
        return row, f"INFO: selected cycle {selected_cycle} not found; using max cycle {int(row['cycle'])}"

    # fallback: closest cycle
    dfp["delta"] = (dfp["cycle"].astype(int) - int(selected_cycle)).abs()
    row = dfp.loc[dfp["delta"].idxmin()]
    return row, f"INFO: selected cycle {selected_cycle} not found; using closest cycle {int(row['cycle'])}"


def derive_action_and_driver(row: pd.Series) -> Dict[str, object]:
    decision_label = str(row.get("decision_label", "UNKNOWN"))
    reason_codes = parse_reason_codes(row.get("reason_codes", ""))
    reason_set = set(reason_codes)

    # recommended_action mapping (MVP)
    if decision_label == "Normal Operation":
        recommended_action = "Monitor"
    elif decision_label == "Enhanced Monitoring":
        recommended_action = "Plan Inspection"
    elif decision_label == "Planned Maintenance":
        recommended_action = "Plan Maintenance"
    elif decision_label == "Immediate Maintenance":
        recommended_action = "Immediate Maintenance"
    else:
        recommended_action = "Review"

    # Primary risk driver (heuristic, robust to v1 tokens)
    rul_risk = ("RUL_LOW" in reason_set) or ("RUL_CRIT" in reason_set) or ("RUL_CRITICAL" in reason_set)
    anom_risk = "ANOM_HIGH" in reason_set
    if rul_risk and anom_risk:
        primary_driver = "BOTH"
    elif rul_risk:
        primary_driver = "RUL"
    elif anom_risk:
        primary_driver = "ANOMALY"
    else:
        primary_driver = "NONE"

    # Confidence heuristic
    if primary_driver == "BOTH":
        confidence = "High"
    elif primary_driver in {"RUL", "ANOMALY"}:
        confidence = "Medium"
    else:
        confidence = "Low"

    # Risk score (0-100)
    risk_score = None
    if "risk_score" in row.index and row.get("risk_score", None) is not None:
        try:
            risk_score = float(row.get("risk_score"))
        except Exception:
            risk_score = None
    if risk_score is None:
        base = 0
        if decision_label == "Immediate Maintenance":
            base += 60
        elif decision_label == "Planned Maintenance":
            base += 45
        elif decision_label == "Enhanced Monitoring":
            base += 30
        if "ANOM_HIGH" in reason_set:
            base += 10
        if ("RUL_LOW" in reason_set) or ("RUL_CRIT" in reason_set) or ("RUL_CRITICAL" in reason_set):
            base += 10
        risk_score = float(max(0, min(100, base)))

    # Short why
    short_why = None
    try:
        short_why = build_short_why(
            decision_label=decision_label,
            rul_pred=float(row.get("rul_pred", float("nan"))),
            anomaly_score=float(row.get("anomaly_score", float("nan"))),
            theta_rul_used=float(row.get("theta_rul_used", float("nan"))),
            alpha_anomaly_used=float(row.get("alpha_anomaly_used", float("nan"))),
        )
    except Exception:
        short_why = f"decision_label={decision_label}"

    return {
        "decision_label": decision_label,
        "recommended_action": recommended_action,
        "primary_driver": primary_driver,
        "risk_score": risk_score,
        "confidence": confidence,
        "short_why": short_why,
        "reason_codes": reason_codes,
    }


def compute_alarm_kpis(
    df_scope: pd.DataFrame,
    window_n: int,
    end_cycle: Optional[int] = None,
) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    if df_scope.empty:
        return None, None, "MISSING: empty input"
    if "decision_label" not in df_scope.columns:
        return None, None, "MISSING: decision_label not found"
    dfp = df_scope.copy()
    if "cycle" in dfp.columns and end_cycle is not None:
        dfp = dfp[pd.to_numeric(dfp["cycle"], errors="coerce") <= int(end_cycle)]
        dfp = dfp.sort_values("cycle", kind="mergesort")
    if window_n is not None and window_n > 0 and len(dfp) > window_n:
        dfp = dfp.tail(int(window_n))

    total = int(len(dfp))
    if total == 0:
        return float("nan"), float("nan"), "MISSING: no rows in window"
    labels = dfp["decision_label"].astype(str)
    enhanced = int((labels == "Enhanced Monitoring").sum())
    immediate = int((labels == "Immediate Maintenance").sum())
    alarm_rate = (enhanced + immediate) / total
    immediate_rate = immediate / total
    return float(alarm_rate), float(immediate_rate), None


def compute_transitions(df_engine: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[str]]:
    if df_engine.empty:
        return pd.DataFrame(), "MISSING: empty engine data"
    if "cycle" not in df_engine.columns or "decision_label" not in df_engine.columns:
        return pd.DataFrame(), "MISSING: cycle/decision_label not found"

    dfp = df_engine.dropna(subset=["cycle"]).copy()
    dfp["cycle"] = pd.to_numeric(dfp["cycle"], errors="coerce").astype(int)
    dfp["decision_label"] = dfp["decision_label"].astype(str).fillna("UNKNOWN")
    dfp = dfp.sort_values("cycle", kind="mergesort")

    prev = dfp["decision_label"].shift(1)
    changed = dfp[prev.notna() & (dfp["decision_label"] != prev)].copy()
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


def compute_trend(
    df_engine: pd.DataFrame,
    window_n: int = 30,
    end_cycle: Optional[int] = None,
) -> Tuple[Optional[Dict[str, float]], Optional[str]]:
    if df_engine.empty:
        return None, "MISSING: empty engine data"
    if "cycle" not in df_engine.columns:
        return None, "MISSING: cycle not found"
    if "rul_pred" not in df_engine.columns or "anomaly_score" not in df_engine.columns:
        return None, "MISSING: rul_pred/anomaly_score not found"

    dfp = df_engine.copy()
    dfp["cycle"] = pd.to_numeric(dfp["cycle"], errors="coerce")
    dfp["rul_pred"] = pd.to_numeric(dfp["rul_pred"], errors="coerce")
    dfp["anomaly_score"] = pd.to_numeric(dfp["anomaly_score"], errors="coerce")
    dfp = dfp.dropna(subset=["cycle", "rul_pred", "anomaly_score"])
    if end_cycle is not None:
        dfp = dfp[dfp["cycle"] <= int(end_cycle)]
    dfp = dfp.sort_values("cycle", kind="mergesort")
    if dfp.empty:
        return None, "MISSING: no valid rows for trend"
    if window_n is not None and window_n > 0 and len(dfp) > window_n:
        dfp = dfp.tail(int(window_n))

    x = dfp["cycle"].to_numpy(dtype=float)
    y_rul = dfp["rul_pred"].to_numpy(dtype=float)
    y_anom = dfp["anomaly_score"].to_numpy(dtype=float)
    if len(x) < 2:
        return None, "MISSING: need >=2 points for trend"

    rul_slope = float(np.polyfit(x, y_rul, 1)[0])
    anom_slope = float(np.polyfit(x, y_anom, 1)[0])
    return {"rul_slope": rul_slope, "anomaly_slope": anom_slope}, None


def compute_kpis(df_ds: pd.DataFrame) -> Dict[str, float]:
    total = int(len(df_ds))
    if total == 0:
        return {"alarm_rate": float("nan"), "immediate_rate": float("nan")}
    label = df_ds["decision_label"].fillna("UNKNOWN")
    enhanced = int((label == "Enhanced Monitoring").sum())
    immediate = int((label == "Immediate Maintenance").sum())
    alarm_rate = (enhanced + immediate) / total
    immediate_rate = immediate / total
    return {"alarm_rate": float(alarm_rate), "immediate_rate": float(immediate_rate)}


def render_label_legend() -> None:
    rows = []
    for label, rgba in LABEL_COLORS.items():
        rows.append(
            f"<span style='display:inline-flex;align-items:center;margin-right:10px;'>"
            f"<span style='width:12px;height:12px;border-radius:2px;background:{rgba};"
            f"border:1px solid rgba(0,0,0,0.15);display:inline-block;margin-right:6px;'></span>"
            f"<span style='font-size:12px;'>{label}</span>"
            f"</span>"
        )
    st.markdown(
        "<div style='padding:8px 10px;border:1px solid rgba(0,0,0,0.08);border-radius:8px;background:rgba(0,0,0,0.02);'>"
        + "".join(rows)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_file_status_table(outdir: Path, dataset_id: str, files: Optional[DatasetFiles]) -> None:
    rows = []
    if files is None:
        expected = expected_paths_for_dataset(outdir, dataset_id)
        for name, path in expected.items():
            rows.append(
                {
                    "file": name,
                    "status": "MISSING",
                    "path": _safe_relpath(path),
                }
            )
    else:
        discovered = {
            "decision_support.csv": files.decision_support_csv,
            "anomaly_scores.csv": files.anomaly_scores_csv,
            "rul_predictions.csv": files.rul_predictions_csv,
        }
        for name, path in discovered.items():
            rows.append(
                {
                    "file": name,
                    "status": "FOUND" if path else "MISSING",
                    "path": _safe_relpath(path) if path else "Not provided",
                }
            )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def build_short_why(
    decision_label: str,
    rul_pred: float,
    anomaly_score: float,
    theta_rul_used: float,
    alpha_anomaly_used: float,
) -> str:
    rul_cmp = ">" if rul_pred > theta_rul_used else "≤"
    anom_cmp = "<" if anomaly_score < alpha_anomaly_used else "≥"
    return (
        f"RUL={rul_pred:.3f} {rul_cmp} θ={theta_rul_used:.3f} ve anomaly={anomaly_score:.3f} {anom_cmp} α={alpha_anomaly_used:.3f}"
        f" → {decision_label}"
    )


def build_timeline_figure(
    df_engine: pd.DataFrame,
    title: str,
    selected_cycle: int,
    theta_rul_used: float,
    alpha_anomaly_used: float,
) -> go.Figure:
    df_engine = df_engine.sort_values("cycle", kind="mergesort")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_engine["cycle"],
            y=df_engine["rul_pred"],
            mode="lines",
            name="rul_pred",
            line=dict(width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_engine["cycle"],
            y=df_engine["anomaly_score"],
            mode="lines",
            name="anomaly_score",
            yaxis="y2",
            line=dict(width=2),
        )
    )

    for start_cycle, end_cycle, label in decision_segments(df_engine):
        color = LABEL_COLORS.get(label, "rgba(149, 165, 166, 0.10)")
        fig.add_vrect(
            x0=start_cycle - 0.5,
            x1=end_cycle + 0.5,
            fillcolor=color,
            opacity=1.0,
            layer="below",
            line_width=0,
        )

    if not math.isnan(theta_rul_used):
        fig.add_shape(
            type="line",
            x0=0,
            x1=1,
            xref="paper",
            y0=theta_rul_used,
            y1=theta_rul_used,
            yref="y",
            line=dict(color="rgba(52, 73, 94, 0.9)", width=1, dash="dash"),
        )
        fig.add_annotation(
            x=0.0,
            xref="paper",
            y=theta_rul_used,
            yref="y",
            text=f"θ_RUL={theta_rul_used:.3f}",
            showarrow=False,
            xanchor="left",
            yanchor="bottom",
            font=dict(color="rgba(52, 73, 94, 0.95)", size=11),
            bgcolor="rgba(255,255,255,0.7)",
        )

    if not math.isnan(alpha_anomaly_used):
        fig.add_shape(
            type="line",
            x0=0,
            x1=1,
            xref="paper",
            y0=alpha_anomaly_used,
            y1=alpha_anomaly_used,
            yref="y2",
            line=dict(color="rgba(155, 89, 182, 0.9)", width=1, dash="dash"),
        )
        fig.add_annotation(
            x=1.0,
            xref="paper",
            y=alpha_anomaly_used,
            yref="y2",
            text=f"α_anomaly={alpha_anomaly_used:.3f}",
            showarrow=False,
            xanchor="right",
            yanchor="bottom",
            font=dict(color="rgba(155, 89, 182, 0.95)", size=11),
            bgcolor="rgba(255,255,255,0.7)",
        )

    fig.add_vline(
        x=selected_cycle,
        line=dict(color="rgba(0,0,0,0.5)", width=1, dash="dot"),
        annotation_text=f"cycle={selected_cycle}",
        annotation_position="bottom",
    )

    row = df_engine[df_engine["cycle"] == selected_cycle]
    if not row.empty:
        r = row.iloc[0]
        label = str(r.get("decision_label", "UNKNOWN"))
        marker_color = LABEL_MARKER_COLORS.get(label, "rgba(149, 165, 166, 0.90)")
        fig.add_trace(
            go.Scatter(
                x=[selected_cycle],
                y=[float(r["rul_pred"])],
                mode="markers",
                name="Selected cycle",
                marker=dict(size=10, color=marker_color, line=dict(width=1, color="rgba(0,0,0,0.25)")),
            )
        )

    fig.update_layout(
        title=title,
        xaxis=dict(title="cycle"),
        yaxis=dict(title="rul_pred"),
        yaxis2=dict(
            title="anomaly_score",
            overlaying="y",
            side="right",
            range=[0.0, 1.0],
        ),
        legend=dict(orientation="h"),
        margin=dict(l=40, r=40, t=50, b=40),
        height=520,
    )
    return fig


def render_twin_current_health(
    current_row: Optional[pd.Series],
    info_msg: Optional[str],
) -> None:
    st.markdown("### Digital Twin — Current Health")
    st.info(
        "MVP’de dijital ikiz, cycle zaman ekseninde RUL + anomaly sinyallerini tek kaynak policy ile birleştirerek "
        "anlık health state ve operasyonel aksiyon önerisi üretir. Phase-2’de aynı arayüz gerçek telemetri akışına bağlanacaktır."
    )

    if current_row is None:
        st.warning(info_msg or "MISSING: current row not available")
        return
    if info_msg:
        st.caption(info_msg)

    derived = derive_action_and_driver(current_row)
    c1, c2, c3, c4, c5 = st.columns([0.22, 0.22, 0.18, 0.18, 0.20])
    c1.metric("Current decision_label", str(derived["decision_label"]))
    c2.metric("Recommended action", str(derived["recommended_action"]))
    c3.metric("Primary driver", str(derived["primary_driver"]))
    c4.metric("Risk score", f"{float(derived['risk_score']):.0f}/100")
    c5.metric("Confidence", str(derived["confidence"]))

    st.caption(str(derived["short_why"]))


def render_ask_the_twin(
    df_engine: pd.DataFrame,
    current_row: Optional[pd.Series],
    selected_cycle: int,
) -> None:
    st.markdown("### Ask the Twin")
    q = st.selectbox(
        "Preset sorgular",
        options=[
            "Şu anki health state nedir?",
            "Bu karara en çok ne sebep oldu?",
            "Son 50 cycle içinde alarm yoğunluğu nedir?",
            "Karar ne zaman değişti? (transition points)",
            "Önümüzdeki 30 cycle trendi risk artışı gösteriyor mu?",
        ],
        index=0,
    )

    if current_row is None:
        st.warning("MISSING: current row")
        return

    derived = derive_action_and_driver(current_row)

    if q == "Şu anki health state nedir?":
        st.success(f"{derived['decision_label']} → {derived['recommended_action']} | confidence={derived['confidence']}")
        st.caption(str(derived["short_why"]))
        return

    if q == "Bu karara en çok ne sebep oldu?":
        reasons = derived.get("reason_codes", [])
        st.info(f"Primary driver: {derived['primary_driver']}")
        st.caption("Top signals: " + (", ".join(reasons[:5]) if reasons else "MISSING"))
        st.caption(str(derived["short_why"]))
        return

    if q == "Son 50 cycle içinde alarm yoğunluğu nedir?":
        alarm_rate, imm_rate, err = compute_alarm_kpis(df_engine, window_n=50, end_cycle=selected_cycle)
        if err:
            st.warning(err)
        else:
            st.metric("Alarm Rate (last 50)", f"{alarm_rate*100:.2f}%")
            st.metric("Immediate Rate (last 50)", f"{imm_rate*100:.2f}%")
        return

    if q == "Karar ne zaman değişti? (transition points)":
        trans, err = compute_transitions(df_engine)
        if err:
            st.warning(err)
            return
        if trans.empty:
            st.info("No transitions found.")
            return
        st.dataframe(trans.tail(10), use_container_width=True, hide_index=True)
        return

    if q == "Önümüzdeki 30 cycle trendi risk artışı gösteriyor mu?":
        trend, err = compute_trend(df_engine, window_n=30, end_cycle=selected_cycle)
        if err:
            st.warning(err)
            return
        rul_slope = float(trend["rul_slope"])
        anom_slope = float(trend["anomaly_slope"])
        eps = 1e-6
        rul_bad = rul_slope < -eps
        anom_bad = anom_slope > eps
        if rul_bad and anom_bad:
            verdict = "Risk increasing"
        elif (not rul_bad) and (not anom_bad):
            verdict = "Risk stable/decreasing"
        else:
            verdict = "Mixed signals"
        st.success(verdict)
        st.caption(f"rul_slope={rul_slope:.6f} (negative=decreasing RUL), anomaly_slope={anom_slope:.6f} (positive=increasing anomaly)")
        return


def render_transitions_summary(
    df_engine: pd.DataFrame,
    df_ds: pd.DataFrame,
    selected_cycle: int,
) -> None:
    st.markdown("### Timeline Transitions & Summary")

    trans, err = compute_transitions(df_engine)
    if err:
        st.warning(err)
    elif trans.empty:
        st.info("No transitions found.")
    else:
        st.markdown("**Transition points (max 10)**")
        st.dataframe(trans.tail(10), use_container_width=True, hide_index=True)

    st.markdown("**Top-3 reason_codes (engine)**")
    if "reason_codes" in df_engine.columns:
        all_codes: List[str] = []
        for v in df_engine["reason_codes"].tolist():
            all_codes.extend(parse_reason_codes(v))
        if all_codes:
            vc = pd.Series(all_codes).value_counts().head(3).reset_index()
            vc.columns = ["reason_code", "count"]
            st.dataframe(vc, use_container_width=True, hide_index=True)
        else:
            st.info("MISSING: reason_codes empty.")
    else:
        st.info("MISSING: reason_codes column not found.")

    st.markdown("**Alarm KPIs scope**")
    scope = st.selectbox("KPI scope", options=["engine", "dataset+split"], index=0)
    if scope == "engine":
        df_scope = df_engine
    else:
        df_scope = df_ds
    alarm_rate, imm_rate, err = compute_alarm_kpis(df_scope, window_n=0, end_cycle=selected_cycle)
    if err:
        st.warning(err)
    else:
        k1, k2 = st.columns(2)
        k1.metric("Alarm Rate", f"{alarm_rate*100:.2f}%")
        k2.metric("Immediate Rate", f"{imm_rate*100:.2f}%")


def main() -> None:
    st.set_page_config(page_title="AeroTrace Decision Support Dashboard", layout="wide")

    st.title("AeroTrace Decision Support Dashboard")
    default_outdir = resolve_default_outputs_dir()

    with st.sidebar:
        st.header("Seçimler")
        outdir = Path(
            st.text_input(
                "Outputs Root",
                value=str(default_outdir),
                help="Decision-support CSV klasörü (ör. demo/decision_support_v2_outputs).",
            )
        ).expanduser()

        datasets = discover_datasets(str(outdir))
        dataset_options = available_dataset_ids(datasets)
        ds = st.selectbox("Dataset", options=dataset_options) if dataset_options else None

        st.markdown("**Dosya Durumu (seçili dataset)**")
        render_file_status_table(outdir, ds or "UNKNOWN", datasets.get(ds) if ds else None)

    st.caption(
        f"Bu uygulama sadece `{_safe_relpath(outdir)}` altındaki CSV/JSON artefact’larını okur; eğitim/yeniden üretim yapmaz."
    )

    if not outdir.exists():
        st.error(
            f"Output klasörü bulunamadı: `{_safe_relpath(outdir)}`\n\n"
            "Beklenen dosyalar (örnek):\n"
            f"- `{_safe_relpath(outdir / 'fd001_decision_support_v2.csv')}`\n"
            f"- `{_safe_relpath(outdir / 'ncmapss_DS01_decision_support_v2.csv')}`"
        )
        st.stop()

    if not datasets or ds is None:
        st.error(
            "Seçilebilir dataset bulunamadı.\n"
            f"- Klasör: `{_safe_relpath(outdir)}`\n"
            "- Beklenen adlandırma: `fd001_decision_support_v2.csv`, `ncmapss_DS01_decision_support_v2.csv` veya benzeri"
        )
        st.stop()

    files = datasets.get(ds)
    if files is None or not files.decision_support_csv.exists():
        st.error(
            "Seçili dataset için decision-support CSV bulunamadı.\n"
            f"- Beklenen: `{ds}` için bir decision-support CSV"
        )
        st.stop()

    df = load_decision_support(str(files.decision_support_csv))
    missing = _required_missing_columns(df, CANONICAL_DECISION_SUPPORT_COLS)
    if missing:
        st.error(
            "Decision-support CSV beklenen şemayı karşılamıyor.\n"
            f"- Dosya: `{_safe_relpath(files.decision_support_csv)}`\n"
            f"- Eksik kolonlar: {', '.join(missing)}\n"
            f"- Mevcut kolonlar: {', '.join(map(str, df.columns))}"
        )
        st.stop()

    df["dataset_id"] = df["dataset_id"].astype("string")
    df["split"] = df["split"].astype("string")

    splits = sorted([s for s in df["split"].dropna().unique().tolist() if str(s).strip()])
    default_split_idx = splits.index("test") if "test" in splits else 0

    col_left, col_right = st.columns([0.55, 0.45], gap="large")

    with col_left:
        st.subheader("Timeline")
        split = st.selectbox("Split", options=splits, index=default_split_idx)
        df_ds = df[(df["dataset_id"] == ds) & (df["split"] == split)].copy()

        if df_ds.empty:
            st.warning(f"Seçimde veri yok: dataset_id={ds}, split={split}")
            st.stop()

        engines = sorted(df_ds["engine_id"].dropna().unique().tolist())
        engine_id = st.selectbox("Engine", options=engines, index=0)

        df_engine = df_ds[df_ds["engine_id"] == engine_id].copy()
        df_engine = df_engine.sort_values("cycle", kind="mergesort")
        if df_engine.empty:
            st.warning("Seçili engine için veri yok.")
            st.stop()

        cycle_min = int(df_engine["cycle"].min())
        cycle_max = int(df_engine["cycle"].max())
        live_mode = st.toggle("Live Mode (simulate)", value=bool(st.session_state.get("live_mode_enabled", False)))
        st.session_state["live_mode_enabled"] = bool(live_mode)

        cycle_key = "cycle_slider"
        default_cycle = int(st.session_state.get("live_cycle", cycle_max)) if live_mode else cycle_max
        default_cycle = int(min(max(default_cycle, cycle_min), cycle_max))
        if live_mode:
            st.session_state[cycle_key] = default_cycle
        elif cycle_key not in st.session_state:
            st.session_state[cycle_key] = default_cycle

        selected_cycle = st.slider(
            "Cycle (Why? paneli için)",
            min_value=cycle_min,
            max_value=cycle_max,
            key=cycle_key,
        )
        if live_mode:
            st.session_state["live_cycle"] = int(selected_cycle)
            if int(selected_cycle) < int(cycle_max):
                time.sleep(1.0)
                st.session_state["live_cycle"] = int(selected_cycle) + 1
                st.session_state[cycle_key] = int(selected_cycle) + 1
                try:
                    st.rerun()
                except Exception:
                    st.experimental_rerun()

        theta_rul_used = _single_value_or_nan(df_ds["theta_rul_used"])
        alpha_anomaly_used = _single_value_or_nan(df_ds["alpha_anomaly_used"])
        if df_ds["theta_rul_used"].dropna().nunique() > 1 or df_ds["alpha_anomaly_used"].dropna().nunique() > 1:
            st.warning(
                "Eşik değerleri dataset+split içinde tekil değil (birden fazla değer bulundu). "
                "Grafikte medyan değer çiziliyor."
            )

        title = f"{ds} / {split} / engine_id={engine_id}"
        fig = build_timeline_figure(
            df_engine,
            title=title,
            selected_cycle=int(selected_cycle),
            theta_rul_used=float(theta_rul_used),
            alpha_anomaly_used=float(alpha_anomaly_used),
        )
        st.plotly_chart(fig, use_container_width=True)

        render_label_legend()

    with col_right:
        current_row, current_row_info = get_current_row(df_engine, int(selected_cycle), default_max=True)
        render_twin_current_health(current_row=current_row, info_msg=current_row_info)

        st.subheader("Why?")
        mode_detail = st.toggle("Detay (açık) / Kısa (kapalı)", value=True)
        row = df_engine[df_engine["cycle"] == selected_cycle]
        if row.empty:
            st.warning("Seçili cycle satırı bulunamadı (cycle filtrelemesi sonrası).")
        else:
            r = row.iloc[0]
            st.markdown(f"**Seçili satır**: `dataset_id={ds}`, `split={split}`, `engine_id={engine_id}`, `cycle={selected_cycle}`")
            if mode_detail:
                st.code(
                    "\n".join(
                        [
                            f"decision_label: {r['decision_label']}",
                            f"reason_codes: {r['reason_codes']}",
                            f"reason_text: {r['reason_text']}",
                            f"theta_rul_used: {r['theta_rul_used']}",
                            f"alpha_anomaly_used: {r['alpha_anomaly_used']}",
                        ]
                    ),
                    language="text",
                )
            else:
                st.info(
                    build_short_why(
                        decision_label=str(r["decision_label"]),
                        rul_pred=float(r["rul_pred"]),
                        anomaly_score=float(r["anomaly_score"]),
                        theta_rul_used=float(r["theta_rul_used"]),
                        alpha_anomaly_used=float(r["alpha_anomaly_used"]),
                    )
                )

        st.markdown("**Top-5 reason_codes (seçili engine)**")
        all_codes: List[str] = []
        for v in df_engine["reason_codes"].tolist():
            all_codes.extend(parse_reason_codes(v))
        if not all_codes:
            st.info("reason_codes boş veya parse edilemedi.")
        else:
            vc = pd.Series(all_codes).value_counts().head(5).reset_index()
            vc.columns = ["reason_code", "count"]
            st.dataframe(vc, use_container_width=True, hide_index=True)

        st.subheader("Özet (dataset + split)")
        q_anom = format_quantiles(df_ds["anomaly_score"])
        q_rul = format_quantiles(df_ds["rul_pred"])
        kpis = compute_kpis(df_ds)
        n_rows = int(len(df_ds))

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Satır sayısı", f"{n_rows:,}")
        m2.metric("Alarm Rate", f"{kpis['alarm_rate']*100:.2f}%")
        m3.metric("Immediate Rate", f"{kpis['immediate_rate']*100:.2f}%")
        m4.metric("Anomali p50", f"{q_anom['p50']:.3f}")
        m5.metric("Anomali p95", f"{q_anom['p95']:.3f}")
        m6.metric("Anomali max", f"{q_anom['max']:.3f}")

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("RUL min", f"{q_rul['min']:.3f}")
        r2.metric("RUL p50", f"{q_rul['p50']:.3f}")
        r3.metric("RUL p95", f"{q_rul['p95']:.3f}")
        r4.metric("RUL max", f"{q_rul['max']:.3f}")

        st.markdown("**decision_label dağılımı (count)**")
        dist = df_ds["decision_label"].fillna("UNKNOWN").value_counts().reset_index()
        dist.columns = ["decision_label", "count"]
        st.dataframe(dist, use_container_width=True, hide_index=True)

        tabs = st.tabs(["Ask the Twin", "Transitions & Summary"])
        with tabs[0]:
            render_ask_the_twin(df_engine=df_engine, current_row=current_row, selected_cycle=int(selected_cycle))
        with tabs[1]:
            render_transitions_summary(df_engine=df_engine, df_ds=df_ds, selected_cycle=int(selected_cycle))

    st.divider()
    st.caption(
        "Build info: "
        + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        + f" | repo_root={repo_root()}"
    )


if __name__ == "__main__":
    main()
