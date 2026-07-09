/* ─────────────────────────────────────────────────────────────────────────
   export_utils.js — Exportación CSV (Fase 3 del runbook).

   Utilidad pura `toCSV` sin dependencias, reutilizable en el navegador (global
   `ACABExport`) y en node (`require`) para tools/test_export.js. El helper
   `download` es solo de navegador (los tests node no lo tocan).

   Los datos ya están en el navegador; la exportación no añade dependencias.
   ───────────────────────────────────────────────────────────────────────── */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ACABExport = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Perfiles de formato. Las parejas (delimitador, decimal) están elegidas para
  // que NUNCA colisionen: con decimal ',' el separador es ';', y con decimal '.'
  // el separador es ','. Así los números nunca necesitan comillas.
  const PRESETS = {
    es:   { delimiter: ';', decimal: ',' },   // Excel es-ES
    intl: { delimiter: ',', decimal: '.' },
  };

  function _fmtNumber(n, decimal) {
    if (!isFinite(n)) return '';
    // Recorta el ruido de coma flotante a ~10 cifras significativas y conserva
    // una notación legible (String solo usa exponencial en extremos).
    let s = String(Number(n.toPrecision(10)));
    s = s.replace('e', 'E');            // Excel prefiere el exponente en mayúscula
    if (decimal === ',') s = s.replace('.', ',');
    return s;
  }

  function _fmtCell(c, delimiter, decimal) {
    if (c === null || c === undefined) return '';
    if (typeof c === 'number') return _fmtNumber(c, decimal);
    let s = String(c);
    // Entrecomillado RFC-4180 si la celda de texto contiene delimitador, comilla
    // o salto de línea.
    if (s.indexOf(delimiter) !== -1 || s.indexOf('"') !== -1 ||
        s.indexOf('\n') !== -1 || s.indexOf('\r') !== -1) {
      s = '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
  }

  /**
   * Construye una cadena CSV.
   *   rows:    array de arrays (celdas: number | string | null).
   *   headers: array opcional de títulos de columna.
   *   opts:    { delimiter, decimal } (por defecto ';' y ',').
   * Líneas terminadas en CRLF para máxima compatibilidad con hojas de cálculo.
   */
  function toCSV(rows, headers, opts) {
    opts = opts || {};
    const delimiter = opts.delimiter || ';';
    const decimal   = opts.decimal   || ',';
    const out = [];
    if (headers && headers.length) {
      out.push(headers.map(h => _fmtCell(h, delimiter, decimal)).join(delimiter));
    }
    (rows || []).forEach(row => {
      out.push((row || []).map(c => _fmtCell(c, delimiter, decimal)).join(delimiter));
    });
    return out.join('\r\n');
  }

  /** Slug seguro para nombres de fichero (MBq/g → MBq_g). */
  function slug(s) {
    return String(s).replace(/[^0-9A-Za-z]+/g, '_').replace(/^_+|_+$/g, '') || 'x';
  }

  function preset(name) { return PRESETS[name] || PRESETS.es; }

  /** Descarga de navegador (no la usan los tests node). */
  function download(filename, text) {
    if (typeof document === 'undefined') return;
    // BOM UTF-8 para que Excel muestre bien ³/²/µ/ñ.
    const BOM = String.fromCharCode(0xFEFF);
    const blob = new Blob([BOM + text], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return { PRESETS, toCSV, slug, preset, download };
});
