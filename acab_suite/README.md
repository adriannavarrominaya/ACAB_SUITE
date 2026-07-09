# acab_suite — transversal de la suite ACAB

> Parte de la [suite ACAB del TFG](../README.md) — configurar entradas → ejecutar → analizar salidas.

Carpeta transversal de la suite del TFG: launcher, configuración común y runbooks
de mejoras. No es una app; las tres apps viven en las carpetas hermanas.

## Puertos canónicos

| App | Puerto |
| --- | --- |
| ACAB_inp_file_configurator | 5000 |
| ACAB_fort_file_analyzer | 5001 |
| COLLAPS_inp_file_configurator | 5002 |

## Instalación (primera vez / ordenador nuevo)

```powershell
.\setup.ps1
```

Crea el venv compartido en `C:\venv\acab-venv` (parametrizable con `-VenvPath`) e
instala en él las dependencias de las 3 apps. Es el único setup necesario para
usar la suite con `suite_launcher.py` — sustituye a ejecutar el `setup.ps1` de
cada app por separado (esos siguen existiendo para arrancar una app suelta con
su propio venv local).

## Launcher

```powershell
# Con el venv de la suite (o cualquier Python con flask+waitress instalados):
C:\venv\acab-venv\Scripts\python suite_launcher.py
```

Qué hace:

1. Lee `suite_config.json` (lo crea con la plantilla por defecto si no existe).
2. Lanza cada app (`app.py --port <puerto> --no-browser`) como subproceso, con la
   salida redirigida a `logs/<name>.log`. Si una app ya responde en su puerto,
   avisa "ya en ejecución" y no la lanza de nuevo.
3. Health-check de `/api/ping` hasta 15 s e informa ✓/✗ por consola.
4. Abre UNA pestaña del navegador en `open_browser`.
5. `Ctrl+C` para las apps lanzadas por el launcher (terminate; kill a los 5 s).

### `suite_config.json`

```json
{
  "apps": [
    {"name": "inp-configurator", "path": "../ACAB_inp_file_configurator", "port": 5000},
    {"name": "fort-analyzer",    "path": "../ACAB_fort_file_analyzer",    "port": 5001},
    {"name": "collaps",          "path": "../COLLAPS_inp_file_configurator", "port": 5002}
  ],
  "open_browser": "http://127.0.0.1:5000",
  "python": null
}
```

- `python` (global u opcionalmente por app): ruta del intérprete con el que lanzar
  las apps, p. ej. `"C:/venv/acab-venv/Scripts/python.exe"`. Si es `null`, el
  launcher busca en este orden: venv local del repo (`<app>/venv/`) y, si no
  existe, el mismo Python con el que se ejecutó el launcher. Así ninguna ruta de
  venv queda hardcodeada en el código.
- `open_browser`: URL que se abre al terminar el health-check (una sola pestaña;
  las apps se lanzan con `--no-browser`).

## Banner de navegación

Cada app muestra un banner superior con enlaces a las otras dos y un punto de
estado (● verde / ○ gris) alimentado por `static/js/suite_banner.js` (fetch a
`/api/ping` al cargar y cada 15 s). El fragmento HTML del banner y ese JS son
**copias sincronizadas en los 3 repos** — si se edita una copia, replicar en las
demás (ver comentario de cabecera en los propios ficheros).

## Runbooks

- `RUNBOOK_suite_y_runner.md` — Parte A (puertos/banner/launcher, implementada).
  Su Parte B (runner de ejecución) queda sustituida íntegramente por
  `RUNBOOK_runner_v2.md`.
- `RUNBOOK_runner_v2.md` — runner de ejecución de ACAB/COLLAPS desde las
  interfaces. Fases R0-R5 completadas: `runner.py` (con cola) en COLLAPS y en
  el INP configurator, paneles de ejecución individual, deep link al analyzer
  (`?folder=`), ejecución en cola del barrido (`/api/run/batch`) y detección de
  resultados desactualizados (badge en el analyzer si el `inp.5` es más
  reciente que el `fort.6`).
- `RUNBOOK_barrido_parametrico_v2.md` — generador de barridos paramétricos
  (sustituye a `RUNBOOK_barrido_parametrico.md`, v1). Completado: fases T0 y
  1-3 implementadas, y Fase 5 opcional implementada en el analyzer (pestaña
  "Optimización", que lee `sweep_manifest.json`). T0 ya existía en el código y
  se verificó el 2026-07-09.
- `RUNBOOK_fort_analyzer_mejoras.md` — mejoras del fort file analyzer. Fases
  0-5 completadas (tests oro, i18n/paridad, unidades físicas, exportación CSV,
  datos experimentales, métricas de optimización de producción). Fases 6-7
  (espectro gamma genérico desde PHOTON.dat y cierre de documentación)
  pendientes: falta el fixture `PHOTON.dat` de partida.

