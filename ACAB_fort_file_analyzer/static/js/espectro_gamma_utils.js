/* ─────────────────────────────────────────────────────────────────────────
   espectro_gamma_utils.js — B1 del BACKLOG, pestaña "Espectro gamma".

   Puro (UMD, sin DOM): da forma al espectro ya calculado por el servidor
   (fort_analyzer.calcular_espectro_gamma, Fase 2) para la pestaña —
   filtrado por rango de energía / tasa mínima (las líneas débiles de
   I-132/I-135 ensucian la vista si no se recortan), agrupación por
   nucleido (para el stick plot coloreado por origen) y construcción de las
   trazas de Plotly. No recalcula ninguna tasa; solo combina/filtra/da
   forma a lo que ya viene en `espectro.lineas`.
   ───────────────────────────────────────────────────────────────────────── */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ACABEspectroGamma = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * Filtra líneas por rango de energía [eMinKeV, eMaxKeV] (ambos opcionales,
   * null = sin límite) y tasa mínima (opcional, null = sin umbral).
   */
  function filtrarLineas(lineas, opts) {
    opts = opts || {};
    const eMin = opts.eMinKeV != null ? opts.eMinKeV : null;
    const eMax = opts.eMaxKeV != null ? opts.eMaxKeV : null;
    const tasaMin = opts.tasaMin != null ? opts.tasaMin : null;
    return (lineas || []).filter(l => {
      if (eMin != null && l.E_keV < eMin) return false;
      if (eMax != null && l.E_keV > eMax) return false;
      if (tasaMin != null && l.tasa_fotones_s_cm3 < tasaMin) return false;
      return true;
    });
  }

  /** Agrupa líneas por nucleido de origen, claves ordenadas alfabéticamente. */
  function agruparPorNucleido(lineas) {
    const grupos = {};
    (lineas || []).forEach(l => {
      if (!grupos[l.nucleido]) grupos[l.nucleido] = [];
      grupos[l.nucleido].push(l);
    });
    return grupos;
  }

  /** Nombres de nucleido presentes, ordenados alfabéticamente (para colorear/leyenda). */
  function nucleidosOrdenados(lineas) {
    return Object.keys(agruparPorNucleido(lineas)).sort();
  }

  /** Las N líneas de mayor tasa, ordenadas descendentemente (tabla). */
  function topLineas(lineas, n) {
    return (lineas || [])
      .slice()
      .sort((a, b) => b.tasa_fotones_s_cm3 - a.tasa_fotones_s_cm3)
      .slice(0, n == null ? undefined : n);
  }

  /**
   * Trazas de Plotly para el espectro de palotes (stick plot): dos trazas
   * por nucleido — los palotes (mode 'lines', sin hover propio) y los
   * marcadores en la punta (mode 'markers', hover rico), unidas por
   * legendgroup para que el toggle de leyenda afecte a ambas a la vez.
   * *colorFor(nucleido, index)* decide el color (inyectado, sin DOM aquí).
   */
  function construirTrazasStick(lineas, colorFor) {
    const grupos = agruparPorNucleido(lineas);
    const nombres = Object.keys(grupos).sort();
    const trazas = [];
    nombres.forEach((nucleido, i) => {
      const filas = grupos[nucleido].slice().sort((a, b) => a.E_keV - b.E_keV);
      const color = colorFor(nucleido, i);
      const xSticks = [], ySticks = [];
      filas.forEach(l => {
        xSticks.push(l.E_keV, l.E_keV, null);
        ySticks.push(0, l.tasa_fotones_s_cm3, null);
      });
      trazas.push({
        x: xSticks, y: ySticks, name: nucleido, mode: 'lines', type: 'scatter',
        line: { color, width: 1.5 }, legendgroup: nucleido, hoverinfo: 'skip',
        showlegend: true,
      });
      trazas.push({
        x: filas.map(l => l.E_keV), y: filas.map(l => l.tasa_fotones_s_cm3),
        name: nucleido, mode: 'markers', type: 'scatter',
        marker: { color, size: 6 }, legendgroup: nucleido, showlegend: false,
        text: filas.map(l => l.intensidad_pct),
        hovertemplate: 'E = %{x:.2f} keV<br>tasa = %{y:.3e}<br>I = %{text:.3g} %'
          + '<extra>' + nucleido + '</extra>',
      });
    });
    return trazas;
  }

  /**
   * B1b del BACKLOG — umbral de tasa mínima POR DEFECTO para que la vista
   * inicial sea legible sin tocar ningún filtro: relativo al máximo del
   * INSTANTE actual (no un valor absoluto fijo, que no tendría sentido
   * entre instantes/simulaciones con actividades muy distintas). 0 si no
   * hay líneas o el máximo es 0 (no hay nada que recortar).
   */
  function umbralPorDefecto(lineas, factor) {
    factor = factor == null ? 1e6 : factor;
    if (!lineas || !lineas.length) return 0;
    const max = lineas.reduce((m, l) => Math.max(m, l.tasa_fotones_s_cm3), 0);
    return max > 0 ? max / factor : 0;
  }

  /** Tasa total (suma) por nucleido, para decidir qué entra en la leyenda. */
  function totalTasaPorNucleido(lineas) {
    const totales = {};
    (lineas || []).forEach(l => {
      totales[l.nucleido] = (totales[l.nucleido] || 0) + l.tasa_fotones_s_cm3;
    });
    return totales;
  }

  /** Los N nucleidos de mayor tasa TOTAL (suma de sus líneas), descendente. */
  function topNNucleidos(lineas, n) {
    const totales = totalTasaPorNucleido(lineas);
    return Object.keys(totales)
      .sort((a, b) => totales[b] - totales[a])
      .slice(0, n == null ? undefined : n);
  }

  /**
   * Como `construirTrazasStick`, pero con la leyenda acotada a los N
   * nucleidos de mayor tasa total (criterio de U4: nunca volcado completo);
   * el resto se agrupa visualmente en una única traza "otros" con color
   * neutro — el hover de cada punto sigue mostrando su nucleido real
   * (`customdata`), aunque comparta color/leyenda con los demás agrupados.
   * *opts.topN* (por defecto 8), *opts.colorOtros* (por defecto gris),
   * *opts.otrosLabel* (por defecto 'otros' — el caller pasa la traducción).
   */
  function construirTrazasStickTopN(lineas, colorFor, opts) {
    opts = opts || {};
    const topN = opts.topN == null ? 8 : opts.topN;
    const colorOtros = opts.colorOtros || '#9e9e9e';
    const otrosLabel = opts.otrosLabel || 'otros';
    const OTROS = '__otros__';

    const top = new Set(topNNucleidos(lineas, topN));
    const grupos = {};
    (lineas || []).forEach(l => {
      const grupo = top.has(l.nucleido) ? l.nucleido : OTROS;
      if (!grupos[grupo]) grupos[grupo] = [];
      grupos[grupo].push(l);
    });

    const nombresTop = Object.keys(grupos).filter(g => g !== OTROS).sort();
    const nombres = grupos[OTROS] ? nombresTop.concat([OTROS]) : nombresTop;

    const trazas = [];
    nombres.forEach((grupo, i) => {
      const esOtros = grupo === OTROS;
      const filas = grupos[grupo].slice().sort((a, b) => a.E_keV - b.E_keV);
      const color = esOtros ? colorOtros : colorFor(grupo, i);
      const nombreLeyenda = esOtros ? otrosLabel : grupo;
      const xSticks = [], ySticks = [];
      filas.forEach(l => {
        xSticks.push(l.E_keV, l.E_keV, null);
        ySticks.push(0, l.tasa_fotones_s_cm3, null);
      });
      trazas.push({
        x: xSticks, y: ySticks, name: nombreLeyenda, mode: 'lines', type: 'scatter',
        line: { color, width: 1.5 }, legendgroup: grupo, hoverinfo: 'skip',
        showlegend: true,
      });
      trazas.push({
        x: filas.map(l => l.E_keV), y: filas.map(l => l.tasa_fotones_s_cm3),
        name: nombreLeyenda, mode: 'markers', type: 'scatter',
        marker: { color, size: 6 }, legendgroup: grupo, showlegend: false,
        customdata: filas.map(l => [l.nucleido, l.intensidad_pct]),
        hovertemplate: 'E = %{x:.2f} keV<br>tasa = %{y:.3e}<br>I = %{customdata[1]:.3g} %'
          + '<extra>%{customdata[0]}</extra>',
      });
    });
    return trazas;
  }

  return {
    filtrarLineas,
    agruparPorNucleido,
    nucleidosOrdenados,
    topLineas,
    construirTrazasStick,
    umbralPorDefecto,
    totalTasaPorNucleido,
    topNNucleidos,
    construirTrazasStickTopN,
  };
});
