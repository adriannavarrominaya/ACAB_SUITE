/**
 * app.js — ACAB Configurator frontend logic
 *
 * State:
 *   appState.data     — parsed dict from ACABParser (mirrors Python structure)
 *   appState.filename — current filename (for Save As default)
 *   appState.dirty    — unsaved changes flag
 */

'use strict';

// ── i18n engine ──────────────────────────────────────────────────────────────
let _i18n = {};
let _lang  = localStorage.getItem('acab-lang') || 'es';

/** Resolve a dot-separated key from the loaded translations. */
function t(key) {
  const val = key.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : null), _i18n);
  return (val !== null && val !== undefined) ? val : key;
}

/** Fetch and apply a language pack. */
async function loadLang(lang) {
  try {
    const res = await fetch(`/static/i18n/${lang}.json`);
    _i18n = await res.json();
  } catch (_) { _i18n = {}; }
  _lang = lang;
  localStorage.setItem('acab-lang', lang);
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

/** Walk DOM and substitute i18n attributes. */
function applyLang() {
  // Text nodes (preserves child elements like icons)
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const val = t(el.dataset.i18n);
    if (!val || val === el.dataset.i18n) return;
    [...el.childNodes]
      .filter(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim())
      .forEach(n => { n.textContent = n.textContent.replace(n.textContent.trim(), val); });
  });
  // Placeholders
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    const val = t(el.dataset.i18nPh);
    if (val && val !== el.dataset.i18nPh) el.placeholder = val;
  });
  // Title attributes
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const val = t(el.dataset.i18nTitle);
    if (val && val !== el.dataset.i18nTitle) el.title = val;
  });
  // innerHTML (for elements with embedded HTML like <code>)
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const val = t(el.dataset.i18nHtml);
    if (val && val !== el.dataset.i18nHtml) el.innerHTML = val;
  });
}
// ────────────────────────────────────────────────────────────────────────────

const appState = { data: null, filename: 'output.5', dirty: false };

// Última carpeta usada en "Guardar en carpeta…" (U2 del BACKLOG), recordada
// por app vía localStorage; se ofrece como valor inicial en el siguiente
// guardado y como prefijo del workdir de ejecución (U3) si no hay uno más
// reciente.
const LAST_SAVE_FOLDER_KEY = 'acab-inp-last-save-folder';

// ---------------------------------------------------------------------------
// ACAB code search index
// Each entry: { code, tabBtn, pillBtn|null, elementId, blockLabel, tabKey }
// ---------------------------------------------------------------------------
const ACAB_CODE_INDEX = [
  // ── Block #1 — Parámetros generales ─────────────────────────────────────
  { code:'IUNC',    tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-IUNC',    blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'ITMAX',   tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-ITMAX',   blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'IZMAX',   tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-IZMAX',   blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'MPCTAB',  tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-MPCTAB',  blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'IR',      tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-IR',      blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'JTO',     tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-JTO',     blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'NTABLE',  tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-NTABLE',  blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'MSTAR',   tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-MSTAR',   blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'INPT',    tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-INPT',    blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'INFD',    tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-INFD',    blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'NOGG',    tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-NOGG',    blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'NGRP',    tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-NGRP',    blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'IGRP',    tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-IGRP',    blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'IGE',     tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-IGE',     blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'IZM',     tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-IZM',     blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'IM',      tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-IM',      blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'JM',      tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-JM',      blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'IFLU',    tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-IFLU',    blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'IPRT',    tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-IPRT',    blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'ILIB',    tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-ILIB',    blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'IRAD',    tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-IRAD',    blockLabel:'Block #1', tabKey:'tabs.general' },
  { code:'IPUN',    tabBtn:'tab-general-btn', pillBtn:'pill-b1',  elementId:'b1-IPUN',    blockLabel:'Block #1', tabKey:'tabs.general' },
  // ── Block #4 — Reinicio ──────────────────────────────────────────────────
  { code:'IREST',   tabBtn:'tab-general-btn', pillBtn:'pill-b4',  elementId:'b4-IREST',   blockLabel:'Block #4', tabKey:'tabs.general' },
  // ── Block #9 — Error y normalización ────────────────────────────────────
  { code:'ERR',     tabBtn:'tab-general-btn', pillBtn:'pill-b9',  elementId:'b9-ERR',     blockLabel:'Block #9', tabKey:'tabs.general' },
  { code:'XNORM',   tabBtn:'tab-general-btn', pillBtn:'pill-b9',  elementId:'b9-XNORM',   blockLabel:'Block #9', tabKey:'tabs.general' },
  // ── Block #10 — Productos de fisión ─────────────────────────────────────
  { code:'IGFP',    tabBtn:'tab-general-btn', pillBtn:'pill-b10', elementId:'b10-IGFP',   blockLabel:'Block #10', tabKey:'tabs.general' },
  { code:'IWFYD',   tabBtn:'tab-general-btn', pillBtn:'pill-b10', elementId:'b10-IWFYD',  blockLabel:'Block #10', tabKey:'tabs.general' },
  { code:'IFORT96', tabBtn:'tab-general-btn', pillBtn:'pill-b10', elementId:'b10-IFORT96',blockLabel:'Block #10', tabKey:'tabs.general' },
  // ── Block #2 — Malla y salida ────────────────────────────────────────────
  { code:'XRR',     tabBtn:'tab-geometry-btn', pillBtn:'pill-b2', elementId:'b2-XRR',     blockLabel:'Block #2', tabKey:'tabs.geometry' },
  { code:'YZT',     tabBtn:'tab-geometry-btn', pillBtn:'pill-b2', elementId:'b2-YZT',     blockLabel:'Block #2', tabKey:'tabs.geometry' },
  { code:'MA',      tabBtn:'tab-geometry-btn', pillBtn:'pill-b2', elementId:'b2-MA',      blockLabel:'Block #2', tabKey:'tabs.geometry' },
  { code:'NUCZO',   tabBtn:'tab-geometry-btn', pillBtn:'pill-b2', elementId:'b2-NUCZO',   blockLabel:'Block #2', tabKey:'tabs.geometry' },
  { code:'ISOZO',   tabBtn:'tab-geometry-btn', pillBtn:'pill-b2', elementId:'b2-ISOZO',   blockLabel:'Block #2', tabKey:'tabs.geometry' },
  { code:'EGRP',    tabBtn:'tab-geometry-btn', pillBtn:'pill-b2', elementId:'b2-EGRP',    blockLabel:'Block #2', tabKey:'tabs.geometry' },
  { code:'CUTOFF',  tabBtn:'tab-geometry-btn', pillBtn:'pill-b2', elementId:'b2-cutoff-0',blockLabel:'Block #2', tabKey:'tabs.geometry' },
  { code:'NTO',     tabBtn:'tab-geometry-btn', pillBtn:'pill-b2', elementId:'b2-nto-0',   blockLabel:'Block #2', tabKey:'tabs.geometry' },
  // ── Block #3 — Flujo neutrónico ──────────────────────────────────────────
  { code:'FLUX',    tabBtn:'tab-materials-btn', pillBtn:'pill-b3', elementId:'b3-FLUX',   blockLabel:'Block #3', tabKey:'tabs.materials' },
  // ── Block #5 — Composición inicial (zonas dinámicas) ────────────────────
  { code:'INUCL',   tabBtn:'tab-materials-btn', pillBtn:'pill-b5', elementId:'b5-zones-container', blockLabel:'Block #5', tabKey:'tabs.materials' },
  { code:'XCOMP',   tabBtn:'tab-materials-btn', pillBtn:'pill-b5', elementId:'b5-zones-container', blockLabel:'Block #5', tabKey:'tabs.materials' },
  // ── Block #6 — Alimentación continua (zonas dinámicas) ──────────────────
  { code:'IDNUM',   tabBtn:'tab-materials-btn', pillBtn:'pill-b6', elementId:'b6-zones-container', blockLabel:'Block #6', tabKey:'tabs.materials' },
  { code:'XFEED',   tabBtn:'tab-materials-btn', pillBtn:'pill-b6', elementId:'b6-zones-container', blockLabel:'Block #6', tabKey:'tabs.materials' },
  // ── Blocks #7/#8 — Historial temporal ───────────────────────────────────
  { code:'MMN',     tabBtn:'tab-temporal-btn', pillBtn:'pill-b78', elementId:'b78-irr-tbody',    blockLabel:'Blocks #7/#8', tabKey:'tabs.temporal' },
  { code:'MOUT',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b78', elementId:'b78-irr-tbody',    blockLabel:'Blocks #7/#8', tabKey:'tabs.temporal' },
  { code:'NGO',     tabBtn:'tab-temporal-btn', pillBtn:'pill-b78', elementId:'b78-irr-tbody',    blockLabel:'Blocks #7/#8', tabKey:'tabs.temporal' },
  { code:'MSUB',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b78', elementId:'b78-irr-tbody',    blockLabel:'Blocks #7/#8', tabKey:'tabs.temporal' },
  { code:'IUNIT',   tabBtn:'tab-temporal-btn', pillBtn:'pill-b78', elementId:'b78-iunit',        blockLabel:'Blocks #7/#8', tabKey:'tabs.temporal' },
  { code:'MFEED',   tabBtn:'tab-temporal-btn', pillBtn:'pill-b78', elementId:'b78-irr-tbody',    blockLabel:'Blocks #7/#8', tabKey:'tabs.temporal' },
  { code:'IOUT',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b78', elementId:'b78-iout',         blockLabel:'Blocks #7/#8', tabKey:'tabs.temporal' },
  { code:'IPLOT',   tabBtn:'tab-temporal-btn', pillBtn:'pill-b78', elementId:'b78-iplot',        blockLabel:'Blocks #7/#8', tabKey:'tabs.temporal' },
  { code:'TIMES',   tabBtn:'tab-temporal-btn', pillBtn:'pill-b78', elementId:'b78-code-preview', blockLabel:'Blocks #7/#8', tabKey:'tabs.temporal' },
  // ── Block #11 — Control de ejecución ────────────────────────────────────
  { code:'IWP',     tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-IWP',     blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'IMTX',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-IMTX',    blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'IWDR',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-IWDR',    blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'IDOSE',   tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-IDOSE',   blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'IPHCUT',  tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-IPHCUT',  blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'IDHEAT',  tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-IDHEAT',  blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'IOFFSD',  tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-IOFFSD',  blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'ICEDE',   tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-ICEDE',   blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'INEMISS', tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-INEMISS', blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'IDAMAGE', tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-IDAMAGE', blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'PH',      tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-dose-PH', blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'BREM',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-dose-BREM',blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'TOT',     tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-dose-TOT',blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'RHOR',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-dose-RHOR',blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'NOPUL',   tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-NOPUL',   blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'NTSEQ',   tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-NTSEQ',   blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'NOTTS',   tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-NOTTS',   blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'NVFL',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-NVFL',    blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'FVAR',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-FVAR',    blockLabel:'Block #11', tabKey:'tabs.temporal' },
  { code:'NMULT',   tabBtn:'tab-temporal-btn', pillBtn:'pill-b11', elementId:'b11-NMULT',   blockLabel:'Block #11', tabKey:'tabs.temporal' },
  // ── Block #13 — Control de salida ────────────────────────────────────────
  { code:'NCYO',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b13', elementId:'b13-NCYO',    blockLabel:'Block #13', tabKey:'tabs.temporal' },
  { code:'IFSO',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b13', elementId:'b13-IFSO',    blockLabel:'Block #13', tabKey:'tabs.temporal' },
  { code:'ICYO',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b13', elementId:'b13-ICYO',    blockLabel:'Block #13', tabKey:'tabs.temporal' },
  { code:'ITSO',    tabBtn:'tab-temporal-btn', pillBtn:'pill-b13', elementId:'b13-ITSO',    blockLabel:'Block #13', tabKey:'tabs.temporal' },
  // ── Block #14 — Análisis de incertidumbres ───────────────────────────────
  { code:'NMOHI',   tabBtn:'tab-uncertainties-btn', pillBtn:null, elementId:'b14-NMOHI',   blockLabel:'Block #14', tabKey:'tabs.uncertainties' },
  { code:'NTIMES',  tabBtn:'tab-uncertainties-btn', pillBtn:null, elementId:'b14-NTIMES',  blockLabel:'Block #14', tabKey:'tabs.uncertainties' },
  { code:'NCYU',    tabBtn:'tab-uncertainties-btn', pillBtn:null, elementId:'b14-NCYU',    blockLabel:'Block #14', tabKey:'tabs.uncertainties' },
  { code:'IFSU',    tabBtn:'tab-uncertainties-btn', pillBtn:null, elementId:'b14-IFSU',    blockLabel:'Block #14', tabKey:'tabs.uncertainties' },
  { code:'NNUCU',   tabBtn:'tab-uncertainties-btn', pillBtn:null, elementId:'b14-NNUCU',   blockLabel:'Block #14', tabKey:'tabs.uncertainties' },
  { code:'ICYU',    tabBtn:'tab-uncertainties-btn', pillBtn:null, elementId:'b14-ICYU',    blockLabel:'Block #14', tabKey:'tabs.uncertainties' },
  { code:'ITSU',    tabBtn:'tab-uncertainties-btn', pillBtn:null, elementId:'b14-ITSU',    blockLabel:'Block #14', tabKey:'tabs.uncertainties' },
  { code:'ITIMEU',  tabBtn:'tab-uncertainties-btn', pillBtn:null, elementId:'b14-ITIMEU',  blockLabel:'Block #14', tabKey:'tabs.uncertainties' },
  { code:'INUCU',   tabBtn:'tab-uncertainties-btn', pillBtn:null, elementId:'b14-INUCU',   blockLabel:'Block #14', tabKey:'tabs.uncertainties' },
];

// ---------------------------------------------------------------------------
// Bootstrap component references (initialised on DOMContentLoaded)
// ---------------------------------------------------------------------------
let saveAsModal, saveFolderModal, previewModal, validationModal, appToast, runModal;

document.addEventListener('DOMContentLoaded', async () => {
  saveAsModal  = new bootstrap.Modal(document.getElementById('saveAsModal'));
  saveFolderModal = new bootstrap.Modal(document.getElementById('saveFolderModal'));
  previewModal  = new bootstrap.Modal(document.getElementById('previewModal'));
  validationModal = new bootstrap.Modal(document.getElementById('validationModal'));
  appToast     = new bootstrap.Toast(document.getElementById('appToast'));
  runModal     = new bootstrap.Modal(document.getElementById('runModal'));

  // ── "Proceed anyway" button in validation modal ──────────────────────────
  document.getElementById('validation-proceed-btn')
    .addEventListener('click', () => {
      validationModal.hide();
      if (_validationProceedCb) {
        const cb = _validationProceedCb;
        _validationProceedCb = null;
        cb();
      }
    });

  // ── Toolbar buttons ──────────────────────────────────────────────────────
  document.getElementById('btn-new')
    .addEventListener('click', e => { e.preventDefault(); handleNew(); });

  document.getElementById('btn-load')
    .addEventListener('click', e => { e.preventDefault(); document.getElementById('fileInput').click(); });

  document.getElementById('btn-saveas')
    .addEventListener('click', async e => {
      e.preventDefault();
      if (window.showSaveFilePicker) {
        // Native OS file-save dialog (Chromium-based browsers)
        await handleSaveAsNative();
      } else {
        // Fallback: Bootstrap modal with text input
        document.getElementById('save-filename').value = appState.filename;
        saveAsModal.show();
      }
    });

  document.getElementById('btn-save-confirm')
    .addEventListener('click', () => {
      const fname = document.getElementById('save-filename').value.trim() || 'output.5';
      appState.filename = fname;
      saveAsModal.hide();
      handleSave(fname);
    });

  // ── Guardar en carpeta… (U2 del BACKLOG) ──────────────────────────────────
  document.getElementById('btn-save-folder-open')
    .addEventListener('click', e => {
      e.preventDefault();
      const lastFolder = localStorage.getItem(LAST_SAVE_FOLDER_KEY) || '';
      document.getElementById('save-folder-input').value = lastFolder;
      saveFolderModal.show();
    });
  document.getElementById('btn-save-folder-browse')
    .addEventListener('click', e => {
      browseIntoInput('save-folder-input', e.currentTarget, t('modal.save_folder_title'));
    });
  document.getElementById('btn-save-folder-confirm')
    .addEventListener('click', () => handleSaveToFolder());

  // Diálogo de carpeta para el workdir de ejecución (U3 del BACKLOG)
  document.getElementById('btn-run-workdir-browse')
    .addEventListener('click', e => {
      browseIntoInput('run-workdir', e.currentTarget, t('run.workdir_lbl'));
    });

  // ── Preview button ───────────────────────────────────────────────────────
  document.getElementById('btn-preview')
    .addEventListener('click', e => { e.preventDefault(); exportToAcab(); });

  document.getElementById('btn-validate')
    .addEventListener('click', e => {
      e.preventDefault();
      if (!appState.data) appState.data = {};
      collectAll(appState.data);
      showValidationModal(validateAll(), null);
    });

  document.getElementById('btn-preview-copy')
    .addEventListener('click', () => {
      const txt = document.getElementById('preview-content').value;
      navigator.clipboard.writeText(txt).then(
        () => showToast(t('toast.copied'), 'success'),
        () => showToast(t('toast.copy_err'), 'danger'),
      );
    });

  // ── Secciones menu links ─────────────────────────────────────────────────
  document.querySelectorAll('.section-link[data-section]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const target = link.dataset.section;
      const btn = document.querySelector(`[data-bs-target="#${target}"]`);
      if (btn && !btn.classList.contains('disabled')) btn.click();
    });
  });

  // ── File input ───────────────────────────────────────────────────────────
  document.getElementById('fileInput').addEventListener('change', e => {
    const file = e.target.files[0];
    if (file) handleLoad(file);
    e.target.value = '';  // reset so the same file can be re-selected
  });

  // ── Mark dirty on any form change ────────────────────────────────────────
  document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('change', () => {
      if (!appState.dirty) {
        appState.dirty = true;
        setStatus(appState.filename, true);
      }
    });
  });

  // ── Reactive: Block #2 ↔ Block #5/#6, Block #1 ↔ Block #3 warnings ───────
  const b2NuczoEl = document.getElementById('b2-NUCZO');
  const b2IsozoEl = document.getElementById('b2-ISOZO');
  const b1InfdEl  = document.getElementById('b1-INFD');
  const b1IfluEl  = document.getElementById('b1-IFLU');
  const b1IzmEl   = document.getElementById('b1-IZM');
  if (b2NuczoEl) {
    b2NuczoEl.addEventListener('change', () => { rebuildBlock5(); updateIzmNuczoNotice(); });
    // Reconstrucción en vivo mientras se escribe (con debounce), conservando
    // los datos ya introducidos en las zonas que no cambian.
    let _nuczoTimer = null;
    b2NuczoEl.addEventListener('input', () => {
      updateIzmNuczoNotice();
      clearTimeout(_nuczoTimer);
      _nuczoTimer = setTimeout(() => rebuildBlock5(), 400);
    });
  }
  if (b1IzmEl) b1IzmEl.addEventListener('input', updateIzmNuczoNotice);
  if (b2IsozoEl) b2IsozoEl.addEventListener('change', () => rebuildBlock6());
  if (b1InfdEl)  b1InfdEl.addEventListener('change', () => { updateBlock6Visibility(); rebuildBlock6(); });
  if (b1IfluEl)  b1IfluEl.addEventListener('change', updateBlock3Warning);

  // Event delegation for dirty tracking on dynamically created zone inputs
  ['b5-zones-container', 'b6-zones-container'].forEach(cid => {
    const c = document.getElementById(cid);
    if (c) c.addEventListener('change', () => {
      if (!appState.dirty) { appState.dirty = true; setStatus(appState.filename, true); }
    });
  });

  // ── Composición asistida (Block #5) y presets EGRP (Block #2 Card #6) ──
  initB5Calc();
  initEgrpPresets();

  // ── Temporal history (Blocks #7/#8) generator ──────────────────────────
  wireB78EditorButtons('b78', _b78MarkDirty);
  const btnGenerar = document.getElementById('btn-b78-generar');
  if (btnGenerar) btnGenerar.addEventListener('click', generarB78);

  // ── Block #11 conditional visibility ─────────────────────────────────────
  ['b11-IDOSE', 'b11-NVFL', 'b11-NOPUL'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', updateB11Conditional);
  });

  // ── Block #13 conditional visibility ─────────────────────────────────────
  const b13NcyoEl = document.getElementById('b13-NCYO');
  if (b13NcyoEl) b13NcyoEl.addEventListener('change', updateB13Conditional);

  // ── Block #14: enable/disable section when IUNC changes ──────────────────
  const b1IuncEl = document.getElementById('b1-IUNC');
  if (b1IuncEl) b1IuncEl.addEventListener('change', updateIUNCSection);

  // ── Block #14 conditional card 2 (NCYU) ──────────────────────────────────
  const b14NcyuEl = document.getElementById('b14-NCYU');
  if (b14NcyuEl) b14NcyuEl.addEventListener('change', updateB14Conditional);

  // ── Language selector ────────────────────────────────────────────────────
  document.querySelectorAll('.lang-item').forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      loadLang(item.dataset.lang);
    });
  });

  // Load initial language before booting (ensures t() works for first toasts)
  await loadLang(_lang);

  // ── Code search ───────────────────────────────────────────────────────────
  initCodeSearch();

  // ── Ejecución de ACAB (Fase R3) ───────────────────────────────────────────
  document.getElementById('btn-run-open').addEventListener('click', async () => {
    if (!document.getElementById('btn-run-start').disabled) {
      await loadRunConfig();
    }
    runModal.show();
  });

  document.getElementById('btn-run-start').addEventListener('click', () => {
    if (!appState.data) appState.data = {};
    collectAll(appState.data);
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
    showToast(t('toast.session_restored'), 'info', 4000);
  } else {
    handleNew();
  }

  // Autosave periódico + al cambiar de app / recargar / cerrar.
  startAutosave();
});

