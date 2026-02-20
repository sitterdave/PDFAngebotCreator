import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'angebote.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS company_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            company_name TEXT DEFAULT '',
            company_street TEXT DEFAULT '',
            company_zip TEXT DEFAULT '',
            company_city TEXT DEFAULT '',
            company_country TEXT DEFAULT 'AT',
            company_phone TEXT DEFAULT '',
            company_email TEXT DEFAULT '',
            company_website TEXT DEFAULT '',
            company_tax_number TEXT DEFAULT '',
            company_ust_id TEXT DEFAULT '',
            firmenbuchnummer TEXT DEFAULT '',
            gerichtsstandort TEXT DEFAULT '',
            bank_name TEXT DEFAULT '',
            iban TEXT DEFAULT '',
            bic TEXT DEFAULT '',
            logo_path TEXT DEFAULT '',
            default_valid_days INTEGER DEFAULT 30,
            default_country TEXT DEFAULT 'AT',
            default_creator_name TEXT DEFAULT '',
            terms_text TEXT DEFAULT '',
            brand_name TEXT DEFAULT '',
            brand_slogan TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_number TEXT NOT NULL UNIQUE,
            date TEXT NOT NULL,
            valid_until TEXT NOT NULL,
            country TEXT NOT NULL DEFAULT 'AT',
            customer_name TEXT NOT NULL,
            customer_company TEXT DEFAULT '',
            customer_street TEXT DEFAULT '',
            customer_zip TEXT DEFAULT '',
            customer_city TEXT DEFAULT '',
            customer_country_label TEXT DEFAULT '',
            customer_phone TEXT DEFAULT '',
            customer_email TEXT DEFAULT '',
            project_name TEXT DEFAULT '',
            project_description TEXT DEFAULT '',
            creator_name TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            custom_terms TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quote_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            quantity TEXT NOT NULL DEFAULT '1x',
            total_price REAL NOT NULL DEFAULT 0,
            is_carport INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE
        );
    ''')

    # Ensure default company settings row exists
    existing = conn.execute("SELECT id FROM company_settings WHERE id = 1").fetchone()
    if not existing:
        default_terms = (
            "1) Dieses Angebot ist 30 Tage ab Ausstellungsdatum gueltig. "
            "Nach Ablauf dieser Frist behalten wir uns eine Anpassung der Konditionen vor.\n"
            "2) Wir behandeln Ihre Daten mit groesster Sorgfalt.\n"
            "3) Die Zahlung erfolgt in zwei Raten:\n"
            "    - 50 % Anzahlung bei Angebotsannahme. Eine Anzahlungsrechnung ueber 50% wird hierzu erstellt.\n"
            "    - 50 % Restzahlung nach Fertigstellung und Lieferung aller Positionen.\n"
            "4) Partnerfirma fuer Installationsarbeiten: Alle Installations- und elektrischen Anschlussarbeiten "
            "werden in Zusammenarbeit mit unserer erfahrenen Partnerfirma durchgefuehrt.\n"
        )
        conn.execute(
            "INSERT INTO company_settings (id, terms_text) VALUES (1, ?)",
            (default_terms,)
        )
        conn.commit()

    conn.close()


# --- Company Settings ---

def get_company_settings():
    conn = get_db()
    row = conn.execute("SELECT * FROM company_settings WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else {}


def update_company_settings(**kwargs):
    conn = get_db()
    allowed = [
        'company_name', 'company_street', 'company_zip', 'company_city',
        'company_country', 'company_phone', 'company_email', 'company_website',
        'company_tax_number', 'company_ust_id', 'firmenbuchnummer', 'gerichtsstandort',
        'bank_name', 'iban', 'bic', 'logo_path', 'default_valid_days',
        'default_country', 'default_creator_name', 'terms_text',
        'brand_name', 'brand_slogan'
    ]
    sets = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            values.append(v)
    if sets:
        conn.execute(f"UPDATE company_settings SET {', '.join(sets)} WHERE id = 1", values)
        conn.commit()
    conn.close()


# --- Quotes ---

def generate_quote_number():
    """Generate quote number as timestamp: DD.MM.YYYY HH:MM:SS"""
    return datetime.now().strftime('%d.%m.%Y %H:%M:%S')


def create_quote(data, items):
    conn = get_db()
    now = datetime.now().isoformat()
    cursor = conn.execute('''
        INSERT INTO quotes (quote_number, date, valid_until, country,
            customer_name, customer_company, customer_street, customer_zip,
            customer_city, customer_country_label, customer_phone, customer_email,
            project_name, project_description, creator_name, notes, custom_terms,
            created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['quote_number'], data['date'], data['valid_until'], data['country'],
        data['customer_name'], data.get('customer_company', ''),
        data.get('customer_street', ''), data.get('customer_zip', ''),
        data.get('customer_city', ''), data.get('customer_country_label', ''),
        data.get('customer_phone', ''), data.get('customer_email', ''),
        data.get('project_name', ''), data.get('project_description', ''),
        data.get('creator_name', ''), data.get('notes', ''),
        data.get('custom_terms', ''), now, now
    ))
    quote_id = cursor.lastrowid

    for i, item in enumerate(items):
        conn.execute('''
            INSERT INTO quote_items (quote_id, position, title, description, quantity, total_price, is_carport)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            quote_id, i + 1, item.get('title', ''),
            item.get('description', ''),
            item.get('quantity', '1x'),
            float(item.get('total_price', 0) or 0),
            int(item.get('is_carport', 0))
        ))

    conn.commit()
    conn.close()
    return quote_id


def get_quote(quote_id):
    conn = get_db()
    quote = conn.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
    if not quote:
        conn.close()
        return None, []
    items = conn.execute(
        "SELECT * FROM quote_items WHERE quote_id = ? ORDER BY position", (quote_id,)
    ).fetchall()
    conn.close()
    return dict(quote), [dict(i) for i in items]


def get_all_quotes():
    conn = get_db()
    quotes = conn.execute("SELECT * FROM quotes ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(q) for q in quotes]


def update_quote(quote_id, data, items):
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute('''
        UPDATE quotes SET date=?, valid_until=?, country=?,
            customer_name=?, customer_company=?, customer_street=?, customer_zip=?,
            customer_city=?, customer_country_label=?, customer_phone=?, customer_email=?,
            project_name=?, project_description=?, creator_name=?, notes=?, custom_terms=?,
            updated_at=?
        WHERE id=?
    ''', (
        data['date'], data['valid_until'], data['country'],
        data['customer_name'], data.get('customer_company', ''),
        data.get('customer_street', ''), data.get('customer_zip', ''),
        data.get('customer_city', ''), data.get('customer_country_label', ''),
        data.get('customer_phone', ''), data.get('customer_email', ''),
        data.get('project_name', ''), data.get('project_description', ''),
        data.get('creator_name', ''), data.get('notes', ''),
        data.get('custom_terms', ''), now, quote_id
    ))

    # Replace items
    conn.execute("DELETE FROM quote_items WHERE quote_id = ?", (quote_id,))
    for i, item in enumerate(items):
        conn.execute('''
            INSERT INTO quote_items (quote_id, position, title, description, quantity, total_price, is_carport)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            quote_id, i + 1, item.get('title', ''),
            item.get('description', ''),
            item.get('quantity', '1x'),
            float(item.get('total_price', 0) or 0),
            int(item.get('is_carport', 0))
        ))

    conn.commit()
    conn.close()


