/* test_reference_data.js — Tests del parser/interpolación de datos de
   referencia (Fase 4 del runbook).

   Ejercita static/js/reference_data.js (y su dependencia units.js) con node,
   sin framework (estilo de la suite).

   Uso:
       node tools/test_reference_data.js

   Devuelve código de salida 0 si todo pasa, 1 si algún test falla.

   Nota: el harness local del repo es Python y esta máquina puede no tener
   node; el criterio de aceptación numérico (desviaciones equivalentes al
   script legacy sobre la ref_sim) está además cubierto en
   tools/test_reference_data.py, que sí corre siempre. Ver memoria
   [[no-node-runtime]].
*/
'use strict';

const fs = require('fs');
const path = require('path');
const R = require(path.join(__dirname, '..', 'static', 'js', 'reference_data.js'));

let passed = 0, failed = 0;
function ok(m)   { passed++; console.log('  [PASS] ' + m); }
function fail(m) { failed++; console.log('  [FAIL] ' + m); }
function check(cond, m) { cond ? ok(m) : fail(m); }
function close(got, exp, m, rtol) {
  rtol = rtol === undefined ? 1e-3 : rtol;
  if (got === null || got === undefined || !isFinite(got)) return fail(m + ': valor no numérico ' + got);
  const rel = Math.abs(got - exp) / (Math.abs(exp) || 1);
  rel <= rtol ? ok(m + ' (=' + got + ')') : fail(m + ': obtenido ' + got + ', esperado ' + exp);
}
function section(n) { console.log('\n== ' + n + ' =='); }

const FIXTURES = path.join(__dirname, '..', 'tests', 'fixtures', 'experimental');

// ─────────────────────────────────────────────────────────────────────────
section('parseCSV — ejemplo de la especificación (docs/SPEC_csv_datos_referencia.md)');
const SPEC_EXAMPLE = [
  '# tipo: experimental',
  '# descripcion: Fig. 6 - Actividad I-131 medida, cuarto experimento (MURR, TeO2)',
  '# fase: enfriamiento',
  '# isotopo: I131',
  '# unidad_t: h',
  '# unidad_A: MBq/g',
  '# fuente: digitalizado del paper de referencia',
  't;A;A_err',
  '14,5975;7728,904;120,5',
  '16,2340;7866,102;118,2',
].join('\n');

const specParsed = R.parseCSV(SPEC_EXAMPLE);
check(specParsed.meta.tipo === 'experimental', 'meta.tipo = experimental');
check(specParsed.meta.fase === 'enfriamiento', 'meta.fase = enfriamiento');
check(specParsed.meta.isotopo === 'I131', 'meta.isotopo = I131');
check(specParsed.meta.unidad_t === 'h', 'meta.unidad_t = h');
check(specParsed.meta.unidad_a === 'MBq/g', 'meta.unidad_a = MBq/g (clave normalizada a minúsculas)');
check(specParsed.delimiter === ';', 'delimitador autodetectado = ;');
check(specParsed.decimal === ',', 'decimal autodetectado = , (con delimitador ;)');
check(Array.isArray(specParsed.headers) && specParsed.headers[0] === 't', 'cabecera t;A;A_err detectada y separada');
check(specParsed.rows.length === 2, '2 filas de datos (obtenido ' + specParsed.rows.length + ')');
close(specParsed.rows[0][0], 14.5975, 'fila 1, t = 14.5975 (decimal coma parseado)');
close(specParsed.rows[0][1], 7728.904, 'fila 1, A = 7728.904');
close(specParsed.rows[0][2], 120.5, 'fila 1, A_err = 120.5');

const roles = R.guessColumnRoles(specParsed.rows);
check(roles[0] === 't', 'guessColumnRoles: columna 0 → t (monótona)');
check(roles[1] === 'A', 'guessColumnRoles: columna 1 → A');
check(roles[2] === 'A_err', 'guessColumnRoles: columna 2 → A_err');

// ─────────────────────────────────────────────────────────────────────────
section('guessColumnRoles — columnas invertidas (A antes que t)');
// Caso realista de digitalización invertida: col0 = actividad (subida y bajada,
// como el pico de I131 tras el pulso: crece y luego decae → NO monótona),
// col1 = tiempo (siempre monótono). El pico está en A, no en t.
const swappedRows = [[5, 1], [20, 2], [15, 3], [8, 4]];
const swappedRoles = R.guessColumnRoles(swappedRows);
check(swappedRoles[1] === 't', 'columna estrictamente monótona (col 1, tiempo) detectada como t pese a venir en 2ª posición');
check(swappedRoles[0] === 'A', 'columna 0 (actividad, con subida y bajada) asignada a A');

