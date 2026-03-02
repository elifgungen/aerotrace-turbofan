# FD004 Repro Fix Report (BASE/A/B) — PASS Criteria Audit

Bu PR, **FD004** için “A/B/C” belirsizliğini repo gerçekliğine indirgedi ve **BASE/A/B** tutarlılığı + repo-relative reproducibility + preprocess kanıt zinciri ekledi.

## Kapsam kararı (bu PR)
- Bu repo’da **C varyantı yok**; bu PR’da **C eklenmedi**.
- Resmi kapsam artık: **BASE, A, B**.

## Kapatılan FAIL maddeleri (kanıtlı)

### 1) BLOCKER — “A/B/C” yerine BASE/A/B tutarlılığı
- Runner yalnızca BASE/A/B çalıştırır: `scripts/train_fd004_variants.py:210`
- Notebook DATASETS yalnızca BASE/A/B içerir ve repo-relative: `02_notebooks_exports/RUL/FD004/FD004_compare_BASE_A_B_OzcanMetrics_CAP125.ipynb:111`

### 2) HIGH — Hard-coded Windows path kaldırıldı (repo-relative)
- Notebook’ta A/B path’leri artık repo-relative: `02_notebooks_exports/RUL/FD004/FD004_compare_BASE_A_B_OzcanMetrics_CAP125.ipynb:119`
- Windows path kalmadı (ör. `C:\\Havelsan\\...`): `02_notebooks_exports/RUL/FD004/FD004_compare_BASE_A_B_OzcanMetrics_CAP125.ipynb:119`
- Runner’da missing file SKIP yok; net hata: `scripts/train_fd004_variants.py:50`

### 3) MED — Preprocess üretim script’i + train-only fit meta kanıtı
- A/B varyant üretimi (BASE’den) script’i: `scripts/build_fd004_variants.py:95`
- KMeans fit sadece train’de (train-only): `scripts/build_fd004_variants.py:127`
- Üretilen meta json’larda `fit_split=train_only`: `scripts/build_fd004_variants.py:139`, `scripts/build_fd004_variants.py:163`
- Build report JSON: `scripts/build_fd004_variants.py:183`

### 4) LOW — OOF’da estimator clone
- Runner OOF’da clone kullanır: `scripts/train_fd004_variants.py:124`
- Notebook OOF’da clone kullanır: `02_notebooks_exports/RUL/FD004/FD004_compare_BASE_A_B_OzcanMetrics_CAP125.ipynb:379`

### 5) MED — Metrik raporlama (RMSE primary + secondary açık)
- Seçim kuralı açıkça string olarak yazılır: `scripts/train_fd004_variants.py:173`
- Secondary metrikler raporda gösterilir (tau precision/recall): `scripts/train_fd004_variants.py:317`

## Repro komutları
1) A/B varyant üret (default BASE input path’leri ile):
   - Komut:
     - `python scripts/build_fd004_variants.py --base-train-csv 01_data/processed/CMAPSS_full_norm/FD004/FD004_full_global_zscore/train_FD004_full_global_zscore_nodrop.csv --base-test-csv 01_data/processed/CMAPSS_full_norm/FD004/FD004_full_global_zscore/test_FD004_full_global_zscore_nodrop.csv --out-dir 01_data/processed/CMAPSS_full_norm/FD004/_generated_variants --k 6 --seed 42 --ddof 1`
   - Beklenen çıktılar:
     - `01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/build_report.json`
     - `01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/A_global_zscore_regime_onehot_k6/train_FD004_global_zscore_regime_onehot_k6.csv`
     - `01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/A_global_zscore_regime_onehot_k6/test_FD004_global_zscore_regime_onehot_k6.csv`
     - `01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/A_global_zscore_regime_onehot_k6/fd004_regime_k6_model.json`
     - `01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/B_regimeaware_sensor_zscore_k6_onehot/train_FD004_regimeaware_sensor_zscore_k6_onehot.csv`
     - `01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/B_regimeaware_sensor_zscore_k6_onehot/test_FD004_regimeaware_sensor_zscore_k6_onehot.csv`
     - `01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/B_regimeaware_sensor_zscore_k6_onehot/fd004_regimeaware_sensor_scaler_k6.json`

2) Train/eval (BASE/A/B; leakage-safe OOF stacking):
   - Komut:
     - `python scripts/train_fd004_variants.py --cap 125 --tau 15 --seed 42 --stacking-folds 5 --out-dir outputs/fd004 --base-train-csv 01_data/processed/CMAPSS_full_norm/FD004/FD004_full_global_zscore/train_FD004_full_global_zscore_nodrop.csv --base-test-csv 01_data/processed/CMAPSS_full_norm/FD004/FD004_full_global_zscore/test_FD004_full_global_zscore_nodrop.csv --a-train-csv 01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/A_global_zscore_regime_onehot_k6/train_FD004_global_zscore_regime_onehot_k6.csv --a-test-csv 01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/A_global_zscore_regime_onehot_k6/test_FD004_global_zscore_regime_onehot_k6.csv --b-train-csv 01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/B_regimeaware_sensor_zscore_k6_onehot/train_FD004_regimeaware_sensor_zscore_k6_onehot.csv --b-test-csv 01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/B_regimeaware_sensor_zscore_k6_onehot/test_FD004_regimeaware_sensor_zscore_k6_onehot.csv`
   - Beklenen çıktılar:
     - `outputs/fd004/best_per_variant.csv`
     - `outputs/fd004/best_per_variant.json`
     - `outputs/fd004/BASE/metrics.csv`
     - `outputs/fd004/BASE/report.md`
     - `outputs/fd004/A/metrics.csv`
     - `outputs/fd004/A/report.md`
     - `outputs/fd004/B/metrics.csv`
     - `outputs/fd004/B/report.md`

Alternatif (tek komut):
- `python scripts/run_fd004.py --cap 125 --tau 15 --seed 42 --k 6 --ddof 1 --stacking-folds 5 --variants-out-dir 01_data/processed/CMAPSS_full_norm/FD004/_generated_variants --out-dir outputs/fd004`

## Beklenen artefact’lar (çalıştırma sonrası)
- Variant build: `01_data/processed/CMAPSS_full_norm/FD004/_generated_variants/build_report.json`: `scripts/build_fd004_variants.py:219`
- Runner outputs: `outputs/fd004/*/metrics.csv`, `outputs/fd004/*/report.md`: `scripts/train_fd004_variants.py:297`, `scripts/train_fd004_variants.py:325`
- Aggregate: `outputs/fd004/best_per_variant.csv`: `scripts/train_fd004_variants.py:328`

## Kalan riskler
- **MED:** Ortamda `lightgbm`/`catboost` yoksa runner çalışmaz (install gerektirir): `scripts/train_fd004_variants.py:20`, `scripts/train_fd004_variants.py:28`
- **LOW:** `scripts/build_fd004_variants.py` KMeans `n_init='auto'` sklearn sürümüne bağlı davranabilir; seed ile deterministik amaçlandı: `scripts/build_fd004_variants.py:32`
