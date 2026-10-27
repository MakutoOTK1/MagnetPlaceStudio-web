// Cliente del worker de Pyodide: promesas sobre postMessage.
//
// Cada llamada lleva un id y el worker contesta por orden (atiende un mensaje
// detrás de otro), así que la última respuesta que llega es siempre la de la
// última petición enviada.

export class Api {
  constructor(onProgress) {
    this.worker = new Worker(new URL('./worker.js', import.meta.url));
    this.pending = new Map();
    this.seq = 0;
    this.ready = new Promise((resolve, reject) => {
      this.worker.onmessage = (ev) => {
        const msg = ev.data;
        if (msg.type === 'progress') { onProgress && onProgress(msg.step); return; }
        if (msg.type === 'ready') { resolve(); return; }
        if (msg.type === 'fatal') { reject(new Error(msg.message)); return; }
        const entry = this.pending.get(msg.id);
        if (!entry) return;
        this.pending.delete(msg.id);
        if (!msg.ok) entry.reject(new Error(msg.message));
        else if (msg.data !== undefined) entry.resolve(msg.data);
        else entry.resolve(JSON.parse(msg.json));
      };
      this.worker.onerror = (ev) => reject(new Error(ev.message || 'worker error'));
    });
  }

  _send(payload, transfer) {
    const id = ++this.seq;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.worker.postMessage({ id, ...payload }, transfer || []);
    });
  }

  /** Llama a `WebApp.<fn>(*args)` de `py/webapi.py`. */
  call(fn, ...args) { return this._send({ type: 'call', fn, args }); }

  /** Copia un archivo al sistema de ficheros de Pyodide. */
  writeFile(path, arrayBuffer) {
    return this._send({ type: 'writeFile', path, data: arrayBuffer }, [arrayBuffer]);
  }

  /** Recoge (y borra) un archivo generado. Devuelve un ArrayBuffer. */
  readFile(path) { return this._send({ type: 'readFile', path }); }
}
