// MagnetPlace Studio — versión web.
//
// Hace el papel de magnet_app/main_window.py: monta la interfaz, guarda las
// preferencias del navegador y lleva cada acción al Python de `py/webapi.py`,
// que corre en un Web Worker con Pyodide. Ningún archivo sale del equipo: se
// leen, se procesan y se descargan dentro del propio navegador.

import { Api } from './api.js';
import { BedCanvas2D } from './bed2d.js';

const $ = (id) => document.getElementById(id);
const MARK_START = '; INICIO INSERCIÓN IMANES AUTO';
const KNOWN_LANGS = ['es', 'en', 'zh', 'ja', 'it', 'fr', 'de', 'pt'];

// Colores del lienzo 2D por tema (magnet_app/theme.py).
const CANVAS_THEMES = {
  dark: { fig_bg: '#181b26', fg: '#9aa2b8', text: '#e6e9f2', plate_top: '#8e949e',
          plate_bottom: '#6e747e', plate_edge: '#4a4f58',
          hud: 'rgba(37,42,58,0.84)', flash: 'rgba(37,42,58,0.92)' },
  light: { fig_bg: '#f4f6fb', fg: '#5c6577', text: '#1c2230', plate_top: '#a7b4cd',
           plate_bottom: '#8b9ab6', plate_edge: '#5d6a85',
           hud: 'rgba(238,241,247,0.88)', flash: 'rgba(238,241,247,0.95)' },
};
const VIEWER_THEMES = {
  dark: { bg: '#181b26', panel: 'rgba(37,42,58,0.92)', border: '#363c52', text: '#e6e9f2', text_dim: '#9aa2b8', accent: '#3b82f6' },
  light: { bg: '#f4f6fb', panel: 'rgba(238,241,247,0.94)', border: '#cfd6e4', text: '#1c2230', text_dim: '#5c6577', accent: '#2563eb' },
};

// --- preferencias del navegador (solo comodidad; si fallan, valores de fábrica)
const store = {
  get(key, fallback = null) {
    try { const v = localStorage.getItem('mps.' + key); return v === null ? fallback : v; } catch (_) { return fallback; }
  },
  set(key, value) { try { localStorage.setItem('mps.' + key, String(value)); } catch (_) { /* sin almacenamiento */ } },
};

// --- estado ----------------------------------------------------------------
let api = null;
let TR = {};
let LANG = 'es';
let LANGUAGES = [];
let OPTIONS = null;
let DEFAULTS = null;
let VERSION = '';
const S = {
  settings: null,
  ui: null,
  theme: 'dark',
  mode: '2d',
  dirty3d: true,
  seqKey: 'seq_red',
  preview: { text: '', mark: -1 },
  templateName: null,
  viewerReady: false,
};

// --- traducción ------------------------------------------------------------
function format(text, params) {
  return text.replace(/\{\{|\}\}|\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (m, k) => {
    if (m === '{{') return '{';
    if (m === '}}') return '}';
    return params && k in params ? String(params[k]) : m;
  });
}
function tr(key, params) {
  const e = TR[key];
  if (!e) return key;
  const text = e[LANG] || e.en || e.es || key;
  return format(text, params).replace(/&(?=\S)/g, '');   // sin los atajos "&Archivo" de Qt
}
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
function trSafe(key, params) {
  const p = {};
  for (const k in params || {}) p[k] = esc(params[k]);
  return tr(key, p);
}

function applyStaticTexts() {
  document.documentElement.lang = LANG;
  document.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = tr(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-html]').forEach((el) => { el.innerHTML = tr(el.dataset.i18nHtml); });
  document.querySelectorAll('[data-i18n-title]').forEach((el) => { el.title = tr(el.dataset.i18nTitle); });
  $('version').textContent = `${'MagnetPlace Studio'} v${VERSION} · web`;
}

// --- estado de trabajo y mensajes ------------------------------------------
function setStatus(html) { $('status').innerHTML = html || ''; }
function busy(on, msg) {
  $('busy').hidden = !on;
  $('busyMsg').textContent = msg || tr('viewer.loading');
}

// --- diálogos --------------------------------------------------------------
/**
 * Abre un diálogo y resuelve con el `value` del botón pulsado (null = cerrado).
 * `ack` añade el recuadro de responsabilidad y apaga los botones `needsAck`
 * hasta que se marca, como `ProblemWarningDialog(require_ack=True)`.
 */
