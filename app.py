import streamlit as st
import streamlit.components.v1 as components

# Definujeme tloušťky (mezery mezi prostory)
TL_PRICKA = 0.125
TL_NOSNA = 0.250
RASTR = 0.625

st.set_page_config(page_title="Matomas Volume Engine", layout="wide")

# --- ADMIN / VSTUPY ---
with st.sidebar:
    st.title("📦 Skladba prostorů")
    mod_obivak_x = st.slider("Obývák délka (moduly)", 8, 20, 12)
    mod_loznice_x = st.slider("Ložnice délka (moduly)", 6, 12, 8)
    sirka_traktu = st.slider("Šířka traktu (moduly)", 8, 16, 10)

# Přepočet na metry
sirka = sirka_traktu * RASTR
d_obivak = mod_obivak_x * RASTR
d_loznice = mod_loznice_x * RASTR

# LOGIKA MEZERY: Mezi obývákem a ložnicí je nosná zeď
pos_loznice = d_obivak + TL_NOSNA 

# --- THREE.JS VOLUME RENDERER ---
three_js_code = f"""
<div id="container" style="width: 100%; height: 600px; background: #1a1a1a; border-radius: 15px;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 600, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 600);
    document.getElementById('container').appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(5, 10, 7);
    scene.add(light);

    // FUNKCE PRO PROSTOR (ROOM)
    function createRoom(w, l, h, x, z, color, name) {{
        const geom = new THREE.BoxGeometry(w, h, l);
        const mat = new THREE.MeshPhongMaterial({{ color: color, transparent: true, opacity: 0.6 }});
        const room = new THREE.Mesh(geom, mat);
        room.position.set(x, h/2, z);
        scene.add(room);

        // Hrany (vizualizace stěn)
        const edges = new THREE.EdgesGeometry(geom);
        const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({{ color: 0xffffff }}));
        line.position.set(x, h/2, z);
        scene.add(line);
    }}

    // SKLÁDÁNÍ PROSTORŮ (Místnosti)
    // Obývák (střed na [0, 0, d_obivak/2])
    createRoom({sirka}, {d_obivak}, 2.7, 0, {d_obivak}/2, 0xffcc00, "Obývák");

    // Ložnice (posunutá o délku obýváku + MEZERA/STĚNA)
    createRoom({sirka}, {d_loznice}, 2.7, 0, {d_obivak} + {TL_NOSNA} + {d_loznice}/2, 0x00ffcc, "Ložnice");

    // GRID
    scene.add(new THREE.GridHelper(30, 30, 0x444444, 0x222222));
    camera.position.set(15, 10, 15);
    const controls = new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{ requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=620)
