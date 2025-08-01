# financial_dashboard.py

import os
import tempfile
import streamlit as st
import pandas as pd
import plotly.express as px

from financial_assistant import FinancialAssistant
import detect_subs

def main():
    st.set_page_config(page_title="Asistente financiero", layout="wide")
    st.title("Asistente financiero y analizador de gastos")

    uploaded_file = st.file_uploader(
        "Sube tu extracto bancario (Excel o CSV)", type=["xls", "xlsx", "csv"]
    )

    if uploaded_file is None:
        st.info("Por favor, sube un archivo para comenzar el análisis.")
        return

    # Guardamos temporalmente
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    # Procesamos
    assistant = FinancialAssistant(tmp_path)
    try:
        assistant.load_transactions()
        assistant.classify_transactions()
        assistant.compute_summaries()
    except Exception as e:
        st.error(f"Error al procesar movimientos: {e}")
        return

    # Tabla de movimientos
    st.header("Movimientos bancarios")
    st.dataframe(assistant.dataframe[['fecha_operacion','concepto','importe','categoria']])

    # Métricas
    total_ingresos = assistant.dataframe[assistant.dataframe['importe'] > 0]['importe'].sum()
    total_gastos   = assistant.dataframe[assistant.dataframe['importe'] < 0]['importe'].sum()
    ahorro         = total_ingresos + total_gastos
    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos totales", f"{total_ingresos:,.2f} €")
    col2.metric("Gastos totales", f"{total_gastos:,.2f} €")
    col3.metric("Ahorro neto",    f"{ahorro:,.2f} €")

    # Gráficos
    cat_totals = assistant.category_totals.copy()
    cat_totals['signo'] = cat_totals['importe'].apply(lambda x: 'Ingresos' if x>=0 else 'Gastos')
    fig_bar = px.bar(cat_totals, x='categoria', y='importe', color='signo',
                     title='Totales por categoría', labels={'importe':'Importe (€)','categoria':'Categoría'})
    st.plotly_chart(fig_bar, use_container_width=True)

    monthly = assistant.monthly_summary_df.copy()
    monthly.index = monthly.index.astype(str)
    gastos_mensuales = monthly.applymap(lambda x: x if x<0 else 0)
    fig_area = px.area(
        gastos_mensuales.reset_index().melt(id_vars='mes', var_name='Categoría', value_name='Importe'),
        x='mes', y='Importe', color='Categoría',
        title='Evolución mensual de gastos por categoría',
        labels={'mes':'Mes','Importe':'Importe (€)'}
    )
    st.plotly_chart(fig_area, use_container_width=True)

    # Consejos y planes de ahorro
    st.header("Consejos para tu economía")
    tips = assistant.generate_tips()
    for tip in tips:
        st.markdown(f"- {tip}")

    # Suscripciones
    st.header("Suscripciones mensuales")
    try:
        df_subs = detect_subs.detect_subscriptions(tmp_path)
        if df_subs.empty:
            st.info("No se detectaron suscripciones mensuales.")
        else:
            df_subs = df_subs.rename(columns={
                'concepto_norm':'Suscripción',
                'importe':'Importe (€)',
                'meses_distintos':'Mensualidades',
                'total_cargos':'Total pagos',
                'primer_pago':'Desde',
                'ultimo_pago':'Último pago'
            })
            st.dataframe(df_subs, use_container_width=True)
    except Exception as e:
        st.error(f"Error al detectar suscripciones: {e}")

    # Planes de ahorro
    st.header("Planes de ahorro sugeridos")
    plans = assistant.suggest_saving_plan()
    for plan in plans:
        st.markdown(f"- {plan}")

if __name__ == "__main__":
    main()
