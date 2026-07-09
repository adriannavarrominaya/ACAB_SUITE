/* Test de las validaciones V23–V25 añadidas a validateAll (app.js)
 * Ejecutar: node tools/test_validate_all.js
 * Carga app.js con stubs mínimos de DOM/localStorage y verifica que las
 * nuevas reglas de coherencia se disparan (y no se disparan) donde toca.
 */
const fs = require('fs');
const path = require('path');

// ── stubs de entorno navegador ─────────────────────────────────────────────
global.localStorage = { getItem: () => null, setItem: () => {} };
global.document = {
  addEventListener: () => {},
  querySelectorAll: () => [],
  getElementById: () => null,
  documentElement: {},
};
global.window = global;
global.Node = { TEXT_NODE: 3 };
global.fetch = () => Promise.resolve({ json: () => Promise.resolve({}) });

// calc_utils como globales (en el navegador se cargan por <script>)
const cu = require('../static/js/calc_utils.js');
global.validateEgrp = cu.validateEgrp;
global.parseChemFormula = cu.parseChemFormula;
global.computeComposition = cu.computeComposition;

// sweep_utils como globales (app.js referencia buildBlocks78)
const su = require('../static/js/sweep_utils.js');
global.buildBlocks78 = su.buildBlocks78;
global.calcularVectorTiempos = su.calcularVectorTiempos;

// cargar app.js con eval no estricto para que las declaraciones queden en scope
let src = fs.readFileSync(path.join(__dirname, '../static/js/app.js'), 'utf-8');
src = src.replace("'use strict';", '');
src = src.replace('const appState =', 'global.appState =');
eval(src);

// t() devuelve la clave (i18n no cargado): validamos por códigos de clave
function run(data) {
  appState.data = data;
  return validateAll();
}
function has(result, kind, key) {
  return result[kind].some(x => x.msg.startsWith('val.' + key));
}

let fails = 0;
function check(name, cond) {
  console.log(`${cond ? 'OK   ' : 'FALLO'} ${name}`);
  if (!cond) fails++;
}

// Base coherente (calcada del exp1 parseado)
function base() {
  return {
    block1: { IUNC: 0, JTO: 1, INPT: 1, INFD: 0, NOGG: 3, NGRP: 1, IGRP: 0,
              IGE: 4, IZM: 1, IM: 1, JM: 0, IFLU: 1, IGFP: 0, MSTAR: 1 },
    block2: { XRR: [1.0, 1.0], MA: [1], NUCZO: [2], ISOZO: null,
              EGRP: [20.0, 10.0, 5.0, 0.0], CUTOFF: [0,0,0,0,0,0],
              NTO: [0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0] },
    block3: { FLUX: [6.5e13] },
    block4: { IREST: 0 },
    block5: [{ INUCL: [520000, 80000], XCOMP: [4.6448e-4, 9.2896e-4] }],
    block10: { IGFP: 0 },
    block11: { NOPUL: 0, NTSEQ: 0, NOTTS: 2, NVFL: 0, IDOSE: 0 },
    block13: { NCYO: 0, IFSO: 1, ICYO: null, ITSO: [1, 1] },
    blocks78: { sets: [
      { MMN: 1, MOUT: 10, NGO: 1, MSUB: 0,  IUNIT: 3, MFEED: 0, IOUT: 1, IPLOT: 0,
        TIMES: [2.778e-3,0.25,0.5,0.75,1.0,1.25,1.5,1.75,2.0,2.25] },
      { MMN: 0, MOUT: 9,  NGO: 0, MSUB: 10, IUNIT: 3, MFEED: 0, IOUT: 1, IPLOT: 0,
        TIMES: [2.5,2.75,3.0,3.25,3.5,3.75,4.0,4.25,4.5] },
    ] },
  };
}

// caso base: sin errores nuevos
let r = run(base());
check('base sin errores', r.errors.length === 0);

// V23a: EGRP no decreciente
let d = base(); d.block2.EGRP = [20.0, 10.0, 10.0, 0.0];
check('V23a EGRP no decreciente', has(run(d), 'errors', 'v23a'));

// V23b: última frontera negativa
d = base(); d.block2.EGRP = [20.0, 10.0, 5.0, -1.0];
check('V23b última frontera negativa', has(run(d), 'errors', 'v23b'));

// V24a: INPT=1 con identificador de isótopo
d = base(); d.block5[0].INUCL = [521300, 80000];
check('V24a isótopo con INPT=1', has(run(d), 'errors', 'v24a'));

// V24b: INPT=2 con todo elementos (aviso)
d = base(); d.block1.INPT = 2;
check('V24b elementos con INPT=2 (aviso)', has(run(d), 'warnings', 'v24b'));

// V25a: MOUT fuera de rango
d = base(); d.blocks78.sets[0].MOUT = 11;
r = run(d);
check('V25a MOUT > 10', has(r, 'errors', 'v25a'));

// V25b: MMN > MOUT
d = base(); d.blocks78.sets[1].MMN = 12;
check('V25b MMN > MOUT', has(run(d), 'errors', 'v25b'));

// V25c: nº de tiempos ≠ MOUT
d = base(); d.blocks78.sets[1].TIMES = [2.5, 2.75];
check('V25c len(TIMES) ≠ MOUT', has(run(d), 'errors', 'v25c'));

// V25d: último set con NGO=1
d = base(); d.blocks78.sets[1].NGO = 1;
check('V25d último NGO ≠ 0', has(run(d), 'errors', 'v25d'));

// V25e: set intermedio con NGO=0
d = base(); d.blocks78.sets[0].NGO = 0;
check('V25e NGO=0 intermedio', has(run(d), 'errors', 'v25e'));

// V25f: MSUB que no encadena (aviso)
d = base(); d.blocks78.sets[1].MSUB = 7;
check('V25f MSUB no encadena (aviso)', has(run(d), 'warnings', 'v25f'));

// el exp1 real parseado no debe disparar nada nuevo — coherencia con patrón oro
console.log(fails === 0 ? '\nTODOS LOS TESTS OK' : `\n${fails} TESTS FALLARON`);
process.exit(fails === 0 ? 0 : 1);
