# Wortlisten für die Plausibilitätsprüfung

Lokanon prüft damit, ob ein vorgeschlagener Name in Wirklichkeit ein gewöhnliches deutsches Wort ist
("Gespräch", "Ferienregelung"). Die Listen werden nur lokal gelesen.

| Datei | Inhalt | Quelle |
|---|---|---|
| substantive.txt.gz | ca. 184 000 deutsche Substantive mit Beugungsformen | Wiktionary (über kaikki.org, Abzug 04.11.2026) |
| adjektive.txt.gz | ca. 147 000 deutsche Adjektive mit Beugungsformen | Wiktionary (über kaikki.org) |
| vornamen.txt.gz | ca. 1 800 Vornamen | Wiktionary (über kaikki.org) |
| nachnamen.txt.gz | ca. 4 700 Nachnamen | Wiktionary (über kaikki.org) |

Lizenz der Listen: Creative Commons Namensnennung – Weitergabe unter gleichen Bedingungen 4.0 (CC BY-SA 4.0),
Urheber: die Autorinnen und Autoren von Wiktionary (https://www.wiktionary.org), aufbereitet von kaikki.org
(Tatu Ylonen, Wiktextract). Die Dateien sind ein Auszug (nur Wortformen) und stehen unter derselben Lizenz.

Zusätzlich (05.11.2026, gebaut mit `experimente/messlatte/listen_bauen.py`):

| Datei | Inhalt | Quelle |
|---|---|---|
| medizin.txt.gz | ca. 40 600 medizinische Wörter: Wirkstoffe, Handelsnamen, Krankheiten, Anatomie, Laborwerte; ohne Eigennamen aus Krankheitsbezeichnungen („Alzheimer“, „Crohn“) | Wikidata (Bezeichnungen zu ATC-, ICD-10/11-, MeSH-, TA98-, LOINC-, RxNorm-Codes) |
| vornamen_wikidata.txt.gz | ca. 16 000 weitere Vornamen, ohne solche, die gewöhnliche deutsche Wörter sind | Wikidata (Vornamen, männlich/weiblich/neutral) |

Lizenz dieser beiden Listen: CC0 1.0 (Wikidata), keine Bedingungen.
