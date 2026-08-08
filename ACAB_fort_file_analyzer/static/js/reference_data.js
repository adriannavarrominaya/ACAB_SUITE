/* ─────────────────────────────────────────────────────────────────────────
   reference_data.js — Datos de referencia externos (Fase 4 del runbook).

   Parser + interpolación + métricas de desviación para el CSV de la
   especificación docs/SPEC_csv_datos_referencia.md. Función pura, sin
   dependencias de DOM, reutilizable en el navegador (global `ACABRefData`) y
   en node (`require`) para tools/test_reference_data.js.

   Depende de ACABUnits (static/js/units.js) solo para invertir el factor de
   conversión de unidad de actividad declarada en el CSV → Bq/cm³ interno.
   ───────────────────────────────────────────────────────────────────────── */
(function (root, factory) {
  const dep = (typeof module !== 'undefined' && module.exports)
    ? require('./units.js')
    : root.ACABUnits;
  const api = factory(dep);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ACABRefData = api;
})(typeof self !== 'undefined' ? self : this, function (ACABUnits) {
  'use strict';

  // Horas por unidad de tiempo declarada en el CSV.
  const TIME_UNIT_TO_H = { s: 1 / 3600, min: 1 / 60, h: 1, d: 24 };

  // Etiquetas de texto libre (metadatos / UI) → clave de ACABUnits.
  const ACTIVITY_LABEL_TO_UNIT = {
    'bq/cm3': 'bqcm3', 'bq/cm³': 'bqcm3',
    'mbq/g': 'mbqg',
    'mbq': 'mbq_total',
    'mci': 'mci_total',
  };

  function _normLabel(s) {
    return String(s || '').trim().toLowerCase();
  }

  /** "MBq/g" → 'mbqg'; clave de ACABUnits ya válida se devuelve tal cual. */
  function parseActivityUnitLabel(s) {
    const norm = _normLabel(s);
    if (ACABUnits && ACABUnits.isKnownUnit(s)) return s;
    return ACTIVITY_LABEL_TO_UNIT[norm] || null;
  }

  /** "h" / "H" / " h " → 'h'; unidad desconocida → null. */
  function parseTimeUnitLabel(s) {
    const norm = _normLabel(s);
    return Object.prototype.hasOwnProperty.call(TIME_UNIT_TO_H, norm) ? norm : null;
  }

  function convertTimeToHours(value, unit) {
    const f = TIME_UNIT_TO_H[unit];
    if (f === undefined) return null;
    const v = Number(value);
    return isFinite(v) ? v * f : null;
  }

  /** Bq/cm³ ← valor en `unit` (clave ACABUnits), usando la densidad/volumen de la sim de referencia. */
  function bqcm3FromUnit(value, unit, opts) {
    if (!ACABUnits) return null;
    const f = ACABUnits.unitFactor(unit, opts);
    if (!f) return null; // null o 0 → no convertible
    const v = Number(value);
    return isFinite(v) ? v / f : null;
  }

  // ───────────────────────────────────────────────────────────────────────
  // Parseo del CSV (docs/SPEC_csv_datos_referencia.md)
  // ───────────────────────────────────────────────────────────────────────

  function _splitLines(text) {
    // Tolerante a BOM UTF-8 y a finales de línea \r\n / \n / \r.
    const noBom = text.charCodeAt(0) === 0xFEFF ? text.slice(1) : text;
    return noBom.split(/\r\n|\r|\n/);
  }

  function _isBlank(line) {
    return line.trim().length === 0;
  }

  /** Línea "# clave: valor" → [clave normalizada, valor] o null si no matchea. */
  function _parseMetaLine(line) {
    const body = line.trim().replace(/^#\s*/, '');
    const idx = body.indexOf(':');
    if (idx === -1) return null;
    const key = body.slice(0, idx).trim().toLowerCase();
    const val = body.slice(idx + 1).trim();
    return key ? [key, val] : null;
  }

  function _detectDelimiter(dataLines) {
    for (const line of dataLines) {
      if (_isBlank(line)) continue;
      if (line.indexOf(';') !== -1) return ';';
      if (line.indexOf('\t') !== -1) return '\t';
      if (line.indexOf(',') !== -1) return ',';
      return ';'; // sin separador detectable (¿una sola columna?): por defecto
    }
    return ';';
  }

  /** Con delimitador ',' el decimal es SIEMPRE '.'; si no, autodetecta por muestreo. */
  function _detectDecimal(delimiter, dataLines) {
    if (delimiter === ',') return '.';
    let commaDecimals = 0, dotDecimals = 0;
    let sampled = 0;
    for (const line of dataLines) {
      if (_isBlank(line)) continue;
      if (sampled >= 8) break;
      sampled++;
      line.split(delimiter).forEach(cell => {
        const c = cell.trim();
        if (/^-?\d+,\d+$/.test(c)) commaDecimals++;
        else if (/^-?\d+\.\d+$/.test(c)) dotDecimals++;
      });
    }
    return commaDecimals >= dotDecimals ? ',' : '.';
  }

  function _parseNumberCell(cell, decimal) {
    let s = cell.trim();
    if (s === '') return NaN;
    if (decimal === ',') s = s.replace(/\./g, '').replace(',', '.');
    return parseFloat(s);
  }

  function _isNumericRow(cells, decimal) {
    return cells.every(c => c.trim() !== '' && !isNaN(_parseNumberCell(c, decimal)));
  }

  /**
   * Parsea el CSV completo. Devuelve:
   *   { meta, delimiter, decimal, headers (array|null), rows (number[][]) }
   * `rows` son solo las filas de datos (cabecera y comentarios ya excluidos),
   * ordenadas tal como aparecen en el fichero (sin reordenar por t todavía).
   */
  function parseCSV(text) {
    const lines = _splitLines(text);
    const meta = {};
    const dataLines = [];

    lines.forEach(line => {
      if (_isBlank(line)) return;
      const trimmed = line.trim();
      if (trimmed.startsWith('#')) {
        const kv = _parseMetaLine(trimmed);
        if (kv) meta[kv[0]] = kv[1];
        return;
      }
      dataLines.push(line);
    });

    if (dataLines.length === 0) {
      return { meta, delimiter: ';', decimal: ',', headers: null, rows: [] };
    }

    const delimiter = _detectDelimiter(dataLines);
    const decimal = _detectDecimal(delimiter, dataLines);

    let headers = null;
    let body = dataLines;
    const firstCells = dataLines[0].split(delimiter).map(c => c.trim());
    if (!_isNumericRow(firstCells, decimal)) {
      headers = firstCells;
      body = dataLines.slice(1);
    }

    const rows = body
      .filter(line => !_isBlank(line))
      .map(line => line.split(delimiter).map(c => _parseNumberCell(c, decimal)));

    return { meta, delimiter, decimal, headers, rows };
  }

  // ───────────────────────────────────────────────────────────────────────
  // Mapeo de columnas (heurística + construcción de la serie)
  // ───────────────────────────────────────────────────────────────────────

  /** Fracción de saltos consecutivos no decrecientes o no crecientes (monotonía). */
  function _monotonicRatio(values) {
    if (values.length < 2) return 0;
    let up = 0, down = 0, total = 0;
    for (let i = 1; i < values.length; i++) {
      const d = values[i] - values[i - 1];
      if (d === 0) continue;
      total++;
      if (d > 0) up++; else down++;
    }
    if (total === 0) return 1; // todo constante: técnicamente monótono
    return Math.max(up, down) / total;
  }

  /**
   * Preasignación heurística de roles por columna: la (casi) monótona es t;
   * de las restantes, la primera por orden original es A y la segunda A_err.
   * Devuelve un array de 't' | 'A' | 'A_err' | null, uno por columna.
   */
  function guessColumnRoles(rows) {
    if (!rows.length) return [];
    const nCols = rows[0].length;
    if (nCols === 0) return [];
    if (nCols === 1) return ['A'];

    const ratios = [];
    for (let c = 0; c < nCols; c++) {
      ratios.push(_monotonicRatio(rows.map(r => r[c])));
    }
    let tCol = 0;
    for (let c = 1; c < nCols; c++) if (ratios[c] > ratios[tCol]) tCol = c;

    const roles = new Array(nCols).fill(null);
    roles[tCol] = 't';
    const remaining = [];
    for (let c = 0; c < nCols; c++) if (c !== tCol) remaining.push(c);
    if (remaining[0] !== undefined) roles[remaining[0]] = 'A';
    if (remaining[1] !== undefined) roles[remaining[1]] = 'A_err';
    return roles;
  }

  /**
   * Construye los puntos {t, A, A_err} a partir de las filas y un mapeo de
   * columnas { t: idx, A: idx, A_err: idx|null|undefined }. Descarta filas
   * sin t/A numéricos válidos y ordena por t ascendente.
   */
  function buildSeriesPoints(rows, colMap) {
    const points = [];
    rows.forEach(row => {
      const t = row[colMap.t];
      const A = row[colMap.A];
      if (!isFinite(t) || !isFinite(A)) return;
      const hasErr = colMap.A_err !== null && colMap.A_err !== undefined;
      const A_err = hasErr ? row[colMap.A_err] : null;
      points.push({ t, A, A_err: (A_err !== null && isFinite(A_err)) ? A_err : null });
    });
    points.sort((a, b) => a.t - b.t);
    return points;
  }

  // ───────────────────────────────────────────────────────────────────────
  // Interpolación y métricas de desviación
  // ───────────────────────────────────────────────────────────────────────

  /**
   * Interpolación lineal con recorte a los extremos (igual que numpy.interp):
   * x <= xs[0] → ys[0]; x >= xs[last] → ys[last]. `xs` debe venir ordenado
   * ascendente. Devuelve null si no hay puntos.
   */
  function linearInterpClamped(xs, ys, x) {
    const n = xs.length;
    if (n === 0) return null;
    if (n === 1) return ys[0];
    if (x <= xs[0]) return ys[0];
    if (x >= xs[n - 1]) return ys[n - 1];
    for (let i = 1; i < n; i++) {
      if (x <= xs[i]) {
        const x0 = xs[i - 1], x1 = xs[i], y0 = ys[i - 1], y1 = ys[i];
        if (x1 === x0) return y0;
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0);
      }
    }
    return ys[n - 1];
  }

  /**
   * Para cada punto experimental {t, A}, interpola la curva ACAB (curveXs/Ys,
   * ordenada ascendente) en su t y calcula la desviación relativa (%):
   *   dev% = (A_interp - A_exp) / A_exp * 100
   * (mismo signo que compare_simulaciones.py: positivo si ACAB sobreestima).
   */
  function computeDeviationMetrics(expPoints, curveXs, curveYs) {
    const rows = expPoints.map(p => {
      const A_interp = linearInterpClamped(curveXs, curveYs, p.t);
      const dev_pct = (A_interp !== null && p.A !== 0)
        ? (A_interp - p.A) / p.A * 100
        : null;
      return { t: p.t, A_exp: p.A, A_interp, dev_pct };
    });
    const devs = rows.map(r => r.dev_pct).filter(d => d !== null && isFinite(d));
    const meanDevPct = devs.length ? devs.reduce((a, b) => a + b, 0) / devs.length : null;
    const maxAbsDevPct = devs.length ? Math.max(...devs.map(Math.abs)) : null;
    return { rows, meanDevPct, maxAbsDevPct };
  }

  // ───────────────────────────────────────────────────────────────────────
  // Series que entran en las tablas de desviación + selector de simulación
  // objetivo (Fase 6 del BACKLOG)
  // ───────────────────────────────────────────────────────────────────────

  /**
   * Series de referencia que generan tabla de desviación para un isótopo:
   * TODAS las cargadas para ese isótopo, sea su tipo `experimental` o
   * `computacional_referencia` (antes de la Fase 6 solo entraban las
   * experimentales). La distinción visual en la gráfica (huecos/rellenos) no
   * cambia: esto solo decide qué series generan tabla de métricas.
   */
  function seriesForMetrics(series, iso) {
    return (series || []).filter(s => s.isotopo === iso);
  }

  /**
   * Resuelve qué simulación usar como objetivo de interpolación para TODAS
   * las tablas de desviación (Fase 6 del BACKLOG: antes cada serie
   * interpolaba contra la simulación elegida al importarla). Si la
   * solicitada sigue entre las disponibles se respeta; si no (o no se pidió
   * ninguna todavía) se usa la primera — mismo comportamiento por defecto
   * que el `<select>` de importación sin tocar, que el navegador preselecciona
   * en su primera opción. `null` si no hay ninguna simulación disponible.
   */
  function resolveTargetSimName(simNames, requestedName) {
    if (!simNames || !simNames.length) return null;
    if (requestedName && simNames.indexOf(requestedName) !== -1) return requestedName;
    return simNames[0];
  }

  // ───────────────────────────────────────────────────────────────────────
  // F12 del BACKLOG: desfase de origen temporal al interpolar series de
  // referencia de fase 'enfriamiento'.
  //
  // Diagnóstico: antes de esta corrección, TODA serie de referencia se
  // trasladaba a un eje absoluto común (t_h = T_irr + t_local para
  // 'enfriamiento') para poder compararla contra una curva ACAB COMBINADA
  // (irradiación + enfriamiento concatenados, cuyo tramo de enfriamiento
  // también arranca en T_irr). Ambos lados usaban la MISMA convención
  // absoluta, pero cualquier discrepancia entre el T_irr usado al importar
  // la serie (el de la simulación de referencia elegida en el diálogo) y el
  // de la simulación objetivo de la tabla de métricas (elegible aparte,
  // Fase 6 del BACKLOG) desplazaba la interpolación en la diferencia de
  // T_irr — o el T_irr completo si se comparaba, como aquí, contra una
  // curva que ya no llevaba ese desplazamiento.
  //
  // Corrección: una serie declarada de fase 'enfriamiento' tiene su t en
  // tiempo DESDE EL FIN DE IRRADIACIÓN (EOI/RESTART) — igual origen que
  // sim.t_cool/datos_cool. Se compara DIRECTAMENTE contra la serie de
  // enfriamiento de la simulación objetivo, sin desplazamiento alguno; una
  // serie de fase 'irradiacion' ya comparte origen con sim.t_irr (t=0 =
  // inicio de irradiación), tampoco necesita desplazamiento. `curveForPhase`
  // centraliza esta elección — nunca combina fases.
  // ───────────────────────────────────────────────────────────────────────

  /**
   * Curva ACAB (Bq/cm³) de la MISMA fase/origen temporal que una serie de
   * referencia declarada con esa fase — nunca la curva combinada
   * irradiación+enfriamiento (ver nota F12 arriba).
   */
  function curveForPhase(sim, iso, fase) {
    if (fase === 'irradiacion') {
      return {
        xs: (sim && sim.t_irr) || [],
        ys: (sim && sim.datos_irr_Bq && sim.datos_irr_Bq[iso]) || [],
      };
    }
    return {
      xs: (sim && sim.t_cool) || [],
      ys: (sim && sim.datos_cool && sim.datos_cool[iso]) || [],
    };
  }

  /**
   * Método + origen temporal declarados en la cabecera de exportación (F12) —
   * claves puras (sin texto, i18n lo resuelve en app.js, igual que
   * pureza_time_utils.js/estadoBadgeClass): 'linear_clamped' es el único
   * método soportado hoy; el origen depende de la fase.
   */
  function interpolationOriginLabel(fase) {
    return {
      metodoKey: 'linear_clamped',
      origenKey: fase === 'irradiacion' ? 'irr_start' : 'eoi',
    };
  }

  return {
    TIME_UNIT_TO_H,
    parseActivityUnitLabel,
    parseTimeUnitLabel,
    convertTimeToHours,
    bqcm3FromUnit,
    parseCSV,
    guessColumnRoles,
    buildSeriesPoints,
    linearInterpClamped,
    computeDeviationMetrics,
    seriesForMetrics,
    resolveTargetSimName,
    curveForPhase,
    interpolationOriginLabel,
  };
});
