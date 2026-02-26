import streamlit as st
import streamlit.components.v1 as components

# --- KONFIGURACE ---
RASTR = 0.625

st.set_page_config(page_title="Matomas Geometrical Correctness", layout="wide")

with st.sidebar:
    st.title("📍 Přesná geometrie")
    # Zkus si schválně změnit body na hodně šišatý tvar
    default_coords = "[ [0,0], [30,5], [25,40], [-10,35], [0,0] ]"
    coords_json = st.text_area("Souřadnice pozemku [x,y]", value=default_coords)
    odstup = st.slider("Zákonný odstup (m)", 0.0, 10.0, 3.0)
    
    st.write("---")
    st.subheader("Dům")
    pos_x = st.slider("X pozice", -30.0, 30.0, 5.0)
    pos_z = st.slider("Z pozice", -30.0, 30.0, 15.0)
    rotace = st.slider("Rotace (°)", 0, 360, 0)

st.title("📐 Geometricky přesný offset a osazení")

three_js_code = f"""
<div id="container" style="width: 100%; height: 600px; background: #f0f2f6; border-radius: 15px;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    // MATEMATICKÁ FUNKCE PRO PŘESNÝ OFFSET (Místo lživého scale)
    function getOffsetPoints(points, distance) {{
        const offsetPoints = [];
        const count = points.length;
        
        for (let i = 0; i < count; i++) {{
            const prev = points[(i - 1 + count) % count];
            const curr = points[i];
            const next = points[(i + 1) % count];

            // Vektory hran
            const v1 = {{ x: curr[0] - prev[0], y: curr[1] - prev[1] }};
            const v2 = {{ x: next[0] - curr[0], y: next[1] - curr[1] }};

            // Normalizace
            const l1 = Math.sqrt(v1.x * v1.x + v1.y * v1.y);
            const l2 = Math.sqrt(v2.x * v2.x + v2.y * v2.y);
            const n1 = {{ x: -v1.y / l1, y: v1.x / l1 }};
            const n2 = {{ x: -v2.y / l2, y: v2.x / l2 }};

            // Průměrná normála pro roh (bisector)
            const nx = (n1.x + n2.x) / 2;
            const ny = (n1.y + n2.y) / 2;
            const nl = Math.sqrt(nx * nx + ny * ny);
            
            // Korekce délky v rozích (aby byl odstup konstantní)
            const cosA = n1.x * nx + n1.y * ny;
            const s = distance / (cosA * nl);

            offsetPoints.push(new THREE.Vector3(curr[0] + nx * s, 0.1, -(curr[1] + ny * s)));
        }}
        return offsetPoints;
    }}

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f2f6);
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 600, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 600);
    document.getElementById('container').appendChild(renderer.domElement);

    const raw_pts = {coords_json};
    const offset_val = {odstup};

    // 1. POZEMEK
    const shape = new THREE.Shape();
    shape.moveTo(raw_pts[0][0], raw_pts[0][1]);
    raw_pts.forEach(p => shape.lineTo(p[0], p[1]));
    const geometry = new THREE.ShapeGeometry(shape);
    const material = new THREE.MeshPhongMaterial({{ color: 0x9edb9e, side: THREE.DoubleSide }});
    const mesh = new THREE.Mesh(geometry, material);
    mesh.rotation.x = -Math.PI / 2;
    scene.add(mesh);

    // 2. PŘESNÝ OFFSET (Červená čára)
    if (offset_val > 0) {{
        const offset_vecs = getOffsetPoints(raw_pts, offset_val);
        const offGeom = new THREE.BufferGeometry().setFromPoints(offset_vecs);
        const offLine = new THREE.LineLoop(offGeom, new THREE.LineBasicMaterial({{ color: 0xff0000, linewidth: 3 }}));
        scene.add(offLine);
    }}

    // 3. DŮM (Tvůj 6m trakt)
    const houseGeom = new THREE.BoxGeometry(6.25, 2.7, 12.5);
    const houseMat = new THREE.MeshPhongMaterial({{ color: 0x3498db, transparent: true, opacity: 0.9 }});
    const house = new THREE.Mesh(houseGeom, houseMat);
    house.position.set({pos_x}, 1.35, -{pos_z});
    house.rotation.y = ({rotace} * Math.PI) / 180;
    scene.add(house);

    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    camera.position.set(20, 40, 20);
    new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=620)
