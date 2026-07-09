/**
 * chains.js — CHAINS input file configurator frontend logic
 */
'use strict';

// ── Element symbols Z=1..103 ──────────────────────────────────────────────
const SYMBOLS = [
  '',
  'H',  'He', 'Li', 'Be', 'B',  'C',  'N',  'O',  'F',  'Ne',
  'Na', 'Mg', 'Al', 'Si', 'P',  'S',  'Cl', 'Ar', 'K',  'Ca',
  'Sc', 'Ti', 'V',  'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
  'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y',  'Zr',
  'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
  'Sb', 'Te', 'I',  'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',
  'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',
  'Lu', 'Hf', 'Ta', 'W',  'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
  'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',
  'Pa', 'U',  'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm',
  'Md', 'No', 'Lr',
];

function symbolOf(z) {
  return (z > 0 && z < SYMBOLS.length) ? SYMBOLS[z] : `Z${z}`;
}

function nuclideId(z, a, meta) {
  return z * 10000 + a * 10 + (meta ? 1 : 0);
}

function nuclideLabel(id) {
  const z   = Math.floor(id / 10000);
  const a   = Math.floor((id % 10000) / 10);
  const iso = id % 10;
  return `${symbolOf(z)}-${a}${iso ? 'm' : ''}`;
}

function idToZAMeta(id) {
  return {
    z:    Math.floor(id / 10000),
    a:    Math.floor((id % 10000) / 10),
    meta: (id % 10) === 1,
  };
}

// ── State ─────────────────────────────────────────────────────────────────
const state = { filename: 'input.chain.txt', dirty: false };

// ── Nuclide widget helpers ────────────────────────────────────────────────

function refreshNuclideDisplay(prefix) {
  const z    = parseInt(document.getElementById(`f-${prefix}-z`).value,  10) || 0;
  const a    = parseInt(document.getElementById(`f-${prefix}-a`).value,  10) || 0;
  const meta = document.getElementById(`f-${prefix}-meta`).checked;

  document.getElementById(`f-${prefix}-sym`).textContent = symbolOf(z);

  const id = nuclideId(z, a, meta);
  document.getElementById(`f-${prefix}-id`).textContent   = id;
  document.getElementById(`f-${prefix}-name`).textContent = nuclideLabel(id);
}

function setNuclideFromId(prefix, id) {
  const { z, a, meta } = idToZAMeta(id);
  document.getElementById(`f-${prefix}-z`).value    = z;
  document.getElementById(`f-${prefix}-a`).value    = a;
  document.getElementById(`f-${prefix}-meta`).checked = meta;
  refreshNuclideDisplay(prefix);
}

// ── Mode selection ────────────────────────────────────────────────────────

function setMode(iflag) {
  document.getElementById('f-iflag').value = iflag;

  [1, 2, 3].forEach(m => {
    document.getElementById(`mode-card-${m}`)
      .classList.toggle('selected', m === iflag);
  });

  const cardInitial = document.getElementById('card-initial');
  const pcntGroup   = document.getElementById('pcnt-group');

  if (iflag === 2) {
    cardInitial.classList.remove('hidden-card');
    pcntGroup.classList.remove('hidden-card');
  } else {
    cardInitial.classList.add('hidden-card');
    pcntGroup.classList.add('hidden-card');
  }
}

// ── Collect UI → data dict ────────────────────────────────────────────────

function collectUI() {
  const iflag = parseInt(document.getElementById('f-iflag').value, 10);

  const initialZ    = parseInt(document.getElementById('f-initial-z').value,  10) || 0;
  const initialA    = parseInt(document.getElementById('f-initial-a').value,  10) || 0;
  const initialMeta = document.getElementById('f-initial-meta').checked;

  const ifinalZ    = parseInt(document.getElementById('f-ifinal-z').value,  10) || 0;
  const ifinalA    = parseInt(document.getElementById('f-ifinal-a').value,  10) || 0;
  const ifinalMeta = document.getElementById('f-ifinal-meta').checked;

  return {
    IFLAG:   iflag,
    INITIAL: nuclideId(initialZ, initialA, initialMeta),
    IFINAL:  nuclideId(ifinalZ,  ifinalA,  ifinalMeta),
    NMAX:    parseInt(document.getElementById('f-nmax').value, 10)   || 4,
    PCNT:    parseFloat(document.getElementById('f-pcnt').value)      || 0.1,
  };
}

// ── Populate UI from data dict ────────────────────────────────────────────

function populateUI(data) {
  setMode(data.IFLAG ?? 2);
  setNuclideFromId('initial', data.INITIAL ?? 130270);
  setNuclideFromId('ifinal',  data.IFINAL  ?? 110240);
  document.getElementById('f-nmax').value = data.NMAX ?? 4;
  document.getElementById('f-pcnt').value = data.PCNT ?? 0.1;
}

// ── Status bar ────────────────────────────────────────────────────────────

function setStatus(filename, dirty) {
  const el = document.getElementById('file-status');
  if (!el) return;
  if (!filename) {
    el.innerHTML = '<i class="bi bi-circle text-secondary me-1"></i>Sin fichero cargado';
  } else {
    const dot = dirty
      ? '<i class="bi bi-circle-fill text-warning me-1"></i>'
      : '<i class="bi bi-check-circle-fill text-success me-1"></i>';
    el.innerHTML = `${dot}${filename}${dirty ? ' — modificado' : ''}`;
  }
}

function markDirty() {
  state.dirty = true;
  setStatus(state.filename, true);
}

// ── Toast ─────────────────────────────────────────────────────────────────

