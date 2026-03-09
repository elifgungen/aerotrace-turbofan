# Decision Logic v2 (Human-in-the-Loop Decision Support)

Bu katman otomatik bakım icrası yapmaz; deterministik ve audit edilebilir bir `öneri/uyarı` çıktısı üretir.

## 1) Girdiler
- `rul_pred`: Kalan ömür tahmini (cycle).
- `anomaly_score_raw`: Ham anomaly skoru.

Zorunlu kimlik/zaman kolonları:
- `id_cols` (örn. `dataset_id`, `split`, `asset_id`)
- `time_col` (örn. `t` / `cycle`)

## 2) Ön İşleme
- `anomaly_score_smoothed` uygulanır.
- v2 varsayılanı: `EMA` (`method=ema`, `span=7`).
- Alternatif: `rolling_median` (`window=7`).

Smoothing her asset için zaman sıralı yapılır.

## 3) Eşikler
### 3.1 Theta (RUL)
- `theta_rul.mode = fixed`
- `theta_rul.value` doğrudan kullanılır.

### 3.2 Alpha (Anomaly)
- `alpha_anomaly.mode = fixed` ise `alpha_high = value`
- `alpha_anomaly.mode = quantile` ise:
  - `alpha_high = quantile(anomaly_score_smoothed, q)`

### 3.3 Hysteresis
- `alpha_low = alpha_high * alpha_low_multiplier`
- Beklenen: `alpha_low < alpha_high`
- `alpha_high_multiplier` varsa `alpha_high` üzerine uygulanır.

## 4) Persistence (ON Latch)
Her asset için zaman sıralı state machine:
- `candidate_on`: `anomaly_score_smoothed >= alpha_high`
- `candidate_off`: `anomaly_score_smoothed <= alpha_low`
- `min_persistence_cycles` (`min_cycles_on`) sağlanmadan `ON` state’e geçilmez.
- MVP: `candidate_off` geldiğinde state `OFF`’a döner (OFF için ayrıca persistence zorunlu değil).

## 5) Karar Matrisi (4-sınıf)
Boyutlar:
- `anomaly_state` in `{OFF, ON}`
- `rul_low` in `{RUL <= theta, RUL > theta}`

| anomaly_state | RUL durumu | decision_label | reason_codes (base) | recommended_action_text |
|---|---|---|---|---|
| OFF | RUL > theta | `Normal Operation` | `RUL_HIGH|ANOM_OFF` | Rutin izleme |
| ON | RUL > theta | `Enhanced Monitoring` | `RUL_HIGH|ANOM_ON` | İzleme artır + teşhis |
| OFF | RUL <= theta | `Planned Maintenance` | `RUL_LOW|ANOM_OFF` | Planlı bakım/inspection |
| ON | RUL <= theta | `Immediate Maintenance` | `RUL_LOW|ANOM_ON` | Acil bakım kararı için yükselt |

Ek reason code’lar (duruma göre):
- `PERSISTENCE_PENDING`
- `STATE_CHANGE_OFF_TO_ON`
- `STATE_CHANGE_ON_TO_OFF`

## 6) Audit Alanları
Her çıktı satırında aşağıdaki alanlar taşınır:
- `policy_version`
- `run_id`
- `theta_rul_used`
- `alpha_high_used`
- `alpha_low_used`
- `smoothing_params`
- `persistence_params`
- `prev_state`
- `new_state`
- `persistence_counter`

Bu sayede tüm kararlar tekrar üretilebilir (deterministik + izlenebilir).

Implementasyon notu:
- `run_id` formatı: `ds-YYYYMMDDTHHMMSSZ-<10hex>` (UTC timestamp + policy config hash).
- `policy_version`, `configs/decision_support.yaml` içindeki `policy.version` alanından set edilir (varsayılan `v2`).

## 7) Safety Positioning (Jüri Notu)
- Bu katman **human-in-the-loop decision support** içindir; safety-critical bir kontrolcü değildir.
- `smoothing + hysteresis + persistence` birlikte alarm flip-flop davranışını azaltır ve yanlış alarm riskini düşürür.
- `policy_version + run_id + *_used threshold` alanları satır bazında audit izini sağlar.
