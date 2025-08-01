# financial_dashboard.py

import os
import tempfile

import streamlit as st
import pandas as pd
import plotly.express as px

from financial_assistant import FinancialAssistant
import detect_subs  # <-- Asegúrate de que detect_subs.py está en el mismo directorio

def main():
    st.set_page_config(page_title="Asistente financiero", layout="wide")
    st.title("Asistente financiero y analizador de gastos")
    st.write(
        "Carga tu extracto bancario y obtén un análisis visual de tus movimientos, consejos de ahorro, planes y suscripciones."
    )

    # Cargador de archivos
    uploaded_file = st.file_uploader(
        "Sube tu extracto bancario (Excel o CSV)", type=["xls", "xlsx", "csv"]
    )

    if uploaded_file is None:
        st.info("Por favor, sube un archivo para comenzar.")
        return

    # Guardar en fichero temporal
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmpfile:
        tmpfile.write(uploaded_file.getvalue())
        tmp_path = tmpfile.name

    # Procesar con FinancialAssistant
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
    ahorro_neto = total_ingresos + total_gastos
    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos totales", f"{total_ingresos:,.2f} €")
    col2.metric("Gastos totales", f"{total_gastos:,.2f} €")
    col3.metric("Ahorro neto", f"{ahorro_neto:,.2f} €")

    # Gráfico por categoría
    cat_totals = assistant.category_totals.copy()
    cat_totals['signo'] = cat_totals['importe'].apply(lambda x: 'Ingresos' if x >= 0 else 'Gastos')
    fig_bar = px.bar(
        cat_totals, x='categoria', y='importe', color='signo',
        title='Totales por categoría', labels={'importe': 'Importe (€)', 'categoria': 'Categoría'}
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # Evolución mensual gastos
    monthly = assistant.monthly_summary_df.copy().astype(float)
    monthly.index = monthly.index.astype(str)
    gastos_mensuales = monthly.applymap(lambda x: x if x < 0 else 0)
    fig_area = px.area(
        gastos_mensuales.reset_index().melt(id_vars='mes', var_name='Categoría', value_name='Importe'),
        x='mes', y='Importe', color='Categoría',
        title='Evolución mensual de gastos por categoría',
        labels={'mes': 'Mes', 'Importe': 'Importe (€)'}
    )
    st.plotly_chart(fig_area, use_container_width=True)

    # Consejos y planes de ahorro
    st.header("Consejos para tu economía")
    tips = assistant.generate_tips()
    for tip in tips:
        st.markdown(f"- {tip}")

    st.header("Planes de ahorro sugeridos")
    plans = assistant.suggest_saving_plan() if hasattr(assistant, 'suggest_saving_plan') else []
    if plans:
        for plan in plans:
            st.markdown(f"- {plan}")
    else:
        st.info("No hay planes de ahorro sugeridos.")

    # ----------------------------------------------------
    #  NUEVO BLOQUE: SUSCRIPCIONES MENSUALES
    # ----------------------------------------------------
    st.header("Suscripciones mensuales")
    df_subs = detect_subs.detect_subscriptions(tmp_path)
    if not df_subs.empty:
        df_subs['Desde'] = pd.to_datetime(df_subs['Desde']).dt.date
        st.dataframe(df_subs)
    else:
        st.info(
            "No se detectaron suscripciones mensuales. "
            "Revisa las palabras clave en detect_subs.py si falta alguna."
        )

if __name__ == "__main__":
    main()
