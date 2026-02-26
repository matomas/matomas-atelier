import streamlit as st
import streamlit.components.v1 as components
import requests
import json

st.set_page_config(page_title="Matomas Live API v0.31", layout="wide")

# --- FUNKCE PRO STAŽENÍ DAT Z ČÚZK ---
def stahni_parcelu_cuzk(ku_kod, kmen, pod):
    # Vrstva 5 = Parcely v Prohlížecí službě RÚIAN
    url = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/5/query"
    
    # Přesné systémové názvy sloupců podle dokumentace RÚIAN (Layer 5)
    where_clause = f"katastralniuzemi={ku_kod} AND kmenovecislo={kmen}"
    
    if pod and pod.strip() != "":
        where_clause += f" AND poddelenicisla={pod}"
    else:
        where_clause += " AND poddelenicisla IS NULL"
        
    params = {
        "where": where_clause,
        "outFields": "objectid,katastralniuzemi,kmenovecislo,poddelenicisla",
        "returnGeometry": "true",
        "f": "geojson"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        debug_url = response.url # Záchranné lano pro kontrolu
        
        if response.status_code == 200:
            data = response.json()
            
            # Odchytí SQL chybu uvnitř JSONu
            if "error" in data:
                return f"ArcGIS Chyba: {data['error'].get('message', 'Neznámý problém')} | URL: {debug_url}"
            
            if "features" in data and len(data["features"]) > 0:
                # Vytáhneme vnější hranici polygonu
                coords = data["features"][0]["geometry"]["coordinates"][0]
                return {"coords": coords, "url": debug_url}
            else:
                return f"Nenalezeno. Parcela neexistuje. (Zkus případně Stavební parcelu). URL: {debug_url}"
        else:
            return f"Výpadek serveru ČÚZK ({response.status_code}). URL: {debug_url}"
    except Exception as e:
        return f"Chyba sítě/připojení: {e}"

# --- NORMALIZACE S-JTSK DO 3D NULY ---
def normalizuj_sjtsk(raw_pts):
    if not raw_pts or not isinstance(raw_pts, list): return []
    xs = [p[0] for p in raw_pts]
    ys = [p[1] for p in raw_pts]
    cx = min(xs) + (max(xs) - min(xs)) / 2
    cy = min(ys) + (max(ys) - min(ys)) / 2
    
    return [[round(p[0] - cx, 3), round(p[1] - cy, 3)] for p in raw_pts]

# --- UI a SIDEBAR ---
with st.sidebar:
    st.title("📡 Živé napojení ČÚZK")
    
    ku_kod = st.text_input("Kód KÚ (např. 707015)", value="707015")
    col1, col2 = st.columns(2)
    with col1:
        kmen = st.text_input("Kmenové č.", value="45")
    with col2:
        pod = st.text_input("Pododdělení", value="104")
        
    if st.button("Stáhnout parcelu", type="primary"):
        with st.spinner("Pojď mi, ČÚZK..."):
            vysledek = stahni_parcelu_cuzk(ku_kod, kmen, pod)
            if isinstance(vysledek, dict):
                st.session_state['api_data'] = vysledek['coords']
                st.session_state['last_url'] = vysledek['url']
                st.success("Bingo! Data stažena.")
            else:
                st.error(f"Chyba: {vysledek}")
                # Pokud to spadne, uložíme url pro debug
                if "URL:" in vysledek:
                    st.session_state['last_url'] = vysledek.split("URL: ")[-1]

    st.write("---")
    st.subheader("🛠️ Diagnostika")
    
    if 'last_url' in st.session_state:
        st.write("Poslední volaná adresa:")
        st.code(st.session_state['last_url'], language="text")
        
    raw_data = st.session_state.get('api_data', [])
    if raw_data:
        display_pts = normalizuj_sjtsk(raw_data)
        st.write(f"Načteno bodů: {len(display_pts)}")
    else:
        display_pts = []

# --- 3D ENGINE ---
st.title("📐 Digitální dvojče z RÚIAN (v0.31)")

if not display_pts:
    st.info("Vyplň údaje a klikni na 'Stáhnout parcelu'.")
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
        // Osy S-JTSK jsou zrádné. Pro vykreslení ve 3D používáme -Y.
        // Pokud bude parcela zrcadlově obrácená, změníme na -X, Y.
        shape.moveTo(pts[0][0], -pts[0][1]);
        for(let i=1; i<pts.length; i++) {{
            shape.lineTo(pts[i][0], -pts[i][1]);
        }}
        
        const parcelGeom = new THREE.ShapeGeometry(shape);
        const parcelMat = new THREE.MeshPhongMaterial({{ color: 0xc8e6c9, side: THREE.DoubleSide }});
        const parcel = new THREE.Mesh(parcelGeom, parcelMat);
        parcel.rotation.x = -Math.PI / 2;
        scene.add(parcel);

        // KRESLENÍ HRANICE (Katastrální červená)
        const linePts = pts.map(p => new THREE.Vector3(p[0], 0.1, -p[1]));
        const borderGeom = new THREE.BufferGeometry().setFromPoints(linePts);
        const border = new THREE.Line(borderGeom, new THREE.LineBasicMaterial({{ color: 0xd32f2f, linewidth: 3 }}));
        scene.add(border);

        // DŮM - Zlatý standard (Modrý)
        const house = new THREE.Mesh(
            new THREE.BoxGeometry(6.25, 2.7, 12.5),
            new THREE.MeshPhongMaterial({{ color: 0x1976d2, transparent: true, opacity: 0.9 }})
        );
        house.position.set(0, 1.35, 0);
        house.castShadow = true;
        scene.add(house);

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
