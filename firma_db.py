import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=CORTEXSRV2\\CORTEX;"
    "DATABASE=THAMM_BN;"
    "UID=sharepoint;"
    "PWD=Thamm1234;"
    "TrustServerCertificate=yes;"
)

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
        unique_wg = {row["WG_NAME"] for row in data}
        anzahl_wg = len(unique_wg)
        count = len(rows)
        return count, anzahl_wg, data