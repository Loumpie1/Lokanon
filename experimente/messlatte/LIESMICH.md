# Messlatte aus öffentlichen Daten (05.11.2026)

Die eigenen Sammlungen (Testsammlung, Prüfsammlung, Kanzleifälle) sind klein, selbst geschrieben und fast gelöst.
Sie zeigen kaum noch, ob eine Änderung hilft. Deshalb messen wir zusätzlich an öffentlichen deutschen Datensätzen
mit markierten Personenangaben. Die Daten liegen außerhalb des Projekts unter `%USERPROFILE%\Lokanon\messdaten`
und kommen nicht ins Repository.

## Quellen

| Datensatz | Inhalt | Lizenz | Herkunft |
|---|---|---|---|
| German LER (Leitner, Rehm, Moreno-Schneider 2019) | 66 723 Sätze aus Bundesgerichtsurteilen, 19 Arten | CC BY 4.0 | github.com/elenanereiss/Legal-Entity-Recognition, `data/ler.conll` |
| GraSCCo_PII V2 (Modersohn u. a.) | 63 erfundene Arztbriefe, 1 439 markierte Angaben | CC BY 4.0 | Zenodo 11502329, `grascco_phi_annotation_json.zip` |
| Wikidata | deutsche Bezeichnungen mit ATC-, ICD-10/11-, MeSH-, TA98-, LOINC-, RxNorm-Code; Vornamen | CC0 | query.wikidata.org (SPARQL, 05.11.2026) |
| CodE Alltag 2.0 | 800 E-Mails (pseudonymisiert) | CC BY-SA 4.0 | github.com/codealltag | 

CodE Alltag enthält nur die pseudonymisierten Texte, nicht die markierten Stellen. Als Messlatte taugt es deshalb
nicht und wurde nicht geladen.

## Aufteilung

`umwandeln.py` schreibt je Datensatz einen Mess- und einen Trainingsteil im Format von `evaluate.py`:

- **LER:** 25 Sätze ergeben einen Abschnitt. Die letzten 20 % der Abschnitte sind nur zum Messen da
  (`ler_test.jsonl`, 139 Abschnitte); der Rest ist für Entwicklung und Training (`ler_train.jsonl`).
- **GraSCCo:** jedes dritte Dokument zum Messen (`grascco_test.jsonl`, 21 Briefe), der Rest für Entwicklung und
  Training (42 Briefe).
- An den Messteilen wird nicht nachgebessert. Fehler werden nur in den Trainingsteilen angesehen.

Wie die Labels auf Lokanon übertragen werden, steht oben in `umwandeln.py`. Kurz gesagt:
- **Was Lokanon nach seinen Einstellungen bewusst stehen lässt, zählt als OPTIONAL:**
  - Gerichte, Gesetze und Aktenzeichen veröffentlichter Urteile
  - Kliniknamen
  - Daten außer dem Geburtsdatum
  - Städte ohne Anschrift
- **Initialen in Urteilen** („F.“) sind dort schon anonymisiert und zählen ebenfalls als OPTIONAL.

## Ablauf

    python experimente/messlatte/umwandeln.py      # Rohdaten → *_test.jsonl / *_train.jsonl
    python experimente/messlatte/listen_bauen.py   # Wikidata → anonymizer/daten/medizin.txt.gz, vornamen_wikidata.txt.gz
    python experimente/messlatte/messen.py NAME [--gegen BASIS] [--sets …]

## Ergebnisse

Siehe unten (wird nach jeder Messrunde ergänzt).
