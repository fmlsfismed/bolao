"""Dashboard & Ranking page — Bolão Copa FIFA 2k26 (Grupos + Empates + Ranking)."""

import pandas as pd
import streamlit as st
import database as db
import scoring

st.set_page_config(page_title="Dashboard & Ranking — Bolão 2k26", layout="wide")

db.init_db()

if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Faça login na página principal.")
    st.stop()

user = st.session_state.user

# --- LÓGICA DE FILTRO POR GRUPO DE USUÁRIOS ---
user_profile = db.get_user_by_id(user["id"])
user_group_id = user_profile.get("group_id") if user_profile else None

escopo_options = ["🌍 Visão Geral do Bolão"]
if user_group_id:
    group_name = db.get_group_name(user_group_id)
    escopo_options.append(f"👥 Meu Grupo: {group_name}")

st.title("📊 Dashboard e Classificação")
selected_escopo = st.selectbox("Visualizar dados e rankings de:", escopo_options)
selected_group_id = user_group_id if "👥" in selected_escopo else None

st.write("---")

# Criamos duas abas principais
tab_dash, tab_rank = st.tabs(["⭐ Destaques e Métricas", "🏆 Tabelas de Classificação"])

# 1. Puxamos o ranking GLOBAL do seu scoring (sem passar group_id para não quebrar)
df_ranking = scoring.ranking_dataframe()

# 2. SE o usuário selecionou o grupo privado, filtramos o DataFrame via Pandas aqui no app
if selected_group_id is not None and not df_ranking.empty:
    # IMPORTANTE: Mapeamos quem pertence a este grupo buscando no banco
    # Supondo que db traga uma lista de usuários ou participantes do grupo. 
    # Caso não tenha essa função pronta, filtramos buscando os perfis que possuem esse group_id.
     todos_usuarios = db.get_all_users() if hasattr(db, 'get_all_users') else []
    
    if todos_usuarios:
         usernames_do_grupo = [u["username"] for u in todos_usuarios if u.get("group_id") == selected_group_id]
    else:
        # Alternativa caso get_all_users não exista: usar uma query simulada ou fallback seguro
        usernames_do_grupo = [user["username"]] # Garante pelo menos o usuário logado
        
    # Filtragem inteligente usando Pandas
    # Verifica qual coluna identifica o usuário único no seu DataFrame ('Usuário' ou 'Participante')
    col_user = "Usuário" if "Usuário" in df_ranking.columns else "Participante"
    
    if todos_usuarios:
        df_ranking = df_ranking[df_ranking[col_user].isin(usernames_do_grupo)].copy()
    else:
        # Se não conseguirmos a lista do banco, filtramos dinamicamente pela regra geral do grupo (se houver a coluna no DF)
        if "group_id" in df_ranking.columns:
            df_ranking = df_ranking[df_ranking["group_id"] == selected_group_id].copy()
            
    # Recalcula a Posição sequencial para o grupo de amigos
    if not df_ranking.empty:
        df_ranking = df_ranking.sort_values(by=["Pontos Totais", "Placares Exatos"], ascending=[False, False])
        df_ranking["Posição"] = range(1, len(df_ranking) + 1)

