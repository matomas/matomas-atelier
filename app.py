import streamlit as st
import matplotlib.pyplot as plt
import ezdxf
import io

# --- KONFIGURACE ---
RASTR = 0.625

def vypocitej_rozmer(moduly):
    return round(moduly * RASTR, 3)

# --- WEB ---
st.set_page_config(page_title="Matomas AI Ateliér v0.4", layout="wide")
st.title("🧩 Matomas AI Ateliér - Generátor dispozice")

with st.sidebar:
    st.header("1. Rozměry")
    mod_x = st.slider("Délka (moduly 625mm)", 16, 32, 24)
    mod_y = st.slider("Šířka (moduly 625mm)", 10, 16, 12)
    
    sirka = vypocitej_rozmer(mod_y)
    delka = vypocitej_rozmer(mod_x)
    
    st.header("2. Dispozice")
    pomer_denni = st.slider("Poměr denní zóny (%)", 40, 60, 50) / 100

# VÝPOČET ZÓN
moduly_denni = round((delka * pomer_denni) / RASTR)
delka_denni = moduly_denni * RASTR
delka_nocni = delka - delka_denni

# --- LOGIKA MÍSTNOSTÍ V NOČNÍ ZÓNĚ ---
sirka_chodby = 2 * RASTR # 1.25m
sirka_pokoju = sirka - sirka_chodby

# GRAF
fig, ax = plt.subplots(figsize=(12, 8))

# 1. Hrubá stavba
ax.add_patch(plt.Rectangle((0, 0), sirka, delka, lw=3, edgecolor='black', facecolor='#f8f9fa'))

# 2. Hlavní dělící příčka (Nosná)
ax.plot([0, sirka], [delka_denni, delka_denni], color='black', lw=4)

# 3. Chodba (svislá příčka)
ax.plot([sirka_pokoju, sirka_pokoju], [delka_denni, delka], color='#555', lw=2)

# 4. Koupelna (vodorovná příčka v noční zóně)
vyska_koupelny = 4 * RASTR # 2.5m
ax.plot([0, sirka_pokoju], [delka_denni + vyska_koupelny, delka_denni + vyska_koupelny], color='#555', lw=2)

# --- POPISKY ---
ax.text(sirka/2, delka_denni/2, "OBÝVACÍ POKOJ + KK", ha='center', va='center', fontsize=12, fontweight='bold')
ax.text(sirka_pokoju/2, delka_denni + (vyska_koupelny/2), "KOUPELNA / TM", ha='center', va='center', color='blue')
ax.text(sirka_pokoju/2, (delka + delka_denni + vyska_koupelny)/2, "LOŽNICE", ha='center', va='center')
ax.text(sirka - (sirka_chodby/2), (delka + delka_denni)/2, "CHODBA", ha='center', va='center', rotation=90, fontsize=8)

# Rastr (pomocný)
for x in [i * RASTR for i in range(mod_y + 1)]:
    ax.axvline(x, color='#ddd', lw=0.5)
for y in [i * RASTR for i in range(mod_x + 1)]:
    ax.axhline(y, color='#ddd', lw=0.5)

ax.set_xlim(-0.5, sirka + 0.5)
ax.set_ylim(-0.5, delka + 0.5)
ax.set_aspect('equal')
ax.axis('off')
st.pyplot(fig)

st.info(f"Aktuální konfigurace: Trakt šířky {sirka} m. Všechny vnitřní příčky jsou zarovnány na modul {RASTR} m.")
