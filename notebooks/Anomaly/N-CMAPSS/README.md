# N-CMAPSS 2 - Çalışma Özeti

Bu klasör, Jet-Cube N-CMAPSS anomaly scoring çalışmalarının paylaşıma uygun çıktısını içerir.

## Klasör Yapısı
- `scripts/compute_anomaly_ncmapss.py`: Üretim anomaly scoring scripti
- `OUTPUTS/`: DS bazlı anomaly skor çıktıları (`ncmapss_DSXX_anomaly_scores.csv`)
- `data/`: İşleme girdileri / yardımcı veriler
- `ANOMALY_REPORT.md`: Anomaly kalite/doğrulama raporu
- `SPLIT_SEMANTICS_AUDIT_REPORT.md`: Sorunun tespiti, Senaryo A/B kanıtı ve çözüm stratejisi

## Tamamlanan İşler
1. N-CMAPSS DS01-DS07 için anomaly score üretildi.
2. Çıktılar aşağıdaki contract'e göre doğrulandı:
   - Kolonlar: `dataset_id, split, engine_id, cycle, anomaly_score, anomaly_raw`
   - `split in {train,test}`
   - Key duplicate yok (`dataset_id, split, engine_id, cycle`)
   - `anomaly_score` aralığı `[0,1]`
   - `NaN/Inf` yok
3. Senaryo A/B split-semantics audit'i (DS01-DS04) çalıştırıldı ve `VERDICT: A` bulundu.

## Önemli Not (Decision-Support Öncesi)
Anomaly çıktıları canonical `train/test` split semantiğine göre üretilmiştir.
RUL çıktılarında `val` kullanımı varsa, decision-support birleşimi öncesi canonical split'e göre
re-label/re-export yapılmalıdır.

## Hızlı Çalıştırma
```bash
python3 scripts/compute_anomaly_ncmapss.py \
  --dataset DS04 \
  --input_root /path/to/N-CMAPSS \
  --output_root /path/to/OUTPUTS \
  --method mahalanobis \
  --seed 42 \
  --chunksize 50000
```

## Sonraki Adım
- RUL + Anomaly birleşimi için canonical split tek kaynak olacak şekilde decision-support katmanını finalize etmek.
