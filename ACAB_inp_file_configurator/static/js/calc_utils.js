/* calc_utils.js — Funciones puras para el modo calculado del Bloque #5 y el
 * validador de EGRP (Bloque #2 Card #6).  Sin dependencias del DOM: este
 * módulo es testeable con node (ver tools/test_calc_utils.js).
 *
 * Convenios (docs/Block#1.md y docs/Block#5.md):
 *   - INPT=1/2 → XCOMP en átomos/barn·cm (= 1e24 átomos/cm3).  Es una
 *     DENSIDAD atómica: el volumen de zona V debe tratarse explícitamente.
 *   - INPT=3   → XCOMP en g/cc.
 *   - Fórmula del método analítico validado (V en cm3):
 *       XCOMP_i = (m · w_i / M_i) · N_A / (1e24 · V)
 *     Caso de test: m = 0.1231 g de TeO2, V = 1 cm3 →
 *       N(Te) = 4.6450e-4, N(O) = 9.2899e-4  (ver tools/test_calc_utils.js).
 */
'use strict';

const AVOGADRO = 6.02214076e23;   // mol^-1 (CODATA, exacto desde SI 2019)

/**
 * Parsea una fórmula química (con paréntesis y subíndices) o una lista
 * "Elemento:índice" separada por espacios/comas.
 *   parseChemFormula('TeO2')        → { Te: 1, O: 2 }
 *   parseChemFormula('Al2(SO4)3')   → { Al: 2, S: 3, O: 12 }
 *   parseChemFormula('Te:1 O:2')    → { Te: 1, O: 2 }
 * Lanza Error con mensaje descriptivo si la sintaxis es inválida.
 */
function parseChemFormula(input) {
  const str = String(input || '').trim();
  if (!str) throw new Error('Fórmula vacía.');

  // Modo lista "El:n"
  if (str.includes(':')) {
    const out = {};
    for (const part of str.split(/[\s,;]+/)) {
      if (!part) continue;
      const m = part.match(/^([A-Z][a-z]?):([0-9]*\.?[0-9]+)$/);
      if (!m) throw new Error(`Entrada inválida en la lista elemento:índice: '${part}'`);
      const n = parseFloat(m[2]);
      if (!(n > 0)) throw new Error(`Índice no positivo para '${m[1]}'.`);
      out[m[1]] = (out[m[1]] || 0) + n;
    }
    if (Object.keys(out).length === 0) throw new Error('Lista elemento:índice vacía.');
    return out;
  }

  // Modo fórmula química con paréntesis
  let i = 0;
  function parseGroup() {
    const counts = {};
    while (i < str.length) {
      const ch = str[i];
      if (ch === '(') {
        i++;
        const inner = parseGroup();
        if (str[i] !== ')') throw new Error('Paréntesis sin cerrar en la fórmula.');
        i++;
        const mult = readNumber(1);
        for (const [el, n] of Object.entries(inner))
          counts[el] = (counts[el] || 0) + n * mult;
      } else if (ch === ')') {
        return counts;
      } else if (/[A-Z]/.test(ch)) {
        let sym = ch; i++;
        if (i < str.length && /[a-z]/.test(str[i])) { sym += str[i]; i++; }
        const n = readNumber(1);
        counts[sym] = (counts[sym] || 0) + n;
      } else if (/\s/.test(ch)) {
        i++;
      } else {
        throw new Error(`Carácter inesperado '${ch}' en la fórmula.`);
      }
    }
    return counts;
  }
  function readNumber(def) {
    let s = '';
    while (i < str.length && /[0-9.]/.test(str[i])) { s += str[i]; i++; }
    if (!s) return def;
    const n = parseFloat(s);
    if (!(n > 0)) throw new Error(`Subíndice no positivo: '${s}'.`);
    return n;
  }
  const res = parseGroup();
  if (i < str.length) throw new Error("Paréntesis ')' inesperado en la fórmula.");
  if (Object.keys(res).length === 0) throw new Error('La fórmula no contiene elementos.');
  return res;
}

/**
 * Calcula la composición inicial del Bloque #5 a partir de la masa del blanco.
 *
 * @param {Object} opts
 *   formula   {string}  fórmula química o lista "El:n"
 *   massG     {number}  masa del blanco [g]
 *   volumeCc  {number}  volumen de la zona [cm3]  (para IGE=4 debe coincidir
 *                        con la componente XRR de la zona)
 *   inpt      {number}  1 o 3 (INPT=2 —isótopos— no soportado en modo calculado)
 *   elements  {Object}  tabla { Sym: {Z, mass} } de atomic_data.json
 * @returns {Object} {
 *   molarMass, stoich, rows: [{symbol, Z, elemid, atoms, massFrac, xcomp}],
 *   inucl: [...], xcomp: [...] }
 */
