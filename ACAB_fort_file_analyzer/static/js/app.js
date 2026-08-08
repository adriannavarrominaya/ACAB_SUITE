/* ─────────────────────────────────────────────────────────────────────────
   ACAB Fort File Analyzer — Frontend JavaScript
   Uses Plotly.js (loaded via CDN) for all interactive charts.
   ───────────────────────────────────────────────────────────────────────── */
'use strict';

// ─────────────────────────────────────────────────────────────────────────────
// i18n engine  (mirrors the COLLAPS configurator; es default)
// ─────────────────────────────────────────────────────────────────────────────
let _i18n = {};
let _lang = localStorage.getItem('fort-analyzer-lang') || 'es';

/**
 * Translate a dotted key. Optional params object replaces {name} placeholders.
 * Returns the key itself if no translation is found (visible during dev).
 */
function t(key, params) {
  let val = key.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : null), _i18n);
  if (val === null || val === undefined) return key;
  if (params) {
    for (const p in params) val = String(val).split(`{${p}}`).join(params[p]);
  }
  return val;
}

async function loadLang(lang) {
  try {
    const res = await fetch(`/static/i18n/${lang}.json`);
    _i18n = await res.json();
  } catch (_) { _i18n = {}; }
  _lang = lang;
  localStorage.setItem('fort-analyzer-lang', lang);
  document.documentElement.lang = lang;
  applyLang();
  const flagEl = document.getElementById('lang-flag');
  const nameEl = document.getElementById('lang-name');
  if (flagEl) flagEl.className = `lang-flag lang-flag-${lang}`;
  if (nameEl) nameEl.textContent = lang === 'es' ? 'Español' : 'English';
  // Re-render any already-rendered dynamic content so it picks up the new language
  refreshDynamicUI();
}

function applyLang() {
  // Plain-text nodes (preserve sibling icons)
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const val = t(el.dataset.i18n);
    if (!val || val === el.dataset.i18n) return;
    const textNodes = [...el.childNodes]
      .filter(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim());
    if (textNodes.length) {
      textNodes.forEach(n => { n.textContent = n.textContent.replace(n.textContent.trim(), val); });
    } else {
      el.textContent = val;
    }
  });
  // Rich-text nodes (values may contain HTML markup)
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const val = t(el.dataset.i18nHtml);
    if (val && val !== el.dataset.i18nHtml) el.innerHTML = val;
  });
  // Placeholders
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    const val = t(el.dataset.i18nPh);
    if (val && val !== el.dataset.i18nPh) el.placeholder = val;
  });
  // Titles / tooltips
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const val = t(el.dataset.i18nTitle);
    if (val && val !== el.dataset.i18nTitle) el.title = val;
  });
  // ARIA labels
  document.querySelectorAll('[data-i18n-aria]').forEach(el => {
    const val = t(el.dataset.i18nAria);
    if (val && val !== el.dataset.i18nAria) el.setAttribute('aria-label', val);
  });
}

/** Re-render dynamic (JS-generated) UI after a language switch. */
function refreshDynamicUI() {
  if (!_state.analysisData) return;
  renderOverview(_state.analysisData);
  renderSimList(Object.keys(_state.analysisData.simulations), _state.analysisData.simulations);
  if (_state.chartsRendered) renderCharts();
  if (_state.selectedIsotopo && _state.isotopoReport) {
    renderIsotopoReport();
    renderIsotopoSummaryCard(_state.selectedIsotopo, _state.isotopoReport.informe);
    if (_state.tablesRendered) renderTables();
    if (_state.optimRendered) renderOptimizacion();
  }
  if (_state.espectroRendered) renderEspectroGamma();
  if (_state.chainsPanelBuilt) {
    renderChainsPanel();
    if (_state.chainsData) _renderChainsResults();
  }
}

/** Translate the backend phase string ("irradiación"/"enfriamiento"/"n/a"). */
function phaseLabel(fase) {
  if (fase === 'irradiación') return t('phase.irr');
  if (fase === 'enfriamiento') return t('phase.cool');
  return t('phase.na');
}

// ─────────────────────────────────────────────────────────────────────────────
// Global state  (F1)
// ─────────────────────────────────────────────────────────────────────────────
const _state = {
  analysisData:    null,
  folder:          null,   // normalised folder path analysed (sent to isotopo_report)
  selectedIsotopo: null,   // isotope key chosen by the user (e.g. "I131")
  isotopoReport:   null,   // last response from /api/isotopo_report
  showIrr:         false,
  chartFilter:     'all',
  chartsRendered:  false,
  isotopoRendered: false,  // Tab 3 rendered for current selectedIsotopo
  tablesRendered:  false,  // Tab 4 rendered for current selectedIsotopo
  refSeries:       [],     // Fase 4: series de referencia importadas (appState, no disco)
  refImportDraft:  null,   // CSV recién parseado, pendiente de confirmar en el diálogo
  refMetricsTargetSim: null, // Fase 6: simulación objetivo elegida en el desplegable de métricas (null = primera)
  optimRendered:   false,  // Tab 5 rendered for current selectedIsotopo (Fase 5 opcional, barrido)
  optimYVar:       'a_pico', // variable Y elegida: 'a_pico' | 't_pico' | 'pureza' | 'rendimiento'
  optimXParam:     null,     // clave de parámetro elegida para el eje X (null = por defecto)
  figurasOriginal: null,   // copia profunda de data.figuras tal como se cargó (yaml/auto/upload); null si no hay YAML de partida
  yamlConfigLoaded: null,  // dict YAML completo tal como se cargó (para el round-trip al guardar/descargar, RUNBOOK_figuras_yaml.md)
  // B1 del BACKLOG — pestaña "Espectro gamma": el espectro se pide al servidor
  // bajo demanda (POST /api/espectro_gamma) por simulación+instante, no viaja
  // entero en /api/analyze (podría ser enorme con un PHOTON.dat completo).
  espectroRendered:    false,
  espectroSim:         null,   // simulación elegida (null = primera)
  espectroT:           null,   // instante de enfriamiento elegido [h] (null = último timestep)
  espectroPhotonPath:  '',     // override manual de la ruta de PHOTON.dat
  espectroData:        null,  // última respuesta de /api/espectro_gamma
  espectroFiltros:     { eMinKeV: null, eMaxKeV: null, tasaMin: null }, // sobrevive a rebuilds (cambio de idioma, sim, t)
  espectroAutoLoadDone: false, // B1b: intento único de recarga desde la ruta recordada en localStorage por análisis
  espectroTasaMinTouched: false, // B1b: false = el umbral de tasa mínima se recalcula solo (max/1e6); true = manda el valor del usuario

  // F9 del BACKLOG, Fase 4 — pestaña "Análisis de cadenas": independiente de
  // analysisData/folder de arriba, carga su PROPIA carpeta (chains_manifest.json).
  chainsPanelBuilt: false, // el esqueleto del panel (input de carpeta, etc.) solo se construye una vez
  chainsRoot:       null,  // carpeta del análisis de cadenas ya cargada
  chainsData:       null,  // última respuesta de /api/chains_report
  chainsTManual:    null,  // t_h elegido a mano en el selector (null = usar el t_pico por defecto del servidor)
  chainsSelectedRow: null, // índice de la fila de tabla2 elegida para el diagrama (null = ninguna)
};

// Simulation colour palette (up to 10 simulations)
const PALETTE = [
  '#1565c0', '#e65100', '#2e7d32', '#c62828',
  '#6a1b9a', '#4e342e', '#ad1457', '#00695c',
  '#827717', '#1a237e',
];

// Full symbol → atomic number table (uppercase keys, as they appear in fort.6).
// Covers the whole periodic table so element filtering and the report Z field
// work with any target material, not just the Te/Xe/I analyses.
const Z_BY_ELEM = {
  H: 1, HE: 2, LI: 3, BE: 4, B: 5, C: 6, N: 7, O: 8, F: 9, NE: 10,
  NA: 11, MG: 12, AL: 13, SI: 14, P: 15, S: 16, CL: 17, AR: 18, K: 19, CA: 20,
  SC: 21, TI: 22, V: 23, CR: 24, MN: 25, FE: 26, CO: 27, NI: 28, CU: 29, ZN: 30,
  GA: 31, GE: 32, AS: 33, SE: 34, BR: 35, KR: 36, RB: 37, SR: 38, Y: 39, ZR: 40,
  NB: 41, MO: 42, TC: 43, RU: 44, RH: 45, PD: 46, AG: 47, CD: 48, IN: 49, SN: 50,
  SB: 51, TE: 52, I: 53, XE: 54, CS: 55, BA: 56, LA: 57, CE: 58, PR: 59, ND: 60,
  PM: 61, SM: 62, EU: 63, GD: 64, TB: 65, DY: 66, HO: 67, ER: 68, TM: 69, YB: 70,
  LU: 71, HF: 72, TA: 73, W: 74, RE: 75, OS: 76, IR: 77, PT: 78, AU: 79, HG: 80,
  TL: 81, PB: 82, BI: 83, PO: 84, AT: 85, RN: 86, FR: 87, RA: 88, AC: 89, TH: 90,
  PA: 91, U: 92, NP: 93, PU: 94, AM: 95, CM: 96, BK: 97, CF: 98, ES: 99, FM: 100,
  MD: 101, NO: 102, LR: 103, RF: 104, DB: 105, SG: 106, BH: 107, HS: 108, MT: 109, DS: 110,
  RG: 111, CN: 112, NH: 113, FL: 114, MC: 115, LV: 116, TS: 117, OG: 118,
};

// ─────────────────────────────────────────────────────────────────────────────
// Activity units (F2)
// Conversion is a per-simulation factor applied in the FRONTEND; the cache and
// all internal data stay in Bq/cm³. Pure maths live in static/js/units.js.
// ─────────────────────────────────────────────────────────────────────────────
const UNIT_KEY = 'fort-analyzer-unit';
const VOLUME_KEY = 'fort-analyzer-volume';
// B1b del BACKLOG — última ruta de PHOTON.dat cargada con éxito (patrón U2:
// recordar la última carpeta/fichero elegido, precargarlo la próxima vez).
const PHOTON_PATH_KEY = 'fort-analyzer-photon-path';

function activeUnit() {
  const u = localStorage.getItem(UNIT_KEY) || 'bqcm3';
  return ACABUnits.isKnownUnit(u) ? u : 'bqcm3';
}
function activeVolume() {
  const v = parseFloat(localStorage.getItem(VOLUME_KEY));
  return (isFinite(v) && v > 0) ? v : 1;
}
/** i18n unit token for axes / table headers (Bq/cm³, MBq/g, MBq, mCi). */
function unitLabel() { return t('units.u_' + activeUnit()); }
/** Conversion opts for a simulation: its own density + the global volume. */
function unitOpts(sim) {
  return { density: sim ? sim.densidad_g_cm3 : null, volume: activeVolume() };
}
/** Multiplicative factor for a sim under the active unit; null if not convertible. */
function convFactor(sim) {
  return ACABUnits.unitFactor(activeUnit(), unitOpts(sim));
}
/** Convert a Bq/cm³ value for a sim to the active unit; null if not convertible. */
function conv(value, sim) {
  return ACABUnits.convertUnits(value, activeUnit(), unitOpts(sim));
}
/** Format a Bq/cm³ value into the active unit; '—' if not convertible. */
function fmtA(value, sim, digits = 4) {
  const c = conv(value, sim);
  return (c === null || c === undefined) ? '—' : c.toExponential(digits);
}
/** Names of analysed simulations lacking a CONCENTRATIONS(GRAM) density. */
function simsMissingDensity() {
  const sims = _state.analysisData ? _state.analysisData.simulations : null;
  if (!sims) return [];
  return Object.keys(sims).filter(name => sims[name].densidad_g_cm3 == null);
}

/**
 * Do ALL analysed simulations carry a density? A mass sweep has one fort.6 (and
 * one CONCENTRATIONS(GRAM)/density) per simulation, so MBq/g requires every sim
 * to be convertible — otherwise its rows/curve would silently disappear from
 * the comparison instead of being shown consistently. Gates the MBq/g option.
 */
function allDensity() {
  const sims = _state.analysisData ? _state.analysisData.simulations : null;
  return !!sims && simsMissingDensity().length === 0;
}

/** Tooltip/note for why MBq/g is disabled: generic if no sim has density at
 * all, naming the specific simulation(s) missing it otherwise. */
function mbqgDisabledMsg() {
  const sims = _state.analysisData ? _state.analysisData.simulations : {};
  const missing = simsMissingDensity();
  if (missing.length === Object.keys(sims).length) return t('units.mbqg_disabled');
  return missing.map(name => t('units.no_density_series', { sim: name })).join(' ');
}

/** Reflect unit state in the controls (option enabled/disabled, volume field). */
function syncUnitControls() {
  const sel = document.getElementById('unit-select');
  if (!sel) return;
  const analysed = !!_state.analysisData;
  const hasDensity = allDensity();

  const mbqgOpt = sel.querySelector('option[value="mbqg"]');
  if (mbqgOpt) {
    mbqgOpt.disabled = analysed && !hasDensity;
    mbqgOpt.title = mbqgOpt.disabled ? mbqgDisabledMsg() : '';
  }

  // If MBq/g was active but some sim in the sweep lacks density, fall back to
  // Bq/cm³ (each sim has its own density; a mixed sweep can't convert consistently).
  let unit = activeUnit();
  if (unit === 'mbqg' && analysed && !hasDensity) {
    unit = 'bqcm3';
    localStorage.setItem(UNIT_KEY, unit);
  }
  sel.value = unit;

  const needsVol = ACABUnits.unitRequires(unit) === 'volume';
  document.getElementById('unit-volume-wrap').classList.toggle('d-none', !needsVol);

  const note = document.getElementById('unit-note');
  if (note) {
    const show = analysed && !hasDensity;
    note.textContent = show ? mbqgDisabledMsg() : '';
    note.classList.toggle('d-none', !show);
  }
}

/** Change the active unit: persist, refresh controls, re-render dynamic UI. */
function setActiveUnit(u) {
  localStorage.setItem(UNIT_KEY, ACABUnits.isKnownUnit(u) ? u : 'bqcm3');
  syncUnitControls();
  refreshDynamicUI();
}

// ─────────────────────────────────────────────────────────────────────────────
// CSV export (F3) — everything client-side; pure maths in static/js/export_utils.js
// ─────────────────────────────────────────────────────────────────────────────
const CSV_KEY = 'fort-analyzer-csv';

function activeCsv() {
  return localStorage.getItem(CSV_KEY) === 'intl' ? 'intl' : 'es';
}
/** Filename-safe slug of the active unit label (MBq/g → MBq_g). */
function unitSlug() { return ACABExport.slug(unitLabel()); }
/** Filename-safe slug of the analysed folder's basename. */
function folderSlug() {
  const base = (_state.folder || '').split(/[\\/]/).filter(Boolean).pop() || 'export';
  return ACABExport.slug(base);
}
/** Commented metadata block prepended to every CSV (# folder, isotope, unit, date). */
function csvMeta(isoOrTitle) {
  return [
    `# ${t('export.meta_folder')}: ${_state.folder || ''}`,
    `# ${t('export.meta_iso')}: ${isoOrTitle || ''}`,
    `# ${t('export.meta_unit')}: ${unitLabel()}`,
    `# ${t('export.meta_date')}: ${new Date().toISOString()}`,
  ].join('\r\n');
}
/** Assemble metadata + table into one CSV string and trigger the download. */
function emitCSV(filename, isoOrTitle, rows, headers, extraMeta) {
  const opts = ACABExport.preset(activeCsv());
  const meta = csvMeta(isoOrTitle) + (extraMeta ? '\r\n' + extraMeta : '');
  const csv = meta + '\r\n' + ACABExport.toCSV(rows, headers, opts);
  ACABExport.download(filename, csv);
}

/**
 * Export a chart figure: read the traces already plotted (values are in the
 * active unit) and align them on the union of their time points.
 */
function exportChartCSV(divId, cfg, figIndex) {
  const div = document.getElementById(divId);
  const traces = (div && div.data) ? div.data : [];
  if (!traces.length) return;

  // Union of all x (time) values across traces, sorted.
  const xset = new Set();
  traces.forEach(tr => (tr.x || []).forEach(v => xset.add(+v)));
  const xs = Array.from(xset).sort((a, b) => a - b);
  const maps = traces.map(tr => {
    const m = new Map();
    const x = tr.x || [], y = tr.y || [];
    for (let i = 0; i < x.length; i++) m.set(+x[i], y[i]);
    return m;
  });
  const headers = ['t [h]', ...traces.map(tr => tr.name)];
  const rows = xs.map(x => [x, ...maps.map(m => (m.has(x) ? m.get(x) : null))]);

  const title = cfg.titulo || t('charts.fig', { n: figIndex });
  emitCSV(`${ACABExport.slug(title)}_series_${unitSlug()}_${folderSlug()}.csv`,
          title, rows, headers);
}

/** Export the isotope report: nuclear properties (commented) + per-sim activity. */
function exportReportCSV() {
  if (!_state.isotopoReport || !_state.analysisData) return;
  const iso  = _state.selectedIsotopo;
  const sims = _state.analysisData.simulations;
  const p    = _state.isotopoReport.informe.nuclear_props || {};

  const elem = (iso.match(/^([A-Z]{1,2})/) || [])[1] || '';
  const Z = Z_BY_ELEM[elem] !== undefined ? Z_BY_ELEM[elem] : '';
  const A = (iso.match(/(\d+)/) || [])[1] || '';
  const props = [
    `# ${t('report.za')}: ${Z} / ${A}`,
    `# ${t('report.halflife')} [s]: ${p.T12_s || ''} | ` +
      `${t('report.lambda')} [1/s]: ${p.lam_s || ''} | ` +
      `${t('report.spec_act')} [Bq/g]: ${p.A_esp || ''}`,
  ].join('\r\n');

  const rows = [];
  Object.entries(sims).forEach(([name, sim]) => {
    const tIrr = sim.t_irr || [], yIrr = sim.datos_irr_Bq[iso] || [];
    for (let i = 0; i < tIrr.length; i++) rows.push([name, t('phase.irr'), tIrr[i], conv(yIrr[i], sim)]);
    const tCool = sim.t_cool || [], yCool = sim.datos_cool[iso] || [];
    for (let i = 0; i < tCool.length; i++) rows.push([name, t('phase.cool'), tCool[i], conv(yCool[i], sim)]);
  });
  const headers = [t('overview.th_sim'), t('report.th_fase'), 't [h]', `A [${unitLabel()}]`];
  emitCSV(`${ACABExport.slug(iso)}_informe_${unitSlug()}_${folderSlug()}.csv`,
          iso, rows, headers, props);
}

/** Export comparison Table 1 (activity of every isotope at the reference peak). */
function exportTable1CSV() {
  const json = _state.isotopoReport;
  if (!json || !_state.analysisData) return;
  const iso  = _state.selectedIsotopo;
  const sims = _state.analysisData.simulations;
  const rows = [];
  Object.entries(json.tabla1).forEach(([name, tbl]) => {
    const sim = sims[name];
    (tbl.rows || []).forEach(r => {
      rows.push([name, `${r.label} (${r.iso})`, r.A != null ? conv(r.A, sim) : null, r.ratio]);
    });
  });
  const headers = [t('overview.th_sim'), t('tables.th_iso'),
                   `A [${unitLabel()}]`, `A/A(${isoLabel(iso)})`];
  emitCSV(`${ACABExport.slug(iso)}_tabla1_${unitSlug()}_${folderSlug()}.csv`,
          iso, rows, headers);
}

/** Export comparison Table 2 (each isotope's own peak + reference activity there). */
function exportTable2CSV() {
  const json = _state.isotopoReport;
  if (!json || !_state.analysisData) return;
  const iso  = _state.selectedIsotopo;
  const sims = _state.analysisData.simulations;
  const rows = [];
  Object.entries(json.tabla2).forEach(([name, tbl]) => {
    const sim = sims[name];
    (tbl.rows || []).forEach(r => {
      rows.push([name, `${r.label} (${r.iso})`,
                 r.A_pico != null ? conv(r.A_pico, sim) : null,
                 r.t_pico,
                 r.A_ref_en != null ? conv(r.A_ref_en, sim) : null]);
    });
  });
  const headers = [t('overview.th_sim'), t('tables.th_iso'),
                   `A_pico [${unitLabel()}]`, 't_pico [h]',
                   `A(${isoLabel(iso)}) [${unitLabel()}]`];
  emitCSV(`${ACABExport.slug(iso)}_tabla2_${unitSlug()}_${folderSlug()}.csv`,
          iso, rows, headers);
}

