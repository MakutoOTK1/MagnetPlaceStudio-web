// Parser de G-code para el visor 3D.
//
// Portado del simulador de referencia con tres correcciones necesarias aquí:
//
//  1. **Tokenizador por expresión regular** en vez de por espacios. El original
//     partía la línea por espacios, así que `G1X10Y10` se parseaba mal y las
//     plantillas de secuencia de MagnetPlace (`G1 Z {z+0.4} F1200`) daban
//     `parseFloat("{z+0.4}") = NaN`, que contaminaba las coordenadas para el
//     resto del archivo. Ahora un token que no lleve número detrás simplemente
//     no existe, que es el comportamiento correcto (parámetro no presente).
//  2. **Índice de línea de origen** en cada movimiento, para poder repartirlos
//     entre las tres fases (antes de la pausa / secuencia de imanes / después).
//  3. **Capas por el comentario del laminador** (`; layer num/...`) cuando
//     existe, en vez de la heurística de "Z que sube", que inventa cientos de
//     capas en modo jarrón.

// Índices dentro de cada movimiento (array plano de números, por memoria).
export const MV = {
  X1: 0, Y1: 1, Z1: 2,
  X2: 3, Y2: 4, Z2: 5,
  EXTRUDE: 6,   // 0 = viaje, 1 = cordón
  TIME: 7,      // segundos
  FEATURE: 8,   // índice en la tabla de FEATURES, -1 si ninguna
  FEED: 9,      // mm/s
  TOOL: 10,
  DELTA_E: 11,  // mm de filamento
  LINE: 12,     // índice de línea en el archivo original
  LAYER_MARK: 13, // nº de marcadores "; layer num" vistos, -1 si no hay
  SIZE: 14,
};

const TOKEN_RE = /([A-Za-z])\s*(-?\d*\.?\d+(?:[eE][-+]?\d+)?)/g;
const LAYER_COMMENT = '; layer num/total_layer_count:';
const MAGNET_COMMENT_RE = /^;\s*Im[aá]n\s+(\d+)\s*\(([^)]*)\)/i;
const CIRCLES_END = 'FIN CÍRCULOS CONCÉNTRICOS';

// Tabla de tipos de trazo. La rellena Python al cargar (magnet_app/features.py)
// para que la vista 2D y la 3D coincidan; esto es solo el valor de reserva.
let FEATURES = [];
export function setFeatureTable(table) {
  FEATURES = (table || []).map((f) => ({ keys: f.keys || [], color: f.color, label: f.label }));
}
export function getFeatureTable() { return FEATURES; }

export function featureFromComment(s) {
  const low = s.toLowerCase();
  for (let i = 0; i < FEATURES.length; i++) {
    for (const k of FEATURES[i].keys) if (low.includes(k)) return i;
  }
  return -1;
}

/**
 * Parsea el texto de un G-code.
 * @returns {{moves: Array, filament: number, colors: (string[]|null),
 *            magnetMarks: Array, pauseLines: number[], lineCount: number}}
 */