function computeComposition({ formula, massG, volumeCc, inpt, elements }) {
  const m = Number(massG), V = Number(volumeCc);
  if (!(m > 0))  throw new Error('La masa del blanco debe ser > 0 g.');
  if (!(V > 0))  throw new Error('El volumen de la zona debe ser > 0 cm3.');
  if (inpt !== 1 && inpt !== 3)
    throw new Error('El modo calculado solo soporta INPT=1 (átomos/barn·cm) o INPT=3 (g/cc). '
      + 'Para INPT=2 (isótopos) introduce las concentraciones manualmente.');

  const stoich = parseChemFormula(formula);

  let molar = 0;
  const rows = [];
  for (const [sym, atoms] of Object.entries(stoich)) {
    const el = elements[sym];
    if (!el) throw new Error(`Elemento '${sym}' no disponible en la librería de datos atómicos.`);
    molar += atoms * el.mass;
  }
  if (!(molar > 0)) throw new Error('Masa molar nula.');

  let wsum = 0;
  for (const [sym, atoms] of Object.entries(stoich)) {
    const el = elements[sym];
    const massFrac = (atoms * el.mass) / molar;
    wsum += massFrac;
    const xcomp = inpt === 1
      ? (m * massFrac / el.mass) * AVOGADRO / (1e24 * V)   // átomos/barn·cm
      : (m * massFrac) / V;                                 // g/cc
    rows.push({ symbol: sym, Z: el.Z, elemid: 10000 * el.Z, atoms,
                massFrac, xcomp });
  }
  // Invariante: la suma de fracciones másicas debe ser 1 (validación estequiometría)
  if (Math.abs(wsum - 1) > 1e-9)
    throw new Error(`Suma de fracciones másicas = ${wsum} ≠ 1 (error interno).`);

  rows.sort((a, b) => a.Z - b.Z);
  return {
    molarMass: molar,
    stoich,
    rows,
    inucl: rows.map(r => r.elemid),
    xcomp: rows.map(r => r.xcomp),
  };
}

/**
 * Valida un array EGRP frente a NOGG (docs/Block#2.md):
 *   - NOGG+1 valores, todos finitos
 *   - estrictamente decreciente
 *   - última frontera ≥ 0
 * @returns {{ errors: string[], warnings: string[] }}  mensajes sin traducir;
 *          la capa de UI los mapea a i18n con los códigos EGRP_*.
 */
function validateEgrp(egrp, nogg) {
  const errors = [], warnings = [];
  const arr = egrp || [];
  if (nogg > 0 && arr.length !== nogg + 1)
    errors.push({ code: 'EGRP_COUNT', exp: nogg + 1, got: arr.length });
  for (let i = 0; i < arr.length; i++) {
    if (!Number.isFinite(arr[i])) {
      errors.push({ code: 'EGRP_NAN', i: i + 1 });
      return { errors, warnings };
    }
  }
  for (let i = 1; i < arr.length; i++) {
    if (!(arr[i] < arr[i - 1])) {
      errors.push({ code: 'EGRP_NOT_DECREASING', i: i + 1, v: arr[i], prev: arr[i - 1] });
      break;
    }
  }
  if (arr.length && arr[arr.length - 1] < 0)
    errors.push({ code: 'EGRP_NEGATIVE', v: arr[arr.length - 1] });
  return { errors, warnings };
}

/**
 * F10/F11 — Volumen efectivo de una zona según Block #1/#2 (docs/Block#2.md,
 * "fuente de verdad" de formato). Es el volumen que ACAB usa REALMENTE para
 * calcular la densidad atómica de la zona, con independencia de lo que el
 * usuario haya tecleado en la composición asistida:
 *   - IGE=4 (3-D, acoplado a Monte Carlo): XRR NO son fronteras, es
 *     directamente el volumen de cada zona en cm3; la tarjeta XRR termina
 *     con un valor adicional no nulo que NO es volumen (formato, ver
 *     docs/Block#2.md card #1) — por eso solo se leen los índices
 *     [0, IZM-1], nunca el último.
 *   - IGE 1/2/3 (1-D planar/cilíndrico/esférico): XRR son fronteras en cm
 *     de los IM intervalos; el volumen de cada intervalo se deriva de la
 *     geometría (área/superficie unidad) y se suman los intervalos que MA
 *     asigna a la zona pedida (una zona puede agrupar varios intervalos).
 *   - Geometrías 2-D (JM > 0) u otras configuraciones no derivables con
 *     confianza: 'indeterminado' (nunca se inventa un valor).
 * @param {Object} bloque1  { IGE, IZM, JM }  (Block #1, card #3)
 * @param {Object} bloque2  { XRR, MA }       (Block #2, cards #1 y #3)
 * @param {number} zona     nº de zona, 1-based (como en NUCZO/MA)
 * @returns {{ volumen: number|null, indeterminado: boolean, motivo: string|null }}
 *          motivo (solo si indeterminado): 'GEOMETRIA_2D' | 'XRR_NO_DISPONIBLE'
 *          | 'DATOS_INSUFICIENTES' | 'ZONA_SIN_INTERVALOS' | 'GEOMETRIA_NO_SOPORTADA'
 *          | 'ZONA_INVALIDA'
 */
