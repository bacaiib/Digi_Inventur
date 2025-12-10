import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=CORTEXSRV2\\CORTEX;"
    "DATABASE=THAMM_BN;"
    "UID=sharepoint;"
    "PWD=Thamm1234;"
    "TrustServerCertificate=yes;"
)

def fetch_artikel_by_nr(art_nr):
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM dbo.ART_STAMM_VW
        WHERE ART_NR = ?
    """, (art_nr,))

    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()

    conn.close()

    if not row:
        return None

    # Row in Dict umwandeln
    result = {}
    for col, value in zip(columns, row):
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8")
            except:
                value = value.decode("latin1", errors="ignore")
        result[col] = value

    return result

def fetch_artikel_top10():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 2 * FROM dbo.ART_STAMM_VW")

    # Spaltennamen holen
    columns = [col[0] for col in cursor.description]

    result = []
    for row in cursor.fetchall():
        row_dict = {}
        for col_name, value in zip(columns, row):
            # Bytes in Strings umwandeln
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8")
                except:
                    value = value.decode("latin1", errors="ignore")
            row_dict[col_name] = value

        result.append(row_dict)

    conn.close()
    return result