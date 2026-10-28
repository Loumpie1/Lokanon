@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Entwicklungsstart: Programmfenster über das venv (Installer-Version startet lokanon.py direkt)
call "%USERPROFILE%\Lokanon\venv\Scripts\activate.bat"
start "" pythonw lokanon.py
