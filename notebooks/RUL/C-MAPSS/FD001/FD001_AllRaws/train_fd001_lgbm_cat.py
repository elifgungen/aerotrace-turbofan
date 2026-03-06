"""
Train/evaluate LightGBM + CatBoost ensemble using Özcan et al. (Scientific Reports, 2025) hyperparameters.

Primary intent:
  - Run on your already z-score normalized FD001 CSVs (train/test) that include per-row RUL labels.
  - Train two base regressors (LightGBM, CatBoost) with Özcan Table 4 parameters.
  - Produce equal-weight ensemble predictions + metrics, including the PHM08 RUL Score (Ozcan Eq. 4).

Paper pointers (for humans, not used programmatically):
  - Hyperparameters: Table 4 (Ozcan PDF p. 9)
  - RUL Score formula: Eq. (4) with a1=10, a2=13 (Ozcan PDF p. 10)

Example:
  python train_fd001_lgbm_cat.py ^
    --train Data/FD001/Sensor_Deleted/FD001-20260122T184021Z-1-001/train_FD001_norm.csv ^
    --test  Data/FD001/Sensor_Deleted/FD001-20260122T184021Z-1-001/test_FD001_norm.csv ^
    --outdir outputs/fd001_lgbm_cat
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold


def _require_optional_deps() -> tuple[object, object]:
    try:
        import lightgbm as lgb  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: lightgbm. Install with: pip install lightgbm"
        ) from exc

    try:
        import catboost  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: catboost. Install with: pip install catboost"
        ) from exc

    return lgb, catboost


def phm08_rul_score(y_true: np.ndarray, y_pred: np.ndarray, a1: float = 10.0, a2: float = 13.0) -> float:
    """
    PHM08 RUL Score as given in Özcan et al. 2025, Eq. (4).

    di = y_pred - y_true
    s = sum( exp(-di/a1) if di < 0 else exp(di/a2) )
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    d = y_pred - y_true

    score = 0.0
    for di in d:
        if di < 0:
            score += math.exp(-di / a1)
        else:
            score += math.exp(di / a2)
    return float(score)


@dataclass(frozen=True)
class Metrics:
    n_rows: int
    rmse: float
    mse: float
    mae: float
    r2: float
    phm08_rul_score: float


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Metrics:
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(math.sqrt(mse))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    score = phm08_rul_score(y_true, y_pred)
    return Metrics(
        n_rows=int(len(y_true)),
        rmse=rmse,
        mse=mse,
        mae=mae,
        r2=r2,
        phm08_rul_score=score,
    )


