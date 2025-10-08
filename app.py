import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Calcola Rata", page_icon="💶", layout="centered")

st.title("Calcola Rata")
st.caption("BNP • GRENKE • IFIS — coefficienti pre-caricati, con possibilità di aggiornare da file.")

# ----------------------
# Default coefficient tables (percent values)
# ----------------------

# BNP (ex VFL1), Mensile, Dilazione=0
BNP_BANDS = [(1000, 4999), (5000, 49999), (50000, 300000)]
BNP_DURS  = [24, 36, 48, 60, 72]
BNP_COEFF = {
    24: [4.426, 4.363, 4.351],
    36: [3.057, 2.993, 2.980],
    48: [2.374, 2.309, 2.296],
    60: [1.925, 1.892, 1.872],
    72: [1.653, 1.619, 1.599],
}

# GRENKE (ELIOS 2025), Mensile
GRENKE_BANDS = [(500, 2500), (2501, 5000), (5001, 12000), (12001, 25000), (25001, 50000), (50001, 100000)]
GRENKE_DURS  = [24, 36, 48, 60, 72]
GRENKE_COEFF = {
    24: [4.320, 4.317, 4.316, 4.311, 4.300, 4.298],
    36: [2.956, 2.933, 2.932, 2.929, 2.930, 2.928],
    48: [2.290, 2.266, 2.265, 2.264, 2.249, 2.247],
    60: [1.889, 1.860, 1.859, 1.858, 1.845, 1.844],
    72: [1.638, 1.602, 1.601, 1.599, 1.583, 1.581],
}

# IFIS (Mensile, Anticipato=SI, RV=1) — fasce derivate dai punti "VALORE BENE": 2500, 10000, 25000, 100000, 300000
IFIS_BANDS = [(1000, 2500), (2501, 10000), (10001, 25000), (25001, 100000), (100001, 300000)]
IFIS_DURS  = [36, 48, 60, 72]
# Coefficienti di default (se non troviamo l'Excel nel repo)
IFIS_COEFF = {
    36: [3.0189, 3.0691, 2.3500, 2.3864, 1.9778],  # esempio
    48: [2.3500, 2.3864, 2.3643, 2.3275, 2.3759],  # esempio
    60: [1.9892, 1.9612, 1.9778, 1.9497, 1.9600],  # esempio
    72: [1.6956, 1.7180, 1.6838, 1.7064, 1.7015],  # esempio
}

# ----------------------
# Helpers
# ----------------------
def find_band_index(bands, imponibile):
    for i, (lo, hi) in enumerate(bands):
        if lo <= imponibile <= hi:
            return i
    return None

def rate_from_coeff(imponibile, coeff_percent, tipo):
    # tipo: "Mensile" or "Trimestrale" — trimestrale = mensile*3
    monthly = imponibile * coeff_percent / 100.0
    return (monthly*3.0) if (tipo == "Trimestrale") else monthly, monthly

def implied_imponibile_from_rate(rate_value, coeff_percent, tipo):
    # reverse: se trimestrale, prima riportiamo a mensile
    if coeff_percent <= 0:
        return None
    monthly_rate = rate_value/3.0 if (tipo == "Trimestrale") else rate_value
    return (monthly_rate * 100.0) / coeff_percent

def make_table(fin_list, imponibile, durata, tipo, tables):
    rows = []
    for fin in fin_list:
        bands, durs, coeffs = tables[fin]
        if durata not in durs:
            rows.append({"Finanziaria": fin, "Tipo rata": tipo, "Durata (mesi)": durata,
                         "Rata (€)": None, "Rata mensile (€)": None})
            continue
        band_idx = find_band_index(bands, imponibile)
        if band_idx is None:
            rows.append({"Finanziaria": fin, "Tipo rata": tipo, "Durata (mesi)": durata,
                         "Rata (€)": None, "Rata mensile (€)": None})
            continue
        coeff_percent = coeffs[durata][band_idx] if isinstance(coeffs, dict) else coeffs[band_idx]
        rata, mensile = rate_from_coeff(imponibile, coeff_percent, tipo)
        rows.append({"Finanziaria": fin, "Tipo rata": tipo, "Durata (mesi)": durata,
                     "Rata (€)": round(rata, 2), "Rata mensile (€)": round(mensile, 2)})
    return pd.DataFrame(rows)

def make_reverse_table(fin_list, rate_value, durata, tipo, tables):
    rows = []
    for fin in fin_list:
        bands, durs, coeffs = tables[fin]
        if durata not in durs:
            rows.append({"Finanziaria": fin, "Tipo rata": tipo, "Durata (mesi)": durata,
                         "Imponibile stimato (€)": None})
            continue
        candidates = []
        for band_idx, (lo, hi) in enumerate(bands):
            coeff_percent = coeffs[durata][band_idx] if isinstance(coeffs, dict) else coeffs[band_idx]
            imp = implied_imponibile_from_rate(rate_value, coeff_percent, tipo)
            if imp is not None and lo <= imp <= hi:
                candidates.append(imp)
        imp_final = round(min(candidates), 2) if candidates else None
        rows.append({"Finanziaria": fin, "Tipo rata": tipo, "Durata (mesi)": durata,
                     "Imponibile stimato (€)": imp_final})
    return pd.DataFrame(rows)

