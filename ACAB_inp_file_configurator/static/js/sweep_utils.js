/* sweep_utils.js — Funciones PURAS (sin DOM) para el generador de barridos
 * paramétricos (Fase 1 del runbook v2).  Testeable con node:
 *   node tools/test_sweep_utils.js
 *
 * Un barrido = un solo tipo (flujo XOR masa XOR temporal).  Cada función
 * "buildXxxPatches" devuelve una lista de { params, patch }, donde `patch` es
 * un fragmento del dict de datos del formulario que se fusiona (merge
 * recursivo) sobre una copia del fichero base en el servidor.
 *
 * Convenios de dominio (docs/):
 *   - Flujo → block9.XNORM (factor multiplicativo del flujo; escala magnitud,
 *     NO la forma del espectro).
 *   - Masa  → XCOMP de UNA zona (volumen y compuesto fijos ⇒ varía la densidad
 *     de empaquetado del blanco).  Estructura de zonas congelada.
 *   - Temporal → blocks78 regenerado + block11.NOTTS = nº de sets.
 *
 * La lógica de mallas (buildBlocks78 / calcularVectorTiempos) es la MISMA que
 * usaba generarB78 en app.js; se extrajo aquí para reutilizarla en el barrido
 * temporal sin cambiar el comportamiento del generador manual.
 */
'use strict';

/* En node, calc_utils es un módulo; en el navegador queda como global. */
const _calc = (typeof module !== 'undefined' && module.exports)
  ? require('./calc_utils.js') : null;
function _computeComposition(args) {
  const fn = _calc ? _calc.computeComposition : computeComposition;
  return fn(args);
}

// ── Vector de tiempos (espaciado lineal por fase) ──────────────────────────
/**
 * Reparte cada fase {t_fin, pasos} en `pasos` instantes equiespaciados desde
 * el tiempo acumulado anterior hasta t_fin (comportamiento idéntico al
 * generador manual original).
 * @param {{t_fin:number, pasos:number}[]} entradas
 * @param {(k:string)=>string} [t]  traductor i18n (por defecto identidad)
 * @returns {number[]}
 */
function calcularVectorTiempos(entradas, t) {
  const tr = (typeof t === 'function') ? t : (k => k);
  const tiempos = [];
  let t_actual = 0.0;
  for (const { t_fin, pasos } of entradas) {
    if (!Number.isFinite(pasos) || pasos < 1 || pasos > 10)
      throw new Error(tr('b78.error_steps').replace('{n}', pasos));
    if (!Number.isFinite(t_fin) || t_fin <= t_actual)
      throw new Error(tr('b78.error_time').replace('{t}', t_fin).replace('{prev}', t_actual));
    const salto = (t_fin - t_actual) / pasos;
    for (let i = 1; i <= pasos; i++) tiempos.push(t_actual + i * salto);
    t_actual = t_fin;
  }
  return tiempos;
}

// ── Bloques #7/#8 a partir de las fases de irradiación y enfriamiento ──────
/**
 * @param {{t_fin:number,pasos:number}[]} fasesIrr
 * @param {{t_fin:number,pasos:number}[]} fasesCool
 * @param {{iunit?:number,iout?:number|boolean,iplot?:number|boolean,t?:Function}} [opts]
 * @returns {{sets:Object[], times:Array, notts:number}}
 */
function buildBlocks78(fasesIrr, fasesCool, opts) {
  const o = opts || {};
  const iunit = Number.isFinite(o.iunit) ? o.iunit : 3;
  const iout  = o.iout ? 1 : 0;
  const iplot = o.iplot ? 1 : 0;
  const tr    = o.t;

  const tiempos_irr  = (fasesIrr  && fasesIrr.length)  ? calcularVectorTiempos(fasesIrr, tr)  : [];
  const tiempos_cool = (fasesCool && fasesCool.length) ? calcularVectorTiempos(fasesCool, tr) : [];
  const lista_global = [
    ...tiempos_irr.map(t  => [t, 1]),
    ...tiempos_cool.map(t => [t, 0]),
  ];

  const chunks = [];
  for (let i = 0; i < lista_global.length; i += 10) chunks.push(lista_global.slice(i, i + 10));

  const sets = chunks.map((chunk, idx) => ({
    MMN:   chunk.filter(([, tipo]) => tipo === 1).length,
    MOUT:  chunk.length,
    NGO:   idx < chunks.length - 1 ? 1 : 0,
    MSUB:  idx > 0 ? chunks[idx - 1].length : 0,
    IUNIT: iunit, MFEED: 0, IOUT: iout, IPLOT: iplot,
    TIMES: chunk.map(([t]) => t),
  }));

  return { sets, times: lista_global, notts: sets.length };
}

