import streamlit as st
import ezdxf
import io

# --- KONSTRUKČNÍ LOGIKA DLE TVÉHO ZADÁNÍ ---
def vypocitej_projekt(sirka, delka):
    plocha = sirka * delka
    obvod = 2 * (sirka + delka)
    
    # 1. Spodní stavba
    beton_pasy = obvod * 0.4 * 0.2  # pasy 400x200
    zb_ks = (obvod / 0.5) * 2       # 2 šáry ztraceného bednění 250mm
    beton_vypln_zb = zb_ks * 0.02   # orientační výplň na kus
    beton_deska = plocha * 0.15     # deska 150mm
    
    # Výztuž (sítě 8/100/100 2x + 20% rezerva na pruty)
    ocel_kg = (plocha * 7.9 * 1.3) + (obvod * 5)
    
    # 2. Svislé konstrukce
    plocha_sten = obvod * 2.7       # výška 2.7m
    beton_tvarovky_ks = plocha_sten / 0.125 # tvarovky 500x250
    beton_vypln_sten = plocha_sten * 0.15 # výplň betonem C25/30
    
    # 3. Strop a Střecha
    beton_strop = plocha * 0.15     # monolit 150mm
    fosny_m = (plocha / 0.4) * 1.1  # fošny á 400mm s prořezem
    osb_m2 = plocha * 2             # 2 vrstvy 18mm
    
    # 4. Izolace
    eps_fasada_m2 = plocha_sten
    eps_podlaha_m3 = plocha * 0.16
    vata_strop_m2 = plocha
    
    # --- Ceny (orientační pro rok 2026) ---
    c_beton = 3300  # C25/30 za m3
    c_ocel = 32     # za kg
    c_eps = 2500    # za m3
    
    cena_material = (beton_pasy + beton_deska + beton_vypln_sten + beton_strop) * c_beton
    cena_material += ocel_kg * c_ocel
    
    # Celková cena (materiál + práce + tvých 15% rezerva)
    cena_celkem = cena_material * 1.8 # koeficient pro práci a režii
    
    return {
        "Cena celkem": f"{round(cena_celkem):,} Kč",
        "Beton celkem (m3)": round(beton_pasy + beton_deska + beton_vypln_sten + beton_strop, 1),
        "Ocel celkem (kg)": round(ocel_kg),
        "Ztracené bednění (ks)": round(zb_ks),
        "Fošny na střechu (m)": round(fosny_m)
    }

# --- WEBOWÉ ROZHRANÍ ---
st.set_page_config(page_title="Matomas AI Ateliér", layout="wide")

st.title("🏗️ Matomas AI Ateliér - Zlatý Standard")
st.write("Parametrický návrh domu v rastru 625 mm s přesným technickým výpočtem.")

with st.sidebar:
    st.header("Nastavení rozměrů")
    # Posuvníky nastavené na násobky 0.625 m
    mod_x = st.slider("Počet modulů - délka", 10, 32, 20) # 6.25m až 20m
    mod_y = st.slider("Počet modulů - šířka", 8, 16, 10)  # 5m až 10m
    
    sirka_m = mod_y * 0.625
    delka_m = mod_x * 0.625
    
    st.info(f"Rozměr hrubé stavby: {sirka_m} x {delka_m} m")
    st.info(f"Vnější rozměr (zateplení 180mm): {sirka_m + 0.36} x {delka_m + 0.36} m")

# Výpočet
vysledky = vypocitej_projekt(sirka_m, delka_m)

# Zobrazení výsledků
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Ekonomický a materiálový přehled")
    # Zobrazení metrik v pěkné mřížce
    c1, c2, c3 = st.columns(3)
    for i, (k, v) in enumerate(vysledky.items()):
        if i < 3:
            with [c1, c2, c3][i]: st.metric(k, v)
        else:
            st.write(f"**{k}:** {v}")

with col2:
    st.subheader("Technická specifikace")
    st.markdown("""
    * **Základy:** Pasy 400x200 + ZB 250mm
    * **Konstrukce:** Betonové tvarovky + monolitický strop
    * **Střecha:** Fošnový systém, 2x OSB, asfaltové pásy, kačírek
    * **Izolace:** Fasáda 180mm EPS, Podlaha 160mm EPS, Strop 240mm vata
    """)

# --- GENEROVÁNÍ DXF ---
if st.button("💾 Stáhnout DXF Studii"):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Body v milimetrech pro CAD
    s = sirka_m * 1000
    d = delka_m * 1000
    
    # Vnější obvod hrubé stavby
    msp.add_lwpolyline([(0, 0), (s, 0), (s, d), (0, d), (0, 0)], dxfattribs={'color': 7})
    
    # Uložení do bufferu pro stažení
    out = io.StringIO()
    doc.write(out)
    
    st.download_button(
        label="Klikněte pro stažení souboru .dxf",
        data=out.getvalue(),
        file_name="studie_matomas.dxf",
        mime="application/dxf"
    )