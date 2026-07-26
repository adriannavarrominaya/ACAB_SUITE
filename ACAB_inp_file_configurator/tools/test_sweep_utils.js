/* Tests de aceptación (node tools/test_sweep_utils.js) para sweep_utils.js
 * (Fase 1 del runbook v2 del barrido paramétrico).
 *
 *   buildBlocks78     — mallas: caso lineal y troceado en sets de 10
 *   buildMassPatches  — reutiliza el caso oro de calc_utils (0.1231 g TeO2)
 *   buildFluxPatches  — modo 'phi' (φ_base=2e14, objetivo=1e14 → XNORM=0.5)
 *   parseSweepValues / proposeSuffix — casos límite
 *   buildTimePatches  — historiales multi-tramo (U7): sincroniza
 *                        block11.NOTTS, block13.ITSO (F8), params.t_irr_fin/
 *                        t_cool_fin y equivalencia estructural con
 *                        buildBlocks78 (mismo cálculo que el generador manual)
 *   summarizeFases / insertDuplicate / uniqueSuffix — lógica pura del
 *                        acordeón de tarjetas (resumen, duplicar, sufijos)
 */
'use strict';
const fs   = require('fs');
const path = require('path');
const {
  calcularVectorTiempos, buildBlocks78, parseSweepValues, proposeSuffix,
  buildFluxPatches, fluxBaseTotal, buildMassPatches, buildTimePatches,
  fluxValuesPlaceholder, fluxSweepGuardrail, summarizeFases, insertDuplicate,
  uniqueSuffix,
} = require('../static/js/sweep_utils.js');

const atomic = JSON.parse(fs.readFileSync(
  path.join(__dirname, '../static/data/atomic_data.json'), 'utf-8'));

let fails = 0;
function check(name, cond, detail = '') {
  console.log(`${cond ? 'OK   ' : 'FALLO'} ${name}${detail ? '  — ' + detail : ''}`);
  if (!cond) fails++;
}
function relDiff(a, b) { return Math.abs(a - b) / Math.abs(b); }

// ── buildBlocks78: caso oro lineal (irr t_fin=64, pasos=7) ──────────────────
// El generador manual usa espaciado LINEAL: (t_fin - t_actual)/pasos.
const b1 = buildBlocks78([{ t_fin: 64, pasos: 7 }], [], { iunit: 3, iout: 1, iplot: 0 });
check('buildBlocks78: 1 set para 7 pasos', b1.sets.length === 1 && b1.notts === 1);
check('buildBlocks78: 7 tiempos', b1.sets[0].TIMES.length === 7);
check('buildBlocks78: último tiempo = 64', relDiff(b1.sets[0].TIMES[6], 64) < 1e-12);
const deltas = b1.sets[0].TIMES.map((t, i, a) => i ? t - a[i - 1] : t);
check('buildBlocks78: espaciado lineal (Δ = 64/7)',
  deltas.every(d => relDiff(d, 64 / 7) < 1e-9), `Δ=${(64 / 7).toFixed(6)}`);
check('buildBlocks78: set único MMN=7 MOUT=7 NGO=0 MSUB=0',
  b1.sets[0].MMN === 7 && b1.sets[0].MOUT === 7 && b1.sets[0].NGO === 0 && b1.sets[0].MSUB === 0);
check('buildBlocks78: IUNIT/IOUT/IPLOT propagados',
  b1.sets[0].IUNIT === 3 && b1.sets[0].IOUT === 1 && b1.sets[0].IPLOT === 0 && b1.sets[0].MFEED === 0);

// ── buildBlocks78: > 10 timesteps → 2 sets encadenados ──────────────────────
const b2 = buildBlocks78([{ t_fin: 10, pasos: 10 }], [{ t_fin: 20, pasos: 5 }], { iunit: 3 });
check('buildBlocks78: 15 pasos → 2 sets, notts=2', b2.sets.length === 2 && b2.notts === 2);
check('buildBlocks78: set0 MMN=10 MOUT=10 NGO=1 MSUB=0',
  b2.sets[0].MMN === 10 && b2.sets[0].MOUT === 10 && b2.sets[0].NGO === 1 && b2.sets[0].MSUB === 0);
check('buildBlocks78: set1 MMN=0 MOUT=5 NGO=0 MSUB=10',
  b2.sets[1].MMN === 0 && b2.sets[1].MOUT === 5 && b2.sets[1].NGO === 0 && b2.sets[1].MSUB === 10);
