import streamlit as st
import streamlit.components.v1 as components
import requests
import json

st.set_page_config(page_title="Matomas Site Intelligence v0.40", layout="wide")

# --- 1. STAŽENÍ HLAVNÍ PARCELY (S-JTSK) ---
def stahni_parcelu_cuzk_sjtsk(ku_kod, kmen, pod):
    # Opravená doména gov.cz
    url = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/5/query"
    where_clause = f"katastralniuzemi={ku_kod} AND kmenovecislo={kmen}"
    if pod and pod.strip() != "": where_clause += f" AND poddelenicisla={pod}"
    else: where_clause += " AND poddelenicisla IS NULL"
    
    params = {"where": where_clause, "outFields": "objectid", "returnGeometry": "true", "outSR": "5514", "f": "json"}
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if "features" in data and len(data["features"]) > 0:
                return data["features"][0]["geometry"]["rings"][0]
    except: pass
    return None

# --- 2. STAŽENÍ OKOLÍ (S-JTSK) ---
def stahni_okoli_sjtsk(cx_orig, cy_orig, layer_id, out_fields="objectid"):
    xmin, xmax = cx_orig - 50, cx_orig + 50
    ymin, ymax = cy_orig - 50, cy_orig + 50
    # Opravená doména gov.cz
    url = f"https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/{layer_id}/query"
    params = {"geometry": f"{xmin},{ymin},{xmax},{ymax}", "geometryType": "esriGeometryEnvelope", "inSR": "5514", "spatialRel": "esriSpatialRelIntersects", "outFields": out_fields, "returnGeometry": "true", "outSR": "5514", "f": "json"}
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200: return res.json().get("features", [])
    except: pass
    return []

# --- 3. STAŽENÍ VÝŠKOPISU DMR 5G ---
def stahni_dmr5g(pts_sjtsk):
    # Opravená doména gov.cz, aby nedocházelo ke ztrátě POST dat při přesměrování
    url = "https://ags.cuzk.gov.cz/arcgis/rest/services/3D/dmr5g/ImageServer/getSamples"
    geom = {"points": pts_sjtsk, "spatialReference": {"wkid": 5514}}
    data = {"geometry": json.dumps(geom), "geometryType": "esriGeometryMultipoint", "returnFirstValueOnly": "true", "f": "json"}
    try:
        res = requests.post(url, data=data, timeout=15)
        st.session_state['terrain_debug'] = res.text # Uložíme odpověď pro diagnostiku
        if res.status_code == 200:
            rj = res.json()
            if "samples" in rj:
                vals = []
                for s in rj["samples"]:
                    v = s.get("value", "NoData")
                    if v != "NoData":
                        try: vals.append(float(v))
                        except: vals.append(None)
                    else: vals.append(None)
                return vals
    except Exception as e:
        st.session_state['terrain_debug'] = str(e)
    return None

