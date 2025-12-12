import pyodbc
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
    "3D-Druck": { "Filament", "Zubehör aus 3D-Druck" },
    "Displays": { "Displays" },
    "Drahtseile-Halter" : { "Drahtseile", "Drahtseilhalter" },
    "Druckfolien": { "Folien - Druck", "Folien - Magnetisch/Ferro" },
    "Laminate": { "Laminat" },
    "Papier": { "Papier" },
    "Papier Filme nicht SK": { "Filme nicht SK" },
    "Platten": { "Platten", "Platten Acryl" },
    "Plottfolien": { "Folien - Plott" },
    "POS-Zubehör": { "POS-Zubehör" },
    "PVC-Rollenware": { "PVC" },
    "Standfüße Ürofile sont.": { "Profile sonstige", "standfüße" },
    "Textil-Rollenware": { "Textilien dye-sub", "Textilien UV & sonstiges" },
    "Truckframe txwall": { "truckframe", "txtrail", "txframe", "txwall" },
    "Verbrauchsmat. Druck": { "Druck" },
    "Verbrauchsmat. Klebebänder": { "Klebebänder" },
    "Verbrauchsmat. Klett-Flauschbänder": { "Klett- & Flauschbänder" },
    "Verbrauchsmat. Konfektion": { "Konfektion" },
    "Verbrauchsmat. Messer Fräsen": { "Messer & Fräsen" },
    "Verbrauchsmat. Metall": { "Metall" },
    "Verbrauchsmat. Montage": { "Montage" },
    "Verbrauchsmat. Tinten": { "Tinten" },
    "Verbrauchsmat. Versand": { "Versand" },
    "Verbrauchsmat. Werbetechnik": { "Werbetechnik" },
    "Zubehör Metall": { "LED", "Zubehör" }
}

AUSLASSEN = {
    "Büro",
    "Dienstleistungen",
    "Druck Extern / Zukauf",
    "Konstruktionen",
    "Overhead",
    "Pulvern/Eloxieren/Bearbeitung",
    "Rohrrahmen",
    "skyframe",
    "Zubehör Kundenspezifisch",

}


def norm(s: str) -> str:
    return (s or "").strip().casefold()

def gruppen_zu_uebergruppen(gruppen: dict, UEBERGRUPPEN: dict, AUSLASSEN: set):
    # Auslassen
    gruppen = {k: v for k, v in gruppen.items() if k not in AUSLASSEN}

    # Reverse-Mapping: WG_NAME -> Übergruppe
    wg_to_ueber = {}
    for ueber, wg_set in UEBERGRUPPEN.items():
        for wg in wg_set:
            wg_to_ueber[wg] = ueber

    # Übergruppe -> [Artikel...]
    ueber_dict = defaultdict(list)

    for wg_name, artikel_liste in gruppen.items():
        ueber = wg_to_ueber.get(wg_name, "Sonstiges")
        ueber_dict[ueber].extend(artikel_liste)   # <- HIER: alles zusammenwerfen

    return dict(ueber_dict)

from collections import defaultdict

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
               EK,
               EINH,
               EINH_BEST,
               EINH_UMR,
               WG_NAME,
               Lager
        FROM dbo.ART_STAMM_VW
        WHERE Aktiv = 1 AND WOG_NR > 3
        ORDER BY WG_NAME ASC, HERST_ART_NR ASC
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [c[0] for c in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    conn.close()

    # 1) Gruppen (WG_NAME -> [Artikel...])
    gruppen = defaultdict(list)
    for zeile in data:
        gruppen[zeile["WG_NAME"]].append(zeile)

    # 2) Auslassen
    gruppen = {k: v for k, v in gruppen.items() if k not in AUSLASSEN}

    # 3) Reverse Mapping WG_NAME -> Übergruppe
    wg_to_ueber = {}
    for ueber, wg_set in UEBERGRUPPEN.items():
        for wg in wg_set:
            wg_to_ueber[wg] = ueber

    # 4) FLAT: Übergruppe -> [Artikel...]  (genau eine Tabelle pro Übergruppe)
    uebergruppen_flat = defaultdict(list)
    for wg_name, artikel_liste in gruppen.items():
        ueber = wg_to_ueber.get(wg_name, "Sonstiges")
        uebergruppen_flat[ueber].extend(artikel_liste)

    unique_wg = sorted(gruppen.keys())
    return len(rows), len(unique_wg), unique_wg, gruppen, dict(uebergruppen_flat)