def df_to_tables(df):
    # df colonne: Durata, FasciaMin, FasciaMax, Coeff_percent
    durs = sorted(df["Durata"].unique().tolist())
    bands_df = df[["FasciaMin","FasciaMax"]].drop_duplicates().sort_values(["FasciaMin","FasciaMax"])
    bands = [tuple(x) for x in bands_df.to_numpy()]
    coeff = {}
    for d in durs:
        row = df[df["Durata"]==d].sort_values(["FasciaMin","FasciaMax"])
        coeff[d] = row["Coeff_percent"].tolist()
    return bands, durs, coeff

# ----------------------
# Uploader in sidebar (opzionale)
# ----------------------
st.sidebar.header("Aggiorna coefficienti (opzionale)")
uploaded_bnp = st.sidebar.file_uploader("BNP (CSV con colonne: Durata,FasciaMin,FasciaMax,Coeff_percent)", type=["csv"])
uploaded_grk = st.sidebar.file_uploader("GRENKE (CSV con colonne: Durata,FasciaMin,FasciaMax,Coeff_percent)", type=["csv"])
uploaded_ifis = st.sidebar.file_uploader("IFIS (CSV/Excel con colonne: Durata,FasciaMin,FasciaMax,Coeff_percent)", type=["csv","xlsx","xls"])

def override_from_upload(default_bands, default_durs, default_coeff, file, engine="csv"):
    if not file:
        return default_bands, default_durs, default_coeff
    df = pd.read_csv(file) if engine == "csv" else pd.read_excel(file)
    return df_to_tables(df)

# ----------------------
# Tabelle base (default)
# ----------------------
BNP_tbl    = (BNP_BANDS, BNP_DURS, BNP_COEFF)
GRENKE_tbl = (GRENKE_BANDS, GRENKE_DURS, GRENKE_COEFF)
IFIS_tbl   = (IFIS_BANDS, IFIS_DURS, IFIS_COEFF)

# ----------------------
# Autocaricamento da Excel nel repo (se presente)
# ----------------------
EXCEL_PATH = "CalcolaRata_Fin.xlsx"   # metti il file nella root del repo

if os.path.exists(EXCEL_PATH):
    try:
        full = pd.read_excel(EXCEL_PATH, sheet_name="Coefficienti")
        # se nel file c'è RV, filtra IFIS a RV=1
        if "RV" in full.columns:
            full = full[(full["Finanziaria"]!="IFIS") | (full["RV"]==1)]

        # Per ciascuna finanziaria sovrascrivi le tabelle base, se disponibili
        for fin in ["BNP", "GRENKE", "IFIS"]:
            sub = full[full["Finanziaria"]==fin][["Durata","FasciaMin","FasciaMax","Coeff_percent"]]
            if not sub.empty:
                if fin == "BNP":
                    BNP_tbl = df_to_tables(sub)
                elif fin == "GRENKE":
                    GRENKE_tbl = df_to_tables(sub)
                elif fin == "IFIS":
                    IFIS_tbl = df_to_tables(sub)
        st.success("Coefficienti caricati da CalcolaRata_Fin.xlsx")
    except Exception as e:
        st.warning(f"Non riesco a leggere {EXCEL_PATH}: {e}")

# ----------------------
# Upload override (sovrascrive quanto caricato da Excel per quella specifica finanziaria)
# ----------------------
BNP_tbl    = override_from_upload(*BNP_tbl, uploaded_bnp, "csv")
GRENKE_tbl = override_from_upload(*GRENKE_tbl, uploaded_grk, "csv")
if uploaded_ifis:
    IFIS_tbl = override_from_upload(*IFIS_tbl, uploaded_ifis, "csv" if uploaded_ifis.name.lower().endswith(".csv") else "excel")

TABLES = {
    "BNP": BNP_tbl,
    "GRENKE": GRENKE_tbl,
    "IFIS": IFIS_tbl,
}

# ----------------------
# Inputs (default: 60 mesi, Trimestrale)
# Durate mostrate = unione di tutte le durate disponibili nelle tabelle caricate
# ----------------------
ALL_DURS = sorted(set().union(*[set(tbl[1]) for tbl in TABLES.values()] or {24,30,36,48,60,72}))
default_idx = ALL_DURS.index(60) if 60 in ALL_DURS else 0

col1, col2, col3 = st.columns(3)
with col1:
    imponibile = st.number_input("Imponibile (€)", min_value=0.0, step=100.0, value=15000.0, format="%.2f")
with col2:
    durata = st.selectbox("Durata (mesi)", ALL_DURS, index=default_idx)
with col3:
    tipo = st.selectbox("Tipo rata", ["Mensile","Trimestrale"], index=1)

st.subheader("Calcola rata")
fin_list = ["BNP","GRENKE","IFIS"]
df_rata = make_table(fin_list, imponibile, durata, tipo, TABLES)

# Evidenzia la rata mensile minima
min_val = df_rata["Rata mensile (€)"].min(skipna=True)
def highlight_min(s):
    return ["background-color: #C6EFCE; font-weight: 700" if (v==min_val and pd.notnull(v)) else "" for v in s]

st.dataframe(df_rata.style.apply(highlight_min, subset=["Rata mensile (€)"]), use_container_width=True)

st.divider()

st.subheader("Calcola imponibile da rata")
rate_value = st.number_input("Rata (€)", min_value=0.0, step=10.0, value=450.0, format="%.2f")
df_imp = make_reverse_table(fin_list, rate_value, durata, tipo, TABLES)
st.dataframe(df_imp, use_container_width=True)

st.caption("Suggerimento: su iPad, aggiungi questa pagina alla schermmata Home (Condividi → Aggiungi a Home).")
