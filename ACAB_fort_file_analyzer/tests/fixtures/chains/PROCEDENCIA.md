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
