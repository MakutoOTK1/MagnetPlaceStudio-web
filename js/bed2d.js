// Visor 2D de la capa de la pausa sobre la placa (port de magnet_app/bed_canvas.py).
//
// Dibuja la placa de 256 × 256 mm, los dos depósitos de imanes, la geometría de
// la capa expuesta al parar (con los arcos ya aplanados y el ancho real de cada
// cordón, que llegan hechos desde Python) y los imanes a su diámetro. Las
// cuentas —alcance, separación, pasillos, reorden— no se hacen aquí: las hace
// `webapi.py` con el código de la app y este lienzo solo las pinta.

export const BED_SIZE = 256;
const SNAP_RADIUS = 5;          // mm: distancia para "imantar" a un centro sugerido
const HIT_RADIUS = 2.5;         // mm: distancia para seleccionar un imán existente
const DEFAULT_MAGNET_D = 5;     // mm: diámetro si el color no tiene módulo
const CONTAINER_SIZE = 22;
const CONTAINER_ORDER = ['red', 'blue'];
const WORLD = { x: 0, y: 0, w: BED_SIZE + CONTAINER_SIZE * CONTAINER_ORDER.length, h: BED_SIZE };
const MARGIN_PX = 26;
const MIN_VIEW_MM = 8;
const FLASH_MS = 4000;
const DRAG_PX = 4;              // lo que hay que mover para que un clic sea arrastre
const LONG_PRESS_MS = 650;      // pulsación larga en táctil = borrar

export const COLOR_MAP = { red: '#e23b3b', blue: '#2b6cff' };
const COLOR_DARK = { red: '#a12a2a', blue: '#1f4db6' };
const AREA_OK = '#1f9d55';
const AREA_BAD = '#e23b3b';
const SPACING = '#e8a33d';
const SWEEP = 'rgba(232,163,61,0.47)';

export class BedCanvas2D {
  constructor(canvas, { onPointsChanged, tr }) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.onPointsChanged = onPointsChanged;
    this.tr = tr;
    this.colors = {};
    this.currentColor = 'red';
    this.points = [];
    this.suggested = [];
    this.paths = [];             // {path: Path2D, w, c, infill, bounds}
    this.hasLayer = false;
    this.layerZ = null;
    this.hideInfill = true;
    this.state = { dmins: [], dmin: 0, travels: [], pairs: [], out: [], stacks: [],
                   area: [8.4, 256, 0, 223], sizes: {}, kind_sweep: 'sweep' };
    this.showArea = false;
    this.showSpacing = false;
    this.flashLines = [];
    this.flashTimer = null;
    this.view = { ...WORLD };
    this.drag = null;            // gesto en curso
    this.dragging = false;       // hay un imán arrastrándose (para la API)

