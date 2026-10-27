// Web Worker con Pyodide: aquí corre el Python de MagnetPlace Studio.
//
// La lógica (análisis del G-code, detección de agujeros, avisos y generación)
// es la misma de la app de escritorio: los módulos de `py/` son copias sin tocar
// de `gcode_magnets` y `magnet_app`, más `webapi.py`, que hace de ventana.
// Va en un worker para que analizar un G-code grande no congele la página.

const PYODIDE_VERSION = '0.26.4';
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

// Lo que se copia al sistema de ficheros de Pyodide. Rutas relativas a `py/`.
const PY_FILES = [
  'webapi.py',
  'gcode_magnets/__init__.py', 'gcode_magnets/adhesion.py', 'gcode_magnets/analysis.py',
  'gcode_magnets/config.py', 'gcode_magnets/fit.py', 'gcode_magnets/footprint.py',
  'gcode_magnets/generator.py', 'gcode_magnets/geometry.py', 'gcode_magnets/io.py',
  'gcode_magnets/magnetics.py', 'gcode_magnets/parser.py',
  'magnet_app/__init__.py', 'magnet_app/features.py', 'magnet_app/i18n.py',
  'magnet_app/limits.py', 'magnet_app/magnetics.py', 'magnet_app/pipeline.py',
  'magnet_app/project.py', 'magnet_app/settings.py',
];

// Cambia con cada versión publicada para que el navegador no sirva los .py
// viejos desde su caché.
const ASSET_VERSION = '1.1.2-web1';

let pyodide = null;
let callPy = null;

function post(msg, transfer) { self.postMessage(msg, transfer || []); }

async function boot() {
  post({ type: 'progress', step: 'runtime' });
  importScripts(PYODIDE_URL + 'pyodide.js');
  pyodide = await loadPyodide({ indexURL: PYODIDE_URL });

  post({ type: 'progress', step: 'code' });
  const base = new URL('../py/', self.location.href);
  const FS = pyodide.FS;
  for (const dir of ['/app', '/app/gcode_magnets', '/app/magnet_app', '/work', '/work/in', '/work/out', '/work/template']) {
    try { FS.mkdir(dir); } catch (_) { /* ya existe */ }
  }
  await Promise.all(PY_FILES.map(async (rel) => {
    const resp = await fetch(new URL(rel + '?v=' + ASSET_VERSION, base));
    if (!resp.ok) throw new Error(`No se pudo cargar ${rel} (${resp.status})`);
    FS.writeFile('/app/' + rel, await resp.text());
  }));

  post({ type: 'progress', step: 'start' });
  pyodide.runPython(`
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/app')
import webapi
`);
  callPy = pyodide.globals.get('webapi').call;
}

function clearDir(dir) {
  const FS = pyodide.FS;
  for (const name of FS.readdir(dir)) {
    if (name === '.' || name === '..') continue;
    try { FS.unlink(dir + '/' + name); } catch (_) { /* no es un archivo */ }
  }
}

const ready = boot().then(
  () => post({ type: 'ready' }),
  (err) => post({ type: 'fatal', message: String(err && err.message || err) }),
);

self.onmessage = async (ev) => {
  const { id, type } = ev.data;
  try {
    await ready;
    if (!callPy) throw new Error('Pyodide no ha arrancado');
    if (type === 'call') {
      const json = callPy(ev.data.fn, JSON.stringify(ev.data.args || []));
      post({ id, ok: true, json });
    } else if (type === 'writeFile') {
      // Cada carpeta guarda un solo archivo: el que está abierto, o la
      // plantilla. Así la memoria no crece con cada archivo que se abre.
      const path = ev.data.path;
      const dir = path.slice(0, path.lastIndexOf('/'));
      clearDir(dir);
      pyodide.FS.writeFile(path, new Uint8Array(ev.data.data));
      post({ id, ok: true, json: '{}' });
    } else if (type === 'readFile') {
      const bytes = pyodide.FS.readFile(ev.data.path);
      pyodide.FS.unlink(ev.data.path);
      const buf = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
      post({ id, ok: true, data: buf }, [buf]);
    } else {
      throw new Error('Mensaje desconocido: ' + type);
    }
  } catch (err) {
    post({ id, ok: false, message: String(err && err.message || err) });
  }
};
