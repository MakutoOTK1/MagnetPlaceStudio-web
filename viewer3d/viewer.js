// Visor 3D de MagnetPlace Studio.
//
// Portado del simulador de referencia (three.js r160) y ampliado con lo que
// aquel no tenía: el **árbol de tiempo** de la inserción de imanes. El G-code
// que llega ya lleva el bloque insertado, y Python indica en qué líneas empieza
// y acaba, de modo que cada movimiento cae en una de tres fases:
//
//   0 — la pieza imprimiéndose hasta la parada `M400 U1`
//   1 — los movimientos de recogida y colocación de los imanes
//   2 — la pieza reanudándose y cerrándose sobre ellos
//
// El truco que hace barata la animación es el de la referencia: `extrIndex` es
// una suma acumulada que traduce "índice de movimiento" → "cuántos cordones
// dibujar", así que mostrar la escena hasta el instante T es fijar
// `extrudeMesh.count` (o el `drawRange` de las líneas). Coste constante.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { parseGcode, setFeatureTable, getFeatureTable, MV } from './gcode_parser.js';

// ============================================================
//  Constantes
// ============================================================
const BED_X = 256, BED_Y = 256, BED_Z = 256;
const NOZ_WX = 0, NOZ_WZ = 5;
const FIL_AREA = Math.PI * 0.875 * 0.875;   // filamento de 1.75 mm
const LINE_MODE_THRESHOLD = 400000;         // más cordones que esto → modo líneas

const PHASE_COLORS = [0x6f7ea0, 0xf0a726, 0x35c07a];
const MAGNET_COLORS = { red: 0xe23b3b, blue: 0x2b6cff };
const PALETTE = ['#00c16a', '#e63946', '#3a86ff', '#ffbe0b', '#f1f1f1', '#9d4edd', '#ff6d00', '#26241f'];

// Placa gris, a juego con la vista 2D de la app.
const PLATE_COLOR = 0x6e747e;
const PLATE_EDGE = 0x4a4f58;

const $ = (id) => document.getElementById(id);
let T = {};                                  // textos traducidos (los manda Python)
const tr = (k, fallback) => (T[k] !== undefined ? T[k] : (fallback !== undefined ? fallback : k));

// ============================================================
//  Escena
// ============================================================
const container = $('canvas-container');
// `high-performance` evita que en portátiles con gráfica híbrida el navegador
// cambie de GPU a mitad de sesión: ese cambio recrea el contexto y se ve como
// un parpadeo de la escena entera.
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(container.clientWidth, container.clientHeight);
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x181b26);
scene.fog = new THREE.Fog(0x181b26, 900, 2000);

// El plano cercano NO puede ser 0.1: con far=5000 el búfer de profundidad se
// reparte de forma tan desigual que a ~400 mm de la cámara dos superficies
// separadas menos de ~0.1 mm ya no se distinguen, y la rejilla (z=0.08), el
// borde de la placa y la primera capa se pelean por el mismo píxel — eso es el
// parpadeo al orbitar. Con near=0.5 el margen baja a ~0.02 mm y desaparece.
const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.5, 5000);
camera.position.set(330, 300, 330);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.target.set(0, 60, 0);
controls.maxDistance = 1500;
controls.minDistance = 5;   // por debajo, el plano cercano empezaría a recortar

scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const dl = new THREE.DirectionalLight(0xffffff, 1.1); dl.position.set(200, 400, 150); scene.add(dl);
const dl2 = new THREE.DirectionalLight(0x88aaff, 0.35); dl2.position.set(-200, 150, -200); scene.add(dl2);

// El G-code trabaja con Z arriba; three.js con Y arriba. Dentro de
// `printerWorld` un punto (px,py,pz) del G-code cae en (px, pz, -py) de mundo,
// así que toda la geometría se puede volcar con coordenadas crudas.
const printerWorld = new THREE.Group();
printerWorld.rotation.x = -Math.PI / 2;
scene.add(printerWorld);

const bedOrigin = new THREE.Group();
bedOrigin.position.set(-BED_X / 2, -BED_Y / 2, 0);
printerWorld.add(bedOrigin);

// --- placa, rejilla, volumen y ejes ---
const volumeGroup = new THREE.Group();
bedOrigin.add(volumeGroup);

const procPlate = new THREE.Mesh(
  new THREE.BoxGeometry(BED_X + 14, BED_Y + 14, 4),
  // La primera capa se imprime a 0.2 mm de la cara superior de la placa. El
  // desplazamiento de polígono empuja la placa un pelo hacia atrás en
  // profundidad para que nunca compita con esos cordones ni con la rejilla.
  new THREE.MeshStandardMaterial({
    color: PLATE_COLOR, roughness: 0.7, metalness: 0.2,
    polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
  })
);
procPlate.position.set(BED_X / 2, BED_Y / 2, -2.01);
bedOrigin.add(procPlate);

const plateEdge = new THREE.LineSegments(
  new THREE.EdgesGeometry(new THREE.BoxGeometry(BED_X + 14, BED_Y + 14, 4)),
  new THREE.LineBasicMaterial({ color: PLATE_EDGE })
);
plateEdge.position.copy(procPlate.position);
bedOrigin.add(plateEdge);

{
  const gv = [];
  const gz = 0.08;
  for (let i = 0; i <= BED_X; i += 16) gv.push(i, 0, gz, i, BED_Y, gz);
  for (let j = 0; j <= BED_Y; j += 16) gv.push(0, j, gz, BED_X, j, gz);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(gv, 3));
  volumeGroup.add(new THREE.LineSegments(g, new THREE.LineBasicMaterial({
    color: 0x9aa2b0, transparent: true, opacity: 0.45,
  })));

  const box = new THREE.EdgesGeometry(new THREE.BoxGeometry(BED_X, BED_Y, BED_Z));
  const volBox = new THREE.LineSegments(box, new THREE.LineBasicMaterial({
    color: 0x35a2ff, transparent: true, opacity: 0.3,
  }));
  volBox.position.set(BED_X / 2, BED_Y / 2, BED_Z / 2);
  volumeGroup.add(volBox);

  const mkAxis = (x, y, z, color) => {
    const g2 = new THREE.BufferGeometry();
    g2.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0.2, x, y, z + 0.2], 3));
    volumeGroup.add(new THREE.Line(g2, new THREE.LineBasicMaterial({ color })));
  };
  mkAxis(34, 0, 0, 0xff4444);
  mkAxis(0, 34, 0, 0x44ff44);
  mkAxis(0, 0, 34, 0x4488ff);
}

