import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Matomas AI Atelier v0.22", layout="wide")

with st.sidebar:
    st.title("📐 Technické osazení")
    st.subheader("1. Morfologie")
    sklon_x = st.slider("Sklon východ-západ (%)", -20, 20, 5)
    sklon_z = st.slider("Sklon sever-jih (%)", -20, 20, 10)
    
    st.subheader("2. Parametry domu")
    vyska_osazeni = st.slider("Kóta 0.000", -2.0, 5.0, 1.0)
    rotace = st.slider("Rotace (°)", 0, 360, 0)

three_js_code = f"""
<div id="container" style="width: 100%; height: 700px; background: #ffffff; border-radius: 5px; border: 1px solid #ddd;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xfafafa);
    const camera = new THREE.PerspectiveCamera(40, window.innerWidth / 700, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 700);
    renderer.shadowMap.enabled = true;
    document.getElementById('container').appendChild(renderer.domElement);

    // 1. REÁLNÝ TERÉN (Velká plocha s jemnou mřížkou)
    const terrainGeom = new THREE.PlaneGeometry(100, 100, 50, 50);
    const vertices = terrainGeom.attributes.position.array;
    for (let i = 0; i < vertices.length; i += 3) {{
        let x = vertices[i];
        let y = vertices[i + 1];
        // Výška je definována lineárním sklonem (rovina svahu)
        vertices[i + 2] = (x * {sklon_x/100}) + (y * {sklon_z/100});
    }}
    terrainGeom.computeVertexNormals();
    const terrainMat = new THREE.MeshPhongMaterial({{ 
        color: 0xeeeeee, 
        wireframe: true, 
        transparent: true, 
        opacity: 0.3 
    }});
    const terrain = new THREE.Mesh(terrainGeom, terrainMat);
    terrain.rotation.x = -Math.PI / 2;
    terrain.receiveShadow = true;
    scene.add(terrain);

    // 2. HRANICE PARCELY (Promítnutá na svah)
    const parcelPts = [[0,0], [25,2], [23,30], [-5,28], [0,0]];
    const linePts = [];
    parcelPts.forEach(p => {{
        let x = p[0];
        let y = p[1];
        let h = (x * {sklon_x/100}) + (y * {sklon_z/100});
        linePts.push(new THREE.Vector3(x, h + 0.02, -y));
    }});
    const lineGeom = new THREE.BufferGeometry().setFromPoints(linePts);
    const line = new THREE.Line(lineGeom, new THREE.LineBasicMaterial({{ color: 0xff0000, linewidth: 2 }}));
    scene.add(line);

    // 3. DŮM (Tvůj poctivý 6m trakt)
    const houseGeom = new THREE.BoxGeometry(6.25, 2.7, 12.5);
    const houseMat = new THREE.MeshPhongMaterial({{ color: 0x3498db, transparent: true, opacity: 0.9 }});
    const house = new THREE.Mesh(houseGeom, houseMat);
    house.position.set(10, {vyska_osazeni} + 1.35, -15);
    house.rotation.y = ({rotace} * Math.PI) / 180;
    house.castShadow = true;
    scene.add(house);

    // Světla (Architektonické nasvícení)
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
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

components.html(three_js_code, height=720)
