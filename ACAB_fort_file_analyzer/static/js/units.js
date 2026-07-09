/* ─────────────────────────────────────────────────────────────────────────
   units.js — Conversión de unidades de actividad (Fase 2 del runbook).

   Función pura, sin dependencias, reutilizable en el navegador (global
   `ACABUnits`) y en node (`require`) para tools/test_units.js.

   Modelo: los datos internos y el cache SIEMPRE están en Bq/cm³; la conversión
   a la unidad activa es un factor multiplicativo aplicado en el frontend,
   distinto por simulación (cada una con su propia densidad).

     Bq/cm³ (bqcm3)      factor 1                         (siempre disponible)
     MBq/g  (mbqg)       1 / (densidad_g_cm3 · 1e6)       (requiere densidad)
     MBq    (mbq_total)  volumen_cm3 / 1e6                (requiere volumen)
     mCi    (mci_total)  volumen_cm3 / 3.7e7              (requiere volumen)

   Un factor `null` significa "no convertible" (falta densidad/volumen o no es
   positivo): el llamante debe deshabilitar la opción o saltar esa serie.
   ───────────────────────────────────────────────────────────────────────── */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ACABUnits = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const BQ_PER_MCI = 3.7e7;   // 1 mCi = 37 MBq = 3.7e7 Bq

  // Qué necesita cada unidad: null (nada), 'density' o 'volume'.
  const UNITS = {
    bqcm3:     { requires: null },
    mbqg:      { requires: 'density' },
    mbq_total: { requires: 'volume' },
    mci_total: { requires: 'volume' },
  };

  function _pos(x) {
    const n = Number(x);
    return (isFinite(n) && n > 0) ? n : null;
  }

  /**
   * Factor multiplicativo para pasar de Bq/cm³ a `unit`.
   * opts: { density (g/cm³), volume (cm³) }. Devuelve null si no es computable.
   */
  function unitFactor(unit, opts) {
    opts = opts || {};
    switch (unit) {
      case 'bqcm3':
        return 1;
      case 'mbqg': {
        const d = _pos(opts.density);
        return d === null ? null : 1 / (d * 1e6);
      }
      case 'mbq_total': {
        const v = _pos(opts.volume);
        return v === null ? null : v / 1e6;
      }
      case 'mci_total': {
        const v = _pos(opts.volume);
        return v === null ? null : v / BQ_PER_MCI;
      }
      default:
        return null;
    }
  }

  /**
   * Convierte un valor en Bq/cm³ a `unit`. Devuelve null si no es convertible
   * o si la entrada no es un número finito (null/NaN → null).
   */
  function convertUnits(valueBqcm3, unit, opts) {
    const f = unitFactor(unit, opts);
    if (f === null) return null;
    if (valueBqcm3 === null || valueBqcm3 === undefined) return null;
    const v = Number(valueBqcm3);
    return isFinite(v) ? v * f : null;
  }

  function unitRequires(unit) {
    return (UNITS[unit] || {}).requires || null;
  }

  function isKnownUnit(unit) {
    return Object.prototype.hasOwnProperty.call(UNITS, unit);
  }

  return { UNITS, BQ_PER_MCI, unitFactor, convertUnits, unitRequires, isKnownUnit };
});
