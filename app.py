import streamlit as st
import streamlit.components.v1 as components
import requests
import json

st.set_page_config(page_title="Matomas Live API v0.28", layout="wide")

# --- FUNKCE PRO STAŽENÍ DAT Z ČÚZK ---
def stahni_parcelu_cuzk(ku_kod, kmen, pod):
    # Endpoint pro vrstvu Parcely (číslo 17 v RÚIAN MapServeru)
    url = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/17/query"
    
    where_clause = f"KATUZE_KOD={ku_kod} AND KMENOVE_CISLO={kmen}"
    if pod:
        where_clause += f" AND PODODDELENI_CISLA={pod}"
        
    params = {
        "where": where_clause,
        "outFields": "OBJECTID,KATUZE_KOD,KMENOVE_CISLO",
        "returnGeometry": "true",
        "f": "geojson"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "features" in data and len(data["features"]) > 0:
                # GeoJSON polygon je seznam ringů, bereme první (vnější hranici)
                coords = data["features"][0]["geometry"]["coordinates"][0]
                return coords
            else:
                return "Nenalezeno"
        else:
            return f"Chyba serveru: {response.status_code}"
    except Exception as e:
        return f"Chyba připojení: {e}"

# --- FUNKCE PRO PŘEVOD S-JTSK DO 3D NULY ---
def normalizuj_sjtsk(raw_pts):
    if not raw_pts or not isinstance(raw_pts, list): return []
    
    # Najdeme těžiště (bounding box center)
    xs = [p[0] for p in raw_pts]
    ys = [p[1] for p in raw_pts]
    cx = min(xs) + (max(xs) - min(xs)) / 2
    cy = min(ys) + (max(ys) - min(ys)) / 2
    
    # S-JTSK má specifickou orientaci os. Pro začátek to jen posuneme do [0,0].
    # V Three.js pak použijeme X a -Y pro správné zobrazení na rovině Z.
    return [[round(p[0] - cx, 3), round(p[1] - cy, 3)] for p in raw_pts]

# --- UI a SIDEBAR ---
with st.sidebar:
    st.title("📡 Živé napojení ČÚZK")
    st.info("Zadejte parametry podle RÚIAN")
    
    ku_kod = st.text_input("Kód KÚ (např. 707015 pro Nučničky)", value="707015")
    col1, col2 = st.columns(2)
    with col1:
        kmen = st.text_input("Kmenové č.", value="45")
    with col2:
        pod = st.text_input("Pododdělení", value="104")
        
    if st.button("Stáhnout z katastru", type="primary"):
        with st.spinner("Stahuji data z ČÚZK..."):
            vysledek = stahni_parcelu_cuzk(ku_kod, kmen, pod)
            if isinstance(vysledek, list):
                st.session_state['api_data'] = vysledek
                st.success("Polygon úspěšně stažen!")
            else:
                st.error(f"Chyba: {vysledek}")

    st.write("---")
    st.subheader("🛠️ Debugger přijatých dat")
    # Zde uvidíš surová data z API (v S-JTSK), pokud se to povede
    raw_data = st.session_state.get('api_data', [])
    if raw_data:
        st.text_area("S-JTSK souřadnice z API:", value=json.dumps(raw_data), height=150)
        display_pts = normalizuj_sjtsk(raw_data)
    else:
        st.warning("Čekám na stažení dat...")
        display_pts = []

# --- 3D ENGINE ---
st.title("📐 Skutečný model parcely z RÚIAN")

if not display_pts:
    st.info("Zadej parcelu v sidebaru a klikni na 'Stáhnout'.")
else:
    # Generování Three.js kódu pouze pokud máme reálná data
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
        // Osa Y ze S-JTSK jde často opačně, vkládáme jako -Y do 3D prostoru (osa Z)
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
