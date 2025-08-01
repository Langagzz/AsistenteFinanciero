"""
financial_dashboard.py
----------------------

Este script crea una interfaz web sencilla utilizando Streamlit para analizar
extractos bancarios. Permite al usuario subir su fichero de movimientos, ver
resúmenes de ingresos y gastos, gráficos interactivos por categorías y meses,
y recibir consejos y planes de ahorro sugeridos basados en los datos.

Para ejecutar la aplicación:

    pip install streamlit plotly pandas numpy xlrd
    pip install streamlit plotly pandas xlrd
    streamlit run financial_dashboard.py

La aplicación se abrirá en tu navegador predeterminado (normalmente en
http://localhost:8501). Carga tu extracto bancario (en formato Excel o CSV) y
obtendrás un análisis visual de tus gastos.
"""
"""Streamlit dashboard for the financial assistant."""

import os
import tempfile
import streamlit as st

import pandas as pd
import plotly.express as px
import streamlit as st

from financial_assistant import FinancialAssistant


def main():
def main() -> None:
    st.set_page_config(page_title="Asistente financiero", layout="wide")
    st.title("Asistente financiero y analizador de gastos")
    st.write(
        "Carga tu extracto bancario y obtén un análisis visual de tus movimientos, consejos de ahorro y planes para alcanzar tus objetivos."
    )

    # Cargador de archivos
    uploaded_file = st.file_uploader(
@@ -39,104 +39,103 @@ def main():
        "Sube tu extracto bancario en formato Excel (.xls, .xlsx) o CSV", type=["xls", "xlsx", "csv"]
    )

    if uploaded_file is not None:
        # Guardamos el archivo en un fichero temporal
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmpfile:
            tmpfile.write(uploaded_file.getvalue())
            tmp_path = tmpfile.name

        # Procesamos el extracto con FinancialAssistant
        assistant = FinancialAssistant(tmp_path)
        try:
            assistant.load_transactions()
            assistant.classify_transactions()
            assistant.compute_summaries()
        except Exception as e:
            st.error(f"Error al procesar el fichero: {e}")
            return

        # Mostrar tabla de movimientos
        st.header("Movimientos bancarios")
        st.dataframe(assistant.dataframe[['fecha_operacion', 'concepto', 'importe', 'categoria']])

        # Resumen de ingresos/gastos
        total_ingresos = assistant.dataframe[assistant.dataframe['importe'] > 0]['importe'].sum()
        total_gastos = assistant.dataframe[assistant.dataframe['importe'] < 0]['importe'].sum()
        ahorro = total_ingresos + total_gastos
        total_gastos = -assistant.dataframe[assistant.dataframe['importe'] < 0]['importe'].sum()
        ahorro = total_ingresos - total_gastos
        col1, col2, col3 = st.columns(3)
        col1.metric("Ingresos totales", f"{total_ingresos:,.2f} €")
        col2.metric("Gastos totales", f"{total_gastos:,.2f} €")
        col3.metric("Ahorro neto", f"{ahorro:,.2f} €")

        # Gráfico de barras de gastos/ingresos por categoría
        cat_totals = assistant.category_totals.copy()
        cat_totals['signo'] = cat_totals['importe'].apply(lambda x: 'Ingresos' if x >= 0 else 'Gastos')
        fig_bar = px.bar(
            cat_totals,
            x='categoria',
            y='importe',
            color='signo',
            title='Totales por categoría',
            labels={'importe': 'Importe (€)', 'categoria': 'Categoría'},
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Gráfico de líneas o áreas por mes y categoría (solo gastos negativos)
        monthly = assistant.monthly_summary_df.copy().astype(float)
        monthly.index = monthly.index.astype(str)
        gastos_mensuales = monthly.applymap(lambda x: x if x < 0 else 0)
        fig_area = px.area(
            gastos_mensuales.reset_index().melt(id_vars='mes', var_name='Categoría', value_name='Importe'),
            x='mes',
            y='Importe',
            color='Categoría',
            title='Evolución mensual de los gastos por categoría',
            labels={'mes': 'Mes', 'Importe': 'Importe (€)'},
        )
        st.plotly_chart(fig_area, use_container_width=True)

        # Consejos y planes de ahorro
        st.header("Consejos para tu economía")
        tips = assistant.generate_tips()
        for tip in tips:
            st.markdown(f"- {tip}")

        # Detección automática de suscripciones periódicas
        import numpy as np
        st.header("Suscripciones mensuales")
        df_sub = assistant.dataframe.copy()
        df_sub['fecha_operacion'] = pd.to_datetime(df_sub['fecha_operacion'])
        subs = []
        for (desc, imp), grupo in df_sub.groupby(['concepto', 'importe']):
            fechas = grupo['fecha_operacion'].sort_values()
            diffs = fechas.diff().dt.days.dropna()
            if len(diffs) >= 2:
                med = diffs.median()
                if 25 <= med <= 35:
                    subs.append({
                        'Suscripción': desc,
                        'Importe (€)': imp,
                        'Primer pago': fechas.min(),
                        'Último pago': fechas.max(),
                        'Veces detectadas': int(len(grupo)),
                        'Intervalo medio (días)': int(med)
                    })
        if subs:
            subs_df = pd.DataFrame(subs)
            st.table(subs_df)
        else:
            st.info("No se detectan suscripciones periódicas automáticas.")

        # Planes de ahorro sugeridos
        st.header("Planes de ahorro sugeridos")
        plans = assistant.suggest_saving_plan() if hasattr(assistant, 'suggest_saving_plan') else []
        plans = assistant.suggest_saving_plan()
        for plan in plans:
            st.markdown(f"- {plan}")

    else:
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
