import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# ==========================================
# CONFIGURAÇÃO E INTERFACE
# ==========================================
st.set_page_config(page_title="Nayara - Simulador Térmico v1.8", layout="wide")

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

if material == "Asfalto":
    emissividade = st.sidebar.slider(f"Emissividade ({material})", 0.85, 0.93, 0.90)
    albedo = 0.10
else:
    emissividade = st.sidebar.slider(f"Emissividade ({material})", 0.88, 0.93, 0.91)
    albedo = 0.30

taxa_edificada = st.sidebar.slider("Taxa de Área Edificada (%)", 0, 100, 30)

st.sidebar.subheader("🌳 Natureza e Água")
taxa_permeavel = st.sidebar.slider("Taxa de Área Permeável (%)", 0, 100, 15)
taxa_sombra = st.sidebar.slider("Taxa de Sombreamento (%)", 0, 100, 20)
taxa_agua = st.sidebar.slider("Taxa de Corpos d'Água (%)", 0, 100, 5)

btn_simular = st.sidebar.button("Simular Desempenho Térmico")

# ==========================================
# 1. CONFIGURAÇÃO DA ÁREA DE ESTUDO
# ==========================================
st.header("📂 1. Configuração da Área de Estudo")

grid_dim = 50
mapa_data = np.zeros((grid_dim, grid_dim))
np.random.seed(42)

# Lógica de preenchimento da grade
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

col_map, col_leg = st.columns([3, 1])
with col_map:
    st.plotly_chart(fig_mapa, use_container_width=True)
with col_leg:
    st.write("### 🏷️ Legenda")
    st.markdown("⬛ **Cinza**: Pavimento")
    st.markdown("🟩 **Verde**: Vegetação/Permeável")
    st.markdown("🟫 **Marrom**: Edificações")
    st.markdown("🟦 **Azul**: Água")

# ==========================================
# 2. RESULTADOS DA SIMULAÇÃO
# ==========================================
st.header("⚡ 2. Resultados da Simulação")

if btn_simular:
    horas = np.arange(0, 24, 0.5)
    
    # Cálculos
    bloqueio = (taxa_sombra * 0.75 + taxa_edificada * 0.35) / 100
    rad_solar = 800 * np.maximum(0, np.sin((horas - 6) * np.pi / 12)) * (1 - bloqueio)
    refrescamento = (taxa_agua * 0.20) + (umidade * 0.05) + (taxa_permeavel * 0.12)
    perda_onda_longa = emissividade * 0.12
    
    temp_surf = t_min + (rad_solar * (1 - albedo) / 34) - (vento * 0.45) - perda_onda_longa - (refrescamento / 2)
    temp_5cm = temp_surf * 0.81 + (t_min * 0.19)

    # Layout: Gráfico e Métricas LADO A LADO
    col_graph, col_stats = st.columns([3, 1])

    with col_graph:
        fig_res = go.Figure()
        fig_res.add_trace(go.Scatter(x=horas, y=temp_surf, name="Superfície", line=dict(color='firebrick', width=4)))
        fig_res.add_trace(go.Scatter(x=horas, y=temp_5cm, name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash')))
        fig_res.update_layout(xaxis_title="Hora do Dia", yaxis_title="Temperatura (°C)", hovermode="x")
        st.plotly_chart(fig_res, use_container_width=True)

    with col_stats:
        st.write("### 🌡️ Variação Térmica")
        st.metric("Máxima", f"{max(temp_surf):.1f} °C")
        st.metric("Mínima", f"{min(temp_surf):.1f} °C")
        st.info(f"**ΔT:** {max(temp_surf) - min(temp_surf):.1f} °C")
        
        # Download Excel
        export_data = [{"Hora": h, "T_Surf": ts, "T_5cm": t5} for h, ts, t5 in zip(horas, temp_surf, temp_5cm)]
        df_export = pd.DataFrame(export_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False)
        st.download_button("📥 Planilha", output.getvalue(), f"simulacao_{material}.xlsx", use_container_width=True)

# EXPANDER DE METODOLOGIA (Sempre visível após simular)
    with st.expander("📖 Notas Científicas e Metodologia Aplicada"):
        st.write(f"""
        Esta simulação utiliza parâmetros térmicos para a cidade de Fortaleza/CE:
        * **Emissividade:** Configurada em {emissividade} para {material}.
        * **Curva de Profundidade:** Estimativa de amortecimento a 5cm (Referência ENVI-met).
        * **Mitigação:** Considera refrescamento evaporativo por água ({taxa_agua}%) e solo permeável.
        """)
