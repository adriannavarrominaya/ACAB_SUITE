# Runbook — Runner de ejecución v2 (ACAB/COLLAPS desde las interfaces)

Estado: completado (R0–R5). El estado de todos los runbooks se mantiene en README.md de esta carpeta.

**Sustituye íntegramente a la "Parte B" de RUNBOOK_suite_y_runner.md.**
(La Parte A — puertos, banner, launcher — sigue vigente tal cual.)

**Objetivo:** ejecutar COLLAPS y ACAB desde las apps que poseen sus ficheros de
entrada, con tres modos: ejecución individual (COLLAPS configurator y INP
configurator), ejecución en cola de un barrido completo (pestaña Barrido del INP
configurator), y detección de resultados desactualizados en el analyzer.

**Decisiones de arquitectura ya tomadas (no re-debatir):**
- La ejecución vive en la app dueña del fichero de entrada. El analyzer NO ejecuta
  nada: solo recibe deep links y detecta desactualización.
- Guardar y ejecutar son acciones separadas: NUNCA auto-ejecutar al guardar. El
  panel de ejecución tiene la casilla "guardar el fichero actual en el workdir antes
  de ejecutar" marcada por defecto.
- Un solo slot de ejecución por app (un proceso ACAB/COLLAPS a la vez). La cola de
  barrido es secuencial dentro de ese slot.
- La cola NO lanza el script run_all: ejecuta las simulaciones una a una con el
  runner (estado por simulación, log por simulación, cancelación limpia,
  continuación ante fallos). Los scripts run_all.ps1/.sh se siguen generando como
  vía externa/headless.
- El fichero de cadenas (chains) no tiene botón propio: es un fichero más del
  directorio de trabajo.

---

## Fase R0 — TAREA HUMANA PREVIA (imprescindible, sin cambios respecto al B0 original)

Documentar en `acab_suite/README.md`, sección "Invocación de los códigos", cómo se
ejecutan hoy a mano ACAB y COLLAPS: ruta de cada ejecutable; cómo recibe el input
(redirección `< inp.5`, convención `fort.5` en el cwd, o argumento); qué ficheros
deben estar presentes en el directorio de trabajo (DECAY.dat, librerías XS, fichero
de cadenas, salida de COLLAPS…) y cuáles genera; duración típica de una ejecución
(fija el timeout por defecto). Sin esto no se implementa nada.

---

## Fase R1 — `runner.py`: núcleo con soporte de cola (repo COLLAPS primero)

Módulo `runner.py` sin dependencias de Flask, instancia única a nivel de módulo.

**Modelo de estados:** `idle` | `running_single` | `running_batch`.

**API del módulo:**
- `start(cmd, workdir, timeout_s)` — ejecución individual: `Popen` con `cwd=workdir`,
  stdout+stderr → `workdir/run.log` (line-buffered, encoding tolerante con
  errors='replace': la salida FORTRAN puede no ser UTF-8). Excepción específica si
  el slot está ocupado. Hilo vigilante de timeout (terminate + estado 'timeout').
- `start_batch(jobs, cmd_template, timeout_s_por_sim, results_path)` — cola
  secuencial: `jobs = [{'workdir': ...}]`. Hilo que itera: lanza, espera, registra
  `{workdir, estado, returncode, duracion_s, inicio, fin}`, y CONTINÚA con la
  siguiente aunque una falle (estado 'failed'/'timeout' registrado). Al terminar
  (o cancelarse) escribe `results_path` (batch_results.json) con la lista completa
  y un resumen {total, ok, fallos, canceladas}.
- `status()` — dict según modo:
  - single: `{mode, running, returncode, elapsed_s, timed_out, log_tail}`
  - batch: `{mode, running, current_index, jobs: [{workdir, estado, returncode,
    duracion_s}], log_tail}` (log_tail = últimos 16 KB del run.log de la sim EN CURSO)
- `cancel()` — single: terminate (kill a los 5 s). Batch: terminate de la sim en
  curso Y las pendientes pasan a 'cancelled'; se escribe batch_results.json igualmente.

