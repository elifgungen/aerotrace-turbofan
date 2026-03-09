Dataset: NASA C-MAPSS FD001
Amaç: RUL (Remaining Useful Life) çalışması için kept sensörlerle sadeleştirilmiş veri

KEPT sensörler (14): s2 s3 s4 s7 s8 s9 s11 s12 s13 s14 s15 s17 s20 s21
DROPPED sensörler (7): s1 s5 s6 s10 s16 s18 s19

Kolon sırası (19 kolon):
  engine_id cycle setting1 setting2 setting3 s2 s3 s4 s7 s8 s9 s11 s12 s13 s14 s15 s17 s20 s21

Format: Boşlukla ayrılmış TXT, header yok

Dosyalar:
  - train_FD001_kept.txt : Eğitim verisi (100 motor, ~20K satır)
  - test_FD001_kept.txt  : Test verisi (100 motor, ~13K satır)
  - RUL_FD001.txt        : Test motorları için gerçek RUL değerleri

Kaynak: NASA Prognostics Data Repository
Referans: Saxena et al., "Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation", PHM08
