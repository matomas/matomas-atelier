import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import numpy as np

st.set_page_config(page_title="Matomas Master Site v0.51", layout="wide")

API_KEY_TOPO = "27b312106a0008e8d9879f1800bc2e6b"

# --- 1. KATASTRÁLNÍ DATA (S-JTSK) ---
def stahni_cuzk_data(url, params):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        if res.status_code == 200: return res.json().get("features", [])
    except: pass
    return []

# --- 2. SATELITNÍ TERÉN (OpenTopography) ---
def get_satellite_terrain(lat, lon, size=0.0015):
    south, north = lat - size, lat + size
    west, east = lon - size, lon + size
    url = f"https://portal.opentopography.org/API/globaldem?demtype=COP30&south={south}&north={north}&west={west}&east={east}&outputFormat=JSON&API_Key={API_KEY_TOPO}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return None

# --- 3. PŘEVOD A CENTROVÁNÍ ---
def center_sjtsk(raw_pts, cx=None, cy=None):
    cartesian = [[-p[0], -p[1]] for p in raw_pts]
    if cx is None:
        xs, ys = [p[0] for p in cartesian], [p[1] for p in cartesian]
        cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
    return [[round(p[0]-cx, 3), round(p[1]-cy, 3)] for p in cartesian], cx, cy

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🏗️ Master Site Analysis")
    ku_kod = st.text_input("Kód KÚ", value="768031")
    col1, col2 = st.columns(2)
    with col1: kmen = st.text_input("Kmen", value="45")
    with col2: pod = st.text_input("Pod", value="124")
    
    if st.button("Generovat kompletní model", type="primary"):
        with st.spinner("Skládám katastr, budovy a terén..."):
            # A. Hlavní parcela
            url_p = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/5/query"
            where_p = f"katastralniuzemi={ku_kod} AND kmenovecislo={kmen} AND " + (f"poddelenicisla={pod}" if pod else "poddelenicisla IS NULL")
            feat_p = stahni_cuzk_data(url_p, {"where": where_p, "outFields": "objectid", "returnGeometry": "true", "outSR": "5514", "f": "json"})
            
            if feat_p:
                raw_main = feat_p[0]["geometry"]["rings"][0]
                main_pts, cx, cy = center_sjtsk(raw_main)
                st.session_state['main_pts'] = main_pts
                
                # B. Bounding box pro okolí (cca 60m)
                orig_cx = sum(p[0] for p in raw_main) / len(raw_main)
                orig_cy = sum(p[1] for p in raw_main) / len(raw_main)
                bbox = f"{orig_cx-60},{orig_cy-60},{orig_cx+60},{orig_cy+60}"
                
                # C. Okolní parcely (Cesty)
                neighs = stahni_cuzk_data(url_p, {"geometry": bbox, "geometryType": "esriGeometryEnvelope", "inSR": "5514", "outFields": "druhpozemkukod", "returnGeometry": "true", "outSR": "5514", "f": "json"})
                st.session_state['neighbors'] = []
                for fn in neighs:
                    if fn["geometry"]["rings"][0] != raw_main:
                        n_met, _, _ = center_sjtsk(fn["geometry"]["rings"][0], cx, cy)
                        st.session_state['neighbors'].append({"poly": n_met, "road": fn["attributes"].get("druhpozemkukod")==14})
                
                # D. Okolní budovy
                url_b = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/3/query"
                bldgs = stahni_cuzk_data(url_b, {"geometry": bbox, "geometryType": "esriGeometryEnvelope", "inSR": "5514", "returnGeometry": "true", "outSR": "5514", "f": "json"})
                st.session_state['budovy'] = []
                for fb in bldgs:
                    for ring in fb["geometry"]["rings"]:
                        b_met, _, _ = center_sjtsk(ring, cx, cy)
                        st.session_state['budovy'].append(b_met)
                
                # E. Satelitní terén (GPS Nučničky)
                terrain = get_satellite_terrain(50.518, 14.165)
                if terrain:
                    zs = np.array(terrain["height"])
                    z_min = np.min(zs)
                    st.session_state['t_data'] = {"heights": (zs - z_min).tolist(), "dim": int(np.sqrt(len(zs)))}
                
                st.success("Analýza dokončena!")

    st.write("---")
    vyska = st.slider("Výška 1.NP (m)", -5.0, 5.0, 0.0)
    pos_x = st.slider("Posun X", -30.0, 30.0, 0.0)
    pos_z = st.slider("Posun Z", -30.0, 30.0, 0.0)
    rot = st.slider("Rotace (°)", 0, 360, 0)

# --- 3D ENGINE ---
st.title("🏡 Digitální dvojče lokality (v0.51)")

