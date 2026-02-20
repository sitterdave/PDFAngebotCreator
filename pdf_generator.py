"""
PDF Generator for Stromsparen24 quotes.
Professional layout with Verdana font, brand colors, and clean structure.
"""

import os
from fpdf import FPDF
from models import calculate_quote_totals, get_company_settings

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

# Brand colors
BLUE = (51, 147, 198)
DARK_BLUE = (30, 100, 150)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
LIGHT_GRAY_TEXT = (120, 120, 120)
WHITE = (255, 255, 255)
ROW_ALT = (245, 249, 252)  # Light blue-gray for alternating rows


def fmt(value):
    """Format number as German currency: 1.234,56"""
    s = f"{value:,.2f}"
    s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    return s


def format_date_german(date_str):
    """Convert YYYY-MM-DD to 'DD. Monat YYYY' German format."""
    if not date_str:
        return ''
    months = {
        '01': 'Jänner', '02': 'Februar', '03': 'März', '04': 'April',
        '05': 'Mai', '06': 'Juni', '07': 'Juli', '08': 'August',
        '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Dezember'
    }
    try:
        parts = date_str.split('-')
        day = parts[2].lstrip('0')
        month = months.get(parts[1], parts[1])
        return f"{day}. {month} {parts[0]}"
    except (IndexError, ValueError):
        return date_str


class QuotePDF(FPDF):

    def __init__(self, company):
        super().__init__()
        self.company = company
        self.set_auto_page_break(auto=True, margin=30)

        # Try to load Verdana, fallback to DejaVu, then Helvetica
        font_dir = os.path.join(os.path.dirname(__file__), 'static', 'fonts')

        verdana = os.path.join(font_dir, 'Verdana.ttf')
        verdana_bold = os.path.join(font_dir, 'Verdana-Bold.ttf')
        verdana_italic = os.path.join(font_dir, 'Verdana-Italic.ttf')
        verdana_bi = os.path.join(font_dir, 'Verdana-BoldItalic.ttf')

        dejavu = os.path.join(font_dir, 'DejaVuSans.ttf')
        dejavu_bold = os.path.join(font_dir, 'DejaVuSans-Bold.ttf')
        dejavu_italic = os.path.join(font_dir, 'DejaVuSans-Oblique.ttf')
        dejavu_bi = os.path.join(font_dir, 'DejaVuSans-BoldOblique.ttf')

        if os.path.exists(verdana):
            self.add_font('Verdana', '', verdana, uni=True)
            self.add_font('Verdana', 'B', verdana_bold if os.path.exists(verdana_bold) else verdana, uni=True)
            self.add_font('Verdana', 'I', verdana_italic if os.path.exists(verdana_italic) else verdana, uni=True)
            self.add_font('Verdana', 'BI', verdana_bi if os.path.exists(verdana_bi) else verdana, uni=True)
            self.f = 'Verdana'
        elif os.path.exists(dejavu):
            self.add_font('DejaVu', '', dejavu, uni=True)
            self.add_font('DejaVu', 'B', dejavu_bold if os.path.exists(dejavu_bold) else dejavu, uni=True)
            self.add_font('DejaVu', 'I', dejavu_italic if os.path.exists(dejavu_italic) else dejavu, uni=True)
            self.add_font('DejaVu', 'BI', dejavu_bi if os.path.exists(dejavu_bi) else dejavu, uni=True)
            self.f = 'DejaVu'
        else:
            self.f = 'Helvetica'

    def header(self):
        # --- Logo ---
        logo = self.company.get('logo_path', '')
        if logo:
            full_path = os.path.join(STATIC_DIR, 'uploads', logo)
            if os.path.exists(full_path):
                self.image(full_path, x=10, y=5, h=42)

        # Brand name fallback (if no logo)
        brand = self.company.get('brand_slogan', '') or self.company.get('brand_name', '')
        if brand and not logo:
            self.set_font(self.f, 'B', 14)
            self.set_text_color(*BLUE)
            self.set_xy(10, 12)
            self.cell(100, 8, brand, ln=False)

        # Contact info top-right
        email = self.company.get('company_email', '')
        website = self.company.get('company_website', '')
        phone = self.company.get('company_phone', '')
        if email or website or phone:
            self.set_font(self.f, '', 8)
            self.set_text_color(*LIGHT_GRAY_TEXT)
            y_pos = 10
            if phone:
                self.set_xy(140, y_pos)
                self.cell(60, 4, phone, align='R', ln=True)
                y_pos += 4.5
            if email:
                self.set_text_color(*BLUE)
                self.set_xy(140, y_pos)
                self.cell(60, 4, email, align='R', ln=True)
                y_pos += 4.5
            if website:
                self.set_text_color(*BLUE)
                self.set_xy(140, y_pos)
                self.cell(60, 4, website, align='R', ln=True)

        # Blue accent line under header
        self.set_draw_color(*BLUE)
        self.set_line_width(0.8)
        self.line(10, 39, 200, 39)

        self.set_y(43)

    def footer(self):
        self.set_y(-25)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

        self.set_font(self.f, '', 6.5)
        self.set_text_color(*GRAY)

        y = self.get_y()

        # Column 1: Company legal info
        self.set_xy(10, y)
        name = self.company.get('company_name', '')
        if name:
            self.cell(60, 3.2, name, ln=True)
            self.set_x(10)
        street = self.company.get('company_street', '')
        plz = self.company.get('company_zip', '')
        city = self.company.get('company_city', '')
        if street or plz or city:
            addr = f"{street}, {plz} {city}".strip(', ')
            self.cell(60, 3.2, addr, ln=True)
            self.set_x(10)
        gericht = self.company.get('gerichtsstandort', '')
        if gericht:
            self.cell(60, 3.2, f"Gericht: {gericht}", ln=True)

        # Column 2: Tax info
        self.set_xy(80, y)
        ust = self.company.get('company_ust_id', '')
        if ust:
            self.cell(55, 3.2, f"UID: {ust}", ln=True)
            self.set_x(80)
        fb = self.company.get('firmenbuchnummer', '')
        if fb:
            self.cell(55, 3.2, f"FN: {fb}", ln=True)

        # Column 3: Bank details
        self.set_xy(145, y)
        bank = self.company.get('bank_name', '')
        if bank:
            self.cell(55, 3.2, f"Bank: {bank}", align='L', ln=True)
            self.set_x(145)
        iban = self.company.get('iban', '')
        if iban:
            self.cell(55, 3.2, f"IBAN: {iban}", align='L', ln=True)
            self.set_x(145)
        bic = self.company.get('bic', '')
        if bic:
            self.cell(55, 3.2, f"BIC: {bic}", align='L', ln=True)

        # Page number
        self.set_xy(170, -8)
        self.set_font(self.f, '', 7)
        self.set_text_color(*LIGHT_GRAY_TEXT)
        self.cell(30, 4, f"Seite {self.page_no()} / {{nb}}", align='R')


