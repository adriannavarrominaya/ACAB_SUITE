/* ─────────────────────────────────────────────────────────────────────────
   optim_utils.js — Pestaña "Optimización" (Fase 5 opcional del runbook del
   barrido paramétrico: RUNBOOK_barrido_parametrico_v2.md).

   Funciones puras (sin DOM) que combinan `sweep_manifest.json` (folder →
   params, generado por el ACAB INP File Configurator) con el informe del
   isótopo ya calculado por el servidor (`/api/isotopo_report`: A_pico,
   t_pico, pureza, rendimiento). NO recalculan ninguna fórmula física — solo
   combinan, filtran y agrupan datos que ya existen. UMD puro, estilo
   units.js / export_utils.js: reutilizable en el navegador (global
   `ACABOptim`) y en node (tools/test_optim_utils.js).
   ───────────────────────────────────────────────────────────────────────── */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ACABOptim = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * Combina `manifest.simulations` (folder → params) con `reportSimulations`
   * (A_pico/t_pico por sim, de informe.simulations) y `reportMetricas`
   * (pureza/rendimiento por sim, de informe.metricas), restringido a
   * `simNames` (las simulaciones realmente analizadas en esta carpeta).
   * Devuelve una fila por simulación con entrada en el manifest.
   */
  function mergeSweepRows(manifest, simNames, reportSimulations, reportMetricas) {
    const bySimName = {};
    ((manifest && manifest.simulations) || []).forEach(s => {
      bySimName[s.folder] = s.params || {};
    });

    const rows = [];
    (simNames || []).forEach(name => {
      if (!Object.prototype.hasOwnProperty.call(bySimName, name)) return;
      const pico = (reportSimulations && reportSimulations[name]) || {};
      const met  = (reportMetricas && reportMetricas[name]) || {};
      rows.push({
        name,
        params:              bySimName[name],
        A_pico:              pico.A_pico != null ? pico.A_pico : null,
        t_pico:              pico.t_pico != null ? pico.t_pico : null,
        // F21 del BACKLOG: instante DECLARADO (origen explícito, vía
        // fort_analyzer.declarar_instante) -- el que debe mostrarse o
        // exportarse; `t_pico` (arriba, absoluto) queda solo para usos
        // internos que de verdad necesiten el eje común irr+enfriamiento.
        t_pico_declarado_h: pico.t_pico_declarado_h != null ? pico.t_pico_declarado_h : null,
        origen_pico:        pico.origen_pico || null,
        P_pct:               met.pureza ? met.pureza.P_pct : null,
        rendimiento_medio:   met.rendimiento ? met.rendimiento.rendimiento_medio : null,
        // F2 del BACKLOG: valor destacado (en t_cruce de pureza) de la
        // actividad específica del yodo -- null si el isótopo no es yodo o
        // no hay instante de cruce que destacar.
        A_esp_yodo_t_cruce: met.actividad_especifica_yodo_serie
          ? met.actividad_especifica_yodo_serie.valor_destacado_MBq_g : null,
      });
    });
    return rows;
  }

  /** Union de las claves de `params` cuyo valor es numérico, en orden de
   * primera aparición (las candidatas a eje X / columnas de la tabla). */
  function paramKeys(rows) {
    const keys = [];
    (rows || []).forEach(r => {
      Object.entries(r.params || {}).forEach(([k, v]) => {
        if (typeof v === 'number' && isFinite(v) && keys.indexOf(k) === -1) keys.push(k);
      });
    });
    return keys;
  }

  /**
   * Agrupa `rows` por el valor conjunto de las claves de parámetro DISTINTAS
   * de `xKey` (las "demás dimensiones" del barrido, mostradas como series de
   * color); si solo varía `xKey`, todas las filas caen en un único grupo sin
   * etiqueta. Cada grupo se devuelve ordenado por `params[xKey]` ascendente.
   * Filas sin valor numérico para `xKey` se omiten.
   */
  function groupByOtherParams(rows, xKey, keys) {
    const allKeys = keys || paramKeys(rows);
    const otherKeys = allKeys.filter(k => k !== xKey);
    const order = [];
    const groups = {};

    (rows || []).forEach(r => {
      const xv = r.params ? r.params[xKey] : undefined;
      if (typeof xv !== 'number' || !isFinite(xv)) return;
      const label = otherKeys.map(k => `${k}=${r.params[k]}`).join(', ');
      const groupKey = label || '__single__';
      if (!groups[groupKey]) {
        groups[groupKey] = { label, rows: [] };
        order.push(groupKey);
      }
      groups[groupKey].rows.push(r);
    });

    return order.map(k => {
      const g = groups[k];
      g.rows.sort((a, b) => a.params[xKey] - b.params[xKey]);
      return g;
    });
  }

  /** Valor crudo (sin convertir de unidad) de la variable Y elegida.
   *
   * F21 del BACKLOG: 't_pico' usa SIEMPRE el instante DECLARADO (origen
   * explícito) -- necesario también aquí, no solo en exportaciones: un
   * barrido temporal (U8) puede comparar simulaciones con T_irr distinto,
   * y el eje absoluto mezclaría orígenes sin decirlo. */
  function yRawValue(row, yVar) {
    if (yVar === 't_pico')      return row.t_pico_declarado_h;
    if (yVar === 'pureza')      return row.P_pct;
    if (yVar === 'rendimiento') return row.rendimiento_medio;
    if (yVar === 'a_esp_yodo')  return row.A_esp_yodo_t_cruce;
    return row.A_pico; // 'a_pico', valor por defecto
  }

  /** ¿La variable Y es una actividad (Bq/cm³) que necesita convertirse a la
   * unidad activa? t_pico [h] y pureza [%] son invariantes de unidad;
   * a_esp_yodo también lo es -- ya viene en MBq/g de YODO del servidor
   * (fort_analyzer.calcular_actividad_especifica_yodo_serie), un eje de
   * unidad distinto del selector Bq/cm³↔MBq/g↔MBq↔mCi del target (F2). */
  function yNeedsUnitConv(yVar) {
    return yVar === 'a_pico' || yVar === 'rendimiento' || !yVar;
  }

  /** ¿Es un barrido espectral? (U4 del BACKLOG: una sola serie por métrica,
   * nunca agrupada por las fracciones espectrales -- ver groupByOtherParams). */
  function isSpectrumSweep(manifest) {
    return !!(manifest && manifest.sweep_type === 'spectrum');
  }

  /** Etiqueta legible de una fila de barrido espectral: el NOMBRE del
   * espectro (`row.params.espectro`, escrito por el runbook espectral desde
   * sweep_manifest.json). Si un manifest viejo no lo trae, degrada al
   * identificador de carpeta (`row.name`) -- NUNCA a un volcado de
   * parámetros (frac_termica/n_grupos/...); criterio compartido con la
   * vista de "consultar un barrido" del INP configurator (U6). */
  function spectrumRowLabel(row) {
    const esp = row && row.params && row.params.espectro;
    if (typeof esp === 'string' && esp.trim()) return esp;
    return (row && row.name) || '';
  }

  /** Claves numéricas candidatas a eje X en un barrido espectral (U4b del
   * BACKLOG), en el orden fijado por el diseño. Distinto de `paramKeys`
   * (genérico, cualquier clave numérica): aquí solo interesan las fracciones
   * espectrales, nunca `n_grupos` (sin significado físico como eje X). */
  const SPECTRUM_FRAC_KEYS = ['frac_termica', 'frac_epitermica', 'frac_rapida'];

  /** De `SPECTRUM_FRAC_KEYS`, las que están realmente presentes (numéricas)
   * en `rows` -- un manifest viejo sin fracciones espectrales no las trae,
   * y la UI debe poder distinguir "disponible" de "no disponible" por clave. */
  function spectrumNumericKeys(rows) {
    const present = paramKeys(rows);
    return SPECTRUM_FRAC_KEYS.filter(k => present.indexOf(k) !== -1);
  }

  /** Posición de la etiqueta de texto junto a cada punto de la dispersión
   * eje-X-numérico del barrido espectral (U4b): alterna arriba/abajo cuando
   * dos puntos consecutivos (`xs` ya ordenado ascendente) caen a menos del
   * 4 % del rango total -- desplazamiento simple para que los 9 reactores
   * reales (agrupados en frac_termica) no se solapen todos en el mismo
   * punto. Puntos aislados se quedan en la posición por defecto. */
  function spectrumTextPositions(xs) {
    const n = (xs || []).length;
    const positions = new Array(n).fill('top center');
    if (n < 2) return positions;

    const finite = xs.filter(v => typeof v === 'number' && isFinite(v));
    const range = finite.length ? (Math.max(...finite) - Math.min(...finite)) : 0;
    if (!(range > 0)) return positions;

    const threshold = range * 0.04;
    for (let i = 1; i < n; i++) {
      const close = Math.abs(xs[i] - xs[i - 1]) < threshold;
      positions[i] = close
        ? (positions[i - 1] === 'top center' ? 'bottom center' : 'top center')
        : 'top center';
    }
    return positions;
  }

  /** ¿Es un barrido temporal? (U8 del BACKLOG: opción de eje X categórico
   * por simulación, para comparar historiales de igual t_irr_fin y
   * distinta forma -- caso habilitado por U7 del INP configurator, que
   * permite tarjetas con el mismo t_irr_fin pero un historial de tramos
   * distinto). */
  function isTimeSweep(manifest) {
    return !!(manifest && manifest.sweep_type === 'time');
  }

  /** Clave sentinela del eje X categórico "por simulación" (U8) en el
   * `<select>` de eje X de un barrido temporal -- nunca coincide con una
   * clave real de `params` (t_irr_fin/t_cool_fin son siempre identificadores
   * ASCII simples sin espacios ni "__"), así que convive sin ambigüedad con
   * las claves numéricas de `paramKeys()` en el mismo desplegable. */
  const TIME_X_CATEGORICAL = '__sim__';

  /** Etiqueta de una fila de barrido temporal en el eje X categórico: el
   * NOMBRE de la simulación (carpeta) -- el manifest de un barrido temporal
   * no trae ningún campo tipo `espectro` (U4) más descriptivo, y el nombre
   * de carpeta ya es la identificación que U7 desambigua (p. ej.
   * "Tirr050.0h"/"Tirr050.0h_2"). */
  function timeRowLabel(row) {
    return (row && row.name) || '';
  }

  /** `rows` ordenadas para el eje X categórico (U8): por nombre de
   * simulación, ascendente -- un orden estable y predecible que no depende
   * de ningún parámetro numérico (a diferencia de `groupByOtherParams`, que
   * SÍ asume un `xKey` numérico). */
  function sortRowsByName(rows) {
    return (rows || []).slice().sort((a, b) => timeRowLabel(a).localeCompare(timeRowLabel(b)));
  }

  return {
    mergeSweepRows,
    paramKeys,
    groupByOtherParams,
    yRawValue,
    yNeedsUnitConv,
    isSpectrumSweep,
    spectrumRowLabel,
    SPECTRUM_FRAC_KEYS,
    spectrumNumericKeys,
    spectrumTextPositions,
    isTimeSweep,
    TIME_X_CATEGORICAL,
    timeRowLabel,
    sortRowsByName,
  };
});
