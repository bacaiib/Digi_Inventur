from io import BytesIO
from datetime import date

from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth

from firma_db import fetch_artikel_lager, STANDORTE, filtere_gruppen_fuer_standort


def inventur_pdf_view(request):
    # Standort über URL-Parameter wählen: ?site=A oder ?site=B
    site = request.GET.get("site", "A")
    cfg = STANDORTE.get(site, STANDORTE["A"])
    standort_label = cfg["label"]

    count, anzahl_wg, unique_wg, gruppen = fetch_artikel_lager()

    # Standort-spezifisch Gruppen rausfiltern
    unique_wg, gruppen = filtere_gruppen_fuer_standort(unique_wg, gruppen, cfg["skip_groups"])
    anzahl_wg = len(unique_wg)

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

    def fit_cell(text, col_width_pt):
        usable = max(1, col_width_pt - 2 * CELL_PAD_X)
        return truncate_to_width(text, usable, BODY_FONT, BODY_SIZE)

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

    story = []

    # --- Tabellen bauen: eine Tabelle pro Gruppe ---
    for gruppen_name in unique_wg:
        artikel_liste = gruppen.get(gruppen_name, [])
        if not artikel_liste:
            continue

        table_data = [header]

        for art in artikel_liste:
            row = [
                fit_cell(art.get("ART_NR"), col_widths[0]),
                fit_cell(art.get("HERST_NAME"), col_widths[1]),
                fit_cell(art.get("HERST_ART_NR"), col_widths[2]),
                fit_cell(art.get("ART_NAME"), col_widths[3]),
                "", "", "", "",
            ]
            table_data.append(row)

        # --- Leerzeilen für händische Ergänzungen ---
        EXTRA_EMPTY_ROWS = 10

        empty_row = [""] * len(header)
        for _ in range(EXTRA_EMPTY_ROWS):
            table_data.append(empty_row)

        t = Table(
            table_data,
            colWidths=col_widths,
            repeatRows=1  # Header wird auf jeder Seite wiederholt
        )

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
    footer_rechts = standort_label

    def on_page(canvas, doc_):
        canvas.saveState()

        # Header links
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(doc_.leftMargin, page_height - 30, titel_links)

        canvas.setFont("Helvetica", 9)
        canvas.drawString(doc_.leftMargin, page_height - 45, datum_links)

        # Footer rechts
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(page_width - doc_.rightMargin, 18, footer_rechts)

        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="inventur.pdf"'
    response.write(pdf)
    return response