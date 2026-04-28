import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
from datetime import time
from streamlit_option_menu import option_menu
from streamlit_folium import st_folium
import folium
import geopandas as gpd
from shapely.geometry import Point

# ==========================================
# CONFIGURAÇÃO E CARREGAMENTO DE DADOS
# ==========================================
st.set_page_config(page_title="Nayara - Simulador Térmico v2.1", layout="wide")

@st.cache_data
def carregar_dados_geograficos():
    try:
        gdf = gpd.read_file("data/bairros.shp")
        gdf = gdf.to_crs(epsg=4326)
        gdf["nome_bairr"] = gdf["nome_bairr"].astype(str).str.strip()
        return gdf
    except Exception as e:
        st.error(f"Erro ao carregar mapa: {e}")
        return None

@st.cache_data
def carregar_dados_bairros():
    try:
        df = pd.read_csv("data/informacoes_bairros.csv")
        df["nome_bairr"] = df["nome_bairr"].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar CSV: {e}")
        return pd.DataFrame({"nome_bairr": ["Fortaleza (Geral)"]})

gdf_mapa = carregar_dados_geograficos()
df_bairros = carregar_dados_bairros()

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🚀 Menu Principal")
    pagina = option_menu(
        menu_title=None,
        options=["Simular Área", "Sobre o Projeto", "Referências"],
        icons=["cpu", "book", "journal-text"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa"},
            "icon": {"color": "orange", "font-size": "20px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#ff4b4b"},
        }
    )

if pagina == "Sobre o Projeto":
    st.title("📖 Sobre o Projeto")
    st.markdown("---")
    st.write("Nayara, aluna de doutorado do Programa de Pós-graduação em Engenharia de Transportes da UFC.")
    st.info("Foco: Análise do microclima urbano em cidades tropicais (Fortaleza/CE).")

elif pagina == "Referências":
    st.title("📄 Produção Acadêmica")
    st.markdown("---")
    st.write("Bases: Scopus e Web of Science.")

