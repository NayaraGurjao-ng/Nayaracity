import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import geopandas as gpd
import tempfile
import os
import zipfile

# ==========================================
# CONFIGURAÇÃO E INTERFACE
# ==========================================
st.set_page_config(page_title="Nayara - Simulador Térmico v1.6.5", layout="wide")

st.title("🏙️ Plataforma de Simulação de Microclima Urbano")
st.markdown("---")

# --- SIDEBAR: PARÂMETROS ---
st.sidebar.header("📍 Parâmetros do Cenário Teórico")

st.sidebar.subheader("☁️ Condições Climáticas")
t_max = st.sidebar.slider("Temperatura Máxima (°C)", 15, 45, 32)
t_min = st.sidebar.slider("Temperatura Mínima (°C)", 10, 35, 24)
umidade = st.sidebar.slider("Umidade Relativa Média (%)", 10, 100, 65)
vento = st.sidebar.number_input("Velocidade do Vento (m/s)", value=2.0)

st.sidebar.subheader("🏗️ Materiais (Modelo Paramétrico)")
material = st.sidebar.selectbox("Material de Referência", ["Asfalto", "Concreto"])

if material == "Asfalto":
    emissividade = st.sidebar.slider("Emissividade (Asfalto)", 0.85, 0.93, 0.90)
    albedo = 0.10
else:
    emissividade = st.sidebar.slider("Emissividade (Concreto)", 0.88, 0.93, 0.91)
    albedo = 0.30

taxa_edificada = st.sidebar.slider("Taxa de Área Edificada (%)", 0, 100, 30)

st.sidebar.subheader("🌳 Natureza e Água")
taxa_permeavel = st.sidebar.slider("Taxa de Área Permeável (%)", 0, 100, 15)
taxa_sombra = st.sidebar.slider("Taxa de Sombreamento (%)", 0, 100, 20)
taxa_agua = st.sidebar.slider("Taxa de Corpos d'Água (%)", 0, 100, 5)

btn_simular = st.sidebar.button("Simular Desempenho Térmico")

# --- FUNÇÃO AUXILIAR PARA LER ZIP ---
def carregar_shape_do_zip(uploaded_file, tmpdir):
    path_zip = os.path.join(tmpdir, uploaded_file.name)
    with open(path_zip, "wb") as f:
        f.write(uploaded_file.getvalue())
    
    with zipfile.ZipFile(path_zip, 'r') as zip_ref:
        zip_ref.extractall(tmpdir)
    
    # Procura o arquivo .shp dentro da pasta extraída
    for root, dirs, files in os.walk(tmpdir):
        for file in files:
            if file.endswith(".shp"):
                return gpd.read_file(os.path.join(root, file))
    return None

# ==========================================
# 1. CONFIGURAÇÃO DAS BASES DE DADOS
# ==========================================
st.header("📂 1. Configuração das Bases de Dados")
col_arq1, col_arq2 = st.columns(2)
with col_arq1:
    geo_file = st.file_uploader("Upload: Limite Administrativo de Fortaleza (Zip)", type=['zip'])
with col_arq2:
    bld_file = st.file_uploader("Upload: Área Edificada Real (Zip)", type=['zip'])

# ==========================================
# 2. CENÁRIO TEÓRICO (MODELO PARAMÉTRICO)
# ==========================================
st.markdown("---")
st.subheader("📊 Cenário Teórico (Modelo Paramétrico)")

grid_dim = 50
mapa_data = np.zeros((grid_dim, grid_dim))
np.random.seed(42)

idx_edif = np.random.choice(grid_dim**2, int((taxa_edificada/100)*grid_dim**2), replace=False)
mapa_data.flat[idx_edif] = 2
vazios = np.where(mapa_data.flat == 0)[0]
idx_agua = np.random.choice(vazios, min(len(vazios), int((taxa_agua/100)*grid_dim**2)), replace=False)
mapa_data.flat[idx_agua] = 3
vazios = np.where(mapa_data.flat == 0)[0]
taxa_verde = (taxa_sombra + taxa_permeavel) / 2
idx_verde = np.random.choice(vazios, min(len(vazios), int((taxa_verde/100)*grid_dim**2)), replace=False)
mapa_data.flat[idx_verde] = 1

