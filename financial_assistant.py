#!/usr/bin/env python3
"""Financial Assistant CLI utility."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Diccionario por defecto de categorías y palabras clave
DEFAULT_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "finanzas": [
        "transferencia", "transfer", "bizum", "paypal", "comision", "comisiones",
        "cuota", "liquidacion contrato", "retirada", "ingreso", "nomina",
        "mantenimiento", "cajero", "atm", "reintegro", "pension", "abono", "devolucion"
    ],
    "servicios": [
        "telefonica", "digi", "internet", "fibra", "vodafone", "orange", "jazztel",
        "electricidad", "luz", "endesa", "iberdrola", "naturgy", "agua", "gas", "factura"
    ],
    "salud": ["medico", "sanitas", "seguro medico", "hospital", "farmacia", "parafarmacia", "dentista"],
    "viajes": ["hotel", "alojamiento", "airbnb", "booking", "vueling", "renfe", "iberia", "vuelo", "billete"],
    "compras": [
        "zara", "primark", "h&m", "pull&bear", "pull and bear", "bershka", "decathlon", "amazon",
        "corte ingles", "fnac", "ikea", "aliexpress", "game", "electronica", "farmacia", "farmac", "supercor"
    ],
    "ocio": [
        "netflix", "spotify", "gym", "gimnasio", "deporte", "cine", "cinepolis", "teatro", "estanco",
        "tabaco", "loteria", "apuesta", "pub", "cerveceria", "discoteca"
    ],
    "impuestos": ["impuesto", "tasas", "dgt", "multas", "hacienda", "seguridad social"],
    "restauracion": [
        "restaurante", "restaurant", "bar", "cafeteria", "cafetería", "cafe", "cerveceria", "cervecería",
        "pub", "pizzeria", "pizzería", "burger", "kebab", "sushi", "taberna", "marisqueria",
        "merendero", "hamburguesa", "bocateria", "bocatería", "comida rapida"
    ],
    "transporte": [
        "repsol", "cepsa", "ballenoil", "bp", "terzo", "cedipsa", "estacion de servicio", "gasolinera",
        "combustible", "gasolina", "diesel", "peaje", "parking", "aparcamiento", "taxi", "uber", "bus", "metro", "tren"
    ],
    "alimentacion": [
        "mercadona", "carrefour", "dia", "lidl", "eroski", "alcampo", "hiper", "supermercado",
        "super", "misuper", "condis", "caprabo", "panaderia", "pasteleria", "fruteria",
        "carniceria", "pescaderia", "alimentacion", "comestibles", "ultramarinos", "camper", "galileo"
    ],
    "mascotas": ["veterinario", "pet", "mascotas"]
}

def _normalize_description(desc: str) -> str:
    """Normaliza la descripción para facilitar la búsqueda de palabras clave."""
    if not isinstance(desc, str):
        return ""
    desc = desc.lower()
    for prefix in [
        "pago movil en", "pago móvil en", "pago mov en", "pago movil", "pago móvil",
        "pago mov.", "transaccion contactless en", "transacción contactless en",
        "transaccion contactless", "transacción contactless", "compra en", "compra",
        "recibo de", "recibo", "cargo de", "abono de"
    ]:
        if desc.startswith(prefix):
            desc = desc[len(prefix):]
            break
    for token in [",", ";", ":", ".", "-", "*", "#", "!", "@"]:
        desc = desc.replace(token, " ")
    return " ".join(desc.split())

@dataclass
class FinancialAssistant:
    filename: str
    categories_file: str = "categories.json"
    dataframe: pd.DataFrame = field(default_factory=pd.DataFrame, init=False)
    monthly_summary_df: Optional[pd.DataFrame] = None
    category_totals: Optional[pd.DataFrame] = None
    category_keywords: Dict[str, List[str]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.category_keywords = self._load_categories()

    def _load_categories(self) -> Dict[str, List[str]]:
        try:
            with open(self.categories_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                return {k: [w.lower() for w in v] for k, v in data.items()}
        except FileNotFoundError:
            return DEFAULT_CATEGORY_KEYWORDS

    def load_transactions(self) -> None:
        """Carga el fichero de movimientos bancarios en un DataFrame."""
        if self.filename.lower().endswith((".xls", ".xlsx", ".xlsm")):
            read_func = pd.read_excel
        elif self.filename.lower().endswith(".csv"):
            read_func = pd.read_csv
        else:
            raise ValueError(f"Formato de archivo no reconocido: {self.filename}")

        # Detectar fila de cabecera
        df_raw = read_func(self.filename, header=None)
        header_row = None
        for idx, row in df_raw.iterrows():
            if row.astype(str).str.contains("CONCEPTO", case=False, na=False).any():
                header_row = idx
                break
        if header_row is None:
            raise ValueError("No se ha encontrado la fila de cabeceras en el archivo")

        # Leer con la fila detectada
        df = read_func(self.filename, header=header_row)
        rename_map: Dict[str, str] = {}
        for col in df.columns:
            lc = str(col).lower()
            if "fecha operacion" in lc or "fecha operación" in lc:
                rename_map[col] = "fecha_operacion"
            elif "fecha valor" in lc:
                rename_map[col] = "fecha_valor"
            elif "concepto" in lc:
                rename_map[col] = "concepto"
            elif "importe" in lc:
                rename_map[col] = "importe"
            elif "saldo" in lc:
                rename_map[col] = "saldo"
        df = df.rename(columns=rename_map)

        df = df[df["importe"].notnull()]
        df["fecha_operacion"] = pd.to_datetime(df["fecha_operacion"], errors="coerce")
        df["importe"] = pd.to_numeric(df["importe"], errors="coerce")
        df["saldo"] = pd.to_numeric(df["saldo"], errors="coerce")
        df["concepto"] = df["concepto"].astype(str)
        df = df.dropna(subset=["fecha_operacion", "importe"])
        self.dataframe = df.reset_index(drop=True)

    def classify_transactions(self) -> None:
        """Clasifica cada movimiento usando las categorías definidas."""
        if self.dataframe.empty:
            raise RuntimeError("Primero carga los movimientos con load_transactions().")
        categories: List[str] = []
        descriptions = self.dataframe["concepto"].apply(_normalize_description)
        for desc, amount in zip(descriptions, self.dataframe["importe"]):
            assigned = None
            for cat, keywords in self.category_keywords.items():
                if any(kw in desc for kw in keywords):
                    assigned = cat
                    break
            categories.append(assigned or ("finanzas" if amount > 0 else "otros"))
        self.dataframe["categoria"] = categories

    def compute_summaries(self) -> None:
        """Calcula totales por categoría y resumen mensual."""
        if "categoria" not in self.dataframe.columns:
            raise RuntimeError("Primero clasifica las transacciones con classify_transactions().")
        self.category_totals = (
            self.dataframe.groupby("categoria")["importe"]
            .sum()
            .reset_index()
            .sort_values("importe", ascending=False)
        )
        df = self.dataframe.copy()
        df["mes"] = df["fecha_operacion"].dt.to_period("M")
        self.monthly_summary_df = (
            df.pivot_table(index="mes", columns="categoria", values="importe", aggfunc="sum", fill_value=0)
            .sort_index()
        )

    def generate_tips(self) -> List[str]:
        """Genera consejos de ahorro basados en tus datos."""
        if self.category_totals is None:
            raise RuntimeError("Debe ejecutar compute_summaries() antes de generar consejos.")
        tips: List[str] = []
        ingresos = self.dataframe[self.dataframe["importe"] > 0]["importe"].sum()
        gastos = -self.dataframe[self.dataframe["importe"] < 0]["importe"].sum()
        ahorro_neto = ingresos - gastos
        if ingresos > 0:
            pct_nec = (
                -self.dataframe[
                    (self.dataframe["categoria"].isin({"alimentacion","servicios","salud","transporte","impuestos"}))
                    & (self.dataframe["importe"] < 0)
                ]["importe"].sum() / ingresos * 100
            )
            pct_ocio = (
                -self.dataframe[
                    (self.dataframe["categoria"].isin({"restauracion","ocio","compras","viajes","mascotas"}))
                    & (self.dataframe["importe"] < 0)
                ]["importe"].sum() / ingresos * 100
            )
            tips.append(f"Ahorro neto actual: {ahorro_neto:.2f} EUR. Necesidades {pct_nec:.1f}%, ocio {pct_ocio:.1f}%")
        com = self.dataframe[(self.dataframe["categoria"]=="finanzas")&(self.dataframe["importe"]<0)]
        if not com.empty:
            total_com = -com["importe"].sum()
            tips.append(f"Has pagado {total_com:.2f} EUR en comisiones bancarias. Considera un banco sin comisiones.")
        return tips

    def suggest_saving_plan(self) -> List[str]:
        """Sugiere cuánto ahorrar cada mes para llegar al 20%."""
        if self.monthly_summary_df is None:
            raise RuntimeError("Debe ejecutar compute_summaries() antes de planificar el ahorro.")
        df = self.dataframe.copy()
        df["mes"] = df["fecha_operacion"].dt.to_period("M")
        ingresos = df[df["importe"]>0].groupby("mes")["importe"].sum()
        gastos = -df[df["importe"]<0].groupby("mes")["importe"].sum()
        plans: List[str] = []
        for mes in sorted(ingresos.index.union(gastos.index)):
            ing = float(ingresos.get(mes,0))
            gst = float(gastos.get(mes,0))
            if ing==0:
                plans.append(f"Mes {mes}: sin ingresos registrados.")
                continue
            objetivo = ing*0.20
            real = ing-gst
            if real>=objetivo:
                plans.append(f"Mes {mes}: buen trabajo, ahorraste {real:,.2f} EUR (objetivo {objetivo:,.2f} EUR).")
            else:
                falta = objetivo-real
                plans.append(f"Mes {mes}: intenta ahorrar {falta:,.2f} EUR más para alcanzar el 20% ({objetivo:,.2f} EUR).")
        return plans

    def detect_subscriptions(self, amount_tolerance: float = 2.0) -> pd.DataFrame:
        """Detecta cargos periódicos con importe similar (±tolerancia)."""
        if self.dataframe.empty:
            raise RuntimeError("Cargue y clasifique primero las transacciones.")
        df = self.dataframe[self.dataframe["importe"]<0].copy()
        df["desc_norm"] = df["concepto"].apply(_normalize_description)
        subs = []
        for desc, grp in df.groupby("desc_norm"):
            if len(grp)<2 or grp["importe"].std()>amount_tolerance:
                continue
            fechas = grp["fecha_operacion"].sort_values()
            diffs = fechas.diff().dt.days.dropna()
            if len(diffs)<2:
                continue
            med = diffs.median()
            if 25<=med<=35:
                freq="mensual"
            elif 85<=med<=95:
                freq="trimestral"
            elif 355<=med<=375:
                freq="anual"
            else:
                continue
            subs.append({
                "descripcion": desc,
                "importe_medio": round(grp["importe"].mean(),2),
                "frecuencia": freq,
                "veces": len(grp),
                "primer_pago": fechas.min().date().isoformat(),
                "ultimo_pago": fechas.max().date().isoformat()
            })
        return pd.DataFrame(subs)


def main(argv: List[str]) -> int:
    if len(argv)!=2:
        print("Uso: python financial_assistant.py <fichero.csv|xls>")
        return 1
    assistant = FinancialAssistant(argv[1])
    try:
        assistant.load_transactions()
        assistant.classify_transactions()
        assistant.compute_summaries()
        tips = assistant.generate_tips()
        plans = assistant.suggest_saving_plan()
        subs = assistant.detect_subscriptions()
        print("\n=== Resumen de ingresos y gastos ===")
        print(f"Ingresos totales: {assistant.dataframe[assistant.dataframe['importe']>0]['importe'].sum():,.2f} EUR")
        print(f"Gastos totales: {-assistant.dataframe[assistant.dataframe['importe']<0]['importe'].sum():,.2f} EUR")
        print(f"Ahorro neto: {(assistant.dataframe[assistant.dataframe['importe']>0]['importe'].sum() + assistant.dataframe[assistant.dataframe['importe']<0]['importe'].sum()):,.2f} EUR")
        print("\nSuscripciones detectadas:")
        print(subs.to_string(index=False) if not subs.empty else "  (ninguna)")
        print("\nConsejos:")
        for i, t in enumerate(tips,1):
            print(f"{i}. {t}")
        print("\nPlan de ahorro:")
        for p in plans:
            print(f"- {p}")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    return 0

if __name__=="__main__":
    sys.exit(main(sys.argv))