// --- contenedores de imanes ---
// Los dos depósitos de donde la máquina recoge los imanes: 22 x 22 mm, fuera
// del área de impresión, pegados al borde derecho de la cama y centrados en
// altura, primero el rojo y luego el azul. Cuelgan de `bedOrigin` para que
// acompañen a la cama cuando se desliza, igual que la pieza.
const CONTAINER_SIZE = 22;
{
  const orden = ['red', 'blue'];
  const y0 = BED_Y / 2;
  orden.forEach((color, i) => {
    const x = BED_X + CONTAINER_SIZE * (i + 0.5);
    const caja = new THREE.Mesh(
      new THREE.BoxGeometry(CONTAINER_SIZE, CONTAINER_SIZE, 3),
      new THREE.MeshStandardMaterial({
        color: MAGNET_COLORS[color], roughness: 0.55, metalness: 0.15,
      })
    );
    caja.position.set(x, y0, 1.5);
    bedOrigin.add(caja);

    const borde = new THREE.LineSegments(
      new THREE.EdgesGeometry(caja.geometry),
      new THREE.LineBasicMaterial({ color: 0x1b1b1b, transparent: true, opacity: 0.55 })
    );
    borde.position.copy(caja.position);
    bedOrigin.add(borde);
  });
}

// --- cabezal esquemático (se oculta cuando está el modelo real) ---
const toolhead = new THREE.Group();
{
  const nozzle = new THREE.Mesh(
    new THREE.ConeGeometry(2.2, 6, 20),
    new THREE.MeshStandardMaterial({ color: 0x00c16a, roughness: 0.4, metalness: 0.3 })
  );
  nozzle.rotation.x = Math.PI;
  nozzle.position.y = 3;
  toolhead.add(nozzle);
  const body = new THREE.Mesh(
    new THREE.BoxGeometry(16, 12, 18),
    new THREE.MeshStandardMaterial({ color: 0x3a4652, roughness: 0.7 })
  );
  body.position.y = 15;
  toolhead.add(body);
}
printerWorld.add(toolhead);

const gantry = new THREE.Mesh(
  new THREE.BoxGeometry(BED_X + 60, 7, 7),
  new THREE.MeshStandardMaterial({ color: 0x242e37, roughness: 0.8 })
);
printerWorld.add(gantry);

// ============================================================
//  Modelo real de la impresora (GLB)
// ============================================================
let printerModel = null;
let modelParts = null;

new GLTFLoader().load(
  './printer_a1.glb',
  setupPrinterModel,
  undefined,
  (err) => { console.warn('No se pudo cargar el modelo de la impresora:', err); }
);

function setupPrinterModel(gltf) {
  const root = new THREE.Group();
  // La superficie de la placa del modelo está a +83.8 mm; se baja hasta y=0,
  // que es el plano de la cama virtual (Z=0 del G-code).
  root.position.set(0, -83.8, 0);
  scene.add(root);

  const parts = {
    bed: new THREE.Group(), head: new THREE.Group(),
    xaxis: new THREE.Group(), static: new THREE.Group(),
  };
  Object.values(parts).forEach((g) => root.add(g));

  const src = gltf.scene;
  src.scale.setScalar(1000);   // el GLB viene en metros; la escena está en mm
  root.add(src);
  src.updateMatrixWorld(true);

  const meshes = [];
  src.traverse((o) => { if (o.isMesh) meshes.push(o); });
  for (const m of meshes) {
    const n = (m.name || '').toLowerCase();
    let target = parts.static;
    if (n.includes('toolhead')) target = parts.head;
    else if (n.includes('x axis') || n.includes('x_axis')) target = parts.xaxis;
    else if (n.includes('heatbed') || n.includes('buildplate')) target = parts.bed;
    if (m.material) {
      m.material = m.material.clone();   // el GLB comparte materiales entre mallas
      m.material.side = THREE.DoubleSide;
      if ('metalness' in m.material) {
        m.material.metalness = Math.min(m.material.metalness, 0.55);
        m.material.roughness = Math.max(m.material.roughness, 0.4);
      }
      // La placa extraíble del modelo viene en un marrón dorado (#473a06). Se
      // tiñe del mismo gris que la vista 2D para que la cama se reconozca
      // igual en los dos modos.
      if (n.includes('buildplate') && m.material.color) {
        m.material.color.setHex(PLATE_COLOR);
        m.material.metalness = 0.2;
        m.material.roughness = 0.7;
      }
    }
    target.attach(m);   // attach() conserva la transformación de mundo
  }
  root.remove(src);

  printerModel = root;
  modelParts = parts;
  applyModelVisibility();
  updateKinematics(lastHead.x, lastHead.y, lastHead.z);
}

function applyModelVisibility() {
  const on = printerModel && $('chkModel').checked;
  if (printerModel) printerModel.visible = !!on;
  // El cabezal esquemático y el real son mutuamente excluyentes.
  toolhead.visible = !on;
  gantry.visible = !on;
  procPlate.visible = !on;
  plateEdge.visible = !on;
}

// --- cinemática de bedslinger (A1): la boquilla no se mueve en Y de mundo,
//     es la cama entera (con la pieza) la que se desliza. ---
const lastHead = { x: BED_X / 2, y: BED_Y / 2, z: 170 };

