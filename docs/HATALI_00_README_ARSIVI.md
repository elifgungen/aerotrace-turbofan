# Hatali 00 README Arsivi

Bu dosya, eski `00_README/` iceriginden tasinan ancak yayinlanmaya uygun bulunmayan metinleri tek yerde tutar.

Durum:
- Bu icerikler aktif rehber olarak kullanilmamalidir.
- Repo navigasyonundan geri cekilmistir.
- Icerikler yeniden yazilana kadar sadece referans ve duzeltme calismasi icin burada tutulur.

## Kaynak: `00_README/README.md`

```md
# HAVELSAN JET CUBE — Turbofan MVP (Jet-Cube)

Bu repo, **CFM56-7B sınıfı turbofan motorlar** için:
- **Kestirimci bakım (Predictive Maintenance)**
- **Karar-destek odaklı dijital ikiz yaklaşımı**

temelli bir MVP kurgusunu **NASA C-MAPSS / (N-)CMAPSS** gibi açık/sentetik veri setleriyle göstermeyi hedefler.

## Pipeline nasıl çalışır?
Bu MVP, otomatik bakım kararı vermez; **insan bakım mühendisine karar desteği** sağlar.

Uçtan uca akış:
1. **Veri**: `data/raw/` altına veri seti konur.
2. **Önişleme** (`notebooks/02_preprocess_fd001.ipynb`): ham veriden temiz/özellikli tablo üretir → `data/processed/`
3. **Model çıktıları**
   - **RUL tahmini** (`notebooks/03_rul_baseline_fd001.ipynb`): `fd001_rul_predictions.csv` → `data/outputs/`
   - **Anomali skoru** (`notebooks/04_anomaly_fd001.ipynb`): `fd001_anomaly_scores.csv` → `data/outputs/`
4. **Karar destek** (`notebooks/05_decision_support.ipynb`)
   - Girdi: `data/processed/fd001_processed.csv` + `data/outputs/*.csv`
   - Çıktı: `data/outputs/fd001_decision_support.csv`

## Hafta 1 (Elif) — Beklenen somut çıktılar
- Dummy veriyle çalışan **decision-support notebook’u** (`notebooks/05_decision_support.ipynb`)
- Repo’da herkesin uyacağı **net teknik akış** (bu dosya + `docs/weekly_updates.md`)
- Sonraki haftalarda eklenecek modeller için hazır iskelet (`data/`, `notebooks/`, `docs/`)

## Klasör yapısı
```
jet-cube-turbofan-mvp/
  data/
    raw/
    processed/
    outputs/
  notebooks/
  docs/
```

## Hızlı başlangıç
1. `notebooks/00_setup.ipynb` ile dizinleri ve bağımlılıkları hazırla.
2. `notebooks/05_decision_support.ipynb` çalıştır:
   - Hafta 1 için dummy CSV üretir
   - Karar-destek çıktısını `data/outputs/` altına yazar

## Documentation
Decision-support logic is defined in [docs/decision_logic.md](docs/decision_logic.md) and implemented in `notebooks/05_decision_support.ipynb`.
```

## Kaynak: `00_README/anomaly_pipeline.md`

```md
# Baseline Deviation Anomaly Pipeline (FD003 / FD004) — v1

Bu doküman, FD003/FD004 için **baseline deviation** anomali skor hattının nasıl koşturulacağını ve hangi artefact’ların üretileceğini tanımlar.

## Kapsam (bu PR)
- Decision-support entegrasyonu: **YOK**
- RUL runner’ları: **DEĞİŞMEDİ**

## Input gereksinimleri (processed)
Aşağıdaki dosyalar **zorunludur** (yoksa FAIL):
- `data/processed/train_FD003_full_norm.csv`
- `data/processed/test_FD003_full_norm.csv`
- `data/processed/train_FD004_full_norm.csv`
- `data/processed/test_FD004_full_norm.csv`

Minimum kolonlar:
- `engine_id` (int)
- `cycle` (int)
- sensör kolonları: allowlist’ten en az 1 tanesi (default allowlist `configs/anomaly_thresholds.json` içinde)

Not:
- `dataset_id` kolonunu script otomatik ekler (FD003/FD004).
- `engine_id` ve `cycle` asla feature listesine girmez.

## Config (tek kaynak)
- `configs/anomaly_thresholds.json`
  - `baseline_n`: per-engine baseline window (ilk N cycle)
  - `eps`: z-score denom stabilizasyonu
  - `mapping_mode`: `sigmoid`
  - `sigmoid_k`: sigmoid eğimi
  - `mapping_fit_on`: `train` (train-only fit kuralı)
  - `smooth_window`: rolling mean (per engine)
  - `sensor_allowlist`: kullanılacak sensörler (kesişim alınıp eksikler raporlanır)

## Repro komutları

### FD003
```bash
python scripts/anomaly_baseline_deviation.py --dataset FD003 --train_csv data/processed/train_FD003_full_norm.csv --test_csv data/processed/test_FD003_full_norm.csv --config configs/anomaly_thresholds.json --outdir data/outputs
python scripts/validate_anomaly_artifacts.py --dataset FD003 --train_csv data/processed/train_FD003_full_norm.csv --test_csv data/processed/test_FD003_full_norm.csv --scores_csv data/outputs/fd003_anomaly_scores.csv --report_json data/outputs/fd003_anomaly_report.json --mapping_json data/outputs/fd003_anomaly_mapping_params.json
```

Beklenen çıktı dosyaları:
- `data/outputs/fd003_anomaly_scores.csv`
- `data/outputs/fd003_anomaly_report.json`
- `data/outputs/fd003_anomaly_mapping_params.json`

### FD004
```bash
python scripts/anomaly_baseline_deviation.py --dataset FD004 --train_csv data/processed/train_FD004_full_norm.csv --test_csv data/processed/test_FD004_full_norm.csv --config configs/anomaly_thresholds.json --outdir data/outputs
python scripts/validate_anomaly_artifacts.py --dataset FD004 --train_csv data/processed/train_FD004_full_norm.csv --test_csv data/processed/test_FD004_full_norm.csv --scores_csv data/outputs/fd004_anomaly_scores.csv --report_json data/outputs/fd004_anomaly_report.json --mapping_json data/outputs/fd004_anomaly_mapping_params.json
```

Beklenen çıktı dosyaları:
- `data/outputs/fd004_anomaly_scores.csv`
- `data/outputs/fd004_anomaly_report.json`
- `data/outputs/fd004_anomaly_mapping_params.json`

## Output kontratı (scores CSV)
Her dataset için tek bir CSV yazılır (train+test satırları birlikte):
- kolonlar: `dataset_id`, `split`, `engine_id`, `cycle`, `anomaly_score`
- `split` değerleri: `train` / `test`
- join key uniqueness: `(dataset_id, split, engine_id, cycle)` unique olmalı
- `anomaly_score` 0–1 aralığında olmalı
```

## Kaynak: `00_README/data_sources.md`

```md
# Data Sources (FD003 / FD004)

Bu repo, **FD003/FD004 için raw (ham) C-MAPSS dosyalarını içermez**. Bu nedenle ham dosyaların edinimi ve versiyon/kanıt bilgisi repo dışında yönetilmelidir.

## Beklenen ham dosyalar
Aşağıdaki isimler, repo içindeki FD001 raw isimlendirmesiyle aynı şablonu izler:

- `train_FD003.txt`
- `test_FD003.txt`
- `RUL_FD003.txt`
- `train_FD004.txt`
- `test_FD004.txt`
- `RUL_FD004.txt`

Notlar:
- Bu dosyalar tipik olarak “NASA C-MAPSS Turbofan Engine Degradation Simulation Dataset” (FD003/FD004) altındadır.
- İndirilen dosyaların **indirme tarihi** ve **sha256** hash’leri kayıt altına alınmalıdır (audit/repro için).

Örnek hash alma:
```bash
shasum -a 256 train_FD003.txt test_FD003.txt RUL_FD003.txt
shasum -a 256 train_FD004.txt test_FD004.txt RUL_FD004.txt
```

## Repo içindeki mevcut girdiler
Bu repo, FD003/FD004 için **processed** CSV’leri içerir (raw’dan türetilmiş):

- FD003 processed:
  - `data/processed/CMAPSS_full_norm/FD003/train_FD003_full_global_zscore_nodrop.csv`
  - `data/processed/CMAPSS_full_norm/FD003/test_FD003_full_global_zscore_nodrop.csv`
  - `data/processed/CMAPSS_full_norm/FD003/fd003_full_global_zscore_nodrop_scaler.json`
- FD004 BASE processed:
  - `data/processed/CMAPSS_full_norm/FD004/FD004_full_global_zscore/train_FD004_full_global_zscore_nodrop.csv`
  - `data/processed/CMAPSS_full_norm/FD004/FD004_full_global_zscore/test_FD004_full_global_zscore_nodrop.csv`

## FD003 preprocess audit çıktısı (zorunlu kanıt)
FD003 için “train-only fit” meta iddiasını ve mevcut processed artefact’ların tutarlılığını kontrol eden audit çıktısı:

```bash
python scripts/verify_fd003_preprocess_artifacts.py
```

Varsayılan çıktı:
- `outputs/fd003/fd003_preprocess_audit.json`

## FD003 preprocess rebuild (raw tabular CSV varsa)
Eğer elinizde raw FD003’ü **header’lı tek CSV formatında** (engine_id, cycle, os1..os3, s1..s21, RUL) tutuyorsanız, train-only fit ile processed CSV’leri yeniden üretmek için:

```bash
python scripts/build_fd003_preprocess.py --train-csv <RAW_TRAIN_CSV> --test-csv <RAW_TEST_CSV>
```

Not: Repo, raw `.txt` parse adımını bu PR kapsamında içermez; bu parse adımı kurum içi pipeline’da belgelenmelidir.
```

## Kaynak: `00_README/demo_runbook.md`

```md
# Streamlit Demo Runbook — JET-CUBE Decision Support (FD001–FD004)

Bu demo **sadece yerel artefact dosyalarını** okur; eğitim/yeniden üretim yapmaz.

## 1) Kurulum

```bash
pip install -r requirements_demo.txt
```

## 2) Çalıştırma

Repo kök dizininde:

```bash
streamlit run demo/streamlit_dashboard/streamlit_app.py
```

## 3) Input gereksinimleri (canonical)

Uygulama varsayılan olarak şu dizinleri sırayla dener:
- `demo/data/outputs/`
- `demo/decision_support_v2_outputs/`

Bu dizinler altında şu dosyaları otomatik keşfeder:

- `fd001_decision_support.csv`
- `fd002_decision_support.csv`
- `fd003_decision_support.csv`
- `fd004_decision_support.csv`

Opsiyonel olarak (varsa keşfedilir):

- `data/outputs/fd00x_anomaly_scores.csv`
- `data/outputs/fd00x_rul_predictions.csv`

`*_decision_support.csv` minimum şema:

- `dataset_id, split, engine_id, cycle`
- `rul_pred, anomaly_score`
- `decision_label, reason_codes, reason_text`
- `theta_rul_used, alpha_anomaly_used`

Dosyalardan biri yoksa uygulama UI’da hangi path’in beklendiğini net şekilde yazar.

## 4) Ekran / Panel açıklaması (beklenen)

- **Sol sidebar**:
  - Dataset seçimi (FD001–FD004)
  - Keşfedilen dosyaların repo-relative path listesi
- **Timeline**:
  - `rul_pred` (line)
  - `anomaly_score` (sağ eksen, 0–1)
  - `decision_label` değişimleri cycle boyunca renkli arka-plan şeritleriyle işaretlenir
- **Why? paneli**:
  - Seçili `cycle` için `reason_codes` ve `reason_text`
  - Seçili engine için top-5 `reason_codes` frekansı
- **Özet metrikleri**:
  - Satır sayısı
  - `decision_label` dağılımı (count)
  - `anomaly_score` ve `rul_pred` için min/p50/p95/max
```

## Kaynak: `00_README/executive_summary.md`

```md
# Yönetici Özeti (1 sayfa) — JET-CUBE Turbofan MRO Karar Destek MVP

## Kısa değerlendirme: 6 kritik iyileştirme
- Uçtan uca artefact zinciri: RUL + anomaly + decision-support (FD001–FD004)
- Tek kaynak eşik/policy yönetimi + raporlarda kullanılan değerlerin audit’i
- Leakage-safe yaklaşım ve veri bütünlüğü kontrolleri (duplicate/NaN=0)
- Join anahtarı standardı ile izlenebilirlik: `(dataset_id, split, engine_id, cycle)`
- Repo-relative demo (Streamlit) ile jüriye hızlı gösterim
- Raw veri repo dışı olsa bile “beklenen input” dokümantasyonu ve repro komutları

## Problem
Turbofan motor bakımında (MRO) doğru zamanda doğru aksiyonu almak kritik: **erken bakım** maliyet yaratır, **geç bakım** arıza riskini artırır. Operasyon ekibinin ihtiyacı; motorun yaşam döngüsü boyunca **kalan ömür (RUL)** ve **beklenmedik sapma/anomali** sinyallerini tek bir çerçevede görüp aksiyon alabilmektir.

## Çözüm (MVP yaklaşımı)
Bu MVP; her motor ve çevrim için:
- **RUL tahmini** (`rul_pred`)
- **Baseline deviation anomaly score** (`anomaly_score`, 0–1) — **MVP’de hızlı, açıklanabilir ve audit edilebilir** olduğu için seçildi.

üretir ve bunları tek kaynak eşik/policy ile birleştirerek **decision_label** (karar/öneri) çıktısı verir; bu çıktı operasyonel aksiyona doğrudan bağlanır: **Normal Operation → normal izleme**, **Enhanced Monitoring → sıklaştırılmış izleme**, **Planned Maintenance → planlı bakım planlama**, **Immediate Maintenance → acil bakım**.

## MVP kapsamı (C-MAPSS)
CMAPSS FD001–FD004 için uçtan uca **artefact üretim zinciri** repo içinde mevcuttur:
- `data/outputs/fd00x_rul_predictions.csv`
- `data/outputs/fd00x_anomaly_scores.csv`
- `data/outputs/fd00x_decision_support.csv`
- `data/outputs/fd00x_*_report.json` (audit/kanıt zinciri)

Kanıt formatı (teknik ama güçlü): tüm çıktılar `(dataset_id, split, engine_id, cycle)` anahtarıyla join edilebilir; **duplicate=0 ve NaN=0** koşulları doğrulanır.

## Güven / Audit edilebilirlik
MVP; “sonuç var” değil, “sonuç **kanıtlanabilir**” hedefiyle tasarlanmıştır:
- **Tek kaynak config**: `configs/decision_support_thresholds.json`, `configs/anomaly_thresholds.json`
- Artefact raporlarında **config hash** / kullanılan eşikler (`*_report.json`) ile iz sürülebilirlik
- **Leakage-safe ve data-integrity odaklı protokol**: train-only fit yaklaşımı + join/duplicate/NaN kontrolleri ile pipeline güvenilirliği.
- FD003/FD004 değerlendirme ve reproducibility raporları: `docs/fd003_protocol_fix_report.md`, `docs/fd004_repro_fix_report.md`

## Demo / Görselleştirme
Karar destek çıktıları, repo-relative çalışan bir Streamlit dashboard ile görselleştirilir:
- `app/streamlit_app.py`
- Çalıştırma kılavuzu: `docs/demo_runbook.md`

## Kısıtlar (bilerek)
- **Raw veri repo içinde değildir** (lisans/boyut). Beklenen dosyalar ve edinim bilgisi: `docs/data_sources.md` (ayrıca repro komutları: `docs/repro_commands.md`)
- Raw yoksa ilgili script’ler **FAIL** ederek beklenen raw dosyaları/şemayı açıkça raporlar (repro zinciri).

## Next steps (Phase‑2)
- İş değeri odaklı kalibrasyon: **threshold tuning** (maliyet/false-alarm vs missed-alarm, ARL/MTBF hedefleri) + alarm stabilizasyonu (hysteresis/debounce)
- (Opsiyonel) Daha ileri modelleme: **DL RUL** ve **Autoencoder anomaly** ile planın “ileri” kapsamı
```

## Kaynak: `00_README/mvp_quickstart.md`

```md
# MVP Quickstart (≤3 dk) — JET-CUBE Karar Destek Demo

Bu quickstart yalnızca hazır artefact’ları okur; eğitim/yeniden üretim yapmaz.

## 1) Kurulum

Repo kökünde:

```bash
pip install -r requirements_demo.txt
```

## 2) Demo çalıştırma (Streamlit)

```bash
streamlit run app/streamlit_app.py
```

Uygulama `data/outputs/` altındaki `fd001..fd004` decision-support artefact’larını otomatik keşfeder.
Dosya yoksa UI’da hangi path’in beklendiğini açıkça gösterir.

## 3) Artefact’lar nerede?

Canonical çıktı klasörü: `data/outputs/`

Beklenen ana dosyalar:
- `data/outputs/fd001_decision_support.csv`
- `data/outputs/fd002_decision_support.csv`
- `data/outputs/fd003_decision_support.csv`
- `data/outputs/fd004_decision_support.csv`

Opsiyonel ama (varsa) otomatik keşfedilen eşleşen dosyalar:
- `data/outputs/fd00x_rul_predictions.csv`
- `data/outputs/fd00x_anomaly_scores.csv`

## 4) Repro komutları nerede?

Uçtan uca üretim/repro komutları: `docs/repro_commands.md`

Raw veri repo içinde değilse edinim/versiyon ve beklenen dosya isimleri: `docs/data_sources.md`
```

## Kaynak: `00_README/repro_commands.md`

```md
# Repro Commands (FD001 / FD002) — MVP Closure

Bu doküman, **FD001** ve **FD002** için reproducibility zincirini (raw → processed → anomaly → decision-support v1) tek komutla çalıştırma komutlarını ve beklenen çıktıları listeler.

## Önkoşul: Raw veri
Raw CMAPSS dosyaları repo’da varsayılan olarak yoksa, aşağıdaki path’lere yerleştirin:
- `data/raw/CMAPSSData/train_FD001.txt`
- `data/raw/CMAPSSData/test_FD001.txt`
- `data/raw/CMAPSSData/RUL_FD001.txt`
- `data/raw/CMAPSSData/train_FD002.txt`
- `data/raw/CMAPSSData/test_FD002.txt`
- `data/raw/CMAPSSData/RUL_FD002.txt`

## FD001 — tek komutla repro
```bash
python scripts/build_fd001_preprocess.py \
  --raw-dir data/raw/CMAPSSData \
  --out-train data/processed/train_FD001_full_norm.csv \
  --out-test data/processed/test_FD001_full_norm.csv \
  --report-json data/outputs/fd001_preprocess_report.json

python scripts/anomaly_baseline_deviation.py \
  --dataset FD001 \
  --train_csv data/processed/train_FD001_full_norm.csv \
  --test_csv data/processed/test_FD001_full_norm.csv \
  --config configs/anomaly_thresholds.json \
  --outdir data/outputs

python scripts/standardize_rul_predictions.py \
  --dataset FD001 --split test \
  --in_csv notebooks/RUL/FD001/FD001_Ozcan_AllRaws/predictions_cycle_all_rows.csv \
  --pred_col pred_ensemble \
  --out_csv data/outputs/fd001_rul_predictions.csv

python scripts/build_decision_support_v1.py \
  --dataset FD001 \
  --rul_csv data/outputs/fd001_rul_predictions.csv \
  --anomaly_csv data/outputs/fd001_anomaly_scores.csv \
  --config configs/decision_support_thresholds.json \
  --out_csv data/outputs/fd001_decision_support.csv \
  --report_json data/outputs/fd001_decision_support_report.json
```

Beklenen çıktılar:
- `data/processed/train_FD001_full_norm.csv`
- `data/processed/test_FD001_full_norm.csv`
- `data/outputs/fd001_preprocess_report.json`
- `data/outputs/fd001_anomaly_scores.csv`
- `data/outputs/fd001_anomaly_report.json`
- `data/outputs/fd001_anomaly_mapping_params.json`
- `data/outputs/fd001_rul_predictions.csv`
- `data/outputs/fd001_decision_support.csv`
- `data/outputs/fd001_decision_support_report.json`

## FD002 — tek komutla repro
```bash
python scripts/build_fd002_preprocess.py \
  --raw-dir data/raw/CMAPSSData \
  --out-train data/processed/train_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --out-test data/processed/test_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --report-json data/outputs/fd002_preprocess_report.json

python scripts/build_fd002_anomaly.py \
  --train_csv data/processed/train_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --test_csv data/processed/test_FD002_regimeaware_sensor_zscore_k6_onehot.csv \
  --config configs/anomaly_thresholds.json \
  --outdir data/outputs

python scripts/standardize_rul_predictions.py \
  --dataset FD002 --split test \
  --in_csv notebooks/RUL/FD002/FD002_Ozcan_All/fd002_test_predictions_FD002_LOCAL_REGIMEAWARE_SENSOR_ZSCORE_K6_ONEHOT.csv \
  --out_csv data/outputs/fd002_rul_predictions.csv

python scripts/build_decision_support_v1.py \
  --dataset FD002 \
  --rul_csv data/outputs/fd002_rul_predictions.csv \
  --anomaly_csv data/outputs/fd002_anomaly_scores.csv \
  --config configs/decision_support_thresholds.json \
  --out_csv data/outputs/fd002_decision_support.csv \
  --report_json data/outputs/fd002_decision_support_report.json
```

Beklenen çıktılar:
- `data/processed/train_FD002_regimeaware_sensor_zscore_k6_onehot.csv`
- `data/processed/test_FD002_regimeaware_sensor_zscore_k6_onehot.csv`
- `data/outputs/fd002_preprocess_report.json`
- `data/outputs/fd002_anomaly_scores.csv`
- `data/outputs/fd002_anomaly_report.json`
- `data/outputs/fd002_anomaly_mapping_params.json`
- `data/outputs/fd002_rul_predictions.csv`
- `data/outputs/fd002_decision_support.csv`
- `data/outputs/fd002_decision_support_report.json`
```

## Kaynak: `00_README/requirements_demo.txt`

```text
streamlit>=1.30
pandas>=2.0
numpy>=1.24
plotly>=5.18
cachetools<6
```
