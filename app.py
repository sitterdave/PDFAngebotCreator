import os
import json
from datetime import datetime, timedelta
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_file, jsonify
)
from werkzeug.utils import secure_filename
from models import (
    init_db, get_company_settings, update_company_settings,
    generate_quote_number, create_quote, get_quote, get_all_quotes,
    update_quote, delete_quote, duplicate_quote, calculate_quote_totals,
    get_all_product_templates, get_product_template,
    create_product_template, update_product_template, delete_product_template
)
from pdf_generator import generate_quote_pdf
import io

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.before_request
def before_request():
    init_db()


# --- Dashboard ---

@app.route('/')
def index():
    quotes = get_all_quotes()
    for q in quotes:
        _, items = get_quote(q['id'])
        totals = calculate_quote_totals(items, q['country'])
        q['brutto'] = totals['brutto']
        q['netto'] = totals['netto']
    return render_template('index.html', quotes=quotes)


# --- Quote CRUD ---

@app.route('/quote/new')
def new_quote():
    settings = get_company_settings()
    quote_number = generate_quote_number()
    today = datetime.now().strftime('%Y-%m-%d')
    valid_days = settings.get('default_valid_days', 30) or 30
    valid_until = (datetime.now() + timedelta(days=int(valid_days))).strftime('%Y-%m-%d')
    default_country = settings.get('default_country', 'AT') or 'AT'
    default_creator = settings.get('default_creator_name', '') or ''

    quote = {
        'quote_number': quote_number,
        'date': today,
        'valid_until': valid_until,
        'country': default_country,
        'customer_salutation': '',
        'customer_name': '',
        'customer_company': '',
        'customer_street': '',
        'customer_zip': '',
        'customer_city': '',
        'customer_country_label': 'Österreich' if default_country == 'AT' else 'Deutschland',
        'customer_phone': '',
        'customer_email': '',
        'project_name': '',
        'project_description': '',
        'creator_name': default_creator,
        'notes': '',
        'custom_terms': settings.get('terms_text', ''),
    }
    items = []
    return render_template('quote_form.html', quote=quote, items=items, is_new=True)


@app.route('/quote/save', methods=['POST'])
def save_quote():
    data = {
        'quote_number': request.form.get('quote_number', ''),
        'date': request.form.get('date', ''),
        'valid_until': request.form.get('valid_until', ''),
        'country': request.form.get('country', 'AT'),
        'customer_salutation': request.form.get('customer_salutation', ''),
        'customer_name': request.form.get('customer_name', ''),
        'customer_company': request.form.get('customer_company', ''),
        'customer_street': request.form.get('customer_street', ''),
        'customer_zip': request.form.get('customer_zip', ''),
        'customer_city': request.form.get('customer_city', ''),
        'customer_country_label': request.form.get('customer_country_label', ''),
        'customer_phone': request.form.get('customer_phone', ''),
        'customer_email': request.form.get('customer_email', ''),
        'customer_uid': request.form.get('customer_uid', ''),
        'project_name': request.form.get('project_name', ''),
        'project_description': request.form.get('project_description', ''),
        'creator_name': request.form.get('creator_name', ''),
        'notes': request.form.get('notes', ''),
        'custom_terms': request.form.get('custom_terms', ''),
    }

    items = parse_items_from_form(request.form)
    quote_id = request.form.get('quote_id')

    if quote_id:
        update_quote(int(quote_id), data, items)
        flash('Angebot erfolgreich aktualisiert.', 'success')
        return redirect(url_for('view_quote', quote_id=int(quote_id)))
    else:
        new_id = create_quote(data, items)
        flash('Angebot erfolgreich erstellt.', 'success')
        return redirect(url_for('view_quote', quote_id=new_id))


@app.route('/quote/<int:quote_id>')
def view_quote(quote_id):
    quote, items = get_quote(quote_id)
    if not quote:
        flash('Angebot nicht gefunden.', 'error')
        return redirect(url_for('index'))
    totals = calculate_quote_totals(items, quote['country'])
    settings = get_company_settings()
    return render_template('quote_view.html', quote=quote, items=items, totals=totals, settings=settings)


