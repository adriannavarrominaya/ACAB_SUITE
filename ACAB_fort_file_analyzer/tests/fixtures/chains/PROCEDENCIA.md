# Procedencia de tests/fixtures/chains (analyzer)

Copia byte a byte de `output_chain_Te130_to_I131.txt`, cuya copia canónica
(junto con `inp.5_original`/`inp.5_tape22`/`inp.5_tape24`/
`input_chain_Te130_to_I131.txt` y su propio `PROCEDENCIA.md` con el detalle
completo de generación) vive en
`ACAB_inp_file_configurator/tests/fixtures/chains/`. Duplicada aquí para que
la suite de este repo sea autocontenida (regla de la suite: los fixtures
viven junto a los tests que los consumen), ya que `test_chains.py` solo
necesita el output de CHAINS, no los ficheros de entrada de ACAB.

SHA256 (idéntico al original, verificado 2026-07-25):
```
5327951BFA3CD014D5C6EDCA040514092B4D0B6A3A67969E9C6098131A0A3D8  output_chain_Te130_to_I131.txt
```

Caso oro (F9 del BACKLOG, Fase 1 de `runbook_F9_analisis_cadenas.md`): 3
cadenas por encima de PCNT=0.01, PTOT=100, P = 95.79 / 3.119 / 1.090 %,
cadena dominante TE130(N,G-g)→TE131(B-)→I131 con XSEC=1.1084E-11 (paso 1) y
DELTA=4.6210E-04 (paso 2).

No modificar sin re-verificar el original y sincronizar ambas copias.

## `output_chain_no_pathways_O16.txt` (F9d del BACKLOG, 2026-07-26)

Copia byte a byte (verificada con `Get-FileHash`, no hay copia canónica en
otro repo — este caso solo lo consume `leer_output_chains` del analyzer,
`chains_inventory.py` de inp-conf no lo duplica) de
`chains_O16/output_chain.txt`, generado por la **primera ejecución real
completa** del pipeline de F9 (11 isótopos del blanco TeO₂: 8 de Te + O16/
O17/O18, IFINAL=I131, NMAX=5, PCNT=0.01). Congelado tras detectar que
`leer_output_chains` lanzaba `ValueError: Campo no encontrado... NCHAIN`
contra este fichero — forma distinta a `output_chain_Te130_to_I131.txt`
cuando CHAINS **no encuentra ningún camino** INITIAL→IFINAL en ≤ NMAX
pasos (aquí, ningún isótopo de oxígeno decae a yodo): la cabecera
(IFLAG/INITIAL/IFINAL/NMAX/PCNT) está, pero no hay NCHAIN/NCH/PTOT ni
ningún bloque de cadena — solo el literal `THERE ARE NO PATHWAYS FOR
FORMATION OF NUCLIDE IFINAL`.

SHA256:
```
1FE86463516DEFF5F23FA916B0BD0A97DB66E543268E5CF6A83196CEBEC74227  output_chain_no_pathways_O16.txt
```

Confirmado que O17 (`INITIAL=80170`) y O18 (`INITIAL=80180`) del mismo
análisis real tienen **exactamente la misma forma** literal (difieren solo
en INITIAL) — no hace falta congelar fixtures propios para ellos, este
fichero cubre el caso los tres.

`leer_output_chains` detecta el literal `NO PATHWAYS FOR FORMATION OF
NUCLIDE` y devuelve `nchain=nch=0`, `ptot=0.0`, `cadenas=[]` en vez de
lanzar — ver docstring de la función y `test_chains.py`.

## `output_chain_TE128_to_I131.txt` (F9e del BACKLOG, 2026-07-26)

Copia byte a byte (sin copia canónica en otro repo, mismo criterio que
`output_chain_no_pathways_O16.txt`) de `chains_TE128/output_chain.txt`,
generado por la misma ejecución real que el fixture anterior (11 isótopos
del blanco TeO₂, IFINAL=I131, NMAX=5, PCNT=0.01), esta vez para el isótopo
TE128 (`INITIAL=521280`). Caso oro: NCHAIN=13, NCH=12, PTOT=0.02304 (2,3 %
— nótese que NO es 100: PTOT aquí es la probabilidad TOTAL de alcanzar
IFINAL, no una renormalización entre supervivientes de PCNT como en el
caso TE130→I131 de arriba; ambos son "PTOT" pero de magnitud muy distinta,
ver nota en la Tabla 2 / docstring de `leer_output_chains`). Las 12 cadenas
detalladas terminan TODAS en I131 (4 o 5 pasos cada una).

Congelado tras detectar el bug de causa raíz (F9e, hermano de C6 del
BACKLOG): `_CHAIN_STEP_RE` no toleraba un espacio inicial de relleno de
columna en el ORIGEN de un paso cuando el nucleido empieza por un símbolo
de una letra (yodo, "I") — p. ej. la línea " I129 (N,G-g)      I130
XSEC=1.1305E-09" de la cadena 2 no matcheaba y se perdía, truncando esa
cadena en TE128→TE129→I129 cuando el fichero real llega a I131. Arreglado
añadiendo `\s*` al principio del patrón. Casos oro que verifican el
arreglo:

- Cadena 2 (P=18.61 %): 4 pasos, el último con `hasta="I131"` (antes del
  fix, solo 2 pasos, truncada en I129).
- Cadena 3 (P=8.747 %): 5 pasos, el último con `hasta="I131"`; su
  cabecera de ruta compacta (redundante, no se parsea) ocupa DOS líneas
  de texto (`... I130 (N,G-g)     \n I131`) — confirma que el header
  multi-línea no rompe el parseo del bloque de pasos que sigue.

SHA256:
```text
1D1EA7B7289CB8AB2A3578FE2A08EA7DC7FD22AF970E503FB9C29EEEE0F3C6A7  output_chain_TE128_to_I131.txt
```
