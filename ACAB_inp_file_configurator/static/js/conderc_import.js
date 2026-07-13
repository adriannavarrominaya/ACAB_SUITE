/* conderc_import.js — Funciones PURAS (sin DOM) para importar espectros en
 * formato CONDERC (OIEA, https://nds.iaea.org/conderc/spectra) en el barrido
 * espectral (Fase P2 del RUNBOOK_barrido_espectral.md). Testeable con node:
 *   node tools/test_conderc_import.js
 *
 * Formato CONDERC (clavado con el fixture 112_MURR-G1.txt): cabecera
 * "GROUP UPPER LOWER LETHARGY DATA DATA/LETHARGY"; una fila por grupo;
 * energías en eV; línea final "TOTAL <valor>" como checksum de Σ(DATA).
 *
 * Convenios de dominio (RUNBOOK_barrido_espectral.md):
 *   D4 — Import = transcripción, sin rebinning. NGROUP = ±N (signo
 *        autodetectado de la monotonía de las fronteras), CX = N+1 fronteras,
 *        FT = columna DATA. CX del COLL.inp está en MeV (P0.2, verificado);
 *        CONDERC en eV → el import convierte las fronteras ×1e-6 (única
 *        transformación; los FT no se convierten).
 *   D8 — Índices espectrales: fracción térmica (E<0.625 eV), epitérmica
 *        (0.625 eV–0.1 MeV) y rápida (>0.1 MeV), con reparto plano-por-
 *        letargia en el grupo que contiene la frontera.
 */
'use strict';

const THERMAL_EV = 0.625;   // límite térmico/epitérmico
const FAST_EV = 1.0e5;      // límite epitérmico/rápido (0.1 MeV)
const EV_TO_MEV = 1e-6;

function _parseNum(tok, line) {
  const n = Number(tok);
  if (!Number.isFinite(n)) throw new Error(`Valor no numérico ('${tok}') en la fila: '${line}'`);
  return n;
}

/**
 * Parsea un fichero de espectro en formato CONDERC.
 *
 * @param {string} text  contenido íntegro del fichero
 * @returns {{n:number, boundaries_eV:number[], data:number[], total:number,
 *            orden:'creciente'|'decreciente'}}
 *   boundaries_eV tiene n+1 valores (UPPER del primer grupo + LOWER de todos).
 * @throws {Error} si faltan columnas, hay tokens no numéricos, falta la línea
 *   TOTAL, el checksum no cuadra (tolerancia relativa 1e-3) o las fronteras
 *   no son monótonas.
 */
function parseConderc(text) {
  const lines = String(text == null ? '' : text).split(/\r?\n/);
  const rows = [];
  let total = null;

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (/^GROUP\b/i.test(line)) continue;
    if (/^TOTAL\b/i.test(line)) {
      const m = line.match(/^TOTAL\s+(\S+)/i);
      if (!m) throw new Error(`Línea TOTAL sin valor: '${line}'`);
      total = _parseNum(m[1], line);
      continue;
    }
    const parts = line.split(/\s+/);
    if (parts.length < 5)
      throw new Error(`Fila de espectro CONDERC con columnas truncadas: '${line}' (se esperan ≥5 columnas).`);
    rows.push({
      upper: _parseNum(parts[1], line),
      lower: _parseNum(parts[2], line),
      data: _parseNum(parts[4], line),
    });
  }

  if (rows.length === 0) throw new Error('El fichero no contiene filas de datos de espectro.');
  if (total === null) throw new Error("Falta la línea 'TOTAL' (checksum) al final del fichero.");

  const n = rows.length;
  const boundaries_eV = [rows[0].upper, ...rows.map(r => r.lower)];
  const data = rows.map(r => r.data);

  const sum = data.reduce((a, b) => a + b, 0);
  const relErr = total !== 0 ? Math.abs(sum - total) / Math.abs(total) : Math.abs(sum);
  if (relErr > 1e-3)
    throw new Error(`Checksum fallido: Σ(DATA)=${sum} ≠ TOTAL=${total} (error relativo ${relErr.toExponential(3)}).`);

  let increasing = true, decreasing = true;
  for (let i = 1; i < boundaries_eV.length; i++) {
    if (boundaries_eV[i] > boundaries_eV[i - 1]) decreasing = false;
    if (boundaries_eV[i] < boundaries_eV[i - 1]) increasing = false;
  }
  if (!increasing && !decreasing)
    throw new Error('Las fronteras de energía no son monótonas (ni crecientes ni decrecientes).');

  return { n, boundaries_eV, data, total, orden: decreasing ? 'decreciente' : 'creciente' };
}

