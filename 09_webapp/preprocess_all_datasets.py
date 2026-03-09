#!/usr/bin/env python3
"""
Multi-dataset preprocessor for AeroTrace web app.
Processes all 11 datasets (C-MAPSS FD001-FD004 + N-CMAPSS DS01-DS07) into JSON.

Output:
  public/data/datasets.json           — manifest (id, label, engine/cycle counts)
  public/data/{id}/fleet_summary.json  — per-engine last-cycle snapshot + stats
  public/data/{id}/engines/engine_{n}.json — per-engine full timeline

Usage:
  python preprocess_all_datasets.py
"""

import json, os, sys, csv, math
from pathlib import Path
from collections import defaultdict

# ─── Configuration ───────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # AeroTrace 2/
WEBAPP_DATA = Path(__file__).resolve().parent / "public" / "data"

# Dataset sources: (id, label, csv_path, format)
DATASETS = [
    # C-MAPSS v2 (FD001 has v2 in demo outputs)
    ("FD001", "C-MAPSS FD001", PROJECT_ROOT / "demo/decision_support_v2_outputs/fd001_decision_support_v2.csv", "v2_fd"),
    # C-MAPSS v1 (FD002-FD004)
    ("FD002", "C-MAPSS FD002", PROJECT_ROOT / "JET-CUBE-public/01_data/processed/outputs/FD002/fd002_decision_support.csv", "v1"),
    ("FD003", "C-MAPSS FD003", PROJECT_ROOT / "JET-CUBE-public/01_data/processed/outputs/FD003/fd003_decision_support.csv", "v1"),
    ("FD004", "C-MAPSS FD004", PROJECT_ROOT / "JET-CUBE-public/01_data/processed/outputs/FD004/fd004_decision_support.csv", "v1"),
    # N-CMAPSS v2 (DS01-DS07)
    ("DS01", "N-CMAPSS DS01", PROJECT_ROOT / "demo/decision_support_v2_outputs/ncmapss_DS01_decision_support_v2.csv", "v2_ncmapss"),
    ("DS02", "N-CMAPSS DS02", PROJECT_ROOT / "demo/decision_support_v2_outputs/ncmapss_DS02_decision_support_v2.csv", "v2_ncmapss"),
    ("DS03", "N-CMAPSS DS03", PROJECT_ROOT / "demo/decision_support_v2_outputs/ncmapss_DS03_decision_support_v2.csv", "v2_ncmapss"),
    ("DS04", "N-CMAPSS DS04", PROJECT_ROOT / "demo/decision_support_v2_outputs/ncmapss_DS04_decision_support_v2.csv", "v2_ncmapss"),
    ("DS05", "N-CMAPSS DS05", PROJECT_ROOT / "demo/decision_support_v2_outputs/ncmapss_DS05_decision_support_v2.csv", "v2_ncmapss"),
    ("DS06", "N-CMAPSS DS06", PROJECT_ROOT / "demo/decision_support_v2_outputs/ncmapss_DS06_decision_support_v2.csv", "v2_ncmapss"),
    ("DS07", "N-CMAPSS DS07", PROJECT_ROOT / "demo/decision_support_v2_outputs/ncmapss_DS07_decision_support_v2.csv", "v2_ncmapss"),
]

LABEL_ACTIONS = {
    "Normal Operation": "Rutin izleme",
    "Enhanced Monitoring": "İzleme sıklığını artır",
    "Planned Maintenance": "Bakım planla",
    "Immediate Maintenance": "Acil müdahale gerekli",
}

def parse_row_v2_fd(row):
    """Parse FD001 v2 format (no dataset_id/split prefix)."""
    return {
        "engineId": int(row["asset_id"]),
        "t": int(row["t"]),
        "rul": round(float(row["rul_pred"]), 2),
        "anomRaw": round(float(row["anomaly_score_raw"]), 6),
        "anomSmooth": round(float(row["anomaly_score_smoothed"]), 6),
        "anomState": row["anomaly_state"],
        "label": row["decision_label"],
        "reasonCodes": row.get("reason_codes", ""),
        "reasonText": row.get("reason_text", ""),
        "action": row.get("recommended_action_text", ""),
        "theta": round(float(row.get("theta_rul_used", 30)), 1),
        "alphaHigh": round(float(row.get("alpha_high_used", 0.5)), 4),
        "alphaLow": round(float(row.get("alpha_low_used", 0)), 4),
        "policyVersion": row.get("policy_version", ""),
        "runId": row.get("run_id", ""),
    }

