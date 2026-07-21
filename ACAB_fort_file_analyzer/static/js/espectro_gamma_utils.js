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

  return {
    filtrarLineas,
    agruparPorNucleido,
    nucleidosOrdenados,
    topLineas,
    construirTrazasStick,
  };
});
