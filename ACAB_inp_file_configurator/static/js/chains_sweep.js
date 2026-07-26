/* chains_sweep.js — Pestaña "Análisis de cadenas" (F9 del BACKLOG, Fase 2:
 * configuración y generación).
 *
 * Carga el inventario isotópico inicial del fort.6 de una carpeta de
 * referencia, deja elegir isótopos + IFINAL/PCNT/NMAX, y delega en
 * /api/chains-analysis (preview/generación) del servidor. Sigue el patrón
 * de sweep.js (mismo IIFE, mismos globales de app.js: t, showToast) pero
 * con manifest PROPIO, no reutiliza sweep_manifest.json.
 */
(function () {
  'use strict';

  const $ = id => document.getElementById(id);

  const LS_KEYS = {
    ref: 'acab-chainsan-ref', root: 'acab-chainsan-root',
  };

  let _inventory = [];      // [{name, c_i, zzaaas}] del último /inventory
  let _lastPreviewOk = false;

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
    } catch (e) {
      setMsg('chainsan-msg', 'danger', e.message);
    } finally {
      $('chainsan-spinner').classList.add('d-none');
      $('btn-chainsan-generate').disabled = false;
    }
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
        if (targetId === 'chainsan-ref') localStorage.setItem(LS_KEYS.ref, json.folder);
        if (targetId === 'chainsan-root') localStorage.setItem(LS_KEYS.root, json.folder);
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

  function loadPersisted() {
    const set = (id, key) => { const v = localStorage.getItem(key); if (v) $(id).value = v; };
    set('chainsan-ref', LS_KEYS.ref);
    set('chainsan-root', LS_KEYS.root);
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
  });
})();
