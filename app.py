import streamlit as st
import streamlit.components.v1 as components

# --- KONFIGURACE ---
RASTR = 0.625

st.set_page_config(page_title="Matomas Site Engine", layout="wide")

with st.sidebar:
    st.title("📍 Definice pozemku")
    p_sirka = st.number_input("Šířka pozemku (m)", value=20.0, step=1.0)
    p_delka = st.number_input("Délka pozemku (m)", value=40.0, step=1.0)
    st.header("⚖️ Legislativa")
    odstup = st.slider("Odstup od hranic (m)", 2.0, 5.0, 3.0)
    zastavenost_limit = st.slider("Max. zastavěnost (%)", 10, 50, 30)

# VÝPOČET LIMITŮ
max_sirka_domu = p_sirka - (2 * odstup)
max_delka_domu = p_delka - (2 * odstup)
max_plocha_domu = (p_sirka * p_delka) * (zastavenost_limit / 100)

st.title("📐 Analýza pozemku a Hrubá hmota")
st.write(f"Povolená plocha pro stavbu: **{max_plocha_domu:.1f} m²** | Max. rozměr: **{max_sirka_domu} x {max_delka_domu} m**")

# --- THREE.JS SITE & MASS RENDERER ---
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

    // 1. POZEMEK (Zelená plocha)
    const plotGeom = new THREE.PlaneGeometry({p_sirka}, {p_delka});
    const plotMat = new THREE.MeshBasicMaterial({{ color: 0x9edb9e, side: THREE.DoubleSide }});
    const plot = new THREE.Mesh(plotGeom, plotMat);
    plot.rotation.x = Math.PI / 2;
    scene.add(plot);

    // 2. LIMITNÍ KONTEJNER (Kde se smí stavět - červený obrys)
    const limitGeom = new THREE.PlaneGeometry({max_sirka_domu}, {max_delka_domu});
    const limitEdges = new THREE.EdgesGeometry(limitGeom);
    const limitLine = new THREE.LineSegments(limitEdges, new THREE.LineBasicMaterial({{ color: 0xff0000 }}));
    limitLine.rotation.x = Math.PI / 2;
    limitLine.position.y = 0.05;
    scene.add(limitLine);

    // 3. HRUBÁ HMOTA (Tvoje první kostka)
    const massGeom = new THREE.BoxGeometry(8, 2.7, 12); // Příklad 8x12m
    const massMat = new THREE.MeshPhongMaterial({{ color: 0x3498db, transparent: true, opacity: 0.8 }});
    const mass = new THREE.Mesh(massGeom, massMat);
    mass.position.set(0, 1.35, 0); // Střed na nule, zvednutý o půlku výšky
    scene.add(mass);

    scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    camera.position.set({p_sirka}, 20, {p_delka});
    new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=620)