function updateKinematics(hx, hy, hz) {
  lastHead.x = hx; lastHead.y = hy; lastHead.z = hz;
  const S = hy - BED_Y / 2 + NOZ_WZ;
  bedOrigin.position.y = -BED_Y / 2 - S;
  toolhead.position.set(hx - BED_X / 2 - NOZ_WX, -NOZ_WZ, hz);
  gantry.position.set(0, 22, hz + 24);
  if (modelParts) {
    modelParts.bed.position.z = S;
    modelParts.head.position.set(hx - BED_X / 2 - NOZ_WX, hz, 0);
    modelParts.xaxis.position.y = hz;
  }
  showCoords(hx, hy, hz);
}

// --- lectura de coordenadas (esquina superior izquierda) ---------------------
// Son las de la boquilla en el sistema de la máquina, las mismas que llevan las
// líneas G1 del archivo; no las de mundo de three.js (donde en un bedslinger lo
// que se mueve en Y es la cama).
const _coordEls = { x: $('posX'), y: $('posY'), z: $('posZ') };
const _coordShown = { x: null, y: null, z: null };

function showCoords(hx, hy, hz) {
  for (const [axis, v] of [['x', hx], ['y', hy], ['z', hz]]) {
    const txt = (Number.isFinite(v) ? v : 0).toFixed(2);
    // Escribir en el DOM 60 veces por segundo obliga a recalcular la caja; se
    // toca solo cuando el texto cambia de verdad.
    if (_coordShown[axis] === txt) continue;
    _coordShown[axis] = txt;
    if (_coordEls[axis]) _coordEls[axis].textContent = txt;
  }
}

// ============================================================
//  Estado de la simulación
// ============================================================
const sim = {
  moves: [],
  cumTime: null, extrIndex: null, travIndex: null,
  layerOfMove: null, phaseOfMove: null,
  layerZ: [], layerEndMove: [],
  segW: null, segH: null,
  phaseRange: [],       // [{first,last,t0,t1}] por fase
  magnets: [],          // {x,y,z,d,h,color,moveIdx,mesh}
  totalTime: 0, time: 0, playing: false,
  filColors: PALETTE, minFeed: 1, maxFeed: 1,
  hasMagnetBlock: false,
};

let extrudeMesh = null, extrudeLines = null, travelLines = null;
let magnetGroup = null;
let lastIdx = -1;

// ============================================================
//  Carga
// ============================================================
// El G-code llega por URL (mps://app/current-N.gcode) y no dentro del mensaje:
// un archivo real son decenas de MB y no tiene sentido meterlos en un fuente JS.
async function loadFromPayload(payload) {
  let text = payload.gcode;
  if (text === undefined && payload.gcodeUrl) {
    const resp = await fetch(payload.gcodeUrl);
    if (!resp.ok) throw new Error('no se pudo leer el G-code: ' + resp.status);
    text = await resp.text();
  }
  loadPayload(payload, text || '');
}

function loadPayload(payload, gcodeText) {
  if (payload.i18n) T = payload.i18n;
  if (payload.features) setFeatureTable(payload.features);
  applyStaticTexts();

  const parsed = parseGcode(gcodeText);
  buildTables(parsed, payload);
  buildMagnets(parsed, payload);
  rebuildExtrusionVisual();
  applyColors();
  buildLegend();
  updatePhaseBar();

  $('hint').classList.add('hidden');
  $('banner').classList.toggle('hidden', sim.hasMagnetBlock);
  if (!sim.hasMagnetBlock) $('banner').textContent = tr('v3d.no_pause');

  frameOnPart();
  setTime(0);
  setPlaying(sim.moves.length > 0);
  notify('loaded', { moves: sim.moves.length, layers: sim.layerZ.length, time: sim.totalTime });
}

function buildTables(parsed, payload) {
  const moves = parsed.moves;
  const n = moves.length;
  sim.moves = moves;
  sim.cumTime = new Float64Array(n);
  sim.extrIndex = new Uint32Array(n);
  sim.travIndex = new Uint32Array(n);
  sim.layerOfMove = new Uint32Array(n);
  sim.phaseOfMove = new Uint8Array(n);
  sim.layerZ = [];
  sim.layerEndMove = [];
  sim.filColors = (parsed.colors && parsed.colors.length) ? parsed.colors : PALETTE;

  // Fases: el bloque de imanes va de `markStart` a `markEnd` (índices de línea
  // que calcula Python al ensamblar el archivo). Sin bloque, todo es fase 0.
  const ms = Number.isInteger(payload.markStart) ? payload.markStart : -1;
  const me = Number.isInteger(payload.markEnd) ? payload.markEnd : -1;
  sim.hasMagnetBlock = ms >= 0 && me >= ms;

  const useComment = moves.some((m) => m[MV.LAYER_MARK] >= 0);
  let curLayerZ = -Infinity, curMark = -2;
  let t = 0, ne = 0, nt = 0;
  let minFeed = Infinity, maxFeed = 0;

  for (let i = 0; i < n; i++) {
    const m = moves[i];
    t += m[MV.TIME];
    sim.cumTime[i] = t;

    const line = m[MV.LINE];
    sim.phaseOfMove[i] = !sim.hasMagnetBlock ? 0 : (line < ms ? 0 : (line <= me ? 1 : 2));

    if (m[MV.EXTRUDE]) {
      ne++;
      const newLayer = useComment
        ? (m[MV.LAYER_MARK] !== curMark)
        : (m[MV.Z2] > curLayerZ + 1e-4);
      if (newLayer) {
        curMark = m[MV.LAYER_MARK];
        curLayerZ = m[MV.Z2];
        sim.layerZ.push(curLayerZ);
        sim.layerEndMove.push(i);
      }
      const f = m[MV.FEED];
      if (f < minFeed) minFeed = f;
      if (f > maxFeed) maxFeed = f;
    } else {
      nt++;
    }
    sim.extrIndex[i] = ne;
    sim.travIndex[i] = nt;
    sim.layerOfMove[i] = Math.max(0, sim.layerZ.length - 1);
    if (sim.layerEndMove.length) sim.layerEndMove[sim.layerEndMove.length - 1] = i;
  }

  sim.totalTime = t;
  sim.minFeed = isFinite(minFeed) ? minFeed : 1;
  sim.maxFeed = maxFeed || 1;

  computeBeadSizes(ne);
  computePhaseRanges();
  buildTravelLines(nt);
  setupLayerSlider();
}

