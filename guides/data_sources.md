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

