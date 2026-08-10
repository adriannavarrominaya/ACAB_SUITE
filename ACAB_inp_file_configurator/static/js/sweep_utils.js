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
 * Genera las tarjetas de Blocks #7/#8 SIN compactación entre fases (F7):
 * irradiación y enfriamiento nunca comparten tarjeta. Cada fase se trocea
 * por separado en grupos de <=10 tiempos; las tarjetas de irradiación
 * preceden siempre a las de enfriamiento. NGO/MSUB encadenan las tarjetas
 * globalmente (MSUB = MOUT de la tarjeta anterior, 0 en la primera; NGO=0
 * solo en la última tarjeta).
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

  const chunk10 = (arr) => {
    const out = [];
    for (let i = 0; i < arr.length; i += 10) out.push(arr.slice(i, i + 10));
    return out;
  };
  const chunks = [
    ...chunk10(tiempos_irr).map(times  => ({ TIMES: times, MMN: times.length })),
    ...chunk10(tiempos_cool).map(times => ({ TIMES: times, MMN: 0 })),
  ];

  const sets = chunks.map((chunk, idx) => ({
    MMN:   chunk.MMN,
    MOUT:  chunk.TIMES.length,
    NGO:   idx < chunks.length - 1 ? 1 : 0,
    MSUB:  idx > 0 ? chunks[idx - 1].TIMES.length : 0,
    IUNIT: iunit, MFEED: 0, IOUT: iout, IPLOT: iplot,
    TIMES: chunk.TIMES,
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
 * Devuelve `base` si no está en `taken`; si no, el primer `base_N` (N=2,3,…)
 * que no colisione. Genérica -- desambigua sufijos duplicados dentro de un
 * mismo barrido (usada por el barrido espectral y por el temporal: dos
 * tarjetas con el mismo t_irr_fin pero historial distinto no deben
 * colisionar de carpeta).
 * @returns {string}
 */
function uniqueSuffix(base, taken) {
  if (!taken.includes(base)) return base;
  let i = 2;
  while (taken.includes(`${base}_${i}`)) i++;
  return `${base}_${i}`;
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

// ── F20: reconstrucción de tramos reales desde Blocks #7/#8 ────────────────
/**
 * Tolerancia relativa por defecto para decidir si dos saltos consecutivos
 * pertenecen a la misma racha de espaciado constante. Blocks #7/#8 se
 * escriben con 7 cifras significativas (app.py::_sci), pero un inp.5 ajeno
 * a esta app puede traer menos precisión -- 1e-4 cubre con holgura el
 * redondeo típico de formato E sin fundir rachas realmente distintas.
 */
const TIME_MESH_REL_TOL = 1e-4;

/**
 * Nº máximo de tramos (filas del editor) que se reconstruyen por fase antes
 * de avisar en vez de generar una lista de filas inmanejable -- caso de una
 * malla irregular sin ninguna racha agrupable. Generoso frente al límite de
 * 10 tramos del generador Tkinter legacy (generador_acab.py, el editor web
 * sí hace scroll), pero evita que un fichero con cientos de pasos sin
 * agrupar bloquee la interfaz en silencio.
 */
const TIME_MESH_MAX_TRAMOS = 50;

function _closeEnoughRel(a, b, tol) {
  return Math.abs(a - b) <= tol * Math.max(Math.abs(a), Math.abs(b), 1e-12);
}

/**
 * Segmenta una lista ORDENADA y CRECIENTE de tiempos acumulados de UNA fase
 * (desde su inicio, t=0) en tramos {t_fin, pasos}, inverso de
 * calcularVectorTiempos: dentro de una racha real, TODOS los saltos entre
 * tiempos consecutivos -incluido el salto desde el final de la racha
 * anterior (o desde 0)- son iguales. Reconstruir con esto y volver a
 * generar con buildBlocks78 reproduce EXACTAMENTE los mismos tiempos (F20
 * del BACKLOG: antes, el generador colapsaba la malla entera a un único
 * tramo por fase, conservando solo el tiempo final y perdiendo los cortes
 * intermedios sin ningún aviso).
 *   - Malla uniforme (una sola racha) → un tramo (varios si supera 10
 *     pasos, límite ya impuesto por calcularVectorTiempos -- se reparte
 *     conservando el mismo espaciado, nunca se trunca).
 *   - Varias rachas → un tramo por racha, en el orden en que aparecen.
 *   - Espaciado irregular no agrupable (ninguna racha de más de 1 punto) →
 *     un tramo por paso, sin forzar agrupaciones "por simplificar".
 *   - Si el nº de tramos resultante supera TIME_MESH_MAX_TRAMOS, lanza en
 *     vez de devolver una lista inmanejable (avisar, no colapsar en
 *     silencio).
 * @param {number[]} times  tiempos absolutos crecientes desde el inicio de la fase.
 * @param {{tol?:number, maxTramos?:number, t?:Function}} [opts]
 * @returns {{t_fin:number, pasos:number}[]}
 */
function reconstructFasesFromTimes(times, opts) {
  const o = opts || {};
  const tol = Number.isFinite(o.tol) ? o.tol : TIME_MESH_REL_TOL;
  const maxTramos = Number.isFinite(o.maxTramos) ? o.maxTramos : TIME_MESH_MAX_TRAMOS;
  const tr = (typeof o.t === 'function') ? o.t : (k => k);
  if (!times || times.length === 0) return [];

  // 1. Salto entre cada tiempo y el anterior (el primero, contra t=0).
  const deltas = times.map((v, i) => v - (i === 0 ? 0 : times[i - 1]));

  // 2. Agrupa índices consecutivos cuyo salto coincide (tolerancia relativa)
  //    con el salto que abrió la racha -- referencia fija, no el anterior,
  //    para no acumular deriva en rachas largas.
  const rachas = [];
  let cur = [0];
  for (let i = 1; i < times.length; i++) {
    if (_closeEnoughRel(deltas[i], deltas[cur[0]], tol)) cur.push(i);
    else { rachas.push(cur); cur = [i]; }
  }
  rachas.push(cur);

  // 3. Cada racha se reparte en tramos de ≤10 pasos (límite del editor),
  //    conservando el espaciado -- varias filas de la MISMA racha, no una
  //    racha nueva.
  const tramos = [];
  for (const racha of rachas) {
    for (let i = 0; i < racha.length; i += 10) {
      const chunk = racha.slice(i, i + 10);
      const lastIdx = chunk[chunk.length - 1];
      tramos.push({ t_fin: times[lastIdx], pasos: chunk.length });
    }
  }

  if (tramos.length > maxTramos)
    throw new Error(tr('b78.mesh_too_irregular')
      .replace('{n}', tramos.length).replace('{max}', maxTramos));

  return tramos;
}

/**
 * Reconstruye {fasesIrr, fasesCool} a partir de `blocks78.times` (la lista
 * plana [[t, esIrradiacion01], ...] que trae un inp.5 ya parseado, formato
 * F7 -tarjetas por fase- o compactado histórico -mezcladas-, da igual: la
 * lista plana ya distingue cada tiempo por fase). Camino ÚNICO usado tanto
 * por el generador manual como por la siembra de la tarjeta 1 del barrido
 * temporal (F20 del BACKLOG) -- sin este camino común, cualquier fix
 * aplicado a uno de los dos divergiría del otro.
 * @param {{times:Array}} b78
 * @param {{tol?:number, maxTramos?:number, t?:Function}} [opts]
 * @returns {{fasesIrr:{t_fin:number,pasos:number}[], fasesCool:{t_fin:number,pasos:number}[]}}
 */
function reconstructFasesFromBlocks78(b78, opts) {
  const times = (b78 && b78.times) || [];
  const irr  = times.filter(([, k]) => k === 1).map(([v]) => v);
  const cool = times.filter(([, k]) => k === 0).map(([v]) => v);
  return {
    fasesIrr:  reconstructFasesFromTimes(irr, opts),
    fasesCool: reconstructFasesFromTimes(cool, opts),
  };
}

// ── Barrido temporal (historial multi-tramo + NOTTS, U7 del BACKLOG) ───────
/**
 * Cada fila describe una simulación (una tarjeta del acordeón) con un
 * historial COMPLETO y explícito por fase — ya no hay "campo vacío conserva
 * la fase del fichero base": cada tarjeta lleva su propio iunit/iout/iplot,
 * igual que una instancia del editor de tramos completo.
 * @param {{fasesIrr:{t_fin:number,pasos:number}[], fasesCool:{t_fin:number,pasos:number}[],
 *           iunit?:number, iout?:number|boolean, iplot?:number|boolean}[]} filas
 * @param {{t?:Function}} [opts]
 * @returns {{params:Object, patch:Object}[]}
 */
function buildTimePatches(filas, opts) {
  const o = opts || {};
  const out = [];
  for (const fila of filas) {
    const fasesIrr  = fila.fasesIrr  || [];
    const fasesCool = fila.fasesCool || [];
    if (!fasesIrr.length && !fasesCool.length)
      throw new Error(o.t ? o.t('b78.no_phase') : 'Cada simulación temporal debe definir al menos una fase (irr o cool).');
    const b78 = buildBlocks78(fasesIrr, fasesCool,
      { iunit: fila.iunit, iout: fila.iout, iplot: fila.iplot, t: o.t });
    out.push({
      params: {
        t_irr_fin:  fasesIrr.length  ? fasesIrr[fasesIrr.length - 1].t_fin   : undefined,
        t_cool_fin: fasesCool.length ? fasesCool[fasesCool.length - 1].t_fin : undefined,
        historial_irr: fasesIrr, historial_cool: fasesCool,
      },
      // NOTTS (Block #11) = nº de tarjetas del historial; ITSO (Block #13,
      // tarjeta 3) es un vector [NOTTS] con el flag de salida por time set
      // (manual ACAB 2008, Block #13) -- debe crecer/encoger junto a NOTTS o
      // el inp.5 queda inconsistente (F8 del BACKLOG). Se sincroniza a "todo
      // con salida"; la salida por intervalo exige además IOUT=1 en la
      // tarjeta del set, que buildBlocks78 ya escribe.
      patch: {
        blocks78: { sets: b78.sets, times: b78.times },
        block11: { NOTTS: b78.notts },
        block13: { ITSO: Array(b78.notts).fill(1) },
      },
    });
  }
  return out;
}

/**
 * Resumen de una tarjeta del acordeón temporal: recuentos de tramos y
 * tiempo final de cada fase (o null si la fase está vacía). Pura, sin DOM.
 * @returns {{irrTramos:number, irrFinal:number|null, coolTramos:number, coolFinal:number|null}}
 */
function summarizeFases(fasesIrr, fasesCool) {
  const irr  = fasesIrr  || [];
  const cool = fasesCool || [];
  return {
    irrTramos:  irr.length,  irrFinal:  irr.length  ? irr[irr.length - 1].t_fin   : null,
    coolTramos: cool.length, coolFinal: cool.length ? cool[cool.length - 1].t_fin : null,
  };
}

/**
 * Clona profundamente `list[idx]` e inserta el clon justo después. Devuelve
 * un array NUEVO (no muta `list`). Genérica -- no específica del barrido
 * temporal, usable para cualquier "duplicar" de una lista de tarjetas.
 * @returns {Array}
 */
function insertDuplicate(list, idx) {
  const clone = JSON.parse(JSON.stringify(list[idx]));
  const out = list.slice();
  out.splice(idx + 1, 0, clone);
  return out;
}

/* Export para node (tests); en el navegador quedan como globales. */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    calcularVectorTiempos, buildBlocks78, parseSweepValues, proposeSuffix,
    buildFluxPatches, fluxBaseTotal, buildMassPatches, buildTimePatches,
    fluxValuesPlaceholder, fluxSweepGuardrail, summarizeFases, insertDuplicate,
    uniqueSuffix, reconstructFasesFromTimes, reconstructFasesFromBlocks78,
    TIME_MESH_REL_TOL, TIME_MESH_MAX_TRAMOS,
  };
}