**Tests** (`tools/test_runner.py`, con ejecutable falso multiplataforma — script
Python que imprime N líneas con sleep y sale con el código pedido):
single feliz / rechazo de segundo start / timeout / cancel; batch de 3 jobs con el
2º fallando (el 3º debe ejecutarse; resumen 2 ok + 1 fallo); batch cancelado durante
el job 2 (job 3 'cancelled'; results json escrito); log_tail del job en curso.

**Criterio de aceptación:** tests en verde. `runner.py` lleva comentario de cabecera
"común de la suite — mantener sincronizado" (se replicará en el INP configurator).

---

## Fase R2 — Ejecución individual en COLLAPS configurator (endpoints + panel)

Endpoints en `app.py`:
- `GET/POST /api/run/config` — persiste en `acab_suite/suite_config.json` (o fichero
  local si no existe la carpeta suite): ruta del ejecutable, workdir por defecto,
  timeout. 
- `POST /api/run` — body `{workdir, save_current, overwrite, data?}`. Si
  `save_current`, serializa el formulario con `_write_coll_inp` al workdir con el
  nombre que dicte R0. Pre-checks (422 con mensaje accionable): workdir y ejecutable
  existen; ficheros requeridos presentes (lista de R0); si existe fichero de salida
  previo → exigir overwrite. 409 si slot ocupado.
- `GET /api/run/status`, `POST /api/run/cancel`.

Panel de UI (botón "Ejecutar" en la barra): ejecutable + workdir persistidos,
casilla save_current (marcada), Ejecutar/Cancelar, cronómetro, log monoespaciado con
autoscroll (desactivable al hacer scroll manual), polling de status cada 1 s, badge
final (ok / código de error / timeout / cancelado). Bloqueo si `validateAll()` da
errores. i18n completo.

**Criterios de aceptación:** tests de endpoint con test_client (422/409/feliz con
ejecutable falso); prueba real: editar COLL.inp → Ejecutar → log en vivo → salida
generada. Reinicio del servidor a mitad de run: la UI no queda bloqueada al recargar
(limitación del proceso huérfano documentada en README).

---

## Fase R3 — Ejecución individual en INP configurator + deep link al analyzer

1. Replicar `runner.py` (idéntico salvo constantes) y el patrón endpoints+panel,
   adaptando invocación y lista de ficheros requeridos según R0. El workdir por
   defecto se propone recordando el último usado.
2. Al terminar un run con returncode 0 y `fort.6` presente: botón
   "Abrir en Fort Analyzer" → `http://127.0.0.1:5001/?folder=<workdir url-encoded>`.
3. En el analyzer: soportar `?folder=` al cargar (rellenar campo + lanzar análisis
   automáticamente). Compatible con la cache keyed por carpeta (Fase 1 del runbook
   del analyzer) si ya está hecha.

**Criterios de aceptación:** flujo completo real editar → ejecutar → abrir análisis
sin teclear rutas; suites de ambos repos en verde.

---

## Fase R4 — Ejecución en cola del barrido (pestaña Barrido del INP configurator)

1. **Tras generar un barrido con éxito**, la pestaña muestra el panel "Ejecución del
   barrido": botón Ejecutar barrido → `POST /api/run/batch` con la lista de
   subcarpetas generadas (en el orden del manifest), `results_path = <root>/batch_results.json`.
2. **Ejecutar un barrido existente:** selector de carpeta raíz; el backend lee su
   `sweep_manifest.json` para obtener las subcarpetas (404 claro si no hay manifest).
   Pre-check: aviso con confirmación si alguna subcarpeta ya contiene fort.6
   (re-ejecución sobrescribe).
3. **UI de progreso:** lista de N filas (carpeta, estado con icono
   pendiente/ejecutando/ok/fallo/timeout/cancelada, duración), contador global
   "k/N · ok · fallos", log de la sim en curso, botón Cancelar (cancela la actual y
   las pendientes). Polling de `/api/run/status` cada 1-2 s. Cerrar la pestaña o
   navegar NO cancela la cola (corre en el servidor); al volver, la UI se
   re-sincroniza desde status.
4. **Al terminar:** resumen (X ok, Y fallos, duración total) y botón
   "Abrir en Fort Analyzer" → `?folder=<root>`. Si hubo fallos, listado con enlace
   conceptual al run.log de cada una (mostrar ruta).
