import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Matomas Real Terrain", layout="wide")

with st.sidebar:
    st.title("🏔️ Realistická morfologie")
    st.subheader("1. Terénní data")
    amplituda = st.slider("Členitost terénu", 0.0, 10.0, 4.0)
    
    st.subheader("2. Osazení domu")
    vyska_nuly = st.slider("Výška 0.000", -5.0, 10.0, 2.0)
    pos_x = st.slider("Pozice X", -20.0, 20.0, 5.0)
    pos_z = st.slider("Pozice Z", -20.0, 20.0, 10.0)

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

    // 1. GENERÁTOR PEVNÉHO TERÉNU (Extrude s morfologií)
    const pts = [[0,0], [30,5], [25,40], [-5,35]]; // Tvar tvé parcely
    const shape = new THREE.Shape();
    shape.moveTo(pts[0][0], pts[0][1]);
    pts.forEach(p => shape.lineTo(p[0], p[1]));
    shape.closePath();

    // Vytvoříme 3D objem (podstavu pozemku)
    const extrudeSettings = {{ depth: 10, bevelEnabled: false }};
    const terrainGeom = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    
    // Ohneme pouze horní plochu podle morfologie
    const posAttr = terrainGeom.attributes.position;
    for (let i = 0; i < posAttr.count; i++) {{
        let x = posAttr.getX(i);
        let y = posAttr.getY(i);
        let z = posAttr.getZ(i);
        
        // Pokud je to horní plocha (z=0 v Extrude), dáme jí výšku podle svahu
        if (z === 0) {{
            let height = (Math.sin(x*0.1) * Math.cos(y*0.1)) * {amplituda} + (y*0.2);
            posAttr.setZ(i, -height); 
        }} else {{
            // Spodek pozemku necháme rovný v hloubce -10
            posAttr.setZ(i, 10);
        }}
    }}
    terrainGeom.computeVertexNormals();

    const terrainMat = new THREE.MeshPhongMaterial({{ color: 0x9edb9e, shininess: 10 }});
    const terrain = new THREE.Mesh(terrainGeom, terrainMat);
    terrain.rotation.x = -Math.PI / 2;
    terrain.receiveShadow = true;
    terrain.castShadow = true;
    scene.add(terrain);

    // 2. HRANICE PARCELY (Černá linka přímo na povrchu)
    const borderPoints = [];
    pts.forEach(p => {{
        let x = p[0];
        let y = p[1];
        let h = (Math.sin(x*0.1) * Math.cos(y*0.1)) * {amplituda} + (y*0.2);
        borderPoints.push(new THREE.Vector3(x, h + 0.05, -y));
    }});
    borderPoints.push(borderPoints[0]);
    const borderLine = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(borderPoints),
        new THREE.LineBasicMaterial({{ color: 0x000000, linewidth: 3 }})
    );
    scene.add(borderLine);

    // 3. DŮM (Zlatý Standard - Pevná hmota)
    const houseGeom = new THREE.BoxGeometry(6.25, 2.7, 12.5);
    const houseMat = new THREE.MeshPhongMaterial({{ color: 0x3498db }});
    const house = new THREE.Mesh(houseGeom, houseMat);
    house.position.set({pos_x}, {vyska_nuly} + 1.35, -{pos_z});
    house.castShadow = true;
    scene.add(house);

    // Světla pro hloubku
    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const sun = new THREE.DirectionalLight(0xffffff, 0.8);
    sun.position.set(20, 50, 10);
    sun.castShadow = true;
    scene.add(sun);

    camera.position.set(40, 40, 40);
    new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=670)
