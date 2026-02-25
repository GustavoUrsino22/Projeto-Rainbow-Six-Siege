# analyzer.py

import pandas as pd
from typing import Dict, List


class R6Analyzer:
    """Motor de análise de dados do R6 Siege."""

    def __init__(self, dados_brutos: Dict):
        self.dados = dados_brutos
        self.df_mapas = pd.DataFrame(dados_brutos.get("mapas", []))
        self.df_agentes = pd.DataFrame(dados_brutos.get("agentes", []))
        self.fase = dados_brutos.get("fase", [])
        self.erros = dados_brutos.get("erros", [])

    # ──────────────────────────────────────────────
    #  FERRAMENTA 1 - ANÁLISE DE MAPAS
    # ──────────────────────────────────────────────

    def melhores_mapas_time(self, min_partidas: int = 3) -> pd.DataFrame:
        """
        Agrega os dados de mapa de todo o time.
        Calcula um score ponderado por partidas jogadas.
        """
        if self.df_mapas.empty:
            return pd.DataFrame()

        df = self.df_mapas.copy()

        # Filtra mapas com poucas partidas (ruído)
        df = df[df["Partidas"] >= min_partidas]

        # Agrega por mapa: média ponderada de win%
        agg = (
            df.groupby("Mapa")
            .apply(self._media_ponderada_mapa)
            .reset_index()
        )
        agg.columns = [
            "Mapa",
            "WinRate_Ponderado",
            "Total_Partidas",
            "Jogadores_com_Dados",
            "Confianca"
        ]

        # Score final = WinRate * Confiança
        agg["Score"] = round(
            agg["WinRate_Ponderado"] * agg["Confianca"], 1
        )
        agg = agg.sort_values("Score", ascending=False)

        return agg

    def _media_ponderada_mapa(self, grupo):
        total_partidas = grupo["Partidas"].sum()
        if total_partidas == 0:
            return pd.Series([0, 0, 0, 0])

        win_ponderado = (
            (grupo["WinPct"] * grupo["Partidas"]).sum()
            / total_partidas
        )
        jogadores = grupo["Jogador"].nunique()

        # Confiança: quantos jogadores jogaram esse mapa
        # Escala 0-1 baseado em 5 jogadores
        confianca = min(jogadores / 5, 1.0)

        return pd.Series([
            round(win_ponderado, 1),
            total_partidas,
            jogadores,
            round(confianca, 2)
        ])

    def mapa_por_jogador(self, mapa: str) -> pd.DataFrame:
        """Detalhe de um mapa específico por jogador."""
        if self.df_mapas.empty:
            return pd.DataFrame()

        df = self.df_mapas[
            self.df_mapas["Mapa"].str.upper() == mapa.upper()
        ]
        return df.sort_values("WinPct", ascending=False)

    def comparar_mapas(
        self,
        dados_aliado: Dict,
        dados_adversario: Dict,
        min_partidas: int = 3
    ) -> pd.DataFrame:
        """
        Compara win rates de mapas entre dois times.
        Retorna vantagem/desvantagem por mapa.
        """
        analyzer_aliado = R6Analyzer(dados_aliado)
        analyzer_adv = R6Analyzer(dados_adversario)

        mapas_aliado = analyzer_aliado.melhores_mapas_time(min_partidas)
        mapas_adv = analyzer_adv.melhores_mapas_time(min_partidas)

        if mapas_aliado.empty or mapas_adv.empty:
            return pd.DataFrame()

        merged = mapas_aliado.merge(
            mapas_adv,
            on="Mapa",
            suffixes=("_Aliado", "_Adversario"),
            how="outer"
        ).fillna(0)

        merged["Vantagem"] = round(
            merged["WinRate_Ponderado_Aliado"]
            - merged["WinRate_Ponderado_Adversario"],
            1
        )
        merged["Recomendacao"] = merged["Vantagem"].apply(
            lambda x: "✅ PICK" if x > 5
            else ("⚠️ NEUTRO" if x > -5 else "❌ BAN")
        )

        return merged.sort_values("Vantagem", ascending=False)

    # ──────────────────────────────────────────────
    #  FERRAMENTA 2 - ANÁLISE DE OPERADORES
    # ──────────────────────────────────────────────

    def melhores_operadores(
        self,
        min_partidas: int = 5,
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Retorna os melhores operadores do time
        ordenados por um score composto.
        """
        if self.df_agentes.empty:
            return pd.DataFrame()

        df = self.df_agentes.copy()
        df = df[df["Partidas"] >= min_partidas]

        agg = (
            df.groupby("Agente")
            .apply(self._score_operador)
            .reset_index()
        )
        agg.columns = [
            "Agente",
            "WinRate_Medio",
            "KD_Medio",
            "Total_Partidas",
            "Jogadores_Usam",
            "Score"
        ]

        # Busca o ícone do operador
        icones = (
            df.groupby("Agente")["Icone"]
            .first()
            .reset_index()
        )
        agg = agg.merge(icones, on="Agente", how="left")

        agg = agg.sort_values("Score", ascending=False)
        return agg.head(top_n)

    def _score_operador(self, grupo):
        total_partidas = grupo["Partidas"].sum()
        if total_partidas == 0:
            return pd.Series([0, 0, 0, 0, 0])

        win_medio = (
            (grupo["WinPct"] * grupo["Partidas"]).sum()
            / total_partidas
        )
        kd_medio = (
            (grupo["KD"] * grupo["Partidas"]).sum()
            / total_partidas
        )
        jogadores = grupo["Jogador"].nunique()

        # Score composto:
        # 50% win rate + 30% KD normalizado + 20% popularidade
        score = (
            (win_medio * 0.5)
            + (min(kd_medio, 2.0) * 50 * 0.3)
            + (min(jogadores / 5, 1.0) * 100 * 0.2)
        )

        return pd.Series([
            round(win_medio, 1),
            round(kd_medio, 2),
            total_partidas,
            jogadores,
            round(score, 1)
        ])

    def operadores_por_jogador(
        self,
        jogador: str,
        top_n: int = 5
    ) -> pd.DataFrame:
        """Top operadores de um jogador específico."""
        if self.df_agentes.empty:
            return pd.DataFrame()

        df = self.df_agentes[self.df_agentes["Jogador"] == jogador]
        return (
            df.sort_values("Partidas", ascending=False)
            .head(top_n)
        )

    def operadores_mais_perigosos(
        self,
        min_partidas: int = 5
    ) -> pd.DataFrame:
        """
        Para time adversário: identifica os operadores
        que são mais ameaçadores (alto KD + alto WinRate).
        """
        if self.df_agentes.empty:
            return pd.DataFrame()

        df = self.df_agentes.copy()
        df = df[df["Partidas"] >= min_partidas]

        # Threat score: KD * WinRate / 100
        df["Threat"] = round(df["KD"] * df["WinPct"] / 100, 2)

        return (
            df.sort_values("Threat", ascending=False)
            .head(15)
        )

    # ──────────────────────────────────────────────
    #  ANÁLISE DE FASE (MOMENTO)
    # ──────────────────────────────────────────────

    def analise_fase(self) -> List[Dict]:
        """Analisa o momento atual de cada jogador."""
        resultados = []
        for jogador in self.fase:
            hist = jogador.get("History", ["?"])
            wins = hist.count("W")
            losses = hist.count("L")
            total = wins + losses

            if total > 0:
                win_rate = round((wins / total) * 100, 1)
            else:
                win_rate = 0

            # Sequência atual
            streak = self._calcular_streak(hist)

            # Momento: Hot / Cold / Normal
            if len(hist) >= 3:
                ultimas_3 = hist[:3]
                if ultimas_3.count("W") == 3:
                    momento = "🔥 ON FIRE"
                elif ultimas_3.count("L") == 3:
                    momento = "🧊 GELADO"
                elif ultimas_3.count("W") >= 2:
                    momento = "📈 AQUECIDO"
                elif ultimas_3.count("L") >= 2:
                    momento = "📉 ESFRIANDO"
                else:
                    momento = "😐 NEUTRO"
            else:
                momento = "❓ SEM DADOS"

            resultados.append({
                "Jogador": jogador["Jogador"],
                "Plataforma": jogador["Plataforma"],
                "Historico": " ".join(hist),
                "WinRate_Recente": win_rate,
                "Streak": streak,
                "Momento": momento,
                "Vitorias": wins,
                "Derrotas": losses
            })

        return resultados

    def _calcular_streak(self, hist: List[str]) -> str:
        if not hist or hist[0] == "?":
            return "N/A"

        current = hist[0]
        count = 0
        for r in hist:
            if r == current:
                count += 1
            else:
                break

        if current == "W":
            return f"🟢 {count}W"
        elif current == "L":
            return f"🔴 {count}L"
        else:
            return f"⚪ {count}D"