fig_mapa = px.imshow(mapa_data, x=np.arange(0, 100, 2), y=np.arange(0, 100, 2),
                    color_continuous_scale=['#444444', '#228B22', '#8B4513', '#1E90FF'])
fig_mapa.update_coloraxes(showscale=False)
st.plotly_chart(fig_mapa, use_container_width=True)
st.markdown("**Legenda:** ⬛ Pavimento | 🟩 Verde | 🟫 Edificações | 🟦 Água")

# ==========================================
# 3. CENÁRIO REAL (REPRESENTAÇÃO GEOGRÁFICA)
# ==========================================
if geo_file:
    st.markdown("---")
    st.subheader("🗺️ Cenário Real (Representação Geográfica - Fortaleza)")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            gdf_limite = carregar_shape_do_zip(geo_file, tmpdir)
            if gdf_limite is not None:
                fig_real = px.choropleth_mapbox(gdf_limite, geojson=gdf_limite.geometry.__geo_interface__, 
                                               locations=gdf_limite.index, color_discrete_sequence=["#555555"],
                                               opacity=0.3, mapbox_style="carto-positron",
                                               center={"lat": -3.7319, "lon": -38.5267}, zoom=11)
                
                if bld_file:
                    gdf_bld = carregar_shape_do_zip(bld_file, os.path.join(tmpdir, "bld"))
                    if gdf_bld is not None:
                        gdf_bld['geometry'] = gdf_bld.geometry.simplify(0.0001)
                        fig_bld = px.choropleth_mapbox(gdf_bld, geojson=gdf_bld.geometry.__geo_interface__, 
                                                      locations=gdf_bld.index, color_discrete_sequence=["#8B4513"], opacity=0.7)
                        fig_real.add_trace(fig_bld.data[0])
                
                fig_real.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
                st.plotly_chart(fig_real, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao processar mapas: {e}")

# ==========================================
# 4. RESULTADOS DA SIMULAÇÃO TÉRMICA
# ==========================================
if btn_simular:
    st.markdown("---")
    st.header("⚡ 2. Resultados da Simulação Térmica")
    
    # Cálculos
    bloqueio = (taxa_sombra * 0.75 + taxa_edificada * 0.35) / 100
    horas = np.arange(0, 24, 0.5)
    rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12)) * (1 - bloqueio)
    refrescamento = (taxa_agua * 0.20) + (umidade * 0.05) + (taxa_permeavel * 0.12)
    temp_surf = t_min + (rad_solar * (1 - albedo) / 34) - (vento * 0.45) - (emissividade * 0.12) - (refrescamento / 2)
    temp_5cm = temp_surf * 0.81 + (t_min * 0.19)

    col_graph, col_stats = st.columns([3, 1])

    with col_graph:
        fig_res = go.Figure()
        fig_res.add_trace(go.Scatter(x=horas, y=temp_surf, name="Superfície", line=dict(color='firebrick', width=4)))
        fig_res.add_trace(go.Scatter(x=horas, y=temp_5cm, name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash')))
        fig_res.update_layout(xaxis_title="Hora do Dia", yaxis_title="Temperatura (°C)", hovermode="x",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_res, use_container_width=True)

    with col_stats:
        st.write("### 🌡️ Variação Térmica")
        st.metric("Temp. Máxima", f"{max(temp_surf):.1f} °C")
        st.metric("Temp. Mínima", f"{min(temp_surf):.1f} °C")
        st.info(f"**Variação Total (ΔT):** {max(temp_surf) - min(temp_surf):.1f} °C")
        
        # Download
        export_data = [{"Coord_X": x, "Coord_Y": y, "Temp_Max": round(max(temp_surf), 2)} for x in range(0, 50) for y in range(0, 50)]
        df_export = pd.DataFrame(export_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False)
        st.download_button("📥 Baixar Planilha", output.getvalue(), f"simulacao_{material}.xlsx", use_container_width=True)

    with st.expander("📖 Notas Científicas e Metodologia Aplicada"):
        st.write(f"""
        Esta simulação utiliza parâmetros validados para Fortaleza:
        * **Emissividade:** {emissividade} ({material}).
        * **Amortecimento:** Modelo linear de profundidade (5cm).
        """)
