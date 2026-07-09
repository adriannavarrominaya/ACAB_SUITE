# Runbook — Suite ACAB: navegación entre apps + ejecución de ACAB/COLLAPS

Estado: Parte A completada. Parte B sustituida por RUNBOOK_runner_v2.md — no seguir este documento para el runner.

Dos mejoras independientes, implementables por separado y en este orden:

- **Parte A — Suite:** puertos fijos, banner de navegación común y launcher. (~0.5 día)
- **Parte B — Runner:** botón "Ejecutar" con panel de log en los dos configuradores,
  y deep link al analyzer. (~1.5-2 días)

**Decisión de arquitectura ya tomada (no re-debatir):** NO se crea una cuarta web
orquestadora ni se fusionan las apps. Banner duplicado (3 copias de un fragmento
pequeño) + script launcher. La ejecución vive en la app dueña del fichero de entrada:
COLLAPS configurator ejecuta COLLAPS, INP configurator ejecuta ACAB, el analyzer no
ejecuta nada (solo recibe deep links).

**Orden respecto al barrido paramétrico:** Parte A antes del barrido (trivial, sin
colisiones). Parte B después del barrido.

---

## Parte A — Suite: puertos, banner y launcher

### A0. Contrato de puertos (los tres repos)

Puertos canónicos por defecto:

| App | Puerto |
|---|---|
| ACAB_inp_file_configurator | 5000 |
| ACAB_fort_file_analyzer | 5001 |
| COLLAPS_inp_file_configurator | 5002 |

Tareas:
1. Verificar/fijar el puerto por defecto de cada app (COLLAPS tiene puerto variable:
   fijar 5002 como default, manteniendo el override por argumento/variable de entorno
   que ya exista).
2. Documentar la tabla en el README de cada repo.

### A1. Endpoint `/api/ping` (los tres repos)

En cada `app.py`:

```python
@app.route('/api/ping')
def api_ping():
    resp = jsonify({'ok': True, 'app': 'inp-configurator'})  # nombre propio de cada app
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp
```

La cabecera CORS es imprescindible: el banner de una app en :5000 hará fetch a
:5001 y :5002. Solo en este endpoint — no habilitar CORS global.

### A2. Banner de navegación (los tres repos)

Fragmento idéntico (salvo el resaltado de la app actual) al inicio del `<body>` de
cada `index.html` (y `chains.html` del configurador):

