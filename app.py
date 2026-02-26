import streamlit as st
import streamlit.components.v1 as components

# --- KONFIGURACE ---
RASTR = 0.625
VYSKA = 2.7

st.set_page_config(page_title="Matomas 3D Realtime", layout="wide")

with st.sidebar:
    st.title("🧱 Parametry 3D")
    mod_x = st.slider("Délka (moduly)", 10, 32, 20)
    mod_y = st.slider("Šířka (moduly)", 8, 16, 10)
    
    sirka = round(mod_y * RASTR, 3)
    delka = round(mod_x * RASTR, 3)

st.title("🧊 Interaktivní 3D Model (Three.js)")
st.write(f"Rozměr: {sirka} x {delka} m | Výška: {VYSKA} m")

# --- THREE.JS INTEGRACE ---
# Tento kód vytvoří v prohlížeči skutečné 3D prostředí
three_js_code = f"""
<div id="container" style="width: 100%; height: 500px; background: #eeeeee; border-radius: 10px;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xeeeeee);
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / 500, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 500);
    document.getElementById('container').appendChild(renderer.domElement);

    // Světla
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(5, 10, 7.5).normalize();
    scene.add(light);
    scene.add(new THREE.AmbientLight(0x404040));

    // DŮM (Box)
    const geometry = new THREE.BoxGeometry({sirka}, {VYSKA}, {delka});
    const material = new THREE.MeshPhongMaterial({{ color: 0x3498db, transparent: true, opacity: 0.8, edgeColor: 0x000000 }});
    const house = new THREE.Mesh(geometry, material);
    house.position.y = {VYSKA}/2;
    scene.add(house);

    // Drátěný model (Edges)
    const edges = new THREE.EdgesGeometry(geometry);
    const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({{ color: 0x000000 }}));
    line.position.y = {VYSKA}/2;
    scene.add(line);

    // Země (Rastr)
    const grid = new THREE.GridHelper(20, 20);
    scene.add(grid);

    camera.position.set({sirka}*2, {VYSKA}*2, {delka}*2);
    const controls = new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }}
    animate();
</script>
"""

components.html(three_js_code, height=520)

st.info("💡 Myší můžete modelem otáčet a kolečkem zoomovat.")