function openModal({ title, html = '', el = null, buttons = [], ack = false, wide = false, onOpen = null }) {
  return new Promise((resolve) => {
    const back = document.createElement('div');
    back.className = 'modal-back';
    const box = document.createElement('div');
    box.className = 'modal' + (wide ? ' wide' : '');
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    const head = document.createElement('header');
    head.textContent = title || '';
    const body = document.createElement('div');
    body.className = 'body';
    if (html) body.innerHTML = html;
    if (el) body.appendChild(el);
    box.append(head, body);
    let ackBox = null;
    if (ack) {
      const wrap = document.createElement('div');
      wrap.className = 'ack';
      wrap.innerHTML = `<label class="chk"><input type="checkbox"><span>${esc(tr('risk.accept'))}</span></label>
        <p class="muted">${esc(tr('risk.accept_hint'))}</p>`;
      ackBox = wrap.querySelector('input');
      box.appendChild(wrap);
    }
    const foot = document.createElement('div');
    foot.className = 'foot';
    const close = (v) => { back.remove(); document.removeEventListener('keydown', onKey, true); resolve(v); };
    const gated = [];
    for (const b of buttons) {
      const btn = document.createElement('button');
      btn.textContent = b.label;
      if (b.accent) btn.className = 'accent';
      if (b.left) btn.classList.add('left');
      btn.addEventListener('click', () => (b.onClick ? b.onClick() : close(b.value)));
      if (b.needsAck && ackBox) { btn.disabled = true; gated.push(btn); }
      foot.appendChild(btn);
      if (b.focus) setTimeout(() => btn.focus(), 0);
    }
    if (ackBox) ackBox.addEventListener('change', () => gated.forEach((b) => { b.disabled = !ackBox.checked; }));
    box.appendChild(foot);
    back.appendChild(box);
    const onKey = (e) => { if (e.key === 'Escape' && back.isConnected && back === $('modalRoot').lastElementChild) { e.stopPropagation(); close(null); } };
    document.addEventListener('keydown', onKey, true);
    $('modalRoot').appendChild(back);
    if (onOpen) onOpen(body, close);
  });
}
const okButton = () => ({ label: tr('common.ok'), value: true, accent: true, focus: true });
function msgBox(title, html) { return openModal({ title, html: `<p>${html}</p>`, buttons: [okButton()] }); }
function errorBox(r) {
  const detail = r.detail ? `<p class="muted">${esc(r.detail)}</p>` : '';
  return openModal({ title: tr('msg.warning'), html: `<p><b>${r.error}</b></p>${detail}`, buttons: [okButton()] });
}
function listHtml(items) { return items.map((t) => `<p>${t}</p>`).join(''); }

// --- aplicar respuestas de Python ------------------------------------------
let canvas = null;

function apply(r, { fillForm = false } = {}) {
  if (!r) return;
  if (r.settings && fillForm) { S.settings = r.settings; fillForms(); }
  if (r.layer !== undefined) {
    canvas.setLayer(r.layer, r.ui ? r.ui.suggested : []);
    S.dirty3d = true;
    S.preview = { text: '', mark: -1 };
    $('previewText').value = '';
    $('lblPreview').textContent = '';
  }
  if (r.ui) { S.ui = r.ui; renderUi(); canvas.setSuggested(r.ui.suggested); }
  if (r.canvas) { canvas.setState(r.canvas); renderPointsList(); S.dirty3d = true; }
  if (r.status) setStatus(r.status);
}

function renderUi() {
  const ui = S.ui;
  if (!ui) return;
  $('infoLabel').innerHTML = ui.info;
  $('lblArea').textContent = ui.area_hint;
  $('lblSpacing').textContent = ui.spacing_hint;
  $('lblMatch').textContent = ui.match_hint;
  $('lblMatch').hidden = !ui.match_hint;
  $('lblFit').innerHTML = ui.fit_hint;
  $('pauseBar').hidden = !(ui.pause_total > 1);
  $('lblPause').textContent = tr('pause.nav', { n: ui.pause_n, total: ui.pause_total });
  $('btnPrevPause').disabled = ui.pause_n <= 1;
  $('btnNextPause').disabled = ui.pause_n >= ui.pause_total;
  $('btnPreview').disabled = !ui.has_file;
  $('btnExport').disabled = !ui.has_file;
}

function persistSettings() {
  if (S.settings) store.set('settings', JSON.stringify(S.settings));
}

// --- puntos ------------------------------------------------------------------
let inflight = false;
let pendingDrag = false;
let latestSeq = 0;

function onPointsChanged(_points, dragging) {
  if (dragging) {
    if (inflight) { pendingDrag = true; return; }
    sendPoints(true);
  } else {
    sendPoints(false);
  }
}

function sendPoints(dragging) {
  const my = ++latestSeq;
  inflight = true;
  const pts = canvas.points.map((p) => [p[0], p[1], p[2]]);
  api.call('update_points', pts, dragging).then((r) => {
    inflight = false;
    const latest = my === latestSeq;
    if (r.canvas && (latest || dragging)) {
      canvas.setState(r.canvas, { keepPoints: canvas.dragging || !latest });
      if (latest && !canvas.dragging) renderPointsList();
      S.dirty3d = true;
    }
    if (pendingDrag && canvas.dragging) { pendingDrag = false; sendPoints(true); }
  }).catch((err) => { inflight = false; console.error(err); });
}

function renderPointsList() {
  const list = $('pointsList');
  const sel = list.selectedIndex;
  const pts = canvas.points;
  const pos = new Map();
  for (const g of canvas.state.stacks || []) g.forEach((idx, k) => pos.set(idx, [k + 1, g.length]));
  list.innerHTML = '';
  pts.forEach(([x, y, c], i) => {
    const [k, total] = pos.get(i) || [1, 1];
    const o = document.createElement('option');
    const pila = total > 1 ? `  (${k}/${total})` : '';
    o.textContent = `${i + 1}. ${c.padStart(4, ' ')}  X=${x.toFixed(2)}  Y=${y.toFixed(2)}${pila}`;
    list.appendChild(o);
  });
  if (sel >= 0 && sel < pts.length) list.selectedIndex = sel;
}

// --- color de imán a colocar ------------------------------------------------
function currentColor() { return document.querySelector('input[name=mcolor]:checked').value; }
function setColor(c) {
  const rb = document.querySelector(`input[name=mcolor][value=${c}]`);
  if (rb && !rb.disabled) { rb.checked = true; canvas.setCurrentColor(c); }
}
function updateColorRadios() {
  const avail = new Set((S.settings.modules || []).map((m) => m.color));
  document.querySelectorAll('input[name=mcolor]').forEach((rb) => {
    const ok = avail.has(rb.value);
    rb.disabled = !ok;
    rb.parentElement.classList.toggle('disabled', !ok);
    rb.parentElement.title = ok ? '' : tr('left.no_module');
  });
  const cur = currentColor();
  if (!avail.has(cur)) {
    const other = cur === 'red' ? 'blue' : 'red';
    if (avail.has(other)) setColor(other);
  }
  canvas.setCurrentColor(currentColor());
}

