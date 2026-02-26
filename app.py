import streamlit as st
import streamlit.components.v1 as components
import requests
import json

st.set_page_config(page_title="Matomas Live API v0.32", layout="wide")

# --- FUNKCE PRO STAŽENÍ DAT Z ČÚZK ---
def stahni_parcelu_cuzk(ku_kod, kmen, pod):
    url = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/5/query"
    
    where_clause = f"katastralniuzemi={ku_kod} AND kmenovecislo={kmen}"
    if pod and pod.strip() != "":
        where_clause += f" AND poddelenicisla={pod}"
    else:
        where_clause += " AND poddelenicisla IS NULL"
        
    params = {
        "where": where_clause,
        "outFields": "objectid",
        "returnGeometry": "true",
        "outSR": "5514", # KLÍČOVÉ: Vynutí výstup v metrech (S-JTSK)
        "f": "json"      # Esri JSON je pro metrické systémy spolehlivější
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                return f"ArcGIS Chyba: {data['error'].get('message', '')}"
            
            if "features" in data and len(data["features"]) > 0:
                # Esri JSON ukládá geometrii do pole 'rings'
                coords = data["features"][0]["geometry"]["rings"][0]
                return coords
            else:
                return "Nenalezeno."
        else:
            return f"Výpadek serveru: HTTP {response.status_code}"
    except Exception as e:
        return f"Chyba sítě: {e}"

# --- NORMALIZACE A VÝPOČET ROZMĚRŮ ---
def normalizuj_sjtsk(raw_pts):
    if not raw_pts: return [], 0, 0
    xs = [p[0] for p in raw_pts]
    ys = [p[1] for p in raw_pts]
    
    cx = min(xs) + (max(xs) - min(xs)) / 2
    cy = min(ys) + (max(ys) - min(ys)) / 2
    
    sirka = max(xs) - min(xs)
    delka = max(ys) - min(ys)
    
    norm_pts = [[round(p[0] - cx, 3), round(p[1] - cy, 3)] for p in raw_pts]
    return norm_pts, sirka, delka

# --- UI a SIDEBAR ---
with st.sidebar:
    st.title("📡 Živé napojení ČÚZK")
    
    ku_kod = st.text_input("Kód KÚ (např. 768031)", value="768031")
    col1, col2 = st.columns(2)
    with col1:
        kmen = st.text_input("Kmenové č.", value="45")
    with col2:
        pod = st.text_input("Pododdělení", value="104")
        
    if st.button("Stáhnout parcelu", type="primary"):
        with st.spinner("Stahuji a přepočítávám na metry..."):
            vysledek = stahni_parcelu_cuzk(ku_kod, kmen, pod)
            if isinstance(vysledek, list):
                st.session_state['api_data'] = vysledek
                st.success("Bingo! Data stažena v metrech.")
            else:
                st.error(f"Chyba: {vysledek}")

    st.write("---")
    st.subheader("🛠️ Diagnostika")
    raw_data = st.session_state.get('api_data', [])
    
    if raw_data:
        display_pts, sirka, delka = normalizuj_sjtsk(raw_data)
        st.metric("Počet lomových bodů", len(display_pts))
        st.write(f"**Reálné rozměry:** {sirka:.1f} m × {delka:.1f} m")
    else:
        display_pts = []

# --- 3D ENGINE ---
st.title("📐 Digitální dvojče z RÚIAN (v0.32)")

if not display_pts:
    st.info("Klikni na 'Stáhnout parcelu'.")
else:
    three_
