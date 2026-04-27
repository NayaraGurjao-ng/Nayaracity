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
st.set_page_config(page_title="Nayara - Simulador Térmico v1.6.1", layout="wide")

st.title("🏙️ Plataforma de Simulação de Microclima Urbano")
st.markdown("---")

# --- SIDEBAR: PARÂMETROS ---
st.sidebar.header("📍 Parâmetros Globais")

st.sidebar.subheader("☁️ Clima")
t_max = st.sidebar.slider("Temperatura Máxima (°C)", 15, 45, 32)
t_min = st.sidebar.slider("Temperatura Mínima (°C)", 10, 35, 24)
umidade = st.sidebar.slider("Umidade Relativa Média (%)", 10, 100, 65)
vento = st.sidebar.number_input("Velocidade do Vento (m/s)", value=2.0)

st.sidebar.subheader("🏗️ Materiais e Ocupação")
material = st.sidebar.selectbox("Material de Referência", ["Asfalto", "Concreto"])

label_emissividade = f"Emissividade do Material ({material})"
if material == "Asfalto":
    emissividade = st.sidebar.slider(label_emissividade, 0.85, 0.93, 0.90)
    albedo = 0.10
else:
    emissividade = st.sidebar.slider(label_emissividade, 0.88, 0.93, 0.91)
    albedo = 0.30

usar_edificacao = st.sidebar.checkbox("Simular Edificações?", value=True)
taxa_edificada = st.sidebar.slider("Taxa de Área Edificada (%)", 0, 100, 30) if usar_edificacao else 0

st.sidebar.subheader("🌳 Natureza e Água")
usar_permeavel = st.sidebar.checkbox("Simular Solo Permeável?", value=True)
taxa_permeavel = st.sidebar.slider("Taxa de Área Permeável (%)", 0, 100, 15) if usar_permeavel else 0

usar_sombra = st.sidebar.checkbox("Simular Sombreamento?", value=True)
taxa_sombra = st.sidebar.slider("Taxa de Sombreamento (Copas) (%)", 0, 100, 20) if usar_sombra else 0

usar_agua = st.sidebar.checkbox("Simular Corpos d'Água?", value=True)
taxa_agua = st.sidebar.slider("Taxa de Corpos d'Água (%)", 0, 100, 5) if usar_agua else 0

btn_simular = st.sidebar.button("Simular Desempenho Térmico")

# --- ÁREA DE ESTUDO ---
st.header("📂 1. Configuração da Área de Estudo")
col1, col2 = st.columns(2)
with col1:
    geo_file = st.file_uploader("Upload do Limite (Zip)", type=['zip'], key="geo")
with col2:
    bld_file = st.file_uploader("Upload de Edificações (Zip)", type=['zip'], key="bld")

# --- VISUALIZAÇÃO 1: GRADE DE PIXELS ---
st.subheader("📊 Visualização Paramétrica (Grade de Pixels)")
grid_dim = 50
mapa_data = np.zeros((grid_dim, grid_dim))
np.random.seed(42)

if usar_edificacao:
    idx = np.random.choice(grid_dim**2, int((taxa_edificada/100)*grid_dim**2), replace=False)
    mapa_data.flat[idx] = 2
if usar_agua:
    vazios = np.where(mapa_data.flat == 0)[0]
    idx = np.random.choice(vazios, min(len(vazios), int((taxa_agua/100)*grid_dim**2)), replace=False)
    mapa_data.flat[idx] = 3
if usar_sombra or usar_permeavel:
    vazios = np.where(mapa_data.flat == 0)[0]
    taxa_verde = (taxa_sombra + taxa_permeavel) / 2
    idx = np.random.choice(vazios, min(len(vazios), int((taxa_verde/100)*grid_dim**2)), replace=False)
    mapa_data.flat[idx] = 1

fig_mapa = px.imshow(mapa_data, x=np.arange(0, 100, 2), y=np.arange(0, 100, 2),
                    color_continuous_scale=['#444444', '#228B22', '#8B4513', '#1E90FF'])
fig_mapa.update_coloraxes(showscale=False)

