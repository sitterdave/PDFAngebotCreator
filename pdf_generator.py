"""
PDF Generator that matches the Stromsparen24 quote layout:
- Logo/brand top area
- Two-column: Empfänger (left) / Ersteller (right)
- Angebotsdetails section
- Items table with blue header (Pos | Beschreibung | Menge | Gesamtkosten)
- Totals box (Summe netto, MwSt, Summe brutto)
- Footer with company legal info, UID, bank details
- Page 2: Terms and conditions with signature line
"""

import os
import locale
from fpdf import FPDF
from models import calculate_quote_totals, get_company_settings

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

# Blue accent color matching the brand
BLUE = (25, 118, 210)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
WHITE = (255, 255, 255)
LIGHT_GRAY = (240, 240, 240)


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

        # Try to load DejaVu fonts for Unicode, fallback to Helvetica
        font_dir = os.path.join(os.path.dirname(__file__), 'static', 'fonts')
        dejavu = os.path.join(font_dir, 'DejaVuSans.ttf')
        dejavu_bold = os.path.join(font_dir, 'DejaVuSans-Bold.ttf')
        dejavu_italic = os.path.join(font_dir, 'DejaVuSans-Oblique.ttf')
        dejavu_bi = os.path.join(font_dir, 'DejaVuSans-BoldOblique.ttf')

        if os.path.exists(dejavu):
            self.add_font('DejaVu', '', dejavu, uni=True)
            self.add_font('DejaVu', 'B', dejavu_bold if os.path.exists(dejavu_bold) else dejavu, uni=True)
            self.add_font('DejaVu', 'I', dejavu_italic if os.path.exists(dejavu_italic) else dejavu, uni=True)
            self.add_font('DejaVu', 'BI', dejavu_bi if os.path.exists(dejavu_bi) else dejavu, uni=True)
            self.f = 'DejaVu'
        else:
            self.f = 'Helvetica'

    def header(self):
        # --- Logo / Brand area ---
        logo = self.company.get('logo_path', '')
        if logo:
            full_path = os.path.join(STATIC_DIR, 'uploads', logo)
            if os.path.exists(full_path):
                self.image(full_path, x=10, y=8, h=20)

        # Brand slogan (if no logo, show brand name)
        brand = self.company.get('brand_slogan', '') or self.company.get('brand_name', '')
        if brand and not logo:
            self.set_font(self.f, 'B', 14)
            self.set_text_color(*BLUE)
            self.set_xy(10, 10)
            self.cell(100, 8, brand, ln=False)

        # Contact info top-right (email, website)
        email = self.company.get('company_email', '')
        website = self.company.get('company_website', '')
        if email or website:
            self.set_font(self.f, '', 8)
            self.set_text_color(0, 102, 204)  # Blue for links
            y_pos = 10
            if email:
                self.set_xy(140, y_pos)
                self.cell(60, 4, email, align='R', ln=True)
                y_pos += 5
            if website:
                self.set_xy(140, y_pos)
                self.cell(60, 4, website, align='R', ln=True)

        self.set_y(35)

    def footer(self):
        self.set_y(-25)
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

        self.set_font(self.f, '', 6.5)
        self.set_text_color(*GRAY)

        y = self.get_y()

        # Column 1: Company legal info
        self.set_xy(10, y)
        name = self.company.get('company_name', '')
        if name:
            self.cell(60, 3.2, f"Firmenname: {name}", ln=True)
            self.set_x(10)
        gericht = self.company.get('gerichtsstandort', '')
        if gericht:
            self.cell(60, 3.2, f"Gerichtsstandort: {gericht}", ln=True)
            self.set_x(10)
        street = self.company.get('company_street', '')
        plz = self.company.get('company_zip', '')
        city = self.company.get('company_city', '')
        if street or plz or city:
            addr = f"Adresse:{plz} {city}, {street}".strip(', ')
            self.cell(60, 3.2, addr, ln=True)

        # Column 2: Tax info
        self.set_xy(80, y)
        ust = self.company.get('company_ust_id', '')
        if ust:
            self.cell(55, 3.2, f"UID: {ust}", ln=True)
            self.set_x(80)
        fb = self.company.get('firmenbuchnummer', '')
        if fb:
            self.cell(55, 3.2, f"Firmenbuchnummer: {fb}", ln=True)

        # Column 3: Bank details
        self.set_xy(145, y)
        bank = self.company.get('bank_name', '')
        if bank:
            self.cell(55, 3.2, f"Bank:  {bank}", align='L', ln=True)
            self.set_x(145)
        iban = self.company.get('iban', '')
        if iban:
            self.cell(55, 3.2, f"IBAN:  {iban}", align='L', ln=True)
            self.set_x(145)
        bic = self.company.get('bic', '')
        if bic:
            self.cell(55, 3.2, f"BIC:   {bic}", align='L', ln=True)

        # Page number bottom-right
        self.set_xy(170, -8)
        self.set_font(self.f, '', 7)
        self.cell(30, 4, f"Seite {self.page_no()} / {{nb}}", align='R')


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
    pdf.set_font(f, 'B', 22)
    pdf.set_text_color(*BLACK)
    pdf.cell(0, 12, 'Angebot', ln=True)
    pdf.ln(4)

    # --- Two-column: Empfänger / Ersteller ---
    y_block = pdf.get_y()

    # Left: Empfänger
    pdf.set_font(f, 'B', 10)
    pdf.set_text_color(*BLACK)
    pdf.cell(90, 5, 'Empfänger', ln=True)
    pdf.set_font(f, '', 9)
    pdf.ln(1)

    if quote.get('customer_company'):
        pdf.cell(90, 5, quote['customer_company'], ln=True)
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
    pdf.set_xy(110, y_block)
    pdf.set_font(f, 'B', 10)
    pdf.cell(80, 5, 'Ersteller', ln=True)
    pdf.set_x(110)
    pdf.set_font(f, '', 9)
    pdf.ln(1)

    creator = quote.get('creator_name', '')
    if creator:
        pdf.set_x(110)
        pdf.cell(80, 5, creator, ln=True)
    cname = company.get('company_name', '')
    if cname:
        pdf.set_x(110)
        pdf.cell(80, 5, cname, ln=True)
    cstreet = company.get('company_street', '')
    if cstreet:
        pdf.set_x(110)
        caddr = f"{company.get('company_zip', '')} {company.get('company_city', '')} {cstreet}".strip()
        pdf.cell(80, 5, caddr, ln=True)
    ccountry = company.get('company_country', '')
    if ccountry == 'AT':
        pdf.set_x(110)
        pdf.cell(80, 5, 'Österreich', ln=True)
    elif ccountry == 'DE':
        pdf.set_x(110)
        pdf.cell(80, 5, 'Deutschland', ln=True)
    ust = company.get('company_ust_id', '')
    if ust:
        pdf.set_x(110)
        pdf.cell(80, 5, f"UID: {ust}", ln=True)

    # Move Y to max of both columns
    pdf.set_y(max(empf_end_y, pdf.get_y()) + 8)

    # --- Angebotsdetails ---
    pdf.set_font(f, 'B', 10)
    pdf.set_text_color(*BLACK)
    pdf.cell(0, 5, 'Angebotsdetails', ln=True)
    pdf.ln(2)

    pdf.set_font(f, '', 9)
    label_w = 45
    val_w = 80

    # Angebotsnummer
    pdf.cell(label_w, 5, 'Angebotsnummer:', ln=False)
    pdf.cell(val_w, 5, quote.get('quote_number', ''), ln=True)

    # Angebotsdatum
    pdf.cell(label_w, 5, 'Angebotsdatum:', ln=False)
    pdf.cell(val_w, 5, format_date_german(quote.get('date', '')), ln=True)

    # Angebotsersteller
    if creator:
        pdf.cell(label_w, 5, 'Name Angebotsersteller:', ln=False)
        pdf.cell(val_w, 5, creator, ln=True)

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

        pdf.set_font(f, 'B', 11)
        pdf.set_text_color(*BLACK)
        pdf.cell(0, 7, 'Zusätzliche Angebotsinformationen:', ln=True)
        pdf.ln(4)

        pdf.set_font(f, '', 9)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(0, 5, terms)

        pdf.ln(8)

        # Signature area
        pdf.set_font(f, 'B', 9)
        pdf.cell(0, 6, 'Zur Annahme des Angebots bitte unterschreiben und zurücksenden.', ln=True)
        pdf.ln(12)

        pdf.set_font(f, '', 9)
        # Signature line
        y_sig = pdf.get_y()
        pdf.cell(80, 5, 'Unterschrift: _________________________', ln=False)
        pdf.set_x(130)
        pdf.cell(60, 5, 'Datum: _______________', ln=True)

    return pdf.output()


