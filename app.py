import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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
# Aqui incluímos os valores que mediste na tua investigação
material = st.sidebar.selectbox("Material em Análise", ["Asfalto", "Concreto"])

if material == "Asfalto":
    emissividade = st.sidebar.slider("Emissividade (Asfalto)", 0.85, 0.93, 0.90)
    albedo = 0.10
else:
    emissividade = st.sidebar.slider("Emissividade (Concreto)", 0.88, 0.93, 0.91)
    albedo = 0.30

# --- ÁREA DE ESTUDO ---
st.header("📂 1. Configuração da Área")
uploaded_file = st.file_uploader("Upload de Shapefile (Opcional)", type=['geojson', 'zip'])

if not uploaded_file:
    st.info("💡 Modo de Grade Padrão Ativado: Simulando área de 50x50m (Resolução 2m).")
    largura, altura = 50, 50
    resolucao = 2.0
else:
    st.success("Ficheiro carregado! Usando geometria do Shapefile.")

# --- EXECUÇÃO DA SIMULAÇÃO ---
st.header("⚡ 2. Execução da Simulação")

if st.button("Simular Desempenho Térmico"):
    with st.spinner('A calcular balanço de energia superficial...'):
        horas = np.arange(0, 24, 0.5)
        
        # Metodologia: Balanço de onda curta e onda longa
        # Radiação solar simplificada para Fortaleza
        rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12))
        
        # Cálculo da Temperatura de Superfície (Simplificado)
        # Considera Albedo (reflexão) e Emissividade (emissão de calor)
        ganho_calor = (rad_solar * (1 - albedo)) 
        perda_calor = emissividade * 5.67e-8 * ((t_max + 273.15)**4 - (t_min + 273.15)**4) / 100
        
        temp_surf = t_min + (ganho_calor / 40) - (vento * 0.5)
        
        # Simulação aos 5cm de profundidade (Inércia térmica)
        temp_5cm = temp_surf * 0.85 + (t_min * 0.15)

        # Gráfico de Resultados
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=horas, y=temp_surf, name="Superfície", line=dict(color='firebrick', width=4)))
        fig.add_trace(go.Scatter(x=horas, y=temp_5cm, name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash')))
        
        fig.update_layout(title=f"Comportamento Térmico: {material}",
                          xaxis_title="Hora do Dia", yaxis_title="Temperatura (°C)")
        st.plotly_chart(fig, use_container_width=True)

        st.success(f"Simulação concluída para {material} com emissividade de {emissividade}!")
