<!-- Guardar como: ACAB_inp_file_configurator/CLAUDE.md -->

# ACAB INP File Configurator

App web Flask (monousuario, 127.0.0.1:5000) para crear, cargar, validar y generar ficheros de entrada `inp.5` de ACAB 2008 (formato FORTRAN libre, 14 bloques), con herramienta integrada para ficheros CHAINS. Parte de la suite del TFG (ver CLAUDE.md de la carpeta padre).

## Arranque y stack

- `C:\venv\acab-venv\Scripts\python app.py` (Windows) / `venv/bin/python app.py` — abre el navegador solo.
- Flask + waitress; frontend Bootstrap 5.3 + JS vanilla (sin build step, sin frameworks).
- Dependencias: solo las de `requirements.txt` + stdlib. No añadir dependencias sin necesidad clara.

## Ficheros clave

- `acab_parser.py` — `ACABParser.read_inp5()`: parser de los 14 bloques. Tokenizador
  FORTRAN libre (D-exp, bare-exp tipo `3.2336+27`, comentarios con `<`). Los errores
  deben incluir el bloque en curso y el token ofensivo (`_ctx_msg`).
- `app.py` — rutas + writer `_write_inp5()` y `_sci(v, prec=6)`. TODO fichero inp.5
  que salga de la app pasa por `_write_inp5`; nunca duplicar lógica de formato.
- `static/js/app.js` — lógica de UI y `validateAll()` con las validaciones cruzadas V01–V25. Toda validación nueva sigue esa numeración y se cubre en `tools/test_validate_all.js`.
- `static/js/calc_utils.js` — funciones de cálculo PURAS (sin DOM), testeables con node. Todo cálculo nuevo de frontend va aquí con su test, no dentro de app.js.
- `static/js/sweep_utils.js` — funciones PURAS del barrido paramétrico (mallas `buildBlocks78`/`calcularVectorTiempos` compartidas con el generador temporal, `buildFluxPatches`/`buildMassPatches`/`buildTimePatches`, `parseSweepValues`, `proposeSuffix`). Test: `tools/test_sweep_utils.js`.
- `sweep_writer.py` + `static/js/sweep.js` + pestaña "Barrido" en `index.html` —  generador de barridos: el cliente calcula un `patch` por simulación (y, para el barrido espectral, también un `coll_patch`) y el endpoint genérico `/api/sweep` fusiona el `patch` (merge recursivo) sobre el fichero base, escribe con `_write_inp5`, verifica round-trip, copia la carpeta base y escribe manifest/README/scripts; si hay `coll_patch`, además regenera `<sim>/collaps/COLL.inp` vía `coll_writer.py` (422 si `base_folder` no tiene `collaps/COLL.inp`). Al copiar la carpeta base se excluyen salidas viejas según `sweep_type` (C4 del BACKLOG): en el espectral, salidas de ACAB Y de COLLAPS (`_ACAB_OUTPUT_FILES`/`_COLLAPS_OUTPUT_FILES`); en flujo/masa/temporal, solo las de ACAB (XSECTION.dat/FLUX.inf se conservan a propósito, espectro compartido). Lo excluido queda anotado en `sweep_manifest.json` (`excluded_base_files`). Test: `tools/test_sweep_endpoint.py`.
- `static/js/conderc_import.js` — funciones PURAS (patrón `calc_utils.js`) del barrido espectral (Fase P2 del runbook de barrido espectral): `parseConderc()` (parsea espectros CONDERC del OIEA con checksum contra la línea TOTAL), `spectralIndices()` (fracciones térmica/epitérmica/rápida, D8) y `buildSpectrumPatch()` (NGROUP con signo, CX, FT). Test: `tools/test_conderc_import.js` con el fixture `112_MURR-G1.txt`.
- `coll_writer.py` — parser+writer de `COLL.inp` para el barrido espectral (D9), limitado a NGROUP/FF, CX (`6E12.5`) y FT (`6E12.5`); conserva el resto de tarjetas del `COLL.inp` base. **Copia sincronizada en semántica** con `collaps_parser.py`/`_write_coll_inp()` del repo `COLLAPS_inp_file_configurator` (fuente de verdad de formato: `docs/COLLAPS.md` de aquel repo) — si cambia el formato de COLL.inp allí, replicar aquí. Test: `tools/test_coll_writer.py` (round-trip con el fixture de 211 grupos).
- `static/data/` — `atomic_data.json` (masas atómicas CIAAW), `egrp_presets.json`.
- `runner.py` — **común de la suite, mantener sincronizado** con la copia de   `COLLAPS_inp_file_configurator/runner.py`: motor de ejecución single/batch (Fase R3 del runbook runner v2). `app.py` expone `/api/run`, `/api/run/config`, `/api/run/status` (enriquecido con `output_exists`/`workdir` para single y `root` para batch, para el botón "Abrir en Fort Analyzer") y `/api/run/cancel`.
  Config de invocación (exe_name, required_files, output_file, timeout_s) en `acab_suite/README.md` §"Invocación de los códigos". Test: `tools/test_runner.py`,  `tools/test_run_endpoints.py`.
