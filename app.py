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
st.set_page_config(page_title="Nayara - Simulador Térmico v1.6", layout="wide")

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
    geo_file = st.file_uploader("Upload do Perímetro (Zip/SHP)", type=['zip'], key="geo")
with col2:
    bld_file = st.file_uploader("Upload de Edificações (Opcional)", type=['zip'], key="bld")

# --- VISUALIZAÇÃO 1: GRADE DE PIXELS (DISTRIBUIÇÃO) ---
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
    st.subheader("🗺️ Mapa Geográfico Real (Shapefile)")
    try:
        # Lógica para ler o ZIP do Shapefile de Fortaleza
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, geo_file.name), "wb") as f:
                f.write(geo_file.getvalue())
            gdf = gpd.read_file(os.path.join(tmpdir, geo_file.name))
            
            # Criando o mapa geográfico
            fig_geo = px.choropleth_mapbox(gdf, 
                                          geojson=gdf.geometry.__geo_interface__, 
                                          locations=gdf.index,
                                          color_discrete_sequence=["#1E90FF"],
                                          opacity=0.5,
                                          center={"lat": -3.7319, "lon": -38.5267},
                                          mapbox_style="carto-positron", zoom=10)
            fig_geo.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500)
            st.plotly_chart(fig_geo, use_container_width=True)
            st.success(f"✅ Perímetro '{geo_file.name}' carregado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao processar o mapa: {e}")

# --- RESULTADOS ---
st.header("⚡ 2. Resultados da Simulação")

if btn_simular:
    horas = np.arange(0, 24, 0.5)
    bloqueio = (taxa_sombra * 0.75 + taxa_edificada * 0.35) / 100
    rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12)) * (1 - bloqueio)
    refrescamento = (taxa_agua * 0.20) + (umidade * 0.05) + (taxa_permeavel * 0.12)
    perda_onda_longa = emissividade * 0.12
    
    temp_surf = t_min + (rad_solar * (1 - albedo) / 34) - (vento * 0.45) - perda_onda_longa - (refrescamento / 2)
    temp_5cm = temp_surf * 0.81 + (t_min * 0.19)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=horas, y=temp_surf, name="Superfície", line=dict(color='firebrick', width=4)))
    fig.add_trace(go.Scatter(x=horas, y=temp_5cm, name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash')))
    fig.update_layout(xaxis_title="Hora do Dia", yaxis_title="Temperatura (°C)", hovermode="x")
    st.plotly_chart(fig, use_container_width=True)

    data_points = []
    for x in range(0, 100, 2):
        for y in range(0, 100, 2):
            data_points.append({
                "Coord_X": x, "Coord_Y": y, "Material": material,
                "Temp_Min_Surf": round(min(temp_surf), 2),
                "Temp_Max_Surf": round(max(temp_surf), 2),
                "Temp_Media_Surf": round(np.mean(temp_surf), 2),
                "Temp_Max_5cm": round(max(temp_5cm), 2),
                "Albedo_Config": albedo, "Emissividade_Config": emissividade,
                "Sombra_%": taxa_sombra, "Agua_%": taxa_agua, "Permeavel_%": taxa_permeavel
            })
    
    df_export = pd.DataFrame(data_points)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Estatisticas_Termicas')
    
    st.download_button(label="📥 Baixar Planilha Científica Completa", data=output.getvalue(), 
                     file_name=f"simulacao_{material}_v1.6.xlsx", mime="application/vnd.ms-excel")

    with st.expander("📖 Notas Científicas e Metodologia Aplicada"):
        st.write(f"""
        Esta simulação utiliza parâmetros térmicos específicos para a cidade de Fortaleza:
        * **Emissividade:** Ajustada para {emissividade} (Ref: Dados fornecidos pelo pesquisador).
        * **Albedo:** {albedo} para {material}.
        * **Refrescamento:** Baseado na evapotranspiração da água ({taxa_agua}%) e solo permeável ({taxa_permeavel}%).
        * **Sombreamento:** Redução da radiação de onda curta em {taxa_sombra}%.
        """)
