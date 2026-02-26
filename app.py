import streamlit as st
import matplotlib.pyplot as plt
import io

# --- KONFIGURACE ---
RASTR = 0.625
VYSKA_NP = 2.70
TL_STROP = 0.25

# --- WEB ---
st.set_page_config(page_title="Matomas 3D Ateliér", layout="wide")
st.title("🧊 Matomas AI - 3D Generátor")

with st.sidebar:
    st.header("1. Geometrie")
    mod_x = st.slider("Délka (moduly)", 10, 32, 20)
    mod_y = st.slider("Šířka (moduly)", 8, 16, 10)
    
    sirka = round(mod_y * RASTR, 3)
    delka = round(mod_x * RASTR, 3)
    
    st.header("2. Vizualizace")
    view_type = st.radio("Zobrazení", ["3D Model (Hmotový)", "2D Půdorys"])

if view_type == "2D Půdorys":
    # (Zde zůstává tvůj kód pro matplotlib graf z minula)
    fig, ax = plt.subplots()
    ax.add_patch(plt.Rectangle((0, 0), sirka, delka, color='gray', alpha=0.3))
    ax.set_aspect('equal')
    st.pyplot(fig)

else:
    # --- JEDNODUCHÝ 3D NÁHLED (SVG ISOMETRIE) ---
    # Skutečné 3D (Three.js) vyžaduje více souborů, pro MVP uděláme izometrický náhled
    st.subheader("Interaktivní 3D hmota (Beta)")
    
    # Tady simulujeme 3D prostorový vjem
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')
    
    # Definice boxu (stěny)
    x = [0, sirka, sirka, 0, 0]
    y = [0, 0, delka, delka, 0]
    z_bot = [0, 0, 0, 0, 0]
    z_top = [VYSKA_NP, VYSKA_NP, VYSKA_NP, VYSKA_NP, VYSKA_NP]
    
    # Vykreslení hran domu
    ax.plot(x, y, z_bot, color='black', lw=2)
    ax.plot(x, y, z_top, color='black', lw=2)
    for i in range(4):
        ax.plot([x[i], x[i]], [y[i], y[i]], [0, VYSKA_NP], color='black', lw=2)
    
    # Střecha (tvůj fošnový systém)
    ax.plot_surface([[0, sirka], [0, sirka]], [[0, 0], [delka, delka]], 
                    [[VYSKA_NP, VYSKA_NP], [VYSKA_NP, VYSKA_NP]], alpha=0.2, color='blue')

    ax.set_xlabel('Šířka (m)')
    ax.set_ylabel('Délka (m)')
    ax.set_zlabel('Výška (m)')
    ax.set_zlim(0, 5)
    st.pyplot(fig)

st.success(f"Objem domu: {round(sirka * delka * VYSKA_NP, 1)} m3 připraven k exportu.")
