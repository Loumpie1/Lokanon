@echo off
chcp 65001 >nul
echo === Lokanon: Einrichtung ===
rem Python-Umgebung bewusst AUSSERHALB von OneDrive (tausende Dateien, Sync-Sperren)
rem py -3.13 statt py -3: "py -3" kann die Free-Threaded-Variante (3.13t) waehlen, fuer die es keine spaCy-Pakete gibt
set VENV=%USERPROFILE%\Lokanon\venv
where py >nul 2>nul || (echo Python fehlt. Bitte Python 3.13 von python.org installieren. & pause & exit /b 1)
py -3.13 -m venv "%VENV%" || (echo venv konnte nicht erstellt werden. & pause & exit /b 1)
call "%VENV%\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
rem Sprachmodell (ca. 570 MB) nur laden, wenn es noch fehlt
python -c "import de_core_news_lg" >nul 2>nul
if errorlevel 1 (
    python -m spacy download de_core_news_lg || (echo Modell-Download fehlgeschlagen. Bitte setup.bat erneut starten. & pause & exit /b 1)
) else (
    echo Sprachmodell de_core_news_lg bereits vorhanden.
)
rem OCR-Modelle liegen im Paket rapidocr (kein Download); einmal aufwaermen, damit alles da ist
python -c "from rapidocr import RapidOCR; RapidOCR(); print('OCR bereit.')" || (echo OCR-Pruefung fehlgeschlagen - Scans werden nicht gelesen. & pause)
rem Zweites Erkennungsmodell GLiNER (ca. 1,1 GB, einmalig; danach offline aus dem Cache)
echo Lade GLiNER-Modell (falls noch nicht vorhanden) ...
python -c "from gliner import GLiNER; GLiNER.from_pretrained('urchade/gliner_multi_pii-v1', map_location='cpu'); print('GLiNER-Modell bereit.')" || (echo GLiNER-Download fehlgeschlagen. Lokanon laeuft auch ohne: in config.yaml gliner_model leer lassen. & pause)
echo.
echo Fertig. Starten mit start.bat
pause
