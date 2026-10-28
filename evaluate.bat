@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "%USERPROFILE%\Lokanon\venv\Scripts\activate.bat"
python evaluate.py --config testdaten\kanzlei\config_eval.yaml testdaten\kanzlei\referenz_markierungen.jsonl
pause