def _draw_items_table(pdf, totals, country):
    """Draw the items table matching the example layout."""
    f = pdf.f

    # Column widths: Pos | Beschreibung | Menge | Gesamtkosten [EUR]
    col_pos = 20
    col_desc = 85
    col_menge = 30
    col_total = 35
    table_w = col_pos + col_desc + col_menge + col_total

    x_start = 15
    headers = ['Pos', 'Beschreibung', 'Menge', 'Gesamtkosten\n[EUR]']

    # Table header with blue background
    pdf.set_fill_color(*BLUE)
    pdf.set_text_color(*WHITE)
    pdf.set_font(f, 'B', 8)
    pdf.set_draw_color(*BLUE)

    hx = x_start
    pdf.set_x(hx)
    pdf.cell(col_pos, 10, 'Pos', border=1, align='C', fill=True)
    pdf.cell(col_desc, 10, 'Beschreibung', border=1, align='C', fill=True)
    pdf.cell(col_menge, 10, 'Menge', border=1, align='C', fill=True)
    # Multi-line header for Gesamtkosten
    gk_x = pdf.get_x()
    gk_y = pdf.get_y()
    pdf.cell(col_total, 10, '', border=1, fill=True)
    # Center "Gesamtkosten" and "[EUR]" in the cell
    pdf.set_xy(gk_x, gk_y + 1)
    pdf.cell(col_total, 4, 'Gesamtkosten', align='C')
    pdf.set_xy(gk_x, gk_y + 5.5)
    pdf.cell(col_total, 4, '[EUR]', align='C')

    pdf.set_y(gk_y + 10)

    # Table rows
    pdf.set_text_color(*BLACK)
    pdf.set_draw_color(180, 180, 180)

    for item in totals['positions']:
        title = item.get('title', '')
        desc = item.get('description', '')
        quantity = item.get('quantity', '1x')
        price = float(item.get('total_price', 0) or 0)

        # Calculate needed height for description
        # Title is bold, description is regular
        combined_text = title
        if desc:
            combined_text += '\n' + desc

        # Estimate height needed
        pdf.set_font(f, 'B', 9)
        title_lines = pdf.multi_cell(col_desc - 4, 5, title, dry_run=True, output='LINES') if title else []
        pdf.set_font(f, '', 8)
        desc_lines = pdf.multi_cell(col_desc - 4, 4.5, desc, dry_run=True, output='LINES') if desc else []

        title_h = len(title_lines) * 5 if title_lines else 0
        desc_h = len(desc_lines) * 4.5 if desc_lines else 0
        content_h = title_h + desc_h + 4  # padding
        row_h = max(content_h, 18)  # minimum row height

        # Check page break
        if pdf.get_y() + row_h > pdf.h - 35:
            pdf.add_page()
            # Redraw header
            pdf.set_fill_color(*BLUE)
            pdf.set_text_color(*WHITE)
            pdf.set_font(f, 'B', 8)
            pdf.set_draw_color(*BLUE)
            pdf.set_x(x_start)
            pdf.cell(col_pos, 10, 'Pos', border=1, align='C', fill=True)
            pdf.cell(col_desc, 10, 'Beschreibung', border=1, align='C', fill=True)
            pdf.cell(col_menge, 10, 'Menge', border=1, align='C', fill=True)
            gk_x2 = pdf.get_x()
            gk_y2 = pdf.get_y()
            pdf.cell(col_total, 10, '', border=1, fill=True)
            pdf.set_xy(gk_x2, gk_y2 + 1)
            pdf.cell(col_total, 4, 'Gesamtkosten', align='C')
            pdf.set_xy(gk_x2, gk_y2 + 5.5)
            pdf.cell(col_total, 4, '[EUR]', align='C')
            pdf.set_y(gk_y2 + 10)
            pdf.set_text_color(*BLACK)
            pdf.set_draw_color(180, 180, 180)

        row_y = pdf.get_y()

        # Draw row borders
        pdf.set_draw_color(180, 180, 180)
        pdf.rect(x_start, row_y, col_pos, row_h)
        pdf.rect(x_start + col_pos, row_y, col_desc, row_h)
        pdf.rect(x_start + col_pos + col_desc, row_y, col_menge, row_h)
        pdf.rect(x_start + col_pos + col_desc + col_menge, row_y, col_total, row_h)

        # Pos number (centered vertically)
        pdf.set_font(f, '', 9)
        pos_y = row_y + (row_h / 2) - 2.5
        pdf.set_xy(x_start, pos_y)
        pdf.cell(col_pos, 5, str(item['position']), align='C')

        # Description: title (bold) + description (regular)
        desc_x = x_start + col_pos + 2
        desc_y = row_y + 2
        pdf.set_xy(desc_x, desc_y)

        if title:
            pdf.set_font(f, 'B', 9)
            pdf.multi_cell(col_desc - 4, 5, title)
        if desc:
            pdf.set_font(f, '', 8)
            pdf.set_x(desc_x)
            pdf.multi_cell(col_desc - 4, 4.5, desc)

        # Menge (centered vertically)
        pdf.set_font(f, '', 9)
        pdf.set_xy(x_start + col_pos + col_desc, pos_y)
        pdf.cell(col_menge, 5, str(quantity), align='C')

        # Gesamtkosten (centered vertically)
        pdf.set_xy(x_start + col_pos + col_desc + col_menge, pos_y)
        pdf.cell(col_total, 5, fmt(price), align='R')

        pdf.set_y(row_y + row_h)


