# FD001_Ozcan_AllRaws — Kapsamlı Özet (All_Rows Odaklı)
## 1) Kapsam ve Amaç
- Bu klasör **All_Rows** değerlendirme hedefi için düzenlenmiştir.
- Amaç: Tüm cycle satırlarında RUL tahmini kalitesini maksimize etmek (MVP demo için).
- **CAP=125** uygulanmış etiketlerle çalışıyoruz (RUL kırpma).
## 2) Veri ve Ön İşleme Özeti
- Girdi: FD001, **Sensor_Full**, z‑score normalize edilmiş CSV.
- Sensör düşürülmedi.
- Etiket: her cycle için RUL; **CAP=125** ile kırpıldı.
- **Cycle feature** dahil edildi (cycle sütunu model girdisinde).
## 3) Modelleme ve Ensemble
- Base modeller: **LightGBM + CatBoost** (Özcan hiperparametreleri).
- Ensemble: **OOF Ridge Stacking** (GroupKFold(engine_id)).
- Meta‑öğrenici: Ridge (alpha=1.0).
- Hedef: **All_Rows** metrikleri.
## 4) Kullanılan Metrikler (All_Rows)
- **RMSE**, **MAE**, **R²**, **PHM08 RUL Score**.
- PHM08 formülü: d = (y_pred − y_true); d<0 için exp(−d/a1), d≥0 için exp(d/a2) toplamı; a1=10, a2=13.
## 5) Sonuçlar (All_Rows)
| Model | RMSE | MAE | R² | PHM08 |
|---|---:|---:|---:|---:|
| lgbm | 16.1618 | 10.4152 | 0.6566 | 123613.65 |
| catboost | 15.8798 | 10.1562 | 0.6685 | 113795.64 |
| ensemble | 15.8655 | 10.2521 | 0.6691 | 111301.96 |

**Not:** last_cycle metrikleri raporda tutulabilir ama **optimizasyon hedefi değildir**.
## 6) Görselleştirmeler (All_Rows)
- Tek motor life‑story (CAP’li): `C:/Havelsan/outputs/FD001_Ozcan_AllRaws/fig_all_rows_rul_life_story_engine_max_cap125.png`
- Parity plot (tüm satırlar): `C:/Havelsan/outputs/FD001_Ozcan_AllRaws/fig_all_rows_parity_cap125.png`
- Tüm motorlar agregat life‑story: `C:/Havelsan/outputs/FD001_Ozcan_AllRaws/fig_all_rows_lifestory_aggregate_cap125.png`
## 7) Yorumlar — İyi ve Geliştirilebilir Noktalar
**İyi:**
- All_Rows’ta trend doğru, parity grafiğinde genel doğrultu korunuyor.
- Life‑story agregatta medyan düşüş yönü doğru.

**Geliştirilebilir:**
- CAP=125 üst bölgede doğal plato yaratıyor; bu bias’ı raporda açık belirtmek gerekir.
- Düşük RUL bölgesinde hata dağılımı daha geniş; karar destek için risk ölçümü gerekir.
## 8) Eksikler ve Riskler
- All_Rows odaklı model, **düşük RUL kritik bölgesi** için yeterli güvenlik garantisi vermez.
- CAP sabitliği farklı datasetlerde (FD002–FD004) genellenmeyebilir.
- Model, işletim koşullarındaki değişimi yeterince ayrıştırmıyor olabilir.
## 9) İyileştirme Önerileri (All_Rows odaklı)
- AutoGluon ile **model aile taraması** (GBM/XT/RF/XGB/CAT) ve ardından Opfunu HPO.
- RUL dilimlerine göre hata analizi (0–30, 30–60, 60–90, 90–125).
- Hata türü raporu: düşük RUL’de **over‑estimate** oranı.
- İhtiyaç halinde CAP sensitivite analizi (FD002/FD003/FD004 öncesi).
## 10) Sonraki Adım
- AutoGluon sonuçlarını alıp Opfunu ile finalist HPO.
- Ardından FD002 geçişi (aynı All_Rows protokolü).
## 11) Açık Sorular (varsa)
- All_Rows hedefi için **ana karar metriği** RMSE mi, PHM08 mi olacak?
- RUL kritik eşik (örn. 30) ve yanlış‑pozitif/negatif toleransını netleştirelim mi?