check('buildBlocks78: times marca fases (1=irr, 0=cool)',
  b2.times.length === 15 && b2.times[0][1] === 1 && b2.times[14][1] === 0);

// ── buildBlocks78 (F7): sin compactación — irr y cool NUNCA comparten tarjeta ──
// Caso oro literal: irr 2.778e-3 h / 1 paso + cool 4.5 h / 18 pasos
// (entrados como 2 tramos de <=10 pasos cada uno, límite de calcularVectorTiempos).
const bGolden = buildBlocks78(
  [{ t_fin: 2.778e-3, pasos: 1 }],
  [{ t_fin: 2.5, pasos: 10 }, { t_fin: 4.5, pasos: 8 }],
  { iunit: 3, iout: 1, iplot: 0 });
check('F7 caso oro: 3 tarjetas (irr solo / cool solo / cool solo)', bGolden.sets.length === 3);
check('F7 caso oro: tarjeta 1 (irr) MMN=1 MOUT=1 NGO=1 MSUB=0',
  bGolden.sets[0].MMN === 1 && bGolden.sets[0].MOUT === 1
  && bGolden.sets[0].NGO === 1 && bGolden.sets[0].MSUB === 0);
check('F7 caso oro: tarjeta 1 TIMES = [2.778e-3]',
  JSON.stringify(bGolden.sets[0].TIMES) === JSON.stringify([2.778e-3]));
check('F7 caso oro: tarjeta 2 (cool) MMN=0 MOUT=10 NGO=1 MSUB=1',
  bGolden.sets[1].MMN === 0 && bGolden.sets[1].MOUT === 10
  && bGolden.sets[1].NGO === 1 && bGolden.sets[1].MSUB === 1);
check('F7 caso oro: tarjeta 2 TIMES = 0.25..2.5',
  JSON.stringify(bGolden.sets[1].TIMES)
  === JSON.stringify([0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5]));
check('F7 caso oro: tarjeta 3 (cool) MMN=0 MOUT=8 NGO=0 MSUB=10',
  bGolden.sets[2].MMN === 0 && bGolden.sets[2].MOUT === 8
  && bGolden.sets[2].NGO === 0 && bGolden.sets[2].MSUB === 10);
check('F7 caso oro: tarjeta 3 TIMES = 2.75..4.5',
  JSON.stringify(bGolden.sets[2].TIMES)
  === JSON.stringify([2.75, 3.0, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5]));

// Fase de irradiación > 10 pasos (2 tarjetas de irr) seguida de enfriamiento:
// ninguna tarjeta debe mezclar fases (regresión del "compactado" pre-F7, que
// habría fusionado los 5 últimos pasos de irr con los 3 de cool en una sola
// tarjeta MMN=5 MOUT=8).
const bIrrMulti = buildBlocks78(
  [{ t_fin: 10, pasos: 10 }, { t_fin: 15, pasos: 5 }],
  [{ t_fin: 20, pasos: 3 }],
  { iunit: 3 });
check('F7 irr>10: 3 tarjetas (irr, irr, cool)', bIrrMulti.sets.length === 3);
check('F7 irr>10: tarjeta 1 pura irr MMN=10 MOUT=10 NGO=1 MSUB=0',
  bIrrMulti.sets[0].MMN === 10 && bIrrMulti.sets[0].MOUT === 10
  && bIrrMulti.sets[0].NGO === 1 && bIrrMulti.sets[0].MSUB === 0);
check('F7 irr>10: tarjeta 2 pura irr (nunca MMN<MOUT) MMN=5 MOUT=5 NGO=1 MSUB=10',
  bIrrMulti.sets[1].MMN === 5 && bIrrMulti.sets[1].MOUT === 5
  && bIrrMulti.sets[1].NGO === 1 && bIrrMulti.sets[1].MSUB === 10);
check('F7 irr>10: tarjeta 3 pura cool MMN=0 MOUT=3 NGO=0 MSUB=5',
  bIrrMulti.sets[2].MMN === 0 && bIrrMulti.sets[2].MOUT === 3
  && bIrrMulti.sets[2].NGO === 0 && bIrrMulti.sets[2].MSUB === 5);