// ─────────────────────────────────────────────────────────────────────────
section('buildSeriesPoints — orden por t y filtrado de filas inválidas');
const rowsUnsorted = [[2, 20], [1, 10], [NaN, 99], [3, 30]];
const points = R.buildSeriesPoints(rowsUnsorted, { t: 0, A: 1, A_err: null });
check(points.length === 3, 'la fila con t=NaN se descarta (obtenido ' + points.length + ')');
check(points[0].t === 1 && points[1].t === 2 && points[2].t === 3, 'puntos ordenados ascendentemente por t');

// ─────────────────────────────────────────────────────────────────────────
section('parseActivityUnitLabel / parseTimeUnitLabel');
check(R.parseActivityUnitLabel('MBq/g') === 'mbqg', "'MBq/g' → 'mbqg'");
check(R.parseActivityUnitLabel('Bq/cm3') === 'bqcm3', "'Bq/cm3' → 'bqcm3'");
check(R.parseActivityUnitLabel('mCi') === 'mci_total', "'mCi' → 'mci_total'");
check(R.parseActivityUnitLabel('MBq') === 'mbq_total', "'MBq' → 'mbq_total'");
check(R.parseActivityUnitLabel('rarunit') === null, 'unidad desconocida → null');
check(R.parseTimeUnitLabel('h') === 'h', "'h' → 'h'");
check(R.parseTimeUnitLabel('d') === 'd', "'d' → 'd'");
check(R.parseTimeUnitLabel('semanas') === null, 'unidad de tiempo desconocida → null');
close(R.convertTimeToHours(60, 'min'), 1, '60 min = 1 h');
close(R.convertTimeToHours(1, 'd'), 24, '1 d = 24 h');

// ─────────────────────────────────────────────────────────────────────────
section('bqcm3FromUnit — inversa de ACABUnits.unitFactor (densidad de la ref_sim)');
const DENS = 0.12317;
// MBq/g → Bq/cm³: valor · densidad · 1e6 (inversa de 1/(densidad·1e6))
close(R.bqcm3FromUnit(0.13396119184866445, 'mbqg', { density: DENS }), 16500.0,
      'pico I131 en MBq/g invertido reproduce 16500 Bq/cm³');
check(R.bqcm3FromUnit(1, 'mbqg', {}) === null, 'sin densidad → null (no importable)');

// ─────────────────────────────────────────────────────────────────────────
section('linearInterpClamped — recorte a los extremos (paridad con numpy.interp)');
const xs = [1, 2, 3], ys = [10, 20, 30];
check(R.linearInterpClamped(xs, ys, 0) === 10, 'x antes del rango → clamp al primer punto');
check(R.linearInterpClamped(xs, ys, 4) === 30, 'x después del rango → clamp al último punto');
close(R.linearInterpClamped(xs, ys, 1.5), 15, 'interpolación lineal en el punto medio');

// ─────────────────────────────────────────────────────────────────────────
section('Criterio de aceptación Fase 4 — 11 puntos legacy de compare_simulaciones.py');
// Mismos arrays embebidos en compare_simulaciones.py (datos experimental y
// computacional de referencia de la simulación v.5 "info thesis" == ref_sim).
const exp_t = [0.26951859, 0.4775716, 0.71976523, 0.92890383, 1.12000271,
               1.56890423, 1.89931071, 2.08787231, 2.26834455, 2.49911054, 2.67779639];
const exp_A = [0.05191691, 0.07064688, 0.08823739, 0.09443323, 0.10597033,
               0.11216617, 0.115727, 0.11679525, 0.11836202, 0.11950148, 0.12042730];
const comp_t = [0.2709231889, 0.4804614151, 0.7204327496, 0.9315613704, 1.121084107,
                1.571873455, 1.902275268, 2.091705142, 2.27125429, 2.50196291, 2.682403319];
const comp_A = [0.04836326, 0.07389830, 0.09358229, 0.10541931, 0.11311902,
                0.12387904, 0.12793620, 0.12942901, 0.13049404, 0.13105821, 0.13169515];

const expPoints = exp_t.map((t, i) => ({ t, A: exp_A[i] }));
const metrics = R.computeDeviationMetrics(expPoints, comp_t, comp_A);
// Valores oráculo calculados con numpy (ver tools/test_reference_data.py).
close(metrics.meanDevPct, 7.487912045806161, 'sesgo medio = 7.49 % (oráculo numpy)', 1e-6);
close(metrics.maxAbsDevPct, 11.475921998900839, 'desviación máxima = 11.48 % (oráculo numpy)', 1e-6);

console.log('\n' + '-'.repeat(50));
console.log('Resultado: ' + passed + ' pasados, ' + failed + ' fallidos');
process.exit(failed === 0 ? 0 : 1);
