import pyodbc
import re
from collections import defaultdict


# ============================================================
# Datenbank-Verbindung
# ============================================================

# Zentrale Connection-String-Definition.
# später evtl. über ENV-Variablen lösen.
CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=CORTEXSRV2\\CORTEX;"
    "DATABASE=THAMM_BN;"
    "UID=sharepoint;"
    "PWD=Thamm1234;"
    "TrustServerCertificate=yes;"
)


# ============================================================
# Fachliche Konfiguration
# ============================================================

# Zuordnung einzelner WG-Nummern zu übergeordneten Gruppen.
# Diese Struktur bildet die fachliche Logik der Inventur ab.
UEBERGRUPPEN = {
    "3D-Druck": {56, 59},
    "Displays": {36},
    "Drahtseile-Halter": {62, 63},
    "Druckfolien": {18, 78},
    "Laminate": {40},
    "Papier": {20},
    "Papier Filme nicht SK": {55},
    "Platten": {19, 77},
    "Plottfolien": {54},
    "POS-Zubehör": {61},
    "PVC-Rollenware": {8},
    "Standfüße Profile sont.": {42, 64},
    "Textil-Rollenware": {3, 75},
    "Truckframe txwall": {22, 57, 9, 21},
    "Verbrauchsmat. Druck": {28},
    "Verbrauchsmat. Klebebänder": {70},
    "Verbrauchsmat. Klett-Flauschbänder": {71},
    "Verbrauchsmat. Konfektion": {29},
    "Verbrauchsmat. Messer Fräsen": {72},
    "Verbrauchsmat. Metall": {31},
    "Verbrauchsmat. Montage": {33},
    "Verbrauchsmat. Tinten": {73},
    "Verbrauchsmat. Versand": {32},
    "Verbrauchsmat. Werbetechnik": {30},
    "Zubehör Metall": {34, 24},
}

# WG-Nummern, die grundsätzlich nicht inventarisiert werden
AUSGESCHLOSSENE_WG_NUMMERN = {25, 37, 80, 35, 41, 67, 60, 23, 65}


# Standort-spezifische Regeln
STANDORTE = {
    "A": {
        "label": "Thamm GmbH",
        "skip_groups": set(),
    },
    "B": {
        "label": "Thamm Süd GmbH",
        "skip_groups": {
            "3D-Druck",
            "Drahtseile-Halter",
            "POS-Zubehör",
            "Standfüße Profile sont.",
            "Truckframe txwall",
            "Verbrauchsmat. Metall",
            "Verbrauchsmat. Montage",
            "Zubehör Metall",
        },
    },
}


# ============================================================
# Hilfsfunktionen
# ============================================================

def gruppen_fuer_standort_filtern(gruppen_namen, gruppen_daten, auszuschliessende_gruppen):
    """
    Entfernt Gruppen, die für einen bestimmten Standort
    nicht relevant sind (z. B. Standort B).
    """
    skip = set(auszuschliessende_gruppen or [])

    gefilterte_namen = [g for g in gruppen_namen if g not in skip]
    gefilterte_daten = {g: gruppen_daten[g] for g in gefilterte_namen}

    return gefilterte_namen, gefilterte_daten


def wg_nummer_fuer_sortierung(gruppenname):
    """
    Extrahiert die WG-Nummer aus einem Gruppennamen wie 'WG 12'.
    Wird für eine saubere Sortierung der Restgruppen benötigt.
    """
    match = re.search(r"\bWG\s*(\d+)\b", str(gruppenname))
    return int(match.group(1)) if match else 10**9


# ============================================================
# Gruppierungslogik
# ============================================================

def artikel_nach_warengruppen_gruppieren(artikel_liste, uebergruppen, ausgeschlossene_wg):
    """
    Gruppiert Artikel anhand ihrer WG_NR in fachliche Warengruppen.
    """
    # Mapping: WG_NR -> Übergruppenname
    wg_zu_gruppe = {}

    for gruppenname, wg_set in uebergruppen.items():
        for wg_nr in wg_set:
            if wg_nr in wg_zu_gruppe:
                # Sollte eigentlich nicht passieren,
                # hilft aber beim Debuggen von Datenfehlern
                print("WARNUNG: doppelte WG_NR-Zuordnung:", wg_nr)

            wg_zu_gruppe[wg_nr] = gruppenname

    gruppen = defaultdict(list)

    for artikel in artikel_liste:
        wg_nr = artikel.get("WG_NR")

        # Ungültige oder explizit ausgeschlossene WG überspringen
        if wg_nr is None or wg_nr in ausgeschlossene_wg:
            continue

        zielgruppe = wg_zu_gruppe.get(wg_nr, f"WG {wg_nr}")
        gruppen[zielgruppe].append(artikel)

    return dict(gruppen)


# ============================================================
# Datenbank-Zugriff
# ============================================================

def artikel_lager_laden():
    """
    Lädt alle relevanten Artikel aus der Datenbank,
    gruppiert sie fachlich und liefert die Daten
    strukturiert für die PDF-Erstellung zurück.
    """
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    sql = """
        SELECT ART_NR,
               HERST_NAME,
               HERST_ART_NR,
               ART_NAME,
               WG_NR,
               WOG_NR,
               WG_NAME,
               EK,
               EINH,
               EINH_BEST,
               EINH_UMR,
               Lager
        FROM dbo.ART_STAMM_VW
        WHERE Aktiv = 1
          AND WOG_NR > 3
        ORDER BY WG_NR ASC, HERST_ART_NR ASC
    """

    cursor.execute(sql)
    rows = cursor.fetchall()

    spalten = [col[0] for col in cursor.description]
    daten = [dict(zip(spalten, row)) for row in rows]

    conn.close()

    # Artikel fachlich gruppieren
    gruppen = artikel_nach_warengruppen_gruppieren(
        artikel_liste=daten,
        uebergruppen=UEBERGRUPPEN,
        ausgeschlossene_wg=AUSGESCHLOSSENE_WG_NUMMERN,
    )

    # Reihenfolge:
    # 1. definierte Übergruppen
    # 2. restliche WG-Gruppen sortiert nach Nummer
    uebergruppen_reihenfolge = list(UEBERGRUPPEN.keys())
    restgruppen = [g for g in gruppen.keys() if g not in UEBERGRUPPEN]

    sortierte_gruppen = (
        [g for g in uebergruppen_reihenfolge if g in gruppen]
        + sorted(restgruppen, key=wg_nummer_fuer_sortierung)
    )

    return (
        len(rows),                 # Anzahl Artikel
        len(sortierte_gruppen),    # Anzahl Gruppen
        sortierte_gruppen,         # Gruppenreihenfolge
        gruppen,                   # Gruppierte Artikeldaten
    )
