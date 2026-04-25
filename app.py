import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Nayara - Simulador Térmico", layout="wide")

st.title("🏙️ Plataforma de Simulação de Microclima Urbano")
st.markdown("---")

# --- SIDEBAR: PARÂMETROS ---
st.sidebar.header("📍 Parâmetros Globais")

# Criando um formulário para que o site só atualize ao clicar no botão
with st.sidebar.form("config_simulacao"):
    st.subheader("Clima")
    t_max = st.slider("Temperatura Máxima (°C)", 20.0, 45.0, 32.0)
    t_min = st.slider("Temperatura Mínima (°C)", 15.0, 35.0, 24.0)
    vento = st.number_input("Velocidade do Vento (m/s)", value=2.0)

    st.subheader("Material")
    material = st.selectbox("Material em Análise", ["Asfalto", "Concreto"])
    
    if material == "Asfalto":
        emissividade = st.slider("Emissividade (Asfalto)", 0.85, 0.93, 0.90)
        albedo = 0.10
    else:
        emissividade = st.slider("Emissividade (Concreto)", 0.88, 0.93, 0.91)
        albedo = 0.30

    st.subheader("Vegetação")
    taxa_sombra = st.slider("Taxa de Sombreamento (%)", 0, 100, 20)
    
    # Botão de submissão dentro do formulário
    btn_simular = st.form_submit_button("Simular Desempenho Térmico")

# --- ÁREA DE ESTUDO (Visualização Estática até o clique) ---
st.header("📂 1. Configuração da Área")
uploaded_file = st.file_uploader("Upload de Shapefile (Opcional)", type=['geojson', 'zip'])

if not uploaded_file:
    # Gerando o mapa visual
    grid_dim = 25 
    mapa_visual = np.zeros((grid_dim, grid_dim))
    num_pontos_sombra = int((taxa_sombra / 100) * (grid_dim**2))
    if num_pontos_sombra > 0:
        # Usamos uma semente fixa (seed) para o mapa não mudar toda hora sozinho
        np.random.seed(42)
        indices = np.random.choice(grid_dim**2, num_pontos_sombra, replace=False)
        mapa_visual.flat[indices] = 1

    fig_mapa = px.imshow(mapa_visual, 
                        x=np.arange(0, 50, 2), 
                        y=np.arange(0, 50, 2),
                        color_continuous_scale=['#444444', '#228B22'])
    fig_mapa.update_coloraxes(showscale=False)
    fig_mapa.update_layout(title="Representação da Grade 50x50m (Cinza: Pavimento | Verde: Sombra)",
                          xaxis_title="Metros (X)", yaxis_title="Metros (Y)")
    st.plotly_chart(fig_mapa)

# --- EXECUÇÃO DA SIMULAÇÃO (Apenas após o clique) ---
st.header("⚡ 2. Resultados da Simulação")

if btn_simular:
    with st.spinner('Processando cálculos...'):
        horas = np.arange(0, 24, 0.5)
        
        # Redução da radiação solar direta pela sombra
        fator_sombra = 1 - (taxa_sombra / 100)
        rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12)) * fator_sombra
        
        # Balanço de Energia
        ganho_calor = (rad_solar * (1 - albedo)) 
        # A perda de calor considera a emissividade (onda longa)
        perda_onda_longa = emissividade * 0.1 
        
        temp_surf = t_min + (ganho_calor / 38) - (vento * 0.4) - perda_onda_longa
        
        # Profundidade 5cm (Fator de amortecimento térmico)
        temp_5cm = temp_surf * 0.82 + (t_min * 0.18)

        # Gráfico
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=horas, y=temp_surf, name="Superfície", line=dict(color='firebrick', width=4)))
        fig.add_trace(go.Scatter(x=horas, y=temp_5cm, name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash')))
        
        fig.update_layout(title=f"Resultados: {material} | Sombra: {taxa_sombra}%",
                          xaxis_title="Hora do Dia", yaxis_title="Temperatura (°C)")
        st.plotly_chart(fig, use_container_width=True)

        st.success(f"Simulação concluída! Pico de Superfície: {max(temp_surf):.1f}°C")
else:
    st.info("Aguardando configuração. Ajuste os parâmetros na lateral e clique em 'Simular Desempenho Térmico'.")
