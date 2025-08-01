import pandas as pd
import re
from datetime import datetime
from typing import List

# ---------------------------------------------------
# Ajustes de columnas y palabras clave de suscripciones
# ---------------------------------------------------
DATE_COL = "FECHA OPERACIÓN"      # Nombre de la columna de fecha en tu extracto
CONCEPT_COL = "CONCEPTO"          # Nombre de la columna de concepto
AMOUNT_COL = "IMPORTE EUR"        # Nombre de la columna de importe
SUBSCRIPTION_KEYWORDS = [
    "digi", "movil", "telefonica", "fibra", "internet",
    "netflix", "youtube", "youtubepremium", "ytmusic", "spotify",
    "apple", "applecom", "dazn", "primevideo", "hbo", "disney",
    "suscripcion", "mensual"
]

# ------------------------------
# Lógica principal de detección
# ------------------------------
def detect_subscriptions(path: str) -> pd.DataFrame:
    """
    Lee el extracto (XLS/XLSX o CSV), busca cargos recurrentes mensuales
    que contengan alguna de las SUBSCRIPTION_KEYWORDS en el concepto,
    y devuelve un DataFrame con:
        - concepto
        - importe
        - primera fecha detectada
        - última fecha detectada
        - veces facturadas
    """
    # 1) Carga según extensión
    try:
        if path.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(path, header=7, engine="openpyxl", dtype=str)
        else:
            # CSV: inferimos delimitador como ';' o ','
            sep = ";" if pd.read_csv(path, nrows=3, sep=";").shape[1] > 3 else ","
            df = pd.read_csv(path, header=7, sep=sep, dtype=str)
    except Exception as e:
        raise RuntimeError(f"Error al leer el fichero: {e}")

    # 2) Normalizar nombres de columna
    df.columns = [c.strip().upper() for c in df.columns]
    if DATE_COL not in df.columns:
        raise RuntimeError(f"No encontré la columna de fecha '{DATE_COL}'. "
                           f"Columnas disponibles: {df.columns.tolist()}")
    if CONCEPT_COL not in df.columns:
        raise RuntimeError(f"No encontré la columna de concepto '{CONCEPT_COL}'.")
    if AMOUNT_COL not in df.columns:
        raise RuntimeError(f"No encontré la columna de importe '{AMOUNT_COL}'.")

    # 3) Filtrar solo cargos negativos (pagos)
    df = df[[DATE_COL, CONCEPT_COL, AMOUNT_COL]].copy()
    # Parseo fechas
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], dayfirst=True, errors="coerce")
    df = df.dropna(subset=[DATE_COL])
    # Convertir importe a float
    df[AMOUNT_COL] = df[AMOUNT_COL].str.replace(",", ".").astype(float)

    pagos = df[df[AMOUNT_COL] < 0].copy()
    pagos[CONCEPT_COL] = pagos[CONCEPT_COL].str.lower()

    # 4) Quedarse solo con conceptos que contengan keyword de suscripción
    pattern = re.compile("|".join(re.escape(k) for k in SUBSCRIPTION_KEYWORDS), re.IGNORECASE)
    pagos = pagos[pagos[CONCEPT_COL].str.contains(pattern)]
    if pagos.empty:
        return pd.DataFrame(columns=[CONCEPT_COL, AMOUNT_COL, "first_date", "last_date", "count"])

    # 5) Agrupar por concepto exacto y ver periodicidad mensual
    pagos["year_month"] = pagos[DATE_COL].dt.to_period("M")
    grouped = pagos.groupby(CONCEPT_COL)

    rows = []
    for concept, grp in grouped:
        months = grp["year_month"].unique()
        if len(months) < 2:
            continue  # no es realmente recurrente
        # Ordenar meses y ver que estén mayoritariamente cada ~30 días
        months = sorted(months)
        # Guardar summarize
        rows.append({
            CONCEPT_COL: concept,
            AMOUNT_COL: grp[AMOUNT_COL].iloc[0],
            "first_date": grp[DATE_COL].min().date(),
            "last_date": grp[DATE_COL].max().date(),
            "count": len(months),
        })

    result = pd.DataFrame(rows)
    # Marcar como "mensual" si al menos 3 meses distintos
    return result[result["count"] >= 3]


# -----------------------
# Ejecución standalone
# -----------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "export2025730.xls"  # cambia al nombre por defecto si lo deseas

    print("Detectando suscripciones en:", path)
    df_subs = detect_subscriptions(path)
    if df_subs.empty:
        print("No se detectaron suscripciones recurrentes.")
    else:
        print(df_subs.to_string(index=False))
