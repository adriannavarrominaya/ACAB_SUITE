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

/* Export para node (tests); en el navegador quedan como globales. */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AVOGADRO, parseChemFormula, computeComposition, validateEgrp };
}
