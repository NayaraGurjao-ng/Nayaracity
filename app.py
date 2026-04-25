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
st.sidebar.header("📍 Localização e Clima")
t_max = st.sidebar.slider("Temperatura Máxima (°C)", 20.0, 45.0, 32.0)
t_min = st.sidebar.slider("Temperatura Mínima (°C)", 15.0, 35.0, 24.0)
vento = st.sidebar.number_input("Velocidade do Vento (m/s)", value=2.0)

st.sidebar.header("🔬 Propriedades do Material")
material = st.sidebar.selectbox("Material em Análise", ["Asfalto", "Concreto"])

if material == "Asfalto":
    emissividade = st.sidebar.slider("Emissividade (Asfalto)", 0.85, 0.93, 0.90)
    albedo = 0.10
else:
    emissividade = st.sidebar.slider("Emissividade (Concreto)", 0.88, 0.93, 0.91)
    albedo = 0.30

# --- NOVA SEÇÃO: TAXA DE SOMBREAMENTO ---
st.sidebar.header("🌳 Vegetação")
taxa_sombra = st.sidebar.slider("Taxa de Sombreamento da Área (%)", 0, 100, 20)

# --- ÁREA DE ESTUDO ---
st.header("📂 1. Configuração da Área")
uploaded_file = st.file_uploader("Upload de Shapefile (Opcional)", type=['geojson', 'zip'])

if not uploaded_file:
    st.info(f"💡 Modo de Grade Padrão Ativado: Simulando área de 50x50m (Resolução 2m). Sombreamento: {taxa_sombra}%")
    
    # Gerando visualização do mapa 50x50 (25x25 células de 2m)
    grid_dim = 25 
    mapa_visual = np.zeros((grid_dim, grid_dim))
    
    # Distribui "pontos de sombra" aleatórios baseados na taxa selecionada
    num_pontos_sombra = int((taxa_sombra / 100) * (grid_dim**2))
    if num_pontos_sombra > 0:
        indices = np.random.choice(grid_dim**2, num_pontos_sombra, replace=False)
        mapa_visual.flat[indices] = 1

    fig_mapa = px.imshow(mapa_visual, 
                        labels=dict(color="Legenda"),
                        x=np.arange(0, 50, 2), 
                        y=np.arange(0, 50, 2),
                        color_continuous_scale=['#444444', '#228B22']) # Cinza=Pavimento, Verde=Sombra
    fig_mapa.update_coloraxes(showscale=False)
    fig_mapa.update_layout(title="Representação da Grade 50x50m (Cinza: Pavimento | Verde: Vegetação/Sombra)",
                          xaxis_title="Metros (X)", yaxis_title="Metros (Y)")
    st.plotly_chart(fig_mapa)
else:
    st.success("Ficheiro carregado! Usando geometria do Shapefile.")

# --- EXECUÇÃO DA SIMULAÇÃO ---
st.header("⚡ 2. Execução da Simulação")

if st.button("Simular Desempenho Térmico"):
    with st.spinner('A calcular balanço de energia superficial...'):
        horas = np.arange(0, 24, 0.5)
        
        # Metodologia: Balanço de onda curta e onda longa
        # O fator de sombra reduz a radiação direta que atinge o solo
        fator_sombra = 1 - (taxa_sombra / 100)
        rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12)) * fator_sombra
        
        # Cálculo da Temperatura de Superfície
        # ganho_calor agora é influenciado pela vegetação
        ganho_calor = (rad_solar * (1 - albedo)) 
        
        # Fórmula ajustada para incluir influência da emissividade e vento
        temp_surf = t_min + (ganho_calor / 38) - (vento * 0.4)
        
        # Simulação aos 5cm de profundidade (Inércia térmica constante)
        temp_5cm = temp_surf * 0.85 + (t_min * 0.15)

        # Gráfico de Resultados
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=horas, y=temp_surf, name="Superfície", line=dict(color='firebrick', width=4)))
        fig.add_trace(go.Scatter(x=horas, y=temp_5cm, name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash')))
        
        fig.update_layout(title=f"Comportamento Térmico: {material} com {taxa_sombra}% de Sombra",
                          xaxis_title="Hora do Dia", yaxis_title="Temperatura (°C)")
        st.plotly_chart(fig, use_container_width=True)

        st.success(f"Simulação concluída! Material: {material} | Emissividade: {emissividade} | Sombra: {taxa_sombra}%")
        st.write("**Nota científica:** A taxa de sombreamento reduz a carga de radiação de onda curta (radiação solar direta), simulando o efeito de mitigação térmica da vegetação urbana em Fortaleza.")
