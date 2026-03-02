# Veri Kaynakları — AeroTrace

Bu doküman, AeroTrace'in kullandığı veri setlerinin edinim bilgisi ve beklenen dosya formatlarını tanımlar.

---

## C-MAPSS (FD001–FD004)

### Kaynak
**NASA Commercial Modular Aero-Propulsion System Simulation Dataset**  
Edinim: [NASA Prognostics Data Repository](https://data.nasa.gov/dataset/C-MAPSS-Aircraft-Engine-Simulator-Data/xaut-bemq)

### Beklenen Ham Dosyalar
Her dataset (FD001, FD002, FD003, FD004) için üç dosya:
- `train_FD00x.txt` — Eğitim verisi (çalışma-sonuna-kadar/run-to-failure)
- `test_FD00x.txt` — Test verisi (kesik çevrim)
- `RUL_FD00x.txt` — Test motorları için gerçek kalan ömür

### Dataset Özellikleri

| Dataset | Motor | Çalışma Koşulu | Hata Modu | Sensör |
|---------|-------|----------------|-----------|--------|
| FD001 | 100 | 1 | 1 (HPC) | 21 |
| FD002 | 259 | 6 | 1 (HPC) | 21 |
| FD003 | 100 | 1 | 2 (HPC+Fan) | 21 |
| FD004 | 248 | 6 | 2 (HPC+Fan) | 21 |

### Sensör Kolonları
`s1`–`s21`: 21 sensör ölçümü  
`os1`–`os3`: 3 çalışma koşulu ayarı

---

## N-CMAPSS (DS01–DS07)

### Kaynak
**NASA New Commercial Modular Aero-Propulsion System Simulation**  
Edinim: [NASA Prognostics Data Repository](https://data.nasa.gov/dataset/CMAPSS-Jet-Engine-Simulated-Data/ff5v-kuh6)

### Beklenen Dosyalar

CSV formatında (v2 format — `split`, `unit`, `cycle` ve sensör kolonları):
- `train_DS0x.csv` veya `DS0x.csv` (tek dosya)

### Dataset Özellikleri

| Dataset | Motorlar | Uçuş Profili | Özellik |
|---------|----------|-------------|---------|
| DS01 | ~10 | Gerçekçi | Referans |
| DS02 | ~10 | Gerçekçi | Farklı koşullar |
| DS03 | ~10 | Gerçekçi | Değişken yük |
| DS04 | ~10 | Gerçekçi | Çoklu bozulma |
| DS05 | ~10 | Gerçekçi | Uzun ömür |
| DS06 | ~10 | Gerçekçi | Kısa ömür |
| DS07 | ~10 | Gerçekçi | Karma koşullar |

### Sensör Kolonları
N-CMAPSS 14 fiziksel sensör kullanır (C-MAPSS'in 21'ine kıyasla azaltılmış set).

---

## Repo İçindeki Mevcut İşlenmiş Veriler

### C-MAPSS İşlenmiş
```
01_data/processed/CMAPSS/
├── CMAPSS_kept_norm/FD001/     # FD001 normalize (z-score)
└── CMAPSS_full_norm/
    ├── FD001/                  # Full global z-score normalize
    ├── FD002/                  # Multiple normalization variants
    ├── FD003/
    └── FD004/
```

### N-CMAPSS İşlenmiş
```
01_data/processed/N-CMAPSS/
├── DS01/                       # manifest.json + normalize CSV
├── DS02/
├── ...
└── DS07/
```

### Pipeline Çıktıları
```
01_data/processed/outputs/
├── fd001_decision_support.csv
├── fd002_decision_support.csv
├── fd003_decision_support.csv
└── fd004_decision_support.csv
```

---

## Veri Bütünlüğü

İndirilen dosyaların hash'lerini kaydedin (audit/repro için):

```bash
shasum -a 256 train_FD001.txt test_FD001.txt RUL_FD001.txt
```

Tüm processed CSV'ler `(dataset_id, split, engine_id, cycle)` unique join key'i ile izlenebilir.

---

## Not
- Raw veri dosyaları repo içinde **yer almaz** (lisans/boyut kısıtı)
- Raw yoksa pipeline script'leri FAIL ederek beklenen dosyaları raporlar
- İşlenmiş veriler script'ler ile raw'dan yeniden üretilebilir
