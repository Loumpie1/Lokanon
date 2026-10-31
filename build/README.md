# Lokanon-Installer bauen

## Ablauf in fünf Sätzen

1. `build.py` lädt ein eigenständiges CPython 3.13 (python-build-standalone von astral-sh) herunter und entpackt es nach `<work>\app\python`.
2. Mit dessen pip werden alle Pakete aus `requirements.txt` installiert (Torch als CPU-Build von download.pytorch.org, dazu das spaCy-Modell `de_core_news_lg` als Wheel); Streamlit wird bewusst weggelassen.
3. Die GLiNER-Gewichte (`urchade/gliner_multi_pii-v1`) und der zugehörige Tokenizer (`microsoft/mdeberta-v3-base`) werden aus dem Hugging-Face-Cache nach `<work>\app\models\hf\hub` kopiert (fehlen sie, lädt `snapshot_download` sie dorthin); zur Laufzeit zeigt `HF_HOME` auf `<app>\models\hf`, zusammen mit `HF_HUB_OFFLINE=1` und `TRANSFORMERS_OFFLINE=1`.
4. Die Projektdateien (`anonymizer/`, `server/`, `ui/`, `assets/`, `static/`, `docs/`, `ki-anweisung/`, `lokanon.py`, `config.default.yaml`, `README.md`, `LICENSE*`) werden nach `<work>\app` kopiert, dazu `VERSION`, `models\MANIFEST.json` und das Startskript `Lokanon.cmd`; danach werden unnötige Teile entfernt (`torch/test`, `torch/include`, `Lib/test`, `tkinter`, `tcl`, `__pycache__`) und `smoke_test.py` prüft das Bundle offline.
5. Mit `--installer` kompiliert Inno Setup (`ISCC.exe`) das Skript `lokanon.iss` und legt `Lokanon-Setup-<version>.exe` unter `<work>\out` ab.

## Voraussetzungen

- Windows 10/11 x64, Internetzugang nur zum Bauen (Python-Archiv, Pakete, spaCy-Wheel).
- Entwicklungs-venv `C:\Users\david\Lokanon\venv` (Python 3.13); daraus läuft `build.py`.
- Hugging-Face-Cache unter `%USERPROFILE%\.cache\huggingface\hub` mit den beiden Modellen (sonst Download beim Bauen).
- Inno Setup 6, als Benutzer installiert: `winget install --id JRSoftware.InnoSetup -e --accept-source-agreements --accept-package-agreements` (liegt dann unter `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`).
- Etwa 6 GB freier Platz: Bundle 2,77 GB, Installer 1,43 GB, Downloads ca. 0,7 GB.
- Kein Code-Signaturzertifikat vorhanden: Windows SmartScreen warnt beim ersten Start des Installers; die Hinweisseite im Setup erklärt das.

## Bauen

Aus dem Projektordner:

```bash
C:\Users\david\Lokanon\venv\Scripts\python.exe build\build.py --installer
```

Optionen:

- `--version 1.0.0` – Versionsnummer (Standard: Inhalt von `build\VERSION`).
- `--work <Ordner>` – Arbeitsverzeichnis, Standard `%USERPROFILE%\Lokanon\build` (außerhalb von OneDrive; `build/` im Projekt enthält nur Skripte).
- `--nur-schritt python|pakete|modelle|projekt|pruefen` – einen Schritt wiederholen, z. B. `--nur-schritt projekt` nach Änderungen am Code, dann `--installer`.
- Ohne `--installer` entsteht nur das Bundle `<work>\app`; es lässt sich dort direkt per `Lokanon.cmd` starten.

Rauchtest allein: `python build\smoke_test.py C:\Users\david\Lokanon\build\app` (Exit 0 = bestanden).

## Was der Installer tut

- `PrivilegesRequired=lowest`, Ziel `%LOCALAPPDATA%\Programs\Lokanon`, keine Adminrechte.
- Startmenü-Verknüpfung (optional Desktop) auf `python\pythonw.exe "…\lokanon.py"`, Arbeitsverzeichnis `{app}`, Icon `assets\lokanon.ico`.
- Hinweisseite vor der Installation: Größe, Offline-Betrieb, SmartScreen-Warnung.
- Deinstaller entfernt nur den Programmordner; `%USERPROFILE%\Lokanon` (Vorgänge, Schlüssel, Einstellungen) bleibt erhalten.
- Kompression `lzma2/normal` + `SolidCompression` (Kompilieren ca. 5 Minuten, Installer 1,43 GB); `ultra64` lohnt sich nicht, weil die Modellgewichte kaum komprimierbar sind und die Build-Zeit vervielfacht würde.

## Ergebnisse

- Bundle: `C:\Users\david\Lokanon\build\app`
- Installer: `C:\Users\david\Lokanon\build\out\Lokanon-Setup-<version>.exe`
- Modellliste: `<app>\models\MANIFEST.json`

Nach Änderungen an der Oberfläche oder am Code den Build wiederholen: `python build\build.py --nur-schritt projekt --installer` (Python, Pakete und Modelle bleiben erhalten und werden nicht neu geladen).

Pilot-Paket (Ordner `%USERPROFILE%\Lokanon\Pilot` und `build\out\Lokanon-Pilot-Paket-<version>.zip`, ohne Installer):
`python build\pilot_paket.py` – nimmt den Installer aus `build\out`, übersetzt die Markdown-Unterlagen aus `docs/` nach Word
und legt die Anleitung offline ab.

## Stand 31.10.2026

Lokanon 0.2.0: Build mit `--nur-schritt projekt --installer` wiederholt, Pilot-Paket per `pilot_paket.py`.

## Stand 28.10.2026

Build durchgelaufen mit CPython 3.13.18 (python-build-standalone 20261026), Torch 2.15.0+cpu, spaCy 3.8.18 /
de_core_news_lg 3.8.0, GLiNER 0.2.29, Rauchtest offline bestanden (PERSON, LOCATION, IBAN_CODE erkannt, fastapi /
uvicorn / webview importierbar). Bundle 2,77 GB (GLiNER 1,1 GB, spaCy-Modell 0,6 GB, Torch 0,38 GB, OpenCV 0,11 GB),
Installer `Lokanon-Setup-0.1.0.exe` 1,43 GB. Bekannte Abweichungen: pip lädt das spaCy-Wheel von GitHub-Releases als
leere Datei, daher lädt `build.py` es selbst herunter; Streamlit ist nicht im Bundle; der Installer ist unsigniert.
Nach Fertigstellung der Oberfläche den Build wiederholen: `python build\build.py --installer`.
