import streamlit as st
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="Matomas Real Site v0.26", layout="wide")

# Funkce pro opravu S-JTSK (převod na lokální metry)
def fix_k_u_nucnicky_geometry(raw_pts):
    if not raw_pts: return []
    # Najdeme min/max pro vystředění, ale zachování tvaru
    xs = [p[0] for p in raw_pts]
    ys = [p[1] for p in raw_pts]
    offset_x = min(xs) + (max(xs) - min(xs)) / 2
    offset_y = min(ys) + (max(ys) - min(ys)) / 2
    # Vracíme body relativně k centru, zachováváme poměry
    return [[round(p[0] - offset_x, 3), round(p[1] - offset_y, 3)] for p in raw_pts]

with st.sidebar:
    st.title("📍 Katastr Nučničky")
    st.info("K. ú. Nučničky (707015), p. č. 45/104")
    
    # TEXTOVÉ POLE PRO TVÁ REÁLNÁ DATA
    # Tady můžeš smazat tuhle simulaci a vložit body, které máš z KN
    input_data = st.text_area("Vložte seznam bodů [X, Y] z KN:", 
        value="[[0, 0], [15.2, 2.1], [14.5, 28.3], [-5.4, 25.1]]", 
        height=150)
    
    try:
        raw_points = json.loads(input_data)
        display_pts = fix_k_u_nucnicky_geometry(raw_points)
    except:
        st.error("Neplatný formát dat.")
        display_pts = []

    st.write("---")
    st.subheader("Technika")
    vyska_000 = st.slider("Výškové osazení (m)", -5.0, 10.0, 1.0)
    rotace_domu = st.slider("Natočení domu (°)", 0, 360, 0)

st.title("📐 Realistický pozemek 45/104")

# --- THREE.JS ENGINE ---
three_js_code = f"""
<div id="container" style="width: 100%; height: 750px; background: #ffffff; border: 1px solid #ddd;"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xfafafa);
    const camera = new THREE.PerspectiveCamera(40, window.innerWidth / 750, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, 750);
    renderer.shadowMap.enabled = true;
    document.getElementById('container').appendChild(renderer.domElement);

    const pts = {display_pts};

    // 1. POZEMEK (Zelený polygon)
    if (pts.length > 2) {{
        const shape = new THREE.Shape();
        shape.moveTo(pts[0][0], pts[0][1]);
        pts.forEach(p => shape.lineTo(p[0], p[1]));
        shape.closePath();

        const parcel = new THREE.Mesh(
            new THREE.ShapeGeometry(shape),
            new THREE.MeshPhongMaterial({{ color: 0x81c784, side: THREE.DoubleSide, transparent: true, opacity: 0.6 }})
        );
        parcel.rotation.x = -Math.PI / 2;
        parcel.receiveShadow = true;
        scene.add(parcel);

        // Červená hranice (KN standard)
        const linePts = pts.map(p => new THREE.Vector3(p[0], 0.05, -p[1]));
        linePts.push(linePts[0]);
        const border = new THREE.Line(
            new THREE.BufferGeometry().setFromPoints(linePts),
            new THREE.LineBasicMaterial({{ color: 0xd32f2f, linewidth: 3 }})
        );
        scene.add(border);
    }}

    // 2. TVŮJ DŮM (Zlatý standard 12.5 x 6.25m)
    const house = new THREE.Mesh(
        new THREE.BoxGeometry(6.25, 2.7, 12.5),
        new THREE.MeshPhongMaterial({{ color: 0x1976d2, transparent: true, opacity: 0.8 }})
    );
    house.position.set(0, 1.35 + {vyska_000}, 0);
    house.rotation.y = ({rotace_domu} * Math.PI) / 180;
    house.castShadow = true;
    scene.add(house);

    // Mřížka pro měřítko (po 1 metru)
    const grid = new THREE.GridHelper(100, 100, 0xdddddd, 0xeeeeee);
    scene.add(grid);

    scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const sun = new THREE.DirectionalLight(0xffffff, 0.9);
    sun.position.set(30, 60, 30);
    sun.castShadow = true;
    scene.add(sun);

    camera.position.set(40, 40, 40);
    new THREE.OrbitControls(camera, renderer.domElement);
    function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
    animate();
</script>
"""

components.html(three_js_code, height=770)