// Ancho y alto de cada cordón a partir del caudal de E (sección rectangular).
function computeBeadSizes(nExtrude) {
  const moves = sim.moves;
  sim.segW = new Float32Array(nExtrude);
  sim.segH = new Float32Array(nExtrude);

  const diffs = [];
  for (let k = 1; k < sim.layerZ.length; k++) {
    const d = sim.layerZ[k] - sim.layerZ[k - 1];
    if (d > 0.04 && d < 1.5) diffs.push(d);
  }
  diffs.sort((a, b) => a - b);
  const typLH = diffs.length ? diffs[diffs.length >> 1] : 0.2;

  let seg = 0;
  for (let i = 0; i < moves.length; i++) {
    const m = moves[i];
    if (!m[MV.EXTRUDE]) continue;
    const k = sim.layerOfMove[i];
    let h = k > 0 ? sim.layerZ[k] - sim.layerZ[k - 1] : Math.min(sim.layerZ[0] || typLH, 0.5);
    if (!(h > 0.04) || h > 1.5) h = typLH;
    const dist = Math.hypot(m[MV.X2] - m[MV.X1], m[MV.Y2] - m[MV.Y1], m[MV.Z2] - m[MV.Z1]);
    let w = (m[MV.DELTA_E] * FIL_AREA) / (dist * h);
    if (!isFinite(w) || w <= 0) w = 0.45;
    sim.segW[seg] = Math.min(1.5, Math.max(0.15, w));
    sim.segH[seg] = h;
    seg++;
  }
}

function computePhaseRanges() {
  sim.phaseRange = [0, 1, 2].map(() => null);
  for (let i = 0; i < sim.moves.length; i++) {
    const p = sim.phaseOfMove[i];
    if (!sim.phaseRange[p]) sim.phaseRange[p] = { first: i, last: i, t0: i > 0 ? sim.cumTime[i - 1] : 0, t1: sim.cumTime[i] };
    else { sim.phaseRange[p].last = i; sim.phaseRange[p].t1 = sim.cumTime[i]; }
  }
}

function buildTravelLines(nTravel) {
  if (travelLines) {
    bedOrigin.remove(travelLines);
    travelLines.geometry.dispose(); travelLines.material.dispose();
    travelLines = null;
  }
  if (!nTravel) return;
  const pos = new Float32Array(nTravel * 6);
  let k = 0;
  for (let i = 0; i < sim.moves.length; i++) {
    const m = sim.moves[i];
    if (m[MV.EXTRUDE]) continue;
    pos[k++] = m[MV.X1]; pos[k++] = m[MV.Y1]; pos[k++] = m[MV.Z1];
    pos[k++] = m[MV.X2]; pos[k++] = m[MV.Y2]; pos[k++] = m[MV.Z2];
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setDrawRange(0, 0);
  travelLines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({
    color: 0x2f8f5b, transparent: true, opacity: 0.28,
  }));
  travelLines.frustumCulled = false;
  travelLines.visible = $('chkTravel').checked;
  bedOrigin.add(travelLines);
}

// --- cilindros de imán: aparecen cuando la secuencia los deposita ---
function buildMagnets(parsed, payload) {
  if (magnetGroup) {
    bedOrigin.remove(magnetGroup);
    magnetGroup.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
  }
  magnetGroup = new THREE.Group();
  bedOrigin.add(magnetGroup);
  sim.magnets = [];

  const list = payload.magnets || [];
  if (!list.length) return;

  // El comentario "; Imán N (color)" y el "FIN CÍRCULOS CONCÉNTRICOS" que le
  // sigue acotan el bloque de cada imán: queda puesto al terminar el asentado.
  const marks = parsed.magnetMarks || [];
  for (let i = 0; i < list.length; i++) {
    const spec = list[i];
    const mark = marks[i];
    const placedLine = mark ? mark.placedLine : -1;
    const moveIdx = placedLine >= 0 ? firstMoveAtLine(placedLine) : 0;

    const d = Math.max(0.5, spec.d || 5);
    const h = Math.max(0.2, spec.h || 3);
    const geo = new THREE.CylinderGeometry(d / 2, d / 2, h, 32);
    geo.rotateX(Math.PI / 2);   // el eje del cilindro pasa de Y a Z (Z arriba aquí)
    const mat = new THREE.MeshStandardMaterial({
      color: MAGNET_COLORS[spec.color] || MAGNET_COLORS.red,
      roughness: 0.35, metalness: 0.65,
    });
    const mesh = new THREE.Mesh(geo, mat);
    // El imán se asienta con su cara superior a ras de la capa de la pausa.
    mesh.position.set(spec.x, spec.y, (spec.z || 0) - h / 2);
    mesh.visible = false;
    // Etiqueta del polo que mira hacia arriba, sobre la cara superior.
    mesh.add(poleLabel(spec.polarity || 'N', d, h));
    magnetGroup.add(mesh);
    sim.magnets.push({ ...spec, d, h, moveIdx, mesh });
  }
}

/**
 * Encuadra la cámara sobre la pieza.
 *
 * Una pieza de 30 mm en una cama de 256 se queda en unos pocos píxeles con la
 * cámara por defecto, así que se apunta a su centro y se acerca en proporción
 * a su tamaño. El tope inferior de distancia evita meter la cámara dentro de
 * la impresora: la gracia es ver la máquina construyendo la pieza, no solo la
 * pieza.
 */