def delete_quote(quote_id):
    conn = get_db()
    conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
    conn.commit()
    conn.close()


def duplicate_quote(quote_id):
    quote, items = get_quote(quote_id)
    if not quote:
        return None
    quote['quote_number'] = generate_quote_number()
    quote['date'] = datetime.now().strftime('%Y-%m-%d')
    settings = get_company_settings()
    valid_days = settings.get('default_valid_days', 30) or 30
    quote['valid_until'] = (datetime.now() + timedelta(days=int(valid_days))).strftime('%Y-%m-%d')
    new_id = create_quote(quote, items)
    return new_id


def calculate_quote_totals(items, country):
    """Calculate totals with country-specific VAT logic.

    Germany (DE): 19% MwSt only on carport items, 0% on everything else.
    Austria (AT): 20% MwSt on all items.
    """
    netto = 0
    item_details = []

    for item in items:
        price = float(item.get('total_price', 0) or 0)
        netto += price

        if country == 'AT':
            vat_rate = 20.0
        elif country == 'DE':
            vat_rate = 19.0 if item.get('is_carport') else 0.0
        else:
            vat_rate = 0.0

        vat_amount = price * (vat_rate / 100)

        item_details.append({
            **item,
            'vat_rate': vat_rate,
            'vat_amount': vat_amount,
        })

    vat_total = sum(i['vat_amount'] for i in item_details)

    return {
        'positions': item_details,
        'netto': netto,
        'vat_total': vat_total,
        'brutto': netto + vat_total,
    }
