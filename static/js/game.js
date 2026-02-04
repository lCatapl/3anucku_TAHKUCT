// Инициализация Three.js
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth * 0.8, 600);
document.getElementById('tank-preview').appendChild(renderer.domElement);

// Освещение
const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
scene.add(ambientLight);
const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
directionalLight.position.set(1, 1, 1);
scene.add(directionalLight);

// Загрузка танка T-34
const loader = new THREE.GLTFLoader();
let tank;
loader.load('/static/models/t34.gltf', (gltf) => {
    tank = gltf.scene;
    tank.scale.set(2, 2, 2);
    tank.position.set(0, 0, 0);
    scene.add(tank);
    animate();
});

// Анимация
function animate() {
    requestAnimationFrame(animate);
    if (tank) {
        tank.rotation.y += 0.01;
    }
    renderer.render(scene, camera);
}
camera.position.z = 5;

// Управление
const keys = {};
document.addEventListener('keydown', (e) => keys[e.key.toLowerCase()] = true);
document.addEventListener('keyup', (e) => keys[e.key.toLowerCase()] = false);

// SocketIO для мультиплеера
const socket = io();
socket.on('tank_update', (data) => {
    console.log('Танк обновлён:', data);
});
