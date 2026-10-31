# Lokanon – lokaler Anonymisierer für Kanzleien

Erkennt und ersetzt personenbezogene und vertrauliche Daten **lokal**, bevor Dateien an eine KI (ChatGPT, Claude, Gemini)
gehen. Kein Cloud-Dienst, keine API: Presidio + spaCy + GLiNER + RapidOCR + eigene Regeln, eigene Oberfläche im
Programmfenster (FastAPI + pywebview). Version 0.2.0 (Pilot).

**Für Endanwender:** fertiger Installer und Pilot-Paket unter
[Releases](https://github.com/Loumpie1/Lokanon/releases) (Installer ca. 1,4 GB, enthält alle Sprachmodelle). Anleitung in
der App („?“ oben rechts) bzw. unter `static/anleitung/index.html`. Pilot-Hinweis und Rückmeldebogen: `docs/pilot/`,
Marketing-Deck und Filme: `docs/marketing/`, `video/`. Selbst bauen: `build/README.md`.

## Entwicklung einrichten (Windows)

1. Python 3.13 (normaler Build, nicht free-threaded) installieren.
2. `setup.bat` doppelklicken: legt `%USERPROFILE%\Lokanonenv` an, installiert `requirements.txt`, spaCy-Modell
   `de_core_news_lg`, prüft RapidOCR und lädt GLiNER (`urchade/gliner_multi_pii-v1`, ca. 1,1 GB) in den Hugging-Face-Cache.
3. `start.bat` → Programmfenster. Alternativ `python lokanon.py --browser` (Standardbrowser) oder `--port 8765`.

Nach der Einrichtung läuft alles offline (`HF_HUB_OFFLINE=1` wird vom Starter gesetzt).

## Bedienung: ein Bildschirm, drei Zustände

1. **Ablegen**: Dateien per Drag & Drop, „Ordner wählen“ oder „Text einfügen“. Die Erkennung startet sofort; gescannte
   PDF-Seiten werden per Texterkennung gelesen (auch gedrehte Scans).
2. **Prüfen**: eine Karte je Person oder Angabe, Schreibweisen zusammengefasst („Moritz Günther“, „Herr Günther“,
   „Günthers“). Schalter (ersetzen / stehen lassen), Platzhalter anklicken und eigenen Namen vergeben (`[Mandant]` statt
   `[Person_1]`), „gehört zu …“ und „trennen …“ für Zuordnungen, Rückfrage bei mehrdeutigen Nachnamen, „Fehlt etwas?“ zum
   Nachtragen. Rechts das Dokument mit Markierungen oder die anonymisierte Fassung. Unten: „Geprüft, jetzt anonymisieren“.
3. **Fertig**: je Datei eine Kopie im gleichen Format mit Zusatz (`Klage.docx` → `Klage_anonymisiert.docx`, PDF echt
   geschwärzt), bei „Ordner wählen“ neben den Originalen, sonst unter `Dokumente\Lokanon\Anonymisiert`. „Ordner öffnen“.

**Einstellungen** (Zahnrad): Kanzlei (nie ersetzen), Erkennung, Ausgabe (Zusatz, Ablageordner, Textfassung) und
**Erweitert**, alles standardmäßig aus: Rückübersetzung mit verschlüsseltem Schlüssel (dann erscheint oben „Antwort
zurückübersetzen“), KI-Anweisung und Claude-Skill, Vorgangsordner mit Prüfbericht und Protokoll unter
`%USERPROFILE%\Lokanon\Vorgaenge`. Einstellungen: `%USERPROFILE%\Lokanon\einstellungen.yaml` (Vorlage `config.default.yaml`).

Startet Lokanon nicht, steht der Grund in `%USERPROFILE%\Lokanon\lokanon.log` (das Programmfenster zeigt beim Start
eine Wartemeldung; der erste Start nach der Installation kann ein bis zwei Minuten dauern).

Platzhalter sind innerhalb eines Durchlaufs konsistent (auch über mehrere Dateien, Namensteile und Genitiv), zwischen
Durchläufen beginnt die Zählung neu.

## Projektstruktur

```
lokanon.py                      Starter: Server auf 127.0.0.1 + Programmfenster (pywebview/WebView2), --browser Fallback
server/app.py                   HTTP-Schnittstelle (FastAPI), nur lokal
server/dienst.py                Sitzungsdienst: Analyse mit Fortschritt, Identitäten, Anonymisieren, erweiterte Funktionen
server/einstellungen.py         persönliche Einstellungen (einstellungen.yaml), Gruppen-Auffüllung
ui/                             Oberfläche: index.html, app.css (Designsystem), app.js, fonts/ (Source Sans 3, Source Serif 4)
anonymizer/engine.py            Erkennung, Bereinigung, Propagation über Dateien, Pseudonyme, Zuordnungen, Rückübersetzung
anonymizer/ausgabe.py           Ausgabe im gleichen Format mit Zusatz im Dateinamen, Leck-Test
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