# --- 4. NORMALIZACE S-JTSK ---
def center_sjtsk(raw_pts, cx=None, cy=None):
    if not raw_pts: return [], cx, cy
    cartesian = [[-p[0], -p[1]] for p in raw_pts]
    if cx is None or cy is None:
        xs = [p[0] for p in cartesian]
        ys = [p[1] for p in cartesian]
        cx = min(xs) + (max(xs) - min(xs)) / 2
        cy = min(ys) + (max(ys) - min(ys)) / 2
    norm_pts = [[round(p[0] - cx, 3), round(p[1] - cy, 3)] for p in cartesian]
    return norm_pts, cx, cy

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🔥 Morfologie a Zástavba")
    
    ku_kod = st.text_input("Kód KÚ", value="768031")
    col1, col2 = st.columns(2)
    with col1: kmen = st.text_input("Kmenové č.", value="45")
    with col2: pod = st.text_input("Pododdělení", value="104")
    
    st.write("---")
    nacteni_okoli = st.checkbox("Detekovat cesty a parcely", value=True)
    nacteni_budov = st.checkbox("Detekovat domy (Požární zóny)", value=True)
    nacteni_teren = st.checkbox("Načíst 3D terén (DMR 5G)", value=True)
        
    if st.button("Stáhnout a Analyzovat", type="primary"):
        with st.spinner("Stahuji data, budovy a skenuji terén..."):
            raw_main = stahni_parcelu_cuzk_sjtsk(ku_kod, kmen, pod)
            if raw_main:
                main_met, cx, cy = center_sjtsk(raw_main)
                st.session_state['main_pts'] = main_met
                
                orig_cx = sum(p[0] for p in raw_main) / len(raw_main)
                orig_cy = sum(p[1] for p in raw_main) / len(raw_main)
                
                # Okolí
                neighbors_data = []
                if nacteni_okoli:
                    okoli_features = stahni_okoli_sjtsk(orig_cx, orig_cy, 5, "druhpozemkukod")
                    for feat in okoli_features:
                        geom = feat.get("geometry", {})
                        if geom and "rings" in geom and len(geom["rings"]) > 0:
                            n_raw = geom["rings"][0]
                            if n_raw == raw_main: continue 
                            n_met, _, _ = center_sjtsk(n_raw, cx, cy)
                            is_road = feat.get("attributes", {}).get("druhpozemkukod") == 14 
                            neighbors_data.append({"polygon": n_met, "is_road": is_road})
                st.session_state['neighbors'] = neighbors_data

                # Budovy
                budovy_data = []
                if nacteni_budov:
                    budovy_features = stahni_okoli_sjtsk(orig_cx, orig_cy, 3)
                    for feat in budovy_features:
                        geom = feat.get("geometry", {})
                        if geom and "rings" in geom and len(geom["rings"]) > 0:
                            for ring in geom["rings"]:
                                b_met, _, _ = center_sjtsk(ring, cx, cy)
                                budovy_data.append(b_met)
                st.session_state['budovy'] = budovy_data
                
                # DMR 5G Terén
                if nacteni_teren:
                    grid_size = 21
                    W_terrain, H_terrain = 100, 100
                    xmin_t, xmax_t = -50, 50
                    ymin_t, ymax_t = -50, 50
                    
                    raw_sjtsk_points = []
                    for j in range(grid_size):
                        ly = ymax_t - j * (H_terrain / (grid_size - 1))
                        for i in range(grid_size):
                            lx = xmin_t + i * (W_terrain / (grid_size - 1))
                            # Převod zpět do absolutních S-JTSK
                            raw_sjtsk_points.append([-(lx + cx), -(ly + cy)])
                            
                    heights = stahni_dmr5g(raw_sjtsk_points)
                    if heights and len(heights) == grid_size * grid_size:
                        valid_h = [h for h in heights if h is not None]
                        if valid_h:
                            center_idx = (grid_size // 2) * grid_size + (grid_size // 2)
                            Z_nula = heights[center_idx] if heights[center_idx] is not None else sum(valid_h)/len(valid_h)
                            normalized_heights = [round(h - Z_nula, 3) if h is not None else 0.0 for h in heights]
                            st.session_state['terrain'] = {
                                "w": W_terrain, "h": H_terrain, "z_nula": Z_nula, "heights": normalized_heights
                            }
                        else: st.session_state['terrain'] = None
                    else: st.session_state['terrain'] = None
                else:
                    st.session_state['terrain'] = None
                
                st.success("Komplexní model načten!")
            else:
                st.error("Chyba: Parcelu se nepodařilo stáhnout.")

    st.write("---")
    st.subheader("📐 Osazení tvého domu")
    vyska = st.slider("Výškové osazení 1.NP (m)", -5.0, 5.0, 0.0, step=0.1)
    pos_x = st.slider("Posun domu X", -30.0, 30.0, 0.0)
    pos_z = st.slider("Posun domu Z", -30.0, 30.0, 0.0)
    rotace = st.slider("Natočení domu (°)", 0, 360, 0)
    
    # Diagnostika terénu
    if st.session_state.get('terrain'):
        st.success(f"Kóta 0.000 (střed parcely) = **{st.session_state['terrain']['z_nula']:.2f} m n.m. (Bpv)**")
    elif nacteni_teren:
        st.warning("Terén se nepodařilo stáhnout.")
        with st.expander("Výpis chyby API ČÚZK"):
            st.code(st.session_state.get('terrain_debug', 'Žádná data z API'), language='json')

# --- 3D ENGINE ---
st.title("🏡 Architektonická situace (v0.40)")

main_pts = st.session_state.get('main_pts', [])
neighbors = st.session_state.get('neighbors', [])
budovy = st.session_state.get('budovy', [])
terrain_data = st.session_state.get('terrain', None)

if not main_pts:
    st.info("Zadej parcelu a klikni na 'Stáhnout a Analyzovat'.")
else:
    # Matematická oprava záporného Z pro bezpečný JS
    safe_z = -1 * pos_z
    
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
        const tData = {json.dumps(terrain_data)};

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

        // 0. DMR 5G TERÉN (Zelený Wireframe)
        if (tData) {{
            const tGeom = new THREE.PlaneGeometry(tData.w, tData.h, 20, 20);
            const tVerts = tGeom.attributes.position.array;
            for (let i = 0; i < tData.heights.length; i++) {{
                tVerts[i * 3 + 2] = tData.heights[i];
            }}
            tGeom.computeVertexNormals();
            const tMat = new THREE.MeshPhongMaterial({{ color: 0x4caf50, wireframe: true, transparent: true, opacity: 0.4 }});
            const terrain = new THREE.Mesh(tGeom, tMat);
            terrain.rotation.x = -Math.PI / 2;
            terrain.position.set(0, 0, 0);
            scene.add(terrain);
        }} else {{
            scene.add(new THREE.GridHelper(300, 300, 0xdddddd, 0xf0f0f0));
        }}

        // 1. OKOLNÍ PARCELY A CESTY
        nbrs.forEach(n => {{
            const nShape = new THREE.Shape();
            nShape.moveTo(n.polygon[0][0], n.polygon[0][1]);
            for(let i=1; i<n.polygon.length; i++) {{ nShape.lineTo(n.polygon[i][0], n.polygon[i][1]); }}
            const color = n.is_road ? 0x9e9e9e : 0xe0e0e0;
            const nMesh = new THREE.Mesh(new THREE.ShapeGeometry(nShape), new THREE.MeshPhongMaterial({{ color: color, side: THREE.DoubleSide, transparent: true, opacity: 0.3 }}));
            nMesh.rotation.x = -Math.PI / 2;
            nMesh.position.y = -0.02;
            scene.add(nMesh);

            const nLinePts = n.polygon.map(p => new THREE.Vector3(p[0], -0.01, -p[1]));
            nLinePts.push(nLinePts[0]);
            const nBorder = new THREE.Line(new THREE.BufferGeometry().setFromPoints(nLinePts), new THREE.LineBasicMaterial({{ color: 0xbdbdbd, linewidth: 1 }}));
            scene.add(nBorder);
        }});

        // 2. HLAVNÍ PARCELA
        const shape = new THREE.Shape();
        shape.moveTo(pts[0][0], pts[0][1]);
        for(let i=1; i<pts.length; i++) {{ shape.lineTo(pts[i][0], pts[i][1]); }}
        const parcel = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshPhongMaterial({{ color: 0xc8e6c9, side: THREE.DoubleSide, transparent: true, opacity: 0.8 }}));
        parcel.rotation.x = -Math.PI / 2;
        parcel.receiveShadow = true;
        scene.add(parcel);

        const linePts = pts.map(p => new THREE.Vector3(p[0], 0.05, -p[1]));
        linePts.push(linePts[0]);
        scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(linePts), new THREE.LineBasicMaterial({{ color: 0xd32f2f, linewidth: 3 }})));

        // 3. FIXNÍ STAVEBNÍ ČÁRA (+2.0m DOVNITŘ)
        const signMain = isClockwise(pts) ? -1 : 1; 
        const offPts = getOffsetPoints(pts, 2.0 * signMain);
        const offLine = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(offPts), new THREE.LineBasicMaterial({{ color: 0xff9800, linewidth: 2 }}));
        scene.add(offLine);

        // 4. BUDOVY SOUSEDŮ A POŽÁRNÍ ZÓNY
        bldgs.forEach(b => {{
            const bShape = new THREE.Shape();
            bShape.moveTo(b[0][0], b[0][1]);
            for(let i=1; i<b.length; i++) {{ bShape.lineTo(b[i][0], b[i][1]); }}
            
            const bMesh = new THREE.Mesh(new THREE.ExtrudeGeometry(bShape, {{ depth: 4.0, bevelEnabled: false }}), new THREE.MeshPhongMaterial({{ color: 0x78909c, transparent: true, opacity: 0.85 }}));
            bMesh.rotation.x = -Math.PI / 2;
            bMesh.position.y = 0;
            bMesh.castShadow = true;
            scene.add(bMesh);
            
            const sign = isClockwise(b) ? 1 : -1; 
            const off4Line = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(getOffsetPoints(b, 4 * sign)), new THREE.LineBasicMaterial({{ color: 0xff9800, linewidth: 2 }}));
            off4Line.position.y = 0.06;
            scene.add(off4Line);

            const off7Line = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(getOffsetPoints(b, 7 * sign)), new THREE.LineBasicMaterial({{ color: 0xf44336, linewidth: 2 }}));
            off7Line.position.y = 0.06;
            scene.add(off7Line);
        }});

        // 5. TVŮJ DŮM S BEZPEČNÝM VÝŠKOVÝM OSAZENÍM
        const houseGeom = new THREE.BoxGeometry(6.25, 4.0, 12.5);
        const houseMat = new THREE.MeshPhongMaterial({{ color: 0x1976d2, transparent: true, opacity: 0.9 }});
        const house = new THREE.Mesh(houseGeom, houseMat);
        house.position.set({pos_x}, {vyska + 2.0}, {safe_z});
        house.rotation.y = ({rotace} * Math.PI) / 180;
        house.castShadow = true;
        scene.add(house);

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
