/**
 * E-Mail Import: Textarea + Button für Carport-Anfrage E-Mails
 * Parst den E-Mail-Text und füllt das Angebotsformular automatisch aus.
 */
document.addEventListener('DOMContentLoaded', function() {
    var textArea = document.getElementById('emailTextArea');
    var importBtn = document.getElementById('emailImportBtn');
    var clearBtn = document.getElementById('emailClearBtn');
    var resultDiv = document.getElementById('emailParseResult');
    var toggleBtn = document.getElementById('toggleImportBtn');
    var importBody = document.getElementById('emailImportBody');
    if (!textArea || !importBtn) return;

    // Toggle ein-/ausklappen
    if (toggleBtn && importBody) {
        toggleBtn.addEventListener('click', function() {
            var hidden = importBody.style.display === 'none';
            importBody.style.display = hidden ? '' : 'none';
            toggleBtn.querySelector('i').className = hidden ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
        });
    }

    // Import-Button
    importBtn.addEventListener('click', function() {
        var text = textArea.value.trim();
        if (!text) {
            showResult('Bitte zuerst den E-Mail-Text in das Feld einfügen.', 'warning');
            return;
        }
        parseAndFill(text);
    });

    // Leeren-Button
    clearBtn.addEventListener('click', function() {
        textArea.value = '';
        resultDiv.style.display = 'none';
    });

    function parseAndFill(text) {
        var data = parseEmail(text);

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
                // Austria -> Österreich
                var label = data.country;
                if (countryLower === 'austria') label = 'Österreich';
                setVal('customer_country_label', label);
            }
            // Trigger change für MwSt-Update
            if (countrySelect) countrySelect.dispatchEvent(new Event('change'));
        }

        // Notizen zusammenstellen
        var notes = [];
        if (data.stellplaetze) notes.push('Stellplätze: ' + data.stellplaetze);
        if (data.carportVariante) notes.push('Carport-Variante: ' + data.carportVariante);
        if (data.installation) notes.push('Installation: ' + data.installation);
        if (data.module) notes.push('Module: ' + data.module);
        if (data.batterie) notes.push('Batterie: ' + data.batterie);
        if (data.weitereInfos) notes.push('Weitere Infos: ' + data.weitereInfos);
        if (data.gesamtbetrag) notes.push('Gesamtbetrag (Anfrage): ' + data.gesamtbetrag);

        var notesField = document.querySelector('[name="notes"]');
        if (notesField && notes.length) {
            notesField.value = notes.join('\n');
        }

        // Erfolgs-Anzeige
        var parts = ['<strong>' + escapeHtml(data.name) + '</strong>'];
        if (data.city) parts.push(escapeHtml(data.city));
        if (data.carportVariante) parts.push(escapeHtml(data.carportVariante));

        showResult('<i class="bi bi-check-circle me-1"></i> Daten importiert: ' + parts.join(' &mdash; '), 'success');

        // Textarea zuklappen
        textArea.style.display = 'none';
        importBtn.style.display = 'none';
        clearBtn.textContent = 'Nochmal importieren';
        clearBtn.className = 'btn btn-outline-primary btn-sm';
        clearBtn.onclick = function() {
            textArea.style.display = '';
            textArea.value = '';
            importBtn.style.display = '';
            clearBtn.textContent = 'Leeren';
            clearBtn.className = 'btn btn-outline-secondary btn-sm';
            resultDiv.style.display = 'none';
            clearBtn.onclick = function() {
                textArea.value = '';
                resultDiv.style.display = 'none';
            };
        };
    }

    function parseEmail(text) {
        var data = {};
        var lines = text.split(/\r?\n/).map(function(l) { return l.trim(); });

        // Bekannte Labels
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

        function isLabel(line) {
            var n = normalize(line);
            return knownLabels.some(function(lab) {
                return n === normalize(lab);
            });
        }

        // Wert nach einem Label finden
        function findValue(label) {
            var normLabel = normalize(label);
            for (var i = 0; i < lines.length; i++) {
                if (normalize(lines[i]) === normLabel) {
                    // Nächste nicht-leere, nicht-Label Zeile ist der Wert
                    for (var j = i + 1; j < lines.length && j <= i + 3; j++) {
                        if (lines[j] && !isLabel(lines[j])) {
                            return lines[j];
                        }
                    }
                }
            }
            return '';
        }

        data.name = findValue('Name');
        data.email = findValue('E-Mail');
        data.phone = findValue('Telefon');
        data.company = findValue('Firma');
        data.uid = findValue('UID-Nummer');
        data.street = findValue('Straße/Nr.');
        if (!data.street) data.street = findValue('Straße/Nr');
        data.zip = findValue('PLZ');
        data.city = findValue('Ort');
        data.country = findValue('Land');
        data.stellplaetze = findValue('Anzahl Stellplätze');
        data.carportVariante = findValue('Carport-Variante');
        data.installation = findValue('Installation');
        data.module = findValue('Ausgewählte Module');
        data.batterie = findValue('Batteriespeicher');
        data.weitereInfos = findValue('Weitere Informationen');
        data.gesamtbetrag = findValue('Gesamtbetrag');

        return data;
    }

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