// --- formularios -----------------------------------------------------------
let pushTimer = null;
function schedulePush(delay = 300) {
  clearTimeout(pushTimer);
  pushTimer = setTimeout(pushSettings, delay);
}
async function pushSettings() {
  clearTimeout(pushTimer);
  pushTimer = null;
  persistSettings();
  // Cambiar un imán puede rehacer la detección, que tarda unos segundos.
  if (S.mode === '2d' && S.ui && S.ui.has_file) $('viewerStatus').textContent = tr('viewer.loading');
  const r = await api.call('set_settings', S.settings);
  if (S.mode === '2d') $('viewerStatus').textContent = '';
  if (r.error) { errorBox(r); return; }
  delete r.settings;          // el formulario manda: no se pisa lo que se está escribiendo
  apply(r);
  S.dirty3d = true;
}
async function flushSettings() { if (pushTimer) await pushSettings(); }

function fillForms() {
  const s = S.settings;
  document.querySelectorAll('[data-key]').forEach((el) => {
    const v = s[el.dataset.key];
    if (el.type === 'checkbox') el.checked = !!v;
    else if (el.dataset.key === 'features') el.value = (v || []).join(', ');
    else el.value = v;
  });
  $('seqEditor').value = s[S.seqKey] || '';
  renderModules();
  updateDetectionEnabled();
  updateColorRadios();
}

function updateDetectionEnabled() {
  const on = !!S.settings.hole_detection_enabled;
  const match = !!S.settings.hole_match_modules;
  document.querySelectorAll('#tab-params .det').forEach((el) => { el.disabled = !on; });
  document.querySelectorAll('#tab-params .rad').forEach((el) => { el.disabled = !on || match; });
}

function bindParamInputs() {
  document.querySelectorAll('#tab-params [data-key]').forEach((el) => {
    const key = el.dataset.key;
    const handler = () => {
      if (el.type === 'checkbox') S.settings[key] = el.checked;
      else if (key === 'features') S.settings[key] = el.value.split(',').map((t) => t.trim()).filter(Boolean);
      else if (el.type === 'number') {
        const v = parseFloat(el.value);
        if (Number.isNaN(v)) return;
        S.settings[key] = v;
      } else S.settings[key] = el.value.trim() || (key === 'pause_token' ? 'M400 U1' : '');
      updateDetectionEnabled();
      schedulePush(el.type === 'checkbox' ? 0 : 350);
    };
    el.addEventListener(el.type === 'checkbox' ? 'change' : 'input', handler);
  });
}

// --- tarjetas de módulo ----------------------------------------------------
function moduleSketch(m) {
  // Boceto acotado con la proporción real diámetro:altura (como ModuleCard).
  const fill = m.color === 'blue' ? '#2b6cff' : '#e23b3b';
  const top = m.color === 'blue' ? '#5b8dff' : '#f06a6a';
  const maxW = 84, maxH = 60;
  const k = Math.min(maxW / m.diameter, maxH / m.height, 12);
  const w = m.diameter * k, h = m.height * k;
  const x = (120 - w) / 2, y = 18 + (66 - h) / 2;
  return `<svg width="120" height="104" viewBox="0 0 120 104" aria-hidden="true">
    <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="${fill}" />
    <rect x="${x}" y="${y}" width="${w}" height="${Math.max(h * 0.18, 3)}" rx="2" fill="${top}" />
    <text x="60" y="${y - 5}" text-anchor="middle" font-size="11" fill="currentColor">${esc(m.polarity)}</text>
    <text x="60" y="100" text-anchor="middle" font-size="11" fill="currentColor">⌀${m.diameter} × ${m.height} mm</text>
  </svg>`;
}

function option(value, label, selected) {
  return `<option value="${esc(value)}"${selected ? ' selected' : ''}>${esc(label)}</option>`;
}

