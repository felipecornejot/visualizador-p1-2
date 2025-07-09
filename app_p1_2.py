import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from io import BytesIO
import requests

# --- Paleta de Colores ---
# Definición de colores en formato RGB (0-1) para Matplotlib
color_primario_1_rgb = (14/255, 69/255, 74/255) # 0E454A (Oscuro)
color_primario_2_rgb = (31/255, 255/255, 95/255) # 1FFF5F (Verde vibrante)
color_primario_3_rgb = (255/255, 255/255, 255/255) # FFFFFF (Blanco)

# Colores del logo de Sustrend para complementar
color_sustrend_1_rgb = (0/255, 155/255, 211/255) # 009BD3 (Azul claro)
color_sustrend_2_rgb = (0/255, 140/255, 207/255) # 008CCF (Azul medio)
color_sustrend_3_rgb = (0/255, 54/255, 110/255) # 00366E (Azul oscuro)

# Selección de colores para los gráficos
# Usaré una combinación de los colores primarios y Sustrend para contraste
colors_for_charts = [color_primario_1_rgb, color_primario_2_rgb, color_sustrend_1_rgb, color_sustrend_3_rgb]

# --- Configuración de la página de Streamlit ---
st.set_page_config(layout="wide")

st.title('✨ Visualizador de Impactos - Proyecto P1.2')
st.subheader('Reducción del uso de sorbato de potasio en ciruelas deshidratadas mediante aspersión electrostática')
st.markdown("""
    Ajusta los parámetros para explorar cómo las proyecciones de impacto ambiental y económico del proyecto
    varían con diferentes escenarios de volumen procesado, porcentaje de reducción de sorbato y porcentaje de devoluciones evitadas.
""")

# --- 1. Datos del Proyecto (Línea Base y Proyecciones) ---
# Datos extraídos de la ficha técnica P1.2
data_p12 = {
    "indicador": [
        "Reducción en el uso de sorbato de potasio (kg/año)",
        "GEI evitados por transporte de devoluciones (tCO₂e/año)",
        "Ahorro en costos por sorbato de potasio (USD/año)",
        "Pérdida y desperdicio de alimentos (PDA) evitado (ton/año)",
        "Pérdidas económicas asociadas a la PDA evitada (USD/año)"
    ],
    "unidad": ["kg/año", "tCO₂e/año", "USD/año", "ton/año", "USD/año"],
    "valor_base_ficha_ejemplo": [
        1600, # Para 1000 ton de producción y reducción de 1.6 g/kg
        6,    # Para 5% de 50 ton y 12000 km
        8000, # Para 1000 ton de producción y reducción del 40% (1.6 kg/ton * $5/kg)
        50,   # Rango 25-50 ton/año, tomamos 50 como ejemplo alto
        160000 # Para 50 ton * $3200/ton
    ],
    "produccion_anual_ejemplo_ton": [
        1000, # para sorbato
        1000, # para GEI (asumiendo 50 ton evitado de un envío de 1000 ton)
        1000, # para ahorro sorbato
        None, # PDA ejemplo no especifica volumen de exportacion
        None  # PDA económica ejemplo no especifica volumen de exportacion
    ],
    "dosis_sorbato_conv_g_kg": [4, None, None, None, None], # 4 g/kg de ficha
    "dosis_sorbato_opt_g_kg": [2.4, None, None, None, None], # 2.4 g/kg de ficha
    "precio_sorbato_usd_kg": [None, None, 5, None, None],
    "porcentaje_rechazo_evitado_transporte": [5, None, None, None, None], # 5% de la ficha
    "volumen_envio_rechazado_ejemplo_ton": [50, None, None, None, None], # 50 ton de la ficha
    "distancia_transporte_km": [12000, None, None, None, None],
    "factor_emision_co2e_ton_km": [0.01, None, None, None, None],
    "precio_ciruela_exportacion_usd_ton": [None, None, None, None, 3200],
    "rango_pda_evitada_min_ton": [None, None, None, 25, None],
    "rango_pda_evitada_max_ton": [None, None, None, 50, None],
}

