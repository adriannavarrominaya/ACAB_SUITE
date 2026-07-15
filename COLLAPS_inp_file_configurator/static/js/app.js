/**
 * app.js — COLLAPS Configurator frontend logic
 *
 * State:
 *   appState.data     — parsed dict from COLLAPSParser (mirrors Python structure)
 *   appState.filename — current filename (for Save As default)
 *   appState.dirty    — unsaved changes flag
 */

'use strict';

// ── i18n engine ──────────────────────────────────────────────────────────────
let _i18n = {};
let _lang  = localStorage.getItem('collaps-lang') || 'es';

function t(key) {
  const val = key.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : null), _i18n);
  return (val !== null && val !== undefined) ? val : key;
}

async function loadLang(lang) {
  try {
    const res = await fetch(`/static/i18n/${lang}.json`);
    _i18n = await res.json();
  } catch (_) { _i18n = {}; }
  _lang = lang;
  localStorage.setItem('collaps-lang', lang);
  document.documentElement.lang = lang;
  applyLang();
  const flagEl = document.getElementById('lang-flag');
  const nameEl = document.getElementById('lang-name');
  if (flagEl) {
    flagEl.className = `lang-flag lang-flag-${lang}`;
    flagEl.textContent = '';
  }
  if (nameEl) nameEl.textContent = lang === 'es' ? 'Español' : 'English';
}

function applyLang() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const val = t(el.dataset.i18n);
    if (!val || val === el.dataset.i18n) return;
    [...el.childNodes]
      .filter(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim())
      .forEach(n => { n.textContent = n.textContent.replace(n.textContent.trim(), val); });
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    const val = t(el.dataset.i18nPh);
    if (val && val !== el.dataset.i18nPh) el.placeholder = val;
  });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const val = t(el.dataset.i18nTitle);
    if (val && val !== el.dataset.i18nTitle) el.title = val;
  });
  // refresh dynamic UI labels that depend on translations
  updateFtCountBadge();
}
// ────────────────────────────────────────────────────────────────────────────

const appState = { data: null, filename: 'COLL.inp', dirty: false };

// Última carpeta usada en "Guardar en carpeta…" (U2 del BACKLOG), recordada
// por app vía localStorage; se ofrece como valor inicial en el siguiente
// guardado y como prefijo del workdir de ejecución (U3) si no hay uno más
// reciente.
const LAST_SAVE_FOLDER_KEY = 'collaps-last-save-folder';

// ── Conditional-panel helpers ────────────────────────────────────────────────

function updateCard4Visibility() {
  const isfis = parseInt(document.getElementById('c3-ISFIS').value, 10);
  const msg    = document.getElementById('card4-disabled-msg');
  const fields = document.getElementById('card4-fields');
  if (isfis !== 0) {
    msg.style.display   = 'none';
    fields.style.cssText = '';       // remove !important display:none
    fields.style.display = 'flex';
    fields.classList.add('row');
  } else {
    msg.style.display   = '';
    fields.style.cssText = 'display:none!important';
  }
}

function updateCard6Visibility() {
  const iesf   = parseInt(document.getElementById('c1-IESF').value, 10);
  const msg    = document.getElementById('card6-disabled-msg');
  const fields = document.getElementById('card6-fields');
  if (iesf === 5) {
    msg.style.display   = 'none';
    fields.style.cssText = '';
    fields.style.display = 'block';
  } else {
    msg.style.display   = '';
    fields.style.cssText = 'display:none!important';
  }
}

function updateFtCountBadge() {
  const ta    = document.getElementById('c7-FT');
  const badge = document.getElementById('ft-count-badge');
  if (!ta || !badge) return;
  const vals = ta.value.trim().split(/\s+/).filter(v => v !== '');
  const n    = vals.length;
  const word = t('c7.count') || 'valores';
  badge.textContent = `${n} ${word}`;
}

// ── Populate UI from data dict ───────────────────────────────────────────────

function sel(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  el.value = (val !== null && val !== undefined) ? String(val) : '';
}

function inp(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  el.value = (val !== null && val !== undefined) ? val : '';
}

