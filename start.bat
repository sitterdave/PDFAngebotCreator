@echo off
title Angebot Creator
echo ========================================
echo   Angebot PDF Creator - Starte...
echo ========================================
echo.

cd /d "%~dp0"

:: Prüfen ob Python installiert ist
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo FEHLER: Python wurde nicht gefunden!
    echo.
    echo Bitte installiere Python von https://www.python.org/downloads/
    echo WICHTIG: Bei der Installation "Add Python to PATH" ankreuzen!
    echo.
    pause
    exit /b 1
)

:: Python-Umgebung prüfen/erstellen
if not exist "venv" (
    echo [1/3] Erstelle Python-Umgebung...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo FEHLER: Python-Umgebung konnte nicht erstellt werden!
        echo.
        pause
        exit /b 1
    )
)

:: Aktivieren
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo.
    echo FEHLER: Python-Umgebung konnte nicht aktiviert werden!
    echo Versuche den venv Ordner zu löschen und starte erneut.
    echo.
    pause
    exit /b 1
)

:: Abhängigkeiten prüfen - alle Pakete importierbar?
python -c "import flask; import olefile" >nul 2>&1
if errorlevel 1 (
    echo [2/3] Installiere Abhängigkeiten...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo FEHLER: Abhängigkeiten konnten nicht installiert werden!
        echo Bitte prüfe deine Internetverbindung.
        echo.
        pause
        exit /b 1
    )
) else (
    echo [2/3] Abhängigkeiten bereits installiert.
)

echo [3/3] Starte Angebot Creator...
echo.
echo ========================================
echo   App läuft auf: http://localhost:5000
echo   Browser öffnet sich automatisch.
echo   Zum Beenden: Strg+C oder Fenster schließen
echo ========================================
echo.

:: Browser nach 2 Sekunden öffnen
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

:: App starten
python app.py

:: Falls die App unerwartet beendet wird, Fenster offen halten
echo.
echo ========================================
echo   Die App wurde beendet.
echo   Falls ein Fehler aufgetreten ist,
echo   steht die Meldung oben.
echo ========================================
echo.
pause