df_diagnostico_p12 = pd.DataFrame(data_p12)

# --- 2. Widgets Interactivos para Parámetros (Streamlit) ---
st.sidebar.header('Parámetros de Simulación')

produccion_anual = st.sidebar.slider(
    'Producción Anual (ton):',
    min_value=100,
    max_value=5000,
    value=1000,
    step=100,
    help="Volumen total de ciruelas procesadas anualmente."
)

porcentaje_reduccion_sorbato = st.sidebar.slider(
    'Reducción Sorbato (%):',
    min_value=20.0,
    max_value=60.0,
    value=40.0,
    step=1.0,
    help="Porcentaje de reducción en el uso de sorbato de potasio."
)

porcentaje_devoluciones_evitadas = st.sidebar.slider(
    'Devoluciones Evitadas (% del envío rechazado):',
    min_value=0.0,
    max_value=10.0,
    value=5.0,
    step=0.5,
    help="Porcentaje de envíos rechazados que se evitan gracias a la tecnología."
)

precio_ciruela = st.sidebar.slider(
    'Precio Ciruela Exportación (USD/ton):',
    min_value=2000,
    max_value=5000,
    value=3200,
    step=100,
    help="Precio promedio de exportación de la tonelada de ciruela."
)

# --- 3. Cálculos de Indicadores ---

# Reducción sorbato (kg/año)
dosis_conv_g_kg = df_diagnostico_p12.loc[0, 'dosis_sorbato_conv_g_kg']
dosis_optim_g_kg = dosis_conv_g_kg * (1 - porcentaje_reduccion_sorbato / 100)
reduccion_sorbato_kg_año = (dosis_conv_g_kg - dosis_optim_g_kg) * produccion_anual / 1000 # Convertir g/kg a kg/ton

# Ahorro en costos por sorbato (USD/año)
precio_sorbato = df_diagnostico_p12.loc[2, 'precio_sorbato_usd_kg']
ahorro_costos_sorbato_usd_año = reduccion_sorbato_kg_año * precio_sorbato

# PDA evitado (ton/año)
# Usaremos el rango de PDA evitada de la ficha (25-50 ton) como base y ajustaremos con el % de devoluciones evitadas
# sobre el volumen anual para una estimación.
pda_evitada_ton_año = (porcentaje_devoluciones_evitadas / df_diagnostico_p12.loc[1, 'porcentaje_rechazo_evitado_transporte']) * df_diagnostico_p12.loc[1, 'volumen_envio_rechazado_ejemplo_ton']
pda_evitada_ton_año = min(pda_evitada_ton_año, df_diagnostico_p12.loc[3, 'rango_pda_evitada_max_ton'])


# GEI evitados por transporte (tCO₂e/año)
gei_evitados_tco2e_año = pda_evitada_ton_año * (df_diagnostico_p12.loc[1, 'distancia_transporte_km'] * df_diagnostico_p12.loc[1, 'factor_emision_co2e_ton_km'] / 1000)

# Pérdidas económicas asociadas a PDA evitada (USD/año)
perdidas_economicas_pda_evitada_usd_año = pda_evitada_ton_año * precio_ciruela

st.header('Resultados Proyectados Anuales:')

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="🧪 **Reducción en Uso de Sorbato**", value=f"{reduccion_sorbato_kg_año:.2f} kg")
    st.caption("Menor cantidad de conservante químico utilizado.")
with col2:
    st.metric(label="💸 **Ahorro en Costos por Sorbato**", value=f"USD {ahorro_costos_sorbato_usd_año:,.2f}")
    st.caption("Ahorro económico directo por la reducción en el uso de sorbato.")
with col3:
    st.metric(label="🗑️ **PDA Evitado**", value=f"{pda_evitada_ton_año:.2f} ton")
    st.caption("Reducción de Pérdida y Desperdicio de Alimentos.")

col4, col5 = st.columns(2)

