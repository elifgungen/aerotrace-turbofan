#!/usr/bin/env python3
"""
Build canonical Twin feed files for N-CMAPSS DS01-DS07.

Inputs:
- RUL predictions: notebooks/RUL/N-CMAPSS/**/ncmapss_DSxx_rul_predictions*.csv
- Anomaly scores:   notebooks/Anomaly/N-CMAPSS/DSxx/anomaly_scores.csv

Output per dataset:
- twin/inputs/ncmapss_DSxx_twin_feed.csv

Audit output:
- twin/inputs/ncmapss_twin_input_audit.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import pandas as pd


KEY_COLS = ["dataset_id", "split", "engine_id", "cycle"]
REQUIRED_RUL_COLS = KEY_COLS + ["rul_pred"]
REQUIRED_ANOM_COLS = KEY_COLS + ["anomaly_score"]
DEFAULT_DATASETS = ["DS01", "DS02", "DS03", "DS04", "DS05", "DS06", "DS07"]


@dataclass
class DatasetAudit:
    dataset: str
    rul_file: str
    anomaly_file: str
    output_file: str
    rul_rows: int
    anomaly_rows: int
    output_rows: int
    rul_duplicates: int
    anomaly_duplicates: int
    rul_only_keys: int
    anomaly_only_keys: int
    split_values: List[str]
    ready: bool
    notes: List[str]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build canonical Twin feed from RUL + anomaly outputs.")
    p.add_argument(
        "--datasets",
        nargs="+",
        default=DEFAULT_DATASETS,
        help="Dataset ids to process. Example: DS01 DS02 ... DS07",
    )
    p.add_argument(
        "--rul-root",
        default="notebooks/RUL/N-CMAPSS",
        help="Root folder for RUL prediction outputs.",
    )
    p.add_argument(
        "--anomaly-root",
        default="notebooks/Anomaly/N-CMAPSS",
        help="Root folder for anomaly outputs organized as DSxx/anomaly_scores.csv.",
    )
    p.add_argument(
        "--out-root",
        default="twin/inputs",
        help="Output folder for twin feed CSV files.",
    )
    p.add_argument(
        "--split-mode",
        choices=["all", "test_only"],
        default="all",
        help="Whether to keep train+test or only test rows in output feed.",
    )
    p.add_argument(
        "--allow-key-loss",
        action="store_true",
        help="Allow key-loss between RUL and anomaly merges.",
    )
    return p.parse_args()


def resolve_rul_file(rul_root: Path, dataset: str) -> Path:
    fixed = sorted(rul_root.rglob(f"ncmapss_{dataset}_rul_predictions*FIXED.csv"))
    if len(fixed) == 1:
        return fixed[0]
    if len(fixed) > 1:
        raise RuntimeError(f"{dataset}: multiple FIXED RUL files found: {fixed}")

    generic = sorted(rul_root.rglob(f"ncmapss_{dataset}_rul_predictions*.csv"))
    if len(generic) == 1:
        return generic[0]
    if not generic:
        raise FileNotFoundError(f"{dataset}: RUL predictions file not found under {rul_root}")
    raise RuntimeError(f"{dataset}: multiple non-FIXED RUL files found: {generic}")


def resolve_anomaly_file(anomaly_root: Path, dataset: str) -> Path:
    p = anomaly_root / dataset / "anomaly_scores.csv"
    if not p.exists():
        p2 = anomaly_root / "OUTPUTS" / f"ncmapss_{dataset}_anomaly_scores.csv"
        if not p2.exists():
            raise FileNotFoundError(f"{dataset}: anomaly file not found: {p} or {p2}")
        return p2
    return p


def ensure_required(df: pd.DataFrame, required: Sequence[str], tag: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{tag}: missing required columns: {missing}")


def canonicalize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["dataset_id"] = out["dataset_id"].astype(str).str.strip()
    out["split"] = out["split"].astype(str).str.strip().str.lower()
    out["engine_id"] = pd.to_numeric(out["engine_id"], errors="raise").astype(int)
    out["cycle"] = pd.to_numeric(out["cycle"], errors="raise").astype(int)
    return out


def key_df(df: pd.DataFrame) -> pd.DataFrame:
    return df[KEY_COLS].copy()


def build_dataset_feed(
    dataset: str,
    rul_file: Path,
    anomaly_file: Path,
    out_root: Path,
    split_mode: str,
    allow_key_loss: bool,
) -> DatasetAudit:
    notes: List[str] = []

    rul = pd.read_csv(rul_file)
    anom = pd.read_csv(anomaly_file)

    ensure_required(rul, REQUIRED_RUL_COLS, f"{dataset}/rul")
    ensure_required(anom, REQUIRED_ANOM_COLS, f"{dataset}/anomaly")

    rul = canonicalize(rul)
    anom = canonicalize(anom)

    rul_dups = int(rul.duplicated(subset=KEY_COLS).sum())
    anom_dups = int(anom.duplicated(subset=KEY_COLS).sum())
    if rul_dups:
        notes.append(f"RUL duplicates={rul_dups}")
    if anom_dups:
        notes.append(f"Anomaly duplicates={anom_dups}")

    rul_key_set = set(map(tuple, key_df(rul).to_numpy().tolist()))
    anom_key_set = set(map(tuple, key_df(anom).to_numpy().tolist()))
    rul_only = int(len(rul_key_set - anom_key_set))
    anom_only = int(len(anom_key_set - rul_key_set))

    merged = rul.merge(anom, on=KEY_COLS, how="inner", suffixes=("", "_anomaly"))

    if split_mode == "test_only":
        merged = merged[merged["split"] == "test"].copy()

    split_values = sorted(merged["split"].dropna().astype(str).unique().tolist())
    canonical_ok = set(split_values).issubset({"train", "test"})
    if not canonical_ok:
        notes.append(f"Non-canonical split values in output: {split_values}")

    base_cols = KEY_COLS + ["rul_pred", "anomaly_score"]
    optional_cols = [
        c
        for c in ["anomaly_raw", "is_validation_subset", "orig_split"]
        if c in merged.columns
    ]
    out_df = merged[base_cols + optional_cols].copy()

    # Replay order: split(train->test), engine, cycle
    split_rank = {"train": 0, "test": 1}
    out_df["split_rank"] = out_df["split"].map(split_rank).fillna(99).astype(int)
    out_df = out_df.sort_values(["split_rank", "engine_id", "cycle"], kind="stable").drop(
        columns=["split_rank"]
    )
    out_df["row_id"] = range(1, len(out_df) + 1)

    out_root.mkdir(parents=True, exist_ok=True)
    out_file = out_root / f"ncmapss_{dataset}_twin_feed.csv"
    out_df.to_csv(out_file, index=False)

    ready = (
        rul_dups == 0
        and anom_dups == 0
        and canonical_ok
        and (allow_key_loss or (rul_only == 0 and anom_only == 0))
        and len(out_df) > 0
    )

    if not ready and not allow_key_loss and (rul_only > 0 or anom_only > 0):
        notes.append("Key loss detected and --allow-key-loss is disabled.")

    return DatasetAudit(
        dataset=dataset,
        rul_file=str(rul_file),
        anomaly_file=str(anomaly_file),
        output_file=str(out_file),
        rul_rows=len(rul),
        anomaly_rows=len(anom),
        output_rows=len(out_df),
        rul_duplicates=rul_dups,
        anomaly_duplicates=anom_dups,
        rul_only_keys=rul_only,
        anomaly_only_keys=anom_only,
        split_values=split_values,
        ready=ready,
        notes=notes,
    )


def main() -> None:
    args = parse_args()
    rul_root = Path(args.rul_root)
    anomaly_root = Path(args.anomaly_root)
    out_root = Path(args.out_root)

    audits: List[DatasetAudit] = []
    overall_ready = True

    for ds in args.datasets:
        ds = ds.strip()
        if not ds:
            continue
        rul_file = resolve_rul_file(rul_root, ds)
        anomaly_file = resolve_anomaly_file(anomaly_root, ds)
        audit = build_dataset_feed(
            dataset=ds,
            rul_file=rul_file,
            anomaly_file=anomaly_file,
            out_root=out_root,
            split_mode=args.split_mode,
            allow_key_loss=args.allow_key_loss,
        )
        audits.append(audit)
        overall_ready = overall_ready and audit.ready
        print(
            f"{audit.dataset}: ready={audit.ready} rows={audit.output_rows} "
            f"rul_only={audit.rul_only_keys} anom_only={audit.anomaly_only_keys}"
        )

    payload: Dict[str, object] = {
        "overall_ready": overall_ready,
        "split_mode": args.split_mode,
        "datasets": [a.__dict__ for a in audits],
    }
    out_root.mkdir(parents=True, exist_ok=True)
    audit_path = out_root / "ncmapss_twin_input_audit.json"
    audit_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"audit={audit_path}")

    if not overall_ready:
        raise SystemExit("Input build completed with readiness failures. Check audit JSON.")


if __name__ == "__main__":
    main()

