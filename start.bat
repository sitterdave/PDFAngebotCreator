@echo off
title Angebot Creator
echo ========================================
echo   Angebot PDF Creator - Starte...
echo ========================================
echo.

cd /d "%~dp0"

:: Python-Umgebung pruefen/erstellen
if not exist "venv" (
    echo [1/3] Erstelle Python-Umgebung...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo FEHLER: Python nicht gefunden!
        echo Bitte installiere Python von https://www.python.org/downloads/
        echo Wichtig: Bei der Installation "Add Python to PATH" ankreuzen!
        pause
        exit /b 1
    )
)

:: Aktivieren
call venv\Scripts\activate.bat

:: Abhaengigkeiten installieren
if not exist "venv\.installed" (
    echo [2/3] Installiere Abhaengigkeiten...
    pip install -r requirements.txt --quiet
    echo done > venv\.installed
)

echo [3/3] Starte Angebot Creator...
echo.
echo ========================================
echo   App laeuft auf: http://localhost:5000
echo   Browser oeffnet sich automatisch.
echo   Zum Beenden: Strg+C oder Fenster schliessen
echo ========================================
echo.

:: Browser nach 2 Sekunden oeffnen
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

:: App starten
python app.py
