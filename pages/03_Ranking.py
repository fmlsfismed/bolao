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

# --- LÓGICA DE FILTRO POR GRUPO DE USUÁRIOS (ESCOPO MESTRE) ---
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

# Criamos duas abas principais para organizar o layout de forma limpa e profissional
tab_dash, tab_rank = st.tabs(["⭐ Destaques e Métricas", "🏆 Tabelas de Classificação"])

# ==============================================================================
# --- ABA 1: DASHBOARD (MÉTRICAS + EMPATES) ---
# ==============================================================================
with tab_dash:
    metrics = scoring.dashboard_metrics(group_id=selected_group_id)

    if not metrics:
        st.info("Estatísticas e destaques indisponíveis para o escopo selecionado.")
    else:
        # FUNÇÃO FORMATADORA DE EMPATES MÚLTIPLOS
        def formatar_nomes(lista_nomes: list[str]) -> str:
            if not lista_nomes:
                return "Ninguém ainda"
            if len(lista_nomes) == 1:
                return lista_nomes[0]
            if len(lista_nomes) == 2:
                return f"{lista_nomes[0]} e {lista_nomes[1]}"
            return ", ".join(lista_nomes)

        # Recupera as informações processadas com suporte a empates
        label_lider = formatar_nomes(metrics.get("leaders", []))
        label_exato = formatar_nomes(metrics.get("exact_kings", []))
        label_hat_trick = formatar_nomes(metrics.get("hat_tricks", []))
        label_zebra = formatar_nomes(metrics.get("zebra_kings", []))

        best_phase = metrics.get("best_phase", {"phase": None, "user": "-", "points": -1})
        climb = metrics.get("biggest_climb", {"user": None, "delta": 0})

        # LINHA SUPERIOR
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("### 👑 Líder")
            st.metric(
                label=label_lider,
                value=f"{metrics.get('max_points', 0)} pts",
                delta=f"{metrics.get('max_exact_leader', 0)} exatos" if metrics.get('max_exact_leader', 0) > 0 else None,
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
                value=f"{metrics.get('max_exact', 0)} exatos" if metrics.get('max_exact', 0) > 0 else "0 exatos",
            )

        st.divider()

        # LINHA INFERIOR
        c4, c5, c6 = st.columns(3)
        with c4:
            st.markdown("### ⚡ Hat-Trick")
            st.caption("Mais sequências de 3+ placares exatos consecutivos")
            if metrics.get("max_hat_tricks", 0) > 0:
                st.metric(
                    label=label_hat_trick,
                    value=f"{metrics.get('max_hat_tricks')} hat-tricks",
                    delta=f"Maior sequência: {metrics.get('max_streak', 0)}",
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
            if metrics.get("max_zebra_pts", 0) > 0:
                st.metric(label=label_zebra, value=f"{metrics.get('max_zebra_pts')} pts")
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
    
    # Coleta a classificação injetando o grupo selecionado
    df_ranking = scoring.ranking_dataframe(group_id=selected_group_id)

    if df_ranking.empty:
        st.info("Tabela de classificação indisponível no momento.")
    else:
        # Encontra o usuário logado
        my_row = df_ranking[df_ranking["Usuário"] == user["username"]]

        if not my_row.empty:
            pos = int(my_row.iloc[0]["Posição"])
            pts = int(my_row.iloc[0]["Pontos Totais"])
            
            rc1, rc2, rc3 = st.columns(3)
            rc1.metric(f"Sua posição ({'Meu Grupo' if selected_group_id else 'Geral'})", f"{pos}º")
            rc2.metric("Seus pontos", pts)
            rc3.metric("Seus placares exatos", int(my_row.iloc[0]["Placares Exatos"]))
            
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
        chart_data = df_ranking.set_index("Participante")["Pontos Totais"]
        st.bar_chart(chart_data)

        st.divider()

        # --- RANKING POR FASE COM FILTRAGEM DINÂMICA ---
        st.subheader("🏆 Classificação por Fase")
        phases = db.list_phases()
        if phases:
            phase_names = [p["name"] for p in phases]
            sel_phase = st.selectbox("Selecionar fase para análise:", phase_names)
            phase_id = next(p["id"] for p in phases if p["name"] == sel_phase)
            
            df_phase = scoring.phase_ranking(phase_id)
            if not df_phase.empty:
                # Se houver grupo ativo, filtra o ranking da fase com base nos membros elegíveis
                if selected_group_id is not None:
                    allowed_names = set(df_ranking["Participante"])
                    df_phase = df_phase[df_phase["Participante"].isin(allowed_names)].reset_index(drop=True)
                
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
