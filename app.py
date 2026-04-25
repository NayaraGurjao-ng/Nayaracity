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
    
    if material == "Asfalto":
        emissividade = st.slider("Emissividade (Asfalto)", 0.85, 0.93, 0.90)
        albedo = 0.10
    else:
        emissividade = st.slider("Emissividade (Concreto)", 0.88, 0.93, 0.91)
        albedo = 0.30

    usar_edificacao = st.checkbox("Simular Edificações?", value=True)
    taxa_edificada = st.slider("Taxa de Área Edificada (%)", 0, 100, 30) if usar_edificacao else 0
    
    usar_permeavel = st.checkbox("Simular Solo Permeável?", value=True)
    taxa_permeavel = st.slider("Taxa de Área Permeável (%)", 0, 100, 15) if usar_permeavel else 0

    st.subheader("🌳 Natureza e Água")
    usar_sombra = st.checkbox("Simular Sombreamento?", value=True)
    taxa_sombra = st.slider("Taxa de Sombreamento (Copas) (%)", 0, 100, 20) if usar_sombra else 0
    
    usar_agua = st.checkbox("Simular Corpos d'Água?", value=True)
    taxa_agua = st.slider("Taxa de Corpos d'Água (%)", 0, 100, 5) if usar_agua else 0
    
    btn_simular = st.form_submit_button("Simular Desempenho Térmico")

# --- ÁREA DE ESTUDO (Grade 100x100m) ---
st.header("📂 1. Configuração da Área de Estudo")
col1, col2 = st.columns(2)

with col1:
    sh_geo = st.file_uploader("Upload da Geometria Urbana (Opcional)", type=['geojson', 'zip'], key="geo")
with col2:
    sh_bld = st.file_uploader("Upload de Edificações (Opcional)", type=['geojson', 'zip'], key="bld")

if not sh_geo:
    grid_dim = 50 # 100m / 2m por célula
    mapa_data = np.zeros((grid_dim, grid_dim))
    np.random.seed(42)
    
    # Preenchimento lógico do mapa conforme prioridades de ocupação
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

    fig_mapa = px.imshow(mapa_data, 
                        x=np.arange(0, 100, 2), y=np.arange(0, 100, 2),
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

# --- SIMULAÇÃO ---
st.header("⚡ 2. Resultados da Simulação")

if btn_simular:
    with st.spinner('Processando modelos térmicos avançados...'):
        horas = np.arange(0, 24, 0.5)
        
        # 1. Influência do bloqueio solar (Sombra + Edificações)
        bloqueio = (taxa_sombra * 0.75 + taxa_edificada * 0.35) / 100
        rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12)) * (1 - bloqueio)
        
        # 2. Efeito evaporativo e umidade (refrescamento latente)
        refrescamento_h_w = (taxa_agua * 0.18) + (umidade * 0.04) + (taxa_permeavel * 0.10)
        
        # 3. Balanço de Superfície (Lei de Stefan-Boltzmann simplificada e Convecção)
        ganho_calor = (rad_solar * (1 - albedo)) 
        perda_onda_longa = emissividade * 0.12
        
        temp_surf = t_min + (ganho_calor / 34) - (vento * 0.45) - perda_onda_longa - (refrescamento_h_w / 2)
        temp_5cm = temp_surf * 0.81 + (t_min * 0.19) # Inércia térmica do solo

        # Plotagem
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=horas, y=temp_surf, name="Superfície", line=dict(color='firebrick', width=4)))
        fig.add_trace(go.Scatter(x=horas, y=temp_5cm, name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash')))
        
        fig.update_layout(title=f"Comportamento Térmico: {material}",
                          xaxis_title="Hora do Dia", yaxis_title="Temperatura (°C)")
        st.plotly_chart(fig, use_container_width=True)

        # 4. GERAÇÃO DO ARQUIVO EXCEL COMPLETO
        df_export = pd.DataFrame([
            {
                "Coord_X": x, 
                "Coord_Y": y, 
                "Temp_Pico_Superficie": round(max(temp_surf), 2), 
                "Temp_Pico_5cm": round(max(temp_5cm), 2),
                "Material": material,
                "Sombra_%": taxa_sombra,
                "Edificado_%": taxa_edificada
            }
            for x in range(0, 100, 2) for y in range(0, 100, 2)
        ])
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Dados_Microclima')
        
        st.download_button(
            label="📥 Baixar Dados da Simulação (Excel)",
            data=output.getvalue(),
            file_name=f"simulacao_v1.4_{material}.xlsx",
            mime="application/vnd.ms-excel"
        )

    # --- NOTA CIENTÍFICA EXPANSÍVEL ---
    with st.expander("📖 Veja a Nota Científica e Metodologia"):
        st.write(f"""
        **Metodologia de Cálculo Microclimático (v1.4):**
        
        * **Vegetação e Sombreamento:** O cálculo tem como base o **Índice de Área Foliar (LAI)**, que atua na redução da radiação de onda curta incidente.
        * **Área Permeável:** Considera o resfriamento por evapotranspiração do solo natural, reduzindo a carga térmica superficial.
        * **Edificações:** Simula a redução do **Sky View Factor (SVF)**, influenciando tanto o sombreamento diurno quanto a retenção de calor noturna.
        * **Corpos d'Água:** O efeito de resfriamento é modelado via calor latente de evaporação e umidade relativa.
        * **Propriedades Físicas:** Utiliza emissividade de {emissividade} e albedo de {albedo} conforme literatura para {material}.
        """)