- `/api/run/batch` (Fase R4 del runbook runner v2) — ejecución en cola de un barrido completo desde la pestaña "Barrido": body `{root, folders?, overwrite}`; si no se pasan `folders` los lee de `root/sweep_manifest.json` (404 si no existe). Cada subcarpeta lleva su propia copia del ejecutable (la sweep copia la carpeta base), así que el `cmd_template` pasado a `runner.start_batch` usa el marcador `{workdir}` para resolverse por-job; `batch_results.json` queda en la raíz. UI en `static/js/sweep.js` (panel tras generar + "Ejecutar un barrido existente"), pestaña Barrido en `index.html`. Test: `tools/test_run_batch_endpoint.py`.
- `app.py` — `/api/browse-folder` (diálogo nativo de carpeta vía tkinter en subprocess, ya existía para la pestaña Barrido) y `/api/save-to-folder` (U2 del BACKLOG: escribe `<folder>/inp.5` con `_write_inp5`, 409 con `exists:true` si ya existe y `overwrite` no es `true`). Botón primario "Guardar en carpeta…" en la barra de navegación (`static/js/app.js`); recuerda la última carpeta usada en `localStorage` (`acab-inp-last-save-folder`) y la ofrece como valor inicial en el siguiente guardado y como prefijo del workdir de ejecución (U3: `loadRunConfig`, con prioridad sobre `default_workdir`). "Descargar" (antes "Guardar como…", incluyendo el flujo `showSaveFilePicker` en navegadores Chromium) queda como opción secundaria sin cambios de lógica. Test: `tools/test_save_to_folder.py` (no cubre `/api/browse-folder`, subprocess con tkinter — se verifica a mano, igual que en el resto de la suite).
- `sweep_manifest_view.py` (U6 del BACKLOG) — vista de SOLO LECTURA de un barrido ya generado: `build_manifest_view(root)` lee `sweep_manifest.json` (+ `batch_results.json` si existe) y añade, por simulación, `value_label` (el NOMBRE del espectro en el barrido espectral — criterio compartido con la pestaña Optimización del analyzer, nunca un volcado de `params` — o `None` si no se puede derivar, p. ej. `sweep_type` desconocido) y `fort6_exists`. Tolera manifests PRE-C4 sin `excluded_base_files` (degrada a `[]`, nunca rompe). `app.py` expone `GET /api/sweep/manifest?root=<carpeta>` (404 si no hay manifest, 422 si es JSON inválido). `static/js/sweep.js` unifica con esto el flujo de carga: cargar una carpeta (patrón browse-folder) SIEMPRE muestra esta vista; "Ejecutar" (`btn-sweep-loaded-run`) es una acción sobre el barrido ya cargado que reutiliza `startSweepBatchRun`/el panel de ejecución de la Fase R4, no un segundo camino de carga. Test: `tools/test_sweep_manifest_view.py`.
- `chains_handler.py` + `templates/chains.html` + `static/js/chains.js` — utilidad CHAINS.
- `docs/Block#*.md`, `docs/chainsCode.md`, `docs/inp.5.md` — manual del formato.
  **Fuente de verdad**: ante cualquier duda de formato o semántica de un parámetro, consultar aquí antes que suponer. Directorio de solo lectura: no editar.
