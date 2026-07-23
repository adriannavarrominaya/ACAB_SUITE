/* sweep.js — Pestaña "Barrido paramétrico" (Fase 3 del runbook v2).
 *
 * Calcula en el cliente, por simulación, un `patch` (fragmento del dict del
 * formulario) usando las funciones puras de sweep_utils.js / calc_utils.js, y
 * delega en el endpoint genérico /api/sweep del servidor la escritura de las
 * carpetas.  Sigue el patrón de chains.js: un IIFE que engancha sus listeners
 * en DOMContentLoaded y reutiliza los globales de app.js (t, appState,
 * collectAll, validateAll, showToast, showValidationModal, parseIntArray…).
 */
(function () {
  'use strict';

  const LS_KEYS = {
    root: 'acab-sweep-root', base: 'acab-sweep-base', prefix: 'acab-sweep-prefix',
    loadRoot: 'acab-sweep-load-root',
  };
  let _lastPatches = [];        // [{params, patch, suffix}] tras "Previsualizar"
  let _lastFluxGuardrail = [];  // U5(c): [{value, xnorm}] sospechosos del último buildPatches (solo tipo 'flux')

  // ── Barrido espectral (Fase P3 del RUNBOOK_barrido_espectral.md) ─────────
  const XSBL_LIBRARY_NGROUP = 211;   // D5: constante de configuración (grupos de la librería XSBL)
  let _spectrumRows = [];            // [{id, label, suffix, parsed, indices, patch}]
  let _spectrumRowSeq = 0;
  let _spectrumPhiRefEdited = false; // D1: solo se parchea block3 si el usuario edita φ_ref

  // ── Barrido temporal (U7 del BACKLOG): acordeón de tarjetas, una por sim ──
  // Cada tarjeta instancia el editor de tramos COMPLETO (b78_editor.js, el
  // MISMO componente que usa la pestaña manual) con un prefijo de ids único
  // — cero divergencia de validaciones entre el generador manual y el
  // barrido, por ser literalmente el mismo código.
  let _timeSimCards = [];   // [{id, fasesIrr, fasesCool, iunit, iout, iplot, seeded}]
  let _timeSimSeq = 0;
  let _timeExpandedId = null; // tarjeta a expandir en el próximo render (recién añadida/duplicada)

  const $ = id => document.getElementById(id);

  function humanBytes(n) {
    if (!Number.isFinite(n) || n <= 0) return '0 B';
    const u = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0, v = n;
    while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
    return `${v.toFixed(i ? 1 : 0)} ${u[i]}`;
  }

  function currentType() {
    const el = document.querySelector('input[name="sweep-type"]:checked');
    return el ? el.value : 'flux';
  }

  function setMsg(kind, text) {
    const el = $('sweep-msg');
    if (!el) return;
    el.className = `alert alert-${kind} py-2 small`;
    el.textContent = text;
    el.classList.remove('d-none');
  }
  function clearMsg() { const el = $('sweep-msg'); if (el) el.classList.add('d-none'); }

  // ── Validación del fichero base ──────────────────────────────────────────
  function refreshValidation() {
    const banner = $('sweep-validation-banner');
    if (!banner) return true;
    if (!appState.data) appState.data = {};
    collectAll(appState.data);
    const r = validateAll();
    const ok = r.errors.length === 0;
    if (ok) {
      banner.className = 'alert alert-success py-2 small mb-3';
      banner.innerHTML = `<i class="bi bi-check-circle-fill me-1"></i>${t('sweep.val_ok')}`;
    } else {
      const items = r.errors.map(e => `<li>${e.msg}</li>`).join('');
      banner.className = 'alert alert-danger py-2 small mb-3';
      banner.innerHTML =
        `<strong><i class="bi bi-x-circle-fill me-1"></i>`
        + `${t('sweep.val_bad').replace('{n}', r.errors.length)}</strong>`
        + `<ul class="mb-2 mt-2 ps-3">${items}</ul>`
        + `<button type="button" class="btn btn-sm btn-outline-danger" id="sweep-val-details">`
        + `${t('sweep.val_details')}</button>`;
      const btn = $('sweep-val-details');
      if (btn) btn.addEventListener('click', () => showValidationModal(r, null));
    }
    $('sweep-preview-btn').disabled = !ok;
    $('sweep-generate-btn').disabled = true;  // requiere previsualizar primero
    return ok;
  }

  // ── Paneles por tipo ─────────────────────────────────────────────────────
  function syncTypePanels() {
    const type = currentType();
    ['flux', 'mass', 'time', 'spectrum'].forEach(k =>
      $(`sweep-panel-${k}`).classList.toggle('d-none', k !== type));
    if (type === 'flux') refreshFluxInfo();
    if (type === 'mass') refreshMassPanel();
    if (type === 'time') { seedTimeSimCardsFromBase(); renderTimeSimCards(); }
    if (type === 'spectrum') refreshSpectrumPanel();
    hidePreview();
  }

  function fluxMode() {
    const el = document.querySelector('input[name="sweep-flux-mode"]:checked');
    return el ? el.value : 'xnorm';
  }

  // U5(a)+(b): placeholder y etiqueta del campo de valores dependen del modo
  // (factores XNORM vs. flujo total objetivo) y, en modo flujo, del φ_base
  // REAL del fichero cargado — nunca se mezcla el placeholder de un modo con
  // la etiqueta del otro.
  function refreshFluxValuesUI(phi) {
    const label = $('sweep-flux-values-lbl');
    const input = $('sweep-flux-values');
    if (!label || !input) return;
    const mode = fluxMode();
    const labelKey = mode === 'phi' ? 'sweep.flux_values_lbl_phi' : 'sweep.flux_values_lbl_xnorm';
    label.dataset.i18n = labelKey;
    label.textContent = t(labelKey);
    const ph = fluxValuesPlaceholder(mode, phi);
    input.placeholder = ph != null ? ph : t('sweep.flux_values_ph_phi_generic');
  }

  function refreshFluxInfo() {
    if (!appState.data) appState.data = {};
    collectAll(appState.data);
    const phi = fluxBaseTotal(appState.data.block3, appState.data.block9);
    const el = $('sweep-flux-phibase');
    if (el) el.textContent = Number.isFinite(phi) && phi > 0 ? phi.toExponential(4) : '—';
    refreshFluxValuesUI(phi);
  }

  function refreshMassPanel() {
    // Selector de zona (zonas activas de NUCZO)
    const sel = $('sweep-mass-zone');
    if (sel) {
      const prev  = sel.value;
      const nuczo = parseIntArray(getVal('b2-NUCZO'));
      const opts = [];
      nuczo.forEach((n, i) => {
        if (n !== 0) opts.push(`<option value="${i}">${t('b5.zone_lbl')} ${i + 1}</option>`);
      });
      sel.innerHTML = opts.join('');
      if (prev && [...sel.options].some(o => o.value === prev)) sel.value = prev;
    }
    // Prefill desde la composición asistida si se usó
    if (!getVal('sweep-mass-formula')) {
      const f = getVal('b5calc-formula');
      if (f) setVal('sweep-mass-formula', f);
    }
    if (!getVal('sweep-mass-vol')) {
      const v = getVal('b5calc-vol');
      if (v) setVal('sweep-mass-vol', v);
    }
    // Bloqueo si INPT=2
    const inpt2 = getInt('b1-INPT') === 2;
    $('sweep-mass-inpt2').classList.toggle('d-none', !inpt2);
  }

  // Reconstruye las fases del fichero base (para sembrar la primera
  // tarjeta) a partir de blocks78.times, igual que el generador manual con
  // _tryPopulateGeneratorFromTimes: colapsa la malla intermedia a UN tramo
  // por fase (los límites entre tramos no sobreviven al parseo de un
  // inp.5, solo la lista plana de pasos) — misma limitación aceptada que
  // ya tenía el generador manual, no algo nuevo de U7.
  function baseFases() {
    const times = appState.data?.blocks78?.times || [];
    const irr  = times.filter(([, k]) => k === 1).map(([v]) => v);
    const cool = times.filter(([, k]) => k === 0).map(([v]) => v);
    const out = { baseIrr: [], baseCool: [] };
    if (irr.length)  out.baseIrr  = [{ t_fin: irr[irr.length - 1],   pasos: Math.min(irr.length, 10) }];
    if (cool.length) out.baseCool = [{ t_fin: cool[cool.length - 1], pasos: Math.min(cool.length, 10) }];
    return out;
  }

  // ── Barrido temporal: acordeón de tarjetas (U7) ─────────────────────────
  function seedTimeSimCardsFromBase() {
    if (_timeSimCards.length > 0) return;
    const { baseIrr, baseCool } = baseFases();
    const set0 = appState.data?.blocks78?.sets?.[0];
    _timeSimCards.push({
      id: ++_timeSimSeq,
      fasesIrr: baseIrr, fasesCool: baseCool,
      iunit: set0?.IUNIT ?? 3,
      iout:  set0?.IOUT  ? 1 : 0,
      iplot: set0?.IPLOT ? 1 : 0,
      seeded: true,
    });
  }

  function _timeSummaryPart(phaseKey, tramos, final) {
    if (!tramos) return t(`sweep.time_summary_empty_${phaseKey}`);
    const key = tramos === 1 ? `sweep.time_summary_${phaseKey}_one` : `sweep.time_summary_${phaseKey}`;
    return t(key).replace('{n}', tramos).replace('{t}', final);
  }

  function _timeCardSummaryText(card) {
    const s = summarizeFases(card.fasesIrr, card.fasesCool);
    return [
      _timeSummaryPart('irr', s.irrTramos, s.irrFinal),
      _timeSummaryPart('cool', s.coolTramos, s.coolFinal),
    ].join(' · ');
  }

  function _syncTimeCard(id) {
    const card = _timeSimCards.find(c => c.id === id);
    if (!card) return;
    const prefix = `sweep-time-${id}`;
    const { fasesIrr, fasesCool } = getB78EditorFases(prefix);
    const { iunit, iout, iplot } = getB78EditorIunitIoutIplot(prefix);
    Object.assign(card, { fasesIrr, fasesCool, iunit, iout, iplot });
    const summaryEl = $(`sweep-time-summary-${id}`);
    if (summaryEl) summaryEl.textContent = _timeCardSummaryText(card);
    hidePreview();
  }

  function _mountTimeCardEditor(card) {
    const prefix = `sweep-time-${card.id}`;
    const host = $(`sweep-time-editor-${card.id}`);
    if (!host) return;
    host.innerHTML = b78EditorBodyHtml(prefix);
    setVal(`${prefix}-iunit`, card.iunit);
    const ioutEl  = $(`${prefix}-iout`);  if (ioutEl)  ioutEl.checked  = !!card.iout;
    const iplotEl = $(`${prefix}-iplot`); if (iplotEl) iplotEl.checked = !!card.iplot;
    const onChange = () => _syncTimeCard(card.id);
    setB78EditorFases(prefix, card.fasesIrr, card.fasesCool, onChange);
    wireB78EditorButtons(prefix, onChange);
  }

  function renderTimeSimCards() {
    const container = $('sweep-time-accordion');
    if (!container) return;
    const expandId = _timeExpandedId != null
      ? _timeExpandedId
      : (_timeSimCards[0] ? _timeSimCards[0].id : null);
    container.innerHTML = _timeSimCards.map((card, idx) => {
      const expanded = card.id === expandId;
      const seededHint = card.seeded
        ? `<div class="alert alert-warning py-2 small">${t('sweep.time_seeded_hint')}</div>` : '';
      return `
        <div class="accordion-item">
          <h2 class="accordion-header d-flex">
            <button class="accordion-button flex-grow-1 ${expanded ? '' : 'collapsed'}" type="button"
                    data-bs-toggle="collapse" data-bs-target="#sweep-time-collapse-${card.id}">
              <span class="me-2 fw-bold">#${idx + 1}</span>
              <span class="small text-muted sweep-time-summary" id="sweep-time-summary-${card.id}">${_timeCardSummaryText(card)}</span>
            </button>
            <button type="button" class="btn btn-outline-secondary border-0 rounded-0 sweep-time-dup-btn"
                    data-id="${card.id}" title="${t('sweep.time_dup')}">
              <i class="bi bi-files"></i>
            </button>
            <button type="button" class="btn btn-outline-danger border-0 rounded-0 sweep-time-del-btn"
                    data-id="${card.id}" title="${t('sweep.time_del')}">
              <i class="bi bi-trash"></i>
            </button>
          </h2>
          <div id="sweep-time-collapse-${card.id}" class="accordion-collapse collapse ${expanded ? 'show' : ''}"
               data-bs-parent="#sweep-time-accordion">
            <div class="accordion-body">
              ${seededHint}
              <div id="sweep-time-editor-${card.id}"></div>
            </div>
          </div>
        </div>`;
    }).join('');

    _timeSimCards.forEach(_mountTimeCardEditor);
    _timeExpandedId = null;

    container.querySelectorAll('.sweep-time-dup-btn').forEach(btn => btn.addEventListener('click', () => {
      const id = parseInt(btn.dataset.id, 10);
      const idx = _timeSimCards.findIndex(c => c.id === id);
      if (idx < 0) return;
      _timeSimCards = insertDuplicate(_timeSimCards, idx);
      const clone = _timeSimCards[idx + 1];
      clone.id = ++_timeSimSeq;
      clone.seeded = false;
      _timeExpandedId = clone.id;
      renderTimeSimCards();
      hidePreview();
    }));
    container.querySelectorAll('.sweep-time-del-btn').forEach(btn => btn.addEventListener('click', () => {
      const id = parseInt(btn.dataset.id, 10);
      _timeSimCards = _timeSimCards.filter(c => c.id !== id);
      renderTimeSimCards();
      hidePreview();
    }));
  }

  function addTimeSimCard() {
    if (_timeSimCards.length === 0) { seedTimeSimCardsFromBase(); renderTimeSimCards(); return; }
    const lastIdx = _timeSimCards.length - 1;
    _timeSimCards = insertDuplicate(_timeSimCards, lastIdx);
    const clone = _timeSimCards[lastIdx + 1];
    clone.id = ++_timeSimSeq;
    clone.seeded = false;
    _timeExpandedId = clone.id;
    renderTimeSimCards();
    hidePreview();
  }

  // ── Panel: Espectro (COLLAPS) — Fase P3 del RUNBOOK_barrido_espectral.md ──
  // Reutiliza conderc_import.js (P2) para parseo (parseConderc), índices
  // (spectralIndices) y patch (buildSpectrumPatch); esta capa solo hace UI.

  function spectrumPhiRefBase() {
    const flux = (appState.data && appState.data.block3 && appState.data.block3.FLUX) || [];
    return flux.reduce((a, b) => a + (Number(b) || 0), 0);
  }

  function refreshSpectrumPanel() {
    if (!appState.data) appState.data = {};
    collectAll(appState.data);
    const el = $('sweep-spectrum-phiref');
    if (el && !_spectrumPhiRefEdited) {
      const base = spectrumPhiRefBase();
      el.value = Number.isFinite(base) && base > 0 ? base.toExponential(4) : '';
    }
    renderSpectrumRows();
  }

  function _sanitizeSuffix(s) {
    const clean = String(s == null ? '' : s).trim().replace(/[^A-Za-z0-9._+-]/g, '_');
    return clean || 'espectro';
  }

  async function handleSpectrumFiles(fileList) {
    for (const file of fileList) {
      let text;
      try {
        text = await file.text();
      } catch (_) {
        setMsg('danger', t('sweep.err_spectrum_read').replace('{file}', file.name));
        continue;
      }
      addSpectrumRow(file.name, text);
    }
  }

  function addSpectrumRow(filename, text) {
    let parsed, indices, patch;
    try {
      parsed = parseConderc(text);
      indices = spectralIndices(parsed.boundaries_eV, parsed.data);
      patch = buildSpectrumPatch(parsed, { cxUnit: 'MeV' });
    } catch (e) {
      setMsg('danger', t('sweep.err_spectrum_parse').replace('{file}', filename).replace('{err}', e.message));
      return;
    }
    const baseLabel = filename.replace(/\.[^./\\]+$/, '') || filename;
    const takenSuffixes = _spectrumRows.map(r => r.suffix);
    const suffix = uniqueSuffix(_sanitizeSuffix(baseLabel), takenSuffixes);
    _spectrumRows.push({
      id: ++_spectrumRowSeq, label: baseLabel, suffix, parsed, indices, patch,
    });
    clearMsg();
    renderSpectrumRows();
    hidePreview();
  }

  function renderSpectrumRows() {
    const tb = $('sweep-spectrum-tbody');
    if (!tb) return;
    tb.innerHTML = '';
    _spectrumRows.forEach(row => {
      const tr = document.createElement('tr');

      const tdLabel = document.createElement('td');
      const labelInput = document.createElement('input');
      labelInput.type = 'text';
      labelInput.className = 'form-control form-control-sm font-monospace';
      labelInput.value = row.label;
      labelInput.addEventListener('input', () => { row.label = labelInput.value; hidePreview(); });
      tdLabel.appendChild(labelInput);
      tr.appendChild(tdLabel);

      const tdN = document.createElement('td');
      tdN.className = 'text-center font-monospace';
      tdN.textContent = row.parsed.n;
      tr.appendChild(tdN);

      const tdRange = document.createElement('td');
      tdRange.className = 'text-center font-monospace small';
      const bounds = row.parsed.boundaries_eV;
      const eMin = Math.min(...bounds);
      const eMax = Math.max(...bounds);
      tdRange.textContent = `${eMin.toExponential(2)} – ${eMax.toExponential(2)} eV`;
      tdRange.title = t('sweep.spectrum_erange_hint');
      tr.appendChild(tdRange);

      const tdOrder = document.createElement('td');
      tdOrder.className = 'text-center';
      tdOrder.textContent = row.parsed.orden === 'decreciente'
        ? t('sweep.spectrum_order_desc') : t('sweep.spectrum_order_asc');
      tdOrder.title = t('sweep.spectrum_order_confirm');
      tr.appendChild(tdOrder);

      const tdChecksum = document.createElement('td');
      tdChecksum.className = 'text-center';
      tdChecksum.innerHTML = `<span class="badge bg-success"><i class="bi bi-check-circle-fill me-1"></i>${t('sweep.spectrum_checksum_ok')}</span>`;
      tr.appendChild(tdChecksum);

      const tdThermal = document.createElement('td');
      tdThermal.className = 'text-center font-monospace';
      tdThermal.textContent = `${(row.indices.frac_termica * 100).toFixed(1)}%`;
      tr.appendChild(tdThermal);

      const tdWarn = document.createElement('td');
      tdWarn.className = 'text-center';
      if (row.parsed.n < XSBL_LIBRARY_NGROUP) {
        tdWarn.innerHTML = '<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle-fill"></i></span>';
        tdWarn.title = t('sweep.spectrum_warn_directional');
      }
      tr.appendChild(tdWarn);

      const tdDel = document.createElement('td');
      tdDel.className = 'text-center';
      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.className = 'btn btn-sm btn-outline-danger p-1 lh-1';
      delBtn.innerHTML = '<i class="bi bi-x-lg"></i>';
      delBtn.addEventListener('click', () => {
        _spectrumRows = _spectrumRows.filter(r => r.id !== row.id);
        renderSpectrumRows();
        hidePreview();
      });
      tdDel.appendChild(delBtn);
      tr.appendChild(tdDel);

      tb.appendChild(tr);
    });

    const empty = $('sweep-spectrum-empty');
    if (empty) empty.classList.toggle('d-none', _spectrumRows.length > 0);

    updateSpectrumPlot();
  }

  function updateSpectrumPlot() {
    const div = $('sweep-spectrum-plot');
    if (!div || typeof Plotly === 'undefined') return;
    if (_spectrumRows.length === 0) {
      Plotly.purge(div);
      div.classList.add('d-none');
      return;
    }
    div.classList.remove('d-none');

    const traces = _spectrumRows.map(row => {
      const { boundaries_eV, data, total } = row.parsed;
      const x = [], y = [];
      for (let i = 0; i < data.length; i++) {
        const eHi = Math.max(boundaries_eV[i], boundaries_eV[i + 1]);
        const eLo = Math.min(boundaries_eV[i], boundaries_eV[i + 1]);
        if (!(eHi > eLo) || eLo <= 0) continue;
        const width = Math.log(eHi / eLo);
        const dNorm = total > 0 ? data[i] / total : data[i];
        x.push(Math.sqrt(eHi * eLo));
        y.push(dNorm / width);
      }
      return { x, y, mode: 'lines', type: 'scatter', name: row.label };
    });

    Plotly.newPlot(div, traces, {
      margin: { t: 20, r: 20, b: 45, l: 55 },
      xaxis: { title: t('sweep.spectrum_plot_x'), type: 'log' },
      yaxis: { title: t('sweep.spectrum_plot_y'), type: 'log' },
      legend: { orientation: 'h' },
    }, { displaylogo: false, responsive: true });
  }

  // ── Construcción de patches (cliente) ────────────────────────────────────
  function buildPatches() {
    const type = currentType();
    if (!appState.data) appState.data = {};
    collectAll(appState.data);
    _lastFluxGuardrail = [];

    if (type === 'flux') {
      const mode = document.querySelector('input[name="sweep-flux-mode"]:checked')?.value || 'xnorm';
      const vals = parseSweepValues(getVal('sweep-flux-values'));
      const phi  = fluxBaseTotal(appState.data.block3, appState.data.block9);
      const list = buildFluxPatches(vals, mode, phi);
      _lastFluxGuardrail = fluxSweepGuardrail(vals, mode, phi);
      return list.map(p => ({ ...p, suffix: proposeSuffix('flux', p.patch.block9.XNORM) }));
    }

    if (type === 'mass') {
      if (getInt('b1-INPT') === 2) throw new Error(t('sweep.mass_inpt2'));
      if (!_atomicData || !_atomicData.elements)
        throw new Error(t('sweep.err_no_atomic'));
      const masas   = parseSweepValues(getVal('sweep-mass-values'));
      const formula = getVal('sweep-mass-formula').trim();
      const volumen = parseFloat(getVal('sweep-mass-vol'));
      const zoneIdx = parseInt(getVal('sweep-mass-zone'), 10) || 0;
      const list = buildMassPatches({
        masas, formula, volumen, inpt: getInt('b1-INPT') || 1, zoneIdx,
        baseBlock5: appState.data.block5, elements: _atomicData.elements,
      });
      return list.map(p => ({ ...p, suffix: proposeSuffix('mass', p.params.mass) }));
    }

    if (type === 'time') {
      if (_timeSimCards.length === 0) throw new Error(t('sweep.err_no_rows'));
      const rows = _timeSimCards.map(c => ({
        fasesIrr: c.fasesIrr, fasesCool: c.fasesCool,
        iunit: c.iunit, iout: c.iout, iplot: c.iplot,
      }));
      const list = buildTimePatches(rows, { t });
      const taken = [];
      return list.map(p => {
        const base = proposeSuffix('time',
          Number.isFinite(p.params.t_irr_fin) ? p.params.t_irr_fin : p.params.t_cool_fin);
        // U7: dos tarjetas pueden compartir t_irr_fin con historiales
        // distintos (misma duración, distinta segmentación) — se reutiliza
        // el desambiguador ya usado por el barrido espectral para no
        // colisionar de carpeta.
        const suffix = uniqueSuffix(base, taken);
        taken.push(suffix);
        return { ...p, suffix };
      });
    }

    // spectrum (Fase P3): D1 — φ_ref solo se parchea (uniforme, todas las
    // sims) si el usuario lo edita; el resto del inp.5 queda intacto.
    if (_spectrumRows.length === 0) throw new Error(t('sweep.err_no_spectra'));
    let block3Patch = null;
    if (_spectrumPhiRefEdited) {
      const phiRef = parseFloat(getVal('sweep-spectrum-phiref'));
      if (!Number.isFinite(phiRef) || phiRef <= 0) throw new Error(t('sweep.err_bad_phiref'));
      block3Patch = { block3: { FLUX: [phiRef] } };
    }
    return _spectrumRows.map(row => ({
      params: {
        espectro: row.label,
        n_grupos: row.parsed.n,
        frac_termica: row.indices.frac_termica,
        frac_epitermica: row.indices.frac_epitermica,
        frac_rapida: row.indices.frac_rapida,
      },
      patch: block3Patch || {},
      coll_patch: row.patch,
      suffix: row.suffix,
    }));
  }

  function paramsLabel(params) {
    // typeof v !== 'object' descarta arrays/dicts (p. ej. historial_irr/
    // historial_cool de U7): son datos de trazabilidad para el manifest,
    // no un valor compacto para la etiqueta "k=v, k=v" de la previsualización
    // -- sin este filtro un array de tramos se renderiza como
    // "[object Object],[object Object]".
    return Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== null && !Number.isNaN(v) && typeof v !== 'object')
      .map(([k, v]) => `${k}=${typeof v === 'number' ? (Math.abs(v) < 1e-3 || Math.abs(v) >= 1e6 ? v.toExponential(3) : v) : v}`)
      .join(', ');
  }

  // ── Previsualizar ────────────────────────────────────────────────────────
  async function doPreview() {
    clearMsg();
    hidePreview();
    if (!refreshValidation()) return;
    let patches;
    try {
      patches = buildPatches();
    } catch (e) {
      setMsg('danger', e.message);
      return;
    }
    if (patches.length === 0) { setMsg('warning', t('sweep.err_no_values')); return; }
    _lastPatches = patches;

    const prefix = getVal('sweep-prefix');
    const sims = patches.map(p => ({ suffix: p.suffix }));

    let res;
    try {
      const r = await fetch('/api/sweep/preview', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          root: getVal('sweep-root'), base_folder: getVal('sweep-base'),
          prefix, sims,
        }),
      });
      res = await r.json();
      if (!r.ok || !res.ok) throw new Error(res.error || 'preview error');
    } catch (e) {
      setMsg('danger', e.message);
      return;
    }

    renderPreview(patches, prefix, res);
  }

  function renderPreview(patches, prefix, res) {
    $('sweep-preview').classList.remove('d-none');
    $('sweep-preview-n').textContent = patches.length;
    $('sweep-preview-pattern').textContent = `${prefix}<${t('sweep.suffix_word')}>`;
    $('sweep-preview-disk').textContent = humanBytes(res.est_disk);

    const warnEl = $('sweep-preview-warn');
    const warns = [];
    if (!res.base_exists) warns.push(t('sweep.warn_no_base'));
    if (res.base_has_inp5) warns.push(t('sweep.warn_base_inp5'));
    if (res.collisions && res.collisions.length)
      warns.push(t('sweep.warn_collisions').replace('{list}', res.collisions.join(', ')));
    if (res.est_disk > 2 * 1024 * 1024 * 1024)
      warns.push(t('sweep.warn_disk').replace('{size}', humanBytes(res.est_disk)));
    if (currentType() === 'flux' && _lastFluxGuardrail.length) {
      const list = _lastFluxGuardrail.map(g => g.value).join(', ');
      const key = fluxMode() === 'phi' ? 'sweep.warn_flux_mode_confusion_phi' : 'sweep.warn_flux_mode_confusion_xnorm';
      warns.push(t(key).replace('{list}', list));
    }
    if (warns.length) {
      warnEl.innerHTML = warns.map(w => `<div>${w}</div>`).join('');
      warnEl.classList.remove('d-none');
    } else {
      warnEl.classList.add('d-none');
    }

    const tb = $('sweep-preview-tbody');
    tb.innerHTML = '';
    patches.forEach((p, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML =
        `<td class="small">${paramsLabel(p.params)}</td>`
        + `<td><input type="text" class="form-control form-control-sm font-monospace sweep-suffix-in" value="${p.suffix}"></td>`
        + `<td class="font-monospace small sweep-folder-cell">${prefix}${p.suffix}</td>`;
      tb.appendChild(tr);
      const inp = tr.querySelector('.sweep-suffix-in');
      inp.addEventListener('input', () => {
        p.suffix = inp.value;
        tr.querySelector('.sweep-folder-cell').textContent = `${prefix}${inp.value}`;
      });
    });

    // Habilitar generar solo si base accesible y sin sufijos inválidos
    const canGen = res.base_exists && !res.over_limit;
    $('sweep-generate-btn').disabled = !canGen;
  }

  function hidePreview() {
    const el = $('sweep-preview');
    if (el) el.classList.add('d-none');
    $('sweep-generate-btn').disabled = true;
  }

  // ── Generar ──────────────────────────────────────────────────────────────
  function collectFixedParams() {
    const fp = {};
    const type = currentType();
    const b9 = appState.data?.block9 || {};
    fp.XNORM_base = b9.XNORM;
    const phi = fluxBaseTotal(appState.data?.block3, b9);
    if (Number.isFinite(phi) && phi > 0) fp.phi_base = phi.toExponential(4);
    if (type === 'mass') {
      const f = getVal('sweep-mass-formula'); if (f) fp.formula = f;
      const v = getVal('sweep-mass-vol');     if (v) fp.volumen_cc = v;
    }
    if (type === 'spectrum') {
      const phiRef = parseFloat(getVal('sweep-spectrum-phiref'));
      if (Number.isFinite(phiRef) && phiRef > 0) fp.phi_ref = phiRef.toExponential(4);
      fp.libreria_ngroup = XSBL_LIBRARY_NGROUP;
    }
    return fp;
  }

  async function doGenerate(overwrite) {
    clearMsg();
    if (!refreshValidation()) return;
    if (!_lastPatches.length) { setMsg('warning', t('sweep.err_preview_first')); return; }
    if (!getVal('sweep-desc').trim()) { setMsg('danger', t('sweep.err_desc')); return; }

    const n = _lastPatches.length;
    if (n > 30 && !overwrite &&
        !window.confirm(t('sweep.confirm_many').replace('{n}', n))) return;

    // Re-sincronizar sufijos editados en la tabla
    const sims = _lastPatches.map(p => ({
      suffix: p.suffix, params: p.params, patch: p.patch,
      ...(p.coll_patch ? { coll_patch: p.coll_patch } : {}),
    }));

    const payload = {
      root: getVal('sweep-root'), base_folder: getVal('sweep-base'),
      prefix: getVal('sweep-prefix'), description: getVal('sweep-desc'),
      sweep_type: currentType(), fixed_params: collectFixedParams(),
      data: appState.data, sims, overwrite: !!overwrite,
    };

    $('sweep-spinner').classList.remove('d-none');
    $('sweep-generate-btn').disabled = true;
    try {
      const r = await fetch('/api/sweep', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const res = await r.json();
      if (r.status === 409) {
        if (window.confirm(t('sweep.confirm_overwrite') + '\n\n' + (res.error || ''))) {
          $('sweep-spinner').classList.add('d-none');
          return doGenerate(true);
        }
        setMsg('warning', res.error || 'colisión');
        return;
      }
      if (!r.ok || !res.ok) throw new Error(res.error || 'error');
      setMsg('success', t('sweep.done').replace('{n}', res.n_written).replace('{root}', res.root));
      showToast(t('sweep.done_toast').replace('{n}', res.n_written), 'success');
      showSweepRunPanel(res.root, res.folders);
    } catch (e) {
      setMsg('danger', e.message);
    } finally {
      $('sweep-spinner').classList.add('d-none');
      $('sweep-generate-btn').disabled = false;
    }
  }

  // ── Ejecución en cola del barrido (Fase R4) ─────────────────────────────
  const sweepRunState = { polling: null, root: null, folders: null };

  const SWEEP_STATE_VARIANT = {
    pending: 'secondary', running: 'info', ok: 'success',
    failed: 'danger', timeout: 'warning', cancelled: 'secondary',
  };
  const SWEEP_STATE_ICON = {
    pending: 'bi-hourglass', running: 'bi-arrow-repeat', ok: 'bi-check-circle-fill',
    failed: 'bi-x-circle-fill', timeout: 'bi-clock-history', cancelled: 'bi-slash-circle',
  };

  function showSweepRunPanel(root, folders) {
    sweepRunState.root = root;
    sweepRunState.folders = folders || null;
    $('sweep-run-panel').classList.remove('d-none');
    $('sweep-run-root').textContent = root;
    $('btn-sweep-run-start').disabled = false;
    $('btn-sweep-run-cancel').disabled = true;
    $('sweep-run-badge').className = 'badge bg-secondary ms-auto';
    $('sweep-run-badge').textContent = '';
    $('sweep-run-tbody').innerHTML = '';
    $('sweep-run-progress').textContent = '';
    $('sweep-run-log').textContent = '';
    $('btn-sweep-run-open-analyzer').classList.add('d-none');
  }

  function sweepFolderOf(workdir, root) {
    if (root && workdir.startsWith(root)) {
      return workdir.slice(root.length).replace(/^[\\/]/, '');
    }
    return workdir;
  }

  // Etiquetas i18n de los pasos del pipeline D7 (barrido espectral), en el
  // mismo orden que 'pipeline_steps' de /api/run/status (ver app.py).
  const SWEEP_STEP_I18N = {
    collaps: 'sweep.run_step_collaps', copy: 'sweep.run_step_copy',
    acab: 'sweep.run_step_acab', check_flux: 'sweep.run_step_check_flux',
  };

  function sweepStepLabel(j, pipelineSteps) {
    if (!pipelineSteps || j.step_index == null) return '';
    const key = pipelineSteps[j.step_index];
    const i18nKey = key && SWEEP_STEP_I18N[key];
    return i18nKey ? t(i18nKey) : '';
  }

  function renderSweepBatchRows(jobs, root, pipelineSteps) {
    const tb = $('sweep-run-tbody');
    tb.innerHTML = '';
    jobs.forEach(j => {
      const folder = sweepFolderOf(j.workdir, root);
      const dur = j.duracion_s != null ? `${j.duracion_s.toFixed(1)} s` : '—';
      const variant = SWEEP_STATE_VARIANT[j.estado] || 'secondary';
      const icon = SWEEP_STATE_ICON[j.estado] || 'bi-question-circle';
      const step = sweepStepLabel(j, pipelineSteps);
      const tr = document.createElement('tr');
      tr.innerHTML =
        `<td class="font-monospace small">${folder}</td>`
        + `<td><span class="badge bg-${variant}"><i class="bi ${icon} me-1"></i>`
        + `${t('sweep.run_state_' + j.estado)}</span></td>`
        + `<td class="small">${step}</td>`
        + `<td class="small">${dur}</td>`;
      tb.appendChild(tr);
    });
  }

  function stopSweepBatchPolling() {
    if (sweepRunState.polling) { clearInterval(sweepRunState.polling); sweepRunState.polling = null; }
  }
  function startSweepBatchPolling() {
    stopSweepBatchPolling();
    sweepRunState.polling = setInterval(pollSweepBatchStatus, 1000);
    pollSweepBatchStatus();
  }

  async function pollSweepBatchStatus() {
    let json;
    try {
      const res = await fetch('/api/run/status');
      json = await res.json();
    } catch (_) { return; }
    const s = json.status || {};
    if (s.mode !== 'batch') return;

    const root = s.root || sweepRunState.root || '';
    $('sweep-run-log').textContent = s.log_tail || '';
    const jobs = s.jobs || [];
    renderSweepBatchRows(jobs, root, s.pipeline_steps || null);

    const total  = jobs.length;
    const ok     = jobs.filter(j => j.estado === 'ok').length;
    const fallos = jobs.filter(j => j.estado === 'failed' || j.estado === 'timeout').length;
    const pend   = jobs.filter(j => j.estado === 'pending' || j.estado === 'running').length;
    $('sweep-run-progress').textContent = t('sweep.run_progress')
      .replace('{k}', total - pend).replace('{n}', total)
      .replace('{ok}', ok).replace('{fail}', fallos);

    if (s.running) {
      $('sweep-run-badge').className = 'badge bg-info ms-auto';
      $('sweep-run-badge').textContent = t('run.badge_running');
      return;
    }

    stopSweepBatchPolling();
    $('btn-sweep-run-start').disabled = false;
    $('btn-sweep-run-cancel').disabled = true;

    const cancelled = jobs.some(j => j.estado === 'cancelled');
    if (cancelled) {
      $('sweep-run-badge').className = 'badge bg-secondary ms-auto';
      $('sweep-run-badge').textContent = t('run.badge_cancelled');
    } else if (fallos > 0) {
      $('sweep-run-badge').className = 'badge bg-warning ms-auto';
      $('sweep-run-badge').textContent = t('sweep.run_badge_partial').replace('{fail}', fallos);
    } else if (total > 0) {
      $('sweep-run-badge').className = 'badge bg-success ms-auto';
      $('sweep-run-badge').textContent = t('run.badge_ok');
    }

    if (root) {
      $('btn-sweep-run-open-analyzer').href =
        `http://127.0.0.1:5001/?folder=${encodeURIComponent(root)}`;
      $('btn-sweep-run-open-analyzer').classList.remove('d-none');
    }
  }

  async function startSweepBatchRun(root, folders, overwrite) {
    $('btn-sweep-run-start').disabled = true;
    try {
      const body = { root, overwrite: !!overwrite };
      if (folders) body.folders = folders;
      const r = await fetch('/api/run/batch', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const json = await r.json();

      if (r.status === 422 && json.needs_overwrite) {
        if (window.confirm(json.error)) { return startSweepBatchRun(root, folders, true); }
        $('btn-sweep-run-start').disabled = false;
        return;
      }
      if (!json.ok) {
        showToast(json.error || 'error', 'danger');
        $('btn-sweep-run-start').disabled = false;
        return;
      }

      showSweepRunPanel(root, folders);
      $('btn-sweep-run-start').disabled = true;
      $('btn-sweep-run-cancel').disabled = false;
      startSweepBatchPolling();
    } catch (e) {
      showToast(String(e), 'danger');
      $('btn-sweep-run-start').disabled = false;
    }
  }

  async function resyncSweepBatchState() {
    try {
      const res = await fetch('/api/run/status');
      const json = await res.json();
      const s = json.status || {};
      if (s.mode !== 'batch') return;
      showSweepRunPanel(s.root || '', null);
      if (s.running) {
        $('btn-sweep-run-start').disabled = true;
        $('btn-sweep-run-cancel').disabled = false;
      }
      startSweepBatchPolling();
    } catch (_) { /* servidor no disponible todavía: ignorar */ }
  }

  // ── Cargar/consultar un barrido ya generado (U6) ─────────────────────────
  // Unifica el flujo de carga: cargar SIEMPRE muestra el contenido del
  // barrido (solo lectura, vía /api/sweep/manifest); "Ejecutar" es una
  // acción sobre lo ya cargado, reutilizando startSweepBatchRun/el panel de
  // ejecución de la Fase R4 -- no hay un segundo camino de carga.
  const loadedSweepState = { root: null, folders: null };

  function setLoadMsg(kind, text) {
    const el = $('sweep-load-msg');
    if (!el) return;
    el.className = `alert alert-${kind} py-2 small`;
    el.textContent = text;
    el.classList.remove('d-none');
  }
  function clearLoadMsg() { const el = $('sweep-load-msg'); if (el) el.classList.add('d-none'); }

  function hideLoadedSweepView() {
    $('sweep-loaded-view')?.classList.add('d-none');
    loadedSweepState.root = null;
    loadedSweepState.folders = null;
  }

  async function loadSweepManifest() {
    clearLoadMsg();
    hideLoadedSweepView();
    const root = getVal('sweep-load-root').trim();
    if (!root) { setLoadMsg('danger', t('sweep.load_no_root')); return; }
    localStorage.setItem(LS_KEYS.loadRoot, root);

    let res;
    try {
      const r = await fetch('/api/sweep/manifest?root=' + encodeURIComponent(root));
      res = await r.json();
      if (!r.ok || !res.ok) throw new Error(res.error || 'error');
    } catch (e) {
      setLoadMsg('danger', e.message);
      return;
    }
    renderLoadedSweepView(res);
  }

  function renderLoadedSweepView(view) {
    loadedSweepState.root = view.root;
    loadedSweepState.folders = view.simulations.map(s => s.folder);

    $('sweep-loaded-type').textContent = view.sweep_type
      ? t('sweep.type_' + view.sweep_type) : '—';
    $('sweep-loaded-desc').textContent = view.description || '';

    const fixedEl = $('sweep-loaded-fixed');
    const fixedEntries = Object.entries(view.fixed_params || {});
    fixedEl.innerHTML = fixedEntries.length
      ? fixedEntries.map(([k, v]) => `<li>${k}: ${v}</li>`).join('')
      : `<li class="text-muted">${t('sweep.loaded_fixed_empty')}</li>`;

    const excludedEl = $('sweep-loaded-excluded');
    const excluded = view.excluded_base_files || [];
    excludedEl.innerHTML = excluded.length
      ? excluded.map(f => `<li>${f}</li>`).join('')
      : `<li class="text-muted">${t('sweep.loaded_excluded_empty')}</li>`;

    $('sweep-loaded-not-run').classList.toggle('d-none', !!view.has_batch_results);
    const summaryEl = $('sweep-loaded-batch-summary');
    if (view.has_batch_results && view.batch_summary) {
      const s = view.batch_summary;
      summaryEl.textContent = t('sweep.loaded_batch_summary')
        .replace('{ok}', s.ok).replace('{fail}', s.fallos).replace('{total}', s.total);
    } else {
      summaryEl.textContent = '';
    }

    const tb = $('sweep-loaded-tbody');
    tb.innerHTML = view.simulations.map(sim => {
      const value = sim.value_label != null ? sim.value_label : sim.folder;
      const outBadge = sim.fort6_exists
        ? `<span class="badge bg-success">${t('sweep.loaded_output_yes')}</span>`
        : `<span class="badge bg-secondary">${t('sweep.loaded_output_no')}</span>`;
      let stateBadge = `<span class="text-muted small">${t('sweep.loaded_not_run_badge')}</span>`;
      if (sim.estado) {
        const variant = SWEEP_STATE_VARIANT[sim.estado] || 'secondary';
        const icon = SWEEP_STATE_ICON[sim.estado] || 'bi-question-circle';
        stateBadge = `<span class="badge bg-${variant}"><i class="bi ${icon} me-1"></i>`
          + `${t('sweep.run_state_' + sim.estado)}</span>`;
      }
      return `
        <tr>
          <td class="font-monospace small">${sim.folder}</td>
          <td class="font-monospace small">${value}</td>
          <td class="text-center">${outBadge}</td>
          <td>${stateBadge}</td>
        </tr>`;
    }).join('');

    $('sweep-loaded-view').classList.remove('d-none');
  }

  // ── Persistencia localStorage ────────────────────────────────────────────
  function loadPersisted() {
    const set = (id, key) => { const v = localStorage.getItem(key); if (v) setVal(id, v); };
    set('sweep-root', LS_KEYS.root);
    set('sweep-base', LS_KEYS.base);
    set('sweep-prefix', LS_KEYS.prefix);
    set('sweep-load-root', LS_KEYS.loadRoot);
  }
  function persist() {
    localStorage.setItem(LS_KEYS.root, getVal('sweep-root'));
    localStorage.setItem(LS_KEYS.base, getVal('sweep-base'));
    localStorage.setItem(LS_KEYS.prefix, getVal('sweep-prefix'));
  }

  // ── Selector de carpeta nativo (evita teclear rutas a mano) ──────────────
  async function browseFolder(btn) {
    const targetId = btn.dataset.target;
    const input = $(targetId);
    if (!input) return;
    const icon = btn.querySelector('i');
    const prevIcon = icon ? icon.className : null;
    btn.disabled = true;
    if (icon) icon.className = 'bi bi-hourglass-split';
    try {
      const title = targetId === 'sweep-base' ? t('sweep.base_lbl')
        : targetId === 'sweep-load-root' ? t('sweep.load_h')
        : t('sweep.root_lbl');
      const res = await fetch('/api/browse-folder', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      const json = await res.json();
      if (json.folder) {
        input.value = json.folder;
        if (targetId === 'sweep-load-root') {
          localStorage.setItem(LS_KEYS.loadRoot, json.folder);
          hideLoadedSweepView();
        } else {
          persist();
          hidePreview();
        }
      } else if (!json.error) {
        showToast(t('sweep.browse_none'), 'secondary');
      } else {
        showToast(json.error, 'warning');
      }
    } catch (_) {
      showToast(t('sweep.browse_err'), 'warning');
    } finally {
      btn.disabled = false;
      if (icon && prevIcon) icon.className = prevIcon;
    }
  }

  // ── Init ─────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    const tabBtn = $('tab-sweep-btn');
    if (!tabBtn) return;   // pestaña no presente

    loadPersisted();

    tabBtn.addEventListener('shown.bs.tab', () => {
      refreshValidation();
      syncTypePanels();
    });

    document.querySelectorAll('input[name="sweep-type"]').forEach(r =>
      r.addEventListener('change', syncTypePanels));
    document.querySelectorAll('input[name="sweep-flux-mode"]').forEach(r =>
      r.addEventListener('change', () => { refreshFluxInfo(); hidePreview(); }));

    ['sweep-root', 'sweep-base', 'sweep-prefix'].forEach(id => {
      const el = $(id);
      if (el) el.addEventListener('change', () => { persist(); hidePreview(); });
    });
    ['sweep-flux-values', 'sweep-mass-values', 'sweep-mass-formula',
     'sweep-mass-vol', 'sweep-mass-zone', 'sweep-desc'].forEach(id => {
      const el = $(id);
      if (el) el.addEventListener('input', hidePreview);
    });

    $('sweep-time-add-sim')?.addEventListener('click', addTimeSimCard);
    $('sweep-preview-btn')?.addEventListener('click', doPreview);
    $('sweep-generate-btn')?.addEventListener('click', () => doGenerate(false));

    $('sweep-spectrum-add')?.addEventListener('click', () => $('sweep-spectrum-file').click());
    $('sweep-spectrum-file')?.addEventListener('change', async (e) => {
      const files = [...e.target.files];
      await handleSpectrumFiles(files);
      e.target.value = '';
    });
    $('sweep-spectrum-phiref')?.addEventListener('input', () => {
      _spectrumPhiRefEdited = true;
      hidePreview();
    });

    document.querySelectorAll('.sweep-browse-btn').forEach(btn =>
      btn.addEventListener('click', () => browseFolder(btn)));

    // ── Ejecución en cola del barrido (Fase R4) ───────────────────────────
    $('btn-sweep-run-start')?.addEventListener('click', () => {
      if (!sweepRunState.root) return;
      startSweepBatchRun(sweepRunState.root, sweepRunState.folders, false);
    });
    $('btn-sweep-run-cancel')?.addEventListener('click', async () => {
      try { await fetch('/api/run/cancel', { method: 'POST' }); } catch (_) { /* ignorar */ }
    });
    // ── Cargar/consultar un barrido ya generado (U6) ──────────────────────
    $('btn-sweep-load')?.addEventListener('click', loadSweepManifest);
    $('sweep-load-root')?.addEventListener('change', hideLoadedSweepView);
    $('btn-sweep-loaded-run')?.addEventListener('click', () => {
      if (!loadedSweepState.root) return;
      startSweepBatchRun(loadedSweepState.root, loadedSweepState.folders, false);
    });
    resyncSweepBatchState();
  });
})();