// ── Parseo y sufijos ───────────────────────────────────────────────────────
/**
 * Convierte un texto separado por comas/espacios/; en una lista de números.
 * Lanza Error si está vacía, hay tokens no numéricos, o supera 200 valores.
 */
function parseSweepValues(txt) {
  const parts = String(txt == null ? '' : txt).split(/[\s,;]+/).filter(s => s.length);
  if (parts.length === 0) throw new Error('La lista de valores está vacía.');
  const nums = [];
  for (const p of parts) {
    const n = Number(p);
    if (!Number.isFinite(n)) throw new Error(`Valor no numérico: '${p}'.`);
    nums.push(n);
  }
  if (nums.length > 200) throw new Error(`Demasiados valores (${nums.length}); el máximo es 200.`);
  return nums;
}

function _cleanNum(v) {
  // Representación estable y segura para nombres de fichero (sin '+').
  return String(v).replace('+', '');
}

/**
 * Propone un sufijo de subcarpeta estable y seguro a partir de un valor.
 *   proposeSuffix('flux', 0.75) → 'x0.75'
 *   proposeSuffix('mass', 1.5)  → 'm1.500g'
 *   proposeSuffix('time', 48)   → 'Tirr048.0h'
 */
function proposeSuffix(tipo, valor) {
  const v = Number(valor);
  if (!Number.isFinite(v)) return 'NA';
  if (tipo === 'flux' || tipo === 'xnorm' || tipo === 'phi') return 'x' + _cleanNum(v);
  if (tipo === 'mass') return 'm' + v.toFixed(3) + 'g';
  if (tipo === 'time' || tipo === 'tirr') {
    const [intp, dec] = v.toFixed(1).split('.');
    return 'Tirr' + intp.padStart(3, '0') + '.' + dec + 'h';
  }
  return _cleanNum(v);
}

// ── Barrido de flujo (XNORM) ───────────────────────────────────────────────
/**
 * @param {number[]} valores
 * @param {'xnorm'|'phi'} modo  'xnorm' = valores son factores XNORM directos;
 *                              'phi'   = valores son flujo total objetivo →
 *                                        XNORM = φ_objetivo / φ_base.
 * @param {number} [phiBase]    flujo total del fichero base (necesario en 'phi').
 * @returns {{params:Object, patch:Object}[]}
 */
function buildFluxPatches(valores, modo, phiBase) {
  const out = [];
  for (const v of valores) {
    let xnorm, params;
    if (modo === 'phi') {
      if (!(phiBase > 0))
        throw new Error('El flujo base (φ_base) debe ser > 0 para el modo "flujo objetivo".');
      xnorm  = v / phiBase;
      params = { phi: v, XNORM: xnorm };
    } else {
      xnorm  = v;
      params = { XNORM: xnorm };
    }
    out.push({ params, patch: { block9: { XNORM: xnorm } } });
  }
  return out;
}

/** φ_base = Σ(FLUX del Bloque #3) × XNORM_base. */
function fluxBaseTotal(block3, block9) {
  const flux  = (block3 && block3.FLUX) || [];
  const xnorm = (block9 && Number.isFinite(block9.XNORM)) ? block9.XNORM : 1;
  const sum   = flux.reduce((a, b) => a + (Number(b) || 0), 0);
  return sum * xnorm;
}

// ── U5: placeholder dinámico y guardarraíl de confusión flujo/factor ──────
/**
 * Placeholder del campo de valores del barrido de flujo.
 * Modo 'xnorm' → ejemplos de factores (estáticos, sin unidades).
 * Modo 'phi'   → ejemplos ×0.5/×1/×2 derivados del φ_base REAL del fichero
 *                cargado; si no hay φ_base (sin fichero cargado o φ_base ≤ 0)
 *                devuelve null — el llamador debe usar un texto genérico con
 *                la unidad, NUNCA el placeholder de factores del otro modo.
 * @returns {string|null}
 */
function fluxValuesPlaceholder(modo, phiBase) {
  if (modo === 'phi') {
    if (!(phiBase > 0)) return null;
    return [0.5, 1, 2].map(f => (phiBase * f).toExponential(2)).join(', ');
  }
  return '0.5, 0.75, 1.0, 1.5';
}

/**
 * Guardarraíl de confusión flujo total ⇄ factor XNORM: devuelve los valores
 * introducidos cuyo XNORM cae fuera del rango habitual [1e-3, 1e3].
 * Modo 'phi'   → XNORM resultante = valor / φ_base (mismo cálculo que
 *                buildFluxPatches); fuera de rango ⇒ ¿el valor es en
 *                realidad un factor, no un flujo?
 * Modo 'xnorm' → el valor introducido SE USA directamente como XNORM; fuera
 *                de rango (típicamente por ser enorme, ~escala de flujo real)
 *                ⇒ ¿el valor es en realidad un flujo absoluto, no un factor?
 * @returns {{value:number, xnorm:number}[]} valores sospechosos
 */
