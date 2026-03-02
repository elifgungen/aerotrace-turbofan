#!/usr/bin/env python3
"""Leakage-safe AutoGluon RUL training script for N-CMAPSS DS01/DS02/DS03."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from autogluon.tabular import TabularPredictor
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "AutoGluon is required. Install with: pip install autogluon.tabular"
    ) from exc


VALID_DATASETS = ("DS01", "DS02", "DS03", "DS04")
TARGET_COL = "RUL"
ENGINE_COL = "engine_id"
CYCLE_COL = "cycle"
META_COLS = {"dataset_id", "split"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train AutoGluon Tabular model for N-CMAPSS RUL."
    )
    parser.add_argument("--dataset", required=True, choices=VALID_DATASETS)
    parser.add_argument("--input_root", default="data/processed/N-CMAPSS")
    parser.add_argument("--output_root", default="data/outputs")
    parser.add_argument("--preset", default="high_quality")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--use_cycle", type=int, choices=[0, 1], default=1)
    parser.add_argument("--fe_mode", choices=["none", "light"], default="none")
    parser.add_argument("--time_limit", type=int, default=None)
    parser.add_argument("--use_scaler_features", type=int, choices=[0, 1], default=1)
    parser.add_argument("--val_engines", type=int, default=0)
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def json_default(obj: Any) -> Any:
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        return obj.to_dict()
    return str(obj)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, default=json_default)


def validate_split_schema(
    df: pd.DataFrame, split_name: str, require_target: bool = True
) -> None:
    required_cols = {ENGINE_COL, CYCLE_COL}
    if require_target:
        required_cols.add(TARGET_COL)
    missing = required_cols.difference(df.columns)
    if missing:
        raise ValueError(f"{split_name} missing required columns: {sorted(missing)}")

    if df[[ENGINE_COL, CYCLE_COL]].isna().any().any():
        raise ValueError(f"{split_name} contains null values in join keys")

    dup_count = int(df.duplicated(subset=[ENGINE_COL, CYCLE_COL]).sum())
    if dup_count > 0:
        raise ValueError(f"{split_name} has duplicated (engine_id, cycle) rows: {dup_count}")


def assert_no_engine_overlap(train_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    train_engines = set(train_df[ENGINE_COL].astype(str).unique())
    test_engines = set(test_df[ENGINE_COL].astype(str).unique())
    overlap = train_engines.intersection(test_engines)
    if overlap:
        sample = sorted(list(overlap))[:10]
        raise AssertionError(
            f"Engine-level leakage detected. Overlap count={len(overlap)}, sample={sample}"
        )


def load_scaler_feature_columns(scaler_path: Path) -> Optional[List[str]]:
    if not scaler_path.exists():
        return None
    try:
        with scaler_path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except Exception as exc:
        print(f"[WARN] Failed to read scaler file {scaler_path}: {exc}")
        return None

    feature_columns = payload.get("feature_columns")
    if not isinstance(feature_columns, list) or not feature_columns:
        return None

    return [str(col) for col in feature_columns]


def split_train_for_tuning(
    train_df: pd.DataFrame, val_engines: int, seed: int
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], int]:
    if val_engines <= 0:
        return train_df.copy(), None, 0

    unique_engines = np.asarray(sorted(train_df[ENGINE_COL].astype(str).unique()))
    n_engines = len(unique_engines)
    if n_engines < 2:
        print("[WARN] val_engines ignored: need at least 2 engines in train split.")
        return train_df.copy(), None, 0

    effective_val_engines = min(val_engines, n_engines - 1)
    if effective_val_engines <= 0:
        print("[WARN] val_engines ignored: not enough engines left for training.")
        return train_df.copy(), None, 0
    if effective_val_engines != val_engines:
        print(
            f"[WARN] val_engines={val_engines} reduced to {effective_val_engines} "
            f"to keep at least one train engine."
        )

    rng = np.random.RandomState(seed)
    val_engine_set = set(rng.choice(unique_engines, size=effective_val_engines, replace=False))
    val_df = train_df[train_df[ENGINE_COL].astype(str).isin(val_engine_set)].copy()
    train_part_df = train_df[~train_df[ENGINE_COL].astype(str).isin(val_engine_set)].copy()

    if val_df.empty or train_part_df.empty:
        print("[WARN] val_engines split produced empty partition, fallback to no tuning_data.")
        return train_df.copy(), None, 0

    return train_part_df, val_df, effective_val_engines


def build_base_feature_cols(
    train_df: pd.DataFrame,
    use_cycle: bool,
    preferred_feature_cols: Optional[List[str]] = None,
) -> List[str]:
    excluded_cols = {TARGET_COL, ENGINE_COL}.union(META_COLS)
    if preferred_feature_cols:
        missing_preferred = [c for c in preferred_feature_cols if c not in train_df.columns]
        if missing_preferred:
            print(
                f"[WARN] Ignoring {len(missing_preferred)} scaler features not present in data: "
                f"{missing_preferred[:5]}"
            )
        candidate_cols = [c for c in preferred_feature_cols if c in train_df.columns]
    else:
        candidate_cols = [c for c in train_df.columns if c not in excluded_cols]

    candidate_cols = [c for c in candidate_cols if c not in excluded_cols]
    feature_cols = [
        c for c in candidate_cols if pd.api.types.is_numeric_dtype(train_df[c])
    ]
    # Preserve ordering while deduplicating.
    feature_cols = list(dict.fromkeys(feature_cols))
    if not use_cycle and CYCLE_COL in feature_cols:
        feature_cols.remove(CYCLE_COL)

    if ENGINE_COL in feature_cols:
        raise AssertionError("engine_id must not be in features")
    if TARGET_COL in feature_cols:
        raise AssertionError("RUL must not be in features")
    if any(col in feature_cols for col in META_COLS):
        raise AssertionError("Meta columns must not be in features")
    if any(c.lower() == "rul" or c.lower().startswith("rul_") for c in feature_cols):
        raise AssertionError("Potential target leakage: RUL-like column detected in features")
    if not feature_cols:
        raise ValueError("No usable numeric features found after feature selection")

    return feature_cols


def build_fe_plan(train_df: pd.DataFrame, feature_cols: List[str], fe_mode: str) -> Dict[str, Any]:
    plan: Dict[str, Any] = {"fe_mode": fe_mode}
    if fe_mode == "none":
        plan["base_numeric_cols"] = []
        return plan

    numeric_cols = [
        col
        for col in feature_cols
        if pd.api.types.is_numeric_dtype(train_df[col]) and col != CYCLE_COL
    ]
    plan.update(
        {
            "base_numeric_cols": numeric_cols,
            "rolling_window": 3,
            "slope_window": 5,
        }
    )
    return plan


def apply_light_fe(df: pd.DataFrame, fe_plan: Dict[str, Any]) -> pd.DataFrame:
    if fe_plan["fe_mode"] == "none":
        return df.copy()

    base_cols = fe_plan["base_numeric_cols"]
    missing = [c for c in base_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns required by FE plan: {missing[:10]}")

    roll_w = int(fe_plan["rolling_window"])
    slope_w = int(fe_plan["slope_window"])

    out = df.sort_values([ENGINE_COL, CYCLE_COL]).copy()
    grouped = out.groupby(ENGINE_COL, sort=False)

    for col in base_cols:
        out[f"{col}__delta1"] = grouped[col].diff().fillna(0.0)
        out[f"{col}__roll_mean{roll_w}"] = grouped[col].transform(
            lambda s: s.rolling(roll_w, min_periods=1).mean()
        )
        out[f"{col}__roll_std{roll_w}"] = grouped[col].transform(
            lambda s: s.rolling(roll_w, min_periods=1).std().fillna(0.0)
        )
        # Local trend proxy from recent first differences.
        out[f"{col}__slope{slope_w}"] = grouped[col].transform(
            lambda s: s.diff().rolling(slope_w, min_periods=1).mean().fillna(0.0)
        )

    return out


def build_final_feature_cols(
    base_feature_cols: List[str], train_fe: pd.DataFrame, fe_plan: Dict[str, Any]
) -> List[str]:
    final_cols = list(base_feature_cols)
    if fe_plan["fe_mode"] == "none":
        return final_cols

    roll_w = int(fe_plan["rolling_window"])
    slope_w = int(fe_plan["slope_window"])
    for col in fe_plan["base_numeric_cols"]:
        engineered = [
            f"{col}__delta1",
            f"{col}__roll_mean{roll_w}",
            f"{col}__roll_std{roll_w}",
            f"{col}__slope{slope_w}",
        ]
        for e_col in engineered:
            if e_col in train_fe.columns:
                final_cols.append(e_col)

    return list(dict.fromkeys(final_cols))


def rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    err = np.asarray(y_true) - np.asarray(y_pred)
    return float(np.sqrt(np.mean(np.square(err))))


def main() -> int:
    args = parse_args()
    set_seed(args.seed)

    dataset_dir = Path(args.input_root) / args.dataset
    train_path = dataset_dir / f"train_{args.dataset}_v0.csv"
    test_path = dataset_dir / f"test_{args.dataset}_v0.csv"
    scaler_path = dataset_dir / f"scaler_{args.dataset}_v0.json"

    if not train_path.exists():
        raise FileNotFoundError(f"Train file not found: {train_path}")
    if not test_path.exists():
        raise FileNotFoundError(f"Test file not found: {test_path}")

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / f"ncmapss_{args.dataset}_autogluon_artifacts"
    run_dir.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    validate_split_schema(train_df, "train", require_target=True)
    validate_split_schema(test_df, "test", require_target=False)
    assert_no_engine_overlap(train_df, test_df)

    scaler_feature_cols: Optional[List[str]] = None
    if bool(args.use_scaler_features):
        scaler_feature_cols = load_scaler_feature_columns(scaler_path)
        if scaler_feature_cols:
            print(f"[INFO] Using feature_columns from scaler: {scaler_path}")
        else:
            print("[INFO] scaler feature_columns unavailable; using inferred CSV features.")

    train_part_raw, val_part_raw, val_engines_used = split_train_for_tuning(
        train_df, args.val_engines, args.seed
    )

    try:
        base_feature_cols = build_base_feature_cols(
            train_part_raw,
            use_cycle=bool(args.use_cycle),
            preferred_feature_cols=scaler_feature_cols,
        )
    except ValueError:
        if scaler_feature_cols:
            print("[WARN] scaler feature_columns produced no usable features; falling back to inferred CSV features.")
            base_feature_cols = build_base_feature_cols(
                train_part_raw,
                use_cycle=bool(args.use_cycle),
                preferred_feature_cols=None,
            )
        else:
            raise
    missing_in_test = set(base_feature_cols).difference(test_df.columns)
    if missing_in_test:
        raise ValueError(f"Test split missing feature columns: {sorted(missing_in_test)[:10]}")
    if val_part_raw is not None:
        missing_in_val = set(base_feature_cols).difference(val_part_raw.columns)
        if missing_in_val:
            raise ValueError(f"Validation split missing feature columns: {sorted(missing_in_val)[:10]}")

    fe_plan = build_fe_plan(train_part_raw, base_feature_cols, args.fe_mode)
    train_fe = apply_light_fe(train_df, fe_plan)
    train_part_fe = apply_light_fe(train_part_raw, fe_plan)
    val_part_fe = apply_light_fe(val_part_raw, fe_plan) if val_part_raw is not None else None
    test_fe = apply_light_fe(test_df, fe_plan)

    final_feature_cols = build_final_feature_cols(base_feature_cols, train_fe, fe_plan)

    if ENGINE_COL in final_feature_cols:
        raise AssertionError("engine_id must not be in final feature set")
    if TARGET_COL in final_feature_cols:
        raise AssertionError("RUL must not be in final feature set")
    if any(col in final_feature_cols for col in META_COLS):
        raise AssertionError("Meta columns must not be in final feature set")

    missing_final_test = set(final_feature_cols).difference(test_fe.columns)
    if missing_final_test:
        raise ValueError(
            f"Final feature mismatch. Missing in test: {sorted(missing_final_test)[:10]}"
        )
    if val_part_fe is not None:
        missing_final_val = set(final_feature_cols).difference(val_part_fe.columns)
        if missing_final_val:
            raise ValueError(
                f"Final feature mismatch. Missing in validation: {sorted(missing_final_val)[:10]}"
            )

    train_model_df = train_part_fe[final_feature_cols + [TARGET_COL]].copy()
    val_model_df = (
        val_part_fe[final_feature_cols + [TARGET_COL]].copy()
        if val_part_fe is not None
        else None
    )
    has_test_rul = TARGET_COL in test_fe.columns
    test_model_df = (
        test_fe[final_feature_cols + [TARGET_COL]].copy()
        if has_test_rul
        else test_fe[final_feature_cols].copy()
    )

    model_path = run_dir / "autogluon_models"
    predictor = TabularPredictor(
        label=TARGET_COL,
        eval_metric="rmse",
        path=str(model_path),
    )

    fit_kwargs: Dict[str, Any] = {
        "train_data": train_model_df,
        "presets": args.preset,
    }
    if val_model_df is not None:
        fit_kwargs["tuning_data"] = val_model_df
        fit_kwargs["use_bag_holdout"] = True
    if args.time_limit is not None:
        fit_kwargs["time_limit"] = args.time_limit

    started_at = time.time()
    predictor.fit(**fit_kwargs)
    elapsed_sec = time.time() - started_at

    # Leaderboard: prefer val if available; else prefer test if labeled; else fall back to train_part
    leaderboard_data = (
        val_model_df
        if val_model_df is not None
        else (test_model_df if has_test_rul else train_model_df)
    )
    leaderboard = predictor.leaderboard(data=leaderboard_data, silent=True)
    leaderboard_path = run_dir / "leaderboard.csv"
    leaderboard.to_csv(leaderboard_path, index=False)

    train_part_pred = predictor.predict(train_model_df.drop(columns=[TARGET_COL]))
    val_pred = (
        predictor.predict(val_model_df.drop(columns=[TARGET_COL]))
        if val_model_df is not None
        else None
    )
    test_pred = predictor.predict(test_model_df.drop(columns=[TARGET_COL], errors="ignore"))

    prediction_parts = [
        pd.DataFrame(
            {
                "dataset_id": args.dataset,
                "split": "train",
                ENGINE_COL: train_part_fe[ENGINE_COL].values,
                CYCLE_COL: train_part_fe[CYCLE_COL].values,
                "rul_pred": np.asarray(train_part_pred),
            }
        )
    ]
    if val_part_fe is not None and val_pred is not None:
        prediction_parts.append(
            pd.DataFrame(
                {
                    "dataset_id": args.dataset,
                    "split": "val",
                    ENGINE_COL: val_part_fe[ENGINE_COL].values,
                    CYCLE_COL: val_part_fe[CYCLE_COL].values,
                    "rul_pred": np.asarray(val_pred),
                }
            )
        )
    prediction_parts.append(
        pd.DataFrame(
            {
                "dataset_id": args.dataset,
                "split": "test",
                ENGINE_COL: test_fe[ENGINE_COL].values,
                CYCLE_COL: test_fe[CYCLE_COL].values,
                "rul_pred": np.asarray(test_pred),
            }
        )
    )
    predictions_df = pd.concat(prediction_parts, ignore_index=True)
    pred_path = output_root / f"ncmapss_{args.dataset}_rul_predictions_autogluon.csv"
    predictions_df.to_csv(pred_path, index=False)

    model_note = (
        "Test split is used only for reporting/benchmarking. "
        "Model selection is based on AutoGluon internal CV on train split."
    )
    if val_model_df is not None:
        model_note = (
            "Test split is used only for reporting/benchmarking. "
            "Model selection is based on train split with engine-based holdout tuning_data."
        )

    model_info = {
        "dataset": args.dataset,
        "best_model": predictor.model_best,
        "train_rows": int(len(train_model_df)),
        "test_rows": int(len(test_model_df)),
        "train_total_rows": int(len(train_fe)),
        "val_rows": int(len(val_model_df)) if val_model_df is not None else 0,
        "val_engines_used": int(val_engines_used),
        "n_features": int(len(final_feature_cols)),
        "train_part_rmse": rmse(train_model_df[TARGET_COL], train_part_pred),
        "val_rmse": rmse(val_model_df[TARGET_COL], val_pred) if val_model_df is not None else None,
        "test_rmse": rmse(test_fe[TARGET_COL], test_pred) if has_test_rul else None,
        "fit_elapsed_sec": elapsed_sec,
        "predictor_info": predictor.info(),
        "note": model_note,
    }
    dump_json(run_dir / "model_info.json", model_info)

    run_config = {
        "dataset": args.dataset,
        "seed": args.seed,
        "preset": args.preset,
        "use_cycle": bool(args.use_cycle),
        "fe_mode": args.fe_mode,
        "use_scaler_features": bool(args.use_scaler_features),
        "val_engines": int(args.val_engines),
        "val_engines_used": int(val_engines_used),
        "time_limit": args.time_limit,
        "input_root": str(Path(args.input_root).resolve()),
        "output_root": str(output_root.resolve()),
        "train_path": str(train_path.resolve()),
        "test_path": str(test_path.resolve()),
        "scaler_path": str(scaler_path.resolve()),
        "scaler_features_used": bool(scaler_feature_cols),
        "prediction_path": str(pred_path.resolve()),
        "artifacts_dir": str(run_dir.resolve()),
        "feature_count": int(len(final_feature_cols)),
        "feature_sample": final_feature_cols[:20],
        "engine_overlap_assertion": "passed",
        "target_leakage_assertion": "passed",
    }
    dump_json(run_dir / "run_config.json", run_config)

    print(f"[OK] Dataset: {args.dataset}")
    print(f"[OK] Predictions: {pred_path}")
    print(f"[OK] Leaderboard: {leaderboard_path}")
    print(f"[OK] Model info: {run_dir / 'model_info.json'}")
    print(f"[OK] Run config: {run_dir / 'run_config.json'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise
