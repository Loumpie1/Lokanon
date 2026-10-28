# Lokanon – lokaler Anonymisierer für Kanzleien

Erkennt und ersetzt personenbezogene und vertrauliche Daten **lokal**, bevor Text an eine KI (ChatGPT, Claude …) geht,
und übersetzt die KI-Antwort wieder zurück. Kein Cloud-Dienst, keine API: Presidio + spaCy + GLiNER + RapidOCR + eigene
Regeln, eigene Oberfläche im Programmfenster (FastAPI + pywebview). Version 2.0-pilot.

**Für Endanwender:** Installer aus `build/` (siehe `build/README.md`) und die Anleitung in der App („Anleitung“) bzw.
unter `static/anleitung/index.html`. Pilot-Hinweis und Rückmeldebogen: `docs/pilot/`.

## Entwicklung einrichten (Windows)

1. Python 3.13 (normaler Build, nicht free-threaded) installieren.
2. `setup.bat` doppelklicken: legt `%USERPROFILE%\Lokanon\venv` an, installiert `requirements.txt`, spaCy-Modell
   `de_core_news_lg`, prüft RapidOCR und lädt GLiNER (`urchade/gliner_multi_pii-v1`, ca. 1,1 GB) in den Hugging-Face-Cache.
3. `start.bat` → Programmfenster. Alternativ `python lokanon.py --browser` (Standardbrowser) oder `--port 8765`.

Nach der Einrichtung läuft alles offline (`HF_HUB_OFFLINE=1` wird vom Starter gesetzt).

## Bedienung (Kurzfassung)

1. **Start**: Vorgang benennen, Dateien per Drag & Drop ablegen, Aktenordner wählen oder Text einfügen. Die Analyse startet
   automatisch; gescannte PDF-Seiten werden per Texterkennung gelesen (auch gedrehte Scans).
2. **Prüfen**: Karten nach Art (Personen, Firmen, Adressen, Kontaktdaten, Akten …) mit Fundstelle, Sicherheit und Schalter.
   „benennen“ vergibt eine eigene Bezeichnung (`[MANDANT]` statt `[PERSON_1]`), die überall im Vorgang gilt. Rechts das
   Original mit Markierungen (Etikett = Platzhalter, gestrichelt = bleibt stehen) oder die anonymisierte Fassung.
   „Bitte ansehen“ listet unsichere Treffer. Übersehenes nachtragen.
3. **Fertigstellen**: Prüfung bestätigen, „Dateien erzeugen“. Ergebnis je Datei mit Leck-Test-Status, „Ordner öffnen“,
   KI-Anweisung zum Kopieren, Schlüssel mit Passwort speichern.
4. **Antwort**: KI-Antwort einfügen, Platzhalter werden ersetzt (auch `[MANDANT]`, „Person 1“, `[PERSON_1]s`).
   Frühere Vorgänge über „Antwort zurückübersetzen“ mit Schlüsseldatei und Passwort.

Vorgangsordner (bei Upload/Text unter `%USERPROFILE%\Lokanon\Vorgaenge\<Name>`, bei Aktenordner `<Akte>\Lokanon`):
`Originale\`, `Anonymisiert\` (Originalnamen), `Fuer die KI\` (bereinigte Namen – hochladen), `Pruefbericht.html`
(Klartext!), `Uebersicht.csv`, `Protokoll.md/.json`. Schlüssel: `%USERPROFILE%\Lokanon\schluessel\<Name>.anon.json`.
Einstellungen: `%USERPROFILE%\Lokanon\einstellungen.yaml` (Vorlage `config.default.yaml`).

Startet Lokanon nicht, steht der Grund in `%USERPROFILE%\Lokanon\lokanon.log` (das Programmfenster zeigt beim Start
eine Wartemeldung; der erste Start nach der Installation kann ein bis zwei Minuten dauern).

Platzhalter sind innerhalb eines Vorgangs konsistent (auch über mehrere Dateien, Namensteile und Genitiv), zwischen
Vorgängen beginnt die Zählung neu.

## Projektstruktur

```
lokanon.py                      Starter: Server auf 127.0.0.1 + Programmfenster (pywebview/WebView2), --browser Fallback
server/app.py                   HTTP-Schnittstelle (FastAPI), nur lokal
server/dienst.py                Vorgangsdienst: Analyse mit Fortschritt, Begriffe, Bezeichnungen, Ausgabe, Schlüssel
server/einstellungen.py         persönliche Einstellungen (einstellungen.yaml), Gruppen-Auffüllung
ui/                             Oberfläche: index.html, app.css (Designsystem), app.js, fonts/ (Source Sans 3, Source Serif 4)
anonymizer/engine.py            Erkennung, Bereinigung, vorgangsweite Propagation, Pseudonyme, Bezeichnungen, Rückübersetzung
anonymizer/recognizers_de.py    Deutsche Muster (Telefon, Adresse, Aktenzeichen, Diktatzeichen, FIN, Grundbuch, Versicherung,
                                Datum in Worten …) + 13 eingebaute Presidio-DE-Erkenner
anonymizer/ocr.py               Texterkennung für Scans (RapidOCR) mit Ausrichtung, Pixel-Schwärzung, OCR-Gegenprüfung
anonymizer/files.py             Dateien lesen; Word-/Excel-/PDF-Kopien, Metadaten entfernen, PDF-Leck-Test
anonymizer/vorgang.py           Vorgangsordner, Dateinamen, Übersicht, Protokoll, Prüfbericht, Schlüsseldatei
anonymizer/vault.py             Schlüsseldatei verschlüsselt (PBKDF2 + Fernet)
ki-anweisung/                   Projekt-Anweisung für ChatGPT/Claude und Claude-Skill
docs/vorlagen/                  Rechtliche Textbausteine (Art. 13, Verarbeitungsverzeichnis, Anbieter-Checkliste)
docs/pilot/                     Pilot-Hinweis, Rückmeldebogen
static/anleitung/               Endanwender-Anleitung (HTML, offline, in der App eingebettet)
build/                          Installer (python-build-standalone + Inno Setup)
video/                          Produktvideo (Remotion)
evaluate.py, evaluate.bat       Qualität messen (mit testdaten/kanzlei/config_eval.yaml)
tests/                          pytest: Erkennung v1/v2, OCR, PDF, Vorgang, API
testdaten/                      fiktive Kanzleifälle, Scan-Testdatei
```

## Qualität

`evaluate.bat` misst gegen `testdaten/kanzlei/referenz_markierungen.jsonl` (Stand 28.10.2026: Recall 98 %, Precision 98 %;
nur indirekte Identifikatoren fehlen). Die Regeln sind an diesen Fällen und an einem echten Pilot-Testvorgang geschärft;
echte Akten werden einzelne Lücken zeigen – die Prüfung in Schritt 2 ist Pflicht. Tests: `python -m pytest tests -q`
(ca. 3 Minuten, lädt spaCy; `tests/test_server.py` läuft gegen einen Temp-Datenordner).

## Grenzen

- Keine Erkennung ist vollständig; indirekte Identifikatoren (Rolle + Einrichtung + Ort) erkennt die Software nicht.
- Mit gespeichertem Schlüssel ist das Ergebnis pseudonymisiert, nicht anonym (für die Kanzlei bleibt der Personenbezug).
- Word/Excel: Kommentare, Änderungsverfolgung, Textfelder werden noch nicht bereinigt → für die KI die Textfassung nehmen.
- Scans: OCR-Text kann Fehler enthalten (Handschrift, Stempel, schlechte Qualität); Sichtkopien nur nach bestandener
  Gegenprüfung.
- Kein Praxis-Profil, keine Code-Signatur (SmartScreen-Hinweis) in dieser Version.
