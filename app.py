import streamlit as st
import ezdxf
import io
import matplotlib.pyplot as plt

# --- KONFIGURACE KONSTRUKCÍ ---
STAVEBNI_SYSTEMY = {
    "Zlatý Standard (Monolit)": {
        "zed_tloustka": 0.250, 
        "zatepleni": 0.180, 
        "cena_m2": 55000,
        "popis": "Betonové tvarovky, armování, monolitický strop. Maximální tuhost."
    },
    "Cihla (Jednovrstvá)": {
        "zed_tloustka": 0.440, 
        "zatepleni": 0.0, 
        "cena_m2": 58000,
        "popis": "Broušená cihla bez zateplení. Klasická cesta."
    },
    "Dřevostavba (2by4)": {
        "zed_tloustka": 0.140, 
        "zatepleni": 0.200, 
        "cena_m2": 48000,
        "popis": "Lehký dřevěný skelet. Rychlá stavba, nízká akumulace."
    }
}

def vypocitej_projekt(sirka, delka, system_name):
    sys = STAVEBNI_SYSTEMY[system_name]
    plocha = sirka * delka
    obvod = 2 * (sirka + delka)
    
    # Výpočet ceny na základě plochy a zvoleného systému
    cena_zakladni = plocha * sys["cena_m2"]
    
    # Technické detaily (zjednodušeně pro demo)
    beton_m3 = (plocha * 0.15) + (obvod * 0.4 * 0.2)
    ocel_kg = (plocha * 7.9 * 1.3)
    
    return {
        "Cena celkem": f"{round(cena_zakladni):,} Kč",
        "Beton (m3)": round(beton_m3, 1),
        "Ocel (kg)": round(ocel_kg),
        "Vnější rozměr": f"{sirka + 2*sys['zatepleni']:.2f} x {delka + 2*sys['zatepleni']:.2f} m"
    }

# --- WEBOWÉ ROZHRANÍ ---
st.set_page_config(page_title="Matomas AI Ateliér", layout="wide")

st.title("🏗️ Matomas AI Ateliér - verze 0.2")

with st.sidebar:
    st.header("1. Parametry domu")
    mod_x = st.slider("Délka (modul 625mm)", 10, 32, 20)
    mod_y = st.slider("Šířka (modul 625mm)", 8, 16, 10)
    
    sirka = mod_y * 0.625
    delka = mod_x * 0.625
    
    st.header("2. Konstrukce")
    system_choice = st.selectbox("Vyberte systém", list(STAVEBNI_SYSTEMY.keys()))
    st.caption(STAVEBNI_SYSTEMY[system_choice]["popis"])

# Data a výpočty
vysledky = vypocitej_projekt(sirka, delka, system_choice)

# --- VIZUALIZACE PŮDORYSU ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Náhled půdorysu (Hrubá stavba)")
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Vnější obrys
    rect = plt.Rectangle((0, 0), sirka, delka, linewidth=3, edgecolor='black', facecolor='none')
    ax.add_patch(rect)
    
    # Rastr 625mm (jemné linky)
    for x in [i * 0.625 for i in range(int(sirka/0.625) + 1)]:
        ax.axvline(x, color='gray', lw=0.5, ls='--')
    for y in [i * 0.625 for i in range(int(delka/0.625) + 1)]:
        ax.axhline(y, color='gray', lw=0.5, ls='--')
        
    ax.set_xlim(-1, sirka + 1)
    ax.set_ylim(-1, delka + 1)
    ax.set_aspect('equal')
    ax.set_title(f"Hrubý rozměr: {sirka} x {delka} m")
    st.pyplot(fig)

with col2:
    st.subheader("Ekonomika a technika")
    c1, c2 = st.columns(2)
    c1.metric("Odhadovaná cena", vysledky["Cena celkem"])
    c2.metric("Vnější rozměr s fasádou", vysledky["Vnější rozměr"])
    
    st.write("---")
    st.write(f"**Materiálový odhad pro {system_choice}:**")
    st.write(f"- Beton: {vysledky['Beton (m3)']} m3")
    st.write(f"- Ocel: {vysledky['Ocel (kg)']} kg")

# --- DXF EXPORT ---
if st.button("💾 Exportovat DXF studii"):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    s_mm, d_mm = sirka * 1000, delka * 1000
    msp.add_lwpolyline([(0, 0), (s_mm, 0), (s_mm, d_mm), (0, d_mm), (0, 0)], dxfattribs={'color': 7})
    
    out = io.StringIO()
    doc.write(out)
    st.download_button("Klikněte pro stažení DXF", data=out.getvalue(), file_name="studie.dxf")