// ─────────────────────────────────────────────────────────────────────────────
// Initialisation
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  // Load language first so the initial (static) UI is translated
  await loadLang(_lang);

  // Language switcher
  document.querySelectorAll('.lang-item').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      loadLang(a.dataset.lang);
    });
  });

  // Activity unit selector (F2)
  const volInput = document.getElementById('unit-volume');
  volInput.value = localStorage.getItem(VOLUME_KEY) || '1';
  document.getElementById('unit-select').addEventListener('change', e => {
    setActiveUnit(e.target.value);
  });
  volInput.addEventListener('input', () => {
    const v = parseFloat(volInput.value);
    if (isFinite(v) && v > 0) {
      localStorage.setItem(VOLUME_KEY, String(v));
      if (ACABUnits.unitRequires(activeUnit()) === 'volume') refreshDynamicUI();
    }
  });
  syncUnitControls();

  // CSV export format (F3) — only affects downloads, no re-render needed.
  const csvSel = document.getElementById('csv-format');
  csvSel.value = activeCsv();
  csvSel.addEventListener('change', e => {
    localStorage.setItem(CSV_KEY, e.target.value === 'intl' ? 'intl' : 'es');
  });

  // Parameter source toggle
  document.querySelectorAll('input[name="paramSource"]').forEach(r => {
    r.addEventListener('change', () => {
      const isManual = document.getElementById('src-manual').checked;
      document.getElementById('manual-overrides').classList.toggle('d-none', !isManual);
    });
  });

  // Folder browser button — calls server which opens native OS dialog
  document.getElementById('btn-browse-folder').addEventListener('click', async () => {
    const browseBtn  = document.getElementById('btn-browse-folder');
    const analyzeBtn = document.getElementById('btn-analyze');
    const icon = browseBtn.querySelector('i');

    // Disable both buttons so the user can't trigger Analyze while the
    // fetch is in-flight (the OS dialog blocks the server response until
    // the user clicks OK/Cancel — without this, a fast click on Analizar
    // races against the fetch and sees an empty folder input).
    browseBtn.disabled  = true;
    analyzeBtn.disabled = true;
    icon.className = 'bi bi-hourglass-split';

    try {
      const res  = await fetch('/api/browse-folder', { method: 'POST' });
      const json = await res.json();
      if (json.folder) {
        document.getElementById('folder-input').value = json.folder;
      } else if (!json.error) {
        // User cancelled the dialog — no toast needed, just a subtle hint
        showToast(t('toast.no_folder_selected'), 'secondary');
      }
    } catch {
      showToast(t('toast.browse_err'), 'warning');
    } finally {
      browseBtn.disabled  = false;
      analyzeBtn.disabled = false;
      icon.className = 'bi bi-folder2-open';
    }
  });

  // Analyze button
  document.getElementById('btn-analyze').addEventListener('click', doAnalyze);
  document.getElementById('folder-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') doAnalyze();
  });

  // Irradiation toggle
  document.getElementById('toggle-irr').addEventListener('change', e => {
    _state.showIrr = e.target.checked;
    if (_state.analysisData && _state.chartsRendered) {
      renderCharts();
    }
  });

  // Chart filter
  document.getElementById('chart-filter').addEventListener('change', e => {
    _state.chartFilter = e.target.value;
    if (_state.analysisData && _state.chartsRendered) {
      renderCharts();
    }
  });

  // Lazy render tabs on first show  (F8, F9)
  document.getElementById('tab-charts-btn').addEventListener('shown.bs.tab', () => {
    if (!_state.chartsRendered && _state.analysisData) {
      renderCharts();
      _state.chartsRendered = true;
    }
  });

  // Tab 3: show placeholder if no isotope selected yet  (F8)
  document.getElementById('tab-i131-btn').addEventListener('shown.bs.tab', () => {
    if (_state.isotopoReport && !_state.isotopoRendered) {
      renderIsotopoReport();
      _state.isotopoRendered = true;
    } else if (!_state.selectedIsotopo && _state.analysisData) {
      document.getElementById('i131-report-container').innerHTML = `
        <div class="alert alert-info mt-3">
          <i class="bi bi-hand-index me-2"></i>
          ${t('report.placeholder')}
        </div>`;
    }
  });

  // Tab 4: show placeholder if no isotope selected yet  (F9)
  document.getElementById('tab-tables-btn').addEventListener('shown.bs.tab', () => {
    if (_state.isotopoReport && !_state.tablesRendered) {
      renderTables();
      _state.tablesRendered = true;
    } else if (!_state.selectedIsotopo && _state.analysisData) {
      document.getElementById('tables-container').innerHTML = `
        <div class="alert alert-info mt-3">
          <i class="bi bi-hand-index me-2"></i>
          ${t('tables.placeholder')}
        </div>`;
    }
  });

  // Tab 5: sweep optimisation — show placeholder if no isotope selected yet
  // (Fase 5 opcional, RUNBOOK_barrido_parametrico_v2)
  document.getElementById('tab-optim-btn').addEventListener('shown.bs.tab', () => {
    if (_state.isotopoReport && !_state.optimRendered) {
      renderOptimizacion();
      _state.optimRendered = true;
    } else if (!_state.selectedIsotopo && _state.analysisData) {
      document.getElementById('optim-container').innerHTML = `
        <div class="alert alert-info mt-3">
          <i class="bi bi-hand-index me-2"></i>
          ${t('optim.placeholder')}
        </div>`;
    }
  });

  // Tab: gamma emission spectrum (B1 del BACKLOG) — solo depende de la carpeta
  // analizada, no del isótopo seleccionado (a diferencia de Informe/Tablas/Optim).
  document.getElementById('tab-espectro-btn').addEventListener('shown.bs.tab', () => {
    if (_state.analysisData && !_state.espectroRendered) {
      renderEspectroGamma();
      _state.espectroRendered = true;
    }
  });

  // Tab: análisis de cadenas (F9 del BACKLOG) — independiente de
  // analysisData: construye su propio panel de carga la primera vez que se
  // muestra la pestaña, sin esperar a ningún análisis previo.
  document.getElementById('tab-chains-btn').addEventListener('shown.bs.tab', () => {
    if (!_state.chainsPanelBuilt) {
      renderChainsPanel();
      _state.chainsPanelBuilt = true;
    }
  });

  // ── Figure editor (E1–E7) ─────────────────────────────────────────────────
  document.getElementById('btn-edit-figuras').addEventListener('click', openFigurasEditor);
  document.getElementById('btn-figuras-reset').addEventListener('click', resetFigurasToLoaded);
  document.getElementById('btn-figuras-apply').addEventListener('click', applyFigurasChanges);
  document.getElementById('btn-figuras-download').addEventListener('click', downloadFigurasYaml);
  document.getElementById('btn-figuras-save').addEventListener('click', saveFigurasToFolder);

  // ── Selector de fichero YAML de figuras (decisión 4 del runbook) ──────────
  document.getElementById('btn-load-figuras-yaml')
    .addEventListener('click', () => document.getElementById('figuras-yaml-file-input').click());
  document.getElementById('figuras-yaml-file-input').addEventListener('change', async e => {
    const file = e.target.files && e.target.files[0];
    e.target.value = ''; // permite volver a elegir el mismo fichero más tarde
    if (!file) return;
    try {
      const text = await file.text();
      await doAnalyze({ yamlContentOverride: text });
    } catch (err) {
      showToast(t('toast.net_err', { msg: err.message }), 'danger');
    }
  });

  // Single persistent event delegation on the modal body — handles dynamic content
  document.getElementById('figuras-editor-body').addEventListener('click', e => {
    const body = document.getElementById('figuras-editor-body');

    if (e.target.closest('.btn-remove-fig')) {
      e.target.closest('.figura-card').remove();
      body.querySelectorAll('.figura-card').forEach((c, i) => {
        const h = c.querySelector('.fig-num');
        if (h) h.textContent = t('figeditor.fig', { n: i + 1 });
      });
      return;
    }

    if (e.target.closest('.btn-remove-series')) {
      e.target.closest('.series-row').remove();
      return;
    }

    if (e.target.closest('.btn-add-series')) {
      const seriesList = e.target.closest('.card-body').querySelector('.series-list');
      const div = document.createElement('div');
      div.innerHTML = _makeSeriesRow('', '');
      seriesList.appendChild(div.firstElementChild);
      return;
    }

    if (e.target.closest('#btn-add-figura')) {
      const addBtn = document.getElementById('btn-add-figura');
      const count  = body.querySelectorAll('.figura-card').length;
      const div    = document.createElement('div');
      div.innerHTML = _makeFigCard({ titulo: '', series: [{ iso: '', label: '' }] }, count + 1);
      body.insertBefore(div.firstElementChild, addBtn);
      return;
    }
  });

  // ── Import de datos de referencia (Fase 4) ────────────────────────────────
  document.getElementById('refdata-file-input').addEventListener('change', async e => {
    const file = e.target.files && e.target.files[0];
    e.target.value = ''; // permite volver a elegir el mismo fichero más tarde
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = ACABRefData.parseCSV(text);
      if (!parsed.rows.length) {
        showToast(t('refdata.err_no_rows'), 'warning');
        return;
      }
      _state.refImportDraft = { parsed, filename: file.name };
      renderRefDataDialog();
      bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-refdata')).show();
    } catch (err) {
      showToast(t('refdata.err_parse', { msg: err.message }), 'danger');
    }
  });
  document.getElementById('btn-refdata-import').addEventListener('click', confirmRefDataImport);

  // ── Deep link desde el runner (Fase R3): ?folder=<carpeta> ────────────────
  // Rellena el campo y lanza el análisis automáticamente; compatible con la
  // cache del backend keyed por carpeta (varias pestañas no se pisan).
  const folderParam = new URLSearchParams(window.location.search).get('folder');
  if (folderParam) {
    document.getElementById('folder-input').value = folderParam;
    doAnalyze();
  }

  // ── Deep link desde el análisis de cadenas (F9e del BACKLOG):
  // ?chains_root=<carpeta> ──────────────────────────────────────────────────
  // La pestaña "Análisis de cadenas" es independiente de folder-input/
  // analysisData (tiene su propio _state.chainsRoot, ver arriba) -- un
  // chains_manifest.json no es una carpeta de "Simulaciones" normal, así
  // que el botón "Abrir en Fort Analyzer" del pipeline de cadenas (inp-conf,
  // chains_sweep.js) no puede reutilizar ?folder= sin más: cambia a esta
  // pestaña y lanza fetchChainsReport() automáticamente, mismo patrón que
  // el deep link de arriba pero apuntando a su propio estado.
  const chainsRootParam = new URLSearchParams(window.location.search).get('chains_root');
  if (chainsRootParam) {
    _state.chainsRoot = chainsRootParam;
    const chainsTabBtn = document.getElementById('tab-chains-btn');
    chainsTabBtn.addEventListener('shown.bs.tab', () => fetchChainsReport(), { once: true });
    bootstrap.Tab.getOrCreateInstance(chainsTabBtn).show();
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Analysis workflow
// ─────────────────────────────────────────────────────────────────────────────
async function doAnalyze(opts = {}) {
  const folder = document.getElementById('folder-input').value.trim();
  if (!folder) {
    showToast(t('toast.enter_folder'), 'warning');
    return;
  }

  const leerInp5 = document.getElementById('src-inp5').checked;
  let tIrrOv = null, tCoolOv = null, phiOv = null;
  if (!leerInp5) {
    tIrrOv  = parseFloatOrNull(document.getElementById('t-irr-override').value);
    tCoolOv = parseFloatOrNull(document.getElementById('t-cool-override').value);
    phiOv   = parseFloatOrNull(document.getElementById('phi-override').value);
  }

  setLoading(true, t('loading.default'));
  setStatus(t('status.analyzing'), 'warning');

  // Reset state for new analysis  (F1)
  _state.chartsRendered  = false;
  _state.isotopoRendered = false;
  _state.tablesRendered  = false;
  _state.selectedIsotopo = null;
  _state.isotopoReport   = null;
  _state.refSeries       = [];
  _state.refImportDraft  = null;
  _state.refMetricsTargetSim = null;
  _state.optimRendered   = false;
  _state.optimXParam     = null;
  _state.espectroRendered = false;
  _state.espectroSim      = null;
  _state.espectroT        = null;
  _state.espectroData     = null;
  _state.espectroFiltros  = { eMinKeV: null, eMaxKeV: null, tasaMin: null };
  _state.espectroAutoLoadDone = false;
  _state.espectroTasaMinTouched = false;

  // Hide sidebar isotope summary card
  document.getElementById('i131-summary-card').classList.add('d-none');

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        folder,
        leer_inp5:       leerInp5,
        t_irr_override:  tIrrOv,
        t_cool_override: tCoolOv,
        phi_override:    phiOv,
        yaml_content:    opts.yamlContentOverride || null,
      }),
    });

    const json = await res.json();
    if (!res.ok || !json.ok) {
      showToast(json.error || t('toast.unknown_err'), 'danger');
      setStatus(t('status.error'), 'danger');
      return;
    }

    _state.analysisData    = json;
    _state.folder          = folder;
    // Snapshot of the figuras/yaml as loaded (yaml_used auto|upload) or empty
    // (none) — feeds the editor's "restore to loaded YAML" reset button and
    // the save/download round-trip (decisiones 6 y 7 del runbook de figuras).
    _state.figurasOriginal  = JSON.parse(JSON.stringify(json.figuras || []));
    _state.yamlConfigLoaded = JSON.parse(JSON.stringify(json.yaml_config || {}));
    const simNames = Object.keys(json.simulations);

    // Enable/disable MBq/g and reconcile the active unit with the new data
    // (falls back to Bq/cm³ if MBq/g was active but no sim carries density).
    syncUnitControls();

    setStatus(t('status.sims_count', { n: simNames.length }), 'success');

    // YAML badges (sidebar general status + figuras-tab origin badge)
    showYamlStatus(json.yaml_used);
    updateFigurasBadge(json.yaml_used);

    // Render errors + sidebar sim list
    renderErrors(json.errors || {});
    renderSimList(simNames, json.simulations);

    // Always switch to Overview tab and render it (ensures re-analysis works
    // correctly when the user was already on another tab, because shown.bs.tab
    // won't fire for a tab that is already active, leaving stale content)
    const _overviewBtn = document.getElementById('tab-overview-btn');
    if (_overviewBtn) {
      bootstrap.Tab.getOrCreateInstance(_overviewBtn).show();
    }
    renderOverview(json);

    // Warn if any errors
    const errCount = Object.keys(json.errors || {}).length;
    if (errCount > 0) {
      showToast(t('toast.errors_count', { n: errCount }), 'warning');
    }

  } catch (err) {
    showToast(t('toast.net_err', { msg: err.message }), 'danger');
    setStatus(t('status.net_error'), 'danger');
  } finally {
    setLoading(false);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Isotope selection  (F3, F4)
// ─────────────────────────────────────────────────────────────────────────────

// Called when a badge in the Overview isotope list is clicked
function selectIsotopo(isoKey) {
  _state.selectedIsotopo = isoKey;
  _state.isotopoRendered = false;
  _state.tablesRendered  = false;
  _state.optimRendered   = false;
  _state.optimXParam     = null;

  // Highlight selected badge, reset others
  document.querySelectorAll('.isotopo-badge').forEach(b => {
    const sel = b.dataset.iso === isoKey;
    b.classList.toggle('bg-primary',  sel);
    b.classList.toggle('text-white',  sel);
    b.classList.toggle('bg-light',   !sel);
    b.classList.toggle('text-dark',  !sel);
  });

  // Switch to isotope report tab
  bootstrap.Tab.getOrCreateInstance(document.getElementById('tab-i131-btn')).show();

  // Fetch report (renders Tab 3 on success)
  fetchIsotopoReport(isoKey);
}

async function fetchIsotopoReport(isoKey, impurezas) {
  const container = document.getElementById('i131-report-container');
  container.innerHTML = `
    <div class="d-flex align-items-center gap-3 mt-4 ms-2">
      <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
      <span class="text-muted">${t('report.generating', { label: escHtml(isoLabel(isoKey)) })}</span>
    </div>`;

  try {
    const res = await fetch('/api/isotopo_report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // Send the analysed folder explicitly so the folder-keyed server cache
      // returns this tab's data even if another tab analysed a different folder.
      // impurezas (Fase 5): override editable desde la UI de la lista de
      // isótopos considerados en la métrica de pureza; omitido → mismo-elemento.
      body: JSON.stringify({ isotopo: isoKey, folder: _state.folder, impurezas: impurezas || undefined }),
    });
    const json = await res.json();

    if (!res.ok || !json.ok) {
      container.innerHTML = `<div class="alert alert-danger mt-3">${escHtml(json.error || t('toast.unknown_err'))}</div>`;
      return;
    }

    _state.isotopoReport   = json;
    _state.isotopoRendered = false;
    _state.tablesRendered  = false;
    _state.optimRendered   = false;
    _state.optimXParam     = null;

    renderIsotopoReport();
    _state.isotopoRendered = true;

    // If tables tab was already rendered for a prior isotope, reset it
    document.getElementById('tables-container').innerHTML = `
      <div class="alert alert-info mt-3">
        <i class="bi bi-hand-index me-2"></i>
        ${t('report.goto_tables', { label: escHtml(isoLabel(isoKey)) })}
      </div>`;

    // Same for Tab 5 (Optimización, Fase 5 opcional) if it was already rendered.
    const optimContainer = document.getElementById('optim-container');
    if (optimContainer) {
      optimContainer.innerHTML = `
        <div class="alert alert-info mt-3">
          <i class="bi bi-hand-index me-2"></i>
          ${t('optim.goto', { label: escHtml(isoLabel(isoKey)) })}
        </div>`;
    }

    renderIsotopoSummaryCard(isoKey, json.informe);

  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger mt-3">${t('toast.net_err', { msg: escHtml(err.message) })}</div>`;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Sidebar: simulation list
// ─────────────────────────────────────────────────────────────────────────────
function renderSimList(simNames, simulations) {
  const card = document.getElementById('sim-list-card');
  const list = document.getElementById('sim-list');
  card.classList.remove('d-none');

  list.innerHTML = simNames.map((name, i) => {
    const sim = simulations[name];
    const phi = sim.PHI > 0 ? `φ = ${fmtSci(sim.PHI)} n/cm²/s` : '';
    return `
      <a href="#" class="list-group-item list-group-item-action sim-item py-2"
         data-sim="${escAttr(name)}">
        <div class="d-flex align-items-start gap-2">
          <span class="sim-dot mt-1" style="background:${PALETTE[i % PALETTE.length]}"></span>
          <div class="overflow-hidden">
            <div class="fw-semibold text-truncate" style="font-size:0.82rem"
                 title="${escAttr(name)}">${escHtml(name)}</div>
            <div class="text-muted" style="font-size:0.72rem">
              T<sub>irr</sub>&nbsp;${sim.T_IRR_h.toFixed(2)}&nbsp;h
              &nbsp;|&nbsp;${phi}
            </div>
          </div>
        </div>
      </a>
    `;
  }).join('');

  if (list.firstElementChild) list.firstElementChild.classList.add('active');

  list.querySelectorAll('.sim-item').forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      list.querySelectorAll('.sim-item').forEach(x => x.classList.remove('active'));
      el.classList.add('active');
    });
  });
}