function frameOnPart() {
  let minX = Infinity, minY = Infinity, minZ = Infinity;
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
  for (const m of sim.moves) {
    if (!m[MV.EXTRUDE]) continue;
    minX = Math.min(minX, m[MV.X1], m[MV.X2]); maxX = Math.max(maxX, m[MV.X1], m[MV.X2]);
    minY = Math.min(minY, m[MV.Y1], m[MV.Y2]); maxY = Math.max(maxY, m[MV.Y1], m[MV.Y2]);
    minZ = Math.min(minZ, m[MV.Z1], m[MV.Z2]); maxZ = Math.max(maxZ, m[MV.Z1], m[MV.Z2]);
  }
  if (!isFinite(minX)) return;

  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2, cz = (minZ + maxZ) / 2;
  const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 10);
  // La cama se desplaza en Y al animar, así que el objetivo se fija en el
  // marco de mundo con la cama centrada (que es donde arranca la simulación).
  // El objetivo se sube un poco por encima de la pieza: durante la secuencia
  // el cabezal trepa hasta Z≈240 a recoger los imanes, y si se encuadra a ras
  // de la cama esa parte del movimiento se sale del cuadro.
  const target = new THREE.Vector3(cx - BED_X / 2, cz + 55, -(cy - BED_Y / 2));
  const dist = Math.min(900, Math.max(330, size * 3.2));

  const dir = camera.position.clone().sub(controls.target);
  if (dir.lengthSq() < 1e-6) dir.set(1, 0.9, 1);
  dir.normalize();
  controls.target.copy(target);
  camera.position.copy(target).addScaledVector(dir, dist);
  controls.update();
}

/** Letra del polo (N/S) pintada sobre la cara superior del imán. */
function poleLabel(letter, diameter, height) {
  const size = 64;
  const cv = document.createElement('canvas');
  cv.width = cv.height = size;
  const ctx = cv.getContext('2d');
  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 44px "Segoe UI", system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(letter, size / 2, size / 2 + 2);

  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  const plane = new THREE.Mesh(
    new THREE.PlaneGeometry(diameter * 0.7, diameter * 0.7),
    new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false })
  );
  // Justo por encima de la tapa, mirando hacia arriba (Z+ en este marco).
  plane.position.set(0, 0, height / 2 + 0.02);
  return plane;
}

function firstMoveAtLine(line) {
  const moves = sim.moves;
  let lo = 0, hi = moves.length - 1, ans = moves.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (moves[mid][MV.LINE] >= line) { ans = mid; hi = mid - 1; } else lo = mid + 1; }
  return Math.max(0, ans);
}

// ============================================================
//  Geometría de los cordones
// ============================================================
const _dummy = new THREE.Object3D();
const _dir = new THREE.Vector3();
const _AXIS_X = new THREE.Vector3(1, 0, 0);

function setInstanceTransform(segIdx, m, frac, track = true) {
  const w = sim.segW[segIdx], h = sim.segH[segIdx];
  const dx = m[MV.X2] - m[MV.X1], dy = m[MV.Y2] - m[MV.Y1], dz = m[MV.Z2] - m[MV.Z1];
  const ex = m[MV.X1] + dx * frac, ey = m[MV.Y1] + dy * frac, ez = m[MV.Z1] + dz * frac;
  const len = Math.hypot(dx, dy, dz) * frac;
  // La Z del G-code es el techo del cordón, de ahí el -h/2.
  _dummy.position.set((m[MV.X1] + ex) / 2, (m[MV.Y1] + ey) / 2, (m[MV.Z1] + ez) / 2 - h / 2);
  _dir.set(dx, dy, dz);
  if (_dir.lengthSq() > 1e-12) { _dir.normalize(); _dummy.quaternion.setFromUnitVectors(_AXIS_X, _dir); }
  else _dummy.quaternion.identity();
  // Un solape longitudinal pequeño mantiene las esquinas continuas.
  _dummy.scale.set(Math.max(len + Math.min(w, h) * 0.5, 0.02), w, h);
  _dummy.updateMatrix();
  extrudeMesh.setMatrixAt(segIdx, _dummy.matrix);
  if (track) {
    const attr = extrudeMesh.instanceMatrix;
    if (attr.addUpdateRange) attr.addUpdateRange(segIdx * 16, 16);
    else if (attr.updateRange) { attr.updateRange.offset = segIdx * 16; attr.updateRange.count = 16; }
    attr.needsUpdate = true;
  }
}

function rebuildExtrusionVisual() {
  if (extrudeMesh) {
    bedOrigin.remove(extrudeMesh);
    extrudeMesh.geometry.dispose(); extrudeMesh.material.dispose();
    extrudeMesh = null;
  }
  if (extrudeLines) {
    bedOrigin.remove(extrudeLines);
    extrudeLines.geometry.dispose(); extrudeLines.material.dispose();
    extrudeLines = null;
  }
  const ne = sim.segW ? sim.segW.length : 0;
  if (!ne) return;

  if (ne <= LINE_MODE_THRESHOLD) {
    const geo = new THREE.BoxGeometry(1, 1, 1);
    const mat = new THREE.MeshStandardMaterial({ roughness: 0.55, metalness: 0.05 });
    extrudeMesh = new THREE.InstancedMesh(geo, mat, ne);
    extrudeMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    extrudeMesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(ne * 3), 3);
    extrudeMesh.frustumCulled = false;
    extrudeMesh.count = 0;
    let seg = 0;
    for (let i = 0; i < sim.moves.length; i++) {
      const m = sim.moves[i];
      if (!m[MV.EXTRUDE]) continue;
      setInstanceTransform(seg++, m, 1, false);
    }
    extrudeMesh.instanceMatrix.needsUpdate = true;
    bedOrigin.add(extrudeMesh);
  } else {
    const pos = new Float32Array(ne * 6);
    let k = 0;
    for (let i = 0; i < sim.moves.length; i++) {
      const m = sim.moves[i];
      if (!m[MV.EXTRUDE]) continue;
      pos[k++] = m[MV.X1]; pos[k++] = m[MV.Y1]; pos[k++] = m[MV.Z1];
      pos[k++] = m[MV.X2]; pos[k++] = m[MV.Y2]; pos[k++] = m[MV.Z2];
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(ne * 6), 3));
    g.setDrawRange(0, 0);
    extrudeLines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ vertexColors: true }));
    extrudeLines.frustumCulled = false;
    bedOrigin.add(extrudeLines);
  }
}