# ==============================================================================
# --- ABA 1: DASHBOARD (MÉTRICAS + EMPATES DINÂMICOS) ---
# ==============================================================================
with tab_dash:
    # Chamamos a métrica global sem argumentos conflitantes
    metrics_global = scoring.dashboard_metrics()

    if df_ranking.empty or not metrics_global:
        st.info("Estatísticas e destaques indisponíveis para o escopo selecionado.")
    else:
        def formatar_nomes(lista_nomes: list[str]) -> str:
            if not lista_nomes:
                return "Ninguém ainda"
            if len(lista_nomes) == 1:
                return lista_nomes[0]
            if len(lista_nomes) == 2:
                return f"{lista_nomes[0]} e {lista_nomes[1]}"
            return ", ".join(lista_nomes)

        col_nome_exibicao = "Participante" if "Participante" in df_ranking.columns else "Usuário"

        if selected_group_id is not None:
            # Recalcula destaques de Líder e Rei do Exato LOCALMENTE usando o Pandas filtrado
            max_pts_grupo = df_ranking["Pontos Totais"].max()
            leaders = df_ranking[df_ranking["Pontos Totais"] == max_pts_grupo][col_nome_exibicao].tolist()
            
            max_exat_grupo = df_ranking["Placares Exatos"].max() if "Placares Exatos" in df_ranking.columns else 0
            exact_kings = df_ranking[df_ranking["Placares Exatos"] == max_exat_grupo][col_nome_exibicao].tolist() if max_exat_grupo > 0 else []
            
            # Filtra os demais destaques da lista global se eles estiverem no seu grupo
            usuarios_do_grupo_nomes = set(df_ranking[col_nome_exibicao])
            hat_tricks = [n for n in metrics_global.get("hat_tricks", []) if n in usuarios_do_grupo_nomes]
            zebra_kings = [n for n in metrics_global.get("zebra_kings", []) if n in usuarios_do_grupo_nomes]
            
            max_points = max_pts_grupo
            max_exact = max_exat_grupo
            max_hat_tricks = metrics_global.get("max_hat_tricks", 0) if hat_tricks else 0
            max_zebra_pts = metrics_global.get("max_zebra_pts", 0) if zebra_kings else 0
        else:
            leaders = metrics_global.get("leaders", [])
            exact_kings = metrics_global.get("exact_kings", [])
            hat_tricks = metrics_global.get("hat_tricks", [])
            zebra_kings = metrics_global.get("zebra_kings", [])
            
            max_points = metrics_global.get("max_points", 0)
            max_exact = metrics_global.get("max_exact", 0)
            max_hat_tricks = metrics_global.get("max_hat_tricks", 0)
            max_zebra_pts = metrics_global.get("max_zebra_pts", 0)

        label_lider = formatar_nomes(leaders)
        label_exato = formatar_nomes(exact_kings)
        label_hat_trick = formatar_nomes(hat_tricks)
        label_zebra = formatar_nomes(zebra_kings)

        best_phase = metrics_global.get("best_phase", {"phase": None, "user": "-", "points": -1})
        climb = metrics_global.get("biggest_climb", {"user": None, "delta": 0})

        # LINHA SUPERIOR
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("### 👑 Líder")
            st.metric(
                label=label_lider,
                value=f"{max_points} pts",
                delta=f"{metrics_global.get('max_exact_leader', 0)} exatos" if selected_group_id is None and metrics_global.get('max_exact_leader', 0) > 0 else None,
            )
        with c2:
            st.markdown("### 🏅 Melhor da Fase")
            if best_phase.get("phase"):
                st.metric(
                    label=best_phase["user"] or "-",
                    value=f"{best_phase['points']} pts" if best_phase["points"] >= 0 else "-",
                    delta=best_phase["phase"],
                )
            else:
                st.info("Nenhuma fase finalizada para este escopo.")
        with c3:
            st.markdown("### 🎯 Rei do Placar Exato")
            st.metric(
                label=label_exato,
                value=f"{max_exact} exatos" if max_exact > 0 else "0 exatos",
            )

        st.divider()

        # LINHA INFERIOR
        c4, c5, c6 = st.columns(3)
        with c4:
            st.markdown("### ⚡ Hat-Trick")
            st.caption("Mais sequências de 3+ placares exatos consecutivos")
            if max_hat_tricks > 0:
                st.metric(
                    label=label_hat_trick,
                    value=f"{max_hat_tricks} hat-tricks",
                    delta=f"Maior sequência: {metrics_global.get('max_streak', 0)}",
                )
            else:
                st.info("Nenhum hat-trick registrado neste escopo.")
        with c5:
            st.markdown("### 📈 Maior Escalada")
            st.caption("Maior subida no ranking (snapshots)")
            if climb.get("user") and climb.get("delta", 0) > 0:
                st.metric(label=climb["user"], value=f"+{climb['delta']} posições")
            else:
                st.info("Aguardando novas rodadas para computar variações.")
        with c6:
            st.markdown("### 🦓 Rei das Zebras")
            st.caption("Mais pontos em acertos de resultados surpresa")
            if max_zebra_pts > 0:
                st.metric(label=label_zebra, value=f"{max_zebra_pts} pts")
            else:
                st.info("Nenhuma zebra registrada neste escopo ainda.")

