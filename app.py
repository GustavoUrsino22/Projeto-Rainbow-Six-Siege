import streamlit as st
import pandas as pd
import plotly.express as px
import time
from scraper import get_r6_team_stats
from ocr_processor import process_lobby_screenshot

st.set_page_config(page_title="R6 Tactical Suite", layout="wide", page_icon="⚔️")

ATACANTES = [
    "sledge", "thatcher", "ash", "thermite", "twitch", "montagne", "glaz", "fuze", 
    "blitz", "iq", "buck", "blackbeard", "capitao", "hibana", "jackal", "ying", 
    "zofia", "dokkaebi", "lion", "finka", "maverick", "nomad", "gridlock", "nokk", 
    "amaru", "kali", "iana", "ace", "zero", "flores", "osa", "sens", "grim", 
    "brava", "ram", "deimos", "striker"
]

st.markdown("""
    <style>
    .role-header-atk { color: #ff4b4b; font-size: 1.1rem; font-weight: bold; border-bottom: 2px solid #ff4b4b; padding-bottom: 5px; margin-top: 15px; margin-bottom: 10px; }
    .role-header-def { color: #0088ff; font-size: 1.1rem; font-weight: bold; border-bottom: 2px solid #0088ff; padding-bottom: 5px; margin-top: 15px; margin-bottom: 10px; }
    .player-card { background-color: #262730; border-radius: 10px; padding: 15px; border-top: 5px solid #fff; text-align: center; margin-bottom: 10px;}
    .ai-insight { background-color: #161b22; border-left: 4px solid #a371f7; padding: 15px; border-radius: 8px; margin-top: 20px; margin-bottom: 20px; font-family: monospace;}
    </style>
""", unsafe_allow_html=True)

def render_op_card(op, role):
    color = "#ff4b4b" if role == "atk" else "#0088ff"
    img_html = f'<img src="{op.get("Icone", "")}" width="38" height="38" style="border-radius:5px; margin-right:12px; object-fit: cover;">' if op.get("Icone") else ''
    return f"""
    <div style="background-color: #1e212b; border-left: 4px solid {color}; border-radius: 6px; padding: 10px; margin-bottom: 8px; display: flex; align-items: center;">
        {img_html}
        <div style="flex-grow: 1;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                <span style="font-weight: bold; font-size: 0.95rem; color:#fff;">{op['Agente']}</span>
                <span style="font-size: 0.8rem; color: #aaa;">{op['Partidas']} j</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #ccc; margin-bottom: 5px;">
                <span>WR: <b>{op['WinPct']}%</b></span>
                <span>KD: <b>{op['KD']}</b></span>
            </div>
            <div style="width: 100%; background-color: #333; height: 6px; border-radius: 3px;">
                <div style="width: {min(op['WinPct'], 100)}%; background-color: {color}; height: 100%; border-radius: 3px;"></div>
            </div>
        </div>
    </div>
    """

if "final_players" not in st.session_state: st.session_state.final_players = []
if "map_data" not in st.session_state: st.session_state.map_data = None
if "agent_data" not in st.session_state: st.session_state.agent_data = None
if "fase_data" not in st.session_state: st.session_state.fase_data = None
for i in range(5):
    if f"nick_{i}" not in st.session_state: st.session_state[f"nick_{i}"] = ""
    if f"plat_{i}" not in st.session_state: st.session_state[f"plat_{i}"] = "ubi"

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Rainbow_Six_Siege_logo.svg/1200px-Rainbow_Six_Siege_logo.svg.png", width=150)
    st.header("🛠️ Menu Tático")
    pagina = st.radio("Módulos:", ["📸 Scanner & Configuração", "📈 Fase Atual (W/L)", "🗺️ Estratégia de Mapas", "🔫 Inteligência de Agentes"])
    st.divider()
    temporada = st.selectbox("Temporada:", ["Y10S4 (Atual)", "Geral"], index=0)
    playlist = st.selectbox("Playlist:", ["Ranked", "Standard", "Casual"], index=0)
    season_id = "40" if "Y10S4" in temporada else "all"

