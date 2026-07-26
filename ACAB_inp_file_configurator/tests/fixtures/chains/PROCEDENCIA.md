# Procedencia de tests/fixtures/chains

Fixtures del caso manual F9 (`acab_suite/runbook_F9_analisis_cadenas.md`, Fase 0),
congelados verbatim tal y como se generaron a mano una vez con los ejecutables
reales de ACAB 2008 y CHAINS.

## inp.5_original

Byte-idéntico a `ACAB_fort_file_analyzer/tests/fixtures/ref_sim/inp.5` (la
referencia canónica del tablón, ver su propio `PROCEDENCIA.md`), verificado con
`fc.exe /N` (sin diferencias) el 2026-07-25. Es el inp.5 de la simulación de
referencia (pulso de 10 s, blanco TeO2, espectro de la tesis) ANTES de aplicar
ningún patch de Bloque #11.

## inp.5_tape22 / inp.5_tape24

Copias de `inp.5_original` con un único patch en el Bloque #11, confirmado por
diff línea a línea (`fc.exe /N`, única línea distinta en los tres ficheros:
la línea 41, "Block #11 Type of run"):

| Fichero | IWP | IMTX | Delta frente a inp.5_original |
|---|---|---|---|
| `inp.5_original` | 1 | 0 | — |
| `inp.5_tape22` | 3 | 0 | IWP 1→3 (pathway analysis, escribe fort.22) |
| `inp.5_tape24` | 1 | 1 | IMTX 0→1 (escribe fort.24, ACAB para tras escribirlo) |

Nota sobre la decisión de diseño del runbook ("confirmar IWP 0→3"): el
`inp.5_original` NO tiene IWP=0 sino IWP=1 (ya es un run normal con tabla de
isótopos más importantes activada, ver Block#11 del manual). El delta real
de `tape22` es por tanto IWP 1→3, no 0→3; el resto de la frase (IMTX 0→1) es
exacto. Todo lo demás de los tres ficheros es byte-idéntico — ningún otro
campo cambia (XSECTION, historial, XNORM, NOTTS/ITSO incluidos).

## input_chain_Te130_to_I131.txt / output_chain_Te130_to_I131.txt

Generados ejecutando `chains.exe < input_chain_Te130_to_I131.txt >
output_chain_Te130_to_I131.txt` con `fort.22` (de la ejecución de
`inp.5_tape22`) y `fort.24` (de `inp.5_tape24`) presentes en el cwd.
IFLAG=2, IINICIAL=521300 (Te130), IFINAL=531310 (I131), NMAX=14, PCNT=0.01.

Caso oro verificado a mano y reproducido por lectura del fichero: NCH=3
cadenas por encima de PCNT, PTOT=100, P = 95.79 / 3.119 / 1.090 %, cadena
dominante TE130(N,G-g)→TE131(B-)→I131 con XSEC=1.1084E-11 (paso 1) y
DELTA=4.6210E-04 (paso 2) — coincide con la Fig. 1 del paper (vía directa,
sin pasar por el isómero TE131M).

## SHA256 (verificado 2026-07-25)

```
CE75BCD933299ACC9040343D1A03B086CF28ACC13E6A0237D8FB229426677CA  inp.5_original
E54CE4803F5ADC8A9A7DFDC384485C8C6D85DBCB9DDCAFB9246C7C0C9DE7B7B  inp.5_tape22
764D7FFAEF4541A88EC0E3BEDB57012474877DACF5FA9F3B64E46812D0D0564  inp.5_tape24
4538BDB0BCA6A4D13C2BE4FDA20930B278271F31C4EA52710921591186A6076  input_chain_Te130_to_I131.txt
5327951BFA3CD014D5C6EDCA040514092B4D0B6A3A67969E9C6098131A0A3D8  output_chain_Te130_to_I131.txt
```

## Verificación de unidades (Fase 0 del runbook)

`inp.5_original` tiene INPT=1 (Bloque #1, card #3, posición 8: "Read initial
concentrations as elements") ⇒ XCOMP del Bloque #5 está en átomos/barn·cm
(1 barn = 1e-24 cm² ⇒ átomos/cm³ = XCOMP × 1e24).

XCOMP(Te, ZZAAAS elemental 520000) = 4.6448E-04 → 4.6448E20 átomos/cm³.

Suma de C_i (t=0, eco `INITIAL CONCENTRATIONS`/tabla `NUMBER OF ATOMS` del
`fort.6` de `ref_sim`, mismo inp.5 byte-idéntico) de los 8 isótopos de Te con
abundancia natural no nula (TE120, TE122, TE123, TE124, TE125, TE126, TE128,
TE130): 4.6451E20 átomos/cm³.

Coincide dentro del redondeo de imprenta del fort.6 (4 cifras significativas
por isótopo, ~0,006 % de desviación acumulada) — confirma que el Bloque #5
del inp.5 y el desglose isotópico del fort.6 comparten unidad sin conversión
adicional, tal y como asume el diseño de F9 (patch monoisotópico con XCOMP
copiado directamente del eco). Contraste de control con el O (520000→80000,
XCOMP=9.2896E-04 → 9.2896E20 át/cm³ vs. Σ(O16+O17+O18, t=0)=9.28911E20
át/cm³): mismo orden de acuerdo.

No modificar estos ficheros sin re-verificar el diff de Bloque #11 y los
valores de esta nota.

## inp.5_iso_TE130 / input_chain_generated_TE130_to_I131.txt

Casos oro de regresión de bytes de la Fase 2 (generación), a diferencia de
los ficheros anteriores (ejecutados a mano con los binarios reales): estos
dos los produce la propia app (`chains_analysis.generate_chains_analysis`)
a partir de `inp.5_original` como referencia, isótopo TE130
(C_i=1.57E20 át/cm³, el mismo valor verificado en la nota de unidades de
arriba), IFINAL=I131, NMAX=5, PCNT=0.01 — verificados a mano una vez
(2026-07-26) y congelados como el "caso oro construido a mano" que exige el
runbook para el patch monoisotópico del Bloque #5:

- `inp.5_iso_TE130`: idéntico a `inp.5_original` salvo Bloque #2 NUCZO
  (`2` → `1`, ajuste necesario no explícito en el runbook pero obligatorio
  por el formato — ver docstring de `chains_analysis.py`) y Bloque #5
  (`520000 80000` / `4.644800E-04 9.289600E-04` → `521300` /
  `1.570000E-04`, INUCL=ZZAAAS(TE130) y XCOMP=C_i×1e-24). Todo lo demás
  byte-idéntico.
- `input_chain_generated_TE130_to_I131.txt`: generado con
  `chains_handler.write_chains_inp` (IFLAG=2, INITIAL=521300, IFINAL=531310,
  NMAX=5, PCNT=0.01) — mismo contenido NUMÉRICO que
  `input_chain_Te130_to_I131.txt` de más arriba salvo NMAX/PCNT (los de
  este caso de prueba, no los NMAX=14/PCNT=0.01 del caso manual) y las
  etiquetas de campo (`INITIAL`/`Te-130` en vez de `IINICIAL`/`Te130`):
  chains.exe hace una lectura FORTRAN posicional, las etiquetas son solo
  para lectura humana y no afectan al resultado.

SHA256 (verificado 2026-07-26):
```
112649CB045C61D9667BB6CDCE85DBDA0558C945376F7193C9CA621BF20ABD33  inp.5_iso_TE130
03BB237BC3331567FD2D4524CD3D40F44FCC5EEF7E2655B5F20DBA654ECD66B8  input_chain_generated_TE130_to_I131.txt
```
