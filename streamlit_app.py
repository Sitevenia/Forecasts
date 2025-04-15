
import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Forecast de Commandes", layout="wide")

st.title("📦 Application de Forecast de Commandes")

# Upload du fichier
uploaded_file = st.file_uploader("📁 Charger le fichier Excel", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        
        # Colonnes attendues de base
        required_columns = ["référence fournisseur", "référence produit", "désignation", "stock", "prix d’achat", "conditionnement"]
        month_columns = [col for col in df.columns if str(col).strip().lower() in [f"mois {i}" for i in range(1, 13)]]

        if not all(col in df.columns for col in required_columns) or len(month_columns) != 12:
            st.error("❌ Le fichier doit contenir les colonnes : référence fournisseur, référence produit, désignation, stock, prix d’achat, conditionnement + 12 mois (mois 1 à mois 12).")
        else:
            st.success("✅ Fichier chargé avec succès.")

            # Sélection du pourcentage de progression
            progression = st.slider("📈 Pourcentage de progression annuel (%)", min_value=-100, max_value=300, value=0)

            # Objectif d'achat (optionnel)
            use_objectif = st.checkbox("🎯 Utiliser un objectif de montant global d'achat ?")
            objectif_achat = None
            if use_objectif:
                objectif_achat = st.number_input("💰 Objectif d’achat annuel (€)", min_value=0.0, step=1000.0)

            # Conversion colonnes mois en numérique
            df[month_columns] = df[month_columns].apply(pd.to_numeric, errors='coerce').fillna(0)
            df["stock"] = pd.to_numeric(df["stock"], errors='coerce').fillna(0)
            df["prix d’achat"] = pd.to_numeric(df["prix d’achat"], errors='coerce').fillna(0)
            df["conditionnement"] = pd.to_numeric(df["conditionnement"], errors='coerce').fillna(1)

            # Simulation 1 : progression + tendance
            df_sim1 = df.copy()
            trend_ratio = df[month_columns[-4:]].sum(axis=1) / df[month_columns[:4]].sum(axis=1).replace(0, np.nan)
            trend_ratio = trend_ratio.fillna(1).clip(0.5, 1.5)

            df_sim1[month_columns] = (df[month_columns] * (1 + progression / 100) * trend_ratio[:, None]).clip(lower=0)

            # Simulation 2 : ajustement pour atteindre objectif global
            df_sim2 = df_sim1.copy()
            if use_objectif and objectif_achat:
                montant_total = (df_sim2[month_columns].sum(axis=1) * df_sim2["prix d’achat"]).sum()
                facteur_ajustement = objectif_achat / montant_total if montant_total > 0 else 1
                df_sim2[month_columns] = (df_sim2[month_columns] * facteur_ajustement).clip(lower=0)

            # Ajustement au conditionnement
            for df_temp in [df_sim1, df_sim2]:
                for col in month_columns:
                    df_temp[col] = (df_temp[col] / df_temp["conditionnement"]).round().clip(lower=0) * df_temp["conditionnement"]

            # Calcul taux de rotation = conso annuelle / stock
            for df_temp in [df_sim1, df_sim2]:
                df_temp["taux rotation"] = (df_temp[month_columns].sum(axis=1) / df_temp["stock"]).replace([np.inf, -np.inf], 0).fillna(0).round(2)

            # Comparatif
            comparatif = df_sim1[["référence fournisseur", "référence produit", "désignation"] + month_columns].copy()
            comparatif.columns = ["référence fournisseur", "référence produit", "désignation"] + [f"Simu1 - Mois {i+1}" for i in range(12)]
            for i, col in enumerate(month_columns):
                comparatif[f"Simu2 - Mois {i+1}"] = df_sim2[col]
                comparatif[f"Écart Mois {i+1}"] = df_sim2[col] - df_sim1[col]

            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df_sim1.to_excel(writer, sheet_name="Simulation 1", index=False)
                df_sim2.to_excel(writer, sheet_name="Simulation 2", index=False)
                comparatif.to_excel(writer, sheet_name="Comparatif", index=False)
            st.download_button("📤 Télécharger les résultats", buffer.getvalue(), file_name="forecast_resultats.xlsx")

            # Aperçus
            st.subheader("📊 Aperçu des résultats")
            st.dataframe(comparatif.head(20))

    except Exception as e:
        st.error(f"Erreur de traitement : {e}")