function applyColors() {
  const mode = $('colorMode').value;
  const table = getFeatureTable();
  const c = new THREE.Color();
  const nLayers = Math.max(1, sim.layerZ.length - 1);
  const span = Math.max(1e-6, sim.maxFeed - sim.minFeed);
  const colorAttr = extrudeLines ? extrudeLines.geometry.getAttribute('color') : null;

  let seg = 0;
  for (let i = 0; i < sim.moves.length; i++) {
    const m = sim.moves[i];
    if (!m[MV.EXTRUDE]) continue;
    if (mode === 'feature') {
      const f = m[MV.FEATURE];
      const entry = (f >= 0 && f < table.length) ? table[f] : table[table.length - 1];
      c.set(entry && entry.color ? entry.color : '#9aa7b3');
    } else if (mode === 'phase') {
      c.setHex(PHASE_COLORS[sim.phaseOfMove[i]]);
    } else if (mode === 'layer') {
      const t = sim.layerOfMove[i] / nLayers;
      c.setHSL(0.62 - 0.62 * t, 0.85, 0.42 + 0.18 * t);
    } else {
      const t = (m[MV.FEED] - sim.minFeed) / span;
      c.setHSL(0.66 - 0.66 * t, 0.9, 0.5);
    }
    if (extrudeMesh) extrudeMesh.setColorAt(seg, c);
    else if (colorAttr) {
      colorAttr.setXYZ(seg * 2, c.r, c.g, c.b);
      colorAttr.setXYZ(seg * 2 + 1, c.r, c.g, c.b);
    }
    seg++;
  }
  if (extrudeMesh && extrudeMesh.instanceColor) extrudeMesh.instanceColor.needsUpdate = true;
  if (colorAttr) colorAttr.needsUpdate = true;
}

function buildLegend() {
  const mode = $('colorMode').value;
  const box = $('legend');
  box.innerHTML = '';
  const add = (color, label) => {
    const s = document.createElement('span');
    s.innerHTML = `<i class="swatch" style="background:${color}"></i>${label}`;
    box.appendChild(s);
  };
  if (mode === 'feature') {
    for (const f of getFeatureTable()) add(f.color, tr(f.label, f.label));
  } else if (mode === 'phase') {
    add('#6f7ea0', tr('v3d.phase_before'));
    add('#f0a726', tr('v3d.phase_magnets'));
    add('#35c07a', tr('v3d.phase_after'));
  } else {
    box.textContent = '—';
  }
}

// ============================================================
//  Línea de tiempo
// ============================================================
function moveIndexAtTime(t) {
  const ct = sim.cumTime;
  if (!ct || !ct.length) return 0;
  let lo = 0, hi = ct.length - 1, ans = ct.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (ct[mid] >= t) { ans = mid; hi = mid - 1; } else lo = mid + 1;
  }
  return Math.min(ans, ct.length - 1);
}

function restoreSegment(currentIdx) {
  if (lastIdx < 0 || lastIdx === currentIdx) { lastIdx = currentIdx; return; }
  const m = sim.moves[lastIdx];
  if (m && m[MV.EXTRUDE] && extrudeMesh) {
    setInstanceTransform(sim.extrIndex[lastIdx] - 1, m, 1);
  } else if (m && m[MV.EXTRUDE] && extrudeLines) {
    const o = (sim.extrIndex[lastIdx] - 1) * 6;
    const pos = extrudeLines.geometry.getAttribute('position');
    pos.array[o + 3] = m[MV.X2]; pos.array[o + 4] = m[MV.Y2]; pos.array[o + 5] = m[MV.Z2];
    pos.needsUpdate = true;
  }
  lastIdx = currentIdx;
}

let stoppedAtPhase = -1;

