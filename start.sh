#!/bin/bash
echo "========================================"
echo "  Angebot PDF Creator - Starte..."
echo "========================================"
echo

cd "$(dirname "$0")"

# Python prüfen
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "FEHLER: Python3 nicht gefunden!"
    echo "Installiere Python: brew install python3 (Mac) oder sudo apt install python3 (Linux)"
    read -p "Drücke Enter zum Beenden..."
    exit 1
fi

# Python-Umgebung prüfen/erstellen
if [ ! -d "venv" ]; then
    echo "[1/3] Erstelle Python-Umgebung..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo ""
        echo "FEHLER: Python-Umgebung konnte nicht erstellt werden!"
        read -p "Drücke Enter zum Beenden..."
        exit 1
    fi
fi

# Aktivieren
source venv/bin/activate

# Abhängigkeiten installieren
if [ ! -f "venv/.installed" ]; then
    echo "[2/3] Installiere Abhängigkeiten..."
    pip install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then
        echo ""
        echo "FEHLER: Abhängigkeiten konnten nicht installiert werden!"
        echo "Bitte prüfe deine Internetverbindung."
        read -p "Drücke Enter zum Beenden..."
        exit 1
    fi
    touch venv/.installed
fi

echo "[3/3] Starte Angebot Creator..."
echo ""
echo "========================================"
echo "  App läuft auf: http://localhost:5000"
echo "  Browser öffnet sich automatisch."
echo "  Zum Beenden: Strg+C"
echo "========================================"
echo

# Browser öffnen (nach 2 Sekunden)
(sleep 2 && open http://localhost:5000 2>/dev/null || xdg-open http://localhost:5000 2>/dev/null) &

# App starten
python app.py

# Falls die App beendet wird
echo ""
echo "Die App wurde beendet."
read -p "Drücke Enter zum Beenden..."
