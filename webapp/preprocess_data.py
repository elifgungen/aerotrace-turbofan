#!/usr/bin/env python3
"""
Preprocess AeroTrace CSV data into compact JSON files for the web app.
Reads fd001_decision_support_v2.csv and produces:
  - public/data/fleet_summary.json   (per-engine last-cycle snapshot + aggregate stats)
  - public/data/engines/engine_{id}.json (full timeline per engine)

Now also integrates raw FD001 sensor data to compute per-cycle sensor
z-score deviations for XAI (Explainable AI) insights.
"""
import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "05_demo" / "decision_support_v2_outputs" / "fd001_decision_support_v2.csv"
OUT = Path(__file__).resolve().parent / "public" / "data"

# Raw FD001 sensor data
RAW_FD001 = Path(__file__).resolve().parent.parent / "01_data" / "raw" / "CMAPSS" / "FD001_raw_dataset" / "train_FD001.txt"

# ── Sensor Configuration ──────────────────────────────────────────────
# Column indices in train_FD001.txt (0-indexed):
#   0: unit_id, 1: cycle, 2-4: operational settings, 5-25: sensors s1-s21
SENSOR_COLS = {
    "s2":  {"idx": 6,  "name": "T24",     "fullName": "LPC çıkış sıcaklığı (T24)",         "unit": "°R"},
    "s3":  {"idx": 7,  "name": "T30",     "fullName": "HPC çıkış sıcaklığı (T30)",         "unit": "°R"},
    "s4":  {"idx": 8,  "name": "T50",     "fullName": "LPT çıkış sıcaklığı (T50)",         "unit": "°R"},
    "s7":  {"idx": 11, "name": "P30",     "fullName": "HPC çıkış basıncı (P30)",           "unit": "psia"},
    "s8":  {"idx": 12, "name": "Nf",      "fullName": "Fiziksel fan hızı (Nf)",             "unit": "rpm"},
    "s9":  {"idx": 13, "name": "Nc",      "fullName": "Fiziksel çekirdek hızı (Nc)",        "unit": "rpm"},
    "s11": {"idx": 15, "name": "Ps30",    "fullName": "HPC statik basınç (Ps30)",          "unit": "psia"},
    "s12": {"idx": 16, "name": "phi",     "fullName": "Yakıt akış oranı (phi)",            "unit": "pps/psi"},
    "s13": {"idx": 17, "name": "NRf",     "fullName": "Düzeltilmiş fan hızı (NRf)",        "unit": "rpm"},
    "s14": {"idx": 18, "name": "NRc",     "fullName": "Düzeltilmiş çekirdek hızı (NRc)",   "unit": "rpm"},
    "s15": {"idx": 19, "name": "BPR",     "fullName": "Bypass oranı (BPR)",                "unit": "—"},
    "s17": {"idx": 21, "name": "htBleed", "fullName": "Bleed entalpisi (htBleed)",          "unit": "—"},
    "s20": {"idx": 24, "name": "W31",     "fullName": "HPT soğutma havası (W31)",          "unit": "lbm/s"},
    "s21": {"idx": 25, "name": "W32",     "fullName": "LPT soğutma havası (W32)",          "unit": "lbm/s"},
}

BASELINE_CYCLES = 10  # first N cycles as healthy reference
MAX_TOP_SENSORS = 5
Z_THRESHOLD_INFO = 1.5
Z_THRESHOLD_WARNING = 2.5
Z_THRESHOLD_CRITICAL = 4.0


def load_raw_sensors():
    """Load raw FD001 sensor data and return dict: {engine_id: {cycle: {sensor_id: value}}}"""
    if not RAW_FD001.exists():
        print(f"⚠️  Raw sensor file not found: {RAW_FD001}", file=sys.stderr)
        print("   Sensor insights will be empty.", file=sys.stderr)
        return None

    print(f"📡 Loading raw sensor data from {RAW_FD001.name}...")
    engines = defaultdict(dict)  # {eid: {cycle: {sid: val}}}

    with open(RAW_FD001) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 26:
                continue
            eid = int(parts[0])
            cycle = int(parts[1])
            sensor_vals = {}
            for sid, info in SENSOR_COLS.items():
                sensor_vals[sid] = float(parts[info["idx"]])
            engines[eid][cycle] = sensor_vals

    print(f"   Loaded {sum(len(v) for v in engines.values())} rows for {len(engines)} engines")
    return dict(engines)