function setTime(t, fromUser = false) {
  if (!sim.moves.length) return;
  sim.time = Math.max(0, Math.min(t, sim.totalTime));
  let idx = moveIndexAtTime(sim.time);

  // El deslizador de capa recorta duro el índice de movimiento.
  const maxLayerSel = parseInt($('layerSlider').value, 10);
  if (sim.layerEndMove.length) {
    const capMove = sim.layerEndMove[Math.min(maxLayerSel, sim.layerEndMove.length - 1)];
    if (idx > capMove) { idx = capMove; sim.time = sim.cumTime[capMove]; setPlaying(false); }
  }

  // Parar al entrar en la secuencia de imanes, si se ha pedido.
  if (!fromUser && $('chkStop').checked && sim.hasMagnetBlock && sim.playing) {
    const ph = sim.phaseOfMove[idx];
    if (ph === 1 && stoppedAtPhase !== 1) {
      const r = sim.phaseRange[1];
      if (r) { idx = r.first; sim.time = r.t0; }
      stoppedAtPhase = 1;
      setPlaying(false);
    }
  }
  if (sim.phaseOfMove[idx] !== 1) stoppedAtPhase = -1;

  const m = sim.moves[idx];
  const tStart = idx > 0 ? sim.cumTime[idx - 1] : 0;
  const frac = m[MV.TIME] > 0 ? Math.max(0, Math.min((sim.time - tStart) / m[MV.TIME], 1)) : 1;

  const hx = m[MV.X1] + (m[MV.X2] - m[MV.X1]) * frac;
  const hy = m[MV.Y1] + (m[MV.Y2] - m[MV.Y1]) * frac;
  const hz = m[MV.Z1] + (m[MV.Z2] - m[MV.Z1]) * frac;
  updateKinematics(hx, hy, hz);

  const fullE = idx > 0 ? sim.extrIndex[idx - 1] : 0;
  const fullT = idx > 0 ? sim.travIndex[idx - 1] : 0;
  const done = frac >= 1;

  if (m[MV.EXTRUDE]) {
    const segIdx = sim.extrIndex[idx] - 1;
    if (extrudeMesh) { setInstanceTransform(segIdx, m, done ? 1 : frac); extrudeMesh.count = fullE + 1; }
    else if (extrudeLines) {
      const o = segIdx * 6;
      const pos = extrudeLines.geometry.getAttribute('position');
      pos.array[o + 3] = hx; pos.array[o + 4] = hy; pos.array[o + 5] = hz;
      pos.needsUpdate = true;
      extrudeLines.geometry.setDrawRange(0, (fullE + 1) * 2);
    }
    if (travelLines) travelLines.geometry.setDrawRange(0, fullT * 2);
  } else {
    if (extrudeMesh) extrudeMesh.count = fullE;
    else if (extrudeLines) extrudeLines.geometry.setDrawRange(0, fullE * 2);
    if (travelLines) travelLines.geometry.setDrawRange(0, (fullT + 1) * 2);
  }
  restoreSegment(idx);

  for (const mag of sim.magnets) mag.mesh.visible = idx >= mag.moveIdx;

  if ($('chkFollow').checked) {
    const wp = new THREE.Vector3(hx - BED_X / 2 - NOZ_WX, hz, NOZ_WZ);
    controls.target.lerp(wp, 0.12);
  }

  $('progress').value = String(Math.round((sim.time / Math.max(sim.totalTime, 1e-6)) * 10000));
  $('clock').innerHTML = `<b>${fmtTime(sim.time)}</b> / ${fmtTime(sim.totalTime)}`;
  updatePhaseButtons(sim.phaseOfMove[idx]);
}