if 'main_pts' in st.session_state:
    three_js_code = f"""
    <div id="c" style="width:100%; height:750px; background:#fff;"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script>
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xfafafa);
        const renderer = new THREE.WebGLRenderer({{antialias:true}});
        renderer.setSize(window.innerWidth, 750);
        document.getElementById('c').appendChild(renderer.domElement);
        const camera = new THREE.PerspectiveCamera(45, window.innerWidth/750, 1, 2000);
        camera.position.set(50, 70, 50);

        function getOffset(pts, dist) {{
            const res = [];
            for (let i=0; i<pts.length; i++) {{
                const p1 = pts[(i+pts.length-1)%pts.length], p2 = pts[i], p3 = pts[(i+1)%pts.length];
                const v1 = {{x:p2[0]-p1[0], y:p2[1]-p1[1]}}, v2 = {{x:p3[0]-p2[0], y:p3[1]-p2[1]}};
                const m1 = Math.sqrt(v1.x**2+v1.y**2), m2 = Math.sqrt(v2.x**2+v2.y**2);
                const n1 = {{x:-v1.y/m1, y:v1.x/m1}}, n2 = {{x:-v2.y/m2, y:v2.x/m2}};
                const bx = n1.x+n2.x, by = n1.y+n2.y, bm = Math.sqrt(bx**2+by**2);
                const s = dist / ((n1.x*bx + n1.y*by)/bm);
                res.push(new THREE.Vector3(p2[0]+(bx/bm)*s, 0.15, -(p2[1]+(by/bm)*s)));
            }}
            return res;
        }}

        // 1. TERÉN
        const t = {json.dumps(st.session_state.get('t_data'))};
        if(t) {{
            const geom = new THREE.PlaneGeometry(160, 160, t.dim-1, t.dim-1);
            const v = geom.attributes.position.array;
            for(let i=0; i<t.heights.length; i++) {{ v[i*3+2] = t.heights[i] * 1.5; }}
            geom.computeVertexNormals();
            scene.add(new THREE.Mesh(geom, new THREE.MeshPhongMaterial({{color:0x4caf50, wireframe:true, transparent:true, opacity:0.2}})));
            const terrainSolid = new THREE.Mesh(geom, new THREE.MeshPhongMaterial({{color:0xfcfcfc, side:2}}));
            terrainSolid.rotation.x = -Math.PI/2;
            scene.add(terrainSolid);
        }}

        // 2. PARCELA A OKOLÍ
        const main = {st.session_state['main_pts']};
        const shape = new THREE.Shape();
        shape.moveTo(main[0][0], main[0][1]);
        main.forEach(p => shape.lineTo(p[0], p[1]));
        const pMesh = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshBasicMaterial({{color:0xc8e6c9, transparent:true, opacity:0.6, side:2}}));
        pMesh.rotation.x = -Math.PI/2; pMesh.position.y = 0.05;
        scene.add(pMesh);

        // Stavební čára (fix 2m dovnitř)
        const offLine = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(getOffset(main, -2)), new THREE.LineBasicMaterial({{color:0xff9800, linewidth:2}}));
        scene.add(offLine);

        // Okolní parcely
        const neighs = {json.dumps(st.session_state.get('neighbors', []))};
        neighs.forEach(n => {{
            const nShape = new THREE.Shape();
            nShape.moveTo(n.poly[0][0], n.poly[0][1]);
            n.poly.forEach(p => nShape.lineTo(p[0], p[1]));
            const nMesh = new THREE.Mesh(new THREE.ShapeGeometry(nShape), new THREE.MeshBasicMaterial({{color: n.road ? 0xcccccc : 0xf0f0f0, side:2}}));
            nMesh.rotation.x = -Math.PI/2; nMesh.position.y = 0.02;
            scene.add(nMesh);
        }});

        // 3. BUDOVY
        const bldgs = {json.dumps(st.session_state.get('budovy', []))};
        bldgs.forEach(b => {{
            const bShape = new THREE.Shape();
            bShape.moveTo(b[0][0], b[0][1]);
            b.forEach(p => bShape.lineTo(p[0], p[1]));
            const bMesh = new THREE.Mesh(new THREE.ExtrudeGeometry(bShape, {{depth:4, bevelEnabled:false}}), new THREE.MeshPhongMaterial({{color:0x78909c, transparent:true, opacity:0.8}}));
            bMesh.rotation.x = -Math.PI/2;
            scene.add(bMesh);
            // Požární zóny (7m)
            const f7 = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(getOffset(b, 7)), new THREE.LineBasicMaterial({{color:0xf44336}}));
            scene.add(f7);
        }});

        // 4. DŮM
        const house = new THREE.Mesh(new THREE.BoxGeometry(6.25, 4, 12.5), new THREE.MeshPhongMaterial({{color:0x1976d2}}));
        house.position.set({pos_x}, {vyska+2}, {-pos_z});
        house.rotation.y = ({rot} * Math.PI) / 180;
        scene.add(house);

        scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        const sun = new THREE.DirectionalLight(0xffffff, 0.5); sun.position.set(10,20,10); scene.add(sun);
        new THREE.OrbitControls(camera, renderer.domElement);
        function anim() {{ requestAnimationFrame(anim); renderer.render(scene, camera); }}
        anim();
    </script>
    """
    components.html(three_js_code, height=770)
else:
    st.info("Zadejte údaje vlevo a klikněte na 'Generovat kompletní model'.")
    
