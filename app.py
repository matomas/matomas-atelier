import streamlit as st
import streamlit.components.v1 as components
import json
from shapely.geometry import Polygon

st.set_page_config(page_title="Matomas Site Intelligence", layout="wide")

with st.sidebar:
    st.title("🗺️ Katastrální data")
    default_coords = "[ [0,0], [25,5], [22,35], [-5,30], [0,0] ]"
    coords_json = st.text_area("Souřadnice bodů [x,y]", value=default_coords)
    odstup_val = st.slider("Zákonný odstup (m)", 2.0, 7.0, 3.0)

# LOGIKA GEOMETRIE (Shapely)
try:
    pts = json.loads(coords_json)
    poly = Polygon(pts)
    
    # Tady se děje to kouzlo: záporný buffer vytvoří vnitřní odstup
    inner_poly = poly.buffer(-odstup_val, join_style=2) # join_style 2 = ostré rohy
    
    # Převedeme zpět na seznam bodů pro Three.js
    if not inner_poly.is_empty:
        inner_pts = list(inner_poly.exterior.coords)
    else:
        inner_pts = []
        st.warning("Odstup je příliš velký, na pozemku nelze stavět!")
except Exception as e:
    st.error(f"Chyba výpočtu: {e}")
    pts = [[0,0], [20,0], [20,20], [0,20]]
    inner_pts = []

st.title("📐 Analýza stavební čáry")

# --- THREE.JS GENERÁTOR ---
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

    // 1. CELÝ POZEMEK (Zelený)
    const pts = {pts};
    const shape = new THREE.Shape();
    shape.moveTo(pts[0][0], pts[0][1]);
    pts.forEach(p => shape.lineTo(p[0], p[1]));
    
    const geom = new THREE.ShapeGeometry(shape);
    const mat = new THREE.MeshBasicMaterial({{ color: 0x9edb9e, side: THREE.DoubleSide }});
    const mesh = new THREE.Mesh(geom, mat);
    mesh.rotation.x = -Math.PI / 2;
    scene.add(mesh);

    // 2. STAVEBNÍ ČÁRA (Červená)
    const i_pts = {inner_pts};
    if (i_pts.length > 0) {{
        const i_points_vec = i_pts.map(p => new THREE.Vector3(p[0], 0.05, -p[1]));
        const i_lineGeom = new THREE.BufferGeometry().setFromPoints(i_points_vec);
        const i_line = new THREE.Line(i_lineGeom, new THREE.LineBasicMaterial({{ color: 0xff0000, linewidth: 3 }}));
        scene.add(i_line);
    }}

    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    camera.position.set(20, 40, 20);
    new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=620)
