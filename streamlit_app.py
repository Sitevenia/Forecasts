
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Forecast App", layout="wide")
st.title("📦 Application de Prévision des Commandes")

uploaded_file = st.file_uploader("Charger un fichier Excel", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Tableau final")
    month_columns = [str(i) for i in range(1, 13)]

    st.subheader("Simulation 1 : progression 0% (base N-1)")
    df["Tarif d'achat"] = pd.to_numeric(df["Tarif d'achat"], errors="coerce").fillna(0)
    df["Total ventes N-1"] = df[month_columns].sum(axis=1)
    df["Montant achat N-1"] = df["Total ventes N-1"] * df["Tarif d'achat"]
    total_sim1 = df["Montant achat N-1"].sum()
    st.metric("💰 Total Simulation 1", f"€ {total_sim1:,.2f}")

    objectif_global = st.number_input("🎯 Montant cible à atteindre pour la Simulation 2", value=0)

    if objectif_global > 0 and st.button("▶️ Lancer Simulation 2"):
        df_sim2 = df.copy()
        for col in month_columns:
            df_sim2[col] = 0
        df_sim2["Conditionnement"] = pd.to_numeric(df_sim2["Conditionnement"], errors='coerce').fillna(1).replace(0, 1)
        df_sim2["Coût par lot"] = df_sim2["Tarif d'achat"] * df_sim2["Conditionnement"]
        df_sim2["Packs"] = 0

        total = 0
        for _ in range(100000):
            if total >= objectif_global:
                break
            eligible = df_sim2[df_sim2["Coût par lot"] > 0].sort_values(by="Coût par lot")
            for idx in eligible.index:
                cost = df_sim2.loc[idx, "Coût par lot"]
                if total + cost <= objectif_global:
                    df_sim2.loc[idx, "Packs"] += 1
                    total += cost
                    break

        for col in month_columns:
            df_sim2[col] = (df_sim2["Packs"] * df_sim2["Conditionnement"] / 12).round().astype(int)

        df_sim2["Qté Totale"] = df_sim2[month_columns].sum(axis=1)
        df_sim2["Montant Sim 2"] = df_sim2["Qté Totale"] * df_sim2["Tarif d'achat"]
        montant_sim2 = df_sim2["Montant Sim 2"].sum()
        st.metric("✅ Objectif atteint", "€ {:,.2f}".format(montant_sim2))
        st.dataframe(df_sim2[["Référence fournisseur", "Référence produit", "Désignation", "Montant Sim 2"]])

        st.subheader("📊 Comparatif Simulation 1 vs Simulation 2")
        comparatif = df[["Référence fournisseur", "Référence produit", "Désignation"]].copy()
        comparatif["Montant Sim 1"] = df["Montant achat N-1"]
        if "Montant Sim 2" in df_sim2.columns:
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
