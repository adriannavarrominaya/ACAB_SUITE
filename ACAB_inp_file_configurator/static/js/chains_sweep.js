/* chains_sweep.js — Pestaña "Análisis de cadenas" (F9 del BACKLOG, Fases 2-3).
 *
 * Carga el inventario isotópico inicial del fort.6 de una carpeta de
 * referencia, deja elegir isótopos + IFINAL/PCNT/NMAX, y delega en
 * /api/chains-analysis (preview/generación) y /api/chains-analysis/run
 * (orquestación: tape22 -> tape24 -> N x [ACAB monoisotópico + CHAINS]) del
 * servidor. Sigue el patrón de sweep.js (mismo IIFE, mismos globales de
 * app.js: t, showToast) pero con manifest y ejecución PROPIOS, no
 * reutiliza sweep_manifest.json / /api/run/batch.
 */
(function () {
  'use strict';

  const $ = id => document.getElementById(id);

  const LS_KEYS = {
    ref: 'acab-chainsan-ref', root: 'acab-chainsan-root',
    loadRoot: 'acab-chainsan-load-root',
  };

  let _inventory = [];      // [{name, c_i, zzaaas}] del último /inventory
  let _lastPreviewOk = false;

  const STATE_VARIANT = {
    pending: 'secondary', running: 'info', ok: 'success',
    failed: 'danger', timeout: 'warning', cancelled: 'secondary',
  };
  const STATE_ICON = {
    pending: 'bi-hourglass', running: 'bi-arrow-repeat', ok: 'bi-check-circle-fill',
    failed: 'bi-x-circle-fill', timeout: 'bi-clock-history', cancelled: 'bi-slash-circle',
  };

  function setMsg(id, kind, text) {
    const el = $(id);
    if (!el) return;
    el.className = `alert alert-${kind} py-2 small mt-3`;
    el.textContent = text;
    el.classList.remove('d-none');
  }
  function clearMsg(id) { const el = $(id); if (el) el.classList.add('d-none'); }

  function fmtCi(v) {
    return Number.isFinite(v) ? v.toExponential(4) : String(v);
  }

  // ── Inventario isotópico inicial ─────────────────────────────────────────
  async function loadInventory() {
    clearMsg('chainsan-inventory-msg');
    $('chainsan-inventory-wrap').classList.add('d-none');
    const ref = $('chainsan-ref').value.trim();
    if (!ref) { setMsg('chainsan-inventory-msg', 'danger', t('chainsan.err_no_ref')); return; }
    localStorage.setItem(LS_KEYS.ref, ref);

    let res;
    try {
      const r = await fetch('/api/chains-analysis/inventory?reference_folder=' + encodeURIComponent(ref));
      res = await r.json();
      if (!r.ok || !res.ok) throw new Error(res.error || 'error');
    } catch (e) {
      setMsg('chainsan-inventory-msg', 'danger', e.message);
      return;
    }
    _inventory = res.isotopos || [];
    if (_inventory.length === 0) {
      setMsg('chainsan-inventory-msg', 'warning', t('chainsan.no_isotopes'));
      return;
    }
    renderInventory();
    $('chainsan-inventory-wrap').classList.remove('d-none');
    hidePreview();
  }

  function renderInventory() {
    const tb = $('chainsan-inventory-tbody');
    tb.innerHTML = _inventory.map(iso => `
      <tr>
        <td class="text-center">
          <input type="checkbox" class="form-check-input chainsan-iso-check" data-name="${iso.name}">
        </td>
        <td class="font-monospace">${iso.name}</td>
        <td class="font-monospace small">${fmtCi(iso.c_i)}</td>
      </tr>`).join('');
    tb.querySelectorAll('.chainsan-iso-check').forEach(cb =>
      cb.addEventListener('change', () => { updateSelectedCount(); hidePreview(); }));
    updateSelectedCount();
  }

  function selectedIsotopes() {
    const names = new Set(
      [...document.querySelectorAll('.chainsan-iso-check:checked')].map(cb => cb.dataset.name));
    return _inventory.filter(iso => names.has(iso.name));
  }

  function updateSelectedCount() {
    const n = selectedIsotopes().length;
    const el = $('chainsan-selected-count');
    if (el) el.textContent = t('chainsan.selected_count').replace('{n}', n);
  }

  // ── Previsualizar / Generar ──────────────────────────────────────────────
  function hidePreview() {
    _lastPreviewOk = false;
    $('chainsan-preview').classList.add('d-none');
    $('btn-chainsan-generate').disabled = true;
  }

  function currentParams() {
    return {
      ifinal: $('chainsan-ifinal').value.trim(),
      pcnt: parseFloat($('chainsan-pcnt').value),
      nmax: parseInt($('chainsan-nmax').value, 10),
    };
  }

  async function doPreview() {
    clearMsg('chainsan-msg');
    hidePreview();
    const isotopes = selectedIsotopes();
    if (isotopes.length === 0) { setMsg('chainsan-msg', 'warning', t('chainsan.err_no_selection')); return; }
    const root = $('chainsan-root').value.trim();
    const ref = $('chainsan-ref').value.trim();
    if (!root) { setMsg('chainsan-msg', 'danger', t('chainsan.err_no_root')); return; }

    let res;
    try {
      const r = await fetch('/api/chains-analysis/preview', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ root, reference_folder: ref, isotopes }),
      });
      res = await r.json();
      if (!r.ok || !res.ok) throw new Error(res.error || 'error');
    } catch (e) {
      setMsg('chainsan-msg', 'danger', e.message);
      return;
    }

    const lines = [
      t('chainsan.preview_n').replace('{n}', res.n_isotopes),
      t('chainsan.preview_folders').replace('{n}', res.folders.length),
    ];
    if (!res.reference_exists) lines.push(t('chainsan.warn_no_ref'));
    if (!res.reference_has_inp5) lines.push(t('chainsan.warn_no_inp5'));
    if (res.collisions && res.collisions.length)
      lines.push(t('chainsan.warn_collisions').replace('{list}', res.collisions.join(', ')));
    if (res.over_limit) lines.push(t('chainsan.warn_over_limit'));

    const el = $('chainsan-preview');
    el.innerHTML = lines.map(l => `<div>${l}</div>`).join('');
    el.classList.remove('d-none');

    _lastPreviewOk = res.reference_exists && res.reference_has_inp5 && !res.over_limit;
    $('btn-chainsan-generate').disabled = !_lastPreviewOk;
  }

  async function doGenerate(overwrite) {
    clearMsg('chainsan-msg');
    if (!_lastPreviewOk) { setMsg('chainsan-msg', 'warning', t('chainsan.err_preview_first')); return; }
    const isotopes = selectedIsotopes();
    const { ifinal, pcnt, nmax } = currentParams();
    if (!ifinal) { setMsg('chainsan-msg', 'danger', t('chainsan.err_no_ifinal')); return; }
    if (!Number.isFinite(pcnt) || pcnt <= 0) { setMsg('chainsan-msg', 'danger', t('chainsan.err_bad_pcnt')); return; }
    if (!Number.isFinite(nmax) || nmax <= 0) { setMsg('chainsan-msg', 'danger', t('chainsan.err_bad_nmax')); return; }

    const payload = {
      root: $('chainsan-root').value.trim(),
      reference_folder: $('chainsan-ref').value.trim(),
      isotopes, ifinal, pcnt, nmax, overwrite: !!overwrite,
    };

    $('chainsan-spinner').classList.remove('d-none');
    $('btn-chainsan-generate').disabled = true;
    try {
      const r = await fetch('/api/chains-analysis', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const res = await r.json();
      if (r.status === 409) {
        if (window.confirm(t('sweep.confirm_overwrite') + '\n\n' + (res.error || ''))) {
          $('chainsan-spinner').classList.add('d-none');
          return doGenerate(true);
        }
        setMsg('chainsan-msg', 'warning', res.error || 'colisión');
        return;
      }
      if (!r.ok || !res.ok) throw new Error(res.error || 'error');
      setMsg('chainsan-msg', 'success',
        t('chainsan.done').replace('{n}', res.n_isotopes).replace('{root}', res.root));
      showToast(t('chainsan.done_toast').replace('{n}', res.n_isotopes), 'success');
      localStorage.setItem(LS_KEYS.root, res.root);
      showRunPanel(res.root);
    } catch (e) {
      setMsg('chainsan-msg', 'danger', e.message);
    } finally {
      $('chainsan-spinner').classList.add('d-none');
      $('btn-chainsan-generate').disabled = false;
    }
  }

  // ── Ejecución (Fase 3) ───────────────────────────────────────────────────
  const runState = { polling: null, root: null };

  function folderOf(workdir, root) {
    if (root && workdir.startsWith(root)) return workdir.slice(root.length).replace(/^[\\/]/, '');
    return workdir;
  }

  function stepLabel(job, pipelineSteps) {
    // step_type por sí solo no distingue el run de ACAB del run de CHAINS
    // (ambos son 'run') -- pipelineSteps (de /api/run/status, F9c) da la
    // etiqueta real por step_index: ['acab','copy','copy','chains'].
    if (job.step_index == null) return '';
    const kind = (pipelineSteps && pipelineSteps[job.step_index]) || job.step_type;
    if (kind === 'acab') return t('chainsan.step_acab');
    if (kind === 'chains') return t('chainsan.step_chains');
    if (kind === 'copy') return t('chainsan.step_copy');
    return kind || '';
  }

  function showRunPanel(root) {
    runState.root = root;
    $('chainsan-run-panel').classList.remove('d-none');
    $('chainsan-run-root').textContent = root;
    $('btn-chainsan-run-start').disabled = false;
    $('btn-chainsan-run-cancel').disabled = true;
    $('chainsan-run-badge').className = 'badge bg-secondary ms-auto';
    $('chainsan-run-badge').textContent = '';
    $('chainsan-run-tbody').innerHTML = '';
    $('chainsan-run-progress').textContent = '';
    $('chainsan-run-log').textContent = '';
    $('btn-chainsan-run-open-analyzer').classList.add('d-none');
  }

  // Último jobs[]/root pintados (F9c): permite al botón "ver run.log" de
  // cada fila resolver su job por índice sin serializar datos en el DOM.
  let _lastRunJobs = [];
  let _lastRunRoot = '';

  function renderRunRows(jobs, root, pipelineSteps) {
    _lastRunJobs = jobs;
    _lastRunRoot = root;
    const tb = $('chainsan-run-tbody');
    tb.innerHTML = jobs.map((j, idx) => {
      const folder = folderOf(j.workdir, root);
      const dur = j.duracion_s != null ? `${j.duracion_s.toFixed(1)} s` : '—';
      const variant = STATE_VARIANT[j.estado] || 'secondary';
      const icon = STATE_ICON[j.estado] || 'bi-question-circle';
      // Botón "ver run.log" (F9c, UX de fallo): solo tiene sentido con el
      // job ya terminado (steps[] completo) y en estado fallido/timeout --
      // el error FORTRAN existía en disco y antes la UI no lo enseñaba.
      const canShowDetail = (j.estado === 'failed' || j.estado === 'timeout')
        && Array.isArray(j.steps) && j.steps.length > 0;
      const detailBtn = canShowDetail
        ? `<button type="button" class="btn btn-sm btn-outline-secondary chainsan-viewlog-btn"
             data-job-idx="${idx}"><i class="bi bi-file-text me-1"></i>${t('chainsan.view_log_btn')}</button>`
        : '';
      return `<tr>
        <td class="font-monospace small">${folder}</td>
        <td><span class="badge bg-${variant}"><i class="bi ${icon} me-1"></i>${t('sweep.run_state_' + j.estado)}</span></td>
        <td class="small">${stepLabel(j, pipelineSteps)}</td>
        <td class="small">${dur}</td>
        <td class="small">${detailBtn}</td>
      </tr>`;
    }).join('');
    tb.querySelectorAll('.chainsan-viewlog-btn').forEach(btn => btn.addEventListener('click', () => {
      const job = _lastRunJobs[parseInt(btn.dataset.jobIdx, 10)];
      if (job) showStepFailureDetail(job, _lastRunRoot);
    }));
  }

  // Muestra en el panel de log el detalle del paso que falló (F9c): si es
  // un paso 'run' con cwd propio (puede ser una carpeta distinta del
  // workdir del job, p. ej. chains_<isótopo>/ dentro del job de
  // iso_<isótopo>/), pide su run.log a /api/run/log; si es un paso 'copy'
  // fallido, no hay run.log -- el motivo ya viene en el propio resultado.
  async function showStepFailureDetail(job, root) {
    const idx = job.step_index;
    const step = Array.isArray(job.steps) && idx != null ? job.steps[idx] : null;
    if (!step) { $('chainsan-run-log').textContent = ''; return; }
    const stepFolder = step.cwd ? folderOf(step.cwd, root) : folderOf(job.workdir, root);
    if (step.type === 'run' && step.cwd) {
      let logText = '';
      try {
        const r = await fetch('/api/run/log?workdir=' + encodeURIComponent(step.cwd));
        const json = await r.json();
        logText = (r.ok && json.ok) ? (json.log || '') : (json.error || '');
      } catch (e) { logText = String(e); }
      $('chainsan-run-log').textContent = `[${stepFolder}]\n` + (logText || t('chainsan.no_log'));
    } else {
      $('chainsan-run-log').textContent = `[${stepFolder}] ` + (step.error || t('chainsan.no_log'));
    }
  }

  function stopPolling() { if (runState.polling) { clearInterval(runState.polling); runState.polling = null; } }
  function startPolling() { stopPolling(); runState.polling = setInterval(pollStatus, 1000); pollStatus(); }

  async function pollStatus() {
    let json;
    try {
      const res = await fetch('/api/run/status');
      json = await res.json();
    } catch (_) { return; }
    const s = json.status || {};
    if (s.mode !== 'batch') return;

    const root = s.root || runState.root || '';
    $('chainsan-run-log').textContent = s.log_tail || '';
    const jobs = s.jobs || [];
    renderRunRows(jobs, root, s.pipeline_steps);

    const total = jobs.length;
    const ok = jobs.filter(j => j.estado === 'ok').length;
    const fallos = jobs.filter(j => j.estado === 'failed' || j.estado === 'timeout').length;
    const pend = jobs.filter(j => j.estado === 'pending' || j.estado === 'running').length;
    $('chainsan-run-progress').textContent = t('sweep.run_progress')
      .replace('{k}', total - pend).replace('{n}', total)
      .replace('{ok}', ok).replace('{fail}', fallos);

    if (s.running) {
      $('chainsan-run-badge').className = 'badge bg-info ms-auto';
      $('chainsan-run-badge').textContent = t('run.badge_running');
      return;
    }

    stopPolling();
    $('btn-chainsan-run-start').disabled = false;
    $('btn-chainsan-run-cancel').disabled = true;

    const cancelled = jobs.some(j => j.estado === 'cancelled');
    if (cancelled) {
      $('chainsan-run-badge').className = 'badge bg-secondary ms-auto';
      $('chainsan-run-badge').textContent = t('run.badge_cancelled');
    } else if (fallos > 0) {
      $('chainsan-run-badge').className = 'badge bg-warning ms-auto';
      $('chainsan-run-badge').textContent = t('sweep.run_badge_partial').replace('{fail}', fallos);
    } else if (total > 0) {
      $('chainsan-run-badge').className = 'badge bg-success ms-auto';
      $('chainsan-run-badge').textContent = t('run.badge_ok');
    }

    if (root) {
      $('btn-chainsan-run-open-analyzer').href =
        `http://127.0.0.1:5001/?folder=${encodeURIComponent(root)}`;
      $('btn-chainsan-run-open-analyzer').classList.remove('d-none');
    }
  }

  async function startRun(root, overwrite) {
    $('btn-chainsan-run-start').disabled = true;
    try {
      const r = await fetch('/api/chains-analysis/run', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ root, overwrite: !!overwrite }),
      });
      const json = await r.json();

      if (r.status === 422 && json.needs_overwrite) {
        if (window.confirm(json.error)) return startRun(root, true);
        $('btn-chainsan-run-start').disabled = false;
        return;
      }
      if (!json.ok) {
        showToast(json.error || 'error', 'danger');
        $('btn-chainsan-run-start').disabled = false;
        return;
      }
      showRunPanel(root);
      $('btn-chainsan-run-start').disabled = true;
      $('btn-chainsan-run-cancel').disabled = false;
      startPolling();
    } catch (e) {
      showToast(String(e), 'danger');
      $('btn-chainsan-run-start').disabled = false;
    }
  }

  async function resyncRunState() {
    try {
      const res = await fetch('/api/run/status');
      const json = await res.json();
      const s = json.status || {};
      if (s.mode !== 'batch' || !s.root) return;
      // Heurística: solo re-engancha el panel si la última ejecución la
      // lanzó esta pestaña (chains_manifest.json presente en la raíz).
      const check = await fetch('/api/chains-analysis/manifest?root=' + encodeURIComponent(s.root));
      if (!check.ok) return;
      showRunPanel(s.root);
      if (s.running) {
        $('btn-chainsan-run-start').disabled = true;
        $('btn-chainsan-run-cancel').disabled = false;
      }
      startPolling();
    } catch (_) { /* servidor no disponible todavía: ignorar */ }
  }

  // ── Cargar un análisis ya generado ───────────────────────────────────────
  const loadedState = { root: null };

  function setLoadMsg(kind, text) {
    const el = $('chainsan-load-msg');
    el.className = `alert alert-${kind} py-2 small`;
    el.textContent = text;
    el.classList.remove('d-none');
  }
  function clearLoadMsg() { $('chainsan-load-msg').classList.add('d-none'); }
  function hideLoadedView() { $('chainsan-loaded-view').classList.add('d-none'); loadedState.root = null; }

  async function loadManifest() {
    clearLoadMsg();
    hideLoadedView();
    const root = $('chainsan-load-root').value.trim();
    if (!root) { setLoadMsg('danger', t('chainsan.load_no_root')); return; }
    localStorage.setItem(LS_KEYS.loadRoot, root);

    let res;
    try {
      const r = await fetch('/api/chains-analysis/manifest?root=' + encodeURIComponent(root));
      res = await r.json();
      if (!r.ok || !res.ok) throw new Error(res.error || 'error');
    } catch (e) {
      setLoadMsg('danger', e.message);
      return;
    }
    renderLoadedView(root, res.manifest, res.batch_results);
  }

  function renderLoadedView(root, manifest, batchResults) {
    loadedState.root = root;
    $('chainsan-loaded-ifinal').textContent = manifest.ifinal;
    $('chainsan-loaded-pcnt-nmax').textContent = `${manifest.pcnt} / ${manifest.nmax}`;

    const jobsByWorkdir = {};
    (batchResults && batchResults.jobs || []).forEach(j => { jobsByWorkdir[j.workdir] = j; });

    const tb = $('chainsan-loaded-tbody');
    tb.innerHTML = (manifest.isotopes || []).map(iso => {
      const job = jobsByWorkdir[`${root}\\${iso.iso_folder}`] || jobsByWorkdir[`${root}/${iso.iso_folder}`];
      let badge = `<span class="text-muted small">${t('sweep.loaded_not_run_badge')}</span>`;
      if (job) {
        const variant = STATE_VARIANT[job.estado] || 'secondary';
        const icon = STATE_ICON[job.estado] || 'bi-question-circle';
        badge = `<span class="badge bg-${variant}"><i class="bi ${icon} me-1"></i>${t('sweep.run_state_' + job.estado)}</span>`;
      }
      return `<tr>
        <td class="font-monospace small">${iso.name}</td>
        <td class="font-monospace small">${fmtCi(iso.c_i)}</td>
        <td>${badge}</td>
      </tr>`;
    }).join('');

    $('chainsan-loaded-view').classList.remove('d-none');
  }

  // ── Selector de carpeta nativo ───────────────────────────────────────────
  async function browseFolder(btn) {
    const targetId = btn.dataset.target;
    const input = $(targetId);
    if (!input) return;
    const icon = btn.querySelector('i');
    const prevIcon = icon ? icon.className : null;
    btn.disabled = true;
    if (icon) icon.className = 'bi bi-hourglass-split';
    try {
      const res = await fetch('/api/browse-folder', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: t('chainsan.browse_title') }),
      });
      const json = await res.json();
      if (json.folder) {
        input.value = json.folder;
        if (targetId === 'chainsan-load-root') {
          localStorage.setItem(LS_KEYS.loadRoot, json.folder);
          hideLoadedView();
        } else {
          if (targetId === 'chainsan-ref') localStorage.setItem(LS_KEYS.ref, json.folder);
          if (targetId === 'chainsan-root') localStorage.setItem(LS_KEYS.root, json.folder);
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

  function loadPersisted() {
    const set = (id, key) => { const v = localStorage.getItem(key); if (v) $(id).value = v; };
    set('chainsan-ref', LS_KEYS.ref);
    set('chainsan-root', LS_KEYS.root);
    set('chainsan-load-root', LS_KEYS.loadRoot);
  }

  // ── Init ─────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    const tabBtn = $('tab-chains-btn');
    if (!tabBtn) return;

    loadPersisted();

    $('btn-chainsan-inventory')?.addEventListener('click', loadInventory);
    $('btn-chainsan-select-all')?.addEventListener('click', () => {
      document.querySelectorAll('.chainsan-iso-check').forEach(cb => { cb.checked = true; });
      updateSelectedCount(); hidePreview();
    });
    $('btn-chainsan-select-none')?.addEventListener('click', () => {
      document.querySelectorAll('.chainsan-iso-check').forEach(cb => { cb.checked = false; });
      updateSelectedCount(); hidePreview();
    });
    ['chainsan-ifinal', 'chainsan-pcnt', 'chainsan-nmax', 'chainsan-root'].forEach(id => {
      $(id)?.addEventListener('input', hidePreview);
    });

    $('btn-chainsan-preview')?.addEventListener('click', doPreview);
    $('btn-chainsan-generate')?.addEventListener('click', () => doGenerate(false));

    document.querySelectorAll('.chainsan-browse-btn').forEach(btn =>
      btn.addEventListener('click', () => browseFolder(btn)));

    $('btn-chainsan-run-start')?.addEventListener('click', () => {
      if (!runState.root) return;
      startRun(runState.root, false);
    });
    $('btn-chainsan-run-cancel')?.addEventListener('click', async () => {
      try { await fetch('/api/run/cancel', { method: 'POST' }); } catch (_) { /* ignorar */ }
    });

    $('btn-chainsan-load')?.addEventListener('click', loadManifest);
    $('chainsan-load-root')?.addEventListener('change', hideLoadedView);
    $('btn-chainsan-loaded-run')?.addEventListener('click', () => {
      if (!loadedState.root) return;
      startRun(loadedState.root, false);
    });

    resyncRunState();
  });
})();