// Solo-irradiación (sin fase de enfriamiento): última tarjeta con NGO=0.
const bSoloIrr = buildBlocks78(
  [{ t_fin: 10, pasos: 10 }, { t_fin: 12, pasos: 2 }], [], { iunit: 3 });
check('F7 solo-irr: 2 tarjetas, ambas MMN=MOUT (puro irr)',
  bSoloIrr.sets.length === 2
  && bSoloIrr.sets[0].MMN === 10 && bSoloIrr.sets[0].MOUT === 10
  && bSoloIrr.sets[1].MMN === 2 && bSoloIrr.sets[1].MOUT === 2);
check('F7 solo-irr: NGO 1,0 y MSUB 0,10',
  bSoloIrr.sets[0].NGO === 1 && bSoloIrr.sets[0].MSUB === 0
  && bSoloIrr.sets[1].NGO === 0 && bSoloIrr.sets[1].MSUB === 10);

// Solo-enfriamiento (sin fase de irradiación): MMN=0 en todas las tarjetas.
const bSoloCool = buildBlocks78(
  [], [{ t_fin: 10, pasos: 10 }, { t_fin: 12, pasos: 2 }], { iunit: 3 });
check('F7 solo-cool: 2 tarjetas, MMN=0 en ambas',
  bSoloCool.sets.length === 2 && bSoloCool.sets[0].MMN === 0 && bSoloCool.sets[1].MMN === 0);
check('F7 solo-cool: MOUT 10,2 NGO 1,0 MSUB 0,10',
  bSoloCool.sets[0].MOUT === 10 && bSoloCool.sets[0].NGO === 1 && bSoloCool.sets[0].MSUB === 0
  && bSoloCool.sets[1].MOUT === 2 && bSoloCool.sets[1].NGO === 0 && bSoloCool.sets[1].MSUB === 10);

// calcularVectorTiempos rechaza pasos/tiempo inválidos
let threw = false; try { calcularVectorTiempos([{ t_fin: 10, pasos: 11 }]); } catch (e) { threw = true; }
check('calcularVectorTiempos rechaza pasos > 10', threw);
threw = false; try { calcularVectorTiempos([{ t_fin: 0, pasos: 3 }]); } catch (e) { threw = true; }
check('calcularVectorTiempos rechaza t_fin ≤ t_actual', threw);

// ── buildMassPatches: caso oro de calc_utils ────────────────────────────────
const baseB5 = [{ INUCL: [520000, 80000], XCOMP: [4.6448e-4, 9.2896e-4] }];
const mp = buildMassPatches({
  masas: [0.1231], formula: 'TeO2', volumen: 1.0, inpt: 1,
  zoneIdx: 0, baseBlock5: baseB5, elements: atomic.elements,
});
check('buildMassPatches: 1 patch', mp.length === 1 && !!mp[0].patch.block5);
const z0 = mp[0].patch.block5[0];
check('buildMassPatches: INUCL conservado (orden base)',
  JSON.stringify(z0.INUCL) === '[520000,80000]');
check('buildMassPatches: XCOMP(Te) ≈ 4.6450e-4', relDiff(z0.XCOMP[0], 4.6450e-4) < 1e-3,
  z0.XCOMP[0].toExponential(5));
check('buildMassPatches: XCOMP(O) ≈ 9.2899e-4', relDiff(z0.XCOMP[1], 9.2899e-4) < 1e-3,
  z0.XCOMP[1].toExponential(5));
// escalado lineal con la masa
const mp2 = buildMassPatches({
  masas: [0.2462], formula: 'TeO2', volumen: 1.0, inpt: 1,
  zoneIdx: 0, baseBlock5: baseB5, elements: atomic.elements,
});
check('buildMassPatches: doble masa → doble XCOMP',
  relDiff(mp2[0].patch.block5[0].XCOMP[0], 2 * z0.XCOMP[0]) < 1e-9);
// INPT=2 rechazado
threw = false;
try {
  buildMassPatches({ masas: [1], formula: 'TeO2', volumen: 1, inpt: 2,
    zoneIdx: 0, baseBlock5: baseB5, elements: atomic.elements });
} catch (e) { threw = /INPT=2/.test(e.message); }
check('buildMassPatches: INPT=2 rechazado', threw);
// compuesto incompatible con INUCL base
threw = false;
try {
  buildMassPatches({ masas: [1], formula: 'H2O', volumen: 1, inpt: 1,
    zoneIdx: 0, baseBlock5: baseB5, elements: atomic.elements });
} catch (e) { threw = /no contiene el nucleido/.test(e.message); }
check('buildMassPatches: compuesto incompatible detectado', threw);

