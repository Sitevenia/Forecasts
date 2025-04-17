
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Forecast App", layout="wide")
st.title("📦 Application de Prévision des Commandes")

uploaded_file = st.file_uploader("📁 Charger votre fichier Excel", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Tableau final")
        st.success("✅ Fichier chargé avec succès.")
        month_columns = [str(i) for i in range(1, 13)]

        # Nettoyage
        df[month_columns] = df[month_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
        df["Tarif d'achat"] = pd.to_numeric(df["Tarif d'achat"], errors="coerce").fillna(0)
        df["Conditionnement"] = pd.to_numeric(df["Conditionnement"], errors="coerce").fillna(1).replace(0, 1)

        # Simulation 1
        st.subheader("Simulation 1 : basée sur les ventes N-1")
        df["Total ventes N-1"] = df[month_columns].sum(axis=1)
        df["Montant achat N-1"] = df["Total ventes N-1"] * df["Tarif d'achat"]
        total_sim1 = df["Montant achat N-1"].sum()
        st.metric("💰 Total Simulation 1", f"€ {total_sim1:,.2f}")

        # Simulation 2
        objectif_global = st.number_input("🎯 Objectif global Simulation 2 (€)", value=0)

        if objectif_global > 0 and st.button("▶️ Lancer Simulation 2"):
            df_sim2 = df.copy()
            df_sim2[month_columns] = 0
            df_sim2["Qté Sim 2"] = 0

            # Saison : répartition N-1
            saisonnalite = df[month_columns].div(df["Total ventes N-1"].replace(0, 1), axis=0)

            # Initialisation
            df_sim2["Ajouté"] = 0
            total_montant = 0

            while total_montant < objectif_global:
                for idx in df_sim2.index:
                    cond = df_sim2.loc[idx, "Conditionnement"]
                    prix = df_sim2.loc[idx, "Tarif d'achat"]
                    ajout = cond
                    df_sim2.at[idx, "Ajouté"] += ajout
                    df_sim2.at[idx, "Qté Sim 2"] = df_sim2.at[idx, "Ajouté"]
                    montant_ligne = ajout * prix
                    total_montant += montant_ligne
                    if total_montant >= objectif_global:
                        break

            # Répartition mensuelle selon la saisonnalité
            for mois in month_columns:
                df_sim2[mois] = (df_sim2["Qté Sim 2"] * saisonnalite[mois]).round().astype(int)

            df_sim2["Montant Sim 2"] = df_sim2["Qté Sim 2"] * df_sim2["Tarif d'achat"]
            montant_sim2 = df_sim2["Montant Sim 2"].sum()
            st.metric("✅ Objectif Simulation 2", f"€ {montant_sim2:,.2f}")
            st.dataframe(df_sim2[["Référence fournisseur", "Référence produit", "Désignation", "Qté Sim 2", "Montant Sim 2"]])

            # Comparatif
            st.subheader("📊 Comparatif")
            comparatif = df[["Référence fournisseur", "Référence produit", "Désignation"]].copy()
            comparatif["Qté Sim 1"] = df["Total ventes N-1"]
            comparatif["Montant Sim 1"] = df["Montant achat N-1"]
            comparatif["Qté Sim 2"] = df_sim2["Qté Sim 2"]
            comparatif["Montant Sim 2"] = df_sim2["Montant Sim 2"]
            st.dataframe(comparatif)

            # Export Excel
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, sheet_name="Simulation_1", index=False)
                df_sim2.to_excel(writer, sheet_name="Simulation_2", index=False)
                comparatif.to_excel(writer, sheet_name="Comparatif", index=False)
            output.seek(0)
            st.download_button("📥 Télécharger le fichier Excel", output, file_name="export_forecast.xlsx")
    except Exception as e:
        st.error(f"❌ Erreur : {e}")
else:
    st.info("Veuillez charger un fichier pour commencer.")
