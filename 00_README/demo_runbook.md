# Demo Runbook — AeroTrace Karar Destek Platformu

Bu doküman, AeroTrace web uygulamasını jüri/sunum ortamında çalıştırmak için adım adım kılavuz sağlar.

## Seçenek A: Canlı Demo (önerilen)

Herhangi bir kurulum gerektirmez — tarayıcıdan erişin:

🌐 **[https://dist-ebon-nine.vercel.app](https://dist-ebon-nine.vercel.app)**

## Seçenek B: Yerel Çalıştırma

### 1) Kurulum

```bash
cd 09_webapp
npm install
```

### 2) Çalıştırma

```bash
npm run dev
```

Tarayıcıda **http://localhost:5173** açılır.

### 3) Veri Gereksinimleri

Tüm veri dosyaları `public/data/` altında hazır gelir (11 dataset). Ekstra adım gerekmez.

Eğer veri dosyaları eksikse:
```bash
python preprocess_all_datasets.py
```

---

## Jüri Demo Modu (Rehberli Sunum)

AeroTrace, sunumlarda kullanmak üzere entegre bir **Jüri Demo** modu içerir.

### Başlatma
1. Sol alt köşedeki **"▶ Jüri Demo"** butonuna tıklayın
2. Ekranın ortasında yarı-saydam narration overlay belirir
3. **"İleri →"** butonuyla adım adım ilerleyin

### Demo Akışı (6 adım)

| Adım | Sayfa | Gösterilen |
|------|-------|-----------|
| 1 | Intro | Proje tanıtımı, pipeline akışı, karar seviyeleri |
| 2 | Ana Sayfa | Filo istatistikleri, dataset seçici |
| 3 | Filo Görünümü | Risk matrisi, karar dağılımı, motor tablosu |
| 4 | Motor Detay | RUL & Anomaly timeline, "Neden Bu Karar?" paneli |
| 5 | 3D Twin | 3D motor modeli, bileşen sağlığı animasyonu |
| 6 | Audit | Policy snapshot, veri kalitesi kontrolleri |

### Çıkma
Demo herhangi bir adımda **"✕"** ile kapatılabilir.

---

## Sunum Senaryosu (Önerilen Akış)

### 1. Giriş (2 dk)
- Intro sayfasını gösterin — proje vizyonu ve pipeline
- "Bu bir **karar destek** sistemi, otonom karar vermiyor" vurgusu

### 2. Filo Genel Bakış (2 dk)
- Ana sayfada dataset seçiciyi gösterin (11 senaryo)
- Filo Görünümüne geçin → risk matrisi ve motor tablosu

### 3. Motor Detay (3 dk)
- Herhangi bir motorun "Detay →" butonuna tıklayın
- Timeline'da RUL ve anomali trendini gösterin
- "Neden Bu Karar?" panelini açıklayın — Türkçe metin, metrik chip'ler, neden kodları
- Cycle slider'ı kaydırarak kararın nasıl değiştiğini gösterin

### 4. 3D Digital Twin (2 dk)
- Sidebar'dan 3D Twin'e geçin
- Auto-Play ile degradasyon animasyonunu başlatın
- Bileşen sağlık bar'larının değişimini gösterin

### 5. Audit & Kanıt (1 dk)
- Policy version, eşik değerleri, veri kalitesi kontrollerini gösterin
- "Her karar denetlenebilir ve geriye dönük izlenebilir" vurgusu

---

## Ekran / Panel Açıklaması

### Filo Görünümü
- **Risk Matrisi:** X=Anomaly Score, Y=RUL — motorları görsel olarak konumlar
- **Karar Dağılımı:** 4 seviye donut chart
- **Motor Tablosu:** ID, RUL, Anomaly, Durum, Aksiyon ile sıralanabilir tablo

### Motor Detay
- **Timeline:** Dual-axis — RUL (sol), Anomaly Score (sağ), eşik çizgileri, bölge renkleri
- **Neden Bu Karar?:** Yapısal Türkçe açıklama, metrik chip'ler (RUL, θ, Anomali, α), neden kodları
- **Durum Geçişleri:** Motor yaşam döngüsü boyunca karar değişimleri

### 3D Digital Twin
- **3D Model:** 7 bileşen (Fan, LPC, HPC, Combustor, HPT, LPT, Shaft) — renk = sağlık
- **Sağlık Paneli:** Bileşen bazında yüzde barları
- **Not:** "3D görünüm temsilîdir; karar destek amaçlı şematik sağlık görselleştirmesi"