function showToast(msg, type = 'success') {
  const container = document.getElementById('toast-container');
  const id  = `toast-${Date.now()}`;
  const icon = type === 'danger'  ? 'bi-exclamation-triangle-fill text-danger'
             : type === 'warning' ? 'bi-exclamation-circle-fill text-warning'
             : 'bi-check-circle-fill text-success';
  container.insertAdjacentHTML('beforeend', `
    <div id="${id}" class="toast align-items-center border-0 bg-dark text-white" role="alert">
      <div class="d-flex">
        <div class="toast-body"><i class="bi ${icon} me-2"></i>${msg}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto"
                data-bs-dismiss="toast"></button>
      </div>
    </div>`);
  const el = document.getElementById(id);
  const bs = new bootstrap.Toast(el, { delay: 3500 });
  bs.show();
  el.addEventListener('hidden.bs.toast', () => el.remove());
}

// ── API calls ─────────────────────────────────────────────────────────────

async function apiNew() {
  try {
    const res  = await fetch('/api/chains/new');
    const json = await res.json();
    if (!json.ok) { showToast(json.error || 'Error', 'danger'); return; }
    populateUI(json.data);
    state.filename = 'input.chain.txt';
    state.dirty    = false;
    setStatus(state.filename, false);
    showToast('Nuevo fichero CHAINS creado.');
  } catch (e) { showToast(String(e), 'danger'); }
}

async function apiLoad(file) {
  const fd = new FormData();
  fd.append('file', file);
  try {
    setStatus(file.name, false);
    document.getElementById('file-status').innerHTML =
      '<i class="bi bi-hourglass-split text-warning me-1"></i>Cargando…';
    const res  = await fetch('/api/chains/load', { method: 'POST', body: fd });
    const json = await res.json();
    if (json.error) {
      showToast(json.error, 'danger');
      setStatus(null);
      return;
    }
    populateUI(json.data);
    state.filename = json.filename || file.name;
    state.dirty    = false;
    setStatus(state.filename, false);
    showToast(`Fichero "${state.filename}" cargado correctamente.`);
  } catch (e) { showToast(String(e), 'danger'); setStatus(null); }
}

async function apiSave(filename) {
  const data = collectUI();
  try {
    const res = await fetch('/api/chains/save', {
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
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
    state.filename = filename;
    state.dirty    = false;
    setStatus(filename, false);
    showToast(`Fichero "${filename}" guardado.`);
  } catch (e) { showToast(String(e), 'danger'); }
}

async function apiPreview() {
  const data  = collectUI();
  const el    = document.getElementById('preview-content');
  const lines = document.getElementById('preview-lines');
  el.textContent = 'Generando…';
  try {
    const res  = await fetch('/api/chains/preview', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ data }),
    });
    const json = await res.json();
    if (!json.ok) { el.textContent = json.error || 'Error'; return; }
    el.textContent = json.content;
    const n = json.content.split('\n').length;
    lines.textContent = `${n} líneas`;
  } catch (e) { el.textContent = String(e); }
}

// ── Event wiring ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {

  // Mode cards
  document.querySelectorAll('.mode-card').forEach(card => {
    card.addEventListener('click', () => {
      setMode(parseInt(card.dataset.mode, 10));
      markDirty();
    });
  });

  // Nuclide inputs — refresh display on change
  ['initial', 'ifinal'].forEach(prefix => {
    ['z', 'a', 'meta'].forEach(field => {
      const el = document.getElementById(`f-${prefix}-${field}`);
      el.addEventListener('input',  () => { refreshNuclideDisplay(prefix); markDirty(); });
      el.addEventListener('change', () => { refreshNuclideDisplay(prefix); markDirty(); });
    });
  });

  // Apply direct ID
  document.getElementById('btn-apply-direct').addEventListener('click', () => {
    const rawI = parseInt(document.getElementById('f-initial-direct').value, 10);
    const rawF = parseInt(document.getElementById('f-ifinal-direct').value,  10);
    if (!isNaN(rawI) && rawI > 0) setNuclideFromId('initial', rawI);
    if (!isNaN(rawF) && rawF > 0) setNuclideFromId('ifinal',  rawF);
    markDirty();
  });

  // File menu
  document.getElementById('btn-new').addEventListener('click', e => {
    e.preventDefault(); apiNew();
  });
  document.getElementById('btn-load').addEventListener('click', e => {
    e.preventDefault();
    document.getElementById('file-input').click();
  });
  document.getElementById('file-input').addEventListener('change', e => {
    if (e.target.files.length) { apiLoad(e.target.files[0]); e.target.value = ''; }
  });

  document.getElementById('btn-saveas').addEventListener('click', e => {
    e.preventDefault();
    document.getElementById('saveas-filename').value = state.filename;
    bootstrap.Modal.getOrCreateInstance(document.getElementById('saveasModal')).show();
  });
  document.getElementById('btn-saveas-confirm').addEventListener('click', () => {
    const fname = document.getElementById('saveas-filename').value.trim() || 'input.chain.txt';
    bootstrap.Modal.getInstance(document.getElementById('saveasModal')).hide();
    apiSave(fname);
  });
  document.getElementById('saveas-filename').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('btn-saveas-confirm').click();
  });

  document.getElementById('btn-preview').addEventListener('click', async e => {
    e.preventDefault();
    bootstrap.Modal.getOrCreateInstance(document.getElementById('previewModal')).show();
    await apiPreview();
  });

  document.getElementById('btn-copy-preview').addEventListener('click', async () => {
    const text = document.getElementById('preview-content').textContent;
    try {
      await navigator.clipboard.writeText(text);
      showToast('Copiado al portapapeles.');
    } catch (_) { showToast('No se pudo copiar.', 'warning'); }
  });

  // Mark dirty on any form change
  document.querySelectorAll('input, select').forEach(el => {
    el.addEventListener('change', markDirty);
  });

  // Init: load defaults
  apiNew();
});