with col4:
    st.metric(label="🌎 **GEI Evitados por Devoluciones**", value=f"{gei_evitados_tco2e_año:.2f} tCO₂e")
    st.caption("Reducción de emisiones de gases de efecto invernadero por evitar transporte inverso de devoluciones.")
with col5:
    st.metric(label="💰 **Pérdidas Económicas Asociadas a PDA Evitada**", value=f"USD {perdidas_economicas_pda_evitada_usd_año:,.2f}")
    st.caption("Ahorros económicos directos al evitar el desperdicio de ciruelas.")

st.markdown("---")

st.header('📊 Análisis Gráfico de Impactos')

# --- Visualización (Gráficos 2D con Matplotlib) ---
# Cálculo de valores de línea base para los gráficos (desde los datos de la ficha)
reduccion_sorbato_base_ejemplo = df_diagnostico_p12.loc[0, 'valor_base_ficha_ejemplo']
pda_evitada_base_ejemplo = df_diagnostico_p12.loc[3, 'rango_pda_evitada_max_ton']
perdidas_economicas_pda_base_ejemplo = df_diagnostico_p12.loc[4, 'valor_base_ficha_ejemplo']

# Creamos una figura con 3 subplots (2D)
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 7), facecolor=color_primario_3_rgb)
fig.patch.set_facecolor(color_primario_3_rgb)

# Definición de etiquetas y valores para los gráficos de barras 2D
labels = ['Línea Base', 'Proyección']
bar_width = 0.6
x = np.arange(len(labels))

# --- Gráfico 1: Reducción Sorbato (kg/año) ---
sorbato_values = [reduccion_sorbato_base_ejemplo, reduccion_sorbato_kg_año]
bars1 = ax1.bar(x, sorbato_values, width=bar_width, color=[colors_for_charts[0], colors_for_charts[1]])
ax1.set_ylabel('Kilogramos/año', fontsize=12, color=colors_for_charts[3])
ax1.set_title('Reducción Uso Sorbato de Potasio', fontsize=14, color=colors_for_charts[3], pad=20) # Aumentado pad
ax1.set_xticks(x)
ax1.set_xticklabels(labels, rotation=15, color=colors_for_charts[0])
ax1.yaxis.set_tick_params(colors=colors_for_charts[0])
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.tick_params(axis='x', length=0)
ax1.set_ylim(bottom=0)
for bar in bars1:
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, yval + 0.05 * yval, round(yval, 2), ha='center', va='bottom', color=colors_for_charts[0])

# --- Gráfico 2: PDA Evitado (ton/año) ---
pda_values = [pda_evitada_base_ejemplo, pda_evitada_ton_año]
bars2 = ax2.bar(x, pda_values, width=bar_width, color=[colors_for_charts[2], colors_for_charts[3]])
ax2.set_ylabel('Toneladas/año', fontsize=12, color=colors_for_charts[0])
ax2.set_title('Pérdida y Desperdicio de Alimentos Evitado', fontsize=14, color=colors_for_charts[3], pad=20) # Aumentado pad
ax2.set_xticks(x)
ax2.set_xticklabels(labels, rotation=15, color=colors_for_charts[0])
ax2.yaxis.set_tick_params(colors=colors_for_charts[0])
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.tick_params(axis='x', length=0)
ax2.set_ylim(bottom=0)
for bar in bars2:
    yval = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2, yval + 0.05 * yval, round(yval, 2), ha='center', va='bottom', color=colors_for_charts[0])

