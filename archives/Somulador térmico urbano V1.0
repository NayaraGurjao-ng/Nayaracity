import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import plotly.graph_objects as go
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Nayara - Simulador Térmico Urbano", layout="wide")

st.title("🏙️ Plataforma de Simulação de Microclima Urbano")
st.markdown("---")

# --- SIDEBAR: PARÂMETROS DE ENTRADA (O que você colocou no Guide) ---
st.sidebar.header("📍 Localização e Clima")
loc_name = st.sidebar.text_input("Nome da Localidade", "Fortaleza, CE")
lat = st.sidebar.number_input("Latitude", value=-3.73, format="%.4f")
lon = st.sidebar.number_input("Longitude", value=-38.52, format="%.4f")

st.sidebar.subheader("🌡️ Condições Meteorológicas")
t_max = st.sidebar.slider("Temperatura Máxima (°C)", 20.0, 45.0, 32.0)
t_min = st.sidebar.slider("Temperatura Mínima (°C)", 15.0, 35.0, 24.0)
umidade = st.sidebar.slider("Umidade Relativa Média (%)", 0, 100, 65)
vento = st.sidebar.number_input("Velocidade do Vento (m/s)", value=4.0)

# --- ÁREA DE ESTUDO (A grade 50x50) ---
st.sidebar.header("📏 Domínio da Simulação")
grid_size = st.sidebar.selectbox("Tamanho da Grade (m)", [30, 50, 100], index=1)
cell_res = st.sidebar.number_input("Resolução da Célula (m)", value=2.0)

# --- UPLOAD DE ARQUIVOS (GeoJSON/Shapefile) ---
st.header("📂 1. Configuração da Área")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Geometria da Cidade")
    uploaded_file = st.file_uploader("Upload de Shapefile ou GeoJSON", type=['geojson', 'zip'])
    if uploaded_file:
        # Aqui o código lerá o mapa de Fortaleza que você subir
        st.success("Arquivo carregado com sucesso!")

with col2:
    st.subheader("Materiais do Pavimento")
    pavimento = st.selectbox("Tipo de Revestimento", ["Asfalto Convencional", "Concreto Rígido", "Asfalto com Aditivo Térmico"])
    arvores = st.checkbox("Incluir sombreamento por vegetação?")

# --- LÓGICA DE CÁLCULO (A Metodologia "Guardada") ---
st.header("⚡ 2. Execução da Simulação")

if st.button("Simular Desempenho Térmico"):
    with st.spinner('Calculando balanço de energia...'):
        # Simulando uma curva de temperatura do pavimento baseada na metodologia de Fourier
        horas = np.arange(0, 24, 1)
        # Fórmula simplificada de oscilação térmica
        temp_pavimento = t_min + (t_max - t_min + 5) * np.sin((horas - 8) * np.pi / 12)
        
        if arvores:
            temp_pavimento = temp_pavimento - 4  # Redução hipotética por sombra

        # --- VISUALIZAÇÃO DOS RESULTADOS ---
        st.subheader("Resultado: Temperatura de Superfície (24h)")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=horas, y=temp_pavimento, mode='lines+markers', name=pavimento))
        fig.update_layout(xaxis_title="Hora do Dia", yaxis_title="Temperatura (°C)")
        st.plotly_chart(fig, use_container_width=True)

        st.info(f"Análise para {loc_name}: O pico térmico do {pavimento} será de {max(temp_pavimento):.2f}°C.")