// ---------------------------------------------------------------------------
// Ejecución de ACAB (Fase R3 del runbook runner v2)
// ---------------------------------------------------------------------------

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
    document.getElementById('run-exe').value     = cfg.exe_name || 'acab.exe';
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

function updateOpenAnalyzerButton(status) {
  const btn = document.getElementById('btn-run-open-analyzer');
  if (status && status.output_exists && status.workdir) {
    btn.href = `http://127.0.0.1:5001/?folder=${encodeURIComponent(status.workdir)}`;
    btn.classList.remove('d-none');
  } else {
    btn.classList.add('d-none');
  }
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

  updateOpenAnalyzerButton(s);

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
  const exeName  = document.getElementById('run-exe').value.trim() || 'acab.exe';
  const timeoutS = parseFloat(document.getElementById('run-timeout').value) || 60;
  const saveCur  = document.getElementById('run-save-current').checked;

  if (!workdir) { showToast(t('toast.run_no_workdir'), 'danger'); return; }

  const body = { workdir, exe_name: exeName, timeout_s: timeoutS,
                 save_current: saveCur, overwrite };
  if (saveCur) {
    if (!appState.data) appState.data = {};
    collectAll(appState.data);
    body.data = appState.data;
  }

  document.getElementById('run-log').textContent = '';
  document.getElementById('btn-run-open-analyzer').classList.add('d-none');
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

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Autosave de sesión (localStorage)
//
// Persiste el fichero en edición para no perderlo al navegar por el banner de
// la suite, recargar la página o cerrar la pestaña. Se restaura al reabrir la
// app. Guardado periódico + al salir de la página (pagehide/beforeunload).
// ---------------------------------------------------------------------------
const SESSION_KEY     = 'acab-inp-session';
const SESSION_VERSION = 1;
const AUTOSAVE_MS     = 5000;

function saveSession() {
  try {
    if (!appState.data) appState.data = {};
    collectAll(appState.data);
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
    appState.filename = payload.filename || 'nuevo.5';
    appState.dirty    = !!payload.dirty;
    populateAll(appState.data);
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

async function handleNew() {
  try {
    const res = await fetch('/api/new');
    const json = await res.json();
    if (!json.ok) throw new Error(json.error || 'Error al crear nuevo fichero.');
    appState.data     = json.data;
    appState.filename = 'nuevo.5';
    appState.dirty    = false;
    populateAll(json.data);
    setStatus('nuevo.5', false);
    showToast(t('toast.new_ok'), 'success');
  } catch (err) {
    showToast(err.message, 'danger');
  }
}

async function handleLoad(file) {
  const fd = new FormData();
  fd.append('file', file);
  try {
    setStatus(file.name, false, /* loading */ true);
    const res  = await fetch('/api/load', { method: 'POST', body: fd });
    const json = await res.json();
    if (!res.ok) {
      if (json.chains) {
        showToast(
          `${json.error} &nbsp;<a href="/chains" class="alert-link text-white fw-bold">Ir a CHAINS →</a>`,
          'warning',
          6000
        );
      } else {
        throw new Error(json.error || 'Error al cargar el fichero.');
      }
      setStatus(appState.filename, appState.dirty);
      return;
    }
    appState.data     = json.data;
    appState.filename = json.filename;
    appState.dirty    = false;
    populateAll(json.data);
    setStatus(json.filename, false);
    showToast(t('toast.file_loaded').replace('{name}', json.filename), 'success');
  } catch (err) {
    setStatus(appState.filename, appState.dirty);
    showToast(err.message, 'danger');
  }
}

async function handleSaveAsNative() {
  if (!appState.data) appState.data = {};
  collectAll(appState.data);

  const timeVal = validateTimesStrictlyIncreasing();
  if (!timeVal.ok) {
    showToast(`${t('toast.err_temporal')}: ${timeVal.errors[0]}`, 'danger');
    return;
  }

  const valResult = validateAll();
  if (valResult.errors.length > 0) {
    showValidationModal(valResult, null);
    return;
  }

  const doSave = async () => {
    let fileHandle;
    try {
      fileHandle = await window.showSaveFilePicker({
        suggestedName: appState.filename,
        types: [{ description: 'ACAB Input Files', accept: { 'text/plain': ['.5'] } }],
      });
    } catch (err) {
      if (err.name !== 'AbortError') showToast(err.message, 'danger');
      return;
    }
    const fname = fileHandle.name;
    appState.filename = fname;
    await _doSave(fname, fileHandle);
  };

  if (valResult.warnings.length > 0) {
    showValidationModal(valResult, doSave);
  } else {
    await doSave();
  }
}

async function handleSave(filename, fileHandle = null) {
  // Flush current form values into appState.data before saving
  if (!appState.data) appState.data = {};
  collectAll(appState.data);

  // 1. Validate temporal history
  const timeVal = validateTimesStrictlyIncreasing();
  if (!timeVal.ok) {
    showToast(`${t('toast.err_temporal')}: ${timeVal.errors[0]}`, 'danger');
    return;
  }

  // 2. Full consistency validation — block on errors, warn on warnings
  const valResult = validateAll();
  if (valResult.errors.length > 0) {
    showValidationModal(valResult, null);
    return;
  }
  if (valResult.warnings.length > 0) {
    showValidationModal(valResult, () => _doSave(filename, fileHandle));
    return;
  }

  await _doSave(filename, fileHandle);
}

// ── Selector de carpeta nativo (U2 del BACKLOG) ─────────────────────────────
// Reutiliza el patrón ya existente en la pestaña Barrido: botón con icono
// junto a un input de texto, con fallback manual (el usuario puede teclear
// la ruta si el diálogo nativo no está disponible).
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

// "Guardar en carpeta…" — escribe inp.5 directamente en la carpeta elegida
// (POST /api/save-to-folder); pide confirmación y reintenta con overwrite
// si el fichero ya existe (mismo patrón que figuras.yaml en el analyzer).
async function handleSaveToFolder() {
  const folder = document.getElementById('save-folder-input').value.trim();
  if (!folder) { showToast(t('toast.no_folder_selected'), 'warning'); return; }

  if (!appState.data) appState.data = {};
  collectAll(appState.data);

  const timeVal = validateTimesStrictlyIncreasing();
  if (!timeVal.ok) {
    showToast(`${t('toast.err_temporal')}: ${timeVal.errors[0]}`, 'danger');
    return;
  }

  const valResult = validateAll();
  if (valResult.errors.length > 0) {
    showValidationModal(valResult, null);
    return;
  }
  if (valResult.warnings.length > 0) {
    showValidationModal(valResult, () => apiSaveToFolder(folder));
    return;
  }

  await apiSaveToFolder(folder);
}

async function apiSaveToFolder(folder) {
  async function attempt(overwrite) {
    const res  = await fetch('/api/save-to-folder', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ data: appState.data, folder, overwrite }),
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
    appState.filename = 'inp.5';
    appState.dirty    = false;
    setStatus(appState.filename, false);
    showToast(t('toast.folder_saved').replace('{name}', appState.filename).replace('{folder}', folder));
    saveFolderModal.hide();
  } catch (e) { showToast(String(e), 'danger'); }
}

async function _doSave(filename, fileHandle = null) {
  try {
    const res = await fetch('/api/save', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ data: appState.data, filename }),
    });
    if (!res.ok) {
      const json = await res.json().catch(() => ({}));
      throw new Error(json.error || 'Error al guardar.');
    }
    const blob = await res.blob();

    if (fileHandle) {
      // Write directly to the file chosen via the native OS dialog
      const writable = await fileHandle.createWritable();
      await writable.write(blob);
      await writable.close();
    } else {
      // Fallback: trigger browser download
      const url = URL.createObjectURL(blob);
      const a   = Object.assign(document.createElement('a'),
                                { href: url, download: filename });
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }

    appState.dirty = false;
    setStatus(filename, false);
    showToast(t('toast.file_saved').replace('{name}', filename), 'success');
  } catch (err) {
    showToast(err.message, 'danger');
  }
}