def parse_row_v2_ncmapss(row):
    """Parse N-CMAPSS v2 format (has dataset_id, split, asset_id)."""
    return {
        "engineId": int(row["asset_id"]),
        "t": int(row["t"]),
        "rul": round(float(row["rul_pred"]), 2),
        "anomRaw": round(float(row["anomaly_score_raw"]), 6),
        "anomSmooth": round(float(row["anomaly_score_smoothed"]), 6),
        "anomState": row["anomaly_state"],
        "label": row["decision_label"],
        "reasonCodes": row.get("reason_codes", ""),
        "reasonText": row.get("reason_text", ""),
        "action": row.get("recommended_action_text", ""),
        "theta": round(float(row.get("theta_rul_used", 30)), 1),
        "alphaHigh": round(float(row.get("alpha_high_used", 0.5)), 4),
        "alphaLow": round(float(row.get("alpha_low_used", 0)), 4),
        "policyVersion": row.get("policy_version", ""),
        "runId": row.get("run_id", ""),
        "split": row.get("split", ""),
    }

def parse_row_v1(row):
    """Parse C-MAPSS v1 format (FD002-FD004)."""
    anom = round(float(row.get("anomaly_score", 0)), 6)
    theta = round(float(row.get("theta_rul_used", 50)), 1)
    alpha = round(float(row.get("alpha_anomaly_used", 0.5)), 4)
    return {
        "engineId": int(row["engine_id"]),
        "t": int(row["cycle"]),
        "rul": round(float(row["rul_pred"]), 2),
        "anomRaw": anom,
        "anomSmooth": anom,  # v1 has no smoothed — use raw
        "anomState": "ON" if anom >= alpha else "OFF",
        "label": row["decision_label"],
        "reasonCodes": row.get("reason_codes", ""),
        "reasonText": row.get("reason_text", ""),
        "action": LABEL_ACTIONS.get(row["decision_label"], ""),
        "theta": theta,
        "alphaHigh": alpha,
        "alphaLow": round(alpha * 0.9, 4),
        "policyVersion": "v1",
        "runId": "",
    }

def process_dataset(ds_id, ds_label, csv_path, fmt):
    """Process a single dataset CSV into fleet_summary.json + engine JSONs."""
    print(f"  Processing {ds_id} ({ds_label})...")
    
    if not csv_path.exists():
        print(f"    ⚠ CSV not found: {csv_path}")
        return None

    # Parse CSV
    engines = defaultdict(list)
    parser = {"v2_fd": parse_row_v2_fd, "v2_ncmapss": parse_row_v2_ncmapss, "v1": parse_row_v1}[fmt]
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = parser(row)
            engines[parsed["engineId"]].append(parsed)

    if not engines:
        print(f"    ⚠ No data rows for {ds_id}")
        return None

    # Sort each engine timeline by cycle
    for eid in engines:
        engines[eid].sort(key=lambda r: r["t"])

    # Output directory
    out_dir = WEBAPP_DATA / ds_id
    engines_dir = out_dir / "engines"
    engines_dir.mkdir(parents=True, exist_ok=True)

    # Generate engine JSON files
    for eid, timeline in engines.items():
        # Remove split field from final JSON (N-CMAPSS specific)
        for row in timeline:
            row.pop("split", None)
        
        engine_path = engines_dir / f"engine_{eid}.json"
        with open(engine_path, "w", encoding="utf-8") as f:
            json.dump(timeline, f, ensure_ascii=False)

    # Generate fleet summary
    total_cycles = 0
    label_counts = defaultdict(int)
    fleet_engines = []

    for eid, timeline in sorted(engines.items()):
        last = timeline[-1]
        total_cycles += len(timeline)
        label_counts[last["label"]] += 1

        # Detect transitions
        transitions = []
        for i in range(1, len(timeline)):
            if timeline[i]["label"] != timeline[i - 1]["label"]:
                transitions.append({
                    "cycle": timeline[i]["t"],
                    "from": timeline[i - 1]["label"],
                    "to": timeline[i]["label"],
                })

        fleet_engines.append({
            "id": eid,
            "maxCycle": last["t"],
            "rul": last["rul"],
            "anomSmooth": last["anomSmooth"],
            "label": last["label"],
            "theta": last["theta"],
            "alphaHigh": last["alphaHigh"],
            "transitions": len(transitions),
        })

    summary = {
        "datasetId": ds_id,
        "datasetLabel": ds_label,
        "totalEngines": len(engines),
        "totalCycles": total_cycles,
        "labelCounts": dict(label_counts),
        "engines": fleet_engines,
    }

    summary_path = out_dir / "fleet_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    print(f"    ✓ {len(engines)} engines, {total_cycles} cycles → {out_dir}")
    return {
        "id": ds_id,
        "label": ds_label,
        "engines": len(engines),
        "cycles": total_cycles,
        "labels": dict(label_counts),
    }


def main():
    print("AeroTrace Multi-Dataset Preprocessor")
    print("=" * 50)

    manifest = []
    for ds_id, ds_label, csv_path, fmt in DATASETS:
        result = process_dataset(ds_id, ds_label, csv_path, fmt)
        if result:
            manifest.append(result)

    # Write datasets manifest
    manifest_path = WEBAPP_DATA / "datasets.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Done: {len(manifest)} datasets processed")
    print(f"   Manifest: {manifest_path}")
    for m in manifest:
        print(f"   {m['id']}: {m['engines']} engines, {m['cycles']} cycles")


if __name__ == "__main__":
    main()
