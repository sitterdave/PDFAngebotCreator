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
            customer_uid TEXT DEFAULT '',
            project_name TEXT DEFAULT '',
            project_description TEXT DEFAULT '',
            creator_name TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            custom_terms TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS product_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            default_quantity TEXT NOT NULL DEFAULT '1x',
            title_1_slot TEXT DEFAULT '',
            title_2_slot TEXT DEFAULT '',
            title_3_plus_title TEXT DEFAULT '',
            description_1_slot TEXT DEFAULT '',
            description_2_slot TEXT DEFAULT '',
            description_3_plus_desc TEXT DEFAULT '',
            quantity_1_slot TEXT DEFAULT '',
            quantity_2_slot TEXT DEFAULT '',
            quantity_3_plus_qty TEXT DEFAULT '',
            price_1_slot REAL DEFAULT NULL,
            price_2_slot REAL DEFAULT NULL,
            price_3_plus TEXT DEFAULT '',
            is_carport INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0
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
            is_optional INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE
        );
    ''')

    # Ensure default company settings row exists
    existing = conn.execute("SELECT id FROM company_settings WHERE id = 1").fetchone()
    if not existing:
        default_terms = (
            "1) Dieses Angebot ist 30 Tage ab Ausstellungsdatum gültig. "
            "Nach Ablauf dieser Frist behalten wir uns eine Anpassung der Konditionen vor.\n\n"
            "2) Wir behandeln Ihre Daten mit größter Sorgfalt. "
            "Unsere aktuelle Datenschutzerklärung finden Sie auf www.stromsparen24.at "
            "oder wir senden Ihnen diese auf Anfrage zu.\n\n"
            "3) Die Zahlung erfolgt in zwei Raten:\n"
            "    \u2022 50 % Anzahlung bei Angebotsannahme. Eine Anzahlungsrechnung über 50% wird hierzu erstellt.\n"
            "    \u2022 50 % Restzahlung nach Fertigstellung und Lieferung aller Positionen.\n\n"
            "4) Bitte beachten Sie, dass Stromsparen24.at ein Service der Labsupport GmbH & Co KG ist. "
            "Deshalb erfolgt die Rechnungsstellung für alle Käufe auf Stromsparen24.at "
            "durch Labsupport GmbH & Co KG.\n\n"
            "5) Partnerfirma für Installationsarbeiten: Alle Installations- und elektrischen Anschlussarbeiten "
            "werden in Zusammenarbeit mit unserer erfahrenen Partnerfirma ProPhone KG durchgeführt. "
            "Diese Partnerschaft gewährleistet eine fachgerechte und reibungslose Umsetzung Ihres Projekts.\n\n"
            "6) Dieses Angebot ist freibleibend und unverbindlich. "
            "Irrtümer, Druckfehler und Preisänderungen bleiben ausdrücklich vorbehalten.\n"
        )
        conn.execute(
            """INSERT INTO company_settings (
                id, company_name, company_street, company_zip, company_city,
                company_country, company_email, company_website,
                company_ust_id, firmenbuchnummer, gerichtsstandort,
                bank_name, iban, bic,
                default_valid_days, default_country, default_creator_name,
                terms_text, brand_name, brand_slogan
            ) VALUES (
                1, 'Labsupport GmbH & Co KG', 'Hauptplatz 5', '3430', 'Tulln an der Donau',
                'AT', 'office@stromsparen24.at', 'www.stromsparen24.at',
                'ATU69952367', 'FN 440720v', 'Tulln',
                'Raiffeisenbank', 'AT44 3254 7000 0101 4591', 'RLNWATWWTLN',
                30, 'AT', 'David Sitter',
                ?, 'Stromsparen24', 'UNSER SONNENSYSTEM, IHRE ENERGIEQUELLE.'
            )""",
            (default_terms,)
        )
        conn.commit()

    # Migrate existing DB: add new columns, fix old text, update company defaults
    _migrate_quotes_columns(conn)
    _migrate_quote_items_columns(conn)
    _migrate_product_template_columns(conn)
    _migrate_existing_data(conn)
    _migrate_product_template_data(conn)

    # Seed product templates if empty
    count = conn.execute("SELECT COUNT(*) as c FROM product_templates").fetchone()['c']
    if count == 0:
        _seed_product_templates(conn)

    conn.close()


def _migrate_quotes_columns(conn):
    """Add new columns to quotes if they don't exist yet."""
    existing = [col[1] for col in conn.execute("PRAGMA table_info(quotes)").fetchall()]
    if 'customer_uid' not in existing:
        conn.execute("ALTER TABLE quotes ADD COLUMN customer_uid TEXT DEFAULT ''")
        conn.commit()


def _migrate_quote_items_columns(conn):
    """Add new columns to quote_items if they don't exist yet."""
    existing = [col[1] for col in conn.execute("PRAGMA table_info(quote_items)").fetchall()]
    if 'is_optional' not in existing:
        conn.execute("ALTER TABLE quote_items ADD COLUMN is_optional INTEGER NOT NULL DEFAULT 0")
        conn.commit()


def _migrate_product_template_columns(conn):
    """Add new columns to product_templates if they don't exist yet."""
    existing = [col[1] for col in conn.execute("PRAGMA table_info(product_templates)").fetchall()]
    new_cols = [
        ('title_1_slot', "TEXT DEFAULT ''"),
        ('title_2_slot', "TEXT DEFAULT ''"),
        ('title_3_plus_title', "TEXT DEFAULT ''"),
        ('description_1_slot', "TEXT DEFAULT ''"),
        ('description_2_slot', "TEXT DEFAULT ''"),
        ('description_3_plus_desc', "TEXT DEFAULT ''"),
        ('quantity_1_slot', "TEXT DEFAULT ''"),
        ('quantity_2_slot', "TEXT DEFAULT ''"),
        ('quantity_3_plus_qty', "TEXT DEFAULT ''"),
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE product_templates ADD COLUMN {col_name} {col_type}")
    conn.commit()


def _migrate_product_template_data(conn):
    """Update existing product templates with slot-specific data."""
    # Update Wechselrichter with slot-specific models
    wr = conn.execute(
        "SELECT id FROM product_templates WHERE title LIKE '%echselrichter%' AND title NOT LIKE '%GoodWe%'"
    ).fetchone()
    if wr:
        conn.execute("""UPDATE product_templates SET
            title = 'Wechselrichter',
            description = 'Hybrid-Wechselrichter mit intelligenter Energiesteuerung und Batteriespeicher-Kompatibilität.',
            title_1_slot = 'GoodWe GW6.5KN-ET PLUS+ Hybrid-Wechselrichter',
            description_1_slot = 'Effizienter Hybrid-Wechselrichter mit intelligenter Energiesteuerung und Batteriespeicher-Kompatibilität für maximale Eigenverbrauchsoptimierung.',
            title_2_slot = 'GoodWe GW8KN-ET PLUS+ Hybrid Wechselrichter',
            description_2_slot = 'Notstromfähig, lüfterlos und geräuscharm ausgestattet mit zwei MPP-Trackern (2 MPPT).',
            default_quantity = '1x',
            price_1_slot = 1085.00,
            price_2_slot = 1211.00,
            price_3_plus = 'Preis auf Anfrage'
        WHERE id = ?""", (wr['id'],))

    # Update PV-Module with slot-specific quantities
    pv = conn.execute(
        "SELECT id FROM product_templates WHERE title LIKE '%PV-Module%' AND category = 'Komponenten'"
    ).fetchone()
    if pv:
        conn.execute("""UPDATE product_templates SET
            quantity_1_slot = '9x',
            quantity_2_slot = '15x',
            quantity_3_plus_qty = '24x'
        WHERE id = ?""", (pv['id'],))

    # Replace generic Batteriespeicher with 3 specific options
    old_bat = conn.execute(
        "SELECT id, sort_order FROM product_templates WHERE title LIKE '%Batteriespeicher%' AND title NOT LIKE '%Pylontech%' AND title NOT LIKE '%Huawei%'"
    ).fetchone()
    if old_bat:
        sort_base = old_bat['sort_order'] or 32
        conn.execute("DELETE FROM product_templates WHERE id = ?", (old_bat['id'],))

        batteries = [
            ('Komponenten', 'Pylontech Force H2 Batteriespeicher 7,1kWh',
             'Modularer Hochvolt-Batteriespeicher mit 7,1 kWh Kapazität, stapelbarem Design und über 5.000 Ladezyklen für eine langlebige Eigenverbrauchsoptimierung.',
             '1x', 2950.00, 2950.00, '', 0, sort_base),
            ('Komponenten', 'Pylontech Force H2 Batteriespeicher 10,65kWh',
             'LiFePO\u2084-Hochvolt-Speicher, IP55, >5000 Zyklen, 95 % DoD.',
             '1x', 3458.00, 3458.00, '', 0, sort_base + 1),
            ('Komponenten', 'Huawei LUNA2000-10-S0 Batterie - 10kWh Speicherpaket',
             'Hochvolt-Batteriespeicher mit 10 kWh Kapazität.',
             '1x', 4050.00, 4050.00, '', 0, sort_base + 2),
        ]
        for b in batteries:
            conn.execute('''
                INSERT INTO product_templates (category, title, description, default_quantity,
                    price_1_slot, price_2_slot, price_3_plus, is_carport, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', b)

    conn.commit()


def _migrate_existing_data(conn):
    """Update existing data that still has old ae/oe/ue text or missing company defaults."""
    row = conn.execute("SELECT terms_text, company_name FROM company_settings WHERE id = 1").fetchone()
    if not row:
        return

    terms = row['terms_text'] or ''
    company_name = row['company_name'] or ''

    # Check if terms need updating: old patterns, wrong numbering, or missing disclaimer
    needs_update = (
        'gueltig' in terms or 'groesster' in terms or 'ueber' in terms
        or 'fuer' in terms or 'durchgefuehrt' in terms
        or '4)\n\n5)' in terms
        or ('\nPartnerfirma' in terms and '5) Partnerfirma' not in terms)
        or ('5) Partnerfirma' in terms and '6) Dieses Angebot ist freibleibend' not in terms)
    )
    if needs_update:
        new_terms = (
            "1) Dieses Angebot ist 30 Tage ab Ausstellungsdatum gültig. "
            "Nach Ablauf dieser Frist behalten wir uns eine Anpassung der Konditionen vor.\n\n"
            "2) Wir behandeln Ihre Daten mit größter Sorgfalt. "
            "Unsere aktuelle Datenschutzerklärung finden Sie auf www.stromsparen24.at "
            "oder wir senden Ihnen diese auf Anfrage zu.\n\n"
            "3) Die Zahlung erfolgt in zwei Raten:\n"
            "    \u2022 50 % Anzahlung bei Angebotsannahme. Eine Anzahlungsrechnung über 50% wird hierzu erstellt.\n"
            "    \u2022 50 % Restzahlung nach Fertigstellung und Lieferung aller Positionen.\n\n"
            "4) Bitte beachten Sie, dass Stromsparen24.at ein Service der Labsupport GmbH & Co KG ist. "
            "Deshalb erfolgt die Rechnungsstellung für alle Käufe auf Stromsparen24.at "
            "durch Labsupport GmbH & Co KG.\n\n"
            "5) Partnerfirma für Installationsarbeiten: Alle Installations- und elektrischen Anschlussarbeiten "
            "werden in Zusammenarbeit mit unserer erfahrenen Partnerfirma ProPhone KG durchgeführt. "
            "Diese Partnerschaft gewährleistet eine fachgerechte und reibungslose Umsetzung Ihres Projekts.\n\n"
            "6) Dieses Angebot ist freibleibend und unverbindlich. "
            "Irrtümer, Druckfehler und Preisänderungen bleiben ausdrücklich vorbehalten.\n"
        )
        conn.execute("UPDATE company_settings SET terms_text = ? WHERE id = 1", (new_terms,))
        conn.commit()

    # Fill in missing company defaults if company_name is still empty
    if not company_name:
        conn.execute("""UPDATE company_settings SET
            company_name = 'Labsupport GmbH & Co KG',
            company_street = 'Hauptplatz 5',
            company_zip = '3430',
            company_city = 'Tulln an der Donau',
            company_country = 'AT',
            company_email = 'office@stromsparen24.at',
            company_website = 'www.stromsparen24.at',
            company_ust_id = 'ATU69952367',
            firmenbuchnummer = 'FN 440720v',
            gerichtsstandort = 'Tulln',
            bank_name = 'Raiffeisenbank',
            iban = 'AT44 3254 7000 0101 4591',
            bic = 'RLNWATWWTLN',
            default_creator_name = 'David Sitter',
            brand_name = 'Stromsparen24',
            brand_slogan = 'UNSER SONNENSYSTEM, IHRE ENERGIEQUELLE.'
        WHERE id = 1""")
        conn.commit()

    # Fix old ae/oe/ue in product template descriptions
    templates = conn.execute("SELECT id, title, description FROM product_templates").fetchall()
    for t in templates:
        title = t['title'] or ''
        desc = t['description'] or ''
        if any(old in desc for old in ['fuer', 'hoechst', 'zustaendig', 'Enthaelt', 'Kapazitaet', 'waehlbar', 'abschliess']):
            new_desc = desc
            replacements = [
                ('Fuer', 'Für'), ('fuer', 'für'),
                ('hoechsten', 'höchsten'), ('zustaendigen', 'zuständigen'),
                ('Enthaelt', 'Enthält'), ('Kapazitaet', 'Kapazität'),
                ('waehlbar', 'wählbar'), ('abschliessender', 'abschließender'),
            ]
            for old, new in replacements:
                new_desc = new_desc.replace(old, new)
            if new_desc != desc:
                conn.execute("UPDATE product_templates SET description = ? WHERE id = ?", (new_desc, t['id']))
        new_title = title.replace('Anschluesse', 'Anschlüsse')
        if new_title != title:
            conn.execute("UPDATE product_templates SET title = ? WHERE id = ?", (new_title, t['id']))
    conn.commit()


def _seed_product_templates(conn):
    """Insert default product templates based on the carport/solar pricing.

    All carport prices are NETTO (brutto inkl. 20% MwSt / 1.20).
    Carport + Carport Installation = is_carport=1 (19% MwSt in DE).
    """
    # Tuple format: (category, title, description, default_quantity,
    #  title_1_slot, title_2_slot, title_3_plus_title,
    #  description_1_slot, description_2_slot, description_3_plus_desc,
    #  quantity_1_slot, quantity_2_slot, quantity_3_plus_qty,
    #  price_1_slot, price_2_slot, price_3_plus, is_carport, sort_order)
    templates = [
        # ===================== CARPORT-MODELLE =====================
        ('Carport', 'PV-Carport Modell S - Selbstmontagefreundlich',
         'Für hohe Schneelasten bis 2,6 kN/m2. Selbstmontagefreundlich.',
         '1x', '', '', '', '', '', '', '', '', '',
         2150.00, None, '', 1, 1),

        ('Carport', 'PV-Carport Modell S - inkl. 9 PV-Module',
         'Inkl. 9 PV-Module. Für Schneelast bis 2,6 kN/m2.',
         '1x', '', '', '', '', '', '', '', '', '',
         2975.00, None, '', 1, 2),

        ('Carport', 'PV-Carport Modell S2 - Selbstmontagefreundlich',
         'Für Schneelasten bis 1,6 kN/m2. Selbstmontagefreundlich.',
         '1x', '', '', '', '', '', '', '', '', '',
         None, 2541.67, '', 1, 3),

        ('Carport', 'PV-Carport Modell 01 - Modernes Carport',
         'Modernes Carport-Design.',
         '1x', '', '', '', '', '', '', '', '', '',
         3590.00, 4404.17, 'Preis auf Anfrage', 1, 4),

        ('Carport', 'PV-Carport Modell 02 - Stabil & Wetterfest',
         'Stabile und wetterfeste Konstruktion.',
         '1x', '', '', '', '', '', '', '', '', '',
         None, 3441.67, 'Preis auf Anfrage', 1, 5),

        ('Carport', 'PV-Carport Modell 03 - Stabile Carport-Struktur',
         'Stabile Carport-Struktur.',
         '1x', '', '', '', '', '', '', '', '', '',
         4025.00, None, '', 1, 6),

        ('Carport', 'PV-Carport Modell 04 - Robustes Einzelcarport',
         'Robustes Einzelcarport.',
         '1x', '', '', '', '', '', '', '', '', '',
         3536.67, None, '', 1, 7),

        ('Carport', 'PV-Carport Modell 05 - Robuste Konstruktion',
         'Robuste Konstruktion.',
         '1x', '', '', '', '', '', '', '', '', '',
         2420.00, 3508.33, 'Preis auf Anfrage', 1, 8),

        ('Carport', 'PV-Carport Modell 06 - Carport-Konstruktion',
         'Carport-Konstruktion.',
         '1x', '', '', '', '', '', '', '', '', '',
         2640.00, 3912.50, 'Preis auf Anfrage', 1, 9),

        ('Carport', 'PV-Carport 07 - Robustes Carport',
         'Robustes Carport.',
         '1x', '', '', '', '', '', '', '', '', '',
         2550.00, None, '', 1, 10),

        # ===================== INSTALLATION =====================
        ('Installation', 'Carport Installation',
         'Fachgerechte Montage der Carport Struktur inkl. stabiler Befestigung und abschließender Endabnahme.',
         '', '', '', '', '', '', '', '', '', '',
         1450.00, 1650.00, 'Preis auf Anfrage', 1, 20),

        ('Installation', 'Installation der PV-Anlage',
         'Professionelle Installation und Verschaltung der PV-Module nach höchsten Standards.',
         '', '', '', '', '', '', '', '', '', '',
         None, None, 'Preis auf Anfrage', 0, 21),

        ('Installation', 'Elektrische Anschlüsse und Inbetriebnahme',
         'Installation und Anschluss des Wechselrichters, des Batteriespeichers, '
         'der DC-AC-Leitung sowie des Potentialausgleichs und des PV-Abgangsverteilers. '
         'Dies beinhaltet auch die Inbetriebnahme der Anlage und die offizielle Meldung '
         'beim zuständigen Energieversorger.',
         '', '', '', '', '', '', '', '', '', '',
         None, None, 'Preis auf Anfrage', 0, 22),

        ('Installation', 'Montage und Anschlussarbeiten',
         'Professionelle Installation und Verschaltung der PV-Module nach höchsten Standards, '
         'sodass sie optimal für den weiteren elektrischen Anschluss vorbereitet sind.',
         '', '', '', '', '', '', '', '', '', '',
         None, None, 'Preis auf Anfrage', 0, 23),

        # ===================== KOMPONENTEN =====================
        ('Komponenten', 'PV-Module',
         'Solarmodule für Carport-Dach.',
         '', '', '', '', '', '', '',
         '9x', '15x', '24x',
         990.00, 1450.00, 'Preis auf Anfrage', 0, 30),

        # Wechselrichter: slot-specific titles & descriptions
        ('Komponenten', 'Wechselrichter',
         'Hybrid-Wechselrichter mit intelligenter Energiesteuerung und Batteriespeicher-Kompatibilität.',
         '1x',
         'GoodWe GW6.5KN-ET PLUS+ Hybrid-Wechselrichter',
         'GoodWe GW8KN-ET PLUS+ Hybrid Wechselrichter',
         '',
         'Effizienter Hybrid-Wechselrichter mit intelligenter Energiesteuerung und Batteriespeicher-Kompatibilität für maximale Eigenverbrauchsoptimierung.',
         'Notstromfähig, lüfterlos und geräuscharm ausgestattet mit zwei MPP-Trackern (2 MPPT).',
         '',
         '', '', '',
         1085.00, 1211.00, 'Preis auf Anfrage', 0, 31),

        # Batteriespeicher: 3 separate options (same price for all slots)
        ('Komponenten', 'Pylontech Force H2 Batteriespeicher 7,1kWh',
         'Modularer Hochvolt-Batteriespeicher mit 7,1 kWh Kapazität, stapelbarem Design und über 5.000 Ladezyklen für eine langlebige Eigenverbrauchsoptimierung.',
         '1x', '', '', '', '', '', '', '', '', '',
         2950.00, 2950.00, '', 0, 32),

        ('Komponenten', 'Pylontech Force H2 Batteriespeicher 10,65kWh',
         'LiFePO\u2084-Hochvolt-Speicher, IP55, >5000 Zyklen, 95 % DoD.',
         '1x', '', '', '', '', '', '', '', '', '',
         3458.00, 3458.00, '', 0, 33),

        ('Komponenten', 'Huawei LUNA2000-10-S0 Batterie - 10kWh Speicherpaket',
         'Hochvolt-Batteriespeicher mit 10 kWh Kapazität.',
         '1x', '', '', '', '', '', '', '', '', '',
         4050.00, 4050.00, '', 0, 34),

        ('Komponenten', 'Elektromaterialien inkl. PV Abgangsverteiler',
         'Enthält: MC4-Stecker, Solarkabel, Rohr, Befestigungsmaterial sowie Komponenten '
         'für den PV-Abgangsverteiler (Fehlerstromschutzschalter, Leitungsschutzschalter, '
         'Verdrahtungsmaterial).',
         '', '', '', '', '', '', '', '', '', '',
         None, None, 'Preis auf Anfrage', 0, 35),

        # ===================== LIEFERUNG =====================
        ('Lieferung', 'Lieferung der angebotenen Positionen',
         'Transport und Anlieferung der im Angebot enthaltenen Komponenten per Spedition / '
         'auf Palette bis zur Bordsteinkante.',
         '', '', '', '', '', '', '', '', '', '',
         None, None, '', 0, 40),
    ]
    for t in templates:
        conn.execute('''
            INSERT INTO product_templates (category, title, description, default_quantity,
                title_1_slot, title_2_slot, title_3_plus_title,
                description_1_slot, description_2_slot, description_3_plus_desc,
                quantity_1_slot, quantity_2_slot, quantity_3_plus_qty,
                price_1_slot, price_2_slot, price_3_plus, is_carport, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', t)
    conn.commit()


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
            customer_uid, project_name, project_description, creator_name, notes, custom_terms,
            created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['quote_number'], data['date'], data['valid_until'], data['country'],
        data['customer_name'], data.get('customer_company', ''),
        data.get('customer_street', ''), data.get('customer_zip', ''),
        data.get('customer_city', ''), data.get('customer_country_label', ''),
        data.get('customer_phone', ''), data.get('customer_email', ''),
        data.get('customer_uid', ''),
        data.get('project_name', ''), data.get('project_description', ''),
        data.get('creator_name', ''), data.get('notes', ''),
        data.get('custom_terms', ''), now, now
    ))
    quote_id = cursor.lastrowid

    for i, item in enumerate(items):
        conn.execute('''
            INSERT INTO quote_items (quote_id, position, title, description, quantity, total_price, is_carport, is_optional)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            quote_id, i + 1, item.get('title', ''),
            item.get('description', ''),
            item.get('quantity', '1x'),
            float(item.get('total_price', 0) or 0),
            int(item.get('is_carport', 0)),
            int(item.get('is_optional', 0))
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
            customer_uid=?, project_name=?, project_description=?, creator_name=?, notes=?, custom_terms=?,
            updated_at=?
        WHERE id=?
    ''', (
        data['date'], data['valid_until'], data['country'],
        data['customer_name'], data.get('customer_company', ''),
        data.get('customer_street', ''), data.get('customer_zip', ''),
        data.get('customer_city', ''), data.get('customer_country_label', ''),
        data.get('customer_phone', ''), data.get('customer_email', ''),
        data.get('customer_uid', ''),
        data.get('project_name', ''), data.get('project_description', ''),
        data.get('creator_name', ''), data.get('notes', ''),
        data.get('custom_terms', ''), now, quote_id
    ))

    # Replace items
    conn.execute("DELETE FROM quote_items WHERE quote_id = ?", (quote_id,))
    for i, item in enumerate(items):
        conn.execute('''
            INSERT INTO quote_items (quote_id, position, title, description, quantity, total_price, is_carport, is_optional)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            quote_id, i + 1, item.get('title', ''),
            item.get('description', ''),
            item.get('quantity', '1x'),
            float(item.get('total_price', 0) or 0),
            int(item.get('is_carport', 0)),
            int(item.get('is_optional', 0))
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
        is_optional = int(item.get('is_optional', 0) or 0)

        if country == 'AT':
            vat_rate = 20.0
        elif country == 'DE':
            vat_rate = 19.0 if item.get('is_carport') else 0.0
        else:
            vat_rate = 0.0

        vat_amount = price * (vat_rate / 100)

        # Optionale Positionen nicht in Summe zählen
        if not is_optional:
            netto += price

        item_details.append({
            **item,
            'vat_rate': vat_rate,
            'vat_amount': vat_amount if not is_optional else 0,
        })

    vat_total = sum(i['vat_amount'] for i in item_details)

    return {
        'positions': item_details,
        'netto': netto,
        'vat_total': vat_total,
        'brutto': netto + vat_total,
    }


# --- Product Templates ---

def get_all_product_templates():
    conn = get_db()
    rows = conn.execute("SELECT * FROM product_templates ORDER BY sort_order, id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product_template(template_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM product_templates WHERE id = ?", (template_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_product_template(data):
    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO product_templates (category, title, description, default_quantity,
            title_1_slot, title_2_slot, title_3_plus_title,
            description_1_slot, description_2_slot, description_3_plus_desc,
            quantity_1_slot, quantity_2_slot, quantity_3_plus_qty,
            price_1_slot, price_2_slot, price_3_plus, is_carport, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('category', ''),
        data.get('title', ''),
        data.get('description', ''),
        data.get('default_quantity', '1x'),
        data.get('title_1_slot', ''),
        data.get('title_2_slot', ''),
        data.get('title_3_plus_title', ''),
        data.get('description_1_slot', ''),
        data.get('description_2_slot', ''),
        data.get('description_3_plus_desc', ''),
        data.get('quantity_1_slot', ''),
        data.get('quantity_2_slot', ''),
        data.get('quantity_3_plus_qty', ''),
        float(data['price_1_slot']) if data.get('price_1_slot') else None,
        float(data['price_2_slot']) if data.get('price_2_slot') else None,
        data.get('price_3_plus', ''),
        int(data.get('is_carport', 0)),
        int(data.get('sort_order', 0)),
    ))
    conn.commit()
    tid = cursor.lastrowid
    conn.close()
    return tid


def update_product_template(template_id, data):
    conn = get_db()
    conn.execute('''
        UPDATE product_templates SET category=?, title=?, description=?, default_quantity=?,
            title_1_slot=?, title_2_slot=?, title_3_plus_title=?,
            description_1_slot=?, description_2_slot=?, description_3_plus_desc=?,
            quantity_1_slot=?, quantity_2_slot=?, quantity_3_plus_qty=?,
            price_1_slot=?, price_2_slot=?, price_3_plus=?, is_carport=?, sort_order=?
        WHERE id=?
    ''', (
        data.get('category', ''),
        data.get('title', ''),
        data.get('description', ''),
        data.get('default_quantity', '1x'),
        data.get('title_1_slot', ''),
        data.get('title_2_slot', ''),
        data.get('title_3_plus_title', ''),
        data.get('description_1_slot', ''),
        data.get('description_2_slot', ''),
        data.get('description_3_plus_desc', ''),
        data.get('quantity_1_slot', ''),
        data.get('quantity_2_slot', ''),
        data.get('quantity_3_plus_qty', ''),
        float(data['price_1_slot']) if data.get('price_1_slot') else None,
        float(data['price_2_slot']) if data.get('price_2_slot') else None,
        data.get('price_3_plus', ''),
        int(data.get('is_carport', 0)),
        int(data.get('sort_order', 0)),
        template_id,
    ))
    conn.commit()
    conn.close()


def delete_product_template(template_id):
    conn = get_db()
    conn.execute("DELETE FROM product_templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()