col_map, col_leg = st.columns([3, 1])
with col_map:
    st.plotly_chart(fig_mapa, use_container_width=True)
with col_leg:
    st.write("### Legenda")
    st.markdown("⬛ **Cinza**: Pavimento")
    st.markdown("🟩 **Verde**: Vegetação/Permeável")
    st.markdown("🟫 **Marrom**: Edificações")
    st.markdown("🟦 **Azul**: Corpos d'Água")

# --- VISUALIZAÇÃO 2: MAPA GEOGRÁFICO REAL ---
if geo_file:
    st.markdown("---")
    st.subheader("🗺️ Análise Geoespacial de Fortaleza")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Lendo Limite
            path_geo = os.path.join(tmpdir, geo_file.name)
            with open(path_geo, "wb") as f: f.write(geo_file.getvalue())
            gdf_limite = gpd.read_file(path_geo)
            
            fig_geo = px.choropleth_mapbox(gdf_limite, geojson=gdf_limite.geometry.__geo_interface__, 
                                          locations=gdf_limite.index, color_discrete_sequence=["#555555"],
                                          opacity=0.3, mapbox_style="carto-positron", 
                                          center={"lat": -3.7319, "lon": -38.5267}, zoom=11)

            # Lendo Edificações (Se houver upload)
            if bld_file:
                path_bld = os.path.join(tmpdir, bld_file.name)
                with open(path_bld, "wb") as f: f.write(bld_file.getvalue())
                gdf_bld = gpd.read_file(path_bld)
                # Simplificação para performance
                gdf_bld['geometry'] = gdf_bld.geometry.simplify(0.0001) 
                
                fig_bld = px.choropleth_mapbox(gdf_bld, geojson=gdf_bld.geometry.__geo_interface__, 
                                              locations=gdf_bld.index, color_discrete_sequence=["#8B4513"],
                                              opacity=0.7)
                fig_geo.add_trace(fig_bld.data[0])
            
            fig_geo.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
            st.plotly_chart(fig_geo, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao processar camadas: {e}")

# --- RESULTADOS ---
st.header("⚡ 2. Resultados da Simulação")

if btn_simular:
    horas = np.arange(0, 24, 0.5)
    bloqueio = (taxa_sombra * 0.75 + taxa_edificada * 0.35) / 100
    rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12)) * (1 - bloqueio)
    refrescamento = (taxa_agua * 0.20) + (umidade * 0.05) + (taxa_permeavel * 0.12)
    perda_onda_longa = emissividade * 0.12
    
    temp_surf = t_min + (rad_solar * (1 - albedo) / 34) - (vento * 0.45) - perda_onda_longa - (refrescamento / 2)
    
    # 1. Gráfico
    fig_res = go.Figure()
    fig_res.add_trace(go.Scatter(x=horas, y=temp_surf, name="Superfície", line=dict(color='firebrick', width=4)))
    fig_res.update_layout(xaxis_title="Hora do Dia", yaxis_title="Temperatura (°C)")
    
    col_graph, col_stats = st.columns([3, 1])
    with col_graph:
        st.plotly_chart(fig_res, use_container_width=True)
    
    # 2. CAIXINHA DE VARIAÇÃO (DELTA T)
    with col_stats:
        st.write("### 🌡️ Variação Térmica")
        delta_t = max(temp_surf) - min(temp_surf)
        st.metric(label="Temp. Máxima", value=f"{max(temp_surf):.1f} °C")
        st.metric(label="Temp. Mínima", value=f"{min(temp_surf):.1f} °C")
        st.info(f"**Variação (ΔT):** {delta_t:.1f} °C")
        
    # Download do Excel Rico (Mínima, Máxima, Média)
    data_points = [{"Coord_X": x, "Coord_Y": y, "Temp_Min": round(min(temp_surf), 2), 
                    "Temp_Max": round(max(temp_surf), 2), "Media": round(np.mean(temp_surf), 2)} 
                   for x in range(0, 50) for y in range(0, 50)]
    df_export = pd.DataFrame(data_points)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False)
    st.download_button("📥 Baixar Planilha Completa", output.getvalue(), "simulacao_v1.6.1.xlsx")
