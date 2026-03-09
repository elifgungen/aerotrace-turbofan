# Decision Support Output Schema

Bu doküman, repo içinde üretilen decision-support CSV kontratlarını tek yerde toplar.

Kaynak doğrulama:
- V1 örnek: `03_docs/Decision_Support/C-MAPSS/data/outputs/fd001_decision_support.csv`
- V2 örnekler: `OUTPUTS/fd001_decision_support_v2.csv`, `OUTPUTS/ncmapss_DS01_decision_support_v2.csv`

## 1) V1 Output Schema (Required)
V1 kontratı aşağıdaki kolonları zorunlu taşır:
- `engine_id`
- `cycle`
- `rul_pred`
- `anomaly_score`
- `decision_label`
- `reason_codes`
- `reason_text`
- `theta_rul_used`
- `alpha_anomaly_used`

Not:
- V1 legacy akışta dosya adı tipik olarak `*_decision_support.csv` şeklindedir.

## 2) V2 Output Schema (Required)
V2 kontratı (policy engine + adapter) aşağıdaki minimum kolonları taşır:
- `asset_id`
- `t`
- `rul_pred`
- `anomaly_score_raw`
- `anomaly_score_smoothed`
- `anomaly_state`
- `persistence_counter`
- `decision_label`
- `reason_codes`
- `reason_text`
- `theta_rul_used`
- `alpha_high_used`
- `alpha_low_used`
- `policy_version`
- `run_id`

Not:
- Mevcut adapter çıktılarında `dataset_id` ve `split` de bulunur.
- V2 dosya adı tipik olarak `*_decision_support_v2.csv` şeklindedir (veya `--out-suffix` ile).

## 3) V2 Optional Columns
V2’de sık görülen opsiyonel/audit yardımcı kolonlar:
- `prev_state`
- `new_state`
- `smoothing_params`
- `persistence_params`
- `recommended_action_text`
- `dataset_id`
- `split`

## 4) Canonical Schema
Canonical alan adları (dataset bağımsız):
- Kimlik/Zaman: `asset_id`, `t`
- Model çıktıları: `rul_pred`, `anomaly_score_raw`
- Karar çıktıları: `anomaly_state`, `decision_label`, `reason_codes`, `reason_text`
- Audit: `policy_version`, `run_id`, `theta_rul_used`, `alpha_high_used`, `alpha_low_used`

## 5) Dataset Mapping
| Dataset / Path | Input ID-Time | V2 Canonical ID-Time |
|---|---|---|
| C-MAPSS (legacy/v1 outputs) | `engine_id`, `cycle` | `asset_id <- engine_id`, `t <- cycle` |
| N-CMAPSS (adapter outputs) | `engine_id`, `cycle` (+ `dataset_id`, `split`) | `asset_id <- engine_id`, `t <- cycle` |

Ek not:
- V2 adapter join key keşfi sırasında `dataset_id` ve `split` bulunuyorsa join anahtarına dahil edilir.