function populateUI(data) {
  if (!data) return;

  const c1 = data.card1 || {};
  const c2 = data.card2 || {};
  const c3 = data.card3 || {};
  const c4 = data.card4 || {};
  const c5 = data.card5 || {};
  const c6 = data.card6 || {};
  const c7 = data.card7 || {};
  const c8 = data.card8 || {};
  const c9 = data.card9 || {};

  sel('c1-ILIB',  c1.ILIB ?? 2);
  sel('c1-IESF',  c1.IESF ?? 2);
  inp('c2-IHEAD', c2.IHEAD ?? 16);

  sel('c3-ISFIS', c3.ISFIS ?? 0);
  sel('c3-IGEN',  c3.IGEN  ?? 0);
  sel('c3-ISOCA', c3.ISOCA ?? 1);
  sel('c3-IBEST', c3.IBEST ?? 1);

  inp('c4-EB1', c4.EB1 ?? '');
  inp('c4-EB2', c4.EB2 ?? '');

  inp('c5-NGROUP', c5.NGROUP ?? -175);
  sel('c5-FF',     c5.FF     ?? 0);

  // Card #6: CX array → textarea (space-separated)
  if (c6 && c6.CX && c6.CX.length) {
    document.getElementById('c6-CX').value = c6.CX
      .map(v => v.toExponential ? v.toExponential(5).toUpperCase() : String(v))
      .join(' ');
  } else {
    document.getElementById('c6-CX').value = '';
  }

  // Card #7: FT array → textarea
  if (c7 && c7.FT && c7.FT.length) {
    document.getElementById('c7-FT').value = c7.FT
      .map(v => v.toExponential ? v.toExponential(5).toUpperCase() : String(v))
      .join(' ');
  } else {
    document.getElementById('c7-FT').value = '';
  }

  sel('c8-IUNC3G', c8.IUNC3G ?? 0);
  sel('c9-ISTOP',  c9.ISTOP  ?? 0);

  updateCard4Visibility();
  updateCard6Visibility();
  updateFtCountBadge();
}

// ── Collect UI → data dict ───────────────────────────────────────────────────

function parseFloatArray(text) {
  return text.trim().split(/\s+/).filter(v => v !== '').map(Number);
}

function gv(id)  { return document.getElementById(id)?.value ?? ''; }
function gvi(id) { return parseInt(gv(id), 10) || 0; }
function gvf(id) { return parseFloat(gv(id)) || 0.0; }

function collectUI() {
  const isfis  = gvi('c3-ISFIS');
  const iesf   = gvi('c1-IESF');

  return {
    card1: { ILIB: gvi('c1-ILIB'), IESF: iesf },
    card2: { IHEAD: gvi('c2-IHEAD') },
    card3: {
      ISFIS: isfis,
      IGEN:  gvi('c3-IGEN'),
      ISOCA: gvi('c3-ISOCA'),
      IBEST: gvi('c3-IBEST'),
    },
    card4: isfis !== 0
      ? { EB1: gvf('c4-EB1'), EB2: gvf('c4-EB2') }
      : null,
    card5: { NGROUP: gvi('c5-NGROUP'), FF: gvi('c5-FF') },
    card6: iesf === 5
      ? { CX: parseFloatArray(gv('c6-CX')) }
      : null,
    card7: { FT: parseFloatArray(gv('c7-FT')) },
    card8: { IUNC3G: gvi('c8-IUNC3G') },
    card9: { ISTOP: gvi('c9-ISTOP') },
  };
}

// ── Status bar ───────────────────────────────────────────────────────────────

function setStatus(filename, dirty) {
  const el = document.getElementById('file-status');
  if (!el) return;
  if (!filename) {
    el.innerHTML = `<i class="bi bi-circle text-secondary me-1"></i>${t('status.no_file')}`;
  } else {
    const dot = dirty
      ? `<i class="bi bi-circle-fill text-warning me-1"></i>`
      : `<i class="bi bi-check-circle-fill text-success me-1"></i>`;
    const mod = dirty ? ` — ${t('status.modified')}` : '';
    el.innerHTML = `${dot}${filename}${mod}`;
  }
}

function markDirty() {
  appState.dirty = true;
  setStatus(appState.filename, true);
}

// ── Toast ────────────────────────────────────────────────────────────────────

