# Procedencia de tests/fixtures/chains/iso_TE130_real

Fixture oro POSITIVO pendiente desde F9e (ver "F9e — causa raíz..." en
`ACAB_inp_file_configurator/tests/fixtures/chains/PROCEDENCIA.md`): en aquel
hotfix se corrigió `_monoisotopic_patch` para fijar `INPT=2` en el Bloque #1
del `inp.5` de cada `iso_<isótopo>/` (antes INPT=1 heredado de la
referencia, que ACAB interpreta como "elemento" y expande XCOMP a la
composición isotópica natural de Te en vez de dejar solo el isótopo puro),
pero no había binarios reales de ACAB disponibles para reejecutar el
pipeline y verificar el `fort.6` resultante. Congelado tras la primera
ejecución real POST-hotfix, sesión F9f (2026-07-26).

## Origen

Copia byte a byte de `fort.6` (y su `inp.5`) de
`C:\Simulaciones\Analisis de cadenas\iso_TE130\` — carpeta
`iso_TE130/` de un análisis de cadenas real generado y ejecutado por
`ACAB_inp_file_configurator` (11 isótopos del blanco TeO₂: 8 de Te + O16/
O17/O18, IFINAL=I131, NMAX=5, PCNT=0.01; misma ejecución real que ya dio
`output_chain_no_pathways_O16.txt`/`output_chain_TE128_to_I131.txt`, F9d/F9e,
esta vez con el código YA corregido). No regenerable sin los binarios reales
de ACAB — fuera del repo, referenciado aquí solo por trazabilidad.

`inp.5` de esta carpeta es **byte-idéntico** a `inp.5_iso_TE130`
(`ACAB_inp_file_configurator/tests/fixtures/chains/`, SHA256
`96A2B3671C471DB80202567E351540B6DF55FCE586C5A777FC3504A6F76F6095`,
verificado con `Get-FileHash`): confirma que el `inp.5` generado por la app
(patch monoisotópico con `INPT=2`) es exactamente el que se ejecutó de
verdad para producir este `fort.6` — cierra el círculo generación → ejecución
→ resultado.

## Caso oro (positivo, corrige la evidencia negativa de F9e)

Bloque #1 card #3 de `inp.5` (posición 8, INPT) = `2` ("read initial
concentrations as isotopes"); Bloque #5 declara un único nucleido, INUCL=
`521300` (TE130), XCOMP=`1.570000E-04` át/barn·cm = 1.570E20 át/cm³.

Eco `NUMBER OF ATOMS` (t=0, columna INITIAL) del `fort.6`: contiene
**SOLO TE130**, `C_i = 1.570E+20` át/cm³ — a diferencia del extracto INPT=1
(`fort6_iso_TE130_INPT1_invalido_extracto.txt` del repo inp-conf), que
mostraba los 8 isótopos de Te de abundancia natural. Confirma que el fix de
F9e (INPT=2) produce el inventario monoisotópico puro que exige el diseño
de F9 (Bloque #5 del runbook: "XCOMP copiado DIRECTAMENTE del eco, sin viaje
por masa").

Actividad de I131 durante el enfriamiento (sección `NUCLIDE RADIOACTIVITY,
DISINTEGRATIONS/SEC` del `fort.6`, serie completa verificada línea a línea):
pico **A_pico(I131) = 1.6500E+04** Bq/cm³ (alcanzado en el segundo TIME SET
de enfriamiento, entre t=3,75 h y t=4,00 h tras el fin de irradiación, con la
serie subiendo monótonamente hasta ese punto y decreciendo después —
`1.650E+04, 1.650E+04, 1.649E+04...`).

## SHA256 (verificado 2026-07-26)

```
5C51DBF31B5EA2F5777F3356F8833E01EC07C0623B83FF7A82DB96E453489280  fort.6
96A2B3671C471DB80202567E351540B6DF55FCE586C5A777FC3504A6F76F6095  inp.5
```

Cubierto por `tools/test_chains.py::test_leer_concentraciones_iniciales_iso_te130_real_positivo`.
No modificar sin re-verificar contra la carpeta de origen.
