__author__ = 'Rudolf Horvath'
__date__ = '2015.06.15'

__encoding__ = 'utf-8'
# encoding: utf-8

"""
Függvények:
 - TracerouteMeasure-ből álló lista kezelése:
  - Json file készítése
  - Beemelése SQLite adatbázisba
  - Éllisták beemelése SQLite adatbázisba
  - IP címek beolvasása
  - DNS nevek beolvasása
 - Ezen funkciók akár adatbázisból beolvasva (nyers traceroute-ból)
 - ip cím - domain név párok tárolása
 - ip cím id párosítás
 - domain név - id párosítás
"""