# --- Gráfico 3: Pérdidas Económicas Evitadas (USD/año) ---
perdidas_eco_values = [perdidas_economicas_pda_base_ejemplo, perdidas_economicas_pda_evitada_usd_año]
bars3 = ax3.bar(x, perdidas_eco_values, width=bar_width, color=[colors_for_charts[1], colors_for_charts[0]])
ax3.set_ylabel('USD/año', fontsize=12, color=colors_for_charts[3])
ax3.set_title('Pérdidas Económicas Asociadas a PDA Evitada', fontsize=14, color=colors_for_charts[3], pad=20) # Aumentado pad
ax3.set_xticks(x)
ax3.set_xticklabels(labels, rotation=15, color=colors_for_charts[0])
ax3.yaxis.set_tick_params(colors=colors_for_charts[0])
ax3.spines['top'].set_visible(False)
ax3.spines['right'].set_visible(False)
ax3.tick_params(axis='x', length=0)
ax3.set_ylim(bottom=0)
for bar in bars3:
    yval = bar.get_height()
    # CAMBIO AQUÍ: Usar f"{yval:,.0f}" para redondear a entero y formatear con comas
    ax3.text(bar.get_x() + bar.get_width()/2, yval + 0.05 * yval, f"${yval:,.0f}", ha='center', va='bottom', color=colors_for_charts[0])

plt.tight_layout(rect=[0, 0.05, 1, 0.95])
st.pyplot(fig)

# --- Funcionalidad de descarga de cada gráfico ---
st.markdown("---")
st.subheader("Descargar Gráficos Individualmente")

# Función auxiliar para generar el botón de descarga
def download_button(fig, filename_prefix, key):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=300)
    st.download_button(
        label=f"Descargar {filename_prefix}.png",
        data=buf.getvalue(),
        file_name=f"{filename_prefix}.png",
        mime="image/png",
        key=key
    )

# Crear figuras individuales para cada gráfico para poder descargarlas
# Figura 1: Reducción Sorbato
fig_sorbato, ax_sorbato = plt.subplots(figsize=(8, 6), facecolor=color_primario_3_rgb)
ax_sorbato.bar(x, sorbato_values, width=bar_width, color=[colors_for_charts[0], colors_for_charts[1]])
ax_sorbato.set_ylabel('Kilogramos/año', fontsize=12, color=colors_for_charts[3])
ax_sorbato.set_title('Reducción Uso Sorbato de Potasio', fontsize=14, color=colors_for_charts[3], pad=20)
ax_sorbato.set_xticks(x)
ax_sorbato.set_xticklabels(labels, rotation=15, color=colors_for_charts[0])
ax_sorbato.yaxis.set_tick_params(colors=colors_for_charts[0])
ax_sorbato.spines['top'].set_visible(False)
ax_sorbato.spines['right'].set_visible(False)
ax_sorbato.tick_params(axis='x', length=0)
ax_sorbato.set_ylim(bottom=0)
for bar in ax_sorbato.patches:
    yval = bar.get_height()
    ax_sorbato.text(bar.get_x() + bar.get_width()/2, yval + 0.05 * yval, round(yval, 2), ha='center', va='bottom', color=colors_for_charts[0])
plt.tight_layout()
download_button(fig_sorbato, "Reduccion_Sorbato", "download_sorbato")
plt.close(fig_sorbato)

# Figura 2: PDA Evitado
fig_pda, ax_pda = plt.subplots(figsize=(8, 6), facecolor=color_primario_3_rgb)
ax_pda.bar(x, pda_values, width=bar_width, color=[colors_for_charts[2], colors_for_charts[3]])
ax_pda.set_ylabel('Toneladas/año', fontsize=12, color=colors_for_charts[0])
ax_pda.set_title('Pérdida y Desperdicio de Alimentos Evitado', fontsize=14, color=colors_for_charts[3], pad=20)
ax_pda.set_xticks(x)
ax_pda.set_xticklabels(labels, rotation=15, color=colors_for_charts[0])
ax_pda.yaxis.set_tick_params(colors=colors_for_charts[0])
ax_pda.spines['top'].set_visible(False)
ax_pda.spines['right'].set_visible(False)
ax_pda.tick_params(axis='x', length=0)
ax_pda.set_ylim(bottom=0)
for bar in ax_pda.patches:
    yval = bar.get_height()
    ax_pda.text(bar.get_x() + bar.get_width()/2, yval + 0.05 * yval, round(yval, 2), ha='center', va='bottom', color=colors_for_charts[0])
plt.tight_layout()
download_button(fig_pda, "PDA_Evitado", "download_pda")
plt.close(fig_pda)