// ---------------------------------------------------------------------------
// Form population  (server data  →  DOM)
// ---------------------------------------------------------------------------

function populateAll(data) {
  populateBlock1(data.block1);
  populateBlock2(data.block2);
  populateBlock3(data.block3);
  populateBlock5(data.block5);   // must come after block2 (reads b2-NUCZO)
  populateBlock6(data.block6);   // must come after block2 (reads b2-ISOZO)
  populateBlocks78(data.blocks78);
  populateBlock4(data.block4);
  populateBlock9(data.block9);
  populateBlock10(data.block10);
  populateBlock11(data.block11);
  populateBlock13(data.block13);
  populateBlock14(data.block14);
  populateComments(data.comments);
  updateBlock3Warning();
  updateBlock6Visibility();
  updateB11Conditional();
  updateB13Conditional();
  updateB14Conditional();
  updateIUNCSection();
  updateIzmNuczoNotice();
}

function populateBlock1(b) {
  if (!b) return;
  setVal('b1-title', b.title ?? '');
  setVal('b1-IUNC',  b.IUNC  ?? 0);

  const fields = ['ITMAX','IZMAX','MPCTAB','IR','JTO','NTABLE','MSTAR',
                  'INPT','INFD','NOGG','NGRP','IGRP','IGE',
                  'IZM','IM','JM','IFLU','IPRT','ILIB','IRAD','IPUN'];
  fields.forEach(k => setVal(`b1-${k}`, b[k] ?? 0));
}

function populateBlock2(b) {
  if (!b) return;
  setVal('b2-XRR',  b.XRR   ? b.XRR.join('  ')   : '');
  setVal('b2-YZT',  b.YZT   ? b.YZT.join('  ')   : '');
  setVal('b2-MA',   b.MA    ? b.MA.join('  ')     : '');
  setVal('b2-NUCZO',b.NUCZO ? b.NUCZO.join('  ')  : '');
  setVal('b2-ISOZO',b.ISOZO ? b.ISOZO.join('  ') : '');
  setVal('b2-EGRP', b.EGRP  ? b.EGRP.join('  ')  : '');

  // CUTOFF: 6 values
  const cutoff = b.CUTOFF || [0, 0, 0, 0, 0, 0];
  for (let i = 0; i < 6; i++) {
    setVal(`b2-cutoff-${i}`, fmtSci(cutoff[i] ?? 0, 0));
  }

  // NTO: 18 checkbox values
  const nto = b.NTO || Array(18).fill(0);
  for (let i = 0; i < 18; i++) {
    const el = document.getElementById(`b2-nto-${i}`);
    if (el) el.checked = (nto[i] === 1);
  }
}

function collectBlock2() {
  const b = {};
  b.XRR   = parseFloatArray(getVal('b2-XRR'));
  const yzt = parseFloatArray(getVal('b2-YZT'));
  b.YZT   = yzt.length > 0 ? yzt : null;
  b.MA    = parseIntArray(getVal('b2-MA'));
  b.NUCZO = parseIntArray(getVal('b2-NUCZO'));
  const isozo = parseIntArray(getVal('b2-ISOZO'));
  b.ISOZO = isozo.length > 0 ? isozo : null;
  b.EGRP  = parseFloatArray(getVal('b2-EGRP'));

  b.CUTOFF = [];
  for (let i = 0; i < 6; i++) {
    b.CUTOFF.push(parseFloat(getVal(`b2-cutoff-${i}`)) || 0);
  }

  const nto = [];
  for (let i = 0; i < 18; i++) {
    const el = document.getElementById(`b2-nto-${i}`);
    nto.push((el && !el.disabled && el.checked) ? 1 : 0);
  }
  b.NTO = nto.some(v => v === 1) ? nto : null;

  return b;
}

function populateBlock4(b) {
  if (!b) return;
  setVal('b4-IREST', b.IREST ?? 0);
}

function populateBlock9(b) {
  if (!b) return;
  setVal('b9-ERR',   fmtSci(b.ERR,   1e-25));
  setVal('b9-XNORM', fmtSci(b.XNORM, 1.0));
}

function populateBlock10(b) {
  if (!b) return;
  setVal('b10-IGFP',    b.IGFP    ?? 0);
  setVal('b10-IWFYD',   b.IWFYD   ?? 0);
  setVal('b10-IFORT96', b.IFORT96 ?? 0);
}

// ---------------------------------------------------------------------------
// Form collection  (DOM  →  data object)
// ---------------------------------------------------------------------------

function collectAll(data) {
  data.block1   = collectBlock1();
  data.block2   = collectBlock2();
  data.block3   = collectBlock3();
  data.block4   = collectBlock4();
  data.block5   = collectBlock5();
  data.block6   = collectBlock6();
  data.blocks78 = collectBlocks78();
  data.block9   = collectBlock9();
  data.block10  = collectBlock10();
  data.block11  = collectBlock11();
  data.block13  = collectBlock13();
  data.block14  = collectBlock14();
  data.comments = collectComments();
}

function collectBlock1() {
  const b = { title: getVal('b1-title'), IUNC: getInt('b1-IUNC') };
  ['ITMAX','IZMAX','MPCTAB','IR','JTO','NTABLE','MSTAR',
   'INPT','INFD','NOGG','NGRP','IGRP','IGE',
   'IZM','IM','JM','IFLU','IPRT','ILIB','IRAD','IPUN']
    .forEach(k => { b[k] = getInt(`b1-${k}`); });
  return b;
}

function collectBlock4() {
  return { IREST: getInt('b4-IREST') };
}

// ---------------------------------------------------------------------------
// Block #2  helpers
// ---------------------------------------------------------------------------

/** Parse a whitespace-separated string of floats into an array. */
function parseFloatArray(str) {
  return (str || '').trim().split(/\s+/).filter(s => s !== '')
    .map(s => parseFloat(s)).filter(v => !isNaN(v));
}

/** Parse a whitespace-separated string of integers into an array. */
function parseIntArray(str) {
  return (str || '').trim().split(/\s+/).filter(s => s !== '')
    .map(s => parseInt(s, 10)).filter(v => !isNaN(v));
}

function collectBlock9() {
  return {
    ERR:   parseFloat(getVal('b9-ERR'))   || 1e-25,
    XNORM: parseFloat(getVal('b9-XNORM')) || 1.0,
  };
}

function collectBlock10() {
  return {
    IGFP:    getInt('b10-IGFP'),
    IWFYD:   getInt('b10-IWFYD'),
    IFORT96: getInt('b10-IFORT96'),
  };
}

// ---------------------------------------------------------------------------
// Block #3 — Neutron flux
// ---------------------------------------------------------------------------

function populateBlock3(b) {
  setVal('b3-FLUX', b && b.FLUX ? b.FLUX.join('  ') : '');
}

function collectBlock3() {
  const flux = parseFloatArray(getVal('b3-FLUX'));
  return flux.length > 0 ? { FLUX: flux } : null;
}

function updateBlock3Warning() {
  const warn = document.getElementById('b3-iflu-warning');
  if (warn) warn.classList.toggle('d-none', getInt('b1-IFLU') === 1);
}

