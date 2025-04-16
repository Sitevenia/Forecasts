
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from io import BytesIO
import tempfile

st.set_page_config(page_title="Forecast de commandes", layout="wide")
st.title("📦 Forecast de commandes")

# Authentification
PASSWORD = "forecast2024"
if "authenticated" not in st.session_state:
    pwd = st.text_input("🔐 Mot de passe", type="password")
    if pwd == PASSWORD:
        st.session_state.authenticated = True
    else:
        st.stop()

uploaded_file = st.file_uploader("📁 Charger le fichier Excel", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.lower().str.replace("’", "'")

        required_columns = ["référence fournisseur", "référence produit", "désignation", "tarif d'achat", "conditionnement", "stock"]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            st.error(f"❌ Colonnes manquantes : {missing}")
            st.stop()

        mois_possibles = {
            "1": "janvier", "2": "février", "3": "mars", "4": "avril",
            "5": "mai", "6": "juin", "7": "juillet", "8": "août",
            "9": "septembre", "10": "octobre", "11": "novembre", "12": "décembre"
        }
        month_columns = []
        for k, v in mois_possibles.items():
            if k in df.columns:
                month_columns.append(k)
            elif v in df.columns:
                month_columns.append(v)

        if len(month_columns) != 12:
            st.error("❌ 12 colonnes de mois attendues.")
            st.stop()

        st.success("✅ Données chargées")
        progression = st.slider("📈 Progression (%)", -100, 200, 10)
        use_objectif = st.checkbox("🎯 Activer un objectif d'achat ?")
        objectif_global = st.number_input("💰 Objectif total (€)", value=0.0, step=1000.0) if use_objectif else None

        for col in ["tarif d'achat", "conditionnement", "stock"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).replace(0, 1)

        df_sim1 = df.copy()
        df_sim1[month_columns] = (df_sim1[month_columns].apply(pd.to_numeric, errors='coerce').fillna(0) * (1 + progression / 100)).clip(lower=0)
        for col in month_columns:
            df_sim1[col] = (df_sim1[col] / df_sim1["conditionnement"]).round() * df_sim1["conditionnement"].round().astype(int)
            

        df_sim1["Montant annuel"] = df_sim1[month_columns].sum(axis=1) * df_sim1["tarif d'achat"]
        df_sim1["Taux de rotation"] = (df_sim1[month_columns].sum(axis=1) / df_sim1["stock"]).round(2)
        df_sim1["Qté Sim 1"] = df_sim1[month_columns].sum(axis=1)

        remarques_sim1 = []
        for idx, row in df_sim1.iterrows():
            taux = row["Taux de rotation"]
            if taux < 0.5:
                df_sim1.loc[idx, month_columns] *= 0.7
                remarques_sim1.append("Quantité réduite : taux < 0.5")
            elif taux > 4:
                df_sim1.loc[idx, month_columns] *= 1.2
                remarques_sim1.append("Quantité augmentée : taux > 4")
            else:
                remarques_sim1.append("")
        df_sim1["Remarque"] = remarques_sim1

        df_sim2 = df.copy()
        df_sim2[month_columns] = df_sim2[month_columns].apply(pd.to_numeric, errors='coerce').fillna(0)

        if use_objectif and objectif_global and st.button("▶️ Lancer Simulation 2 (objectif d'achat)"):
            df_sim2[month_columns] = 0
            df_sim2["tarif d'achat"] = pd.to_numeric(df_sim2["tarif d'achat"], errors="coerce").fillna(0)
            df_sim2["conditionnement"] = pd.to_numeric(df_sim2["conditionnement"], errors="coerce").fillna(1).replace(0, 1)
            df_sim2["stock"] = pd.to_numeric(df_sim2["stock"], errors="coerce").fillna(1).replace(0, 1)

            df_sim2["coût_conditionnement"] = df_sim2["tarif d'achat"] * df_sim2["conditionnement"]
            df_sim2["packs"] = 0
            total = 0
            max_iterations = 100000

            for _ in range(max_iterations):
                if total >= objectif_global:
                    break
                eligible = df_sim2[df_sim2["coût_conditionnement"] > 0].copy()
                eligible = eligible.sort_values(by="coût_conditionnement")
                for idx in eligible.index:
                    potential_add = df_sim2.loc[idx, "coût_conditionnement"]
                    if total + potential_add <= objectif_global:
                        df_sim2.loc[idx, "packs"] += 1
                        total += potential_add
                        break

            for col in month_columns:
                df_sim2[col] = (df_sim2["packs"] * df_sim2["conditionnement"] / 12).round().astype(int)

            df_sim2["Montant annuel"] = df_sim2[month_columns].sum(axis=1) * df_sim2["tarif d'achat"]
            df_sim2["Taux de rotation"] = (df_sim2[month_columns].sum(axis=1) / df_sim2["stock"]).replace([np.inf, -np.inf], 0).round(2)
            df_sim2["Qté Sim 2"] = df_sim2[month_columns].sum(axis=1)

            remarques_sim2 = []
            for idx, row in df_sim2.iterrows():
                taux = row["Taux de rotation"]
                if taux < 0.5:
                    df_sim2.loc[idx, month_columns] *= 0.7
                    remarques_sim2.append("Quantité réduite : taux < 0.5")
                elif taux > 4:
                    df_sim2.loc[idx, month_columns] *= 1.2
                    remarques_sim2.append("Quantité augmentée : taux > 4")
                else:
                    remarques_sim2.append("")
            df_sim2["Remarque"] = remarques_sim2

        comparatif = df[["référence produit", "désignation"]].copy()
        comparatif["Qté Sim 1"] = df_sim1["Qté Sim 1"]
        comparatif["Montant Sim 1"] = df_sim1["Montant annuel"]
        if "Qté Sim 2" in df_sim2.columns:
            comparatif["Qté Sim 2"] = df_sim2["Qté Sim 2"]
        if "Montant annuel" in df_sim2.columns:
            comparatif["Montant annuel Sim 2"] = df_sim2["Montant annuel"]
        if "Montant Sim 2" in df_sim2.columns:
        comparatif["Écart (€)"] = comparatif["Montant Sim 2"] - comparatif["Montant Sim 1"]
        st.subheader("🔍 Comparatif")
        st.dataframe(comparatif)

        st.subheader("📊 Graphique produit")
        produit = st.selectbox("Produit à afficher", df["référence produit"].unique())
        if produit:
            data_plot = pd.DataFrame({
                "Mois": month_columns * 2,
                "Quantité": list(df_sim1[df_sim1["référence produit"] == produit][month_columns].values[0]) +
                            list(df_sim2[df_sim2["référence produit"] == produit][month_columns].values[0]),
                "Simulation": ["Simulation 1"] * len(month_columns) + ["Simulation 2"] * len(month_columns)
            })
            fig, ax = plt.subplots()
            for sim in data_plot["Simulation"].unique():
                sub = data_plot[data_plot["Simulation"] == sim]
                ax.plot(sub["Mois"], sub["Quantité"], label=sim, marker='o')
            ax.legend()
            st.pyplot(fig)

        def create_pdf(df_export, title):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt=title, ln=True, align="C")
            pdf.ln(10)
            headers = ["référence fournisseur", "référence produit", "désignation", "quantité totale à commander"]
            col_widths = [40, 40, 70, 40]
            for h in headers:
                pdf.cell(col_widths[headers.index(h)], 10, h, border=1)
            pdf.ln()
            for _, row in df_export.iterrows():
                for h in headers:
                    val = str(row[h])[:30]
                    pdf.cell(col_widths[headers.index(h)], 10, val, border=1)
                pdf.ln()
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            pdf.output(temp.name)
            return temp.name

        st.subheader("📄 Bons de commande (PDF)")
        for label, dfx in [("Simulation 1", df_sim1), ("Simulation 2", df_sim2)]:
            df_bon = dfx[["référence fournisseur", "référence produit", "désignation"]].copy()
            df_bon["quantité totale à commander"] = dfx[month_columns].sum(axis=1).astype(int)
            file = create_pdf(df_bon, f"Bon de commande - {label}")
            with open(file, "rb") as f:
                st.download_button(f"Télécharger le PDF - {label}", f.read(), file_name=f"bon_commande_{label.replace(' ', '_')}.pdf")

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_sim1.to_excel(writer, sheet_name="Simulation_Progression", index=False)
            df_sim2.to_excel(writer, sheet_name="Simulation_Objectif", index=False)
            comparatif.to_excel(writer, sheet_name="Comparatif", index=False)
        output.seek(0)
        st.download_button("📥 Télécharger Excel complet", data=output, file_name="forecast_complet.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        st.error(f"Erreur : {e}")
