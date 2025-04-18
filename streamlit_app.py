
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Forecast Simulation", layout="wide")
st.title("📦 Application de Prévision des Commandes")

uploaded_file = st.file_uploader("📁 Charger votre fichier Excel", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Tableau final")
        st.success("✅ Fichier chargé avec succès.")
        month_columns = [str(i) for i in range(1, 13)]

        df[month_columns] = df[month_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
        df["Tarif d'achat"] = pd.to_numeric(df["Tarif d'achat"], errors="coerce").fillna(0)
        df["Conditionnement"] = pd.to_numeric(df["Conditionnement"], errors="coerce").fillna(1).replace(0, 1)

        df["Total ventes N-1"] = df[month_columns].sum(axis=1)
        saisonnalite = df[month_columns].div(df["Total ventes N-1"].replace(0, 1), axis=0)

        # --- Simulation 1 ---
        st.subheader("Simulation 1 : progression des ventes N-1")
        progression = st.number_input("📈 Pourcentage de progression Simulation 1", value=0.0, step=1.0)
        df["Qté Sim 1"] = (df["Total ventes N-1"] * (1 + progression / 100))
        df["Qté Sim 1"] = (np.ceil(df["Qté Sim 1"] / df["Conditionnement"]) * df["Conditionnement"]).astype(int)
        for mois in month_columns:
            df[mois] = (df["Qté Sim 1"] * saisonnalite[mois]).round().astype(int)
        df["Montant Sim 1"] = df["Qté Sim 1"] * df["Tarif d'achat"]
        total_sim1 = df["Montant Sim 1"].sum()
        st.metric("💰 Total Simulation 1", f"€ {total_sim1:,.2f}")

        # --- Simulation 2 : basée sur boucle équilibrée et saisonnalité ---
        st.subheader("Simulation 2 : atteindre un objectif d'achat équilibré")
        objectif = st.number_input("🎯 Objectif d'achat à atteindre (€)", value=0)

        if objectif > 0 and st.button("▶️ Lancer Simulation 2"):
            df_sim2 = df.copy()
            df_sim2["Qté Sim 2"] = 0
            df_sim2["Montant cumulé"] = 0
            total = 0
            max_iterations = 100000

            for _ in range(max_iterations):
                for idx in df_sim2.index:
                    prix = df_sim2.at[idx, "Tarif d'achat"]
                    cond = df_sim2.at[idx, "Conditionnement"]
                    ajout = cond
                    montant = prix * ajout
                    if total + montant > objectif:
                        continue
                    df_sim2.at[idx, "Qté Sim 2"] += ajout
                    total += montant
                if total >= objectif:
                    break

            df_sim2["Montant Sim 2"] = df_sim2["Qté Sim 2"] * df_sim2["Tarif d'achat"]
            for mois in month_columns:
                df_sim2[mois] = (df_sim2["Qté Sim 2"] * saisonnalite[mois]).round().astype(int)

            st.metric("✅ Montant Simulation 2", f"€ {df_sim2['Montant Sim 2'].sum():,.2f}")
            st.dataframe(df_sim2[["Référence fournisseur", "Référence produit", "Désignation", "Qté Sim 2", "Montant Sim 2"]])

            # --- Comparatif ---
            st.subheader("📊 Comparatif Simulation 1 vs 2")
            comparatif = df[["Référence fournisseur", "Référence produit", "Désignation"]].copy()
            comparatif["Qté Sim 1"] = df["Qté Sim 1"]
            comparatif["Montant Sim 1"] = df["Montant Sim 1"]
            comparatif["Qté Sim 2"] = df_sim2["Qté Sim 2"]
            comparatif["Montant Sim 2"] = df_sim2["Montant Sim 2"]
            st.dataframe(comparatif)

            # --- Export ---
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, sheet_name="Simulation_1", index=False)
                df_sim2.to_excel(writer, sheet_name="Simulation_2", index=False)
                comparatif.to_excel(writer, sheet_name="Comparatif", index=False)
            output.seek(0)
            st.download_button("📥 Télécharger le fichier Excel", output, file_name="forecast_result.xlsx")

    except Exception as e:
        st.error(f"❌ Erreur : {e}")
else:
    st.info("Veuillez charger un fichier pour commencer.")