// Sidebar isotope peak summary card  (F7)
function renderIsotopoSummaryCard(isoKey, report) {
  if (!report) return;
  const card   = document.getElementById('i131-summary-card');
  const header = document.getElementById('i131-summary-header');
  const body   = document.getElementById('i131-summary-body');

  header.innerHTML = `<i class="bi bi-radioactive text-warning me-1"></i>${t('sidebar.iso_peak', { label: isoLabel(isoKey) })}`;
  card.classList.remove('d-none');

  const sims = _state.analysisData ? _state.analysisData.simulations : {};
  const rows = Object.entries(report.simulations).map(([name, s]) => {
    const Ap = s.A_pico > 0 ? fmtA(s.A_pico, sims[name], 3) : '—';
    const tp = s.t_pico !== null && s.t_pico !== undefined ? s.t_pico.toFixed(2) : '—';
    const phaseCls = s.fase === 'irradiación' ? 'badge-phase-irr' : 'badge-phase-cool';
    return `
      <div class="mb-2 pb-2 border-bottom" style="font-size:0.78rem">
        <div class="fw-semibold text-truncate" title="${escAttr(name)}">${escHtml(name)}</div>
        <div class="font-monospace text-danger fw-bold">${Ap} ${unitLabel()}</div>
        <div class="text-muted">t = ${tp} h &nbsp;
          <span class="badge ${phaseCls}" style="font-size:0.65rem">${phaseLabel(s.fase)}</span>
        </div>
      </div>
    `;
  }).join('');

  body.innerHTML = rows || `<span class="text-muted small">${t('report.no_data', { label: isoLabel(isoKey) })}</span>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 1: Overview
// ─────────────────────────────────────────────────────────────────────────────
function renderOverview(data) {
  const container = document.getElementById('overview-container');
  const sims = data.simulations;
  const simNames = Object.keys(sims);
  const anyDesactualizada = simNames.some(name => sims[name].desactualizada);

  // Main summary table
  const rows = simNames.map((name, i) => {
    const sim = sims[name];
    const nIrr  = Object.keys(sim.datos_irr_Bq).length;
    const nCool = Object.keys(sim.datos_cool).length;
    const hasI131 = 'I131' in sim.datos_irr_Bq || 'I131' in sim.datos_cool;
    const fluxLabel = sim.fluxes.length > 1
      ? t('overview.groups_count', { n: sim.ngrp })
      : (sim.PHI > 0 ? fmtSci(sim.PHI) : '—');
    const fechaLabel = sim.fort6_fecha
      ? sim.fort6_fecha.replace('T', ' ')
      : '—';
    const desactualizadaBadge = sim.desactualizada
      ? `<span class="badge bg-warning text-dark ms-1" style="font-size:0.65rem;cursor:help"
               title="${escAttr(t('overview.desactualizada_tooltip'))}">
           <i class="bi bi-exclamation-triangle-fill me-1"></i>${t('overview.desactualizada_badge')}
         </span>`
      : '';
    return `
      <tr>
        <td><span class="sim-dot" style="background:${PALETTE[i % PALETTE.length]}"></span></td>
        <td class="fw-semibold small" title="${escAttr(name)}">${escHtml(name)}</td>
        <td class="font-monospace small">${sim.T_IRR_h.toFixed(4)}</td>
        <td class="font-monospace small">${sim.T_COOL_h.toFixed(2)}</td>
        <td class="font-monospace small">${fluxLabel}</td>
        <td class="font-monospace small">${sim.densidad_g_cm3 != null ? sim.densidad_g_cm3.toFixed(5) : '—'}</td>
        <td class="text-center">${sim.ngrp}</td>
        <td class="text-center small">${nIrr} / ${nCool}</td>
        <td class="text-center">${hasI131
          ? '<i class="bi bi-check-circle-fill text-success"></i>'
          : '<i class="bi bi-dash-circle text-secondary"></i>'}</td>
        <td class="text-center">${sim.inp5_found
          ? '<i class="bi bi-check-circle-fill text-success"></i>'
          : '<i class="bi bi-x-circle text-danger"></i>'}</td>
        <td class="font-monospace small">${fechaLabel}${desactualizadaBadge}</td>
      </tr>
    `;
  }).join('');

  let html = `
    <h5 class="mb-3">${t('overview.title')}</h5>
    ${anyDesactualizada ? `
      <div class="alert alert-warning d-flex align-items-center gap-2 py-2 mb-3" style="font-size:0.85rem">
        <i class="bi bi-exclamation-triangle-fill"></i>
        <span>${t('overview.desactualizada_warning')}</span>
      </div>
    ` : ''}
    <div class="table-responsive mb-4">
      <table class="table table-sm table-hover overview-table align-middle">
        <thead class="table-dark">
          <tr>
            <th style="width:18px"></th>
            <th>${t('overview.th_sim')}</th>
            <th>${t('overview.th_tirr')}</th>
            <th>${t('overview.th_tcool')}</th>
            <th>${t('overview.th_phi')}</th>
            <th>${t('overview.th_dens')}</th>
            <th class="text-center">${t('overview.th_ngrp')}</th>
            <th class="text-center">${t('overview.th_iso')}<br><span class="fw-normal">${t('overview.th_iso_sub')}</span></th>
            <th class="text-center">${t('overview.th_i131')}</th>
            <th class="text-center">${t('overview.th_inp5')}</th>
            <th>${t('overview.th_fecha')}</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;

  // Per-simulation flux detail (only if multi-group)
  simNames.forEach((name, i) => {
    const sim = sims[name];
    if (!sim.fluxes || sim.fluxes.length <= 1) return;

    const groupLabel = (g, n) =>
      g === 0 ? t('overview.group_fast')
      : g === n - 1 ? t('overview.group_thermal')
      : t('overview.group_epi', { n: g + 1 });

    const fluxRows = sim.fluxes.map((f, g) =>
      `<tr>
        <td>${t('overview.group_row', { n: g + 1, label: groupLabel(g, sim.fluxes.length) })}</td>
        <td class="font-monospace">${fmtSci(f)} n/cm²/s</td>
      </tr>`
    ).join('');

    html += `
      <div class="mb-3">
        <div class="section-heading">
          <span class="sim-dot me-1" style="background:${PALETTE[i % PALETTE.length]}"></span>
          ${t('overview.flux_detail', { name: escHtml(name) })}
        </div>
        <div class="table-responsive" style="max-width:420px">
          <table class="table table-sm table-bordered mb-0" style="font-size:0.82rem">
            <thead class="table-light"><tr><th>${t('overview.th_group')}</th><th>${t('overview.th_flux')}</th></tr></thead>
            <tbody>${fluxRows}</tbody>
          </table>
        </div>
      </div>
    `;
  });

  // Isotope badge list — clickable  (F2)
  html += `
    <div class="mt-2">
      <div class="section-heading">${t('overview.detected')}</div>
      <p class="small text-muted mb-1">
        ${t('overview.click_hint')}
      </p>
      <div class="d-flex flex-wrap gap-1" id="isotope-badges">
        ${(data.all_isotopes || []).map(iso =>
          `<span class="badge bg-light text-dark border isotopo-badge"
                style="font-size:0.78rem;cursor:pointer"
                data-iso="${escAttr(iso)}">${escHtml(iso)}</span>`
        ).join('')}
      </div>
    </div>
  `;

  container.innerHTML = html;

  // Event delegation for isotope badge clicks  (F2)
  const badgeContainer = container.querySelector('#isotope-badges');
  if (badgeContainer) {
    badgeContainer.addEventListener('click', e => {
      const badge = e.target.closest('.isotopo-badge');
      if (badge) selectIsotopo(badge.dataset.iso);
    });
  }

  // Re-apply highlight if an isotope was already selected
  if (_state.selectedIsotopo) {
    container.querySelectorAll('.isotopo-badge').forEach(b => {
      const sel = b.dataset.iso === _state.selectedIsotopo;
      b.classList.toggle('bg-primary',  sel);
      b.classList.toggle('text-white',  sel);
      b.classList.toggle('bg-light',   !sel);
      b.classList.toggle('text-dark',  !sel);
    });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 2: Activity charts
// ─────────────────────────────────────────────────────────────────────────────
function renderCharts() {
  const data = _state.analysisData;
  if (!data) return;

  const container = document.getElementById('charts-container');
  container.innerHTML = '';

  const allFiguras = data.figuras || [];
  if (allFiguras.length === 0) {
    renderFigurasEmptyState(container);
    return;
  }

  const filter = _state.chartFilter;
  const figuras = allFiguras.filter(cfg => {
    if (filter === 'all') return true;
    return cfg.series.some(s => s.iso.startsWith(filter.toUpperCase()));
  });

  if (figuras.length === 0) {
    container.innerHTML = `<div class="alert alert-info">${t('charts.no_figs')}</div>`;
    return;
  }

  figuras.forEach((cfg, idx) => {
    const divId = `chart-${idx}`;
    const figNum = cfg.num !== undefined ? cfg.num : idx + 1;
    const card = document.createElement('div');
    card.className = 'chart-card mb-4';
    card.innerHTML = `
      <div class="card-header d-flex justify-content-between align-items-center">
        <span>${escHtml(cfg.titulo || t('charts.fig', { n: figNum }))}</span>
        <div class="d-flex align-items-center gap-2">
          <span class="text-muted small">${cfg.series.map(s => escHtml(s.label || s.iso)).join(' / ')}</span>
          <button class="btn btn-outline-secondary btn-sm btn-export-chart"
                  title="${escAttr(t('export.csv'))}">
            <i class="bi bi-download"></i>
          </button>
        </div>
      </div>
      <div class="p-2">
        <div id="${divId}" class="plotly-chart"></div>
      </div>
    `;
    container.appendChild(card);
    _renderActivityChart(divId, cfg, data.simulations);
    const btn = card.querySelector('.btn-export-chart');
    if (btn) btn.addEventListener('click', () => exportChartCSV(divId, cfg, figNum));
  });
}

// Sin figuras (sin YAML auto/cargado y editor vacío) — estado vacío amable
// con dos acciones (decisión 1 del runbook de figuras YAML).
function renderFigurasEmptyState(container) {
  container.innerHTML = `
    <div class="alert alert-secondary text-center py-5">
      <i class="bi bi-graph-up display-6 text-muted mb-3 d-block"></i>
      <p class="mb-3">${t('charts.empty_msg')}</p>
      <div class="d-flex justify-content-center gap-2 flex-wrap">
        <button type="button" class="btn btn-outline-secondary btn-sm" id="btn-empty-load-yaml">
          <i class="bi bi-file-earmark-arrow-up me-1"></i>${t('charts.load_yaml')}
        </button>
        <button type="button" class="btn btn-outline-primary btn-sm" id="btn-empty-create-figuras">
          <i class="bi bi-pencil-square me-1"></i>${t('charts.empty_create')}
        </button>
      </div>
    </div>`;
  document.getElementById('btn-empty-load-yaml')
    ?.addEventListener('click', () => document.getElementById('figuras-yaml-file-input').click());
  document.getElementById('btn-empty-create-figuras')
    ?.addEventListener('click', openFigurasEditor);
}

/**
 * B1 del BACKLOG (runbook_B1_espectro_gamma.md) — pestaña "Espectro gamma":
 * espectro de EMISIÓN de la muestra (líneas discretas de PHOTON.dat x
 * actividad del fort.6 en un instante, calculado en el servidor por
 * fort_analyzer.calcular_espectro_gamma). No es la respuesta de un detector
 * (sin resolución/eficiencia/Compton) ni incluye el continuo beta/
 * bremsstrahlung — fuera de alcance por diseño (ver el aviso fijo en la UI).
 *
 * Construye el panel una vez (selectores de simulación/instante, filtros de
 * energía/tasa mínima, ruta de PHOTON.dat) y pide el espectro al servidor
 * bajo demanda (no viaja entero en /api/analyze: con una librería PHOTON.dat
 * completa podría ser enorme). Los filtros solo recortan localmente lo ya
 * recibido (fetchEspectroGamma no se vuelve a llamar al cambiarlos).
 */
function renderEspectroGamma() {
  const container = document.getElementById('espectro-container');
  const data = _state.analysisData;
  if (!container || !data) return;

  const sims = data.simulations;
  const simNames = Object.keys(sims);
  if (!_state.espectroSim || simNames.indexOf(_state.espectroSim) === -1) {
    _state.espectroSim = simNames[0];
  }
  const sim = sims[_state.espectroSim];
  const tCool = sim.t_cool || [];

  if (!tCool.length) {
    container.innerHTML = `<div class="alert alert-secondary mt-3">${t('espectro.no_cooling')}</div>`;
    return;
  }
  if (_state.espectroT == null || tCool.indexOf(_state.espectroT) === -1) {
    _state.espectroT = tCool[tCool.length - 1];
  }

  const simSelectorHtml = simNames.length > 1 ? `
    <div class="col-auto">
      <label class="form-label small mb-1" for="espectro-sim-select">${t('espectro.sim_label')}</label>
      <select class="form-select form-select-sm" id="espectro-sim-select">
        ${simNames.map(n => `<option value="${escAttr(n)}" ${n === _state.espectroSim ? 'selected' : ''}>${escHtml(n)}</option>`).join('')}
      </select>
    </div>` : '';

  container.innerHTML = `
    <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
      <h5 class="mb-0">${t('espectro.title')}</h5>
      <button class="btn btn-outline-secondary btn-sm" id="btn-export-espectro">
        <i class="bi bi-download me-1"></i>${t('export.csv')}
      </button>
    </div>
    <div class="alert alert-secondary small mb-3">
      <i class="bi bi-info-circle me-1"></i>${t('espectro.scope_note')}
    </div>
    <div class="row g-2 align-items-end mb-2">
      ${simSelectorHtml}
      <div class="col-auto">
        <label class="form-label small mb-1" for="espectro-t-select">${t('espectro.t_label')}</label>
        <select class="form-select form-select-sm" id="espectro-t-select">
          ${tCool.map(tv => `<option value="${tv}" ${tv === _state.espectroT ? 'selected' : ''}>${tv.toFixed(3)} h</option>`).join('')}
        </select>
      </div>
      <div class="col-auto">
        <label class="form-label small mb-1" for="espectro-emin">${t('espectro.emin_label')}</label>
        <input type="number" class="form-control form-control-sm" id="espectro-emin" style="width:110px" min="0" placeholder="0"
               value="${_state.espectroFiltros.eMinKeV != null ? _state.espectroFiltros.eMinKeV : ''}">
      </div>
      <div class="col-auto">
        <label class="form-label small mb-1" for="espectro-emax">${t('espectro.emax_label')}</label>
        <input type="number" class="form-control form-control-sm" id="espectro-emax" style="width:110px" min="0" placeholder="${t('espectro.no_limit')}"
               value="${_state.espectroFiltros.eMaxKeV != null ? _state.espectroFiltros.eMaxKeV : ''}">
      </div>
      <div class="col-auto">
        <label class="form-label small mb-1" for="espectro-tasa-min">${t('espectro.tasamin_label')}</label>
        <input type="number" class="form-control form-control-sm" id="espectro-tasa-min" style="width:140px" min="0" placeholder="0"
               value="${_state.espectroFiltros.tasaMin != null ? _state.espectroFiltros.tasaMin : ''}">
      </div>
    </div>
    <div class="row g-2 align-items-end mb-3">
      <div class="col-auto flex-grow-1" style="max-width:420px">
        <label class="form-label small mb-1" for="espectro-photon-path">${t('espectro.photon_path_label')}</label>
        <div class="input-group input-group-sm">
          <input type="text" class="form-control" id="espectro-photon-path"
                 placeholder="${escAttr(t('espectro.photon_path_placeholder'))}" value="${escAttr(_state.espectroPhotonPath || '')}">
          <button class="btn btn-outline-secondary" id="btn-espectro-browse-photon" type="button"
                  title="${escAttr(t('espectro.photon_path_browse_title'))}">
            <i class="bi bi-folder2-open"></i>
          </button>
        </div>
      </div>
      <div class="col-auto">
        <button class="btn btn-outline-primary btn-sm" id="btn-espectro-load-photon">
          <i class="bi bi-arrow-repeat me-1"></i>${t('espectro.photon_path_load')}
        </button>
      </div>
      <div class="col-auto">
        <span id="espectro-photon-status" class="small text-muted"></span>
      </div>
    </div>
    <div id="espectro-chart" style="height:420px"></div>
    <div id="espectro-sin-lineas" class="small text-muted mt-2"></div>
    <h6 class="mt-4">${t('espectro.table_title')}</h6>
    <div class="table-responsive">
      <table class="table table-sm table-hover">
        <thead><tr>
          <th>${t('espectro.th_e')}</th><th>${t('espectro.th_nucleido')}</th>
          <th>${t('espectro.th_intensidad')}</th><th>${t('espectro.th_tasa')}</th>
        </tr></thead>
        <tbody id="espectro-table-body"></tbody>
      </table>
    </div>
  `;

  document.getElementById('espectro-sim-select')?.addEventListener('change', e => {
    _state.espectroSim = e.target.value;
    _state.espectroT = null; // t_cool puede diferir por simulación -> recalcula el último
    renderEspectroGamma();
  });
  document.getElementById('espectro-t-select')?.addEventListener('change', e => {
    _state.espectroT = parseFloat(e.target.value);
    fetchEspectroGamma();
  });
  const FILTRO_INPUT_IDS = { 'espectro-emin': 'eMinKeV', 'espectro-emax': 'eMaxKeV', 'espectro-tasa-min': 'tasaMin' };
  Object.entries(FILTRO_INPUT_IDS).forEach(([id, key]) => {
    document.getElementById(id)?.addEventListener('input', e => {
      _state.espectroFiltros[key] = parseFloatOrNull(e.target.value);
      // B1b: en cuanto el usuario toca la tasa mínima a mano, deja de
      // recalcularse el umbral por defecto (su elección manda, "0 = sin
      // filtro" incluido).
      if (id === 'espectro-tasa-min') _state.espectroTasaMinTouched = true;
      _renderEspectroChartAndTable();
    });
  });
  document.getElementById('btn-espectro-load-photon')?.addEventListener('click', () => {
    const p = document.getElementById('espectro-photon-path').value.trim();
    if (!p) { showToast(t('espectro.photon_path_required'), 'warning'); return; }
    _state.espectroPhotonPath = p;
    fetchEspectroGamma(p);
  });
  // B1b del BACKLOG — explorador nativo de FICHERO (variante de U2, que usa
  // la carpeta): rellena la ruta y carga de inmediato, sin paso manual extra.
  document.getElementById('btn-espectro-browse-photon')?.addEventListener('click', async () => {
    const browseBtn = document.getElementById('btn-espectro-browse-photon');
    const icon = browseBtn.querySelector('i');
    browseBtn.disabled = true;
    icon.className = 'bi bi-hourglass-split';
    try {
      const res = await fetch('/api/browse-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: t('espectro.photon_path_dialog_title') }),
      });
      const json = await res.json();
      if (json.path) {
        document.getElementById('espectro-photon-path').value = json.path;
        _state.espectroPhotonPath = json.path;
        fetchEspectroGamma(json.path);
      } else if (!json.error) {
        showToast(t('toast.no_file_selected'), 'secondary');
      }
    } catch {
      showToast(t('toast.browse_file_err'), 'warning');
    } finally {
      browseBtn.disabled = false;
      icon.className = 'bi bi-folder2-open';
    }
  });
  document.getElementById('btn-export-espectro')?.addEventListener('click', exportEspectroCSV);

  fetchEspectroGamma();
}

/**
 * POST /api/espectro_gamma para (simulación, instante) actuales del estado.
 * *opts.silent*, si true, no muestra toast de error (usado por el intento
 * automático de recarga desde la ruta recordada en localStorage — "si la
 * ruta sigue existiendo", B1b del BACKLOG: si ya no existe, se queda
 * calladamente en el estado "sin librería", no es un fallo del usuario).
 */
async function fetchEspectroGamma(photonPathOverride, opts) {
  opts = opts || {};
  if (!_state.analysisData) return;
  const chartDiv = document.getElementById('espectro-chart');
  if (chartDiv) chartDiv.innerHTML = `<div class="text-muted small p-3">${t('espectro.loading')}</div>`;

  try {
    const res = await fetch('/api/espectro_gamma', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        folder:          _state.folder,
        sim:             _state.espectroSim,
        t_h:             _state.espectroT,
        photon_dat_path: photonPathOverride || null,
      }),
    });
    const json = await res.json();
    if (!res.ok || !json.ok) {
      if (opts.silent) {
        _renderEspectroChartAndTable();
        return;
      }
      const msg = (json && json.error) || t('toast.unknown_err');
      showToast(msg, 'danger');
      if (chartDiv) chartDiv.innerHTML = `<div class="alert alert-danger small mb-0">${escHtml(msg)}</div>`;
      return;
    }
    _state.espectroData = json;
    const statusEl = document.getElementById('espectro-photon-status');
    if (statusEl) {
      statusEl.textContent = json.photon_dat_used
        ? t('espectro.photon_path_status_ok', { path: json.photon_dat_path || '' })
        : t('espectro.photon_path_status_none');
    }
    if (json.photon_dat_used && json.photon_dat_path) {
      localStorage.setItem(PHOTON_PATH_KEY, json.photon_dat_path);
      _state.espectroPhotonPath = json.photon_dat_path;
      const pathInput = document.getElementById('espectro-photon-path');
      if (pathInput) pathInput.value = json.photon_dat_path;
    }
    _renderEspectroChartAndTable();

    // Primer render de esta carpeta analizada solamente: si el servidor no
    // autodescubrió ninguna librería junto al fort.6, intenta la última ruta
    // recordada en localStorage (silenciosamente).
    if (!_state.espectroAutoLoadDone) {
      _state.espectroAutoLoadDone = true;
      if (!json.photon_dat_used) {
        const remembered = localStorage.getItem(PHOTON_PATH_KEY);
        if (remembered) {
          const pathInput = document.getElementById('espectro-photon-path');
          if (pathInput) pathInput.value = remembered;
          fetchEspectroGamma(remembered, { silent: true });
        }
      }
    }
  } catch (err) {
    showToast(t('toast.net_err', { msg: err.message }), 'danger');
  }
}

/** Filtra (localmente) lo ya recibido de /api/espectro_gamma y pinta el stick plot + tabla. */
function _renderEspectroChartAndTable() {
  const json = _state.espectroData;
  const chartDiv   = document.getElementById('espectro-chart');
  const tbody      = document.getElementById('espectro-table-body');
  const sinLineasDiv = document.getElementById('espectro-sin-lineas');
  if (!json || !chartDiv) return;

  const espectro = json.espectro || {};
  const lineasTodas = espectro.lineas || [];

  if (!json.photon_dat_used) {
    chartDiv.innerHTML = `<div class="alert alert-secondary small mb-0">${t('espectro.no_library')}</div>`;
    if (tbody) tbody.innerHTML = '';
    if (sinLineasDiv) sinLineasDiv.innerHTML = '';
    return;
  }

  // B1b del BACKLOG — umbral de tasa mínima POR DEFECTO relativo al máximo
  // del instante (vista inicial legible sin tocar ningún filtro); una vez
  // el usuario toca el campo, su elección manda y ya no se recalcula solo
  // (incluido "0 = sin filtro", que sigue disponible tecleándolo).
  if (!_state.espectroTasaMinTouched) {
    const defecto = ACABEspectroGamma.umbralPorDefecto(lineasTodas);
    _state.espectroFiltros.tasaMin = defecto > 0 ? defecto : null;
    const tasaInput = document.getElementById('espectro-tasa-min');
    if (tasaInput) tasaInput.value = defecto > 0 ? Number(defecto.toPrecision(3)) : '';
  }

  const lineas = ACABEspectroGamma.filtrarLineas(lineasTodas, _state.espectroFiltros);

  if (!lineas.length) {
    chartDiv.innerHTML = `<div class="alert alert-warning small mb-0">${t('espectro.no_lines_after_filter')}</div>`;
  } else {
    chartDiv.innerHTML = '';
    // Leyenda acotada a los 8 nucleidos de mayor tasa total (criterio de U4:
    // nunca volcado completo); el resto se agrupa en una única traza "otros"
    // con color neutro (el hover de cada punto sigue mostrando su nucleido real).
    const colorFor = (nucleido, i) => PALETTE[i % PALETTE.length];
    const traces = ACABEspectroGamma.construirTrazasStickTopN(lineas, colorFor, {
      topN: 8, colorOtros: '#9e9e9e', otrosLabel: t('espectro.legend_otros'),
    });
    Plotly.newPlot(chartDiv, traces, {
      xaxis: { title: t('espectro.ax_e'), showgrid: true, gridcolor: '#eee' },
      yaxis: { title: t('espectro.ax_tasa'), type: 'log', exponentformat: 'e', showgrid: true, gridcolor: '#eee' },
      margin: { t: 20, b: 40, l: 70, r: 20 },
      legend: { orientation: 'h', y: -0.25, font: { size: 9 } },
      hovermode: 'closest',
      plot_bgcolor: '#fafafa', paper_bgcolor: '#fff',
    }, { responsive: true });
  }

  if (tbody) {
    const top = ACABEspectroGamma.topLineas(lineas, 50);
    tbody.innerHTML = top.length ? top.map(l => `
      <tr>
        <td>${l.E_keV.toFixed(2)}</td>
        <td>${escHtml(isoLabel(l.nucleido))} (${escHtml(l.nucleido)})</td>
        <td>${l.intensidad_pct.toFixed(3)}</td>
        <td>${fmtSci(l.tasa_fotones_s_cm3)}</td>
      </tr>`).join('')
      : `<tr><td colspan="4" class="text-muted small">${t('espectro.no_lines_after_filter')}</td></tr>`;
  }

  const sinLineas = espectro.nucleidos_sin_lineas || [];
  if (sinLineasDiv) {
    sinLineasDiv.innerHTML = sinLineas.length ? `
      <details>
        <summary>${t('espectro.sin_lineas_summary', { n: sinLineas.length })}</summary>
        <span class="font-monospace">${sinLineas.map(escHtml).join(', ')}</span>
      </details>` : '';
  }
}

/** Exporta la tabla de líneas (ya filtradas por energía/tasa) a CSV. */
function exportEspectroCSV() {
  const json = _state.espectroData;
  if (!json || !json.espectro || !json.photon_dat_used) return;
  const lineas = ACABEspectroGamma.filtrarLineas(json.espectro.lineas || [], _state.espectroFiltros);
  if (!lineas.length) return;

  const rows = ACABEspectroGamma.topLineas(lineas, null)
    .map(l => [l.E_keV, l.nucleido, l.intensidad_pct, l.tasa_fotones_s_cm3]);
  const headers = [t('espectro.th_e'), t('espectro.th_nucleido'), t('espectro.th_intensidad'), t('espectro.th_tasa')];
  const title = `${json.sim} t=${json.espectro.t_h}h`;
  emitCSV(`espectro_gamma_t${json.espectro.t_h}_${folderSlug()}.csv`, title, rows, headers);
}

/* ─────────────────────────────────────────────────────────────────────────
   F9 del BACKLOG, Fase 4-5 — pestaña "Análisis de cadenas"
   Independiente de _state.analysisData/folder: carga su PROPIA carpeta de
   análisis (chains_manifest.json, generado por el ACAB INP File
   Configurator, sección "Análisis de cadenas"). Sin caché propia: cada
   cambio de instante t* vuelve a pedir /api/chains_report entero (mismo
   criterio que el resto de la app: los datos de un análisis de cadenas son
   pequeños, como mucho MAX_ISOTOPES fort.6/output_chain.txt individuales).
   ───────────────────────────────────────────────────────────────────────── */

/** Construye el panel una vez: carpeta de análisis + área de resultados. */
function renderChainsPanel() {
  const container = document.getElementById('chains-container');
  if (!container) return;

  container.innerHTML = `
    <h5 class="mb-2">${t('chains.title')}</h5>
    <div class="alert alert-secondary small mb-3">
      <i class="bi bi-info-circle me-1"></i>${t('chains.scope_note')}
    </div>
    <div class="row g-2 align-items-end mb-3">
      <div class="col-auto flex-grow-1" style="max-width:480px">
        <label class="form-label small mb-1" for="chains-root-input">${t('chains.root_label')}</label>
        <div class="input-group input-group-sm">
          <input type="text" class="form-control font-monospace" id="chains-root-input"
                 placeholder="${escAttr(t('chains.root_ph'))}" value="${escAttr(_state.chainsRoot || '')}">
          <button class="btn btn-outline-secondary" id="btn-chains-browse" type="button"
                  title="${escAttr(t('sidebar.browse'))}">
            <i class="bi bi-folder2-open"></i>
          </button>
        </div>
      </div>
      <div class="col-auto">
        <button class="btn btn-primary btn-sm" id="btn-chains-load">
          <i class="bi bi-arrow-repeat me-1"></i>${t('chains.load')}
        </button>
      </div>
    </div>
    <div id="chains-results"></div>
  `;

  document.getElementById('btn-chains-browse')?.addEventListener('click', async () => {
    const browseBtn = document.getElementById('btn-chains-browse');
    const icon = browseBtn.querySelector('i');
    browseBtn.disabled = true;
    icon.className = 'bi bi-hourglass-split';
    try {
      const res = await fetch('/api/browse-folder', { method: 'POST' });
      const json = await res.json();
      if (json.folder) {
        document.getElementById('chains-root-input').value = json.folder;
      } else if (!json.error) {
        showToast(t('toast.no_folder_selected'), 'secondary');
      }
    } catch {
      showToast(t('toast.browse_err'), 'warning');
    } finally {
      browseBtn.disabled = false;
      icon.className = 'bi bi-folder2-open';
    }
  });

  document.getElementById('btn-chains-load')?.addEventListener('click', () => {
    const root = document.getElementById('chains-root-input').value.trim();
    if (!root) { showToast(t('chains.root_required'), 'warning'); return; }
    _state.chainsRoot = root;
    _state.chainsTManual = null;
    _state.chainsSelectedRow = null;
    fetchChainsReport();
  });
  document.getElementById('chains-root-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('btn-chains-load').click();
  });

  if (_state.chainsRoot && _state.chainsData) {
    _renderChainsResults();
  }
}

/** POST /api/chains_report para la carpeta y el instante t* actuales del estado. */
async function fetchChainsReport() {
  const resultsDiv = document.getElementById('chains-results');
  if (!_state.chainsRoot || !resultsDiv) return;
  resultsDiv.innerHTML = `<div class="text-muted small p-3">${t('chains.loading')}</div>`;

  try {
    const res = await fetch('/api/chains_report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ root: _state.chainsRoot, t_h: _state.chainsTManual }),
    });
    const json = await res.json();
    if (!res.ok || !json.ok) {
      const msg = (json && json.error) || t('toast.unknown_err');
      showToast(msg, 'danger');
      resultsDiv.innerHTML = `<div class="alert alert-danger small mb-0">${escHtml(msg)}</div>`;
      return;
    }
    _state.chainsData = json;
    _renderChainsResults();
  } catch (err) {
    showToast(t('toast.net_err', { msg: err.message }), 'danger');
  }
}

