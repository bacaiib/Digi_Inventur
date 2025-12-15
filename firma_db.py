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
    "3D-Druck": {"Filament", "Zubehör aus 3D-Druck"},
    "Displays": {"Displays"},
    "Drahtseile-Halter": {"Drahtseile", "Drahtseilhalter"},
    "Druckfolien": {"Folien - Druck", "Folien - Magnetisch/Ferro"},
    "Laminate": {"Laminat"},
    "Papier": {"Papier"},
    "Papier Filme nicht SK": {"Filme nicht SK"},
    "Platten": {"Platten", "Platten Acryl"},
    "Plottfolien": {"Folien - Plott"},
    "POS-Zubehör": {"POS-Zubehör"},
    "PVC-Rollenware": {"PVC"},
    "Standfüße Ürofile sont.": {"Profile sonstige", "standfüße"},
    "Textil-Rollenware": {"Textilien dye-sub", "Textilien UV & sonstiges"},
    "Truckframe txwall": {"truckframe", "txtrail", "txframe", "txwall"},
    "Verbrauchsmat. Druck": {"Druck"},
    "Verbrauchsmat. Klebebänder": {"Klebebänder"},
    "Verbrauchsmat. Klett-Flauschbänder": {"Klett- & Flauschbänder"},
    "Verbrauchsmat. Konfektion": {"Konfektion"},
    "Verbrauchsmat. Messer Fräsen": {"Messer & Fräsen"},
    "Verbrauchsmat. Metall": {"Metall"},
    "Verbrauchsmat. Montage": {"Montage"},
    "Verbrauchsmat. Tinten": {"Tinten"},
    "Verbrauchsmat. Versand": {"Versand"},
    "Verbrauchsmat. Werbetechnik": {"Werbetechnik"},
    "Zubehör Metall": {"LED", "Zubehör"},
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


def norm_name(s) -> str:
    """Robust normalisieren (NBSP, Mehrfachspaces, Casefold)."""
    if s is None:
        return ""
    s = str(s).replace("\u00A0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s.casefold()


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

    # Reverse-Mapping: WG_NAME(normalisiert) -> Übergruppe
    wg_to_ueber = {}
    for ueber, wg_set in UEBERGRUPPEN.items():
        for wg in wg_set:
            key = norm_name(wg)
            if key in wg_to_ueber and wg_to_ueber[key] != ueber:
                # nur Warnung, damit du Doppelzuordnungen siehst
                print("WARN doppelt gemappt:", repr(wg), "->", wg_to_ueber[key], "und", ueber)
            wg_to_ueber[key] = ueber

    # Auslassen normalisiert
    auslassen_norm = {norm_name(x) for x in AUSLASSEN}

    # FINAL gruppieren: Zielname = Übergruppe ODER Original-WG (wenn nicht gemappt)
    final_gruppen = defaultdict(list)

    for zeile in data:
        wg_raw = zeile.get("WG_NAME") or ""
        wg_disp = str(wg_raw).replace("\u00A0", " ")
        wg_disp = re.sub(r"\s+", " ", wg_disp).strip()

        wg_key = norm_name(wg_disp)

        if wg_key in auslassen_norm:
            continue

        ziel = wg_to_ueber.get(wg_key, wg_disp)
        final_gruppen[ziel].append(zeile)

    # stabil sortierte Gruppenliste
    unique_groups = sorted(final_gruppen.keys(), key=norm_name)

    return len(rows), len(unique_groups), unique_groups, dict(final_gruppen)