- Navbar Bootstrap fina, por encima o integrada con la barra existente, con tres
  enlaces: "INP Configurator" (http://127.0.0.1:5000), "Fort Analyzer"
  (http://127.0.0.1:5001), "COLLAPS" (http://127.0.0.1:5002). `target="_blank"` o
  misma pestaña — elegir uno y ser consistente (recomendado: misma pestaña).
- La app actual: resaltada y sin enlace.
- Junto a cada enlace externo, un punto de estado (● verde / ○ gris) alimentado por
  un JS común: al cargar y cada 15 s, `fetch('http://127.0.0.1:PUERTO/api/ping',
  {signal: AbortSignal.timeout(1500)})`; verde si responde ok, gris si falla.
  Si está gris, el enlace muestra tooltip "No arrancada — usa suite_launcher.py".
- JS del banner en un fichero propio (p. ej. `static/js/suite_banner.js`) copiado a
  los tres repos. Marcar con un comentario de cabecera: "Fragmento común de la suite
  — mantener sincronizado en los 3 repos" (mismo aviso en el HTML).
- i18n donde la app lo soporte (configuradores); el analyzer no tiene i18n aún —
  textos en español directos, sin bloquear por ello.

### A3. Launcher `suite_launcher.py`

Ubicación: carpeta nueva hermana de los tres repos (p. ej. `acab_suite/`), con su
propio README breve. Contenido:

1. Lee `suite_config.json` (misma carpeta), creándolo con plantilla si no existe:

```json
{
  "apps": [
    {"name": "inp-configurator", "path": "../ACAB_inp_file_configurator", "port": 5000},
    {"name": "fort-analyzer",    "path": "../ACAB_fort_file_analyzer",    "port": 5001},
    {"name": "collaps",          "path": "../COLLAPS_inp_file_configurator", "port": 5002}
  ],
  "open_browser": "http://127.0.0.1:5000"
}
```

2. Para cada app: localizar el Python del venv (`venv/Scripts/python.exe` en Windows,
   `venv/bin/python` en Linux/macOS; error claro si no existe con instrucción de
   ejecutar setup.ps1/setup.sh), y lanzar `app.py` con el puerto como subproceso,
   redirigiendo su salida a `acab_suite/logs/<name>.log`.
3. Health-check: poll a `/api/ping` de cada una hasta 15 s; informar por consola
   del estado (✓/✗) de cada app.
4. Abrir el navegador en `open_browser` cuando todas respondan (o las que respondan).
5. Ctrl+C → terminar los tres subprocesos limpiamente (terminate, luego kill a los 5 s).
6. Evitar doble arranque: si `/api/ping` ya responde en un puerto antes de lanzar,
   no lanzar esa app y avisar ("ya en ejecución").
7. Importante: los `app.py` actuales abren el navegador solos al arrancar (Timer +
   webbrowser). Añadir a cada app una variable de entorno o flag
   (`ACAB_SUITE_NO_BROWSER=1` / `--no-browser`) que suprima esa apertura, y que el
   launcher la use — si no, se abrirían 3 pestañas + la del launcher.

### A4. Criterios de aceptación de la Parte A

- `python suite_launcher.py` arranca las tres apps, imprime ✓✓✓ y abre UNA pestaña.
- El banner aparece en las tres apps con la actual resaltada y puntos verdes en las
  otras dos; parar una app a mano → su punto pasa a gris en ≤15 s sin errores en consola.
- Navegar entre las tres apps por el banner funciona.
- Cada app sigue arrancando de forma individual exactamente igual que antes
  (`python app.py`), con su apertura de navegador intacta.
- READMEs actualizados (tabla de puertos + sección del launcher en un README de
  `acab_suite/`).

**Prompt sugerido (una sesión, los tres repos + carpeta nueva):**
> Implementa la Parte A del runbook: fija los puertos por defecto (5000/5001/5002),
> añade /api/ping con CORS a las tres apps, el banner de navegación con puntos de
> estado en las tres index.html (y chains.html), el flag --no-browser en cada app.py,
> y crea acab_suite/suite_launcher.py con suite_config.json y logs/. Verifica los
> criterios de aceptación A4 arrancando realmente las apps.

---

## Parte B — Runner de ejecución de COLLAPS y ACAB

### B0. TAREA HUMANA PREVIA (imprescindible, no delegar)

Documentar en `acab_suite/README.md` (sección "Invocación de los códigos") cómo se
ejecutan hoy a mano ACAB y COLLAPS en tu máquina. Como mínimo:

- Ruta de cada ejecutable.
- Cómo recibe el input: ¿redirección (`acab.exe < inp.5`)? ¿convención de nombre en
  el cwd (`fort.5`)? ¿argumento de línea de comandos?
- Qué ficheros deben estar presentes en el directorio de trabajo (DECAY.dat,
  PHOTON.dat, librerías XS, salida de COLLAPS…), y cuáles genera cada código.
- Duración típica de una ejecución (para fijar el timeout por defecto).

Sin esto, Claude Code implementaría una invocación inventada. Con esto, la Parte B
es mecánica.

### B1. Backend del runner — primero en COLLAPS_inp_file_configurator

Se implementa primero en la app más pequeña como banco de pruebas del patrón; luego
se replica en el configurador de inp.5. Módulo nuevo `runner.py` (sin Flask, testeable)
+ endpoints en `app.py`.

`runner.py`:

- `class Runner` (instancia única a nivel de módulo): mantiene el `Popen` actual,
  workdir, hora de inicio.
- `start(cmd: list[str] | str, workdir: Path, use_shell: bool, timeout_s: int)`:
  - Rechaza (excepción específica) si ya hay un run activo.
  - Lanza el proceso con `cwd=workdir`, stdout+stderr → `workdir/run.log`
    (fichero abierto en modo escritura, line-buffered).
  - Hilo vigilante para el timeout (terminate + marca 'timeout').
- `status()` → dict: `{running, returncode, elapsed_s, timed_out, log_tail}` donde
  `log_tail` son los últimos 16 KB de run.log (leer por seek desde el final, tolerante
  a encoding con errors='replace' — la salida FORTRAN puede no ser UTF-8).
- `cancel()` → terminate; kill si no muere en 5 s.

Endpoints:

- `GET/POST /api/run/config`: lee/escribe la sección de esta app en
  `acab_suite/suite_config.json` (o fichero local si la carpeta suite no existe):
  ruta del ejecutable, workdir por defecto, timeout. Nunca devolver trazas internas.
- `POST /api/run`: body `{workdir, save_current: bool, data?: {...}}`.
  Si `save_current`, serializa el formulario actual (reutilizar `_write_coll_inp` /
  `_write_inp5`) y lo escribe en el workdir con el nombre que exija la invocación
  documentada en B0. Comprobaciones antes de lanzar: workdir existe, ejecutable
  existe, ficheros de librería requeridos presentes (lista según B0; si falta alguno
  → 422 con la lista), y si ya existe el fichero de salida (fort.6 / salida COLLAPS)
  exigir `overwrite: true`. Devuelve `{ok: true}` o 409 si hay run activo.
- `GET /api/run/status` y `POST /api/run/cancel`: envoltorios de Runner.

### B2. Frontend del panel de ejecución

En la app correspondiente:

- Botón "Ejecutar" en la barra de herramientas → panel/modal con: ruta del ejecutable
  y workdir (persistidos vía /api/run/config), checkbox "guardar el fichero actual en
  el workdir antes de ejecutar" (marcado por defecto), botón Ejecutar/Cancelar,
  cronómetro, y panel de log monoespaciado con autoscroll (desactivable si el usuario
  hace scroll manual hacia arriba).
- Polling de `/api/run/status` cada 1 s mientras `running`; al terminar, badge de
  resultado (código de retorno / timeout / cancelado) y detener el polling.
- Bloqueos: no ejecutar si `validateAll()` reporta errores (mismo patrón que Guardar);
  botón deshabilitado mientras hay un run activo.
- i18n de todas las cadenas nuevas.

### B3. Replicar en ACAB_inp_file_configurator + deep link al analyzer

1. Copiar `runner.py` y el patrón de endpoints/panel (adaptando invocación y lista de
   ficheros requeridos según B0). Mantener los dos `runner.py` idénticos salvo
   constantes (comentario de sincronización como el del banner).
2. Al terminar un run de ACAB con returncode 0 y `fort.6` presente en el workdir:
   mostrar botón "Abrir en el Analyzer" →
   `http://127.0.0.1:5001/?folder=<workdir url-encoded>`.
3. En el analyzer (cambio pequeño): al cargar la página, si hay parámetro `?folder=`,
   rellenar el campo de carpeta y lanzar el análisis automáticamente (reutilizar
   `doAnalyze()`).

### B4. Tests y criterios de aceptación de la Parte B

Tests (en `tools/` de cada configurador, estilo de los existentes):

- `runner.py` con un ejecutable falso multiplataforma (script Python que imprime N
  líneas con sleep y sale con código dado): start/status/log_tail/returncode,
  rechazo de segundo run concurrente, timeout, cancel.
- Endpoint /api/run con `app.test_client()`: 422 por workdir inexistente, 409 por
  run activo, flujo feliz con el ejecutable falso.

Aceptación funcional (manual, con los códigos reales):

- COLLAPS: editar COLL.inp → Ejecutar → log visible en vivo → fichero de salida
  generado en el workdir.
- ACAB: editar inp.5 → Ejecutar → al terminar, "Abrir en el Analyzer" abre el
  análisis de ese workdir ya lanzado, sin teclear la ruta.
- Cancelar un run a mitad deja la UI en estado consistente y permite relanzar.
- Reinicio del servidor Flask a mitad de un run: al recargar, la UI no queda
  bloqueada (status informa que no hay run activo; el proceso huérfano es una
  limitación conocida a documentar en el README).

**Prompts sugeridos:**
> (Sesión 1, COLLAPS) Implementa B1+B2 en COLLAPS_inp_file_configurator según el
> runbook. La invocación exacta está documentada en acab_suite/README.md, sección
> "Invocación de los códigos" — síguela literalmente. Empieza por runner.py con sus
> tests usando un ejecutable falso.

> (Sesión 2, INP configurator + analyzer) Replica el runner en
> ACAB_inp_file_configurator (B3), añade el botón "Abrir en el Analyzer" y el soporte
> del parámetro ?folder= con auto-análisis en ACAB_fort_file_analyzer. Ejecuta todas
> las suites de tests de ambos repos al terminar.

---

## Mejoras futuras conectadas (NO incluir en este trabajo)

- Botón "Ejecutar todo el barrido": recorrer `sweep_manifest.json` en cola secuencial
  con el runner. Requiere cola/estado multi-run — v2 del runner.
- "Importar espectro de COLLAPS al Bloque #3" tras un run de COLLAPS con éxito.
- Fusión de las apps en una sola Flask con blueprints (post-TFG).