/** Pinta tabla 1 (Σ R_i + cobertura), tabla 2 (Y_z_i desc.) y el diagrama de la fila elegida. */
function _renderChainsResults() {
  const resultsDiv = document.getElementById('chains-results');
  const json = _state.chainsData;
  if (!resultsDiv || !json) return;

  const tCandidatos = json.t_candidatos_h || [];
  const tSel = _state.chainsTManual != null ? _state.chainsTManual : json.t_star_h;
  const tPicoRef = json.t_pico_referencia_h;

  const cobertura = json.cobertura || {};
  const coberturaMsg = cobertura.completa
    ? t('chains.cobertura_completa')
    : t('chains.cobertura_parcial', { n: cobertura.n_seleccionados, total: cobertura.n_total_inventario });

  const fmtExp = v => (v != null ? v.toExponential(4) : '');
  const fmtFix = v => (v != null ? v.toFixed(4) : t('chains.na'));

  const filasT1 = (json.tabla1 || []).map(f => `
    <tr>
      <td>${escHtml(f.isotopo)}</td>
      <td class="font-monospace">${fmtExp(f.c_i)}</td>
      <td class="font-monospace">${fmtExp(f.a_i)}</td>
      <td class="font-monospace">${fmtExp(f.a_ref)}</td>
      <td class="font-monospace">${fmtFix(f.r_i)}</td>
      <td class="small text-muted">${f.nota_cadenas ? escHtml(t('chains.nota_ilegible')) : ''}</td>
    </tr>`).join('');

  const filasT2 = (json.tabla2 || []).map((f, idx) => `
    <tr class="chains-row-select ${idx === _state.chainsSelectedRow ? 'table-primary' : ''}" data-idx="${idx}" style="cursor:pointer">
      <td>${escHtml(f.isotopo)}</td>
      <td class="font-monospace small">${escHtml(f.cadena_label)}</td>
      <td class="font-monospace">${f.p != null ? f.p.toFixed(3) : ''}</td>
      <td class="font-monospace">${f.x_z_i != null ? f.x_z_i.toFixed(4) : ''}</td>
      <td class="font-monospace">${fmtFix(f.r_i)}</td>
      <td class="font-monospace fw-semibold">${fmtFix(f.y_z_i)}</td>
    </tr>`).join('');

  resultsDiv.innerHTML = `
    <div class="row g-2 align-items-end mb-3">
      <div class="col-auto">
        <label class="form-label small mb-1" for="chains-t-select">${t('chains.t_label')}</label>
        <select class="form-select form-select-sm" id="chains-t-select">
          ${tCandidatos.map(tv => `<option value="${tv}" ${Math.abs(tv - tSel) < 1e-9 ? 'selected' : ''}>${tv.toFixed(3)} h${(tPicoRef != null && Math.abs(tv - tPicoRef) < 1e-9) ? ' — ' + t('chains.t_pico_tag') : ''}</option>`).join('')}
        </select>
      </div>
      <div class="col-auto">
        <span class="badge bg-secondary">${t('chains.ifinal_badge', { iso: escHtml(json.ifinal) })}</span>
        <span class="badge bg-secondary">NMAX=${json.nmax}</span>
        <span class="badge bg-secondary">PCNT=${json.pcnt}</span>
        <span class="badge bg-secondary" style="cursor:help" title="${escAttr(json.reference_folder || '')}">
          ${t('chains.reference_badge', { folder: escHtml(_folderBasename(json.reference_folder)) })}
        </span>
      </div>
    </div>
    <div class="small text-muted mb-3">
      <i class="bi bi-info-circle me-1"></i>${t('chains.reference_note')}
    </div>

    <h6 class="mt-3">${t('chains.tabla1_title')}</h6>
    <div class="table-responsive mb-1">
      <table class="table table-sm table-hover">
        <thead><tr>
          <th>${t('chains.th_isotopo')}</th><th>C<sub>i</sub> [át/cm³]</th>
          <th>A<sub>i</sub>(t*) [Bq/cm³]</th><th>A<sub>ref</sub>(t*) [Bq/cm³]</th><th>R<sub>i</sub></th>
          <th>${t('chains.th_nota')}</th>
        </tr></thead>
        <tbody>
          ${filasT1}
          <tr class="table-secondary fw-semibold">
            <td colspan="4">Σ R<sub>i</sub></td>
            <td class="font-monospace">${fmtFix(json.suma_r_i)}</td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="small text-muted mb-3">${coberturaMsg}</div>

    <div class="d-flex justify-content-between align-items-center mb-2">
      <h6 class="mb-0">${t('chains.tabla2_title')}</h6>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-secondary btn-sm" id="btn-export-chains1">
          <i class="bi bi-download me-1"></i>${t('chains.export_tabla1')}
        </button>
        <button class="btn btn-outline-secondary btn-sm" id="btn-export-chains2">
          <i class="bi bi-download me-1"></i>${t('chains.export_tabla2')}
        </button>
      </div>
    </div>
    <div class="table-responsive mb-1">
      <table class="table table-sm table-hover">
        <thead><tr>
          <th>${t('chains.th_isotopo')}</th><th>${t('chains.th_cadena')}</th>
          <th>P [%]</th><th>X<sub>z,i</sub></th><th>R<sub>i</sub></th><th>Y<sub>z,i</sub></th>
        </tr></thead>
        <tbody id="chains-tabla2-body">${filasT2}</tbody>
      </table>
    </div>
    <div class="small text-muted mb-3">${t('chains.ptot_note')}</div>
    <div class="small text-muted mb-3">${t('chains.row_hint')}</div>

    <div id="chains-diagrama"></div>
  `;

  document.getElementById('chains-t-select')?.addEventListener('change', e => {
    _state.chainsTManual = parseFloat(e.target.value);
    fetchChainsReport();
  });
  document.querySelectorAll('#chains-tabla2-body tr.chains-row-select').forEach(tr => {
    tr.addEventListener('click', () => {
      const idx = parseInt(tr.dataset.idx, 10);
      _state.chainsSelectedRow = (_state.chainsSelectedRow === idx) ? null : idx;
      _renderChainsResults();
    });
  });
  document.getElementById('btn-export-chains1')?.addEventListener('click', exportChainsTabla1CSV);
  document.getElementById('btn-export-chains2')?.addEventListener('click', exportChainsTabla2CSV);

  if (_state.chainsSelectedRow != null && json.tabla2[_state.chainsSelectedRow]) {
    _renderChainsDiagram(json.tabla2[_state.chainsSelectedRow]);
  }
}

/** T½ legible (d/h/s según magnitud) o "estable"/"desconocido" (Fase 5). */
function _formatT12Chains(nodo) {
  if (!nodo) return '';
  if (nodo.estable) return t('chains.estable');
  if (!nodo.conocido || nodo.t12_s == null) return t('chains.t12_desconocido');
  const h = nodo.t12_s / 3600;
  const d = h / 24;
  if (d >= 1) return `${d.toExponential(3)} d`;
  if (h >= 1) return `${h.toExponential(3)} h`;
  return `${nodo.t12_s.toExponential(3)} s`;
}

/** Diagrama v1 (Fase 5): la cadena elegida como secuencia lineal de nodos+aristas. */
function _renderChainsDiagram(fila) {
  const div = document.getElementById('chains-diagrama');
  if (!div) return;
  if (!fila || !fila.diagrama) { div.innerHTML = ''; return; }

  const { nodos, aristas } = fila.diagrama;
  const parts = [];
  (nodos || []).forEach((n, i) => {
    parts.push(`
      <div class="text-center px-2">
        <div class="fw-semibold font-monospace border rounded px-2 py-1 bg-white">${escHtml(n.nombre)}</div>
        <div class="small text-muted mt-1">${escHtml(_formatT12Chains(n))}</div>
      </div>`);
    if (aristas && i < aristas.length) {
      const a = aristas[i];
      const val = a.xsec != null ? `XSEC=${a.xsec.toExponential(4)}`
                : (a.delta != null ? `DELTA=${a.delta.toExponential(4)}` : '');
      parts.push(`
        <div class="text-center px-2">
          <div class="small fw-semibold">${escHtml(a.proceso)}</div>
          <div><i class="bi bi-arrow-right fs-5"></i></div>
          <div class="small text-muted">${val}</div>
        </div>`);
    }
  });

  div.innerHTML = `
    <h6 class="mt-3">${t('chains.diagram_title', { iso: escHtml(fila.isotopo), n: fila.cadena_idx })}</h6>
    <div class="d-flex flex-wrap align-items-center gap-1 p-3 border rounded bg-light">${parts.join('')}</div>
  `;
}

function exportChainsTabla1CSV() {
  const json = _state.chainsData;
  if (!json) return;
  const rows = (json.tabla1 || []).map(f => [f.isotopo, f.c_i, f.a_i, f.a_ref, f.r_i, f.nota_cadenas || '']);
  rows.push([t('chains.suma_row'), null, null, null, json.suma_r_i, '']);
  const headers = [t('chains.th_isotopo'), 'C_i [at/cm3]', 'A_i(t*) [Bq/cm3]', 'A_ref(t*) [Bq/cm3]', 'R_i', t('chains.th_nota')];
  const meta = [
    `# root: ${_state.chainsRoot || ''}`,
    `# IFINAL: ${json.ifinal}`,
    `# t*: ${json.t_star_h} h (${json.t_star_fuente})`,
  ].join('\r\n');
  const opts = ACABExport.preset(activeCsv());
  const csv = meta + '\r\n' + ACABExport.toCSV(rows, headers, opts);
  ACABExport.download(`chains_tabla1_${ACABExport.slug(json.ifinal)}.csv`, csv);
}

function exportChainsTabla2CSV() {
  const json = _state.chainsData;
  if (!json) return;
  const rows = (json.tabla2 || []).map(f => [f.isotopo, f.cadena_label, f.p, f.x_z_i, f.r_i, f.y_z_i]);
  const headers = [t('chains.th_isotopo'), t('chains.th_cadena'), 'P [%]', 'X_z_i', 'R_i', 'Y_z_i'];
  const meta = [
    `# root: ${_state.chainsRoot || ''}`,
    `# IFINAL: ${json.ifinal}`,
    `# NMAX: ${json.nmax}  PCNT: ${json.pcnt}`,
    `# t*: ${json.t_star_h} h (${json.t_star_fuente})`,
  ].join('\r\n');
  const opts = ACABExport.preset(activeCsv());
  const csv = meta + '\r\n' + ACABExport.toCSV(rows, headers, opts);
  ACABExport.download(`chains_tabla2_${ACABExport.slug(json.ifinal)}.csv`, csv);
}

function _renderActivityChart(divId, cfg, simulations) {
  const series   = cfg.series || [];
  const doIrr    = _state.showIrr || Boolean(cfg.mostrar_irr);
  const simNames = Object.keys(simulations);
  const multiIso = series.length > 1;
  const traces   = [];
  const shapes   = [];
  let irrLineAdded = false;

  const uL = unitLabel();

  simNames.forEach((simName, simIdx) => {
    const sim   = simulations[simName];
    const color = PALETTE[simIdx % PALETTE.length];
    const T_irr = sim.T_IRR_h;

    // Per-simulation conversion factor. null → not convertible under the active
    // unit (e.g. MBq/g on a sim without density): skip its series.
    const factor = convFactor(sim);
    if (factor === null) return;

    series.forEach((serie, isoIdx) => {
      const iso   = serie.iso;
      const label = serie.label || isoLabel(iso);
      const tIrr  = sim.t_irr;
      const tCool = sim.t_cool.map(t => T_irr + t);
      const yIrr  = sim.datos_irr_Bq[iso] || [];
      const yCool = sim.datos_cool[iso]    || [];

      const lbl = multiIso ? `${simName} – ${label}` : simName;

      const dashes = ['solid', 'dot', 'dash', 'dashdot'];
      const dashIrr  = dashes[isoIdx % dashes.length];
      const dashCool = isoIdx === 0 ? 'dash' : dashes[(isoIdx + 1) % dashes.length];

      const irrName  = `${lbl} (${t('charts.irr_suffix')})`;
      const coolName = doIrr ? `${lbl} (${t('charts.cool_suffix')})` : lbl;

      if (doIrr && yIrr.some(v => v > 0)) {
        const { xF, yF } = _filterPositive(tIrr, yIrr);
        traces.push({
          x: xF, y: yF.map(v => v * factor),
          name: irrName,
          mode: 'lines+markers',
          type: 'scatter',
          line: { color, width: 2, dash: dashIrr },
          marker: { size: 5 },
          hovertemplate: `t = %{x:.3g} h<br>A = %{y:.3e} ${uL}<extra>` + escHtml(irrName) + '</extra>',
        });
      }

      const xCool = doIrr ? tCool : sim.t_cool;
      if (yCool.some(v => v > 0)) {
        const { xF, yF } = _filterPositive(xCool, yCool);
        traces.push({
          x: xF, y: yF.map(v => v * factor),
          name: coolName,
          mode: 'lines+markers',
          type: 'scatter',
          line: { color, width: 2, dash: doIrr ? dashCool : dashIrr },
          marker: { size: 5, symbol: doIrr ? 'circle-open' : 'circle' },
          hovertemplate: `t = %{x:.3g} h<br>A = %{y:.3e} ${uL}<extra>` +
            escHtml(coolName) + '</extra>',
        });
      }
    });

    if (doIrr && T_irr > 0 && !irrLineAdded) {
      shapes.push({
        type: 'line',
        x0: T_irr, x1: T_irr,
        y0: 0, y1: 1, yref: 'paper',
        line: { color: '#333', width: 1.5, dash: 'dash' },
      });
      irrLineAdded = true;
    }
  });

  const annotations = [];
  if (irrLineAdded) {
    const T_irr0 = simulations[simNames[0]].T_IRR_h;
    annotations.push({
      x: T_irr0, y: 1, yref: 'paper',
      text: t('charts.end_irr', { t: T_irr0.toFixed(2) }),
      showarrow: false, xanchor: 'left', yanchor: 'top',
      font: { size: 9, color: '#555' }, xshift: 4,
    });
  }

  const layout = {
    xaxis: {
      title: doIrr ? t('charts.ax_time') : t('charts.ax_time_cool'),
      showgrid: true, gridcolor: '#eee', zeroline: false,
    },
    yaxis: {
      title: t('charts.ax_activity', { unit: uL }),
      type: 'log', showgrid: true, gridcolor: '#eee',
      exponentformat: 'e', zeroline: false,
    },
    shapes,
    annotations,
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1, font: { size: 9 } },
    margin: { t: 20, b: 50, l: 80, r: 20 },
    hovermode: 'closest',
    plot_bgcolor: '#fafafa',
    paper_bgcolor: '#fff',
  };

  if (traces.length === 0) {
    const noDataDiv = document.getElementById(divId);
    if (noDataDiv) {
      noDataDiv.innerHTML = `<div class="d-flex align-items-center justify-content-center h-100 text-muted small py-4">${t('charts.no_data')}</div>`;
    }
    return;
  }

  Plotly.newPlot(divId, traces, layout, { responsive: true, displayModeBar: true });
}

// Filter out zero/negative values for log-safe Plotly rendering
function _filterPositive(x, y) {
  const xF = [], yF = [];
  for (let i = 0; i < x.length; i++) {
    if (y[i] > 0) { xF.push(x[i]); yF.push(y[i]); }
  }
  return { xF, yF };
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 3: Isotope Detailed Report  (F5)
// ─────────────────────────────────────────────────────────────────────────────
function renderIsotopoReport() {
  const container = document.getElementById('i131-report-container');
  const iso  = _state.selectedIsotopo;
  const json = _state.isotopoReport;
  if (!iso || !json) return;

  const report = json.informe;
  const props  = report.nuclear_props;
  const sims   = _state.analysisData.simulations;
  const label  = isoLabel(iso);

  const T12_d    = props.T12_d   ? props.T12_d.toFixed(4)       : '—';
  const T12_h    = props.T12_h   ? props.T12_h.toFixed(3)       : '—';
  const T12_s    = props.T12_s   ? props.T12_s.toExponential(4) : '—';
  const lam_s    = props.lam_s   ? props.lam_s.toExponential(6) : '—';
  const A_esp    = props.A_esp   ? props.A_esp.toExponential(4) : '—';
  const A_esp_Ci = props.A_esp   ? (props.A_esp / 3.7e10).toExponential(4) : '—';

  // Derive Z and A from key
  const elemMatch = iso.match(/^([A-Z]{1,2})/);
  const elem = elemMatch ? elemMatch[1] : '';
  const Z = Z_BY_ELEM[elem] !== undefined ? Z_BY_ELEM[elem] : '—';
  const massMatch = iso.match(/(\d+)/);
  const A = massMatch ? massMatch[1] : '—';

  const hasGamma = Array.isArray(report.gamma_spectrum) && report.gamma_spectrum.length > 0;
  const isI131   = iso === 'I131';

  // Extra rows shown only for I131
  const extraPropRows = isI131 ? `
    <tr><th>${t('report.decay_mode')}</th><td>${t('report.decay_val')}</td></tr>
    <tr><th>${t('report.gamma_diag')}</th><td>${t('report.gamma_diag_val')}</td></tr>
  ` : '';

  container.innerHTML = `

    <!-- Export toolbar (F3) -->
    <div class="d-flex justify-content-end mb-3">
      <button class="btn btn-outline-secondary btn-sm" id="btn-export-report">
        <i class="bi bi-download me-1"></i>${t('export.csv')}
      </button>
    </div>

    <!-- ── Section 1: Nuclear properties + Peak summary ── -->
    <div class="row g-3 mb-3">

      <!-- Nuclear properties -->
      <div class="col-lg-6">
        <div class="card h-100 shadow-sm">
          <div class="card-header bg-warning bg-opacity-25">
            <i class="bi bi-radioactive text-warning me-1"></i>
            <strong>${t('report.s1', { label })}</strong>
          </div>
          <div class="card-body p-0">
            <table class="table table-sm prop-table mb-0">
              <tbody>
                <tr><th>${t('report.symbol')}</th><td>${label} &nbsp; <span class="text-muted small">(${escHtml(iso)})</span></td></tr>
                <tr><th>${t('report.za')}</th><td class="font-monospace">${Z} / ${A}</td></tr>
                <tr><th>${t('report.halflife')}</th>
                    <td class="font-monospace">${T12_d} d&nbsp;=&nbsp;${T12_h} h&nbsp;=&nbsp;${T12_s} s</td></tr>
                <tr><th>${t('report.lambda')}</th><td class="font-monospace">${lam_s} s⁻¹</td></tr>
                ${extraPropRows}
                <tr><th>${t('report.spec_act')}<br><span class="fw-normal">${t('report.spec_act_sub', { label })}</span></th>
                    <td class="font-monospace">${A_esp} Bq/g<br>${A_esp_Ci} Ci/g</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Peak per simulation -->
      <div class="col-lg-6">
        <div class="card h-100 shadow-sm">
          <div class="card-header bg-danger bg-opacity-10">
            <i class="bi bi-graph-up-arrow me-1 text-danger"></i>
            <strong>${t('report.s2')}</strong>
          </div>
          <div class="card-body p-0">
            <table class="table table-sm mb-0">
              <thead class="table-dark">
                <tr>
                  <th>${t('report.th_sim')}</th>
                  <th>${t('report.th_apico', { unit: unitLabel() })}</th>
                  <th>${t('report.th_tpico')}</th>
                  <th>${t('report.th_fase')}</th>
                </tr>
              </thead>
              <tbody>
                ${Object.entries(report.simulations).map(([name, s], i) => {
                  const Ap = s.A_pico > 0 ? fmtA(s.A_pico, sims[name]) : '—';
                  const tp = s.t_pico !== null && s.t_pico !== undefined ? s.t_pico.toFixed(3) : '—';
                  const phaseCls = s.fase === 'irradiación' ? 'badge-phase-irr' : 'badge-phase-cool';
                  return `<tr>
                    <td>
                      <span class="sim-dot me-1" style="background:${PALETTE[i % PALETTE.length]}"></span>
                      <small class="fw-semibold">${escHtml(name)}</small>
                    </td>
                    <td class="font-monospace text-danger fw-bold small">${Ap}</td>
                    <td class="font-monospace small">${tp}</td>
                    <td><span class="badge ${phaseCls}" style="font-size:0.7rem">${phaseLabel(s.fase)}</span></td>
                  </tr>`;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Section 3: Activity evolution chart ── -->
    <div class="card shadow-sm mb-3">
      <div class="card-header bg-primary bg-opacity-10 d-flex justify-content-between align-items-center flex-wrap gap-2">
        <div>
          <i class="bi bi-graph-up me-1 text-primary"></i>
          <strong>${t('report.s3', { label })}</strong>
          <span class="text-muted small ms-2">${t('report.s3_sub')}</span>
        </div>
        <button class="btn btn-outline-secondary btn-sm" id="btn-load-refdata">
          <i class="bi bi-file-earmark-arrow-up me-1"></i>${t('refdata.load_btn')}
        </button>
      </div>
      <div class="card-body p-2">
        <div id="i131-time-chart" class="plotly-chart-lg"></div>
        <div id="refdata-list-container" class="mt-2 px-1"></div>
      </div>
    </div>

    <!-- ── Section 3b: Reference-data deviation metrics (Fase 4) ── -->
    <div id="refdata-metrics-container" class="mb-3"></div>

    <!-- ── Section 4: Production-optimisation metrics (Fase 5) ── -->
    <div id="metrics-container" class="mb-3"></div>

    ${hasGamma ? `
    <!-- ── Section 5: Gamma spectrum ── -->
    <div class="row g-3 mb-3">
      <div class="col-lg-7">
        <div class="card shadow-sm h-100">
          <div class="card-header bg-success bg-opacity-10">
            <i class="bi bi-bar-chart-steps me-1 text-success"></i>
            <strong>${t('report.s4', { label, n: 5 })}</strong>
            <span class="text-muted small ms-2">${t('report.s4_sub')}</span>
          </div>
          <div class="card-body p-2">
            <div id="i131-gamma-chart" class="plotly-chart"></div>
          </div>
        </div>
      </div>
      <div class="col-lg-5">
        <div class="card shadow-sm h-100">
          <div class="card-header bg-success bg-opacity-10">
            <i class="bi bi-table me-1 text-success"></i>
            <strong>${t('report.gamma_lines')}</strong>
          </div>
          <div class="card-body p-0">
            <div class="gamma-table-wrapper">
              <table class="table table-sm table-hover mb-0">
                <thead>
                  <tr><th>${t('report.th_energy')}</th><th>${t('report.th_intensity')}</th><th></th></tr>
                </thead>
                <tbody>
                  ${report.gamma_spectrum
                    .slice()
                    .sort((a, b) => b[1] - a[1])
                    .map(([e, intens]) => {
                      const rowCls = intens >= 80 ? 'gamma-main' : intens >= 5 ? 'gamma-strong' : '';
                      const badge  = intens >= 80
                        ? `<span class="badge bg-danger" style="font-size:0.65rem">${t('report.badge_main')}</span>`
                        : intens >= 5
                        ? `<span class="badge bg-warning text-dark" style="font-size:0.65rem">${t('report.badge_strong')}</span>`
                        : '';
                      return `<tr class="${rowCls}">
                        <td class="font-monospace">${e.toFixed(3)}</td>
                        <td class="font-monospace">${intens.toFixed(3)}</td>
                        <td>${badge}</td>
                      </tr>`;
                    }).join('')}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
    ` : ''}

    <!-- ── Section 5 (or 4 without gamma): Activity data tables per simulation ── -->
    <div class="card shadow-sm">
      <div class="card-header bg-secondary bg-opacity-10">
        <i class="bi bi-table me-1"></i>
        <strong>${t('report.s5', { n: hasGamma ? 6 : 5, label })}</strong>
      </div>
      <div class="card-body">
        <div id="i131-activity-tables"></div>
      </div>
    </div>
  `;

  // Render Plotly charts
  _renderIsotopoTimeChart(iso, sims, report.metricas || {});
  if (hasGamma) _renderGammaChart(report.gamma_spectrum);
  _renderIsotopoActivityTables(iso, sims);

  // Fase 4: datos de referencia superpuestos + métricas de desviación
  renderRefDataList();
  renderRefDataMetrics();

  // Fase 5: métricas de optimización de producción (saturación, rendimiento, pureza)
  _renderMetricasOptimizacion(iso, sims, report);

  const rbtn = document.getElementById('btn-export-report');
  if (rbtn) rbtn.addEventListener('click', exportReportCSV);
  const loadBtn = document.getElementById('btn-load-refdata');
  if (loadBtn) loadBtn.addEventListener('click', () => document.getElementById('refdata-file-input').click());
}

function _renderIsotopoTimeChart(iso, simulations, metricas) {
  const traces = [];
  const shapes = [];
  let irrLineAdded = false;
  const label = isoLabel(iso);
  const uL = unitLabel();

  Object.entries(simulations).forEach(([name, sim], i) => {
    const color = PALETTE[i % PALETTE.length];
    const T_irr = sim.T_IRR_h;
    const tIrr  = sim.t_irr;
    const tCool = sim.t_cool.map(t => T_irr + t);
    const yIrr  = sim.datos_irr_Bq[iso] || [];
    const yCool = sim.datos_cool[iso]    || [];

    // Skip this sim's series if not convertible under the active unit.
    const factor = convFactor(sim);
    if (factor === null) return;

    const irrName  = `${name} (${t('charts.irr_suffix')})`;
    const coolName = `${name} (${t('charts.cool_suffix')})`;

    if (yIrr.some(v => v > 0)) {
      const { xF, yF } = _filterPositive(tIrr, yIrr);
      traces.push({
        x: xF, y: yF.map(v => v * factor), name: irrName,
        mode: 'lines+markers', type: 'scatter',
        line: { color, width: 2 }, marker: { size: 5 },
        hovertemplate: `t = %{x:.3g} h<br>A = %{y:.3e} ${uL}<extra>` + escHtml(irrName) + '</extra>',
      });
    }
    if (yCool.some(v => v > 0)) {
      const { xF, yF } = _filterPositive(tCool, yCool);
      traces.push({
        x: xF, y: yF.map(v => v * factor), name: coolName,
        mode: 'lines+markers', type: 'scatter',
        line: { color, width: 2, dash: 'dash' }, marker: { size: 5, symbol: 'circle-open' },
        hovertemplate: `t = %{x:.3g} h<br>A = %{y:.3e} ${uL}<extra>` + escHtml(coolName) + '</extra>',
      });
    }

    // Fase 5: curva de saturación teórica A_teo(t) = A_sat·(1−e^(−λt)),
    // solo en la fase de irradiación (ver report Section 4 / metrics-container).
    const sat = metricas && metricas[name] && metricas[name].saturacion;
    if (sat && sat.puntos && sat.puntos.length) {
      const satName = `${name} (${t('metrics.sat_trace')})`;
      traces.push({
        x: sat.puntos.map(p => p[0]), y: sat.puntos.map(p => p[1] * factor),
        name: satName,
        mode: 'lines', type: 'scatter',
        line: { color, width: 1.5, dash: 'dot' },
        hovertemplate: `t = %{x:.3g} h<br>A_teo = %{y:.3e} ${uL}<extra>` + escHtml(satName) + '</extra>',
      });
    }

    if (!irrLineAdded) {
      shapes.push({
        type: 'line', x0: T_irr, x1: T_irr, y0: 0, y1: 1, yref: 'paper',
        line: { color: '#333', width: 1.5, dash: 'dash' },
      });
      irrLineAdded = true;
    }
  });

  // Fase 4: superponer las series de referencia importadas para este isótopo.
  // Huecos = experimental (entra en las métricas); rellenos = computacional
  // de referencia (solo se dibuja). Convertidas con la densidad/volumen de
  // SU simulación de referencia, en la unidad activa (igual que las curvas ACAB).
  const REF_COLORS = ['#212121', '#5d4037', '#37474f', '#4a148c'];
  (_state.refSeries || []).filter(s => s.isotopo === iso).forEach((s, idx) => {
    const refSim = simulations[s.refSimName];
    if (!refSim) return;
    const factor = convFactor(refSim);
    if (factor === null) return;
    const color = REF_COLORS[idx % REF_COLORS.length];
    // F12 del BACKLOG: p.t_h vive en tiempo desde el inicio de SU fase (sin
    // desplazar, ver confirmRefDataImport); este gráfico combina irradiación
    // + enfriamiento en un único eje absoluto (como el resto de trazas), así
    // que el desplazamiento +T_irr se aplica SOLO aquí, para pintar — nunca
    // se guarda desplazado.
    const xShift = s.fase === 'enfriamiento' ? refSim.T_IRR_h : 0;
    const trace = {
      x: s.points.map(p => p.t_h + xShift),
      y: s.points.map(p => p.A_bqcm3 * factor),
      name: s.descripcion,
      mode: 'markers',
      type: 'scatter',
      marker: {
        size: 8,
        symbol: s.tipo === 'experimental' ? 'circle-open' : 'circle',
        color, line: { width: 2, color },
      },
      hovertemplate: `t = %{x:.3g} h<br>A = %{y:.3e} ${uL}<extra>` + escHtml(s.descripcion) + '</extra>',
    };
    if (s.points.some(p => p.A_err_bqcm3 != null)) {
      trace.error_y = {
        type: 'data',
        array: s.points.map(p => (p.A_err_bqcm3 != null ? p.A_err_bqcm3 * factor : 0)),
        visible: true,
      };
    }
    traces.push(trace);
  });

  Plotly.newPlot('i131-time-chart', traces, {
    xaxis: { title: t('charts.ax_time'), showgrid: true, gridcolor: '#eee', zeroline: false },
    yaxis: {
      title: t('report.ax_activity', { label, unit: unitLabel() }),
      type: 'log', showgrid: true, gridcolor: '#eee', exponentformat: 'e', zeroline: false,
    },
    shapes,
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1, font: { size: 9 } },
    margin: { t: 20, b: 50, l: 80, r: 20 },
    hovermode: 'closest',
    plot_bgcolor: '#fafafa', paper_bgcolor: '#fff',
  }, { responsive: true });
}