else:
    st.title("🏙️ Plataforma de Simulação de Microclima Urbano")
    st.markdown("---")

    st.sidebar.header("📍 Localização e Globais")
    bairro_selecionado = st.sidebar.selectbox("Escolha o Bairro", df_bairros["nome_bairr"].unique())

    # --- LÓGICA DE GEOLOCALIZAÇÃO POR SHAPEFILE ---
    lat_centro, lon_centro = -3.7319, -38.5267 
    poligono_bairro = None

    if gdf_mapa is not None:
        bairro_geo = gdf_mapa[gdf_mapa["nome_bairr"] == bairro_selecionado]
        if not bairro_geo.empty:
            centroide = bairro_geo.geometry.centroid.iloc[0]
            lat_centro, lon_centro = centroide.y, centroide.x
            poligono_bairro = bairro_geo

    with st.sidebar.expander("☁️ Configurações Climáticas", expanded=True):
        t_max = st.slider("Temp. Máxima (°C)", 15, 45, 32)
        t_min = st.slider("Temp. Mínima (°C)", 10, 35, 24)
        umidade = st.slider("Umidade (%)", 10, 100, 65)
        vento = st.number_input("Vento (m/s)", value=2.0)

    with st.sidebar.expander("🏗️ Materiais e Ocupação", expanded=True):
        material = st.selectbox("Material de Referência", ["Asfalto", "Concreto"])
        emissividade = st.slider("Emissividade", 0.85, 0.93, 0.90 if material == "Asfalto" else 0.91)
        albedo = 0.10 if material == "Asfalto" else 0.30
        usar_edificacao = st.checkbox("Simular Edificações?", value=True)
        taxa_edificada = st.slider("Taxa Edificada (%)", 0, 100, 30) if usar_edificacao else 0

    with st.sidebar.expander("🌳 Natureza e Água", expanded=True):
        usar_permeavel = st.checkbox("Simular Solo Permeável?", value=True)
        taxa_permeavel = st.slider("Taxa Permeável (%)", 0, 100, 15) if usar_permeavel else 0
        usar_sombra = st.checkbox("Simular Sombreamento?", value=True)
        taxa_sombra = st.slider("Taxa Sombreamento (%)", 0, 100, 20) if usar_sombra else 0
        usar_agua = st.checkbox("Simular Corpos d'Água?", value=True)
        taxa_agua = st.slider("Taxa Água (%)", 0, 100, 5) if usar_agua else 0

    btn_simular = st.sidebar.button("🚀 EXECUTAR SIMULAÇÃO", use_container_width=True)

    # --- 1. ÁREA DE ESTUDO ---
    st.header(f"🗺️ Área de Estudo: {bairro_selecionado}")
    
    # Criamos o mapa base
    mapa = folium.Map(location=[lat_centro, lon_centro], zoom_start=15, tiles="OpenStreetMap")
    
    if poligono_bairro is not None:
        # Desenha o perímetro original
        folium.GeoJson(
            poligono_bairro,
            style_function=lambda x: {'fillColor': 'orange', 'color': 'red', 'weight': 2, 'fillOpacity': 0.1}
        ).add_to(mapa)
        
        # Só executa a plotagem se o botão de simular for clicado
        if btn_simular:
            geom = poligono_bairro.geometry.iloc[0]
            min_x, min_y, max_x, max_y = geom.bounds
            np.random.seed(42)

            def plotar_densidade(taxa, cor, tipo):
                objetivo = int(taxa / 2)
                contagem = 0
                tentativas = 0
                while contagem < objetivo and tentativas < 500:
                    tentativas += 1
                    lat_r = np.random.uniform(min_y, max_y)
                    lon_r = np.random.uniform(min_x, max_x)
                    if Point(lon_r, lat_r).within(geom):
                        if tipo == "circulo":
                            folium.CircleMarker(
                                location=[lat_r, lon_r],
                                radius=5, color=cor, fill=True, fill_opacity=0.6
                            ).add_to(mapa)
                        else:
                            folium.RegularPolygonMarker(
                                location=[lat_r, lon_r],
                                number_of_sides=4, radius=5, color=cor, fill=True, fill_opacity=0.8
                            ).add_to(mapa)
                        contagem += 1

            plotar_densidade(taxa_sombra, "green", "circulo")
            plotar_densidade(taxa_edificada, "gray", "quadrado")

    # A KEY DINÂMICA resolve o problema do mapa apagar após carregar
    st_folium(mapa, width=1100, height=450, key=f"mapa_{bairro_selecionado}_{btn_simular}")

    # --- 2. RESULTADOS ---
    st.header("⚡Resultados da Simulação")

    if btn_simular:
        horas_num = np.arange(0, 24, 0.5)
        horas_formatadas = [time(int(h), int((h % 1) * 60)).strftime("%H:%M") for h in horas_num]
        
        bloqueio = (taxa_sombra * 0.75 + taxa_edificada * 0.35) / 100
        rad_solar = 800 * np.maximum(0, np.sin((horas_num - 6) * np.pi / 12)) * (1 - bloqueio)
        refrescamento = (taxa_agua * 0.20) + (umidade * 0.05) + (taxa_permeavel * 0.12)
        p_onda_longa = emissividade * 0.12
        temp_surf = t_min + (rad_solar * (1 - albedo) / 34) - (vento * 0.45) - p_onda_longa - (refrescamento / 2)
        temp_5cm = temp_surf * 0.81 + (t_min * 0.19)

        st.session_state['resultados'] = {
            'h_n': horas_num, 'h_f': horas_formatadas, 'ts': temp_surf, 't5': temp_5cm,
            'mat': material, 'em': emissividade, 'tx_s': taxa_sombra, 'tx_e': taxa_edificada,
            'tx_a': taxa_agua, 'tx_p': taxa_permeavel
        }

    if 'resultados' in st.session_state:
        res = st.session_state['resultados']
        c_graph, c_stats = st.columns([3, 1])

        with c_graph:
            fig_res = go.Figure()
            fig_res.add_trace(go.Scatter(x=res['h_n'], y=res['ts'], name="Superfície", line=dict(color='firebrick', width=4),
                                         customdata=res['h_f'], hovertemplate="<b>%{name}</b><br>Hora: %{customdata}<br>Temp: %{y:.1f}°C<extra></extra>"))
            fig_res.add_trace(go.Scatter(x=res['h_n'], y=res['t5'], name="Profundidade (5cm)", line=dict(color='royalblue', dash='dash'),
                                         customdata=res['h_f'], hovertemplate="<b>%{name}</b><br>Hora: %{customdata}<br>Temp: %{y:.1f}°C<extra></extra>"))

            fig_res.update_layout(xaxis=dict(title="Hora do Dia", tickmode='array', tickvals=[0, 3, 6, 9, 12, 15, 18, 21, 23.5], 
                                            ticktext=["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00", "23:59"]), 
                                  yaxis_title="Temperatura (°C)", hovermode="x unified")
            st.plotly_chart(fig_res, use_container_width=True)

        with c_stats:
            st.write("### 🌡️ Variação térmica superficial")
            st.metric("Máxima", f"{max(res['ts']):.1f} °C")
            st.metric("Mínima", f"{min(res['ts']):.1f} °C")
            st.info(f"**ΔT:** {max(res['ts']) - min(res['ts']):.1f} °C")
            
            df_ex = pd.DataFrame({"Hora": res['h_f'], "T_Surf (°C)": res['ts'], "T_5cm (°C)": res['t5']})
            out = BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as w:
                df_ex.to_excel(w, index=False, sheet_name='Resultados')
            st.download_button("📥 Planilha Excel", out.getvalue(), f"simulacao_{res['mat']}.xlsx", use_container_width=True)

        with st.expander("📝 Notas Científicas e Metodologia Aplicada"):
            st.markdown(f"""
            ### Metodologia de Simulação
            Simulação térmica para **Fortaleza/CE**:
            1. **Energia:** Radiação solar filtrada por sombra ({res['tx_s']}%) e área edificada ({res['tx_e']}%).
            2. **Materiais:** Emissividade de **{res['em']}** para o material **{res['mat']}**.
            3. **Inércia:** Profundidade (5cm) via decaimento logarítmico (similar ao **ENVI-met**).
            4. **Mitigação:** Corpos d'água ({res['tx_a']}%) e solo permeável ({res['tx_p']}%).
            """)
