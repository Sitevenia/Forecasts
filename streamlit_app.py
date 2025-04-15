
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Forecast mensuel", layout="wide")

st.title("📈 Application de Forecast mensuel")

uploaded_file = st.file_uploader("📁 Charger le fichier Excel", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        required_columns = [
            "référence fournisseur", "référence produit", "désignation", "stock",
            "prix d’achat", "conditionnement"
        ]
        month_columns = [col for col in df.columns if any(str(i) in col.lower() for i in ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"])]
        if not all(col in df.columns for col in required_columns) or len(month_columns) != 12:
            st.error("❌ Certaines colonnes obligatoires sont manquantes.")
        else:
            progression = st.slider("📊 Pourcentage de progression (%)", -50, 100, 10)
            objectif = st.number_input("🎯 Objectif global d'achat (€)", min_value=0.0, value=0.0, step=100.0)
            use_objectif = st.checkbox("✅ Utiliser l’objectif global d’achat")

            df_sim1 = df.copy()
            df_sim1[month_columns] = (
                df_sim1[month_columns].apply(pd.to_numeric, errors='coerce').fillna(0)
                * (1 + progression / 100)
            ).clip(lower=0)

            df_sim1["montant"] = df_sim1[month_columns].sum(axis=1) * df_sim1["prix d’achat"]
            df_sim1["taux de rotation"] = ((df_sim1[month_columns].sum(axis=1) / df_sim1["stock"])
                                            .replace([np.inf, -np.inf], np.nan).fillna(0).round(2))

            df_sim2 = df_sim1.copy()

            if use_objectif and objectif > 0:
                montant_total = df_sim1["montant"].sum()
                if montant_total > 0:
                    ajustement = objectif / montant_total
                    df_sim2[month_columns] = (df_sim2[month_columns] * ajustement).round()
                    df_sim2["montant"] = df_sim2[month_columns].sum(axis=1) * df_sim2["prix d’achat"]
                    df_sim2["ajustement"] = "Ajusté pour atteindre l’objectif"
                else:
                    df_sim2["ajustement"] = "Montant initial nul"
            else:
                df_sim2["ajustement"] = "Non ajusté (objectif non utilisé)"

            # Comparatif
            try:
                comparatif = df_sim1[["référence fournisseur", "référence produit", "désignation", "stock"] + month_columns].copy()
                comparatif = comparatif.rename(columns={col: f"{col} (sim1)" for col in month_columns})

                for col in month_columns:
                    comparatif[f"{col} (sim2)"] = df_sim2[col]
                    comparatif[f"{col} (écart)"] = df_sim2[col] - df_sim1[col]

                st.dataframe(comparatif)
            except Exception as e:
                st.error(f"Erreur dans le comparatif : {e}")
    except Exception as e:
        st.error(f"Erreur de traitement : {e}")
else:
    st.info("Veuillez charger un fichier Excel pour commencer.")
