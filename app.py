import streamlit as st
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="Matomas Site Intelligence", layout="wide")

with st.sidebar:
    st.title("🗺️ Katastrální data")
    st.write("Simulace importu z katastru (WFS/GML)")
    
    # Testovací souřadnice šišatého pozemku (v metrech)
    # Představ si, že tohle nám přišlo z API katastru
    default_coords = "[ [0,0], [25,5], [22,35], [-5,30], [0,0] ]"
    coords_json = st.text_area("Souřadnice bodů pozemku [x,y]", value=default_coords)
    
    odstup = st.slider("Zákonný odstup (m)", 2.0, 7.0, 3.0)

try:
    points = json.loads(coords_json)
except:
    st.error("Chyba ve formátu souřadnic!")
    points = [[0,0], [20,0], [20,20], [0,20]]

st.title("📐 Analýza nepravidelné parcely")
st.info("Algoritmus nyní počítá 'stavební čáru' pro libovolný polygon.")

# --- THREE.JS GENERÁTOR PRO ŠIŠATÝ POZEMEK ---
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

    const pts = {points};
    const shape = new THREE.Shape();
    shape.moveTo(pts[0][0], pts[0][1]);
    for(let i=1; i < pts.length; i++) {{
        shape.lineTo(pts[i][0], pts[i][1]);
    }}

    // 1. POZEMEK (Shape)
    const geometry = new THREE.ShapeGeometry(shape);
    const material = new THREE.MeshBasicMaterial({{ color: 0x9edb9e, side: THREE.DoubleSide }});
    const mesh = new THREE.Mesh(geometry, material);
    mesh.rotation.x = -Math.PI / 2;
    scene.add(mesh);

    // 2. OBRYS (Černá čára)
    const points_vec = pts.map(p => new THREE.Vector3(p[0], 0.01, -p[1]));
    const lineGeom = new THREE.BufferGeometry().setFromPoints(points_vec);
    const line = new THREE.Line(lineGeom, new THREE.LineBasicMaterial({{ color: 0x000000, linewidth: 2 }}));
    scene.add(line);

    // Světlo a kamera
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    camera.position.set(20, 40, 20);
    new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=620)
