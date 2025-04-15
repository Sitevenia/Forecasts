
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Forecast - Refonte", layout="wide")
st.title("📦 Application Forecast (Version Refonte)")

# Authentification simple
PASSWORD = "forecast2024"
if "authenticated" not in st.session_state:
    password = st.text_input("🔐 Mot de passe", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
    else:
        st.stop()

uploaded_file = st.file_uploader("📁 Charger le fichier Excel", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.lower().str.replace("’", "'")

        required_columns = ["référence fournisseur", "référence produit", "désignation",
                            "tarif d'achat", "conditionnement", "stock"]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            st.error(f"❌ Colonnes manquantes : {missing}")
            st.stop()

        # Colonnes de mois (1 à 12)
        month_columns = [col for col in df.columns if col in [str(i) for i in range(1, 13)]]
        if len(month_columns) != 12:
            st.error("❌ 12 colonnes de mois attendues (1 à 12)")
            st.stop()

        st.success("✅ Données chargées")
        st.dataframe(df.head())

        # Simulation 1 : Progression %
        st.subheader("📈 Simulation par pourcentage de progression")
        progression = st.slider("Progression (%)", -100, 200, 10)

        df_sim1 = df.copy()
        df_sim1[month_columns] = df_sim1[month_columns].apply(lambda row: row * (1 + progression / 100))
        for col in month_columns:
            df_sim1[col] = (df_sim1[col] / df_sim1["conditionnement"]).round().astype(int) * df_sim1["conditionnement"]

        df_sim1["Montant annuel"] = df_sim1[month_columns].sum(axis=1) * df_sim1["tarif d'achat"]
        df_sim1["Taux de rotation"] = df_sim1[month_columns].sum(axis=1) / df_sim1["stock"]

        # Simulation 2 : Objectif montant annuel
        st.subheader("🎯 Simulation par objectif d’achat")
        use_objectif = st.checkbox("Activer cette simulation")
        objectif_global = None
        df_sim2 = None

        if use_objectif:
            objectif_global = st.number_input("Objectif de montant total (€)", min_value=0.0, step=1000.0)
            total_actuel = df_sim1["Montant annuel"].sum()
            coef = objectif_global / total_actuel if total_actuel > 0 else 1

            df_sim2 = df.copy()
            df_sim2[month_columns] = df_sim2[month_columns].apply(lambda row: row * coef)
            for col in month_columns:
                df_sim2[col] = (df_sim2[col] / df_sim2["conditionnement"]).round().astype(int) * df_sim2["conditionnement"]

            df_sim2["Montant annuel"] = df_sim2[month_columns].sum(axis=1) * df_sim2["tarif d'achat"]
            df_sim2["Taux de rotation"] = df_sim2[month_columns].sum(axis=1) / df_sim2["stock"]

        # Comparatif
        if use_objectif:
            st.subheader("🔍 Comparatif des simulations")
            comparatif = df[["référence produit", "désignation"]].copy()
            comparatif["Montant Sim 1"] = df_sim1["Montant annuel"]
            comparatif["Montant Sim 2"] = df_sim2["Montant annuel"]
            comparatif["Écart (€)"] = comparatif["Montant Sim 2"] - comparatif["Montant Sim 1"]
            st.dataframe(comparatif)

        # Export Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_sim1.to_excel(writer, index=False, sheet_name="Simulation_Progression")
            if use_objectif and df_sim2 is not None:
                df_sim2.to_excel(writer, index=False, sheet_name="Simulation_Objectif")
                comparatif.to_excel(writer, index=False, sheet_name="Comparatif")
        output.seek(0)

        st.download_button(
            label="📥 Télécharger le fichier Excel",
            data=output,
            file_name="forecast_resultat.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Erreur de traitement : {e}")
