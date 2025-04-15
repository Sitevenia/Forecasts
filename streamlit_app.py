
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
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            st.error(f"❌ Colonnes manquantes : {missing}")
            st.stop()
            st.stop()

        
# Colonnes de mois - détection souple
        # Conversion automatique des colonnes numériques
        df["tarif d'achat"] = pd.to_numeric(df["tarif d'achat"], errors="coerce").fillna(0)
        df["conditionnement"] = pd.to_numeric(df["conditionnement"], errors="coerce").replace(0, 1)
        df["stock"] = pd.to_numeric(df["stock"], errors="coerce").replace(0, 1)
    
        mois_possibles = {
            "1": "janvier", "2": "février", "3": "mars", "4": "avril",
            "5": "mai", "6": "juin", "7": "juillet", "8": "août",
            "9": "septembre", "10": "octobre", "11": "novembre", "12": "décembre"
        }

        month_columns = []
        for key, val in mois_possibles.items():
            if key in df.columns:
                month_columns.append(key)
            elif val in df.columns:
                month_columns.append(val)

        if len(month_columns) != 12:
            st.error("❌ 12 colonnes de mois attendues (chiffres ou noms de mois en français).")
            st.stop()

        st.success("✅ Données chargées")
        st.dataframe(df.head())

        # Simulation 1 : Progression %
        st.subheader("📈 Simulation par pourcentage de progression")
        progression = st.slider("Progression (%)", -100, 200, 10)

        df_sim1 = df.copy()
        df_sim1[month_columns] = (df_sim1[month_columns].apply(pd.to_numeric, errors='coerce').fillna(0) * (1 + progression / 100)).clip(lower=0)
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
            df_sim2[month_columns] = (df_sim2[month_columns].apply(pd.to_numeric, errors='coerce').fillna(0) * coef).clip(lower=0)
            for col in month_columns:
                df_sim2[col] = (df_sim2[col] / df_sim2["conditionnement"]).round().astype(int) * df_sim2["conditionnement"]

            df_sim2["Montant annuel"] = df_sim2[month_columns].sum(axis=1) * df_sim2["tarif d'achat"]
            df_sim2["Taux de rotation"] = df_sim2[month_columns].sum(axis=1) / df_sim2["stock"]

        
    # Comparatif
    comparatif = df_sim1[["référence fournisseur", "référence produit", "désignation", "stock"] + month_columns].copy()
    comparatif = comparatif.rename(columns={col: f"{col} (sim1)" for col in month_columns})

    for col in month_columns:
        comparatif[f"{col} (sim2)"] = df_sim2[col]
        comparatif[f"{col} (écart)"] = df_sim2[col] - df_sim1[col]


    except Exception as e:
        st.error(f"Erreur de traitement : {e}")
    comparatif["écart total"] = df_sim2[month_columns].sum(axis=1) - df_sim1[month_columns].sum(axis=1)

        if use_objectif:
            st.subheader("🔍 Comparatif des simulations")
            comparatif = df[["référence produit", "désignation"]].copy()
            comparatif["Montant Sim 1"] = df_sim1["Montant annuel"]
            comparatif["Montant Sim 2"] = df_sim2["Montant annuel"]
            comparatif["Écart (€)"] = comparatif["Montant Sim 2"] - comparatif["Montant Sim 1"]
            st.dataframe(comparatif)

        
    # Affichage graphique
    st.subheader("Analyse graphique")

    produit_selectionne = st.selectbox("Sélectionner un produit pour visualisation", df_sim1["référence produit"].unique())

    if produit_selectionne:
        data_graph = pd.DataFrame({
            "Mois": month_columns * 2,
            "Quantité": list(df_sim1[df_sim1["référence produit"] == produit_selectionne][month_columns].values[0]) + list(df_sim2[df_sim2["référence produit"] == produit_selectionne][month_columns].values[0]),
            "Simulation": ["Simulation 1"] * len(month_columns) + ["Simulation 2"] * len(month_columns)
        })
        st.line_chart(data_graph.pivot(index="Mois", columns="Simulation", values="Quantité"))

    # Génération des bons de commande
    st.subheader("Bon de commande - Simulation 1")
    bon_commande_1 = df_sim1[["référence fournisseur", "référence produit", "désignation"] + month_columns]
    bon_commande_1["quantité totale à commander"] = df_sim1[month_columns].sum(axis=1).astype(int)
    bon_commande_1 = bon_commande_1[["référence fournisseur", "référence produit", "désignation", "quantité totale à commander"]]
    st.dataframe(bon_commande_1)

    st.subheader("Bon de commande - Simulation 2")
    bon_commande_2 = df_sim2[["référence fournisseur", "référence produit", "désignation"] + month_columns]
    bon_commande_2["quantité totale à commander"] = df_sim2[month_columns].sum(axis=1).astype(int)
    bon_commande_2 = bon_commande_2[["référence fournisseur", "référence produit", "désignation", "quantité totale à commander"]]
    st.dataframe(bon_commande_2)


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