// ── buildFluxPatches ────────────────────────────────────────────────────────
const fxDirect = buildFluxPatches([0.5, 0.75, 1.0], 'xnorm');
check('buildFluxPatches xnorm: valores directos',
  fxDirect.length === 3 && fxDirect[1].patch.block9.XNORM === 0.75);
const fxPhi = buildFluxPatches([1e14], 'phi', 2e14);
check('buildFluxPatches phi: φ_obj=1e14 / φ_base=2e14 → XNORM=0.5',
  fxPhi[0].patch.block9.XNORM === 0.5 && fxPhi[0].params.phi === 1e14);
threw = false;
try { buildFluxPatches([1e14], 'phi', 0); } catch (e) { threw = true; }
check('buildFluxPatches phi: rechaza φ_base = 0', threw);
check('fluxBaseTotal: Σ FLUX × XNORM',
  relDiff(fluxBaseTotal({ FLUX: [1e14, 1e14] }, { XNORM: 1 }), 2e14) < 1e-12);

// ── fluxValuesPlaceholder (U5a) ──────────────────────────────────────────────
check("fluxValuesPlaceholder xnorm: ejemplos de factores fijos",
  fluxValuesPlaceholder('xnorm', 2e14) === '0.5, 0.75, 1.0, 1.5');
check("fluxValuesPlaceholder xnorm: ignora φ_base ausente",
  fluxValuesPlaceholder('xnorm', undefined) === '0.5, 0.75, 1.0, 1.5');
check("fluxValuesPlaceholder phi: ejemplos ×0.5/×1/×2 de φ_base",
  fluxValuesPlaceholder('phi', 2e14) === '1.00e+14, 2.00e+14, 4.00e+14');
check("fluxValuesPlaceholder phi: sin φ_base (sin fichero) → null, nunca el placeholder de factores",
  fluxValuesPlaceholder('phi', undefined) === null && fluxValuesPlaceholder('phi', 0) === null);

// ── fluxSweepGuardrail (U5c) ─────────────────────────────────────────────────
// Modo phi: factor introducido por error como si fuera flujo → XNORM ~1e-14
const guardPhiBad = fluxSweepGuardrail([1.0], 'phi', 2e14);
check("fluxSweepGuardrail phi: factor 1.0 en modo flujo (φ_base=2e14) → XNORM≈5e-15, fuera de rango",
  guardPhiBad.length === 1 && relDiff(guardPhiBad[0].xnorm, 1.0 / 2e14) < 1e-9);
const guardPhiOk = fluxSweepGuardrail([1e14, 2e14], 'phi', 2e14);
check("fluxSweepGuardrail phi: flujos objetivo razonables no disparan aviso", guardPhiOk.length === 0);
// Modo xnorm: flujo absoluto introducido por error como si fuera factor
const guardXnormBad = fluxSweepGuardrail([2e14], 'xnorm', 2e14);
check("fluxSweepGuardrail xnorm: valor 2e14 como factor XNORM directo, fuera de rango",
  guardXnormBad.length === 1 && guardXnormBad[0].xnorm === 2e14);
const guardXnormOk = fluxSweepGuardrail([0.5, 0.75, 1.0, 1.5], 'xnorm', 2e14);
check("fluxSweepGuardrail xnorm: factores razonables no disparan aviso", guardXnormOk.length === 0);

// ── parseSweepValues ────────────────────────────────────────────────────────
check('parseSweepValues coma/espacio', JSON.stringify(parseSweepValues('0.5, 0.75 1')) === '[0.5,0.75,1]');
threw = false; try { parseSweepValues(''); } catch (e) { threw = true; }
check('parseSweepValues rechaza vacío', threw);
threw = false; try { parseSweepValues('0.5, abc'); } catch (e) { threw = true; }
check('parseSweepValues rechaza no numérico', threw);
threw = false; try { parseSweepValues(Array.from({ length: 201 }, (_, i) => i).join(',')); } catch (e) { threw = true; }
check('parseSweepValues rechaza > 200', threw);

