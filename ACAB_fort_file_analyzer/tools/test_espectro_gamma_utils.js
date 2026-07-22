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

section('umbralPorDefecto (B1b)');
{
  // Caso oro real: t=3.750h de ref_sim, máximo=13398.0 (línea 364 keV de
  // I131) -- verificado a mano contra fort_analyzer.calcular_espectro_gamma.
  const lineasRefSim375 = [
    { E_keV: 364.49, nucleido: 'I131', intensidad_pct: 81.2, tasa_fotones_s_cm3: 13398.0 },
    { E_keV: 149.72, nucleido: 'TE131', intensidad_pct: 68.9, tasa_fotones_s_cm3: 11154.91 },
    { E_keV: 1.0, nucleido: 'XE133', intensidad_pct: 0.001, tasa_fotones_s_cm3: 1.2773800000000002e-25 },
  ];
  eq(E.umbralPorDefecto(lineasRefSim375), 13398.0 / 1e6,
     'umbral por defecto = máximo/1e6 (factor por defecto)');
  eq(E.umbralPorDefecto(lineasRefSim375, 1e3), 13398.0 / 1e3,
     'factor explícito (1e3) sobrescribe el valor por defecto (1e6)');
  eq(E.umbralPorDefecto([]), 0, 'sin líneas -> 0 (nada que recortar)');
  eq(E.umbralPorDefecto([{ E_keV: 1, nucleido: 'X', intensidad_pct: 1, tasa_fotones_s_cm3: 0 }]), 0,
     'máximo = 0 -> umbral 0, nunca división por cero');
}

section('totalTasaPorNucleido / topNNucleidos (B1b)');
{
  const totales = E.totalTasaPorNucleido(LINEAS);
  eq(totales, { I131: 13389.88 + 432.0, I132: 0.001, TE131: 5000.0 },
     'suma las tasas de todas las líneas de cada nucleido, no solo la mayor');

  eq(E.topNNucleidos(LINEAS, 2), ['I131', 'TE131'],
     'top 2 nucleidos por tasa TOTAL (I131 suma > TE131 > I132)');
  eq(E.topNNucleidos(LINEAS, null), ['I131', 'TE131', 'I132'],
     'n=null -> todos, ordenados descendente por tasa total');
  eq(E.topNNucleidos([], 8), [], 'sin líneas -> sin nucleidos');
}

section('construirTrazasStickTopN (B1b) — leyenda acotada + agrupación "otros"');
{
  // 4 nucleidos con tasas bien diferenciadas; topN=2 debe agrupar los 2 más
  // débiles (I132, XE133) en una única traza "otros".
  const lineasTopN = [
    { E_keV: 364.49, nucleido: 'I131', intensidad_pct: 81.2, tasa_fotones_s_cm3: 13000 },
    { E_keV: 149.72, nucleido: 'TE131', intensidad_pct: 68.9, tasa_fotones_s_cm3: 5000 },
    { E_keV: 249.0, nucleido: 'I132', intensidad_pct: 0.5, tasa_fotones_s_cm3: 10 },
    { E_keV: 81.0, nucleido: 'XE133', intensidad_pct: 1.0, tasa_fotones_s_cm3: 5 },
  ];
  const colorFor = (nucleido, i) => `color-${i}`;
  const trazas = E.construirTrazasStickTopN(lineasTopN, colorFor, { topN: 2, colorOtros: '#999', otrosLabel: 'otros' });

  // 2 trazas por grupo (palotes+marcadores) x (2 top + 1 otros) = 6.
  check(trazas.length === 6, `6 trazas para 2 top + 1 grupo otros (obtenido ${trazas.length})`);

  const nombresLeyenda = trazas.filter(tr => tr.showlegend).map(tr => tr.name).sort();
  eq(nombresLeyenda, ['I131', 'TE131', 'otros'],
     'la leyenda muestra los 2 nucleidos top + una única entrada "otros"');

  const palotesOtros = trazas.find(tr => tr.name === 'otros' && tr.mode === 'lines');
  check(palotesOtros !== undefined, 'traza de palotes "otros" presente');
  eq(palotesOtros.line.color, '#999', 'la traza "otros" usa el color neutro, no colorFor');

  const marcadoresOtros = trazas.find(tr => tr.name === 'otros' && tr.mode === 'markers');
  check(marcadoresOtros !== undefined, 'traza de marcadores "otros" presente');
  eq(marcadoresOtros.x.length, 2, 'el grupo "otros" agrupa las 2 líneas restantes (I132, XE133)');
  // El hover debe seguir identificando el nucleido REAL de cada punto, aunque
  // estén agrupados visualmente bajo "otros" (vía customdata, no el name compartido).
  eq(marcadoresOtros.customdata.map(c => c[0]).sort(), ['I132', 'XE133'],
     'customdata conserva el nucleido real de cada punto dentro de "otros"');

  const marcadoresI131 = trazas.find(tr => tr.name === 'I131' && tr.mode === 'markers');
  check(marcadoresI131.customdata[0][0] === 'I131', 'customdata de un grupo top también lleva su propio nucleido');

  // topN mayor o igual al nº de nucleidos presentes -> nunca aparece "otros".
  const sinOtros = E.construirTrazasStickTopN(lineasTopN, colorFor, { topN: 10 });
  check(sinOtros.every(tr => tr.name !== 'otros'), 'topN >= nº de nucleidos -> no se crea grupo "otros"');
  check(sinOtros.length === 8, `2 trazas x 4 nucleidos = 8 (obtenido ${sinOtros.length})`);

  eq(E.construirTrazasStickTopN([], colorFor, { topN: 8 }), [], 'sin líneas -> sin trazas');
}

console.log('\n' + '-'.repeat(50));
console.log(`Resultado: ${passed} pasados, ${failed} fallidos`);
process.exit(failed === 0 ? 0 : 1);
