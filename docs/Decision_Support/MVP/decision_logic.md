# Decision Logic for Maintenance Decision Support (FD001, α–θ Thresholding)

This decision-support layer converts per-engine, per-cycle model outputs (predicted remaining useful life and anomaly scores) into simple, explainable maintenance recommendations. The core MVP contribution is an interpretable α–θ threshold mechanism that expresses “how urgent is this engine?” in maintenance language (monitor vs. plan inspection vs. immediate maintenance), with transparent conditions and rationales suitable for review by engineering and operations stakeholders.

## Scope & Non-Goals

**Scope (MVP)**
- Single-engine (per-unit) decision support demonstrated on NASA C-MAPSS FD001 (open benchmark) outputs.
- Batch/offline evaluation using per-engine-cycle records (no streaming requirement).
- Threshold-based, explainable logic that can be implemented directly in `notebooks/05_decision_support.ipynb`.

**Non-goals (out of scope for MVP)**
- Real-time deployment, alert routing, or MRO workflow integration.
- OEM-grade certification, safety case, or regulatory compliance artifacts.
- A fully physics-based digital twin (this is decision-support on top of statistical outputs).
- Automatic execution of maintenance actions (the layer recommends; humans decide).

## Configuration & Audit (Single Source of Truth)

This repository treats threshold/policy parameters as **configuration**, not hard-coded “defaults” in documentation:

- Canonical config: `config/decision_support_thresholds.json`
- Runner: `demo/decision_support_runner.py` supports `--config <json>` and writes the **actual used values** into outputs:
  - CSV columns: `theta_*_used`, `alpha_*_used`, `smooth_window_used`, `anom_debounce_*_used`, etc.
  - JSON report: includes `config_path` and the resolved thresholds.

Any numeric values shown below are **illustrative** unless explicitly stated as “config values”.

## Inputs (Data Contracts)

All inputs are expected at **per engine-cycle granularity** and share join keys `(engine_id, cycle)`.

### 1) `fd001_processed.csv` (sensor + cycle, processed)

**Expected columns (approximate; assumptions below)**
- `engine_id` (int): unit identifier.
- `cycle` (int): time index within engine run.
- Processed operating settings, e.g. `setting_1..setting_3` (float).
- Processed sensor features, e.g. `sensor_1..sensor_21` (float), possibly scaled/normalized.

**Granularity**
- One row per `(engine_id, cycle)`.

**How it is used in decisions (this layer)**
- Optional context only (e.g., to display sensor snapshots near alarms).
- Not required for the core α–θ logic (which is driven by RUL and anomaly outputs).

### 2) `fd001_rul_predictions.csv` (predicted RUL per engine-cycle)

**Expected columns (approximate; assumptions below)**
- `engine_id` (int)
- `cycle` (int)
- `RUL_pred` (float): predicted remaining useful life in **cycles** (higher = healthier).
- Optional: `model_name`, `RUL_true` (not required by this layer).

**Granularity**
- One row per `(engine_id, cycle)`.

**How it is used in decisions**
- Compared to θ (theta) thresholds to determine urgency based on remaining life.

### 3) `fd001_anomaly_scores.csv` (anomaly score per engine-cycle)

**Expected columns (approximate; assumptions below)**
- `engine_id` (int)
- `cycle` (int)
- `anomaly_score` (float): higher = more anomalous behavior.
- Optional: `method`, `score_version` (not required by this layer).

**Granularity**
- One row per `(engine_id, cycle)`.

**How it is used in decisions**
- Compared to α (alpha) thresholds to detect unusual behavior that may warrant inspection earlier than RUL alone.

> **Assumptions**
> - The three files can be left-joined on `(engine_id, cycle)` without duplicates (one row per key).
> - `RUL_pred` is in cycles and is monotone-decreasing “on average” over time but may be noisy.
> - `anomaly_score` is oriented such that “higher means more anomalous”; if the upstream method uses the opposite convention, it must be inverted before applying α thresholds.
> - Missing values are rare. If `RUL_pred` or `anomaly_score` is missing for a row, the MVP should return `state="degrading"` with a rationale indicating insufficient data (rather than silently defaulting to healthy).

## Decision Variables

**Core variables (per engine-cycle)**
- `RUL_pred`: predicted remaining useful life (cycles).
- `anomaly_score`: anomaly score (unitless; higher = more anomalous).

