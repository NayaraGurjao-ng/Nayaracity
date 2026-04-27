import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import geopandas as gpd
import tempfile
import os

# Configuração da Página
st.set_page_config(page_title="Nayara - Simulador Térmico v1.6.2", layout="wide")

st.title("🏙️ Plataforma de Simulação de Microclima Urbano")
st.markdown("---")

# --- SIDEBAR: PARÂMETROS ---
st.sidebar.header("📍 Parâmetros do Cenário Teórico")

st.sidebar.subheader("☁️ Clima")
t_max = st.sidebar.slider("Temperatura Máxima (°C)", 15, 45, 32)
t_min = st.sidebar.slider("Temperatura Mínima (°C)", 10, 35, 24)
umidade = st.sidebar.slider("Umidade Relativa Média (%)", 10, 100, 65)
vento = st.sidebar.number_input("Velocidade do Vento (m/s)", value=2.0)

st.sidebar.subheader("🏗️ Materiais (Modelo Paramétrico)")
material = st.sidebar.selectbox("Material de Referência", ["Asfalto", "Concreto"])

label_emissividade = f"Emissividade ({material})"
if material == "Asfalto":
    emissividade = st.sidebar.slider(label_emissividade, 0.85, 0.93, 0.90)
    albedo = 0.10
else:
    emissividade = st.sidebar.slider(label_emissividade, 0.88, 0.93, 0.91)
    albedo = 0.30

taxa_edificada = st.sidebar.slider("Taxa de Área Edificada (%)", 0, 100, 30)

st.sidebar.subheader("🌳 Natureza e Água")
taxa_permeavel = st.sidebar.slider("Taxa de Área Permeável (%)", 0, 100, 15)
taxa_sombra = st.sidebar.slider("Taxa de Sombreamento (%)", 0, 100, 20)
taxa_agua = st.sidebar.slider("Taxa de Corpos d'Água (%)", 0, 100, 5)

btn_simular = st.sidebar.button("Simular Desempenho Térmico")

# --- ÁREA DE ESTUDO ---
st.header("📂 1. Configuração das Bases de Dados")
col1, col2 = st.columns(2)
with col1:
    geo_file = st.file_uploader("Upload: Limite Administrativo (Zip)", type=['zip'])
with col2:
    bld_file = st.file_uploader("Upload: Área Edificada Real (Zip)", type=['zip'])

# --- VISUALIZAÇÃO 1: CENÁRIO TEÓRICO ---
st.subheader("📊 Cenário Teórico (Modelo Paramétrico)")
grid_dim = 50
mapa_data = np.zeros((grid_dim, grid_dim))
np.random.seed(42)

# Lógica de preenchimento da grade (simplificada para visualização)
idx_edif = np.random.choice(grid_dim**2, int((taxa_edificada/100)*grid_dim**2), replace=False)
mapa_data.flat[idx_edif] = 2
vazios = np.where(mapa_data.flat == 0)[0]
idx_agua = np.random.choice(vazios, min(len(vazios), int((taxa_agua/100)*grid_dim**2)), replace=False)
mapa_data.flat[idx_agua] = 3

fig_mapa = px.imshow(mapa_data, x=np.arange(0, 100, 2), y=np.arange(0, 100, 2),
                    color_continuous_scale=['#444444', '#228B22', '#8B4513', '#1E90FF'])
fig_mapa.update_coloraxes(showscale=False)

col_map, col_stats_box = st.columns([3, 1])
with col_map:
    st.plotly_chart(fig_mapa, use_container_width=True)
with col_stats_box:
    st.write("### 🏷️ Legenda")
    st.markdown("⬛ Pavimento | 🟩 Verde | 🟫 Edificações | 🟦 Água")
    if btn_simular:
        # Cálculos para a caixinha de variação térmica
        bloqueio = (taxa_sombra * 0.75 + taxa_edificada * 0.35) / 100
        horas = np.arange(0, 24, 0.5)
        rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12)) * (1 - bloqueio)
        refrescamento = (taxa_agua * 0.20) + (umidade * 0.05) + (taxa_permeavel * 0.12)
        temp_surf = t_min + (rad_solar * (1 - albedo) / 34) - (vento * 0.45) - (emissividade * 0.12) - (refrescamento / 2)
        
        st.write("---")
        st.write("### 🌡️ Variação Superficial")
        st.metric("Máxima", f"{max(temp_surf):.1f} °C")
        st.metric("Mínima", f"{min(temp_surf):.1f} °C")
        st.info(f"**ΔT:** {max(temp_surf) - min(temp_surf):.1f} °C")

# --- VISUALIZAÇÃO 2: CENÁRIO REAL ---
if geo_file:
    st.markdown("---")
    st.subheader("🗺️ Cenário Real (Representação Geográfica - Fortaleza)")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # CORREÇÃO DO ERRO: Salvando e lendo com prefixo zip://
            path_geo = os.path.join(tmpdir, "limite.zip")
            with open(path_geo, "wb") as f: f.write(geo_file.getvalue())
            gdf_limite = gpd.read_file(f"zip://{path_geo}")
            
            fig_real = px.choropleth_mapbox(gdf_limite, geojson=gdf_limite.geometry.__geo_interface__, 
                                           locations=gdf_limite.index, color_discrete_sequence=["#555555"],
                                           opacity=0.3, mapbox_style="carto-positron",
                                           center={"lat": -3.7319, "lon": -38.5267}, zoom=11)
            
            if bld_file:
                path_bld = os.path.join(tmpdir, "edif.zip")
                with open(path_bld, "wb") as f: f.write(bld_file.getvalue())
                gdf_bld = gpd.read_file(f"zip://{path_bld}")
                # Simplificação para não travar o navegador
                gdf_bld['geometry'] = gdf_bld.geometry.simplify(0.0001)
                fig_bld = px.choropleth_mapbox(gdf_bld, geojson=gdf_bld.geometry.__geo_interface__, 
                                              locations=gdf_bld.index, color_discrete_sequence=["#8B4513"])
                fig_real.add_trace(fig_bld.data[0])

            fig_real.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
            st.plotly_chart(fig_real, use_container_width=True)
    except Exception as e:
        st.error(f"Aviso: Certifique-se de que o arquivo ZIP contém os arquivos .shp, .shx e .dbf. Erro: {e}")

# --- RESULTADOS GRÁFICOS ---
if btn_simular:
    st.header("⚡ 2. Resultados da Simulação Térmica")
    fig_res = go.Figure()
    fig_res.add_trace(go.Scatter(x=horas, y=temp_surf, name="Temperatura de Superfície", line=dict(color='firebrick', width=4)))
    st.plotly_chart(fig_res, use_container_width=True)