function showToast(msg, type = 'success') {
  const container = document.getElementById('toast-container');
  const id = `toast-${Date.now()}`;
  const icon = type === 'danger'  ? 'bi-exclamation-triangle-fill text-danger'
             : type === 'warning' ? 'bi-exclamation-circle-fill text-warning'
             : 'bi-check-circle-fill text-success';
  container.insertAdjacentHTML('beforeend', `
    <div id="${id}" class="toast align-items-center border-0 bg-dark text-white" role="alert">
      <div class="d-flex">
        <div class="toast-body">
          <i class="bi ${icon} me-2"></i>${msg}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto"
                data-bs-dismiss="toast"></button>
      </div>
    </div>`);
  const el = document.getElementById(id);
  const bs = new bootstrap.Toast(el, { delay: 3500 });
  bs.show();
  el.addEventListener('hidden.bs.toast', () => el.remove());
}

// ── Validation ───────────────────────────────────────────────────────────────

const _EXPECTED_GROUPS = { 1: 100, 2: 175, 3: 175, 4: 566, 12: 211 };
const _LIB_NAMES = {
  1: 'GAM-II(100g)', 2: 'Vitamin-J(175g)', 3: 'TART-175(175g)',
  4: 'TART-566(566g)', 5: 'Otra/Other', 12: 'Vitamin-J+(211g)',
};

function validateAll() {
  const data = collectUI();
  const errors   = [];
  const warnings = [];

  const c1 = data.card1 || {};
  const c2 = data.card2 || {};
  const c3 = data.card3 || {};
  const c4 = data.card4 || {};
  const c5 = data.card5 || {};
  const c6 = data.card6 || {};
  const c7 = data.card7 || {};

  const ilib   = c1.ILIB  ?? 2;
  const iesf   = c1.IESF  ?? 2;
  const ihead  = c2.IHEAD ?? 16;
  const isfis  = c3.ISFIS ?? 0;
  const igen   = c3.IGEN  ?? 0;
  const isoca  = c3.ISOCA ?? 1;
  const ngroup = c5.NGROUP ?? -175;
  const nabs   = Math.abs(ngroup);
  const ft     = c7.FT || [];
  const cx     = (c6 && c6.CX) ? c6.CX : [];

  // V01 — NGROUP = 0
  if (ngroup === 0) {
    errors.push({ msg: t('val.v01') });
  }

  // V02 — IHEAD < 1
  if (!Number.isInteger(ihead) || ihead < 1) {
    errors.push({ msg: t('val.v02').replace('{ihead}', ihead) });
  }

  // V03 — FT length != nabs
  if (nabs > 0 && ft.length !== nabs) {
    errors.push({ msg: t('val.v03')
      .replace(/{exp}/g, nabs).replace('{got}', ft.length) });
  }

  // V04 — IESF=5 and CX length != nabs+1
  if (iesf === 5 && nabs > 0 && cx.length !== nabs + 1) {
    errors.push({ msg: t('val.v04')
      .replace('{exp}', nabs + 1).replace('{got}', cx.length) });
  }

  // V05 — IESF != 5 and nabs doesn't match expected group count for that structure
  if (iesf !== 5 && nabs > 0 && _EXPECTED_GROUPS[iesf] !== undefined) {
    const exp = _EXPECTED_GROUPS[iesf];
    if (nabs !== exp) {
      errors.push({ msg: t('val.v05')
        .replace('{iesf}', iesf)
        .replace('{name}', _LIB_NAMES[iesf] || '')
        .replace('{exp}',  exp)
        .replace('{got}',  nabs) });
    }
  }

  // V06 / V07 — Card #4 boundaries (only when ISFIS != 0)
  if (isfis !== 0) {
    const eb1 = (c4 && c4.EB1 != null) ? Number(c4.EB1) : NaN;
    const eb2 = (c4 && c4.EB2 != null) ? Number(c4.EB2) : NaN;
    if (isNaN(eb1) || eb1 <= 0 || isNaN(eb2) || eb2 <= 0) {
      errors.push({ msg: t('val.v06')
        .replace('{eb1}', isNaN(eb1) ? '—' : eb1.toExponential(3).toUpperCase())
        .replace('{eb2}', isNaN(eb2) ? '—' : eb2.toExponential(3).toUpperCase()) });
    } else if (eb1 <= eb2) {
      errors.push({ msg: t('val.v07')
        .replace('{eb1}', eb1.toExponential(3).toUpperCase())
        .replace('{eb2}', eb2.toExponential(3).toUpperCase()) });
    }
  }

  // V08 — All FT values are zero
  if (ft.length > 0 && ft.every(v => v === 0)) {
    warnings.push({ msg: t('val.v08') });
  }

  // V09 — Negative FT values
  if (ft.some(v => v < 0)) {
    warnings.push({ msg: t('val.v09') });
  }

  // V10 — ISFIS=1 and IGEN=1: code stops after EFY generation, no XS collapse
  if (isfis === 1 && igen === 1) {
    warnings.push({ msg: t('val.v10') });
  }

  // V11 — ISFIS=1 and ISOCA=0: external EFY library (EFYBL.dat) must exist
  if (isfis === 1 && isoca === 0) {
    warnings.push({ msg: t('val.v11') });
  }

  // V12 — ILIB != IESF (internal spectrum conversion will occur)
  if (iesf !== 5 && ilib !== iesf) {
    warnings.push({ msg: t('val.v12')
      .replace('{ilib}', ilib).replace('{lib}', _LIB_NAMES[ilib]  || String(ilib))
      .replace('{iesf}', iesf).replace('{esf}', _LIB_NAMES[iesf]  || String(iesf)) });
  }

  return { errors, warnings };
}