# ==============================================================================
# --- ABA 2: RANKINGS E CLASSIFICAÇÃO COMPLETA ---
# ==============================================================================
with tab_rank:
    st.markdown(
        """
        **Critérios de desempate:**
        1. Mais placares exatos · 2. Mais resultados corretos · 3. Acerto do campeão · 4. Sorteio determinístico
        """
    )
    
    if df_ranking.empty:
        st.info("Tabela de classificação vazia ou indisponível para este escopo.")
    else:
        # Localiza o usuário
        my_row = df_ranking[df_ranking["Usuário"] == user["username"]] if "Usuário" in df_ranking.columns else df_ranking[df_ranking["Participante"] == user["full_name"]]

        if not my_row.empty:
            pos = int(my_row.iloc[0]["Posição"])
            pts = int(my_row.iloc[0]["Pontos Totais"])
            exat = int(my_row.iloc[0]["Placares Exatos"]) if "Placares Exatos" in my_row.columns else 0
            
            rc1, rc2, rc3 = st.columns(3)
            rc1.metric(f"Sua posição ({'Meu Grupo' if selected_group_id else 'Geral'})", f"{pos}º")
            rc2.metric("Seus pontos", pts)
            rc3.metric("Seus placares exatos", exat)
            
            st.markdown(f"💡 Destaque: **{user['full_name']}** está em **{pos}º** lugar no filtro atual.")
            st.write("")

        # Exibição do DataFrame de Ranking
        st.dataframe(
            df_ranking,
            width="stretch",
            hide_index=True,
            column_config={
                "Posição": st.column_config.NumberColumn(format="%dº"),
            },
        )

        # Histograma/Gráfico de Barras
        st.subheader("Distribuição de pontos por participante")
        col_grafico = "Participante" if "Participante" in df_ranking.columns else "Usuário"
        chart_data = df_ranking.set_index(col_grafico)["Pontos Totais"]
        st.bar_chart(chart_data)

        st.divider()

        # --- RANKING POR FASE COM FILTRAGEM DINÂMICA VIA PANDAS ---
        st.subheader("🏆 Classificação por Fase")
        phases = db.list_phases()
        if phases:
            phase_names = [p["name"] for p in phases]
            sel_phase = st.selectbox("Selecionar fase para análise:", phase_names)
            phase_id = next(p["id"] for p in phases if p["name"] == sel_phase)
            
            df_phase = scoring.phase_ranking(phase_id)
            if not df_phase.empty:
                # Se houver grupo ativo, usamos a interseção do Pandas para limpar quem não é do grupo
                if selected_group_id is not None:
                    allowed_names = set(df_ranking[col_grafico])
                    df_phase = df_phase[df_phase[col_grafico].isin(allowed_names)].reset_index(drop=True)
                
                df_phase.index = df_phase.index + 1
                df_phase.index.name = "Posição"
                st.dataframe(df_phase, width="stretch")
            else:
                st.info("Sem dados computados para esta fase.")

    # Regulamento de pontos
    st.divider()
    st.subheader("📋 Regras de Pontuação Oficial")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            **Jogos (não cumulativo)**
            | Regra | Pontos |
            |-------|--------|
            | Placar exato | 8 |
            | Resultado + saldo | 5 |
            | Resultado correto | 3 |
            | Erro | 0 |
            """
        )
    with col2:
        st.markdown(
            """
            **Palpites especiais**
            | Palpite | Pontos |
            |---------|--------|
            | Campeão | 10 |
            | Vice | 5 |
            | Artilheiro | 5 |
            """
        )

# ==============================================================================
# --- RODAPÉ (STATUS DO TORNEIO) ---
# ==============================================================================
st.divider()
st.subheader("🟢 Status das Fases da Copa")
phases_status = db.list_phases()
status_cols = st.columns(len(phases_status) if phases_status else 1)

for idx, phase in enumerate(phases_status):
    status = phase["status"]
    icon = {"Não iniciada": "⬜", "Aberta": "🟢", "Fechada": "🟡", "Finalizada": "✅"}.get(status, "❓")
    with status_cols[idx % len(status_cols)]:
        st.markdown(f"{icon} **{phase['name']}**\n`{status}`")
