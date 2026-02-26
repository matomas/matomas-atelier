import streamlit as st
import streamlit.components.v1 as components
import requests
import json

st.set_page_config(page_title="Matomas Site Intelligence v0.37", layout="wide")

# --- 1. STAŽENÍ HLAVNÍ PARCELY ---
def stahni_parcelu_cuzk(ku_kod, kmen, pod):
    url = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/5/query"
    where_clause = f"katastralniuzemi={ku_kod} AND kmenovecislo={kmen}"
    if pod and pod.strip() != "": where_clause += f" AND poddelenicisla={pod}"
    else: where_clause += " AND poddelenicisla IS NULL"
    params = {"where": where_clause, "outFields": "objectid", "returnGeometry": "true", "f": "geojson"}
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if "features" in data and len(data["features"]) > 0:
                return data["features"][0]["geometry"]["coordinates"][0]
    except: pass
    return None

# --- 2. STAŽENÍ OKOLÍ (PARCELY + BUDOVY) ---
def stahni_okoli(xmin, ymin, xmax, ymax, layer_id, out_fields="objectid"):
    url = f"https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/{layer_id}/query"
    params = {
        "geometry": f"{xmin},{ymin},{xmax},{ymax}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": out_fields,
        "returnGeometry": "true",
        "f": "geojson"
    }
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200:
            return res.json().get("features", [])
    except: pass
    return []

# --- 3. PŘEVOD DO METRŮ ---
def prevod_do_metru(pts, cx=None, cy=None):
    if not cx or not cy:
        lons = [p[0] for p in pts]
        lats = [p[1] for p in pts]
        cx = min(lons) + (max(lons) - min(lons)) / 2
        cy = min(lats) + (max(lats) - min(lats)) / 2
    norm_pts = []
    for p in pts:
        x_m = (p[0] - cx) * 71500
        y_m = (p[1] - cy) * 111320
        norm_pts.append([round(x_m, 3), round(y_m, 3)])
    return norm_pts, cx, cy

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🔥 Komplexní Analýza Zástavby")
    
    ku_kod = st.text_input("Kód KÚ", value="768031")
    col1, col2 = st.columns(2)
    with col1: kmen = st.text_input("Kmenové č.", value="45")
    with col2: pod = st.text_input("Pododdělení", value="104")
    
    st.write("---")
    nacteni_okoli = st.checkbox("Detekovat cesty a parcely", value=True)
    nacteni_budov = st.checkbox("Detekovat domy (Požární zóny)", value=True)
        
    if st.button("Stáhnout a Analyzovat", type="primary"):
        with st.spinner("Stahuji data, budovy a počítám zóny..."):
            raw_main = stahni_parcelu_cuzk(ku_kod, kmen, pod)
            if raw_main:
                main_met, cx, cy = prevod_do_metru(raw_main)
                st.session_state['main_pts'] = main_met
                
                # Výřez 30 metrů okolo
                margin = 0.0004 
                xmin = min([p[0] for p in raw_main]) - margin
                ymin = min([p[1] for p in raw_main]) - margin
                xmax = max([p[0] for p in raw_main]) + margin
                ymax = max([p[1] for p in raw_main]) + margin
                
                # Sousední parcely
                neighbors_data = []
                if nacteni_okoli:
                    okoli_features = stahni_okoli(xmin, ymin, xmax, ymax, 5, "druhpozemkukod")
                    for feat in okoli_features:
                        props = feat.get("properties", {})
                        geom = feat.get("geometry", {})
                        if geom and "coordinates" in geom and len(geom["coordinates"]) > 0:
                            n_raw = geom["coordinates"][0]
                            if n_raw == raw_main: continue 
                            n_met, _, _ = prevod_do_metru(n_raw, cx, cy)
                            is_road = props.get("druhpozemkukod") == 14 
                            neighbors_data.append({"polygon": n_met, "is_road": is_road})
                st.session_state['neighbors'] = neighbors_data

                # Okolní budovy
                budovy_data = []
                if nacteni_budov:
                    budovy_features = stahni_okoli(xmin, ymin, xmax, ymax, 3)
                    for feat in budovy_features:
                        geom = feat.get("geometry", {})
                        if geom and "coordinates" in geom and len(geom["coordinates"]) > 0:
                            coords = geom["coordinates"]
                            if feat["geometry"]["type"] == "MultiPolygon": coords = coords[0]
                            if len(coords) > 0:
                                b_raw = coords[0]
                                b_met, _, _ = prevod_do_metru(b_raw, cx, cy)
                                budovy_data.append(b_met)
                st.session_state['budovy'] = budovy_data
                
                st.success("Kompletní kontext byl nahrán!")
            else:
                st.error("Chyba: Parcelu se nepodařilo stáhnout.")

    st.write("---")
    st.subheader("📐 Limity a Osazení tvého domu")
    # Vrácen posuvník pro stavební čáru (odstup od hrany pozemku)
    odstup = st.slider("Zákonný odstup - parcela (m)", -10.0, 10.0, -3.0, step=0.5)
    pos_x = st.slider("Posun domu X", -30.0, 30.0, 0.0)
    pos_z = st.slider("Posun domu Z", -30.0, 30.0, 0.0)
    rotace = st.slider("Natočení domu (°)", 0, 360, 0)

