import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Matomas Site Projection", layout="wide")

with st.sidebar:
    st.title("🏗️ Projekt na terénu")
    st.subheader("1. Tvar parcely")
    coords_raw = st.text_area("Body pozemku [x,y]", value="[[0,0], [30,5], [25,40], [-10,35]]")
    
    st.subheader("2. Výškový profil")
    sklon = st.slider("Intenzita svahu", 0.0, 5.0, 1.5)
    
    st.subheader("3. Osazení domu")
    vyska_nuly = st.slider("Výška 0.000 (m.n.m)", 405.0, 415.0, 410.0)
    pos_x = st.slider("X", -15.0, 15.0, 5.0)
    pos_z = st.slider("Z", -20.0, 20.0, 15.0)

three_js_code = f"""
<div id="container" style="width: 100%; height: 650px; background: #000; border-radius: 15px;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 650, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 650);
    document.getElementById('container').appendChild(renderer.domElement);

    const pts = {coords_raw};
    const segments = 25;

    // 1. GENERÁTOR TERÉNU VE TVARU POZEMKU (Shape + Extrude na Mesh)
    const shape = new THREE.Shape();
    shape.moveTo(pts[0][0], pts[0][1]);
    pts.forEach(p => shape.lineTo(p[0], p[1]));
    shape.closePath();

    // Vytvoříme geometrii a ručně jí ohneme podle "DMR"
    const terrainGeom = new THREE.ShapeBufferGeometry(shape, 20);
    const posAttr = terrainGeom.attributes.position;
    
    for (let i = 0; i < posAttr.count; i++) {{
        let x = posAttr.getX(i);
        let y = posAttr.getY(i);
        // MATEMATIKA SVAHU: Výška Z je určena pozicí na parcele
        let z = (Math.sin(x*0.1) + (y*0.2)) * {sklon};
        posAttr.setZ(i, z);
    }}
    terrainGeom.computeVertexNormals();

    const terrainMat = new THREE.MeshPhongMaterial({{ color: 0x228B22, wireframe: true, side: THREE.DoubleSide }});
    const terrain = new THREE.Mesh(terrainGeom, terrainMat);
    terrain.rotation.x = -Math.PI / 2;
    scene.add(terrain);

    // 2. PROPSÁNÍ HRANIC (Vektorová čára kopírující terén)
    const borderPoints = [];
    pts.forEach(p => {{
        let x = p[0];
        let y = p[1];
        let z = (Math.sin(x*0.1) + (y*0.2)) * {sklon};
        borderPoints.push(new THREE.Vector3(x, z + 0.1, -y));
    }});
    borderPoints.push(borderPoints[0]); // Uzavřít loop
    
    const borderGeom = new THREE.BufferGeometry().setFromPoints(borderPoints);
    const borderLine = new THREE.Line(borderGeom, new THREE.LineBasicMaterial({{ color: 0xffffff, linewidth: 2 }}));
    scene.add(borderLine);

    // 3. DŮM (Zlatý Standard)
    const houseGeom = new THREE.BoxGeometry(6.25, 2.7, 12.5);
    const houseMat = new THREE.MeshPhongMaterial({{ color: 0x3498db, transparent: true, opacity: 0.8 }});
    const house = new THREE.Mesh(houseGeom, houseMat);
    house.position.set({pos_x}, {vyska_nuly} - 410 + 1.35, -{pos_z});
    scene.add(house);

    // Pomocná mřížka absolutní nuly
    scene.add(new THREE.GridHelper(100, 20, 0x444444, 0x222222));

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const sun = new THREE.DirectionalLight(0xffffff, 0.8);
    sun.position.set(10, 50, 10);
    scene.add(sun);

    camera.position.set(40, 40, 40);
    new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=670)