function renderModules() {
  const box = $('moduleCards');
  box.innerHTML = '';
  const mods = S.settings.modules || [];
  mods.forEach((m, i) => {
    const allowed = OPTIONS.allowed_heights[String(m.diameter)] || OPTIONS.heights;
    const capped = allowed.length < OPTIONS.heights.length;
    const card = document.createElement('div');
    card.className = 'mod-card ' + m.color;
    const auto = tr('mod.default_name', { n: i + 1 });
    card.innerHTML = `
      <div class="mod-head"><span class="title"></span>
        <button class="x" title="${esc(tr('mod.remove'))}" aria-label="${esc(tr('mod.remove'))}">✕</button></div>
      <div class="form">
        <label>${esc(tr('mod.name'))}</label><input type="text" data-f="name" placeholder="${esc(auto)}">
        <label>${esc(tr('mod.color'))}</label><select data-f="color">
          ${option('red', tr('mod.color_red'), m.color === 'red')}${option('blue', tr('mod.color_blue'), m.color === 'blue')}</select>
        <label>${esc(tr('mod.diameter'))}</label><select data-f="diameter">
          ${OPTIONS.diameters.map((d) => option(d, String(d), d === m.diameter)).join('')}</select>
        <label>${esc(capped ? tr('mod.height_capped', { max: OPTIONS.max_height[String(m.diameter)] }) : tr('mod.height'))}</label>
        <select data-f="height">${allowed.map((h) => option(h, String(h), h === m.height)).join('')}</select>
        <label>${esc(tr('mod.polarity'))}</label><select data-f="polarity">
          ${option('N', tr('mod.pole_n'), m.polarity === 'N')}${option('S', tr('mod.pole_s'), m.polarity === 'S')}</select>
        <label>${esc(tr('mod.grade'))}</label><select data-f="grade">
          ${OPTIONS.grades.map((g) => option(g, g, g === m.grade)).join('')}</select>
        <label>${esc(tr('mod.pull_kg'))}</label><input type="number" min="0" step="0.1" data-f="pull_kg" title="${esc(tr('mod.pull_kg_hint'))}">
      </div>
      <div class="mod-sketch">${moduleSketch(m)}</div>
      <p class="muted small" style="grid-column:1/-1;margin:0">${esc(tr('mod.pole_hint', { pole: m.polarity }))} · ${esc(tr('mod.pull_kg_hint'))}</p>`;
    card.querySelector('.title').textContent = m.name || auto;
    const nameIn = card.querySelector('[data-f=name]');
    nameIn.value = m.name || '';
    card.querySelector('[data-f=pull_kg]').value = m.pull_kg || 0;
    nameIn.addEventListener('input', () => {
      m.name = nameIn.value;
      card.querySelector('.title').textContent = m.name || auto;
      schedulePush(500);
    });
    card.querySelector('[data-f=pull_kg]').addEventListener('input', (e) => {
      const v = parseFloat(e.target.value);
      m.pull_kg = Number.isNaN(v) ? 0 : Math.max(v, 0);
      schedulePush(400);
    });
    card.querySelectorAll('select').forEach((sel) => sel.addEventListener('change', () => {
      const f = sel.dataset.f;
      if (f === 'color') {
        // Un dispensador por color: si el otro módulo ya lo tenía, se intercambian.
        const other = mods.find((o) => o !== m && o.color === sel.value);
        if (other) other.color = m.color;
        m.color = sel.value;
      } else if (f === 'diameter' || f === 'height') {
        m[f] = parseFloat(sel.value);
        const ok = OPTIONS.allowed_heights[String(m.diameter)] || OPTIONS.heights;
        if (!ok.includes(m.height)) m.height = Math.max(...ok);
      } else {
        m[f] = sel.value;
      }
      renderModules();
      updateColorRadios();
      schedulePush(0);
    }));
    card.querySelector('.x').addEventListener('click', () => {
      mods.splice(i, 1);
      renderModules();
      updateColorRadios();
      schedulePush(0);
    });
    box.appendChild(card);
  });
  $('btnAddModule').disabled = mods.length >= OPTIONS.max_modules;
}

function addModule() {
  const mods = S.settings.modules;
  if (mods.length >= OPTIONS.max_modules) return;
  const used = new Set(mods.map((m) => m.color));
  const color = OPTIONS.colors.find((c) => !used.has(c)) || OPTIONS.colors[0];
  const proto = DEFAULTS.modules[0];
  mods.push({ ...proto, name: '', diameter: 6, height: 3, color });
  renderModules();
  updateColorRadios();
  schedulePush(0);
}

// --- pestañas --------------------------------------------------------------
function showTab(name) {
  document.querySelectorAll('#tabs button').forEach((b) => b.classList.toggle('on', b.dataset.tab === name));
  document.querySelectorAll('.tab-page').forEach((p) => p.classList.toggle('on', p.id === 'tab-' + name));
}

