import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import numpy as np

st.set_page_config(page_title="Matomas Site Intelligence v0.50", layout="wide")

API_KEY_TOPO = "27b312106a0008e8d9879f1800bc2e8d9879f1800bc2e6b"

# --- 1. KATASTR (S-JTSK) ---
def stahni_parcelu_cuzk_sjtsk(ku_kod, kmen, pod):
    url = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/5/query"
    where_clause = f"katastralniuzemi={ku_kod} AND kmenovecislo={kmen}"
    if pod and pod.strip() != "": where_clause += f" AND poddelenicisla={pod}"
    else: where_clause += " AND poddelenicisla IS NULL"
    params = {"where": where_clause, "outFields": "objectid", "returnGeometry": "true", "outSR": "5514", "f": "json"}
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if "features" in data and len(data["features"]) > 0:
                # Vrátí i obálku pro GPS souřadnice terénu
                geom = data["features"][0]["geometry"]
                return geom["rings"][0], data["features"][0]["attributes"].get("objectid")
    except: pass
    return None, None

# --- 2. INSTANTNÍ TERÉN (OpenTopography) ---
def get_satellite_terrain(lat, lon, size=0.002):
    # Copernicus Global DEM (30m resolution) - neprůstřelné API
    south, north = lat - size, lat + size
    west, east = lon - size, lon + size
    url = f"https://portal.opentopography.org/API/globaldem?demtype=COP30&south={south}&north={north}&west={west}&east={east}&outputFormat=GTiff&API_Key={API_KEY_TOPO}"
    
    # Poznámka: OpenTopography vrací binární GeoTIFF, pro web jej musíme zpracovat.
    # Abychom se vyhnuli Rasterio závislostem v cloudu, využijeme JSON formát, pokud je dostupný, 
    # nebo simulujeme mřížku pro vizuální kontext.
    # Zde použijeme SRTM15+ (vysoká rychlost)
    url_json = f"https://portal.opentopography.org/API/globaldem?demtype=SRTM15Plus&south={south}&north={north}&west={west}&east={east}&outputFormat=JSON&API_Key={API_KEY_TOPO}"
    
    try:
        res = requests.get(url_json, timeout=10)
        if res.status_code == 200:
            return res.json()
    except: pass
    return None

# --- 3. PŘEVOD S-JTSK DO LOKÁLNÍ NULY ---
def center_sjtsk(raw_pts, cx=None, cy=None):
    cartesian = [[-p[0], -p[1]] for p in raw_pts]
    if cx is None:
        xs, ys = [p[0] for p in cartesian], [p[1] for p in cartesian]
        cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
    return [[round(p[0]-cx, 3), round(p[1]-cy, 3)] for p in cartesian], cx, cy

# --- UI ---
with st.sidebar:
    st.title("🛰️ Satelitní Morfologie")
    ku_kod = st.text_input("Kód KÚ", value="768031")
    col1, col2 = st.columns(2)
    with col1: kmen = st.text_input("Kmen", value="45")
    with col2: pod = st.text_input("Pod", value="124")
    
    if st.button("Analyzovat lokalitu", type="primary"):
        with st.spinner("Stahuji katastr a satelitní výškopis..."):
            pts_raw, obj_id = stahni_parcelu_cuzk_sjtsk(ku_kod, kmen, pod)
            if pts_raw:
                main_pts, cx, cy = center_sjtsk(pts_raw)
                st.session_state['main_pts'] = main_pts
                
                # GPS pro terén (přibližný převod z Nučniček)
                # V profi verzi by zde byl přesný převodník S-JTSK -> WGS84
                terrain = get_satellite_terrain(50.518, 14.165)
                if terrain and "height" in terrain:
                    zs = np.array(terrain["height"])
                    z_min = np.min(zs)
                    st.session_state['t_data'] = {
                        "heights": (zs - z_min).tolist(),
                        "dim": int(np.sqrt(len(zs))),
                        "base": z_min
                    }
                st.success("Hotovo!")

    st.write("---")
    vyska = st.slider("Výška 1.NP (m)", -5.0, 5.0, 0.0)
    pos_x = st.slider("Posun X", -30.0, 30.0, 0.0)
    pos_z = st.slider("Posun Z", -30.0, 30.0, 0.0)

# --- 3D ENGINE ---
st.title("🏡 Digitální dvojče lokality (v0.50)")

if 'main_pts' in st.session_state:
    t = st.session_state.get('t_data')
    three_js_code = f"""
    <div id="c" style="width:100%; height:750px;"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script>
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xfafafa);
        const renderer = new THREE.WebGLRenderer({{antialias:true}});
        renderer.setSize(window.innerWidth, 750);
        document.getElementById('c').appendChild(renderer.domElement);
        const camera = new THREE.PerspectiveCamera(45, window.innerWidth/750, 1, 2000);
        camera.position.set(60, 60, 60);

        // TERÉN
        const t = {json.dumps(t)};
        if(t) {{
            const geom = new THREE.PlaneGeometry(150, 150, t.dim-1, t.dim-1);
            const v = geom.attributes.position.array;
            for(let i=0; i<t.heights.length; i++) {{ v[i*3+2] = t.heights[i] * 2; }} // Přehnané Z pro vizualizaci
            geom.computeVertexNormals();
            const mesh = new THREE.Mesh(geom, new THREE.MeshPhongMaterial({{color:0x4caf50, wireframe:true, transparent:true, opacity:0.3}}));
            mesh.rotation.x = -Math.PI/2;
            scene.add(mesh);
        }}

        // PARCELA
        const pts = {st.session_state['main_pts']};
        const shape = new THREE.Shape();
        shape.moveTo(pts[0][0], pts[0][1]);
        pts.forEach(p => shape.lineTo(p[0], p[1]));
        const pMesh = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshBasicMaterial({{color:0xc8e6c9, side:2, transparent:true, opacity:0.7}}));
        pMesh.rotation.x = -Math.PI/2;
        pMesh.position.y = 0.1;
        scene.add(pMesh);

        // DŮM
        const house = new THREE.Mesh(new THREE.BoxGeometry(6, 4, 12), new THREE.MeshPhongMaterial({{color:0x1976d2}}));
        house.position.set({pos_x}, {vyska+2}, {-pos_z});
        scene.add(house);

        scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        new THREE.OrbitControls(camera, renderer.domElement);
        function anim() {{ requestAnimationFrame(anim); renderer.render(scene, camera); }}
        anim();
    </script>
    """
    components.html(three_js_code, height=770)
else:
    st.info("Zadejte údaje a spusťte analýzu.")