# ==========================================
# 1. SCANNER & CONFIGURAÇÃO
# ==========================================
if pagina == "📸 Scanner & Configuração":
    st.title("📸 Scanner de Lobby")
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("1. IA de Visão")
        img_file = st.file_uploader("Suba a foto", type=['png', 'jpg', 'jpeg'])
        if img_file:
            st.image(img_file, use_container_width=True)
            if st.button("🔍 Extrair Nomes", type="primary"):
                with open("temp.png", "wb") as f: f.write(img_file.getbuffer())
                with st.spinner("Analisando..."):
                    res = process_lobby_screenshot("temp.png")
                    for i, p in enumerate(res["players"]):
                        st.session_state[f"nick_{i}"] = p['nick']
                        st.session_state[f"plat_{i}"] = p['platform']
                    st.success("Concluído!")
                    time.sleep(1)
                    st.rerun()
    
    with col2:
        st.subheader("2. Esquadrão Inimigo")
        temp_players = []
        for i in range(5):
            c_n, c_p = st.columns([2, 1])
            n = c_n.text_input(f"Nick {i+1}", key=f"nick_{i}")
            p = c_p.selectbox(f"Plat. {i+1}", ["psn", "xbl", "ubi"], key=f"plat_{i}")
            if n.strip(): temp_players.append({"nick": n.strip(), "platform": p})
        
        if st.button("💾 CONFIRMAR SQUAD", use_container_width=True):
            st.session_state.final_players = temp_players
            st.session_state.map_data, st.session_state.agent_data, st.session_state.fase_data = None, None, None
            st.success("Squad salvo!")
            
        if temp_players:
            plats = [p['platform'] for p in temp_players]
            if "ubi" in plats and ("psn" in plats or "xbl" in plats):
                st.markdown('<div class="ai-insight">🤖 <b>Dica da IA:</b> Detectei Crossplay entre PC e Consoles. Espere variação no ritmo de jogo e possível falha de comunicação interna no time adversário (nem todos usam o mesmo chat de voz nativo).</div>', unsafe_allow_html=True)
            elif "ubi" not in plats:
                st.markdown('<div class="ai-insight">🤖 <b>Dica da IA:</b> Squad 100% Console. Foquem em posicionamento de mira cruzada; a movimentação de controle pode ser mais previsível sob pressão.</div>', unsafe_allow_html=True)

# ==========================================
# 2. FASE ATUAL (W/L)
# ==========================================
elif pagina == "📈 Fase Atual (W/L)":
    st.title("📈 Fase Atual (Últimas Partidas)")
    
    if not st.session_state.final_players:
        st.warning("⚠️ Salve o Squad primeiro.")
    else:
        if st.button("🚀 BUSCAR HISTÓRICO", type="primary"):
            with st.status("Analisando partidas..."):
                dados = get_r6_team_stats(st.session_state.final_players, season_id, playlist.lower(), fetch_type="fase")
                if "erro_critico" not in dados: st.session_state.fase_data = dados["fase"]

        if st.session_state.fase_data:
            total_w, total_l = 0, 0
            tiltados = []
            
            for p in st.session_state.fase_data:
                ws = p['History'].count('W')
                ls = p['History'].count('L')
                total_w += ws
                total_l += ls
                if ls > ws and ls >= 3:
                    tiltados.append(p['Jogador'])

            if total_w > total_l * 1.5:
                st.markdown('<div class="ai-insight">🤖 <b>Dica da IA:</b> O adversário está em <b>WIN STREAK</b> (Alta Confiança). Eles provavelmente jogarão de forma agressiva nos primeiros rounds. Segurem o avanço inicial e punam a afobação deles.</div>', unsafe_allow_html=True)
            elif tiltados:
                nomes_tilt = ", ".join(tiltados)
                st.markdown(f'<div class="ai-insight">🤖 <b>Dica da IA:</b> Detectei jogadores numa péssima fase ({nomes_tilt}). Eles estão <b>TILTADOS</b>. Joguem com agressividade em cima deles para quebrar o psicológico da equipe logo no round 1.</div>', unsafe_allow_html=True)

            st.divider()
            for p_data in st.session_state.fase_data:
                st.markdown(f"<h4 style='margin-bottom: 5px;'>{p_data['Jogador']}</h4>", unsafe_allow_html=True)
                history_html = ""
                for result in p_data['History']:
                    if result == "W": history_html += '<span style="color: #00ffcc; font-weight: bold; font-size: 1.5rem; margin-right: 12px;">W</span>'
                    elif result == "L": history_html += '<span style="color: #ff4b4b; font-weight: bold; font-size: 1.5rem; margin-right: 12px;">L</span>'
                    elif result == "D": history_html += '<span style="color: #aaaaaa; font-weight: bold; font-size: 1.5rem; margin-right: 12px;">D</span>'
                    else: history_html += '<span style="color: #555555; font-weight: bold; font-size: 1.5rem; margin-right: 12px;">?</span>'
                st.markdown(f'<div style="background-color: #1e212b; padding: 10px 20px; border-radius: 8px; margin-bottom: 20px; border-left: 3px solid #555;">{history_html}</div>', unsafe_allow_html=True)

