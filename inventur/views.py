from io import BytesIO
from datetime import date
from math import ceil
from dataclasses import dataclass

from django.http import HttpResponse

# ReportLab (Platypus) – direkte PDF-Erzeugung ohne HTML/CSS
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak, Spacer
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth

from firma_db import artikel_lager_laden, STANDORTE, gruppen_fuer_standort_filtern


# ============================================================
# PDF-Layout-Konfiguration
# ============================================================

@dataclass(frozen=True)
class PdfLayout:
    """
    Zentrale Sammlung aller Layout-Werte für die PDF.
    Änderungen am Drucklayout sollen nur hier passieren.
    """
    seitenformat: tuple = landscape(A3)

    rand_links: int = 20
    rand_rechts: int = 20
    rand_oben: int = 55
    rand_unten: int = 35

    kopfzeile_hoehe: int = 22
    tabellenzeile_hoehe: int = 18

    schriftart: str = "Helvetica"
    schriftgroesse: int = 9
    zellen_padding_x: int = 6

    # Zusätzliche Leerzeilen am Tabellenende (Platz zum Schreiben)
    extra_leerzeilen: int = 6

    # Kleine Reserve, damit Tabellen nicht über den Seitenrand laufen
    hoehen_reserve: int = 10


LAYOUT = PdfLayout()


# ============================================================
# Tabellenstruktur
# ============================================================

TABELLEN_KOPF = [
    "Cortexnr.",
    "Hersteller",
    "Artikelnr. Hersteller",
    "Artikelnaam",
    "Verpackungseinheit",
    "Anzahl",
    "Einheit Rest (qm/lfm/Stk./usw.)",
    "Anzahl",
]

# Spaltenbreiten in Punkt (ReportLab-Einheit)
SPALTEN_BREITEN = [55, 105, 105, 400, 107, 55, 157, 55]


# ============================================================
# Hilfsfunktionen
# ============================================================

def db_wert_bereinigen(wert) -> str:
    """
    Vereinheitlicht Werte aus der Datenbank:
    - None, 'None' oder '-' werden als leer dargestellt
    """
    if wert is None:
        return ""

    text = str(wert).strip()
    if not text or text.lower() == "none" or text == "-":
        return ""

    return text


def text_auf_spaltenbreite_kuerzen(text, max_breite_pt, schriftart, schriftgroesse) -> str:
    """
    Kürzt Text so, dass er sicher in die Spalte passt.
    Wichtig für den Druck, damit nichts in andere Spalten läuft.
    """
    text = db_wert_bereinigen(text)
    if not text:
        return ""

    if stringWidth(text, schriftart, schriftgroesse) <= max_breite_pt:
        return text

    auslassung = "…"
    auslassung_breite = stringWidth(auslassung, schriftart, schriftgroesse)

    gekuerzt = text
    while gekuerzt and (stringWidth(gekuerzt, schriftart, schriftgroesse) + auslassung_breite) > max_breite_pt:
        gekuerzt = gekuerzt[:-1]

    return gekuerzt + auslassung if gekuerzt else auslassung


def tabellenzelle_formatieren(text, spaltenbreite) -> str:
    """
    Formatiert eine einzelne Tabellenzelle inkl. Padding-Berechnung.
    """
    nutzbare_breite = max(1, spaltenbreite - 2 * LAYOUT.zellen_padding_x)

    return text_auf_spaltenbreite_kuerzen(
        text,
        nutzbare_breite,
        LAYOUT.schriftart,
        LAYOUT.schriftgroesse
    )


# ============================================================
# Seiten- & Tabellenlogik
# ============================================================