## Invocación de los códigos (fuente de verdad para el runner — fase R0)

Convención de la suite: **simulaciones autocontenidas**. Cada carpeta de
simulación contiene su propio ejecutable junto a sus ficheros de entrada, y el
código lee todo del directorio de trabajo actual. Esta sección prevalece sobre
cualquier mención a "ruta del ejecutable" en los runbooks: NO hay ruta global de
ejecutable; el runner invoca el exe de la propia carpeta.

### ACAB
- Ejecutable: `acab.exe`, presente EN la carpeta de la simulación.
- Invocación: el runner lanza `acab.exe` SIN argumentos con
  `cwd = carpeta de la simulación` (comando: la ruta absoluta
  `<workdir>\acab.exe`). Lee todas sus entradas del cwd.
- Fichero de entrada principal: `inp.5` (nombre que debe usar la opción
  "guardar el fichero actual en el workdir" del runner).
- Ficheros requeridos en el workdir (pre-check del runner; lista exacta de una
  carpeta de trabajo buena conocida): `acab.exe`, `inp.5`, `DECAY.dat`, `XSECTION.dat`.
- Salidas generadas: `fort.6` (la que consume el analyzer), fichero de tiempo
  de CPU (nombre: `cpu_time.txt`) y otros auxiliares.
- Duración típica: < 1 s. Timeout por defecto del runner: 60 s.
- Barridos: `acab.exe` y el resto de ficheros requeridos deben estar en la
  CARPETA BASE del barrido (se copian a cada subcarpeta de simulación, que así
  nace autocontenida).

  Nota: `XSECTION.dat` es salida de COLLAPS — si se regenera el espectro, actualizar la carpeta base de los barridos antes de generar/ejecutar.

### COLLAPS
- Ejecutable: `collaps.exe`, presente EN la carpeta de trabajo, mismo modelo
  que ACAB (sin argumentos, todo por cwd).
- Fichero de entrada principal: `COLL.inp`.
- Ficheros requeridos en el workdir: `collaps.exe`, `COLL.inp`, `XSBL.dat`.
- Salidas generadas: `XSECTION.dat`, `FLUX.inf`, `XS.inf`, `REACTIONS.dat`, `XSZERO.dat`.
- Duración típica: ~2 s. Timeout por defecto del runner: 60 s.

### Configuración del runner (a implementar en las fases R1-R4)
Se persiste por app en `suite_config.json`, clave `runner` dentro de cada app:
`{"exe_name": "acab.exe", "required_files": [...], "output_file": "fort.6",
"timeout_s": 60, "default_workdir": "..."}`. Los pre-checks del runner leen esta
configuración, no listas hardcodeadas en el código. `exe_name` es un fichero
requerido más: si no está en el workdir, error 422 con mensaje indicándolo.

## Verificaciones de control (checklist)

- **Control XNORM** ✅ (2026-07-09): barrido de flujo con XNORM ∈ {0.5, 1.0} sobre el
  caso de pulso (T_irr=10 s). A_pico(I131): 8.6140e+3 vs 1.7230e+4 Bq/cm³ →
  cociente 0.4999 ≈ 0.5 teórico (régimen lineal). El barrido de flujo escala la
  producción linealmente como predice la teoría. Ambas sims: t_pico=3.753 h (enfr.).
- **Control de malla** ✅ (2026-07-09): mismo historial temporal (T_irr y pasos
  idénticos) generado por las dos vías — generador manual de la pestaña temporal
  vs barrido temporal de una fila — produce inp.5 BYTE-IDÉNTICOS (verificado con
  fc). Al compartir ambas vías buildBlocks78 (sweep_utils.js) y _write_inp5, la
  equivalencia de los fort.6 queda garantizada sin ejecución comparada.
- **Criterio de pureza radionucleídica** ✅
  impurezas = otros isótopos de yodo (confirmado el default mismo-elemento);
  requisito del producto: pureza > 99.9 % (impurezas < 0.1 %), con atención a
  I-124 (emisor β+) e I-125. Fuera de alcance de la herramienta: pureza química
  del Te (<10 μg/dosis, se mide en proceso). Concepto adicional anotado: I-127
  estable e I-129 de vida larga no penalizan la pureza radionucleídica pero
  reducen la ACTIVIDAD ESPECÍFICA del yodo — posible métrica futura (los datos
  de átomos están en el fort.6).
- **Desviación saturación teórica vs ACAB** ✅ (2026-07-09): verificada la
  consistencia interna de la métrica sobre la ref_sim (A_sat=4.0138e+6 Bq/cm³ y
  t_50=192.61 h = ln2/λ, correctos). Con el pulso de 10 s la comparación de
  curvas es degenerada por construcción (anclaje en t_fin), así que la medición
  de la desviación real queda pendiente de un caso de irradiación larga.
  Detalle y valores oro: `ACAB_fort_file_analyzer/tests/fixtures/README.md`.