"""Streamlit dashboard for the financial assistant."""

import os
import tempfile

import pandas as pd
import plotly.express as px
import streamlit as st

from financial_assistant import FinancialAssistant

def main() -> None:
    """Run the Streamlit dashboard application."""
    st.set_page_config(page_title="Asistente financiero", layout="wide")
    st.title("Asistente financiero y analizador de gastos")
    st.write(
        "Carga tu extracto bancario y obtén un análisis visual de tus movimientos, "
        "consejos de ahorro, suscripciones y planes para alcanzar tus objetivos."
    )

    uploaded_file = st.file_uploader(
        "Sube tu extracto bancario (.xls, .xlsx, .csv)", type=["xls", "xlsx", "csv"]
    )
    if not uploaded_file:
        st.info("Por favor, sube un archivo para comenzar el análisis.")
        return

    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    assistant = FinancialAssistant(tmp_path)
    try:
        assistant.load_transactions()
        assistant.classify_transactions()
        assistant.compute_summaries()
    except Exception as e:
        st.error(f"Error al procesar el fichero: {e}")
        return

    # Tabla de movimientos
    st.header("Movimientos bancarios")
    st.dataframe(assistant.dataframe[["fecha_operacion", "concepto", "importe", "categoria"]])

    # Métricas
    ingresos = assistant.dataframe[assistant.dataframe["importe"]>0]["importe"].sum()
    gastos = -assistant.dataframe[assistant.dataframe["importe"]<0]["importe"].sum()
    ahorro = ingresos - gastos
    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos totales", f"{ingresos:,.2f} €")
    c2.metric("Gastos totales", f"{gastos:,.2f} €")
    c3.metric("Ahorro neto", f"{ahorro:,.2f} €")

    # Gráfica por categorías
    cat_totals = assistant.category_totals.copy()
    cat_totals["signo"] = cat_totals["importe"].apply(lambda x: "Ingresos" if x>=0 else "Gastos")
    fig1 = px.bar(cat_totals, x="categoria", y="importe", color="signo",
                  title="Totales por categoría",
                  labels={"importe":"Importe (€)","categoria":"Categoría"})
    st.plotly_chart(fig1, use_container_width=True)

    # Evolución mensual de gastos
    monthly = assistant.monthly_summary_df.copy().astype(float)
    monthly.index = monthly.index.astype(str)
    gastos_m = monthly.applymap(lambda x: x if x<0 else 0)
    df_melt = gastos_m.reset_index().melt(id_vars="mes", var_name="Categoría", value_name="Importe")
    fig2 = px.area(df_melt, x="mes", y="Importe", color="Categoría",
                   title="Evolución mensual de gastos por categoría",
                   labels={"mes":"Mes","Importe":"Importe (€)"})
    st.plotly_chart(fig2, use_container_width=True)

    # Consejos
    st.header("Consejos para tu economía")
    for tip in assistant.generate_tips():
        st.markdown(f"- {tip}")

    # Suscripciones
    st.header("Suscripciones detectadas")
    subs_df = assistant.detect_subscriptions()
    if subs_df.empty:
        st.info("No se detectan suscripciones periódicas automáticas.")
    else:
        st.table(subs_df)

    # Planes de ahorro
    st.header("Planes de ahorro sugeridos")
    for plan in assistant.suggest_saving_plan():
        st.markdown(f"- {plan}")

if __name__=="__main__":
    main()