- `generador_acab.py` — [LEGACY] GUI Tkinter de mallas temporales; su lógica ya está extraída a static/js/sweep_utils.js (buildBlocks78) y el generador web de la pestaña temporal la usa. No invertir más en él.
- `examples/` — ficheros inp.5 reales; casos oro de regresión, organizados en subcarpetas (`Inp5/`, `Simulation/`, `Spectra/`). Los 4 patrones oro del round-trip están en `examples/Inp5/exp1.inp.5`…`exp4.inp.5`.
- `tests/fixtures/spectra/` — espectros CONDERC de referencia para el barrido espectral: `112_MURR-G1.txt` (caso oro del parser: 112 grupos, energías en eV decrecientes, línea TOTAL como checksum), `sneg_2-6` (extremo grueso, 6 grupos: test del aviso direccional) y `br2-621` (extremo fino, 621 grupos).
- `tests/fixtures/COLL.inp` — COLL.inp de referencia (211 grupos, NGROUP=-211)
  para el round-trip de `coll_writer.py`. Regla: los fixtures viven junto a los
  tests que los consumen — la suite de este repo es autocontenida y no depende
  de ficheros de otros repos.

## Tests (obligatorio en verde antes de cada commit)

```bash
python tools/regression_roundtrip.py "examples/Inp5/exp1.inp.5" "examples/Inp5/exp2.inp.5" "examples/Inp5/exp3.inp.5" "examples/Inp5/exp4.inp.5"
python tools/test_parser_robustness.py "examples/Inp5/exp1.inp.5"
node tools/test_calc_utils.js
node tools/test_validate_all.js
node tools/test_sweep_utils.js
python tools/test_sweep_endpoint.py
python tools/test_runner.py
python tools/test_run_endpoints.py
python tools/test_run_batch_endpoint.py
node tools/test_conderc_import.js
python tools/test_coll_writer.py
python tools/test_save_to_folder.py
python tools/test_sweep_manifest_view.py
```

Los tests nuevos se añaden en `tools/` siguiendo el estilo existente (scripts
autocontenidos ejecutables directamente, sin framework).

## Convenciones y gotchas

- **i18n obligatorio**: ninguna cadena de UI hardcodeada. Atributo `data-i18n` +
  entrada en `static/i18n/es.json` y `en.json` (ambos, siempre).
- **Round-trip como invariante**: parsear → regenerar debe conservar la semántica.
  Cualquier cambio en parser o writer se verifica con `regression_roundtrip.py`.
- **Limitación documentada, no "arreglar" sin decisión explícita**: `_sci` formatea
  reales a 7 cifras significativas (README §10); originales con más cifras se
  redondean al regenerar.
- **`regression_roundtrip.py` y `test_parser_robustness.py` no tienen fichero por
  defecto**: sin argumentos, imprimen el `__doc__` y salen con código 2 (no
  confundir con "todo OK"). Los 4 "patrones oro" (`exp1.inp.5`…`exp4.inp.5`, 6
  decimales) son los únicos ficheros de `examples/` pensados para el round-trip;
  el resto de `examples/` (`inp (N).5`, `Activation of TeO2 Experiment 1.5`, etc.)
  tiene valores con más de 7 cifras significativas y falla el round-trip por la
  limitación de precisión de arriba — eso es esperado, no una regresión.
- El writer no debe fabricar valores silenciosos: lista de reales vacía donde se
  esperan datos → error claro con el nombre del campo (comportamiento actual, conservar).
- INPT condiciona la interpretación del Bloque #5 (1/2 = átomos/barn·cm, 3 = g/cc);
  la composición asistida y `compute_xcomp` NO soportan INPT=2.
- Los ficheros del repo mezclan finales de línea CRLF/LF; no hacer commits que
  renormalicen líneas en masa.
