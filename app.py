import streamlit as st
import matplotlib.pyplot as plt
import ezdxf
import io

# --- KONFIGURACE ---
RASTR = 0.625

def vypocitej_rozmer(moduly):
    return round(moduly * RASTR, 3)

# --- WEB ---
st.set_page_config(page_title="Matomas AI Ateliér v0.3", layout="wide")
st.title("🏠 Matomas AI Ateliér - Zónování prostoru")

with st.sidebar:
    st.header("1. Rozměry obálky")
    mod_x = st.slider("Délka (moduly 625mm)", 10, 32, 24)
    mod_y = st.slider("Šířka (moduly 625mm)", 8, 16, 12)
    
    sirka = vypocitej_rozmer(mod_y)
    delka = vypocitej_rozmer(mod_x)
    
    st.header("2. Dispozice")
    pomer_denni = st.slider("Velikost denní zóny (%)", 30, 70, 50) / 100

# VÝPOČET PŘÍČKY
# Příčka musí sedět na rastru
delka_denni_raw = delka * pomer_denni
moduly_denni = round(delka_denni_raw / RASTR)
delka_denni = moduly_denni * RASTR

# GRAF
fig, ax = plt.subplots(figsize=(12, 7))

# Obvod (Hrubá stavba)
rect = plt.Rectangle((0, 0), sirka, delka, linewidth=3, edgecolor='black', facecolor='#f0f0f0', label="Hrubá stavba")
ax.add_patch(rect)

# Dělící příčka (Zlatý standard - nosná/akustická)
ax.plot([0, sirka], [delka_denni, delka_denni], color='red', lw=4, label="Hlavní dělící příčka")

# Popisky zón
ax.text(sirka/2, delka_denni/2, "DENNÍ ZÓNA\n(Obývací pokoj + KK)", ha='center', va='center', fontweight='bold')
ax.text(sirka/2, (delka + delka_denni)/2, "NOČNÍ ZÓNA\n(Ložnice + Koupelna)", ha='center', va='center', fontweight='bold')

# Rastr
for x in [i * RASTR for i in range(mod_y + 1)]:
    ax.axvline(x, color='white', lw=0.8, ls='-')
for y in [i * RASTR for i in range(mod_x + 1)]:
    ax.axhline(y, color='white', lw=0.8, ls='-')

ax.set_xlim(-0.5, sirka + 0.5)
ax.set_ylim(-0.5, delka + 0.5)
ax.set_aspect('equal')
plt.legend(loc='upper right')
st.pyplot(fig)

# STATISTIKA
st.subheader("Parametry zón")
c1, c2, c3 = st.columns(3)
c1.metric("Plocha denní zóny", f"{round(sirka * delka_denni, 2)} m²")
c2.metric("Plocha noční zóny", f"{round(sirka * (delka - delka_denni), 2)} m²")
c3.metric("Celková užitná plocha", f"{round(sirka * delka, 2)} m²")
