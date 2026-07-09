/* Tests de aceptación (node tools/test_sweep_utils.js) para sweep_utils.js
 * (Fase 1 del runbook v2 del barrido paramétrico).
 *
 *   buildBlocks78     — mallas: caso lineal y troceado en sets de 10
 *   buildMassPatches  — reutiliza el caso oro de calc_utils (0.1231 g TeO2)
 *   buildFluxPatches  — modo 'phi' (φ_base=2e14, objetivo=1e14 → XNORM=0.5)
 *   parseSweepValues / proposeSuffix — casos límite
 *   buildTimePatches  — sincroniza block11.NOTTS con el nº de sets
 */
'use strict';
const fs   = require('fs');
const path = require('path');
const {
  calcularVectorTiempos, buildBlocks78, parseSweepValues, proposeSuffix,
  buildFluxPatches, fluxBaseTotal, buildMassPatches, buildTimePatches,
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

// ── buildTimePatches: sincroniza NOTTS ──────────────────────────────────────
const tp = buildTimePatches(
  [{ t_irr_fin: 10, pasos_irr: 10, t_cool_fin: 20, pasos_cool: 5 }],
  { iunit: 3 });
check('buildTimePatches: NOTTS = nº de sets',
  tp[0].patch.block11.NOTTS === 2 && tp[0].patch.blocks78.sets.length === 2);
// fase vacía → conserva la del base
const tp2 = buildTimePatches(
  [{ t_irr_fin: 8, pasos_irr: 4 }],
  { iunit: 3, baseCool: [{ t_fin: 100, pasos: 3 }] });
check('buildTimePatches: fase cool vacía conserva la del base',
  tp2[0].patch.blocks78.times.some(([, tipo]) => tipo === 0));

console.log(fails === 0 ? '\nTODOS LOS TESTS OK' : `\n${fails} TESTS FALLARON`);
process.exit(fails === 0 ? 0 : 1);