function fluxSweepGuardrail(valores, modo, phiBase) {
  const LO = 1e-3, HI = 1e3;
  const out = [];
  for (const v of valores) {
    const xnorm = modo === 'phi' ? (phiBase > 0 ? v / phiBase : NaN) : v;
    if (Number.isFinite(xnorm) && (xnorm < LO || xnorm > HI)) out.push({ value: v, xnorm });
  }
  return out;
}

// ── Barrido de masa (XCOMP de una zona) ────────────────────────────────────
/**
 * Recalcula XCOMP de la zona `zoneIdx` para cada masa, conservando INUCL y el
 * resto de zonas.  El compuesto y el volumen son fijos ⇒ solo cambia la
 * densidad.  El orden de INUCL de la zona base se conserva (los XCOMP se
 * reordenan para casar con él).
 * @returns {{params:Object, patch:Object}[]}
 */
function buildMassPatches({ masas, formula, volumen, inpt, zoneIdx, baseBlock5, elements }) {
  if (inpt === 2)
    throw new Error('El barrido de masa no soporta INPT=2 (isótopos); usa átomos/barn·cm o g/cc.');
  const base = baseBlock5 || [];
  const zone = base[zoneIdx];
  if (!zone) throw new Error(`La zona ${zoneIdx + 1} no existe en la composición base.`);
  const baseInucl = zone.INUCL || [];
  if (baseInucl.length === 0)
    throw new Error(`La zona ${zoneIdx + 1} no tiene nucleidos (INUCL vacío).`);

  const out = [];
  for (const m of masas) {
    const comp = _computeComposition({ formula, massG: m, volumeCc: volumen, inpt, elements });
    const byId = {};
    comp.rows.forEach(r => { byId[r.elemid] = r.xcomp; });
    const xcomp = baseInucl.map(id => {
      if (!(id in byId))
        throw new Error(`La fórmula '${formula}' no contiene el nucleido ${id} presente `
          + `en la zona ${zoneIdx + 1}; no se puede barrer la masa sin cambiar el compuesto.`);
      return byId[id];
    });
    const newB5 = base.map((z, i) => i === zoneIdx
      ? { INUCL: baseInucl.slice(), XCOMP: xcomp }
      : { INUCL: (z.INUCL || []).slice(), XCOMP: (z.XCOMP || []).slice() });
    out.push({ params: { mass: m }, patch: { block5: newB5 } });
  }
  return out;
}

// ── Barrido temporal (historial + NOTTS) ───────────────────────────────────
/**
 * Cada fila describe una simulación: {t_irr_fin, pasos_irr, t_cool_fin,
 * pasos_cool}.  Un campo de fase vacío/NaN ⇒ se conserva la fase del fichero
 * base (opts.baseIrr / opts.baseCool).
 * @returns {{params:Object, patch:Object}[]}
 */
function buildTimePatches(filas, opts) {
  const o = opts || {};
  const iunit    = Number.isFinite(o.iunit) ? o.iunit : 3;
  const iout     = o.iout ? 1 : 0;
  const iplot    = o.iplot ? 1 : 0;
  const baseIrr  = o.baseIrr  || [];
  const baseCool = o.baseCool || [];
  const out = [];
  for (const fila of filas) {
    const fasesIrr = (Number.isFinite(fila.t_irr_fin) && Number.isFinite(fila.pasos_irr))
      ? [{ t_fin: fila.t_irr_fin, pasos: fila.pasos_irr }] : baseIrr;
    const fasesCool = (Number.isFinite(fila.t_cool_fin) && Number.isFinite(fila.pasos_cool))
      ? [{ t_fin: fila.t_cool_fin, pasos: fila.pasos_cool }] : baseCool;
    if ((!fasesIrr || !fasesIrr.length) && (!fasesCool || !fasesCool.length))
      throw new Error('Cada simulación temporal debe definir al menos una fase (irr o cool).');
    const b78 = buildBlocks78(fasesIrr, fasesCool, { iunit, iout, iplot, t: o.t });
    out.push({
      params: {
        t_irr_fin: fila.t_irr_fin, pasos_irr: fila.pasos_irr,
        t_cool_fin: fila.t_cool_fin, pasos_cool: fila.pasos_cool,
      },
      patch: { blocks78: { sets: b78.sets, times: b78.times }, block11: { NOTTS: b78.notts } },
    });
  }
  return out;
}

/* Export para node (tests); en el navegador quedan como globales. */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    calcularVectorTiempos, buildBlocks78, parseSweepValues, proposeSuffix,
    buildFluxPatches, fluxBaseTotal, buildMassPatches, buildTimePatches,
    fluxValuesPlaceholder, fluxSweepGuardrail,
  };
}
