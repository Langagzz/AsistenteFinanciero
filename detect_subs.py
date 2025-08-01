# detect_subs.py

#!/usr/bin/env python3
"""
detect_subs.py

Detecta posibles suscripciones mensuales (pagos que se repiten en ≥MIN_MONTHS meses distintos)
en tu extracto bancario (CSV o Excel).

Uso:
    python detect_subs.py [ruta_fichero]
Si no pasas ruta, usará 'export2025730.csv' o 'export2025730.xls/xlsx' en el directorio actual.
"""

import os
import sys
import pandas as pd
from datetime import datetime
from typing import Tuple

# Número mínimo de meses distintos para considerar un cargo "suscripción"
MIN_MONTHS = 2

# Nombre de la columna fecha en tu extracto
DATE_COL = 'FECHA OPERACIÓN'

def load_transactions(path: str) -> pd.DataFrame:
    """
    Carga el extracto (CSV o Excel) en un DataFrame y devuelve las columnas
    necesarias (fecha, concepto, importe).
    """
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in ('.csv', '.txt'):
            df = pd.read_csv(path,
                             sep=';',
                             header=7,
                             dtype=str,
                             usecols=[DATE_COL, 'CONCEPTO', 'IMPORTE EUR'])
        else:
            df = pd.read_excel(path,
                               header=7,
                               dtype=str)  # CSV y Excel
    except Exception as e:
        raise RuntimeError(f"Error al leer el fichero: {e}")

    if DATE_COL not in df.columns:
        raise RuntimeError(f"No se encuentra la columna de fecha '{DATE_COL}'. Columnas disponibles: {list(df.columns)}")

    df = df.rename(columns={'CONCEPTO': 'concepto', 'IMPORTE EUR': 'importe', DATE_COL: 'fecha'})
    # Convertimos importe a float
    df['importe'] = df['importe'].str.replace(',', '.').astype(float)
    # Parseamos fecha con dayfirst=True
    df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['fecha'])
    return df[['fecha', 'concepto', 'importe']]

def detect_subscriptions(path: str) -> pd.DataFrame:
    df = load_transactions(path)

    # Creamos columna mes
    df['mes'] = df['fecha'].dt.to_period('M')
    # Agrupamos por concepto e importe parecido (redondeado)
    grouped = (
        df.assign(concepto_norm=df['concepto'].str.lower().str.strip())
          .groupby(['concepto_norm'])
    )

    subs = grouped.apply(lambda g: pd.Series({
        'importe': round(g['importe'].mean(), 2),
        'meses_distintos': g['mes'].nunique(),
        'total_cargos': len(g),
        'primer_pago': g['fecha'].min(),
        'ultimo_pago': g['fecha'].max()
    })).reset_index()

    # Filtramos solo los que tienen al menos MIN_MONTHS meses distintos
    subs = subs[subs['meses_distintos'] >= MIN_MONTHS]
    # Ordenamos por meses_distintos desc
    subs = subs.sort_values('meses_distintos', ascending=False)

    return subs[['concepto_norm', 'importe', 'meses_distintos', 'total_cargos', 'primer_pago', 'ultimo_pago']]

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        # Intentamos CSV primero, luego XLS, luego XLSX
        for candidate in ('export2025730.csv', 'export2025730.xls', 'export2025730.xlsx'):
            if os.path.exists(candidate):
                path = candidate
                break
    if not path or not os.path.exists(path):
        print("No se encontró el fichero. Pasa la ruta como argumento o pon 'export2025730.csv/xls/xlsx' aquí.")
        sys.exit(1)

    try:
        subs = detect_subscriptions(path)
    except Exception as e:
        print(f"Error al detectar suscripciones: {e}")
        sys.exit(1)

    if subs.empty:
        print(f"No se detectaron cargos repetidos en ≥{MIN_MONTHS} meses diferentes.")
    else:
        print(f"\nPosibles suscripciones (≥{MIN_MONTHS} meses distintos):\n")
        print(subs.to_string(
            index=False,
            columns=['concepto_norm','importe','meses_distintos','total_cargos','primer_pago','ultimo_pago'],
            header=['Concepto','Importe (€)','Meses distintos','Veces totales','Primer pago','Último pago']
        ))

if __name__ == '__main__':
    main()