# --- 3D ENGINE ---
st.title("🏡 Architektonická situace (v0.37)")

main_pts = st.session_state.get('main_pts', [])
neighbors = st.session_state.get('neighbors', [])
budovy = st.session_state.get('budovy', [])

if not main_pts:
    st.info("Zadej parcelu a klikni na 'Stáhnout a Analyzovat'.")
else:
    three_js_code = f"""
    <div id="container" style="width: 100%; height: 750px; background: #ffffff; border: 1px solid #ddd; border-radius: 8px;"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script>
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xfafafa);
        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 750, 0.1, 5000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, 750);
        renderer.shadowMap.enabled = true;
        document.getElementById('container').appendChild(renderer.domElement);

        const pts = {main_pts};
        const nbrs = {json.dumps(neighbors)};
        const bldgs = {json.dumps(budovy)};
        const offsetDistMain = {odstup};

        // Bisektor algoritmus pro ofsety
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

        function isClockwise(points) {{
            let sum = 0;
            for (let i = 0; i < points.length; i++) {{
                const p1 = points[i];
                const p2 = points[(i + 1) % points.length];
                sum += (p2[0] - p1[0]) * (p2[1] + p1[1]);
            }}
            return sum > 0;
        }}

        // 1. OKOLNÍ PARCELY A CESTY (Včetně vrácených šedých linek!)
        nbrs.forEach(n => {{
            const nShape = new THREE.Shape();
            nShape.moveTo(n.polygon[0][0], -n.polygon[0][1]);
            for(let i=1; i<n.polygon.length; i++) {{ nShape.lineTo(n.polygon[i][0], -n.polygon[i][1]); }}
            const color = n.is_road ? 0x9e9e9e : 0xe0e0e0;
            const nMesh = new THREE.Mesh(new THREE.ShapeGeometry(nShape), new THREE.MeshPhongMaterial({{ color: color, side: THREE.DoubleSide, transparent: true, opacity: 0.3 }}));
            nMesh.rotation.x = -Math.PI / 2;
            nMesh.position.y = -0.02;
            scene.add(nMesh);

            // Tady jsou ty tvoje ztracené hranice okolí
            const nLinePts = n.polygon.map(p => new THREE.Vector3(p[0], -0.01, -p[1]));
            nLinePts.push(nLinePts[0]);
            const nBorder = new THREE.Line(new THREE.BufferGeometry().setFromPoints(nLinePts), new THREE.LineBasicMaterial({{ color: 0xbdbdbd, linewidth: 1 }}));
            scene.add(nBorder);
        }});

        // 2. HLAVNÍ PARCELA A JEJÍ ODSTUP
        const shape = new THREE.Shape();
        shape.moveTo(pts[0][0], -pts[0][1]);
        for(let i=1; i<pts.length; i++) {{ shape.lineTo(pts[i][0], -pts[i][1]); }}
        const parcel = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshPhongMaterial({{ color: 0xc8e6c9, side: THREE.DoubleSide, transparent: true, opacity: 0.8 }}));
        parcel.rotation.x = -Math.PI / 2;
        parcel.receiveShadow = true;
        scene.add(parcel);

        const linePts = pts.map(p => new THREE.Vector3(p[0], 0.05, -p[1]));
        linePts.push(linePts[0]);
        scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(linePts), new THREE.LineBasicMaterial({{ color: 0xd32f2f, linewidth: 3 }})));

        if (offsetDistMain !== 0) {{
            const offPts = getOffsetPoints(pts, offsetDistMain);
            const offGeom = new THREE.BufferGeometry().setFromPoints(offPts);
            const offLine = new THREE.LineLoop(offGeom, new THREE.LineBasicMaterial({{ color: 0xff9800, linewidth: 2 }}));
            scene.add(offLine);
        }}

        // 3. BUDOVY SOUSEDŮ (4 metry výška) A JEJICH 4m/7m ZÓNY
        bldgs.forEach(b => {{
            const bShape = new THREE.Shape();
            bShape.moveTo(b[0][0], -b[0][1]);
            for(let i=1; i<b.length; i++) {{ bShape.lineTo(b[i][0], -b[i][1]); }}
            
            // Hmota budovy (Zvednuto z 3.5 na 4 metry)
            const extrudeSettings = {{ depth: 4.0, bevelEnabled: false }};
            const bGeom = new THREE.ExtrudeGeometry(bShape, extrudeSettings);
            const bMat = new THREE.MeshPhongMaterial({{ color: 0x78909c, transparent: true, opacity: 0.85 }});
            const bMesh = new THREE.Mesh(bGeom, bMat);
            bMesh.rotation.x = -Math.PI / 2;
            bMesh.position.y = 0;
            bMesh.castShadow = true;
            scene.add(bMesh);
            
            const cw = isClockwise(b);
            const sign = cw ? 1 : -1; 

            // 4m zóna (oranžová - bez oken)
            const off4 = getOffsetPoints(b, 4 * sign);
            const off4Geom = new THREE.BufferGeometry().setFromPoints(off4);
            const off4Line = new THREE.LineLoop(off4Geom, new THREE.LineBasicMaterial({{ color: 0xff9800, linewidth: 2 }}));
            off4Line.position.y = 0.06;
            scene.add(off4Line);

            // 7m zóna (červená - s okny)
            const off7 = getOffsetPoints(b, 7 * sign);
            const off7Geom = new THREE.BufferGeometry().setFromPoints(off7);
            const off7Line = new THREE.LineLoop(off7Geom, new THREE.LineBasicMaterial({{ color: 0xf44336, linewidth: 2 }}));
            off7Line.position.y = 0.06;
            scene.add(off7Line);
        }});

        // 4. TVŮJ DŮM (Modrý blok)
        const houseGeom = new THREE.BoxGeometry(6.25, 4.0, 12.5); // Rovněž 4m výška pro referenci
        const houseMat = new THREE.MeshPhongMaterial({{ color: 0x1976d2, transparent: true, opacity: 0.9 }});
        const house = new THREE.Mesh(houseGeom, houseMat);
        house.position.set({pos_x}, 2.0, -{pos_z}); // Zvednutí do osy, když má výšku 4m
        house.rotation.y = ({rotace} * Math.PI) / 180;
        house.castShadow = true;
        scene.add(house);

        scene.add(new THREE.GridHelper(300, 300, 0xdddddd, 0xf0f0f0));
        scene.add(new THREE.AmbientLight(0xffffff, 0.7));
        const sun = new THREE.DirectionalLight(0xffffff, 0.7);
        sun.position.set(50, 100, 50);
        sun.castShadow = true;
        scene.add(sun);

        camera.position.set(40, 70, 40);
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.target.set(0, 0, 0);
        controls.update();

        function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
        animate();
    </script>
    """
    components.html(three_js_code, height=770)
