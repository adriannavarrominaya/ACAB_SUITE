# Procedencia de ref_sim_f7_irr2sets

Variante sintética de [[ref_sim]] (mismo material, `acab.exe`, `DECAY.dat`,
`XSECTION.dat` y `REACTIONS.dat` que `ref_sim`/[[ref_sim_f7]]) pensada para
ejercitar una fase de **irradiación que ocupa más de una tarjeta** de
Blocks #7/#8 (formato F7, sin compactación): esto es lo que expuso el bug de
`leer_fort6_irradiacion` (analyzer) que solo leía la PRIMERA tabla NUMBER OF
ATOMS y descartaba el resto — con 2 tarjetas de irradiación la serie se
cortaba en el final de la primera.

Generada re-ejecutando `acab.exe` sobre un `inp.5` derivado de
`tests/fixtures/ref_sim/inp.5` (mismo Bloque #5 — 0.1231 g TeO2 — y mismo
Bloque #3 — espectro de la tesis) con una malla temporal distinta,
construida con `buildBlocks78` (`sweep_utils.js`, inp-conf):

- Irradiación: 2 tramos de 10 pasos de 0.25 h (0.25→2.5 h y 2.75→5.0 h) → 2
  tarjetas puras de irradiación (`MMN=MOUT=10` cada una), NOTTS pasa a 4.
- Enfriamiento: 2 tramos (10 + 8 pasos de 0.25 h, 0.25→4.5 h, igual malla que
  `ref_sim_f7`) → 2 tarjetas puras de enfriamiento.

Verificado 2026-07-23. SHA256 fort.6:
de701ecd82981cc87060027cd786a6bb5c3fa99653c51aef8fc212489f01a33

## Estructura de TIME SETs en el fort.6
1. Irradiación, tarjeta 1: `NUMBER OF ATOMS` con cabecera `INITIAL 2.50E-01 …
   2.50E+00` (10 puntos nuevos).
2. Irradiación, tarjeta 2 (misma fase, sin reinicio de reloj): cabecera
   `INITIAL RESTART 2.75E+00 … 5.00E+00` — RESTART duplica el ÚLTIMO valor de
   la tarjeta 1 (reloj de irradiación acumulado, nunca se reinicia entre
   tarjetas de la MISMA fase). Verificado a mano: I131 en t=2.50h (tarjeta 1,
   última columna) = 1.141E+13 át/cm³, e I131 en la columna RESTART de la
   tarjeta 2 = 1.141E+13 át/cm³ — idénticos.
3-4. Enfriamiento, 2 tarjetas: misma mecánica que `ref_sim_f7` (RESTART de la
   tarjeta 3 marca el t=0 real de enfriamiento, transición cayendo en un
   límite de tarjeta; RESTART de la tarjeta 4 es un duplicado de
   continuación).

## Arreglo (analyzer, fort_analyzer.py)
`leer_fort6_irradiacion` solo buscaba la PRIMERA aparición de `NUMBER OF
ATOMS` y paraba en el literal `"2. TIME SET"`. Reescrita para fusionar TODAS
las tablas `NUMBER OF ATOMS` bajo `CONCENTRATIONS DURING IRRADIATION BY
INTERVAL` (excluyendo las `BY ZONE` duplicadas, mismo criterio que
`leer_fort6_enfriamiento`), con INITIAL deduplicado (solo cuenta una vez, de
la primera tabla) y RESTART excluido siempre (en el alcance actual de pulso
único, NOPUL=0, el reloj de irradiación nunca se reinicia entre tarjetas de
irradiación, así que RESTART aquí SIEMPRE es un duplicado de continuación —
a diferencia del RESTART de enfriamiento, que sí puede ser genuino).

## Valores oro
- Serie de irradiación fusionada: INITIAL + 20 puntos = 21 timesteps, de 0.00
  a 5.00 h en pasos de 0.25 h, sin duplicados, estrictamente creciente.
- I131 en t=2.50 h (tarjeta 1) = I131 en la columna RESTART de la tarjeta 2 =
  1.141E+13 át/cm³ (verificado a mano contra el texto del fort.6, líneas 2896
  y 5418).
- I131 al final de la irradiación (t=5.00 h) = 2.622E+13 át/cm³.
- Serie de enfriamiento: 19 puntos (0.00-4.50 h, igual malla que
  `ref_sim_f7`), sin duplicados.
- Pico de I131: A_pico ≈ 2.961e7 Bq/cm³ en t_global ≈ 7.5 h (T_irr=5.0h +
  2.5h de enfriamiento) — no comparable con el pico oro de `ref_sim`
  (1.6500e4 Bq/cm³), es una simulación distinta (pulso continuo de 5h vs.
  pulso de ~10s): sirve solo para verificar que la fusión multi-tarjeta de
  `leer_fort6_irradiacion` funciona, no como caso oro de física.
- Test adicional: las tablas `BY ZONE` (duplicadas, mismos valores) no deben
  contarse como tarjetas nuevas — el nº de puntos fusionados no cambia
  aunque existan.

No modificar: si se regenera este fixture, re-verificar los valores oro de
arriba (en especial la igualdad I131 t=2.50h == RESTART tarjeta 2) y
actualizar el SHA256.