**Optional derived variables (MVP-friendly)**
- `anomaly_score_smooth`: rolling mean of `anomaly_score` over the last *w* cycles (e.g., `w=5`) per engine.
  - Rationale: anomaly detectors can produce spiky scores; light smoothing reduces false alarms while preserving trend.
- `RUL_pred_smooth`: optional rolling mean of `RUL_pred` (same window) to reduce jitter near thresholds.
- `risk_score` (0–100): an interpretable scalar used only for ranking/triage, not as the primary decision rule.
  - MVP suggestion: compute component risks from threshold proximity and take the maximum:
    - `rul_risk = clamp((θ_warn - RUL_pred) / (θ_warn - θ_critical), 0, 1)`
    - `anom_risk = clamp((anomaly_score - α_warn) / (α_critical - α_warn), 0, 1)`
    - `risk_score = round(100 * max(rul_risk, anom_risk))`

## Thresholds (α and θ)

This layer uses an Ozcan-style α–θ approach:
- **θ (theta)**: thresholds on `RUL_pred` (life-based urgency).
- **α (alpha)**: thresholds on `anomaly_score` (behavioral abnormality).

### θ_RUL thresholds (tunable parameters)

Define two RUL thresholds (in cycles):
- `θ_warn`: below this, plan an inspection / maintenance slot (lead-time region).
- `θ_critical`: below this, treat as urgent (minimal remaining life).

### α thresholds (tunable parameters)

Define two anomaly thresholds:
- `α_warn`: above this, the engine behavior is suspicious and should be checked.
- `α_critical`: above this, the anomaly evidence is strong enough to trigger urgent action even if RUL is not yet low.

### How we will set initial values for the MVP

These values are **not industry standard**; they are **tunable** and chosen to make the MVP interpretable and testable on FD001 outputs.

**Option A (recommended for FD001 MVP): quantile-based initialization**
- Compute thresholds on the model outputs across FD001 (or per engine, if desired):
  - `θ_warn` = 30th percentile of `RUL_pred`
  - `θ_critical` = 10th percentile of `RUL_pred`
  - `α_warn` = 90th percentile of `anomaly_score`
  - `α_critical` = 97th percentile of `anomaly_score`
- Advantages: adapts automatically to the scale and distribution of the specific model outputs.

**Option B: simple fixed defaults (useful for demos)**
- If `RUL_pred` is in cycles and roughly comparable across runs: start with `θ_warn=50`, `θ_critical=20`.
- If `anomaly_score` is normalized to `[0, 1]`: start with `α_warn=0.7`, `α_critical=0.9`.

### How thresholds would be calibrated later (post-MVP)

When real operational data exists (e.g., inspection findings, maintenance events, fault confirmations):
- Calibrate α and θ to meet target false-alarm rates and lead-time requirements.
- Use cost-aware trade-offs (missed detection vs. unnecessary maintenance) and confidence intervals.
- Add per-engine / per-operating-regime thresholds (contextual calibration) rather than global static values.

## State Machine / Decision Matrix (CORE)

The state machine is intentionally small and explainable:
- **HEALTHY**: continue normal monitoring.
- **DEGRADING**: increased risk; schedule inspection/maintenance planning.
- **CRITICAL**: high urgency; immediate maintenance action recommended.

### Decision matrix (α–θ logic)

Let `R = RUL_pred` (or `RUL_pred_smooth`) and `A = anomaly_score` (or `anomaly_score_smooth`).

| State | Condition (explainable rule) | Recommended maintenance action | Maintenance-language rationale |
|---|---|---|---|
| HEALTHY | `R > θ_warn` **AND** `A < α_warn` | Monitor (routine) | Plenty of remaining life and no abnormal behavior; continue standard monitoring. |
| DEGRADING | (`θ_critical < R ≤ θ_warn`) **OR** (`α_warn ≤ A < α_critical`) | Schedule inspection / plan maintenance | Either remaining life is entering the planning window or behavior is suspicious; allocate lead time and verify condition. |
| CRITICAL | `R ≤ θ_critical` **OR** `A ≥ α_critical` | Immediate maintenance / remove from service (per ops policy) | Remaining life is critically low and/or anomaly evidence is strong; risk of near-term failure is elevated. |

### Tie-breaks and stability (MVP-friendly)

