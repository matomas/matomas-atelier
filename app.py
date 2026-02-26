import streamlit as st
import streamlit.components.v1 as components

# --- KONFIGURACE ---
RASTR = 0.625
VYSKA_NP = 2.7

st.set_page_config(page_title="Matomas Terrain Engine", layout="wide")

with st.sidebar:
    st.title("⛰️ Morfologie terénu")
    st.write("Nastavte převýšení rohů pozemku (m)")
    z_vlevo_dole = st.slider("Levý dolní roh", -5.0, 5.0, 0.0)
    z_vpravo_dole = st.slider("Pravý dolní roh", -5.0, 5.0, 1.5)
    z_vpravo_nahore = st.slider("Pravý horní roh", -5.0, 5.0, 3.0)
    z_vlevo_nahore = st.slider("Levý horní roh", -5.0, 5.0, 1.0)
    
    st.write("---")
    st.subheader("Osazení domu")
    vyska_osazeni = st.slider("Výškové osazení domu (Z)", -2.0, 5.0, 1.0)
    rotace = st.slider("Rotace (°)", 0, 360, 45)

three_js_code = f"""
<div id="container" style="width: 100%; height: 650px; background: #f0f2f6; border-radius: 15px;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f2f6);
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 650, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 650);
    renderer.shadowMap.enabled = true;
    document.getElementById('container').appendChild(renderer.domElement);

    // 1. TERÉN S MORFOLOGIÍ
    // Vytvoříme mřížku 2x2 segmenty (pro 4 rohy)
    const terrainGeom = new THREE.PlaneGeometry(30, 40, 1, 1);
    const vertices = terrainGeom.attributes.position.array;

    // Přepsání Z souřadnic (v Three.js Plane je to index 2, 5, 8, 11...)
    // Indexy vertexů: 0: vlevo nahoře, 1: vpravo nahoře, 2: vlevo dole, 3: vpravo dole
    vertices[2] = {z_vlevo_nahore};
    vertices[5] = {z_vpravo_nahore};
    vertices[8] = {z_vlevo_dole};
    vertices[11] = {z_vpravo_dole};
    
    terrainGeom.computeVertexNormals(); // Pro správné stínování svahu

    const terrainMat = new THREE.MeshPhongMaterial({{ color: 0x9edb9e, side: THREE.DoubleSide, wireframe: false }});
    const terrain = new THREE.Mesh(terrainGeom, terrainMat);
    terrain.rotation.x = -Math.PI / 2;
    terrain.receiveShadow = true;
    scene.add(terrain);

    // 2. DŮM (Tvůj 6m trakt)
    const houseGeom = new THREE.BoxGeometry(6.25, {VYSKA_NP}, 12.5);
    const houseMat = new THREE.MeshPhongMaterial({{ color: 0x3498db, transparent: true, opacity: 0.9 }});
    const house = new THREE.Mesh(houseGeom, houseMat);
    house.position.set(5, {vyska_osazeni} + ({VYSKA_NP}/2), -15);
    house.rotation.y = ({rotace} * Math.PI) / 180;
    house.castShadow = true;
    scene.add(house);

    // Pomocný Grid (ukazuje absolutní nulu)
    const grid = new THREE.GridHelper(50, 50, 0xaaaaaa, 0xcccccc);
    scene.add(grid);

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const sun = new THREE.DirectionalLight(0xffffff, 0.8);
    sun.position.set(10, 20, 10);
    sun.castShadow = true;
    scene.add(sun);

    camera.position.set(30, 30, 30);
    new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=670)
