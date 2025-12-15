import pyodbc
import re
from collections import defaultdict

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=CORTEXSRV2\\CORTEX;"
    "DATABASE=THAMM_BN;"
    "UID=sharepoint;"
    "PWD=Thamm1234;"
    "TrustServerCertificate=yes;"
)

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

AUSLASSEN = {44, 6, 9, 110, 9992, 8123, 123, 634}

STANDORTE = {
    "A": {
        "label": "Thamm GmbH",
        "skip_groups": set(),  # nichts auslassen
    },
    "B": {
        "label": "Thamm Süd GmbH",
        "skip_groups": {"3D-Druck", "Truckframe txwall"},  # Beispiel
    },
}

def filtere_gruppen_fuer_standort(unique_wg, gruppen, skip_groups):
    """Filtert Gruppen nach Gruppennamen (z.B. '3D-Druck')."""
    skip_groups = set(skip_groups or [])
    unique_wg = [g for g in unique_wg if g not in skip_groups]
    gruppen = {g: gruppen[g] for g in unique_wg}
    return unique_wg, gruppen


def wg_num(k):
    m = re.search(r"\bWG\s*(\d+)\b", str(k))
    return int(m.group(1)) if m else 10**9


def gruppiere_artikel_nach_wg_nr(artikel_liste, uebergruppen, auslassen):
    wg_nr_to_ueber = {}
    for ueber_name, wg_nr_set in uebergruppen.items():
        for wg_nr in wg_nr_set:
            if wg_nr in wg_nr_to_ueber:
                print("WARN doppelte WG_NR:", wg_nr)
            wg_nr_to_ueber[wg_nr] = ueber_name

    gruppen = defaultdict(list)

    for art in artikel_liste:
        wg_nr = art.get("WG_NR")

        if wg_nr is None:
            continue
        if wg_nr in auslassen:
            continue

        ziel_gruppe = wg_nr_to_ueber.get(wg_nr, f"WG {wg_nr}")
        gruppen[ziel_gruppe].append(art)

    return dict(gruppen)


def fetch_artikel_lager():
    conn = pyodbc.connect(CONN_STR)
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
        WHERE Aktiv = 1 AND WOG_NR > 3
        ORDER BY WG_NR ASC, HERST_ART_NR ASC
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [c[0] for c in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    conn.close()

    gruppen = gruppiere_artikel_nach_wg_nr(
        artikel_liste=data,
        uebergruppen=UEBERGRUPPEN,
        auslassen=AUSLASSEN,
    )

    order = list(UEBERGRUPPEN.keys())
    rest = [k for k in gruppen.keys() if k not in UEBERGRUPPEN]
    unique_groups = [k for k in order if k in gruppen] + sorted(rest, key=wg_num)

    return len(rows), len(unique_groups), unique_groups, gruppen