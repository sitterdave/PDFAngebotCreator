document.addEventListener('DOMContentLoaded', function() {
    let itemIndex = document.querySelectorAll('.item-row').length;

    const addItemBtn = document.getElementById('addItemBtn');
    const itemsBody = document.getElementById('itemsBody');
    const countrySelect = document.getElementById('countrySelect');

    // --- Add new empty item row ---
    addItemBtn.addEventListener('click', function() {
        addItemRow();
    });

    function addItemRow(data) {
        const idx = itemIndex;
        const row = document.createElement('tr');
        row.className = 'item-row';
        row.dataset.index = idx;

        const title = data ? (data.title || '') : '';
        const desc = data ? (data.description || '') : '';
        const qty = data ? (data.quantity || '1x') : '1x';
        const price = data ? (data.price || 0) : 0;
        const isCarport = data ? data.is_carport : false;
        const isOptional = data ? data.is_optional : false;

        row.innerHTML = `
            <td class="align-middle text-center pos-number">${document.querySelectorAll('.item-row').length + 1}</td>
            <td>
                <input type="text" name="item_title_${idx}"
                       class="form-control form-control-sm"
                       value="${escapeAttr(title)}"
                       placeholder="z.B. PV-Carport Modell S2">
            </td>
            <td>
                <textarea name="item_description_${idx}"
                          class="form-control form-control-sm" rows="2"
                          placeholder="Detailbeschreibung...">${escapeHtml(desc)}</textarea>
            </td>
            <td>
                <input type="text" name="item_quantity_${idx}"
                       class="form-control form-control-sm" value="${escapeAttr(qty)}"
                       placeholder="1x">
            </td>
            <td>
                <input type="number" name="item_price_${idx}"
                       class="form-control form-control-sm item-price" value="${price}"
                       step="0.01" min="0">
            </td>
            <td class="text-center carport-col">
                <input type="checkbox" name="item_is_carport_${idx}"
                       class="form-check-input item-carport" value="1"
                       ${isCarport ? 'checked' : ''}>
            </td>
            <td class="text-center">
                <input type="checkbox" name="item_is_optional_${idx}"
                       class="form-check-input item-optional" value="1"
                       ${isOptional ? 'checked' : ''}>
            </td>
            <td>
                <button type="button" class="btn btn-sm btn-outline-danger remove-item-btn">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;

        // Remove empty hint if present
        const hint = document.getElementById('emptyItemsHint');
        if (hint) hint.remove();

        itemsBody.appendChild(row);
        itemIndex++;
        updateCarportVisibility();
        bindRemoveButtons();
        recalculate();
    }

    // --- Remove item ---
    function bindRemoveButtons() {
        document.querySelectorAll('.remove-item-btn').forEach(function(btn) {
            btn.onclick = function() {
                btn.closest('tr').remove();
                renumberPositions();
                recalculate();
                updateEmptyHint();
            };
        });
    }
    bindRemoveButtons();

    function renumberPositions() {
        const rows = document.querySelectorAll('.item-row');
        rows.forEach(function(row, i) {
            row.querySelector('.pos-number').textContent = i + 1;
            row.dataset.index = i;
            // Re-index all form field names so indices are always 0, 1, 2, ...
            row.querySelectorAll('input, textarea').forEach(function(el) {
                if (el.name) {
                    el.name = el.name.replace(/_\d+$/, '_' + i);
                }
            });
        });
        itemIndex = rows.length;
    }

    // --- Country change: show/hide carport column ---
    if (countrySelect) {
        countrySelect.addEventListener('change', function() {
            updateCarportVisibility();
            recalculate();
        });
    }

    function updateCarportVisibility() {
        const country = countrySelect ? countrySelect.value : 'AT';
        const carportHeader = document.getElementById('carportColHeader');
        const carportCols = document.querySelectorAll('.carport-col');

        if (country === 'DE') {
            if (carportHeader) carportHeader.style.display = '';
            carportCols.forEach(c => c.style.display = '');
        } else {
            if (carportHeader) carportHeader.style.display = 'none';
            carportCols.forEach(c => c.style.display = 'none');
        }
    }
    updateCarportVisibility();

    // --- Live calculation ---
    function recalculate() {
        const country = countrySelect ? countrySelect.value : 'AT';
        let netto = 0;
        let vatTotal = 0;

        document.querySelectorAll('.item-row').forEach(function(row) {
            const priceInput = row.querySelector('.item-price');
            const carportCheckbox = row.querySelector('.item-carport');
            const optionalCheckbox = row.querySelector('.item-optional');
            const price = parseFloat(priceInput ? priceInput.value : 0) || 0;
            const isCarport = carportCheckbox ? carportCheckbox.checked : false;
            const isOptional = optionalCheckbox ? optionalCheckbox.checked : false;

            // Optionale Positionen nicht in Summe zählen
            if (isOptional) return;

            netto += price;

            let vatRate = 0;
            if (country === 'AT') {
                vatRate = 0.20;
            } else if (country === 'DE' && isCarport) {
                vatRate = 0.19;
            }
            vatTotal += price * vatRate;
        });

        const brutto = netto + vatTotal;

        document.getElementById('subtotal').textContent = formatCurrency(netto) + ' \u20AC';
        document.getElementById('vatTotal').textContent = formatCurrency(vatTotal) + ' \u20AC';
        document.getElementById('grandTotal').textContent = formatCurrency(brutto) + ' \u20AC';
    }

    function formatCurrency(value) {
        return value.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // Bind price change events (using event delegation)
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('item-price') || e.target.classList.contains('item-carport') || e.target.classList.contains('item-optional')) {
            recalculate();
        }
    });
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('item-carport') || e.target.classList.contains('item-optional')) {
            recalculate();
        }
    });

    // Initial calculation
    recalculate();

    // Show hint when no items exist (no auto-added empty row)
    function updateEmptyHint() {
        let hint = document.getElementById('emptyItemsHint');
        if (document.querySelectorAll('.item-row').length === 0) {
            if (!hint) {
                hint = document.createElement('tr');
                hint.id = 'emptyItemsHint';
                hint.innerHTML = '<td colspan="8" class="text-center text-muted py-3">'
                    + '<i class="bi bi-info-circle me-1"></i>'
                    + 'Positionen über "Aus Vorlage" oder "Leere Position" hinzufügen'
                    + '</td>';
                itemsBody.appendChild(hint);
            }
        } else if (hint) {
            hint.remove();
        }
    }
    updateEmptyHint();

    // === Product Template Quick-Add ===
    const productModal = document.getElementById('productModal');
    if (productModal) {
        // Bei jedem Öffnen: zurück zu Step 1 (Stellplatz-Auswahl)
        productModal.addEventListener('show.bs.modal', function() {
            document.getElementById('slotSelectionStep').style.display = '';
            document.getElementById('productSelectionStep').style.display = 'none';
        });

        // Stellplatz-Buttons: Auswahl setzen und zu Step 2 wechseln
        document.querySelectorAll('.slot-select-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var slots = this.getAttribute('data-slots');
                document.getElementById('slotCount').value = slots;
                var label = slots === '1' ? '1 Stellplatz' : (slots === '2' ? '2 Stellplätze' : '3+ Stellplätze');
                document.getElementById('selectedSlotBadge').textContent = label;
                document.getElementById('slotSelectionStep').style.display = 'none';
                document.getElementById('productSelectionStep').style.display = '';
                loadProductTemplates();
            });
        });

        // Zurück-Button: zurück zu Step 1
        document.getElementById('backToSlotBtn').addEventListener('click', function() {
            document.getElementById('slotSelectionStep').style.display = '';
            document.getElementById('productSelectionStep').style.display = 'none';
        });
    }

    function loadProductTemplates() {
        const container = document.getElementById('productList');
        container.innerHTML = '<p class="text-muted">Lade...</p>';

        fetch('/api/products')
            .then(r => r.json())
            .then(templates => {
                if (!templates.length) {
                    container.innerHTML = '<p class="text-muted">Keine Produktvorlagen vorhanden. Erstellen Sie welche unter "Produkte".</p>';
                    return;
                }

                // Group by category
                const cats = {};
                templates.forEach(t => {
                    const cat = t.category || 'Sonstige';
                    if (!cats[cat]) cats[cat] = [];
                    cats[cat].push(t);
                });

                let html = '';
                for (const [catName, catItems] of Object.entries(cats)) {
                    html += '<h6 class="mt-3 mb-2 text-muted">' + escapeHtml(catName) + '</h6>';
                    html += '<div class="list-group mb-2">';
                    catItems.forEach(t => {
                        const qty = getTemplateQuantityDisplay(t);
                        const displayTitle = getTemplateTitle(t);
                        const displayDesc = getTemplateDescription(t);
                        html += '<button type="button" class="list-group-item list-group-item-action product-add-btn"'
                            + ' data-product-id="' + t.id + '">'
                            + '<div class="d-flex justify-content-between align-items-center">'
                            + '<div>'
                            + '<strong class="product-title">' + escapeHtml(displayTitle) + '</strong>'
                            + (displayDesc ? '<br><small class="text-muted product-desc">' + escapeHtml(displayDesc.substring(0, 100)) + '</small>' : '')
                            + '</div>'
                            + '<div class="text-end text-nowrap ms-3">'
                            + (qty ? '<span class="product-qty badge bg-info me-1">' + escapeHtml(qty) + '</span>' : '')
                            + '<span class="product-price badge bg-secondary">' + getTemplatePrice(t) + '</span>'
                            + '</div>'
                            + '</div>'
                            + '</button>';
                    });
                    html += '</div>';
                }
                container.innerHTML = html;

                // Store templates for later use
                container._templates = templates;

                // Bind click handlers
                container.querySelectorAll('.product-add-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const pid = parseInt(this.dataset.productId);
                        const product = templates.find(t => t.id === pid);
                        if (product) addProductToQuote(product, this);
                    });
                });

                // Update prices when slot count changes
                const slotSelect = document.getElementById('slotCount');
                if (slotSelect) {
                    slotSelect.onchange = function() {
                        container.querySelectorAll('.product-add-btn').forEach(btn => {
                            const pid = parseInt(btn.dataset.productId);
                            const product = templates.find(t => t.id === pid);
                            if (product) {
                                const priceSpan = btn.querySelector('.product-price');
                                if (priceSpan) priceSpan.textContent = getTemplatePrice(product);
                                const qtySpan = btn.querySelector('.product-qty');
                                const qtyText = getTemplateQuantityDisplay(product);
                                if (qtySpan) {
                                    if (qtyText) { qtySpan.textContent = qtyText; qtySpan.style.display = ''; }
                                    else { qtySpan.style.display = 'none'; }
                                }
                                const titleEl = btn.querySelector('.product-title');
                                if (titleEl) titleEl.textContent = getTemplateTitle(product);
                                const descEl = btn.querySelector('.product-desc');
                                if (descEl) {
                                    const d = getTemplateDescription(product);
                                    descEl.textContent = d ? d.substring(0, 100) : '';
                                }
                            }
                        });
                    };
                }
            })
            .catch(() => {
                container.innerHTML = '<p class="text-danger">Fehler beim Laden der Vorlagen.</p>';
            });
    }

    function getSlotCount() {
        const el = document.getElementById('slotCount');
        return el ? el.value : '2';
    }

    function getTemplateTitle(template) {
        const slots = getSlotCount();
        if (slots === '1' && template.title_1_slot) return template.title_1_slot;
        if (slots === '2' && template.title_2_slot) return template.title_2_slot;
        if (slots === '3' && template.title_3_plus_title) return template.title_3_plus_title;
        return template.title || '';
    }

    function getTemplateDescription(template) {
        const slots = getSlotCount();
        if (slots === '1' && template.description_1_slot) return template.description_1_slot;
        if (slots === '2' && template.description_2_slot) return template.description_2_slot;
        if (slots === '3' && template.description_3_plus_desc) return template.description_3_plus_desc;
        return template.description || '';
    }

    function getTemplateQuantityDisplay(template) {
        const slots = getSlotCount();
        if (slots === '1' && template.quantity_1_slot) return template.quantity_1_slot;
        if (slots === '2' && template.quantity_2_slot) return template.quantity_2_slot;
        if (slots === '3' && template.quantity_3_plus_qty) return template.quantity_3_plus_qty;
        return '';
    }

    function getTemplatePrice(template) {
        const slots = getSlotCount();
        if (slots === '1' && template.price_1_slot != null) {
            return formatCurrency(template.price_1_slot) + ' \u20AC';
        } else if (slots === '2' && template.price_2_slot != null) {
            return formatCurrency(template.price_2_slot) + ' \u20AC';
        } else if (slots === '3' && template.price_3_plus) {
            return template.price_3_plus;
        }
        if (template.price_1_slot != null) return formatCurrency(template.price_1_slot) + ' \u20AC';
        if (template.price_2_slot != null) return formatCurrency(template.price_2_slot) + ' \u20AC';
        if (template.price_3_plus) return template.price_3_plus;
        return 'Preis eingeben';
    }

    function getTemplatePriceValue(template) {
        const slots = getSlotCount();
        if (slots === '1' && template.price_1_slot != null) return template.price_1_slot;
        if (slots === '2' && template.price_2_slot != null) return template.price_2_slot;
        if (slots === '3' && template.price_3_plus) {
            const parsed = parseFloat(template.price_3_plus);
            if (!isNaN(parsed)) return parsed;
        }
        if (template.price_1_slot != null) return template.price_1_slot;
        if (template.price_2_slot != null) return template.price_2_slot;
        return 0;
    }

    function getTemplateQuantity(product) {
        const slots = getSlotCount();
        if (slots === '1' && product.quantity_1_slot) return product.quantity_1_slot;
        if (slots === '2' && product.quantity_2_slot) return product.quantity_2_slot;
        if (slots === '3' && product.quantity_3_plus_qty) return product.quantity_3_plus_qty;
        return product.default_quantity || '1x';
    }

    function addProductToQuote(product, btnElement) {
        const price = getTemplatePriceValue(product);
        const quantity = getTemplateQuantity(product);
        let title = getTemplateTitle(product);
        const description = getTemplateDescription(product);

        // Append Stellplatz info for carport products
        if (product.is_carport && product.category === 'Carport') {
            const slots = getSlotCount();
            const slotLabel = slots === '1' ? '1 Stellplatz' : slots + ' Stellplätze';
            if (!/Stellpl/i.test(title)) {
                title += ' \u2013 ' + slotLabel;
            }
        }

        addItemRow({
            title: title,
            description: description,
            quantity: quantity,
            price: price,
            is_carport: product.is_carport ? true : false,
        });

        // Visual feedback: flash the button blue instead of closing modal
        if (btnElement) {
            const origBg = btnElement.style.backgroundColor;
            const origColor = btnElement.style.color;
            btnElement.style.backgroundColor = '#1976D280';
            btnElement.style.color = '#fff';
            const badge = document.createElement('span');
            badge.className = 'badge bg-primary ms-2 added-badge';
            badge.textContent = 'Hinzugefügt!';
            btnElement.querySelector('.d-flex').appendChild(badge);
            setTimeout(() => {
                btnElement.style.backgroundColor = origBg;
                btnElement.style.color = origColor;
                const b = btnElement.querySelector('.added-badge');
                if (b) b.remove();
            }, 1500);
        }
    }

    // --- Form submit: serialize items to JSON hidden field for reliable submission ---
    const quoteForm = document.getElementById('quoteForm');
    if (quoteForm) {
        quoteForm.addEventListener('submit', function() {
            renumberPositions();
            const items = [];
            document.querySelectorAll('.item-row').forEach(function(row) {
                const idx = row.dataset.index;
                const titleEl = row.querySelector('[name="item_title_' + idx + '"]');
                const descEl = row.querySelector('[name="item_description_' + idx + '"]');
                const qtyEl = row.querySelector('[name="item_quantity_' + idx + '"]');
                const priceEl = row.querySelector('[name="item_price_' + idx + '"]');
                const carportEl = row.querySelector('[name="item_is_carport_' + idx + '"]');
                const optionalEl = row.querySelector('[name="item_is_optional_' + idx + '"]');
                items.push({
                    title: titleEl ? titleEl.value : '',
                    description: descEl ? descEl.value : '',
                    quantity: qtyEl ? qtyEl.value || '1x' : '1x',
                    total_price: priceEl ? parseFloat(priceEl.value) || 0 : 0,
                    is_carport: carportEl ? (carportEl.checked ? 1 : 0) : 0,
                    is_optional: optionalEl ? (optionalEl.checked ? 1 : 0) : 0,
                });
            });
            // Write JSON into hidden field
            let jsonField = document.getElementById('items_json');
            if (!jsonField) {
                jsonField = document.createElement('input');
                jsonField.type = 'hidden';
                jsonField.id = 'items_json';
                jsonField.name = 'items_json';
                quoteForm.appendChild(jsonField);
            }
            jsonField.value = JSON.stringify(items);
        });
    }

    // --- Utility ---
    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function escapeAttr(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
});
