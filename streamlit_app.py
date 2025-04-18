
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Forecast App", layout="wide")
st.title("📦 Application de Prévision des Commandes")

uploaded_file = st.file_uploader("📁 Charger le fichier Excel", type=["xlsx"])

# Répartition saisonnière ajustée au total et au conditionnement
def repartir_et_ajuster(qte_totale, saisonnalite, conditionnement):
    try:
        if not np.isfinite(qte_totale) or qte_totale <= 0 or saisonnalite.isnull().all():
            return np.zeros(12, dtype=int)
        saisonnalite = np.array(saisonnalite.fillna(0))
        if saisonnalite.sum() == 0:
            return np.zeros(12, dtype=int)
        saisonnalite = saisonnalite / saisonnalite.sum()
        raw = qte_totale * saisonnalite
        repartition = np.nan_to_num(np.ceil(raw / conditionnement) * conditionnement, nan=0.0, posinf=0.0, neginf=0.0)
        ecart = int(qte_totale - repartition.sum())
        while ecart != 0:
            idx = np.argmax(saisonnalite) if ecart > 0 else np.argmax(repartition)
            modif = conditionnement if ecart > 0 else -conditionnement
            tentative = repartition[idx] + modif
            if tentative >= 0:
                repartition[idx] = tentative
                ecart -= modif
            else:
                break
        return repartition.astype(int)
    except:
        return np.zeros(12, dtype=int)

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Tableau final")
        st.success("✅ Fichier chargé avec succès.")
        month_columns = [str(i) for i in range(1, 13)]

        df[month_columns] = df[month_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
        df["Tarif d'achat"] = pd.to_numeric(df["Tarif d'achat"], errors="coerce").fillna(0)
        df["Conditionnement"] = pd.to_numeric(df["Conditionnement"], errors="coerce").fillna(1).replace(0, 1)

        df["Total ventes N-1"] = df[month_columns].sum(axis=1).replace(0, np.nan)
        saisonnalite = df[month_columns].div(df["Total ventes N-1"].replace(0, np.nan), axis=0).replace([np.inf, -np.inf], 0).fillna(0)

        # Simulation 1
        st.subheader("Simulation 1 : progression personnalisée")
        progression = st.number_input("📈 Progression (%)", value=0.0, step=1.0)
        df["Qté Sim 1"] = df["Total ventes N-1"] * (1 + progression / 100)
        df["Qté Sim 1"] = (np.ceil(df["Qté Sim 1"] / df["Conditionnement"]) * df["Conditionnement"]).astype(int)

        for i in df.index:
            try:
                repartition = repartir_et_ajuster(
                    df.at[i, "Qté Sim 1"],
                    saisonnalite.loc[i, month_columns],
                    df.at[i, "Conditionnement"]
                )
                df.loc[i, month_columns] = pd.Series([int(x) if np.isfinite(x) else 0 for x in repartition], index=month_columns)
            except:
                df.loc[i, month_columns] = [0] * 12

        df["Montant Sim 1"] = df["Qté Sim 1"] * df["Tarif d'achat"]
        total_sim1 = df["Montant Sim 1"].sum()
        st.metric("💰 Total Simulation 1", f"€ {total_sim1:,.2f}")

        # Simulation 2
        st.subheader("Simulation 2 : objectif d'achat ajusté précisément")
        objectif = st.number_input("🎯 Objectif (€)", value=0.0, step=1000.0)

        if objectif > 0 and st.button("▶️ Lancer Simulation 2"):
            df_sim2 = df.copy()
            df_sim2["Qté Base"] = df["Total ventes N-1"].replace(0, 1)
            total_base_value = (df_sim2["Qté Base"] * df_sim2["Tarif d'achat"]).sum()

            if total_base_value == 0:
                st.error("❌ Impossible : total de base nul.")
            else:
                best_coef = 1.0
                best_diff = float("inf")
                for coef in np.arange(0.01, 2.0, 0.01):
                    q_test = np.ceil((df_sim2["Qté Base"] * coef) / df_sim2["Conditionnement"]) * df_sim2["Conditionnement"]
                    montant_test = (q_test * df_sim2["Tarif d'achat"]).sum()
                    diff = abs(montant_test - objectif)
                    if montant_test <= objectif and diff < best_diff:
                        best_diff = diff
                        best_coef = coef

                df_sim2["Qté Sim 2"] = (np.ceil((df_sim2["Qté Base"] * best_coef) / df_sim2["Conditionnement"]) * df_sim2["Conditionnement"]).astype(int)

                for i in df_sim2.index:
                    try:
                        repartition = repartir_et_ajuster(
                            df_sim2.at[i, "Qté Sim 2"],
                            saisonnalite.loc[i, month_columns],
                            df_sim2.at[i, "Conditionnement"]
                        )
                        df_sim2.loc[i, month_columns] = pd.Series([int(x) if np.isfinite(x) else 0 for x in repartition], index=month_columns)
                    except:
                        df_sim2.loc[i, month_columns] = [0] * 12

                df_sim2["Montant Sim 2"] = df_sim2["Qté Sim 2"] * df_sim2["Tarif d'achat"]
                total_sim2 = df_sim2["Montant Sim 2"].sum()
                st.metric("✅ Montant Simulation 2", f"€ {total_sim2:,.2f}")

                st.dataframe(df_sim2[["Référence fournisseur", "Référence produit", "Désignation", "Qté Sim 2", "Montant Sim 2"]])

                # Comparatif
                st.subheader("📊 Comparatif")
                comparatif = df[["Référence fournisseur", "Référence produit", "Désignation"]].copy()
                comparatif["Qté Sim 1"] = df["Qté Sim 1"]
                comparatif["Montant Sim 1"] = df["Montant Sim 1"]
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
                st.download_button("📥 Télécharger le fichier Excel", output, file_name="forecast_result_final.xlsx")

    except Exception as e:
        st.error(f"❌ Erreur : {e}")
else:
    st.info("Veuillez charger un fichier pour commencer.")
