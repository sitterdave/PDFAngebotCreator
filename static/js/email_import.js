/**
 * E-Mail Import für Carport-Anfrage E-Mails
 * - Drag & Drop: .eml Datei aus Outlook auf die Seite ziehen -> Server parst die Datei
 * - Textarea + Button: Text einfügen und "Importieren" klicken -> Client parst den Text
 * Füllt das Angebotsformular automatisch aus und speichert die Anfrage in den internen Notizen.
 */
document.addEventListener('DOMContentLoaded', function() {
    var textArea = document.getElementById('emailTextArea');
    var importBtn = document.getElementById('emailImportBtn');
    var clearBtn = document.getElementById('emailClearBtn');
    var resultDiv = document.getElementById('emailParseResult');
    var toggleBtn = document.getElementById('toggleImportBtn');
    var importBody = document.getElementById('emailImportBody');
    var dropOverlay = document.getElementById('dropOverlay');
    if (!textArea || !importBtn) return;

    // === Toggle ein-/ausklappen ===
    if (toggleBtn && importBody) {
        toggleBtn.addEventListener('click', function() {
            var hidden = importBody.style.display === 'none';
            importBody.style.display = hidden ? '' : 'none';
            toggleBtn.querySelector('i').className = hidden ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
        });
    }

    // === Textarea Import-Button ===
    importBtn.addEventListener('click', function() {
        var text = textArea.value.trim();
        if (!text) {
            showResult('Bitte zuerst den E-Mail-Text in das Feld einfügen.', 'warning');
            return;
        }
        var data = parseEmailText(text);
        fillForm(data, text);
    });

    // === Leeren-Button ===
    clearBtn.addEventListener('click', function() {
        textArea.value = '';
        resultDiv.style.display = 'none';
    });

    // === Drag & Drop auf die ganze Seite ===
    var dragCounter = 0;

    document.addEventListener('dragenter', function(e) {
        e.preventDefault();
        dragCounter++;
        if (dropOverlay) dropOverlay.style.display = '';
    });

    document.addEventListener('dragleave', function(e) {
        e.preventDefault();
        dragCounter--;
        if (dragCounter <= 0) {
            dragCounter = 0;
            if (dropOverlay) dropOverlay.style.display = 'none';
        }
    });

    document.addEventListener('dragover', function(e) {
        e.preventDefault();
    });

    document.addEventListener('drop', function(e) {
        e.preventDefault();
        dragCounter = 0;
        if (dropOverlay) dropOverlay.style.display = 'none';

        // Prüfen ob Dateien gedroppt wurden (.eml)
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            var file = e.dataTransfer.files[0];
            // .eml oder .msg Datei -> an Server senden
            if (file.name.endsWith('.eml') || file.name.endsWith('.msg') || file.type === 'message/rfc822') {
                uploadEmlFile(file);
                return;
            }
            // Vielleicht eine Textdatei?
            if (file.type && file.type.startsWith('text/')) {
                var reader = new FileReader();
                reader.onload = function(ev) {
                    var text = ev.target.result;
                    textArea.value = text;
                    var data = parseEmailText(text);
                    fillForm(data, text);
                };
                reader.readAsText(file);
                return;
            }
        }

        // Fallback: Plain-text aus Drag
        var text = e.dataTransfer.getData('text/plain') || e.dataTransfer.getData('text');
        if (text) {
            textArea.value = text;
            var data = parseEmailText(text);
            fillForm(data, text);
            return;
        }

        // HTML-Text aus Drag (z.B. aus Outlook Web)
        var html = e.dataTransfer.getData('text/html');
        if (html) {
            var tmp = document.createElement('div');
            tmp.innerHTML = html;
            var plainText = tmp.textContent || tmp.innerText || '';
            if (plainText.trim()) {
                textArea.value = plainText;
                var data = parseEmailText(plainText);
                fillForm(data, plainText);
                return;
            }
        }

        showResult('Konnte die Datei nicht lesen. Bitte den Text manuell einfügen.', 'warning');
    });

    // === .eml an Server senden ===
    function uploadEmlFile(file) {
        showResult('<i class="bi bi-hourglass-split me-1"></i> E-Mail wird verarbeitet...', 'info');

        var formData = new FormData();
        formData.append('file', file);

        fetch('/api/parse-email', {
            method: 'POST',
            body: formData
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) {
                showResult('Fehler: ' + escapeHtml(data.error), 'danger');
                return;
            }
            var rawText = data.raw_text || '';
            fillForm(data, rawText);
        })
        .catch(function() {
            showResult('Fehler beim Verarbeiten der E-Mail-Datei.', 'danger');
        });
    }

    // === Formular ausfüllen ===
    function fillForm(data, rawText) {
        if (!data.name) {
            showResult('Konnte keine Kundendaten erkennen. Ist der E-Mail-Text vollständig?', 'warning');
            return;
        }

        // Felder ausfüllen
        setVal('customer_name', data.name);
        setVal('customer_email', data.email);
        setVal('customer_phone', data.phone);
        setVal('customer_company', data.company);
        setVal('customer_uid', data.uid);
        setVal('customer_street', data.street);
        setVal('customer_zip', data.zip);
        setVal('customer_city', data.city);

        // Land-Mapping
        if (data.country) {
            var countryLower = data.country.toLowerCase();
            var countrySelect = document.querySelector('[name="country"]');
            if (countryLower.indexOf('deutsch') >= 0 || countryLower === 'germany' || countryLower === 'de') {
                if (countrySelect) countrySelect.value = 'DE';
                setVal('customer_country_label', 'Deutschland');
            } else {
                if (countrySelect) countrySelect.value = 'AT';
                var label = data.country;
                if (countryLower === 'austria') label = 'Österreich';
                setVal('customer_country_label', label);
            }
            if (countrySelect) countrySelect.dispatchEvent(new Event('change'));
        }

        // Interne Notizen: Zusammenfassung + komplette Anfrage
        var notes = [];
        if (data.stellplaetze || data.carport_variante || data.carportVariante) {
            notes.push('=== ANFRAGE-DETAILS ===');
            if (data.stellplaetze) notes.push('Stellplätze: ' + data.stellplaetze);
            if (data.carport_variante || data.carportVariante) notes.push('Carport-Variante: ' + (data.carport_variante || data.carportVariante));
            if (data.installation) notes.push('Installation: ' + data.installation);
            if (data.module) notes.push('Module: ' + data.module);
            if (data.batterie) notes.push('Batterie: ' + data.batterie);
            if (data.weitere_infos || data.weitereInfos) notes.push('Weitere Infos: ' + (data.weitere_infos || data.weitereInfos));
            if (data.gesamtbetrag) notes.push('Gesamtbetrag (Anfrage): ' + data.gesamtbetrag);
        }
        notes.push('');
        notes.push('=== ORIGINAL-ANFRAGE ===');
        notes.push(rawText.trim());

        var notesField = document.querySelector('[name="notes"]');
        if (notesField) {
            notesField.value = notes.join('\n');
        }

        // Erfolgs-Anzeige
        var parts = ['<strong>' + escapeHtml(data.name) + '</strong>'];
        if (data.city) parts.push(escapeHtml(data.city));
        var variante = data.carport_variante || data.carportVariante || '';
        if (variante) parts.push(escapeHtml(variante));

        showResult('<i class="bi bi-check-circle me-1"></i> Daten importiert: ' + parts.join(' &mdash; '), 'success');

        // Textarea zuklappen nach Erfolg
        textArea.style.display = 'none';
        importBtn.style.display = 'none';
        var helpText = importBody.querySelector('p.text-muted');
        if (helpText) helpText.style.display = 'none';
        clearBtn.innerHTML = '<i class="bi bi-arrow-counterclockwise"></i> Nochmal importieren';
        clearBtn.className = 'btn btn-outline-primary btn-sm';
        clearBtn.onclick = function() {
            textArea.style.display = '';
            textArea.value = '';
            importBtn.style.display = '';
            if (helpText) helpText.style.display = '';
            clearBtn.innerHTML = '<i class="bi bi-x-lg"></i> Leeren';
            clearBtn.className = 'btn btn-outline-secondary btn-sm';
            resultDiv.style.display = 'none';
            clearBtn.onclick = function() {
                textArea.value = '';
                resultDiv.style.display = 'none';
            };
        };
    }

    // === Client-seitiger E-Mail-Parser (für Textarea-Text) ===
    function parseEmailText(text) {
        var lines = text.split(/\r?\n/).map(function(l) { return l.trim(); });

        var knownLabels = [
            'neue carport-anfrage', 'kundendaten', 'name', 'e-mail', 'telefon',
            'firma', 'uid-nummer', 'adresse', 'straße/nr.', 'straße/nr', 'plz', 'ort', 'land',
            'konfiguration', 'anzahl stellplätze', 'carport-variante', 'installation',
            'ausgewählte module', 'batteriespeicher', 'weitere informationen',
            'preisübersicht', 'gesamtbetrag', 'hinweis'
        ];

        function normalize(s) {
            return s.toLowerCase().replace(/[:\-\/\.]/g, '').replace(/\s+/g, ' ').trim();
        }

        var normLabels = knownLabels.map(normalize);

        function isLabel(line) {
            return normLabels.indexOf(normalize(line)) >= 0;
        }

        function findValue(label) {
            var target = normalize(label);
            for (var i = 0; i < lines.length; i++) {
                if (normalize(lines[i]) === target) {
                    for (var j = i + 1; j < lines.length && j <= i + 3; j++) {
                        if (lines[j] && !isLabel(lines[j])) {
                            return lines[j];
                        }
                    }
                }
            }
            return '';
        }

        return {
            name: findValue('Name'),
            email: findValue('E-Mail'),
            phone: findValue('Telefon'),
            company: findValue('Firma'),
            uid: findValue('UID-Nummer'),
            street: findValue('Straße/Nr.') || findValue('Straße/Nr'),
            zip: findValue('PLZ'),
            city: findValue('Ort'),
            country: findValue('Land'),
            stellplaetze: findValue('Anzahl Stellplätze'),
            carportVariante: findValue('Carport-Variante'),
            installation: findValue('Installation'),
            module: findValue('Ausgewählte Module'),
            batterie: findValue('Batteriespeicher'),
            weitereInfos: findValue('Weitere Informationen'),
            gesamtbetrag: findValue('Gesamtbetrag')
        };
    }

    // === Hilfsfunktionen ===
    function setVal(name, value) {
        if (!value) return;
        var el = document.querySelector('[name="' + name + '"]');
        if (el) el.value = value;
    }

    function showResult(html, type) {
        resultDiv.innerHTML = '<div class="alert alert-' + type + ' mb-0 py-2">' + html + '</div>';
        resultDiv.style.display = '';
    }

    function escapeHtml(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
});