/**
 * Calcula las fracciones espectrales térmica/epitérmica/rápida (D8) a partir
 * de las fronteras de energía (eV, cualquier orden) y la columna DATA.
 * Reparte por letargia (u = ln(E)) la porción del grupo que cae a cada lado
 * de un umbral cuando este cae dentro del grupo.
 *
 * @param {number[]} boundaries  n+1 fronteras de energía (eV)
 * @param {number[]} data        n valores DATA
 * @returns {{frac_termica:number, frac_epitermica:number, frac_rapida:number}}
 */
function spectralIndices(boundaries, data) {
  const n = data.length;
  if (!boundaries || boundaries.length !== n + 1)
    throw new Error(`spectralIndices: se esperan ${n + 1} fronteras para ${n} grupos `
      + `(recibidas ${boundaries ? boundaries.length : 0}).`);

  let thermal = 0, epithermal = 0, fast = 0;
  for (let i = 0; i < n; i++) {
    const eHi = Math.max(boundaries[i], boundaries[i + 1]);
    const eLo = Math.min(boundaries[i], boundaries[i + 1]);
    const d = data[i];

    if (!(eHi > eLo) || eLo <= 0) {
      // Grupo degenerado (ancho nulo o frontera no positiva): sin letargia
      // definida; se asigna entero según el extremo superior.
      if (eHi <= THERMAL_EV) thermal += d;
      else if (eHi <= FAST_EV) epithermal += d;
      else fast += d;
      continue;
    }

    const totalLeth = Math.log(eHi / eLo);
    const cuts = [eLo, eHi];
    for (const T of [THERMAL_EV, FAST_EV])
      if (T > eLo && T < eHi) cuts.push(T);
    cuts.sort((a, b) => a - b);

    for (let k = 0; k < cuts.length - 1; k++) {
      const lo = cuts[k], hi = cuts[k + 1];
      const frac = totalLeth > 0 ? Math.log(hi / lo) / totalLeth : 1 / (cuts.length - 1);
      const share = d * frac;
      const mid = Math.sqrt(lo * hi);
      if (mid < THERMAL_EV) thermal += share;
      else if (mid < FAST_EV) epithermal += share;
      else fast += share;
    }
  }

  const sum = thermal + epithermal + fast;
  if (!(sum > 0)) throw new Error('spectralIndices: la suma de DATA es nula; no se pueden calcular fracciones.');
  return {
    frac_termica: thermal / sum,
    frac_epitermica: epithermal / sum,
    frac_rapida: fast / sum,
  };
}

/**
 * Construye el patch de barrido espectral (D9) a partir de un espectro
 * CONDERC ya parseado: NGROUP con signo (según orden), CX en las unidades
 * del COLL.inp base y FT.
 *
 * @param {{n:number, boundaries_eV:number[], data:number[], orden:string}} parsed
 * @param {{cxUnit?:'eV'|'MeV'}} [collBase]  unidades de CX del COLL.inp base
 *   (D4/P0.2: MeV por defecto).
 * @returns {{ngroup:number, cx:number[], ft:number[]}}
 */
function buildSpectrumPatch(parsed, collBase) {
  const cxUnit = (collBase && collBase.cxUnit) || 'MeV';
  const sign = parsed.orden === 'decreciente' ? -1 : 1;
  const ngroup = sign * parsed.n;
  const cx = cxUnit === 'MeV'
    ? parsed.boundaries_eV.map(e => e * EV_TO_MEV)
    : parsed.boundaries_eV.slice();
  return { ngroup, cx, ft: parsed.data.slice() };
}

/* Export para node (tests); en el navegador quedan como globales. */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    THERMAL_EV, FAST_EV, parseConderc, spectralIndices, buildSpectrumPatch,
  };
}