def compute_baselines(raw_sensors):
    """Compute per-engine baseline mean & std from first N cycles."""
    baselines = {}  # {eid: {sid: {"mean": m, "std": s}}}

    for eid, cycles in raw_sensors.items():
        sorted_cycles = sorted(cycles.keys())
        baseline_cycles = sorted_cycles[:BASELINE_CYCLES]
        if len(baseline_cycles) < 3:
            continue

        baseline = {}
        for sid in SENSOR_COLS:
            vals = [cycles[c][sid] for c in baseline_cycles]
            n = len(vals)
            mean = sum(vals) / n
            variance = sum((v - mean) ** 2 for v in vals) / max(n - 1, 1)
            std = math.sqrt(variance)
            baseline[sid] = {"mean": mean, "std": std}

        baselines[eid] = baseline

    return baselines


def compute_sensor_insights(eid, cycle, raw_sensors, baselines, label, rul=None, anom_smooth=None):
    """Compute sensor z-scores and generate insights for a single cycle."""
    if not raw_sensors or eid not in raw_sensors or eid not in baselines:
        # No raw data at all — generate text-only insights from RUL/anomaly
        summary_tr = _generate_summary_tr([], label, 0, rul, anom_smooth)
        return {
            "topSensors": [],
            "summary_tr": summary_tr,
            "overallDeviation": 0,
        }

    # Try exact cycle, otherwise fall back to closest available
    engine_cycles = raw_sensors[eid]
    cycle_data = engine_cycles.get(cycle)
    if cycle_data is None:
        # Use the closest available cycle (last known if cycle is beyond raw data)
        available = sorted(engine_cycles.keys())
        if not available:
            summary_tr = _generate_summary_tr([], label, 0, rul, anom_smooth)
            return {"topSensors": [], "summary_tr": summary_tr, "overallDeviation": 0}
        closest = min(available, key=lambda c: abs(c - cycle))
        cycle_data = engine_cycles[closest]

    baseline = baselines[eid]

    # Compute z-scores
    scored = []
    for sid, info in SENSOR_COLS.items():
        bl = baseline.get(sid)
        if not bl or bl["std"] < 1e-9:
            continue  # skip constant sensors
        val = cycle_data[sid]
        z = (val - bl["mean"]) / bl["std"]
        abs_z = abs(z)

        if abs_z < Z_THRESHOLD_INFO:
            continue  # not significant

        severity = "critical" if abs_z >= Z_THRESHOLD_CRITICAL else "warning" if abs_z >= Z_THRESHOLD_WARNING else "info"
        direction = "up" if z > 0 else "down"

        # Percent change from baseline
        pct_change = round(((val - bl["mean"]) / abs(bl["mean"])) * 100, 1) if abs(bl["mean"]) > 1e-9 else 0.0

        scored.append({
            "id": sid,
            "name": info["name"],
            "fullName": info["fullName"],
            "zscore": round(abs_z, 2),
            "direction": direction,
            "severity": severity,
            "pctChange": pct_change,
        })

    # Sort by z-score descending, limit to top N
    scored.sort(key=lambda x: x["zscore"], reverse=True)
    top = scored[:MAX_TOP_SENSORS]

    # Overall deviation (0-1 scale, max z / 6 capped)
    max_z = top[0]["zscore"] if top else 0
    overall = round(min(max_z / 6.0, 1.0), 2)

    # Generate Turkish summary
    summary_tr = _generate_summary_tr(top, label, overall, rul, anom_smooth)

    return {
        "topSensors": top,
        "summary_tr": summary_tr,
        "overallDeviation": overall,
    }


