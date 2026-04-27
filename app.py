import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import geopandas as gpd
import tempfile
import os

# ==========================================
# CONFIGURAÇÃO E INTERFACE
# ==========================================
st.set_page_config(page_title="Nayara - Simulador Térmico v1.6.2", layout="wide")

st.title("🏙️ Plataforma de Simulação de Microclima Urbano")
st.markdown("---")

# --- SIDEBAR: PARÂMETROS DO CENÁRIO TEÓRICO ---
st.sidebar.header("📍 Parâmetros do Cenário Teórico")

st.sidebar.subheader("☁️ Condições Climáticas")
t_max = st.sidebar.slider("Temperatura Máxima (°C)", 15, 45, 32)
t_min = st.sidebar.slider("Temperatura Mínima (°C)", 10, 35, 24)
umidade = st.sidebar.slider("Umidade Relativa Média (%)", 10, 100, 65)
vento = st.sidebar.number_input("Velocidade do Vento (m/s)", value=2.0)

st.sidebar.subheader("🏗️ Materiais (Modelo Paramétrico)")
material = st.sidebar.selectbox("Material de Referência", ["Asfalto", "Concreto"])

# Aplicação das correções de emissividade da Nayara
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
st.subheader("📊 Cenário Teórico (Modelo Paramétrico)")

grid_dim = 50
mapa_data = np.zeros((grid_dim, grid_dim))
np.random.seed(42)

# Lógica de preenchimento da grade de pixels
# 2 = Edificação, 3 = Água, 1 = Verde, 0 = Pavimento
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

col_map, col_stats_box = st.columns([3, 1])

with col_map:
    st.plotly_chart(fig_mapa, use_container_width=True)

with col_stats_box:
    st.write("### 🏷️ Legenda")
    st.markdown("⬛ **Cinza**: Pavimento")
    st.markdown("🟩 **Verde**: Vegetação")
    st.markdown("🟫 **Marrom**: Edificações")
    st.markdown("🟦 **Azul**: Água")
    
    if btn_simular:
        # Cálculos térmicos baseados nos sliders
        bloqueio = (taxa_sombra * 0.75 + taxa_edificada * 0.35) / 100
        horas = np.arange(0, 24, 0.5)
        rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12)) * (1 - bloqueio)
        refrescamento = (taxa_agua * 0.20) + (umidade * 0.05) + (taxa_permeavel * 0.12)
        
        # Balanço térmico
        temp_surf = t_min + (rad_solar * (1 - albedo) / 34) - (vento * 0.45) - (emissividade * 0.12) - (refrescamento / 2)
        
        st.markdown("---")
        st.write("### 🌡️ Variação Superficial")
        st.metric("Máxima", f"{max(temp_surf):.1f} °C")
        st.metric("Mínima", f"{min(temp_surf):.1f} °C")
        st.info(f"**Variação (ΔT):** {max(temp_surf) - min(temp_surf):.1f} °C")

# ==========================================
# 3. CENÁRIO REAL (REPRESENTAÇÃO GEOGRÁFICA)
# ==========================================
if geo_file:
    st.markdown("---")
    st.subheader("🗺️ Cenário Real (Representação Geográfica - Fortaleza)")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Correção do erro de Driver: Usando prefixo zip://
            path_geo = os.path.join(tmpdir, "limite.zip")
            with open(path_geo, "wb") as f:
                f.write(geo_file.getvalue())
            
            gdf_limite = gpd.read_file(f"zip://{path_geo}")
            
            fig_real = px.choropleth_mapbox(
                gdf_limite, 
                geojson=gdf_limite.geometry.__geo_interface__, 
                locations=gdf_limite.index, 
                color_discrete_sequence=["#555555"],
                opacity=0.3, 
                mapbox_style="carto-positron",
                center={"lat": -3.7319, "lon": -38.5267}, 
                zoom=11
            )
            
            if bld_file:
                path_bld = os.path.join(tmpdir, "edificacoes.zip")
                with open(path_bld, "wb") as f:
                    f.write(bld_file.getvalue())
                
                gdf_bld = gpd.read_file(f"zip://{path_bld}")
                # Simplificação para performance no navegador
                gdf_bld['geometry'] = gdf_bld.geometry.simplify(0.0001)
                
                fig_bld = px.choropleth_mapbox(
                    gdf_bld, 
                    geojson=gdf_bld.geometry.__geo_interface__, 
                    locations=gdf_bld.index, 
                    color_discrete_sequence=["#8B4513"],
                    opacity=0.7
                )
                fig_real.add_trace(fig_bld.data[0])

            fig_real.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
            st.plotly_chart(fig_real, use_container_width=True)
            st.success("✅ Bases geográficas carregadas com sucesso!")
            
    except Exception as e:
        st.error(f"Erro ao processar arquivos geográficos: {e}")

# ==========================================
# 4. RESULTADOS DA SIMULAÇÃO TÉRMICA
# ==========================================
if btn_simular:
    st.header("⚡ 2. Resultados da Simulação Térmica")
    
    # Gráfico de variação horária
    fig_res = go.Figure()
    fig_res.add_trace(go.Scatter(
        x=horas, 
        y=temp_surf, 
        name="Temperatura de Superfície", 
        line=dict(color='firebrick', width=4)
    ))
    fig_res.update_layout(
        xaxis_title="Hora do Dia", 
        yaxis_title="Temperatura (°C)",
        hovermode="x"
    )
    st.plotly_chart(fig_res, use_container_width=True)

    # Preparação da planilha para download (Excel Rico)
    # Aqui expandi as linhas para ficar mais claro o que está sendo exportado
    export_list = []
    for x in range(0, grid_dim):
        for y in range(0, grid_dim):
            export_list.append({
                "Coord_X": x,
                "Coord_Y": y,
                "Material": material,
                "Emissividade": emissividade,
                "Temp_Min": round(min(temp_surf), 2),
                "Temp_Max": round(max(temp_surf), 2),
                "Media_Diaria": round(np.mean(temp_surf), 2)
            })
    
    df_export = pd.DataFrame(export_list)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Estatisticas')
    
    st.download_button(
        label="📥 Baixar Planilha de Dados (Cenário Teórico)",
        data=output.getvalue(),
        file_name=f"simulacao_fortaleza_{material}.xlsx",
        mime="application/vnd.ms-excel"
    )