def _draw_totals_box(pdf, totals, country):
    """Draw the totals summary box on the right side."""
    f = pdf.f

    box_x = 110
    label_w = 45
    val_w = 35

    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.3)

    y_start = pdf.get_y() + 2

    # Summe netto [EUR]
    pdf.set_xy(box_x, y_start)
    pdf.set_font(f, 'B', 9)
    pdf.set_text_color(*BLACK)
    pdf.cell(label_w, 6, 'Summe netto', border='TB', align='L')
    pdf.cell(val_w, 6, fmt(totals['netto']), border='TB', align='R')
    pdf.ln()

    # [EUR] label row
    pdf.set_xy(box_x, pdf.get_y())
    pdf.set_font(f, '', 8)
    pdf.cell(label_w, 5, '[EUR]', border=0, align='L')
    pdf.cell(val_w, 5, '', border=0)
    pdf.ln()

    # MwSt line(s)
    if country == 'AT':
        pdf.set_xy(box_x, pdf.get_y())
        pdf.set_font(f, '', 9)
        pdf.cell(label_w, 6, '20 % MwSt.', border=0, align='L')
        pdf.cell(val_w, 6, fmt(totals['vat_total']), border=0, align='R')
        pdf.ln()
    elif country == 'DE':
        vat_19 = sum(i['vat_amount'] for i in totals['positions'] if i['vat_rate'] == 19.0)
        netto_0 = sum(float(i.get('total_price', 0)) for i in totals['positions'] if i['vat_rate'] == 0.0)
        if vat_19 > 0:
            pdf.set_xy(box_x, pdf.get_y())
            pdf.set_font(f, '', 9)
            pdf.cell(label_w, 6, '19 % MwSt. (Carport)', border=0, align='L')
            pdf.cell(val_w, 6, fmt(vat_19), border=0, align='R')
            pdf.ln()
        if netto_0 > 0:
            pdf.set_xy(box_x, pdf.get_y())
            pdf.set_font(f, '', 9)
            pdf.cell(label_w, 6, '0 % MwSt. (Sonstiges)', border=0, align='L')
            pdf.cell(val_w, 6, '0,00', border=0, align='R')
            pdf.ln()

    # Summe brutto
    pdf.set_xy(box_x, pdf.get_y())
    pdf.set_font(f, 'B', 10)
    pdf.cell(label_w, 7, 'Summe brutto', border='TB', align='L')
    pdf.cell(val_w, 7, fmt(totals['brutto']), border='TB', align='R')
    pdf.ln()

    # [EUR] label
    pdf.set_xy(box_x, pdf.get_y())
    pdf.set_font(f, '', 8)
    pdf.cell(label_w, 5, '[EUR]', border=0, align='L')