// ---------------------------------------------------------------------------
// Block #5 — Initial material composition  (dynamic zone panels)
// ---------------------------------------------------------------------------

/**
 * Reactive notice near IZM and NUCZO when their counts disagree.
 * Complements the V05 validation with immediate, in-place feedback.
 */
function updateIzmNuczoNotice() {
  const izm   = getInt('b1-IZM');
  const nuczo = parseIntArray(getVal('b2-NUCZO'));
  const mismatch = Number.isFinite(izm) && izm > 0 && nuczo.length !== izm;
  const html = mismatch
    ? `<span class="text-danger"><i class="bi bi-exclamation-triangle me-1"></i>`
      + `${t('b2.nuczo_izm_mismatch').replace('{n}', nuczo.length).replace('{izm}', izm)}</span>`
    : '';
  const nFb = document.getElementById('b2-nuczo-izm-feedback');
  const iFb = document.getElementById('b1-izm-nuczo-feedback');
  if (nFb) nFb.innerHTML = html;
  if (iFb) iFb.innerHTML = html;
}

/**
 * Rebuild Block #5 zone panels from the current b2-NUCZO textarea.
 * @param {Array|undefined} savedData  Server data (first load) or undefined to
 *                                     preserve what is currently in the DOM.
 */
function rebuildBlock5(savedData) {
  const nuczo     = parseIntArray(getVal('b2-NUCZO'));
  const container = document.getElementById('b5-zones-container');
  const emptyMsg  = document.getElementById('b5-empty-msg');
  if (!container || !emptyMsg) return;

  const saved = (savedData !== undefined) ? savedData : collectBlock5();

  container.innerHTML = '';
  let zoneIdx = 0;
  let hasZones = false;

  nuczo.forEach((n, i) => {
    if (n === 0) return;          // zone omitted
    hasZones = true;
    const count     = Math.abs(n);
    const savedZone = saved[zoneIdx] || { INUCL: [], XCOMP: [] };
    container.appendChild(buildZone5Card(i + 1, zoneIdx, count, savedZone));
    zoneIdx++;
  });

  emptyMsg.classList.toggle('d-none', hasZones);
  refreshB5CalcZoneSelect();   // mantener el selector de la composición asistida al día
}

