import os
import re
from datetime import datetime
from typing import List, Tuple

import pandas as pd

# Nombre de la columna de fecha en tu extracto
DATE_COL = "FECHA OPERACIÓN"

# Proveedores habituales de suscripción (keywords en minúsculas)
SUB_PROVIDERS = [
    "digimobil", "digi spain", "netflix", "spotify", "youtube", "yt music",
    "apple", "itunes", "amazon", "prime", "hbo", "disney+", "movistar", "vodafone"
]

def normalize_concept(concept: str) -> str:
    """Pone en minúsculas y elimina múltiples espacios/puntuación."""
    text = concept.lower()
    text = re.sub(r"[^\w ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def detect_subscriptions(path: str, min_months: int = 3) -> pd.DataFrame:
    """
    Detecta cargos recurrentes mensuales en el extracto.
    - path: ruta al XLS/XLSX o CSV exportado de tu banco.
    - min_months: número mínimo de meses distintos para considerarlo suscripción.
    Devuelve un DataFrame con columnas:
      ['concepto_normalizado','importe','first_date','last_date','months_count']
    """
    ext = os.path.splitext(path)[1].lower()
    # Lectura según extensión
    if ext in (".xls", ".xlsx"):
        engine = "xlrd" if ext == ".xls" else "openpyxl"
        df = pd.read_excel(
            path,
            header=7,
            engine=engine,
            parse_dates=[DATE_COL],
            dayfirst=True,
            dtype=str,
        )
    elif ext == ".csv":
        # Detecta separador (punto y coma o comas)
        sample = open(path, encoding="utf-8", errors="ignore").read(2048)
        sep = ";" if ";" in sample and sample.count(";") > sample.count(",") else ","
        df = pd.read_csv(
            path,
            sep=sep,
            header=7,
            parse_dates=[DATE_COL],
            dayfirst=True,
            dtype=str,
        )
    else:
        raise RuntimeError(f"Formato no soportado: {ext}")

    # Normalizamos columnas
    if DATE_COL not in df.columns:
        raise RuntimeError(f"No se encontró la columna de fecha '{DATE_COL}'.")
    if "CONCEPTO" not in df.columns and "CONCEPTO;" not in df.columns:
        raise RuntimeError("No se encontró la columna de concepto.")

    # Ajuste de nombre de columna 'CONCEPTO' con o sin punto y coma
    concept_col = "CONCEPTO"
    if concept_col not in df.columns:
        # si aparece con punto y coma en CSV
        for c in df.columns:
            if c.startswith("CONCEPTO"):
                concept_col = c
                break

    # Preparamos datos
    df = df[[DATE_COL, concept_col, 'IMPORTE EUR']].dropna(subset=[DATE_COL, concept_col])
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], dayfirst=True, errors="coerce")
    df = df.dropna(subset=[DATE_COL])
    df['importe'] = df['IMPORTE EUR'].astype(float)
    df['concepto_norm'] = df[concept_col].apply(normalize_concept)

    # Filtrar sólo importes negativos (cargos)
    cargos = df[df['importe'] < 0].copy()

    # Agrupamos por concepto normalizado
    grupos = cargos.groupby('concepto_norm')

    registros: List[Tuple[str, float, datetime, datetime, int]] = []
    for concept, g in grupos:
        # Comprobar proveedor en la lista de suscripciones
        if not any(prov in concept for prov in SUB_PROVIDERS):
            continue

        # Meses distintos
        meses = g[DATE_COL].dt.to_period("M").unique()
        if len(meses) < min_months:
            continue

        importe_mean = g['importe'].mean()
        first = g[DATE_COL].min()
        last = g[DATE_COL].max()
        registros.append((concept, importe_mean, first, last, len(meses)))

    # Construimos DataFrame de resultado
    df_subs = pd.DataFrame(
        registros,
        columns=['concepto', 'importe', 'first_date', 'last_date', 'meses_distintos']
    )

    # Ordenar por fecha de inicio
    df_subs = df_subs.sort_values('first_date').reset_index(drop=True)
    return df_subs