# ==========================================
# 3. ESTRATÉGIA DE MAPAS
# ==========================================
elif pagina == "🗺️ Estratégia de Mapas":
    st.title("🗺️ Inteligência de Mapas")
    
    if not st.session_state.final_players:
        st.warning("⚠️ Salve o Squad primeiro.")
    else:
        if st.button("🚀 BUSCAR MAPAS", type="primary"):
            with st.status("Extraindo dados..."):
                dados = get_r6_team_stats(st.session_state.final_players, season_id, playlist.lower(), fetch_type="maps")
                if "erro_critico" not in dados: st.session_state.map_data = dados["mapas"]

        if st.session_state.map_data:
            df_m = pd.DataFrame(st.session_state.map_data)
            team_maps = df_m.groupby("Mapa").agg({"WinPct": "mean", "Partidas": "sum"}).sort_values("WinPct", ascending=False)
            
            if not team_maps.empty:
                melhor_mapa = team_maps.iloc[0].name
                pior_mapa = team_maps.iloc[-1].name
                st.markdown(f"""
                <div class="ai-insight">
                    🤖 <b>Veredito da IA Tática:</b><br>
                    ❌ <b>Obrigatório Banir:</b> {melhor_mapa} (Eles amam e dominam esse mapa).<br>
                    ✅ <b>Forçar o Jogo:</b> Deixem {pior_mapa} aberto! É a maior fraqueza tática deles.
                </div>
                """, unsafe_allow_html=True)

            st.divider()
            m1, m2, m3 = st.columns(3)
            for i, (mapa, row) in enumerate(team_maps.head(3).iterrows()):
                [m1, m2, m3][i].metric(f"PRIORIDADE DE BAN {i+1}", mapa, f"{row['WinPct']:.1f}% WR")

            fig = px.bar(team_maps.reset_index(), x="Mapa", y="WinPct", color="WinPct", title="Perigo Coletivo por Mapa (%)", color_continuous_scale="Reds", text_auto='.1f')
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 4. INTELIGÊNCIA DE AGENTES
# ==========================================
elif pagina == "🔫 Inteligência de Agentes":
    st.title("🔫 Perfil Tático Visual")
    
    if not st.session_state.final_players:
        st.warning("⚠️ Salve o Squad primeiro.")
    else:
        if st.button("🚀 BUSCAR AGENTES", type="primary"):
            with st.status("Baixando perfis..."):
                dados = get_r6_team_stats(st.session_state.final_players, season_id, playlist.lower(), fetch_type="agentes")
                if "erro_critico" not in dados: st.session_state.agent_data = dados["agentes"]

        if st.session_state.agent_data:
            df_ops = pd.DataFrame(st.session_state.agent_data)
            
            if not df_ops.empty:
                # NOVA REGRA: Acha o operador mais letal (Maior K/D com MAIS de 10 partidas)
                ops_confiaveis = df_ops[df_ops['Partidas'] > 10]
                
                if not ops_confiaveis.empty:
                    pior_inimigo = ops_confiaveis.loc[ops_confiaveis['KD'].idxmax()]
                    st.markdown(f"""
                    <div class="ai-insight">
                        🤖 <b>Relatório da IA:</b><br>
                        ⚠️ Cuidado extremo com <b>{pior_inimigo['Jogador']}</b> jogando de <b>{pior_inimigo['Agente']}</b>. 
                        Ele possui um K/D altíssimo ({pior_inimigo['KD']}) com um volume sólido de jogo ({pior_inimigo['Partidas']} partidas). 
                        Usem utilitários para isolá-lo e evitem trocas 1v1 diretas contra ele!
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Se ninguém tiver mais de 10 partidas com um boneco, a IA dá um alerta de "Flexibilidade"
                    st.markdown("""
                    <div class="ai-insight">
                        🤖 <b>Relatório da IA:</b><br>
                        🔍 O time adversário não possui nenhum jogador com grande volume (>10 partidas) focado em um único operador. Eles parecem jogar de forma "flexível" dependendo do mapa. Foquem no jogo coletivo em vez de caçar um alvo específico!
                    </div>
                    """, unsafe_allow_html=True)
            
            st.divider()
            p_cols = st.columns(len(st.session_state.final_players))
            
            for i, p_cfg in enumerate(st.session_state.final_players):
                nick = p_cfg['nick']
                with p_cols[i]:
                    st.markdown(f'<div class="player-card"><h4 style="margin:0;">{nick}</h4></div>', unsafe_allow_html=True)
                    
                    player_ops = df_ops[df_ops["Jogador"] == nick].sort_values("Partidas", ascending=False)
                    player_ops['is_atk'] = player_ops['Agente'].str.lower().str.replace('ã', 'a').isin(ATACANTES)
                    
                    ops_ataque = player_ops[player_ops['is_atk']].head(5)
                    ops_defesa = player_ops[~player_ops['is_atk']].head(5)
                    
                    st.markdown('<div class="role-header-atk">⚔️ ATAQUE</div>', unsafe_allow_html=True)
                    if not ops_ataque.empty:
                        for _, op in ops_ataque.iterrows(): st.markdown(render_op_card(op, "atk"), unsafe_allow_html=True)
                    else: st.write("Sem dados.")

                    st.markdown('<div class="role-header-def">🗼 DEFESA</div>', unsafe_allow_html=True)
                    if not ops_defesa.empty:
                        for _, op in ops_defesa.iterrows(): st.markdown(render_op_card(op, "def"), unsafe_allow_html=True)
                    else: st.write("Sem dados.")