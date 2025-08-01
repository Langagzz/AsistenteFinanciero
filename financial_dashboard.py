# financial_dashboard.py
# ----------------------
#
# Este script crea una interfaz web sencilla utilizando Streamlit para analizar
# extractos bancarios. Permite al usuario subir su fichero de movimientos, ver
# resúmenes de ingresos y gastos, gráficos interactivos por categorías y meses,
# suscripciones recurrentes y recibir consejos y planes de ahorro sugeridos.

import os
import tempfile

import streamlit as st
import pandas as pd
import plotly.express as px

from financial_assistant import FinancialAssistant
import detect_subs  # módulo para detectar suscripciones

def main():
    st.set_page_config(page_title="Asistente financiero", layout="wide")
    st.title("Asistente financiero y analizador de gastos")
    st.write(
        "Carga tu extracto bancario y obtén un análisis visual de tus movimientos, "
        "suscripciones mensuales, consejos de ahorro y planes para alcanzar tus objetivos."
    )

    # Cargador de archivos
    uploaded_file = st.file_uploader(
        "Sube tu extracto bancario en formato Excel (.xls, .xlsx) o CSV", 
        type=["xls", "xlsx", "csv"]
    )

    if uploaded_file is None:
        st.info("Por favor, sube un archivo para comenzar el análisis.")
        return

    # Guardamos el archivo en un fichero temporal
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmpfile:
        tmpfile.write(uploaded_file.getvalue())
        tmp_path = tmpfile.name

    # Instanciamos y procesamos con FinancialAssistant
    assistant = FinancialAssistant(tmp_path)
    try:
        assistant.load_transactions()
        assistant.classify_transactions()
        assistant.compute_summaries()
    except Exception as e:
        st.error(f"Error al procesar el fichero: {e}")
        return

    # 1) Tabla de movimientos
    st.header("Movimientos bancarios")
    st.dataframe(
        assistant.dataframe[
            ['fecha_operacion', 'concepto', 'importe', 'categoria']
        ].sort_values('fecha_operacion', ascending=False)
    )

    # 2) Métricas de ingresos/gastos
    ingresos = assistant.dataframe[assistant.dataframe['importe'] > 0]['importe'].sum()
    gastos   = assistant.dataframe[assistant.dataframe['importe'] < 0]['importe'].sum()
    ahorro   = ingresos + gastos
    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos totales", f"{ingresos:,.2f} €")
    col2.metric("Gastos totales", f"{gastos:,.2f} €")
    col3.metric("Ahorro neto",     f"{ahorro:,.2f} €")

    # 3) Gráfico por categoría
    cat_tot = assistant.category_totals.copy()
    cat_tot['signo'] = cat_tot['importe'].apply(lambda x: 'Ingresos' if x >= 0 else 'Gastos')
    fig_bar = px.bar(
        cat_tot, x='categoria', y='importe', color='signo',
        title='Totales por categoría',
        labels={'importe':'Importe (€)','categoria':'Categoría'}
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # 4) Evolución mensual de gastos
    monthly = assistant.monthly_summary_df.copy().astype(float)
    monthly.index = monthly.index.astype(str)
    gastos_mens = monthly.applymap(lambda x: x if x < 0 else 0)
    df_melt = gastos_mens.reset_index().melt(
        id_vars='mes', var_name='Categoría', value_name='Importe'
    )
    fig_area = px.area(
        df_melt, x='mes', y='Importe', color='Categoría',
        title='Evolución mensual de los gastos por categoría',
        labels={'mes':'Mes','Importe':'Importe (€)'}
    )
    st.plotly_chart(fig_area, use_container_width=True)

    # 5) Suscripciones mensuales
    st.header("Suscripciones mensuales")
    try:
        df_subs = detect_subs.detect_subscriptions(tmp_path)
        if df_subs.empty:
            st.info("No se detectaron suscripciones recurrentes mensuales.")
        else:
            # Formato visual
            df_subs_display = df_subs.rename(columns={
                'concepto': 'Concepto',
                'importe': 'Importe (€)',
                'first_date': 'Desde',
                'last_date': 'Hasta',
                'meses_distintos': 'Veces detectadas'
            })
            st.dataframe(df_subs_display)
    except Exception as e:
        st.error(f"Error al detectar suscripciones: {e}")

    # 6) Consejos y planes de ahorro
    st.header("Consejos para tu economía")
    tips = assistant.generate_tips()
    for tip in tips:
        st.markdown(f"- {tip}")

    st.header("Planes de ahorro sugeridos")
    try:
        plans = assistant.suggest_saving_plan()
        if plans:
            for plan in plans:
                st.markdown(f"- {plan}")
        else:
            st.info("No hay planes de ahorro sugeridos disponibles.")
    except AttributeError:
        st.info("No está disponible la función de planes de ahorro.")
    except Exception as e:
        st.error(f"Error al generar planes de ahorro: {e}")

if __name__ == "__main__":
    main()
