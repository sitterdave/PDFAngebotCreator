document.addEventListener('DOMContentLoaded', function() {
    let itemIndex = document.querySelectorAll('.item-row').length;

    const addItemBtn = document.getElementById('addItemBtn');
    const itemsBody = document.getElementById('itemsBody');
    const countrySelect = document.getElementById('countrySelect');

    // Add new item row
    addItemBtn.addEventListener('click', function() {
        addItemRow();
    });

    function addItemRow() {
        const idx = itemIndex;
        const row = document.createElement('tr');
        row.className = 'item-row';
        row.dataset.index = idx;

        row.innerHTML = `
            <td class="align-middle text-center pos-number">${idx + 1}</td>
            <td>
                <input type="text" name="item_title_${idx}"
                       class="form-control form-control-sm"
                       placeholder="z.B. PV-Carport Modell S2">
            </td>
            <td>
                <textarea name="item_description_${idx}"
                          class="form-control form-control-sm" rows="2"
                          placeholder="Detailbeschreibung..."></textarea>
            </td>
            <td>
                <input type="text" name="item_quantity_${idx}"
                       class="form-control form-control-sm" value="1x"
                       placeholder="1x">
            </td>
            <td>
                <input type="number" name="item_price_${idx}"
                       class="form-control form-control-sm item-price" value="0"
                       step="0.01" min="0">
            </td>
            <td class="text-center carport-col">
                <input type="checkbox" name="item_is_carport_${idx}"
                       class="form-check-input item-carport" value="1">
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

    // Remove item
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

    // Renumber positions after removal
    function renumberPositions() {
        const rows = document.querySelectorAll('.item-row');
        rows.forEach(function(row, i) {
            row.querySelector('.pos-number').textContent = i + 1;
        });
    }

    // Country change: show/hide carport column
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

    // Live calculation
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

    // Bind price change events
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
});
