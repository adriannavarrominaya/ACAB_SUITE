/* Tests de aceptación (node tools/test_conderc_import.js) para
 * conderc_import.js (Fase P2 del RUNBOOK_barrido_espectral.md).
 *
 *   parseConderc      — caso oro 112_MURR-G1.txt (112 grupos, decreciente,
 *                        checksum), fixtures extremos (6 y 621 grupos),
 *                        y casos de error: TOTAL descuadrado, columnas
 *                        truncadas, sin línea TOTAL.
 *   spectralIndices   — fracción térmica del MURR-G1 calculada una vez y
 *                        congelada como oro (D8, reparto plano-por-letargia).
 *   buildSpectrumPatch — signo de NGROUP y conversión eV→MeV de CX (D4/D9).
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { THERMAL_EV, parseConderc, spectralIndices, buildSpectrumPatch } =
  require('../static/js/conderc_import.js');

const FIXDIR = path.join(__dirname, '../tests/fixtures/spectra');
const readFixture = name => fs.readFileSync(path.join(FIXDIR, name), 'utf-8');

let fails = 0;
function check(name, cond, detail = '') {
  console.log(`${cond ? 'OK   ' : 'FALLO'} ${name}${detail ? '  — ' + detail : ''}`);
  if (!cond) fails++;
}
function relDiff(a, b) { return Math.abs(a - b) / Math.abs(b); }

// ── parseConderc: caso oro 112_MURR-G1.txt ──────────────────────────────────
const murrText = readFixture('112_MURR-G1.txt');
const murr = parseConderc(murrText);
check('MURR-G1: n=112', murr.n === 112);
check('MURR-G1: 113 fronteras', murr.boundaries_eV.length === 113);
check('MURR-G1: orden decreciente', murr.orden === 'decreciente');
check('MURR-G1: primera frontera = 2.0000E+07 eV', relDiff(murr.boundaries_eV[0], 2.0000e7) < 1e-9);
check('MURR-G1: última frontera = 1.0500E-03 eV', relDiff(murr.boundaries_eV[112], 1.0500e-3) < 1e-9);
check('MURR-G1: TOTAL = 1.4634E+14', relDiff(murr.total, 1.4634e14) < 1e-9);
check('MURR-G1: Σ(DATA) ≈ TOTAL (checksum)', relDiff(murr.data.reduce((a, b) => a + b, 0), murr.total) < 1e-3);

// ── spectralIndices: fracción térmica del MURR-G1 (oro, congelada) ─────────
// Calculada una vez con esta misma implementación (reparto plano-por-letargia,
// D8) y congelada como valor de referencia; ver docstring de spectralIndices.
// MURR es un reactor de investigación fuertemente termalizado (piscina,
// moderado por agua ligera): frac_termica dominante es el resultado esperado.
const murrIdx = spectralIndices(murr.boundaries_eV, murr.data);
// Fracción térmica (E < 0.625 eV) del MURR-G1, reparto plano-por-letargia en el
// grupo que contiene la frontera. Verificado independientemente el 2026-07-13
// (implementación separada, coincidencia a 10 cifras).
const MURR_FRAC_TERMICA_GOLD = 0.6441751228;
check('MURR-G1: fracciones suman 1',
  Math.abs(murrIdx.frac_termica + murrIdx.frac_epitermica + murrIdx.frac_rapida - 1) < 1e-9);
check('MURR-G1: frac_termica ≈ oro congelado', relDiff(murrIdx.frac_termica, MURR_FRAC_TERMICA_GOLD) < 1e-6,
  murrIdx.frac_termica.toFixed(10));
check('MURR-G1: frac_termica dominante (reactor termalizado)', murrIdx.frac_termica > 0.5, murrIdx.frac_termica.toFixed(6));

// ── spectralIndices: caso sintético con umbral EXACTO en una frontera ───────
// 2 grupos: [0.625eV,1eV] (íntegramente epitérmico, por encima del umbral
// térmico) y [0.01eV,0.625eV] (íntegramente térmico) con DATA iguales.
const idx2 = spectralIndices([1, 0.625, 0.01], [5, 5]);
check('spectralIndices: umbral exacto en frontera → reparto 50/50 por grupo',
  relDiff(idx2.frac_termica, 0.5) < 1e-9 && relDiff(idx2.frac_epitermica, 0.5) < 1e-9,
  JSON.stringify(idx2));

// ── spectralIndices: grupo que atraviesa el umbral térmico (letargia) ──────
// Grupo único [10 eV, 0.0625 eV] con umbral 0.625 eV dentro: fracción de
// letargia por debajo de 0.625 eV = ln(0.625/0.0625)/ln(10/0.0625).
const lo = 0.0625, hi = 10, T = THERMAL_EV;
const fracEsperada = Math.log(T / lo) / Math.log(hi / lo);
const idx3 = spectralIndices([hi, lo], [1]);
check('spectralIndices: reparto por letargia dentro de un grupo',
  relDiff(idx3.frac_termica, fracEsperada) < 1e-9,
  `esperado=${fracEsperada.toFixed(6)} obtenido=${idx3.frac_termica.toFixed(6)}`);

// ── spectralIndices: dimensiones incoherentes ───────────────────────────────
let threw = false;
try { spectralIndices([1, 2], [1, 2, 3]); } catch (e) { threw = true; }
check('spectralIndices rechaza boundaries.length ≠ n+1', threw);

// ── parseConderc: fixtures extremos (D5, control de conteo de grupos) ──────
const sneg = parseConderc(readFixture('6_SNEG-2.txt'));
check('SNEG-2: n=6 (extremo grueso)', sneg.n === 6);
check('SNEG-2: orden decreciente', sneg.orden === 'decreciente');
check('SNEG-2: TOTAL = 1.0 (normalizado)', relDiff(sneg.total, 1.0) < 1e-9);

const br2 = parseConderc(readFixture('621_SCK-BR2.txt'));
check('SCK-BR2: n=621 (extremo fino)', br2.n === 621);
check('SCK-BR2: orden decreciente', br2.orden === 'decreciente');

// ── parseConderc: casos de error ────────────────────────────────────────────
threw = false;
try {
  parseConderc(murrText.replace(/TOTAL(\s+)[\d.eE+-]+/, 'TOTAL$19.9999E+20'));
} catch (e) { threw = /Checksum/.test(e.message); }
check('parseConderc rechaza TOTAL descuadrado', threw, threw ? '' : 'no lanzó o mensaje inesperado');

threw = false;
try {
  parseConderc('  GROUP      UPPER       LOWER         LETHARGY         DATA        DATA/LETHARGY\n\n'
    + '     1     2.0000E+07  1.9300E+07     3.5627E-02\n'  // fila truncada (solo 4 columnas)
    + '  TOTAL                                              0.0\n');
} catch (e) { threw = /columnas truncadas/.test(e.message); }
check('parseConderc rechaza filas con columnas truncadas', threw);

threw = false;
try {
  parseConderc('  GROUP      UPPER       LOWER         LETHARGY         DATA        DATA/LETHARGY\n\n'
    + '     1     2.0000E+07  1.9300E+07     3.5627E-02     1.0000E+00     1.0000E+00\n');
} catch (e) { threw = /TOTAL/.test(e.message); }
check('parseConderc rechaza fichero sin línea TOTAL', threw);

threw = false;
try { parseConderc(''); } catch (e) { threw = /no contiene filas/.test(e.message); }
check('parseConderc rechaza fichero vacío', threw);

// ── buildSpectrumPatch ───────────────────────────────────────────────────────
const patchMurr = buildSpectrumPatch(murr, { cxUnit: 'MeV' });
check('buildSpectrumPatch: NGROUP negativo (orden decreciente)', patchMurr.ngroup === -112);
check('buildSpectrumPatch: CX tiene n+1 valores', patchMurr.cx.length === 113);
check('buildSpectrumPatch: CX convertido eV→MeV (primera frontera = 20 MeV)',
  relDiff(patchMurr.cx[0], 20) < 1e-9, patchMurr.cx[0]);
check('buildSpectrumPatch: FT = columna DATA (sin conversión)',
  relDiff(patchMurr.ft[0], murr.data[0]) < 1e-12 || (patchMurr.ft[0] === 0 && murr.data[0] === 0));

const parsedCreciente = { n: 3, boundaries_eV: [1, 10, 100, 1000], data: [1, 2, 3], orden: 'creciente' };
const patchCreciente = buildSpectrumPatch(parsedCreciente, { cxUnit: 'eV' });
check('buildSpectrumPatch: NGROUP positivo (orden creciente)', patchCreciente.ngroup === 3);
check('buildSpectrumPatch: cxUnit=eV no convierte', patchCreciente.cx[1] === 10);

console.log(fails === 0 ? '\nTODOS LOS TESTS OK' : `\n${fails} TESTS FALLARON`);
process.exit(fails === 0 ? 0 : 1);
