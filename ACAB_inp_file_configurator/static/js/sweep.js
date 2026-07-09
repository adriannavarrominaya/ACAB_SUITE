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

  const LS_KEYS = { root: 'acab-sweep-root', base: 'acab-sweep-base', prefix: 'acab-sweep-prefix' };
  let _lastPatches = [];   // [{params, patch, suffix}] tras "Previsualizar"

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
    ['flux', 'mass', 'time'].forEach(k =>
      $(`sweep-panel-${k}`).classList.toggle('d-none', k !== type));
    if (type === 'flux') refreshFluxInfo();
    if (type === 'mass') refreshMassPanel();
    if (type === 'time') ensureTimeRow();
    hidePreview();
  }

  function refreshFluxInfo() {
    if (!appState.data) appState.data = {};
    collectAll(appState.data);
    const phi = fluxBaseTotal(appState.data.block3, appState.data.block9);
    const el = $('sweep-flux-phibase');
    if (el) el.textContent = Number.isFinite(phi) && phi > 0 ? phi.toExponential(4) : '—';
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

  function ensureTimeRow() {
    const tb = $('sweep-time-tbody');
    if (tb && tb.children.length === 0) addTimeRow();
  }

  function addTimeRow() {
    const tb = $('sweep-time-tbody');
    const idx = tb.children.length + 1;
    const tr = document.createElement('tr');
    tr.innerHTML =
      `<td class="text-center text-muted small align-middle sweep-time-num">${idx}</td>`
      + `<td><input type="number" step="any" min="0" class="form-control form-control-sm sweep-t-irr"></td>`
      + `<td><input type="number" min="1" max="10" step="1" class="form-control form-control-sm sweep-p-irr"></td>`
      + `<td><input type="number" step="any" min="0" class="form-control form-control-sm sweep-t-cool"></td>`
      + `<td><input type="number" min="1" max="10" step="1" class="form-control form-control-sm sweep-p-cool"></td>`
      + `<td class="text-center align-middle">`
      + `<button class="btn btn-sm btn-outline-danger p-1 lh-1 sweep-time-del"><i class="bi bi-x-lg"></i></button></td>`;
    tb.appendChild(tr);
    tr.querySelector('.sweep-time-del').addEventListener('click', () => {
      tr.remove();
      [...tb.querySelectorAll('.sweep-time-num')].forEach((td, i) => { td.textContent = i + 1; });
    });
  }

  // Reconstruye las fases del base (para conservar cuando una fila deja el
  // campo vacío) a partir de blocks78.times, igual que el generador manual.
  function baseFases() {
    const times = appState.data?.blocks78?.times || [];
    const irr  = times.filter(([, k]) => k === 1).map(([v]) => v);
    const cool = times.filter(([, k]) => k === 0).map(([v]) => v);
    const out = { baseIrr: [], baseCool: [] };
    if (irr.length)  out.baseIrr  = [{ t_fin: irr[irr.length - 1],   pasos: Math.min(irr.length, 10) }];
    if (cool.length) out.baseCool = [{ t_fin: cool[cool.length - 1], pasos: Math.min(cool.length, 10) }];
    return out;
  }

  // ── Construcción de patches (cliente) ────────────────────────────────────
  function buildPatches() {
    const type = currentType();
    if (!appState.data) appState.data = {};
    collectAll(appState.data);

    if (type === 'flux') {
      const mode = document.querySelector('input[name="sweep-flux-mode"]:checked')?.value || 'xnorm';
      const vals = parseSweepValues(getVal('sweep-flux-values'));
      const phi  = fluxBaseTotal(appState.data.block3, appState.data.block9);
      const list = buildFluxPatches(vals, mode, phi);
      return list.map(p => ({ ...p, suffix: proposeSuffix('flux', p.patch.block9.XNORM) }));
    }

    if (type === 'mass') {
      if (getInt('b1-INPT') === 2) throw new Error(t('sweep.mass_inpt2'));
      if (!window._atomicData || !_atomicData.elements)
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

    // temporal
    const rows = [...$('sweep-time-tbody').querySelectorAll('tr')].map(tr => ({
      t_irr_fin:  parseFloat(tr.querySelector('.sweep-t-irr').value),
      pasos_irr:  parseInt(tr.querySelector('.sweep-p-irr').value, 10),
      t_cool_fin: parseFloat(tr.querySelector('.sweep-t-cool').value),
      pasos_cool: parseInt(tr.querySelector('.sweep-p-cool').value, 10),
    }));
    if (rows.length === 0) throw new Error(t('sweep.err_no_rows'));
    const iunit = getInt('b78-iunit') || 3;
    const iout  = $('b78-iout')?.checked ? 1 : 0;
    const iplot = $('b78-iplot')?.checked ? 1 : 0;
    const list = buildTimePatches(rows, { iunit, iout, iplot, t, ...baseFases() });
    return list.map(p => ({
      ...p,
      suffix: proposeSuffix('time',
        Number.isFinite(p.params.t_irr_fin) ? p.params.t_irr_fin : p.params.t_cool_fin),
    }));
  }

  function paramsLabel(params) {
    return Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== null && !Number.isNaN(v))
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
    const sims = _lastPatches.map(p => ({ suffix: p.suffix, params: p.params, patch: p.patch }));

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

  function renderSweepBatchRows(jobs, root) {
    const tb = $('sweep-run-tbody');
    tb.innerHTML = '';
    jobs.forEach(j => {
      const folder = sweepFolderOf(j.workdir, root);
      const dur = j.duracion_s != null ? `${j.duracion_s.toFixed(1)} s` : '—';
      const variant = SWEEP_STATE_VARIANT[j.estado] || 'secondary';
      const icon = SWEEP_STATE_ICON[j.estado] || 'bi-question-circle';
      const tr = document.createElement('tr');
      tr.innerHTML =
        `<td class="font-monospace small">${folder}</td>`
        + `<td><span class="badge bg-${variant}"><i class="bi ${icon} me-1"></i>`
        + `${t('sweep.run_state_' + j.estado)}</span></td>`
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
    renderSweepBatchRows(jobs, root);

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

  // ── Persistencia localStorage ────────────────────────────────────────────
  function loadPersisted() {
    const set = (id, key) => { const v = localStorage.getItem(key); if (v) setVal(id, v); };
    set('sweep-root', LS_KEYS.root);
    set('sweep-base', LS_KEYS.base);
    set('sweep-prefix', LS_KEYS.prefix);
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
      const title = targetId === 'sweep-base'
        ? t('sweep.base_lbl') : t('sweep.root_lbl');
      const res = await fetch('/api/browse-folder', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      const json = await res.json();
      if (json.folder) {
        input.value = json.folder;
        persist();
        hidePreview();
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
      r.addEventListener('change', hidePreview));

    ['sweep-root', 'sweep-base', 'sweep-prefix'].forEach(id => {
      const el = $(id);
      if (el) el.addEventListener('change', () => { persist(); hidePreview(); });
    });
    ['sweep-flux-values', 'sweep-mass-values', 'sweep-mass-formula',
     'sweep-mass-vol', 'sweep-mass-zone', 'sweep-desc'].forEach(id => {
      const el = $(id);
      if (el) el.addEventListener('input', hidePreview);
    });

    $('sweep-time-add')?.addEventListener('click', () => { addTimeRow(); hidePreview(); });
    $('sweep-preview-btn')?.addEventListener('click', doPreview);
    $('sweep-generate-btn')?.addEventListener('click', () => doGenerate(false));

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
    $('btn-sweep-run-existing')?.addEventListener('click', () => {
      const root = getVal('sweep-run-existing-root').trim();
      if (!root) { showToast(t('sweep.run_no_root'), 'danger'); return; }
      startSweepBatchRun(root, null, false);
    });
    resyncSweepBatchState();
  });
})();
