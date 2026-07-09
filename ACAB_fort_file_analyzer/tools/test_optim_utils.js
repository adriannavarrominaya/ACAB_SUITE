/* test_optim_utils.js — Tests de la combinación pura sweep_manifest + informe
   (pestaña "Optimización", Fase 5 opcional del runbook del barrido).

   Ejercita static/js/optim_utils.js con node, sin framework.

   Uso:
       node tools/test_optim_utils.js

   Devuelve código de salida 0 si todo pasa, 1 si algún test falla.

   Nota: esta lógica es solo-frontend (combina datos ya calculados por el
   servidor, no repite ninguna fórmula física), así que no tiene un oráculo
   equivalente en Python; su verificación de ejecución vive aquí (como
   test_export.js / test_units.js).
*/
'use strict';

const path = require('path');
const O = require(path.join(__dirname, '..', 'static', 'js', 'optim_utils.js'));

let passed = 0, failed = 0;
function ok(m)   { passed++; console.log('  [PASS] ' + m); }
function fail(m) { failed++; console.log('  [FAIL] ' + m); }
function eq(got, exp, m) {
  const g = JSON.stringify(got), e = JSON.stringify(exp);
  g === e ? ok(m) : fail(m + '\n        obtenido: ' + g + '\n        esperado: ' + e);
}
function section(n) { console.log('\n== ' + n + ' =='); }

// ── Fixtures: barrido de flujo (2 sims), estilo sweep_manifest.json real ──
const manifest = {
  sweep_type: 'flux',
  description: 'Barrido de flujo x0.5/x1.0',
  simulations: [
    { folder: 'TeO2_x0.50', params: { XNORM: 0.5 } },
    { folder: 'TeO2_x1.00', params: { XNORM: 1.0 } },
  ],
};
const reportSimulations = {
  'TeO2_x0.50': { A_pico: 8250, t_pico: 3.75, fase: 'enfriamiento' },
  'TeO2_x1.00': { A_pico: 16500, t_pico: 3.75, fase: 'enfriamiento' },
};
const reportMetricas = {
  'TeO2_x0.50': { pureza: { P_pct: 99.1 }, rendimiento: { rendimiento_medio: 343.75 } },
  'TeO2_x1.00': { pureza: { P_pct: 99.2 }, rendimiento: { rendimiento_medio: 687.5 } },
};

section('mergeSweepRows');
{
  const rows = O.mergeSweepRows(manifest, ['TeO2_x0.50', 'TeO2_x1.00'], reportSimulations, reportMetricas);
  eq(rows.length, 2, '2 filas para 2 simulaciones con entrada en el manifest');
  eq(rows[0], {
    name: 'TeO2_x0.50', params: { XNORM: 0.5 },
    A_pico: 8250, t_pico: 3.75, P_pct: 99.1, rendimiento_medio: 343.75,
  }, 'fila combinada: params + A_pico/t_pico + pureza/rendimiento');

  // Simulación analizada pero SIN entrada en el manifest (p. ej. carpeta
  // suelta añadida a mano dentro de la raíz del barrido) → se omite.
  const rows2 = O.mergeSweepRows(manifest, ['TeO2_x0.50', 'otra_sim_suelta'],
                                  reportSimulations, reportMetricas);
  eq(rows2.length, 1, 'simulación sin entrada en el manifest se omite');

  // Métricas ausentes (p. ej. isótopo estable, sin rendimiento) → null, no excepción.
  const rowsNoMet = O.mergeSweepRows(manifest, ['TeO2_x0.50'], reportSimulations, {});
  eq(rowsNoMet[0].P_pct, null, 'pureza ausente → P_pct null');
  eq(rowsNoMet[0].rendimiento_medio, null, 'rendimiento ausente → null');
}

section('paramKeys');
{
  const rows = O.mergeSweepRows(manifest, ['TeO2_x0.50', 'TeO2_x1.00'], reportSimulations, reportMetricas);
  eq(O.paramKeys(rows), ['XNORM'], 'clave numérica única detectada: XNORM');

  // Barrido temporal (varias claves numéricas por fila).
  const rowsTime = [
    { params: { t_irr_fin: 24, pasos_irr: 7, t_cool_fin: 4.5, pasos_cool: 5 } },
    { params: { t_irr_fin: 48, pasos_irr: 7, t_cool_fin: 4.5, pasos_cool: 5 } },
  ];
  eq(O.paramKeys(rowsTime), ['t_irr_fin', 'pasos_irr', 't_cool_fin', 'pasos_cool'],
     'orden de aparición preservado con varias claves numéricas');
}

section('groupByOtherParams');
{
  const rows = O.mergeSweepRows(manifest, ['TeO2_x0.50', 'TeO2_x1.00'], reportSimulations, reportMetricas);
  const groups = O.groupByOtherParams(rows, 'XNORM');
  eq(groups.length, 1, 'una sola clave de parámetro ⇒ un único grupo (sin color extra)');
  eq(groups[0].label, '', 'grupo único sin otras dimensiones → etiqueta vacía');
  eq(groups[0].rows.map(r => r.params.XNORM), [0.5, 1.0], 'filas del grupo ordenadas por X ascendente');

  // Con una segunda dimensión que varía, aparecen grupos/series distintos.
  const rowsTime = [
    { params: { t_irr_fin: 48, pasos_irr: 7 } },
    { params: { t_irr_fin: 24, pasos_irr: 7 } },
    { params: { t_irr_fin: 24, pasos_irr: 10 } },
  ];
  const groupsTime = O.groupByOtherParams(rowsTime, 't_irr_fin', ['t_irr_fin', 'pasos_irr']);
  eq(groupsTime.length, 2, 'pasos_irr distinto ⇒ 2 grupos/series de color');
  eq(groupsTime.find(g => g.label === 'pasos_irr=7').rows.map(r => r.params.t_irr_fin),
     [24, 48], 'grupo pasos_irr=7 ordenado por t_irr_fin ascendente');

  // Fila sin valor numérico para xKey se omite del todo.
  const rowsPartial = [{ params: { XNORM: 1.0 } }, { params: {} }];
  eq(O.groupByOtherParams(rowsPartial, 'XNORM')[0].rows.length, 1,
     'fila sin XNORM numérico omitida del agrupado');
}

section('yRawValue / yNeedsUnitConv');
{
  const row = { A_pico: 16500, t_pico: 3.75, P_pct: 99.2, rendimiento_medio: 687.5 };
  eq(O.yRawValue(row, 'a_pico'), 16500, "yVar='a_pico' → A_pico");
  eq(O.yRawValue(row, undefined), 16500, 'yVar por defecto (undefined) → A_pico');
  eq(O.yRawValue(row, 't_pico'), 3.75, "yVar='t_pico' → t_pico");
  eq(O.yRawValue(row, 'pureza'), 99.2, "yVar='pureza' → P_pct");
  eq(O.yRawValue(row, 'rendimiento'), 687.5, "yVar='rendimiento' → rendimiento_medio");

  eq(O.yNeedsUnitConv('a_pico'), true, 'a_pico necesita conversión de unidad');
  eq(O.yNeedsUnitConv('rendimiento'), true, 'rendimiento necesita conversión de unidad');
  eq(O.yNeedsUnitConv('t_pico'), false, 't_pico es invariante de unidad');
  eq(O.yNeedsUnitConv('pureza'), false, 'pureza (%) es invariante de unidad');
}

console.log('\n' + '-'.repeat(50));
console.log(`Resultado: ${passed} pasados, ${failed} fallidos`);
process.exit(failed === 0 ? 0 : 1);
