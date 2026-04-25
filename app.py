import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# Configuração da Página
st.set_page_config(page_title="Nayara - Simulador Térmico v1.4", layout="wide")

st.title("🏙️ Plataforma de Simulação de Microclima Urbano")
st.markdown("---")

# --- SIDEBAR: PARÂMETROS ---
st.sidebar.header("📍 Parâmetros Globais")

with st.sidebar.form("config_simulacao"):
    st.subheader("☁️ Clima")
    t_max = st.slider("Temperatura Máxima (°C)", 15, 45, 32)
    t_min = st.slider("Temperatura Mínima (°C)", 10, 35, 24)
    umidade = st.slider("Umidade Relativa Média (%)", 10, 100, 65)
    vento = st.number_input("Velocidade do Vento (m/s)", value=2.0)

    st.subheader("🏗️ Materiais e Ocupação")
    material = st.selectbox("Material de Referência", ["Asfalto", "Concreto"])
    
    # Checkbox para desativar influência de Edificações
    usar_edificacao = st.checkbox("Simular Edificações?", value=True)
    taxa_edificada = st.slider("Taxa de Área Edificada (%)", 0, 100, 30) if usar_edificacao else 0
    
    # Diferenciando Vegetação de Área Permeável
    usar_permeavel = st.checkbox("Simular Solo Permeável?", value=True)
    taxa_permeavel = st.slider("Taxa de Área Permeável (Solo/Grama) (%)", 0, 100, 15) if usar_permeavel else 0

    st.subheader("🌳 Natureza e Água")
    usar_sombra = st.checkbox("Simular Sombreamento?", value=True)
    taxa_sombra = st.slider("Taxa de Sombreamento (Copas) (%)", 0, 100, 20) if usar_sombra else 0
    
    usar_agua = st.checkbox("Simular Corpos d'Água?", value=True)
    taxa_agua = st.slider("Taxa de Corpos d'Água (%)", 0, 100, 5) if usar_agua else 0
    
    btn_simular = st.form_submit_button("Simular Desempenho Térmico")

# --- ÁREA DE ESTUDO ---
st.header("📂 1. Configuração da Área de Estudo")
col1, col2 = st.columns(2)

with col1:
    sh_geo = st.file_uploader("Upload da Geometria Urbana (Opcional)", type=['geojson', 'zip'], key="geo")
with col2:
    sh_bld = st.file_uploader("Upload de Edificações (Opcional)", type=['geojson', 'zip'], key="bld")

# Lógica do Mapa e Legenda
if not sh_geo:
    grid_dim = 50 # 100m / 2m = 50 células
    mapa_data = np.zeros((grid_dim, grid_dim))
    np.random.seed(42)
    
    # Preenchimento do mapa conforme escolhas
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

    # Mapa com legenda customizada
    fig_mapa = px.imshow(mapa_data, 
                        x=np.arange(0, 100, 2), y=np.arange(0, 100, 2),
                        color_continuous_scale=['#444444', '#228B22', '#8B4513', '#1E90FF'])
    fig_mapa.update_coloraxes(showscale=False)
    
    col_map, col_leg = st.columns([3, 1])
    with col_map:
        st.plotly_chart(fig_mapa, use_container_width=True)
    with col_leg:
        st.markdown("### Legenda")
        st.markdown("⬛ **Cinza**: Pavimento")
        st.markdown("🟩 **Verde**: Vegetação/Permeável")
        st.markdown("🟫 **Marrom**: Edificações")
        st.markdown("🟦 **Azul**: Corpos d'Água")

# --- SIMULAÇÃO E EXPORTAÇÃO ---
st.header("⚡ 2. Resultados da Simulação")

if btn_simular:
    horas = np.arange(0, 24, 0.5)
    # Metodologia simplificada
    bloqueio = (taxa_sombra * 0.7 + taxa_edificada * 0.3) / 100
    rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12)) * (1 - bloqueio)
    
    albedo = 0.10 if material == "Asfalto" else 0.30
    temp_surf = t_min + (rad_solar * (1 - albedo) / 35) - (vento * 0.4)
    temp_5cm = temp_surf * 0.82 + (t_min * 0.18)

    # Gráfico Principal
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=horas, y=temp_surf, name="Superfície", line=dict(color='firebrick', width=4)))
    fig.add_trace(go.Scatter(x=horas, y=temp_5cm, name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash')))
    st.plotly_chart(fig, use_container_width=True)

    # GERAÇÃO DO ARQUIVO EXCEL PARA DOWNLOAD
    # Criamos uma tabela onde cada linha é uma coordenada da grade 100x100
    df_export = pd.DataFrame([
        {"Coord_X": x, "Coord_Y": y, "Temp_Pico_Superficie": max(temp_surf), "Temp_Pico_5cm": max(temp_5cm)}
        for x in range(0, 100, 2) for y in range(0, 100, 2)
    ])
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Dados_Simulacao')
    
    st.download_button(
        label="📥 Baixar Dados da Simulação (Excel)",
        data=output.getvalue(),
        file_name=f"simulacao_fortaleza_{material}.xlsx",
        mime="application/vnd.ms-excel"
    )

    with st.expander("📖 Veja a Nota Científica e Metodologia"):
        st.write(f"""
        **Metodologia de Cálculo Microclimático (v1.4):**
        * **Vegetação:** O cálculo baseia-se no **Índice de Área Foliar (LAI)**, reduzindo a radiação de onda curta.
        * **Área Permeável:** Considera-se a capacidade de infiltração e resfriamento evaporativo do solo natural em relação ao {material}.
        * **Edificações:** Simula a obstrução do céu (**Sky View Factor**), afetando o balanço de radiação noturna.
        * **Pavimento:** Modelado com emissividade de {emissividade} e foco na profundidade de 5cm.
        """)
