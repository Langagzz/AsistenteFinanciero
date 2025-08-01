
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
financial_assistant.py
----------------------

Este módulo define un asistente financiero sencillo que permite:

- Cargar un extracto bancario en Excel (.xls/.xlsx) o CSV.
- Clasificar automáticamente transacciones por categorías usando un diccionario de keywords.
- Calcular resúmenes de ingresos/gastos y ofrecer tips de ahorro.
- Detectar PLANES DE AHORRO (siguiente cuota / objetivo).
- Detectar SUSCRIPCIONES periódicas **solo** de proveedores listados en categories.json.

Para usarlo, instala dependencias:
    pip install pandas numpy

Y luego:
    python financial_assistant.py export2025730.csv
"""

import json
import sys
from datetime import datetime
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

class FinancialAssistant:
    def __init__(self, filepath: str, categories_path: str = "categories.json"):
        self.filepath = filepath
        self.df = pd.DataFrame()
        self.monthly_summary_df = None

        # Carga keywords desde JSON
        try:
            with open(categories_path, encoding="utf-8") as f:
                self.category_keywords: Dict[str, List[str]] = json.load(f)
        except Exception as e:
            raise RuntimeError(f"No pude leer '{categories_path}': {e}")

    def load_transactions(self):
        """Carga el fichero Excel/CSV en self.df normalizando columnas."""
        ext = self.filepath.lower().split('.')[-1]
        if ext in ("xls", "xlsx"):
            df = pd.read_excel(self.filepath, header=7 engine="openpyxl")
        else:
            df = pd.read_csv(self.filepath, header=7, sep=';', encoding='utf-8')
        df = df.rename(
            columns={
                'FECHA OPERACIÓN': 'fecha_operacion',
                'CONCEPTO': 'concepto',
                'IMPORTE EUR': 'importe'
            }
        )
        # Convertir fecha a datetime
        df['fecha_operacion'] = pd.to_datetime(df['fecha_operacion'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['fecha_operacion'])
        self.df = df

    def classify_transactions(self):
        """Clasifica cada fila en una categoría según keywords."""
        if self.df.empty:
            raise RuntimeError("Debe cargar las transacciones primero.")
        cats = []
        for text in self.df['concepto'].astype(str).str.lower():
            found = False
            for cat, keys in self.category_keywords.items():
                if any(k in text for k in keys):
                    cats.append(cat)
                    found = True
                    break
            cats.append('Otros' if not found else None)
        self.df['categoria'] = cats

    def compute_summaries(self):
        """Calcula resumen mensual de ingresos/gastos para consejos."""
        if self.df.empty:
            raise RuntimeError("Debe cargar las transacciones primero.")
        self.monthly_summary_df = (
            self.df
            .assign(mes=self.df['fecha_operacion'].dt.to_period("M"))
            .groupby('mes')['importe']
            .sum()
            .to_frame()
        )

    def generate_tips(self) -> List[str]:
        """Genera consejos básicos basados en porcentajes 50/30/20."""
        if self.monthly_summary_df is None:
            raise RuntimeError("Debe ejecutar compute_summaries() primero.")
        total_ing = self.df.loc[self.df['importe'] > 0, 'importe'].sum()
        total_gast = -self.df.loc[self.df['importe'] < 0, 'importe'].sum()
        savings_rate = (total_ing - total_gast) / total_ing * 100 if total_ing else 0.0
        # Ejemplos de tip
        tips = [
            f"Tu tasa de ahorro es {savings_rate:.1f}%. Intenta 20% ahorros.",
            "Revisa tus principales categorías de gasto y reduce las mayores."
        ]
        return tips

    def detect_subscriptions(self, amount_tolerance: float = 2.0) -> pd.DataFrame:
        """
        Detecta SUSCRIPCIONES periódicas solo de proveedores listados en categories.json.
        
        - Filtra importes < 0 (gastos).
        - Normaliza el texto a minúsculas.
        - Se queda solo con aquellos que contienen alguna keyword de 'suscripciones'.
        - Agrupa por texto e importe, filtra por ruido de importe (< tolerance) y periodicidad:
          mensual (25–35 días), trimestral (85–95 días), anual (355–375 días).
        """
        if self.df.empty:
            raise RuntimeError("Cargue y clasifique antes de detectar suscripciones.")

        # 1) Filtramos solo gastos y normalizamos descripción
        df = self.df[self.df['importe'] < 0].copy()
        df['desc_norm'] = df['concepto'].str.lower()

        # 2) Solo proveedores de subs
        subs_keys = self.category_keywords.get('suscripciones', [])
        df = df[df['desc_norm'].apply(lambda d: any(k in d for k in subs_keys))]
        if df.empty:
            return pd.DataFrame()

        # 3) Detectamos periodicidad
        records = []
        for desc, group in df.groupby(['desc_norm', 'importe']):
            desc_text, imp = desc
            if len(group) < 2:
                continue
            if group['importe'].std() > amount_tolerance:
                continue
            fechas = group['fecha_operacion'].sort_values()
            diffs = fechas.diff().dt.days.dropna()
            if len(diffs) < 2:
                continue
            med = diffs.median()
            if 25 <= med <= 35:
                freq = 'mensual'
            elif 85 <= med <= 95:
                freq = 'trimestral'
            elif 355 <= med <= 375:
                freq = 'anual'
            else:
                continue
            records.append({
                'descripcion': desc_text,
                'importe_medio': round(float(group['importe'].mean()), 2),
                'frecuencia': freq,
                'veces': len(group),
                'primer_pago': fechas.min().date().isoformat(),
                'ultimo_pago': fechas.max().date().isoformat()
            })
        return pd.DataFrame(records)

def main():
    if len(sys.argv) < 2:
        print("Uso: python financial_assistant.py <extracto.csv|.xls>", file=sys.stderr)
        sys.exit(1)
    fa = FinancialAssistant(sys.argv[1])
    fa.load_transactions()
    fa.classify_transactions()
    fa.compute_summaries()

    print("\n=== Consejos para tus finanzas ===")
    for tip in fa.generate_tips():
        print(" -", tip)

    print("\n=== Suscripciones detectadas ===")
    subs = fa.detect_subscriptions()
    if subs.empty:
        print("No se encontraron suscripciones periódicas.")
    else:
        print(subs.to_string(index=False))

if __name__ == '__main__':
    main()
