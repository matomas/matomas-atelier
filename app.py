import streamlit as st
import streamlit.components.v1 as components
import requests
import json

st.set_page_config(page_title="Matomas Live API v0.33", layout="wide")

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
        "f": "geojson" # Vždy nám vrátí GPS souřadnice (WGS84)
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                return f"ArcGIS Chyba: {data['error'].get('message', '')}"
            
            if "features" in data and len(data["features"]) > 0:
                # GeoJSON polygon (stahujeme první nalezený obrys)
                return data["features"][0]["geometry"]["coordinates"][0]
            else:
                return "Nenalezeno."
        else:
            return f"Výpadek serveru: HTTP {response.status_code}"
    except Exception as e:
        return f"Chyba sítě: {e}"

# --- MATEMATICKÁ KONVERZE GPS -> METRY (Lokální projekce ČR) ---
def wgs84_do_metru(raw_pts):
    if not raw_pts: return [], 0, 0
    
    # Najdeme střed v GPS stupních
    lons = [p[0] for p in raw_pts]
    lats = [p[1] for p in raw_pts]
    cx = min(lons) + (max(lons) - min(lons)) / 2
    cy = min(lats) + (max(lats) - min(lats)) / 2
    
    norm_pts = []
    for p in raw_pts:
        # Převod rozdílu ve stupních na metry (konstanty pro rovnoběžku 50°)
        x_metry = (p[0] - cx) * 71500   # 1° délky = cca 71 500 m
        y_metry = (p[1] - cy) * 111320  # 1° šířky = cca 111 320 m
        norm_pts.append([round(x_metry, 3), round(y_metry, 3)])
        
    # Výpočet rozměrů
    m_xs = [p[0] for p in norm_pts]
    m_ys = [p[1] for p in norm_pts]
    sirka = max(m_xs) - min(m_xs)
    delka = max(m_ys) - min(m_ys)
    
    return norm_pts, sirka, delka

# --- UI a SIDEBAR ---
with st.sidebar:
    st.title("📡 Živé napojení ČÚZK")
    
    ku_kod = st.text_input("Kód KÚ (např. 768031 pro Nučničky)", value="768031")
    col1, col2 = st.columns(2)
    with col1:
        kmen = st.text_input("Kmenové č.", value="45")
    with col2:
        pod = st.text_input("Pododdělení", value="104")
        
    if st.button("Stáhnout parcelu", type="primary"):
        with st.spinner("Stahuji a modeluji..."):
            vysledek = stahni_parcelu_cuzk(ku_kod, kmen, pod)
            if isinstance(vysledek, list):
                st.session_state['api_data'] = vysledek
                st.success("Data stažena a převedena do metrů!")
            else:
                st.error(f"Chyba: {vysledek}")

    st.write("---")
    st.subheader("🛠️ Diagnostika a rozměry")
    raw_data = st.session_state.get('api_data', [])
    
    if raw_data:
        display_pts, sirka, delka = wgs84_do_metru(raw_data)
        st.metric("Počet lomových bodů", len(display_pts))
        # Nyní už tu nebudou nuly, ale skutečné metry!
        st.write(f"**Reálné rozměry:** {sirka:.1f} m × {delka:.1f} m")
    else:
        display_pts = []

# --- 3D ENGINE ---
st.title("📐 Skutečné 3D dvojče z katastru (v0.33)")

if not display_pts:
    st.info("Klikni na 'Stáhnout parcelu'.")
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
        // GPS data mají orientaci X=Východ, Y=Sever. V Three.js je Sever = -Z.
        shape.moveTo(pts[0][0], -pts[0][1]);
        for(let i=1; i<pts.length; i++) {{
            shape.lineTo(pts[i][0], -pts[i][1]);
        }}
        
        const parcelGeom = new THREE.ShapeGeometry(shape);
        const parcelMat = new THREE.MeshPhongMaterial({{ color: 0xc8e6c9, side: THREE.DoubleSide }});
        const parcel = new THREE.Mesh(parcelGeom, parcelMat);
        parcel.rotation.x = -Math.PI / 2;
        scene.add(parcel);

        // KRESLENÍ HRANICE
        const linePts = pts.map(p => new THREE.Vector3(p[0], 0.1, -p[1]));
        const borderGeom = new THREE.BufferGeometry().setFromPoints(linePts);
        const border = new THREE.Line(borderGeom, new THREE.LineBasicMaterial({{ color: 0xd32f2f, linewidth: 3 }}));
        scene.add(border);

        // DŮM - Zlatý standard 12.5 x 6.25m
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

        camera.position.set(40, 60, 40);
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.target.set(0, 0, 0);
        controls.update();

        function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
        animate();
    </script>
    """
    components.html(three_js_code, height=720)
