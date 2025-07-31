"""
financial_dashboard.py
----------------------

Este script crea una interfaz web sencilla utilizando Streamlit para analizar
extractos bancarios. Permite al usuario subir su fichero de movimientos, ver
resúmenes de ingresos y gastos, gráficos interactivos por categorías y meses,
y recibir consejos y planes de ahorro sugeridos basados en los datos.

Para ejecutar la aplicación:

    pip install streamlit plotly pandas numpy xlrd openpyxl
    streamlit run financial_dashboard.py

La aplicación se abrirá en tu navegador predeterminado (normalmente en
http://localhost:8501). Carga tu extracto bancario (en formato Excel o CSV) y
obtendrás un análisis visual de tus gastos.
"""

import os
import tempfile
import streamlit as st
import pandas as pd
import plotly.express as px

from financial_assistant import FinancialAssistant


def main():
    st.set_page_config(page_title="Asistente financiero", layout="wide")
    st.title("Asistente financiero y analizador de gastos")
    st.write(
        "Carga tu extracto bancario y obtén un análisis visual de tus movimientos, consejos de ahorro y planes para alcanzar tus objetivos."
    )

    # Cargador de archivos
    uploaded_file = st.file_uploader(
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

        # Consejos para tu economía
        tips = assistant.generate_tips()
        for tip in tips:
            st.markdown(f"- {tip}")

                # Suscripciones recurrentes
        st.header("Suscripciones mensuales")
        df = assistant.dataframe.copy()
        # Suscripciones explícitas
        subs_cat = df[df['categoria'] == 'Suscripciones']
        # Detección heurística: pagos recurrentes (mismo concepto e importe 2+ veces)
        recurring = (
            df.groupby(['concepto', 'importe'])
              .agg(count=('fecha_operacion', 'count'), primera_fecha=('fecha_operacion', 'min'))
              .reset_index()
        )
        subs_rec = recurring[recurring['count'] >= 2]
        # Combinar ambas fuentes y eliminar duplicados
        subs_combined = pd.concat([
            subs_cat[['concepto', 'importe', 'fecha_operacion']],
            subs_rec.rename(columns={'primera_fecha': 'fecha_operacion'})[['concepto', 'importe', 'fecha_operacion']]
        ], ignore_index=True).drop_duplicates(['concepto','importe'])

        if not subs_combined.empty:
            # Preparamos tabla
            summary = (
                subs_combined
                  .groupby(['concepto','importe'])
                  .agg(Desde=('fecha_operacion','min'), Cuotas=('concepto','count'))
                  .reset_index()
                  .sort_values('Desde')
            )
            summary = summary.rename(columns={
                'concepto':'Suscripción', 'importe':'Importe (€)','Desde':'Desde','Cuotas':'Cuotas detectadas'
            })
            st.table(summary)
        else:
            st.info("No se detectan suscripciones recurrentes. Ajusta tus palabras clave o añade más conceptos.")

        # Planes de ahorro sugeridos
        st.header("Planes de ahorro sugeridos")
        try:
            plans = assistant.suggest_saving_plan()
        except Exception:
            # ... existing fallback logic
            gastos_mensuales = assistant.monthly_summary_df.apply(
                lambda row: -row[row < 0].sum(), axis=1
            )
            gasto_medio = gastos_mensuales.mean()
            total_ingresos = assistant.dataframe[assistant.dataframe.importe > 0].importe.sum()
            total_gastos = assistant.dataframe[assistant.dataframe.importe < 0].importe.sum()
            ahorro_mensual = total_ingresos + total_gastos

            plans = []
            if ahorro_mensual > 0:
                fondo_obj = gasto_medio * 3
                meses_fondo = fondo_obj / ahorro_mensual
                plans.append(
                    f"Objetivo: fondo de emergencia de {fondo_obj:.2f} € (≈3 meses de gastos medios). Con tu ahorro mensual de {ahorro_mensual:.2f} € lo lograrías en {meses_fondo:.1f} meses."
                )
                vac_obj = gasto_medio
                percent = 0.10
                aportacion = total_ingresos * percent
                meses_vac = vac_obj / aportacion if aportacion > 0 else float('inf')
                plans.append(
                    f"Objetivo: reservar {vac_obj:.2f} € para vacaciones. Si apartas el {int(percent*100)}% de tus ingresos ({aportacion:.2f} €), lo lograrás en {meses_vac:.1f} meses."
                )
            else:
                plans.append("No detecto ahorro mensual positivo. Revisa tus ingresos o gastos.")
        for plan in plans:
            st.markdown(f"- {plan}")
    else:
        st.info(
            "Por favor, sube un archivo para comenzar el análisis. Puedes exportar tu extracto bancario desde tu banco en formato Excel o CSV."
        )

if __name__ == "__main__":
    main()