let _validationProceedCb = null;

function showValidationModal(result, onProceed = null) {
  const { errors, warnings } = result;
  const body    = document.getElementById('validation-modal-body');
  const procBtn = document.getElementById('validation-proceed-btn');

  if (errors.length === 0 && warnings.length === 0) {
    body.innerHTML = `
      <div class="alert alert-success mb-0">
        <i class="bi bi-check-circle-fill me-2"></i>
        <strong>${t('val.ok_title')}</strong> ${t('val.ok_msg')}
      </div>`;
  } else {
    let html = '';
    if (errors.length > 0) {
      const items = errors.map(e => `<li>${e.msg}</li>`).join('');
      html += `<div class="alert alert-danger">
        <h6 class="mb-2"><i class="bi bi-x-circle-fill me-2"></i>
        <strong>${t('val.errors_title')}</strong> (${errors.length})</h6>
        <ul class="mb-0 ps-3">${items}</ul>
      </div>`;
    }
    if (warnings.length > 0) {
      const items = warnings.map(w => `<li>${w.msg}</li>`).join('');
      html += `<div class="alert alert-warning mb-0">
        <h6 class="mb-2"><i class="bi bi-exclamation-triangle-fill me-2"></i>
        <strong>${t('val.warnings_title')}</strong> (${warnings.length})</h6>
        <ul class="mb-0 ps-3">${items}</ul>
      </div>`;
    }
    body.innerHTML = html;
  }

  _validationProceedCb = onProceed;
  if (procBtn) {
    const showProceed = errors.length === 0 && warnings.length > 0 && typeof onProceed === 'function';
    procBtn.classList.toggle('d-none', !showProceed);
  }

  bootstrap.Modal.getOrCreateInstance(document.getElementById('validationModal')).show();
}

// ── API calls ────────────────────────────────────────────────────────────────
// ── Autosave de sesión (localStorage) ───────────────────────────────────
// Persiste el fichero en edición para no perderlo al navegar por el banner de
// la suite, recargar la página o cerrar la pestaña. Se restaura al reabrir la
// app. Guardado periódico + al salir de la página (pagehide/beforeunload).
const SESSION_KEY     = 'collaps-session';
const SESSION_VERSION = 1;
const AUTOSAVE_MS     = 5000;

function saveSession() {
  try {
    appState.data = collectUI();
    localStorage.setItem(SESSION_KEY, JSON.stringify({
      v:        SESSION_VERSION,
      ts:       Date.now(),
      filename: appState.filename,
      dirty:    appState.dirty,
      data:     appState.data,
    }));
  } catch (_) { /* localStorage no disponible o lleno: ignorar */ }
}