// ── proposeSuffix ───────────────────────────────────────────────────────────
check("proposeSuffix('flux',0.75) = 'x0.75'", proposeSuffix('flux', 0.75) === 'x0.75');
check("proposeSuffix('mass',1.5) = 'm1.500g'", proposeSuffix('mass', 1.5) === 'm1.500g');
check("proposeSuffix('time',48) = 'Tirr048.0h'", proposeSuffix('time', 48) === 'Tirr048.0h');
check("proposeSuffix('xnorm',1) = 'x1'", proposeSuffix('xnorm', 1) === 'x1');

// ── buildTimePatches (U7): historiales multi-tramo por tarjeta ─────────────
// Regresión: 1 tramo por fase, mismo comportamiento exacto que antes de U7.
const singleFila = {
  fasesIrr:  [{ t_fin: 10, pasos: 10 }],
  fasesCool: [{ t_fin: 20, pasos: 5 }],
  iunit: 3, iout: 1, iplot: 0,
};
const tp = buildTimePatches([singleFila], {});
check('buildTimePatches: NOTTS = nº de sets (regresión 1 tramo/fase)',
  tp[0].patch.block11.NOTTS === 2 && tp[0].patch.blocks78.sets.length === 2);
check('buildTimePatches: params.t_irr_fin/t_cool_fin = t_fin del tramo',
  tp[0].params.t_irr_fin === 10 && tp[0].params.t_cool_fin === 20);
check('buildTimePatches: historial_irr/historial_cool presentes',
  JSON.stringify(tp[0].params.historial_irr) === JSON.stringify(singleFila.fasesIrr)
  && JSON.stringify(tp[0].params.historial_cool) === JSON.stringify(singleFila.fasesCool));
// F8: block13.ITSO debe crecer junto a block11.NOTTS (bug hermano: antes de
// F8 solo se parcheaba block11.NOTTS y block13.ITSO quedaba desincronizado).
check('F8 buildTimePatches: block13.ITSO longitud = NOTTS, todo con salida',
  JSON.stringify(tp[0].patch.block13.ITSO) === JSON.stringify([1, 1]));

// Multi-tramo: 2 tramos de irradiación + 2 de enfriamiento en una tarjeta.
const multiFila = {
  fasesIrr:  [{ t_fin: 10, pasos: 5 }, { t_fin: 40, pasos: 8 }],
  fasesCool: [{ t_fin: 20, pasos: 4 }, { t_fin: 168, pasos: 6 }],
  iunit: 3, iout: 1, iplot: 0,
};
const tpMulti = buildTimePatches([multiFila], {});
check('buildTimePatches multi-tramo: t_irr_fin = t_fin del ÚLTIMO tramo de irr',
  tpMulti[0].params.t_irr_fin === 40);
check('buildTimePatches multi-tramo: t_cool_fin = t_fin del ÚLTIMO tramo de cool',
  tpMulti[0].params.t_cool_fin === 168);
check('buildTimePatches multi-tramo: NOTTS = nº de sets (5+8 irr + 4+6 cool = 23 pasos → 3 sets)',
  tpMulti[0].patch.block11.NOTTS === 3 && tpMulti[0].patch.blocks78.sets.length === 3);
check('F8 buildTimePatches multi-tramo: block13.ITSO longitud = NOTTS (3), todo con salida',
  JSON.stringify(tpMulti[0].patch.block13.ITSO) === JSON.stringify([1, 1, 1]));
// F7: los tramos se concatenan por fase y se trocean sin mezclar -- ninguna
// tarjeta puede tener 0 < MMN < MOUT (eso sería una tarjeta mixta irr+cool).
check('F7 multi-tramo: ninguna tarjeta mezcla fases (MMN=0 o MMN=MOUT)',
  tpMulti[0].patch.blocks78.sets.every(s => s.MMN === 0 || s.MMN === s.MOUT));

// Ambas fases vacías sigue siendo un error (misma semántica que el editor manual).
let threwEmptyPhases = false;
try { buildTimePatches([{ fasesIrr: [], fasesCool: [] }], {}); }
catch (e) { threwEmptyPhases = true; }
check('buildTimePatches: ambas fases vacías lanza error', threwEmptyPhases);

