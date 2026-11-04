# Modellvergleich (04.11.2026)

Ausgetauscht wurde nur das zweite KI-Modell neben spaCy. Regeln, Felder, Wörterbuch und Filter blieben gleich.
Konfiguration `testdaten/kanzlei/config_eval.yaml`, Messung mit `vergleich.py` (Ergebnisse in `ergebnisse.json`).

| Variante | Testsammlung R / P | Prüfsammlung R / P | Kanzlei R / P | s je 1000 Zeichen |
|---|---|---|---|---|
| jetzt: urchade/gliner_multi_pii-v1 | 99,3 / 99,2 | 96,2 / 94,6 | 100 / 99,0 | 1,8–2,2 |
| naeyn/nobody-pii-de, unsere Labels | 99,3 / 97,2 | 96,2 / 95,7 | 100 / 99,0 | 1,6–1,8 |
| naeyn/nobody-pii-de, eigene 4 Labels | 95,6 / 97,2 | 96,2 / 95,7 | 100 / 99,0 | 1,1–1,2 |
| fastino/gliner2-privacy-filter-PII-multi | 98,9 / 98,1 | 97,1 / 93,9 | 100 / 98,1 | 1,3–1,5 |
| GLiNER2-PII + Label „company“ | 98,9 / 98,4 | 97,1 / 93,9 | 100 / 98,1 | 1,3–1,5 |

**Ergebnis: kein Wechsel.** Die Unterschiede betreffen je Sammlung ein bis zwei Angaben (Prüfsammlung: 104 Angaben).
Das liegt im Rauschen.

- nobody-pii-de: Zwei Fehlalarme fallen weg („König-Heinrich-Platz 1“, „Orthopädische Gemeinschaftspraxis“), dafür
  kommen „Dipl“ als Person und zwei Fehlalarme in der Testsammlung dazu. Mit den eigenen 4 Labels fehlen die
  E-Mail-Adressen. Das liegt an den Testdaten (Endung `.example`, die die E-Mail-Regel ablehnt), nicht am Modell.
- GLiNER2-PII: findet „K77013“ und die Personalnummer im Lohnscan zusätzlich, verliert im Lohnscan Steuer-ID und
  SV-Nummer und bringt „88.410“ als Steuer-ID und „BARMER“ als Person neu.
- Rund 15–40 % schneller als das jetzige Modell. Das allein rechtfertigt keinen Wechsel.

**Nebenbefund:** Im Lohnscan (`L1_…_scan.pdf`) fehlen in der Wertezeile unter „Steuer-ID | SV-Nummer | …“ die
Spaltentrenner. Die Felderkennung ordnet die Werte dann nicht zu, nur das KI-Modell findet sie. In der PDF-Fassung
erkennen die Regeln beide Nummern.
