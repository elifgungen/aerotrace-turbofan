from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import pandas as pd

from decision_support.policy_engine import apply_policy, load_policy_config

LOGGER = logging.getLogger(__name__)

ASSET_COL_CANDIDATES = ["asset_id", "engine_id", "unit_id", "id"]
TIME_COL_CANDIDATES = ["t", "cycle", "timestamp", "time"]
RUL_COL_CANDIDATES = ["rul_pred", "RUL_pred", "pred_ensemble", "y_pred"]
ANOM_COL_CANDIDATES = ["anomaly_score_raw", "anomaly_score", "anomaly_raw", "score"]


@dataclass(frozen=True)
class AdapterResult:
    output_path: str
    join_keys: List[str]
    id_cols: List[str]
    time_col: str
    rows: int


def read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    unnamed = [c for c in df.columns if str(c).lower().startswith("unnamed")]
    if unnamed:
        df = df.drop(columns=unnamed)
    return df


def infer_column(columns: Iterable[str], candidates: Sequence[str], kind: str) -> str:
    for cand in candidates:
        if cand in columns:
            return cand
    raise ValueError(f"Could not infer {kind} column. Candidates: {list(candidates)}")


def _build_join_candidates(common_cols: set[str], asset_col: str, time_col: str) -> List[List[str]]:
    candidates: List[List[str]] = []

    if {"dataset_id", "split", asset_col, time_col}.issubset(common_cols):
        candidates.append(["dataset_id", "split", asset_col, time_col])
    if {"dataset_id", asset_col, time_col}.issubset(common_cols):
        candidates.append(["dataset_id", asset_col, time_col])
    if {"split", asset_col, time_col}.issubset(common_cols):
        candidates.append(["split", asset_col, time_col])
    if {asset_col, time_col}.issubset(common_cols):
        candidates.append([asset_col, time_col])

    unique_candidates: List[List[str]] = []
    seen = set()
    for keys in candidates:
        key_t = tuple(keys)
        if key_t not in seen:
            seen.add(key_t)
            unique_candidates.append(keys)
    return unique_candidates


def discover_join_keys(
    rul_df: pd.DataFrame,
    anomaly_df: pd.DataFrame,
    anomaly_col: str,
    preferred_asset_col: str,
    preferred_time_col: str,
) -> Tuple[List[str], Dict[str, float]]:
    common_cols = set(rul_df.columns).intersection(anomaly_df.columns)
    candidates = _build_join_candidates(common_cols, preferred_asset_col, preferred_time_col)
    if not candidates:
        raise ValueError(
            "No viable join key candidates found between RUL and anomaly files. "
            f"Common columns: {sorted(common_cols)}"
        )

    best_keys: List[str] | None = None
    best_score: Tuple[float, float, float, float] | None = None
    best_meta: Dict[str, float] = {}

    for keys in candidates:
        dup_rul = float(rul_df.duplicated(keys).sum())
        dup_anomaly = float(anomaly_df.duplicated(keys).sum())

        merged = rul_df[keys].merge(
            anomaly_df[keys + [anomaly_col]],
            on=keys,
            how="left",
        )
        row_expansion = float(max(len(merged) - len(rul_df), 0))
        missing_rate = float(merged[anomaly_col].isna().mean())

        # Lower is better. Prefer richer keys when other metrics tie.
        score = (row_expansion, dup_rul + dup_anomaly, missing_rate, -float(len(keys)))

        if best_score is None or score < best_score:
            best_score = score
            best_keys = keys
            best_meta = {
                "row_expansion": row_expansion,
                "dup_rul": dup_rul,
                "dup_anomaly": dup_anomaly,
                "missing_rate": missing_rate,
            }

    assert best_keys is not None
    LOGGER.info("Selected join keys=%s diagnostics=%s", best_keys, best_meta)
    return best_keys, best_meta


def merge_and_standardize(
    rul_csv: str,
    anomaly_csv: str,
    config_path: str,
    out_csv: str,
    dataset_tag: str,
) -> AdapterResult:
    cfg = load_policy_config(config_path)
    rul_df = read_csv(rul_csv)
    anomaly_df = read_csv(anomaly_csv)

    rul_col = infer_column(rul_df.columns, RUL_COL_CANDIDATES, "RUL prediction")
    anomaly_col = infer_column(anomaly_df.columns, ANOM_COL_CANDIDATES, "anomaly score")

    asset_col = infer_column(rul_df.columns, ASSET_COL_CANDIDATES, "asset id")
    time_col = infer_column(rul_df.columns, TIME_COL_CANDIDATES, "time")

    if asset_col not in anomaly_df.columns or time_col not in anomaly_df.columns:
        raise ValueError(
            f"Anomaly CSV must include inferred asset/time columns: {asset_col}, {time_col}"
        )

    join_keys, diagnostics = discover_join_keys(
        rul_df=rul_df,
        anomaly_df=anomaly_df,
        anomaly_col=anomaly_col,
        preferred_asset_col=asset_col,
        preferred_time_col=time_col,
    )

    if int(rul_df.duplicated(join_keys).sum()) > 0:
        raise ValueError(f"RUL CSV has duplicate keys for selected join keys: {join_keys}")

    # Aggregate anomaly duplicates by mean to keep deterministic behavior.
    anomaly_keyed = (
        anomaly_df[join_keys + [anomaly_col]]
        .copy()
        .groupby(join_keys, as_index=False)[anomaly_col]
        .mean()
    )

    merged = rul_df.merge(anomaly_keyed, on=join_keys, how="left")

    rename_map = {
        asset_col: "asset_id",
        time_col: "t",
        rul_col: "rul_pred",
        anomaly_col: "anomaly_score_raw",
    }
    standardized = merged.rename(columns=rename_map)

    id_cols_raw = [k for k in join_keys if k != time_col]
    id_cols = [rename_map.get(k, k) for k in id_cols_raw]
    policy_out = apply_policy(
        standardized,
        cfg,
        id_cols=id_cols,
        time_col="t",
    )

    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    policy_out.to_csv(out_path, index=False)

    LOGGER.info(
        "Adapter %s completed | rows=%d out=%s join_keys=%s diagnostics=%s",
        dataset_tag,
        len(policy_out),
        str(out_path),
        join_keys,
        diagnostics,
    )

    return AdapterResult(
        output_path=str(out_path),
        join_keys=join_keys,
        id_cols=id_cols,
        time_col="t",
        rows=int(len(policy_out)),
    )