@app.route('/quote/<int:quote_id>/edit')
def edit_quote(quote_id):
    quote, items = get_quote(quote_id)
    if not quote:
        flash('Angebot nicht gefunden.', 'error')
        return redirect(url_for('index'))
    return render_template('quote_form.html', quote=quote, items=items, is_new=False)


@app.route('/quote/<int:quote_id>/delete', methods=['POST'])
def delete_quote_route(quote_id):
    delete_quote(quote_id)
    flash('Angebot gelöscht.', 'success')
    return redirect(url_for('index'))


@app.route('/quote/<int:quote_id>/duplicate', methods=['POST'])
def duplicate_quote_route(quote_id):
    new_id = duplicate_quote(quote_id)
    if new_id:
        flash('Angebot dupliziert.', 'success')
        return redirect(url_for('edit_quote', quote_id=new_id))
    flash('Fehler beim Duplizieren.', 'error')
    return redirect(url_for('index'))


@app.route('/quote/<int:quote_id>/pdf')
def download_pdf(quote_id):
    quote, items = get_quote(quote_id)
    if not quote:
        flash('Angebot nicht gefunden.', 'error')
        return redirect(url_for('index'))

    pdf_bytes = generate_quote_pdf(quote, items)
    buffer = io.BytesIO(pdf_bytes)
    filename = f"Angebot_{quote['quote_number'].replace('/', '-').replace(':', '-').replace(' ', '_')}.pdf"

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@app.route('/quote/<int:quote_id>/pdf/preview')
def preview_pdf(quote_id):
    quote, items = get_quote(quote_id)
    if not quote:
        flash('Angebot nicht gefunden.', 'error')
        return redirect(url_for('index'))

    pdf_bytes = generate_quote_pdf(quote, items)
    buffer = io.BytesIO(pdf_bytes)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=False,
    )


# --- Settings ---

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        kwargs = {
            'company_name': request.form.get('company_name', ''),
            'company_street': request.form.get('company_street', ''),
            'company_zip': request.form.get('company_zip', ''),
            'company_city': request.form.get('company_city', ''),
            'company_country': request.form.get('company_country', 'AT'),
            'company_phone': request.form.get('company_phone', ''),
            'company_email': request.form.get('company_email', ''),
            'company_website': request.form.get('company_website', ''),
            'company_tax_number': request.form.get('company_tax_number', ''),
            'company_ust_id': request.form.get('company_ust_id', ''),
            'firmenbuchnummer': request.form.get('firmenbuchnummer', ''),
            'gerichtsstandort': request.form.get('gerichtsstandort', ''),
            'bank_name': request.form.get('bank_name', ''),
            'iban': request.form.get('iban', ''),
            'bic': request.form.get('bic', ''),
            'default_valid_days': int(request.form.get('default_valid_days', 30) or 30),
            'default_country': request.form.get('default_country', 'AT'),
            'default_creator_name': request.form.get('default_creator_name', ''),
            'terms_text': request.form.get('terms_text', ''),
            'brand_name': request.form.get('brand_name', ''),
            'brand_slogan': request.form.get('brand_slogan', ''),
        }

        # Handle logo upload
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                name, ext = os.path.splitext(filename)
                filename = f"logo_{int(datetime.now().timestamp())}{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                kwargs['logo_path'] = filename

        update_company_settings(**kwargs)
        flash('Einstellungen gespeichert.', 'success')
        return redirect(url_for('settings'))

    current = get_company_settings()
    return render_template('settings.html', settings=current)


@app.route('/settings/delete-logo', methods=['POST'])
def delete_logo():
    settings_data = get_company_settings()
    if settings_data.get('logo_path'):
        logo_file = os.path.join(UPLOAD_FOLDER, settings_data['logo_path'])
        if os.path.exists(logo_file):
            os.remove(logo_file)
        update_company_settings(logo_path='')
    flash('Logo entfernt.', 'success')
    return redirect(url_for('settings'))


# --- API for live calculation ---

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    data = request.get_json()
    items = data.get('items', [])
    country = data.get('country', 'AT')
    totals = calculate_quote_totals(items, country)
    return jsonify({
        'netto': round(totals['netto'], 2),
        'vat_total': round(totals['vat_total'], 2),
        'brutto': round(totals['brutto'], 2),
        'items': [{
            'total_price': round(float(i.get('total_price', 0)), 2),
            'vat_rate': i['vat_rate'],
            'vat_amount': round(i['vat_amount'], 2),
        } for i in totals['positions']]
    })


