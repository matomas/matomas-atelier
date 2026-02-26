import streamlit as st
import streamlit.components.v1 as components

# --- TVŮJ ZLATÝ STANDARD ---
RASTR = 0.625
SIRKA_DOMU = 10 * RASTR  # 6.25 m
DELKA_DOMU = 20 * RASTR  # 12.5 m
VYSKA_DOMU = 2.7

st.set_page_config(page_title="Matomas Precision Engine", layout="wide")

with st.sidebar:
    st.title("📏 Přesné osazení")
    # Zkus si klidně zadat reálnou parcelu
    coords_raw = st.text_area("Body pozemku [x,y]", value="[[0,0], [30,5], [25,40], [-10,35]]")
    odstup = st.slider("Odstup (m)", 0.0, 10.0, 3.0)
    
    st.write("---")
    st.subheader("Manipulace s domem")
    pos_x = st.slider("Posun X", -40.0, 40.0, 10.0)
    pos_z = st.slider("Posun Z", -40.0, 40.0, 15.0)
    rotace = st.slider("Rotace domu (°)", 0, 360, 45)

# --- ENGINE ---
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
    document.getElementById('container').appendChild(renderer.domElement);

    const pts = {coords_raw};
    
    // 1. POZEMEK (Správně uzavřený)
    const shape = new THREE.Shape();
    shape.moveTo(pts[0][0], pts[0][1]);
    for(let i=1; i < pts.length; i++) shape.lineTo(pts[i][0], pts[i][1]);
    shape.closePath();
    
    const plotGeom = new THREE.ShapeGeometry(shape);
    const plotMat = new THREE.MeshPhongMaterial({{ color: 0x9edb9e, side: THREE.DoubleSide }});
    const plotMesh = new THREE.Mesh(plotGeom, plotMat);
    plotMesh.rotation.x = -Math.PI / 2;
    scene.add(plotMesh);

    // 2. STAVEBNÍ ČÁRA (Geometrický Offset)
    function getOffsetPath(points, dist) {{
        const result = [];
        const len = points.length;
        for (let i = 0; i < len; i++) {{
            const p1 = points[(i + len - 1) % len];
            const p2 = points[i];
            const p3 = points[(i + 1) % len];

            const v1 = {{ x: p2[0]-p1[0], y: p2[1]-p1[1] }};
            const v2 = {{ x: p3[0]-p2[0], y: p3[1]-p2[1] }};
            
            const mag1 = Math.sqrt(v1.x**2 + v1.y**2);
            const mag2 = Math.sqrt(v2.x**2 + v2.y**2);
            
            const n1 = {{ x: -v1.y/mag1, y: v1.x/mag1 }};
            const n2 = {{ x: -v2.y/mag2, y: v2.x/mag2 }};
            
            const bisectorX = n1.x + n2.x;
            const bisectorY = n1.y + n2.y;
            const bMag = Math.sqrt(bisectorX**2 + bisectorY**2);
            const scale = dist / ( (n1.x * bisectorX + n1.y * bisectorY) / bMag );
            
            result.push(new THREE.Vector3(p2[0] + (bisectorX/bMag)*scale, 0.1, -(p2[1] + (bisectorY/bMag)*scale)));
        }}
        return result;
    }}

    const offsetPts = getOffsetPath(pts, {odstup});
    const offGeom = new THREE.BufferGeometry().setFromPoints(offsetPts);
    const offLine = new THREE.LineLoop(offGeom, new THREE.LineBasicMaterial({{ color: 0xff0000, linewidth: 3 }}));
    scene.add(offLine);

    // 3. DŮM (Pevný kvádr - nezkreslený)
    const houseGeom = new THREE.BoxGeometry({SIRKA_DOMU}, {VYSKA_DOMU}, {DELKA_DOMU});
    const houseMat = new THREE.MeshPhongMaterial({{ color: 0x3498db, transparent: true, opacity: 0.85 }});
    const house = new THREE.Mesh(houseGeom, houseMat);
    
    // Pozicování
    house.position.set({pos_x}, {VYSKA_DOMU}/2, -{pos_z});
    house.rotation.y = ({rotace} * Math.PI) / 180;
    scene.add(house);

    // Světla a Grid
    scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const pLight = new THREE.PointLight(0xffffff, 0.5);
    pLight.position.set(20, 50, 20);
    scene.add(pLight);
    scene.add(new THREE.GridHelper(100, 100, 0xcccccc, 0xdddddd));

    camera.position.set(40, 50, 40);
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    
    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=670)
