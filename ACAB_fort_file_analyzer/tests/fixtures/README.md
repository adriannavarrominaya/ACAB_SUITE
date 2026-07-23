# Simulación de referencia (caso oro)
Origen: simulación v.5 "info thesis" (TeO2, MURR), usada en compare_simulaciones.py

## ref_sim_f7 (F7 del BACKLOG)

`tests/fixtures/ref_sim_f7/` es la MISMA física que `ref_sim` (idéntico
`acab.exe`/`DECAY.dat`/`XSECTION.dat`/`REACTIONS.dat`, mismo `inp.5` salvo
Blocks #7/#8), regenerada tras F7 con el formato sin compactación: 3 TIME
SETs en vez de 2 (irradiación y enfriamiento nunca comparten tarjeta). Este
fixture fue el que expuso que `leer_fort6_enfriamiento` trataba el token
RESTART siempre como "excluir" — con F7 el t=0 real puede caer en un límite
de tarjeta y aparecer como RESTART en vez de SHUTDOWN. Ver
`tests/fixtures/ref_sim_f7/PROCEDENCIA.md` para el detalle y los valores oro
(deben coincidir exactamente con los de `ref_sim` de abajo).

## Valores esperados (leídos del analyzer actual, 2026-07-07)
- A_pico I131 (enfriamiento): 1.6500e+04 Bq/cm3, en t_global = 3.753 h
  (= T_irr 0.00278 h + 3.75 h de enfriamiento; calcular_pico usa el eje global
  irradiación+enfriamiento y toma el máximo de la malla, sin interpolar)
- T_irr = 0.00278 h (3.17E-07 años, pulso de ~10 s) ; T_cool = 4.50 h (según inp.5)
- Malla de enfriamiento: 19 puntos, de 0.00 a 4.50 h en pasos de 0.25 h
  (dos time sets en el fort.6; la columna INITIAL se omite y RESTART es t=0)
- Nº de isotopos detectados en fort.6: 499 (tanto en irradiación como en enfriamiento)
- T1/2 de I131 usada: 8.0231 d (fuente: DECAY.dat)

## Verificado a mano contra el texto del fort.6
- CONCENTRATIONS(GRAM): O = 2.4688E-02, TE = 9.8478E-02 → total = 0.12317 g/cm3
  (el fichero incluye línea explícita "TOTAL  1.2317E-01"; secciones duplicadas
  BY INTERVAL y BY ZONE con valores idénticos)
- VOLUME OF ZONE: 1.00000E+00 CCM (útil para la conversión a actividad total)
- Primer valor de I131 en la sección de enfriamiento (columna RESTART, t=0):
  3.8420e+01 Bq/cm3 (línea 4139 del fort.6: "I131  0.000E+00 3.842E+01 5.690E+03 ...")
- Valor de I131 en t=0.25 h de enfriamiento: 5.6900e+03 Bq/cm3
- Último valor de I131 (t=4.50 h): 1.6490e+04 Bq/cm3 (ya pasado el pico de t=3.75 h)
- Átomos de I131 al final de la irradiación (sección NUMBER OF ATOMS):
  3.841E+07 átomos/cm3

## Cross-check de consistencia física (validación de la conversión átomos→actividad)
λ·N = ln(2)/T1/2 · N = 0.6931/(8.0231 d · 86400 s/d) · 3.841e7 ≈ 38.4 Bq/cm3,
que coincide con el valor RESTART del enfriamiento (3.8420e+01). La actividad de
I131 CRECE durante el enfriamiento (38 → 16500 Bq/cm3, pico en t=3.75 h) por
decaimiento del Te131/Te131m generado durante el pulso de irradiación: el pico del
producto está en la fase de enfriamiento, no al final de la irradiación.

## Notas para los tests
- Tolerancia recomendada: relativa 1e-3 (el fort.6 imprime 4-5 cifras significativas).
- Las secciones BY INTERVAL y BY ZONE están duplicadas con los mismos valores; los
  tests deben verificar que el parser no duplica isótopos ni timesteps por ello.
- PHOTON.dat: pendiente de localizar (no presente aún en fixtures/). La Fase 6 del
  runbook no puede empezar sin él; el fallback de GAMMA_I131 cubre mientras tanto.

## Métricas de optimización de producción (Fase 5) — observación sobre la ref_sim
La ref_sim NO es un buen caso para juzgar visualmente el ajuste de la curva de
saturación de I131, por la razón física ya documentada arriba: T_irr es un pulso
de ~10 s (0.00278 h) y el fort.6 solo imprime dos columnas de irradiación
(INITIAL y ese único instante), así que `calcular_saturacion` genera una curva
de 2 puntos que coincide con ACAB por construcción (A_teo(0)=0 y
A_teo(T_irr)=A_ACAB(T_irr) exactamente) — no hay margen para observar quemado
del blanco con solo 2 puntos. Los tests oro de "ajuste exacto" usan curvas
sintéticas con más puntos (`tools/test_metricas.py`) precisamente por esto.

Además, I131 se produce en esta simulación de forma indirecta (cadena
¹³⁰Te(n,γ)¹³¹Te/¹³¹ᵐTe → β⁻ → ¹³¹I, ver sección de cross-check más arriba): su
pico de actividad (1.65e4 Bq/cm³) ocurre en ENFRIAMIENTO, no al final de la
irradiación. Esto hace que, con la ref_sim, el rendimiento medio
(A_pico/T_irr ≈ 1.65e4/0.00278 ≈ 5.94e6 Bq/cm³/h) sea artificialmente enorme
frente a la ganancia marginal del último tramo de irradiación
(≈ 1.38e4 Bq/cm³/h, calculada sobre la actividad directa de I131 al final del
pulso) → `compensa_seguir = False`. Es el comportamiento correcto de la
fórmula tal como está definida en el runbook (A_pico/T_irr), pero para
isótopos de producción indirecta como I131 el rendimiento así definido mezcla
la actividad de enfriamiento con el tiempo de irradiación; anotado aquí para
que quien lea la memoria del TFG entienda por qué esta métrica concreta no es
representativa en simulaciones de pulso corto y conviene interpretarla junto
con la Sección 2 (pico por simulación), no de forma aislada.

La pureza radionucleídica de I131 en t_pico (3.753 h) con el criterio por
defecto (todos los isótopos de yodo presentes en el fort.6) da ≈ 99.9999998 %:
a esa hora de enfriamiento el resto de isótopos de I de vida corta generados
en el pulso ya se han desintegrado casi por completo. Valor oro usado también
como caso de humo en `tools/test_metricas.py` (con curvas sintéticas para el
caso exacto 80/20 %).

## Métricas de saturación (Fase 5, anotado 2026-07-09)
- A_sat(I131) con el caso base (XNORM=1): 4.0138e+6 Bq/cm3; t_50=192.61 h,
  coherente con ln2/λ. Con T_irr=10 s (2 timesteps), la comparación curva
  teórica vs ACAB es degenerada por construcción (anclaje en t_fin): la
  verificación significativa de la desviación queda pendiente de un caso de
  irradiación larga (p. ej. cuarto experimento).