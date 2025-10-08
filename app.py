import streamlit as st
import pandas as pd

st.set_page_config(page_title="Calcolo Rata da Excel", layout="centered")
st.title("📊 Calcolatore Rata Finanziamento da Excel")

# Carica file Excel fisso (in locale o nel repo)
file_path = "CalcolaRata_Fin.xlsx"
xls = pd.ExcelFile(file_path)

df_coeff = xls.parse("Coefficienti")

# Mostra dati
with st.expander("📄 Visualizza tabella coefficienti"):
    st.dataframe(df_coeff)

# Input utente
st.subheader("📥 Parametri del finanziamento")

finanziaria = st.selectbox("Scegli Finanziaria", df_coeff["Finanziaria"].unique())
durata = st.selectbox("Scegli Durata (mesi)", sorted(df_coeff["Durata"].unique()))
importo = st.number_input("Inserisci Importo (€)", value=5000.0, step=100.0)

# Filtra il coefficiente corretto
filtro = df_coeff[
    (df_coeff["Finanziaria"] == finanziaria) &
    (df_coeff["Durata"] == durata) &
    (df_coeff["FasciaMin"] <= importo) &
    (df_coeff["FasciaMax"] >= importo)
]

if filtro.empty:
    st.error("❌ Nessun coefficiente trovato per i parametri selezionati.")
else:
    coeff = filtro.iloc[0]["Coeff_percent"]
    rata = importo * (coeff / 100)

    st.success(f"💰 Rata mensile: **{rata:,.2f} €**")
    st.info(f"📈 Coefficiente applicato: {coeff} per {durata} mesi con {finanziaria}")
