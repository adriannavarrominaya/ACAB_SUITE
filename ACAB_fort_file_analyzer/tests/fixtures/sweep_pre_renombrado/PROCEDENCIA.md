# `sweep_manifest.json` — cálculo paramétrico de espectro, 9 reactores (PRE-renombrado)

## Qué es

Copia **byte-idéntica** del `sweep_manifest.json` REAL del cálculo paramétrico
de espectro de nueve reactores del TFG, generado el **2026-07-13** con la
versión de la app anterior al renombrado terminológico
«barrido paramétrico» → «cálculo paramétrico».

Origen: `…/TFG/Documentacion/ACAB/barridos/Barrido 5/sweep_manifest.json`
(nueve espectros CONDERC del OIEA: LANL-OWR, Cf252, MURR-G1, HFR-C3, Phenix,
ITER-DT, HFIR-VXF3-AD, SCK-BR2, LR-0-Void).

## Para qué sirve

Es el **caso oro de compatibilidad hacia atrás** del renombrado, por el lado del
analyzer: `leer_sweep_manifest` y la pestaña **Optimización** tienen que seguir
abriendo los manifiestos ya generados, sin avisos ni migraciones. Congela la
forma que escribía la app ANTES del cambio:

- nombre de fichero `sweep_manifest.json` (no se renombró),
- clave `sweep_type` con el valor `"spectrum"` — el que resuelve la etiqueta de
  la UI vía la clave i18n `optim.type_spectrum`, cuyo TEXTO sí cambió
  («barrido espectral» → «cálculo paramétrico de espectro») pero cuya CLAVE no,
- `params.espectro` de cada simulación, que es lo que
  `ACABOptim.spectrumRowLabel` usa como etiqueta de fila,
- las tres fracciones espectrales (`frac_termica`/`frac_epitermica`/
  `frac_rapida`) que alimentan el eje X numérico de U4b,
- **sin** la clave `excluded_base_files` (anterior a C4 del BACKLOG).

Consumido por `tools/test_fort_analyzer.py` (`test_sweep_manifest_pre_renombrado`)
y `tools/test_optim_utils.js`. Copia hermana en
`ACAB_inp_file_configurator/tests/fixtures/sweep_pre_renombrado/`; se duplica en
vez de compartirse porque la suite de cada repo es autocontenida.

## No editar

Si se edita, deja de ser un manifiesto real anterior al cambio y el test deja
de probar lo que dice probar. Para casos nuevos, añade fixtures aparte.