export function parseGcode(text) {
  const moves = [];
  const magnetMarks = [];   // { index, color, commentLine, placedLine }
  const pauseLines = [];    // líneas con "M400 U1" (la pausa de Bambu)
  let filament = 0;
  let colors = null;

  let x = 0, y = 0, z = 0, e = 0, f = 3000; // f en mm/min
  let absPos = true, absE = true;
  let feature = -1, tool = 0;
  let layerMark = -1;
  let pendingMagnet = null;

  const lines = text.split('\n');

  for (let li = 0; li < lines.length; li++) {
    let line = lines[li];
    if (!line) continue;

    // --- comentarios ---
    const semi = line.indexOf(';');
    if (semi >= 0) {
      const comment = line.slice(semi);
      const low = comment.toLowerCase();

      if (low.includes(LAYER_COMMENT)) layerMark += 1;
      const t = /;\s*(?:type|feature)\s*:\s*(.+)/i.exec(comment);
      if (t) feature = featureFromComment(t[1]);
      if (low.includes('color_change')) tool++;
      if (!colors) {
        const c = /(?:filament_colou?r|extruder_colou?r)\s*[=:]\s*(.+)/i.exec(comment);
        if (c) {
          const list = c[1].split(/[;,]/).map((s) => s.trim()).filter((s) => /^#?[0-9a-f]{6}$/i.test(s));
          if (list.length) colors = list.map((s) => (s[0] === '#' ? s : '#' + s));
        }
      }
      const mag = MAGNET_COMMENT_RE.exec(comment.trim());
      if (mag) {
        pendingMagnet = {
          index: parseInt(mag[1], 10),
          color: mag[2].trim().toLowerCase(),
          commentLine: li,
          placedLine: li,
        };
        magnetMarks.push(pendingMagnet);
      } else if (pendingMagnet && comment.includes(CIRCLES_END)) {
        // El imán queda depositado al terminar los círculos de asentado.
        pendingMagnet.placedLine = li;
        pendingMagnet = null;
      }
      line = line.slice(0, semi);
    }
    if (!line.trim()) continue;

    // --- tokens ---
    let cmd = null, cmdNum = -1;
    const params = {};
    TOKEN_RE.lastIndex = 0;
    let m;
    while ((m = TOKEN_RE.exec(line)) !== null) {
      const letter = m[1].toUpperCase();
      const val = parseFloat(m[2]);
      if (cmd === null && (letter === 'G' || letter === 'M' || letter === 'T')) {
        cmd = letter; cmdNum = val;
      } else {
        params[letter] = val;
      }
    }
    if (cmd === null) continue;

    if (cmd === 'T') {
      // T255 / T1000+ son herramientas internas de Bambu, no filamentos.
      if (cmdNum >= 0 && cmdNum <= 64) tool = cmdNum;
      continue;
    }
    if (cmd === 'M') {
      if (cmdNum === 82) absE = true;
      else if (cmdNum === 83) absE = false;
      else if (cmdNum === 600) tool++;
      else if (cmdNum === 400 && params.U === 1) pauseLines.push(li);
      continue;
    }

    // --- G ---
    if (cmdNum === 90) { absPos = true; absE = true; continue; }
    if (cmdNum === 91) { absPos = false; absE = false; continue; }
    if (cmdNum === 92) {
      if (params.X !== undefined) x = params.X;
      if (params.Y !== undefined) y = params.Y;
      if (params.Z !== undefined) z = params.Z;
      if (params.E !== undefined) e = params.E;
      continue;
    }
    if (cmdNum === 28) {
      const any = params.X !== undefined || params.Y !== undefined || params.Z !== undefined;
      if (!any || params.X !== undefined) x = 0;
      if (!any || params.Y !== undefined) y = 0;
      if (!any || params.Z !== undefined) z = 0;
      continue;
    }
    if (cmdNum !== 0 && cmdNum !== 1 && cmdNum !== 2 && cmdNum !== 3) continue;

    if (params.F !== undefined && params.F > 0) f = params.F;
    const feedMMs = Math.max(f / 60, 1e-3);

    const nx = params.X !== undefined ? (absPos ? params.X : x + params.X) : x;
    const ny = params.Y !== undefined ? (absPos ? params.Y : y + params.Y) : y;
    const nz = params.Z !== undefined ? (absPos ? params.Z : z + params.Z) : z;

    let de = 0;
    if (params.E !== undefined) {
      if (absE) { de = params.E - e; e = params.E; }
      else { de = params.E; e += params.E; }
    }

    if (cmdNum === 2 || cmdNum === 3) {
      pushArc(moves, x, y, z, nx, ny, nz, params, cmdNum === 2, de, feedMMs, feature, tool, li, layerMark);
    } else {
      pushSegment(moves, x, y, z, nx, ny, nz, de, feedMMs, feature, tool, li, layerMark);
    }
    if (de > 0) filament += de;
    x = nx; y = ny; z = nz;
  }

  return { moves, filament, colors, magnetMarks, pauseLines, lineCount: lines.length };
}

function pushSegment(moves, x, y, z, nx, ny, nz, de, feedMMs, feature, tool, li, layerMark) {
  const dist = Math.hypot(nx - x, ny - y, nz - z);
  if (dist <= 1e-6) return; // retracción o purga en sitio: no dibuja nada
  const mv = new Array(MV.SIZE);
  mv[MV.X1] = x; mv[MV.Y1] = y; mv[MV.Z1] = z;
  mv[MV.X2] = nx; mv[MV.Y2] = ny; mv[MV.Z2] = nz;
  mv[MV.EXTRUDE] = de > 1e-6 ? 1 : 0;
  mv[MV.TIME] = dist / feedMMs;
  mv[MV.FEATURE] = feature;
  mv[MV.FEED] = feedMMs;
  mv[MV.TOOL] = tool;
  mv[MV.DELTA_E] = de;
  mv[MV.LINE] = li;
  mv[MV.LAYER_MARK] = layerMark;
  moves.push(mv);
}

// Arcos G2/G3 en forma I/J (la única que emite Bambu), plano XY.
function pushArc(moves, x, y, z, nx, ny, nz, params, clockwise, de, feedMMs, feature, tool, li, layerMark) {
  const cx = x + (params.I || 0);
  const cy = y + (params.J || 0);
  const r = Math.hypot(x - cx, y - cy);
  if (r < 1e-9) {
    pushSegment(moves, x, y, z, nx, ny, nz, de, feedMMs, feature, tool, li, layerMark);
    return;
  }
  let a0 = Math.atan2(y - cy, x - cx);
  let a1 = Math.atan2(ny - cy, nx - cx);
  if (clockwise) { if (a1 >= a0) a1 -= 2 * Math.PI; }
  else { if (a1 <= a0) a1 += 2 * Math.PI; }

  const arcLen = Math.abs(a1 - a0) * r;
  const steps = Math.max(2, Math.min(96, Math.ceil(arcLen / 0.6)));
  const dz = (nz - z) / steps;
  const dee = de / steps;

  let px = x, py = y, pz = z;
  for (let k = 1; k <= steps; k++) {
    const a = a0 + (a1 - a0) * (k / steps);
    const qx = k === steps ? nx : cx + r * Math.cos(a);
    const qy = k === steps ? ny : cy + r * Math.sin(a);
    const qz = z + dz * k;
    pushSegment(moves, px, py, pz, qx, qy, qz, dee, feedMMs, feature, tool, li, layerMark);
    px = qx; py = qy; pz = qz;
  }
}
