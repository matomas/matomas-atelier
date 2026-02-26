import streamlit as st
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="Matomas KN Debugger v0.25", layout="wide")

# Funkce pro normalizaci souřadnic (aby střed pozemku byl [0,0])
def normalize_geometry(points_list):
    if not points_list: return []
    avg_x = sum(p[0] for p in points_list) / len(points_list)
    avg_y = sum(p[1] for p in points_list) / len(points_list)
    return [[round(p[0] - avg_x, 3), round(p[1] - avg_y, 3)] for p in points_list]

with st.sidebar:
    st.title("🔍 Katastrální vyhledávač")
    obec = st.text_input("Obec / K.ú.", value="Nučničky")
    parcela = st.text_input("Parcelní číslo", value="45/104")
    
    if st.button("Načíst z ČÚZK"):
        # Zde by proběhlo reálné volání RÚIAN WFS
        # Simulujeme reálný nepravidelný tvar, který odpovídá KN
        simulated_kn_data = [[-745120.5, -1045200.1], [-745090.2, -1045205.4], [-745095.8, -1045240.2], [-745130.1, -1045235.7]]
        st.session_state['raw_points'] = simulated_kn_data
        st.success("Data načtena.")

    st.write("---")
    st.subheader("🛠️ Geometrický Debugger")
    # Zde vidíš a edituješ body, které přišly z API
    raw_data = st.session_state.get('raw_points', [[0,0], [20,0], [20,20], [0,20]])
    edited_data_str = st.text_area("Body parcely [X, Y]", value=json.dumps(raw_data))
    
    try:
        current_pts = json.loads(edited_data_str)
        display_pts = normalize_geometry(current_pts)
    except:
        st.error("Chyba ve formátu bodů!")
        display_pts = []

    sklon = st.slider("Sklon terénu (%)", -20, 20, 5)

st.title("📐 Analýza parcely z KN (v0.25)")
if not display_pts:
    st.warning("Zadejte platné souřadnice bodů.")
else:
    st.info(f"Zobrazeno {len(display_pts)} lomových bodů parcely. Souřadnice byly normalizovány k těžišti.")

# --- THREE.JS ENGINE ---
three_js_code = f"""
<div id="container" style="width: 100%; height: 700px; background: #ffffff; border-radius: 10px;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xfafafa);
    const camera = new THREE.PerspectiveCamera(40, window.innerWidth / 700, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 700);
    document.getElementById('container').appendChild(renderer.domElement);

    // TERÉN (Mřížka)
    const terrain = new THREE.Mesh(
        new THREE.PlaneGeometry(150, 150, 40, 40),
        new THREE.MeshPhongMaterial({{ color: 0xe0e0e0, wireframe: true, transparent: true, opacity: 0.2 }})
    );
    terrain.rotation.x = -Math.PI / 2;
    scene.add(terrain);

    // PARCELA (Plocha + Obrys)
    const pts = {display_pts};
    const shape = new THREE.Shape();
    shape.moveTo(pts[0][0], pts[0][1]);
    pts.forEach(p => shape.lineTo(p[0], p[1]));
    shape.closePath();

    const parcelGeom = new THREE.ShapeGeometry(shape);
    const parcelMat = new THREE.MeshBasicMaterial({{ color: 0x9edb9e, side: THREE.DoubleSide, transparent: true, opacity: 0.5 }});
    const parcelMesh = new THREE.Mesh(parcelGeom, parcelMat);
    parcelMesh.rotation.x = -Math.PI / 2;
    parcelMesh.position.y = 0.01;
    scene.add(parcelMesh);

    // Červená hranice KN
    const linePts = pts.map(p => new THREE.Vector3(p[0], 0.05, -p[1]));
    linePts.push(linePts[0]);
    const border = new THREE.Line(new THREE.BufferGeometry().setFromPoints(linePts), new THREE.LineBasicMaterial({{ color: 0xff0000, linewidth: 3 }}));
    scene.add(border);

    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    camera.position.set(50, 50, 50);
    new THREE.OrbitControls(camera, renderer.domElement);
    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=720)
