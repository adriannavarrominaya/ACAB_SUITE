<!-- Guardar como: COLLAPS_inp_file_configurator/CLAUDE.md -->

# COLLAPS INP File Configurator

App web Flask (monousuario, 127.0.0.1:5002) para crear, cargar, validar y generar el fichero de entrada `COLL.inp` de COLLAPS (utilidad de colapsado de espectros/librerías asociada a ACAB 2008). Es la app más pequeña de la suite y sirve de banco de pruebas para patrones nuevos antes de replicarlos en las otras (ver CLAUDE.md de la carpeta padre).

## Arranque y stack

- `C:\venv\acab-venv\Scripts\python app.py` / `venv\Scripts\python app.py` — puerto 5002 por defecto
  (`--port` o variable `PORT`).
- Flask + waitress; frontend Bootstrap 5.3 + JS vanilla. Dependencias: solo
  requirements.txt (flask, waitress).

## Ficheros clave

- `collaps_parser.py` — `COLLAPSParser.read_coll_inp()`: parser de las 9 tarjetas
  Mismo tokenizador FORTRAN que la suite (D-exp, bare-exp).
  ⚠ Copia sincronizada: si se modifica este parser, replicar en   `ACAB_inp_file_configurator/coll_writer.py`.
- `app.py` — rutas + writer `_write_coll_inp()`. Formatos de salida que hay que respetar: Card #1 y Card #5 en `2I4` fijo; listas de reales (CX, FT) en bloques `6E12.5` vía `_floats_block_e125`. 
  Todo COLL.inp generado pasa por este writer.
  ⚠ Copia sincronizada: si se modifica el writer, replicar en  `ACAB_inp_file_configurator/coll_writer.py`.
- `static/js/app.js` — UI + `validateAll()` (V01, V03, V04, …). Validaciones nuevas siguen la numeración.
- `static/i18n/es.json`, `en.json` — i18n completo de la UI.
- `docs/COLLAPS.md` — manual del formato. **Fuente de verdad** ante cualquier duda de semántica; solo lectura, no editar.
- `runner.py` — núcleo de ejecución (single + batch/cola) sin dependencias de Flask, instancia única a nivel de módulo (`start`, `start_batch`, `status`, `cancel`). **Común de la suite — mantener sincronizado con `ACAB_inp_file_configurator/runner.py`.**
- `app.py` también expone los endpoints del runner (Fase R2 del runbook runner v2): `GET/POST /api/run/config`, `POST /api/run`, `GET /api/run/status`, `POST /api/run/cancel`. Panel de ejecución correspondiente en `templates/index.html`.
- `app.py` — `/api/browse-folder` (diálogo nativo de carpeta vía tkinter en subprocess) y `/api/save-to-folder` (U2 del BACKLOG: escribe `<folder>/COLL.inp` con `_write_coll_inp`, 409 con `exists:true` si ya existe y `overwrite` no es `true`). Botón primario "Guardar en carpeta…" en la barra de navegación (`static/js/app.js`); recuerda la última carpeta usada en `localStorage` (`collaps-last-save-folder`) y la ofrece como valor inicial en el siguiente guardado y como prefijo del workdir de ejecución (U3: `loadRunConfig`, con prioridad sobre `default_workdir`). "Descargar" (antes "Guardar como…") queda como opción secundaria sin cambios de lógica. Test: `tools/test_save_to_folder.py` (no cubre `/api/browse-folder`, subprocess con tkinter — se verifica a mano, igual que en el resto de la suite).

## Semántica del formato (no violar)

- Estructura condicional de tarjetas: Card #4 (EB1, EB2) solo existe si `ISFIS ≠ 0`; Card #6 (CX) solo si `IESF = 5`. El parser devuelve `None` en esos casos y el writer debe omitirlas coherentemente.
- `NGROUP` lleva signo y el signo SIGNIFICA orden: negativo = energías decrecientes, positivo = crecientes. Conservar el signo en round-trip; nunca usar `abs()` salvo para dimensionar listas.
- Dimensiones acopladas: `len(FT) = |NGROUP|` y, si IESF=5, `len(CX) = |NGROUP|+1` (validaciones V03/V04 en el frontend).

## Tests

- `C:\venv\acab-venv\Scripts\python.exe tools/test_runner.py` — Fase R1 del runbook runner v2: `runner.py` (single feliz/rechazo de slot ocupado/timeout/cancel; batch con job fallido que no para la cola; cancelación a mitad; log_tail).
- `C:\venv\acab-venv\Scripts\python.exe tools/test_run_endpoints.py` — Fase R2: endpoints `/api/run`, `/api/run/config`, `/api/run/status`, `/api/run/cancel` vía test_client de Flask (422/409/camino feliz; `runner.start` mockeado).
- `C:\venv\acab-venv\Scripts\python.exe tools/test_save_to_folder.py` — U2 del BACKLOG: `/api/save-to-folder` (construcción de ruta `<folder>/COLL.inp`, 400/422 de entrada inválida, 409+overwrite).

Regla: cualquier cambio en parser o writer va acompañado de tests en `tools/` al estilo de los anteriores (scripts autocontenidos, sin framework), incluyendo un round-trip (parsear → regenerar → re-parsear → comparar) con un COLL.inp de referencia, cubriendo los cuatro casos: ISFIS=0/≠0 × IESF=5/≠5.

## Convenciones

- **i18n obligatorio**: ninguna cadena de UI hardcodeada; `data-i18n` + entrada en es.json y en.json (ambos, siempre).
- Errores de API en JSON con mensaje accionable en español (estilo actual).
- No añadir dependencias ni build steps de frontend.