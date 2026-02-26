import streamlit as st
import streamlit.components.v1 as components
import requests
import json

st.set_page_config(page_title="Matomas Site Intelligence v0.34", layout="wide")

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
        "f": "geojson"
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if "features" in data and len(data["features"]) > 0:
                return data["features"][0]["geometry"]["coordinates"][0]
            return "Nenalezeno."
        return f"Chyba serveru: HTTP {response.status_code}"
    except Exception as e:
        return f"Chyba sítě: {e}"

# --- KONVERZE WGS84 -> METRY ---
def wgs84_do_metru(raw_pts):
    if not raw_pts: return [], 0, 0
    lons = [p[0] for p in raw_pts]
    lats = [p[1] for p in raw_pts]
    cx = min(lons) + (max(lons) - min(lons)) / 2
    cy = min(lats) + (max(lats) - min(lats)) / 2
    
    norm_pts = []
    for p in raw_pts:
        x_metry = (p[0] - cx) * 71500
        y_metry = (p[1] - cy) * 111320
        norm_pts.append([round(x_metry, 3), round(y_metry, 3)])
        
    m_xs = [p[0] for p in norm_pts]
    m_ys = [p[1] for p in norm_pts]
    return norm_pts, (max(m_xs) - min(m_xs)), (max(m_ys) - min(m_ys))

# --- UI a SIDEBAR ---
with st.sidebar:
    st.title("📡 Živý Katastr")
    
    ku_kod = st.text_input("Kód KÚ", value="768031")
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
    st.subheader("📐 Limity a Osazení")
    # Záměrně od -10 do 10, aby šlo kompenzovat směr vykreslování polygonu
    odstup = st.slider("Zákonný odstup (m)", -10.0, 10.0, 3.0, step=0.5)
    
    st.write("---")
    pos_x = st.slider("Posun domu X", -30.0, 30.0, 0.0)
    pos_z = st.slider("Posun domu Z", -30.0, 30.0, 0.0)
    rotace = st.slider("Natočení domu (°)", 0, 360, 0)

    raw_data = st.session_state.get('api_data', [])
    if raw_data:
        display_pts, sirka, delka = wgs84_do_metru(raw_data)
        st.write("---")
        st.caption(f"Rozměry parcely: {sirka:.1f} × {delka:.1f} m")
    else:
        display_pts = []

# --- 3D ENGINE ---
st.title("🏡 Analýza zastavitelnosti (v0.34)")

if not display_pts:
    st.info("Zadej parcelu a stáhni data pro analýzu.")
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
        const offsetDist = {odstup};

        // 1. KRESLENÍ POLYGONU PARCELY (Zelená)
        const shape = new THREE.Shape();
        shape.moveTo(pts[0][0], -pts[0][1]);
        for(let i=1; i<pts.length; i++) {{ shape.lineTo(pts[i][0], -pts[i][1]); }}
        const parcelGeom = new THREE.ShapeGeometry(shape);
        const parcelMat = new THREE.MeshPhongMaterial({{ color: 0xc8e6c9, side: THREE.DoubleSide, transparent: true, opacity: 0.8 }});
        const parcel = new THREE.Mesh(parcelGeom, parcelMat);
        parcel.rotation.x = -Math.PI / 2;
        scene.add(parcel);

        // 2. KRESLENÍ HRANICE (Červená linka)
        const linePts = pts.map(p => new THREE.Vector3(p[0], 0.05, -p[1]));
        const borderGeom = new THREE.BufferGeometry().setFromPoints(linePts);
        const border = new THREE.LineLoop(borderGeom, new THREE.LineBasicMaterial({{ color: 0xd32f2f, linewidth: 2 }}));
        scene.add(border);

        // 3. VÝPOČET STAVEBNÍ ČÁRY (Bisektor algoritmus)
        function getOffsetPoints(points, distance) {{
            const result = [];
            const len = points.length;
            for (let i = 0; i < len; i++) {{
                const p1 = points[(i + len - 1) % len];
                const p2 = points[i];
                const p3 = points[(i + 1) % len];

                const v1 = {{ x: p2[0]-p1[0], y: p2[1]-p1[1] }};
                const v2 = {{ x: p3[0]-p2[0], y: p3[1]-p2[1] }};

                const mag1 = Math.sqrt(v1.x**2 + v1.y**2);
                const mag2 = Math.sqrt(v2.x**2 + v2.y**2);

                const n1 = {{ x: -v1.y/mag1, y: v1.x/mag1 }};
                const n2 = {{ x: -v2.y/mag2, y: v2.x/mag2 }};

                const bx = n1.x + n2.x;
                const by = n1.y + n2.y;
                const bMag = Math.sqrt(bx**2 + by**2);

                if (bMag < 0.0001) {{
                    result.push(new THREE.Vector3(p2[0] + n1.x * distance, 0.1, -(p2[1] + n1.y * distance)));
                    continue;
                }}

                const scale = distance / ( (n1.x * bx + n1.y * by) / bMag );
                result.push(new THREE.Vector3(p2[0] + (bx/bMag)*scale, 0.1, -(p2[1] + (by/bMag)*scale)));
            }}
            return result;
        }}

        if (offsetDist !== 0) {{
            const offPts = getOffsetPoints(pts, offsetDist);
            const offGeom = new THREE.BufferGeometry().setFromPoints(offPts);
            // Stavební čára je oranžová přerušovaná (simulujeme LineLoop)
            const offLine = new THREE.LineLoop(offGeom, new THREE.LineBasicMaterial({{ color: 0xff9800, linewidth: 3 }}));
            scene.add(offLine);
        }}

        // 4. DŮM - Zlatý standard s interakcí
        const houseGeom = new THREE.BoxGeometry(6.25, 2.7, 12.5);
        const houseMat = new THREE.MeshPhongMaterial({{ color: 0x1976d2, transparent: true, opacity: 0.9 }});
        const house = new THREE.Mesh(houseGeom, houseMat);
        house.position.set({pos_x}, 1.35, -{pos_z});
        house.rotation.y = ({rotace} * Math.PI) / 180;
        house.castShadow = true;
        scene.add(house);

        // Grid a Světla
        scene.add(new THREE.GridHelper(200, 200, 0xdddddd, 0xeeeeee));
        scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        const sun = new THREE.DirectionalLight(0xffffff, 0.6);
        sun.position.set(50, 100, 50);
        sun.castShadow = true;
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
