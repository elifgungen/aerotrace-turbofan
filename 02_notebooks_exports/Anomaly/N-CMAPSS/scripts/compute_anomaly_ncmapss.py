#!/usr/bin/env python3
"""
Compute per-row anomaly scores for Jet-Cube N-CMAPSS processed datasets.

This script enforces the Anomaly Input Contract and supports two methods:
1) `mahalanobis` (default): fit LedoitWolf on train features only and compute
   squared Mahalanobis distance.
2) `iforest`: fit IsolationForest on train features only.

Contract enforcement (hard asserts):
- Model input X uses ONLY `scaler_<DS>_v0.json["feature_columns"]`.
- `meta_columns` may be used only for grouping/sorting/join and are excluded from X.
- Forbidden columns (case-insensitive) are excluded from model input:
  `RUL`, `rul_*`, `*_rul*`, `rul_pred`, `pred*`, `target*`, `label*`.
- Train/test feature sets must match exactly for selected feature_columns.
- All selected feature_columns must be numeric in both train and test.
- Leakage prevention: model fit is train-only; test is scoring-only.

Outputs:
- CSV: <output_root>/ncmapss_<DS>_anomaly_scores.csv
  Columns: dataset_id, split, engine_id, cycle, anomaly_score, anomaly_raw
- Artifacts: <output_root>/ncmapss_<DS>_anomaly_artifacts/
  - model_info.json
  - run_config.json
  - mahalanobis_params.npz (only for mahalanobis)

Usage:
python compute_anomaly_ncmapss.py --dataset DS04 --input_root /path/to/input --output_root /path/to/out \
  --method mahalanobis --seed 42 --chunksize 50000
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.stats import chi2
from sklearn.covariance import LedoitWolf
from sklearn.ensemble import IsolationForest


FORBIDDEN_RE = re.compile(
    r"(^rul$|^rul_.*|.*_rul.*|^rul_pred$|^pred.*|^target.*|^label.*)",
    flags=re.IGNORECASE,
)
REQUIRED_ID_COLS = ("engine_id", "cycle")
OUTPUT_COLS = ("dataset_id", "split", "engine_id", "cycle", "anomaly_score", "anomaly_raw")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute anomaly scores for N-CMAPSS processed CSVs.")
    parser.add_argument("--dataset", required=True, help="Dataset ID (e.g., DS01, DS08a, DS08c).")
    parser.add_argument(
        "--input_root",
        required=True,
        help="Root input directory containing dataset folders: <input_root>/<DS>/...",
    )
    parser.add_argument("--output_root", required=True, help="Directory where outputs/artifacts are written.")
    parser.add_argument(
        "--method",
        default="mahalanobis",
        choices=["mahalanobis", "iforest"],
        help="Anomaly method.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--contamination",
        type=float,
        default=0.02,
        help="IsolationForest contamination in (0, 0.5]. Used only for --method iforest.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=50000,
        help="Test scoring chunk size (rows per chunk).",
    )
    return parser.parse_args()


def find_unique_file(base_dir: Path, filename: str) -> Path:
    matches = sorted(base_dir.rglob(filename))
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        raise FileNotFoundError(f"Required file not found under {base_dir}: {filename}")
    raise FileExistsError(
        f"Multiple files matched under {base_dir} for {filename}: "
        + ", ".join(str(m) for m in matches[:10])
    )


def resolve_dataset_files(input_root: Path, dataset: str) -> Tuple[Path, Path, Path]:
    ds_dir = input_root / dataset
    if not ds_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {ds_dir}")

    train_name = f"train_{dataset}_v0.csv"
    test_name = f"test_{dataset}_v0.csv"
    scaler_name = f"scaler_{dataset}_v0.json"

    direct_train = ds_dir / train_name
    direct_test = ds_dir / test_name
    direct_scaler = ds_dir / scaler_name
    if direct_train.exists() and direct_test.exists() and direct_scaler.exists():
        return direct_train, direct_test, direct_scaler

    # Nested layout fallback under dataset folder (e.g., DS08a/V0_global_zscore_nodrop/*).
    train_path = find_unique_file(ds_dir, train_name)
    test_path = find_unique_file(ds_dir, test_name)
    scaler_path = find_unique_file(ds_dir, scaler_name)
    return train_path, test_path, scaler_path


def load_scaler_config(scaler_path: Path) -> Dict:
    with scaler_path.open("r", encoding="utf-8") as f:
        scaler = json.load(f)

    if "feature_columns" not in scaler:
        raise KeyError(f"'feature_columns' missing in scaler JSON: {scaler_path}")
    feature_columns = scaler["feature_columns"]
    if not isinstance(feature_columns, list) or not feature_columns:
        raise ValueError(f"'feature_columns' must be a non-empty list in {scaler_path}")
    if len(set(feature_columns)) != len(feature_columns):
        raise AssertionError(f"Duplicate entries found in feature_columns: {scaler_path}")
    if len(feature_columns) != 72:
        raise AssertionError(
            f"Contract violation: expected 72 feature_columns, found {len(feature_columns)} in {scaler_path}"
        )

    bad_features = [c for c in feature_columns if FORBIDDEN_RE.search(c)]
    if bad_features:
        raise AssertionError(
            f"Contract violation: forbidden columns in feature_columns: {bad_features}"
        )
    return scaler


def read_header(path: Path) -> List[str]:
    return pd.read_csv(path, nrows=0).columns.tolist()


def validate_contract_schema(
    train_path: Path,
    test_path: Path,
    feature_columns: Sequence[str],
    scaler_meta_columns: Sequence[str] | None,
) -> None:
    train_cols = read_header(train_path)
    test_cols = read_header(test_path)
    feature_set = set(feature_columns)

    for col in REQUIRED_ID_COLS:
        if col not in train_cols:
            raise AssertionError(f"Required ID column missing in train CSV: {col}")
        if col not in test_cols:
            raise AssertionError(f"Required ID column missing in test CSV: {col}")

    missing_train = sorted(feature_set - set(train_cols))
    missing_test = sorted(feature_set - set(test_cols))
    if missing_train:
        raise AssertionError(f"feature_columns missing in train CSV: {missing_train}")
    if missing_test:
        raise AssertionError(f"feature_columns missing in test CSV: {missing_test}")

    train_selected_set = {c for c in train_cols if c in feature_set}
    test_selected_set = {c for c in test_cols if c in feature_set}
    if train_selected_set != test_selected_set or train_selected_set != feature_set:
        raise AssertionError(
            "Contract violation: train/test selected feature sets do not match exactly."
        )

    # Forbidden columns may exist in CSV, but they must never be part of model X.
    forbidden_in_train = [c for c in train_selected_set if FORBIDDEN_RE.search(c)]
    forbidden_in_test = [c for c in test_selected_set if FORBIDDEN_RE.search(c)]
    if forbidden_in_train or forbidden_in_test:
        raise AssertionError(
            "Contract violation: forbidden columns leaked into selected feature set. "
            f"train={forbidden_in_train}, test={forbidden_in_test}"
        )

    if scaler_meta_columns:
        overlap = sorted(set(scaler_meta_columns).intersection(feature_set))
        if overlap:
            raise AssertionError(
                f"Contract violation: meta_columns overlap with feature_columns: {overlap}"
            )


def to_numeric_matrix(df: pd.DataFrame, feature_columns: Sequence[str], split_name: str) -> np.ndarray:
    x_df = df.loc[:, feature_columns]
    converted = x_df.apply(pd.to_numeric, errors="coerce")

    bad_cols: List[str] = []
    for c in feature_columns:
        invalid_mask = x_df[c].notna() & converted[c].isna()
        if invalid_mask.any():
            bad_cols.append(c)
    if bad_cols:
        sample = bad_cols[:10]
        raise AssertionError(
            f"Contract violation: non-numeric values detected in {split_name} for columns: {sample}"
        )
    return converted.to_numpy(dtype=np.float64, copy=False)


def fit_mahalanobis(
    X_train: np.ndarray,
) -> Tuple[Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]], Dict, Dict[str, np.ndarray]]:
    lw = LedoitWolf().fit(X_train)
    mean = lw.location_
    precision = lw.precision_
    n_features = X_train.shape[1]

    def score_fn(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        delta = X - mean
        dist2 = np.einsum("ij,jk,ik->i", delta, precision, delta)
        tail_prob = 1.0 - chi2.cdf(dist2, df=n_features)  # requested conversion primitive
        score = np.clip(1.0 - tail_prob, 0.0, 1.0)  # higher score => more anomalous
        return score.astype(np.float64), dist2.astype(np.float64)

    info = {
        "method": "mahalanobis",
        "n_features": int(n_features),
        "chi2_df": int(n_features),
    }
    params = {
        "location": mean,
        "covariance": lw.covariance_,
        "precision": precision,
    }
    return score_fn, info, params


def fit_iforest(
    X_train: np.ndarray,
    contamination: float,
    seed: int,
) -> Tuple[Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]], Dict]:
    if not (0.0 < contamination <= 0.5):
        raise ValueError(f"Invalid contamination={contamination}. Must be in (0, 0.5].")

    model = IsolationForest(
        contamination=contamination,
        random_state=seed,
        n_estimators=300,
        n_jobs=-1,
    )
    model.fit(X_train)

    train_decision = model.decision_function(X_train)
    train_raw = -train_decision
    raw_min = float(np.min(train_raw))
    raw_max = float(np.max(train_raw))
    scale = raw_max - raw_min

    def score_fn(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        decision = model.decision_function(X)
        raw = -decision
        if scale <= 1e-12:
            score = np.zeros_like(raw, dtype=np.float64)
        else:
            score = (raw - raw_min) / scale
            score = np.clip(score, 0.0, 1.0)
        return score.astype(np.float64), raw.astype(np.float64)

    info = {
        "method": "iforest",
        "n_features": int(X_train.shape[1]),
        "contamination": float(contamination),
        "train_raw_min": raw_min,
        "train_raw_max": raw_max,
    }
    return score_fn, info


def build_output_frame(
    dataset_id: str,
    split: str,
    engine_id: Iterable,
    cycle: Iterable,
    anomaly_score: np.ndarray,
    anomaly_raw: np.ndarray,
) -> pd.DataFrame:
    out_df = pd.DataFrame(
        {
            "dataset_id": dataset_id,
            "split": split,
            "engine_id": engine_id,
            "cycle": cycle,
            "anomaly_score": anomaly_score,
            "anomaly_raw": anomaly_raw,
        }
    )
    out_df = out_df.sort_values(["engine_id", "cycle"], kind="mergesort")
    return out_df.loc[:, OUTPUT_COLS]


def safe_quantiles(values: np.ndarray) -> Dict[str, float]:
    q = np.quantile(values, [0.0, 0.25, 0.5, 0.75, 1.0])
    return {
        "min": float(q[0]),
        "q25": float(q[1]),
        "median": float(q[2]),
        "q75": float(q[3]),
        "max": float(q[4]),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
    }


def main() -> None:
    args = parse_args()
    np.random.seed(args.seed)

    dataset = args.dataset
    input_root = Path(args.input_root).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"[{dataset}] Start anomaly scoring")
    print(f"[{dataset}] Input root: {input_root}")
    print(f"[{dataset}] Output root: {output_root}")

    train_path, test_path, scaler_path = resolve_dataset_files(input_root, dataset)
    print(f"[{dataset}] train:  {train_path}")
    print(f"[{dataset}] test:   {test_path}")
    print(f"[{dataset}] scaler: {scaler_path}")

    scaler = load_scaler_config(scaler_path)
    feature_columns: List[str] = list(scaler["feature_columns"])
    meta_columns: List[str] = list(scaler.get("meta_columns", []))

    validate_contract_schema(train_path, test_path, feature_columns, meta_columns)
    print(
        f"[{dataset}] Feature checks PASS | feature_count={len(feature_columns)} | "
        f"meta_count={len(meta_columns)}"
    )

    # Fit on train only (leakage prevention).
    train_usecols = list(REQUIRED_ID_COLS) + feature_columns
    train_df = pd.read_csv(train_path, usecols=train_usecols)
    X_train = to_numeric_matrix(train_df, feature_columns, split_name="train")

    mahalanobis_params: Dict[str, np.ndarray] | None = None
    if args.method == "mahalanobis":
        score_fn, model_info, mahalanobis_params = fit_mahalanobis(X_train)
    else:
        score_fn, model_info = fit_iforest(
            X_train,
            contamination=float(args.contamination),
            seed=int(args.seed),
        )
    print(f"[{dataset}] Fit done | method={args.method} | train_rows={len(train_df)}")

    train_score, train_raw = score_fn(X_train)
    train_out = build_output_frame(
        dataset_id=dataset,
        split="train",
        engine_id=train_df["engine_id"].values,
        cycle=train_df["cycle"].values,
        anomaly_score=train_score,
        anomaly_raw=train_raw,
    )

    out_csv = output_root / f"ncmapss_{dataset}_anomaly_scores.csv"
    train_out.to_csv(out_csv, index=False, mode="w")
    print(f"[{dataset}] Wrote train scores: {out_csv} (rows={len(train_out)})")

    test_usecols = list(REQUIRED_ID_COLS) + feature_columns
    test_rows_total = 0
    chunk_idx = 0
    for chunk in pd.read_csv(test_path, usecols=test_usecols, chunksize=args.chunksize):
        chunk_idx += 1
        X_chunk = to_numeric_matrix(chunk, feature_columns, split_name=f"test_chunk_{chunk_idx}")
        chunk_score, chunk_raw = score_fn(X_chunk)

        out_chunk = build_output_frame(
            dataset_id=dataset,
            split="test",
            engine_id=chunk["engine_id"].values,
            cycle=chunk["cycle"].values,
            anomaly_score=chunk_score,
            anomaly_raw=chunk_raw,
        )

        out_chunk.to_csv(out_csv, index=False, mode="a", header=False)
        test_rows_total += len(out_chunk)
        print(
            f"[{dataset}] Test chunk {chunk_idx} done | rows={len(out_chunk)} | "
            f"cumulative_test_rows={test_rows_total}"
        )

    artifacts_dir = output_root / f"ncmapss_{dataset}_anomaly_artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    run_config = {
        "dataset": dataset,
        "method": args.method,
        "seed": int(args.seed),
        "contamination": float(args.contamination),
        "chunksize": int(args.chunksize),
        "input_root": str(input_root),
        "output_root": str(output_root),
        "train_csv": str(train_path),
        "test_csv": str(test_path),
        "scaler_json": str(scaler_path),
        "output_csv": str(out_csv),
    }
    with (artifacts_dir / "run_config.json").open("w", encoding="utf-8") as f:
        json.dump(run_config, f, indent=2, ensure_ascii=False)

    model_info.update(
        {
            "dataset": dataset,
            "feature_count": len(feature_columns),
            "feature_sample": feature_columns[:10],
            "meta_columns": meta_columns,
            "train_rows": int(len(train_df)),
            "test_rows": int(test_rows_total),
            "train_anomaly_raw_stats": safe_quantiles(train_raw),
            "train_anomaly_score_stats": safe_quantiles(train_score),
            "forbidden_pattern": FORBIDDEN_RE.pattern,
            "contract_enforced": True,
        }
    )

    if args.method == "mahalanobis" and mahalanobis_params is not None:
        # Lightweight model parameters for reproducibility.
        np.savez_compressed(
            artifacts_dir / "mahalanobis_params.npz",
            location=mahalanobis_params["location"],
            covariance=mahalanobis_params["covariance"],
            precision=mahalanobis_params["precision"],
        )

    with (artifacts_dir / "model_info.json").open("w", encoding="utf-8") as f:
        json.dump(model_info, f, indent=2, ensure_ascii=False)

    print(f"[{dataset}] Saved artifacts: {artifacts_dir}")
    print(f"[{dataset}] Done")


if __name__ == "__main__":
    main()
