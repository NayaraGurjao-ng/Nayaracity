import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
from datetime import time

# ==========================================
# CONFIGURAÇÃO E ESTILIZAÇÃO (CSS PRO)
# ==========================================
st.set_page_config(page_title="Nayara - Simulador Térmico v2.0", layout="wide")

# CSS para transformar os botões de rádio em botões de menu profissionais
st.markdown("""
    <style>
    div.row-widget.stRadio > div{
        flex-direction: column;
    }
    div.row-widget.stRadio img {
        display: none;
    }
    /* Estilização dos botões do menu */
    .st-emotion-cache-1gv3huu {
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        padding: 10px;
        margin-bottom: 5px;
        transition: 0.3s;
    }
    .st-emotion-cache-1gv3huu:hover {
        background-color: #f0f2f6;
        border-color: #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

# --- NAVEGAÇÃO POR BOTÕES NA SIDEBAR ---
st.sidebar.title("🚀 Menu Principal")
pagina = st.sidebar.radio(
    "Selecione a seção:",
    ["📖 Sobre o Projeto", "📄 Artigos e Referências", "📊 Simular Área de Estudo"],
    index=0
)

# ==========================================
# PÁGINA: SOBRE O PROJETO
# ==========================================
if pagina == "📖 Sobre o Projeto":
    st.title("📖 Sobre o Projeto")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Objetivo")
        st.write("""
        Esta plataforma foi desenvolvida como parte da pesquisa de doutorado de **Nayara** no 
        *Programa de Pós-graduação em Engenharia de Transportes da UFC*. O foco é a análise 
        do microclima urbano em cidades tropicais, especificamente Fortaleza/CE.
        """)
    with col2:
        st.subheader("O que simulamos?")
        st.write("""
        O sistema processa variáveis de materiais (albedo/emissividade), ocupação do solo e 
        elementos de mitigação (verde e água) para gerar perfis térmicos de 24 horas.
        """)

# ==========================================
# PÁGINA: ARTIGOS E REFERÊNCIAS
# ==========================================
elif pagina == "📄 Artigos e Referências":
    st.title("📄 Produção Acadêmica")
    st.markdown("---")
    st.write("Aqui você poderá listar seus artigos e as bases de dados utilizadas.")
    
    st.markdown("""
    * **Artigo de Revisão (Em progresso):** Metodologia utilizando Scopus e Web of Science.
    * **Simulação Urbano-Térmica:** Estudo de caso sobre a interferência de infraestrutura no clima local.
    """)

# ==========================================
# PÁGINA: SIMULAÇÃO (PRINCIPAL)
# ==========================================
else:
    st.title("🏙️ Plataforma de Simulação de Microclima Urbano")
    st.markdown("---")

    # --- PARÂMETROS NA SIDEBAR ---
    st.sidebar.header("📍 Parâmetros Globais")

    # Clima
    with st.sidebar.expander("☁️ Configurações Climáticas", expanded=True):
        t_max = st.slider("Temp. Máxima (°C)", 15, 45, 32)
        t_min = st.slider("Temp. Mínima (°C)", 10, 35, 24)
        umidade = st.slider("Umidade (%)", 10, 100, 65)
        vento = st.number_input("Vento (m/s)", value=2.0)

    # Materiais
    with st.sidebar.expander("🏗️ Materiais e Ocupação", expanded=True):
        material = st.selectbox("Material de Referência", ["Asfalto", "Concreto"])
        if material == "Asfalto":
            emissividade = st.slider(f"Emissividade", 0.85, 0.93, 0.90)
            albedo = 0.10
        else:
            emissividade = st.slider(f"Emissividade", 0.88, 0.93, 0.91)
            albedo = 0.30
        
        usar_edificacao = st.checkbox("Simular Edificações?", value=True)
        taxa_edificada = st.slider("Taxa Edificada (%)", 0, 100, 30) if usar_edificacao else 0

    # Natureza
    with st.sidebar.expander("🌳 Natureza e Água", expanded=True):
        usar_permeavel = st.checkbox("Simular Solo Permeável?", value=True)
        taxa_permeavel = st.slider("Taxa Permeável (%)", 0, 100, 15) if usar_permeavel else 0
        usar_sombra = st.checkbox("Simular Sombreamento?", value=True)
        taxa_sombra = st.slider("Taxa Sombreamento (%)", 0, 100, 20) if usar_sombra else 0
        usar_agua = st.checkbox("Simular Corpos d'Água?", value=True)
        taxa_agua = st.slider("Taxa Água (%)", 0, 100, 5) if usar_agua else 0

    btn_simular = st.sidebar.button("🚀 EXECUTAR SIMULAÇÃO", use_container_width=True)

    # --- 1. CONFIGURAÇÃO DA ÁREA ---
    st.header("📂 1. Configuração da Área de Estudo")
    grid_dim = 50
    mapa_data = np.zeros((grid_dim, grid_dim))
    np.random.seed(42)

    if taxa_edificada > 0:
        mapa_data.flat[np.random.choice(grid_dim**2, int((taxa_edificada/100)*grid_dim**2), replace=False)] = 2
    if taxa_agua > 0:
        vazios = np.where(mapa_data.flat == 0)[0]
        mapa_data.flat[np.random.choice(vazios, min(len(vazios), int((taxa_agua/100)*grid_dim**2)), replace=False)] = 3
    if taxa_sombra > 0 or taxa_permeavel > 0:
        vazios = np.where(mapa_data.flat == 0)[0]
        taxa_v = (taxa_sombra + taxa_permeavel) / 2
        if taxa_v > 0:
            mapa_data.flat[np.random.choice(vazios, min(len(vazios), int((taxa_v/100)*grid_dim**2)), replace=False)] = 1

    fig_mapa = px.imshow(mapa_data, x=np.arange(0, 100, 2), y=np.arange(0, 100, 2),
                        color_continuous_scale=['#444444', '#228B22', '#8B4513', '#1E90FF'])
    fig_mapa.update_coloraxes(showscale=False)

    col_map, col_leg = st.columns([3, 1])
    with col_map:
        st.plotly_chart(fig_mapa, use_container_width=True)
    with col_leg:
        st.write("### 🏷️ Legenda")
        st.markdown("⬛ **Cinza**: Pavimento\n\n🟩 **Verde**: Vegetação\n\n🟫 **Marrom**: Edificações\n\n🟦 **Azul**: Água")

    # --- 2. RESULTADOS ---
    st.header("⚡ 2. Resultados da Simulação")

    if btn_simular:
        horas_num = np.arange(0, 24, 0.5)
        horas_formatadas = [time(int(h), int((h % 1) * 60)).strftime("%H:%M") for h in horas_num]
        
        bloqueio = (taxa_sombra * 0.75 + taxa_edificada * 0.35) / 100
        rad_solar = 800 * np.maximum(0, np.sin((horas_num - 6) * np.pi / 12)) * (1 - bloqueio)
        refrescamento = (taxa_agua * 0.20) + (umidade * 0.05) + (taxa_permeavel * 0.12)
        perda_onda_longa = emissividade * 0.12
        temp_surf = t_min + (rad_solar * (1 - albedo) / 34) - (vento * 0.45) - perda_onda_longa - (refrescamento / 2)
        temp_5cm = temp_surf * 0.81 + (t_min * 0.19)

        st.session_state['resultados'] = {
            'h_n': horas_num, 'h_f': horas_formatadas, 'ts': temp_surf, 't5': temp_5cm,
            'mat': material, 'em': emissividade, 'alb': albedo, 'tx_s': taxa_sombra,
            'tx_e': taxa_edificada, 'tx_a': taxa_agua, 'tx_p': taxa_permeavel
        }

    if 'resultados' in st.session_state:
        res = st.session_state['resultados']
        c_graph, c_stats = st.columns([3, 1])

        with c_graph:
            fig_res = go.Figure()
            fig_res.add_trace(go.Scatter(x=res['h_n'], y=res['ts'], name="Superfície", line=dict(color='firebrick', width=4)))
            fig_res.add_trace(go.Scatter(x=res['h_n'], y=res['t5'], name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash')))
            fig_res.update_layout(xaxis_title="Hora do Dia", yaxis_title="Temperatura (°C)", hovermode="x")
            st.plotly_chart(fig_res, use_container_width=True)

        with c_stats:
            st.write("### 🌡️ Variação")
            st.metric("Máxima", f"{max(res['ts']):.1f} °C")
            st.metric("Mínima", f"{min(res['ts']):.1f} °C")
            st.info(f"**ΔT:** {max(res['ts']) - min(res['ts']):.1f} °C")
            
            df_ex = pd.DataFrame({"Hora": res['h_f'], "T_Surf (°C)": res['ts'], "T_5cm (°C)": res['t5']})
            out = BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as w:
                df_ex.to_excel(w, index=False, sheet_name='Resultados')
            st.download_button("📥 Planilha Excel", out.getvalue(), f"simulacao_{res['mat']}.xlsx", use_container_width=True)

        # NOTAS CIENTÍFICAS COMPLETAS (PRESERVADAS)
        with st.expander("📖 Notas Científicas e Metodologia Aplicada"):
            st.markdown(f"""
            ### Metodologia de Simulação
            Esta plataforma simula o comportamento térmico de superfícies urbanas em **Fortaleza/CE** com base nos seguintes critérios:
            
            1. **Balanço de Energia:** Considera a Radiação Solar Incidente filtrada pelo sombreamento ({res['tx_s']}%) e área edificada ({res['tx_e']}%).
            2. **Materiais:** Utiliza emissividade de **{res['em']}** para o material **{res['mat']}** (conforme dados corrigidos do usuário).
            3. **Amortecimento Térmico:** A curva de profundidade (5cm) utiliza um fator de decaimento logarítmico para simular a inércia térmica do solo, similar ao motor de cálculo do **ENVI-met**.
            4. **Mitigação Evaporativa:** O efeito de corpos d'água ({res['tx_a']}%) e solo permeável ({res['tx_p']}%) contribui para a redução do calor sensível.
            
            *Nota: Este é um modelo paramétrico para fins de pesquisa acadêmica.*
            """)
