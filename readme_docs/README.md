# AeroTrace — Turbofan Kestirimci Bakım Karar Destek Platformu

**AeroTrace** by **AeroLith Systems** · v2.0

> İnsan-onaylı, açıklanabilir ve denetlenebilir kestirimci bakım karar destek sistemi.  
> NASA C-MAPSS (FD001–FD004) ve N-CMAPSS (DS01–DS07) veri setleri üzerinde çalışır.

🌐 **Live Demo:** [https://dist-ebon-nine.vercel.app](https://dist-ebon-nine.vercel.app)

---

## Proje Nedir?

AeroTrace, turbofan motor filolarında:

- **RUL (Remaining Useful Life)** tahmini — Gradient Boosting tabanlı
- **Anomali skoru** — Baseline deviation yöntemi (Mahalanobis + sigmoid mapping)
- **4 seviyeli bakım kararı** — İnsan-onaylı eşik politikası ile

sunarak bakım mühendisine **karar desteği** sağlar. Sistem otomatik karar vermez; nihai karar insanda kalır.

### Karar Matrisi

| Anomali | RUL   | Etiket                    | Aksiyon                |
|---------|-------|---------------------------|------------------------|
| OFF     | > θ   | **Normal Operation**      | Rutin izleme           |
| ON      | > θ   | **Enhanced Monitoring**   | İzleme artır + teşhis  |
| OFF     | ≤ θ   | **Planned Maintenance**   | Planlı bakım/inspection|
| ON      | ≤ θ   | **Immediate Maintenance** | Acil bakım             |

Her karar deterministik, denetlenebilir ve geriye dönük izlenebilirdir.

---

## Hızlı Başlangıç

### Web Uygulaması (önerilen)

```bash
cd webapp
npm install
npm run dev
```

Tarayıcıda **http://localhost:5173** açılır. Veri dosyaları hazır gelir, ekstra adım gerekmez.

> **Gereksinimler:** Node.js v18+ · npm

### Karar Destek Pipeline (Python)

```bash
cd demo/decision_support_v2_package
pip install -e .
python scripts/run_decision_support.py --dataset FD001
```

---

## Klasör Yapısı

```
AeroTrace/
├── readme_docs/                    # Proje dokümantasyonu
│   ├── README.md                 # Bu dosya
│   ├── executive_summary.md      # Yönetici özeti
│   ├── mvp_quickstart.md         # Hızlı başlangıç
│   ├── demo_runbook.md           # Demo çalıştırma kılavuzu
│   ├── data_sources.md           # Veri kaynakları ve edinim bilgisi
│   └── anomaly_pipeline.md       # Anomali pipeline açıklaması
│
├── data/                      # Ham ve işlenmiş veri
│   ├── raw/                      # NASA orijinal dosyaları
│   └── processed/                # Normalize / feature-engineered CSV'ler
│       ├── CMAPSS/               # FD001–FD004 işlenmiş
│       ├── N-CMAPSS/             # DS01–DS07 işlenmiş
│       └── outputs/              # Decision support CSV çıktıları
│
├── docs/                      # Teknik raporlar ve analiz dokümanları
│   ├── Decision_Support/         # Karar destek raporları
│   ├── final reports/            # Dataset bazlı final raporlar
│   └── incident reports/         # Pipeline hata/düzeltme raporları
│
├── figures/                   # Analiz görselleri
│
├── demo/                      # Demo ve karar destek pipeline
│   ├── decision_support_v2_package/  # Python karar destek paketi
│   │   ├── src/decision_support/     # Policy engine + adapter'lar
│   │   ├── scripts/                  # Runner script'leri
│   │   └── tests/                    # Unit test'ler
│   └── decision_support_v2_outputs/  # Pipeline çıktı CSV'leri (11 dataset)
│       └── audit/                    # Audit ve delta raporları
│
├── twin/                      # 3D Digital Twin (Streamlit versiyonu)
│   ├── app/                      # Streamlit uygulaması
│   ├── config/                   # Twin konfigürasyonları
│   └── data/                     # Twin veri dosyaları
│
└── webapp/                    # ★ Ana web uygulaması (Vite + Vanilla JS)
    ├── main.js                   # SPA router, render fonksiyonları, demo modu
    ├── style.css                 # AeroTrace Design System
    ├── index.html                # Sidebar, navigation, demo overlay
    ├── preprocess_all_datasets.py # Multi-dataset JSON üretici
    └── public/data/              # 11 dataset JSON verisi
        ├── datasets.json         # Dataset manifest
        ├── FD001/                # C-MAPSS FD001
        ├── ...                   # FD002, FD003, FD004
        ├── DS01/                 # N-CMAPSS DS01
        └── ...                   # DS02–DS07
```

---

## Veri Setleri

### C-MAPSS (4 senaryo)
NASA Commercial Modular Aero-Propulsion System Simulation:
- **FD001:** 100 motor, tek çalışma koşulu, tek hata modu
- **FD002:** 259 motor, 6 çalışma koşulu, tek hata modu
- **FD003:** 100 motor, tek çalışma koşulu, 2 hata modu
- **FD004:** 248 motor, 6 çalışma koşulu, 2 hata modu

### N-CMAPSS (7 senaryo)
New Commercial Modular Aero-Propulsion System Simulation:
- **DS01–DS07:** Gerçekçi uçuş profilleri, değişken çalışma koşulları, 14 sensör

Tüm veri setleri NASA'nın açık erişimli veri havuzundan edinilmiştir.

---

## Web Uygulaması Sayfaları

| Sayfa | Açıklama |
|-------|----------|
| **Intro** | Hero mesajı, brand lockup, MVP pipeline akışı, şeffaflık kartları |
| **Ana Sayfa** | Filo istatistikleri, dataset seçici, karar seviyesi kartları |
| **Filo Görünümü** | Risk matrisi, karar dağılımı, filtrelenebilir motor tablosu |
| **Motor Detay** | Timeline (RUL + Anomaly), cycle scrubber, "Neden Bu Karar?" paneli, geçiş geçmişi |
| **3D Digital Twin** | Plotly.js 3D motor modeli, 7 bileşen sağlık barları, auto-play |
| **Audit & Kanıt** | Policy snapshot, veri kalitesi kontrolleri, kanıt kartları |

**Jüri Demo Modu:** Sol alt köşedeki "Jüri Demo" butonuyla 6 adımlı rehberli sunum.

---

## Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Frontend | Vanilla JavaScript (framework yok) |
| Build | Vite |
| Grafikler | Plotly.js (scatter, bar, pie, 3D surface) |
| Stil | CSS Custom Properties (light tema) |
| Font | Inter + JetBrains Mono (Google Fonts) |
| Hosting | Vercel (statik CDN, SSL otomatik) |
| Pipeline | Python 3 (karar destek, anomali, preprocessing) |
| ML | Gradient Boosting (AutoGluon) — RUL tahmini |
| Anomali | Baseline deviation (Mahalanobis distance + sigmoid mapping) |

---

## Audit & Denetlenebilirlik

Her karar satırında şu alanlar bulunur:
- `policy_version` · `run_id` — İzlenebilirlik
- `theta_rul_used` · `alpha_high_used` · `alpha_low_used` — Kullanılan eşikler
- `reason_codes` · `reason_text` — Karar gerekçesi
- `smoothing_params` · `persistence_params` — Sinyal işleme parametreleri

Tüm eşikler tek kaynak config dosyasından yönetilir; pipeline deterministik ve reproducible'dır.

---

## Deploy

```bash
cd webapp
npm run build
npx vercel --prod ./dist
```

Statik hosting — sunucu veya veritabanı gerektirmez.

---

## Lisans

Bu proje akademik/demo amaçlıdır. NASA C-MAPSS ve N-CMAPSS veri setleri NASA'nın açık erişim lisansı altındadır.
