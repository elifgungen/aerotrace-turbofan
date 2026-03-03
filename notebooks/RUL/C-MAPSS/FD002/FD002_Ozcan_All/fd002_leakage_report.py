#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import pandas as pd


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate leakage evidence report from FD002 OOF predictions.")
    ap.add_argument("--oof", required=True, help="Path to fd002_oof_predictions*.csv")
    ap.add_argument("--out", required=True, help="Path to write JSON report")
    args = ap.parse_args()

    oof_path = Path(args.oof)
    out_path = Path(args.out)

    df = pd.read_csv(oof_path)
    required = {"engine_id", "cycle", "fold", "y_true", "y_pred"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"OOF missing required columns: {missing}")

    # Core leakage invariant: each engine must be assigned to exactly one fold.
    engine_fold_nunique = df.groupby("engine_id")["fold"].nunique()
    bad = engine_fold_nunique[engine_fold_nunique > 1]

    folds = sorted(int(f) for f in df["fold"].unique().tolist())
    per_fold = []
    all_engines = set(df["engine_id"].unique().tolist())

    for f in folds:
        df_f = df[df["fold"] == f]
        val_engines = set(df_f["engine_id"].unique().tolist())
        train_engines = all_engines - val_engines
        overlap = sorted(list(val_engines.intersection(train_engines)))
        per_fold.append(
            {
                "fold": int(f),
                "valid_rows": int(len(df_f)),
                "valid_engines": int(len(val_engines)),
                "train_engines": int(len(train_engines)),
                "engine_overlap": int(len(overlap)),
            }
        )

    report: Dict[str, Any] = {
        "generated_utc": _utc_now_iso(),
        "oof_path": str(oof_path),
        "rows": int(len(df)),
        "unique_engines": int(len(all_engines)),
        "folds": folds,
        "blocker_engine_multi_fold_count": int(len(bad)),
        "blocker_engine_multi_fold_sample": bad.head(10).to_dict(),
        "per_fold_evidence": per_fold,
        "passed": bool(len(bad) == 0 and all(x["engine_overlap"] == 0 for x in per_fold)),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