function volumenZonaEfectivo(bloque1, bloque2, zona) {
  const b1  = bloque1 || {};
  const b2  = bloque2 || {};
  const ige = b1.IGE;
  const jm  = b1.JM  || 0;
  const izm = b1.IZM || 0;
  const xrr = b2.XRR || [];
  const ma  = b2.MA  || [];

  const indet = motivo => ({ volumen: null, indeterminado: true, motivo });

  if (!(zona >= 1)) return indet('ZONA_INVALIDA');
  if (jm > 0)        return indet('GEOMETRIA_2D');

  if (ige === 4) {
    const idx = zona - 1;
    const v = xrr[idx];
    if (idx >= izm || !Number.isFinite(v)) return indet('XRR_NO_DISPONIBLE');
    return { volumen: v, indeterminado: false, motivo: null };
  }

  if (ige === 1 || ige === 2 || ige === 3) {
    if (xrr.length < 2 || ma.length === 0) return indet('DATOS_INSUFICIENTES');
    let vol = 0, encontrado = false;
    for (let l = 0; l < ma.length; l++) {
      if (ma[l] !== zona) continue;
      const x1 = xrr[l], x2 = xrr[l + 1];
      if (!Number.isFinite(x1) || !Number.isFinite(x2)) return indet('XRR_NO_DISPONIBLE');
      encontrado = true;
      if (ige === 1)      vol += (x2 - x1);               // planar: área unidad 1 cm2
      else if (ige === 2) vol += Math.PI * (x2 * x2 - x1 * x1);       // cilíndrico: altura unidad 1 cm
      else                 vol += (4 / 3) * Math.PI * (x2 ** 3 - x1 ** 3); // esférico
    }
    if (!encontrado) return indet('ZONA_SIN_INTERVALOS');
    return { volumen: vol, indeterminado: false, motivo: null };
  }

  return indet('GEOMETRIA_NO_SOPORTADA');
}

/**
 * F10 — Compara el V introducido en la composición asistida con el volumen
 * efectivo de la zona destino (volumenZonaEfectivo). Si difieren, ACAB no lo
 * detecta: la masa realmente simulada pasa a ser m·(V_zona/V_tecleado), un
 * desajuste silencioso. La construcción del mensaje (i18n) queda en la capa
 * de UI, este función solo decide el estado.
 * @param {number} volumenIntroducido  V tecleado en el formulario [cm3]
 * @param {{volumen:number|null, indeterminado:boolean, motivo:string|null}} volEfectivo
 *          resultado de volumenZonaEfectivo
 * @param {number} [tol=1e-6]  tolerancia relativa
 * @returns {{ estado: 'coincide'|'no_coincide'|'indeterminado',
 *             volumenEfectivo: number|null, factor: number|null, motivo: string|null }}
 *          factor = V_zona/V_tecleado (relación entre la masa realmente
 *          simulada y la masa objetivo cuando 'no_coincide').
 */
function compararVolumenZona(volumenIntroducido, volEfectivo, tol = 1e-6) {
  if (!volEfectivo || volEfectivo.indeterminado)
    return { estado: 'indeterminado', volumenEfectivo: null, factor: null,
             motivo: volEfectivo ? volEfectivo.motivo : null };
  const vz = volEfectivo.volumen;
  const v  = volumenIntroducido;
  if (!(v > 0))
    return { estado: 'indeterminado', volumenEfectivo: vz, factor: null, motivo: 'V_INVALIDO' };
  const rel = Math.abs(vz - v) / Math.max(Math.abs(vz), Math.abs(v));
  if (rel > tol)
    return { estado: 'no_coincide', volumenEfectivo: vz, factor: vz / v, motivo: null };
  return { estado: 'coincide', volumenEfectivo: vz, factor: 1, motivo: null };
}

/* Export para node (tests); en el navegador quedan como globales. */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    AVOGADRO, parseChemFormula, computeComposition, validateEgrp,
    volumenZonaEfectivo, compararVolumenZona,
  };
}