function buildZone5Card(zoneNum, zoneIdx, count, savedZone) {
  const card = document.createElement('div');
  card.className       = 'card mb-3 block-card';
  card.dataset.zoneIdx = zoneIdx;

  let rows = '';
  for (let j = 0; j < count; j++) {
    const inucl = savedZone.INUCL[j] != null ? savedZone.INUCL[j] : '';
    const xcomp = savedZone.XCOMP[j] != null ? fmtSci(savedZone.XCOMP[j], 0) : '';
    rows += `
      <tr>
        <td class="text-center text-muted small align-middle">${j + 1}</td>
        <td><input type="number"
               class="form-control form-control-sm font-monospace b5-inucl"
               id="b5-z${zoneIdx}-inucl-${j}"
               min="0" step="1" value="${inucl}"
               placeholder="ej. 260000"></td>
        <td><input type="text"
               class="form-control form-control-sm font-monospace b5-xcomp"
               id="b5-z${zoneIdx}-xcomp-${j}"
               value="${xcomp}" placeholder="1.0E-02"></td>
      </tr>`;
  }

  card.innerHTML = `
    <div class="card-header block-card-header">
      <i class="bi bi-grid me-1"></i>${t('b5.zone_lbl')} ${zoneNum}
      <span class="badge bg-secondary ms-2">
        ${count} ${count !== 1 ? t('b5.species_pl') : t('b5.species')}
        <span class="fw-normal">(|NUCZO| = ${count})</span>
      </span>
    </div>
    <div class="card-body p-2">
      <table class="table table-sm table-bordered mb-0 zone-input-table">
        <thead class="table-light">
          <tr>
            <th style="width:2.5rem">#</th>
            <th>${t('b5.col_inucl')} <span class="fw-normal text-muted small">${t('b5.col_inucl_hint')}</span></th>
            <th>${t('b5.col_xcomp')} <span class="fw-normal text-muted small">${t('b5.col_xcomp_hint')}</span></th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  return card;
}

function populateBlock5(b5) {
  rebuildBlock5(Array.isArray(b5) ? b5 : []);
}

function collectBlock5() {
  const zones = [];
  document.querySelectorAll('#b5-zones-container .block-card').forEach(card => {
    const inucls = [...card.querySelectorAll('.b5-inucl')]
      .map(el => parseInt(el.value, 10) || 0);
    const xcomps = [...card.querySelectorAll('.b5-xcomp')]
      .map(el => parseFloat(el.value) || 0);
    zones.push({ INUCL: inucls, XCOMP: xcomps });
  });
  return zones;
}

// ---------------------------------------------------------------------------
// Block #5 — Composición asistida (2A): cálculo a partir de la masa del blanco
// Usa las funciones puras de calc_utils.js y la librería static/data/atomic_data.json
// ---------------------------------------------------------------------------

let _atomicData  = null;   // atomic_data.json (elementos + compuestos)
let _b5CalcLast  = null;   // último resultado de computeComposition

async function initB5Calc() {
  try {
    const res = await fetch('/static/data/atomic_data.json');
    _atomicData = await res.json();
  } catch (_) { _atomicData = null; return; }

  // Datalist de compuestos de la librería
  const dl = document.getElementById('b5calc-compounds');
  if (dl && _atomicData.compounds) {
    dl.innerHTML = _atomicData.compounds
      .map(c => `<option value="${c.formula}">${c.name} — ρ=${c.density} g/cm³</option>`)
      .join('');
  }

  // Selector de modo
  const modeManual = document.getElementById('b5-mode-manual');
  const modeCalc   = document.getElementById('b5-mode-calc');
  const panel      = document.getElementById('b5calc-panel');
  const syncMode = () => panel && panel.classList.toggle('d-none', !modeCalc.checked);
  if (modeManual && modeCalc) {
    modeManual.addEventListener('change', syncMode);
    modeCalc.addEventListener('change', syncMode);
  }

  const btn      = document.getElementById('b5calc-btn');
  const btnApply = document.getElementById('b5calc-apply');
  const btnVol   = document.getElementById('b5calc-vol-from-rho');
  const btnFix   = document.getElementById('b5calc-vol-fix-btn');
  const formulaEl = document.getElementById('b5calc-formula');
  const massEl    = document.getElementById('b5calc-mass');
  const volEl     = document.getElementById('b5calc-vol');
  const zoneEl    = document.getElementById('b5calc-zone');
  if (btn)      btn.addEventListener('click', computeB5Calc);
  if (btnApply) btnApply.addEventListener('click', applyB5Calc);
  if (btnVol)   btnVol.addEventListener('click', volumeFromDensity);
  if (btnFix)   btnFix.addEventListener('click', fixVolumeToZone);
  if (formulaEl) formulaEl.addEventListener('input', refreshB5CalcLive);
  if (massEl)    massEl.addEventListener('input', refreshB5CalcLive);
  if (volEl)     volEl.addEventListener('input', refreshB5CalcLive);
  if (zoneEl)    zoneEl.addEventListener('change', refreshB5CalcLive);

  refreshB5CalcZoneSelect();
}

/**
 * Devuelve la densidad conocida para una fórmula, o null si no hay dato.
 * Busca en dos fuentes, por este orden:
 *   1) La lista de compuestos de la librería (coincidencia exacta de fórmula).
 *   2) La densidad del elemento, si la fórmula se reduce a un único elemento
 *      (p. ej. "Ag", "W", "O2"): en ese caso la densidad de bulto es la del
 *      elemento en su estado de referencia, independiente del subíndice.
 * @returns {{name, density, provenance}|null}
 */
function _findDensity(formula) {
  if (!_atomicData) return null;
  const f = String(formula || '').trim();
  if (!f) return null;

  // 1) Compuesto explícito de la librería
  const comp = (_atomicData.compounds || []).find(c => c.formula === f);
  if (comp) return { name: comp.name, density: comp.density, provenance: comp.provenance };

  // 2) Elemento puro: la fórmula parsea a un único símbolo con densidad conocida
  let stoich;
  try { stoich = parseChemFormula(f); } catch (_) { return null; }
  const syms = Object.keys(stoich);
  if (syms.length === 1) {
    const sym = syms[0];
    const el  = _atomicData.elements && _atomicData.elements[sym];
    if (el && Number.isFinite(el.density) && el.density > 0) {
      const phase = el.state === 'gas'    ? 'gas, 0 °C 1 atm'
                  : el.state === 'liquid' ? 'líquido, ~20 °C'
                  :                         'sólido, ~20 °C';
      return { name: sym, density: el.density, provenance: `elemento (${phase}), CRC Handbook` };
    }
  }
  return null;
}

function updateDensityHint() {
  const hint = document.getElementById('b5calc-density-hint');
  if (!hint) return;
  const c = _findDensity(getVal('b5calc-formula'));
  if (c) {
    hint.textContent = `${c.name}: ρ = ${c.density} g/cm³  (${c.provenance})`;
    hint.classList.remove('d-none');
  } else {
    hint.classList.add('d-none');
  }
}

/** Nº de zona (1-based, como en NUCZO/MA) seleccionado en el selector de zona destino. */
function _b5CalcZoneNumber() {
  const idx = parseInt(getVal('b5calc-zone'), 10);
  return Number.isFinite(idx) ? idx + 1 : null;
}

/** Volumen efectivo (volumenZonaEfectivo, calc_utils.js) de la zona destino actual. */
function _b5CalcVolumenEfectivo() {
  const zona = _b5CalcZoneNumber();
  if (zona == null) return null;
  const bloque1 = { IGE: getInt('b1-IGE'), IZM: getInt('b1-IZM'), JM: getInt('b1-JM') };
  const bloque2 = { XRR: parseFloatArray(getVal('b2-XRR')), MA: parseIntArray(getVal('b2-MA')) };
  return volumenZonaEfectivo(bloque1, bloque2, zona);
}

/**
 * F10 — Valida en vivo el V tecleado frente al volumen efectivo de la zona
 * destino (compararVolumenZona, calc_utils.js). Un desajuste no lo detecta
 * ACAB: la masa realmente simulada pasa a ser m·(V_zona/V_tecleado).
 */
function updateVolumeCoherence() {
  const errBox  = document.getElementById('b5calc-vol-error');
  const errText = document.getElementById('b5calc-vol-error-text');
  const infoBox = document.getElementById('b5calc-vol-info');
  if (!errBox || !errText || !infoBox) return;
  errBox.classList.add('d-none');
  infoBox.classList.add('d-none');

  const zona  = _b5CalcZoneNumber();
  const V     = parseFloat(getVal('b5calc-vol'));
  const volEf = _b5CalcVolumenEfectivo();
  if (zona == null || !volEf || !(V > 0)) return;

  const cmp = compararVolumenZona(V, volEf);
  if (cmp.estado === 'indeterminado') {
    if (cmp.motivo !== 'V_INVALIDO') {
      infoBox.textContent = t('b5calc.vol_indeterminado').replace('{z}', zona);
      infoBox.classList.remove('d-none');
    }
    return;
  }
  if (cmp.estado === 'no_coincide') {
    errText.textContent = t('b5calc.vol_mismatch')
      .replace('{v}', V)
      .replace('{vz}', cmp.volumenEfectivo)
      .replace('{z}', zona)
      .replace('{factor}', cmp.factor.toPrecision(4));
    errBox.classList.remove('d-none');
  }
}

/** Botón de corrección de F10: rellena V con el volumen efectivo de la zona. */
function fixVolumeToZone() {
  const volEf = _b5CalcVolumenEfectivo();
  if (!volEf || volEf.indeterminado) return;
  setVal('b5calc-vol', volEf.volumen.toPrecision(6));
  refreshB5CalcLive();
}

/** Refresca en vivo la pista de densidad y F10 (coherencia de volumen). */
function refreshB5CalcLive() {
  updateDensityHint();
  updateVolumeCoherence();
}

function volumeFromDensity() {
  const c = _findDensity(getVal('b5calc-formula'));
  const m = parseFloat(getVal('b5calc-mass'));
  const msg = document.getElementById('b5calc-msg');
  if (!c) {
    if (msg) { msg.textContent = t('b5calc.err_no_density'); msg.classList.remove('d-none'); }
    return;
  }
  if (!(m > 0)) {
    if (msg) { msg.textContent = t('b5calc.err_mass'); msg.classList.remove('d-none'); }
    return;
  }
  if (msg) msg.classList.add('d-none');
  setVal('b5calc-vol', (m / c.density).toPrecision(6));
  refreshB5CalcLive();
}

/** Rellena el selector de zona destino con las zonas activas (NUCZO ≠ 0). */
function refreshB5CalcZoneSelect() {
  const sel = document.getElementById('b5calc-zone');
  if (!sel) return;
  const prev  = sel.value;
  const nuczo = parseIntArray(getVal('b2-NUCZO'));
  const opts  = [];
  nuczo.forEach((n, i) => {
    if (n !== 0) opts.push(`<option value="${i}">${t('b5.zone_lbl')} ${i + 1}</option>`);
  });
  sel.innerHTML = opts.join('');
  if (prev && [...sel.options].some(o => o.value === prev)) sel.value = prev;
  refreshB5CalcLive();
}

function computeB5Calc() {
  const msg = document.getElementById('b5calc-msg');
  const res = document.getElementById('b5calc-result');
  [msg, res].forEach(el => el && el.classList.add('d-none'));
  _b5CalcLast = null;

  if (!_atomicData) {
    if (msg) { msg.textContent = t('b5calc.err_no_lib'); msg.classList.remove('d-none'); }
    return;
  }
  const inpt = getInt('b1-INPT') || 1;
  const V    = parseFloat(getVal('b5calc-vol'));
  let out;
  try {
    out = computeComposition({
      formula:  getVal('b5calc-formula'),
      massG:    parseFloat(getVal('b5calc-mass')),
      volumeCc: V,
      inpt,
      elements: _atomicData.elements,
    });
  } catch (e) {
    if (msg) { msg.textContent = e.message; msg.classList.remove('d-none'); }
    return;
  }
  _b5CalcLast = out;

  // F10/F11: coherencia de volumen y densidad efectiva de la zona destino
  refreshB5CalcLive();

  // Tabla de resultados
  const unit  = inpt === 3 ? 'g/cc' : 'átomos/barn·cm';
  const tbody = document.getElementById('b5calc-tbody');
  if (tbody) {
    tbody.innerHTML = out.rows.map(r => `
      <tr>
        <td>${r.symbol}</td><td>${r.Z}</td>
        <td class="font-monospace">${r.elemid}</td>
        <td class="font-monospace">${r.massFrac.toFixed(6)}</td>
        <td class="font-monospace">${r.xcomp.toExponential(6).toUpperCase()} ${unit}</td>
      </tr>`).join('');
  }
  if (res) res.classList.remove('d-none');
}

function applyB5Calc() {
  if (!_b5CalcLast) return;
  const zoneIdx = parseInt(getVal('b5calc-zone'), 10);
  if (!Number.isFinite(zoneIdx)) return;
  const n = _b5CalcLast.rows.length;

  // Ajustar NUCZO[zoneIdx] al nº de elementos calculados si difiere
  const nuczo = parseIntArray(getVal('b2-NUCZO'));
  if (nuczo[zoneIdx] !== n) {
    nuczo[zoneIdx] = n;
    setVal('b2-NUCZO', nuczo.join(' '));
    rebuildBlock5();
    showToast(t('b5calc.toast_nuczo').replace('{z}', zoneIdx + 1).replace('{n}', n), 'warning');
  }

  // Rellenar los inputs de la zona (mapear zoneIdx real → índice de card)
  let cardIdx = 0;
  for (let i = 0; i < zoneIdx; i++) if (nuczo[i] !== 0) cardIdx++;
  _b5CalcLast.rows.forEach((r, j) => {
    setVal(`b5-z${cardIdx}-inucl-${j}`, r.elemid);
    setVal(`b5-z${cardIdx}-xcomp-${j}`, r.xcomp.toExponential(6).toUpperCase());
  });
  appState.dirty = true;
  setStatus(appState.filename, true);
  showToast(t('b5calc.toast_applied'), 'success');
}

// ---------------------------------------------------------------------------
// Block #2 Card #6 — Presets EGRP y validación en vivo (2B)
// Librería: static/data/egrp_presets.json; validador: validateEgrp (calc_utils.js)
// ---------------------------------------------------------------------------

let _egrpPresets = null;

async function initEgrpPresets() {
  try {
    const res = await fetch('/static/data/egrp_presets.json');
    _egrpPresets = await res.json();
  } catch (_) { _egrpPresets = null; }

  const sel = document.getElementById('b2-egrp-preset');
  if (sel && _egrpPresets) {
    const nameKey = _lang === 'en' ? 'name_en' : 'name_es';
    sel.innerHTML = `<option value="">${t('egrp.preset_none')}</option>` +
      _egrpPresets.presets
        .map(p => `<option value="${p.id}">${p[nameKey]}</option>`)
        .join('');
    sel.addEventListener('change', () => {
      const prov = document.getElementById('b2-egrp-provenance');
      const p = _egrpPresets.presets.find(x => x.id === sel.value);
      if (prov) {
        prov.textContent = p ? `${t('egrp.provenance_lbl')}: ${p.provenance}` : '';
        prov.classList.toggle('d-none', !p);
      }
    });
  }

  const btn = document.getElementById('b2-egrp-apply');
  if (btn) btn.addEventListener('click', applyEgrpPreset);

  const egrpEl = document.getElementById('b2-EGRP');
  const noggEl = document.getElementById('b1-NOGG');
  if (egrpEl) egrpEl.addEventListener('input', liveValidateEgrp);
  if (noggEl) noggEl.addEventListener('change', liveValidateEgrp);
}

function applyEgrpPreset() {
  if (!_egrpPresets) return;
  const sel = document.getElementById('b2-egrp-preset');
  const p   = _egrpPresets.presets.find(x => x.id === (sel && sel.value));
  if (!p) { showToast(t('egrp.toast_pick'), 'warning'); return; }
  setVal('b2-EGRP', p.boundaries.join(' '));
  setVal('b1-NOGG', p.nogg);          // coherencia Bloque #1 ↔ Bloque #2
  appState.dirty = true;
  setStatus(appState.filename, true);
  liveValidateEgrp();
  showToast(t('egrp.toast_applied').replace('{nogg}', p.nogg), 'success');
}

/** Validación en vivo del textarea EGRP frente al NOGG actual del Bloque #1. */
function liveValidateEgrp() {
  const fb = document.getElementById('b2-egrp-feedback');
  if (!fb) return;
  const nogg = getInt('b1-NOGG') || 0;
  const raw  = getVal('b2-EGRP').trim();
  if (!raw || nogg <= 0) { fb.innerHTML = ''; return; }
  const arr = parseFloatArray(raw);
  const msgs = [];
  for (const e of validateEgrp(arr, nogg).errors) {
    if (e.code === 'EGRP_COUNT')
      msgs.push(t('val.v03').replace('{exp}', e.exp).replace('{got}', e.got));
    else if (e.code === 'EGRP_NOT_DECREASING')
      msgs.push(t('val.v23a').replace('{i}', e.i).replace('{v}', e.v).replace('{prev}', e.prev));
    else if (e.code === 'EGRP_NEGATIVE')
      msgs.push(t('val.v23b').replace('{v}', e.v));
    else if (e.code === 'EGRP_NAN')
      msgs.push(t('val.v23c').replace('{i}', e.i));
  }
  fb.innerHTML = msgs.length
    ? `<span class="text-danger"><i class="bi bi-x-circle me-1"></i>${msgs.join('<br>')}</span>`
    : `<span class="text-success"><i class="bi bi-check-circle me-1"></i>${t('egrp.valid_ok').replace('{nogg}', nogg)}</span>`;
}

// ---------------------------------------------------------------------------
// Block #6 — Continuous feed  (dynamic zone panels)
// ---------------------------------------------------------------------------

function updateBlock6Visibility() {
  const pill = document.getElementById('pill-b6');
  if (pill) pill.classList.toggle('opacity-50', getInt('b1-INFD') === 0);
}

function rebuildBlock6(savedData) {
  const isozo     = parseIntArray(getVal('b2-ISOZO'));
  const container = document.getElementById('b6-zones-container');
  const emptyMsg  = document.getElementById('b6-empty-msg');
  if (!container || !emptyMsg) return;

  const saved = (savedData !== undefined) ? savedData : collectBlock6();

  container.innerHTML = '';
  let zoneIdx = 0;
  let hasZones = false;

  if (getInt('b1-INFD') > 0) {
    isozo.forEach((n, i) => {
      if (n === 0) return;
      hasZones = true;
      const savedZone = (saved || [])[zoneIdx] || { IDNUM: [], XFEED: [] };
      container.appendChild(buildZone6Card(i + 1, zoneIdx, n, savedZone));
      zoneIdx++;
    });
  }

  emptyMsg.classList.toggle('d-none', hasZones);
}

function buildZone6Card(zoneNum, zoneIdx, count, savedZone) {
  const card = document.createElement('div');
  card.className       = 'card mb-3 block-card';
  card.dataset.zoneIdx = zoneIdx;

  let rows = '';
  for (let j = 0; j < count; j++) {
    const idnum = savedZone.IDNUM[j] != null ? savedZone.IDNUM[j] : '';
    const xfeed = savedZone.XFEED[j] != null ? fmtSci(savedZone.XFEED[j], 0) : '';
    rows += `
      <tr>
        <td class="text-center text-muted small align-middle">${j + 1}</td>
        <td><input type="number"
               class="form-control form-control-sm font-monospace b6-idnum"
               id="b6-z${zoneIdx}-idnum-${j}"
               min="0" step="1" value="${idnum}"
               placeholder="ej. 260000"></td>
        <td><input type="text"
               class="form-control form-control-sm font-monospace b6-xfeed"
               id="b6-z${zoneIdx}-xfeed-${j}"
               value="${xfeed}" placeholder="1.0E+00"></td>
      </tr>`;
  }

  card.innerHTML = `
    <div class="card-header block-card-header">
      <i class="bi bi-droplet me-1"></i>${t('b6.zone_lbl')} ${zoneNum}
      <span class="badge bg-secondary ms-2">
        ${count} ${count !== 1 ? t('b6.species_pl') : t('b6.species')}
        <span class="fw-normal">(ISOZO = ${count})</span>
      </span>
    </div>
    <div class="card-body p-2">
      <table class="table table-sm table-bordered mb-0 zone-input-table">
        <thead class="table-light">
          <tr>
            <th style="width:2.5rem">#</th>
            <th>${t('b6.col_idnum')} <span class="fw-normal text-muted small">${t('b6.col_idnum_hint')}</span></th>
            <th>${t('b6.col_xfeed')} <span class="fw-normal text-muted small">${t('b6.col_xfeed_hint')}</span></th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  return card;
}

function populateBlock6(b6) {
  rebuildBlock6(Array.isArray(b6) ? b6 : null);
}

function collectBlock6() {
  const zones = [];
  document.querySelectorAll('#b6-zones-container .block-card').forEach(card => {
    const idnums = [...card.querySelectorAll('.b6-idnum')]
      .map(el => parseInt(el.value, 10) || 0);
    const xfeeds = [...card.querySelectorAll('.b6-xfeed')]
      .map(el => parseFloat(el.value) || 0);
    zones.push({ IDNUM: idnums, XFEED: xfeeds });
  });
  return zones.length > 0 ? zones : null;
}

// ---------------------------------------------------------------------------
// Blocks #7/#8 — Temporal history generator (port of generador_acab.py)
//
// El editor de tramos (tablas + IUNIT/IOUT/IPLOT) vive en
// static/js/b78_editor.js como componente reutilizable (prefijo de ids
// parametrizable) -- U7 del BACKLOG lo instancia también por tarjeta en el
// barrido temporal. Esta sección es solo el wrapper de la pestaña manual
// (prefijo fijo 'b78' sobre su markup estático de index.html), que añade el
// efecto lateral propio del formulario principal (marcar "dirty").
// ---------------------------------------------------------------------------

function _b78MarkDirty() {
  if (!appState.dirty) { appState.dirty = true; setStatus(appState.filename, true); }
}

function addB78PhaseRow(phase, t_fin = '', pasos = '') {
  addB78EditorRow('b78', phase, t_fin, pasos, _b78MarkDirty);
}

function getB78PhaseEntradas(phase) {
  return getB78EditorFase('b78', phase);
}

