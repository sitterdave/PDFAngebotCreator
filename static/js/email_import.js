/**
 * E-Mail Import für Carport-Anfrage E-Mails
 * - Drag & Drop: .msg/.eml Datei oder Text auf die Seite ziehen
 * - Textarea + Button: Text einfügen und "Importieren" klicken
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

        // Dateien gedroppt -> immer an Server senden (egal welcher Typ)
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            var file = e.dataTransfer.files[0];
            uploadFile(file);
            return;
        }

        // Plain-text aus Drag
        var text = e.dataTransfer.getData('text/plain') || e.dataTransfer.getData('text');
        if (text && text.trim()) {
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

    // === Datei an Server senden ===
    function uploadFile(file) {
        showResult('<i class="bi bi-hourglass-split me-1"></i> E-Mail wird verarbeitet (' + escapeHtml(file.name) + ')...', 'info');

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
            // Zeige den erkannten Text in der Textarea
            if (rawText) textArea.value = rawText;
            fillForm(data, rawText);
        })
        .catch(function(err) {
            showResult('Fehler beim Verarbeiten: ' + escapeHtml(String(err)), 'danger');
        });
    }

    // === Formular ausfüllen ===
    function fillForm(data, rawText) {
        if (!data.name) {
            // Zeige was erkannt wurde, damit der User debuggen kann
            var debugInfo = rawText ? '<br><small class="text-muted">Erkannter Text (erste 500 Zeichen):<br><code>'
                + escapeHtml(rawText.substring(0, 500)) + '</code></small>' : '';
            showResult('Konnte keine Kundendaten erkennen. Ist der E-Mail-Text vollständig?' + debugInfo, 'warning');
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
        var variante = data.carport_variante || data.carportVariante || '';
        if (data.stellplaetze || variante) {
            notes.push('=== ANFRAGE-DETAILS ===');
            if (data.stellplaetze) notes.push('Stellplätze: ' + data.stellplaetze);
            if (variante) notes.push('Carport-Variante: ' + variante);
            if (data.installation) notes.push('Installation: ' + data.installation);
            if (data.module) notes.push('Module: ' + data.module);
            if (data.batterie) notes.push('Batterie: ' + data.batterie);
            var infos = data.weitere_infos || data.weitereInfos || '';
            if (infos) notes.push('Weitere Infos: ' + infos);
            if (data.gesamtbetrag) notes.push('Gesamtbetrag (Anfrage): ' + data.gesamtbetrag);
        }
        notes.push('');
        notes.push('=== ORIGINAL-ANFRAGE ===');
        notes.push(rawText.trim());

        var notesField = document.querySelector('[name="notes"]');
        if (notesField) {
            notesField.value = notes.join('\n');
        }

        // === Automatisch Positionen hinzufügen ===
        if (variante && window.addItemRow) {
            addPositionsFromEmail(data, variante);
        }

        // Erfolgs-Anzeige
        var parts = ['<strong>' + escapeHtml(data.name) + '</strong>'];
        if (data.city) parts.push(escapeHtml(data.city));
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

    // === Client-seitiger E-Mail-Parser ===
    function parseEmailText(text) {
        // Zuerst versuchen: Label und Wert auf separaten Zeilen
        var lines = text.split(/\r?\n/).map(function(l) { return l.trim(); });

        var knownLabels = [
            'neue carport-anfrage', 'neue de carport-anfrage', 'kundendaten',
            'name', 'e-mail', 'telefon', 'firma', 'uid-nummer',
            'adresse', 'straße/nr.', 'straße/nr', 'plz', 'ort', 'land',
            'konfiguration', 'anzahl stellplätze', 'carport-variante',
            'installation', 'ausgewählte module', 'batteriespeicher',
            'weitere informationen', 'preisübersicht', 'gesamtbetrag', 'hinweis'
        ];

        function normalize(s) {
            return s.toLowerCase().replace(/[:\-\/\.]/g, '').replace(/\s+/g, ' ').trim();
        }

        var normLabels = knownLabels.map(normalize);

        function isLabel(line) {
            return normLabels.indexOf(normalize(line)) >= 0;
        }

        // Methode 1: Label auf eigener Zeile, Wert auf nächster Zeile
        function findValueNextLine(label) {
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

        // Methode 2: "Label: Wert" oder "Label\tWert" auf gleicher Zeile
        function findValueSameLine(label) {
            var lowerLabel = label.toLowerCase();
            for (var i = 0; i < lines.length; i++) {
                var line = lines[i];
                var lowerLine = line.toLowerCase();
                // "Name: Siegfried Huber" oder "Name\tSiegfried Huber"
                if (lowerLine.indexOf(lowerLabel) === 0) {
                    var rest = line.substring(lowerLabel.length).replace(/^[\s:;\-\t]+/, '').trim();
                    if (rest) return rest;
                }
                // "Name Siegfried Huber" (Label gefolgt von Wert mit Leerzeichen)
                var labelWithSpace = lowerLabel + ' ';
                if (lowerLine.indexOf(labelWithSpace) === 0) {
                    var rest2 = line.substring(labelWithSpace.length).trim();
                    if (rest2) return rest2;
                }
            }
            return '';
        }

        // Kombiniert: erst nächste Zeile versuchen, dann gleiche Zeile
        function findValue(label) {
            return findValueNextLine(label) || findValueSameLine(label);
        }

        return {
            name: findValue('Name'),
            email: findValue('E-Mail') || findValue('E-Mail-Adresse') || findValue('Email'),
            phone: findValue('Telefon') || findValue('Telefonnummer') || findValue('Tel'),
            company: findValue('Firma') || findValue('Unternehmen'),
            uid: findValue('UID-Nummer') || findValue('UID'),
            street: findValue('Straße/Nr.') || findValue('Straße/Nr') || findValue('Straße'),
            zip: findValue('PLZ') || findValue('Postleitzahl'),
            city: findValue('Ort') || findValue('Stadt'),
            country: findValue('Land'),
            stellplaetze: findValue('Anzahl Stellplätze') || findValue('Stellplätze'),
            carportVariante: findValue('Carport-Variante') || findValue('Carport Variante') || findValue('Variante'),
            installation: findValue('Installation'),
            module: findValue('Ausgewählte Module') || findValue('Module'),
            batterie: findValue('Batteriespeicher') || findValue('Batterie'),
            weitereInfos: findValue('Weitere Informationen') || findValue('Weitere Infos') || findValue('Anmerkungen'),
            gesamtbetrag: findValue('Gesamtbetrag') || findValue('Gesamtpreis')
        };
    }

    // === Automatisch Positionen aus E-Mail-Daten hinzufügen ===
    function addPositionsFromEmail(data, variante) {
        // Stellplätze ermitteln (1, 2, oder 3)
        var stellplaetze = data.stellplaetze || data.carport_stellplaetze || '';
        var slotCount = '2'; // Default
        if (/1\s*Stellpl/i.test(stellplaetze)) slotCount = '1';
        else if (/3/i.test(stellplaetze)) slotCount = '3';
        else if (/2/i.test(stellplaetze)) slotCount = '2';

        // Stellplatz-Auswahl im Modal setzen (für spätere manuelle Nacharbeit)
        var slotInput = document.getElementById('slotCount');
        if (slotInput) slotInput.value = slotCount;

        // Modell-Nummer aus Variante extrahieren (z.B. "Modell 05", "Modell S", "Modell S2")
        var modellMatch = variante.match(/Modell\s+(\S+)/i);
        var modellNr = modellMatch ? modellMatch[1] : '';

        // Installation aus E-Mail
        var installation = data.installation || data.carport_installation || '';

        // Module aus E-Mail
        var module = data.module || '';

        // Batterie aus E-Mail
        var batterie = data.batterie || '';

        // Produkt-Templates laden und matchen
        fetch('/api/products')
            .then(function(r) { return r.json(); })
            .then(function(templates) {
                var added = [];

                // 1. Carport-Modell finden
                if (modellNr) {
                    var carport = findProduct(templates, 'Carport', modellNr);
                    if (carport) {
                        var price = getPrice(carport, slotCount);
                        var title = getTitle(carport, slotCount);
                        var desc = getDesc(carport, slotCount);
                        var qty = getQty(carport, slotCount);
                        // Stellplatz-Info an Titel anhängen
                        var slotLabel = slotCount === '1' ? '1 Stellplatz' : slotCount + ' Stellplätze';
                        if (!/Stellpl/i.test(title)) {
                            title += ' \u2013 ' + slotLabel;
                        }
                        window.addItemRow({
                            title: title,
                            description: desc,
                            quantity: qty,
                            price: price,
                            is_carport: true
                        });
                        added.push(title);
                    }
                }

                // 2. Installation (Carport Installation + PV Installation)
                if (installation) {
                    // Carport Installation
                    var carportInstall = findProduct(templates, 'Installation', 'Carport Installation');
                    if (carportInstall) {
                        window.addItemRow({
                            title: getTitle(carportInstall, slotCount),
                            description: getDesc(carportInstall, slotCount),
                            quantity: getQty(carportInstall, slotCount),
                            price: getPrice(carportInstall, slotCount),
                            is_carport: true
                        });
                        added.push('Carport Installation');
                    }

                    // PV-Installation wenn explizit erwähnt
                    if (/PV|Anlage/i.test(installation)) {
                        var pvInstall = findProduct(templates, 'Installation', 'Installation der PV');
                        if (pvInstall) {
                            window.addItemRow({
                                title: getTitle(pvInstall, slotCount),
                                description: getDesc(pvInstall, slotCount),
                                quantity: getQty(pvInstall, slotCount),
                                price: getPrice(pvInstall, slotCount),
                                is_carport: false
                            });
                            added.push('PV Installation');
                        }
                    }
                }

                // 3. PV-Module (können "PV-Module", "Ja Solar", "Solarmodule" etc. heißen)
                if (module && /PV.?Modul|Modul/i.test(module)) {
                    var pvMod = findProduct(templates, 'Komponenten', 'PV-Module')
                        || findProduct(templates, 'Komponenten', 'Solar')
                        || findProduct(templates, 'Komponenten', 'Modul');
                    if (pvMod) {
                        window.addItemRow({
                            title: getTitle(pvMod, slotCount),
                            description: getDesc(pvMod, slotCount),
                            quantity: getQty(pvMod, slotCount),
                            price: getPrice(pvMod, slotCount),
                            is_carport: false
                        });
                        added.push('PV-Module');
                    }
                }

                // 4. Wechselrichter
                if (module && /Wechselrichter/i.test(module)) {
                    var wr = findProduct(templates, 'Komponenten', 'Wechselrichter');
                    if (wr) {
                        window.addItemRow({
                            title: getTitle(wr, slotCount),
                            description: getDesc(wr, slotCount),
                            quantity: getQty(wr, slotCount),
                            price: getPrice(wr, slotCount),
                            is_carport: false
                        });
                        added.push('Wechselrichter');
                    }
                }

                // 5. Elektrische Anschlüsse (wenn Installation gewählt)
                if (installation && /PV|Anlage/i.test(installation)) {
                    var elektro = findProduct(templates, 'Installation', 'Elektrische Anschlüsse');
                    if (elektro) {
                        window.addItemRow({
                            title: getTitle(elektro, slotCount),
                            description: getDesc(elektro, slotCount),
                            quantity: getQty(elektro, slotCount),
                            price: getPrice(elektro, slotCount),
                            is_carport: false
                        });
                        added.push('Elektrische Anschlüsse');
                    }
                }

                // 6. Elektromaterialien (wenn Installation gewählt)
                if (installation && /PV|Anlage/i.test(installation)) {
                    var emat = findProduct(templates, 'Komponenten', 'Elektromaterial');
                    if (emat) {
                        window.addItemRow({
                            title: getTitle(emat, slotCount),
                            description: getDesc(emat, slotCount),
                            quantity: getQty(emat, slotCount),
                            price: getPrice(emat, slotCount),
                            is_carport: false
                        });
                        added.push('Elektromaterialien');
                    }
                }

                // 7. Lieferung immer hinzufügen
                var lieferung = findProduct(templates, 'Lieferung', 'Lieferung');
                if (lieferung) {
                    window.addItemRow({
                        title: getTitle(lieferung, slotCount),
                        description: getDesc(lieferung, slotCount),
                        quantity: getQty(lieferung, slotCount),
                        price: getPrice(lieferung, slotCount),
                        is_carport: false
                    });
                    added.push('Lieferung');
                }

                if (added.length) {
                    var posInfo = '<br><small class="text-muted"><i class="bi bi-list-check me-1"></i>'
                        + added.length + ' Positionen hinzugefügt: ' + added.join(', ') + '</small>';
                    resultDiv.querySelector('.alert').innerHTML += posInfo;
                }
            })
            .catch(function(err) {
                // Positionen konnten nicht geladen werden - nicht schlimm
            });
    }

    // Produkt-Template nach Kategorie und Titel-Fragment finden
    function findProduct(templates, category, titleFragment) {
        var frag = titleFragment.toLowerCase();
        return templates.find(function(t) {
            return t.category === category && t.title.toLowerCase().indexOf(frag) >= 0;
        }) || null;
    }

    // Preis für Stellplatz-Anzahl ermitteln
    function getPrice(template, slots) {
        if (slots === '1' && template.price_1_slot != null) return template.price_1_slot;
        if (slots === '2' && template.price_2_slot != null) return template.price_2_slot;
        if (slots === '3' && template.price_3_plus) {
            var p = parseFloat(template.price_3_plus);
            if (!isNaN(p)) return p;
        }
        // Fallback
        if (template.price_1_slot != null) return template.price_1_slot;
        if (template.price_2_slot != null) return template.price_2_slot;
        return 0;
    }

    // Titel für Stellplatz-Anzahl
    function getTitle(template, slots) {
        if (slots === '1' && template.title_1_slot) return template.title_1_slot;
        if (slots === '2' && template.title_2_slot) return template.title_2_slot;
        if (slots === '3' && template.title_3_plus_title) return template.title_3_plus_title;
        return template.title || '';
    }

    // Beschreibung für Stellplatz-Anzahl
    function getDesc(template, slots) {
        if (slots === '1' && template.description_1_slot) return template.description_1_slot;
        if (slots === '2' && template.description_2_slot) return template.description_2_slot;
        if (slots === '3' && template.description_3_plus_desc) return template.description_3_plus_desc;
        return template.description || '';
    }

    // Menge für Stellplatz-Anzahl
    function getQty(template, slots) {
        if (slots === '1' && template.quantity_1_slot) return template.quantity_1_slot;
        if (slots === '2' && template.quantity_2_slot) return template.quantity_2_slot;
        if (slots === '3' && template.quantity_3_plus_qty) return template.quantity_3_plus_qty;
        return template.default_quantity || '1x';
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
