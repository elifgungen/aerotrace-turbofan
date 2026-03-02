#!/usr/bin/env python3
"""
RUL Prediction CSV Split Semantic Fix (Tek Dataset Versiyonu)

Kullanım:
  1. Aşağıdaki 3 PATH'i kendi ortamına göre düzenle
  2. python fix_rul_split_single.py

Ne yapar:
  - RUL export'taki split="val" satırlarını split="train" yapar
  - is_validation_subset=True meta column ekler
  - *_FIXED.csv dosyası üretir
  - Anomaly + RUL merge %100 uyumlu olur
"""

import pandas as pd
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
#  SADECE BU 3 YOLU DEĞİŞTİR
# ═══════════════════════════════════════════════════════════════════════════

DATASET_ID = "DS05"  # <-- Hangi dataset? (DS05, DS06, DS07 vs.)

RUL_CSV = Path("/content/drive/MyDrive/N-CMAPSS_DS05/OUTPUTS/ncmapss_DS05_rul_predictions_autogluon.csv")

CANONICAL_TRAIN = Path("/content/drive/MyDrive/N-CMAPSS_DS05/DS05/train_DS05_v0.csv")

CANONICAL_TEST = Path("/content/drive/MyDrive/N-CMAPSS_DS05/DS05/test_DS05_v0.csv")

# ═══════════════════════════════════════════════════════════════════════════
#  BURADAN AŞAĞI DOKUNMA
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print(f"[{DATASET_ID}] RUL Split Semantic Fix")
    print("val → train re-mapping (canonical alignment)")
    print("=" * 60)

    # Dosya kontrolleri
    for label, p in [("RUL CSV", RUL_CSV), ("Canonical Train", CANONICAL_TRAIN), ("Canonical Test", CANONICAL_TEST)]:
        if not p.exists():
            raise FileNotFoundError(f"{label} bulunamadı: {p}")
        print(f"  ✅ {label}: {p}")

    # Oku
    rul_df = pd.read_csv(RUL_CSV)
    canonical_train = pd.read_csv(CANONICAL_TRAIN, usecols=["engine_id", "cycle"])
    canonical_test = pd.read_csv(CANONICAL_TEST, usecols=["engine_id", "cycle"])

    train_engines = set(canonical_train["engine_id"].unique())
    test_engines = set(canonical_test["engine_id"].unique())

    # Leakage kontrolü
    overlap = train_engines & test_engines
    if overlap:
        raise ValueError(f"❌ LEAKAGE! Train/test engine overlap: {overlap}")
    print(f"\n  Train engines: {sorted(train_engines)}")
    print(f"  Test engines:  {sorted(test_engines)}")
    print(f"  ✅ Engine overlap yok")

    # Fix öncesi durum
    split_before = rul_df["split"].value_counts().to_dict()
    val_count = split_before.get("val", 0)
    print(f"\n  Split BEFORE: {split_before}")

    # is_validation_subset ekle
    rul_df["is_validation_subset"] = rul_df["split"] == "val"

    # Canonical split'e göre re-map
    def get_canonical_split(row):
        eid = row["engine_id"]
        if eid in train_engines:
            return "train"
        elif eid in test_engines:
            return "test"
        else:
            raise ValueError(f"Engine {eid} canonical'de yok!")

    rul_df["split"] = rul_df.apply(get_canonical_split, axis=1)

    # Fix sonrası durum
    split_after = rul_df["split"].value_counts().to_dict()
    print(f"  Split AFTER:  {split_after}")
    print(f"  Val → Train re-mapped: {val_count}")

    # Kaydet
    out_path = RUL_CSV.parent / RUL_CSV.name.replace(".csv", "_FIXED.csv")
    rul_df.to_csv(out_path, index=False)

    # Doğrulama
    rul_train_engines = set(rul_df[rul_df["split"] == "train"]["engine_id"].unique())
    rul_test_engines = set(rul_df[rul_df["split"] == "test"]["engine_id"].unique())

    print(f"\n  Train engines match: {'✅' if rul_train_engines == train_engines else '❌'}")
    print(f"  Test engines match:  {'✅' if rul_test_engines == test_engines else '❌'}")

    canonical_total = len(canonical_train) + len(canonical_test)
    print(f"  Row count: RUL={len(rul_df)}, Canonical={canonical_total} {'✅' if len(rul_df)==canonical_total else '⚠️'}")

    print(f"\n{'=' * 60}")
    print(f"✅ [{DATASET_ID}] FIXED!")
    print(f"   Output: {out_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
