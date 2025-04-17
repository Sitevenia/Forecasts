
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Diagnostic Forecast", layout="wide")
st.title("🔍 Diagnostic de chargement du fichier Excel")

uploaded_file = st.file_uploader("📁 Charger votre fichier Excel", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Tableau final")
        st.success("✅ Fichier chargé avec succès.")
        st.write("### 📋 Colonnes détectées :")
        st.write(df.columns.tolist())
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement : {e}")
else:
    st.info("Veuillez charger un fichier pour commencer.")
