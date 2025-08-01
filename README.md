# Asistente Financiero

Este proyecto ofrece dos utilidades principales para analizar tus movimientos bancarios:

- **financial_assistant.py**: herramienta de línea de comandos que carga un extracto bancario (CSV o Excel), clasifica los movimientos por categorías (también reconoce devoluciones), resume ingresos y gastos y genera consejos y un plan de ahorro.
- **financial_dashboard.py**: interfaz web construida con Streamlit que permite subir un archivo y visualizar gráficas interactivas, además de obtener consejos y un plan de ahorro mensual.

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Uso

Para ejecutar el asistente en consola y obtener un resumen junto con consejos y un plan de ahorro (debes indicar la ruta al archivo de movimientos):

```bash
python financial_assistant.py ruta/al/archivo.xls
```

El programa mostrará un resumen de gastos e ingresos, consejos personalizables y un plan de ahorro mensual basado en tus datos.

Para lanzar el dashboard interactivo:

```bash
streamlit run financial_dashboard.py
```

Aparecerá una página web donde podrás cargar tu extracto bancario y consultar el análisis.