function _renderGammaChart(gammaData) {
  const sorted      = gammaData.slice().sort((a, b) => a[0] - b[0]);
  const energies    = sorted.map(d => d[0]);
  const intensities = sorted.map(d => d[1]);
  const colors      = intensities.map(i => i >= 80 ? '#c62828' : i >= 5 ? '#1565c0' : '#78909c');

  Plotly.newPlot('i131-gamma-chart', [{
    x: energies, y: intensities,
    type: 'bar', width: 12,
    marker: { color: colors },
    hovertemplate: '%{x:.3f} keV<br>%{y:.3f} ' + t('report.per_decay') + '<extra></extra>',
  }], {
    xaxis: { title: t('report.gamma_ax_energy'), range: [50, 820], showgrid: true, gridcolor: '#eee' },
    yaxis: { title: t('report.gamma_ax_intensity'), type: 'log', exponentformat: 'e', showgrid: true, gridcolor: '#eee' },
    margin: { t: 10, b: 50, l: 70, r: 20 },
    plot_bgcolor: '#fafafa', paper_bgcolor: '#fff',
    annotations: [{
      x: 364.489, y: 81.5,
      text: '364.5 keV<br>81.5 %',
      showarrow: true, arrowhead: 2, arrowsize: 1,
      xanchor: 'right', yanchor: 'bottom',
      font: { size: 9 },
    }],
  }, { responsive: true });
}

