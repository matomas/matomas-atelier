import streamlit as st
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="Matomas RÚIAN Connector", layout="wide")

with st.sidebar:
    st.title("🔍 Najít parcelu")
    obec = st.text_input("Obec", value="Praha")
    cislo_parcely = st.text_input("Číslo parcely", value="123/4")
    
    if st.button("Načíst data z katastru"):
        # TADY BUDE VOLÁNÍ API: requests.get(f"https://vdp.cuzk.cz/wfs/...")
        st.success(f"Parcela {cislo_parcely} v k.ú. {obec} nalezena.")
        # Simulujeme automaticky stažená data:
        st.session_state['points'] = [[0,0], [35,2], [32,45], [-5,40]]

    st.write("---")
    st.subheader("Technika")
    sklon = st.slider("Sklon terénu (%)", -20, 20, 5)

# Načtení bodů (buď z API nebo default)
pts = st.session_state.get('points', [[0,0], [20,0], [20,20], [0,20]])

three_js_code = f"""
<div id="container" style="width: 100%; height: 700px; background: #ffffff;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xfcfcfc);
    const camera = new THREE.PerspectiveCamera(40, window.innerWidth / 700, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 700);
    document.getElementById('container').appendChild(renderer.domElement);

    // TERÉN
    const terrainGeom = new THREE.PlaneGeometry(100, 100, 40, 40);
    const pos = terrainGeom.attributes.position.array;
    for (let i = 0; i < pos.length; i += 3) {{
        pos[i+2] = (pos[i] * {sklon/100});
    }}
    terrainGeom.computeVertexNormals();
    const terrain = new THREE.Mesh(terrainGeom, new THREE.MeshPhongMaterial({{ color: 0xeeeeee, wireframe: true, transparent: true, opacity: 0.3 }}));
    terrain.rotation.x = -Math.PI / 2;
    scene.add(terrain);

    // AUTOMATICKÁ HRANICE Z API
    const pts = {pts};
    const linePts = pts.map(p => new THREE.Vector3(p[0], (p[0] * {sklon/100}) + 0.1, -p[1]));
    linePts.push(linePts[0]);
    const border = new THREE.Line(new THREE.BufferGeometry().setFromPoints(linePts), new THREE.LineBasicMaterial({{ color: 0xff0000, linewidth: 3 }}));
    scene.add(border);

    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    camera.position.set(40, 40, 40);
    new THREE.OrbitControls(camera, renderer.domElement);
    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=720)
