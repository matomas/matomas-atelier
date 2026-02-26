import streamlit as st
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="Matomas KN Connector v0.23", layout="wide")

with st.sidebar:
    st.title("🗺️ Katastrální data")
    # Tady simulujeme body přímo z Geometrického plánu (S-JTSK)
    # V reálu je sem jen vložíš a Python je "vynuluje"
    st.write("Vložte souřadnice bodů (S-JTSK nebo relativní)")
    coords_input = st.text_area("Seznam bodů", value="[[0,0], [30.5, 4.2], [28.1, 42.5], [-8.4, 38.1]]")
    
    st.write("---")
    st.subheader("Technické parametry")
    sklon = st.slider("Sklon terénu (%)", -15, 15, 8)
    vyska_000 = st.slider("Osazení podlahy (m)", -2.0, 5.0, 1.5)

# Pomocná funkce pro vycentrování jakéhokoliv pozemku do nuly
def normalize_coords(raw_string):
    try:
        data = json.loads(raw_string)
        # Tady probíhá matematické vynulování, aby byl pozemek vždy v centru
        avg_x = sum(p[0] for p in data) / len(data)
        avg_y = sum(p[1] for p in data) / len(data)
        return [[p[0]-avg_x, p[1]-avg_y] for p in data]
    except: return [[-10,-10], [10,-10], [10,10], [-10,10]]

clean_pts = normalize_coords(coords_input)

three_js_code = f"""
<div id="container" style="width: 100%; height: 750px; background: #ffffff; border: 1px solid #eee;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xfcfcfc);
    const camera = new THREE.PerspectiveCamera(40, window.innerWidth / 750, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 750);
    renderer.shadowMap.enabled = true;
    document.getElementById('container').appendChild(renderer.domElement);

    // 1. TERÉN (DMR model)
    const terrainGeom = new THREE.PlaneGeometry(120, 120, 60, 60);
    const pos = terrainGeom.attributes.position.array;
    for (let i = 0; i < pos.length; i += 3) {{
        // Simulace sklonu svahu přes celou plochu
        pos[i+2] = (pos[i] * {sklon/100}) + (Math.sin(pos[i+1]*0.1) * 2);
    }}
    terrainGeom.computeVertexNormals();
    const terrainMat = new THREE.MeshPhongMaterial({{ color: 0xe8f5e9, wireframe: true, transparent: true, opacity: 0.25 }});
    const terrain = new THREE.Mesh(terrainGeom, terrainMat);
    terrain.rotation.x = -Math.PI / 2;
    terrain.receiveShadow = true;
    scene.add(terrain);

    // 2. PŘESNÝ POZEMEK (Import z KN)
    const pts = {clean_pts};
    const linePts = [];
    pts.forEach(p => {{
        let x = p[0];
        let y = p[1];
        // Výpočet přesné výšky v daném bodě terénu
        let z = (x * {sklon/100}) + (Math.sin(-y*0.1) * 2);
        linePts.push(new THREE.Vector3(x, z + 0.05, -y));
    }});
    linePts.push(linePts[0]); // Zavřít hranici

    const borderLine = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(linePts),
        new THREE.LineBasicMaterial({{ color: 0xd32f2f, linewidth: 3 }}) // Katastrální červená
    );
    scene.add(borderLine);

    // 3. DŮM (Zlatý Standard - Monolit)
    const houseGeom = new THREE.BoxGeometry(6.25, 2.7, 12.5);
    const houseMat = new THREE.MeshPhongMaterial({{ color: 0x1976d2, transparent: true, opacity: 0.8 }});
    const house = new THREE.Mesh(houseGeom, houseMat);
    house.position.set(0, {vyska_000} + 1.35, 0);
    house.castShadow = true;
    scene.add(house);

    // Pomocné osy (Sever - Jih)
    const axesHelper = new THREE.AxesHelper(20);
    scene.add(axesHelper);

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const sun = new THREE.DirectionalLight(0xffffff, 0.9);
    sun.position.set(30, 60, 30);
    sun.castShadow = true;
    scene.add(sun);

    camera.position.set(50, 50, 50);
    new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=770)
