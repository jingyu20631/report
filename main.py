import streamlit as st
import streamlit.components.v1 as components

# 페이지 기본 설정
st.set_page_config(
    page_title="문시후 피하기 3D - Horror Game",
    page_icon="😱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 공포 테마 커스텀 CSS
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #030303 !important;
        color: #ff3333;
        font-family: 'Courier New', Courier, monospace;
    }
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
    }
    h1 {
        text-align: center;
        color: #ff0000 !important;
        text-shadow: 0px 0px 15px #ff0000;
        letter-spacing: 5px;
        margin-bottom: 5px;
    }
    .stButton>button {
        width: 100%;
        background-color: #330000;
        color: #ff4d4d;
        border: 2px solid #ff0000;
        font-weight: bold;
        padding: 12px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #ff0000;
        color: #000000;
        box-shadow: 0px 0px 20px #ff0000;
    }
    </style>
""", unsafe_allow_html=True)

st.title("👁️ 문시후 피하기 3D")

# 사이드바 설정
st.sidebar.header("⚙️ 게임 난이도")
difficulty = st.sidebar.select_slider(
    "난이도 선택",
    options=["쉬움", "보통", "어려움", "광기"],
    value="보통"
)

speed_map = {"쉬움": 0.035, "보통": 0.05, "어려움": 0.07, "광기": 0.09}
monster_speed = speed_map[difficulty]

st.caption("🔦 화면을 클릭하면 3D 시점이 고정됩니다. (마우스로 시야 회전, WASD로 이동)")

# Three.js 3D 공포 게임 엔진 HTML/JS
game_3d_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background-color: #000;
            overflow: hidden;
            font-family: monospace;
            user-select: none;
        }}
        #gameContainer {{
            position: relative;
            width: 100vw;
            height: 100vh;
        }}
        #uiOverlay {{
            position: absolute;
            top: 20px;
            left: 20px;
            color: #ffffff;
            font-size: 18px;
            text-shadow: 0 0 8px #000, 0 0 3px #ff0000;
            pointer-events: none;
            z-index: 10;
        }}
        #crosshair {{
            position: absolute;
            top: 50%;
            left: 50%;
            width: 8px;
            height: 8px;
            background: rgba(255, 255, 255, 0.4);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            pointer-events: none;
            z-index: 10;
        }}
        #startScreen {{
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.85);
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            z-index: 20;
        }}
        #startBtn {{
            padding: 16px 36px;
            font-size: 22px;
            background: #990000;
            color: #fff;
            border: 2px solid #ff0000;
            cursor: pointer;
            font-weight: bold;
            box-shadow: 0 0 20px #ff0000;
            border-radius: 4px;
        }}
        #startBtn:hover {{
            background: #ff0000;
            color: #000;
        }}
        #jumpscare {{
            display: none;
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background-color: #000;
            z-index: 100;
            justify-content: center;
            align-items: center;
            flex-direction: column;
        }}
        #jumpscareImg {{
            width: 85%;
            height: 85%;
            object-fit: contain;
            animation: shake 0.08s infinite alternate;
            filter: drop-shadow(0 0 30px #ff0000) contrast(180%);
        }}
        #jumpscareText {{
            color: #ff0000;
            font-size: 32px;
            font-weight: bold;
            margin-top: 15px;
            text-shadow: 0 0 15px #ff0000;
        }}
        @keyframes shake {{
            0% {{ transform: translate(5px, 5px) scale(1.02) rotate(0deg); }}
            50% {{ transform: translate(-5px, -5px) scale(1.08) rotate(-2deg); }}
            100% {{ transform: translate(5px, -3px) scale(1.05) rotate(2deg); }}
        }}
    </style>
    <!-- Three.js CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>

<div id="gameContainer">
    <div id="crosshair"></div>
    <div id="uiOverlay">
        ⏱️ 생존 시간: <span id="timer">0.0</span>초 | 🔋 손전등: <span id="battery">100</span>%
    </div>

    <div id="startScreen">
        <button id="startBtn" onclick="initGame()">3D 생존 시작 (클릭)</button>
    </div>

    <div id="jumpscare">
        <img id="jumpscareImg" src="l_2016090101000023300336701.jpg" alt="Moon Sihoo Jumpscare">
        <div id="jumpscareText">문시후에게 잡혔습니다...</div>
    </div>
</div>

<script>
let scene, camera, renderer, flashlight, ambientLight;
let monsterMesh, batteryMesh;
let moveForward = false, moveBackward = false, moveLeft = false, moveRight = false;
let prevTime = performance.now();
let velocity = new THREE.Vector3();
let direction = new THREE.Vector3();

let gameRunning = false;
let startTime = 0;
let batteryPower = 100;
let monsterSpeed = {monster_speed};

// 웹 오디오 엔진
let audioCtx = null;
let lastHeartbeat = 0;

function initAudio() {{
    if (!audioCtx) {{
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }}
}}

function playHeartbeat(dist) {{
    if (!audioCtx || !gameRunning) return;
    let normDist = Math.max(0, Math.min(1, dist / 25));
    let osc = audioCtx.createOscillator();
    let gain = audioCtx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(70 - normDist * 30, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(25, audioCtx.currentTime + 0.12);

    gain.gain.setValueAtTime(0.8 * (1 - normDist * 0.75), audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.12);

    osc.connect(gain);
    gain.connect(audioCtx.destination);

    osc.start();
    osc.stop(audioCtx.currentTime + 0.12);
}}

function playJumpscareSound() {{
    if (!audioCtx) return;
    let osc = audioCtx.createOscillator();
    let gain = audioCtx.createGain();

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(120, audioCtx.currentTime);
    osc.frequency.linearRampToValueAtTime(800, audioCtx.currentTime + 0.4);

    gain.gain.setValueAtTime(1.0, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 1.5);

    osc.connect(gain);
    gain.connect(audioCtx.destination);

    osc.start();
    osc.stop(audioCtx.currentTime + 1.5);
}}

// Pointer Lock (1인칭 마우스 시점)
let yaw = 0, pitch = 0;
function setupPointerLock() {{
    document.body.requestPointerLock = document.body.requestPointerLock || document.body.mozRequestPointerLock;
    document.body.requestPointerLock();
}}

document.addEventListener('mousemove', (e) => {{
    if (document.pointerLockElement === document.body) {{
        yaw -= e.movementX * 0.0025;
        pitch -= e.movementY * 0.0025;
        pitch = Math.max(-Math.PI / 2.5, Math.min(Math.PI / 2.5, pitch));

        camera.rotation.order = "YXZ";
        camera.rotation.y = yaw;
        camera.rotation.x = pitch;
    }}
}});

function initGame() {{
    initAudio();
    setupPointerLock();
    document.getElementById('startScreen').style.display = 'none';
    document.getElementById('jumpscare').style.display = 'none';

    // 씬 생성
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x020202);
    scene.fog = new THREE.FogExp2(0x020202, 0.08); // 짙은 공포 안개

    // 카메라는 플레이어 시점
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 1.6, 0); // 눈높이

    // 렌더러
    renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    
    const container = document.getElementById('gameContainer');
    if (container.querySelector('canvas')) {{
        container.querySelector('canvas').remove();
    }}
    container.appendChild(renderer.domElement);

    // 조명 (손전등)
    flashlight = new THREE.SpotLight(0xffffff, 2.5, 20, Math.PI / 5, 0.4, 1);
    flashlight.castShadow = true;
    camera.add(flashlight);
    flashlight.position.set(0, 0, 1);
    flashlight.target = camera;
    scene.add(camera);

    ambientLight = new THREE.AmbientLight(0x110505, 0.2); // 아주 미세한 붉은 암광
    scene.add(ambientLight);

    // 미로/방 공간 벽면 생성
    buildMap();

    // 문시후 (image3.jpeg) 3D 빌보드 메쉬
    const textureLoader = new THREE.TextureLoader();
    textureLoader.load('l_2016090101000023300336701.jpg', (texture) => {{
        const monsterMat = new THREE.MeshBasicMaterial({{ map: texture, side: THREE.DoubleSide }});
        const monsterGeo = new THREE.PlaneGeometry(2.2, 2.2);
        monsterMesh = new THREE.Mesh(monsterGeo, monsterMat);
        spawnMonster();
        scene.add(monsterMesh);
    }}, undefined, () => {{
        // 이미지 로드 실패 시 대체 빨간 얼굴 메쉬
        const canvas = document.createElement('canvas');
        canvas.width = 256; canvas.height = 256;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#ff0000'; ctx.fillRect(0,0,256,256);
        ctx.fillStyle = '#000000'; ctx.fillText('문시후', 80, 128);
        const texture = new THREE.CanvasTexture(canvas);
        const monsterMat = new THREE.MeshBasicMaterial({{ map: texture }});
        monsterMesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), monsterMat);
        spawnMonster();
        scene.add(monsterMesh);
    }});

    // 3D 배터리 아이템
    const batGeo = new THREE.BoxGeometry(0.4, 0.6, 0.4);
    const batMat = new THREE.MeshBasicMaterial({{ color: 0x00ffaa }});
    batteryMesh = new THREE.Mesh(batGeo, batMat);
    spawnBattery();
    scene.add(batteryMesh);

    // 키보드 이벤트
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('keyup', onKeyUp);

    batteryPower = 100;
    startTime = Date.now();
    gameRunning = true;
    prevTime = performance.now();

    animate();
}}

function buildMap() {{
    // 바닥
    const floorGeo = new THREE.PlaneGeometry(60, 60);
    const floorMat = new THREE.MeshStandardMaterial({{ color: 0x111111, roughness: 0.8 }});
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    scene.add(floor);

    // 천장
    const ceilMat = new THREE.MeshStandardMaterial({{ color: 0x050505 }});
    const ceil = new THREE.Mesh(floorGeo, ceilMat);
    ceil.position.y = 4;
    ceil.rotation.x = Math.PI / 2;
    scene.add(ceil);

    // 외곽 벽
    const wallMat = new THREE.MeshStandardMaterial({{ color: 0x221111 }});
    const wallGeo = new THREE.BoxGeometry(60, 4, 1);

    const wallN = new THREE.Mesh(wallGeo, wallMat); wallN.position.set(0, 2, -30); scene.add(wallN);
    const wallS = new THREE.Mesh(wallGeo, wallMat); wallS.position.set(0, 2, 30); scene.add(wallS);
    const wallE = new THREE.Mesh(wallGeo, wallMat); wallE.rotation.y = Math.PI/2; wallE.position.set(30, 2, 0); scene.add(wallE);
    const wallW = new THREE.Mesh(wallGeo, wallMat); wallW.rotation.y = Math.PI/2; wallW.position.set(-30, 2, 0); scene.add(wallW);
}}

function spawnMonster() {{
    if (!monsterMesh) return;
    monsterMesh.position.set((Math.random() - 0.5) * 40, 1.3, (Math.random() - 0.5) * 40);
}}

function spawnBattery() {{
    batteryMesh.position.set((Math.random() - 0.5) * 35, 0.4, (Math.random() - 0.5) * 35);
}}

function onKeyDown(e) {{
    switch (e.code) {{
        case 'KeyW': case 'ArrowUp': moveForward = true; break;
        case 'KeyS': case 'ArrowDown': moveBackward = true; break;
        case 'KeyA': case 'ArrowLeft': moveLeft = true; break;
        case 'KeyD': case 'ArrowRight': moveRight = true; break;
    }}
}}

function onKeyUp(e) {{
    switch (e.code) {{
        case 'KeyW': case 'ArrowUp': moveForward = false; break;
        case 'KeyS': case 'ArrowDown': moveBackward = false; break;
        case 'KeyA': case 'ArrowLeft': moveLeft = false; break;
        case 'KeyD': case 'ArrowRight': moveRight = false; break;
    }}
}}

function animate() {{
    if (!gameRunning) return;

    requestAnimationFrame(animate);

    const time = performance.now();
    const delta = (time - prevTime) / 1000;
    prevTime = time;

    // 생존 시간 업데이트
    let now = Date.now();
    let surv = ((now - startTime) / 1000).toFixed(1);
    document.getElementById('timer').innerText = surv;

    // 플레이어 이동 조작
    direction.z = Number(moveForward) - Number(moveBackward);
    direction.x = Number(moveRight) - Number(moveLeft);
    direction.normalize();

    const speed = 4.5;
    if (moveForward || moveBackward) camera.translateZ(-direction.z * speed * delta);
    if (moveLeft || moveRight) camera.translateX(direction.x * speed * delta);
    camera.position.y = 1.6; // Y축 고정

    // 벽 경계 충돌
    camera.position.x = Math.max(-28, Math.min(28, camera.position.x));
    camera.position.z = Math.max(-28, Math.min(28, camera.position.z));

    // 문시후 추적 AI
    if (monsterMesh) {{
        // 플레이어를 향해 상시 회전 (빌보드 효과)
        monsterMesh.lookAt(camera.position);

        let dx = camera.position.x - monsterMesh.position.x;
        let dz = camera.position.z - monsterMesh.position.z;
        let dist = Math.hypot(dx, dz);

        monsterMesh.position.x += (dx / dist) * monsterSpeed;
        monsterMesh.position.z += (dz / dist) * monsterSpeed;

        // 심장 소리
        if (now - lastHeartbeat > Math.max(160, dist * 60)) {{
            playHeartbeat(dist);
            lastHeartbeat = now;
        }}

        // 충돌 체크 (잡혔을 때)
        if (dist < 1.4) {{
            gameOver();
            return;
        }}
    }}

    // 손전등 배터리 감소 및 조명 업데이트
    batteryPower -= 0.04;
    if (batteryPower < 0) batteryPower = 0;
    document.getElementById('battery').innerText = Math.round(batteryPower);
    flashlight.intensity = (batteryPower / 100) * 2.5;

    // 배터리 획득
    let batDist = camera.position.distanceTo(batteryMesh.position);
    if (batDist < 1.5) {{
        batteryPower = Math.min(100, batteryPower + 40);
        spawnBattery();
    }}
    batteryMesh.rotation.y += 0.03; // 배터리 회전 연출

    renderer.render(scene, camera);
}}

function gameOver() {{
    gameRunning = false;
    document.exitPointerLock();
    playJumpscareSound();
    document.getElementById('jumpscare').style.display = 'flex';

    setTimeout(() => {{
        document.getElementById('startScreen').style.display = 'flex';
        document.getElementById('startBtn').innerText = '다시 3D 생존 도전';
    }}, 2500);
}}

window.addEventListener('resize', () => {{
    if (camera && renderer) {{
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }}
}});
</script>
</body>
</html>
"""

# Streamlit 3D 화면 임베딩 (전체화면 비율)
components.html(game_3d_html, height=580)

# 하단 게임 조작 안내
st.markdown("""
### 🎮 3D 게임 조작법
- **시점 고정**: 화면의 **[3D 생존 시작]** 버튼을 클릭하면 3D 시점 고정이 활성화됩니다.
- **이동**: `W`, `A`, `S`, `D` 또는 `방향키`
- **시선 이동**: 마우스를 움직여 360도 3D 화면 둘러보기
- **시점 해제**: `Esc` 키
- **생존 핵심**:
  - `image3.jpeg` 메쉬로 형상화된 **문시후**가 어둠 속에서 상시 추적해 옵니다.
  - 거리별로 달라지는 **3D 심장 소리**로 위치를 예측하세요.
  - 맵 위에 떠 있는 **초록색 3D 배터리 상자**를 주워 손전등 불빛을 유지하십시오.
""")
