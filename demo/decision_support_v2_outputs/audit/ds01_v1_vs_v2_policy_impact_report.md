# DS01 V1->V2 Policy Impact Report

## Amaç
Bu rapor, N-CMAPSS DS01 için v1 ve v2 decision-support çıktıları arasındaki farkın kaynağını doğrular.
Hedef soru: "Fark yüksek çünkü bug var mı, yoksa policy/threshold etkisi mi?"

## İncelenen Artefact'lar
- `/Users/elifgungen/Downloads/JET-CUBE 3/OUTPUTS/ncmapss_DS01_decision_support.csv` (v1)
- `/Users/elifgungen/Downloads/JET-CUBE 3/OUTPUTS/ncmapss_DS01_decision_support_v2.csv` (v2)
- `/Users/elifgungen/Downloads/JET-CUBE 3/OUTPUTS/audit/delta_ncmapss_ds01.csv`
- `/Users/elifgungen/Downloads/JET-CUBE 3/OUTPUTS/audit/hardening_diagnostics.json`
- Yardımcı tablolar:
  - `/Users/elifgungen/Downloads/JET-CUBE 3/OUTPUTS/audit/ds01_transition_matrix.csv`
  - `/Users/elifgungen/Downloads/JET-CUBE 3/OUTPUTS/audit/ds01_split_change_ratio.csv`

## Kısa Sonuç
DS01'de v1->v2 farkı yüksektir, ancak bulgular bug yerine policy/threshold etkisini göstermektedir.
Ana sürücü, v2'de `theta_rul=30` kullanımıdır; bu eşik v1'e göre daha konservatif planlı bakım üretir.

## Kanıt 1: Karar Dağılımı Değişimi
- v1 dağılımı:
  - Normal Operation: 845
  - Enhanced Monitoring: 46
  - Planned Maintenance: 3
- v2 dağılımı:
  - Normal Operation: 591
  - Planned Maintenance: 302
  - Immediate Maintenance: 1

Toplam join edilen satır: 894
- Değişen satır: 329
- Değişim oranı: 0.3680 (36.8%)

## Kanıt 2: Eşik Farkı (Policy Farkı)
- v1 `theta_rul_used`: `3.64273117`
- v2 `theta_rul_used`: `30.0`
- v1 `alpha_anomaly_used`: `0.0488833139465921`
- v2 `alpha_high_used`: `0.2244259483191497`
- v2 `alpha_low_used`: `0.2019833534872347`

Yorum:
- v2 RUL eşiği v1'e göre belirgin şekilde yüksek (daha erken planlı bakım tetikler).
- v2 anomaly eşiği de daha yüksek; anomaly kaynaklı ON state çok nadir kalır.

## Kanıt 3: Değişimin Kaynağı (Transition Analizi)
En büyük geçişler:
- Normal Operation -> Planned Maintenance: 282
- Enhanced Monitoring -> Normal Operation: 29
- Enhanced Monitoring -> Planned Maintenance: 17
- Normal Operation -> Immediate Maintenance: 1

Değişen 329 satırın:
- 282 tanesi (%85.7) `Normal -> Planned` geçişidir.
- Bu 282 satırın tamamında `rul_pred <= 30`.
- Bu 282 satırın tamamında `anomaly_state = OFF` (anomaly tetiklemiyor).

## Kanıt 4: Anomaly'nin Etkisinin Düşük Olması
v2 anomaly state dağılımı:
- OFF: 893
- ON: 1

Değişen satırlarda anomaly state:
- OFF: 328
- ON: 1

Yorum:
- Farkın neredeyse tamamı anomaly kaynaklı değil, RUL eşiği/policy kaynaklı.

## Kanıt 5: Split Bazında Tutarlılık
- test split: 341 satır, değişim oranı 0.3636
- train split: 553 satır, değişim oranı 0.3707

Yorum:
- Etki tek bir split'e özgü değil; policy farkı her iki split'te benzer çalışıyor.

## Değerlendirme
"DS01’de v1->v2 farkı yüksek; bu bug değil, policy/threshold etkisi" ifadesi veriye dayalı olarak doğrudur.
Özellikle `theta_rul=30` seçimi, `Planned Maintenance` sınıfını belirgin artırmaktadır.

## Operasyonel Not (MVP)
Bu katman human-in-the-loop decision support içindir.
Çıktılar otomatik bakım emri üretmez; mühendis onayıyla aksiyona çevrilir.

## Önerilen Sonraki Adımlar
1. DS bazlı theta kalibrasyonu (örn. sabit 30 yerine quantile veya segment bazlı).
2. Operasyonel raporlamada `test` split ayrı değerlendirme (opsiyonel export zaten mevcut).
3. Delta raporu scriptinde `change_ratio` hesaplamasını doğrulayan küçük bir kontrol ekleme.