def _draw_section_header(pdf, text):
    """Draw a styled section header with blue accent."""
    f = pdf.f
    pdf.set_font(f, 'B', 10)
    pdf.set_text_color(*BLUE)
    pdf.cell(0, 6, text, ln=True)
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)


def generate_quote_pdf(quote, items):
    company = get_company_settings()
    totals = calculate_quote_totals(items, quote['country'])

    pdf = QuotePDF(company)
    pdf.alias_nb_pages()
    pdf.add_page()
    f = pdf.f

    # =====================================================
    # PAGE 1: Quote content
    # =====================================================

    # --- Title "Angebot" ---
    pdf.set_font(f, 'B', 20)
    pdf.set_text_color(*BLUE)
    pdf.cell(0, 10, 'Angebot', ln=True)
    pdf.ln(6)

    # --- Two-column: Empfänger / Ersteller ---
    y_block = pdf.get_y()

    # Left: Empfänger
    _draw_section_header(pdf, 'Empfänger')
    pdf.set_font(f, '', 9)
    pdf.set_text_color(*BLACK)

    if quote.get('customer_company'):
        pdf.set_font(f, 'B', 9)
        pdf.cell(90, 5, quote['customer_company'], ln=True)
        pdf.set_font(f, '', 9)
    if quote.get('customer_name'):
        pdf.cell(90, 5, quote['customer_name'], ln=True)
    if quote.get('customer_street'):
        pdf.cell(90, 5, quote['customer_street'], ln=True)
    zip_city = f"{quote.get('customer_zip', '')} {quote.get('customer_city', '')}".strip()
    if zip_city:
        pdf.cell(90, 5, zip_city, ln=True)
    country_label = quote.get('customer_country_label', '')
    if country_label:
        pdf.cell(90, 5, country_label, ln=True)

    empf_end_y = pdf.get_y()

    # Right: Ersteller
    pdf.set_xy(115, y_block)
    pdf.set_font(f, 'B', 10)
    pdf.set_text_color(*BLUE)
    pdf.cell(75, 6, 'Ersteller', ln=True)
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(0.4)
    pdf.line(115, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font(f, '', 9)
    pdf.set_text_color(*BLACK)

    creator = quote.get('creator_name', '')
    if creator:
        pdf.set_x(115)
        pdf.set_font(f, 'B', 9)
        pdf.cell(75, 5, creator, ln=True)
        pdf.set_font(f, '', 9)
    cname = company.get('company_name', '')
    if cname:
        pdf.set_x(115)
        pdf.cell(75, 5, cname, ln=True)
    cstreet = company.get('company_street', '')
    if cstreet:
        pdf.set_x(115)
        pdf.cell(75, 5, cstreet, ln=True)
    czip = company.get('company_zip', '')
    ccity = company.get('company_city', '')
    if czip or ccity:
        pdf.set_x(115)
        pdf.cell(75, 5, f"{czip} {ccity}".strip(), ln=True)
    ccountry = company.get('company_country', '')
    if ccountry == 'AT':
        pdf.set_x(115)
        pdf.cell(75, 5, 'Österreich', ln=True)
    elif ccountry == 'DE':
        pdf.set_x(115)
        pdf.cell(75, 5, 'Deutschland', ln=True)
    ust = company.get('company_ust_id', '')
    if ust:
        pdf.set_x(115)
        pdf.set_font(f, '', 8)
        pdf.set_text_color(*GRAY)
        pdf.cell(75, 5, f"UID: {ust}", ln=True)

    # Move Y to max of both columns
    pdf.set_y(max(empf_end_y, pdf.get_y()) + 8)

    # --- Angebotsdetails ---
    _draw_section_header(pdf, 'Angebotsdetails')
    pdf.set_font(f, '', 9)
    pdf.set_text_color(*BLACK)

    label_w = 48
    val_w = 80

    # Angebotsnummer
    pdf.set_font(f, '', 8)
    pdf.set_text_color(*GRAY)
    pdf.cell(label_w, 5.5, 'Angebotsnummer:', ln=False)
    pdf.set_font(f, 'B', 9)
    pdf.set_text_color(*BLACK)
    pdf.cell(val_w, 5.5, quote.get('quote_number', ''), ln=True)

    # Angebotsdatum
    pdf.set_font(f, '', 8)
    pdf.set_text_color(*GRAY)
    pdf.cell(label_w, 5.5, 'Angebotsdatum:', ln=False)
    pdf.set_font(f, '', 9)
    pdf.set_text_color(*BLACK)
    pdf.cell(val_w, 5.5, format_date_german(quote.get('date', '')), ln=True)

    # Gültig bis
    valid_until = quote.get('valid_until', '')
    if valid_until:
        pdf.set_font(f, '', 8)
        pdf.set_text_color(*GRAY)
        pdf.cell(label_w, 5.5, 'Gültig bis:', ln=False)
        pdf.set_font(f, '', 9)
        pdf.set_text_color(*BLACK)
        pdf.cell(val_w, 5.5, format_date_german(valid_until), ln=True)

    # Angebotsersteller
    if creator:
        pdf.set_font(f, '', 8)
        pdf.set_text_color(*GRAY)
        pdf.cell(label_w, 5.5, 'Angebotsersteller:', ln=False)
        pdf.set_font(f, '', 9)
        pdf.set_text_color(*BLACK)
        pdf.cell(val_w, 5.5, creator, ln=True)

    pdf.ln(6)

    # --- Items table ---
    _draw_items_table(pdf, totals, quote['country'])

    # --- Totals box ---
    pdf.ln(4)
    _draw_totals_box(pdf, totals, quote['country'])

    # =====================================================
    # PAGE 2: Terms and conditions
    # =====================================================
    terms = quote.get('custom_terms', '') or company.get('terms_text', '')
    if terms:
        pdf.add_page()

        _draw_section_header(pdf, 'Zusätzliche Angebotsinformationen')
        pdf.ln(2)

        pdf.set_font(f, '', 9)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(0, 5, terms, align='L')

        pdf.ln(12)

        # Signature area
        pdf.set_font(f, 'B', 9)
        pdf.set_text_color(*BLACK)
        pdf.cell(0, 6, 'Zur Annahme des Angebots bitte unterschreiben und zurücksenden.', ln=True)
        pdf.ln(15)

        # Signature lines
        pdf.set_draw_color(180, 180, 180)
        pdf.set_line_width(0.3)

        sig_y = pdf.get_y()
        pdf.line(15, sig_y, 90, sig_y)
        pdf.line(120, sig_y, 190, sig_y)

        pdf.set_font(f, '', 8)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(15, sig_y + 1)
        pdf.cell(75, 4, 'Unterschrift', align='L')
        pdf.set_xy(120, sig_y + 1)
        pdf.cell(70, 4, 'Datum', align='L')

    return pdf.output()


def _draw_table_header(pdf, x_start, col_pos, col_desc, col_menge, col_total):
    """Draw the blue table header row."""
    f = pdf.f
    pdf.set_fill_color(*BLUE)
    pdf.set_text_color(*WHITE)
    pdf.set_font(f, 'B', 8)
    pdf.set_draw_color(*BLUE)

    pdf.set_x(x_start)
    pdf.cell(col_pos, 10, 'Pos', border=1, align='C', fill=True)
    pdf.cell(col_desc, 10, 'Beschreibung', border=1, align='C', fill=True)
    pdf.cell(col_menge, 10, 'Menge', border=1, align='C', fill=True)

    gk_x = pdf.get_x()
    gk_y = pdf.get_y()
    pdf.cell(col_total, 10, '', border=1, fill=True)
    pdf.set_xy(gk_x, gk_y + 1)
    pdf.cell(col_total, 4, 'Gesamtkosten', align='C')
    pdf.set_xy(gk_x, gk_y + 5.5)
    pdf.cell(col_total, 4, '(\u20ac)', align='C')

    pdf.set_y(gk_y + 10)
    pdf.set_text_color(*BLACK)
    pdf.set_draw_color(200, 200, 200)


def _draw_items_table(pdf, totals, country):
    """Draw the items table with alternating row colors."""
    f = pdf.f

    col_pos = 15
    col_desc = 90
    col_menge = 25
    col_total = 40
    x_start = 15

    # Draw header
    _draw_table_header(pdf, x_start, col_pos, col_desc, col_menge, col_total)

    row_idx = 0
    for item in totals['positions']:
        title = item.get('title', '')
        desc = item.get('description', '')
        quantity = item.get('quantity', '1x')
        price = float(item.get('total_price', 0) or 0)

        # Estimate height needed
        pdf.set_font(f, 'B', 9)
        title_lines = pdf.multi_cell(col_desc - 4, 5, title, align='L', dry_run=True, output='LINES') if title else []
        pdf.set_font(f, '', 8)
        desc_lines = pdf.multi_cell(col_desc - 4, 4.5, desc, align='L', dry_run=True, output='LINES') if desc else []

        title_h = len(title_lines) * 5 if title_lines else 0
        desc_h = len(desc_lines) * 4.5 if desc_lines else 0
        content_h = title_h + desc_h + 4
        row_h = max(content_h, 16)

        # Check page break
        if pdf.get_y() + row_h > pdf.h - 35:
            pdf.add_page()
            _draw_table_header(pdf, x_start, col_pos, col_desc, col_menge, col_total)

        row_y = pdf.get_y()

        # Alternating row background
        if row_idx % 2 == 1:
            pdf.set_fill_color(*ROW_ALT)
            pdf.rect(x_start, row_y, col_pos + col_desc + col_menge + col_total, row_h, 'F')

        # Draw cell borders (light gray)
        pdf.set_draw_color(210, 210, 210)
        pdf.set_line_width(0.2)
        # Only horizontal lines (top/bottom of row) for a cleaner look
        line_end = x_start + col_pos + col_desc + col_menge + col_total
        pdf.line(x_start, row_y, line_end, row_y)
        pdf.line(x_start, row_y + row_h, line_end, row_y + row_h)
        # Vertical separators
        pdf.line(x_start, row_y, x_start, row_y + row_h)
        x_sep = x_start + col_pos
        pdf.line(x_sep, row_y, x_sep, row_y + row_h)
        x_sep += col_desc
        pdf.line(x_sep, row_y, x_sep, row_y + row_h)
        x_sep += col_menge
        pdf.line(x_sep, row_y, x_sep, row_y + row_h)
        pdf.line(line_end, row_y, line_end, row_y + row_h)

        # Pos number (centered vertically)
        pdf.set_font(f, 'B', 9)
        pdf.set_text_color(*BLUE)
        pos_y = row_y + (row_h / 2) - 2.5
        pdf.set_xy(x_start, pos_y)
        pdf.cell(col_pos, 5, str(item['position']), align='C')

        # Description: title (bold) + description (regular)
        desc_x = x_start + col_pos + 2
        desc_y = row_y + 2
        pdf.set_xy(desc_x, desc_y)

        if title:
            pdf.set_font(f, 'B', 9)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(col_desc - 4, 5, title, align='L')
        if desc:
            pdf.set_font(f, '', 7.5)
            pdf.set_text_color(*GRAY)
            pdf.set_x(desc_x)
            pdf.multi_cell(col_desc - 4, 4, desc, align='L')

        # Menge (centered vertically)
        pdf.set_font(f, '', 9)
        pdf.set_text_color(*BLACK)
        pdf.set_xy(x_start + col_pos + col_desc, pos_y)
        pdf.cell(col_menge, 5, str(quantity), align='C')

        # Gesamtkosten (centered vertically, right-aligned)
        pdf.set_font(f, 'B', 9)
        pdf.set_text_color(*BLACK)
        pdf.set_xy(x_start + col_pos + col_desc + col_menge, pos_y)
        pdf.cell(col_total - 3, 5, fmt(price) + ' \u20ac', align='R')

        pdf.set_y(row_y + row_h)
        row_idx += 1


def _draw_totals_box(pdf, totals, country):
    """Draw the totals summary box on the right side."""
    f = pdf.f

    box_x = 115
    label_w = 45
    val_w = 40
    total_w = label_w + val_w

    pdf.set_line_width(0.3)

    y_start = pdf.get_y() + 4

    # Summe netto
    pdf.set_xy(box_x, y_start)
    pdf.set_font(f, '', 9)
    pdf.set_text_color(*GRAY)
    pdf.cell(label_w, 7, 'Summe netto', border=0, align='L')
    pdf.set_text_color(*BLACK)
    pdf.cell(val_w, 7, fmt(totals['netto']) + ' \u20ac', border=0, align='R')
    pdf.ln()

    # Separator
    pdf.set_draw_color(210, 210, 210)
    pdf.line(box_x, pdf.get_y(), box_x + total_w, pdf.get_y())

    # MwSt line(s)
    if country == 'AT':
        pdf.set_xy(box_x, pdf.get_y())
        pdf.set_font(f, '', 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(label_w, 7, '20 % MwSt.', border=0, align='L')
        pdf.set_text_color(*BLACK)
        pdf.cell(val_w, 7, fmt(totals['vat_total']) + ' \u20ac', border=0, align='R')
        pdf.ln()
    elif country == 'DE':
        vat_19 = sum(i['vat_amount'] for i in totals['positions'] if i['vat_rate'] == 19.0)
        netto_0 = sum(float(i.get('total_price', 0)) for i in totals['positions'] if i['vat_rate'] == 0.0)
        if vat_19 > 0:
            pdf.set_xy(box_x, pdf.get_y())
            pdf.set_font(f, '', 9)
            pdf.set_text_color(*GRAY)
            pdf.cell(label_w, 7, '19 % MwSt. (Carport)', border=0, align='L')
            pdf.set_text_color(*BLACK)
            pdf.cell(val_w, 7, fmt(vat_19) + ' \u20ac', border=0, align='R')
            pdf.ln()
        if netto_0 > 0:
            pdf.set_xy(box_x, pdf.get_y())
            pdf.set_font(f, '', 9)
            pdf.set_text_color(*GRAY)
            pdf.cell(label_w, 7, '0 % MwSt. (Sonstiges)', border=0, align='L')
            pdf.set_text_color(*BLACK)
            pdf.cell(val_w, 7, '0,00 \u20ac', border=0, align='R')
            pdf.ln()

    # Summe brutto - highlighted
    pdf.set_xy(box_x, pdf.get_y() + 1)
    pdf.set_fill_color(*BLUE)
    pdf.set_text_color(*WHITE)
    pdf.set_font(f, 'B', 10)
    pdf.cell(label_w, 9, '  Summe brutto', border=0, align='L', fill=True)
    pdf.cell(val_w, 9, fmt(totals['brutto']) + ' \u20ac  ', border=0, align='R', fill=True)
