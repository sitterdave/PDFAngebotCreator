import os
import json
import email
import re
try:
    import olefile
except ImportError:
    olefile = None
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


@app.route('/api/parse-email', methods=['POST'])
def api_parse_email():
    """Parse an uploaded .eml/.msg file or plain text and extract customer data."""
    text = ''

    if 'file' in request.files:
        f = request.files['file']
        filename = f.filename or ''
        raw = f.read()

        if filename.lower().endswith('.msg'):
            # Outlook .msg format (OLE2)
            text = _parse_msg_file(raw)
        else:
            # .eml format (RFC822)
            text = _parse_eml_file(raw)
    else:
        text = request.get_data(as_text=True)

    if not text:
        return jsonify({'error': 'Kein Text gefunden'}), 400

    data = _parse_email_text(text)
    data['raw_text'] = text
    return jsonify(data)


def _html_to_text(html):
    """Convert HTML to plain text, preserving line breaks from block elements."""
    import html as html_module
    text = html
    # Block-level tags -> newline before content
    text = re.sub(r'<(?:br|BR)\s*/?\s*>', '\n', text)
    text = re.sub(r'<(?:hr|HR)\s*/?\s*>', '\n---\n', text)
    text = re.sub(r'</(?:div|DIV|p|P|tr|TR|li|LI|h[1-6]|H[1-6]|blockquote|BLOCKQUOTE)\s*>', '\n', text)
    text = re.sub(r'<(?:div|DIV|p|P|tr|TR|li|LI|h[1-6]|H[1-6]|blockquote|BLOCKQUOTE)[^>]*>', '\n', text)
    text = re.sub(r'</(?:td|TD|th|TH)\s*>', '\t', text)
    # Remove all remaining tags
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = html_module.unescape(text)
    # Clean up excessive whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    # Trim each line
    text = '\n'.join(line.strip() for line in text.split('\n'))
    return text.strip()


def _parse_msg_file(raw_bytes):
    """Extract body text from Outlook .msg file using olefile."""
    if olefile is None:
        return ''
    import io as io_module
    try:
        ole = olefile.OleFileIO(io_module.BytesIO(raw_bytes))
    except Exception:
        return ''

    body = ''

    # Try plain text body first
    for stream_name in [
        '__substg1.0_1000001F',  # Body (Unicode)
        '__substg1.0_1000001E',  # Body (ANSI)
    ]:
        if ole.exists(stream_name):
            data = ole.openstream(stream_name).read()
            if stream_name.endswith('1F'):
                body = data.decode('utf-16-le', errors='replace')
            else:
                body = data.decode('utf-8', errors='replace')
            break

    # Fallback: try HTML body
    if not body.strip():
        for stream_name in [
            '__substg1.0_10130102',  # HTML body
            '__substg1.0_1013001F',
            '__substg1.0_1013001E',
        ]:
            if ole.exists(stream_name):
                data = ole.openstream(stream_name).read()
                if stream_name.endswith('1F'):
                    raw_html = data.decode('utf-16-le', errors='replace')
                elif stream_name.endswith('1E'):
                    raw_html = data.decode('utf-8', errors='replace')
                else:
                    raw_html = data.decode('utf-8', errors='replace')
                body = _html_to_text(raw_html)
                break

    ole.close()
    return body


def _parse_eml_file(raw_bytes):
    """Extract body text from .eml (RFC822) file."""
    msg = email.message_from_bytes(raw_bytes)
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain':
                charset = part.get_content_charset() or 'utf-8'
                body = part.get_payload(decode=True).decode(charset, errors='replace')
                break
            elif ct == 'text/html' and not body:
                charset = part.get_content_charset() or 'utf-8'
                html_body = part.get_payload(decode=True).decode(charset, errors='replace')
                body = _html_to_text(html_body)
    else:
        charset = msg.get_content_charset() or 'utf-8'
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(charset, errors='replace')
            if msg.get_content_type() == 'text/html':
                body = _html_to_text(body)
    return body


