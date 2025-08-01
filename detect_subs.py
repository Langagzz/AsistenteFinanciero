import pandas as pd
import numpy as np
from datetime import datetime

# Nombre de las columnas en tu extracto
DATE_COL      = "fecha_operacion"
CONCEPT_COL   = "concepto"
AMOUNT_COL    = "importe"

# Lista de palabras clave para identificar posibles suscripciones
SUBSCRIPTION_KEYWORDS = [
    "digi", "digimobil", "telefonica", "orange", "vodafone", "jazztel", "simyo",
    "fibra", "internet", "movil", "movistar",
    "netflix", "spotify", "amazon prime", "disney", "hbo", "youtube premium",
    "itunes", "app store", "google youtube", "yt music",
    "suscripcion", "cuota",
    "alquiler", "hipoteca",
    "endesa", "iberdrola", "naturgy", "luz", "agua", "gas", "electricidad",
]

def detect_subscriptions(path: str) -> pd.DataFrame:
    """
    Detecta cargos mensuales en el extracto.
    Lee CSV o Excel (con cabecera en la fila 8, header=7).
    Devuelve un DataFrame con:
      - Proveedor (keyword)
      - Importe medio (€)
      - Fecha desde la primera detección
      - Número de meses detectados
    Solo mantiene aquellos keywords que aparecen en al menos
    total_meses - 1 meses (para tolerar un mes perdido).
    """
    # 1) Leer fichero (CSV si termina en .csv, si no, Excel)
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path, sep=";", dtype=str)
    else:
        df = pd.read_excel(path, header=7, engine="openpyxl", dtype=str)

    # 2) Normalizar y parsear tipos
    #    - Fecha (dayfirst)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], dayfirst=True, errors="coerce")
    #    - Concepto en minúsculas
    df[CONCEPT_COL] = df[CONCEPT_COL].str.lower().fillna("")
    #    - Importe como float (cambia coma por punto)
    df[AMOUNT_COL] = df[AMOUNT_COL].str.replace(",", ".").astype(float)

    # 3) Crear columna periodo mensual y calcular número total de meses en datos
    df["periodo"] = df[DATE_COL].dt.to_period("M")
    total_meses = df["periodo"].nunique()

    # 4) Para cada keyword, comprobamos en cuántos meses distintos aparece
    subs = []
    for kw in SUBSCRIPTION_KEYWORDS:
        mask = df[CONCEPT_COL].str.contains(kw, regex=False)
        df_kw = df[mask]
        meses_distintos = df_kw["periodo"].nunique()
        # Si aparece en al menos total_meses-1 meses, lo consideramos suscripción
        if meses_distintos >= max(1, total_meses - 1):
            fecha_primera = df_kw[DATE_COL].min()
            importe_medio = df_kw[AMOUNT_COL].mean()
            subs.append({
                "Proveedor (keyword)": kw,
                "Importe medio (€)": round(importe_medio, 2),
                "Desde": fecha_primera,
                "Meses detectados": int(meses_distintos)
            })

    return pd.DataFrame(subs)


if __name__ == "__main__":
    import sys
    fichero = sys.argv[1] if len(sys.argv) > 1 else "export2025730.csv"
    df_subs = detect_subscriptions(fichero)
    if df_subs.empty:
        print("No se detectaron suscripciones mensuales.")
    else:
        print(df_subs.to_string(index=False))
