/* ─────────────────────────────────────────────────────────────────────────
   pureza_time_utils.js — Pestaña Informe Isótopo, gráfica P(t) de pureza
   radionucleídica durante el enfriamiento (F1, runbook_F1_pureza_temporal.md).

   Funciones puras (sin DOM) que dan forma a `informe.metricas[sim].pureza_serie`
   (ya calculado por el servidor: fort_analyzer.calcular_pureza_serie) para la
   gráfica y los textos de la pestaña. NO recalculan pureza ni t_cruce — solo
   preparan rangos de eje y mensajes a partir de lo que devuelve el backend.
   UMD puro, estilo units.js / export_utils.js / optim_utils.js: reutilizable
   en el navegador (global `ACABPurezaTime`) y en node (tools/test_pureza_time_utils.js).
   ───────────────────────────────────────────────────────────────────────── */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ACABPurezaTime = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * Rango [yLo, yHi] del eje P(t) [%]: P vive entre ~90 % y 100 %, así que un
   * 0–100 % aplasta la información (decisión del runbook F1 Fase 3). yHi
   * siempre 100.05 (margen para que el 100 % no quede pegado al borde); yLo
   * es min(90, la P mínima real de la serie − 0.5), redondeado hacia abajo,
   * para no recortar puntos por debajo de 90 % si los hay.
   *
   * *serieRows* = informe.metricas[sim].pureza_serie.serie (lista de
   * {t, P_pct}, P_pct puede ser null). Sin puntos numéricos → rango por
   * defecto [90, 100.05].
   */
  function purezaYRange(serieRows) {
    let minP = null;
    (serieRows || []).forEach(p => {
      if (p && p.P_pct != null && (minP === null || p.P_pct < minP)) minP = p.P_pct;
    });
    const yHi = 100.05;
    if (minP === null) return [90, yHi];
    const yLo = Math.min(90, Math.floor(minP - 0.5));
    return [yLo, yHi];
  }

  /** Clase de badge Bootstrap según el estado del cruce (ver calcular_pureza_serie). */
  function estadoBadgeClass(estado) {
    if (estado === 'no_alcanzado') return 'bg-secondary';
    if (estado === 'alcanzado_en_fin_irradiacion') return 'bg-success';
    if (estado === 'alcanzado_en_enfriamiento') return 'bg-success';
    return 'bg-secondary';
  }

  /** Fracción del pico como texto "NN.N %", o '—' si no hay valor. */
  function formatFraccionPico(frac) {
    return (frac != null && isFinite(frac)) ? (frac * 100).toFixed(1) + ' %' : '—';
  }

  return {
    purezaYRange,
    estadoBadgeClass,
    formatFraccionPico,
  };
});
