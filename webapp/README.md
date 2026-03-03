# 09 — AeroTrace Web Uygulaması

Turbofan motorları için **insan-onaylı kestirimci bakım karar destek sistemi** web arayüzü.  
11 farklı senaryo (C-MAPSS FD001–FD004 + N-CMAPSS DS01–DS07) üzerinde çalışan RUL tahmin ve anomali skorlarını birleştirip her çevrimde **4 seviyeli bakım önerisi** üretir; nihai karar bakım mühendisinde kalır.

> **AeroTrace** by **AeroLith Systems** · v2.0  
> Deploy: [https://dist-ebon-nine.vercel.app](https://dist-ebon-nine.vercel.app)

---

## Hızlı Başlangıç

```bash
# 1. Bu klasöre gel
cd webapp

# 2. Bağımlılıkları kur (sadece ilk seferede)
npm install

# 3. Geliştirme sunucusunu başlat
npm run dev
```

Tarayıcıda **http://localhost:5173** otomatik açılır.

> **Gereksinimler:** Node.js v18+ · npm  
> Veri dosyaları (`public/data/`) hazır gelir, ekstra adım gerekmez.

---

## Ne Yapar?

| Sayfa | Açıklama |
|-------|----------|
| **Intro** | Hero mesajı, brand lockup, 4 karar seviyesi kartı, MVP pipeline akışı, şeffaflık kartları |
| **Ana Sayfa** | Filo istatistikleri, **dataset seçici** (11 senaryo), karar seviyesi kartları |
| **Filo Görünümü** | Risk matrisi (Anomaly vs RUL), karar dağılımı donut chart, filtrelenebilir motor tablosu |
| **Motor Detay** | Dual-axis timeline (RUL + Anomaly), eşik çizgileri, cycle scrubber (play/pause), **"Neden Bu Karar?" paneli** (Türkçe açıklama, metrik chip'ler, neden kodları), durum geçiş geçmişi |
| **3D Digital Twin** | Plotly.js 3D motor modeli (7 bileşen: Fan, LPC, HPC, Combustor, HPT, LPT, Shaft), bileşen sağlık barları, auto-play degradasyon animasyonu |
| **Audit & Kanıt** | Policy snapshot, veri kalitesi kontrolleri, yöntem güvencesi, kanıt kartları |

**Jüri Demo Modu:** Sol alt köşedeki "Jüri Demo" butonuyla 6 adımlı rehberli sunum başlar.

---

## Multi-Dataset Desteği

AeroTrace, 11 farklı senaryo üzerinde çalışır:

### C-MAPSS (4 senaryo)
| Dataset | Motor Sayısı | Çalışma Koşulu | Hata Modu |
|---------|-------------|----------------|-----------|
| FD001 | 100 | 1 | 1 (HPC) |
| FD002 | 259 | 6 | 1 (HPC) |
| FD003 | 100 | 1 | 2 (HPC+Fan) |
| FD004 | 248 | 6 | 2 (HPC+Fan) |

### N-CMAPSS (7 senaryo)
| Dataset | Motor Sayısı | Uçuş Profili |
|---------|-------------|-------------|
| DS01–DS07 | ~10 each | Gerçekçi |

Kullanıcı, Ana Sayfa'daki **dataset seçici** dropdown ile dataset'ler arasında geçiş yapabilir. Seçim yapıldığında tüm sayfalar (Filo, Motor Detay, 3D Twin) otomatik güncellenir.

---

## Karar Destek Mekanizması

### 4 Seviyeli Karar Matrisi

| Anomali | RUL | Etiket | Aksiyon |
|---------|-----|--------|---------|
| OFF | > θ | **Normal Operation** | Rutin izleme |
| ON | > θ | **Enhanced Monitoring** | İzleme artır + teşhis |
| OFF | ≤ θ | **Planned Maintenance** | Planlı bakım/inspection |
| ON | ≤ θ | **Immediate Maintenance** | Acil bakım değerlendirmesi |

### "Neden Bu Karar?" Paneli

Motor Detay sayfasında her çevrim için yapısal Türkçe açıklama:
- **Karar başlığı** + status badge + Türkçe etiket
- **Açıklama metni** — RUL ve anomali değerlerini referans vererek insan diliyle yazılmış 2-3 cümle
- **Metrik chip'ler** — `RUL`, `θ`, `Anomali`, `α` değerleri
- **Neden kodları** — `RUL_LOW`, `ANOM_ON` vb.
- **Önerilen aksiyon** — Kalın vurgulu satır

### Audit Alanları (Her Satırda)

`policy_version` · `run_id` · `theta_rul_used` · `alpha_high_used` · `alpha_low_used` · `reason_codes` · `reason_text` · `smoothing_params` · `persistence_params`

Her karar deterministik ve geriye dönük izlenebilir.

---

## Proje Yapısı

```
webapp/
├── index.html                    # Sidebar, navigation, demo overlay
├── main.js                       # SPA router, render fonksiyonları, demo modu
├── style.css                     # AeroTrace Design System (light tema)
├── package.json                  # npm scriptleri ve bağımlılıklar
├── vite.config.js                # Vite dev server ayarları
├── preprocess_data.py            # CSV → JSON dönüştürücü (tek dataset)
├── preprocess_all_datasets.py    # Multi-dataset JSON üretici (11 senaryo)
├── public/
│   ├── data/
│   │   ├── datasets.json         # Dataset manifest (11 senaryo listesi)
│   │   ├── FD001/
│   │   │   ├── fleet_summary.json
│   │   │   └── engines/engine_*.json
│   │   ├── FD002/ ... FD004/     # C-MAPSS datasets
│   │   ├── DS01/ ... DS07/       # N-CMAPSS datasets
│   │   └── ...
│   ├── logo-main.png             # Intro header logosu
│   └── logo-kare.png             # Sidebar logosu
└── README.md                     # Bu dosya
```

---

## npm Scriptleri

| Komut | Açıklama |
|-------|----------|
| `npm run dev` | Geliştirme sunucusunu başlatır (hot reload) |
| `npm run build` | Production build oluşturur (`dist/`) |
| `npm run preview` | Build edilmiş sürümü önizler |
| `npm run preprocess` | CSV'den JSON verilerini yeniden üretir (Python 3 gerekir) |

---

## Veri Akışı

```
decision_support_v2_outputs/*.csv  (11 dataset)
        │
        ▼  (preprocess_all_datasets.py)
  datasets.json + FD001/ + FD002/ + ... + DS07/
        │           │
        │           └── fleet_summary.json + engines/engine_*.json
        │
        ▼  (main.js fetch)
   Plotly.js Charts · 3D Model · Tablolar
```

- **Kaynak CSV'ler:** `demo/decision_support_v2_outputs/` altında
- **Üretilen JSON'lar:** `public/data/` altında hazır — `preprocess` sadece CSV değişirse gerekir

---

## Teknoloji Yığını

- **Vite** — Dev server ve build tool
- **Vanilla JS** — Framework kullanılmadı, saf JavaScript
- **Plotly.js** — Scatter, bar, pie, 3D surface chartlar
- **CSS Custom Properties** — Light tema design token'ları
- **Google Fonts** — Inter + JetBrains Mono
- **Vercel** — Statik hosting (CDN, SSL otomatik)

---

## Vercel Deploy

```bash
npm run build
npx vercel --prod ./dist
```

Statik hosting — sunucu veya veritabanı gerektirmez. Dosyalar Vercel CDN'inde kalır.

---

## Katkıda Bulunma

1. `main.js` içinde her sayfa ayrı `render*()` fonksiyonuyla yönetilir
2. Yeni sayfa eklemek için: `renderPage()` switch'ine case ekle → sidebar'a link ekle → `render*` fonksiyonu yaz
3. Stil değişiklikleri `style.css` başındaki CSS custom property'ler ile yapılır (`:root` bloğu)
4. UI metinlerinde `PRODUCT_NAME` ve `COMPANY_NAME` sabitlerini kullan

---

## Sık Sorulan Sorular

**S: `npm run dev` çalışmıyor?**  
Node.js v18+ yüklü olduğundan emin ol: `node --version`

**S: Veriler görünmüyor?**  
`public/data/datasets.json` dosyasının var olduğunu kontrol et. Yoksa: `python preprocess_all_datasets.py`

**S: Dataset değiştirince veriler güncellenmiyorsa?**  
Dataset JSON dosyalarının `public/data/{dataset_id}/fleet_summary.json` formatında olduğundan emin ol.

**S: Port 5173 meşgul?**  
`vite.config.js` içindeki `port` değerini değiştir veya `npx vite --port 3000`