def zeilen_pro_seite_berechnen(seitenhoehe, doc) -> int:
    """
    Berechnet, wie viele Tabellenzeilen realistisch auf eine Seite passen.
    Muss dynamisch sein, da Seitenränder variieren können.
    """
    nutzbare_hoehe = (
        seitenhoehe
        - doc.topMargin
        - doc.bottomMargin
        - LAYOUT.hoehen_reserve
    )

    return max(
        1,
        int((nutzbare_hoehe - LAYOUT.kopfzeile_hoehe) // LAYOUT.tabellenzeile_hoehe)
    )


def seitenanzahl_fuer_gruppe_berechnen(artikel_anzahl, zeilen_pro_seite) -> int:
    """
    Ermittelt die benötigte Seitenanzahl pro Warengruppe.
    Zusätzliche Leerzeilen werden bewusst mitgerechnet.
    """
    return max(
        1,
        ceil((artikel_anzahl + LAYOUT.extra_leerzeilen) / zeilen_pro_seite)
    )


# ============================================================
# Tabellen-Erzeugung
# ============================================================

def gruppen_uebersichtstabelle_erstellen(titel, gruppennamen, gruppen_daten, zeilen_pro_seite, tabellenbreite):
    """
    Baut die Übersichtstabelle auf dem Deckblatt,
    die zeigt, wie viele Seiten jede Warengruppe hat.
    """
    daten = [[titel, "Seiten", "", ""]]

    for gruppenname in gruppennamen:
        artikel_anzahl = len(gruppen_daten.get(gruppenname, []))
        seiten = seitenanzahl_fuer_gruppe_berechnen(artikel_anzahl, zeilen_pro_seite)
        daten.append([gruppenname, str(seiten), "", ""])

    spalte_seiten = 30
    spalte_checkbox = 16
    spalte_name = max(120, tabellenbreite - spalte_seiten - 2 * spalte_checkbox)

    tabelle = Table(
        daten,
        colWidths=[spalte_name, spalte_seiten, spalte_checkbox, spalte_checkbox],
        repeatRows=1
    )

    checkbox_stile = []
    for zeile in range(1, len(daten)):
        checkbox_stile.append(("BOX", (2, zeile), (2, zeile), 0.8, colors.black))
        checkbox_stile.append(("BOX", (3, zeile), (3, zeile), 0.8, colors.black))

    tabelle.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),

        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (3, -1), "CENTER"),

        ("LINEBELOW", (0, 0), (-1, 0), 1.2, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ] + checkbox_stile))

    return tabelle


def inventur_tabelle_fuer_seite_erstellen(artikel_zeilen):
    """
    Erstellt die eigentliche Inventurtabelle für eine PDF-Seite.
    """
    daten = [TABELLEN_KOPF]

    for artikel in artikel_zeilen:
        daten.append([
            tabellenzelle_formatieren(artikel.get("ART_NR") if artikel else "", SPALTEN_BREITEN[0]),
            tabellenzelle_formatieren(artikel.get("HERST_NAME") if artikel else "", SPALTEN_BREITEN[1]),
            tabellenzelle_formatieren(artikel.get("HERST_ART_NR") if artikel else "", SPALTEN_BREITEN[2]),
            tabellenzelle_formatieren(artikel.get("ART_NAME") if artikel else "", SPALTEN_BREITEN[3]),
            "", "", "", "",
        ])

    zeilenhoehen = (
        [LAYOUT.kopfzeile_hoehe] +
        [LAYOUT.tabellenzeile_hoehe] * (len(daten) - 1)
    )

    tabelle = Table(
        daten,
        colWidths=SPALTEN_BREITEN,
        rowHeights=zeilenhoehen,
        repeatRows=1
    )

    tabelle.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),

        ("ALIGN", (5, 0), (5, 0), "CENTER"),
        ("ALIGN", (7, 0), (7, 0), "CENTER"),

        ("FONTNAME", (0, 1), (-1, -1), LAYOUT.schriftart),
        ("FONTSIZE", (0, 1), (-1, -1), LAYOUT.schriftgroesse),

        ("LEFTPADDING", (0, 0), (-1, -1), LAYOUT.zellen_padding_x),
        ("RIGHTPADDING", (0, 0), (-1, -1), LAYOUT.zellen_padding_x),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),

        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
    ]))

    return tabelle


# ============================================================
# Django View
# ============================================================

