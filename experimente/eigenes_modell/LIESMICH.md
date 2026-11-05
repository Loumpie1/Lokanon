# Eigenes Erkennungsmodell (05.11.2026)

Ein deutsches Sprachmodell (deepset/gbert-base, 110 Mio. Parameter) wurde lokal auf der CPU als
Token-Klassifikator nachtrainiert: Person (PER), Firma (ORG), Anschrift mit PLZ und Ort (ADR).
Lokanon bindet es als zusätzlichen Erkenner ein (`anonymizer/eigenes_modell.py`, Einstellung `ner_modell`).

## Training

- **Trainingsdaten** (`daten.py`), zusammen 2 333 Fenster zu höchstens 256 Tokens:
  - LER-Trainingsteil (Urteile): 994 Fenster mit Namen, 331 ohne
  - GraSCCo-Trainingsteil (Arztbriefe), dreifach gewichtet
  - 12 Abwandlungen der Testsammlung mit zufälligen Namen
- **Nicht im Training:** Prüfsammlung, Kanzleifälle und die Messteile von LER und GraSCCo.
- **Rechenaufwand:** 3 Epochen, 251 min auf der CPU (6 Threads, parallel zu anderen Messungen). Der Verlust fiel
  von 0,19 auf 0,002.
- **Ablauf:** `python experimente/eigenes_modell/trainieren.py 3`. Das Modell landet unter `modell/` und ist nicht
  im Repository.

## Ergebnis (Recall / Precision)

| Sammlung | v4 (spaCy + GLiNER) | v4 + eigenes Modell | spaCy + eigenes Modell, ohne GLiNER |
|---|---|---|---|
| Arztbriefe, Messteil | 96,9 / 61,1 | 96,9 / 60,6 | 95,0 / 61,0 |
| Urteile, Messteil | 56,3 / 25,4 | 56,3 / 25,1 | 57,6 / 29,5 |
| Prüfsammlung | 96,2 / 95,6 | 96,2 / 95,6 | 96,2 / 95,3 |
| Kanzleifälle | 100 / 99,0 | 100 / 99,0 | 100 / 98,2 |
| Testsammlung (Abwandlungen im Training) | 99,6 / 99,2 | 99,6 / 99,2 | 97,1 / 99,3 |
| Zeit Urteile (760 000 Zeichen) | 3 175 s | 1 506 s* | 710 s |

\* gleichzeitig mit anderen Messungen gelaufen, Zeiten nur grob vergleichbar.

## Befund

- **Zusätzlich zu GLiNER bringt das eigene Modell nichts.** Was es findet, finden spaCy, GLiNER und die Regeln
  schon. Was übrig bleibt, sind meist Grenzfälle, die kein Modell löst.
- **Statt GLiNER** ist es etwa gleich gut:
  - Urteile: etwas besser
  - Arztbriefe: 3 Angaben weniger
  - Testsammlung: 7 E-Mail-Adressen mit der Test-Endung `.example` und eine Personalnummer weniger. Die fand
    bisher GLiNER; die E-Mail-Regel lehnt die Endung `.example` ab.
- **Rund viermal schneller**, und das Modell ist kleiner (gbert 0,4 GB statt GLiNER mit mdeberta rund 1,1 GB).

## Empfehlung

- Vorerst bei GLiNER bleiben. Der Tausch bringt keine bessere Erkennung, nur Tempo und einen kleineren Installer.
- Interessant wird das eigene Modell, sobald **eigene Testfälle aus echten Prüfungen** vorliegen
  (Einstellungen → Erweitert): Dann lässt es sich auf genau die Dokumente der Kanzlei nachtrainieren. Das kann
  GLiNER nicht.
- Für einen Tausch fehlen noch:
  - E-Mail und Telefon als eigene Labels
  - ein Nachtraining mit echten Testfällen
  - die Messung der Laufzeit im Installer