To avoid flip-flopping near thresholds, the notebook may add one of the following simple stabilizers:
- **Consecutive-cycle requirement**: require the condition to hold for `N` consecutive cycles before escalating (e.g., `N=3` for anomaly-driven upgrades).
- **Hysteresis**: use slightly different thresholds for de-escalation (e.g., de-escalate from DEGRADING to HEALTHY only when `R > θ_warn + Δ` and `A < α_warn - Δ`).

These are optional; the base matrix above remains the source-of-truth decision rule.

## Output Schema (What the layer returns)

The layer returns one record per `(engine_id, cycle)` after joining inputs and applying the decision matrix.

| Field | Type | Description |
|---|---|---|
| `engine_id` | int | Engine/unit identifier. |
| `cycle` | int | Cycle index within engine history. |
| `state` | string | One of: `healthy`, `degrading`, `critical`. |
| `recommended_action` | string | Human-facing action label (monitor / schedule inspection / immediate maintenance). |
| `rationale` | string | Short, maintenance-language explanation for the chosen state. |
| `contributing_signals` | string[] | Machine-readable reasons, e.g. `["RUL_pred below θ_critical", "anomaly_score above α_warn"]`. |
| `risk_score` (optional) | int | 0–100 triage score derived from α–θ proximity (not required for decisions). |

## Example Walkthrough (Minimum 2 examples)

Assume the following thresholds for illustration (example only; actual values come from `config/decision_support_thresholds.json` and are written into artefacts as `*_used` fields):
- `θ_warn = 50`, `θ_critical = 20` (cycles)
- `α_warn = 0.70`, `α_critical = 0.90` (normalized anomaly score)

### Example A (low anomaly, high RUL → HEALTHY)

**Inputs**
- `engine_id=12`, `cycle=85`
- `RUL_pred = 120`
- `anomaly_score = 0.15`

**Step-by-step**
1. Compare RUL: `120 > θ_warn (50)` ⇒ life is not in the planning/critical window.
2. Compare anomaly: `0.15 < α_warn (0.70)` ⇒ no suspicious behavior.
3. Apply matrix: `R > θ_warn` AND `A < α_warn` ⇒ `state="healthy"`.

**Output (key fields)**
- `state="healthy"`, `recommended_action="monitor"`
- `contributing_signals=["RUL_pred above θ_warn", "anomaly_score below α_warn"]`

### Example B (high anomaly and/or low RUL → CRITICAL)

**Inputs**
- `engine_id=7`, `cycle=187`
- `RUL_pred = 18`
- `anomaly_score = 0.62`

**Step-by-step**
1. Compare RUL: `18 ≤ θ_critical (20)` ⇒ critically low remaining life.
2. Compare anomaly: `0.62 < α_warn (0.70)` ⇒ anomaly is not elevated, but this does not override the low-RUL urgency.
3. Apply matrix: `R ≤ θ_critical` ⇒ `state="critical"`.

**Output (key fields)**
- `state="critical"`, `recommended_action="immediate maintenance"`
- `contributing_signals=["RUL_pred below θ_critical"]`

> Optional additional check (common in practice): if `RUL_pred` is high but `anomaly_score ≥ α_critical`, the engine becomes `critical` due to strong abnormality evidence (potential sudden fault mode).

## MVP Limitations + Extension Path

**Limitations (acknowledged for MVP)**
- Static, global thresholds (α and θ) may not generalize across operating regimes or fleets.
- FD001 is a benchmark dataset; it does not represent full operational variability or confirmed maintenance events.
- No true physics-based degradation model; this is a decision-support layer on top of statistical outputs.
- Limited uncertainty handling (point predictions and scores, not calibrated probabilities by default).

**Extension path (post-acceptance roadmap)**
- Dynamic/contextual thresholds (per regime, per engine, or adaptive over time).
- Fleet-level aggregation and prioritization dashboards (rank engines by `risk_score` and trends).
- Physics-informed or hybrid twins (combine models with simplified degradation physics constraints).
- Integration with real sensor streams and alerting pipelines (streaming joins, real-time state updates).
- Add uncertainty-aware actions (e.g., “inspect to confirm” when confidence is low).

## Where this integrates in the repo

- The implementing notebook is `notebooks/05_decision_support.ipynb`.
- This document (`docs/decision_logic.md`) is the **source of truth** for the decision rules (α–θ thresholds, state machine, output schema) implemented in that notebook.
