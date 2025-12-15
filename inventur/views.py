from io import BytesIO
from datetime import date
from math import ceil

from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth

from firma_db import fetch_artikel_lager


def inventur_pdf_view(request):
    count, anzahl_wg, unique_wg, gruppen = fetch_artikel_lager()
    # gruppen ist: {gruppenname: [artikel...]}

    def clean(v):
        if v is None:
            return ""
        s = str(v).strip()
        if s.lower() == "none" or s == "-":
            return ""
        return s

    def truncate_to_width(text, max_width_pt, font_name="Helvetica", font_size=8):
        text = clean(text)
        if not text:
            return ""
        if stringWidth(text, font_name, font_size) <= max_width_pt:
            return text
        ell = "…"
        ell_w = stringWidth(ell, font_name, font_size)
        t = text
        while t and (stringWidth(t, font_name, font_size) + ell_w) > max_width_pt:
            t = t[:-1]
        return (t + ell) if t else ell

    BODY_FONT = "Helvetica"
    BODY_SIZE = 9
    CELL_PAD_X = 6

    def fit_cell(text, col_width_pt, font_name=BODY_FONT, font_size=BODY_SIZE, pad_x=CELL_PAD_X):
        usable = max(1, col_width_pt - 2 * pad_x)
        return truncate_to_width(text, usable, font_name, font_size)

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A3),
        leftMargin=20,
        rightMargin=20,
        topMargin=55,
        bottomMargin=35,
    )

    page_width, page_height = landscape(A3)

    header = [
        "Cortexnr.",
        "Hersteller",
        "Artikelnr. Hersteller",
        "Artikelnaam",
        "Verpackungseinheit",
        "Anzahl",
        "Einheit Rest (qm/lfm/Stk./usw.)",
        "Anzahl",
    ]

    col_widths = [55, 105, 102, 400, 105, 55, 155, 55]

    ROWS_PER_PAGE = 50
    pages_meta = []  # [(gruppenname, page_in_group, total_pages_in_group), ...]

    story = []

    # Wichtig: Reihenfolge der Gruppen so nehmen, wie unique_wg sortiert ist
    for gruppen_name in unique_wg:
        artikel_liste = gruppen.get(gruppen_name, [])
        if not artikel_liste:
            continue

        total_pages = ceil(len(artikel_liste) / ROWS_PER_PAGE)

        for p in range(total_pages):
            start = p * ROWS_PER_PAGE
            end = start + ROWS_PER_PAGE
            chunk = artikel_liste[start:end]

            pages_meta.append((gruppen_name, p + 1, total_pages))

            table_data = [header]
            for art in chunk:
                row = [
                    fit_cell(art.get("ART_NR"), col_widths[0]),
                    fit_cell(art.get("HERST_NAME"), col_widths[1]),
                    fit_cell(art.get("HERST_ART_NR"), col_widths[2]),
                    fit_cell(art.get("ART_NAME"), col_widths[3]),
                    "", "", "", "",
                ]
                table_data.append(row)

            t = Table(table_data, colWidths=col_widths, repeatRows=1)

            t.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTNAME", (0, 1), (-1, -1), BODY_FONT),
                ("FONTSIZE", (0, 1), (-1, -1), BODY_SIZE),

                ("LEFTPADDING", (0, 0), (-1, -1), CELL_PAD_X),
                ("RIGHTPADDING", (0, 0), (-1, -1), CELL_PAD_X),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),

                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ]))

            story.append(t)
            story.append(PageBreak())

    titel_links = "Thamm Inventur"
    datum_links = date.today().strftime("%d.%m.%Y")
    footer_rechts = "Thamm GmbH"

    def on_page(canvas, doc_):
        canvas.saveState()

        idx = doc_.page - 1
        gruppen_name = ""
        page_in_group = 0
        total_in_group = 0
        if 0 <= idx < len(pages_meta):
            gruppen_name, page_in_group, total_in_group = pages_meta[idx]

        # Header links
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(doc_.leftMargin, page_height - 30, titel_links)

        canvas.setFont("Helvetica", 9)
        canvas.drawString(doc_.leftMargin, page_height - 45, datum_links)

        # Header rechts: Gruppenname
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawRightString(page_width - doc_.rightMargin, page_height - 30, clean(gruppen_name))

        # Footer Mitte: x von y (pro Gruppe)
        canvas.setFont("Helvetica", 9)
        if total_in_group > 0:
            canvas.drawCentredString(page_width / 2, 18, f"{page_in_group} von {total_in_group}")

        # Footer rechts: Firma
        canvas.drawRightString(page_width - doc_.rightMargin, 18, footer_rechts)

        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="inventur.pdf"'
    response.write(pdf)
    return response