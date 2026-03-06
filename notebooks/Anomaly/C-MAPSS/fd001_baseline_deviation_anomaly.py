#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


ENGINE_ID_COL = "engine_id"
CYCLE_COL = "cycle"


def _read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    unnamed = [c for c in df.columns if str(c).lower().startswith("unnamed")]
    if unnamed:
        df = df.drop(columns=unnamed)
    return df


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _dump_json_list(val: Any) -> str:
    return json.dumps(val, ensure_ascii=False)


def _sigmoid(x: np.ndarray, k: float, c: float) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-k * (x - c)))


@dataclass(frozen=True)
class Mapping:
    mode: str
    params: Dict[str, float]


def _fit_mapping(raw_scores: np.ndarray, mode: str, sigmoid_k: float) -> Mapping:
    x = np.asarray(raw_scores, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        raise ValueError("No finite raw scores to fit mapping.")
    if mode == "minmax":
        return Mapping(mode="minmax", params={"min": float(x.min()), "max": float(x.max())})
    if mode == "sigmoid":
        return Mapping(mode="sigmoid", params={"k": float(sigmoid_k), "c": float(np.median(x))})
    raise ValueError("mode must be one of: sigmoid, minmax")


def _apply_mapping(raw_scores: np.ndarray, mapping: Mapping) -> np.ndarray:
    x = np.asarray(raw_scores, dtype=float)
    if mapping.mode == "minmax":
        mn = float(mapping.params["min"])
        mx = float(mapping.params["max"])
        denom = (mx - mn) if (mx - mn) != 0 else 1.0
        y = (x - mn) / denom
        return np.clip(y, 0.0, 1.0)
    if mapping.mode == "sigmoid":
        return _sigmoid(x, k=float(mapping.params["k"]), c=float(mapping.params["c"]))
    raise ValueError("Unknown mapping mode")


def _rolling_mean_per_engine(df: pd.DataFrame, col: str, window: int) -> pd.Series:
    if window is None or int(window) <= 1:
        return df[col]
    return (
        df.sort_values([ENGINE_ID_COL, CYCLE_COL], kind="mergesort")
        .groupby(ENGINE_ID_COL)[col]
        .transform(lambda s: s.rolling(window=int(window), min_periods=1).mean())
    )


def _sensor_cols_from_metrics(metrics_json_path: Optional[str], include_os: bool) -> Optional[List[str]]:
    if not metrics_json_path:
        return None
    p = Path(metrics_json_path)
    if not p.exists():
        return None
    obj = json.loads(p.read_text(encoding="utf-8"))
    feature_columns = None
    if isinstance(obj, dict) and "all_rows" in obj and isinstance(obj["all_rows"], dict) and "feature_columns" in obj["all_rows"]:
        feature_columns = obj["all_rows"]["feature_columns"]
    if feature_columns is None and isinstance(obj, dict) and "feature_columns" in obj:
        feature_columns = obj["feature_columns"]
    if not isinstance(feature_columns, list):
        return None
    cols = []
    for c in feature_columns:
        if not isinstance(c, str):
            continue
        if c.startswith("s"):
            cols.append(c)
        if include_os and c in ("os1", "os2", "os3"):
            cols.append(c)
    return cols or None


def _pick_sensor_cols_from_df(df: pd.DataFrame, include_os: bool) -> List[str]:
    cols = [c for c in df.columns if c.startswith("s")]
    if include_os:
        cols += [c for c in ["os1", "os2", "os3"] if c in df.columns]
    # keep only numeric
    cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    if not cols:
        raise ValueError("No sensor columns found (expected s1..s21).")
    return cols


def _compute_raw_and_topk(
    df: pd.DataFrame,
    sensor_cols: Sequence[str],
    baseline_n: int,
    eps: float,
    agg: str,
    topk: int,
) -> pd.DataFrame:
    df = df.sort_values([ENGINE_ID_COL, CYCLE_COL]).reset_index(drop=True)
    out_parts: List[pd.DataFrame] = []

    for eid, g in df.groupby(ENGINE_ID_COL, sort=True):
        g = g.sort_values(CYCLE_COL).copy()
        n0 = min(int(baseline_n), int(len(g)))
        base = g.head(n0)

        mu = base[list(sensor_cols)].mean(axis=0)
        sigma = base[list(sensor_cols)].std(axis=0, ddof=1).replace(0.0, np.nan).fillna(0.0) + float(eps)

        Z = (g[list(sensor_cols)] - mu) / sigma
        Zv = Z.to_numpy(dtype=float)

        if agg == "rms":
            raw = np.sqrt(np.mean(np.square(Zv), axis=1))
        elif agg == "meanabs":
            raw = np.mean(np.abs(Zv), axis=1)
        else:
            raise ValueError("agg must be one of: rms, meanabs")

        absZ = np.abs(Zv)
        k = min(int(topk), int(absZ.shape[1]))
        if k <= 0:
            top_idx = np.empty((len(g), 0), dtype=int)
        else:
            top_idx = np.argpartition(-absZ, kth=k - 1, axis=1)[:, :k]

        top_sensors: List[List[str]] = []
        top_vals: List[List[float]] = []
        for i in range(len(g)):
            idxs = top_idx[i]
            idxs = idxs[np.argsort(-absZ[i, idxs])] if len(idxs) else idxs
            top_sensors.append([str(sensor_cols[j]) for j in idxs])
            top_vals.append([float(absZ[i, j]) for j in idxs])

        part = pd.DataFrame(
            {
                ENGINE_ID_COL: g[ENGINE_ID_COL].to_numpy(dtype=int),
                CYCLE_COL: g[CYCLE_COL].to_numpy(dtype=int),
                "anomaly_raw": raw.astype(float),
                "top_sensors": [_dump_json_list(v) for v in top_sensors],
                "top_abs_z": [_dump_json_list(v) for v in top_vals],
            }
        )
        out_parts.append(part)

    return pd.concat(out_parts, ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="FD001 baseline-deviation anomaly score (engine baseline first N cycles, RMS z-score, 0-1 mapping)."
    )
    ap.add_argument(
        "--train",
        default="data/processed/CMAPSS_full_norm/FD001/train_FD001_full_norm.csv",
        help="Train sensor CSV (engine_id,cycle,os*,s*). Used for mapping fit if fit-mapping-on=train.",
    )
    ap.add_argument(
        "--test",
        default="data/processed/CMAPSS_full_norm/FD001/test_FD001_full_norm.csv",
        help="Test sensor CSV (engine_id,cycle,os*,s*). Used to produce decision-support anomaly.",
    )
    ap.add_argument(
        "--pred",
        default="notebooks/RUL/C-MAPSS/FD001/FD001_AllRaws/predictions_cycle_all_rows.csv",
        help="Optional: predictions CSV to validate key alignment and to create a joined artefact.",
    )
    ap.add_argument(
        "--metrics-json",
        default="notebooks/RUL/C-MAPSS/FD001/FD001_AllRaws/metrics_cycle_all_rows.json",
        help="Optional: metrics JSON to enforce sensor set from pipeline feature_columns.",
    )
    ap.add_argument(
        "--out",
        default="notebooks/Anomaly/jet-cube-turbofan-mvp/outputs/fd001_anomaly_scores.csv",
        help="Output anomaly CSV (engine_id,cycle,anomaly_score + optional columns).",
    )
    ap.add_argument(
        "--out-join",
        default="notebooks/Anomaly/jet-cube-turbofan-mvp/outputs/fd001_test_with_preds_and_anomaly.csv",
        help="Optional joined CSV (preds + anomaly fields).",
    )
    ap.add_argument(
        "--out-mapping",
        default="notebooks/Anomaly/jet-cube-turbofan-mvp/outputs/fd001_anomaly_mapping_params.json",
        help="Mapping params JSON (reproducibility).",
    )
    ap.add_argument("--baseline-n", type=int, default=20)
    ap.add_argument("--eps", type=float, default=1e-6)
    ap.add_argument("--include-os", action="store_true", help="Include os1..os3 in anomaly computation.")
    ap.add_argument("--agg", choices=["rms", "meanabs"], default="rms")
    ap.add_argument("--topk", type=int, default=3)
    ap.add_argument("--mapping", choices=["sigmoid", "minmax"], default="sigmoid")
    ap.add_argument("--sigmoid-k", type=float, default=1.0)
    ap.add_argument("--fit-mapping-on", choices=["train", "all"], default="train")
    ap.add_argument("--smooth-window", type=int, default=5)
    ap.add_argument("--export-score-col", choices=["anomaly_score", "anomaly_score_smoothed"], default="anomaly_score")
    ap.add_argument("--minimal", action="store_true", help="Write only engine_id,cycle,anomaly_score columns.")
    args = ap.parse_args()

    train_df = _read_csv(args.train)
    test_df = _read_csv(args.test)

    for name, df in [("train", train_df), ("test", test_df)]:
        miss = [c for c in [ENGINE_ID_COL, CYCLE_COL] if c not in df.columns]
        if miss:
            raise ValueError(f"{name} missing required columns {miss}")

    # Sensor set: prefer metrics.json (pipeline feature_columns), fallback to df columns
    sensor_cols = _sensor_cols_from_metrics(args.metrics_json, include_os=bool(args.include_os))
    if sensor_cols is None:
        sensor_cols = _pick_sensor_cols_from_df(train_df, include_os=bool(args.include_os))

    missing_in_test = [c for c in sensor_cols if c not in test_df.columns]
    missing_in_train = [c for c in sensor_cols if c not in train_df.columns]
    if missing_in_train or missing_in_test:
        raise ValueError(
            f"Sensor set columns missing. missing_in_train={missing_in_train[:10]} missing_in_test={missing_in_test[:10]}"
        )

    train_scores = _compute_raw_and_topk(
        train_df, sensor_cols=sensor_cols, baseline_n=args.baseline_n, eps=args.eps, agg=args.agg, topk=args.topk
    )
    test_scores = _compute_raw_and_topk(
        test_df, sensor_cols=sensor_cols, baseline_n=args.baseline_n, eps=args.eps, agg=args.agg, topk=args.topk
    )

    raw_fit = (
        np.concatenate([train_scores["anomaly_raw"].to_numpy(), test_scores["anomaly_raw"].to_numpy()])
        if args.fit_mapping_on == "all"
        else train_scores["anomaly_raw"].to_numpy()
    )
    mapping = _fit_mapping(raw_fit, mode=str(args.mapping), sigmoid_k=float(args.sigmoid_k))
    train_scores["anomaly_score"] = _apply_mapping(train_scores["anomaly_raw"].to_numpy(), mapping)
    test_scores["anomaly_score"] = _apply_mapping(test_scores["anomaly_raw"].to_numpy(), mapping)

    train_scores["anomaly_score_smoothed"] = _rolling_mean_per_engine(train_scores, "anomaly_score", args.smooth_window)
    test_scores["anomaly_score_smoothed"] = _rolling_mean_per_engine(test_scores, "anomaly_score", args.smooth_window)

    export_col = str(args.export_score_col)
    if export_col not in test_scores.columns:
        raise ValueError(f"--export-score-col={export_col} not found in computed scores.")

    # Contract output (for decision-support): engine_id, cycle, anomaly_score
    out_df = test_scores[[ENGINE_ID_COL, CYCLE_COL]].copy()
    out_df["anomaly_score"] = test_scores[export_col].astype(float).clip(0.0, 1.0)

    if not args.minimal:
        out_df["anomaly_raw"] = test_scores["anomaly_raw"].astype(float)
        out_df["anomaly_score_unsmoothed"] = test_scores["anomaly_score"].astype(float)
        out_df["anomaly_score_smoothed"] = test_scores["anomaly_score_smoothed"].astype(float)
        out_df["top_sensors"] = test_scores["top_sensors"]
        out_df["top_abs_z"] = test_scores["top_abs_z"]

    # No dupes
    if out_df.duplicated([ENGINE_ID_COL, CYCLE_COL]).any():
        raise RuntimeError("Duplicate (engine_id,cycle) rows in output. Check inputs.")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.sort_values([ENGINE_ID_COL, CYCLE_COL]).to_csv(out_path, index=False)

    # Save mapping params + config for traceability
    mapping_obj = {
        "method": "baseline_deviation_rms_zscore",
        "baseline_n": int(args.baseline_n),
        "eps": float(args.eps),
        "agg": str(args.agg),
        "topk": int(args.topk),
        "include_os": bool(args.include_os),
        "sensor_columns": list(sensor_cols),
        "mapping": {"mode": mapping.mode, **mapping.params},
        "fit_mapping_on": str(args.fit_mapping_on),
        "smooth_window": int(args.smooth_window),
        "export_score_col": export_col,
        "input_paths": {"train": str(args.train), "test": str(args.test), "pred": str(args.pred), "metrics_json": str(args.metrics_json)},
        "output_paths": {"anomaly_scores": str(out_path)},
    }
    _write_json(Path(args.out_mapping), mapping_obj)

    # Optional join with predictions (ensures decision-support keys align)
    pred_path = Path(args.pred)
    if pred_path.exists() and args.out_join:
        preds = _read_csv(str(pred_path))
        need = [ENGINE_ID_COL, CYCLE_COL]
        miss = [c for c in need if c not in preds.columns]
        if miss:
            raise ValueError(f"predictions missing required columns {miss}")
        merged = preds.merge(out_df, on=[ENGINE_ID_COL, CYCLE_COL], how="left", validate="one_to_one")
        miss_rate = float(merged["anomaly_score"].isna().mean())
        if miss_rate > 0:
            raise RuntimeError(f"Join produced missing anomaly_score: {miss_rate:.2%}. Check alignment.")
        out_join = Path(args.out_join)
        out_join.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(out_join, index=False)

    print(f"[OK] wrote anomaly scores: {out_path}")
    print(f"[OK] wrote mapping params: {args.out_mapping}")
    if pred_path.exists() and args.out_join:
        print(f"[OK] wrote joined preds+anomaly: {args.out_join}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

