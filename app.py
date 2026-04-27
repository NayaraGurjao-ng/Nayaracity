import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
from datetime import time

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

usar_edificacao = st.sidebar.checkbox("Simular Edificações?", value=True)
taxa_edificada = st.sidebar.slider("Taxa de Área Edificada (%)", 0, 100, 30) if usar_edificacao else 0

st.sidebar.subheader("🌳 Natureza e Água")
usar_permeavel = st.sidebar.checkbox("Simular Solo Permeável?", value=True)
taxa_permeavel = st.sidebar.slider("Taxa de Área Permeável (%)", 0, 100, 15) if usar_permeavel else 0

usar_sombra = st.sidebar.checkbox("Simular Sombreamento?", value=True)
taxa_sombra = st.sidebar.slider("Taxa de Sombreamento (%)", 0, 100, 20) if usar_sombra else 0

usar_agua = st.sidebar.checkbox("Simular Corpos d'Água?", value=True)
taxa_agua = st.sidebar.slider("Taxa de Corpos d'Água (%)", 0, 100, 5) if usar_agua else 0

btn_simular = st.sidebar.button("Simular Desempenho Térmico")

# ==========================================
# 1. CONFIGURAÇÃO DA ÁREA DE ESTUDO
# ==========================================
st.header("📂 1. Configuração da Área de Estudo")

grid_dim = 50
mapa_data = np.zeros((grid_dim, grid_dim))
np.random.seed(42)

if taxa_edificada > 0:
    idx_edif = np.random.choice(grid_dim**2, int((taxa_edificada/100)*grid_dim**2), replace=False)
    mapa_data.flat[idx_edif] = 2
if taxa_agua > 0:
    vazios = np.where(mapa_data.flat == 0)[0]
    idx_agua = np.random.choice(vazios, min(len(vazios), int((taxa_agua/100)*grid_dim**2)), replace=False)
    mapa_data.flat[idx_agua] = 3
if taxa_sombra > 0 or taxa_permeavel > 0:
    vazios = np.where(mapa_data.flat == 0)[0]
    taxa_verde_visual = (taxa_sombra + taxa_permeavel) / 2
    if taxa_verde_visual > 0:
        idx_verde = np.random.choice(vazios, min(len(vazios), int((taxa_verde_visual/100)*grid_dim**2)), replace=False)
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
# 2. RESULTADOS DA SIMULAÇÃO (COM MEMÓRIA)
# ==========================================
st.header("⚡ 2. Resultados da Simulação")

# Lógica para manter os dados na tela
if btn_simular:
    horas_num = np.arange(0, 24, 0.5)
    
    # Formatação da hora para o Excel (0.5 -> 00:30:00)
    horas_formatadas = []
    for h in horas_num:
        minutos = int((h % 1) * 60)
        horas_formatadas.append(time(int(h), minutos).strftime("%H:%M"))

    # Cálculos
    bloqueio = (taxa_sombra * 0.75 + taxa_edificada * 0.35) / 100
    rad_solar = 800 * np.maximum(0, np.sin((horas_num - 6) * np.pi / 12)) * (1 - bloqueio)
    refrescamento = (taxa_agua * 0.20) + (umidade * 0.05) + (taxa_permeavel * 0.12)
    perda_onda_longa = emissividade * 0.12
    
    temp_surf = t_min + (rad_solar * (1 - albedo) / 34) - (vento * 0.45) - perda_onda_longa - (refrescamento / 2)
    temp_5cm = temp_surf * 0.81 + (t_min * 0.19)

    # Salva no estado da sessão para não sumir ao baixar o arquivo
    st.session_state['resultados'] = {
        'horas_num': horas_num,
        'horas_formatadas': horas_formatadas,
        'temp_surf': temp_surf,
        'temp_5cm': temp_5cm,
        'material': material
    }

# Exibição dos resultados (se existirem na memória)
if 'resultados' in st.session_state:
    res = st.session_state['resultados']
    
    col_graph, col_stats = st.columns([3, 1])

    with col_graph:
        fig_res = go.Figure()
        fig_res.add_trace(go.Scatter(x=res['horas_num'], y=res['temp_surf'], name="Superfície", line=dict(color='firebrick', width=4)))
        fig_res.add_trace(go.Scatter(x=res['horas_num'], y=res['temp_5cm'], name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash')))
        fig_res.update_layout(xaxis_title="Hora do Dia", yaxis_title="Temperatura (°C)", hovermode="x")
        st.plotly_chart(fig_res, use_container_width=True)

    with col_stats:
        st.write("### 🌡️ Variação Térmica")
        st.metric("Máxima", f"{max(res['temp_surf']):.1f} °C")
        st.metric("Mínima", f"{min(res['temp_surf']):.1f} °C")
        st.info(f"**ΔT:** {max(res['temp_surf']) - min(res['temp_surf']):.1f} °C")
        
        # Preparação do Excel com formato de Hora
        df_export = pd.DataFrame({
            "Hora": res['horas_formatadas'],
            "T_Surf (°C)": res['temp_surf'],
            "T_5cm (°C)": res['temp_5cm']
        })
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Simulacao')
            # Ajuste de largura de coluna no Excel
            worksheet = writer.sheets['Simulacao']
            worksheet.set_column('A:C', 15)
            
        st.download_button(
            label="📥 Baixar Planilha Excel",
            data=output.getvalue(),
            file_name=f"simulacao_{res['material']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with st.expander("📖 Notas Científicas e Metodologia Aplicada"):
        st.markdown(f"""
        ### Metodologia de Simulação
        Esta plataforma simula o comportamento térmico em **Fortaleza/CE**:
        1. **Balanço de Energia:** Radiação solar filtrada por sombra ({taxa_sombra}%) e edifícios.
        2. **Materiais:** Emissividade de **{emissividade}** para **{material}**.
        3. **Inércia:** Curva de 5cm calculada via decaimento térmico condutivo.
        """)
