import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Forecast App", layout="wide")
st.title("📦 Application de Prévision des Commandes")

def safe_int(x):
    try:
        if pd.isna(x) or not np.isfinite(x):
            return 0
        return int(round(x))
    except:
        return 0

# Sélection du type de simulation au démarrage
simulation_type = st.selectbox("Sélectionnez le type de simulation", ["Simulation simple", "Simulation avec objectif de montant"])

# Chargement du fichier principal
uploaded_file = st.file_uploader("📁 Charger le fichier Excel principal", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Tableau final")
        st.success("✅ Fichier principal chargé avec succès.")

        # Vérifiez si la colonne "Stock" existe et la convertir en numérique si nécessaire
        if "Stock" in df.columns:
            df["Stock"] = pd.to_numeric(df["Stock"], errors="coerce").fillna(0)
        else:
            st.error("La colonne 'Stock' n'existe pas dans le fichier principal.")
            st.stop()

        month_columns = [str(i) for i in range(1, 13)]
        selected_months = st.multiselect("Sélectionnez les mois à inclure", month_columns, default=month_columns)

        for col in month_columns + ["Tarif d'achat"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["Total ventes N-1"] = df[selected_months].sum(axis=1).replace(0, np.nan)
        saisonnalite = df[selected_months].div(df["Total ventes N-1"], axis=0).replace([np.inf, -np.inf], 0).fillna(0)

        # Ajouter une colonne pour les quantités totales vendues en N-1 sur les mois sélectionnés
        df["Total ventes N-1 (sélection)"] = df[selected_months].sum(axis=1)

        if simulation_type == "Simulation simple":
            st.subheader("Simulation simple : progression personnalisée")
            progression = st.number_input("📈 Progression (%)", value=0.0, step=1.0)
            df["Qté Sim 1"] = df["Total ventes N-1"] * (1 + progression / 100)

            if st.button("▶️ Lancer la Simulation simple"):
                for i in df.index:
                    repartition = df.at[i, "Qté Sim 1"] * saisonnalite.loc[i, selected_months]
                    # Assurez-vous que la longueur de repartition correspond à celle des colonnes sélectionnées
                    if len(repartition) == len(selected_months):
                        df.loc[i, selected_months] = repartition
                    else:
                        st.error("Erreur : La longueur de la répartition ne correspond pas aux mois sélectionnés.")

                df["Montant Sim 1"] = df["Qté Sim 1"] * df["Tarif d'achat"]
                total_sim1 = df["Montant Sim 1"].sum()
                st.metric("💰 Total Simulation simple", f"€ {total_sim1:,.2f}")

                # Afficher les résultats dans un tableau
                st.write("### Résultats de la Simulation Simple")
                st.dataframe(df[["Référence fournisseur", "Référence produit", "Désignation", "Stock", "Total ventes N-1 (sélection)", "Qté Sim 1", "Montant Sim 1"] + selected_months])

                # Export Simulation simple
                output1 = io.BytesIO()
                with pd.ExcelWriter(output1, engine="xlsxwriter") as writer:
                    # Filtrer les colonnes avant l'exportation
                    df_filtered = df[["Référence fournisseur", "Référence produit", "Désignation", "Stock", "Total ventes N-1 (sélection)", "Qté Sim 1", "Montant Sim 1"] + selected_months]
                    df_filtered.to_excel(writer, sheet_name="Simulation_simple", index=False)

                    # Ajouter une ligne pour le montant total
                    worksheet = writer.sheets["Simulation_simple"]
                    last_row = len(df_filtered)
                    montant_col = df_filtered.columns.get_loc("Montant Sim 1")
                    worksheet.write(last_row + 1, montant_col, "Total")
                    worksheet.write_formula(last_row + 1, montant_col + 1, f"=SUM(G2:G{last_row + 2})")

                output1.seek(0)
                st.download_button("📥 Télécharger Simulation simple", output1, file_name="simulation_simple.xlsx")

        elif simulation_type == "Simulation avec objectif de montant":
            st.subheader("Simulation avec objectif de montant")
            objectif = st.number_input("🎯 Objectif (€)", value=0.0, step=1000.0)

            if objectif > 0:
                if st.button("▶️ Lancer la Simulation avec objectif de montant"):
                    df_sim2 = df.copy()
                    df_sim2["Qté Base"] = df["Total ventes N-1"].replace(0, 1)
                    total_base_value = (df_sim2["Qté Base"] * df_sim2["Tarif d'achat"]).sum()

                    best_coef = 1.0
                    best_diff = float("inf")
                    for coef in np.arange(0.01, 2.0, 0.01):
                        q_test = df_sim2["Qté Base"] * coef
                        montant_test = (q_test * df_sim2["Tarif d'achat"]).sum()
                        diff = abs(montant_test - objectif)
                        if montant_test <= objectif and diff < best_diff:
                            best_diff = diff
                            best_coef = coef

                    df_sim2["Qté Sim 2"] = (df_sim2["Qté Base"] * best_coef).fillna(0).astype(int)

                    for i in df_sim2.index:
                        repartition = df_sim2.at[i, "Qté Sim 2"] * saisonnalite.loc[i, selected_months]
                        # Assurez-vous que la longueur de repartition correspond à celle des colonnes sélectionnées
                        if len(repartition) == len(selected_months):
                            df_sim2.loc[i, selected_months] = repartition
                        else:
                            st.error("Erreur : La longueur de la répartition ne correspond pas aux mois sélectionnés.")

                    df_sim2["Montant Sim 2"] = df_sim2["Qté Sim 2"] * df_sim2["Tarif d'achat"]
                    total_sim2 = df_sim2["Montant Sim 2"].sum()
                    st.metric("✅ Montant Simulation avec objectif de montant", f"€ {total_sim2:,.2f}")

                    # Afficher les résultats dans un tableau
                    st.write("### Résultats de la Simulation avec Objectif de Montant")
                    st.dataframe(df_sim2[["Référence fournisseur", "Référence produit", "Désignation", "Stock", "Total ventes N-1 (sélection)", "Qté Sim 2", "Montant Sim 2"] + selected_months])

                    # Export Simulation avec objectif de montant
                    output2 = io.BytesIO()
                    with pd.ExcelWriter(output2, engine="xlsxwriter") as writer:
                        # Filtrer les colonnes avant l'exportation
                        df_filtered_sim2 = df_sim2[["Référence fournisseur", "Référence produit", "Désignation", "Stock", "Total ventes N-1 (sélection)", "Qté Sim 2", "Montant Sim 2"] + selected_months]
                        df_filtered_sim2.to_excel(writer, sheet_name="Simulation_objectif", index=False)

                        # Ajouter une ligne pour le montant total
                        worksheet = writer.sheets["Simulation_objectif"]
                        last_row = len(df_filtered_sim2)
                        montant_col = df_filtered_sim2.columns.get_loc("Montant Sim 2")
                        worksheet.write(last_row + 1, montant_col, "Total")
                        worksheet.write_formula(last_row + 1, montant_col + 1, f"=SUM(G2:G{last_row + 2})")

                    output2.seek(0)
                    st.download_button("📥 Télécharger Simulation avec objectif de montant", output2, file_name="simulation_objectif.xlsx")

    except Exception as e:
        st.error(f"❌ Erreur : {e}")
else:
    st.info("Veuillez charger le fichier principal pour commencer.")
