"""
financial_assistant.py
----------------------

Este módulo define un asistente financiero sencillo que permite cargar un extracto bancario
y analizar sus movimientos. La idea es ejecutarlo de forma local para obtener resúmenes de gastos,
clasificar las transacciones por categorías y recibir recomendaciones básicas de ahorro.

Para utilizarlo, ejecuta el archivo en la línea de comandos. Por defecto leerá un
fichero Excel o CSV de la misma carpeta (`export2025730.xls` en el ejemplo) y producirá
informes resumidos y consejos. Si deseas analizar otro fichero, puedes pasarlo como
argumento al ejecutar el script, por ejemplo:

    python3 financial_assistant.py otro_extracto.xlsx

El asistente utiliza un diccionario de palabras clave para categorizar automáticamente
los conceptos. Si detecta movimientos que no encajan, los agrupa bajo "otros" y
presenta un resumen. El objetivo es que puedas ampliar fácilmente el diccionario
añadiendo nuevas palabras clave o subcategorías en la variable CATEGORY_KEYWORDS.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# Definimos un diccionario global con categorías y palabras clave asociadas. Puedes ampliar
# este mapa para adaptarlo mejor a tus movimientos. Las claves son nombres de categorías
# y los valores listas de palabras o fragmentos de texto que, si aparecen en la descripción
# del movimiento, asignan ese movimiento a la categoría.
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "finanzas": [
        "transferencia",
        "transfer",
        "bizum",
        "paypal",
        "comision",
        "comisiones",
        "cuota",
        "liquidacion contrato",
        "retirada",
        "ingreso",
        "nomina",
        "mantenimiento",
        "cajero",
        "atm",
        "reintegro",
        "pension",
        "abono",
        "devolucion",
    ],
    "servicios": [
        "telefonica",
        "digi",
        "internet",
        "fibra",
        "vodafone",
        "orange",
        "jazztel",
        "electricidad",
        "luz",
        "endesa",
        "iberdrola",
        "naturgy",
        "agua",
        "gas",
        "factura",
    ],
    "salud": [
        "medico",
        "sanitas",
        "seguro medico",
        "hospital",
        "farmacia",
        "parafarmacia",
        "dentista",
    ],
    "viajes": [
        "hotel",
        "alojamiento",
        "airbnb",
        "booking",
        "vueling",
        "renfe",
        "iberia",
        "vuelo",
        "billete",
    ],
    "compras": [
        "zara",
        "primark",
        "h&m",
        "pull&bear",
        "pull and bear",
        "bershka",
        "decathlon",
        "amazon",
        "corte ingles",
        "fnac",
        "ikea",
        "aliexpress",
        "game",
        "electronica",
        "farmacia",
        "farmac",
        "supercor",
    ],
    "ocio": [
        "netflix",
        "spotify",
        "gym",
        "gimnasio",
        "deporte",
        "cine",
        "cinepolis",
        "teatro",
        "estanco",
        "tabaco",
        "loteria",
        "apuesta",
        "pub",
        "cerveceria",
        "discoteca",
    ],
    "impuestos": [
        "impuesto",
        "tasas",
        "dgt",
        "multas",
        "hacienda",
        "seguridad social",
    ],
    "restauracion": [
        "restaurante",
        "restaurant",
        "bar",
        "cafeteria",
        "cafetería",
        "cafe",
        "cerveceria",
        "cervecería",
        "pub",
        "pizzeria",
        "pizzería",
        "burger",
        "kebab",
        "sushi",
        "taberna",
        "marisqueria",
        "merendero",
        "hamburguesa",
        "bocateria",
        "bocatería",
        "comida rapida",
    ],
    "transporte": [
        "repsol",
        "cepsa",
        "ballenoil",
        "bp",
        "terzo",
        "cedipsa",
        "estacion de servicio",
        "gasolinera",
        "combustible",
        "gasolina",
        "diesel",
        "peaje",
        "parking",
        "aparcamiento",
        "taxi",
        "uber",
        "bus",
        "metro",
        "tren",
    ],
    "alimentacion": [
        "mercadona",
        "carrefour",
        "dia",
        "lidl",
        "eroski",
        "alcampo",
        "hiper",
        "supermercado",
        "super",
        "misuper",
        "condis",
        "caprabo",
        "panaderia",
        "pasteleria",
        "fruteria",
        "carniceria",
        "pescaderia",
        "alimentacion",
        "comestibles",
        "ultramarinos",
        "camper",
        "galileo",
    ],
    "mascotas": [
        "veterinario",
        "pet",
        "mascotas",
    ],
}


def _normalize_description(desc: str) -> str:
    """
    Normaliza la descripción eliminando prefijos genéricos y puntuación para facilitar
    la búsqueda de palabras clave. Convierte el texto a minúsculas y quita
    espacios redundantes.
    """
    if not isinstance(desc, str):
        return ""
    desc = desc.lower()
    # Eliminar prefijos comunes que no aportan información sobre el comercio
    for prefix in [
        "pago movil en",
        "pago móvil en",
        "pago mov en",
        "pago movil",
        "pago móvil",
        "pago mov.",
        "transaccion contactless en",
        "transacción contactless en",
        "transaccion contactless",
        "transacción contactless",
        "compra en",
        "compra",
        "recibo de",
        "recibo",
        "cargo de",
        "abono de",
    ]:
        if desc.startswith(prefix):
            desc = desc[len(prefix):]
            break
    # Reemplazar caracteres que suelen acompañar a la descripción
    for token in [',', ';', ':', '.', '-', '*', '#', '!', '@']:
        desc = desc.replace(token, ' ')
    # Unificar espacios
    desc = " ".join(desc.split())
    return desc


@dataclass
class FinancialAssistant:
    filename: str
    dataframe: pd.DataFrame = field(default_factory=pd.DataFrame, init=False)
    monthly_summary_df: Optional[pd.DataFrame] = None
    category_totals: Optional[pd.DataFrame] = None

    def load_transactions(self) -> None:
        """
        Carga el fichero de movimientos bancarios. Se admiten tanto CSV como Excel.
        El método detecta la estructura del extracto de Santander (los primeros
        encabezados en las filas iniciales) y reajusta el DataFrame al formato
        esperado con columnas: fecha_operacion, fecha_valor, concepto, importe, saldo.
        """
        if self.filename.lower().endswith(('.xls', '.xlsx', '.xlsm')):
            # Leer Excel. skiprows se ajusta a partir del patrón del fichero de prueba.
            df_raw = pd.read_excel(self.filename, header=None)
        elif self.filename.lower().endswith('.csv'):
            df_raw = pd.read_csv(self.filename, header=None)
        else:
            raise ValueError(f"Formato de archivo no reconocido: {self.filename}")

        # Buscar la fila que contiene las cabeceras. Para simplificar tomamos
        # la primera fila donde aparece 'CONCEPTO' en alguna de las celdas.
        header_row = None
        for idx, row in df_raw.iterrows():
            if row.astype(str).str.contains('CONCEPTO', case=False).any():
                header_row = idx
                break
        if header_row is None:
            raise ValueError("No se ha encontrado la fila de cabeceras en el archivo")
        # Extracción del DataFrame con cabeceras correctas
        df = pd.read_excel(self.filename, header=header_row)
        # Renombramos columnas a nombres estándar
        rename_map = {}
        for col in df.columns:
            lc = str(col).lower().strip()
            if 'fecha operación' in lc or 'fecha operacion' in lc:
                rename_map[col] = 'fecha_operacion'
            elif 'fecha valor' in lc:
                rename_map[col] = 'fecha_valor'
            elif 'concepto' in lc:
                rename_map[col] = 'concepto'
            elif 'importe' in lc:
                rename_map[col] = 'importe'
            elif 'saldo' in lc:
                rename_map[col] = 'saldo'
        df = df.rename(columns=rename_map)
        # Filtramos filas con valores válidos en 'importe'
        df = df[df['importe'].notnull()]
        # Convertimos a tipos apropiados
        df['fecha_operacion'] = pd.to_datetime(df['fecha_operacion'], errors='coerce')
        df['importe'] = pd.to_numeric(df['importe'], errors='coerce')
        df['saldo'] = pd.to_numeric(df['saldo'], errors='coerce')
        df['concepto'] = df['concepto'].astype(str)
        df = df.dropna(subset=['fecha_operacion', 'importe'])
        self.dataframe = df.reset_index(drop=True)

    def classify_transactions(self) -> None:
        """
        Aplica la clasificación de movimientos usando el diccionario CATEGORY_KEYWORDS.
        Cada movimiento se asigna a la primera categoría cuyo patrón aparezca en
        la descripción. Los ingresos (importes positivos) se asignan a 'finanzas'
        automáticamente, a menos que correspondan a devoluciones de servicios.
        """
        if self.dataframe.empty:
            raise RuntimeError("Primero hay que cargar los movimientos con load_transactions().")

        categories: List[str] = []
        descriptions = self.dataframe['concepto'].apply(_normalize_description)
        for desc, amount in zip(descriptions, self.dataframe['importe']):
            category_assigned: Optional[str] = None
            # Ingresos claros van a finanzas
            if amount > 0:
                category_assigned = 'finanzas'
            else:
                # Revisar cada categoría y sus palabras clave
                for cat, keywords in CATEGORY_KEYWORDS.items():
                    for kw in keywords:
                        if kw in desc:
                            category_assigned = cat
                            break
                    if category_assigned:
                        break
            if not category_assigned:
                category_assigned = 'otros'
            categories.append(category_assigned)
        self.dataframe['categoria'] = categories

    def compute_summaries(self) -> None:
        """
        Calcula los totales por categoría y el resumen mensual. Debe llamarse
        después de cargar y clasificar.
        """
        if 'categoria' not in self.dataframe.columns:
            raise RuntimeError("Primero hay que clasificar los movimientos con classify_transactions().")
        # Total por categoría
        category_totals = (
            self.dataframe.groupby('categoria')['importe']
            .sum()
            .reset_index()
            .sort_values('importe', ascending=False)
        )
        self.category_totals = category_totals
        # Resumen mensual por categoría
        df = self.dataframe.copy()
        df['mes'] = df['fecha_operacion'].dt.to_period('M')
        monthly = df.pivot_table(
            index='mes', columns='categoria', values='importe', aggfunc='sum', fill_value=0
        )
        monthly = monthly.sort_index()
        self.monthly_summary_df = monthly

    def print_overview(self) -> None:
        """
        Imprime un resumen general de ingresos y gastos, con totales por categoría
        y una tabla mensual. Llama a este método tras compute_summaries().
        """
        if self.category_totals is None or self.monthly_summary_df is None:
            raise RuntimeError("Primero hay que calcular los resúmenes con compute_summaries().")
        print("\n=== Resumen de ingresos y gastos ===")
        total_ingresos = self.dataframe[self.dataframe['importe'] > 0]['importe'].sum()
        total_gastos = self.dataframe[self.dataframe['importe'] < 0]['importe'].sum()
        print(f"Ingresos totales: {total_ingresos:,.2f} EUR")
        print(f"Gastos totales: {total_gastos:,.2f} EUR")
        ahorro = total_ingresos + total_gastos
        print(f"Ahorro neto: {ahorro:,.2f} EUR")
        # Totales por categoría
        print("\nTotales por categoría:")
        for _, row in self.category_totals.iterrows():
            categoria = row['categoria']
            total = row['importe']
            print(f" - {categoria.capitalize():<15}: {total:>10.2f} EUR")
        # Tabla mensual
        print("\nGastos/Ingresos por mes y categoría (EUR):")
        print(self.monthly_summary_df.to_string())

    def generate_tips(self) -> List[str]:
        """
        Genera sugerencias de ahorro basadas en el análisis de gastos. Las reglas son
        generales e incluyen: porcentaje de ahorro respecto a ingresos, categorías con
        mayor gasto, y recomendaciones de presupuesto usando el método 50/30/20.
        """
        if self.category_totals is None:
            raise RuntimeError("Debe ejecutar compute_summaries() antes de generar consejos.")
        tips: List[str] = []
        total_ingresos = self.dataframe[self.dataframe['importe'] > 0]['importe'].sum()
        total_gastos = -self.dataframe[self.dataframe['importe'] < 0]['importe'].sum()
        ahorro_neto = total_ingresos - total_gastos
        # Regla 1: calcular el porcentaje de ahorro
        if total_ingresos > 0:
            porcentaje_ahorro = (ahorro_neto / total_ingresos) * 100
            tips.append(
                f"Tu tasa de ahorro actual es del {porcentaje_ahorro:.1f}% del total de ingresos. "
                "Intenta mantenerla por encima del 20% para generar colchón de emergencias."
            )
        # Regla 2: identificar las tres categorías de gasto principales
        gastos_por_categoria = self.category_totals[self.category_totals['importe'] < 0].copy()
        gastos_por_categoria['abs_gasto'] = gastos_por_categoria['importe'].abs()
        top3 = gastos_por_categoria.sort_values('abs_gasto', ascending=False).head(3)
        if not top3.empty:
            cats = [c.capitalize() for c in top3['categoria']]
            tips.append(
                f"Tus principales categorías de gasto son: {', '.join(cats)}. "
                "Revisa si puedes reducir alguno de esos importes."
            )
        # Regla 3: método 50/30/20 (50% necesidades, 30% ocio, 20% ahorro)
        # Calculamos porcentaje destinado a servicios esenciales y ocio
        necesidades_cats = {'alimentacion', 'servicios', 'salud', 'transporte', 'impuestos'}
        ocio_cats = {'restauracion', 'ocio', 'compras', 'viajes', 'mascotas'}
        gastos_necesidades = -self.dataframe[
            (self.dataframe['categoria'].isin(necesidades_cats)) & (self.dataframe['importe'] < 0)
        ]['importe'].sum()
        gastos_ocio = -self.dataframe[
            (self.dataframe['categoria'].isin(ocio_cats)) & (self.dataframe['importe'] < 0)
        ]['importe'].sum()
        if total_ingresos > 0:
            porcentaje_necesidades = (gastos_necesidades / total_ingresos) * 100
            porcentaje_ocio = (gastos_ocio / total_ingresos) * 100
            tips.append(
                f"Actualmente destinas un {porcentaje_necesidades:.1f}% de tus ingresos a necesidades "
                f"y un {porcentaje_ocio:.1f}% a ocio/consumo. "
                "Intenta ceñirte al método 50/30/20: 50% necesidades, 30% ocio, 20% ahorro."
            )
        # Regla 4: presencia de comisiones bancarias
        comisiones = self.dataframe[(self.dataframe['categoria'] == 'finanzas') & (self.dataframe['importe'] < 0)]
        if not comisiones.empty:
            total_comisiones = -comisiones['importe'].sum()
            tips.append(
                f"Has pagado {total_comisiones:.2f} EUR en comisiones bancarias. "
                "Valora negociar con tu banco o buscar una entidad sin comisiones."
            )
        return tips


def main(argv: List[str]) -> int:
    """Función principal: carga el fichero, clasifica, resume y genera consejos."""
    if len(argv) > 1:
        filename = argv[1]
    else:
        filename = 'export2025730.xls'
    assistant = FinancialAssistant(filename)
    try:
        assistant.load_transactions()
        assistant.classify_transactions()
        assistant.compute_summaries()
        assistant.print_overview()
        tips = assistant.generate_tips()
        print("\nConsejos para mejorar tu economía:")
        for idx, tip in enumerate(tips, start=1):
            print(f"{idx}. {tip}")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))