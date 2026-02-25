# app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime
import unicodedata
from streamlit_echarts import st_echarts

from analyzer import R6Analyzer
from config import TIME_ALIADO, TIME_ADVERSARIO, SEASON_ATUAL, PLAYLIST


# ══════════════════════════════════════════════
#  CONFIGURAÇÃO DA PÁGINA
# ══════════════════════════════════════════════

st.set_page_config(
    page_title="R6 Team Analyzer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        color: #FF6B35;
        text-align: center;
        padding: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .sub-header {
        font-size: 1.2rem;
        color: #888;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 1.5rem;
        border-left: 4px solid #FF6B35;
        margin: 0.5rem 0;
    }
    .pick-card {
        background: linear-gradient(135deg, #0d3b0d 0%, #1a5c1a 100%);
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
        border: 1px solid #2ecc71;
    }
    .ban-card {
        background: linear-gradient(135deg, #3b0d0d 0%, #5c1a1a 100%);
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
        border: 1px solid #e74c3c;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1a2e;
        border-radius: 8px;
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  FUNÇÕES AUXILIARES E CONSTANTES
# ══════════════════════════════════════════════

CACHE_DIR = "cache"

ATTACKERS = [
    "Sledge", "Thatcher", "Ash", "Thermite", "Twitch", "Montagne", "Glaz", "Fuze", 
    "Blitz", "IQ", "Buck", "Blackbeard", "Capitão", "Hibana", "Jackal", "Ying", 
    "Zofia", "Dokkaebi", "Lion", "Finka", "Maverick", "Nomad", "Gridlock", "Nøkk", 
    "Amaru", "Kali", "Iana", "Ace", "Zero", "Flores", "Osa", "Sens", "Grim", 
    "Brava", "Ram", "Deimos", "Striker", "Capitao", "Nokk"
]

DEFENDERS = [
    "Smoke", "Mute", "Castle", "Pulse", "Doc", "Rook", "Kapkan", "Tachanka", 
    "Jäger", "Jager", "Bandit", "Frost", "Valkyrie", "Caveira", "Echo", "Mira", 
    "Lesion", "Ela", "Vigil", "Maestro", "Alibi", "Clash", "Kaid", "Mozzie", 
    "Warden", "Goyo", "Wamai", "Oryx", "Melusi", "Aruni", "Thunderbird", "Thorn", 
    "Azami", "Solis", "Fenrir", "Tubarão", "Tubarao", "Skopos", "Sentry"
]

def normalize_op(name):
    return ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn').lower()

ATTACKERS_NORM = {normalize_op(op) for op in ATTACKERS}
DEFENDERS_NORM = {normalize_op(op) for op in DEFENDERS}

def get_role(op_name):
    norm = normalize_op(op_name)
    if norm in ATTACKERS_NORM: return "Ataque"
    if norm in DEFENDERS_NORM: return "Defesa"
    return "Desconhecido"


def salvar_cache(dados, nome_time):
    """Salva dados no cache local."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    filepath = os.path.join(CACHE_DIR, f"{nome_time}.json")
    dados_salvos = {
        "timestamp": datetime.now().isoformat(),
        "dados": dados
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(dados_salvos, f, ensure_ascii=False, indent=2)


def carregar_cache(nome_time):
    """Carrega dados do cache."""
    filepath = os.path.join(CACHE_DIR, f"{nome_time}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados
    return None


def buscar_dados_time(config_time, fetch_type="both", progress_bar=None):
    """Busca dados do time via scrapper."""
    from scraper import get_r6_team_stats

    titulos = {
        "both": "tudo...",
        "maps": "mapas...",
        "agentes": "operadores...",
        "fase": "fase..."
    }
    desc = titulos.get(fetch_type, "dados...")

    if progress_bar:
        progress_bar.progress(10, text=f"Iniciando navegador para buscar {desc}")

    resultado = get_r6_team_stats(
        player_configs=config_time["jogadores"],
        season=SEASON_ATUAL,
        playlist=PLAYLIST,
        fetch_type=fetch_type
    )

    if progress_bar:
        progress_bar.progress(100, text="Coleta finalizada!")

    return resultado

def atualizar_estado_sessao(equipe, novos_dados, fetch_type="both"):
    """Atualiza o state apenas com a parte que foi buscada."""
    chave = f"dados_{equipe}"
    if chave not in st.session_state:
        st.session_state[chave] = {"mapas": [], "agentes": [], "fase": [], "erros": []}
    
    if fetch_type in ["both", "maps"]:
        st.session_state[chave]["mapas"] = novos_dados.get("mapas", [])
    if fetch_type in ["both", "agentes"]:
        st.session_state[chave]["agentes"] = novos_dados.get("agentes", [])
    if fetch_type in ["both", "fase"]:
        st.session_state[chave]["fase"] = novos_dados.get("fase", [])
    
    erros = novos_dados.get("erros", [])
    if erros:
        st.session_state[chave]["erros"].extend(erros)
        
    salvar_cache(st.session_state[chave], equipe)


# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════

with st.sidebar:
    st.image(
        "https://staticctf.ubisoft.com/J3yJr34U2pZ2Ieem48Dwy9uqj5P"
        "NUQTn6UqGm0p5hso=/0/0/0/0/0/0/0/0/0/0/"
        "placeholder.png",
        width=60
    )
    st.title("⚙️ Controles")

    st.divider()

    # ── Configuração de nicks inline ──
    st.subheader("📝 Time Adversário")
    col1, col2 = st.columns([7, 3])
    with col1:
        st.caption("Nick")
    with col2:
        st.caption("Plataforma")

    for i in range(5):
        df_nick = TIME_ADVERSARIO["jogadores"][i]["nick"] if i < len(TIME_ADVERSARIO["jogadores"]) else ""
        df_plat = TIME_ADVERSARIO["jogadores"][i]["platform"] if i < len(TIME_ADVERSARIO["jogadores"]) else "uplay"
        c1, c2 = st.columns([7, 3])
        with c1:
            st.text_input("Nick Adversário", value=df_nick, key=f"adv_nick_{i}", label_visibility="collapsed")
        with c2:
            st.selectbox("Plataforma Adversário", ["uplay", "psn", "xbl"], index=["uplay", "psn", "xbl"].index(df_plat) if df_plat in ["uplay", "psn", "xbl"] else 0, key=f"adv_plat_{i}", label_visibility="collapsed")

    st.subheader("📝 Meu Time")
    col1, col2 = st.columns([7, 3])
    with col1:
        st.caption("Nick")
    with col2:
        st.caption("Plataforma")

    for i in range(5):
        df_nick = TIME_ALIADO["jogadores"][i]["nick"] if i < len(TIME_ALIADO["jogadores"]) else ""
        df_plat = TIME_ALIADO["jogadores"][i]["platform"] if i < len(TIME_ALIADO["jogadores"]) else "uplay"
        c1, c2 = st.columns([7, 3])
        with c1:
            st.text_input("Nick Aliado", value=df_nick, key=f"ali_nick_{i}", label_visibility="collapsed")
        with c2:
            st.selectbox("Plataforma Aliado", ["uplay", "psn", "xbl"], index=["uplay", "psn", "xbl"].index(df_plat) if df_plat in ["uplay", "psn", "xbl"] else 0, key=f"ali_plat_{i}", label_visibility="collapsed")

    st.divider()

    # Removido os botões globais da sidebar para otimizar o carregamento.
    # A busca agora é contextual dentro de cada Tab.



    # Filtros
    min_partidas_mapa = st.slider(
        "Min. partidas (Mapas)",
        1, 20, 3
    )
    min_partidas_op = st.slider(
        "Min. partidas (Operadores)",
        1, 20, 5
    )
    top_n_ops = st.slider(
        "Top N Operadores",
        5, 25, 10
    )


# ══════════════════════════════════════════════
#  PROCESSAR NICKS DA SIDEBAR
# ══════════════════════════════════════════════

def get_jogadores_from_state(prefix):
    """Coleta jogadores dos inputs individuais da sidebar."""
    jogadores = []
    for i in range(5):
        nick = st.session_state.get(f"{prefix}_nick_{i}", "").strip()
        if nick:
            plat = st.session_state.get(f"{prefix}_plat_{i}", "uplay")
            jogadores.append({"nick": nick, "platform": plat})
    return jogadores


# As lógicas de busca foram movidas para as seções de cada Tab.

# Carregar do cache se não estiver na sessão
if "dados_adversario" not in st.session_state:
    cache = carregar_cache("adversario")
    if cache:
        st.session_state["dados_adversario"] = cache["dados"]

if "dados_aliado" not in st.session_state:
    cache = carregar_cache("aliado")
    if cache:
        st.session_state["dados_aliado"] = cache["dados"]


# ══════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════

st.markdown(
    '<p class="main-header">🎯 R6 SIEGE TEAM ANALYZER</p>',
    unsafe_allow_html=True
)
st.markdown(
    '<p class="sub-header">'
    'Inteligência tática para sua equipe competitiva'
    '</p>',
    unsafe_allow_html=True
)


# ══════════════════════════════════════════════
#  TABS PRINCIPAIS
# ══════════════════════════════════════════════

tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Mapas Adversário",
    "🎖️ Operadores Adversário",
    "📊 Comparativo",
    "🔥 Fase dos Jogadores"
])


# ── TAB 1: MAPAS DO ADVERSÁRIO ──
with tab1:
    col_hdr, col_btn1, col_btn2 = st.columns([2, 1, 1])
    with col_hdr:
        st.header("🗺️ Ferramenta 1: Melhores Mapas")
    with col_btn1:
        if st.button("🔍 Carregar Mapas (Adv)", key="btn_maps_adv"):
            jogadores_adv = get_jogadores_from_state("adv")
            if jogadores_adv:
                config = {"nome": "adversario", "jogadores": jogadores_adv}
                with st.spinner("🔍 Coletando dados do time adversário..."):
                    progress = st.progress(0)
                    dados = buscar_dados_time(config, fetch_type="maps", progress_bar=progress)
                    atualizar_estado_sessao("adversario", dados, "maps")
                st.success("✅ Mapas do adversário coletados!")
            else:
                st.error("Insira pelo menos um nick (Adv).")
    with col_btn2:
        if st.button("🔍 Carregar Mapas (Nós)", key="btn_maps_ali"):
            jogadores_ali = get_jogadores_from_state("ali")
            if jogadores_ali:
                config = {"nome": "aliado", "jogadores": jogadores_ali}
                with st.spinner("🔍 Coletando dados do seu time..."):
                    progress = st.progress(0)
                    dados = buscar_dados_time(config, fetch_type="maps", progress_bar=progress)
                    atualizar_estado_sessao("aliado", dados, "maps")
                st.success("✅ Mapas do aliado coletados!")
            else:
                st.error("Insira pelo menos um nick (Aliado).")

    if "dados_adversario" in st.session_state and "mapas" in st.session_state["dados_adversario"] and len(st.session_state["dados_adversario"]["mapas"]) > 0:
        analyzer_adv = R6Analyzer(st.session_state["dados_adversario"])
        df_mapas = analyzer_adv.melhores_mapas_time(min_partidas_mapa)

        if not df_mapas.empty:
            # ── Métricas resumo ──
            col1, col2, col3 = st.columns(3)
            melhor_mapa = df_mapas.iloc[0]
            pior_mapa = df_mapas.iloc[-1]

            with col1:
                st.metric(
                    "🏆 Melhor Mapa do Adversário",
                    melhor_mapa["Mapa"],
                    f"{melhor_mapa['WinRate_Ponderado']}% WR"
                )
            with col2:
                st.metric(
                    "💀 Pior Mapa do Adversário",
                    pior_mapa["Mapa"],
                    f"{pior_mapa['WinRate_Ponderado']}% WR"
                )
            with col3:
                st.metric(
                    "📊 Mapas Analisados",
                    len(df_mapas),
                    f"{df_mapas['Total_Partidas'].sum()} partidas"
                )

            st.divider()

            # ── Gráfico principal de mapas ──
            col_chart1, col_chart2 = st.columns([3, 2])

            with col_chart1:
                df_sorted = df_mapas.sort_values("WinRate_Ponderado", ascending=True)
                mapas = df_sorted["Mapa"].tolist()
                wrs = df_sorted["WinRate_Ponderado"].tolist()
                
                colors = []
                for w in wrs:
                    if w < 45: colors.append("#e74c3c")
                    elif w > 55: colors.append("#2ecc71")
                    else: colors.append("#f39c12")

                bar_options = {
                    "title": {
                        "text": "Win Rate por Mapa",
                        "textStyle": {"color": "#fff"}
                    },
                    "tooltip": {
                        "trigger": "axis",
                        "axisPointer": {"type": "shadow"}
                    },
                    "grid": {
                        "left": "3%",
                        "right": "4%",
                        "bottom": "3%",
                        "containLabel": True
                    },
                    "xAxis": {
                        "type": "value",
                        "max": 100,
                        "splitLine": {"show": False},
                        "axisLabel": {"color": "#aaa"}
                    },
                    "yAxis": {
                        "type": "category",
                        "data": mapas,
                        "axisLabel": {"color": "#fff"}
                    },
                    "series": [
                        {
                            "name": "Win Rate (%)",
                            "type": "bar",
                            "data": [
                                {"value": w, "itemStyle": {"color": c}}
                                for w, c in zip(wrs, colors)
                            ],
                            "label": {
                                "show": True,
                                "position": "right",
                                "formatter": "{c}%",
                                "color": "#fff"
                            },
                            "markLine": {
                                "data": [{"xAxis": 50}],
                                "lineStyle": {"color": "#fff", "type": "dashed"}
                            }
                        }
                    ]
                }
                st_echarts(options=bar_options, height="400px")

            with col_chart2:
                radar_options = {
                    "title": {
                        "text": "Radar de Mapas",
                        "textStyle": {"color": "#fff"}
                    },
                    "tooltip": {},
                    "radar": {
                        "indicator": [
                            {"name": m, "max": 100} for m in df_mapas["Mapa"].tolist()
                        ],
                        "splitArea": {"show": False},
                        "axisName": {"color": "#fff"}
                    },
                    "series": [{
                        "name": "Win Rate",
                        "type": "radar",
                        "data": [{
                            "value": df_mapas["WinRate_Ponderado"].tolist(),
                            "name": "Win Rate",
                            "areaStyle": {"color": "rgba(255, 107, 53, 0.4)"},
                            "lineStyle": {"color": "#FF6B35"},
                            "itemStyle": {"color": "#FF6B35"}
                        }]
                    }]
                }
                st_echarts(options=radar_options, height="400px")

            # ── Recomendações de Ban ──
            st.subheader("🎯 Recomendação de Ban/Pick de Mapa")

            cols_per_row = 4
            for i in range(0, len(df_mapas), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(df_mapas):
                        row = df_mapas.iloc[i + j]
                        wr = row["WinRate_Ponderado"]
                        with cols[j]:
                            if wr >= 55:
                                st.markdown(
                                    f'<div class="ban-card">'
                                    f'<strong>❌ BAN</strong><br>'
                                    f'{row["Mapa"]}<br>'
                                    f'{wr}% WR</div>',
                                    unsafe_allow_html=True
                                )
                            elif wr <= 45:
                                st.markdown(
                                    f'<div class="pick-card">'
                                    f'<strong>✅ FORÇAR</strong><br>'
                                    f'{row["Mapa"]}<br>'
                                    f'{wr}% WR</div>',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.info(
                                    f"⚠️ {row['Mapa']}: {wr}% (Neutro)"
                                )

            # ── Tabela detalhada ──
            st.divider()
            st.subheader("📋 Dados Detalhados por Mapa")

            mapa_selecionado = st.selectbox(
                "Selecione um mapa para ver detalhes:",
                df_mapas["Mapa"].tolist()
            )

            if mapa_selecionado:
                df_detalhe = analyzer_adv.mapa_por_jogador(
                    mapa_selecionado
                )
                if not df_detalhe.empty:
                    st.dataframe(
                        df_detalhe[
                            ["Jogador", "Partidas", "WinPct"]
                        ].style.background_gradient(
                            subset=["WinPct"],
                            cmap="RdYlGn"
                        ),
                        width='stretch',
                        hide_index=True
                    )
        else:
            st.warning(
                "Sem dados de mapas suficientes. "
                "Ajuste o filtro de mínimo de partidas ou confirme a busca de jogadores."
            )
    else:
        st.info(
            "👈 Clique nos botões acima para iniciar a busca de mapas."
        )

# ── TAB 2: OPERADORES DO ADVERSÁRIO ──
with tab2:
    col_hdr, col_btn1 = st.columns([3, 1])
    with col_hdr:
        st.header("🎖️ Ferramenta 2: Operadores do Adversário")
    with col_btn1:
        if st.button("🔍 Carregar Operadores", key="btn_ops_adv"):
            jogadores_adv = get_jogadores_from_state("adv")
            if jogadores_adv:
                config = {"nome": "adversario", "jogadores": jogadores_adv}
                with st.spinner("🔍 Coletando operadores..."):
                    progress = st.progress(0)
                    dados = buscar_dados_time(config, fetch_type="agentes", progress_bar=progress)
                    atualizar_estado_sessao("adversario", dados, "agentes")
                st.success("✅ Operadores do adversário coletados!")
            else:
                st.error("Insira pelo menos um nick.")

    if "dados_adversario" in st.session_state and "agentes" in st.session_state["dados_adversario"] and len(st.session_state["dados_adversario"]["agentes"]) > 0:
        analyzer_adv = R6Analyzer(st.session_state["dados_adversario"])

        # Top operadores gerais
        df_ops_all = analyzer_adv.melhores_operadores(
            min_partidas_op, 50  # Pegamos todos para poder dividir em top_n por role
        )

        if not df_ops_all.empty:
            df_ops_all["Role"] = df_ops_all["Agente"].apply(get_role)
            
            tab_atk, tab_def = st.tabs(["⚔️ Ataque", "🛡️ Defesa"])
            
            # Helper para renderizar a interface de operadores por grupo
            def render_ops_tab(df_ops, role_name):
                df_filtered = df_ops[df_ops["Role"] == role_name].head(top_n_ops)
                
                if df_filtered.empty:
                    st.info(f"Sem dados suficientes para {role_name}.")
                    return

                # ── Métricas ──
                col1, col2, col3, col4 = st.columns(4)
                top_op = df_filtered.iloc[0]

                with col1:
                    st.metric(
                        "🏆 Melhor",
                        top_op["Agente"],
                        f"Score: {top_op['Score']}"
                    )
                with col2:
                    st.metric(
                        "📈 Maior Win Rate",
                        df_filtered.loc[
                            df_filtered["WinRate_Medio"].idxmax(), "Agente"
                        ],
                        f"{df_filtered['WinRate_Medio'].max()}%"
                    )
                with col3:
                    st.metric(
                        "⚔️ Maior KD",
                        df_filtered.loc[
                            df_filtered["KD_Medio"].idxmax(), "Agente"
                        ],
                        f"{df_filtered['KD_Medio'].max()}"
                    )
                with col4:
                    st.metric(
                        "👥 Mais Popular",
                        df_filtered.loc[
                            df_filtered["Jogadores_Usam"].idxmax(), "Agente"
                        ],
                        f"{df_filtered['Jogadores_Usam'].max()} players"
                    )

                st.divider()

                # ── Gráfico de bolhas: WR x Partidas ──
                scatter_data = []
                for _, row in df_filtered.iterrows():
                    item = {
                        "name": row["Agente"],
                        "value": [row["WinRate_Medio"], row["Total_Partidas"], row["KD_Medio"]],
                        "symbolSize": max(row["KD_Medio"] * 25, 20),
                        "itemStyle": {"color": "#f39c12"} 
                    }
                    if row.get("Icone"):
                        item["symbol"] = f"image://{row['Icone']}"
                    scatter_data.append(item)

                scatter_options = {
                    "title": {
                        "text": f"{role_name}: Rounds vs Win Rate",
                        "textStyle": {"color": "#fff"}
                    },
                    "tooltip": {
                        "formatter": "{b}<br/>Win Rate: {c[0]}%<br/>Rounds: {c[1]}<br/>KD: {c[2]}"
                    },
                    "xAxis": {
                        "name": "Win Rate (%)",
                        "type": "value",
                        "nameTextStyle": {"color": "#fff"},
                        "axisLabel": {"color": "#aaa"},
                        "splitLine": {"lineStyle": {"color": "#444", "type": "dashed"} }
                    },
                    "yAxis": {
                        "name": "Partidas (Rounds)",
                        "type": "value",
                        "nameTextStyle": {"color": "#fff"},
                        "axisLabel": {"color": "#aaa"},
                        "splitLine": {"lineStyle": {"color": "#444", "type": "dashed"} }
                    },
                    "series": [{
                        "type": "scatter",
                        "data": scatter_data,
                        "label": {
                            "show": True,
                            "position": "bottom",
                            "formatter": "{b}",
                            "color": "#fff"
                        },
                        "markLine": {
                            "data": [{"xAxis": 50}],
                            "lineStyle": {"color": "#aaa", "type": "dashed"}
                        }
                    }]
                }
                st_echarts(options=scatter_options, height="500px")

                # ── Ranking visual ──
                st.subheader(f"🏅 Ranking - {role_name}")

                for idx, (_, op) in enumerate(df_filtered.iterrows()):
                    with st.container():
                        cols = st.columns([0.5, 2, 1.5, 1.5, 1.5, 1])

                        with cols[0]:
                            medals = {0: "🥇", 1: "🥈", 2: "🥉"}
                            st.markdown(
                                f"### {medals.get(idx, f'#{idx+1}')}"
                            )

                        with cols[1]:
                            if op.get("Icone"):
                                st.image(
                                    op["Icone"],
                                    width=32
                                )
                            st.markdown(f"**{op['Agente']}**")

                        with cols[2]:
                            wr = op['WinRate_Medio']
                            wr_color = (
                                "🟢" if wr >= 55
                                else ("🟡" if wr >= 45 else "🔴")
                            )
                            st.metric(
                                "Win Rate",
                                f"{wr_color} {wr}%"
                            )

                        with cols[3]:
                            kd = op['KD_Medio']
                            kd_color = (
                                "🟢" if kd >= 1.2
                                else ("🟡" if kd >= 0.9 else "🔴")
                            )
                            st.metric(
                                "KD",
                                f"{kd_color} {kd}"
                            )

                        with cols[4]:
                            st.metric(
                                "Partidas",
                                op['Total_Partidas']
                            )

                        with cols[5]:
                            st.metric(
                                "Score",
                                op['Score']
                            )

            with tab_atk:
                render_ops_tab(df_ops_all, "Ataque")
                
            with tab_def:
                render_ops_tab(df_ops_all, "Defesa")


            # ── Operadores mais perigosos ──
            st.divider()
            st.subheader("⚠️ Operadores Mais Perigosos (Threat)")

            df_threat = analyzer_adv.operadores_mais_perigosos(
                min_partidas_op
            )
            if not df_threat.empty:
                df_top10 = df_threat.head(10)
                jogadores_threat = df_top10["Jogador"].unique().tolist()
                agentes_threat = df_top10["Agente"].unique().tolist()
                
                series_threat = []
                for j in jogadores_threat:
                    data = []
                    for a in agentes_threat:
                        val = df_top10[(df_top10["Jogador"] == j) & (df_top10["Agente"] == a)]["Threat"]
                        data.append(val.iloc[0] if not val.empty else 0)
                    series_threat.append({
                        "name": j,
                        "type": "bar",
                        "data": data
                    })

                threat_options = {
                    "title": {
                        "text": "Nível de Ameaça por Operador (KD × WinRate)",
                        "textStyle": {"color": "#fff"}
                    },
                    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                    "legend": {"data": jogadores_threat, "textStyle": {"color": "#fff"}, "top": 30},
                    "xAxis": {"type": "category", "data": agentes_threat, "axisLabel": {"color": "#aaa"}},
                    "yAxis": {"type": "value", "splitLine": {"lineStyle": {"color": "#444", "type": "dashed"}}},
                    "series": series_threat
                }
                st_echarts(options=threat_options, height="450px")

            # ── Detalhe por jogador ──
            st.divider()
            st.subheader("🔎 Operadores por Jogador")

            jogadores_list = (
                analyzer_adv.df_agentes["Jogador"]
                .unique()
                .tolist()
            )
            jogador_sel = st.selectbox(
                "Selecione um jogador:",
                jogadores_list
            )

            if jogador_sel:
                df_jogador_ops = analyzer_adv.operadores_por_jogador(
                    jogador_sel, top_n=8
                )
                if not df_jogador_ops.empty:
                    df_jogador_ops = df_jogador_ops.sort_values("Partidas", ascending=False)
                    agentes_jog = df_jogador_ops["Agente"].tolist()
                    partidas_jog = df_jogador_ops["Partidas"].tolist()
                    
                    jog_options = {
                        "title": {
                            "text": f"Operadores de {jogador_sel}",
                            "textStyle": {"color": "#fff"}
                        },
                        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                        "xAxis": {"type": "category", "data": agentes_jog, "axisLabel": {"color": "#aaa"}},
                        "yAxis": {"type": "value", "splitLine": {"lineStyle": {"color": "#444", "type": "dashed"}}},
                        "series": [{
                            "name": "Partidas",
                            "type": "bar",
                            "data": partidas_jog,
                            "itemStyle": {"color": "#2ecc71"}
                        }]
                    }
                    st_echarts(options=jog_options, height="400px")
        else:
            st.warning(
                "Sem dados de operadores suficientes."
            )
    else:
        st.info("👈 Busque os dados do adversário primeiro.")


# ── TAB 3: COMPARATIVO ──
with tab3:
    col_hdr, col_btn = st.columns([3, 1])
    with col_hdr:
        st.header("📊 Comparativo de Times")
    with col_btn:
        if st.button("🔍 Carregar Ambos (Mapas)", key="btn_comp"):
            jogadores_adv = get_jogadores_from_state("adv")
            jogadores_ali = get_jogadores_from_state("ali")
            with st.spinner("Buscando mapas (ambos)..."):
                if jogadores_adv:
                    dados1 = buscar_dados_time({"nome": "adversario", "jogadores": jogadores_adv}, fetch_type="maps", progress_bar=st.progress(0))
                    atualizar_estado_sessao("adversario", dados1, "maps")
                if jogadores_ali:
                    dados2 = buscar_dados_time({"nome": "aliado", "jogadores": jogadores_ali}, fetch_type="maps", progress_bar=st.progress(0))
                    atualizar_estado_sessao("aliado", dados2, "maps")
            st.success("✅ Mapas carregados!")

    has_both = (
        "dados_adversario" in st.session_state and "mapas" in st.session_state["dados_adversario"] and len(st.session_state["dados_adversario"]["mapas"]) > 0
        and "dados_aliado" in st.session_state and "mapas" in st.session_state["dados_aliado"] and len(st.session_state["dados_aliado"]["mapas"]) > 0
    )

    if has_both:
        analyzer_ali = R6Analyzer(
            st.session_state["dados_aliado"]
        )
        analyzer_adv = R6Analyzer(
            st.session_state["dados_adversario"]
        )

        df_comp = analyzer_adv.comparar_mapas(
            st.session_state["dados_aliado"],
            st.session_state["dados_adversario"],
            min_partidas_mapa
        )

        if not df_comp.empty:
            st.subheader("🗺️ Comparativo de Mapas")

            mapas_comp = df_comp['Mapa'].tolist()
            wr_ali = df_comp['WinRate_Ponderado_Aliado'].tolist()
            wr_adv = df_comp['WinRate_Ponderado_Adversario'].tolist()
            
            comp_options = {
                "title": {
                    "text": "Win Rate Comparativo por Mapa",
                    "textStyle": {"color": "#fff"}
                },
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "legend": {"data": ["Meu Time", "Adversário"], "textStyle": {"color": "#fff"}, "top": 30},
                "xAxis": {"type": "category", "data": mapas_comp, "axisLabel": {"color": "#aaa", "rotate": 45}},
                "yAxis": {"type": "value", "max": 100, "splitLine": {"lineStyle": {"color": "#444", "type": "dashed"}}},
                "series": [
                    {
                        "name": "Meu Time",
                        "type": "bar",
                        "data": wr_ali,
                        "itemStyle": {"color": "#2ecc71"}
                    },
                    {
                        "name": "Adversário",
                        "type": "bar",
                        "data": wr_adv,
                        "itemStyle": {"color": "#e74c3c"}
                    }
                ]
            }
            st_echarts(options=comp_options, height="450px")

            # Tabela de recomendações
            st.subheader("🎯 Recomendações de Pick/Ban")

            for _, row in df_comp.iterrows():
                cols = st.columns([2, 1.5, 1.5, 1, 1.5])
                with cols[0]:
                    st.write(f"**{row['Mapa']}**")
                with cols[1]:
                    wr_ali = row.get(
                        'WinRate_Ponderado_Aliado', 0
                    )
                    st.write(f"🟢 Nós: {wr_ali}%")
                with cols[2]:
                    wr_adv = row.get(
                        'WinRate_Ponderado_Adversario', 0
                    )
                    st.write(f"🔴 Eles: {wr_adv}%")
                with cols[3]:
                    vantagem = row.get('Vantagem', 0)
                    cor = (
                        "🟢" if vantagem > 0
                        else "🔴"
                    )
                    st.write(
                        f"{cor} {'+' if vantagem > 0 else ''}"
                        f"{vantagem}"
                    )
                with cols[4]:
                    st.write(
                        row.get('Recomendacao', '⚠️')
                    )
        else:
            st.warning("Dados insuficientes para comparação.")
    else:
        st.info(
            "👈 Busque os dados de ambos os times "
            "para ver o comparativo."
        )


# ── TAB 4: FASE DOS JOGADORES ──
with tab4:
    col_hdr, col_btn1, col_btn2 = st.columns([2, 1, 1])
    with col_hdr:
        st.header("🔥 Momento Atual dos Jogadores")
    with col_btn1:
        if st.button("🔍 Carregar Fase (Adv)", key="btn_fase_adv"):
            jogadores_adv = get_jogadores_from_state("adv")
            if jogadores_adv:
                with st.spinner("Buscando fase do adversário..."):
                    dados = buscar_dados_time({"nome": "adversario", "jogadores": jogadores_adv}, fetch_type="fase", progress_bar=st.progress(0))
                    atualizar_estado_sessao("adversario", dados, "fase")
                st.success("✅ Fase do adversário carregada!")
    with col_btn2:
        if st.button("🔍 Carregar Fase (Nós)", key="btn_fase_ali"):
            jogadores_ali = get_jogadores_from_state("ali")
            if jogadores_ali:
                with st.spinner("Buscando fase do meu time..."):
                    dados = buscar_dados_time({"nome": "aliado", "jogadores": jogadores_ali}, fetch_type="fase", progress_bar=st.progress(0))
                    atualizar_estado_sessao("aliado", dados, "fase")
                st.success("✅ Fase do aliado carregada!")

    col_fase1, col_fase2 = st.columns(2)

    # Fase do adversário
    with col_fase1:
        st.subheader("🔴 Adversário")
        if "dados_adversario" in st.session_state and "fase" in st.session_state["dados_adversario"] and len(st.session_state["dados_adversario"]["fase"]) > 0:
            analyzer_adv = R6Analyzer(
                st.session_state["dados_adversario"]
            )
            fase_adv = analyzer_adv.analise_fase()

            for jogador in fase_adv:
                with st.container():
                    c1, c2, c3 = st.columns([2, 1.5, 1.5])
                    with c1:
                        st.markdown(
                            f"**{jogador['Jogador']}**"
                        )
                        st.caption(jogador['Historico'])
                    with c2:
                        st.write(jogador['Momento'])
                    with c3:
                        st.write(jogador['Streak'])
                    st.divider()
        else:
            st.info("Sem dados.")

    # Fase do meu time
    with col_fase2:
        st.subheader("🟢 Meu Time")
        if "dados_aliado" in st.session_state and "fase" in st.session_state["dados_aliado"] and len(st.session_state["dados_aliado"]["fase"]) > 0:
            analyzer_ali = R6Analyzer(
                st.session_state["dados_aliado"]
            )
            fase_ali = analyzer_ali.analise_fase()

            for jogador in fase_ali:
                with st.container():
                    c1, c2, c3 = st.columns([2, 1.5, 1.5])
                    with c1:
                        st.markdown(
                            f"**{jogador['Jogador']}**"
                        )
                        st.caption(jogador['Historico'])
                    with c2:
                        st.write(jogador['Momento'])
                    with c3:
                        st.write(jogador['Streak'])
                    st.divider()
        else:
            st.info("Sem dados.")


# ══════════════════════════════════════════════
#  FOOTER
# ══════════════════════════════════════════════

st.divider()
st.caption(
    "🎯 R6 Team Analyzer | "
    "Dados via R6Tracker | "
    f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
)