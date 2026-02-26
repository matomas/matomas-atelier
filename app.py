import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import numpy as np

st.set_page_config(page_title="Matomas Urban Master v0.53", layout="wide")

API_KEY_TOPO = "27b312106a0008e8d9879f1800bc2e6b"

# --- 1. DATA KATASTR (S-JTSK) ---
def stahni_cuzk(url, params):
    try:
        res = requests.get(url, params=params, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        return res.json().get("features", [])
    except: return []

# --- 2. DATA TERÉN (Satelit Copernicus) ---
def get_terrain(lat, lon):
    # Fixní výřez 0.003 stupně (~300m)
    size = 0.0015
    url = f"https://portal.opentopography.org/API/globaldem?demtype=COP30&south={lat-size}&north={lat+size}&west={lon-size}&east={lon+size}&outputFormat=JSON&API_Key={API_KEY_TOPO}"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🏙️ Urbanistický Kontext v0.53")
    ku = st.text_input("KÚ", "768031")
    km = st.text_input("Kmen", "45")
    pd = st.text_input("Pod", "124")
    
    if st.button("Načíst digitální dvojče", type="primary"):
        with st.spinner("Sestavuji scénu..."):
            # A. Hlavní parcela
            url_p = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/5/query"
            where = f"katastralniuzemi={ku} AND kmenovecislo={km} AND " + (f"poddelenicisla={pd}" if pd else "poddelenicisla IS NULL")
            f_p = stahni_cuzk(url_p, {"where":where, "outSR":"5514", "f":"json", "returnGeometry":"true"})
            
            if f_p:
                ring = f_p[0]["geometry"]["rings"][0]
                # Střed v metrech S-JTSK (převrácené pro JS)
                cx, cy = -sum(p[0] for p in ring)/len(ring), -sum(p[1] for p in ring)/len(ring)
                st.session_state['origin'] = (cx, cy)
                st.session_state['main'] = [[-p[0]-cx, -p[1]-cy] for p in ring]
                
                # B. Okolí (200m)
                bbox = f"{-cx-100},{-cy-100},{-cx+100},{-cy+100}"
                
                # Sousedé
                neighs = stahni_cuzk(url_p, {"geometry":bbox, "geometryType":"esriGeometryEnvelope", "inSR":"5514", "outSR":"5514", "f":"json", "outFields":"druhpozemkukod"})
                st.session_state['neighs'] = [{"pts":[[-p[0]-cx, -p[1]-cy] for p in n["geometry"]["rings"][0]], "road":n["attributes"].get("druhpozemkukod")==14} for n in neighs if n["geometry"]["rings"][0] != ring]
                
                # Budovy (Vrstva 3)
                url_b = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/3/query"
                bldgs = stahni_cuzk(url_b, {"geometry":bbox, "geometryType":"esriGeometryEnvelope", "inSR":"5514", "outSR":"5514", "f":"json"})
                st.session_state['bldgs'] = [[[-p[0]-cx, -p[1]-cy] for p in b["geometry"]["rings"][0]] for b in bldgs]
                
                # C. Terén (Zatím fix GPS Nučničky)
                topo = get_terrain(50.518, 14.165)
                if topo:
                    zs = np.array(topo["height"])
                    st.session_state['topo'] = {"z": (zs - np.min(zs)).tolist(), "dim": int(np.sqrt(len(zs)))}
                
                st.success("Scéna připravena!")

    st.write("---")
    vyska = st.slider("Výška 1.NP (m)", -5.0, 5.0, 0.0)
    pos_x = st.slider("Posun X", -50.0, 50.0, 0.0)
    pos_z = st.slider("Posun Z", -50.0, 50.0, 0.0)
    rot = st.slider("Rotace (°)", 0, 360, 0)

# --- 3D ENGINE ---
if 'main' in st.session_state:
    t = st.session_state.get('topo')
    three_js = f"""
    <div id="v" style="width:100%; height:750px;"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script>
        const s = new THREE.Scene(); s.background = new THREE.Color(0xf0f0f0);
        const r = new THREE.WebGLRenderer({{antialias:true}}); r.setSize(window.innerWidth, 750);
        document.getElementById('v').appendChild(r.domElement);
        const c = new THREE.PerspectiveCamera(45, window.innerWidth/750, 1, 2000); c.position.set(100, 100, 100);
        new THREE.OrbitControls(c, r.domElement);

        // TERÉN (Zvětšený na 300m aby pokryl vše)
        const t = {json.dumps(t)};
        if(t) {{
            const g = new THREE.PlaneGeometry(300, 300, t.dim-1, t.dim-1);
            const v = g.attributes.position.array;
            for(let i=0; i<t.z.length; i++) {{ v[i*3+2] = t.z[i] * 1.5; }}
            g.computeVertexNormals();
            const mesh = new THREE.Mesh(g, new THREE.MeshPhongMaterial({{color:0x4caf50, wireframe:true, transparent:true, opacity:0.2}}));
            mesh.rotation.x = -Math.PI/2; mesh.position.y = -0.5; s.add(mesh);
            const base = new THREE.Mesh(g, new THREE.MeshPhongMaterial({{color:0xffffff, side:2}}));
            base.rotation.x = -Math.PI/2; base.position.y = -0.6; s.add(base);
        }}

        // PARCELY
        const neighs = {json.dumps(st.session_state['neighs'])};
        neighs.forEach(n => {{
            const shp = new THREE.Shape(); shp.moveTo(n.pts[0][0], n.pts[0][1]);
            n.pts.forEach(p => shp.lineTo(p[0], p[1]));
            const m = new THREE.Mesh(new THREE.ShapeGeometry(shp), new THREE.MeshBasicMaterial({{color:n.road?0xcccccc:0xe0e0e0, side:2}}));
            m.rotation.x = -Math.PI/2; s.add(m);
        }});

        const main = {json.dumps(st.session_state['main'])};
        const mShp = new THREE.Shape(); mShp.moveTo(main[0][0], main[0][1]);
        main.forEach(p => mShp.lineTo(p[0], p[1]));
        const mMesh = new THREE.Mesh(new THREE.ShapeGeometry(mShp), new THREE.MeshBasicMaterial({{color:0xc8e6c9, side:2}}));
        mMesh.rotation.x = -Math.PI/2; mMesh.position.y = 0.02; s.add(mMesh);

        // BUDOVY
        const bldgs = {json.dumps(st.session_state['bldgs'])};
        bldgs.forEach(b => {{
            const bShp = new THREE.Shape(); bShp.moveTo(b[0][0], b[0][1]);
            b.forEach(p => bShp.lineTo(p[0], p[1]));
            const bm = new THREE.Mesh(new THREE.ExtrudeGeometry(bShp, {{depth:4, bevelEnabled:false}}), new THREE.MeshPhongMaterial({{color:0x78909c, transparent:true, opacity:0.8}}));
            bm.rotation.x = -Math.PI/2; s.add(bm);
        }});

        // DŮM
        const h = new THREE.Mesh(new THREE.BoxGeometry(6.25, 4, 12.5), new THREE.MeshPhongMaterial({{color:0x1976d2}}));
        h.position.set({pos_x}, {vyska+2}, {-pos_z}); h.rotation.y = {rot}*Math.PI/180; s.add(h);

        s.add(new THREE.AmbientLight(0xffffff, 0.8));
        const sun = new THREE.DirectionalLight(0xffffff, 0.5); sun.position.set(100,200,100); s.add(sun);
        function anim() {{ requestAnimationFrame(anim); r.render(s, c); }} anim();
    </script>
    """
    components.html(three_js, height=770)
