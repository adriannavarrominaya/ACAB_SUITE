/* test_pureza_time_utils.js — Tests de las utilidades puras de la gráfica
   P(t) de pureza radionucleídica (F1, runbook_F1_pureza_temporal.md).

   Ejercita static/js/pureza_time_utils.js con node, sin framework.

   Uso:
       node tools/test_pureza_time_utils.js

   Devuelve código de salida 0 si todo pasa, 1 si algún test falla.

   Nota: estas funciones solo dan forma (rangos de eje, textos) a
   informe.metricas[sim].pureza_serie, ya calculado por el servidor
   (fort_analyzer.calcular_pureza_serie, con su propio oráculo en
   tools/test_metricas.py); no repiten ninguna fórmula física, así que su
   verificación vive solo aquí (como test_optim_utils.js).
*/
'use strict';

const path = require('path');
const P = require(path.join(__dirname, '..', 'static', 'js', 'pureza_time_utils.js'));

let passed = 0, failed = 0;
function ok(m)   { passed++; console.log('  [PASS] ' + m); }
function fail(m) { failed++; console.log('  [FAIL] ' + m); }
function eq(got, exp, m) {
  const g = JSON.stringify(got), e = JSON.stringify(exp);
  g === e ? ok(m) : fail(m + '\n        obtenido: ' + g + '\n        esperado: ' + e);
}
function section(n) { console.log('\n== ' + n + ' =='); }

section('purezaYRange');
{
  // Caso ref_sim (F1 Fase 1): P siempre >= 99.9999 % → zoom por defecto [90, 100.05].
  const serieRefSim = [
    { t: 0.0,  P_pct: 99.999868941103 },
    { t: 0.25, P_pct: 99.999999167045 },
    { t: 4.5,  P_pct: 99.999999882318 },
  ];
  eq(P.purezaYRange(serieRefSim), [90, 100.05], 'ref_sim: P >= 90 % en todo momento → rango por defecto');

  // P baja por debajo de 90 % en algún punto (p. ej. al inicio del
  // enfriamiento con impurezas de vida corta relevantes) → el rango baja
  // para no recortar esos puntos.
  const serieBaja = [
    { t: 0.0, P_pct: 9.09 },
    { t: 5.0, P_pct: 99.95 },
  ];
  eq(P.purezaYRange(serieBaja), [8, 100.05], 'P mínima 9.09 % → yLo = floor(9.09-0.5) = 8');

  // Puntos con P_pct null (total de impurezas = 0 en ese timestep) se ignoran.
  const serieConNulls = [
    { t: 0.0, P_pct: null },
    { t: 1.0, P_pct: 95.0 },
  ];
  eq(P.purezaYRange(serieConNulls), [90, 100.05], 'null se ignora; mínima real 95 % >= 90 → rango por defecto');

  // Serie vacía o todo null → rango por defecto, sin excepción.
  eq(P.purezaYRange([]), [90, 100.05], 'serie vacía → rango por defecto');
  eq(P.purezaYRange([{ t: 0, P_pct: null }]), [90, 100.05], 'solo nulls → rango por defecto');
  eq(P.purezaYRange(undefined), [90, 100.05], 'undefined → rango por defecto, sin excepción');
}

section('estadoBadgeClass');
{
  eq(P.estadoBadgeClass('no_alcanzado'), 'bg-secondary', 'no_alcanzado → badge secundario');
  eq(P.estadoBadgeClass('alcanzado_en_fin_irradiacion'), 'bg-success', 'ya alcanzado en t=0 → badge de éxito');
  eq(P.estadoBadgeClass('alcanzado_en_enfriamiento'), 'bg-success', 'alcanzado durante enfriamiento → badge de éxito');
  eq(P.estadoBadgeClass('estado_desconocido'), 'bg-secondary', 'estado no reconocido → badge secundario por defecto');
}

section('formatFraccionPico');
{
  eq(P.formatFraccionPico(0.926), '92.6 %', '0.926 → "92.6 %"');
  eq(P.formatFraccionPico(1.0), '100.0 %', '1.0 (t_cruce = t_pico) → "100.0 %"');
  eq(P.formatFraccionPico(null), '—', 'null (sin A_pico > 0) → em dash');
  eq(P.formatFraccionPico(undefined), '—', 'undefined → em dash');
}

console.log('\n' + '-'.repeat(50));
console.log(`Resultado: ${passed} pasados, ${failed} fallidos`);
process.exit(failed === 0 ? 0 : 1);
