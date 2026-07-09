/* test_export.js — Tests de la exportación CSV pura (Fase 3 del runbook).

   Ejercita static/js/export_utils.js con node, sin framework.

   Uso:
       node tools/test_export.js

   Devuelve código de salida 0 si todo pasa, 1 si algún test falla.

   Nota: el harness local del repo es Python y esta máquina puede no tener node
   (ni motor JS embebido). Esta lógica es solo-frontend, así que no tiene un
   camino equivalente en Python; su verificación de ejecución vive aquí.
*/
'use strict';

const path = require('path');
const X = require(path.join(__dirname, '..', 'static', 'js', 'export_utils.js'));

let passed = 0, failed = 0;
function ok(m)   { passed++; console.log('  [PASS] ' + m); }
function fail(m) { failed++; console.log('  [FAIL] ' + m); }
function eq(got, exp, m) {
  got === exp ? ok(m) : fail(m + '\n        obtenido: ' + JSON.stringify(got) +
                              '\n        esperado: ' + JSON.stringify(exp));
}
function section(n) { console.log('\n== ' + n + ' =='); }

const ES = X.PRESETS.es;      // { ';' , ',' }
const INTL = X.PRESETS.intl;  // { ',' , '.' }

section('toCSV — perfil es-ES (Excel) por defecto');
eq(X.toCSV([[1.5, 2.75]], ['t', 'A']),
   't;A\r\n1,5;2,75',
   'decimal coma, delimitador punto y coma, CRLF');
eq(X.toCSV([[0]], null),
   '0',
   'sin cabecera; el 0 se conserva');

section('toCSV — perfil internacional');
eq(X.toCSV([[1.5, 2.75]], ['t', 'A'], INTL),
   't,A\r\n1.5,2.75',
   'decimal punto, delimitador coma');

section('toCSV — números');
eq(X.toCSV([[16500, 0.13396119184866445]], null, ES),
   '16500;0,1339611918',        // recorte a 10 cifras significativas
   'entero intacto + recorte de ruido de coma flotante');
eq(X.toCSV([[1.65e-7]], null, ES),
   '1,65E-7',
   'notación exponencial con E mayúscula y decimal coma');
eq(X.toCSV([[null, undefined, NaN, Infinity]], null, ES),
   ';;;',
   'null / undefined / NaN / Infinity → celda vacía');

section('toCSV — entrecomillado de texto');
// El nombre contiene el delimitador ';' → debe ir entrecomillado.
eq(X.toCSV([['sim;A', 3]], null, ES),
   '"sim;A";3',
   'celda con delimitador se entrecomilla');
eq(X.toCSV([['di"jo']], null, ES),
   '"di""jo"',
   'las comillas internas se duplican');
// Con perfil internacional, el número con decimal punto no colisiona con la coma.
eq(X.toCSV([['a,b', 1.5]], null, INTL),
   '"a,b",1.5',
   'texto con coma entrecomillado; número no colisiona');

section('slug — nombres de fichero');
eq(X.slug('MBq/g'), 'MBq_g', 'MBq/g → MBq_g');
eq(X.slug('Bq/cm³'), 'Bq_cm', 'Bq/cm³ → Bq_cm (³ eliminado)');
eq(X.slug('Simulacion v.5 - info'), 'Simulacion_v_5_info', 'espacios y puntos → _');

console.log('\n' + '-'.repeat(50));
console.log('Resultado: ' + passed + ' pasados, ' + failed + ' fallidos');
process.exit(failed === 0 ? 0 : 1);