/* calcularVectorTiempos y buildBlocks78 viven en static/js/sweep_utils.js
 * (funciones puras reutilizadas por el generador manual y por el barrido
 * paramétrico).  En el navegador quedan como globales; en node se importan. */

/** Format a number in ACAB scientific notation (e.g. 2.400E+01). */
function fmtAcab(n) {
  return n.toExponential(3).toUpperCase().replace(/E([+-])(\d)$/, 'E$10$2');
}

function serializeBlocks78Sets(sets) {
  const lines = [];
  sets.forEach((s, idx) => {
    lines.push(idx === 0
      ? '<Blocks #7,#8  Irradiation and cooling temporal history'
      : '<continue');
    lines.push(
      ` ${String(s.MMN).padStart(2)} ${String(s.MOUT).padStart(2)}`
      + `   ${s.NGO} ${String(s.MSUB).padStart(2)}`
      + `  ${s.IUNIT} ${s.MFEED}   ${s.IOUT} ${s.IPLOT}`
    );
    for (let j = 0; j < s.TIMES.length; j += 5)
      lines.push(' ' + s.TIMES.slice(j, j + 5).map(fmtAcab).join(' '));
  });
  return lines.join('\n');
}

function generarB78() {
  const valMsg = document.getElementById('b78-val-msg');
  const okMsg  = document.getElementById('b78-ok-msg');
  valMsg.classList.add('d-none');
  okMsg.classList.add('d-none');
  try {
    const { fasesIrr: irrEntradas, fasesCool: coolEntradas } = getB78EditorFases('b78');
    if (irrEntradas.length === 0 && coolEntradas.length === 0)
      throw new Error(t('b78.no_phase'));

    const { iunit, iout, iplot } = getB78EditorIunitIoutIplot('b78');

    const { sets, times } = buildBlocks78(irrEntradas, coolEntradas,
                                          { iunit, iout, iplot, t });

    if (!appState.data) appState.data = {};
    appState.data.blocks78 = { sets, times };
    appState.dirty = true;
    setStatus(appState.filename, true);

    const preview = document.getElementById('b78-code-preview');
    if (preview) preview.value = serializeBlocks78Sets(sets);
    okMsg.classList.remove('d-none');

    // Auto-sync NOTTS in Block #11
    const nottsEl = document.getElementById('b11-NOTTS');
    if (nottsEl) nottsEl.value = sets.length;

    // Auto-sync ITSO in Block #13: NOTTS (Block #11) = nº de tarjetas del
    // historial; ITSO (Block #13, tarjeta 3) es un vector [NOTTS] con el
    // flag de salida por time set (manual ACAB 2008, Block #13) -- un 0
    // suprime en silencio ese set del fort.6 (trampa para el analyzer). Se
    // redimensiona a "todo con salida" (1); el campo sigue editable después
    // si el usuario quiere suprimir algún set.
    const itsoEl = document.getElementById('b13-ITSO');
    if (itsoEl) {
      const prevItso = parseIntArray(itsoEl.value);
      const wasCustomized = prevItso.length > 0 && prevItso.some(v => v !== 1);
      itsoEl.value = Array(sets.length).fill(1).join(' ');
      if (wasCustomized)
        showToast(t('b78.itso_resized_hint').replace('{n}', sets.length), 'info');
    }

  } catch (err) {
    valMsg.textContent = err.message;
    valMsg.classList.remove('d-none');
  }
}

function validateTimesStrictlyIncreasing() {
  const b78 = appState.data?.blocks78;
  if (!b78?.times?.length) return { ok: true, errors: [] };
  const errors = [];
  const times  = b78.times;
  let prevT = null, prevType = null;
  for (let i = 0; i < times.length; i++) {
    const [t, type] = times[i];
    if (prevType === type && t <= prevT)
      errors.push(`Paso ${i + 1}: tiempo ${t} no es mayor que el anterior (${prevT}) en la misma fase.`);
    else if (prevType === 1 && type === 0 && t <= 0)
      errors.push(`Primer tiempo de enfriamiento (${t}) debe ser mayor que 0.`);
    prevT = t; prevType = type;
  }
  return { ok: errors.length === 0, errors };
}

// ---------------------------------------------------------------------------
// validateAll — comprehensive cross-block consistency checks
// ---------------------------------------------------------------------------

/**
 * Validate all form data for completeness and cross-block consistency.
 * Must be called after collectAll() has been run.
 * @returns {{ errors: {msg:string}[], warnings: {msg:string}[] }}
 */
function validateAll() {
  const d   = appState.data || {};
  const b1  = d.block1   || {};
  const b2  = d.block2   || {};
  const b3  = d.block3;
  const b4  = d.block4   || {};
  const b5  = d.block5   || [];
  const b6  = d.block6   || [];
  const b10 = d.block10  || {};
  const b11 = d.block11  || {};
  const b13 = d.block13;
  const b14 = d.block14;
  const b78 = d.blocks78 || {};

  const iunc  = b1.IUNC   ?? 0;
  const nogg  = b1.NOGG   ?? 0;
  const ngrp  = b1.NGRP   ?? 1;
  const igrp  = b1.IGRP   ?? 0;
  const ige   = b1.IGE    ?? 4;
  const izm   = b1.IZM    ?? 1;
  const im    = b1.IM     ?? 1;
  const jm    = b1.JM     ?? 0;
  const iflu  = b1.IFLU   ?? 0;
  const infd  = b1.INFD   ?? 0;
  const jto   = b1.JTO    ?? 0;
  const mstar = b1.MSTAR  ?? 1;
  const igfp  = b10.IGFP  ?? 0;
  const nopul = b11.NOPUL ?? 0;
  const ntseq = b11.NTSEQ ?? 0;
  const notts = b11.NOTTS ?? 1;
  const nvfl  = b11.NVFL  ?? 0;
  const irest = b4.IREST  ?? 0;
  const idose = b11.IDOSE ?? 0;

  const jmNote = jm > 0 ? '×JM' : '';

  const errors   = [];
  const warnings = [];
  const err  = msg => errors.push({ msg });
  const warn = msg => warnings.push({ msg });

  // ── V01: IUNC=1 → NGRP must be 1 ──────────────────────────────────────
  if (iunc === 1 && ngrp !== 1)
    err(t('val.v01').replace('{ngrp}', ngrp));

  // ── V02: IGFP=1 (and IUNC=0) → NGRP must be 1 ─────────────────────────
  if (igfp === 1 && iunc === 0 && ngrp !== 1)
    err(t('val.v02').replace('{ngrp}', ngrp));

  // ── V03: NOGG > 0 → EGRP must have NOGG+1 values ──────────────────────
  if (nogg > 0) {
    const egrp = b2.EGRP || [];
    if (egrp.length !== nogg + 1)
      err(t('val.v03').replace('{exp}', nogg + 1).replace('{got}', egrp.length));
  }

  // ── V04: IFLU=1 → FLUX required with correct count ─────────────────────
  if (iflu === 1) {
    const flux = (b3 || {}).FLUX || [];
    if (flux.length === 0) {
      err(t('val.v04a'));
    } else {
      const expected = iunc === 1
        ? im
        : (jm > 0 ? (ngrp + igrp) * im * jm : (ngrp + igrp) * im);
      if (flux.length !== expected)
        err(t('val.v04b')
          .replace('{exp}', expected)
          .replace('{got}', flux.length)
          .replace('{jm_x}', jmNote));
    }
  }

  // ── V05: NUCZO must have IZM values ────────────────────────────────────
  const nuczo = b2.NUCZO || [];
  if (nuczo.length !== izm)
    err(t('val.v05').replace('{izm}', izm).replace('{got}', nuczo.length));

  // ── V06: XRR length (IZM+1 for 3D-MC, IM+1 otherwise) ─────────────────
  const xrr    = b2.XRR || [];
  const xrrExp = ige === 4 ? izm + 1 : im + 1;
  const xrrNote = ige === 4
    ? ` (IZM+1 para geometría 3D-MC: ${izm}+1)`
    : ` (IM+1: ${im}+1)`;
  if (xrr.length !== xrrExp)
    err(t('val.v06')
      .replace('{exp}', xrrExp)
      .replace('{got}', xrr.length)
      .replace('{xrr_note}', xrrNote));

  // ── V07: JM > 0 → YZT required (JM+1 values) ──────────────────────────
  if (jm > 0) {
    const yzt = b2.YZT || [];
    if (yzt.length !== jm + 1)
      err(t('val.v07').replace('{exp}', jm + 1).replace('{got}', yzt.length));
  }

  // ── V08: MA length (IM for 1D/3D; IM×JM for 2D) ───────────────────────
  const ma    = b2.MA || [];
  const maExp = jm > 0 ? im * jm : im;
  if (ma.length !== maExp)
    err(t('val.v08')
      .replace('{exp}', maExp)
      .replace('{got}', ma.length)
      .replace('{jm_x}', jmNote));

  // ── V09: MA values in range [0, IZM] ───────────────────────────────────
  ma.forEach((v, i) => {
    if (v < 0 || v > izm)
      err(t('val.v09').replace('{i}', i + 1).replace('{v}', v).replace('{izm}', izm));
  });

  // ── V10: INFD > 0 → ISOZO must have IZM values ─────────────────────────
  if (infd > 0) {
    const isozo = b2.ISOZO || [];
    if (isozo.length !== izm)
      err(t('val.v10').replace('{izm}', izm).replace('{got}', isozo.length));
  }

  // ── V11: JTO=1 → NTO should have at least one active flag ──────────────
  if (jto === 1) {
    const nto = b2.NTO;
    if (!nto || nto.every(v => v === 0))
      warn(t('val.v11'));
  }

  // ── V12 eliminada ────────────────────────────────────────────────────────
  // MSTAR es un índice de timestep de enfriamiento (Block#1: "Timestep used
  // to select the most important isotopes... chosen from post-irradiation
  // periods"), no un índice de set. Compararlo con NOTTS era incorrecto.
  // Además, cuando NTABLE=0 MSTAR no tiene efecto (Block#1). Sin un rango
  // válido explícito en el manual, esta validación se suprime.

  // ── V13: NOPUL=0 → NTSEQ debería ser 0 (advertencia) ──────────────────
  // El manual (Block#11, Card#6) indica: "If NOPUL=0, NTSEQ must be set to 0."
  // Sin embargo, ACAB acepta NTSEQ≠0 cuando NOPUL=0 ignorando su valor,
  // por lo que se trata como advertencia en lugar de error.
  if (nopul === 0 && ntseq !== 0)
    warn(t('val.v13').replace('{ntseq}', ntseq));

  // ── V14: NTSEQ ≤ NOTTS ─────────────────────────────────────────────────
  if (ntseq > notts)
    err(t('val.v14').replace('{ntseq}', ntseq).replace('{notts}', notts));

  // ── V15: NVFL=1 → FVAR must have NOTTS values ──────────────────────────
  if (nvfl === 1) {
    const fvar = b11.FVAR || [];
    if (fvar.length !== notts)
      err(t('val.v15').replace('{notts}', notts).replace('{got}', fvar.length));
  }

  // ── V16: Blocks #7/#8 sets count must equal NOTTS ──────────────────────
  const sets = b78.sets || [];
  if (sets.length !== notts)
    warn(t('val.v16').replace('{sets}', sets.length).replace('{notts}', notts));

  // ── V17: Block #13 (IUNC=0) consistency ───────────────────────────────
  if (iunc === 0 && b13) {
    const ncyo = b13.NCYO ?? 0;
    if (ncyo > nopul + 1)
      err(t('val.v17a').replace('{ncyo}', ncyo).replace('{max}', nopul + 1));
    if (nopul === 0 && ncyo !== 0)
      err(t('val.v17b').replace('{ncyo}', ncyo));
    if (ncyo > 0) {
      const icyo = b13.ICYO || [];
      if (icyo.length !== ncyo)
        err(t('val.v17c').replace('{ncyo}', ncyo).replace('{got}', icyo.length));
      icyo.forEach((v, i) => {
        if (v < 1 || v > nopul + 1)
          err(t('val.v17d').replace('{i}', i + 1).replace('{v}', v).replace('{max}', nopul + 1));
      });
    }
    const itso = b13.ITSO || [];
    if (itso.length !== notts)
      err(t('val.v17e').replace('{notts}', notts).replace('{got}', itso.length));
  }

  // ── V18: Block #14 (IUNC=1) consistency ───────────────────────────────
  if (iunc === 1) {
    if (!b14) {
      err(t('val.v18a'));
    } else {
      const ncyu = b14.NCYU ?? 0;
      if (ncyu > nopul + 1)
        err(t('val.v18b').replace('{ncyu}', ncyu).replace('{max}', nopul + 1));
      if (nopul === 0 && ncyu !== 0)
        err(t('val.v18c').replace('{ncyu}', ncyu));
      if (ncyu > 0) {
        const icyu = b14.ICYU || [];
        if (icyu.length !== ncyu)
          err(t('val.v18d').replace('{ncyu}', ncyu).replace('{got}', icyu.length));
      }
      const itsu = b14.ITSU || [];
      if (itsu.length !== notts) {
        err(t('val.v18e').replace('{notts}', notts).replace('{got}', itsu.length));
      } else {
        const nonZero = itsu.filter(v => v > 0).length;
        const timeIndices = b14.time_indices || [];
        if (timeIndices.length !== nonZero)
          err(t('val.v18f').replace('{exp}', nonZero).replace('{got}', timeIndices.length));
      }
      const nnucu = b14.NNUCU ?? 0;
      const inucu = b14.INUCU || [];
      if (inucu.length !== nnucu)
        err(t('val.v18g').replace('{nnucu}', nnucu).replace('{got}', inucu.length));
    }
  }

  // ── V19: IDOSE=1 → at least one dose rate must be selected ─────────────
  if (idose === 1) {
    const dose = b11.dose_output || {};
    if (!dose.PH && !dose.BREM && !dose.TOT && !dose.RHOR)
      warn(t('val.v19'));
  }

  // ── V20: Block #5 completeness when IREST=0 ────────────────────────────
  if (irest === 0) {
    if (b5.length === 0) {
      err(t('val.v20a'));
    } else {
      b5.forEach((zone, zi) => {
        (zone.INUCL || []).forEach((v, j) => {
          if (!v || v === 0)
            err(t('val.v20b').replace('{z}', zi + 1).replace('{j}', j + 1));
        });
      });
    }
  }

  // ── V21: INFD > 0 → Block #6 must have zones ───────────────────────────
  if (infd > 0 && (!b6 || b6.length === 0))
    warn(t('val.v21'));

  // ── V22: NOPUL > 0 → NMULT must be specified ───────────────────────────
  if (nopul > 0 && (b11.NMULT === null || b11.NMULT === undefined))
    warn(t('val.v22'));

  // ── V23: EGRP estrictamente decreciente y última frontera ≥ 0 ──────────
  // (el recuento NOGG+1 ya se comprueba en V03; validateEgrp lo repite pero
  //  aquí solo se reportan monotonicidad, signo y valores no numéricos)
  if (nogg > 0) {
    for (const e of validateEgrp(b2.EGRP || [], nogg).errors) {
      if (e.code === 'EGRP_NOT_DECREASING')
        err(t('val.v23a').replace('{i}', e.i).replace('{v}', e.v).replace('{prev}', e.prev));
      else if (e.code === 'EGRP_NEGATIVE')
        err(t('val.v23b').replace('{v}', e.v));
      else if (e.code === 'EGRP_NAN')
        err(t('val.v23c').replace('{i}', e.i));
    }
  }

  // ── V24: coherencia INPT ↔ tipo de identificadores del Bloque #5 ───────
  // INPT=1/3 → elementos (ELEMID = 10000·Z, múltiplo de 10000);
  // INPT=2   → isótopos (NUCLID = 10000·Z + 10·A + IS).
  if (irest === 0 && b5.length > 0) {
    const inpt = b1.INPT ?? 1;
    b5.forEach((zone, zi) => {
      (zone.INUCL || []).forEach((v, j) => {
        if (!v) return; // ya cubierto por V20
        if ((inpt === 1 || inpt === 3) && v % 10000 !== 0)
          err(t('val.v24a').replace('{z}', zi + 1).replace('{j}', j + 1)
                            .replace('{v}', v).replace('{inpt}', inpt));
      });
      if (inpt === 2) {
        const nucl = (zone.INUCL || []).filter(v => v);
        if (nucl.length && nucl.every(v => v % 10000 === 0))
          warn(t('val.v24b').replace('{z}', zi + 1));
      }
    });
  }

  // ── V25: reglas de los sets de Bloques #7/#8 ────────────────────────────
  // MOUT ∈ [1,10]; 0 ≤ MMN ≤ MOUT; len(TIMES)=MOUT; NGO=1 en sets intermedios
  // y 0 en el último; MSUB apunta al último paso del set previo (aviso).
  sets.forEach((s, i) => {
    const mmn  = s.MMN  ?? 0;
    const mout = s.MOUT ?? 0;
    const ngo  = s.NGO  ?? 0;
    const msub = s.MSUB ?? 0;
    const nt   = (s.TIMES || []).length;
    if (mout < 1 || mout > 10)
      err(t('val.v25a').replace('{s}', i + 1).replace('{mout}', mout));
    if (mmn < 0 || mmn > mout)
      err(t('val.v25b').replace('{s}', i + 1).replace('{mmn}', mmn).replace('{mout}', mout));
    if (nt !== mout)
      err(t('val.v25c').replace('{s}', i + 1).replace('{mout}', mout).replace('{got}', nt));
    const isLast = i === sets.length - 1;
    if (isLast && ngo !== 0)
      err(t('val.v25d').replace('{s}', i + 1));
    if (!isLast && ngo === 0)
      err(t('val.v25e').replace('{s}', i + 1));
    if (i > 0 && msub !== (sets[i - 1].MOUT ?? 0))
      warn(t('val.v25f').replace('{s}', i + 1).replace('{msub}', msub)
                        .replace('{prev}', sets[i - 1].MOUT ?? 0));
  });

  return { errors, warnings };
}