function _renderIsotopoActivityTables(iso, simulations) {
  const container = document.getElementById('i131-activity-tables');
  const label = isoLabel(iso);
  let html = '';

  Object.entries(simulations).forEach(([name, sim], i) => {
    const color = PALETTE[i % PALETTE.length];
    const T_irr = sim.T_IRR_h;
    const tIrr  = sim.t_irr;
    const yIrr  = sim.datos_irr_Bq[iso] || [];
    const tCool = sim.t_cool;
    const yCool = sim.datos_cool[iso] || [];

    html += `
      <div class="mb-4">
        <div class="section-heading">
          <span class="sim-dot me-1" style="background:${color}"></span>
          ${escHtml(name)}
          <span class="text-muted fw-normal">
            ${t('report.sim_flux_meta', { tirr: T_irr.toFixed(2), phi: fmtSci(sim.PHI) })}
            ${sim.densidad_g_cm3 != null
              ? ' | ' + t('units.density_val', { d: sim.densidad_g_cm3.toFixed(5) })
              : ''}
          </span>
        </div>
        <div class="row g-3">
    `;

    if (yIrr.length > 0) {
      const irrRows = tIrr.map((t, k) =>
        `<tr><td>${t.toFixed(4)}</td><td>${yIrr[k] > 0 ? fmtA(yIrr[k], sim) : '—'}</td></tr>`
      ).join('');
      html += `
        <div class="col-md-6">
          <p class="small text-muted mb-1">
            <strong>${t('report.irr')}</strong>
            ${t('report.irr_src')}
          </p>
          <div class="activity-table-wrapper">
            <table class="table table-sm table-hover mb-0 font-monospace" style="font-size:0.8rem">
              <thead><tr><th>t<sub>irr</sub> [h]</th><th>${t('report.th_tirr_a', { label, unit: unitLabel() })}</th></tr></thead>
              <tbody>${irrRows}</tbody>
            </table>
          </div>
        </div>
      `;
    }

    if (yCool.length > 0 && yCool.some(v => v > 0)) {
      const coolRows = tCool.map((t, k) =>
        `<tr><td>${t.toFixed(4)}</td><td>${yCool[k] > 0 ? fmtA(yCool[k], sim) : '—'}</td></tr>`
      ).join('');
      html += `
        <div class="col-md-6">
          <p class="small text-muted mb-1">
            <strong>${t('report.cool')}</strong>
            ${t('report.cool_src')}
          </p>
          <div class="activity-table-wrapper">
            <table class="table table-sm table-hover mb-0 font-monospace" style="font-size:0.8rem">
              <thead><tr><th>t<sub>cool</sub> [h]</th><th>${t('report.th_tirr_a', { label, unit: unitLabel() })}</th></tr></thead>
              <tbody>${coolRows}</tbody>
            </table>
          </div>
        </div>
      `;
    } else {
      html += `
        <div class="col-md-6">
          <div class="alert alert-light small py-2 mb-0">
            ${t('report.not_in_cool', { label })}
          </div>
        </div>
      `;
    }

    html += '</div></div>';
  });

  container.innerHTML = html || `<div class="alert alert-warning">${t('report.no_data', { label })}</div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 3, Section 4: Métricas de optimización de producción (Fase 5)
// Cálculo (saturación, rendimiento, pureza) vive en el servidor
// (fort_analyzer.calcular_saturacion/calcular_rendimiento/calcular_pureza),
// junto con calcular_pico; aquí solo se renderiza informe.metricas.
// ─────────────────────────────────────────────────────────────────────────────
function _renderMetricasOptimizacion(iso, simulations, report) {
  const container = document.getElementById('metrics-container');
  if (!container) return;
  const metricas = report.metricas || {};
  const label = isoLabel(iso);
  const uL = unitLabel();

  // ── Saturación teórica ──────────────────────────────────────────────────
  const satBlocks = Object.entries(simulations).map(([name, sim], i) => {
    const sat = metricas[name] && metricas[name].saturacion;
    const dot = `<span class="sim-dot me-1" style="background:${PALETTE[i % PALETTE.length]}"></span>`;
    if (!sat) {
      return `<div class="mb-2">${dot}<small class="fw-semibold">${escHtml(name)}</small>
        <span class="text-muted small">— ${t('metrics.sat_na')}</span></div>`;
    }
    const rows = sat.tabla.map(r => `
      <tr>
        <td>${r.pct.toFixed(0)} %</td>
        <td class="font-monospace">${r.t_x_h != null ? r.t_x_h.toFixed(4) : '—'}</td>
        <td class="text-center">${r.alcanzable
          ? '<i class="bi bi-check-circle-fill text-success"></i>'
          : '<i class="bi bi-x-circle text-secondary"></i>'}</td>
      </tr>`).join('');
    return `
      <div class="mb-3">
        <div class="mb-1">${dot}<small class="fw-semibold">${escHtml(name)}</small>
          <span class="text-muted small">— A<sub>sat</sub> = ${fmtA(sat.A_sat, sim)} ${uL}</span></div>
        <table class="table table-sm mb-0" style="font-size:0.8rem;max-width:340px">
          <thead><tr><th>${t('metrics.sat_th_pct')}</th><th>${t('metrics.sat_th_tx')}</th><th>${t('metrics.sat_th_ok')}</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }).join('');

  // ── Rendimiento ──────────────────────────────────────────────────────────
  const rendRows = Object.entries(simulations).map(([name, sim], i) => {
    const r = metricas[name] && metricas[name].rendimiento;
    if (!r) {
      return `<tr><td colspan="5" class="small text-muted">${escHtml(name)} — ${t('metrics.rend_na')}</td></tr>`;
    }
    const badge = r.compensa_seguir
      ? `<span class="badge bg-success">${t('metrics.rend_si')}</span>`
      : `<span class="badge bg-secondary">${t('metrics.rend_no')}</span>`;
    return `
      <tr>
        <td><span class="sim-dot me-1" style="background:${PALETTE[i % PALETTE.length]}"></span><small class="fw-semibold">${escHtml(name)}</small></td>
        <td class="font-monospace small">${fmtA(r.rendimiento_medio, sim)}</td>
        <td class="font-monospace small">${fmtA(r.A_fin, sim)}</td>
        <td class="font-monospace small">${fmtA(r.ganancia_marginal, sim)}</td>
        <td class="text-center">${badge}</td>
      </tr>`;
  }).join('');

  // ── Pureza: checklist editable + tabla por simulación ────────────────────
  const disponibles = report.isotopos_disponibles || [];
  const usada = new Set(report.isotopos_impureza_usada || report.isotopos_impureza_default || []);
  const checklist = disponibles.map(k => `
    <div class="form-check form-check-inline">
      <input class="form-check-input pureza-chk" type="checkbox" value="${escAttr(k)}"
             id="pureza-chk-${escAttr(k)}" ${usada.has(k) ? 'checked' : ''}>
      <label class="form-check-label small" for="pureza-chk-${escAttr(k)}">
        ${escHtml(isoLabel(k))} <span class="text-muted">(${escHtml(k)})</span>
      </label>
    </div>`).join('');

  const purBlocks = Object.entries(simulations).map(([name, sim], i) => {
    const p = metricas[name] && metricas[name].pureza;
    const dot = `<span class="sim-dot me-1" style="background:${PALETTE[i % PALETTE.length]}"></span>`;
    if (!p) {
      return `<div class="mb-2">${dot}<small class="fw-semibold">${escHtml(name)}</small>
        <span class="text-muted small">— ${t('metrics.pureza_na')}</span></div>`;
    }
    const rows = p.contribuciones.slice().sort((a, b) => (b.A || 0) - (a.A || 0)).map(c => `
      <tr class="${c.iso === iso ? 'table-warning' : ''}">
        <td>${escHtml(isoLabel(c.iso))} <span class="text-muted small">(${escHtml(c.iso)})</span></td>
        <td class="font-monospace small">${c.A != null ? fmtA(c.A, sim) : '—'}</td>
        <td class="font-monospace small">${c.pct != null ? c.pct.toFixed(2) + ' %' : '—'}</td>
      </tr>`).join('');
    return `
      <div class="mb-3">
        <div class="mb-1">${dot}<small class="fw-semibold">${escHtml(name)}</small></div>
        <table class="table table-sm mb-0" style="font-size:0.8rem;max-width:420px">
          <thead><tr><th>${t('metrics.pureza_th_iso')}</th><th>${t('metrics.pureza_th_a', { unit: uL })}</th><th>${t('metrics.pureza_th_pct')}</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }).join('');

  container.innerHTML = `
    <div class="card shadow-sm">
      <div class="card-header bg-info bg-opacity-10">
        <i class="bi bi-speedometer2 me-1 text-info"></i>
        <strong>${t('metrics.title', { n: 4, label })}</strong>
      </div>
      <div class="card-body">

        <div class="mb-4">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-1">
            <div class="section-heading mb-0">${t('metrics.sat_title')}</div>
            <button class="btn btn-outline-secondary btn-sm" id="btn-export-sat">
              <i class="bi bi-download me-1"></i>${t('export.csv')}
            </button>
          </div>
          <p class="small text-muted">${t('metrics.sat_desc')}</p>
          ${satBlocks || `<span class="text-muted small">${t('metrics.sat_na')}</span>`}
        </div>

        <div class="mb-4">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-1">
            <div class="section-heading mb-0">${t('metrics.rend_title')}</div>
            <button class="btn btn-outline-secondary btn-sm" id="btn-export-rend">
              <i class="bi bi-download me-1"></i>${t('export.csv')}
            </button>
          </div>
          <p class="small text-muted">${t('metrics.rend_desc')}</p>
          <div class="table-responsive">
            <table class="table table-sm table-hover mb-0">
              <thead class="table-dark">
                <tr>
                  <th>${t('report.th_sim')}</th>
                  <th>${t('metrics.rend_th_medio', { unit: uL })}</th>
                  <th>${t('metrics.rend_th_afin', { unit: uL })}</th>
                  <th>${t('metrics.rend_th_marginal', { unit: uL })}</th>
                  <th>${t('metrics.rend_th_compensa')}</th>
                </tr>
              </thead>
              <tbody>${rendRows}</tbody>
            </table>
          </div>
        </div>

        <div>
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-1">
            <div class="section-heading mb-0">${t('metrics.pureza_title')}</div>
            <button class="btn btn-outline-secondary btn-sm" id="btn-export-pureza">
              <i class="bi bi-download me-1"></i>${t('export.csv')}
            </button>
          </div>
          <p class="small text-muted mb-2">
            ${t('metrics.pureza_desc')}
            <i class="bi bi-info-circle text-muted ms-1" title="${escAttr(t('metrics.pureza_tooltip'))}"></i>
          </p>
          <div class="mb-2">${checklist}</div>
          <button class="btn btn-primary btn-sm mb-3" id="btn-recalc-pureza">
            <i class="bi bi-arrow-repeat me-1"></i>${t('metrics.pureza_recalc')}
          </button>
          ${purBlocks}
        </div>

        <div class="mt-4">
          <div class="section-heading mb-0">${t('metrics.pureza_serie_title')}</div>
          <p class="small text-muted mb-2">${t('metrics.pureza_serie_desc', { label })}</p>
          <div id="pureza-serie-chart" class="plotly-chart-lg"></div>
          <div id="pureza-serie-info" class="mt-2"></div>
        </div>

        <div class="mt-4" id="aesp-yodo-section" style="display:none">
          <div class="section-heading mb-0">${t('metrics.aesp_title')}</div>
          <p class="small text-muted mb-2">${t('metrics.aesp_desc')}</p>
          <div id="aesp-yodo-chart" class="plotly-chart-lg"></div>
          <div id="aesp-yodo-info" class="mt-2"></div>
        </div>

      </div>
    </div>
  `;

  const btnSat = document.getElementById('btn-export-sat');
  if (btnSat) btnSat.addEventListener('click', exportSaturacionCSV);
  const btnRend = document.getElementById('btn-export-rend');
  if (btnRend) btnRend.addEventListener('click', exportRendimientoCSV);
  const btnPur = document.getElementById('btn-export-pureza');
  if (btnPur) btnPur.addEventListener('click', exportPurezaCSV);
  const btnRecalc = document.getElementById('btn-recalc-pureza');
  if (btnRecalc) {
    btnRecalc.addEventListener('click', () => {
      const chosen = Array.from(container.querySelectorAll('.pureza-chk:checked')).map(el => el.value);
      fetchIsotopoReport(iso, chosen);
    });
  }

  // F1: gráfica P(t) durante el enfriamiento (calcular_pureza_serie en el
  // servidor); vive en su propio contenedor, recién insertado arriba.
  _renderPurezaSerieChart(iso, simulations, metricas);

  // F2: gráfica A_esp(t) del yodo (calcular_actividad_especifica_yodo_serie
  // en el servidor) -- solo aplica cuando el isótopo seleccionado es yodo;
  // el servidor devuelve null en todas las sims si no, y la sección entera
  // se oculta (ninguna otra pestaña del informe distingue por elemento así).
  _renderActividadEspecificaYodoChart(iso, simulations, metricas);
}

/**
 * F1 (runbook_F1_pureza_temporal.md): gráfica de pureza P(t) durante el
 * enfriamiento, en dos paneles apilados que comparten eje temporal — P(t)
 * arriba (con línea de umbral 99,9 % y el instante de cruce) y A(iso,t)
 * abajo (para leer la ventana de administración: cuánta actividad queda
 * cuando el producto alcanza calidad farmacéutica). Los datos ya vienen
 * calculados por fort_analyzer.calcular_pureza_serie; aquí solo se
 * preparan trazas/rango de eje (static/js/pureza_time_utils.js, puro) y se
 * pinta con Plotly.
 */
function _renderPurezaSerieChart(iso, simulations, metricas) {
  const chartDiv = document.getElementById('pureza-serie-chart');
  const infoDiv  = document.getElementById('pureza-serie-info');
  if (!chartDiv) return;
  const label = isoLabel(iso);
  const uL = unitLabel();
  const entries = Object.entries(simulations);
  const singleSim = entries.length === 1;

  const traces = [];
  const shapes = [];
  const annotations = [];
  let allRows = [];
  let anyData = false;
  let infoHtml = '';
  let umbralPct = 99.9;

  entries.forEach(([name, sim], i) => {
    const color = PALETTE[i % PALETTE.length];
    const dot = `<span class="sim-dot me-1" style="background:${color}"></span>`;
    const serie = metricas[name] && metricas[name].pureza_serie;

    if (!serie) {
      infoHtml += `<div class="mb-2">${dot}<small class="fw-semibold">${escHtml(name)}</small>
        <span class="text-muted small">— ${t('metrics.pureza_serie_na')}</span></div>`;
      return;
    }
    anyData = true;
    umbralPct = serie.umbral_pct;
    allRows = allRows.concat(serie.serie);

    traces.push({
      x: serie.serie.map(p => p.t), y: serie.serie.map(p => p.P_pct),
      name, mode: 'lines+markers', type: 'scatter',
      line: { color, width: 2 }, marker: { size: 5 },
      yaxis: 'y', legendgroup: name,
      hovertemplate: `t = %{x:.3g} h<br>P = %{y:.6f} %<extra>` + escHtml(name) + '</extra>',
    });

    const factor = convFactor(sim);
    if (factor !== null) {
      traces.push({
        x: sim.t_cool, y: (sim.datos_cool[iso] || []).map(v => v * factor),
        name: `${name} (A)`, mode: 'lines+markers', type: 'scatter',
        line: { color, width: 2, dash: 'dot' }, marker: { size: 4, symbol: 'circle-open' },
        yaxis: 'y2', legendgroup: name, showlegend: false,
        hovertemplate: `t = %{x:.3g} h<br>A = %{y:.3e} ${uL}<extra>` + escHtml(name) + '</extra>',
      });
    }

    if (serie.t_cruce) {
      const tc = serie.t_cruce.t_h;
      shapes.push({
        type: 'line', x0: tc, x1: tc, y0: 0, y1: 1, yref: 'paper',
        line: { color, width: 1.5, dash: serie.t_cruce.estimado ? 'dot' : 'solid' },
      });
      if (singleSim) {
        annotations.push({
          x: tc, y: 1, yref: 'paper', yanchor: 'bottom', showarrow: false,
          font: { size: 9 },
          text: t('metrics.pureza_serie_cruce_label')
            + (serie.t_cruce.estimado ? ` (${t('metrics.pureza_serie_cruce_estimado')})` : ''),
        });
      }
    }

    infoHtml += `<div class="mb-2">${dot}<small class="fw-semibold">${escHtml(name)}</small> `;
    if (serie.estado === 'no_alcanzado') {
      infoHtml += `<span class="badge ${ACABPurezaTime.estadoBadgeClass(serie.estado)}">${t('metrics.pureza_serie_no_alcanzado')}</span>`;
    } else {
      const tcLabel = serie.t_cruce.t_h.toFixed(4) + ' h'
        + (serie.t_cruce.estimado ? ` (${t('metrics.pureza_serie_cruce_estimado')})` : '');
      infoHtml += `<span class="badge ${ACABPurezaTime.estadoBadgeClass(serie.estado)}">${t('metrics.pureza_serie_th_tcruce')}: ${tcLabel}</span>`;
      const vent = serie.ventana_administracion;
      if (vent) {
        infoHtml += ` <span class="text-muted small">A(${escHtml(label)}) = ${fmtA(vent.A_objetivo, sim)} ${uL}`
          + ` (${ACABPurezaTime.formatFraccionPico(vent.fraccion_pico)} ${t('metrics.pureza_serie_th_frac')})</span>`;
      }
    }
    if (serie.aviso_no_monotono) {
      infoHtml += `<div class="small text-warning mt-1"><i class="bi bi-exclamation-triangle me-1"></i>`
        + t('metrics.pureza_serie_aviso_no_monotono', {
            t: serie.aviso_no_monotono.t_h.toFixed(3),
            p: serie.aviso_no_monotono.P_pct != null ? serie.aviso_no_monotono.P_pct.toFixed(3) : '—',
          }) + '</div>';
    }
    infoHtml += '</div>';
  });

  if (infoDiv) infoDiv.innerHTML = infoHtml;

  if (!anyData) {
    chartDiv.innerHTML = `<div class="alert alert-light small py-2 mb-0">${t('metrics.pureza_serie_na')}</div>`;
    return;
  }
  chartDiv.innerHTML = '';

  const [yLo, yHi] = ACABPurezaTime.purezaYRange(allRows);
  shapes.push({
    type: 'line', xref: 'paper', x0: 0, x1: 1, y0: umbralPct, y1: umbralPct, yref: 'y',
    line: { color: '#c62828', width: 1, dash: 'dash' },
  });
  annotations.push({
    xref: 'paper', x: 1, y: umbralPct, yref: 'y', xanchor: 'right', yanchor: 'bottom',
    showarrow: false, font: { size: 9, color: '#c62828' },
    text: t('metrics.pureza_serie_umbral_label'),
  });

  Plotly.newPlot(chartDiv, traces, {
    xaxis:  { title: t('charts.ax_time_cool'), showgrid: true, gridcolor: '#eee', anchor: 'y2' },
    yaxis:  { title: t('metrics.pureza_serie_ax_p'), domain: [0.55, 1], range: [yLo, yHi], showgrid: true, gridcolor: '#eee' },
    yaxis2: { title: t('report.ax_activity', { label, unit: uL }), domain: [0, 0.42], anchor: 'x',
              type: 'log', exponentformat: 'e', showgrid: true, gridcolor: '#eee' },
    shapes, annotations,
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.08, xanchor: 'right', x: 1, font: { size: 9 } },
    margin: { t: 30, b: 40, l: 80, r: 20 },
    hovermode: 'closest',
    plot_bgcolor: '#fafafa', paper_bgcolor: '#fff',
  }, { responsive: true });
}

/**
 * F2 del BACKLOG: gráfica A_esp(t) = A(iso,t)/masa_total_yodo(t) [MBq/g]
 * durante el enfriamiento -- mismo dominio temporal que P(t) (F1), pero un
 * solo panel (sin umbral ni semáforos: "fuera de alcance" del diseño F2).
 * Los datos ya vienen calculados por fort_analyzer.calcular_actividad_
 * especifica_yodo_serie; aquí solo se pinta con Plotly, destacando el valor
 * en t_destacado_h (t_cruce de pureza, ya resuelto por el servidor). Oculta
 * la sección entera si NINGUNA sim tiene el dato (isótopo no es yodo).
 */
function _renderActividadEspecificaYodoChart(iso, simulations, metricas) {
  const section  = document.getElementById('aesp-yodo-section');
  const chartDiv = document.getElementById('aesp-yodo-chart');
  const infoDiv  = document.getElementById('aesp-yodo-info');
  if (!section || !chartDiv) return;

  const entries = Object.entries(simulations);
  const anyAplica = entries.some(([name]) => metricas[name] && metricas[name].actividad_especifica_yodo_serie);
  if (!anyAplica) {
    section.style.display = 'none';
    return;
  }
  section.style.display = '';

  const traces = [];
  const shapes = [];
  let infoHtml = '';

  entries.forEach(([name], i) => {
    const color = PALETTE[i % PALETTE.length];
    const dot = `<span class="sim-dot me-1" style="background:${color}"></span>`;
    const serie = metricas[name] && metricas[name].actividad_especifica_yodo_serie;

    if (!serie) {
      infoHtml += `<div class="mb-2">${dot}<small class="fw-semibold">${escHtml(name)}</small>
        <span class="text-muted small">— ${t('metrics.aesp_na')}</span></div>`;
      return;
    }

    traces.push({
      x: serie.serie.map(p => p.t), y: serie.serie.map(p => p.A_esp_MBq_g),
      name, mode: 'lines+markers', type: 'scatter',
      line: { color, width: 2 }, marker: { size: 5 },
      hovertemplate: `t = %{x:.3g} h<br>A_esp = %{y:.4e} MBq/g<extra>` + escHtml(name) + '</extra>',
    });

    infoHtml += `<div class="mb-2">${dot}<small class="fw-semibold">${escHtml(name)}</small> `;
    if (serie.t_destacado_h != null && serie.valor_destacado_MBq_g != null) {
      shapes.push({
        type: 'line', x0: serie.t_destacado_h, x1: serie.t_destacado_h, y0: 0, y1: 1, yref: 'paper',
        line: { color, width: 1.5, dash: 'dash' },
      });
      infoHtml += `<span class="badge bg-secondary">${t('metrics.aesp_destacado_label')}: `
        + `${serie.valor_destacado_MBq_g.toExponential(3)} MBq/g (t = ${serie.t_destacado_h.toFixed(4)} h)</span>`;
    } else {
      infoHtml += `<span class="text-muted small">${t('metrics.aesp_sin_destacado')}</span>`;
    }
    infoHtml += '</div>';
  });

  if (infoDiv) infoDiv.innerHTML = infoHtml;

  if (!traces.length) {
    chartDiv.innerHTML = `<div class="alert alert-light small py-2 mb-0">${t('metrics.aesp_na')}</div>`;
    return;
  }
  chartDiv.innerHTML = '';

  Plotly.newPlot(chartDiv, traces, {
    xaxis:  { title: t('charts.ax_time_cool'), showgrid: true, gridcolor: '#eee' },
    yaxis:  { title: t('metrics.aesp_ax_y'), showgrid: true, gridcolor: '#eee', exponentformat: 'e' },
    shapes,
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.08, xanchor: 'right', x: 1, font: { size: 9 } },
    margin: { t: 30, b: 40, l: 80, r: 20 },
    hovermode: 'closest',
    plot_bgcolor: '#fafafa', paper_bgcolor: '#fff',
  }, { responsive: true });
}

/** Export the saturation table (per sim: A_sat + t_x per % target, Fase 5). */
function exportSaturacionCSV() {
  const iso = _state.selectedIsotopo;
  const informe = _state.isotopoReport && _state.isotopoReport.informe;
  if (!iso || !informe || !_state.analysisData) return;
  const sims = _state.analysisData.simulations;
  const rows = [];
  Object.entries(informe.metricas || {}).forEach(([name, m]) => {
    const sat = m.saturacion;
    if (!sat) return;
    const sim = sims[name];
    sat.tabla.forEach(r => rows.push([
      name, conv(sat.A_sat, sim), r.pct, r.t_x_h, r.alcanzable ? 1 : 0,
    ]));
  });
  if (!rows.length) return;
  const headers = [t('overview.th_sim'), `A_sat [${unitLabel()}]`, '% saturación', 't_x [h]', 'alcanzable'];
  emitCSV(`${ACABExport.slug(iso)}_saturacion_${unitSlug()}_${folderSlug()}.csv`, iso, rows, headers);
}

/** Export the yield table (per sim: mean/marginal yield, Fase 5). */
function exportRendimientoCSV() {
  const iso = _state.selectedIsotopo;
  const informe = _state.isotopoReport && _state.isotopoReport.informe;
  if (!iso || !informe || !_state.analysisData) return;
  const sims = _state.analysisData.simulations;
  const uL = unitLabel();
  const rows = [];
  Object.entries(informe.metricas || {}).forEach(([name, m]) => {
    const r = m.rendimiento;
    if (!r) return;
    const sim = sims[name];
    rows.push([
      name, conv(r.rendimiento_medio, sim), conv(r.A_fin, sim),
      conv(r.ganancia_marginal, sim), r.compensa_seguir ? 1 : 0,
    ]);
  });
  if (!rows.length) return;
  const headers = [t('overview.th_sim'), `rendimiento_medio [${uL}/h]`, `A_fin [${uL}]`,
                   `ganancia_marginal [${uL}/h]`, 'compensa_seguir'];
  emitCSV(`${ACABExport.slug(iso)}_rendimiento_${unitSlug()}_${folderSlug()}.csv`, iso, rows, headers);
}

/** Export the purity contribution table (per sim, per isotope considered, Fase 5). */
function exportPurezaCSV() {
  const iso = _state.selectedIsotopo;
  const informe = _state.isotopoReport && _state.isotopoReport.informe;
  if (!iso || !informe || !_state.analysisData) return;
  const sims = _state.analysisData.simulations;
  const rows = [];
  Object.entries(informe.metricas || {}).forEach(([name, m]) => {
    const p = m.pureza;
    if (!p) return;
    const sim = sims[name];
    p.contribuciones.forEach(c => rows.push([
      name, p.P_pct, `${isoLabel(c.iso)} (${c.iso})`,
      c.A != null ? conv(c.A, sim) : null, c.pct,
    ]));
  });
  if (!rows.length) return;
  const headers = [t('overview.th_sim'), 'P [%]', t('metrics.pureza_th_iso'),
                   `A [${unitLabel()}]`, 'contribución [%]'];
  emitCSV(`${ACABExport.slug(iso)}_pureza_${unitSlug()}_${folderSlug()}.csv`, iso, rows, headers);
}

// ─────────────────────────────────────────────────────────────────────────────
// Datos de referencia externos (Fase 4) — CSV según
// docs/SPEC_csv_datos_referencia.md. Parseo/interpolación puros en
// static/js/reference_data.js (global ACABRefData); aquí solo el diálogo,
// el estado y el renderizado.
// ─────────────────────────────────────────────────────────────────────────────

/** "irradiación"/"irradiacion" → 'irradiacion'; "enfriamiento" → 'enfriamiento'; si no matchea, ''. */
function _normalizePhase(s) {
  // Quita marcas diacríticas combinantes (rango Unicode U+0300–U+036F) tras
  // la descomposición NFD, para aceptar tanto "irradiación" como "irradiacion".
  const norm = String(s || '').trim().toLowerCase().normalize('NFD')
    .split('').filter(ch => { const c = ch.charCodeAt(0); return c < 0x0300 || c > 0x036f; }).join('');
  if (norm === 'enfriamiento') return 'enfriamiento';
  if (norm === 'irradiacion') return 'irradiacion';
  return '';
}

// E1: Populate the import dialog from the parsed CSV draft (preview + column
// mapping selects, metadata fields prefilled from the CSV's `#` comments).
function renderRefDataDialog() {
  const draft = _state.refImportDraft;
  const body  = document.getElementById('refdata-modal-body');
  if (!draft) { body.innerHTML = ''; return; }

  const { parsed, filename } = draft;
  const rows = parsed.rows;
  const nCols = rows.length ? rows[0].length : 0;
  const guessedRoles = ACABRefData.guessColumnRoles(rows);
  const preview = rows.slice(0, 5);
  const meta = parsed.meta || {};

  const roleOptions = guessed => `
    <option value="t" ${guessed === 't' ? 'selected' : ''}>${t('refdata.col_role_t')}</option>
    <option value="A" ${guessed === 'A' ? 'selected' : ''}>${t('refdata.col_role_a')}</option>
    <option value="A_err" ${guessed === 'A_err' ? 'selected' : ''}>${t('refdata.col_role_aerr')}</option>
    <option value="ignore" ${!guessed ? 'selected' : ''}>${t('refdata.col_role_ignore')}</option>`;

  const headRow = Array.from({ length: nCols }).map((_, i) => `
    <th style="min-width:130px">
      <div class="small text-muted mb-1">${t('refdata.col_label', { n: i + 1 })}</div>
      <select class="form-select form-select-sm refdata-col-role" data-col="${i}">
        ${roleOptions(guessedRoles[i] || null)}
      </select>
    </th>`).join('');

  const bodyRows = preview.map(row => `
    <tr>${row.map(v => `<td class="font-monospace small">${isFinite(v) ? v : '—'}</td>`).join('')}</tr>
  `).join('');

  const metaFase   = _normalizePhase(meta.fase);
  const metaUnitT  = ACABRefData.parseTimeUnitLabel(meta.unidad_t) || '';
  const metaUnitA  = ACABRefData.parseActivityUnitLabel(meta.unidad_a) || '';
  const metaTipo   = meta.tipo === 'computacional_referencia' ? 'computacional_referencia' : 'experimental';
  const metaIso    = (meta.isotopo || _state.selectedIsotopo || '').toUpperCase();
  const metaLabel  = meta.descripcion || filename;
  const metaFuente = meta.fuente || '';

  const sims = _state.analysisData ? _state.analysisData.simulations : {};
  const simOptions = Object.keys(sims)
    .map(name => `<option value="${escAttr(name)}">${escHtml(name)}</option>`).join('');

  body.innerHTML = `
    <p class="small text-muted">${t('refdata.modal_lead')}</p>

    <div class="mb-2 fw-semibold small">${t('refdata.preview_title')}</div>
    <div class="table-responsive mb-3">
      <table class="table table-sm table-bordered mb-0">
        <thead><tr>${headRow}</tr></thead>
        <tbody>${bodyRows}</tbody>
      </table>
    </div>

    <div class="row g-2">
      <div class="col-md-4">
        <label class="form-label small fw-semibold mb-1">${t('refdata.field_tipo')}</label>
        <select id="refdata-tipo" class="form-select form-select-sm">
          <option value="experimental" ${metaTipo === 'experimental' ? 'selected' : ''}>${t('refdata.tipo_experimental')}</option>
          <option value="computacional_referencia" ${metaTipo === 'computacional_referencia' ? 'selected' : ''}>${t('refdata.tipo_computacional')}</option>
        </select>
      </div>
      <div class="col-md-4">
        <label class="form-label small fw-semibold mb-1">${t('refdata.field_fase')}</label>
        <select id="refdata-fase" class="form-select form-select-sm">
          <option value="" ${!metaFase ? 'selected' : ''} disabled>${t('refdata.field_fase_ph')}</option>
          <option value="irradiacion" ${metaFase === 'irradiacion' ? 'selected' : ''}>${t('phase.irr')}</option>
          <option value="enfriamiento" ${metaFase === 'enfriamiento' ? 'selected' : ''}>${t('phase.cool')}</option>
        </select>
      </div>
      <div class="col-md-4">
        <label class="form-label small fw-semibold mb-1">${t('refdata.field_isotopo')}</label>
        <input type="text" id="refdata-isotopo" class="form-control form-control-sm font-monospace"
               value="${escAttr(metaIso)}">
      </div>

      <div class="col-md-4">
        <label class="form-label small fw-semibold mb-1">${t('refdata.field_unidad_t')}</label>
        <select id="refdata-unidad-t" class="form-select form-select-sm">
          <option value="" ${!metaUnitT ? 'selected' : ''} disabled>${t('refdata.field_fase_ph')}</option>
          <option value="s" ${metaUnitT === 's' ? 'selected' : ''}>s</option>
          <option value="min" ${metaUnitT === 'min' ? 'selected' : ''}>min</option>
          <option value="h" ${metaUnitT === 'h' ? 'selected' : ''}>h</option>
          <option value="d" ${metaUnitT === 'd' ? 'selected' : ''}>d</option>
        </select>
      </div>
      <div class="col-md-4">
        <label class="form-label small fw-semibold mb-1">${t('refdata.field_unidad_a')}</label>
        <select id="refdata-unidad-a" class="form-select form-select-sm">
          <option value="" ${!metaUnitA ? 'selected' : ''} disabled>${t('refdata.field_fase_ph')}</option>
          <option value="bqcm3" ${metaUnitA === 'bqcm3' ? 'selected' : ''}>${t('units.bqcm3')}</option>
          <option value="mbqg" ${metaUnitA === 'mbqg' ? 'selected' : ''}>${t('units.mbqg')}</option>
          <option value="mbq_total" ${metaUnitA === 'mbq_total' ? 'selected' : ''}>${t('units.mbq_total')}</option>
          <option value="mci_total" ${metaUnitA === 'mci_total' ? 'selected' : ''}>${t('units.mci_total')}</option>
        </select>
      </div>
      <div class="col-md-4">
        <label class="form-label small fw-semibold mb-1">${t('refdata.field_refsim')}</label>
        <select id="refdata-refsim" class="form-select form-select-sm">${simOptions}</select>
        <div class="form-text">${t('refdata.field_refsim_hint')}</div>
      </div>

      <div class="col-md-6">
        <label class="form-label small fw-semibold mb-1">${t('refdata.field_etiqueta')}</label>
        <input type="text" id="refdata-etiqueta" class="form-control form-control-sm" value="${escAttr(metaLabel)}">
      </div>
      <div class="col-md-6">
        <label class="form-label small fw-semibold mb-1">${t('refdata.field_fuente')}</label>
        <input type="text" id="refdata-fuente" class="form-control form-control-sm" value="${escAttr(metaFuente)}">
      </div>
    </div>
  `;
}

// E2: Read the dialog DOM, validate, build the series and push it to appState.
function confirmRefDataImport() {
  const draft = _state.refImportDraft;
  if (!draft || !_state.analysisData) return;
  const body = document.getElementById('refdata-modal-body');

  const colMap = { t: null, A: null, A_err: null };
  body.querySelectorAll('.refdata-col-role').forEach(sel => {
    const col  = parseInt(sel.dataset.col, 10);
    const role = sel.value;
    if (role === 't') colMap.t = col;
    else if (role === 'A') colMap.A = col;
    else if (role === 'A_err') colMap.A_err = col;
  });
  if (colMap.t === null || colMap.A === null) {
    showToast(t('refdata.err_col_mapping'), 'warning');
    return;
  }

  const fase       = document.getElementById('refdata-fase').value;
  const unidadT    = document.getElementById('refdata-unidad-t').value;
  const unidadA    = document.getElementById('refdata-unidad-a').value;
  const isotopo    = document.getElementById('refdata-isotopo').value.trim().toUpperCase();
  const tipo       = document.getElementById('refdata-tipo').value;
  const etiqueta   = document.getElementById('refdata-etiqueta').value.trim() || draft.filename;
  const fuente     = document.getElementById('refdata-fuente').value.trim();
  const refSimName = document.getElementById('refdata-refsim').value;

  if (!fase || !unidadT || !unidadA || !isotopo || !refSimName) {
    showToast(t('refdata.err_missing_fields'), 'warning');
    return;
  }

  const refSim = _state.analysisData.simulations[refSimName];
  const opts   = { density: refSim ? refSim.densidad_g_cm3 : null, volume: activeVolume() };
  const factor = ACABUnits.unitFactor(unidadA, opts);
  if (factor === null) {
    const need = ACABUnits.unitRequires(unidadA);
    showToast(t(need === 'density' ? 'refdata.err_no_density' : 'refdata.err_no_volume'), 'danger');
    return;
  }

  const rawPoints = ACABRefData.buildSeriesPoints(draft.parsed.rows, colMap);
  if (!rawPoints.length) {
    showToast(t('refdata.err_no_rows'), 'warning');
    return;
  }

  // F12 del BACKLOG: t_h se guarda SIEMPRE en tiempo desde el inicio de la
  // fase declarada (igual definición que docs/SPEC_csv_datos_referencia.md),
  // SIN desplazar por T_irr — 'enfriamiento' comparte origen con
  // sim.t_cool/datos_cool (EOI/RESTART), 'irradiacion' con sim.t_irr (t=0
  // absoluto). El desplazamiento a eje absoluto para la SUPERPOSICIÓN en el
  // gráfico combinado se calcula solo al pintar (_renderIsotopoTimeChart),
  // nunca al guardar el dato.
  const points = rawPoints
    .map(p => {
      const t_h = ACABRefData.convertTimeToHours(p.t, unidadT);
      const A_bqcm3 = ACABRefData.bqcm3FromUnit(p.A, unidadA, opts);
      const A_err_bqcm3 = (p.A_err !== null) ? ACABRefData.bqcm3FromUnit(p.A_err, unidadA, opts) : null;
      return { t_h, A_bqcm3, A_err_bqcm3 };
    })
    .filter(p => p.A_bqcm3 !== null && isFinite(p.t_h))
    .sort((a, b) => a.t_h - b.t_h);

  if (!points.length) {
    showToast(t('refdata.err_no_rows'), 'warning');
    return;
  }

  _state.refSeries.push({
    id: 'ref-' + Date.now() + '-' + Math.floor(Math.random() * 1000),
    tipo, descripcion: etiqueta, isotopo, fase, unidadT, unidadA, fuente, refSimName, points,
  });

  bootstrap.Modal.getInstance(document.getElementById('modal-refdata'))?.hide();
  _state.refImportDraft = null;
  showToast(t('refdata.toast_imported', { label: etiqueta, n: points.length }), 'success');

  if (isotopo === _state.selectedIsotopo) renderIsotopoReport();
}

// Compact badge list of the series loaded for the current isotope, with remove buttons.
function renderRefDataList() {
  const container = document.getElementById('refdata-list-container');
  if (!container) return;
  const iso = _state.selectedIsotopo;
  const list = (_state.refSeries || []).filter(s => s.isotopo === iso);

  if (!list.length) { container.innerHTML = ''; return; }

  container.innerHTML = `
    <div class="small fw-semibold mb-1">${t('refdata.list_title')}</div>
    <div class="d-flex flex-wrap gap-2">
      ${list.map(s => `
        <span class="badge bg-light text-dark border d-inline-flex align-items-center gap-1" style="font-size:0.78rem">
          <span class="badge ${s.tipo === 'experimental' ? 'bg-secondary' : 'bg-info text-dark'}" style="font-size:0.62rem">
            ${s.tipo === 'experimental' ? t('refdata.badge_experimental') : t('refdata.badge_computacional')}
          </span>
          ${escHtml(s.descripcion)}
          <button type="button" class="btn-close ms-1 btn-remove-refdata" data-id="${escAttr(s.id)}"
                  style="font-size:0.55rem" title="${escAttr(t('refdata.remove_title'))}"></button>
        </span>
      `).join('')}
    </div>
  `;

  container.querySelectorAll('.btn-remove-refdata').forEach(btn => {
    btn.addEventListener('click', () => {
      _state.refSeries = _state.refSeries.filter(s => s.id !== btn.dataset.id);
      renderIsotopoReport();
    });
  });
}

/** 'experimental' | 'computacional_referencia' → etiqueta corta para la cabecera de tabla/CSV. */
function _refTipoLabel(tipo) {
  return tipo === 'experimental'
    ? t('refdata.metrics_tipo_experimental')
    : t('refdata.metrics_tipo_computacional');
}

// Deviation-metrics table (mean/max bias vs. the target simulation) for
// EVERY series loaded for the current isotope — both types, experimental AND
// computacional_referencia (Fase 6 del BACKLOG: antes solo experimental),
// una tabla independiente por serie con su tipo visible en la cabecera.
// Con varias simulaciones cargadas, un desplegable único (_state.refMetricsTargetSim,
// resuelto vía ACABRefData.resolveTargetSimName) elige contra qué simulación
// se interpolan TODAS las series; con una sola, no se muestra. Purely a
// percentage, so it is computed in raw Bq/cm³ (unit-invariant); only the
// displayed A columns are converted to the active unit for readability.
function renderRefDataMetrics() {
  const container = document.getElementById('refdata-metrics-container');
  if (!container) return;
  const iso  = _state.selectedIsotopo;
  const sims = _state.analysisData ? _state.analysisData.simulations : {};
  const simNames = Object.keys(sims);
  const metricSeries = ACABRefData.seriesForMetrics(_state.refSeries, iso);

  if (!metricSeries.length || !simNames.length) { container.innerHTML = ''; return; }

  const targetSimName = ACABRefData.resolveTargetSimName(simNames, _state.refMetricsTargetSim);
  _state.refMetricsTargetSim = targetSimName;
  const sim = sims[targetSimName];
  if (!sim) { container.innerHTML = ''; return; }

  const selectorHtml = simNames.length > 1 ? `
    <div class="d-flex align-items-center gap-2 mb-2">
      <label class="small fw-semibold mb-0" for="refdata-target-sim">${t('refdata.target_sim_label')}</label>
      <select id="refdata-target-sim" class="form-select form-select-sm" style="max-width:260px">
        ${simNames.map(name => `<option value="${escAttr(name)}" ${name === targetSimName ? 'selected' : ''}>${escHtml(name)}</option>`).join('')}
      </select>
    </div>` : '';

  const tablesHtml = metricSeries.map(s => {
    // F12 del BACKLOG: curva ACAB de la MISMA fase que la serie (nunca la
    // combinada irr+enfriamiento) — mismo origen temporal a ambos lados,
    // p.t_h ya viene sin desplazar (confirmRefDataImport).
    const { xs, ys } = ACABRefData.curveForPhase(sim, iso, s.fase);
    const points = s.points.map(p => ({ t: p.t_h, A: p.A_bqcm3 }));
    const metrics = ACABRefData.computeDeviationMetrics(points, xs, ys);
    const factor = convFactor(sim);
    const originKeys = ACABRefData.interpolationOriginLabel(s.fase);
    const origin = { metodo: t('refdata.interp_method_' + originKeys.metodoKey), origen: t('refdata.origin_' + originKeys.origenKey) };

    const rows = metrics.rows.map(r => `
      <tr>
        <td class="font-monospace small">${r.t.toFixed(3)}</td>
        <td class="font-monospace small">${(factor !== null && r.A_exp != null) ? (r.A_exp * factor).toExponential(3) : '—'}</td>
        <td class="font-monospace small">${(factor !== null && r.A_interp != null) ? (r.A_interp * factor).toExponential(3) : '—'}</td>
        <td class="font-monospace small ${r.dev_pct != null && Math.abs(r.dev_pct) > 10 ? 'text-danger' : ''}">${r.dev_pct != null ? r.dev_pct.toFixed(2) : '—'}</td>
      </tr>`).join('');

    const mean = metrics.meanDevPct   != null ? metrics.meanDevPct.toFixed(2)   : '—';
    const max  = metrics.maxAbsDevPct != null ? metrics.maxAbsDevPct.toFixed(2) : '—';

    return `
      <div class="card shadow-sm mb-2">
        <div class="card-header py-2 d-flex justify-content-between align-items-center flex-wrap gap-2">
          <strong class="small">${t('refdata.metrics_title', { label: escHtml(s.descripcion), tipo: _refTipoLabel(s.tipo), sim: escHtml(targetSimName) })}</strong>
          <div class="d-flex align-items-center gap-2">
            <span class="badge bg-secondary">${t('refdata.metrics_mean', { v: mean })}</span>
            <span class="badge bg-dark">${t('refdata.metrics_max', { v: max })}</span>
            <button class="btn btn-outline-secondary btn-sm btn-export-refmetrics" data-id="${escAttr(s.id)}"
                    title="${escAttr(t('refdata.metrics_export'))}">
              <i class="bi bi-download"></i>
            </button>
          </div>
        </div>
        <div class="px-2 pt-1 small text-muted">${t('refdata.metrics_origin_note', { metodo: origin.metodo, origen: origin.origen })}</div>
        <div class="table-responsive" style="max-height:220px">
          <table class="table table-sm mb-0" style="font-size:0.8rem">
            <thead><tr>
              <th>${t('refdata.metrics_th_t')}</th>
              <th>${t('refdata.metrics_th_aserie', { unit: unitLabel() })}</th>
              <th>${t('refdata.metrics_th_ainterp', { unit: unitLabel() })}</th>
              <th>${t('refdata.metrics_th_dev')}</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>`;
  }).join('');

  container.innerHTML = selectorHtml + tablesHtml;

  const targetSel = document.getElementById('refdata-target-sim');
  if (targetSel) {
    targetSel.addEventListener('change', () => {
      _state.refMetricsTargetSim = targetSel.value;
      renderRefDataMetrics();
    });
  }

  container.querySelectorAll('.btn-export-refmetrics').forEach(btn => {
    btn.addEventListener('click', () => exportRefMetricsCSV(btn.dataset.id));
  });
}

/** Export a reference series' deviation table (Fase 3 CSV conventions). */
function exportRefMetricsCSV(seriesId) {
  const iso = _state.selectedIsotopo;
  const s = (_state.refSeries || []).find(x => x.id === seriesId);
  if (!s || !_state.analysisData) return;
  const sims = _state.analysisData.simulations;
  const simNames = Object.keys(sims);
  const targetSimName = ACABRefData.resolveTargetSimName(simNames, _state.refMetricsTargetSim);
  const sim = targetSimName ? sims[targetSimName] : null;
  if (!sim) return;

  // F12 del BACKLOG: misma fase a ambos lados, sin desplazamiento — ver
  // renderRefDataMetrics.
  const { xs, ys } = ACABRefData.curveForPhase(sim, iso, s.fase);
  const points = s.points.map(p => ({ t: p.t_h, A: p.A_bqcm3 }));
  const metrics = ACABRefData.computeDeviationMetrics(points, xs, ys);
  const factor = convFactor(sim);
  const originKeys = ACABRefData.interpolationOriginLabel(s.fase);
  const origin = { metodo: t('refdata.interp_method_' + originKeys.metodoKey), origen: t('refdata.origin_' + originKeys.origenKey) };

  const rows = metrics.rows.map(r => [
    r.t,
    (factor !== null && r.A_exp != null) ? r.A_exp * factor : null,
    (factor !== null && r.A_interp != null) ? r.A_interp * factor : null,
    r.dev_pct,
  ]);
  const headers = ['t [h]', `A_serie [${unitLabel()}]`, `A_ACAB [${unitLabel()}]`, 'desv [%]'];
  const extraMeta = [
    `# ${t('refdata.metrics_csv_meta', { tipo: _refTipoLabel(s.tipo), sim: targetSimName })}`,
    `# ${t('refdata.metrics_csv_origin', { metodo: origin.metodo, origen: origin.origen })}`,
    `# ${t('refdata.metrics_mean', { v: metrics.meanDevPct   != null ? metrics.meanDevPct.toFixed(3)   : '' })}`,
    `# ${t('refdata.metrics_max',  { v: metrics.maxAbsDevPct != null ? metrics.maxAbsDevPct.toFixed(3) : '' })}`,
  ].join('\r\n');

  emitCSV(`${ACABExport.slug(iso)}_desviacion_${ACABExport.slug(s.descripcion)}_${folderSlug()}.csv`,
          iso, rows, headers, extraMeta);
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 4: Comparison Tables  (F6)
// ─────────────────────────────────────────────────────────────────────────────
function renderTables() {
  const container = document.getElementById('tables-container');
  const iso  = _state.selectedIsotopo;
  const json = _state.isotopoReport;
  if (!iso || !json) return;

  const { tabla1, tabla2 } = json;
  const label = isoLabel(iso);
  let html = '';

  // ── Table 1 ──────────────────────────────────────────────────────────────
  html += `
    <div class="mb-2">
      <div class="d-flex justify-content-between align-items-start gap-2">
        <h5>${t('tables.t1_title', { label })}</h5>
        <button class="btn btn-outline-secondary btn-sm flex-shrink-0" id="btn-export-tabla1">
          <i class="bi bi-download me-1"></i>${t('export.csv')}
        </button>
      </div>
      <p class="text-muted small mb-3">
        ${t('tables.t1_desc', { label })}
      </p>
    </div>
  `;

  const allSims = _state.analysisData ? _state.analysisData.simulations : {};

  Object.entries(tabla1).forEach(([simName, tbl], i) => {
    const color = PALETTE[i % PALETTE.length];
    const sim = allSims[simName];
    const Ap = tbl.A_pico_ref !== null && tbl.A_pico_ref > 0
      ? fmtA(tbl.A_pico_ref, sim) : '—';
    const tp = tbl.t_pico_ref !== null
      ? tbl.t_pico_ref.toFixed(3) : '—';

    const sortedRows = (tbl.rows || [])
      .slice()
      .sort((a, b) => (b.A || 0) - (a.A || 0));

    const tableRows = sortedRows.map(r => {
      // Activity converted per sim; the ratio is dimensionless (unit-invariant).
      const A     = r.A     !== null && r.A     > 0 ? fmtA(r.A, sim)             : '—';
      const ratio = r.ratio !== null && r.ratio > 0 ? r.ratio.toExponential(3) : '—';
      const isRef = r.iso === iso;
      return `<tr ${isRef ? 'class="table-warning fw-bold"' : ''}>
        <td>${escHtml(r.label)} <small class="text-muted">(${r.iso})</small></td>
        <td class="font-monospace">${A}</td>
        <td class="font-monospace">${ratio}</td>
      </tr>`;
    }).join('');

    html += `
      <div class="mb-4">
        <div class="d-flex align-items-center gap-2 mb-2">
          <span class="sim-dot" style="background:${color}"></span>
          <span class="fw-semibold">${escHtml(simName)}</span>
          <span class="badge bg-danger ms-1">${t('tables.peak_badge', { label, a: Ap, unit: unitLabel() })}</span>
          <span class="badge bg-secondary">${t('tables.t_badge', { t: tp })}</span>
        </div>
        <div class="comparison-table-wrapper">
          <table class="table table-sm table-hover mb-0" style="font-size:0.82rem">
            <thead>
              <tr>
                <th>${t('tables.th_iso')}</th>
                <th>${t('tables.th_a_tpico', { unit: unitLabel() })}</th>
                <th>${t('tables.th_ratio', { label })}</th>
              </tr>
            </thead>
            <tbody>${tableRows}</tbody>
          </table>
        </div>
      </div>
    `;
  });

  // ── Table 2 ──────────────────────────────────────────────────────────────
  html += `
    <hr>
    <div class="mb-2 mt-4">
      <div class="d-flex justify-content-between align-items-start gap-2">
        <h5>${t('tables.t2_title', { label })}</h5>
        <button class="btn btn-outline-secondary btn-sm flex-shrink-0" id="btn-export-tabla2">
          <i class="bi bi-download me-1"></i>${t('export.csv')}
        </button>
      </div>
      <p class="text-muted small mb-3">
        ${t('tables.t2_desc', { label })}
      </p>
    </div>
  `;

  Object.entries(tabla2).forEach(([simName, tbl], i) => {
    const color = PALETTE[i % PALETTE.length];
    const sim = allSims[simName];
    const sortedRows = (tbl.rows || [])
      .slice()
      .sort((a, b) => (b.A_pico || 0) - (a.A_pico || 0));

    const tableRows = sortedRows.map(r => {
      const Ap = r.A_pico  !== null && r.A_pico  > 0 ? fmtA(r.A_pico, sim)  : '—';
      const tp = r.t_pico  !== null && r.t_pico  !== undefined ? r.t_pico.toFixed(3) : '—';
      const Ai = r.A_ref_en !== null && r.A_ref_en > 0 ? fmtA(r.A_ref_en, sim) : '—';
      const isRef = r.iso === iso;
      return `<tr ${isRef ? 'class="table-warning fw-bold"' : ''}>
        <td>${escHtml(r.label)} <small class="text-muted">(${r.iso})</small></td>
        <td class="font-monospace">${Ap}</td>
        <td class="font-monospace">${tp}</td>
        <td class="font-monospace">${Ai}</td>
      </tr>`;
    }).join('');

    html += `
      <div class="mb-4">
        <div class="d-flex align-items-center gap-2 mb-2">
          <span class="sim-dot" style="background:${color}"></span>
          <span class="fw-semibold">${escHtml(simName)}</span>
        </div>
        <div class="comparison-table-wrapper">
          <table class="table table-sm table-hover mb-0" style="font-size:0.82rem">
            <thead>
              <tr>
                <th>${t('tables.th_iso')}</th>
                <th>${t('tables.th_peak_a', { unit: unitLabel() })}</th>
                <th>${t('tables.th_tpico')}</th>
                <th>${t('tables.th_a_ref', { label, unit: unitLabel() })}</th>
              </tr>
            </thead>
            <tbody>${tableRows}</tbody>
          </table>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;

  const b1 = document.getElementById('btn-export-tabla1');
  if (b1) b1.addEventListener('click', exportTable1CSV);
  const b2 = document.getElementById('btn-export-tabla2');
  if (b2) b2.addEventListener('click', exportTable2CSV);
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 5: Sweep Optimisation  (Fase 5 opcional, RUNBOOK_barrido_parametrico_v2)
// Combina sweep_manifest.json (folder → params, escrito por el ACAB INP File
// Configurator) con el informe del isótopo ya calculado por el servidor:
// A_pico/t_pico (informe.simulations) y pureza/rendimiento (informe.metricas).
// La combinación/agrupación pura vive en static/js/optim_utils.js (global
// ACABOptim); aquí solo se renderiza tabla + gráfica + export CSV, reutilizando
// fmtA/conv/unitLabel — ninguna fórmula física se repite.
// ─────────────────────────────────────────────────────────────────────────────

const OPTIM_YVARS = ['a_pico', 't_pico', 'pureza', 'rendimiento', 'a_esp_yodo'];

function _optimYLabel(yVar) {
  if (yVar === 't_pico')      return t('optim.yvar_tpico');
  if (yVar === 'pureza')      return t('optim.yvar_pureza');
  if (yVar === 'rendimiento') return t('optim.yvar_rendimiento');
  if (yVar === 'a_esp_yodo')  return t('optim.yvar_aesp_yodo');
  return t('optim.yvar_apico');
}

/** Unidad mostrada en el eje Y para la variable elegida. */
function _optimYUnit(yVar) {
  if (yVar === 't_pico')      return 'h';
  if (yVar === 'pureza')      return '%';
  if (yVar === 'rendimiento') return `${unitLabel()}/h`;
  if (yVar === 'a_esp_yodo')  return 'MBq/g';
  return unitLabel();
}

/** Valor de la variable Y ya en la unidad activa (o crudo si es unit-invariante), o null. */
function _optimYDisplay(row, yVar, sim) {
  const raw = ACABOptim.yRawValue(row, yVar);
  if (raw === null || raw === undefined) return null;
  return ACABOptim.yNeedsUnitConv(yVar) ? conv(raw, sim) : raw;
}

function renderOptimizacion() {
  const container = document.getElementById('optim-container');
  const iso  = _state.selectedIsotopo;
  const json = _state.isotopoReport;
  if (!iso || !json || !container) return;

  const manifest = _state.analysisData && _state.analysisData.sweep_manifest;
  if (!manifest) {
    container.innerHTML = `
      <div class="alert alert-secondary mt-3">
        <i class="bi bi-info-circle me-2"></i>${t('optim.no_manifest')}
      </div>`;
    return;
  }

  const sims = _state.analysisData.simulations;
  const simNames = Object.keys(sims);
  const rows = ACABOptim.mergeSweepRows(
    manifest, simNames, json.informe.simulations, json.informe.metricas);

  if (!rows.length) {
    container.innerHTML = `<div class="alert alert-warning mt-3">${t('optim.no_rows')}</div>`;
    return;
  }

  // U4 del BACKLOG: el barrido espectral tiene su propio render (una sola
  // serie, nombre del espectro como identificador) -- paramKeys() recogería
  // aquí n_grupos/frac_termica/frac_epitermica/frac_rapida (todos numéricos)
  // y produciría una leyenda con el volcado de parámetros que U4 corrige.
  if (ACABOptim.isSpectrumSweep(manifest)) {
    renderOptimizacionSpectrum(container, iso, manifest, sims, rows);
    return;
  }

  const keys = ACABOptim.paramKeys(rows);
  if (!keys.length) {
    container.innerHTML = `<div class="alert alert-warning mt-3">${t('optim.no_numeric_params')}</div>`;
    return;
  }

  if (!_state.optimXParam || keys.indexOf(_state.optimXParam) === -1) {
    _state.optimXParam = keys[0];
  }
  const xKey  = _state.optimXParam;
  const yVar  = _state.optimYVar;
  const label = isoLabel(iso);
  const uL    = unitLabel();

  const paramOptions = keys.map(k =>
    `<option value="${escAttr(k)}" ${k === xKey ? 'selected' : ''}>${escHtml(k)}</option>`).join('');
  const yVarOptions = OPTIM_YVARS.map(v =>
    `<option value="${v}" ${v === yVar ? 'selected' : ''}>${escHtml(_optimYLabel(v))}</option>`).join('');

  // ── Table: folder × params × A_pico × t_pico × pureza × rendimiento ──────
  const sortedRows = rows.slice().sort((a, b) => (a.params[xKey] ?? 0) - (b.params[xKey] ?? 0));
  const tableRows = sortedRows.map((r, i) => {
    const sim = sims[r.name];
    const cellsParams = keys.map(k =>
      `<td class="font-monospace small">${r.params[k] != null ? r.params[k] : '—'}</td>`).join('');
    const Ap = r.A_pico != null && r.A_pico > 0 ? fmtA(r.A_pico, sim) : '—';
    const tp = r.t_pico != null ? r.t_pico.toFixed(3) : '—';
    const pp = r.P_pct != null ? r.P_pct.toFixed(2) + ' %' : '—';
    const rm = r.rendimiento_medio != null ? fmtA(r.rendimiento_medio, sim) : '—';
    return `
      <tr>
        <td><span class="sim-dot me-1" style="background:${PALETTE[i % PALETTE.length]}"></span><small class="fw-semibold">${escHtml(r.name)}</small></td>
        ${cellsParams}
        <td class="font-monospace small text-danger fw-bold">${Ap}</td>
        <td class="font-monospace small">${tp}</td>
        <td class="font-monospace small">${pp}</td>
        <td class="font-monospace small">${rm}</td>
      </tr>`;
  }).join('');

  const typeLabel = manifest.sweep_type ? t('optim.type_' + manifest.sweep_type) : '';
  const subtitle = (manifest.description || typeLabel) ? `
    <p class="text-muted small mb-2">
      ${manifest.description ? escHtml(manifest.description) : ''}
      ${typeLabel ? `<span class="badge bg-secondary ms-1">${escHtml(typeLabel)}</span>` : ''}
    </p>` : '';

  container.innerHTML = `
    <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-1">
      <h5 class="mb-0">${t('optim.title', { label })}</h5>
      <button class="btn btn-outline-secondary btn-sm" id="btn-export-optim">
        <i class="bi bi-download me-1"></i>${t('export.csv')}
      </button>
    </div>
    ${subtitle}
    <p class="small text-muted">${t('optim.desc')}</p>

    <div class="d-flex flex-wrap gap-3 align-items-end mb-3">
      <div>
        <label class="form-label small mb-1" for="optim-x-select">${t('optim.param_label')}</label>
        <select class="form-select form-select-sm" id="optim-x-select">${paramOptions}</select>
      </div>
      <div>
        <label class="form-label small mb-1" for="optim-y-select">${t('optim.yvar_label')}</label>
        <select class="form-select form-select-sm" id="optim-y-select">${yVarOptions}</select>
      </div>
    </div>

    <div class="card shadow-sm mb-3">
      <div class="card-body p-2">
        <div id="optim-chart" class="plotly-chart-lg"></div>
      </div>
    </div>

    <div class="table-responsive">
      <table class="table table-sm table-hover mb-0" style="font-size:0.82rem">
        <thead class="table-dark">
          <tr>
            <th>${t('overview.th_sim')}</th>
            ${keys.map(k => `<th class="font-monospace">${escHtml(k)}</th>`).join('')}
            <th>${t('optim.th_apico', { unit: uL })}</th>
            <th>${t('optim.th_tpico')}</th>
            <th>${t('optim.th_pureza')}</th>
            <th>${t('optim.th_rendimiento', { unit: uL })}</th>
          </tr>
        </thead>
        <tbody>${tableRows}</tbody>
      </table>
    </div>
  `;

  _renderOptimChart(rows, xKey, yVar, keys, sims);

  const xSel = document.getElementById('optim-x-select');
  if (xSel) xSel.addEventListener('change', e => {
    _state.optimXParam = e.target.value;
    renderOptimizacion();
  });
  const ySel = document.getElementById('optim-y-select');
  if (ySel) ySel.addEventListener('change', e => {
    _state.optimYVar = e.target.value;
    renderOptimizacion();
  });
  const btnExport = document.getElementById('btn-export-optim');
  if (btnExport) btnExport.addEventListener('click', exportOptimizacionCSV);
}

/** Barrido espectral (U4/U4b del BACKLOG): por defecto una SOLA serie por
 * métrica con el nombre del espectro (ACABOptim.spectrumRowLabel) como
 * identificador de cada punto -- nunca el volcado de fracciones
 * espectrales/n_grupos que producía groupByOtherParams al tratarlos como
 * dimensiones de color. U4b restaura el selector de eje X: "Espectro"
 * (categórico, barras, comportamiento de U4 sin cambios) o una fracción
 * espectral numérica (frac_termica/epitermica/rapida -- dispersión de una
 * sola serie con el nombre del espectro como etiqueta de texto junto a cada
 * punto, nunca como leyenda). */
const SPECTRUM_X_CATEGORICAL = 'espectro';

function renderOptimizacionSpectrum(container, iso, manifest, sims, rows) {
  const label = isoLabel(iso);
  const uL    = unitLabel();
  const yVar  = _state.optimYVar;

  const numericKeys = ACABOptim.spectrumNumericKeys(rows);
  if (!_state.optimSpectrumXParam ||
      (_state.optimSpectrumXParam !== SPECTRUM_X_CATEGORICAL &&
       numericKeys.indexOf(_state.optimSpectrumXParam) === -1)) {
    _state.optimSpectrumXParam = SPECTRUM_X_CATEGORICAL;
  }
  const xKey = _state.optimSpectrumXParam;
  const isCategorical = xKey === SPECTRUM_X_CATEGORICAL;

  const sortedRows = isCategorical
    ? rows.slice().sort((a, b) =>
        ACABOptim.spectrumRowLabel(a).localeCompare(ACABOptim.spectrumRowLabel(b)))
    : rows.slice()
        .filter(r => typeof r.params[xKey] === 'number' && isFinite(r.params[xKey]))
        .sort((a, b) => a.params[xKey] - b.params[xKey]);

  const xOptions = [
    `<option value="${SPECTRUM_X_CATEGORICAL}" ${isCategorical ? 'selected' : ''}>${escHtml(t('optim.spectrum_x_categorical'))}</option>`,
    ...ACABOptim.SPECTRUM_FRAC_KEYS.map(k => {
      const available = numericKeys.indexOf(k) !== -1;
      return available
        ? `<option value="${escAttr(k)}" ${k === xKey ? 'selected' : ''}>${escHtml(k)}</option>`
        : `<option value="${escAttr(k)}" disabled title="${escAttr(t('optim.spectrum_x_key_disabled'))}">${escHtml(k)}</option>`;
    }),
  ].join('');
  const disabledNote = numericKeys.length === 0
    ? `<p class="small text-muted mb-2"><i class="bi bi-info-circle me-1"></i>${t('optim.spectrum_x_all_disabled')}</p>`
    : '';

  const yVarOptions = OPTIM_YVARS.map(v =>
    `<option value="${v}" ${v === yVar ? 'selected' : ''}>${escHtml(_optimYLabel(v))}</option>`).join('');

  const tableRows = sortedRows.map((r, i) => {
    const sim = sims[r.name];
    const Ap = r.A_pico != null && r.A_pico > 0 ? fmtA(r.A_pico, sim) : '—';
    const tp = r.t_pico != null ? r.t_pico.toFixed(3) : '—';
    const pp = r.P_pct != null ? r.P_pct.toFixed(2) + ' %' : '—';
    const rm = r.rendimiento_medio != null ? fmtA(r.rendimiento_medio, sim) : '—';
    return `
      <tr>
        <td><span class="sim-dot me-1" style="background:${PALETTE[i % PALETTE.length]}"></span><small class="fw-semibold">${escHtml(ACABOptim.spectrumRowLabel(r))}</small></td>
        <td class="font-monospace small text-danger fw-bold">${Ap}</td>
        <td class="font-monospace small">${tp}</td>
        <td class="font-monospace small">${pp}</td>
        <td class="font-monospace small">${rm}</td>
      </tr>`;
  }).join('');

  const typeLabel = t('optim.type_spectrum');
  const subtitle = `
    <p class="text-muted small mb-2">
      ${manifest.description ? escHtml(manifest.description) : ''}
      <span class="badge bg-secondary ms-1">${escHtml(typeLabel)}</span>
    </p>`;

  container.innerHTML = `
    <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-1">
      <h5 class="mb-0">${t('optim.title', { label })}</h5>
      <button class="btn btn-outline-secondary btn-sm" id="btn-export-optim">
        <i class="bi bi-download me-1"></i>${t('export.csv')}
      </button>
    </div>
    ${subtitle}
    <p class="small text-muted">${t('optim.desc')}</p>

    <div class="d-flex flex-wrap gap-3 align-items-end mb-1">
      <div>
        <label class="form-label small mb-1" for="optim-x-select">${t('optim.param_label')}</label>
        <select class="form-select form-select-sm" id="optim-x-select">${xOptions}</select>
      </div>
      <div>
        <label class="form-label small mb-1" for="optim-y-select">${t('optim.yvar_label')}</label>
        <select class="form-select form-select-sm" id="optim-y-select">${yVarOptions}</select>
      </div>
    </div>
    ${disabledNote}

    <div class="card shadow-sm mb-3">
      <div class="card-body p-2">
        <div id="optim-chart" class="plotly-chart-lg"></div>
      </div>
    </div>

    <div class="table-responsive">
      <table class="table table-sm table-hover mb-0" style="font-size:0.82rem">
        <thead class="table-dark">
          <tr>
            <th>${t('optim.th_espectro')}</th>
            <th>${t('optim.th_apico', { unit: uL })}</th>
            <th>${t('optim.th_tpico')}</th>
            <th>${t('optim.th_pureza')}</th>
            <th>${t('optim.th_rendimiento', { unit: uL })}</th>
          </tr>
        </thead>
        <tbody>${tableRows}</tbody>
      </table>
    </div>
  `;

  if (isCategorical) {
    _renderSpectrumOptimChart(sortedRows, yVar, sims);
  } else {
    _renderSpectrumScatterChart(sortedRows, xKey, yVar, sims);
  }

  const xSel = document.getElementById('optim-x-select');
  if (xSel) xSel.addEventListener('change', e => {
    _state.optimSpectrumXParam = e.target.value;
    renderOptimizacion();
  });
  const ySel = document.getElementById('optim-y-select');
  if (ySel) ySel.addEventListener('change', e => {
    _state.optimYVar = e.target.value;
    renderOptimizacion();
  });
  const btnExport = document.getElementById('btn-export-optim');
  if (btnExport) btnExport.addEventListener('click', exportOptimizacionSpectrumCSV);
}

/** Plotly bar: una sola serie con el nombre del espectro en el eje X
 * (categórico -- sin orden natural entre espectros, a diferencia del resto
 * de tipos de barrido, así que barras en vez de líneas). */
function _renderSpectrumOptimChart(sortedRows, yVar, sims) {
  const div = document.getElementById('optim-chart');
  if (!div) return;

  const x = [], y = [];
  sortedRows.forEach(r => {
    const yv = _optimYDisplay(r, yVar, sims[r.name]);
    if (yv === null) return;
    x.push(ACABOptim.spectrumRowLabel(r));
    y.push(yv);
  });

  const trace = {
    x, y, type: 'bar',
    marker: { color: PALETTE[0] },
    name: _optimYLabel(yVar),
  };
  const layout = {
    margin: { t: 20, r: 20, b: 70, l: 60 },
    xaxis:  { title: t('optim.spectrum_axis_x'), type: 'category' },
    yaxis:  { title: `${_optimYLabel(yVar)} [${_optimYUnit(yVar)}]` },
    showlegend: false,
  };
  Plotly.newPlot(div, [trace], layout, { responsive: true, displayModeBar: true });
}

/** Plotly scatter (U4b): eje X numérico (una fracción espectral), UNA sola
 * serie -- nunca agrupada por parámetros (esa es la leyenda ilegible que U4
 * eliminó). El nombre de cada espectro va como etiqueta de texto junto al
 * punto (ACABOptim.spectrumTextPositions escalona arriba/abajo los puntos
 * próximos en X, p. ej. los 9 reactores reales agrupados en frac_termica). */
function _renderSpectrumScatterChart(sortedRows, xKey, yVar, sims) {
  const div = document.getElementById('optim-chart');
  if (!div) return;

  const x = [], y = [], text = [];
  sortedRows.forEach(r => {
    const yv = _optimYDisplay(r, yVar, sims[r.name]);
    if (yv === null) return;
    x.push(r.params[xKey]);
    y.push(yv);
    text.push(ACABOptim.spectrumRowLabel(r));
  });

  const trace = {
    x, y, text,
    type: 'scatter',
    mode: 'markers+text',
    textposition: ACABOptim.spectrumTextPositions(x),
    textfont: { size: 10 },
    marker: { color: PALETTE[0], size: 9 },
    name: _optimYLabel(yVar),
  };
  const layout = {
    margin: { t: 20, r: 20, b: 50, l: 60 },
    xaxis:  { title: xKey },
    yaxis:  { title: `${_optimYLabel(yVar)} [${_optimYUnit(yVar)}]` },
    showlegend: false,
  };
  Plotly.newPlot(div, [trace], layout, { responsive: true, displayModeBar: true });
}

/** Export de la tabla del barrido espectral (folder→espectro × métricas). */
function exportOptimizacionSpectrumCSV() {
  const iso      = _state.selectedIsotopo;
  const json     = _state.isotopoReport;
  const manifest = _state.analysisData && _state.analysisData.sweep_manifest;
  if (!iso || !json || !manifest || !_state.analysisData) return;

  const sims = _state.analysisData.simulations;
  const simNames = Object.keys(sims);
  const rows = ACABOptim.mergeSweepRows(
    manifest, simNames, json.informe.simulations, json.informe.metricas);
  if (!rows.length) return;

  const sortedRows = rows.slice().sort((a, b) =>
    ACABOptim.spectrumRowLabel(a).localeCompare(ACABOptim.spectrumRowLabel(b)));

  const uL = unitLabel();
  const csvRows = sortedRows.map(r => {
    const sim = sims[r.name];
    return [
      ACABOptim.spectrumRowLabel(r),
      r.A_pico != null ? conv(r.A_pico, sim) : null,
      r.t_pico,
      r.P_pct,
      r.rendimiento_medio != null ? conv(r.rendimiento_medio, sim) : null,
    ];
  });
  const headers = [
    t('optim.th_espectro'),
    `A_pico [${uL}]`, 't_pico [h]', 'pureza [%]', `rendimiento_medio [${uL}/h]`,
  ];
  emitCSV(`${ACABExport.slug(iso)}_optimizacion_${unitSlug()}_${folderSlug()}.csv`, iso, csvRows, headers);
}

/** Plotly scatter/line: variable Y elegida vs. parámetro elegido, una serie
 * por combinación de las demás dimensiones del barrido (color). */
function _renderOptimChart(rows, xKey, yVar, keys, sims) {
  const div = document.getElementById('optim-chart');
  if (!div) return;
  const groups = ACABOptim.groupByOtherParams(rows, xKey, keys);

  const traces = groups.map((g, i) => {
    const xs = [], ys = [];
    g.rows.forEach(r => {
      const yv = _optimYDisplay(r, yVar, sims[r.name]);
      if (yv === null) return;
      xs.push(r.params[xKey]);
      ys.push(yv);
    });
    return {
      x: xs, y: ys,
      mode: 'lines+markers',
      name: g.label || t('optim.series_default'),
      line:   { color: PALETTE[i % PALETTE.length] },
      marker: { color: PALETTE[i % PALETTE.length], size: 8 },
    };
  });

  const layout = {
    margin: { t: 20, r: 20, b: 50, l: 60 },
    xaxis:  { title: xKey },
    yaxis:  { title: `${_optimYLabel(yVar)} [${_optimYUnit(yVar)}]` },
    showlegend: groups.length > 1,
    legend: { orientation: 'h', y: -0.2 },
  };
  Plotly.newPlot(div, traces, layout, { responsive: true, displayModeBar: true });
}

/** Export the sweep table (folder × params × A_pico/t_pico/pureza/rendimiento). */
function exportOptimizacionCSV() {
  const iso      = _state.selectedIsotopo;
  const json     = _state.isotopoReport;
  const manifest = _state.analysisData && _state.analysisData.sweep_manifest;
  if (!iso || !json || !manifest || !_state.analysisData) return;

  const sims = _state.analysisData.simulations;
  const simNames = Object.keys(sims);
  const rows = ACABOptim.mergeSweepRows(
    manifest, simNames, json.informe.simulations, json.informe.metricas);
  const keys = ACABOptim.paramKeys(rows);
  if (!rows.length || !keys.length) return;

  const xKey = (_state.optimXParam && keys.indexOf(_state.optimXParam) !== -1)
    ? _state.optimXParam : keys[0];
  const sortedRows = rows.slice().sort((a, b) => (a.params[xKey] ?? 0) - (b.params[xKey] ?? 0));

  const uL = unitLabel();
  const csvRows = sortedRows.map(r => {
    const sim = sims[r.name];
    return [
      r.name,
      ...keys.map(k => (r.params[k] != null ? r.params[k] : null)),
      r.A_pico != null ? conv(r.A_pico, sim) : null,
      r.t_pico,
      r.P_pct,
      r.rendimiento_medio != null ? conv(r.rendimiento_medio, sim) : null,
    ];
  });
  const headers = [
    t('overview.th_sim'), ...keys,
    `A_pico [${uL}]`, 't_pico [h]', 'pureza [%]', `rendimiento_medio [${uL}/h]`,
  ];
  emitCSV(`${ACABExport.slug(iso)}_optimizacion_${unitSlug()}_${folderSlug()}.csv`, iso, csvRows, headers);
}

// ─────────────────────────────────────────────────────────────────────────────
// Figure editor  (E1–E7)
// ─────────────────────────────────────────────────────────────────────────────

// E4: Open the figure editor modal
function openFigurasEditor() {
  if (!_state.analysisData) {
    showToast(t('toast.analyze_first'), 'warning');
    return;
  }
  renderFigurasEditor(_state.analysisData.figuras || []);

  // Reset button restores to the loaded YAML snapshot (decisión 7) — disabled
  // with a tooltip when there was no YAML to begin with (yaml_used === 'none').
  const resetBtn   = document.getElementById('btn-figuras-reset');
  const hasLoaded  = _state.analysisData.yaml_used !== 'none';
  resetBtn.disabled = !hasLoaded;
  resetBtn.title    = hasLoaded ? '' : t('figeditor.reset_disabled_title');

  bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-figuras')).show();
}

// E5: Populate modal body from a figuras array
function renderFigurasEditor(figuras) {
  const body  = document.getElementById('figuras-editor-body');
  const cards = (figuras.length > 0 ? figuras : [{ titulo: '', series: [] }])
    .map((cfg, idx) => _makeFigCard(cfg, idx + 1))
    .join('');
  body.innerHTML = `
    ${cards}
    <button type="button" class="btn btn-outline-success btn-sm w-100 mt-1"
            id="btn-add-figura">
      <i class="bi bi-plus-lg me-1"></i>${t('figeditor.add_fig')}
    </button>`;
}

// Read the modal DOM into a figuras array (shared by apply/download/save).
function _readFigurasFromEditor() {
  const body    = document.getElementById('figuras-editor-body');
  const figuras = [];

  body.querySelectorAll('.figura-card').forEach((card, idx) => {
    const titulo  = card.querySelector('.fig-titulo')?.value?.trim() || `Figura ${idx + 1}`;
    const series  = [];
    card.querySelectorAll('.series-row').forEach(row => {
      const iso = row.querySelector('.series-iso')?.value?.trim();
      const lbl = row.querySelector('.series-label')?.value?.trim();
      if (iso) series.push(lbl ? { iso, label: lbl } : { iso });
    });
    if (series.length > 0) figuras.push({ num: idx + 1, titulo, series });
  });

  return figuras;
}

// E6: Read modal DOM → update state → re-render charts
function applyFigurasChanges() {
  _state.analysisData.figuras = _readFigurasFromEditor();
  bootstrap.Modal.getInstance(document.getElementById('modal-figuras'))?.hide();

  // Re-render charts tab if already visible; otherwise mark stale so it
  // re-renders on next tab activation
  _state.chartsRendered = false;
  if (document.getElementById('pane-charts')?.classList.contains('show')) {
    renderCharts();
    _state.chartsRendered = true;
  }
  showToast(t('toast.figs_updated'), 'success');
}

// E7: Restore the editor to the YAML snapshot loaded at analyze time
// (decisión 7 — no longer a hardcoded default; button is disabled when there
// was no YAML to begin with, see openFigurasEditor).
function resetFigurasToLoaded() {
  if (!_state.figurasOriginal) return;
  renderFigurasEditor(JSON.parse(JSON.stringify(_state.figurasOriginal)));
  showToast(t('toast.figs_reset'), 'info');
}

// Build the YAML text to save/download: start from the loaded YAML config (if
// any) and replace ONLY the "figuras" key, preserving "semividas" and any
// other top-level section untouched (decisión 6 del runbook de figuras).
function _buildFigurasYamlText() {
  const base = (_state.yamlConfigLoaded && typeof _state.yamlConfigLoaded === 'object')
    ? JSON.parse(JSON.stringify(_state.yamlConfigLoaded))
    : {};
  base.figuras = _readFigurasFromEditor();
  return jsyaml.dump(base, { noRefs: true, lineWidth: -1 });
}

// "Descargar YAML" — genera el fichero en el navegador, sin servidor.
function downloadFigurasYaml() {
  const blob = new Blob([_buildFigurasYamlText()], { type: 'text/yaml' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url;
  a.download = 'figuras.yaml';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// "Guardar en carpeta analizada" — POST /api/figuras/save; pide confirmación
// y reintenta con overwrite si ya existe un figuras.yaml (decisión 5).
async function saveFigurasToFolder() {
  if (!_state.analysisData || !_state.folder) {
    showToast(t('toast.analyze_first'), 'warning');
    return;
  }
  const yamlText = _buildFigurasYamlText();

  async function attempt(overwrite) {
    const res  = await fetch('/api/figuras/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: _state.folder, yaml_text: yamlText, overwrite }),
    });
    const json = await res.json();
    if (res.status === 409 && json.exists && !overwrite) {
      return confirm(t('figeditor.save_confirm_overwrite')) ? attempt(true) : false;
    }
    if (!res.ok || !json.ok) {
      showToast(json.error || t('toast.unknown_err'), 'danger');
      return false;
    }
    return true;
  }

  try {
    if (!(await attempt(false))) return;
    showToast(t('toast.figs_saved'), 'success');
    bootstrap.Modal.getInstance(document.getElementById('modal-figuras'))?.hide();
    // Re-analyze so figuras/badge/reset-snapshot reflect the just-saved
    // figuras.yaml as the new "carpeta" (auto) origin.
    await doAnalyze();
  } catch (err) {
    showToast(t('toast.net_err', { msg: err.message }), 'danger');
  }
}

// ── Figure editor HTML helpers ────────────────────────────────────────────────

function _makeIsoOptions(selectedIso) {
  return (_state.analysisData?.all_isotopes || [])
    .map(iso =>
      `<option value="${escAttr(iso)}"${iso === selectedIso ? ' selected' : ''}>` +
      `${escHtml(isoLabel(iso))} (${escHtml(iso)})</option>`
    )
    .join('');
}

function _makeSeriesRow(iso = '', lbl = '') {
  return `
    <div class="series-row d-flex gap-2 align-items-center mb-1">
      <select class="form-select form-select-sm series-iso flex-grow-1">
        ${_makeIsoOptions(iso)}
      </select>
      <input type="text" class="form-control form-control-sm series-label"
             style="max-width:140px" placeholder="${escAttr(t('figeditor.label_ph'))}"
             value="${escAttr(lbl)}">
      <button type="button" class="btn btn-sm btn-outline-danger btn-remove-series"
              title="${escAttr(t('figeditor.remove_series'))}">
        <i class="bi bi-x-lg"></i>
      </button>
    </div>`;
}

function _makeFigCard(cfg, displayIdx) {
  const series    = cfg.series && cfg.series.length > 0
    ? cfg.series
    : [{ iso: (_state.analysisData?.all_isotopes || [''])[0], label: '' }];
  const seriesHtml = series.map(s => _makeSeriesRow(s.iso || '', s.label || '')).join('');
  return `
    <div class="figura-card card mb-3">
      <div class="card-header d-flex align-items-center py-2">
        <span class="fw-semibold me-auto small fig-num">${t('figeditor.fig', { n: displayIdx })}</span>
        <button type="button" class="btn btn-sm btn-outline-danger btn-remove-fig"
                title="${escAttr(t('figeditor.remove_fig'))}">
          <i class="bi bi-trash"></i>
        </button>
      </div>
      <div class="card-body py-2">
        <div class="mb-2">
          <label class="form-label small fw-semibold mb-1">${t('figeditor.title_label')}</label>
          <input type="text" class="form-control form-control-sm fig-titulo"
                 value="${escAttr(cfg.titulo || '')}">
        </div>
        <div>
          <label class="form-label small fw-semibold mb-1">${t('figeditor.series_label')}</label>
          <div class="series-list">${seriesHtml}</div>
          <button type="button" class="btn btn-sm btn-outline-primary mt-1 btn-add-series">
            <i class="bi bi-plus-lg me-1"></i>${t('figeditor.add_series')}
          </button>
        </div>
      </div>
    </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Utility functions
// ─────────────────────────────────────────────────────────────────────────────

function setLoading(show, text) {
  const overlay = document.getElementById('loading-overlay');
  if (text) document.getElementById('loading-text').textContent = text;
  overlay.classList.toggle('d-none', !show);
}

function setStatus(text, type) {
  const badge = document.getElementById('status-badge');
  badge.textContent = text;
  badge.className = `badge bg-${type}`;
}

function showYamlStatus(yamlUsed) {
  const okEl   = document.getElementById('yaml-ok');
  const warnEl = document.getElementById('yaml-warn');
  const badge  = document.getElementById('yaml-badge');

  okEl.classList.add('d-none');
  warnEl.classList.add('d-none');
  badge.classList.add('d-none');

  if (yamlUsed === 'none') {
    warnEl.classList.remove('d-none');
  } else {
    const src = yamlUsed === 'upload' ? t('yaml.src_upload') : t('yaml.src_auto');
    document.getElementById('yaml-ok-text').textContent = t('yaml.loaded', { src });
    okEl.classList.remove('d-none');
    badge.classList.remove('d-none');
    badge.className = 'badge bg-success';
    badge.innerHTML = '<i class="bi bi-file-earmark-check me-1"></i>YAML';
  }
}

// E-badge: origin badge in the figuras-tab toolbar. Same three states as
// showYamlStatus (auto|upload|none), relabelled for the figures context
// (carpeta / cargado a mano / sin figuras — decisión 4 del runbook).
function updateFigurasBadge(yamlUsed) {
  const badge = document.getElementById('figuras-badge');
  if (!badge) return;
  const byState = {
    auto:   { cls: 'bg-success',   key: 'charts.badge_carpeta' },
    upload: { cls: 'bg-info',      key: 'charts.badge_manual' },
    none:   { cls: 'bg-secondary', key: 'charts.badge_none' },
  };
  const cfg = byState[yamlUsed] || byState.none;
  badge.className = `badge ${cfg.cls}`;
  badge.textContent = t(cfg.key);
  badge.classList.remove('d-none');
}

function renderErrors(errors) {
  const panel = document.getElementById('errors-panel');
  const list  = document.getElementById('errors-list');
  const entries = Object.entries(errors);
  if (entries.length === 0) {
    panel.classList.add('d-none');
    return;
  }
  panel.classList.remove('d-none');
  list.innerHTML = entries.map(([k, v]) =>
    `<li><code>${escHtml(k)}</code>: ${escHtml(v)}</li>`
  ).join('');
}

function showToast(msg, type = 'info') {
  const toast = document.getElementById('toast-msg');
  const body  = document.getElementById('toast-body');
  body.textContent = msg;
  toast.className = `toast align-items-center border-0 text-bg-${type}`;
  new bootstrap.Toast(toast, { delay: 6000 }).show();
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escAttr(s) {
  return String(s).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/** Último segmento de una ruta Windows/POSIX (badge de referencia, F9f). */
function _folderBasename(path) {
  if (!path) return '';
  const parts = String(path).split(/[\\/]/).filter(Boolean);
  return parts.length ? parts[parts.length - 1] : path;
}

function fmtSci(v) {
  if (v === null || v === undefined || v === 0) return '0';
  const n = Number(v);
  if (isNaN(n)) return '—';
  return n.toExponential(3);
}

function parseFloatOrNull(s) {
  if (!s || !s.trim()) return null;
  const f = parseFloat(s);
  return isNaN(f) ? null : f;
}

/**
 * Convert ACAB isotope key ('TE121M') to Unicode superscript label ('¹²¹ᵐTe').
 */
function isoLabel(key) {
  const sup = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
                '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹' };
  const m = String(key).match(/^([A-Z]{1,2})(\d+)(M?)$/i);
  if (!m) return key;
  const elem = m[1][0].toUpperCase() + (m[1][1] ? m[1][1].toLowerCase() : '');
  const mass = m[2].split('').map(c => sup[c] || c).join('');
  const meta = m[3] ? 'ᵐ' : '';
  return `${mass}${meta}${elem}`;
}
