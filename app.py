import streamlit as st
import streamlit.components.v1 as components
import numpy as np # Teď už ho budeme potřebovat pro práci s maticí výšek

st.set_page_config(page_title="Matomas Terrain Pro", layout="wide")

# SIMULACE IMPORTU Z ČÚZK (DMR 5G)
# V reálu tohle pole naplníme daty z API volání
def generate_real_terrain(size):
    # Simulujeme reálný kopec s proláklinou
    x = np.linspace(0, 5, size)
    y = np.linspace(0, 5, size)
    X, Y = np.meshgrid(x, y)
    Z = np.sin(X) * np.cos(Y) * 3  # Tady budou reálná data z výškopisu
    return Z.flatten().tolist()

with st.sidebar:
    st.title("🏗️ Technická morfologie")
    st.write("Data z digitálního modelu reliéfu (DMR)")
    sklon = st.slider("Celkový sklon svahu (%)", 0, 30, 10)
    vyska_osazeni = st.slider("Osazení 1.NP (m.n.m.)", 350.0, 450.0, 410.0)

# Příprava dat pro JS
size = 21 # mřížka 21x21 bodů
terrain_data = generate_real_terrain(size)

three_js_code = f"""
<div id="container" style="width: 100%; height: 650px; background: #f0f2f6; border-radius: 15px;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 650, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 650);
    renderer.shadowMap.enabled = true;
    document.getElementById('container').appendChild(renderer.domElement);

    // TERÉN Z MATICE (DMR simulace)
    const geometry = new THREE.PlaneGeometry(40, 40, {size-1}, {size-1});
    const vertices = geometry.attributes.position.array;
    const heights = {terrain_data};

    for (let i = 0; i < heights.length; i++) {{
        // Každému bodu mřížky přiřadíme výšku z importu + sklon svahu
        const slopeOffset = (i / {size}) * ({sklon} / 10);
        vertices[i * 3 + 2] = heights[i] + slopeOffset;
    }}
    geometry.computeVertexNormals();

    const material = new THREE.MeshPhongMaterial({{ color: 0x91cf91, wireframe: true }});
    const terrain = new THREE.Mesh(geometry, material);
    terrain.rotation.x = -Math.PI / 2;
    terrain.receiveShadow = true;
    scene.add(terrain);

    // DŮM - 0.000 (Zlatý Standard)
    const houseGeom = new THREE.BoxGeometry(6.25, 2.7, 12.5);
    const houseMat = new THREE.MeshPhongMaterial({{ color: 0x3498db }});
    const house = new THREE.Mesh(houseGeom, houseMat);
    // Výškově dům sedí na uživatelské kótě (relativně k terénu)
    house.position.set(0, 1.35 + ({vyska_osazeni} - 410), 0);
    house.castShadow = true;
    scene.add(house);

    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const sun = new THREE.DirectionalLight(0xffffff, 0.8);
    sun.position.set(20, 50, 20);
    sun.castShadow = true;
    scene.add(sun);

    camera.position.set(40, 40, 40);
    new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=670)