// ---------------------------------------------------------------------------
// showValidationModal — display validation results in the modal
// ---------------------------------------------------------------------------

let _validationProceedCb = null;

/**
 * Populate and show the validation modal.
 * @param {{ errors:{msg:string}[], warnings:{msg:string}[] }} result
 * @param {Function|null} onProceed  Called when "Proceed anyway" is clicked
 *                                   (only shown when errors=0, warnings>0).
 */
function showValidationModal(result, onProceed = null) {
  const { errors, warnings } = result;
  const body = document.getElementById('validation-modal-body');
  const proceedBtn = document.getElementById('validation-proceed-btn');

  let html = '';
  if (errors.length === 0 && warnings.length === 0) {
    html = `<div class="alert alert-success mb-0">
      <i class="bi bi-check-circle-fill me-2"></i>${t('val.ok')}
    </div>`;
  } else {
    if (errors.length > 0) {
      const items = errors.map(e => `<li class="mb-1">${e.msg}</li>`).join('');
      html += `<div class="alert alert-danger mb-3">
        <strong><i class="bi bi-x-circle-fill me-1"></i>
          ${t('val.errors_title')} (${errors.length})
        </strong>
        <ul class="mb-0 mt-2 ps-3 small">${items}</ul>
      </div>`;
    }
    if (warnings.length > 0) {
      const items = warnings.map(w => `<li class="mb-1">${w.msg}</li>`).join('');
      html += `<div class="alert alert-warning mb-0">
        <strong><i class="bi bi-exclamation-triangle-fill me-1"></i>
          ${t('val.warn_title')} (${warnings.length})
        </strong>
        <ul class="mb-0 mt-2 ps-3 small">${items}</ul>
      </div>`;
    }
  }

  if (body) body.innerHTML = html;

  // Show "Proceed anyway" only when there are warnings but no errors
  const canProceed = errors.length === 0 && warnings.length > 0 && onProceed != null;
  if (proceedBtn) proceedBtn.classList.toggle('d-none', !canProceed);
  _validationProceedCb = canProceed ? onProceed : null;

  validationModal.show();
}

function populateBlocks78(b78) {
  const preview = document.getElementById('b78-code-preview');
  if (!preview) return;
  if (!b78?.sets?.length) { preview.value = ''; return; }
  preview.value = serializeBlocks78Sets(b78.sets);
  if (b78.sets[0]) setVal('b78-iunit', b78.sets[0].IUNIT ?? 3);
  _tryPopulateGeneratorFromTimes(b78);
}

function _tryPopulateGeneratorFromTimes(b78) {
  if (!b78?.times?.length) return;
  document.getElementById('b78-irr-tbody').innerHTML  = '';
  document.getElementById('b78-cool-tbody').innerHTML = '';
  const irrTimes  = b78.times.filter(([, t]) => t === 1).map(([v]) => v);
  const coolTimes = b78.times.filter(([, t]) => t === 0).map(([v]) => v);
  if (irrTimes.length  > 0) addB78PhaseRow('irr',  irrTimes[irrTimes.length - 1],   Math.min(irrTimes.length,  10));
  if (coolTimes.length > 0) addB78PhaseRow('cool', coolTimes[coolTimes.length - 1],  Math.min(coolTimes.length, 10));
}

function collectBlocks78() {
  return appState.data?.blocks78 ?? null;
}

// ---------------------------------------------------------------------------
// Block #11 — Run control, response functions, temporal structure
// ---------------------------------------------------------------------------

function updateB11Conditional() {
  const idose = getInt('b11-IDOSE');
  const nvfl  = getInt('b11-NVFL');
  const nopul = getInt('b11-NOPUL');
  const card2 = document.getElementById('b11-card2');
  const card7 = document.getElementById('b11-card7');
  const card8 = document.getElementById('b11-card8');
  if (card2) card2.classList.toggle('d-none', idose !== 1);
  if (card7) card7.classList.toggle('d-none', nvfl  !== 1);
  if (card8) card8.classList.toggle('d-none', nopul === 0);
}

function populateBlock11(b) {
  if (!b) return;
  ['IWP','IMTX','IWDR','IDOSE','IPHCUT','IDHEAT','IOFFSD','ICEDE','INEMISS','IDAMAGE']
    .forEach(k => setVal(`b11-${k}`, b[k] ?? 0));
  const dose = b.dose_output || {};
  ['PH','BREM','TOT','RHOR'].forEach(k => setVal(`b11-dose-${k}`, dose[k] ?? 0));
  ['NOPUL','NTSEQ','NOTTS','NVFL'].forEach(k => setVal(`b11-${k}`, b[k] ?? 0));
  setVal('b11-FVAR',  b.FVAR  ? b.FVAR.join('  ') : '');
  setVal('b11-NMULT', b.NMULT ?? 0);
  updateB11Conditional();
}

function collectBlock11() {
  const b = {};
  ['IWP','IMTX','IWDR','IDOSE','IPHCUT','IDHEAT','IOFFSD','ICEDE','INEMISS','IDAMAGE']
    .forEach(k => { b[k] = getInt(`b11-${k}`); });
  b.dose_output = getInt('b11-IDOSE') === 1
    ? { PH: getInt('b11-dose-PH'), BREM: getInt('b11-dose-BREM'),
        TOT: getInt('b11-dose-TOT'), RHOR: getInt('b11-dose-RHOR') }
    : null;
  // Cards 3-5 (IOFFSD) — preserve from loaded data, not editable in this UI
  b.DISTAN = appState.data?.block11?.DISTAN ?? null;
  b.PODE   = appState.data?.block11?.PODE   ?? null;
  b.ILIFR  = appState.data?.block11?.ILIFR  ?? null;
  b.liberation_fracs = appState.data?.block11?.liberation_fracs ?? null;
  b.NOPUL = getInt('b11-NOPUL');
  b.NTSEQ = getInt('b11-NTSEQ');
  b.NOTTS = getInt('b11-NOTTS');
  b.NVFL  = getInt('b11-NVFL');
  b.FVAR  = b.NVFL  === 1 ? parseFloatArray(getVal('b11-FVAR'))  : null;
  b.NMULT = b.NOPUL !== 0 ? getInt('b11-NMULT') : null;
  return b;
}

// ---------------------------------------------------------------------------
// Block #13 — Output control
// ---------------------------------------------------------------------------

function updateB13Conditional() {
  const card2 = document.getElementById('b13-card2');
  if (card2) card2.classList.toggle('d-none', getInt('b13-NCYO') === 0);
}

function populateBlock13(b) {
  if (!b) return;
  setVal('b13-NCYO', b.NCYO ?? 0);
  setVal('b13-IFSO', b.IFSO ?? 0);
  setVal('b13-ICYO', b.ICYO ? b.ICYO.join(' ') : '');
  setVal('b13-ITSO', b.ITSO ? b.ITSO.join(' ') : '');
  updateB13Conditional();
}