def inventur_pdf_view(request):
    """
    Django-View:
    Erstellt die Inventur-PDF serverseitig
    und liefert sie direkt an den Browser aus.
    """

    # Standort aus URL (?site=A oder ?site=B)
    site = request.GET.get("site", "A")
    standort_cfg = STANDORTE.get(site, STANDORTE["A"])
    standort_label = standort_cfg["label"]

    _, _, gruppen_namen, gruppen = artikel_lager_laden()

    # Standortabhängige Gruppen ausfiltern
    gruppen_namen, gruppen = gruppen_fuer_standort_filtern(
        gruppen_namen,
        gruppen,
        standort_cfg["skip_groups"]
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LAYOUT.seitenformat,
        leftMargin=LAYOUT.rand_links,
        rightMargin=LAYOUT.rand_rechts,
        topMargin=LAYOUT.rand_oben,
        bottomMargin=LAYOUT.rand_unten,
    )

    seitenbreite, seitenhoehe = LAYOUT.seitenformat
    zeilen_pro_seite = zeilen_pro_seite_berechnen(seitenhoehe, doc)

    story = []
    seiten_meta = []  # (Gruppenname, Seite_in_Gruppe, Seiten_gesamt)

    # ================= Deckblatt =================

    gruppen_A, daten_A = gruppen_fuer_standort_filtern(
        gruppen_namen, gruppen, STANDORTE["A"]["skip_groups"]
    )
    gruppen_B, daten_B = gruppen_fuer_standort_filtern(
        gruppen_namen, gruppen, STANDORTE["B"]["skip_groups"]
    )

    halbe_breite = (seitenbreite - doc.leftMargin - doc.rightMargin) / 2 - 10

    t_links = gruppen_uebersichtstabelle_erstellen(
        STANDORTE["A"]["label"], gruppen_A, daten_A, zeilen_pro_seite, halbe_breite
    )
    t_rechts = gruppen_uebersichtstabelle_erstellen(
        STANDORTE["B"]["label"], gruppen_B, daten_B, zeilen_pro_seite, halbe_breite
    )

    deckblatt = Table([[t_links, t_rechts]],
        colWidths=[(seitenbreite - doc.leftMargin - doc.rightMargin) / 2] * 2
    )

    deckblatt.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))

    story.append(Spacer(1, 6))

    titel = Table(
        [["Inventurlisten 2025"]],
        colWidths=[seitenbreite - doc.leftMargin - doc.rightMargin]
    )
    titel.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LINEBELOW", (0, 0), (-1, -1), 1.2, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.extend([titel, Spacer(1, 10), deckblatt, PageBreak()])

    # ================= Inventur-Tabellen =================

    for gruppenname in gruppen_namen:
        artikel_liste = sorted(
            gruppen.get(gruppenname, []),
            key=lambda a: (a.get("ART_NAME") or "").lower()
        )
        if not artikel_liste:
            continue

        artikel_liste_ext = list(artikel_liste) + ([{}] * LAYOUT.extra_leerzeilen)
        gesamt_seiten = ceil(len(artikel_liste_ext) / zeilen_pro_seite)

        for seite in range(gesamt_seiten):
            start = seite * zeilen_pro_seite
            ende = start + zeilen_pro_seite
            seiten_daten = artikel_liste_ext[start:ende]

            seiten_meta.append((gruppenname, seite + 1, gesamt_seiten))

            story.append(inventur_tabelle_fuer_seite_erstellen(seiten_daten))
            story.append(PageBreak())

    # ================= Kopf- & Fußzeile =================

    titel_links = "Thamm Inventur"
    datum_text = "17.12.2025"
    fuss_rechts = standort_label

    def kopf_und_fuss_zeichnen(canvas, doc_):
        canvas.saveState()

        gruppenname = ""
        seite_in_gruppe = 0
        gesamt_in_gruppe = 0

        # Erste Seite = Deckblatt
        if doc_.page >= 2:
            idx = doc_.page - 2
            if 0 <= idx < len(seiten_meta):
                gruppenname, seite_in_gruppe, gesamt_in_gruppe = seiten_meta[idx]

        # Kopf links
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(doc_.leftMargin, seitenhoehe - 30, titel_links)

        canvas.setFont("Helvetica", 9)
        canvas.drawString(doc_.leftMargin, seitenhoehe - 45, datum_text)

        # Kopf rechts (Gruppenname)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawRightString(
            seitenbreite - doc_.rightMargin,
            seitenhoehe - 30,
            db_wert_bereinigen(gruppenname)
        )

        # Fuß Mitte (Seitennummer pro Gruppe)
        if gesamt_in_gruppe:
            canvas.drawCentredString(
                seitenbreite / 2,
                18,
                f"{seite_in_gruppe} von {gesamt_in_gruppe}"
            )

        # Fuß rechts (Standort)
        canvas.drawRightString(
            seitenbreite - doc_.rightMargin,
            18,
            fuss_rechts
        )

        # Fuß links (Unterschrift)
        canvas.drawString(doc_.leftMargin, 12, "Ausgefüllt von:")
        canvas.line(doc_.leftMargin + 85, 10, doc_.leftMargin + 240, 10)

        canvas.restoreState()

    doc.build(story, onFirstPage=kopf_und_fuss_zeichnen, onLaterPages=kopf_und_fuss_zeichnen)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="inventur.pdf"'
    response.write(pdf)
    return response
