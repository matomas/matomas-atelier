import streamlit as st
import streamlit.components.v1 as components
import requests
import json

st.set_page_config(page_title="Matomas Live API v0.30", layout="wide")

# --- FUNKCE PRO STAŽENÍ DAT Z ČÚZK ---
def stahni_parcelu_cuzk(ku_kod, kmen, pod):
    # Vrstva 17 = Katastrální parcely
    url = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/17/query"
    
    # Přesné systémové názvy sloupců (ArcGIS vyžaduje přesnost)
    where_clause = f"KATUZE_KOD={ku_kod} AND KMENOVE_CISLO={kmen}"
    
    if pod and pod.strip() != "":
        where_clause += f" AND PODODDELENI_CISLA={pod}"
    else:
        # Pokud parcela nemá lomítko, v databázi je to NULL
        where_clause += " AND PODODDELENI_CISLA IS NULL"
        
    params = {
        "where": where_clause,
        "outFields": "OBJECTID,KATUZE_KOD,KMENOVE_CISLO",
        "returnGeometry": "true",
        "f": "geojson"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            
            # Odchytí vnitřní SQL chyby databáze
            if "error" in data:
                return f"ArcGIS Chyba: {data['error'].get('message', 'Neznámý problém')}"
            
            if "features" in data and len(data["features"]) > 0:
                # GeoJSON polygon (stahujeme první nalezený obrys)
                coords = data["features"][0]["geometry"]["coordinates"][0]
                return coords
            else:
                return "Nenalezeno - Parcela v tomto KÚ neexistuje (nebo jde o stavební parcelu 'st.')."
        else:
            return f"Výpadek ČÚZK serveru: HTTP {response.status_code}"
    except Exception as e:
        return f"Chyba sítě/připojení: {e}"

# --- NORMALIZACE S-JTSK DO 3D NULY ---
def normalizuj_sjtsk(raw_pts):
    if not raw_pts or not isinstance(raw_pts, list): return []
    # Vycentrujeme obrovská záporná čísla do středu [0,0]
    xs = [p[0] for p in raw_pts]
    ys = [p[1] for p in raw_pts]
    cx = min(xs) + (max(xs) - min(xs)) / 2
    cy = min(ys) + (max(ys) - min(ys)) / 2
    
    return [[round(p[0] - cx, 3), round(p[1] - cy, 3)] for p in raw_pts]

# --- UI a SIDEBAR ---
with st.sidebar:
    st.title("📡 Živé napojení ČÚZK")
    
    ku_kod = st.text_input("Kód KÚ (např. 707015 pro Nučničky)", value="707015")
    col1, col2 = st.columns(2)
    with col1:
        kmen = st.text_input("Kmenové č.", value="45")
    with col2:
        pod = st.text_input("Pododdělení", value="104")
        
    if st.button("Stáhnout parcelu", type="primary"):
        with st.spinner("Komunikuji se státní databází..."):
            vysledek = stahni_parcelu_cuzk(ku_kod, kmen, pod)
            if isinstance(vysledek, list):
                st.session_state['api_data'] = vysledek
                st.success("Data byla úspěšně stažena!")
            else:
                st.error(f"Chyba: {vysledek}")

    st.write("---")
    st.subheader("🛠️ Debugger přijatých dat")
    raw_data = st.session_state.get('api_data', [])
    if raw_data:
        st.text_area("Live data S-JTSK:", value=json.dumps(raw_data), height=150)
        display_pts = normalizuj_sjtsk(raw_data)
    else:
        st.warning("Zatím nemám data. Klikni na 'Stáhnout parcelu'.")
        display_pts = []

# --- 3D ENGINE ---
st.title("📐 Skutečný model parcely z RÚIAN (v0.30)")

if not display_pts:
    st.info("Zadej údaje v sidebaru a stáhni data z katastru.")
else:
    three_js_code = f"""
    <div id="container" style="width: 100%; height: 700px; background: #ffffff; border: 1px solid #ddd; border-radius: 8px;"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script>
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xfafafa);
        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 700, 0.1, 5000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, 700);
        document.getElementById('container').appendChild(renderer.domElement);

        const pts = {display_pts};

        // KRESLENÍ POLYGONU
        const shape = new THREE.Shape();
        // S-JTSK má jinou orientaci os, překlápíme pro 3D zobrazení (-Y)
        shape.moveTo(pts[0][0], -pts[0][1]);
        for(let i=1; i<pts.length; i++) {{
            shape.lineTo(pts[i][0], -pts[i][1]);
        }}
        
        const parcelGeom = new THREE.ShapeGeometry(shape);
        const parcelMat = new THREE.MeshPhongMaterial({{ color: 0xc8e6c9, side: THREE.DoubleSide }});
        const parcel = new THREE.Mesh(parcelGeom, parcelMat);
        parcel.rotation.x = -Math.PI / 2;
        scene.add(parcel);

        // KRESLENÍ OSTRÉ ČERVENÉ HRANICE
        const linePts = pts.map(p => new THREE.Vector3(p[0], 0.1, -p[1]));
        const borderGeom = new THREE.BufferGeometry().setFromPoints(linePts);
        const border = new THREE.Line(borderGeom, new THREE.LineBasicMaterial({{ color: 0xd32f2f, linewidth: 3 }}));
        scene.add(border);

        // DŮM - Zlatý standard
        const house = new THREE.Mesh(
            new THREE.BoxGeometry(6.25, 2.7, 12.5),
            new THREE.MeshPhongMaterial({{ color: 0x1976d2, transparent: true, opacity: 0.9 }})
        );
        house.position.set(0, 1.35, 0);
        house.castShadow = true;
        scene.add(house);

        // ZÁKLADNÍ MŘÍŽKA A SVĚTLO
        scene.add(new THREE.GridHelper(200, 200, 0xdddddd, 0xeeeeee));
        scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        const sun = new THREE.DirectionalLight(0xffffff, 0.5);
        sun.position.set(50, 100, 50);
        scene.add(sun);

        camera.position.set(50, 80, 50);
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.target.set(0, 0, 0);
        controls.update();

        function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
        animate();
    </script>
    """
    components.html(three_js_code, height=720)
