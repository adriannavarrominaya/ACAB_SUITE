/* test_espectro_gamma_utils.js — Tests de las utilidades puras de la
   pestaña "Espectro gamma" (B1 del BACKLOG, Fase 3).

   Ejercita static/js/espectro_gamma_utils.js con node, sin framework.

   Uso:
       node tools/test_espectro_gamma_utils.js

   Devuelve código de salida 0 si todo pasa, 1 si algún test falla.

   Nota: estas funciones solo filtran/agrupan/dan forma al espectro ya
   calculado por el servidor (fort_analyzer.calcular_espectro_gamma, con su
   propio oráculo en tools/test_photon.py); no repiten ninguna fórmula
   física, así que su verificación vive solo aquí (como
   test_optim_utils.js / test_pureza_time_utils.js).
*/
'use strict';

const path = require('path');
const E = require(path.join(__dirname, '..', 'static', 'js', 'espectro_gamma_utils.js'));

let passed = 0, failed = 0;
function ok(m)   { passed++; console.log('  [PASS] ' + m); }
function fail(m) { failed++; console.log('  [FAIL] ' + m); }
function check(cond, m) { cond ? ok(m) : fail(m); }
function eq(got, exp, m) {
  const g = JSON.stringify(got), e = JSON.stringify(exp);
  g === e ? ok(m) : fail(m + '\n        obtenido: ' + g + '\n        esperado: ' + e);
}
function section(n) { console.log('\n== ' + n + ' =='); }

const LINEAS = [
  { E_keV: 364.49, nucleido: 'I131', intensidad_pct: 81.2, tasa_fotones_s_cm3: 13389.88 },
  { E_keV: 80.185, nucleido: 'I131', intensidad_pct: 2.62, tasa_fotones_s_cm3: 432.0 },
  { E_keV: 249.0,  nucleido: 'I132', intensidad_pct: 0.5,  tasa_fotones_s_cm3: 0.001 },
  { E_keV: 149.72, nucleido: 'TE131', intensidad_pct: 68.9, tasa_fotones_s_cm3: 5000.0 },
];

section('filtrarLineas');
{
  eq(E.filtrarLineas(LINEAS, {}), LINEAS, 'sin opts -> devuelve todas las líneas');

  const porEnergia = E.filtrarLineas(LINEAS, { eMinKeV: 100, eMaxKeV: 300 });
  eq(porEnergia.map(l => l.E_keV), [249.0, 149.72],
     'rango de energía [100,300] keV excluye 364.49 y 80.185');

  const porTasa = E.filtrarLineas(LINEAS, { tasaMin: 100 });
  eq(porTasa.map(l => l.nucleido), ['I131', 'I131', 'TE131'],
     'tasaMin=100 excluye la línea débil de I132 (recorta el ruido de I-132/I-135), conserva ambas de I131');

  const combinado = E.filtrarLineas(LINEAS, { eMinKeV: 100, tasaMin: 100 });
  eq(combinado.map(l => l.E_keV), [364.49, 149.72], 'combinación de ambos filtros a la vez');

  eq(E.filtrarLineas([], { eMinKeV: 0 }), [], 'lista vacía -> lista vacía');
}

section('agruparPorNucleido / nucleidosOrdenados');
{
  const grupos = E.agruparPorNucleido(LINEAS);
  check(Object.keys(grupos).length === 3, '3 nucleidos distintos agrupados');
  check(grupos.I131.length === 2, 'I131 tiene 2 líneas');
  check(grupos.TE131.length === 1, 'TE131 tiene 1 línea');

  eq(E.nucleidosOrdenados(LINEAS), ['I131', 'I132', 'TE131'],
     'nombres de nucleido ordenados alfabéticamente');
  eq(E.nucleidosOrdenados([]), [], 'sin líneas -> sin nucleidos');
}

section('topLineas');
{
  const top2 = E.topLineas(LINEAS, 2);
  eq(top2.map(l => l.E_keV), [364.49, 149.72], 'top 2 por tasa descendente');

  const topTodas = E.topLineas(LINEAS, null);
  check(topTodas.length === 4, 'n=null -> devuelve todas, ordenadas');
  eq(topTodas[0].E_keV, 364.49, 'la de mayor tasa va primero');
  eq(topTodas[topTodas.length - 1].E_keV, 249.0, 'la de menor tasa va última');

  // No debe mutar el array original.
  check(LINEAS[0].E_keV === 364.49 && LINEAS.length === 4, 'topLineas no muta la lista de entrada');
}

section('construirTrazasStick');
{
  const colorFor = (nucleido, i) => `color-${i}`;
  const trazas = E.construirTrazasStick(LINEAS, colorFor);

  // 2 trazas por nucleido (palotes + marcadores) x 3 nucleidos = 6.
  check(trazas.length === 6, `6 trazas para 3 nucleidos (obtenido ${trazas.length})`);

  const sticksI131 = trazas.find(tr => tr.name === 'I131' && tr.mode === 'lines');
  check(sticksI131 !== undefined, 'traza de palotes de I131 presente');
  // 2 líneas de I131 -> 2 palotes de 3 puntos cada uno (E,0)-(E,tasa)-(null) = 6 elementos.
  eq(sticksI131.x.length, 6, 'palotes de I131: 2 líneas x 3 puntos (con separador null)');
  eq(sticksI131.x, [80.185, 80.185, null, 364.49, 364.49, null],
     'palotes de I131 ordenados por energía ascendente');
  eq(sticksI131.y, [0, 432.0, null, 0, 13389.88, null], 'palotes van de y=0 a y=tasa');
  check(sticksI131.showlegend === true, 'la traza de palotes SÍ aparece en la leyenda');

  const marcadoresI131 = trazas.find(tr => tr.name === 'I131' && tr.mode === 'markers');
  check(marcadoresI131 !== undefined, 'traza de marcadores de I131 presente');
  check(marcadoresI131.showlegend === false,
        'la traza de marcadores NO duplica la leyenda (legendgroup compartido con los palotes)');
  eq(marcadoresI131.legendgroup, sticksI131.legendgroup,
     'palotes y marcadores del mismo nucleido comparten legendgroup (toggle conjunto)');

  check(trazas.every(tr => typeof tr.line?.color === 'string' || typeof tr.marker?.color === 'string'),
        'todas las trazas llevan color asignado por colorFor');

  eq(E.construirTrazasStick([], colorFor), [], 'sin líneas -> sin trazas');
}

console.log('\n' + '-'.repeat(50));
console.log(`Resultado: ${passed} pasados, ${failed} fallidos`);
process.exit(failed === 0 ? 0 : 1);
