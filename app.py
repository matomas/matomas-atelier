import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import numpy as np

st.set_page_config(page_title="Matomas Urban Master v0.58", layout="wide")

API_KEY_TOPO = "27b312106a0008e8d9879f1800bc2e6b"

# --- 1. CHYTRÉ HLEDÁNÍ KÚ ---
def najdi_kod_ku(nazev_nebo_kod):
    if nazev_nebo_kod.isdigit():
        return nazev_nebo_kod
    # Vyhledávací služba RÚIAN (Layer 1 = Katastrální území)
    url = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Vyhledavaci_sluzba_nad_daty_RUIAN/MapServer/1/query"
    params = {"where": f"UPPER(nazev) LIKE UPPER('{nazev_nebo_kod}%')", "outFields": "kod,nazev", "f": "json"}
    try:
        res = requests.get(url, params=params, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        if "features" in res and len(res["features"]) > 0:
            kod = res["features"][0]["attributes"]["kod"]
            nazev = res["features"][0]["attributes"]["nazev"]
            return str(kod), nazev
    except: pass
    return None, None

# --- 2. DATA KATASTR ---
def stahni_cuzk(url, params):
    try:
        res = requests.get(url, params=params, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        return res.json().get("features", [])
    except: return []

# --- 3. DATA TERÉN (Dynamické GPS) ---
def get_terrain(lat, lon):
    size = 0.0015
    url = f"https://portal.opentopography.org/API/globaldem?demtype=COP30&south={lat-size}&north={lat+size}&west={lon-size}&east={lon+size}&outputFormat=JSON&API_Key={API_KEY_TOPO}"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🏙️ Urbanistický Kontext v0.58")
    
    hledani_ku = st.text_input("Katastrální území (Název nebo Kód)", "Nučničky")
    col1, col2 = st.columns(2)
    with col1: km = st.text_input("Kmenové č.", "45")
    with col2: pd = st.text_input("Pododdělení", "124")
    
    if st.button("Sestavit chytrý model", type="primary"):
        with st.spinner("Hledám katastr a zaměřuji satelit..."):
            
            # Zpracování KÚ
            if hledani_ku.isdigit():
                ku_kod, ku_nazev = hledani_ku, f"Kód {hledani_ku}"
            else:
                ku_kod, ku_nazev = najdi_kod_ku(hledani_ku)
            
            if not ku_kod:
                st.error(f"Katastrální území '{hledani_ku}' nebylo nalezeno.")
            else:
                st.success(f"Nalezeno KÚ: {ku_nazev} ({ku_kod})")
                
                url_p = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/5/query"
                where = f"katastralniuzemi={ku_kod} AND kmenovecislo={km} AND " + (f"poddelenicisla={pd}" if pd else "poddelenicisla IS NULL")
                
                # A. Získání S-JTSK lokálních metrů
                f_p_sjtsk = stahni_cuzk(url_p, {"where":where, "outSR":"5514", "f":"json", "returnGeometry":"true", "outFields":"objectid"})
                
                # B. Získání WGS84 GPS pro satelitní terén (Zlatý grál)
                f_p_gps = stahni_cuzk(url_p, {"where":where, "outSR":"4326", "f":"json", "returnGeometry":"true"})
                
                if f_p_sjtsk and f_p_gps:
                    # Střed parcely v GPS (pro OpenTopography)
                    gps_ring = f_p_gps[0]["geometry"]["rings"][0]
                    gps_lon = sum(p[0] for p in gps_ring)/len(gps_ring)
                    gps_lat = sum(p[1] for p in gps_ring)/len(gps_ring)

                    # Střed parcely v metrech
                    main_raw = f_p_sjtsk[0]["geometry"]["rings"][0]
                    cx, cy = sum(p[0] for p in main_raw)/len(main_raw), sum(p[1] for p in main_raw)/len(main_raw)
                    st.session_state['main'] = [[round(-p[0]+cx, 3), round(-p[1]+cy, 3)] for p in main_raw]
                    
                    bbox = f"{cx-150},{cy-150},{cx+150},{cy+150}"
                    
                    # Sousedé
                    neighs = stahni_cuzk(url_p, {"geometry":bbox, "geometryType":"esriGeometryEnvelope", "inSR":"5514", "outSR":"5514", "f":"json", "outFields":"druhpozemkukod"})
                    st.session_state['neighs'] = []
                    for n in neighs:
                        n_raw = n["geometry"]["rings"][0]
                        if n_raw != main_raw:
                            n_local = [[round(-p[0]+cx, 3), round(-p[1]+cy, 3)] for p in n_raw]
                            st.session_state['neighs'].append({"pts": n_local, "road": n["attributes"].get("druhpozemkukod")==14})
                    
                    # Budovy
                    url_b = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/3/query"
                    bldgs = stahni_cuzk(url_b, {"geometry":bbox, "geometryType":"esriGeometryEnvelope", "inSR":"5514", "outSR":"5514", "f":"json"})
                    st.session_state['bldgs'] = []
                    for b in bldgs:
                        for ring in b["geometry"]["rings"]:
                            st.session_state['bldgs'].append([[round(-p[0]+cx, 3), round(-p[1]+cy, 3)] for p in ring])
                    
                    # Terén s přesnou dynamickou GPS lokací!
                    topo = get_terrain(gps_lat, gps_lon)
                    if topo:
                        zs = np.array(topo["height"])
                        st.session_state['topo'] = {"z": (zs - np.min(zs)).tolist(), "dim": int(np.sqrt(len(zs)))}
                    
                    st.success("Kompletní model vykreslen!")

    st.write("---")
    st.subheader("⛰️ Zobrazení terénu")
    z_mult = st.slider("Zvýraznění převýšení (x)", 1.0, 5.0, 2.0, step=0.5)

    st.write("---")
    st.subheader("📐 Osazení domu")
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
        const s = new THREE.Scene(); s.background = new THREE.Color(0xfafafa);
        const r = new THREE.WebGLRenderer({{antialias:true}}); r.setSize(window.innerWidth, 750);
        document.getElementById('v').appendChild(r.domElement);
        const c = new THREE.PerspectiveCamera(45, window.innerWidth/750, 1, 2000); c.position.set(70, 90, 70);
        new THREE.OrbitControls(c, r.domElement);

        function isClockwise(pts) {{
            let sum = 0;
            for (let i = 0; i < pts.length; i++) {{ sum += (pts[(i + 1) % pts.length][0] - pts[i][0]) * (pts[(i + 1) % pts.length][1] + pts[i][1]); }}
            return sum > 0;
        }}

        function getSafeOffset(pts, dist, zLevel) {{
            const res = [];
            for (let i=0; i<pts.length; i++) {{
                const p1 = pts[(i+pts.length-1)%pts.length], p2 = pts[i], p3 = pts[(i+1)%pts.length];
                const v1 = {{x:p2[0]-p1[0], y:p2[1]-p1[1]}}, v2 = {{x:p3[0]-p2[0], y:p3[1]-p2[1]}};
                const m1 = Math.sqrt(v1.x**2+v1.y**2), m2 = Math.sqrt(v2.x**2+v2.y**2);
                if(m1 < 0.001 || m2 < 0.001) continue;
                const n1 = {{x:-v1.y/m1, y:v1.x/m1}}, n2 = {{x:-v2.y/m2, y:v2.x/m2}};
                const bx = n1.x+n2.x, by = n1.y+n2.y, bm = Math.sqrt(bx**2+by**2);
                if (bm < 0.001) {{ res.push(new THREE.Vector3(p2[0]+n1.x*dist, zLevel, -(p2[1]+n1.y*dist))); continue; }}
                let dot = (n1.x*bx + n1.y*by)/bm;
                let miter = Math.max(-2.5, Math.min(2.5, 1/dot)); // Clamp spiky corners
                res.push(new THREE.Vector3(p2[0]+(bx/bm)*(dist*miter), zLevel, -(p2[1]+(by/bm)*(dist*miter))));
            }}
            if(res.length > 0) res.push(res[0].clone());
            return res;
        }}

        // 1. TERÉN (S flatShading pro architektonický vzhled)
        const t = {json.dumps(t)};
        const zMult = {z_mult}; // Zvýraznění svahu
        if(t) {{
            const g = new THREE.PlaneGeometry(350, 350, t.dim-1, t.dim-1);
            const v = g.attributes.position.array;
            for(let i=0; i<t.z.length; i++) {{ v[i*3+2] = t.z[i] * zMult; }}
            g.computeVertexNormals();
            
            // Architektonický model "Low Poly"
            const mesh = new THREE.Mesh(g, new THREE.MeshPhongMaterial({{
                color:0xc8e6c9, flatShading: true, transparent:true, opacity:0.6
            }}));
            mesh.rotation.x = -Math.PI/2; mesh.position.y = -0.5; s.add(mesh);
            
            // Podkladový Wireframe
            const wire = new THREE.Mesh(g, new THREE.MeshBasicMaterial({{color:0x4caf50, wireframe:true, transparent:true, opacity:0.15}}));
            wire.rotation.x = -Math.PI/2; wire.position.y = -0.48; s.add(wire);
        }}

        // 2. OKOLNÍ PARCELY
        const neighs = {json.dumps(st.session_state.get('neighs', []))};
        neighs.forEach(n => {{
            const shp = new THREE.Shape(); shp.moveTo(n.pts[0][0], n.pts[0][1]);
            n.pts.forEach(p => shp.lineTo(p[0], p[1]));
            const m = new THREE.Mesh(new THREE.ShapeGeometry(shp), new THREE.MeshBasicMaterial({{color: n.road ? 0xdddddd : 0xf0f0f0, side: 2, transparent: true, opacity: 0.8}}));
            m.rotation.x = -Math.PI/2; m.position.y = 0.00; s.add(m);
            const lPts = n.pts.map(p => new THREE.Vector3(p[0], 0.02, -p[1])); lPts.push(lPts[0]);
            s.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(lPts), new THREE.LineBasicMaterial({{color: 0xbbbbbb, linewidth: 1}})));
        }});

        // 3. HLAVNÍ PARCELA
        const mainPts = {json.dumps(st.session_state['main'])};
        const mShp = new THREE.Shape(); mShp.moveTo(mainPts[0][0], mainPts[0][1]);
        mainPts.forEach(p => mShp.lineTo(p[0], p[1]));
        const mMesh = new THREE.Mesh(new THREE.ShapeGeometry(mShp), new THREE.MeshBasicMaterial({{color: 0xa5d6a7, side: 2, transparent: true, opacity: 0.9}}));
        mMesh.rotation.x = -Math.PI/2; mMesh.position.y = 0.05; s.add(mMesh);
        
        const mlPts = mainPts.map(p => new THREE.Vector3(p[0], 0.1, -p[1])); mlPts.push(mlPts[0]);
        s.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(mlPts), new THREE.LineBasicMaterial({{color: 0xd32f2f, linewidth: 3}})));

        const signMain = isClockwise(mainPts) ? -1 : 1; 
        const offMain = getSafeOffset(mainPts, 2.0 * signMain, 0.12);
        if(offMain.length > 0) s.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(offMain), new THREE.LineBasicMaterial({{color: 0xff9800, linewidth: 2}})));

        // 4. BUDOVY A DASHED ZÓNY
        const bldgs = {json.dumps(st.session_state.get('bldgs', []))};
        bldgs.forEach(b => {{
            const bShp = new THREE.Shape(); bShp.moveTo(b[0][0], b[0][1]);
            b.forEach(p => bShp.lineTo(p[0], p[1]));
            const bm = new THREE.Mesh(new THREE.ExtrudeGeometry(bShp, {{depth:4, bevelEnabled:false}}), new THREE.MeshPhongMaterial({{color:0x78909c, transparent:true, opacity:0.8}}));
            bm.rotation.x = -Math.PI/2; bm.position.y = 0.05; s.add(bm);

            const signB = isClockwise(b) ? 1 : -1;
            
            const f4 = getSafeOffset(b, 4.0 * signB, 0.25);
            if(f4.length > 0) {{
                const line4 = new THREE.Line(new THREE.BufferGeometry().setFromPoints(f4), new THREE.LineDashedMaterial({{color: 0xff9800, dashSize: 0.8, gapSize: 0.6}}));
                line4.computeLineDistances(); s.add(line4);
            }}

            const f7 = getSafeOffset(b, 7.0 * signB, 0.26);
            if(f7.length > 0) {{
                const line7 = new THREE.Line(new THREE.BufferGeometry().setFromPoints(f7), new THREE.LineDashedMaterial({{color: 0xf44336, dashSize: 0.8, gapSize: 0.6}}));
                line7.computeLineDistances(); s.add(line7);
            }}
        }});

        // 5. TVŮJ DŮM
        const h = new THREE.Mesh(new THREE.BoxGeometry(6.25, 4, 12.5), new THREE.MeshPhongMaterial({{color:0x1976d2}}));
        h.position.set({pos_x}, {vyska+2.1}, {-pos_z}); h.rotation.y = {rot}*Math.PI/180; s.add(h);

        // Architektonické nasvícení scény
        s.add(new THREE.AmbientLight(0xffffff, 0.6));
        const sun = new THREE.DirectionalLight(0xffffff, 0.7); 
        sun.position.set(100, 200, 100); 
        s.add(sun);
        const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
        fillLight.position.set(-100, 50, -100);
        s.add(fillLight);

        function anim() {{ requestAnimationFrame(anim); r.render(s, c); }} anim();
    </script>
    """
    components.html(three_js, height=770)
