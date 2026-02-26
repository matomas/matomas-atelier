import streamlit as st
import streamlit.components.v1 as components

# --- KONFIGURACE ---
RASTR = 0.625
VYSKA = 2.7

st.set_page_config(page_title="Matomas 3D Dispozice", layout="wide")

with st.sidebar:
    st.title("🧱 Parametry")
    mod_x = st.slider("Délka (moduly)", 16, 32, 24)
    mod_y = st.slider("Šířka (moduly)", 10, 16, 12)
    pomer_denni = st.slider("Denní zóna (%)", 40, 60, 50) / 100
    
    sirka = round(mod_y * RASTR, 3)
    delka = round(mod_x * RASTR, 3)
    
    # Výpočet pozice hlavní příčky
    moduly_denni = round((delka * pomer_denni) / RASTR)
    pos_pricka = moduly_denni * RASTR

st.title("🏠 3D Náhled Dispozice")
st.write(f"Trakt: {sirka}m | Denní část: {pos_pricka}m | Noční část: {round(delka - pos_pricka, 2)}m")

# --- THREE.JS S VNITŘNÍMI STĚNAMI ---
three_js_html = f"""
<div id="three-container" style="width: 100%; height: 600px; background: #f0f2f6; border-radius: 15px;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f2f6);
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 600, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 600);
    document.getElementById('three-container').appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(10, 20, 10);
    scene.add(dirLight);

    // FUNKCE PRO TVORBU STĚN
    function createWall(w, h, d, x, y, z, color=0xcccccc, opacity=1) {{
        const geom = new THREE.BoxGeometry(w, h, d);
        const mat = new THREE.MeshPhongMaterial({{ color: color, transparent: opacity < 1, opacity: opacity }});
        const mesh = new THREE.Mesh(geom, mat);
        mesh.position.set(x, y, z);
        scene.add(mesh);
        
        const edges = new THREE.EdgesGeometry(geom);
        const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({{ color: 0x000000 }}));
        line.position.set(x, y, z);
        scene.add(line);
    }}

    // 1. OBVODOVÉ STĚNY (Průhledné pro náhled dovnitř)
    createWall({sirka}, {VYSKA}, {delka}, 0, {VYSKA}/2, 0, 0x3498db, 0.2);

    // 2. HLAVNÍ DĚLÍCÍ PŘÍČKA (Zlatý Standard)
    createWall({sirka}, {VYSKA}, 0.25, 0, {VYSKA}/2, -{delka}/2 + {pos_pricka});

    // 3. CHODBA (svislá v noční zóně)
    const sirka_chodby = {2 * RASTR};
    const delka_nocni = {delka} - {pos_pricka};
    createWall(0.125, {VYSKA}, delka_nocni, {sirka}/2 - sirka_chodby, {VYSKA}/2, {delka}/2 - delka_nocni/2);

    // 4. PODLAHA (Rastr)
    const grid = new THREE.GridHelper(30, 30, 0x888888, 0xcccccc);
    scene.add(grid);

    camera.position.set({sirka}*2, {VYSKA}*2, {delka}*2);
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    
    function animate() {{
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }}
    animate();
</script>
"""

components.html(three_js_html, height=620)
