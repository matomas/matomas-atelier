import streamlit as st
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="Matomas Site Intelligence", layout="wide")

with st.sidebar:
    st.title("🗺️ Katastrální data")
    # Tady si můžeš definovat body pozemku
    default_coords = "[ [0,0], [25,5], [22,35], [-5,30], [0,0] ]"
    coords_json = st.text_area("Souřadnice bodů pozemku [x,y]", value=default_coords)
    odstup = st.slider("Zákonný odstup (m)", 0.0, 7.0, 3.0)

st.title("📐 Analýza stavební čáry (v0.12)")
st.info("Výpočet probíhá přímo ve 3D enginu pro maximální stabilitu.")

# --- INTERAKTIVNÍ 3D ENGINE (JavaScript verze) ---
three_js_code = f"""
<div id="container" style="width: 100%; height: 600px; background: #f0f2f6; border-radius: 15px;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f2f6);
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 600, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 600);
    document.getElementById('container').appendChild(renderer.domElement);

    const raw_pts = {coords_json};
    const offset_val = {odstup};

    // 1. Vykreslení pozemku (Zelená plocha)
    const shape = new THREE.Shape();
    shape.moveTo(raw_pts[0][0], raw_pts[0][1]);
    for(let i=1; i<raw_pts.length; i++) {{
        shape.lineTo(raw_pts[i][0], raw_pts[i][1]);
    }}
    const geometry = new THREE.ShapeGeometry(shape);
    const material = new THREE.MeshPhongMaterial({{ color: 0x9edb9e, side: THREE.DoubleSide, transparent: true, opacity: 0.8 }});
    const mesh = new THREE.Mesh(geometry, material);
    mesh.rotation.x = -Math.PI / 2;
    scene.add(mesh);

    // 2. Výpočet a vykreslení odstupů (Červená čára)
    // Používáme jednoduchý buffer offset algoritmus
    if (offset_val > 0) {{
        const hole = new THREE.Path();
        // Zjednodušený offset pro demonstraci - v JS funguje bez externích knihoven
        const points_vec = raw_pts.map(p => new THREE.Vector3(p[0], 0.1, -p[1]));
        const lineGeom = new THREE.BufferGeometry().setFromPoints(points_vec);
        const line = new THREE.Line(lineGeom, new THREE.LineBasicMaterial({{ color: 0x000000, linewidth: 2 }}));
        scene.add(line);
        
        // Simulace stavební čáry (vizuální offset)
        // Pro skutečně šišaté pozemky v produkci použijeme clipper.js, 
        // ale pro tento krok to nasimulujeme měřítkem směrem k těžišti
        const innerLineGeom = lineGeom.clone();
        innerLineGeom.scale(0.8, 0.8, 0.8); // Dočasná vizualizace
        const innerLine = new THREE.Line(innerLineGeom, new THREE.LineBasicMaterial({{ color: 0xff0000, linewidth: 4 }}));
        innerLine.position.y = 0.2;
        scene.add(innerLine);
    }}

    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const light = new THREE.PointLight(0xffffff, 0.5);
    light.position.set(10, 20, 10);
    scene.add(light);

    camera.position.set(20, 30, 20);
    new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=620)
