# Procedencia de ref_sim_f7

Variante de [[ref_sim]] (misma malla física, misma carpeta origen `Simulacion
v.5 - info thesis`) regenerada con el formato de Blocks #7/#8 **sin
compactación** introducido en F7 del BACKLOG (`acab_suite/BACKLOG.md`):
irradiación y enfriamiento nunca comparten tarjeta, cada fase se trocea por
separado en grupos de <=10 tiempos.

Generada re-ejecutando `acab.exe` (mismo binario, `DECAY.dat`, `XSECTION.dat`
y `REACTIONS.dat` que `ref_sim`) sobre un `inp.5` idéntico a
`tests/fixtures/ref_sim/inp.5` salvo en Blocks #7/#8 (regenerados con
`buildBlocks78` tras F7) y Block #11 NOTTS (2→3, una tarjeta más). Verificado
2026-07-23. SHA256 fort.6:
70e96cca81b183003f2c6a2d1c60695986be5d97210069f8cf4454b60f0ffeca

## Qué cambia frente a ref_sim
- `ref_sim`: 2 TIME SETs (tarjeta 1 mezcla el único paso de irradiación con 9
  de enfriamiento; tarjeta 2 continúa el enfriamiento con RESTART como
  duplicado del último valor de la tarjeta 1).
- `ref_sim_f7`: 3 TIME SETs (tarjeta 1 = irradiación pura; tarjeta 2 = primeros
  10 pasos de enfriamiento con **RESTART marcando el t=0 real** — la
  transición irr→cool cae exactamente en el límite de tarjeta, así que ACAB
  usa el token RESTART en vez de SHUTDOWN para ese punto; tarjeta 3 continúa
  con los 8 pasos restantes, RESTART aquí sí es un duplicado).

Este caso es el que expuso el bug de `leer_fort6_enfriamiento` (RESTART
tratado siempre como "excluir", perdiendo el t=0 real cuando la transición cae
en un límite de tarjeta): el fix trata RESTART igual que SHUTDOWN (valor 0.0)
y deja que la deduplicación por "tiempo ya visto" decida si es el punto nuevo
o un duplicado. Ver `fort_analyzer.py::leer_fort6_enfriamiento`.

## Valores oro (deben coincidir EXACTAMENTE con los de ref_sim — misma física)
- 19 timesteps de enfriamiento, 0.00 a 4.50 h en pasos de 0.25 h, sin
  duplicados (fusión de los 3 TIME SETs).
- A_pico(I131) = 1.6500e4 Bq/cm³, t_pico = 3.753 h (fase enfriamiento).
- pureza_serie: t_cruce = 0 (alcanzado_en_fin_irradiacion), P(t_pico) ≈
  99.99999987 %.
- actividad_especifica_yodo_serie: valor_destacado_MBq_g =
  4505547272.634922 en t_destacado_h = 0.0 (idéntico a ref_sim, F2b).

No modificar: si se regenera este fixture, re-verificar los valores oro de
arriba (deben seguir coincidiendo con los de `ref_sim`, es la misma física con
distinto agrupado de tarjetas) y actualizar el SHA256.