function restoreSession() {
  let payload;
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return false;
    payload = JSON.parse(raw);
  } catch (_) { return false; }
  if (!payload || payload.v !== SESSION_VERSION || !payload.data) return false;
  try {
    appState.data     = payload.data;
    appState.filename = payload.filename || 'COLL.inp';
    appState.dirty    = !!payload.dirty;
    populateUI(appState.data);
    setStatus(appState.filename, appState.dirty);
    return true;
  } catch (err) {
    console.error('No se pudo restaurar la sesión anterior:', err);
    return false;
  }
}

function startAutosave() {
  setInterval(saveSession, AUTOSAVE_MS);
  // Guardado al cambiar de app (banner de la suite), recargar o cerrar.
  window.addEventListener('pagehide', saveSession);
  window.addEventListener('beforeunload', saveSession);
}
async function apiNew() {
  try {
    const res  = await fetch('/api/new');
    const json = await res.json();
    if (!json.ok) { showToast(json.error || 'Error', 'danger'); return; }
    appState.data     = json.data;
    appState.filename = 'COLL.inp';
    appState.dirty    = false;
    populateUI(appState.data);
    setStatus(appState.filename, false);
    showToast(t('toast.new_ok'));
  } catch (e) { showToast(String(e), 'danger'); }
}

async function apiLoad(file) {
  const fd = new FormData();
  fd.append('file', file);
  try {
    setStatus(file.name, false);
    document.getElementById('file-status').innerHTML =
      `<i class="bi bi-hourglass-split text-warning me-1"></i>${t('status.loading')}`;
    const res  = await fetch('/api/load', { method: 'POST', body: fd });
    const json = await res.json();
    if (json.error) { showToast(json.error, 'danger'); setStatus(null); return; }
    appState.data     = json.data;
    appState.filename = json.filename || file.name;
    appState.dirty    = false;
    populateUI(appState.data);
    setStatus(appState.filename, false);
    const msg = t('toast.file_loaded').replace('{name}', appState.filename);
    showToast(msg);
  } catch (e) { showToast(String(e), 'danger'); setStatus(null); }
}

async function apiSave(filename) {
  const data = collectUI();
  try {
    const res = await fetch('/api/save', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ data, filename }),
    });
    if (!res.ok) {
      const json = await res.json().catch(() => ({}));
      showToast(json.error || `HTTP ${res.status}`, 'danger');
      return;
    }
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    appState.filename = filename;
    appState.dirty    = false;
    setStatus(filename, false);
    showToast(t('toast.file_saved').replace('{name}', filename));
  } catch (e) { showToast(String(e), 'danger'); }
}

// ── Selector de carpeta nativo (U2 del BACKLOG) ─────────────────────────────
// Reutiliza el patrón del analyzer/inp-conf: botón con icono junto a un input
// de texto, con fallback manual (el usuario puede teclear la ruta si el
// diálogo nativo no está disponible).
async function browseIntoInput(inputId, btn, title) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const icon = btn.querySelector('i');
  const prevIcon = icon ? icon.className : null;
  btn.disabled = true;
  if (icon) icon.className = 'bi bi-hourglass-split';
  try {
    const res  = await fetch('/api/browse-folder', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body:   JSON.stringify({ title }),
    });
    const json = await res.json();
    if (json.folder) {
      input.value = json.folder;
    } else if (!json.error) {
      showToast(t('toast.no_folder_selected'), 'secondary');
    } else {
      showToast(json.error, 'warning');
    }
  } catch (_) {
    showToast(t('toast.browse_err'), 'warning');
  } finally {
    btn.disabled = false;
    if (icon && prevIcon) icon.className = prevIcon;
  }
}