// --- archivos --------------------------------------------------------------
function download(data, name, type = 'application/octet-stream') {
  const blob = data instanceof Blob ? data : new Blob([data], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

function safeName(name) { return name.replace(/[\\/]/g, '_'); }

async function openFile(file) {
  if (!file) return;
  if (/\.mip$/i.test(file.name)) { openProjectFile(file); return; }
  await flushSettings();
  busy(true, `${tr('viewer.loading')} ${file.name}`);
  try {
    const name = safeName(file.name);
    const path = '/work/in/' + name;
    await api.writeFile(path, await file.arrayBuffer());
    const r = await api.call('load_file', path, name);
    if (r.error) { busy(false); await errorBox(r); return; }
    apply(r, { fillForm: !!r.project_applied });
    busy(false);
    if (S.mode === '3d') refresh3d();
    if (r.problems && r.problems.length) await msgBox(r.problems_title, r.problems.join('<br><br>'));
    if (r.project_applied) flashOutside();
  } catch (err) {
    busy(false);
    errorBox({ error: tr('msg.error_analyze'), detail: String(err.message || err) });
  }
}

function flashOutside() {
  const n = (canvas.state.out || []).length;
  if (n) canvas.flash(tr('canvas.points_outside_title', { n }), tr('canvas.points_outside_fix'));
}

async function openProjectFile(file) {
  await flushSettings();
  busy(true);
  try {
    const r = await api.call('load_project', await file.text());
    busy(false);
    if (r.error) { errorBox(r); return; }
    apply(r, { fillForm: true });
    persistSettings();
    if (S.mode === '3d') refresh3d();
    if (r.warn) await msgBox(tr('msg.warning'), r.warn);
    flashOutside();
  } catch (err) {
    busy(false);
    errorBox({ error: tr('msg.error_analyze'), detail: String(err.message || err) });
  }
}

async function saveProject() {
  await flushSettings();
  const r = await api.call('save_project');
  download(r.text, r.name, 'application/json');
  setStatus(esc(r.name));
}

// --- avisos antes de generar -----------------------------------------------
function riskBody(d) {
  let h = '';
  if (d.header) h += `<p class="head">${d.header}</p>`;
  else h += `<p class="head">${esc(d.title)}</p>`;
  for (const p of d.paragraphs || []) h += `<p>${p}</p>`;
  for (const t of d.items || []) h += `<p>${t}</p>`;
  if (d.rows && d.rows.length) h += `<ul class="rows">${d.rows.map((r) => `<li>${r}</li>`).join('')}</ul>`;
  if (d.box) h += `<div class="box">${d.box}</div>`;
  if (d.footer) h += `<p class="muted">${d.footer}</p>`;
  return h;
}

/** Pasa por los bloqueos y los cuatro riesgos (MainWindow._generate_text). */
async function runChecks(alwaysAsk, requireAck) {
  await flushSettings();
  const r = await api.call('prepare_generate', alwaysAsk);
  if (r.error) { await msgBox(tr('msg.warning'), r.error); return false; }
  if (r.blocking) {
    await openModal({ title: r.blocking.title,
      html: `<p class="head">${esc(r.blocking.title)}</p>${listHtml(r.blocking.items)}`,
      buttons: [{ label: tr('common.close'), value: true, accent: true, focus: true }] });
    return false;
  }
  const dialogs = r.dialogs || [];
  for (let i = 0; i < dialogs.length; i++) {
    const d = dialogs[i];
    const last = requireAck && i === dialogs.length - 1;
    const buttons = [];
    if (d.details) buttons.push({ label: tr('spacing.see_details'), left: true, onClick: showSpacingInfo });
    buttons.push({ label: tr('common.cancel'), value: false, focus: true });
    buttons.push({ label: d.accept || tr('common.ok'), value: true, needsAck: last });
    const ok = await openModal({ title: d.title, html: riskBody(d), buttons, ack: last });
    if (!ok) { setStatus(d.cancel_status); return false; }
    await api.call('ack', d.kind, d.fp);
  }
  return true;
}

async function doPreview() {
  if (!(await runChecks(false, false))) return;
  busy(true);
  const r = await api.call('generate');
  busy(false);
  if (r.error) { errorBox(r); return; }
  S.preview = { text: r.text, mark: r.mark };
  $('previewText').value = r.text;
  $('lblPreview').textContent = r.info;
  showTab('preview');
  gotoMagnets();
}

function gotoMagnets() {
  const ta = $('previewText');
  const mark = S.preview.mark;
  if (!S.preview.text || mark < 0) return;
  const before = S.preview.text.slice(0, mark);
  let lines = 0;
  for (let i = 0; i < before.length; i++) if (before.charCodeAt(i) === 10) lines++;
  ta.focus({ preventScroll: true });
  ta.setSelectionRange(mark, mark + MARK_START.length);
  const lh = parseFloat(getComputedStyle(ta).lineHeight) || 16;
  ta.scrollTop = Math.max(lines * lh - ta.clientHeight / 2, 0);
}

function chooseFormat(title, first, second) {
  return openModal({ title, html: '', buttons: [
    { label: tr('common.cancel'), value: null },
    { label: second.label, value: second.value },
    { label: first.label, value: first.value, accent: true, focus: true },
  ] });
}

async function doExport() {
  if (!(await runChecks(true, true))) return;
  let fmt = 'gcode';
  if (S.ui.is_3mf) {
    fmt = await chooseFormat(tr('msg.export_title'),
      { label: 'Bambu 3MF (.gcode.3mf)', value: '3mf' }, { label: 'G-code (.gcode)', value: 'gcode' });
    if (!fmt) return;
  }
  busy(true);
  try {
    const r = await api.call('export', fmt);
    if (r.error) { busy(false); errorBox(r); return; }
    const bytes = await api.readFile(r.file);
    busy(false);
    download(bytes, r.name);
    setStatus(r.status);
    msgBox(tr('msg.exported_title'), r.message);
  } catch (err) {
    busy(false);
    errorBox({ error: tr('msg.error_export'), detail: String(err.message || err) });
  }
}

function pickFile(input) {
  return new Promise((resolve) => {
    input.value = '';
    input.onchange = () => resolve(input.files[0] || null);
    input.click();
  });
}

async function chooseTemplate() {
  const file = await pickFile($('templateInput'));
  if (!file) return false;
  const name = safeName(file.name);
  const path = '/work/template/' + name;
  await api.writeFile(path, await file.arrayBuffer());
  const r = await api.call('set_template', path);
  if (r.error) { await msgBox(tr('msg.warning'), r.error); return false; }
  S.templateName = file.name;
  return true;
}

async function doTestSequence() {
  await flushSettings();
  const fmt = await chooseFormat(tr('msg.test_export_title'),
    { label: 'Bambu 3MF (.3mf)', value: '3mf' }, { label: 'G-code (.gcode)', value: 'gcode' });
  if (!fmt) return;
  let r = await api.call('test_sequence', fmt);
  if (r.need_template) {
    await msgBox(tr('msg.test_export_title'), esc(r.message));
    if (!(await chooseTemplate())) return;
    r = await api.call('test_sequence', fmt);
  }
  if (r.error) { errorBox(r); return; }
  const bytes = await api.readFile(r.file);
  download(bytes, r.name);
  setStatus(r.status);
  msgBox(tr('msg.exported_title'), r.message);
}

// --- vista 3D --------------------------------------------------------------
let viewerBooted = null;
function ensureViewer() {
  if (viewerBooted) return viewerBooted;
  const frame = $('v3d');
  viewerBooted = new Promise((resolve) => {
    const onMsg = (ev) => {
      if (ev.origin !== location.origin || !ev.data || ev.data.source !== 'mps-viewer') return;
      if (ev.data.kind === 'booted') { S.viewerReady = true; resolve(frame.contentWindow.mps); }
      if (ev.data.kind === 'error') $('viewerStatus').textContent = String(ev.data.data && ev.data.data.message || '');
      if (ev.data.kind === 'loaded') $('viewerStatus').textContent = '';
    };
    window.addEventListener('message', onMsg);
    frame.src = 'viewer3d/viewer.html';
  });
  return viewerBooted;
}

async function setMode(mode) {
  S.mode = mode;
  const is3d = mode === '3d';
  $('btn2d').classList.toggle('on', !is3d);
  $('btn3d').classList.toggle('on', is3d);
  $('v3d').hidden = !is3d;
  $('bed').hidden = is3d;
  $('zoomCtl').hidden = is3d;
  $('lblInfill').hidden = is3d;
  $('btnRefresh3d').hidden = !is3d;
  $('colorByWrap').hidden = !is3d;
  if (is3d) {
    const mps = await ensureViewer();
    mps.setTheme(VIEWER_THEMES[S.theme]);
    mps.setColorMode($('selColorBy').value);
    if (S.dirty3d) refresh3d();
  } else {
    if (S.viewerReady) $('v3d').contentWindow.mps.pause();
    canvas.render();
  }
}

async function refresh3d() {
  const mps = await ensureViewer();
  if (!S.ui || !S.ui.has_file) {
    mps.setTexts(viewerTexts());
    return;
  }
  $('viewerStatus').textContent = tr('viewer.loading');
  await flushSettings();
  const r = await api.call('build_3d');
  if (r.error) { $('viewerStatus').textContent = r.error; return; }
  if (r.empty) { $('viewerStatus').textContent = ''; return; }
  mps.load(r);
  S.dirty3d = false;
}

function viewerTexts() {
  const keys = ['viewer.no_file_3d', 'v3d.play', 'v3d.pause', 'v3d.reset', 'v3d.speed', 'v3d.layer', 'v3d.color_by',
    'v3d.legend', 'v3d.panel_hide', 'v3d.panel_show', 'v3d.color_feature', 'v3d.color_phase', 'v3d.color_layer',
    'v3d.color_speed', 'v3d.show_travel', 'v3d.show_volume', 'v3d.show_model', 'v3d.follow', 'v3d.stop_at_pause',
    'v3d.phase_before', 'v3d.phase_magnets', 'v3d.phase_after', 'v3d.phase_before_tip', 'v3d.phase_magnets_tip',
    'v3d.phase_after_tip', 'v3d.magnets', 'v3d.no_pause', 'feat.outer_wall', 'feat.inner_wall', 'feat.top_surface',
    'feat.bottom_surface', 'feat.solid_infill', 'feat.infill', 'feat.bridge', 'feat.support', 'feat.skirt',
    'feat.gap', 'feat.other'];
  const out = {};
  for (const k of keys) out[k] = tr(k);
  return out;
}

// --- tema e idioma ---------------------------------------------------------
function applyTheme(name) {
  S.theme = name === 'light' ? 'light' : 'dark';
  document.documentElement.dataset.theme = S.theme;
  canvas.setTheme(CANVAS_THEMES[S.theme]);
  if (S.viewerReady) $('v3d').contentWindow.mps.setTheme(VIEWER_THEMES[S.theme]);
}

async function setLanguage(lang) {
  const r = await api.call('set_language', lang);
  LANG = r.language;
  store.set('lang', LANG);
  applyStaticTexts();
  renderModules();
  apply({ ui: r.ui });
  renderPointsList();
  canvas.render();
  S.dirty3d = true;
  if (S.viewerReady) {
    $('v3d').contentWindow.mps.setTexts(viewerTexts());
    if (S.mode === '3d') refresh3d();
  }
}

async function showPreferences() {
  const el = document.createElement('div');
  el.innerHTML = `<div class="form">
    <label>${esc(tr('prefs.language'))}</label>
    <select id="prefLang">${LANGUAGES.map(([c, n]) => option(c, n, c === LANG)).join('')}</select>
    <label>${esc(tr('prefs.theme'))}</label>
    <select id="prefTheme">${option('dark', tr('prefs.theme_dark'), S.theme === 'dark')}${option('light', tr('prefs.theme_light'), S.theme === 'light')}</select>
    <label>${esc(tr('prefs.template'))}</label>
    <div class="row"><span id="prefTpl" class="muted">${esc(S.templateName || tr('prefs.template_none'))}</span>
      <button id="prefTplBtn">…</button></div>
  </div>`;
  const ok = await openModal({ title: tr('prefs.title'), el, buttons: [
    { label: tr('common.cancel'), value: false },
    { label: tr('common.ok'), value: true, accent: true, focus: true },
  ], onOpen: (body) => {
    body.querySelector('#prefTplBtn').addEventListener('click', async () => {
      if (await chooseTemplate()) body.querySelector('#prefTpl').textContent = S.templateName;
    });
  } });
  if (!ok) return;
  const lang = el.querySelector('#prefLang').value;
  const theme = el.querySelector('#prefTheme').value;
  if (theme !== S.theme) { applyTheme(theme); store.set('theme', theme); }
  if (lang !== LANG) await setLanguage(lang);
}

async function showSpacingInfo() {
  await flushSettings();
  const r = await api.call('spacing_info');
  openModal({ title: r.title, html: r.html, wide: true,
    buttons: [{ label: tr('common.close'), value: true, accent: true, focus: true }] });
}

function showAbout() {
  // Como el diálogo «Acerca de» de escritorio, siempre en inglés.
  openModal({ title: 'About MagnetPlace Studio', html: `
    <p><b>MagnetPlace Studio</b> v${esc(VERSION)} — web edition</p>
    <p>Inserts custom G-code into Bambu <code>.gcode.3mf</code> / <code>.gcode</code> files to place magnets during a print pause.</p>
    <p>Everything runs inside your browser: your files are never uploaded anywhere.</p>
    <p class="muted">© 2026 MagnetPlace · <a href="https://magnetplace.app" target="_blank" rel="noopener">magnetplace.app</a></p>`,
    buttons: [{ label: 'Close', value: true, accent: true, focus: true }] });
}

// --- calibración («¡Calibra tu MagnetPlace!») -------------------------------
const CALIB_FILE = 'MagnetPlace_Calibration.3mf';
const CALIB_STEPS = [
  { media: '1-comprobacion-manual.mp4', title: 'calib.beginner.s1.title', body: 'calib.beginner.s1.body' },
  { media: '2-secuencia-automatica.mp4', title: 'calib.beginner.s2.title', body: 'calib.beginner.s2.body' },
];

function showCalibration(firstRun = false) {
  store.set('calibSeen', '1');
  let idx = 0;
  const el = document.createElement('div');
  const render = () => {
    const st = CALIB_STEPS[idx];
    el.innerHTML = `
      <h4>${esc(tr('calib.beginner.name'))}</h4>
      ${idx === 0 ? `<p>${tr('calib.beginner.intro')}</p>` : ''}
      <p class="muted">${esc(tr('calib.step_counter', { n: idx + 1, total: CALIB_STEPS.length }))}</p>
      <h4>${esc(tr(st.title))}</h4>
      <video src="assets/calibration/${st.media}" controls playsinline preload="metadata"></video>
      <p>${tr(st.body)}</p>
      ${idx === CALIB_STEPS.length - 1 ? `<p><a class="dl" href="assets/calibration/${CALIB_FILE}" download><button class="accent">${esc(tr('calib.download', { file: CALIB_FILE }))}</button></a></p>` : ''}
      ${firstRun ? `<p class="muted small">${esc(tr('calib.first_run_hint'))}</p>` : ''}`;
    prev.disabled = idx === 0;
    next.disabled = idx === CALIB_STEPS.length - 1;
  };
  let prev, next;
  let closeCalib = () => {};
  openModal({ title: tr('calib.title'), el, wide: true, buttons: [
    { label: tr('calib.skip'), left: true, onClick: async () => {
      const sure = await openModal({ title: tr('calib.skip_confirm_title'), html: `<p>${tr('calib.skip_confirm_body')}</p>`,
        buttons: [{ label: tr('common.cancel'), value: false, focus: true }, { label: tr('calib.skip'), value: true, accent: true }] });
      if (sure) closeCalib();
    } },
    { label: tr('calib.prev'), onClick: () => { idx = Math.max(idx - 1, 0); render(); } },
    { label: tr('calib.next'), onClick: () => { idx = Math.min(idx + 1, CALIB_STEPS.length - 1); render(); } },
    { label: tr('common.close'), value: true, accent: true },
  ], onOpen: (_body, close) => {
    closeCalib = () => close(true);
    const btns = el.parentElement.parentElement.querySelectorAll('.foot button');
    prev = btns[1]; next = btns[2];
    render();
  } });
}

// --- cableado ---------------------------------------------------------------
function bindUi() {
  $('btnOpen').addEventListener('click', async () => openFile(await pickFile($('fileInput'))));
  $('btnOpenProject').addEventListener('click', async () => { const f = await pickFile($('projectInput')); if (f) openProjectFile(f); });
  $('btnSaveProject').addEventListener('click', saveProject);
  $('btnPreview').addEventListener('click', doPreview);
  $('btnExport').addEventListener('click', doExport);
  $('btnPrefs').addEventListener('click', showPreferences);
  $('btnAbout').addEventListener('click', showAbout);
  $('btnCalib').addEventListener('click', () => showCalibration(false));

  document.querySelectorAll('input[name=mcolor]').forEach((rb) => rb.addEventListener('change', () => canvas.setCurrentColor(currentColor())));
  $('btn2d').addEventListener('click', () => setMode('2d'));
  $('btn3d').addEventListener('click', () => setMode('3d'));
  $('btnRefresh3d').addEventListener('click', refresh3d);
  $('selColorBy').addEventListener('change', () => { if (S.viewerReady) $('v3d').contentWindow.mps.setColorMode($('selColorBy').value); });
  $('chkInfill').addEventListener('change', () => canvas.setHideInfill($('chkInfill').checked));
  $('zoomIn').addEventListener('click', () => canvas.zoom(1 / 1.4));
  $('zoomOut').addEventListener('click', () => canvas.zoom(1.4));
  $('zoomFit').addEventListener('click', () => canvas.resetView());

  $('btnPrevPause').addEventListener('click', () => goPause(-1));
  $('btnNextPause').addEventListener('click', () => goPause(+1));
  $('btnCollapse').addEventListener('click', () => {
    const c = $('main').classList.toggle('collapsed');
    $('btnCollapse').textContent = c ? '◀' : '▶';
  });

  document.querySelectorAll('#tabs button').forEach((b) => b.addEventListener('click', () => showTab(b.dataset.tab)));

  // Parámetros
  const adv = store.get('advanced') === '1';
  $('chkAdvanced').checked = adv;
  $('tab-params').classList.toggle('basic', !adv);
  $('chkAdvanced').addEventListener('change', () => {
    $('tab-params').classList.toggle('basic', !$('chkAdvanced').checked);
    store.set('advanced', $('chkAdvanced').checked ? '1' : '0');
  });
  $('chkShowArea').addEventListener('change', () => canvas.setShowArea($('chkShowArea').checked));
  $('chkShowSpacing').addEventListener('change', () => canvas.setShowSpacing($('chkShowSpacing').checked));
  $('chkAutoReorder').checked = store.get('autoReorder', '1') === '1';
  $('chkAutoReorder').addEventListener('change', async () => {
    store.set('autoReorder', $('chkAutoReorder').checked ? '1' : '0');
    const r = await api.call('set_auto_reorder', $('chkAutoReorder').checked);
    apply(r);
  });
  $('btnSpacingInfo').addEventListener('click', showSpacingInfo);
  bindParamInputs();
  $('btnRerun').addEventListener('click', async () => {
    await flushSettings();
    const r = await api.call('rerun_detection');
    if (r.error && !r.ui) { msgBox(tr('msg.warning'), r.error); return; }
    apply(r);
  });
  $('btnResetParams').addEventListener('click', async () => {
    const r = await api.call('reset_params');
    apply(r, { fillForm: true });
    persistSettings();
  });

  // Módulos
  $('btnAddModule').addEventListener('click', addModule);

  // Secuencias
  document.querySelectorAll('#seqTabs button').forEach((b) => b.addEventListener('click', () => {
    S.seqKey = b.dataset.seq;
    document.querySelectorAll('#seqTabs button').forEach((o) => o.classList.toggle('on', o === b));
    $('seqEditor').value = S.settings[S.seqKey] || '';
  }));
  $('seqEditor').addEventListener('input', () => { S.settings[S.seqKey] = $('seqEditor').value; schedulePush(500); });
  $('btnExportTest').addEventListener('click', doTestSequence);
  $('btnResetSeq').addEventListener('click', async () => {
    await flushSettings();
    const r = await api.call('reset_sequences');
    apply(r, { fillForm: true });
    persistSettings();
  });

  // Puntos
  $('btnDelPoint').addEventListener('click', deleteSelectedPoint);
  $('btnClearPoints').addEventListener('click', () => { canvas.points = []; onPointsChanged(canvas.points, false); });
  $('pointsList').addEventListener('keydown', (e) => { if (e.key === 'Delete' || e.key === 'Backspace') deleteSelectedPoint(); });

  // Vista previa
  $('btnGenPreview').addEventListener('click', doPreview);
  $('btnGoto').addEventListener('click', gotoMagnets);

  // Teclado: M/N eligen color, como en la app de escritorio.
  document.addEventListener('keydown', (e) => {
    if ($('modalRoot').children.length) return;
    const t = e.target;
    const typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT');
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'o') { e.preventDefault(); $('btnOpen').click(); return; }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); saveProject(); return; }
    if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === 'm' || e.key === 'M') setColor('red');
    if (e.key === 'n' || e.key === 'N') setColor('blue');
  });

  // Arrastrar un archivo a la ventana lo abre.
  let dragDepth = 0;
  window.addEventListener('dragenter', (e) => { e.preventDefault(); dragDepth++; $('dropHint').textContent = tr('msg.file_dialog_open'); $('dropHint').hidden = false; });
  window.addEventListener('dragleave', () => { dragDepth = Math.max(dragDepth - 1, 0); if (!dragDepth) $('dropHint').hidden = true; });
  window.addEventListener('dragover', (e) => e.preventDefault());
  window.addEventListener('drop', (e) => {
    e.preventDefault(); dragDepth = 0; $('dropHint').hidden = true;
    const f = e.dataTransfer && e.dataTransfer.files[0];
    if (f) openFile(f);
  });

  // Los imanes colocados no se guardan solos: avisar antes de cerrar.
  window.addEventListener('beforeunload', (e) => {
    if (canvas && canvas.points.length) { e.preventDefault(); e.returnValue = ''; }
  });
}

