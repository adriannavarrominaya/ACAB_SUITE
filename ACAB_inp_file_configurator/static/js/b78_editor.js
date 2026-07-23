/* b78_editor.js — Componente reutilizable del editor de tramos del
 * historial temporal (Bloques #7/#8/#11): IUNIT/IOUT/IPLOT + fases de
 * irradiación/enfriamiento (tiempo FINAL ACUMULADO por tramo, pasos 1-10,
 * estrictamente crecientes). Usado por el generador manual (pestaña
 * Blocks #7/#8, prefijo 'b78', sobre su markup estático existente en
 * index.html) y por cada tarjeta del barrido temporal (U7 del BACKLOG, un
 * prefijo único por simulación, markup generado por b78EditorBodyHtml) —
 * MISMO código para ambos, cero divergencia de validaciones.
 *
 * Regla dura: este fichero NUNCA referencia `appState`. Los efectos
 * laterales (marcar el formulario como "dirty", refrescar la
 * previsualización de un barrido, etc.) son responsabilidad exclusiva del
 * `onChange` que pasa cada llamador.
 *
 * Todas las funciones toman `prefix` como primer argumento: los ids de los
 * controles siguen el patrón `${prefix}-iunit`, `${prefix}-irr-tbody`,
 * `btn-${prefix}-add-irr`, etc. — el mismo patrón que ya usaba la pestaña
 * manual con prefijo fijo 'b78', así que su markup estático no necesita
 * cambios. Las clases de fila (`b78-row-num`/`b78-t-fin`/`b78-pasos`) no
 * llevan prefijo: la lectura siempre se hace vía el tbody (que sí es único
 * por prefijo), así que no hay colisión entre instancias.
 */
'use strict';

/** HTML del cuerpo del editor (IUNIT/IOUT/IPLOT + ambas tablas + botones
 * "añadir tramo") para una instancia identificada por `prefix`. NO se usa
 * para la pestaña manual (mantiene su markup estático); solo para montar
 * tarjetas del barrido temporal dinámicamente. t() inline (no data-i18n),
 * igual que el resto del contenido dinámico de sweep.js. */
function b78EditorBodyHtml(prefix) {
  return `
    <div class="row g-3 mb-3">
      <div class="col-md-5">
        <label class="form-label" for="${prefix}-iunit">${t('b78.iunit_lbl')}</label>
        <select id="${prefix}-iunit" class="form-select form-select-sm">
          <option value="1">${t('b78.iunit_1')}</option>
          <option value="2">${t('b78.iunit_2')}</option>
          <option value="3" selected>${t('b78.iunit_3')}</option>
          <option value="4">${t('b78.iunit_4')}</option>
          <option value="5">${t('b78.iunit_5')}</option>
          <option value="7">${t('b78.iunit_7')}</option>
          <option value="8">${t('b78.iunit_8')}</option>
          <option value="9">${t('b78.iunit_9')}</option>
        </select>
        <div class="form-text">${t('b78.iunit_hint')}</div>
      </div>
      <div class="col-md-5">
        <label class="form-label">${t('b78.out_lbl')}</label>
        <div class="d-flex gap-3 mt-1">
          <div class="form-check">
            <input class="form-check-input" type="checkbox" id="${prefix}-iout" checked>
            <label class="form-check-label small" for="${prefix}-iout">${t('b78.iout_lbl')}</label>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="checkbox" id="${prefix}-iplot">
            <label class="form-check-label small" for="${prefix}-iplot">${t('b78.iplot_lbl')}</label>
          </div>
        </div>
      </div>
    </div>

    <h6 class="group-heading">
      <i class="bi bi-radioactive me-1 text-danger"></i>${t('b78.grp_irr')}
    </h6>
    <div class="alert alert-info py-2 small mb-2">
      <i class="bi bi-info-circle me-1"></i>${t('b78.irr_hint_html')}
    </div>
    <table class="table table-sm table-bordered zone-input-table mb-0">
      <thead class="table-danger">
        <tr>
          <th style="width:3rem">#</th>
          <th>${t('b78.irr_th_time')} <span class="fw-normal text-muted">${t('b78.irr_th_iunit')}</span></th>
          <th style="width:10rem">${t('b78.irr_th_steps')}</th>
          <th style="width:3rem"></th>
        </tr>
      </thead>
      <tbody id="${prefix}-irr-tbody"></tbody>
    </table>
    <button type="button" id="btn-${prefix}-add-irr" class="btn btn-sm btn-outline-danger mt-2 mb-4">
      <i class="bi bi-plus-lg me-1"></i>${t('b78.btn_add_irr')}
    </button>

    <h6 class="group-heading">
      <i class="bi bi-snow me-1 text-primary"></i>${t('b78.grp_cool')}
    </h6>
    <div class="alert alert-secondary py-2 small mb-2">
      <i class="bi bi-info-circle me-1"></i>${t('b78.cool_hint_html')}
    </div>
    <table class="table table-sm table-bordered zone-input-table mb-0">
      <thead class="table-primary">
        <tr>
          <th style="width:3rem">#</th>
          <th>${t('b78.irr_th_time')} <span class="fw-normal text-muted">${t('b78.cool_th_note')}</span></th>
          <th style="width:10rem">${t('b78.irr_th_steps')}</th>
          <th style="width:3rem"></th>
        </tr>
      </thead>
      <tbody id="${prefix}-cool-tbody"></tbody>
    </table>
    <button type="button" id="btn-${prefix}-add-cool" class="btn btn-sm btn-outline-primary mt-2 mb-2">
      <i class="bi bi-plus-lg me-1"></i>${t('b78.btn_add_cool')}
    </button>`;
}

