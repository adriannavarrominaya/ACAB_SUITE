/* Tests de aceptación (node tools/test_calc_utils.js) para calc_utils.js:
 *   2A-a  reproducir el Bloque #5 del Exp. 1 desde m=0.1231 g TeO2, V=1 cm3
 *   2A-b  invariancia del resultado por gramo al variar m (régimen lineal)
 *   2A-c  validación de estequiometrías (suma fracciones másicas = 1, interna)
 *   2B    validador EGRP (recuento, decreciente, ≥ 0) y presets de librería
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { parseChemFormula, computeComposition, validateEgrp,
        volumenZonaEfectivo, compararVolumenZona } =
  require('../static/js/calc_utils.js');

const atomic = JSON.parse(fs.readFileSync(
  path.join(__dirname, '../static/data/atomic_data.json'), 'utf-8'));
const presets = JSON.parse(fs.readFileSync(
  path.join(__dirname, '../static/data/egrp_presets.json'), 'utf-8'));

let fails = 0;
function check(name, cond, detail = '') {
  console.log(`${cond ? 'OK   ' : 'FALLO'} ${name}${detail ? '  — ' + detail : ''}`);
  if (!cond) fails++;
}
function relDiff(a, b) { return Math.abs(a - b) / Math.abs(b); }

// ── parseChemFormula ────────────────────────────────────────────────────────
check('parseChemFormula TeO2', JSON.stringify(parseChemFormula('TeO2')) === '{"Te":1,"O":2}');
check('parseChemFormula Al2(SO4)3',
  JSON.stringify(parseChemFormula('Al2(SO4)3')) === '{"Al":2,"S":3,"O":12}');
check('parseChemFormula lista Te:1 O:2',
  JSON.stringify(parseChemFormula('Te:1 O:2')) === '{"Te":1,"O":2}');
let threw = false; try { parseChemFormula('Te0O2x!'); } catch (e) { threw = true; }
check('parseChemFormula rechaza sintaxis inválida', threw);

// ── 2A-a: reproducir Bloque #5 del Exp. 1 ──────────────────────────────────
const r = computeComposition({
  formula: 'TeO2', massG: 0.1231, volumeCc: 1.0, inpt: 1,
  elements: atomic.elements,
});
check('masa molar TeO2 = 159.598', relDiff(r.molarMass, 159.598) < 1e-5,
  `M=${r.molarMass.toFixed(4)}`);
check('INUCL = [80000, 520000] (orden Z creciente)',
  JSON.stringify(r.inucl) === '[80000,520000]');
const xTe = r.rows.find(x => x.symbol === 'Te').xcomp;
const xO  = r.rows.find(x => x.symbol === 'O').xcomp;
check('N(Te) ≈ 4.6448E-04 (fichero validado, tol 1e-3)',
  relDiff(xTe, 4.6448e-4) < 1e-3, `N(Te)=${xTe.toExponential(5)}`);
check('N(O)  ≈ 9.2896E-04 (fichero validado, tol 1e-3)',
  relDiff(xO, 9.2896e-4) < 1e-3, `N(O)=${xO.toExponential(5)}`);
check('N(Te) = 4.6450E-04 (valor analítico del runbook, tol 1e-4)',
  relDiff(xTe, 4.6450e-4) < 1e-4);
check('N(O)/N(Te) = 2 (estequiometría)', relDiff(xO / xTe, 2) < 1e-12);

// ── 2A-a bis: rama INPT=3 (g/cc) ────────────────────────────────────────────
const r3 = computeComposition({
  formula: 'TeO2', massG: 0.1231, volumeCc: 1.0, inpt: 3,
  elements: atomic.elements,
});
const wTe = 127.60 / 159.598;
check('INPT=3: XCOMP(Te) = m·w_Te/V', relDiff(
  r3.rows.find(x => x.symbol === 'Te').xcomp, 0.1231 * wTe) < 1e-9);
const sum3 = r3.xcomp.reduce((a, b) => a + b, 0);
check('INPT=3: suma XCOMP = m/V', relDiff(sum3, 0.1231) < 1e-12);

// ── 2A-b: invariancia por gramo al variar m ─────────────────────────────────
const r2 = computeComposition({
  formula: 'TeO2', massG: 0.2462, volumeCc: 1.0, inpt: 1,
  elements: atomic.elements,
});
check('duplicar m duplica XCOMP (lineal)',
  relDiff(r2.rows.find(x => x.symbol === 'Te').xcomp, 2 * xTe) < 1e-12);
check('XCOMP por gramo invariante',
  relDiff(r2.rows.find(x => x.symbol === 'Te').xcomp / 0.2462, xTe / 0.1231) < 1e-12);

// ── volumen explícito: V=2 divide la densidad atómica por 2 ────────────────
const rv = computeComposition({
  formula: 'TeO2', massG: 0.1231, volumeCc: 2.0, inpt: 1,
  elements: atomic.elements,
});
check('V=2 cm3 → XCOMP/2 (densidad, no total)',
  relDiff(rv.rows.find(x => x.symbol === 'Te').xcomp, xTe / 2) < 1e-12);

// ── 2A-c: INPT=2 rechazado con mensaje claro ────────────────────────────────
threw = false;
try {
  computeComposition({ formula: 'TeO2', massG: 1, volumeCc: 1, inpt: 2,
                       elements: atomic.elements });
} catch (e) { threw = /INPT=2/.test(e.message); }
check('INPT=2 rechazado en modo calculado', threw);

// ── 2B: validador EGRP ──────────────────────────────────────────────────────
const p24 = presets.presets.find(p => p.id === 'manual24');
const p18 = presets.presets.find(p => p.id === 'manual18');
check('preset manual24: 25 fronteras, NOGG=24',
  p24.boundaries.length === 25 && p24.nogg === 24);
check('preset manual18: 19 fronteras, NOGG=18',
  p18.boundaries.length === 19 && p18.nogg === 18);
check('preset manual24 válido', validateEgrp(p24.boundaries, 24).errors.length === 0);
check('preset manual18 válido', validateEgrp(p18.boundaries, 18).errors.length === 0);

let v = validateEgrp([20, 10, 10, 0], 3);
check('EGRP no estrictamente decreciente detectado',
  v.errors.some(e => e.code === 'EGRP_NOT_DECREASING'));
v = validateEgrp([20, 10, 5], 3);
check('recuento EGRP ≠ NOGG+1 detectado',
  v.errors.some(e => e.code === 'EGRP_COUNT'));
v = validateEgrp([20, 10, 5, -1], 3);
check('última frontera negativa detectada',
  v.errors.some(e => e.code === 'EGRP_NEGATIVE'));
v = validateEgrp([20, NaN, 5, 0], 3);
check('valor no numérico detectado', v.errors.some(e => e.code === 'EGRP_NAN'));

// ── F10/F11: volumenZonaEfectivo ────────────────────────────────────────────

// Caso oro del proyecto: IGE=4, IZM=1, XRR = [1.0, 1.0] (2º valor = terminador,
// no volumen) → volumen de zona 1 = 1.0 cm3 (VOLUME OF INTERVAL del fort.6).
let vze = volumenZonaEfectivo({ IGE: 4, IZM: 1, JM: 0 }, { XRR: [1.0, 1.0] }, 1);
check('IGE=4 caso oro: volumen zona 1 = 1.0 cm3', !vze.indeterminado && relDiff(vze.volumen, 1.0) < 1e-12);

// IGE=4 sin el terminador extra (solo IZM valores): sigue leyendo el volumen.
vze = volumenZonaEfectivo({ IGE: 4, IZM: 1, JM: 0 }, { XRR: [1.0] }, 1);
check('IGE=4 sin terminador extra: volumen zona 1 = 1.0 cm3', !vze.indeterminado && relDiff(vze.volumen, 1.0) < 1e-12);

// IGE=4, 2 zonas, con terminador no nulo.
const b2ige4 = { XRR: [2.0, 3.0, 5.0] };
check('IGE=4, 2 zonas: zona 1 = 2.0 cm3',
  relDiff(volumenZonaEfectivo({ IGE: 4, IZM: 2, JM: 0 }, b2ige4, 1).volumen, 2.0) < 1e-12);
check('IGE=4, 2 zonas: zona 2 = 3.0 cm3',
  relDiff(volumenZonaEfectivo({ IGE: 4, IZM: 2, JM: 0 }, b2ige4, 2).volumen, 3.0) < 1e-12);
vze = volumenZonaEfectivo({ IGE: 4, IZM: 2, JM: 0 }, b2ige4, 3);
check('IGE=4: zona fuera de rango (usaría el terminador) → indeterminado',
  vze.indeterminado && vze.motivo === 'XRR_NO_DISPONIBLE');

// IGE=1 planar: fronteras XRR, MA asigna intervalos a zonas.
vze = volumenZonaEfectivo({ IGE: 1, IZM: 2, JM: 0 },
  { XRR: [0, 1, 2, 3], MA: [1, 1, 2] }, 1);
check('IGE=1 planar: zona 1 (2 intervalos) = 2.0 cm3', !vze.indeterminado && relDiff(vze.volumen, 2.0) < 1e-12);
vze = volumenZonaEfectivo({ IGE: 1, IZM: 2, JM: 0 },
  { XRR: [0, 1, 2, 3], MA: [1, 1, 2] }, 2);
check('IGE=1 planar: zona 2 (1 intervalo) = 1.0 cm3', !vze.indeterminado && relDiff(vze.volumen, 1.0) < 1e-12);

// IGE=2 cilíndrico: π(r2²-r1²), altura unidad.
vze = volumenZonaEfectivo({ IGE: 2, IZM: 2, JM: 0 },
  { XRR: [0, 1, 2], MA: [1, 2] }, 1);
check('IGE=2 cilíndrico: zona 1 = π cm3', relDiff(vze.volumen, Math.PI) < 1e-9);
vze = volumenZonaEfectivo({ IGE: 2, IZM: 2, JM: 0 },
  { XRR: [0, 1, 2], MA: [1, 2] }, 2);
check('IGE=2 cilíndrico: zona 2 = 3π cm3', relDiff(vze.volumen, 3 * Math.PI) < 1e-9);

// IGE=3 esférico: (4/3)π(r2³-r1³).
vze = volumenZonaEfectivo({ IGE: 3, IZM: 2, JM: 0 },
  { XRR: [0, 1, 2], MA: [1, 2] }, 1);
check('IGE=3 esférico: zona 1 = (4/3)π cm3', relDiff(vze.volumen, (4 / 3) * Math.PI) < 1e-9);
vze = volumenZonaEfectivo({ IGE: 3, IZM: 2, JM: 0 },
  { XRR: [0, 1, 2], MA: [1, 2] }, 2);
check('IGE=3 esférico: zona 2 = (4/3)π·7 cm3', relDiff(vze.volumen, (4 / 3) * Math.PI * 7) < 1e-9);

// Varios intervalos no contiguos para una misma zona (MA intercalado).
vze = volumenZonaEfectivo({ IGE: 1, IZM: 2, JM: 0 },
  { XRR: [0, 1, 2, 3, 4], MA: [1, 2, 1, 2] }, 1);
check('IGE=1: zona con intervalos no contiguos = 2.0 cm3', relDiff(vze.volumen, 2.0) < 1e-12);

// Indeterminado: geometría 2-D (JM>0).
vze = volumenZonaEfectivo({ IGE: 1, IZM: 1, JM: 2 }, { XRR: [0, 1], MA: [1] }, 1);
check('Geometría 2-D (JM>0) → indeterminado', vze.indeterminado && vze.motivo === 'GEOMETRIA_2D');

// Indeterminado: geometría no soportada.
vze = volumenZonaEfectivo({ IGE: 9, IZM: 1, JM: 0 }, { XRR: [0, 1], MA: [1] }, 1);
check('IGE no soportado → indeterminado', vze.indeterminado && vze.motivo === 'GEOMETRIA_NO_SOPORTADA');

// Indeterminado: la zona pedida no tiene ningún intervalo asignado en MA.
vze = volumenZonaEfectivo({ IGE: 1, IZM: 3, JM: 0 },
  { XRR: [0, 1, 2], MA: [1, 2] }, 3);
check('Zona sin intervalos en MA → indeterminado', vze.indeterminado && vze.motivo === 'ZONA_SIN_INTERVALOS');

// ── F10: compararVolumenZona ────────────────────────────────────────────────

const volOro = volumenZonaEfectivo({ IGE: 4, IZM: 1, JM: 0 }, { XRR: [1.0, 1.0] }, 1);
let cmp = compararVolumenZona(1.0, volOro);
check('F10 caso oro: V=1.0 coincide con la zona', cmp.estado === 'coincide');
cmp = compararVolumenZona(2.0, volOro);
check('F10: V=2.0 no coincide con zona=1.0 (factor=0.5)',
  cmp.estado === 'no_coincide' && relDiff(cmp.factor, 0.5) < 1e-12);
cmp = compararVolumenZona(1.0, volumenZonaEfectivo({ IGE: 1, IZM: 1, JM: 2 }, {}, 1));
check('F10: volumen indeterminado → estado indeterminado (no es error)', cmp.estado === 'indeterminado');

console.log(fails === 0 ? '\nTODOS LOS TESTS OK' : `\n${fails} TESTS FALLARON`);
process.exit(fails === 0 ? 0 : 1);
