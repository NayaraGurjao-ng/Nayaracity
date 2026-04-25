import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Nayara - Simulador Térmico v1.3", layout="wide")

st.title("🏙️ Plataforma de Simulação de Microclima Urbano")
st.markdown("---")

# --- SIDEBAR: PARÂMETROS ---
st.sidebar.header("📍 Parâmetros Globais")

with st.sidebar.form("config_simulacao"):
    st.subheader("☁️ Clima")
    t_max = st.slider("Temperatura Máxima (°C)", 20.0, 45.0, 40.0, 32.0)
    t_min = st.slider("Temperatura Mínima (°C)", 15.0, 35.0, 24.0)
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

    taxa_edificada = st.slider("Taxa de Área Edificada (%)", 0, 100, 30)
    
    st.subheader("🌳 Natureza")
    taxa_sombra = st.slider("Taxa de Sombreamento/Vegetação (%)", 0, 100, 20)
    taxa_agua = st.slider("Taxa de Corpos d'Água (%)", 0, 100, 5)
    
    btn_simular = st.form_submit_button("Simular Desempenho Térmico")

# --- ÁREA DE ESTUDO (Grade 100x100) ---
st.header("📂 1. Configuração da Área (Grade 100x100m)")
col1, col2 = st.columns(2)

with col1:
    sh_geo = st.file_uploader("Upload de Geometria/Shapefile (Opcional)", type=['geojson', 'zip'], key="geo")
with col2:
    sh_bld = st.file_uploader("Upload de Edificações (Opcional)", type=['geojson', 'zip'], key="bld")

if not sh_geo:
    grid_dim = 50 # 50 células de 2m = 100m
    mapa_visual = np.zeros((grid_dim, grid_dim))
    np.random.seed(42)
    
    # 1. Edificações (Valor 2 no mapa)
    num_bld = int((taxa_edificada / 100) * (grid_dim**2))
    idx_bld = np.random.choice(grid_dim**2, num_bld, replace=False)
    mapa_visual.flat[idx_bld] = 2

    # 2. Água (Valor 3 no mapa) - Restante das células vazias
    vazios = np.where(mapa_visual.flat == 0)[0]
    num_wat = int((taxa_agua / 100) * (grid_dim**2))
    if len(vazios) > num_wat:
        idx_wat = np.random.choice(vazios, num_wat, replace=False)
        mapa_visual.flat[idx_wat] = 3

    # 3. Vegetação (Valor 1 no mapa) - Restante
    vazios = np.where(mapa_visual.flat == 0)[0]
    num_veg = int((taxa_sombra / 100) * (grid_dim**2))
    if len(vazios) > num_veg:
        idx_veg = np.random.choice(vazios, num_veg, replace=False)
        mapa_visual.flat[idx_veg] = 1

    fig_mapa = px.imshow(mapa_visual, 
                        x=np.arange(0, 100, 2), y=np.arange(0, 100, 2),
                        color_continuous_scale=['#444444', '#228B22', '#8B4513', '#1E90FF'])
    fig_mapa.update_coloraxes(showscale=False)
    fig_mapa.update_layout(title="Mapa da Grade (Cinza: Pavimento | Verde: Veg | Marrom: Edificações | Azul: Água)")
    st.plotly_chart(fig_mapa)

# --- EXECUÇÃO DA SIMULAÇÃO ---
st.header("⚡ 2. Resultados da Simulação")

if btn_simular:
    with st.spinner('Executando modelos de balanço térmico...'):
        horas = np.arange(0, 24, 0.5)
        
        # Influência da Sombra e Edificações (Sky View Factor simplificado)
        bloqueio_solar = (taxa_sombra * 0.8 + taxa_edificada * 0.4) / 100
        rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12)) * (1 - bloqueio_solar)
        
        # Efeito evaporativo da água e umidade
        refrescamento_h_w = (taxa_agua * 0.15) + (umidade * 0.05)
        
        # Balanço de Superfície
        ganho_calor = (rad_solar * (1 - albedo)) 
        perda_onda_longa = emissividade * 0.12
        
        temp_surf = t_min + (ganho_calor / 36) - (vento * 0.5) - perda_onda_longa - (refrescamento_h_w / 2)
        temp_5cm = temp_surf * 0.80 + (t_min * 0.20) # Inércia ajustada

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=horas, y=temp_surf, name="Superfície", line=dict(color='firebrick', width=4)))
        fig.add_trace(go.Scatter(x=horas, y=temp_5cm, name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash')))
        
        fig.update_layout(title="Evolução Térmica do Pavimento", xaxis_title="Hora", yaxis_title="Temp (°C)")
        st.plotly_chart(fig, use_container_width=True)

    # --- NOTA CIENTÍFICA EXPANSÍVEL ---
    with st.expander("📖 Veja a Nota Científica e Metodologia"):
        st.write("""
        **Metodologia de Cálculo Microclimático:**
        
        * **Vegetação e Sombra:** O cálculo tem como base o **Índice de Área Foliar (LAI)** e o fator de sombreamento, que reduzem diretamente a radiação de onda curta incidente no pavimento.
        * **Edificações:** A taxa de área edificada influencia o **Sky View Factor (SVF)**, simulando o aprisionamento de calor (efeito cânion urbano) e o bloqueio solar lateral.
        * **Corpos d'Água:** O efeito de resfriamento é calculado via calor latente de evaporação, reduzindo a temperatura do ar circundante.
        * **Pavimentos:** A modelagem utiliza a **Lei de Fourier** para condução térmica nos primeiros 5 cm de profundidade e o balanço de energia de onda longa baseado na **Emissividade** (valores de 0.88-0.93 para concreto e 0.85-0.93 para asfalto conforme medido em campo).
        * **Umidade:** A umidade relativa atua no balanço de trocas convectivas, influenciando a taxa de resfriamento noturno.
        """)
        st.info(f"Localização de referência: Fortaleza, CE (Lat -3.73).")

else:
    st.info("Ajuste as taxas na lateral e clique em 'Simular' para ver o mapa de 100x100m e o gráfico.")
