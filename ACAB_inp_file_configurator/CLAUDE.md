<!-- Guardar como: ACAB_inp_file_configurator/CLAUDE.md -->

# ACAB INP File Configurator

App web Flask (monousuario, 127.0.0.1:5000) para crear, cargar, validar y generar
ficheros de entrada `inp.5` de ACAB 2008 (formato FORTRAN libre, 14 bloques), con
herramienta integrada para ficheros CHAINS. Parte de la suite del TFG (ver CLAUDE.md
de la carpeta padre).

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
- `static/js/app.js` — lógica de UI y `validateAll()` con las validaciones cruzadas
  V01–V25. Toda validación nueva sigue esa numeración y se cubre en `tools/test_validate_all.js`.
- `static/js/calc_utils.js` — funciones de cálculo PURAS (sin DOM), testeables con
  node. Todo cálculo nuevo de frontend va aquí con su test, no dentro de app.js.
- `static/js/sweep_utils.js` — funciones PURAS del barrido paramétrico (mallas
  `buildBlocks78`/`calcularVectorTiempos` compartidas con el generador temporal,
  `buildFluxPatches`/`buildMassPatches`/`buildTimePatches`, `parseSweepValues`,
  `proposeSuffix`). Test: `tools/test_sweep_utils.js`.
- `sweep_writer.py` + `static/js/sweep.js` + pestaña "Barrido" en `index.html` —
  generador de barridos: el cliente calcula un `patch` por simulación y el
  endpoint genérico `/api/sweep` lo fusiona (merge recursivo) sobre el fichero
  base, escribe con `_write_inp5`, verifica round-trip, copia la carpeta base y
  escribe manifest/README/scripts. Test: `tools/test_sweep_endpoint.py`.
- `static/data/` — `atomic_data.json` (masas atómicas CIAAW), `egrp_presets.json`.
- `runner.py` — **común de la suite, mantener sincronizado** con la copia de
  `COLLAPS_inp_file_configurator/runner.py`: motor de ejecución single/batch
  (Fase R3 del runbook runner v2). `app.py` expone `/api/run`, `/api/run/config`,
  `/api/run/status` (enriquecido con `output_exists`/`workdir` para single y
  `root` para batch, para el botón "Abrir en Fort Analyzer") y `/api/run/cancel`.
  Config de invocación (exe_name, required_files, output_file, timeout_s) en
  `acab_suite/README.md` §"Invocación de los códigos". Test: `tools/test_runner.py`,
  `tools/test_run_endpoints.py`.
- `/api/run/batch` (Fase R4 del runbook runner v2) — ejecución en cola de un
  barrido completo desde la pestaña "Barrido": body `{root, folders?, overwrite}`;
  si no se pasan `folders` los lee de `root/sweep_manifest.json` (404 si no
  existe). Cada subcarpeta lleva su propia copia del ejecutable (la sweep
  copia la carpeta base), así que el `cmd_template` pasado a `runner.start_batch`
  usa el marcador `{workdir}` para resolverse por-job; `batch_results.json`
  queda en la raíz. UI en `static/js/sweep.js` (panel tras generar + "Ejecutar
  un barrido existente"), pestaña Barrido en `index.html`. Test:
  `tools/test_run_batch_endpoint.py`.
- `chains_handler.py` + `templates/chains.html` + `static/js/chains.js` — utilidad CHAINS.
- `docs/Block#*.md`, `docs/chainsCode.md`, `docs/inp.5.md` — manual del formato.
  **Fuente de verdad**: ante cualquier duda de formato o semántica de un parámetro,
  consultar aquí antes que suponer. Directorio de solo lectura: no editar.
- `generador_acab.py` — [LEGACY] GUI Tkinter de mallas temporales; su lógica ya está extraída a static/js/sweep_utils.js (buildBlocks78) y el generador web de la pestaña temporal la usa. No invertir más en él.
- `examples/` — ficheros inp.5 reales; casos oro de regresión.

## Tests (obligatorio en verde antes de cada commit)

```bash
python tools/regression_roundtrip.py examples/<ficheros oro>
python tools/test_parser_robustness.py examples/<inp.5 de referencia>
node tools/test_calc_utils.js
node tools/test_validate_all.js
node tools/test_sweep_utils.js
python tools/test_sweep_endpoint.py
python tools/test_runner.py
python tools/test_run_endpoints.py
python tools/test_run_batch_endpoint.py
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
- El writer no debe fabricar valores silenciosos: lista de reales vacía donde se
  esperan datos → error claro con el nombre del campo (comportamiento actual, conservar).
- INPT condiciona la interpretación del Bloque #5 (1/2 = átomos/barn·cm, 3 = g/cc);
  la composición asistida y `compute_xcomp` NO soportan INPT=2.
- Los ficheros del repo mezclan finales de línea CRLF/LF; no hacer commits que
  renormalicen líneas en masa.