def _ensure_newlines(text):
    """If text has no newlines, insert them before known labels."""
    if '\n' in text and len(text.split('\n')) > 5:
        return text  # Already has newlines

    # Ordered longest first to avoid partial matches
    labels = [
        'Neue DE Carport-Anfrage', 'Neue Carport-Anfrage',
        'Weitere Informationen', 'Ausgewählte Module',
        'Anzahl Stellplätze', 'Carport-Variante', 'Batteriespeicher',
        'Preisübersicht', 'Gesamtbetrag', 'Konfiguration', 'Installation',
        'Kundendaten', 'UID-Nummer', 'Straße/Nr.', 'Adresse',
        'E-Mail', 'Telefon', 'Hinweis:', 'Firma',
        'Name', 'Land', 'PLZ', 'Ort',
    ]
    for label in labels:
        # Use word boundary \b to prevent matching inside words
        # e.g. "Ort" should not match inside "Carport"
        pattern = r' (?=' + re.escape(label) + r'(?:\s|$))'
        text = re.sub(pattern, '\n', text)

    return text


def _parse_email_text(text):
    """Extract structured fields from a Carport inquiry email."""
    # Pre-process: convert tab-separated "Label\tValue" lines (from HTML tables)
    # into "Label\nValue" so the parser can handle them uniformly
    new_lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        if '\t' in stripped:
            parts = [p.strip() for p in stripped.split('\t') if p.strip()]
            for part in parts:
                new_lines.append(part)
        else:
            new_lines.append(stripped)
    text = '\n'.join(new_lines)

    # Ensure text has proper line breaks (for single-line .msg text)
    text = _ensure_newlines(text)
    lines = [l.strip() for l in text.split('\n')]

    known_labels = [
        'neue carport-anfrage', 'neue de carport-anfrage', 'kundendaten',
        'name', 'e-mail', 'telefon',
        'firma', 'uid-nummer', 'adresse', 'straße/nr.', 'straße/nr', 'plz', 'ort', 'land',
        'konfiguration', 'anzahl stellplätze', 'carport-variante', 'installation',
        'ausgewählte module', 'batteriespeicher', 'weitere informationen',
        'preisübersicht', 'gesamtbetrag', 'hinweis',
    ]

    def norm(s):
        return re.sub(r'[\s:\-/\.]+', ' ', s.lower()).strip()

    norm_labels = [norm(l) for l in known_labels]

    def is_label(line):
        n = norm(line)
        if n in norm_labels:
            return True
        # Also treat as label if line starts with a short label (<=8 chars normalized)
        # that has extra text. E.g. "Adresse Straße/Nr. Winzerweg" starts with "Adresse"
        # But NOT "Installation der PV-Anlage" (long label "installation" has real value after it)
        for nl in norm_labels:
            if len(nl) <= 8 and n.startswith(nl + ' '):
                return True
        return False

    def find_value(label):
        target = norm(label)
        for i, line in enumerate(lines):
            n = norm(line)
            # Exact match: label on its own line, value on next non-empty line
            if n == target:
                if i + 1 < len(lines) and lines[i + 1] and not is_label(lines[i + 1]):
                    return lines[i + 1]
                # If next line is a label or empty, this field has no value
                return ''
            # Same-line match: "Label Value" on one line
            elif n.startswith(target + ' '):
                rest = line[len(label):].strip().lstrip(':').strip()
                if rest:
                    return rest
        return ''

    return {
        'name': find_value('Name'),
        'email': find_value('E-Mail'),
        'phone': find_value('Telefon'),
        'company': find_value('Firma'),
        'uid': find_value('UID-Nummer'),
        'street': find_value('Straße/Nr.') or find_value('Straße/Nr'),
        'zip': find_value('PLZ'),
        'city': find_value('Ort'),
        'country': find_value('Land'),
        'stellplaetze': find_value('Anzahl Stellplätze'),
        'carport_variante': find_value('Carport-Variante'),
        'installation': find_value('Installation'),
        'module': find_value('Ausgewählte Module'),
        'batterie': find_value('Batteriespeicher'),
        'weitere_infos': find_value('Weitere Informationen'),
        'gesamtbetrag': find_value('Gesamtbetrag'),
    }


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
