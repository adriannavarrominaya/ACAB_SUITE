/* test_units.js — Tests de la conversión pura de unidades (Fase 2 del runbook).

   Ejercita static/js/units.js con node, sin framework (estilo de la suite).

   Uso:
       node tools/test_units.js

   Devuelve código de salida 0 si todo pasa, 1 si algún test falla.

   Nota: el harness local del repo es Python y esta máquina puede no tener node;
   el criterio de aceptación numérico (pico I131 en MBq/g = valor legacy) está
   además cubierto en tools/test_fort_analyzer.py, que sí corre siempre.
*/
'use strict';

const path = require('path');
const U = require(path.join(__dirname, '..', 'static', 'js', 'units.js'));

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

// Densidad y A_pico oro de la ref_sim (compare_simulaciones.py legacy).
const DENS = 0.12317;      // g/cm³
const A_PICO = 16500.0;    // Bq/cm³

section('unitFactor — disponibilidad');
check(U.unitFactor('bqcm3') === 1, 'bqcm3 → factor 1 (siempre)');
check(U.unitFactor('mbqg', {}) === null, 'mbqg sin densidad → null (opción deshabilitada)');
check(U.unitFactor('mbqg', { density: 0 }) === null, 'mbqg con densidad 0 → null');
check(U.unitFactor('mbq_total', {}) === null, 'mbq_total sin volumen → null');
check(U.unitFactor('mci_total', { volume: -1 }) === null, 'mci_total con volumen negativo → null');
check(U.unitFactor('desconocida') === null, 'unidad desconocida → null');

section('convertUnits — Bq/cm³ (identidad)');
check(U.convertUnits(A_PICO, 'bqcm3') === A_PICO, 'Bq/cm³ no altera el valor');
check(U.convertUnits(0, 'bqcm3') === 0, 'el 0 se conserva');
check(U.convertUnits(null, 'bqcm3') === null, 'entrada null → null');

section('convertUnits — MBq/g (criterio de aceptación legacy)');
// MBq/g = Bq/cm³ / (densidad · 1e6) = 16500 / (0.12317·1e6) ≈ 0.13396
close(U.convertUnits(A_PICO, 'mbqg', { density: DENS }), A_PICO / (DENS * 1e6),
      'pico I131 = 0.13396 MBq/g');
check(U.convertUnits(A_PICO, 'mbqg', {}) === null, 'sim sin densidad → null (se salta la serie)');

section('convertUnits — actividad total');
// MBq total = Bq/cm³ · V / 1e6 ; con V=1 cm³ (VOLUME OF ZONE de la ref_sim)
close(U.convertUnits(A_PICO, 'mbq_total', { volume: 1 }), A_PICO / 1e6,
      'pico I131 = 0.0165 MBq (V=1 cm³)');
// mCi total = Bq/cm³ · V / 3.7e7
close(U.convertUnits(A_PICO, 'mci_total', { volume: 1 }), A_PICO / 3.7e7,
      'pico I131 = 4.459e-4 mCi (V=1 cm³)');
// Escala lineal con el volumen.
close(U.convertUnits(A_PICO, 'mbq_total', { volume: 10 }),
      U.convertUnits(A_PICO, 'mbq_total', { volume: 1 }) * 10,
      'MBq total escala lineal con el volumen');

console.log('\n' + '-'.repeat(50));
console.log('Resultado: ' + passed + ' pasados, ' + failed + ' fallidos');
process.exit(failed === 0 ? 0 : 1);
