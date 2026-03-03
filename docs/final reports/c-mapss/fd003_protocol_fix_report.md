# FD003 Protocol Fix Report (Leakage-Free) — PASS Criteria Audit

Bu PR, **FD003** için önceki FAIL bulgularını kapatmak amacıyla **runner’ı “source of truth”** yaptı ve notebook’u leakage kaynaklarını kaldıracak şekilde “demo-only” hale getirdi.

## Kapsam (bu PR)
- Decision-support entegrasyonu: **YOK**
- Anomaly üretimi: **YOK**

## Kapatılan FAIL maddeleri (kanıtlı)

### 1) BLOCKER — Test leakage (CatBoost eval_set test set) kaldırıldı
- Leakage-free kuralı kodda açık: `scripts/train_fd003.py:114`
- CatBoost early stopping eval_set **yalnızca train fold içinden** ayrılıyor: `scripts/train_fd003.py:116`
- Final fit aşamasında da eval_set **train içinden**: `scripts/train_fd003.py:300`
- Notebook tarafında “holdout test eval_set değil” fix notu: `notebooks/RUL/FD003/FD003_train_ensemble_sensors_plus_cycle_CAP125_with_metrics_export.ipynb:900`

### 2) HIGH — “best” seçimi test RMSE ile yapılmıyor (CV mean/std ile)
- CV split: `GroupKFold(engine_id)` kurallı split: `scripts/train_fd003.py:224`
- Fold bazlı metrik toplama (CV): `scripts/train_fd003.py:231`
- CV mean/std özet + **best_model seçimi**: `scripts/train_fd003.py:256`, `scripts/train_fd003.py:263`, `scripts/train_fd003.py:265`
- Best seçim metadata’da “test excluded” olarak yazılıyor: `scripts/train_fd003.py:285`
- Notebook’ta test-RMSE ile best seçimi kaldırılıp manuel export’a dönüldü: `notebooks/RUL/FD003/FD003_train_ensemble_sensors_plus_cycle_CAP125_with_metrics_export.ipynb:1539`

### 3) HIGH — Stacking OOF olmayan meta-training kaldırıldı / OOF stacking eklendi
- OOF base pred üretimi (GroupKFold): `scripts/train_fd003.py:146`
- Meta modelin fold bazında yalnızca train fold’lar üzerinde fit edilmesi: `scripts/train_fd003.py:162`
- OOF stacking CV’ye dahil edilmesi (opsiyonel): `scripts/train_fd003.py:241`
- Notebook’taki in-sample stacking bloğu kaldırıldı: `notebooks/RUL/FD003/FD003_train_ensemble_sensors_plus_cycle_CAP125_with_metrics_export.ipynb:1231`

### 4) HIGH — Preprocess + label üretimi izlenebilirliği
- Repo’da FD003 raw dosyaları yok; buna rağmen “train-only fit” iddiası:
  - scaler meta’daki `fit_split=train_only`: `data/processed/CMAPSS_full_norm/FD003/fd003_full_global_zscore_nodrop_scaler.json:5`
  - artefact audit script’i (mevcut processed + scaler meta tutarlılığı): `scripts/verify_fd003_preprocess_artifacts.py:28`
  - raw tabular CSV varsa yeniden üretim script’i (train-only fit + build_report.json): `scripts/build_fd003_preprocess.py:49`
- RUL label kuralı (CAP) tek kaynak: `scripts/_rul_metrics.py:11`
- CAP uygulaması runner içinde: `scripts/train_fd003.py:214`

### 5) MED — Repo-relative çalıştırılabilirlik
- Runner varsayılan path’leri repo-relative: `scripts/train_fd003.py:178`
- Çıktılar standard dizine yazılıyor: `scripts/train_fd003.py:181`
- Notebook data path repo-relative yapıldı: `notebooks/RUL/FD003/FD003_train_ensemble_sensors_plus_cycle_CAP125_with_metrics_export.ipynb:76`

## Repro komutları
- Preprocess artefact audit (default input path’leri ile):
  - Komut:
    - `python scripts/verify_fd003_preprocess_artifacts.py --train-csv data/processed/CMAPSS_full_norm/FD003/train_FD003_full_global_zscore_nodrop.csv --test-csv data/processed/CMAPSS_full_norm/FD003/test_FD003_full_global_zscore_nodrop.csv --scaler-json data/processed/CMAPSS_full_norm/FD003/fd003_full_global_zscore_nodrop_scaler.json --out-json outputs/fd003/fd003_preprocess_audit.json`
  - Beklenen çıktı:
    - `outputs/fd003/fd003_preprocess_audit.json`

- Leakage-free train/eval (CV selection + final test; OOF stacking açık):
  - Komut:
    - `python scripts/train_fd003.py --train-csv data/processed/CMAPSS_full_norm/FD003/train_FD003_full_global_zscore_nodrop.csv --test-csv data/processed/CMAPSS_full_norm/FD003/test_FD003_full_global_zscore_nodrop.csv --out-dir outputs/fd003 --cap 125 --seed 42 --cv-folds 5 --stacking`
  - Beklenen çıktılar:
    - `outputs/fd003/run_metadata.json`
    - `outputs/fd003/cv_folds.csv`
    - `outputs/fd003/cv_summary.csv`
    - `outputs/fd003/test_predictions.csv`
    - `outputs/fd003/test_metrics.json`

## Beklenen artefact’lar (çalıştırma sonrası)
- `outputs/fd003/run_metadata.json` (seed/cap/CV + “test excluded” garantisi): `scripts/train_fd003.py:269`
- `outputs/fd003/cv_folds.csv`, `outputs/fd003/cv_summary.csv`: `scripts/train_fd003.py:267`
- `outputs/fd003/test_predictions.csv`, `outputs/fd003/test_metrics.json`: `scripts/train_fd003.py:348`

## Kalan riskler
- **MED:** Ortamda `lightgbm`/`catboost` yoksa runner çalışmaz (install gerektirir): `scripts/train_fd003.py:26`, `scripts/train_fd003.py:36`
- **MED:** FD003 raw kaynak dosyaları repo’da olmadığı için preprocess “tam yeniden üretim” bu repo içinde uçtan uca koşturulamıyor (audit script’i mevcut processed üzerinde çalışır): `scripts/verify_fd003_preprocess_artifacts.py:102`
