"""Streamlit dashboard for the financial assistant."""

import os
import tempfile

import pandas as pd
import plotly.express as px
import streamlit as st

from financial_assistant import FinancialAssistant


def main() -> None:
    """Run the Streamlit dashboard application.

    This function loads the user-uploaded bank statement, analyzes the
    transactions using :class:`FinancialAssistant` and displays charts
    and tips in a Streamlit interface.
    """
    st.set_page_config(page_title="Asistente financiero", layout="wide")
    st.title("Asistente financiero y analizador de gastos")
    st.write(
        "Carga tu extracto bancario y obtén un análisis visual de tus movimientos, consejos de ahorro y planes para alcanzar tus objetivos."
    )

    uploaded_file = st.file_uploader(
        "Sube tu extracto bancario en formato Excel (.xls, .xlsx) o CSV", type=["xls", "xlsx", "csv"]
    )

    if uploaded_file is None:
        st.info(
            "Por favor, sube un archivo para comenzar el análisis. Puedes exportar tu extracto bancario desde tu banco en formato Excel o CSV."
        )
        return

    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmpfile:
        tmpfile.write(uploaded_file.getvalue())
        tmp_path = tmpfile.name

    assistant = FinancialAssistant(tmp_path)
    try:
        assistant.load_transactions()
        assistant.classify_transactions()
        assistant.compute_summaries()
    except Exception as e:
        st.error(f"Error al procesar el fichero: {e}")
        return

    st.header("Movimientos bancarios")
    st.dataframe(assistant.dataframe[["fecha_operacion", "concepto", "importe", "categoria"]])

    total_ingresos = assistant.dataframe[assistant.dataframe["importe"] > 0]["importe"].sum()
    total_gastos = -assistant.dataframe[assistant.dataframe["importe"] < 0]["importe"].sum()
    ahorro = total_ingresos - total_gastos
    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos totales", f"{total_ingresos:,.2f} €")
    col2.metric("Gastos totales", f"{total_gastos:,.2f} €")
    col3.metric("Ahorro neto", f"{ahorro:,.2f} €")

    cat_totals = assistant.category_totals.copy()
    cat_totals["signo"] = cat_totals["importe"].apply(lambda x: "Ingresos" if x >= 0 else "Gastos")
    fig_bar = px.bar(
        cat_totals,
        x="categoria",
        y="importe",
        color="signo",
        title="Totales por categoría",
        labels={"importe": "Importe (€)", "categoria": "Categoría"},
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    monthly = assistant.monthly_summary_df.copy().astype(float)
    monthly.index = monthly.index.astype(str)
    gastos_mensuales = monthly.applymap(lambda x: x if x < 0 else 0)
    fig_area = px.area(
        gastos_mensuales.reset_index().melt(id_vars="mes", var_name="Categoría", value_name="Importe"),
        x="mes",
        y="Importe",
        color="Categoría",
        title="Evolución mensual de los gastos por categoría",
        labels={"mes": "Mes", "Importe": "Importe (€)"},
    )
    st.plotly_chart(fig_area, use_container_width=True)

    st.header("Consejos para tu economía")
    for tip in assistant.generate_tips():
        st.markdown(f"- {tip}")

    st.header("Suscripciones detectadas")
    subs_df = assistant.detect_subscriptions()
    if subs_df.empty:
        st.info("No se detectan suscripciones periódicas automáticas.")
    else:
        st.table(subs_df)

    st.header("Planes de ahorro sugeridos")
    for plan in assistant.suggest_saving_plan():
        st.markdown(f"- {plan}")


if __name__ == "__main__":
    main()