// "Guardar en carpeta…" — escribe COLL.inp directamente en la carpeta
// elegida (POST /api/save-to-folder); pide confirmación y reintenta con
// overwrite si el fichero ya existe (mismo patrón que figuras.yaml en el
// analyzer).
async function apiSaveToFolder(folder) {
  const data = collectUI();

  async function attempt(overwrite) {
    const res  = await fetch('/api/save-to-folder', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ data, folder, overwrite }),
    });
    const json = await res.json().catch(() => ({}));
    if (res.status === 409 && json.exists && !overwrite) {
      return confirm(t('modal.save_confirm_overwrite')) ? attempt(true) : false;
    }
    if (!res.ok || !json.ok) {
      showToast(json.error || `HTTP ${res.status}`, 'danger');
      return false;
    }
    return true;
  }

  try {
    if (!(await attempt(false))) return;
    localStorage.setItem(LAST_SAVE_FOLDER_KEY, folder);
    appState.filename = 'COLL.inp';
    appState.dirty    = false;
    setStatus(appState.filename, false);
    showToast(t('toast.folder_saved').replace('{name}', appState.filename).replace('{folder}', folder));
    bootstrap.Modal.getInstance(document.getElementById('saveFolderModal'))?.hide();
  } catch (e) { showToast(String(e), 'danger'); }
}

async function apiPreview() {
  const data = collectUI();
  const el   = document.getElementById('preview-content');
  const linesEl = document.getElementById('preview-lines');
  el.textContent = t('modal.preview_gen');
  try {
    const res  = await fetch('/api/preview', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ data }),
    });
    const json = await res.json();
    if (!json.ok) { el.textContent = json.error || 'Error'; return; }
    el.textContent = json.content;
    const n = json.content.split('\n').length;
    linesEl.textContent = t('toast.lines').replace('{n}', n);
  } catch (e) { el.textContent = String(e); }
}

// ── Ejecución de COLLAPS (Fase R2) ───────────────────────────────────────────

const runState = {
  polling: null,
  autoscroll: true,
  cancelRequested: false,
};

async function loadRunConfig() {
  try {
    const res  = await fetch('/api/run/config');
    const json = await res.json();
    if (!json.ok) return;
    const cfg = json.config;
    // U3 del BACKLOG: la carpeta del último "Guardar en carpeta…" tiene
    // prioridad sobre el workdir de la última ejecución; sin guardado previo,
    // el comportamiento es el de siempre (default_workdir del runner, o
    // vacío — el campo sigue editable y con el diálogo de carpeta a mano).
    const lastSaveFolder = localStorage.getItem(LAST_SAVE_FOLDER_KEY) || '';
    document.getElementById('run-workdir').value = lastSaveFolder || cfg.default_workdir || '';
    document.getElementById('run-exe').value     = cfg.exe_name || 'collaps.exe';
    document.getElementById('run-timeout').value = cfg.timeout_s || 60;
  } catch (_) { /* backend no disponible: dejar los valores actuales */ }
}

function setRunBadge(text, variant) {
  const el = document.getElementById('run-status-badge');
  el.className = `badge bg-${variant} ms-auto`;
  el.textContent = text;
}

function appendRunLog(text) {
  const pre = document.getElementById('run-log');
  pre.textContent = text || '';
  if (runState.autoscroll) pre.scrollTop = pre.scrollHeight;
}

function stopRunPolling() {
  if (runState.polling) { clearInterval(runState.polling); runState.polling = null; }
}

function startRunPolling() {
  stopRunPolling();
  runState.polling = setInterval(pollRunStatus, 1000);
  pollRunStatus();
}

async function pollRunStatus() {
  let json;
  try {
    const res = await fetch('/api/run/status');
    json = await res.json();
  } catch (_) { return; }

  const s = json.status || {};
  appendRunLog(s.log_tail);

  if (s.running) {
    document.getElementById('run-elapsed').textContent =
      t('run.elapsed').replace('{s}', (s.elapsed_s ?? 0).toFixed(1));
    setRunBadge(t('run.badge_running'), 'info');
    return;
  }

  // Ya no está corriendo: fin del polling y actualización de botones/badge.
  stopRunPolling();
  document.getElementById('btn-run-start').disabled  = false;
  document.getElementById('btn-run-cancel').disabled = true;

  if (s.mode !== 'single' || s.returncode === undefined) return;

  document.getElementById('run-elapsed').textContent =
    t('run.elapsed').replace('{s}', (s.elapsed_s ?? 0).toFixed(1));

  if (s.timed_out) {
    setRunBadge(t('run.badge_timeout'), 'warning');
    showToast(t('toast.run_timeout'), 'warning');
  } else if (runState.cancelRequested) {
    setRunBadge(t('run.badge_cancelled'), 'secondary');
    showToast(t('toast.run_cancelled'), 'warning');
  } else if (s.returncode === 0) {
    setRunBadge(t('run.badge_ok'), 'success');
    showToast(t('toast.run_ok'));
  } else {
    setRunBadge(t('run.badge_error').replace('{code}', s.returncode), 'danger');
    showToast(t('toast.run_error').replace('{code}', s.returncode), 'danger');
  }
  runState.cancelRequested = false;
}