/** Añade un <tr> a `#${prefix}-${phase}-tbody`. `onChange` (si se pasa) se
 * dispara en el `change` de sus inputs y al borrar la fila. */
function addB78EditorRow(prefix, phase, t_fin = '', pasos = '', onChange) {
  const tbody = document.getElementById(`${prefix}-${phase}-tbody`);
  if (!tbody) return;
  const idx = tbody.querySelectorAll('tr').length + 1;
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td class="text-center text-muted small align-middle b78-row-num">${idx}</td>
    <td><input type="number" class="form-control form-control-sm b78-t-fin"
               step="any" min="0" value="${t_fin}" placeholder="${t('b78.ph_time')}"></td>
    <td><input type="number" class="form-control form-control-sm b78-pasos"
               min="1" max="10" step="1" value="${pasos}" placeholder="${t('b78.ph_steps')}"></td>
    <td class="text-center align-middle">
      <button type="button" class="btn btn-sm btn-outline-danger p-1 lh-1 b78-row-del">
        <i class="bi bi-x-lg"></i>
      </button>
    </td>`;
  tbody.appendChild(tr);
  tr.querySelector('.b78-row-del').addEventListener('click', () => {
    tr.remove();
    renumberB78EditorRows(prefix, phase);
    if (onChange) onChange();
  });
  tr.querySelectorAll('input').forEach(el => el.addEventListener('change', () => {
    if (onChange) onChange();
  }));
}

function renumberB78EditorRows(prefix, phase) {
  document.querySelectorAll(`#${prefix}-${phase}-tbody tr .b78-row-num`)
    .forEach((td, i) => { td.textContent = i + 1; });
}

/** Lee todas las filas de `#${prefix}-${phase}-tbody` → [{t_fin, pasos}]. */
function getB78EditorFase(prefix, phase) {
  return [...document.querySelectorAll(`#${prefix}-${phase}-tbody tr`)].map(tr => ({
    t_fin: parseFloat(tr.querySelector('.b78-t-fin').value),
    pasos: parseInt(tr.querySelector('.b78-pasos').value, 10),
  }));
}

function getB78EditorFases(prefix) {
  return { fasesIrr: getB78EditorFase(prefix, 'irr'), fasesCool: getB78EditorFase(prefix, 'cool') };
}

/** Limpia y re-añade filas para ambas fases (sembrado inicial o duplicado
 * de una tarjeta). */
function setB78EditorFases(prefix, fasesIrr, fasesCool, onChange) {
  ['irr', 'cool'].forEach(phase => {
    const tbody = document.getElementById(`${prefix}-${phase}-tbody`);
    if (tbody) tbody.innerHTML = '';
  });
  (fasesIrr  || []).forEach(f => addB78EditorRow(prefix, 'irr',  f.t_fin, f.pasos, onChange));
  (fasesCool || []).forEach(f => addB78EditorRow(prefix, 'cool', f.t_fin, f.pasos, onChange));
}

function getB78EditorIunitIoutIplot(prefix) {
  return {
    iunit: getInt(`${prefix}-iunit`) || 3,
    iout:  document.getElementById(`${prefix}-iout`)?.checked  ? 1 : 0,
    iplot: document.getElementById(`${prefix}-iplot`)?.checked ? 1 : 0,
  };
}

/** Wires the "añadir tramo" buttons of an instance. `onChange` (if given)
 * fires on every row add/remove/edit AND when IUNIT/IOUT/IPLOT change. */
function wireB78EditorButtons(prefix, onChange) {
  const btnIrr  = document.getElementById(`btn-${prefix}-add-irr`);
  const btnCool = document.getElementById(`btn-${prefix}-add-cool`);
  if (btnIrr)  btnIrr.addEventListener('click',  () => addB78EditorRow(prefix, 'irr',  '', '', onChange));
  if (btnCool) btnCool.addEventListener('click', () => addB78EditorRow(prefix, 'cool', '', '', onChange));
  [`${prefix}-iunit`, `${prefix}-iout`, `${prefix}-iplot`].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', () => { if (onChange) onChange(); });
  });
}
