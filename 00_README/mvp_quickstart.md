# MVP Quickstart (≤3 dk) — AeroTrace Karar Destek Demo

Bu quickstart, AeroTrace web uygulamasını yerel makinenizde çalıştırır.  
Hazır JSON verileri ile gelir; eğitim/yeniden üretim yapmaz.

## 1) Gereksinimler

- **Node.js** v18+ ([nodejs.org](https://nodejs.org))
- **npm** (Node.js ile birlikte gelir)

Kontrol:
```bash
node --version   # v18+ olmalı
npm --version
```

## 2) Kurulum ve Çalıştırma

```bash
# Repo kökünden:
cd 09_webapp

# Bağımlılıkları kur (sadece ilk seferde)
npm install

# Geliştirme sunucusunu başlat
npm run dev
```

Tarayıcıda **http://localhost:5173** otomatik açılır.

## 3) Ne Görüyorum?

| Sayfa | Açıklama |
|-------|----------|
| **Intro** | Proje tanıtımı, pipeline akışı |
| **Ana Sayfa** | Filo istatistikleri, dataset seçici (11 senaryo) |
| **Filo Görünümü** | Risk matrisi, motor tablosu |
| **Motor Detay** | RUL & Anomaly timeline, "Neden Bu Karar?" paneli |
| **3D Twin** | 3D motor modeli, bileşen sağlığı |
| **Audit** | Policy ve veri kalitesi kontrolleri |

**Jüri Demo:** Sol alt köşedeki "Jüri Demo" butonuyla rehberli sunum başlar.

## 4) Dataset Değiştirme

Ana sayfadaki **dataset seçici** ile 11 farklı senaryo arasında geçiş yapabilirsiniz:
- C-MAPSS: FD001, FD002, FD003, FD004
- N-CMAPSS: DS01, DS02, DS03, DS04, DS05, DS06, DS07

## 5) Veri Yeniden Üretme (opsiyonel)

Eğer pipeline CSV'leri değiştiyse, JSON verilerini yeniden üretmek için:

```bash
# Python 3 gerekli
cd 09_webapp
python preprocess_all_datasets.py
```

Bu komut `public/data/` altındaki tüm JSON dosyalarını yeniden oluşturur.

## 6) Production Build & Deploy

```bash
npm run build           # dist/ oluşturur
npx vercel --prod ./dist  # Vercel'e deploy
```

## Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| `npm run dev` çalışmıyor | Node.js v18+ yüklü mü? `node --version` |
| Veriler görünmüyor | `public/data/datasets.json` var mı? Yoksa: `python preprocess_all_datasets.py` |
| Port 5173 meşgul | `npx vite --port 3000` |
