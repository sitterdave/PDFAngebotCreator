/**
 * E-Mail Import: Drag & Drop / Paste für Carport-Anfrage E-Mails
 * Parst den E-Mail-Text und füllt das Angebotsformular automatisch aus.
 */
document.addEventListener('DOMContentLoaded', function() {
    var dropZone = document.getElementById('emailDropZone');
    var resultDiv = document.getElementById('emailParseResult');
    if (!dropZone) return;

    // --- Drag & Drop ---
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.style.borderColor = '#198754';
        dropZone.style.backgroundColor = '#f0fff4';
    });

    dropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        dropZone.style.borderColor = '#0d6efd';
        dropZone.style.backgroundColor = '';
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.style.borderColor = '#0d6efd';
        dropZone.style.backgroundColor = '';

        var text = e.dataTransfer.getData('text/plain') || e.dataTransfer.getData('text');
        if (text) {
            parseAndFill(text);
        }
    });

    // --- Paste (Strg+V) auf der Drop-Zone ---
    dropZone.setAttribute('tabindex', '0');
    dropZone.addEventListener('click', function() {
        dropZone.focus();
    });
    dropZone.addEventListener('paste', function(e) {
        e.preventDefault();
        var text = (e.clipboardData || window.clipboardData).getData('text');
        if (text) {
            parseAndFill(text);
        }
    });

    // --- Auch globaler Paste wenn Drop-Zone sichtbar ---
    document.addEventListener('paste', function(e) {
        var card = document.getElementById('emailImportCard');
        if (!card || card.style.display === 'none') return;
        // Nicht abfangen wenn User in einem Input/Textarea tippt
        var tag = (e.target.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

        e.preventDefault();
        var text = (e.clipboardData || window.clipboardData).getData('text');
        if (text) {
            parseAndFill(text);
        }
    });

    function parseAndFill(text) {
        var data = parseEmail(text);

        if (!data.name) {
            showResult('Konnte keine Kundendaten erkennen. Bitte den E-Mail-Text als Text einfügen.', 'warning');
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
                setVal('customer_country_label', data.country);
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
        var summary = '<strong>' + escapeHtml(data.name) + '</strong>';
        if (data.city) summary += ', ' + escapeHtml(data.city);
        if (data.carportVariante) summary += ' &mdash; ' + escapeHtml(data.carportVariante);

        showResult('Daten importiert: ' + summary, 'success');

        // Drop-Zone minimieren
        dropZone.innerHTML = '<i class="bi bi-check-circle text-success fs-4"></i> <span class="text-success fw-bold">Importiert!</span>'
            + ' <button type="button" class="btn btn-sm btn-outline-secondary ms-2" id="resetImportBtn">Nochmal</button>';

        document.getElementById('resetImportBtn').addEventListener('click', function() {
            dropZone.innerHTML = '<i class="bi bi-envelope-arrow-down fs-1 text-primary"></i>'
                + '<p class="mb-1 mt-2 fw-bold text-primary">Carport-Anfrage E-Mail hier reinziehen oder einfügen</p>'
                + '<p class="text-muted small mb-0">Drag &amp; Drop oder <kbd>Strg+V</kbd> zum Einfügen des E-Mail-Textes</p>';
            resultDiv.style.display = 'none';
        });
    }

    function parseEmail(text) {
        var data = {};
        var lines = text.split(/\r?\n/).map(function(l) { return l.trim(); });

        // Hilfsfunktion: Wert nach einem Label finden
        function findValue(label) {
            for (var i = 0; i < lines.length; i++) {
                if (lines[i].toLowerCase() === label.toLowerCase() ||
                    lines[i].toLowerCase().replace(/[:\-\/]/g, '').trim() === label.toLowerCase().replace(/[:\-\/]/g, '').trim()) {
                    // Nächste nicht-leere Zeile ist der Wert
                    for (var j = i + 1; j < lines.length && j <= i + 3; j++) {
                        if (lines[j] && !isLabel(lines[j])) {
                            return lines[j];
                        }
                    }
                }
            }
            return '';
        }

        // Bekannte Labels (um zu erkennen was ein Label ist und was ein Wert)
        var knownLabels = [
            'neue carport-anfrage', 'kundendaten', 'name', 'e-mail', 'telefon',
            'firma', 'uid-nummer', 'adresse', 'straße/nr.', 'straße/nr', 'plz', 'ort', 'land',
            'konfiguration', 'anzahl stellplätze', 'carport-variante', 'installation',
            'ausgewählte module', 'batteriespeicher', 'weitere informationen',
            'preisübersicht', 'gesamtbetrag', 'hinweis'
        ];

        function isLabel(line) {
            var l = line.toLowerCase().replace(/[:\-\/\.]/g, '').trim();
            return knownLabels.some(function(lab) {
                return l === lab.replace(/[:\-\/\.]/g, '').trim();
            });
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