function collectBlock13() {
  const ncyo = getInt('b13-NCYO');
  const icyo = parseIntArray(getVal('b13-ICYO'));
  return {
    NCYO: ncyo,
    IFSO: getInt('b13-IFSO'),
    ICYO: ncyo > 0 && icyo.length > 0 ? icyo : null,
    ITSO: parseIntArray(getVal('b13-ITSO')),
  };
}

// ---------------------------------------------------------------------------
// Block #14 — Uncertainty analysis (IUNC = 1)
// ---------------------------------------------------------------------------

/** Enable or disable the Análisis de Incertidumbres section based on IUNC. */
function updateIUNCSection() {
  const active = getInt('b1-IUNC') === 1;

  // Tab button
  const tabBtn = document.getElementById('tab-uncertainties-btn');
  if (tabBtn) {
    tabBtn.disabled = !active;
    tabBtn.classList.toggle('disabled', !active);
    tabBtn.title = active ? '' : 'Requiere IUNC = 1 (Block #1)';
  }

  // Dropdown item
  const navLink = document.getElementById('nav-uncertainties-link');
  if (navLink) {
    navLink.classList.toggle('disabled', !active);
    navLink.title = active ? '' : 'Requiere IUNC = 1 (Block #1)';
  }

  // If the section is currently shown but IUNC was switched off, go back to general
  if (!active) {
    const pane = document.getElementById('sec-uncertainties');
    if (pane && pane.classList.contains('active')) {
      document.getElementById('tab-general-btn')?.click();
    }
  }
}

function updateB14Conditional() {
  const card2 = document.getElementById('b14-card2');
  if (card2) card2.classList.toggle('d-none', getInt('b14-NCYU') === 0);
}

function populateBlock14(b) {
  if (!b) {
    ['NMOHI','NTIMES','NCYU','NNUCU'].forEach(k => setVal(`b14-${k}`, 0));
    setVal('b14-IFSU',   0);
    setVal('b14-ICYU',   '');
    setVal('b14-ITSU',   '');
    setVal('b14-ITIMEU', '');
    setVal('b14-INUCU',  '');
    updateB14Conditional();
    return;
  }
  setVal('b14-NMOHI',  b.NMOHI  ?? 0);
  setVal('b14-NTIMES', b.NTIMES ?? 0);
  setVal('b14-NCYU',   b.NCYU   ?? 0);
  setVal('b14-IFSU',   b.IFSU   ?? 0);
  setVal('b14-NNUCU',  b.NNUCU  ?? 0);
  setVal('b14-ICYU',   b.ICYU         ? b.ICYU.join(' ')  : '');
  setVal('b14-ITSU',   b.ITSU         ? b.ITSU.join(' ')  : '');
  setVal('b14-ITIMEU', b.time_indices ? b.time_indices.map(row => row.join(' ')).join('\n') : '');
  setVal('b14-INUCU',  b.INUCU        ? b.INUCU.join(' ') : '');
  updateB14Conditional();
}

function collectBlock14() {
  if (getInt('b1-IUNC') !== 1) return null;
  const ncyu = getInt('b14-NCYU');
  const icyu = parseIntArray(getVal('b14-ICYU'));
  const itsu = parseIntArray(getVal('b14-ITSU'));
  const itimeuLines = getVal('b14-ITIMEU').trim().split(/\n+/).filter(l => l.trim() !== '');
  const time_indices = itimeuLines.map(l => parseIntArray(l));
  return {
    NMOHI:        getInt('b14-NMOHI'),
    NTIMES:       getInt('b14-NTIMES'),
    NCYU:         ncyu,
    IFSU:         getInt('b14-IFSU'),
    NNUCU:        getInt('b14-NNUCU'),
    ICYU:         ncyu > 0 && icyu.length > 0 ? icyu : null,
    ITSU:         itsu,
    time_indices: time_indices,
    INUCU:        parseIntArray(getVal('b14-INUCU')),
  };
}

// ---------------------------------------------------------------------------
// Block comments — one free-text field per block
// ---------------------------------------------------------------------------

const _COMMENT_KEYS = ['block1','block2','block3','block4','block5','block6',
                       'blocks78','block9','block10','block11','block13','block14'];

function collectComments() {
  const c = {};
  _COMMENT_KEYS.forEach(k => { c[k] = getVal(`cmt-${k}`); });
  return c;
}

function populateComments(comments) {
  const c = comments || {};
  _COMMENT_KEYS.forEach(k => setVal(`cmt-${k}`, c[k] ?? ''));
}

// ---------------------------------------------------------------------------
// export_to_acab — generate formatted inp.5 string and show in preview modal
// ---------------------------------------------------------------------------

async function exportToAcab() {
  if (!appState.data) appState.data = {};
  collectAll(appState.data);

  // Validate — block on errors, warn but allow proceed
  const valResult = validateAll();
  if (valResult.errors.length > 0) {
    showValidationModal(valResult, null);
    return;
  }
  if (valResult.warnings.length > 0) {
    showValidationModal(valResult, () => _doPreview());
    return;
  }

  await _doPreview();
}

async function _doPreview() {
  const loadingEl = document.getElementById('preview-loading');
  const contentEl = document.getElementById('preview-content');
  const linesEl   = document.getElementById('preview-lines');

  loadingEl.classList.remove('d-none');
  loadingEl.classList.add('d-flex');
  contentEl.value = '';
  linesEl.textContent = '';
  previewModal.show();

  try {
    const res  = await fetch('/api/preview', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ data: appState.data }),
    });
    const json = await res.json();
    if (!res.ok || !json.ok) throw new Error(json.error || 'Error al generar la vista previa.');

    contentEl.value = json.content;
    const lines = json.content.split('\n').length;
    linesEl.textContent = t('toast.lines').replace('{n}', lines);
  } catch (err) {
    contentEl.value = `ERROR: ${err.message}`;
    showToast(err.message, 'danger');
  } finally {
    loadingEl.classList.add('d-none');
    loadingEl.classList.remove('d-flex');
  }
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

/** Set the value of a form element by id. */
function setVal(id, value) {
  const el = document.getElementById(id);
  if (el) el.value = (value !== null && value !== undefined) ? value : '';
}

/** Read the string value of a form element. */
function getVal(id) {
  const el = document.getElementById(id);
  return el ? el.value : '';
}

/** Read and parse an integer from a form element. */
function getInt(id, fallback = 0) {
  const v = parseInt(getVal(id), 10);
  return isNaN(v) ? fallback : v;
}

/**
 * Format a number in scientific notation compatible with ACAB.
 * Falls back to *fallback* if *v* is null/undefined/NaN.
 */
function fmtSci(v, fallback) {
  const n = (v !== null && v !== undefined) ? Number(v) : fallback;
  if (isNaN(n)) return fallback.toExponential(6).toUpperCase().replace('E+', 'E+').replace('E-', 'E-');
  return n.toExponential(6).toUpperCase();
}

/**
 * Update the navbar status indicator.
 * @param {string}  filename
 * @param {boolean} dirty    — unsaved changes
 * @param {boolean} loading  — show spinner
 */
function setStatus(filename, dirty, loading = false) {
  const el = document.getElementById('file-status');
  if (!el) return;
  if (loading) {
    el.innerHTML = `<span class="spinner-border spinner-border-sm text-light me-1"></span>
                    ${t('status.loading').replace(/…$/, '')} ${filename}…`;
  } else if (dirty) {
    el.innerHTML = `<i class="bi bi-circle-fill text-warning me-1"></i>${filename}
                    <span class="badge bg-warning text-dark ms-1">${t('status.modified')}</span>`;
  } else {
    el.innerHTML = `<i class="bi bi-circle-fill text-success me-1"></i>${filename}`;
  }
}

/**
 * Show a Bootstrap toast notification.
 * @param {string} message
 * @param {'success'|'danger'|'warning'|'info'} type
 */
function showToast(message, type = 'info', delay = 3500) {
  const toastEl = document.getElementById('appToast');
  const bodyEl  = document.getElementById('toast-body');
  if (!toastEl || !bodyEl) return;

  toastEl.classList.remove(
    'text-bg-success', 'text-bg-danger', 'text-bg-warning', 'text-bg-info');
  toastEl.classList.add(`text-bg-${type}`);

  if (message.includes('<')) {
    bodyEl.innerHTML = message;
  } else {
    bodyEl.textContent = message;
  }

  // Re-create instance to apply a custom delay if needed
  const existing = bootstrap.Toast.getInstance(toastEl);
  if (existing) existing.dispose();
  appToast = new bootstrap.Toast(toastEl, { delay });
  appToast.show();
}

// ---------------------------------------------------------------------------
// Code search — locate any inp.5 code in the form
// ---------------------------------------------------------------------------

function initCodeSearch() {
  const input    = document.getElementById('code-search-input');
  const dropdown = document.getElementById('code-search-dropdown');
  if (!input || !dropdown) return;

  let activeIdx = -1;

  function renderDropdown(query) {
    activeIdx = -1;
    if (!query) { dropdown.style.display = 'none'; return; }

    const q = query.toUpperCase();
    const starts   = ACAB_CODE_INDEX.filter(e => e.code.startsWith(q));
    const contains = ACAB_CODE_INDEX.filter(e => !e.code.startsWith(q) && e.code.includes(q));
    const results  = [...starts, ...contains].slice(0, 10);

    if (results.length === 0) {
      dropdown.innerHTML = `
        <li class="dropdown-item text-danger small py-2 pe-none">
          <i class="bi bi-question-circle me-1"></i>${t('search.unknown').replace('{code}', query)}
        </li>`;
    } else {
      dropdown.innerHTML = results.map((entry, i) => {
        const tabLabel = t(entry.tabKey);
        const highlighted = entry.code.replace(
          new RegExp(`(${q})`, 'i'),
          '<strong>$1</strong>'
        );
        return `<li>
          <button class="dropdown-item small py-2 search-result-item" data-idx="${i}">
            <span class="font-monospace">${highlighted}</span>
            <span class="text-muted ms-2">${entry.blockLabel}</span>
            <br>
            <small class="text-secondary"><i class="bi bi-folder2 me-1"></i>${tabLabel}</small>
          </button>
        </li>`;
      }).join('');

      dropdown.querySelectorAll('.search-result-item').forEach((btn, i) => {
        btn.addEventListener('mousedown', e => {
          e.preventDefault();
          navigateToCode(results[i]);
          input.value = '';
          dropdown.style.display = 'none';
        });
      });
    }

    dropdown.style.display = 'block';
  }

  input.addEventListener('input', () => renderDropdown(input.value.trim()));

  input.addEventListener('keydown', e => {
    const items = dropdown.querySelectorAll('.search-result-item');
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIdx = Math.min(activeIdx + 1, items.length - 1);
      items.forEach((el, i) => el.classList.toggle('active', i === activeIdx));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIdx = Math.max(activeIdx - 1, 0);
      items.forEach((el, i) => el.classList.toggle('active', i === activeIdx));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const idx = activeIdx >= 0 ? activeIdx : 0;
      if (items[idx]) items[idx].dispatchEvent(new MouseEvent('mousedown'));
    } else if (e.key === 'Escape') {
      dropdown.style.display = 'none';
      input.blur();
    }
  });

  input.addEventListener('blur', () => {
    setTimeout(() => { dropdown.style.display = 'none'; }, 150);
  });

  input.addEventListener('focus', () => {
    if (input.value.trim()) renderDropdown(input.value.trim());
  });
}

/**
 * Navigate to the tab + block where a code lives, then scroll to and
 * briefly highlight its form element.
 */
function navigateToCode(entry) {
  const tabBtn  = document.getElementById(entry.tabBtn);
  const pillBtn = entry.pillBtn ? document.getElementById(entry.pillBtn) : null;

  if (tabBtn && !tabBtn.classList.contains('disabled')) {
    tabBtn.click();
  }

  const scrollAndHighlight = () => {
    const el = document.getElementById(entry.elementId);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.classList.add('code-search-highlight');
    el.addEventListener('animationend', () => el.classList.remove('code-search-highlight'),
      { once: true });
  };

  if (pillBtn) {
    setTimeout(() => {
      pillBtn.click();
      setTimeout(scrollAndHighlight, 80);
    }, 80);
  } else {
    setTimeout(scrollAndHighlight, 120);
  }
}