def _generate_summary_tr(top_sensors, label, overall_deviation, rul=None, anom_smooth=None):
    """Generate a Turkish human-readable summary based on decision label and top sensors.
    Always produces user-friendly text — never technical jargon."""

    # ── Normal Operation ──
    if label == "Normal Operation":
        if not top_sensors:
            return "✅ Tüm sensörler normal aralıkta. Motor sağlıklı çalışıyor."
        # Normal but some low-level deviations
        return (
            f"✅ Motor normal çalışıyor. {top_sensors[0]['fullName']} sensöründe "
            f"küçük bir değişim gözlemleniyor ancak eşik değerleri dahilinde."
        )

    # ── With sensor attribution ──
    if top_sensors:
        top = top_sensors[0]
        direction_tr = "artış" if top["direction"] == "up" else "düşüş"
        pct_str = f"%{abs(top['pctChange']):.0f}" if abs(top.get("pctChange", 0)) >= 1 else ""

        if label == "Enhanced Monitoring":
            extra = ""
            if len(top_sensors) > 1:
                extra = f" {top_sensors[1]['fullName']} sensöründe de değişim gözlemleniyor."
            return (
                f"🔍 Anomali sinyali algılandı; {top['fullName']} normalin "
                f"{'üzerinde' if top['direction'] == 'up' else 'altında'}"
                f"{' (' + pct_str + ' ' + direction_tr + ')' if pct_str else ''}. "
                f"İzleme artırılmalı.{extra}"
            )

        if label == "Planned Maintenance":
            extra = ""
            if len(top_sensors) > 1:
                names = ", ".join(s["fullName"] for s in top_sensors[1:3])
                extra = f" Ayrıca {names} sensörlerinde de sapma tespit edildi."
            return (
                f"🟠 Kalan ömür eşik altına düştü. {top['fullName']} trend analizi "
                f"planlı bakımı destekliyor"
                f"{' (' + pct_str + ' ' + direction_tr + ')' if pct_str else ''}.{extra}"
            )

        # Immediate Maintenance with sensors
        extra_sensors = ""
        if len(top_sensors) > 1:
            names = " ve ".join(s["fullName"] for s in top_sensors[1:3])
            extra_sensors = f" {names} sensörlerinde de anormal değişim tespit edildi."
        return (
            f"⚠️ Kritik sapma: {top['fullName']} başlangıca göre "
            f"{pct_str + ' ' if pct_str else ''}{direction_tr} gösterdi (z={top['zscore']:.1f}). "
            f"Anomali skoru yüksek ve RUL eşik altında. Acil müdahale önerilir."
            f"{extra_sensors}"
        )

    # ── Without sensor attribution (fallback — uses RUL/anomaly info) ──
    rul_str = f"{rul:.0f}" if rul is not None else "?"
    anom_str = f"{anom_smooth:.2f}" if anom_smooth is not None else "?"

    if label == "Enhanced Monitoring":
        return (
            f"🔍 Anomali skoru yükseldi ({anom_str}). Motorun bozulma sürecine "
            f"girmiş olabileceğine dair erken sinyaller mevcut. "
            f"Kalan ömür tahmini: {rul_str} çevrim. İzleme sıklığının artırılması önerilir."
        )

    if label == "Planned Maintenance":
        return (
            f"🟠 Motorun tahmini kalan ömrü ({rul_str} çevrim) eşik değerinin altına düştü. "
            f"Anomali skoru: {anom_str}. Sensör trend analizi bozulma sürecini destekliyor. "
            f"Planlı bakım zamanlaması için değerlendirme yapılmalı."
        )

    # Immediate Maintenance without sensors
    return (
        f"⚠️ Acil bakım gerekiyor! Motorun tahmini kalan ömrü yalnızca {rul_str} çevrim "
        f"ve anomali skoru kritik seviyede ({anom_str}). Motorun bozulma süreci ilerlemiş durumda. "
        f"Uçuş güvenliği için derhal bakım planlanmalı."
    )


