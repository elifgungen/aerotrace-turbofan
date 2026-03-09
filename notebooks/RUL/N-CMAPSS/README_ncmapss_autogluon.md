# README - N-CMAPSS AutoGluon RUL

## 1) Amaç
Bu script (`train_autogluon_ncmapss.py`), N-CMAPSS **DS01 / DS02 / DS03** için leakage-safe şekilde AutoGluon Tabular ile RUL tahmini üretir ve ekip içinde karşılaştırılabilir çıktılar üretmeyi hedefler.

## 2) Gerekli dosyalar (kontrol listesi)
Her dataset için (`<DS> = DS01 | DS02 | DS03`) şu yapı beklenir:

- [ ] `<input_root>/<DS>/train_<DS>_v0.csv`
- [ ] `<input_root>/<DS>/test_<DS>_v0.csv`
- [ ] `<input_root>/<DS>/scaler_<DS>_v0.json` *(opsiyonel, ama `--use_scaler_features=1` için önerilir)*

## 3) Kurulum
```bash
pip install autogluon.tabular pandas numpy
```

## 4) Hızlı çalıştırma

### Baseline (önerilen başlangıç)
- `fe_mode=none`
- `val_engines=1` (train içi engine-based validation)

```bash
python train_autogluon_ncmapss.py \
  --dataset DS01 \
  --input_root /path/to/data/processed/N-CMAPSS \
  --output_root /path/to/data/outputs \
  --preset high_quality \
  --seed 42 \
  --use_cycle 1 \
  --fe_mode none \
  --use_scaler_features 1 \
  --val_engines 1
```

### Light FE
```bash
python train_autogluon_ncmapss.py \
  --dataset DS01 \
  --input_root /path/to/data/processed/N-CMAPSS \
  --output_root /path/to/data/outputs \
  --preset high_quality \
  --seed 42 \
  --use_cycle 1 \
  --fe_mode light \
  --use_scaler_features 1 \
  --val_engines 1
```

> Opsiyonel: `--time_limit 600` gibi bir süre limiti verebilirsiniz.

## 5) Çıktıları nereden bulurum?
`<output_root>` altında:

- `ncmapss_<DS>_rul_predictions_autogluon.csv`
- `ncmapss_<DS>_autogluon_artifacts/leaderboard.csv`
- `ncmapss_<DS>_autogluon_artifacts/model_info.json`
- `ncmapss_<DS>_autogluon_artifacts/run_config.json`
- `ncmapss_<DS>_autogluon_artifacts/autogluon_models/`

Tahmin CSV kolonları:
- `dataset_id, split, engine_id, cycle, rul_pred`

Notlar:
- `val_engines > 0` ise tahmin CSV’de `split=val` satırları da olur.
- Test dosyasında `RUL` yoksa script çalışır, `model_info.json` içinde `test_rmse = null` olur.

## 6) Ekipte paylaşılacaklar
- `ncmapss_<DS>_rul_predictions_autogluon.csv`
- `leaderboard.csv`
- `model_info.json`
- `run_config.json`

## 7) Sık hatalar & çözüm

| Durum | Belirti | Çözüm |
|---|---|---|
| File not found | `Train/Test file not found` | `--input_root` ve DS klasör yapısını kontrol edin. |
| Missing feature columns | `missing feature columns` hatası | Train/Test kolon uyumunu kontrol edin; scaler feature listesi testte de olmalı. Gerekirse `--use_scaler_features 0` deneyin. |
| Engine overlap assertion | `Engine-level leakage detected` | Train ve test engine_id kümeleri ayrık olmalı; veri splitini düzeltin. |
| Test’te RUL yok | `test_rmse` null/None | Bu hata değildir; test etiketi yokken beklenen davranıştır. |
| AutoGluon import error | `AutoGluon is required` | `pip install autogluon.tabular` çalıştırın (gerekirse yeni venv). |

## 8) MVP disiplin notu
- Kıyaslama için aynı `seed` ve `preset` kullanın (`42`, `high_quality`).
- Train/test verisini karıştırmayın.
- DS01/DS02/DS03 karşılaştırmalarını aynı parametre setiyle koşun.
