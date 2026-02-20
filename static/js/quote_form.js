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
            <td>
                <button type="button" class="btn btn-sm btn-outline-danger remove-item-btn">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;

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
            };
        });
    }
    bindRemoveButtons();

    function renumberPositions() {
        const rows = document.querySelectorAll('.item-row');
        rows.forEach(function(row, i) {
            row.querySelector('.pos-number').textContent = i + 1;
        });
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
            const price = parseFloat(priceInput ? priceInput.value : 0) || 0;
            const isCarport = carportCheckbox ? carportCheckbox.checked : false;

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
        if (e.target.classList.contains('item-price') || e.target.classList.contains('item-carport')) {
            recalculate();
        }
    });
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('item-carport')) {
            recalculate();
        }
    });

    // Initial calculation
    recalculate();

    // Add first empty row if no items exist
    if (document.querySelectorAll('.item-row').length === 0) {
        addItemRow();
    }

    // === Product Template Quick-Add ===
    const productModal = document.getElementById('productModal');
    if (productModal) {
        productModal.addEventListener('show.bs.modal', loadProductTemplates);
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
                        const jsonStr = JSON.stringify(t);
                        html += '<button type="button" class="list-group-item list-group-item-action product-add-btn"'
                            + ' data-product-id="' + t.id + '">'
                            + '<div class="d-flex justify-content-between align-items-center">'
                            + '<div>'
                            + '<strong>' + escapeHtml(t.title) + '</strong>'
                            + (t.description ? '<br><small class="text-muted">' + escapeHtml(t.description.substring(0, 100)) + '</small>' : '')
                            + '</div>'
                            + '<div class="text-end text-nowrap ms-3">'
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
                                if (priceSpan) {
                                    priceSpan.textContent = getTemplatePrice(product);
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

    function getTemplatePrice(template) {
        const slots = document.getElementById('slotCount') ? document.getElementById('slotCount').value : '2';
        if (slots === '1' && template.price_1_slot != null) {
            return formatCurrency(template.price_1_slot) + ' \u20AC';
        } else if (slots === '2' && template.price_2_slot != null) {
            return formatCurrency(template.price_2_slot) + ' \u20AC';
        } else if (slots === '3' && template.price_3_plus) {
            return template.price_3_plus;
        }
        // Fallback: try any available price
        if (template.price_1_slot != null) return formatCurrency(template.price_1_slot) + ' \u20AC';
        if (template.price_2_slot != null) return formatCurrency(template.price_2_slot) + ' \u20AC';
        if (template.price_3_plus) return template.price_3_plus;
        return 'Preis eingeben';
    }

    function getTemplatePriceValue(template) {
        const slots = document.getElementById('slotCount') ? document.getElementById('slotCount').value : '2';
        if (slots === '1' && template.price_1_slot != null) return template.price_1_slot;
        if (slots === '2' && template.price_2_slot != null) return template.price_2_slot;
        // Fallback
        if (template.price_1_slot != null) return template.price_1_slot;
        if (template.price_2_slot != null) return template.price_2_slot;
        return 0;
    }

    function addProductToQuote(product, btnElement) {
        const price = getTemplatePriceValue(product);
        let title = product.title;

        // Append Stellplatz info for carport products
        if (product.is_carport && product.category === 'Carport') {
            const slots = document.getElementById('slotCount') ? document.getElementById('slotCount').value : '2';
            const slotLabel = slots === '1' ? '1 Stellplatz' : slots + ' Stellplätze';
            // Only append if title doesn't already contain Stellplatz info
            if (!/Stellpl/i.test(title)) {
                title += ' – ' + slotLabel;
            }
        }

        addItemRow({
            title: title,
            description: product.description || '',
            quantity: product.default_quantity || '1x',
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