# --- Product Templates ---

@app.route('/products')
def product_list():
    templates = get_all_product_templates()
    # Group by category
    categories = {}
    for t in templates:
        cat = t.get('category', 'Sonstige') or 'Sonstige'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)
    return render_template('products.html', categories=categories, templates=templates)


@app.route('/products/new', methods=['GET', 'POST'])
def new_product():
    if request.method == 'POST':
        data = _parse_product_form(request.form)
        create_product_template(data)
        flash('Produktvorlage erstellt.', 'success')
        return redirect(url_for('product_list'))
    return render_template('product_form.html', product={}, is_new=True)


@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    if request.method == 'POST':
        data = _parse_product_form(request.form)
        update_product_template(product_id, data)
        flash('Produktvorlage aktualisiert.', 'success')
        return redirect(url_for('product_list'))
    product = get_product_template(product_id)
    if not product:
        flash('Vorlage nicht gefunden.', 'error')
        return redirect(url_for('product_list'))
    return render_template('product_form.html', product=product, is_new=False)


@app.route('/products/<int:product_id>/delete', methods=['POST'])
def delete_product_route(product_id):
    delete_product_template(product_id)
    flash('Produktvorlage gelöscht.', 'success')
    return redirect(url_for('product_list'))


@app.route('/api/products')
def api_products():
    """Return product templates as JSON for the quote form quick-add."""
    templates = get_all_product_templates()
    return jsonify(templates)


def _parse_product_form(form):
    return {
        'category': form.get('category', ''),
        'title': form.get('title', ''),
        'description': form.get('description', ''),
        'default_quantity': form.get('default_quantity', '1x'),
        'title_1_slot': form.get('title_1_slot', ''),
        'title_2_slot': form.get('title_2_slot', ''),
        'title_3_plus_title': form.get('title_3_plus_title', ''),
        'description_1_slot': form.get('description_1_slot', ''),
        'description_2_slot': form.get('description_2_slot', ''),
        'description_3_plus_desc': form.get('description_3_plus_desc', ''),
        'quantity_1_slot': form.get('quantity_1_slot', ''),
        'quantity_2_slot': form.get('quantity_2_slot', ''),
        'quantity_3_plus_qty': form.get('quantity_3_plus_qty', ''),
        'price_1_slot': form.get('price_1_slot', '') or None,
        'price_2_slot': form.get('price_2_slot', '') or None,
        'price_3_plus': form.get('price_3_plus', ''),
        'is_carport': 1 if form.get('is_carport') else 0,
        'sort_order': int(form.get('sort_order', 0) or 0),
    }


def parse_items_from_form(form):
    # Primary: read items from JSON hidden field (most reliable for dynamic rows)
    items_json = form.get('items_json', '')
    if items_json:
        try:
            raw_items = json.loads(items_json)
            items = []
            for item in raw_items:
                title = str(item.get('title', ''))
                desc = str(item.get('description', ''))
                if title.strip() or desc.strip():
                    items.append({
                        'title': title,
                        'description': desc,
                        'quantity': str(item.get('quantity', '1x')) or '1x',
                        'total_price': float(item.get('total_price', 0) or 0),
                        'is_carport': int(item.get('is_carport', 0) or 0),
                        'is_optional': int(item.get('is_optional', 0) or 0),
                    })
            if items:
                return items
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    # Fallback: read from individual form fields
    indices = set()
    for key in form.keys():
        if key.startswith('item_title_'):
            try:
                indices.add(int(key.split('_')[-1]))
            except ValueError:
                pass

    items = []
    for i in sorted(indices):
        title = form.get(f'item_title_{i}', '')
        if title.strip() or form.get(f'item_description_{i}', '').strip():
            items.append({
                'title': title,
                'description': form.get(f'item_description_{i}', ''),
                'quantity': form.get(f'item_quantity_{i}', '1x') or '1x',
                'total_price': float(form.get(f'item_price_{i}', 0) or 0),
                'is_carport': 1 if form.get(f'item_is_carport_{i}') else 0,
                'is_optional': 1 if form.get(f'item_is_optional_{i}') else 0,
            })
    return items


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