function fmtTime(s) {
  s = Math.max(0, Math.round(s));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

function updatePhaseBar() {
  const total = Math.max(sim.totalTime, 1e-6);
  const bar = $('phases').children;
  for (let p = 0; p < 3; p++) {
    const r = sim.phaseRange[p];
    const dur = r ? Math.max(r.t1 - r.t0, 0) : 0;
    bar[p].style.flex = String(dur / total);
  }
  for (let p = 0; p < 3; p++) $('btnPhase' + p).disabled = !sim.phaseRange[p];
}

function updatePhaseButtons(active) {
  for (let p = 0; p < 3; p++) $('btnPhase' + p).classList.toggle('on', p === active);
}

function setupLayerSlider() {
  const sl = $('layerSlider');
  const n = Math.max(0, sim.layerZ.length - 1);
  sl.min = '0'; sl.max = String(n); sl.value = String(n);
  sl.disabled = n === 0;
  updateLayerLabel();
}

function updateLayerLabel() {
  const v = parseInt($('layerSlider').value, 10);
  const n = Math.max(0, sim.layerZ.length - 1);
  const z = sim.layerZ[v];
  $('layerVal').textContent = `${v}/${n}` + (z !== undefined ? ` · ${z.toFixed(2)}` : '');
}

function setPlaying(on) {
  sim.playing = !!on && sim.moves.length > 0;
  $('btnPlay').textContent = sim.playing ? '❚❚' : '▶';
  $('btnPlay').title = sim.playing ? tr('v3d.pause') : tr('v3d.play');
}

function simSpeed() {
  const v = parseFloat($('speed').value);
  return Math.max(1, Math.round(Math.pow(10, v * 3.477)));
}

// ============================================================
//  Interfaz
// ============================================================
// --- panel derecho plegable --------------------------------------------------
function setPanelCollapsed(on) {
  $('right').classList.toggle('collapsed', !!on);
  const btn = $('btnPanel');
  btn.textContent = on ? '☰' : '–';
  btn.title = tr(on ? 'v3d.panel_show' : 'v3d.panel_hide');
}

function applyStaticTexts() {
  $('hint').textContent = tr('viewer.no_file_3d');
  $('btnReset').title = tr('v3d.reset');
  $('lblSpeed').textContent = tr('v3d.speed');
  $('lblLayer').textContent = tr('v3d.layer');
  $('lblColorBy').textContent = tr('v3d.color_by');
  $('lblTravel').textContent = tr('v3d.show_travel');
  $('lblVolume').textContent = tr('v3d.show_volume');
  $('lblModel').textContent = tr('v3d.show_model');
  $('lblFollow').textContent = tr('v3d.follow');
  $('lblStop').textContent = tr('v3d.stop_at_pause');
  $('lblLegend').textContent = tr('v3d.legend');
  const opts = $('colorMode').options;
  opts[0].textContent = tr('v3d.color_feature');
  opts[1].textContent = tr('v3d.color_phase');
  opts[2].textContent = tr('v3d.color_layer');
  opts[3].textContent = tr('v3d.color_speed');
  $('btnPhase0').textContent = tr('v3d.phase_before');
  $('btnPhase1').textContent = tr('v3d.phase_magnets');
  $('btnPhase2').textContent = tr('v3d.phase_after');
  setPanelCollapsed($('right').classList.contains('collapsed'));   // refresca el tooltip
  $('btnPhase0').title = tr('v3d.phase_before_tip');
  $('btnPhase1').title = tr('v3d.phase_magnets_tip');
  $('btnPhase2').title = tr('v3d.phase_after_tip');
  setPlaying(sim.playing);
}

$('btnPlay').addEventListener('click', () => {
  if (!sim.moves.length) return;
  if (!sim.playing && sim.time >= sim.totalTime) setTime(0, true);
  stoppedAtPhase = sim.phaseOfMove[moveIndexAtTime(sim.time)] === 1 ? 1 : -1;
  setPlaying(!sim.playing);
});
$('btnReset').addEventListener('click', () => { stoppedAtPhase = -1; setTime(0, true); setPlaying(false); });
$('progress').addEventListener('input', (e) => {
  setPlaying(false);
  setTime((parseInt(e.target.value, 10) / 10000) * sim.totalTime, true);
});
for (let p = 0; p < 3; p++) {
  $('btnPhase' + p).addEventListener('click', () => {
    const r = sim.phaseRange[p];
    if (!r) return;
    setPlaying(false);
    stoppedAtPhase = p === 1 ? 1 : -1;
    // Al saltar a una fase se sube el tope de capa: si no, el recorte de capa
    // dejaría el salto sin efecto.
    $('layerSlider').value = $('layerSlider').max;
    updateLayerLabel();
    setTime(r.t0 + 1e-4, true);
  });
}
$('speed').addEventListener('input', () => { $('speedVal').textContent = '×' + simSpeed(); });
$('layerSlider').addEventListener('input', () => {
  updateLayerLabel();
  const v = parseInt($('layerSlider').value, 10);
  const capMove = sim.layerEndMove[Math.min(v, sim.layerEndMove.length - 1)];
  if (capMove !== undefined && sim.time > sim.cumTime[capMove]) setTime(sim.cumTime[capMove], true);
  else setTime(sim.time, true);
});
$('colorMode').addEventListener('change', () => { applyColors(); buildLegend(); });
$('chkTravel').addEventListener('change', (e) => { if (travelLines) travelLines.visible = e.target.checked; });
$('chkVolume').addEventListener('change', (e) => { volumeGroup.visible = e.target.checked; });
$('chkModel').addEventListener('change', applyModelVisibility);
$('btnPanel').addEventListener('click', () => {
  setPanelCollapsed(!$('right').classList.contains('collapsed'));
});

// El visor vive dentro de un QStackedWidget: al alternar 2D/3D o mover el
// divisor la página cambia de tamaño sin que llegue un evento `resize` de
// ventana, y el lienzo se queda con la medida anterior (imagen estirada y
// saltos al primer repintado). Un ResizeObserver sobre el contenedor sí lo ve.
let lastW = 0, lastH = 0;
function syncRendererSize() {
  const w = container.clientWidth, h = container.clientHeight;
  if (!w || !h || (w === lastW && h === lastH)) return;
  lastW = w; lastH = h;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}
window.addEventListener('resize', syncRendererSize);
if (window.ResizeObserver) new ResizeObserver(syncRendererSize).observe(container);

// ============================================================
//  Puente con Python
// ============================================================
let bridge = null;
function notify(kind, data) {
  if (bridge && bridge.fromViewer) bridge.fromViewer(JSON.stringify({ kind, data }));
  // Versión web: la página que contiene el <iframe> escucha estos avisos.
  if (window.parent && window.parent !== window) {
    window.parent.postMessage({ source: 'mps-viewer', kind, data }, window.location.origin);
  }
}

if (window.QWebChannel && window.qt && window.qt.webChannelTransport) {
  new QWebChannel(qt.webChannelTransport, (channel) => {
    bridge = channel.objects.bridge || null;
    notify('ready', {});
  });
}

// Python llama a estas funciones con runJavaScript.
window.mps = {
  load: (payload) => {
    Promise.resolve()
      .then(() => loadFromPayload(typeof payload === 'string' ? JSON.parse(payload) : payload))
      .catch((err) => { console.error(err); notify('error', { message: String(err) }); });
  },
  setTexts: (texts) => { T = typeof texts === 'string' ? JSON.parse(texts) : texts; applyStaticTexts(); buildLegend(); },
  setTheme: (theme) => {
    const t = typeof theme === 'string' ? JSON.parse(theme) : theme;
    const r = document.documentElement.style;
    if (t.bg) { r.setProperty('--bg', t.bg); scene.background = new THREE.Color(t.bg); scene.fog.color = new THREE.Color(t.bg); }
    if (t.panel) r.setProperty('--panel', t.panel);
    if (t.border) r.setProperty('--border', t.border);
    if (t.text) r.setProperty('--text', t.text);
    if (t.text_dim) r.setProperty('--muted', t.text_dim);
    if (t.accent) r.setProperty('--accent', t.accent);
  },
  // El desplegable visible está en la barra de Qt; esto sincroniza el estado.
  setColorMode: (mode) => {
    const sel = $('colorMode');
    if (!sel || !mode || sel.value === mode) return;
    if (!Array.prototype.some.call(sel.options, (o) => o.value === mode)) return;
    sel.value = mode;
    applyColors();
    buildLegend();
  },
  play: () => setPlaying(true),
  pause: () => setPlaying(false),
  goToPhase: (p) => $('btnPhase' + p).click(),
};

// ============================================================
//  Bucle
// ============================================================
const clock = new THREE.Clock();
(function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.1);
  if (sim.playing && sim.moves.length) {
    setTime(sim.time + dt * simSpeed());
    if (sim.time >= sim.totalTime) setPlaying(false);
  }
  controls.update();
  renderer.render(scene, camera);
})();

updateKinematics(BED_X / 2, BED_Y / 2, BED_Z * 0.66);
$('speedVal').textContent = '×' + simSpeed();
applyStaticTexts();

// Gancho de inspección: el estado del visor vive en el ámbito del módulo, así
// que sin esto no hay forma de comprobarlo desde fuera (ni desde Python, ni
// desde las herramientas de desarrollo).
window.__dbg = {
  scene, camera, renderer, controls, sim, setTime, updateKinematics,
  printerModel: () => printerModel,
  modelParts: () => modelParts,
  extrudeMesh: () => extrudeMesh,
  extrudeLines: () => extrudeLines,
  travelLines: () => travelLines,
  // Render y captura en la misma tarea: sin `preserveDrawingBuffer` el búfer
  // se limpia al componer, así que no vale hacerlo en dos pasos.
  snapshot: () => { renderer.render(scene, camera); return renderer.domElement.toDataURL('image/png'); },
};

notify('booted', {});
