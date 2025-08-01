# detect_subs.py
import pandas as pd
import numpy as np
import re
from datetime import datetime

# Nombre de las columnas en tu CSV/Excel
DATE_COL = "fecha_operacion"
CONCEPT_COL = "concepto"
AMOUNT_COL = "importe"

# Lista de palabras clave para identificar posibles suscripciones
SUBSCRIPTION_KEYWORDS = [
    # telecomunicaciones y servicios
    "digi", "digimobil", "telefonica", "orange", "vodafone", "jazztel", "simyo",
    "fibra", "internet", "movil", "movistar",
    # streaming y apps
    "netflix", "spotify", "prime", "amazon prime", "disney", "hbo", "youtube premium",
    "itunes", "app store", "google youtube", "paypal google youtube", "yt music",
    # otros servicios recurrentes
    "suscripcion", "suscripciones", "subscripci", "cuota",
    # alquiler, hipoteca
    "alquiler", "hipoteca",
    # electricidad, agua, gas
    "endesa", "iberdrola", "naturgy", "gas", "agua", "luz", "electricidad",
]

def detect_subscriptions(path: str) -> pd.DataFrame:
    """
    Carga tu extracto (CSV o Excel) y devuelve un DataFrame con
    las filas que parecen suscripciones mensuales recurrentes.
    """
    # 1) Leer el fichero
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path, sep=";", parse_dates=[DATE_COL], dayfirst=True, dtype=str)
    else:
        df = pd.read_excel(path, header=7, engine="openpyxl", parse_dates=[DATE_COL], dayfirst=True, dtype=str)

    # 2) Normalizar tipos
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], dayfirst=True, errors="coerce")
    df[AMOUNT_COL] = pd.to_numeric(df[AMOUNT_COL].str.replace(",", "."), errors="coerce")
    df[CONCEPT_COL] = df[CONCEPT_COL].str.lower().fillna("")

    # 3) Crear columna periodo mensual
    df["periodo"] = df[DATE_COL].dt.to_period("M")
    total_meses = df["periodo"].nunique()

    # 4) Filtrar por palabra clave y periodicidad
    subs = []
    for concepto, grupo in df.groupby(CONCEPT_COL):
        if any(kw in concepto for kw in SUBSCRIPTION_KEYWORDS):
            meses_distintos = grupo["periodo"].nunique()
            # criterio: aparece en casi todos los meses (>= total_meses -1)
            if meses_distintos >= max(3, total_meses - 1):
                fecha_primera = grupo[DATE_COL].min()
                subs.append({
                    "Suscripción": concepto,
                    "Importe (€)": round(grupo[AMOUNT_COL].mean(), 2),
                    "Desde": fecha_primera,
                    "Veces detectadas": meses_distintos
                })

    return pd.DataFrame(subs)


if __name__ == "__main__":
    import sys
    fichero = sys.argv[1] if len(sys.argv) > 1 else "export2025730.csv"
    df_subs = detect_subscriptions(fichero)
    if df_subs.empty:
        print("No se detectaron suscripciones mensuales recurrentes.")
    else:
        print("Suscripciones mensuales detectadas:")
        print(df_subs.to_string(index=False))