def main():
    if not SRC.exists():
        print(f"ERROR: {SRC} not found", file=sys.stderr)
        sys.exit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "engines").mkdir(exist_ok=True)

    # ── Load raw sensor data for XAI ──
    raw_sensors = load_raw_sensors()
    baselines = compute_baselines(raw_sensors) if raw_sensors else {}

    engines = defaultdict(list)
    all_rows = []

    with open(SRC, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            eid = int(row["asset_id"])
            t = int(row["t"])
            rul = round(float(row["rul_pred"]), 2)
            anom_raw = round(float(row["anomaly_score_raw"]), 4)
            anom_smooth = round(float(row["anomaly_score_smoothed"]), 4)
            label = row["decision_label"]
            reason_codes = row.get("reason_codes", "")
            reason_text = row.get("reason_text", "")
            action = row.get("recommended_action_text", "")
            theta = float(row.get("theta_rul_used", 30))
            alpha_high = round(float(row.get("alpha_high_used", 0.8)), 4)
            alpha_low = round(float(row.get("alpha_low_used", 0.7)), 4)
            policy_version = row.get("policy_version", "v2")
            run_id = row.get("run_id", "")
            anomaly_state = row.get("anomaly_state", "OFF")

            rec = {
                "t": t,
                "rul": rul,
                "anomRaw": anom_raw,
                "anomSmooth": anom_smooth,
                "anomState": anomaly_state,
                "label": label,
                "reasonCodes": reason_codes,
                "reasonText": reason_text,
                "action": action,
                "theta": theta,
                "alphaHigh": alpha_high,
                "alphaLow": alpha_low,
            }

            # ── XAI: Sensor insights (always generated) ──
            insights = compute_sensor_insights(eid, t, raw_sensors, baselines, label, rul, anom_smooth)
            rec["sensorInsights"] = insights

            engines[eid].append(rec)
            all_rows.append((eid, rec))

    # Per-engine files
    for eid, rows in engines.items():
        rows.sort(key=lambda r: r["t"])
        with open(OUT / "engines" / f"engine_{eid}.json", "w") as f:
            json.dump(rows, f, separators=(",", ":"))

    # Fleet summary: last cycle per engine
    fleet = []
    label_counts = Counter()
    all_rul = []
    all_anom = []

    for eid, rows in sorted(engines.items()):
        rows.sort(key=lambda r: r["t"])
        last = rows[-1]
        max_cycle = last["t"]
        label_counts[last["label"]] += 1
        all_rul.append(last["rul"])
        all_anom.append(last["anomSmooth"])

        # Find transitions
        transitions = []
        prev_label = rows[0]["label"]
        for r in rows[1:]:
            if r["label"] != prev_label:
                transitions.append({"cycle": r["t"], "from": prev_label, "to": r["label"]})
                prev_label = r["label"]

        # Top sensor for fleet view
        top_sensor_str = ""
        si = last.get("sensorInsights")
        if si and si.get("topSensors"):
            ts = si["topSensors"][0]
            arrow = "↑" if ts["direction"] == "up" else "↓"
            top_sensor_str = f"{ts['name']} {arrow}{ts['zscore']}"

        fleet.append({
            "id": eid,
            "cycles": max_cycle,
            "rul": last["rul"],
            "anomSmooth": last["anomSmooth"],
            "anomRaw": last["anomRaw"],
            "label": last["label"],
            "reasonCodes": last["reasonCodes"],
            "action": last["action"],
            "transitions": transitions[-3:],  # last 3 transitions
            "topSensor": top_sensor_str,
        })

    total_rows = sum(len(v) for v in engines.values())
    summary = {
        "dataset": "FD001",
        "totalEngines": len(engines),
        "totalCycles": total_rows,
        "labelDistribution": {
            "Normal Operation": label_counts.get("Normal Operation", 0),
            "Enhanced Monitoring": label_counts.get("Enhanced Monitoring", 0),
            "Planned Maintenance": label_counts.get("Planned Maintenance", 0),
            "Immediate Maintenance": label_counts.get("Immediate Maintenance", 0),
        },
        "policyVersion": "v2",
        "runId": all_rows[0][1].get("run_id", "") if all_rows else "",
        "theta": 30.0,
        "engines": fleet,
    }

    with open(OUT / "fleet_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"✅ Generated fleet_summary.json ({len(fleet)} engines)")
    print(f"✅ Generated {len(engines)} engine timeline files")
    print(f"   Total rows processed: {total_rows}")
    print(f"   Labels: {dict(label_counts)}")

    # XAI summary
    engines_with_insights = sum(
        1 for rows in engines.values()
        if any("sensorInsights" in r for r in rows)
    )
    print(f"   🔬 Engines with sensor insights: {engines_with_insights}/{len(engines)}")


if __name__ == "__main__":
    main()