    this._bind();
    new ResizeObserver(() => this.render()).observe(canvas);
  }

  // ------------------------------------------------------------- API
  setTheme(colors) { this.colors = colors; this.render(); }

  setLayer(layer, suggested) {
    this.paths = [];
    this.hasLayer = !!layer;
    this.layerZ = layer ? layer.z : null;
    if (layer) {
      for (const run of layer.runs) {
        const p = run.p;
        const path = new Path2D();
        let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
        for (let i = 0; i < p.length; i += 2) {
          const x = p[i], y = p[i + 1];
          if (i === 0) path.moveTo(x, y); else path.lineTo(x, y);
          if (x < x0) x0 = x; if (x > x1) x1 = x;
          if (y < y0) y0 = y; if (y > y1) y1 = y;
        }
        this.paths.push({ path, w: run.w, c: run.c, infill: run.i, bounds: [x0, y0, x1, y1] });
      }
    }
    this.suggested = suggested || [];
    this.resetView();
  }

  setSuggested(s) { this.suggested = s || []; this.render(); }

  /** Estado calculado por Python (`WebApp.canvas_state`). */
  setState(state, { keepPoints = false } = {}) {
    this.state = state;
    if (!keepPoints) this.points = state.points.map((p) => [p[0], p[1], p[2]]);
    this.render();
  }

  setHideInfill(v) { this.hideInfill = !!v; this.render(); }
  setShowArea(v) { this.showArea = !!v; this.render(); }
  setShowSpacing(v) { this.showSpacing = !!v; this.render(); }
  setCurrentColor(c) { this.currentColor = c === 'blue' ? 'blue' : 'red'; }

  flash(title, fix) {
    this.flashLines = [title, fix].filter(Boolean);
    clearTimeout(this.flashTimer);
    this.flashTimer = setTimeout(() => { this.flashLines = []; this.render(); }, FLASH_MS);
    this.render();
  }

  zoom(factor, anchor) {
    const a = anchor || { x: this.view.x + this.view.w / 2, y: this.view.y + this.view.h / 2 };
    const w = Math.min(Math.max(this.view.w * factor, MIN_VIEW_MM), WORLD.w);
    const h = Math.min(Math.max(this.view.h * factor, MIN_VIEW_MM), WORLD.h);
    // El punto bajo el ratón se queda bajo el ratón.
    const fx = (a.x - this.view.x) / this.view.w;
    const fy = (a.y - this.view.y) / this.view.h;
    this._clampView(a.x - fx * w, a.y - fy * h, w, h);
    this.render();
  }

  resetView() {
    const b = this._partBounds();
    if (!b) { this.view = { ...WORLD }; this.render(); return; }
    let side = Math.max(b[2] - b[0], b[3] - b[1]) * 1.35;
    side = Math.min(Math.max(side, 40), BED_SIZE);
    const cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
    this._clampView(cx - side / 2, cy - side / 2, side, side);
    this.render();
  }

  showWorld() { this.view = { ...WORLD }; this.render(); }

  // ---------------------------------------------------------- utilidades
  _magnetD(color) {
    const d = this.state.sizes && this.state.sizes[color];
    return d ? d : DEFAULT_MAGNET_D;
  }

  _partBounds() {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const p of this.paths) {
      if (this.hideInfill && p.infill) continue;
      x0 = Math.min(x0, p.bounds[0]); y0 = Math.min(y0, p.bounds[1]);
      x1 = Math.max(x1, p.bounds[2]); y1 = Math.max(y1, p.bounds[3]);
    }
    return x0 === Infinity ? null : [x0, y0, x1, y1];
  }

  _clampView(x0, y0, w, h) {
    w = Math.min(w, WORLD.w); h = Math.min(h, WORLD.h);
    x0 = Math.min(Math.max(x0, WORLD.x), WORLD.x + WORLD.w - w);
    y0 = Math.min(Math.max(y0, WORLD.y), WORLD.y + WORLD.h - h);
    this.view = { x: x0, y: y0, w, h };
  }

  _metrics() {
    const r = this.canvas.getBoundingClientRect();
    const vw = Math.max(r.width - 2 * MARGIN_PX, 1), vh = Math.max(r.height - 2 * MARGIN_PX, 1);
    const scale = Math.min(vw / this.view.w, vh / this.view.h);
    const cx = r.width / 2, cy = r.height / 2;
    const vcx = this.view.x + this.view.w / 2, vcy = this.view.y + this.view.h / 2;
    return { width: r.width, height: r.height, scale, cx, cy, vcx, vcy };
  }

  _toScreen(m, x, y) { return [m.cx + (x - m.vcx) * m.scale, m.cy - (y - m.vcy) * m.scale]; }
  _toMM(m, sx, sy) { return [m.vcx + (sx - m.cx) / m.scale, m.vcy - (sy - m.cy) / m.scale]; }

  _worldTransform(ctx, m, dpr) {
    ctx.setTransform(m.scale * dpr, 0, 0, -m.scale * dpr,
      (m.cx - m.vcx * m.scale) * dpr, (m.cy + m.vcy * m.scale) * dpr);
  }

  _nearestPoint(x, y) {
    let best = -1, bestD = HIT_RADIUS;
    this.points.forEach(([px, py, c], i) => {
      const reach = Math.max(HIT_RADIUS, this._magnetD(c) / 2);
      const d = Math.hypot(x - px, y - py);
      if (d <= reach && (best < 0 || d <= bestD)) { best = i; bestD = d; }
    });
    return best;
  }

  _stackOf(i) {
    for (const g of this.state.stacks || []) if (g.includes(i)) return g;
    return [i];
  }

  _snap(x, y) {
    let best = null, bestD = SNAP_RADIUS;
    for (const [cx, cy] of this.suggested) {
      const d = Math.hypot(x - cx, y - cy);
      if (d <= bestD) { best = [cx, cy]; bestD = d; }
    }
    return best || [x, y];
  }

  _inArea(x, y) {
    const [x0, x1, y0, y1] = this.state.area;
    return x >= x0 && x <= x1 && y >= y0 && y <= y1;
  }

  _clampArea(x, y) {
    const [x0, x1, y0, y1] = this.state.area;
    return [Math.min(Math.max(x, x0), Math.max(x1, x0)), Math.min(Math.max(y, y0), Math.max(y1, y0))];
  }

  _areaTexts() {
    const f = (v) => String(parseFloat(v.toPrecision(6)));   // como f"{v:g}"
    const [x0, x1, y0, y1] = this.state.area;
    return { xmin: f(x0), xmax: f(x1), ymin: f(y0), ymax: f(y1) };
  }

  _changed(dragging) { this.onPointsChanged(this.points, dragging); }

  // ---------------------------------------------------------- interacción
  addToStack(i) {
    const [x, y] = this.points[i];
    this.points.push([x, y, this.currentColor]);
    this._changed(false);
  }

  removeTopOfStack(i) {
    const g = this._stackOf(i);
    this.points.splice(g[g.length - 1], 1);
    this._changed(false);
  }

  _bind() {
    const c = this.canvas;
    c.addEventListener('contextmenu', (e) => e.preventDefault());
    c.addEventListener('pointerdown', (e) => this._down(e));
    c.addEventListener('pointermove', (e) => this._move(e));
    c.addEventListener('pointerup', (e) => this._up(e));
    c.addEventListener('pointercancel', () => { this.drag = null; });
    c.addEventListener('wheel', (e) => {
      if (!this.hasLayer) return;
      e.preventDefault();
      const m = this._metrics();
      const r = c.getBoundingClientRect();
      const [x, y] = this._toMM(m, e.clientX - r.left, e.clientY - r.top);
      const steps = -e.deltaY / 100;
      this.zoom(Math.pow(1 / 1.2, steps), { x, y });
    }, { passive: false });
  }

  _down(e) {
    if (!this.hasLayer) return;
    const r = this.canvas.getBoundingClientRect();
    const sx = e.clientX - r.left, sy = e.clientY - r.top;
    const m = this._metrics();
    const [x, y] = this._toMM(m, sx, sy);
    const idx = this._nearestPoint(x, y);
    this.canvas.setPointerCapture(e.pointerId);
    this.drag = { button: e.button, sx, sy, lastX: sx, lastY: sy, idx, moved: false,
                  pointerType: e.pointerType, ctrl: e.ctrlKey || e.metaKey, longTimer: null };
    if (e.pointerType === 'touch' && idx >= 0) {
      // En táctil no hay clic derecho: mantener pulsado un imán lo quita.
      this.drag.longTimer = setTimeout(() => {
        if (this.drag && !this.drag.moved) { this.removeTopOfStack(idx); this.drag = null; }
      }, LONG_PRESS_MS);
    }
    if (e.button === 0 && idx >= 0 && this.drag.ctrl) {
      this.addToStack(idx);
      this.drag = null;
    }
  }

  _move(e) {
    const d = this.drag;
    if (!d) return;
    const r = this.canvas.getBoundingClientRect();
    const sx = e.clientX - r.left, sy = e.clientY - r.top;
    if (!d.moved && Math.hypot(sx - d.sx, sy - d.sy) > DRAG_PX) {
      d.moved = true;
      clearTimeout(d.longTimer);
    }
    if (!d.moved) return;
    const m = this._metrics();
    if (d.button === 0 && d.idx >= 0) {
      // Arrastrar un imán (con su pila entera), sin sacarlo del área.
      const [mx, my] = this._toMM(m, sx, sy);
      const [x, y] = this._clampArea(mx, my);
      for (const k of this._stackOf(d.idx)) this.points[k] = [x, y, this.points[k][2]];
      this.dragging = true;
      this._changed(true);
      this.render();
      return;
    }
    // Cualquier otro arrastre mueve la vista.
    const [ax, ay] = this._toMM(m, d.lastX, d.lastY);
    const [bx, by] = this._toMM(m, sx, sy);
    this._clampView(this.view.x + (ax - bx), this.view.y + (ay - by), this.view.w, this.view.h);
    d.lastX = sx; d.lastY = sy;
    this.render();
  }

  _up(e) {
    const d = this.drag;
    this.drag = null;
    if (!d) return;
    clearTimeout(d.longTimer);
    if (this.dragging) {
      this.dragging = false;
      this._changed(false);       // al soltar ya se puede renumerar
      return;
    }
    if (d.moved) return;
    if (d.button === 2) {
      if (d.idx >= 0) this.removeTopOfStack(d.idx);
      return;
    }
    if (d.button !== 0 || d.idx >= 0) return;
    const m = this._metrics();
    const [mx, my] = this._toMM(m, d.sx, d.sy);
    // Fuera de la cama no se imprime: los depósitos son solo referencia.
    if (!(mx >= 0 && mx <= BED_SIZE && my >= 0 && my <= BED_SIZE)) return;
    const [x, y] = this._snap(mx, my);
    if (!this._inArea(x, y)) {
      this.flash(this.tr('canvas.out_of_area_title'), this.tr('canvas.out_of_area_fix', this._areaTexts()));
      return;
    }
    this.points.push([x, y, this.currentColor]);
    this._changed(false);
    this.render();
  }

  // ------------------------------------------------------------- pintado
  render() {
    if (this._raf) return;
    this._raf = requestAnimationFrame(() => { this._raf = null; this._paint(); });
  }

  _paint() {
    const c = this.canvas, ctx = this.ctx;
    const dpr = window.devicePixelRatio || 1;
    const r = c.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return;
    const W = Math.round(r.width * dpr), H = Math.round(r.height * dpr);
    if (c.width !== W || c.height !== H) { c.width = W; c.height = H; }
    const m = this._metrics();
    const col = this.colors;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = col.fig_bg || '#181b26';
    ctx.fillRect(0, 0, W, H);

    const px = 1 / Math.max(m.scale, 1e-6);   // un píxel, en mm
    this._worldTransform(ctx, m, dpr);
    this._drawPlate(ctx, px);
    this._drawContainers(ctx, px);
    this._drawArea(ctx, px);
    if (this.hasLayer) this._drawGeometry(ctx);
    this._drawSuggested(ctx, px);
    this._drawSpacingWorld(ctx, px);
    this._drawMagnetsWorld(ctx, px);

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this._drawRulers(ctx, m);
    this._drawSpacingLabels(ctx, m);
    this._drawMagnetLabels(ctx, m);
    this._drawHud(ctx, m);
    this._drawFlash(ctx, m);
  }

  _drawPlate(ctx, px) {
    const col = this.colors;
    const g = ctx.createLinearGradient(0, BED_SIZE, 0, 0);
    g.addColorStop(0, col.plate_bottom || '#6e747e');
    g.addColorStop(1, col.plate_top || '#8e949e');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, BED_SIZE, BED_SIZE);

    ctx.beginPath();
    for (let v = 10; v <= BED_SIZE; v += 10) { ctx.moveTo(v, 0); ctx.lineTo(v, BED_SIZE); ctx.moveTo(0, v); ctx.lineTo(BED_SIZE, v); }
    ctx.strokeStyle = 'rgba(0,0,0,0.12)'; ctx.lineWidth = px; ctx.stroke();
    ctx.beginPath();
    for (let v = 50; v <= BED_SIZE; v += 50) { ctx.moveTo(v, 0); ctx.lineTo(v, BED_SIZE); ctx.moveTo(0, v); ctx.lineTo(BED_SIZE, v); }
    ctx.strokeStyle = 'rgba(0,0,0,0.25)'; ctx.lineWidth = px * 1.6; ctx.stroke();

    ctx.lineWidth = px * 2.2;
    ctx.strokeStyle = 'rgba(214,60,60,0.86)';
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(30, 0); ctx.stroke();
    ctx.strokeStyle = 'rgba(60,180,90,0.86)';
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, 30); ctx.stroke();

    ctx.strokeStyle = col.plate_edge || '#4a4f58';
    ctx.lineWidth = px * 2;
    ctx.strokeRect(0, 0, BED_SIZE, BED_SIZE);
  }

  _drawContainers(ctx, px) {
    const y0 = BED_SIZE / 2 - CONTAINER_SIZE / 2;
    CONTAINER_ORDER.forEach((color, i) => {
      const x0 = BED_SIZE + i * CONTAINER_SIZE;
      ctx.globalAlpha = 0.59;
      ctx.fillStyle = COLOR_MAP[color];
      ctx.fillRect(x0, y0, CONTAINER_SIZE, CONTAINER_SIZE);
      ctx.globalAlpha = 1;
      ctx.strokeStyle = COLOR_DARK[color];
      ctx.lineWidth = px * 1.6;
      ctx.strokeRect(x0, y0, CONTAINER_SIZE, CONTAINER_SIZE);
      const d = this.state.sizes && this.state.sizes[color];
      const rad = (d || DEFAULT_MAGNET_D) / 2;
      ctx.strokeStyle = d ? 'rgba(255,255,255,0.78)' : 'rgba(255,255,255,0.35)';
      ctx.lineWidth = px * 1.4;
      ctx.setLineDash(d ? [] : [px * 5, px * 3]);
      ctx.beginPath(); ctx.arc(x0 + CONTAINER_SIZE / 2, y0 + CONTAINER_SIZE / 2, rad, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
    });
  }

  _drawArea(ctx, px) {
    if (!(this.showArea || this.flashLines.length)) return;
    const [x0, x1, y0, y1] = this.state.area;
    const w = Math.max(x1 - x0, 0), h = Math.max(y1 - y0, 0);
    if (w <= 0 || h <= 0) return;
    if (this.flashLines.length) {
      ctx.beginPath();
      ctx.rect(0, 0, BED_SIZE, BED_SIZE);
      ctx.rect(x0, y0, w, h);
      ctx.fillStyle = 'rgba(226,59,59,0.27)';
      ctx.fill('evenodd');
    }
    ctx.strokeStyle = AREA_OK;
    ctx.lineWidth = px * 2.2;
    ctx.setLineDash([px * 8, px * 5]);
    ctx.strokeRect(x0, y0, w, h);
    ctx.setLineDash([]);
  }

  _drawGeometry(ctx) {
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    for (const p of this.paths) {
      if (this.hideInfill && p.infill) continue;
      ctx.strokeStyle = p.c;
      ctx.lineWidth = p.w;           // ancho real del cordón, en mm
      ctx.stroke(p.path);
    }
  }

  _drawSuggested(ctx, px) {
    if (!this.suggested.length) return;
    ctx.strokeStyle = '#1f9d55';
    ctx.lineWidth = px * 1.8;
    ctx.setLineDash([px * 4, px * 3]);
    ctx.beginPath();
    for (const [x, y] of this.suggested) { ctx.moveTo(x + 2, y); ctx.arc(x, y, 2, 0, Math.PI * 2); }
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.beginPath();
    for (const [x, y] of this.suggested) { ctx.moveTo(x - 1.2, y); ctx.lineTo(x + 1.2, y); ctx.moveTo(x, y - 1.2); ctx.lineTo(x, y + 1.2); }
    ctx.stroke();
  }

  _drawSpacingWorld(ctx, px) {
    const st = this.state;
    if (!(st.dmin > 0) || !this.points.length) return;
    const ds = st.dmins || [];
    const tv = st.travels || [];
    if (this.showSpacing) {
      ctx.strokeStyle = SWEEP;
      ctx.lineWidth = px * 1.2;
      ctx.setLineDash([px * 1.5, px * 3]);
      this.points.forEach(([x, y], i) => {
        const diam = ds[i] || 0, run = tv[i] || 0;
        if (diam <= 0 || run <= 0) return;
        const r = diam / 2;
        ctx.beginPath();
        ctx.roundRect(x - r, y - r, diam + run, diam, r);
        ctx.stroke();
      });
      ctx.strokeStyle = SPACING;
      ctx.lineWidth = px * 1.6;
      ctx.setLineDash([px * 6, px * 4]);
      this.points.forEach(([x, y], i) => {
        const diam = ds[i] || 0;
        if (diam <= 0) return;
        ctx.beginPath(); ctx.arc(x, y, diam / 2, 0, Math.PI * 2); ctx.stroke();
      });
      ctx.setLineDash([]);
    }
    // El vínculo entre los que están en conflicto se ve siempre.
    for (const par of st.pairs || []) {
      const a = this.points[par.a], b = this.points[par.b];
      if (!a || !b) continue;
      ctx.strokeStyle = AREA_BAD;
      ctx.lineWidth = px * 2.4;
      ctx.setLineDash(par.kind === st.kind_sweep ? [px * 6, px * 4] : []);
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    }
    ctx.setLineDash([]);
  }

  _drawMagnetsWorld(ctx, px) {
    if (!this.points.length) return;
    const out = new Set(this.state.out || []);
    this.points.forEach(([x, y, color], i) => {
      const r = this._magnetD(color) / 2;
      const base = COLOR_MAP[color] || COLOR_MAP.red;
      ctx.globalAlpha = 0.43;
      ctx.fillStyle = base;
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = base;
      ctx.lineWidth = px * 2;
      ctx.stroke();
      if (out.has(i)) {
        ctx.strokeStyle = AREA_BAD;
        ctx.lineWidth = px * 2.6;
        ctx.setLineDash([px * 5, px * 3]);
        ctx.beginPath(); ctx.arc(x, y, r + 1.6, 0, Math.PI * 2); ctx.stroke();
        ctx.setLineDash([]);
      }
    });
  }

  _font(size, bold) {
    return `${bold ? '600 ' : ''}${size}px "Segoe UI", system-ui, -apple-system, sans-serif`;
  }

  _drawRulers(ctx, m) {
    ctx.font = this._font(10.5);
    ctx.fillStyle = this.colors.fg || '#9aa2b8';
    for (let v = 0; v <= BED_SIZE; v += 50) {
      const [bx, by] = this._toScreen(m, v, 0);
      const [lx, ly] = this._toScreen(m, 0, v);
      if (bx >= 0 && bx <= m.width && by + 14 <= m.height) {
        ctx.textAlign = 'center'; ctx.textBaseline = 'top';
        ctx.fillText(String(v), bx, by + 4);
      }
      if (ly >= 0 && ly <= m.height && lx - 4 >= 0) {
        ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
        ctx.fillText(String(v), lx - 4, ly);
      }
    }
  }

  _drawSpacingLabels(ctx, m) {
    const st = this.state;
    if (!(st.dmin > 0) || !(st.pairs || []).length) return;
    ctx.font = this._font(11, true);
    ctx.fillStyle = AREA_BAD;
    ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
    for (const par of st.pairs) {
      const a = this.points[par.a], b = this.points[par.b];
      if (!a || !b) continue;
      const [sx, sy] = this._toScreen(m, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2);
      const txt = par.kind === st.kind_sweep
        ? this.tr('canvas.sweep_label', { n: par.b + 1 })
        : `${par.distance.toFixed(1)} mm`;
      ctx.fillText(txt, sx, sy - 3);
    }
  }

  _drawMagnetLabels(ctx, m) {
    if (!this.points.length) return;
    const tops = new Map();
    for (const g of this.state.stacks || []) tops.set(g[g.length - 1], g.length);
    ctx.font = this._font(12.5, true);
    ctx.fillStyle = '#ffffff';
    this.points.forEach(([x, y, color], i) => {
      if (!tops.has(i)) return;
      const dpx = m.scale * this._magnetD(color);
      if (dpx < 16) return;
      const [sx, sy] = this._toScreen(m, x, y);
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(String(i + 1), sx, sy);
      const n = tops.get(i);
      if (n > 1) {
        ctx.textAlign = 'left'; ctx.textBaseline = 'bottom';
        ctx.fillText(`×${n}`, sx + dpx / 2 - 4, sy - dpx / 2);
      }
    });
  }

  _box(ctx, x, y, w, h, fill, stroke) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 6);
    ctx.fillStyle = fill; ctx.fill();
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1.5; ctx.stroke(); }
  }

  _drawHud(ctx, m) {
    const lines = [];
    if (this.layerZ !== null && this.layerZ !== undefined) lines.push(this.tr('canvas.hud_z', { z: this.layerZ.toFixed(2) }));
    if (this.suggested.length) lines.push(this.tr('canvas.centers_prefix', { n: this.suggested.length }).replace(/[\s·]+$/, ''));
    lines.push(this.hasLayer ? this.tr('canvas.help') : this.tr('canvas.empty'));
    ctx.font = this._font(11.5);
    const lh = 16;
    const maxW = Math.min(Math.max(...lines.map((t) => ctx.measureText(t).width)) + 16, m.width - 12);
    this._box(ctx, 6, 4, maxW, lines.length * lh + 8, this.colors.hud || 'rgba(37,42,58,0.84)');
    ctx.fillStyle = this.colors.text || '#e6e9f2';
    ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
    lines.forEach((t, i) => ctx.fillText(t, 14, 4 + 4 + lh / 2 + i * lh, maxW - 16));
  }

  _wrap(ctx, text, width) {
    const words = text.split(/\s+/), out = [];
    let line = '';
    for (const w of words) {
      const t = line ? line + ' ' + w : w;
      if (ctx.measureText(t).width > width && line) { out.push(line); line = w; } else line = t;
    }
    if (line) out.push(line);
    return out;
  }

  _drawFlash(ctx, m) {
    if (!this.flashLines.length) return;
    ctx.font = this._font(12);
    const top = Math.min(m.width - 12, Math.max(240, m.width * 0.55));
    const util = Math.max(top - 20, 40);
    const blocks = this.flashLines.map((t) => this._wrap(ctx, t, util));
    const lh = 16;
    const w = Math.max(...blocks.flat().map((t) => ctx.measureText(t).width)) + 20;
    const nLines = blocks.reduce((s, b) => s + b.length, 0);
    const h = nLines * lh + 4 * (blocks.length - 1) + 12;
    const x = m.width - w - 6;
    this._box(ctx, x, 4, w, h, this.colors.flash || 'rgba(37,42,58,0.92)', AREA_BAD);
    let y = 10;
    ctx.textAlign = 'left'; ctx.textBaseline = 'top';
    blocks.forEach((b, i) => {
      ctx.fillStyle = i === 0 ? AREA_BAD : (this.colors.text || '#e6e9f2');
      for (const t of b) { ctx.fillText(t, x + 10, y); y += lh; }
      y += 4;
    });
  }
}