async function startRun(overwrite = false) {
  const workdir  = document.getElementById('run-workdir').value.trim();
  const exeName  = document.getElementById('run-exe').value.trim() || 'collaps.exe';
  const timeoutS = parseFloat(document.getElementById('run-timeout').value) || 60;
  const saveCur  = document.getElementById('run-save-current').checked;

  if (!workdir) { showToast(t('toast.run_no_workdir'), 'danger'); return; }

  const body = { workdir, exe_name: exeName, timeout_s: timeoutS,
                 save_current: saveCur, overwrite };
  if (saveCur) body.data = collectUI();

  document.getElementById('run-log').textContent = '';
  setRunBadge(t('run.badge_running'), 'info');

  try {
    const res  = await fetch('/api/run', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    });
    const json = await res.json();

    if (res.status === 422) {
      if (json.needs_overwrite && confirm(json.error)) { await startRun(true); return; }
      showToast(json.error, 'danger');
      setRunBadge('', 'secondary');
      return;
    }
    if (res.status === 409) {
      showToast(json.error, 'danger');
      setRunBadge('', 'secondary');
      return;
    }
    if (!json.ok) {
      showToast(json.error || 'Error', 'danger');
      setRunBadge('', 'secondary');
      return;
    }

    runState.cancelRequested = false;
    document.getElementById('btn-run-start').disabled  = true;
    document.getElementById('btn-run-cancel').disabled = false;
    startRunPolling();
  } catch (e) {
    showToast(String(e), 'danger');
    setRunBadge('', 'secondary');
  }
}

async function resyncRunState() {
  try {
    const res  = await fetch('/api/run/status');
    const json = await res.json();
    const s = json.status || {};
    if (s.mode === 'single' && s.running) {
      document.getElementById('btn-run-start').disabled  = true;
      document.getElementById('btn-run-cancel').disabled = false;
      setRunBadge(t('run.badge_running'), 'info');
      startRunPolling();
    }
  } catch (_) { /* servidor no disponible todavía: ignorar */ }
}

