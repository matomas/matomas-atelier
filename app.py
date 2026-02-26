import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import numpy as np

st.set_page_config(page_title="Matomas Urban Master v0.54", layout="wide")

API_KEY_TOPO = "27b312106a0008e8d9879f1800bc2e6b"

# --- 1. DATA KATASTR ---
def stahni_cuzk(url, params):
    try:
        res = requests.get(url, params=params, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        return res.json().get("features", [])
    except: return []

# --- 2. DATA TERÉN ---
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
    st.title("🏙️ Urbanistický Kontext v0.54")
    ku = st.text_input("KÚ", "768031")
    km = st.text_input("Kmen", "45")
    pd = st.text_input("Pod", "124")
    
    if st.button("Obnovit digitální dvojče", type="primary"):
        with st.spinner("Sestavuji kompletní grafiku..."):
            url_p = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/5/query"
            where = f"katastralniuzemi={ku} AND kmenovecislo={km} AND " + (f"poddelenicisla={pd}" if pd else "poddelenicisla IS NULL")
            f_p = stahni_cuzk(url_p, {"where":where, "outSR":"5514", "f":"json", "returnGeometry":"true", "outFields":"objectid"})
            
            if f_p:
                ring = f_p[0]["geometry"]["rings"][0]
                cx, cy = -sum(p[0] for p in ring)/len(ring), -sum(p[1] for p in ring)/len(ring)
                st.session_state['origin'] = (cx, cy)
                st.session_state['main'] = [[-p[0]-cx, -p[1]-cy] for p in ring]
                
                bbox = f"{-cx-120},{-cy-120},{-cx+120},{-cy+120}"
                
                # Sousedé (Parcely)
                neighs = stahni_cuzk(url_p, {"geometry":bbox, "geometryType":"esriGeometryEnvelope", "inSR":"5514", "outSR":"5514", "f":"json", "outFields":"druhpozemkukod"})
                st.session_state['neighs'] = []
                for n in neighs:
                    p_raw = n["geometry"]["rings"][0]
                    p_local = [[-p[0]-cx, -p[1]-cy] for p in p_raw]
                    st.session_state['neighs'].append({
                        "pts": p_local, 
                        "is_main": p_raw == ring,
                        "road": n["attributes"].get("druhpozemkukod")==14
                    })
                
                # Budovy
                url_b = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/3/query"
                bldgs = stahni_cuzk(url_b, {"geometry":bbox, "geometryType":"esriGeometryEnvelope", "inSR":"5514", "outSR":"5514", "f":"json"})
                st.session_state['bldgs'] = [[[-p[0]-cx, -p[1]-cy] for p in b["geometry"]["rings"][0]] for b in bldgs]
                
                # Terén
                topo = get_terrain(50.518, 14.165)
                if topo:
                    zs = np.array(topo["height"])
                    st.session_state['topo'] = {"z": (zs - np.min(zs)).tolist(), "dim": int(np.sqrt(len(zs)))}
                
                st.success("Grafika a linky obnoveny!")

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
        const s = new THREE.Scene(); s.background = new THREE.Color(0xfafafa);
        const r = new THREE.WebGLRenderer({{antialias:true}}); r.setSize(window.innerWidth, 750);
        document.getElementById('v').appendChild(r.domElement);
        const c = new THREE.PerspectiveCamera(45, window.innerWidth/750, 1, 2000); c.position.set(120, 120, 120);
        new THREE.OrbitControls(c, r.domElement);

        // Pomocná funkce pro offset linky (stavební čára / požár)
        function getOffset(pts, dist) {{
            const res = [];
            for (let i=0; i<pts.length; i++) {{
                const p1 = pts[(i+pts.length-1)%pts.length], p2 = pts[i], p3 = pts[(i+1)%pts.length];
                const v1 = {{x:p2[0]-p1[0], y:p2[1]-p1[1]}}, v2 = {{x:p3[0]-p2[0], y:p3[1]-p2[1]}};
                const m1 = Math.sqrt(v1.x**2+v1.y**2), m2 = Math.sqrt(v2.x**2+v2.y**2);
                if(m1 < 0.1 || m2 < 0.1) continue;
                const n1 = {{x:-v1.y/m1, y:v1.x/m1}}, n2 = {{x:-v2.y/m2, y:v2.x/m2}};
                const bx = n1.x+n2.x, by = n1.y+n2.y, bm = Math.sqrt(bx**2+by**2);
                const scale = dist / ((n1.x*bx + n1.y*by)/bm);
                res.push(new THREE.Vector3(p2[0]+(bx/bm)*scale, 0.25, -(p2[1]+(by/bm)*scale)));
            }}
            if(res.length > 0) res.push(res[0]);
            return res;
        }}

        // 1. TERÉN
        const t = {json.dumps(t)};
        if(t) {{
            const g = new THREE.PlaneGeometry(350, 350, t.dim-1, t.dim-1);
            const v = g.attributes.position.array;
            for(let i=0; i<t.z.length; i++) {{ v[i*3+2] = t.z[i] * 1.5; }}
            g.computeVertexNormals();
            const mesh = new THREE.Mesh(g, new THREE.MeshPhongMaterial({{color:0x4caf50, wireframe:true, transparent:true, opacity:0.15}}));
            mesh.rotation.x = -Math.PI/2; mesh.position.y = -0.1; s.add(mesh);
            const base = new THREE.Mesh(g, new THREE.MeshPhongMaterial({{color:0xffffff, side:2}}));
            base.rotation.x = -Math.PI/2; base.position.y = -0.2; s.add(base);
        }}

        // 2. PARCELY A HRANICE (Všechny čáry jsou zpět!)
        const neighs = {json.dumps(st.session_state['neighs'])};
        neighs.forEach(n => {{
            const shp = new THREE.Shape(); shp.moveTo(n.pts[0][0], n.pts[0][1]);
            n.pts.forEach(p => shp.lineTo(p[0], p[1]));
            
            // Plocha parcely
            const m = new THREE.Mesh(new THREE.ShapeGeometry(shp), new THREE.MeshBasicMaterial({{
                color: n.is_main ? 0xc8e6c9 : (n.road ? 0xdddddd : 0xf0f0f0), 
                side: 2, transparent: true, opacity: 0.8
            }}));
            m.rotation.x = -Math.PI/2; m.position.y = n.is_main ? 0.05 : 0.02; s.add(m);

            // Čáry hranic (Šedé pro sousedy, červená tlustá pro hlavní)
            const lPts = n.pts.map(p => new THREE.Vector3(p[0], 0.1, -p[1])); lPts.push(lPts[0]);
            const lGeom = new THREE.BufferGeometry().setFromPoints(lPts);
            const lMat = new THREE.LineBasicMaterial({{color: n.is_main ? 0xd32f2f : 0xbbbbbb, linewidth: n.is_main ? 3 : 1}});
            s.add(new THREE.Line(lGeom, lMat));

            // Stavební čára 2m pro tvůj dům (Oranžová)
            if(n.is_main) {{
                const offPts = getOffset(n.pts, -2);
                if(offPts.length > 0) s.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(offPts), new THREE.LineBasicMaterial({{color: 0xff9800, linewidth: 2}})));
            }}
        }});

        // 3. BUDOVY A POŽÁRNÍ ZÓNY
        const bldgs = {json.dumps(st.session_state['bldgs'])};
        bldgs.forEach(b => {{
            const bShp = new THREE.Shape(); bShp.moveTo(b[0][0], b[0][1]);
            b.forEach(p => bShp.lineTo(p[0], p[1]));
            const bm = new THREE.Mesh(new THREE.ExtrudeGeometry(bShp, {{depth:4, bevelEnabled:false}}), new THREE.MeshPhongMaterial({{color:0x78909c, transparent:true, opacity:0.8}}));
            bm.rotation.x = -Math.PI/2; bm.position.y = 0.1; s.add(bm);

            // Požární zóny (Červená tenká 7m)
            const f7 = getOffset(b, 7);
            if(f7.length > 0) s.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(f7), new THREE.LineBasicMaterial({{color: 0xf44336, opacity: 0.5, transparent: true}})));
        }});

        // 4. TVŮJ DŮM (Modrý)
        const h = new THREE.Mesh(new THREE.BoxGeometry(6.25, 4, 12.5), new THREE.MeshPhongMaterial({{color:0x1976d2}}));
        h.position.set({pos_x}, {vyska+2.1}, {-pos_z}); h.rotation.y = {rot}*Math.PI/180; s.add(h);

        s.add(new THREE.AmbientLight(0xffffff, 0.8));
        const sun = new THREE.DirectionalLight(0xffffff, 0.5); sun.position.set(100,200,100); s.add(sun);
        function anim() {{ requestAnimationFrame(anim); r.render(s, c); }} anim();
    </script>
    """
    components.html(three_js, height=770)