function deleteSelectedPoint() {
  const i = $('pointsList').selectedIndex;
  if (i < 0) return;
  canvas.points.splice(i, 1);
  onPointsChanged(canvas.points, false);
}

async function goPause(delta) {
  if (!S.ui || !S.ui.has_file) return;
  await flushSettings();
  busy(true);
  const r = await api.call('go_to_pause', S.ui.pause_n - 1 + delta);
  busy(false);
  if (r.error) { errorBox(r); return; }
  apply(r);
  if (S.mode === '3d') refresh3d();
}

// --- arranque ---------------------------------------------------------------
async function boot() {
  const saved = store.get('lang');
  const nav = (navigator.language || 'en').slice(0, 2).toLowerCase();
  const lang = saved || (KNOWN_LANGS.includes(nav) ? nav : 'en');
  const es = lang === 'es';
  const steps = {
    runtime: es ? 'Descargando el motor de Python (solo la primera vez tarda un poco)…' : 'Downloading the Python engine (only slow the first time)…',
    code: es ? 'Cargando MagnetPlace Studio…' : 'Loading MagnetPlace Studio…',
    start: es ? 'Arrancando…' : 'Starting…',
  };
  $('bootMsg').textContent = steps.runtime;

  canvas = new BedCanvas2D($('bed'), { onPointsChanged, tr: (k, p) => tr(k, p) });
  S.theme = store.get('theme', 'dark') === 'light' ? 'light' : 'dark';
  document.documentElement.dataset.theme = S.theme;

  try {
    api = new Api((step) => { $('bootMsg').textContent = steps[step] || steps.start; });
    await api.ready;
    const r = await api.call('init', store.get('settings'), lang, store.get('autoReorder', '1') === '1');
    if (r.error) throw new Error(r.detail || r.error);
    TR = r.tr; LANG = r.language; LANGUAGES = r.languages; OPTIONS = r.options; DEFAULTS = r.defaults; VERSION = r.version;
    applyStaticTexts();
    applyTheme(S.theme);
    bindUi();
    apply(r, { fillForm: true });
    setStatus(tr('status.ready'));
    $('boot').hidden = true;
    if (store.get('calibSeen') !== '1') showCalibration(true);
  } catch (err) {
    console.error(err);
    $('bootMsg').innerHTML = (es
      ? 'No se ha podido arrancar. Comprueba la conexión a internet (la primera carga descarga el motor de Python) y recarga la página.'
      : 'Could not start. Check your internet connection (the first load downloads the Python engine) and reload the page.')
      + `<br><span class="muted small">${esc(err.message || err)}</span>`;
    document.querySelector('#boot .spinner').hidden = true;
  }
}

boot();