def select_last_cycle(df: pd.DataFrame, engine_id_col: str, cycle_col: str) -> pd.DataFrame:
    if engine_id_col not in df.columns:
        raise ValueError(f"Missing engine_id_col={engine_id_col!r} in data columns.")
    if cycle_col not in df.columns:
        raise ValueError(f"Missing cycle_col={cycle_col!r} in data columns.")
    idx = df.groupby(engine_id_col, sort=False)[cycle_col].idxmax()
    return df.loc[idx].sort_values([engine_id_col, cycle_col]).reset_index(drop=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_weights(s: str) -> tuple[float, float]:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 2:
        raise ValueError("--weights must be like '0.5,0.5'")
    w1, w2 = float(parts[0]), float(parts[1])
    if w1 < 0 or w2 < 0:
        raise ValueError("--weights must be non-negative")
    denom = w1 + w2
    if denom <= 0:
        raise ValueError("--weights sum must be > 0")
    return w1 / denom, w2 / denom


def get_feature_columns(df: pd.DataFrame, target_col: str, drop_cols: Iterable[str]) -> list[str]:
    drop = set(drop_cols)
    drop.add(target_col)
    cols = [c for c in df.columns if c not in drop]
    if not cols:
        raise ValueError("No feature columns left after dropping id/cycle/target columns.")
    return cols


def make_lgbm_model(lgb: object, seed: int) -> object:
    return lgb.LGBMRegressor(
        n_estimators=500,
        learning_rate=0.1,
        max_depth=-1,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=int(seed),
    )


def make_cat_model(catboost: object, seed: int) -> object:
    return catboost.CatBoostRegressor(
        iterations=500,
        learning_rate=0.1,
        depth=6,
        random_seed=int(seed),
        verbose=0,
        loss_function="RMSE",
        allow_writing_files=False,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True, help="Path to train CSV (must include target column).")
    ap.add_argument("--test", required=True, help="Path to test CSV (must include target column).")
    ap.add_argument("--target", default="RUL", help="Target column name (default: RUL).")
    ap.add_argument(
        "--cap-rul",
        type=float,
        default=None,
        help=(
            "Optional RUL cap applied to both train/test labels before fitting/evaluation. "
            "If set, labels are clipped to [0, cap]."
        ),
    )
    ap.add_argument("--engine-id-col", default="engine_id", help="Engine id column (default: engine_id).")
    ap.add_argument("--cycle-col", default="cycle", help="Cycle column (default: cycle).")
    ap.add_argument(
        "--drop-cols",
        default=None,
        help="Comma-separated extra columns to drop from features (in addition to engine_id/cycle/target).",
    )
    ap.add_argument(
        "--include-cycle",
        action="store_true",
        help="Include cycle as a feature (default: cycle is dropped).",
    )
    ap.add_argument(
        "--ensemble",
        choices=["mean", "stacking"],
        default="stacking",
        help=(
            "Ensemble method: 'mean' for weighted average, 'stacking' for Ridge(meta) trained on "
            "out-of-fold predictions grouped by engine_id."
        ),
    )
    ap.add_argument("--weights", default="0.5,0.5", help="Ensemble weights: w_lgbm,w_cat (default: 0.5,0.5).")
    ap.add_argument("--stacking-folds", type=int, default=5, help="Number of GroupKFold splits (default: 5).")
    ap.add_argument("--ridge-alpha", type=float, default=1.0, help="Ridge alpha for stacking meta-learner (default: 1.0).")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for model init (default: 42).")
    ap.add_argument("--outdir", default="outputs/fd001_lgbm_cat", help="Output directory.")
    args = ap.parse_args()

    train_path = Path(args.train)
    test_path = Path(args.test)
    outdir = Path(args.outdir)
    ensure_dir(outdir)

    df_train = pd.read_csv(train_path)
    df_test = pd.read_csv(test_path)
    np.random.seed(int(args.seed))

    target_col = args.target
    for name, df in [("train", df_train), ("test", df_test)]:
        if target_col not in df.columns:
            raise ValueError(f"{name} is missing target column {target_col!r}. Columns={list(df.columns)}")

    extra_drops = []
    if args.drop_cols:
        extra_drops = [c.strip() for c in args.drop_cols.split(",") if c.strip()]

    drop_cols = [args.engine_id_col, *extra_drops]
    if not args.include_cycle:
        drop_cols.append(args.cycle_col)

    feature_cols = get_feature_columns(
        df_train,
        target_col=target_col,
        drop_cols=drop_cols,
    )

    X_train = df_train[feature_cols]
    y_train = df_train[target_col].to_numpy()
    X_test = df_test[feature_cols]
    y_test = df_test[target_col].to_numpy()

    if args.cap_rul is not None:
        cap = float(args.cap_rul)
        if cap <= 0:
            raise ValueError("--cap-rul must be > 0 when provided.")
        y_train = np.clip(y_train, 0.0, cap)
        y_test = np.clip(y_test, 0.0, cap)

    lgb, catboost = _require_optional_deps()
    w_lgbm, w_cat = parse_weights(args.weights)

    ridge_meta: Ridge | None = None
    meta_info: dict[str, object] | None = None
    if args.ensemble == "stacking":
        n_engines = int(df_train[args.engine_id_col].nunique())
        if args.stacking_folds < 2:
            raise ValueError("--stacking-folds must be >= 2 for stacking.")
        if args.stacking_folds > n_engines:
            raise ValueError(
                f"--stacking-folds={args.stacking_folds} cannot be > number of train engines ({n_engines})."
            )

        groups = df_train[args.engine_id_col].to_numpy()
        gkf = GroupKFold(n_splits=int(args.stacking_folds))

        oof_pred_lgbm = np.full(shape=(len(df_train),), fill_value=np.nan, dtype=float)
        oof_pred_cat = np.full(shape=(len(df_train),), fill_value=np.nan, dtype=float)

        for train_idx, val_idx in gkf.split(X_train, y_train, groups=groups):
            lgbm_fold = make_lgbm_model(lgb, seed=int(args.seed))
            lgbm_fold.fit(X_train.iloc[train_idx], y_train[train_idx])
            oof_pred_lgbm[val_idx] = lgbm_fold.predict(X_train.iloc[val_idx])

            cat_fold = make_cat_model(catboost, seed=int(args.seed))
            cat_fold.fit(X_train.iloc[train_idx], y_train[train_idx])
            oof_pred_cat[val_idx] = cat_fold.predict(X_train.iloc[val_idx])

        if np.isnan(oof_pred_lgbm).any() or np.isnan(oof_pred_cat).any():
            raise RuntimeError("OOF predictions contain NaNs; check GroupKFold split logic.")

        meta_X = np.column_stack([oof_pred_lgbm, oof_pred_cat])
        ridge_meta = Ridge(alpha=float(args.ridge_alpha))
        ridge_meta.fit(meta_X, y_train)

        meta_info = {
            "meta_model": "Ridge",
            "ridge_alpha": float(args.ridge_alpha),
            "coef": ridge_meta.coef_.tolist(),
            "intercept": float(ridge_meta.intercept_),
            "feature_order": ["pred_lgbm", "pred_catboost"],
            "stacking_folds": int(args.stacking_folds),
            "cv": "GroupKFold(engine_id)",
        }
        (outdir / "meta_ridge.json").write_text(
            json.dumps(meta_info, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        oof_df = df_train[[args.engine_id_col, args.cycle_col, target_col]].copy()
        oof_df["oof_pred_lgbm"] = oof_pred_lgbm
        oof_df["oof_pred_catboost"] = oof_pred_cat
        oof_df["oof_pred_stack"] = ridge_meta.predict(meta_X)
        oof_df.to_csv(outdir / "oof_train_predictions.csv", index=False)

    lgbm_model = make_lgbm_model(lgb, seed=int(args.seed))
    lgbm_model.fit(X_train, y_train)

    cat_model = make_cat_model(catboost, seed=int(args.seed))
    cat_model.fit(X_train, y_train)

    pred_lgbm = lgbm_model.predict(X_test)
    pred_cat = cat_model.predict(X_test)
    if args.ensemble == "mean":
        pred_ens = (w_lgbm * pred_lgbm) + (w_cat * pred_cat)
    else:
        if ridge_meta is None:
            raise RuntimeError("Internal error: stacking requested but ridge_meta is None.")
        pred_ens = ridge_meta.predict(np.column_stack([pred_lgbm, pred_cat]))

    metrics_all = {
        "lgbm": asdict(compute_metrics(y_test, pred_lgbm)),
        "catboost": asdict(compute_metrics(y_test, pred_cat)),
        "ensemble": asdict(compute_metrics(y_test, pred_ens)),
        "feature_columns": feature_cols,
        "ensemble_method": args.ensemble,
        "weights": {"lgbm": w_lgbm, "catboost": w_cat} if args.ensemble == "mean" else None,
        "stacking_meta": meta_info,
        "cap_rul": args.cap_rul,
        "seed": int(args.seed),
    }

    df_test_last = select_last_cycle(df_test, engine_id_col=args.engine_id_col, cycle_col=args.cycle_col)
    X_test_last = df_test_last[feature_cols]
    y_test_last = df_test_last[target_col].to_numpy()
    if args.cap_rul is not None:
        y_test_last = np.clip(y_test_last, 0.0, float(args.cap_rul))
    pred_lgbm_last = lgbm_model.predict(X_test_last)
    pred_cat_last = cat_model.predict(X_test_last)
    if args.ensemble == "mean":
        pred_ens_last = (w_lgbm * pred_lgbm_last) + (w_cat * pred_cat_last)
    else:
        if ridge_meta is None:
            raise RuntimeError("Internal error: stacking requested but ridge_meta is None.")
        pred_ens_last = ridge_meta.predict(np.column_stack([pred_lgbm_last, pred_cat_last]))

    metrics_last = {
        "lgbm": asdict(compute_metrics(y_test_last, pred_lgbm_last)),
        "catboost": asdict(compute_metrics(y_test_last, pred_cat_last)),
        "ensemble": asdict(compute_metrics(y_test_last, pred_ens_last)),
    }

    out_metrics = {"all_rows": metrics_all, "last_cycle": metrics_last}
    (outdir / "metrics.json").write_text(json.dumps(out_metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    preds_df = df_test[[args.engine_id_col, args.cycle_col, target_col]].copy()
    preds_df["pred_lgbm"] = pred_lgbm
    preds_df["pred_catboost"] = pred_cat
    preds_df["pred_ensemble"] = pred_ens
    preds_df.to_csv(outdir / "predictions.csv", index=False)

    print(json.dumps(out_metrics, ensure_ascii=False, indent=2))
    print(f"\nWrote: {outdir / 'metrics.json'}")
    print(f"Wrote: {outdir / 'predictions.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