// ── Event wiring ─────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {

  // Load language first
  await loadLang(_lang);

  // Language switcher
  document.querySelectorAll('.lang-item').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      loadLang(a.dataset.lang);
    });
  });

  // Section dropdown links → activate tab
  document.querySelectorAll('.section-link').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const sec = a.dataset.section;
      const tab = document.querySelector(`[data-bs-target="#${sec}"]`);
      if (tab) bootstrap.Tab.getOrCreateInstance(tab).show();
    });
  });

  // New
  document.getElementById('btn-new').addEventListener('click', e => {
    e.preventDefault();
    apiNew();
  });

  // Load
  document.getElementById('btn-load').addEventListener('click', e => {
    e.preventDefault();
    document.getElementById('file-input').click();
  });
  document.getElementById('file-input').addEventListener('change', e => {
    if (e.target.files.length) {
      apiLoad(e.target.files[0]);
      e.target.value = '';
    }
  });

  // Validate
  document.getElementById('btn-validate').addEventListener('click', e => {
    e.preventDefault();
    showValidationModal(validateAll(), null);
  });

  // Validation proceed-anyway button
  document.getElementById('validation-proceed-btn').addEventListener('click', () => {
    bootstrap.Modal.getInstance(document.getElementById('validationModal')).hide();
    if (typeof _validationProceedCb === 'function') {
      _validationProceedCb();
      _validationProceedCb = null;
    }
  });

  // Save As dialog
  document.getElementById('btn-saveas').addEventListener('click', e => {
    e.preventDefault();
    document.getElementById('saveas-filename').value = appState.filename || 'COLL.inp';
    bootstrap.Modal.getOrCreateInstance(document.getElementById('saveasModal')).show();
  });
  document.getElementById('btn-saveas-confirm').addEventListener('click', () => {
    const fname = document.getElementById('saveas-filename').value.trim() || 'COLL.inp';
    bootstrap.Modal.getInstance(document.getElementById('saveasModal')).hide();
    const result = validateAll();
    if (result.errors.length > 0 || result.warnings.length > 0) {
      showValidationModal(result, () => apiSave(fname));
    } else {
      apiSave(fname);
    }
  });
  document.getElementById('saveas-filename').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('btn-saveas-confirm').click();
  });

  // Guardar en carpeta… (U2 del BACKLOG) — prefija con la última carpeta usada
  document.getElementById('btn-save-folder-open').addEventListener('click', e => {
    e.preventDefault();
    const lastFolder = localStorage.getItem(LAST_SAVE_FOLDER_KEY) || '';
    document.getElementById('save-folder-input').value = lastFolder;
    bootstrap.Modal.getOrCreateInstance(document.getElementById('saveFolderModal')).show();
  });
  document.getElementById('btn-save-folder-browse').addEventListener('click', e => {
    browseIntoInput('save-folder-input', e.currentTarget, t('modal.save_folder_title'));
  });
  document.getElementById('btn-save-folder-confirm').addEventListener('click', () => {
    const folder = document.getElementById('save-folder-input').value.trim();
    if (!folder) { showToast(t('toast.no_folder_selected'), 'warning'); return; }
    const result = validateAll();
    if (result.errors.length > 0 || result.warnings.length > 0) {
      showValidationModal(result, () => apiSaveToFolder(folder));
    } else {
      apiSaveToFolder(folder);
    }
  });

  // Diálogo de carpeta para el workdir de ejecución (U3 del BACKLOG)
  document.getElementById('btn-run-workdir-browse').addEventListener('click', e => {
    browseIntoInput('run-workdir', e.currentTarget, t('run.workdir_lbl'));
  });

  // Preview
  document.getElementById('btn-preview').addEventListener('click', async e => {
    e.preventDefault();
    const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('previewModal'));
    modal.show();
    await apiPreview();
  });

  // Copy preview
  document.getElementById('btn-copy-preview').addEventListener('click', async () => {
    const text = document.getElementById('preview-content').textContent;
    try {
      await navigator.clipboard.writeText(text);
      showToast(t('toast.copied'));
    } catch (_) { showToast(t('toast.copy_err'), 'warning'); }
  });

  // Conditional panel triggers
  document.getElementById('c3-ISFIS').addEventListener('change', updateCard4Visibility);
  document.getElementById('c1-IESF').addEventListener('change', updateCard6Visibility);

  // FT count badge update
  document.getElementById('c7-FT').addEventListener('input', updateFtCountBadge);

  // Mark dirty on any form change
  document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('change', markDirty);
    if (el.tagName === 'TEXTAREA') el.addEventListener('input', markDirty);
  });

  // Ejecución de COLLAPS
  document.getElementById('btn-run-open').addEventListener('click', async () => {
    if (!document.getElementById('btn-run-start').disabled) {
      await loadRunConfig();
    }
    bootstrap.Modal.getOrCreateInstance(document.getElementById('runModal')).show();
  });

  document.getElementById('btn-run-start').addEventListener('click', () => {
    const result = validateAll();
    if (result.errors.length > 0 || result.warnings.length > 0) {
      showValidationModal(result, () => startRun(false));
    } else {
      startRun(false);
    }
  });

  document.getElementById('btn-run-cancel').addEventListener('click', async () => {
    runState.cancelRequested = true;
    try { await fetch('/api/run/cancel', { method: 'POST' }); } catch (_) { /* ignorar */ }
  });

  document.getElementById('run-log').addEventListener('scroll', e => {
    const el = e.target;
    runState.autoscroll = (el.scrollTop + el.clientHeight >= el.scrollHeight - 10);
  });

  resyncRunState();

  // Restaurar la sesión anterior si existe; si no, empezar en blanco.
  if (restoreSession()) {
    showToast(t('toast.session_restored'), 'info');
  } else {
    await apiNew();
  }

  // Autosave periódico + al cambiar de app / recargar / cerrar.
  startAutosave();
});