// Equivalencia de generadores: el barrido y el generador manual son
// literalmente el mismo cálculo (buildBlocks78) -- cero divergencia.
const bDirect = buildBlocks78(multiFila.fasesIrr, multiFila.fasesCool,
  { iunit: multiFila.iunit, iout: multiFila.iout, iplot: multiFila.iplot });
check('buildTimePatches ≡ buildBlocks78 (mismo cálculo, misma entrada)',
  JSON.stringify(tpMulti[0].patch.blocks78)
  === JSON.stringify({ sets: bDirect.sets, times: bDirect.times }));

// ── summarizeFases: resumen de tarjeta (lógica pura) ────────────────────────
const sEmpty = summarizeFases([], []);
check('summarizeFases: ambas fases vacías → tramos 0, final null',
  sEmpty.irrTramos === 0 && sEmpty.irrFinal === null
  && sEmpty.coolTramos === 0 && sEmpty.coolFinal === null);
const sSingle = summarizeFases([{ t_fin: 24, pasos: 6 }], []);
check('summarizeFases: 1 tramo de irr, sin cool',
  sSingle.irrTramos === 1 && sSingle.irrFinal === 24 && sSingle.coolTramos === 0);
const sMulti = summarizeFases(multiFila.fasesIrr, multiFila.fasesCool);
check('summarizeFases multi-tramo: recuentos y tiempo final del ÚLTIMO tramo',
  sMulti.irrTramos === 2 && sMulti.irrFinal === 40
  && sMulti.coolTramos === 2 && sMulti.coolFinal === 168);

// ── insertDuplicate: clonar+insertar una tarjeta (lógica pura) ──────────────
const cards = [{ id: 1, fasesIrr: [{ t_fin: 10, pasos: 2 }] }, { id: 2, fasesIrr: [] }];
const dup = insertDuplicate(cards, 0);
check('insertDuplicate: longitud +1', dup.length === cards.length + 1);
check('insertDuplicate: el clon se inserta justo después del índice',
  dup[0].id === 1 && dup[1].id === 1 && dup[2].id === 2);
check('insertDuplicate: no muta la lista original', cards.length === 2);
dup[1].fasesIrr[0].t_fin = 999;
check('insertDuplicate: el clon es independiente (clon profundo)',
  cards[0].fasesIrr[0].t_fin === 10 && dup[0].fasesIrr[0].t_fin === 10);

// ── uniqueSuffix: desambigua colisiones dentro de un mismo barrido ─────────
check('uniqueSuffix: sin colisión devuelve la base tal cual',
  uniqueSuffix('Tirr040.0h', []) === 'Tirr040.0h');
check('uniqueSuffix: colisión simple añade _2',
  uniqueSuffix('Tirr040.0h', ['Tirr040.0h']) === 'Tirr040.0h_2');
check('uniqueSuffix: colisiones encadenadas añade el primer índice libre',
  uniqueSuffix('Tirr040.0h', ['Tirr040.0h', 'Tirr040.0h_2']) === 'Tirr040.0h_3');
// Caso U7: dos tarjetas con el mismo t_irr_fin (misma duración total) pero
// historiales distintos (distinta segmentación) no deben colisionar de
// carpeta -- exactamente lo que corrige uniqueSuffix en sweep.js.
const cardA = { fasesIrr: [{ t_fin: 40, pasos: 8 }], fasesCool: [] };
const cardB = { fasesIrr: [{ t_fin: 10, pasos: 5 }, { t_fin: 40, pasos: 8 }], fasesCool: [] };
const tpAB = buildTimePatches(
  [{ ...cardA, iunit: 3 }, { ...cardB, iunit: 3 }], {});
check('buildTimePatches: mismo t_irr_fin en dos tarjetas con historial distinto',
  tpAB[0].params.t_irr_fin === 40 && tpAB[1].params.t_irr_fin === 40);
const suffixesAB = [];
tpAB.forEach(p => {
  const base = proposeSuffix('time', p.params.t_irr_fin);
  const suf  = uniqueSuffix(base, suffixesAB);
  suffixesAB.push(suf);
});
check('uniqueSuffix aplicado a buildTimePatches: sufijos desambiguados y únicos',
  suffixesAB[0] === 'Tirr040.0h' && suffixesAB[1] === 'Tirr040.0h_2');

console.log(fails === 0 ? '\nTODOS LOS TESTS OK' : `\n${fails} TESTS FALLARON`);
process.exit(fails === 0 ? 0 : 1);