5. `batch_results.json` queda en la raíz junto al manifest (misma filosofía de
   trazabilidad; la pestaña Optimización del analyzer podrá mostrarlo en el futuro).

**Endpoints nuevos:** `POST /api/run/batch` (body: `{root, folders?|from_manifest,
overwrite}`), reutilizando status/cancel comunes.

**Tests:** batch vía test_client con 3 sims de juguete y ejecutable falso (una
fallando): estados finales correctos, batch_results.json coherente con el manifest,
409 si se pide batch con slot ocupado.

**Criterios de aceptación:** barrido real pequeño (2-3 sims) ejecutado de principio
a fin desde la pestaña, con fort.6 generados, y salto al analyzer mostrando las
simulaciones; cancelación a mitad deja estados coherentes y results json escrito.

---

## Fase R5 — Detección de resultados desactualizados en el analyzer

1. En `descubrir_simulaciones`/`analizar_carpeta`: por simulación, capturar mtime de
   `fort.6` y de `inp.5` (si existe). Flag `desactualizada = mtime(inp.5) > mtime(fort.6)`.
2. `/api/analyze` incluye por sim: `fort6_fecha`, `desactualizada`.
3. UI: en la tarjeta/leyenda de cada simulación, fecha del fort.6 y, si
   `desactualizada`, badge de aviso con tooltip: "El inp.5 fue modificado después de
   generar el fort.6: los resultados pueden no corresponder a la configuración
   actual". Aviso agregado si CUALQUIER sim del análisis está desactualizada.
4. Test: fixture temporal tocando mtimes (`os.utime`) → flag correcto en ambos sentidos.

**Criterio de aceptación:** modificar un inp.5 de una simulación analizada y
re-analizar muestra el badge; suite del analyzer en verde.

---

## Orden de ejecución y prompts

Orden: R0 → R1+R2 (una sesión, repo COLLAPS) → R3 (una sesión, INP
configurator + analyzer) → R4 (una sesión, INP configurator; requiere el generador
de barridos ya operativo) → R5 (sesión corta, analyzer; combinable con R3 si esa
sesión va sobrada).

> (Sesión R1+R2, en COLLAPS_inp_file_configurator) Implementa las fases R1 y R2 del
> runbook del runner v2. La invocación exacta está en acab_suite/README.md, sección
> "Invocación de los códigos" — síguela literalmente. Empieza por runner.py y
> tools/test_runner.py con el ejecutable falso, incluida la cola (start_batch),
> aunque la UI de cola no se use aún en esta app. Ejecuta la suite completa al terminar.

> (Sesión R3) Replica runner.py y el panel de ejecución en
> ACAB_inp_file_configurator, añade el botón "Abrir en Fort Analyzer" y el soporte
> de ?folder= con auto-análisis en ACAB_fort_file_analyzer. Suites de ambos repos en
> verde al terminar.

> (Sesión R4, en ACAB_inp_file_configurator) Implementa la ejecución en cola del
> barrido según la fase R4: panel de progreso en la pestaña Barrido, /api/run/batch,
> batch_results.json, ejecución de barrido existente desde su manifest, y el botón
> final hacia el analyzer. Tests con ejecutable falso incluidos.

> (Sesión R5, en ACAB_fort_file_analyzer) Implementa la detección de simulaciones
> desactualizadas (fase R5) con su test de mtimes.

---

## Verificaciones humanas

- R0 es la crítica: la invocación documentada debe ser EXACTAMENTE la que usas a
  mano (probada en tu máquina), incluida la lista de ficheros del workdir.
- Tras R2 y R3: una ejecución real de cada código comparando el fichero de salida
  con uno generado a mano con la misma entrada (deben ser idénticos).
- Tras R4: un barrido pequeño real de principio a fin, cronometrando, para calibrar
  el timeout por simulación por defecto.
- Limitación aceptada y documentada: si el servidor Flask se reinicia durante una
  cola, el proceso ACAB en curso queda huérfano y la cola no se reanuda
  (batch_results.json parcial no se escribe). Re-lanzar el barrido con overwrite.