# Figura 3: Pérdidas Económicas Evitadas
fig_perdidas_eco, ax_perdidas_eco = plt.subplots(figsize=(8, 6), facecolor=color_primario_3_rgb)
ax_perdidas_eco.bar(x, perdidas_eco_values, width=bar_width, color=[colors_for_charts[1], colors_for_charts[0]])
ax_perdidas_eco.set_ylabel('USD/año', fontsize=12, color=colors_for_charts[3])
ax_perdidas_eco.set_title('Pérdidas Económicas Asociadas a PDA Evitada', fontsize=14, color=colors_for_charts[3], pad=20)
ax_perdidas_eco.set_xticks(x)
ax_perdidas_eco.set_xticklabels(labels, rotation=15, color=colors_for_charts[0])
ax_perdidas_eco.yaxis.set_tick_params(colors=colors_for_charts[0])
ax_perdidas_eco.spines['top'].set_visible(False)
ax_perdidas_eco.spines['right'].set_visible(False)
ax_perdidas_eco.tick_params(axis='x', length=0)
ax_perdidas_eco.set_ylim(bottom=0)
for bar in ax_perdidas_eco.patches:
    yval = bar.get_height()
    # CAMBIO AQUÍ: Usar f"${yval:,.0f}" para redondear a entero y formatear con comas
    ax_perdidas_eco.text(bar.get_x() + bar.get_width()/2, yval + 0.05 * yval, f"${yval:,.0f}", ha='center', va='bottom', color=colors_for_charts[0])
plt.tight_layout()
download_button(fig_perdidas_eco, "Perdidas_Economicas_Evitadas_PDA", "download_perdidas_eco")
plt.close(fig_perdidas_eco)


st.markdown("---")
st.markdown("### Información Adicional:")
st.markdown(f"- **Estado de Avance y Recomendaciones:** El proyecto cuenta con validación técnica en laboratorio. Se recomienda avanzar hacia una validación industrial (TRL 8), incorporando la tecnología en una planta procesadora bajo condiciones reales de operación.")

st.markdown("---")
# Texto de atribución centrado
st.markdown("<div style='text-align: center;'>Visualizador Creado por el equipo Sustrend SpA en el marco del Proyecto TT GREEN Foods</div>", unsafe_allow_html=True)

# Aumentar el espaciado antes de los logos
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# --- Mostrar Logos ---
col_logos_left, col_logos_center, col_logos_right = st.columns([1, 2, 1])

with col_logos_center:
    sustrend_logo_url = "https://drive.google.com/uc?id=1vx_znPU2VfdkzeDtl91dlpw_p9mmu4dd"
    ttgreenfoods_logo_url = "https://drive.google.com/uc?id=1uIQZQywjuQJz6Eokkj6dNSpBroJ8tQf8"

    try:
        sustrend_response = requests.get(sustrend_logo_url)
        sustrend_response.raise_for_status()
        sustrend_image = Image.open(BytesIO(sustrend_response.content))

        ttgreenfoods_response = requests.get(ttgreenfoods_logo_url)
        ttgreenfoods_response.raise_for_status()
        ttgreenfoods_image = Image.open(BytesIO(ttgreenfoods_response.content))

        st.image([sustrend_image, ttgreenfoods_image], width=100)
    except requests.exceptions.RequestException as e:
        st.error(f"Error al cargar los logos desde las URLs. Por favor, verifica los enlaces: {e}")
    except Exception as e:
        st.error(f"Error inesperado al procesar las imágenes de los logos: {e}")

st.markdown("<div style='text-align: center; font-size: small; color: gray;'>Viña del Mar, Valparaíso, Chile</div>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown(f"<div style='text-align: center; font-size: smaller; color: gray;'>Versión del Visualizador: 1.5</div>", unsafe_allow_html=True) # Actualizada la versión
st.sidebar.markdown(f"<div style='text-align: center; font-size: x-small; color: lightgray;'>Desarrollado con Streamlit</div>", unsafe_allow_html=True)
