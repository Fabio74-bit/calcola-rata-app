import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Calcolatore Rata", layout="centered")

st.title("📊 Calcolatore Rata Finanziamento")

uploaded_file = st.file_uploader("Carica il file Excel", type=["xlsx"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.subheader("📄 Dati dal file:")
    st.dataframe(df)

st.subheader("🧮 Inserisci Parametri Manualmente")
importo = st.number_input("Importo Finanziato (€)", value=10000.0)
tasso_annuo = st.number_input("Tasso Annuo (%)", value=5.0)
durata_mesi = st.slider("Durata (mesi)", min_value=6, max_value=120, value=60)

tasso_mensile = (tasso_annuo / 100) / 12
if tasso_mensile > 0:
    rata = importo * (tasso_mensile / (1 - (1 + tasso_mensile) ** -durata_mesi))
else:
    rata = importo / durata_mesi

st.success(f"💰 Rata mensile: **{rata:,.2f} €**")

if st.checkbox("Mostra piano ammortamento"):
    piano = []
    capitale_residuo = importo
    for mese in range(1, durata_mesi + 1):
        interessi = capitale_residuo * tasso_mensile
        quota_capitale = rata - interessi
        capitale_residuo -= quota_capitale
        piano.append({
            "Mese": mese,
            "Rata": round(rata, 2),
            "Quota Capitale": round(quota_capitale, 2),
            "Interessi": round(interessi, 2),
            "Residuo": round(capitale_residuo, 2)
        })

    df_piano = pd.DataFrame(piano)
    st.dataframe(df_piano)
