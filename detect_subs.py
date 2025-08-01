#!/usr/bin/env python3
"""
detect_subs.py

Detecta posibles suscripciones periódicas en tu extracto bancario CSV.
"""

import pandas as pd
import sys

# Parámetros
CSV_FILE   = 'export2025730.csv'
HEADER_ROW = 7   # 0-index (fila 8 en Excel)
MIN_MONTHS = 2   # Mínimo meses distintos para considerarlo recurrente

def main():
    try:
        df = pd.read_csv(CSV_FILE, sep=';', header=HEADER_ROW, encoding='utf-8')
    except Exception as e:
        print(f"ERROR: no pude leer '{CSV_FILE}': {e}", file=sys.stderr)
        sys.exit(1)

    # Renombrar columnas
    df = df.rename(columns={
        'FECHA OPERACIÓN': 'fecha',
        'CONCEPTO':         'concepto',
        'IMPORTE EUR':      'importe'
    })

    # Parsear fechas
    try:
        df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True)
    except Exception as e:
        print(f"ERROR: no pude parsear las fechas: {e}", file=sys.stderr)
        sys.exit(1)
    df['mes'] = df['fecha'].dt.to_period('M')

    # Agrupar y contar
    grp = df.groupby(['concepto','importe'], as_index=False).agg(
        meses_distintos=('mes', 'nunique'),
        total_cargos=('mes', 'count'),
        primer_pago=('fecha', 'min'),
        ultimo_pago=('fecha', 'max')
    )
    subs = grp[grp['meses_distintos'] >= MIN_MONTHS] \
            .sort_values(['meses_distintos','total_cargos'], ascending=False)

    if subs.empty:
        print(f"No se detectaron cargos repetidos en ≥{MIN_MONTHS} meses distintos.")
    else:
        print(f"\nPosibles suscripciones (≥{MIN_MONTHS} meses distintos):\n")
        print(subs.to_string(
            index=False,
            columns=['concepto','importe','meses_distintos','total_cargos','primer_pago','ultimo_pago'],
            header=['Concepto','Importe (€)','Meses distintos','Veces totales','Primer pago','Último pago']
        ))

if __name__ == '__main__':
    main()
