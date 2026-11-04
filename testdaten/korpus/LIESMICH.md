# Testsammlung Erkennung (fiktiv)

16 erfundene Dokumente in vier Familien plus 6 Scan-Varianten. Erzeugt von `generate.py`, Referenz in
`referenz.jsonl` (Text so, wie Lokanon ihn liest; bei Scans der OCR-Text).

| Familie | Dokumente | Prüft vor allem |
|---|---|---|
| schriftsatz | Klage (DOCX), Schreiben der Gegenseite (PDF), E-Mail-Verlauf (TXT), Vollmacht (DOCX) | Gegenseite-Kanzlei, Signaturen, Gericht/eigene Kanzlei bleiben stehen |
| bescheid_formular | Bußgeldbescheid, Schadenmeldung, Europäischer Unfallbericht, Rentenbescheid | Formularfelder („Name“, „Vorname“), Tabellen, Kennnummern |
| lohn_konto_rechnung | Lohnabrechnung, Kontoauszug, Handwerkerrechnung, Betriebskosten (XLSX) | Fachbegriffe, Beträge, Firmen, Kunden-/Vertragsnummern |
| arzt_gutachten | Arztbrief, Kfz-Gutachten, AU-Bescheinigung, Familiengutachten | Krankheitsnamen („Morbus Crohn“), Medikamente, Testverfahren |
| scans | 6 der Dokumente als leicht schiefer, verrauschter Scan, 3 davon mit unsichtbarer Textebene | Texterkennung |

Markierungen: wie in `testdaten/kanzlei`, dazu `OPTIONAL` (darf maskiert werden, muss nicht: Behörden-IBAN,
Tatort, Rechnungsnummer) und `KENNNUMMER` (Kunden-, Vertrags-, Fall-, Kassenzeichen). Werte, die im gelesenen Text
nicht mehr auffindbar sind (OCR verstümmelt), stehen unter `fehlend` und zählen als übersehen.

Messen (Projektordner, venv):

```
python evaluate.py --config testdaten\kanzlei\config_eval.yaml testdaten\korpus\referenz.jsonl
python evaluate.py --config testdaten\kanzlei\config_eval.yaml --gegen testdaten\korpus\messungen\basis.json testdaten\korpus\referenz.jsonl
```

`messungen/basis.json` ist die Basislinie vom 04.11.2026 (spaCy + GLiNER): Recall 89 %, Precision 87 %.
Nach Erkennung v3 (`messungen/b5.json`): Recall 99 %, Precision 99 % – Achtung: an dieser Sammlung entwickelt,
die unabhängige Messung steht in `testdaten/pruefung`.
`tests/test_korpus.py` prüft Untergrenzen je Familie (nur spaCy).
