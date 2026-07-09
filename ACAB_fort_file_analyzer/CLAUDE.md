<!-- Guardar como: ACAB_fort_file_analyzer/CLAUDE.md -->

# ACAB Fort File Analyzer

App web Flask (monousuario, 127.0.0.1:5001) para analizar ficheros de salida `fort.6`
de ACAB 2008: parsea múltiples simulaciones (subcarpetas), convierte átomos→actividad,
grafica evolución temporal (Plotly) y genera informes y tablas comparativas por
isótopo. Parte de la suite del TFG (ver CLAUDE.md de la carpeta padre).

## Arranque y stack

- `C:\venv\acab-venv\Scripts\python app.py` — puerto 5001 por defecto (`--port`/`-p` o variable
  `ACAB_ANALYZER_PORT`; `--host`/`ACAB_ANALYZER_HOST`, por defecto 127.0.0.1).
- Flask + waitress (con fallback al servidor de desarrollo si waitress falta).
- Dependencias: flask, waitress, pyyaml, numpy (requirements.txt). Plotly y Bootstrap por CDN.

## Ficheros clave

- `fort_analyzer.py` — motor de análisis, todo el conocimiento del dominio:
  - Parsers: `leer_fort6_irradiacion` (sección NUMBER OF ATOMS, átomos/cm³),
    `leer_fort6_enfriamiento` (sección NUCLIDE RADIOACTIVITY, Bq/cm³),
    `leer_inp5` (T_irr, T_cool, flujos, XNORM), `leer_decay_dat` (semividas,
    codificación ZZAAAS, S=1 metaestable).
  - Cálculo: conversión A = λ·N en irradiación; `calcular_pico`,
    `calcular_informe_isotopo`, `calcular_tablas_comparativas`.
  - Fase 5 — métricas de optimización de producción (integradas en
    `calcular_informe_isotopo` bajo la clave `"metricas"`, por simulación):
    `calcular_saturacion` (curva teórica A_teo=A_sat·(1−e^−λt) anclada al
    valor ACAB en T_irr + tabla de tiempos a 50/75/90/95 % de saturación),
    `calcular_rendimiento` (A_pico/T_irr vs. ganancia marginal del último
    10 % de irradiación) y `calcular_pureza` (P = A(objetivo)/ΣA(impurezas)
    en t_pico). `isotopos_mismo_elemento` calcula el criterio POR DEFECTO de
    impurezas (mismo elemento que el isótopo objetivo); es el único criterio
    soportado como default — no cambiarlo sin validar con el tutor del TFG
    (ver runbook). Editable desde la UI vía el parámetro `isotopos_impureza`.
  - `GAMMA_I131` hardcodeado (espectro ENSDF/NNDC, solo ¹³¹I por ahora).
  - `leer_sweep_manifest` (Fase 5 opcional, `RUNBOOK_barrido_parametrico_v2.md`):
    lee `sweep_manifest.json` de la raíz analizada si existe (escrito por la
    pestaña "Barrido" del ACAB INP File Configurator); `None` si no hay barrido,
    sin romper el análisis normal. `/api/analyze` lo expone tal cual como
    `sweep_manifest`.
  - `analizar_carpeta` (Fase R5 del runbook runner v2): por simulación calcula
    `fort6_fecha` (mtime de `fort.6`, ISO) y `desactualizada` = `mtime(inp.5) >
    mtime(fort.6)` (si no hay `inp.5` en la subcarpeta, `desactualizada=False`).
    `/api/analyze` expone ambos campos tal cual. Detecta que el `inp.5` se editó
    después de generar ese `fort.6` (resultados potencialmente obsoletos); no
    dispara ninguna re-ejecución, el analyzer nunca ejecuta nada.
- `app.py` — API REST. `_analysis_cache` es un dict global en memoria, keyed
  por carpeta normalizada (varias pestañas con carpetas distintas no se pisan).
- `static/js/app.js` — UI + gráficas Plotly. Con i18n (`static/js/i18n/es.json` /
  `en.json`, función `t()`, atributos `data-i18n*`); español por defecto.
  Soporta deep link `?folder=<carpeta>` (Fase R3 del runbook runner v2, botón
  "Abrir en Fort Analyzer" del INP configurator): al cargar, si el query param
  está presente rellena `folder-input` y lanza `doAnalyze()` automáticamente.
  Pestaña "Simulaciones" (`renderOverview`): si `sim.desactualizada`, badge de
  aviso con tooltip por simulación junto a `fort6_fecha`, y un banner agregado
  si CUALQUIER sim del análisis está desactualizada (claves i18n
  `overview.desactualizada_badge` / `_tooltip` / `_warning`, Fase R5 del
  runbook runner v2).
  `Z_BY_ELEM` cubre la tabla periódica completa símbolo→Z (H..Og, claves en
  MAYÚSCULAS como en fort.6; Fase 1 de `RUNBOOK_fort_analyzer_mejoras.md`) —
  el campo Z del informe y la exportación CSV funcionan con cualquier material,
  no solo Te/I/Xe/Cs/Ba. El filtro por elemento de la métrica de pureza
  (`isotopos_mismo_elemento`, backend) es independiente de esta tabla: usa una
  regex sobre la clave del isótopo, así que ya funcionaba con cualquier
  elemento antes de esta fase.
- `static/js/units.js` — conversión pura de unidades de actividad (Bq/cm³ ↔
  MBq/g / actividad total), aplicada por simulación en el frontend.
- `static/js/export_utils.js` — generación CSV pura (delimitador/decimal es-ES
  o internacional) para gráficas, informe y tablas comparativas.
- `static/js/reference_data.js` — parser del CSV de datos de referencia
  (`docs/SPEC_csv_datos_referencia.md`), interpolación lineal recortada a los
  extremos y métricas de desviación (Fase 4: superposición de datos
  experimentales/computacionales de referencia sobre la curva ACAB).
- `static/js/optim_utils.js` — puro (UMD, sin DOM): combina `sweep_manifest`
  (folder→params) con `informe.simulations`/`informe.metricas` YA calculados
  por el servidor (A_pico, t_pico, pureza, rendimiento) para la pestaña
  "Optimización" (Fase 5 opcional del barrido); NO recalcula ninguna fórmula
  física, solo combina/agrupa. `mergeSweepRows`, `paramKeys`,
  `groupByOtherParams` (series de color = resto de dimensiones del barrido),
  `yRawValue`/`yNeedsUnitConv` (selector de variable Y: A_pico por defecto,
  t_pico, pureza, rendimiento). Renderizado (`renderOptimizacion` en app.js)
  solo se activa si `analysisData.sweep_manifest` no es `null`.
- `figuras.yaml` — ejemplo de configuración de figuras; el formato se documenta en README §7.
- `compare_simulaciones.py` — **[LEGACY]**: la densidad de normalización ya se
  lee automáticamente de `CONCENTRATIONS(GRAM)` (`leer_fort6_concentraciones`)
  y la superposición de datos experimentales la cubre `reference_data.js`; no
  invertir más en este script.
- `add_report_sheet.py` — auxiliar puntual de Excel; no forma parte de la app.

## Tests

Suite de tests oro (scripts autocontenidos, sin framework, estilo de la suite):

- `C:\venv\acab-venv\Scripts\python tools\test_fort_analyzer.py` — parsers
  (`fort.6`, `inp.5`, `DECAY.dat`), cálculo del pico, `CONCENTRATIONS(GRAM)` y
  conversiones de unidad, contra la simulación de referencia. Incluye
  `test_desactualizada()` (Fase R5 del runbook runner v2): toca mtimes con
  `os.utime` sobre un fixture temporal y comprueba el flag `desactualizada` en
  ambos sentidos.
- `C:\venv\acab-venv\Scripts\python tools\test_api.py` — API REST vía
  `app.test_client()` (flujo `/api/analyze` → `/api/isotopo_report`, cache
  keyed por carpeta y errores controlados).
- `C:\venv\acab-venv\Scripts\python tools\test_reference_data.py` — oráculo
  Python de `reference_data.js` (fixtures CSV de `tests/fixtures/experimental/`
  y criterio de aceptación de la Fase 4 contra la ref_sim).
- `C:\venv\acab-venv\Scripts\python tools\test_metricas.py` — métricas de
  optimización de producción (Fase 5: saturación, rendimiento, pureza) con
  curvas sintéticas de solución analítica conocida (no depende de la ref_sim).
- Node (disponible en esta máquina — comprobar con `Get-Command node` antes de
  asumir lo contrario): `node tools\test_units.js`, `node tools\test_export.js`,
  `node tools\test_reference_data.js` — tests directos de las funciones puras
  de frontend. Sus oráculos numéricos también están espejados en los scripts
  Python de arriba.
- `node tools\test_optim_utils.js` — combinación pura `sweep_manifest` +
  informe de `static/js/optim_utils.js` (Fase 5 opcional, pestaña
  Optimización). Sin oráculo Python: no reproduce ninguna fórmula física
  (esas ya están cubiertas por `test_metricas.py`/`test_fort_analyzer.py`),
  solo combina/agrupa datos ya calculados — su verificación vive únicamente
  en node, como `test_export.js`.

Fixtures en `tests/fixtures/ref_sim/` (simulación v.5 "info thesis") y
`tests/fixtures/experimental/` (CSV de la Fase 4); valores oro documentados en
`tests/fixtures/README.md` y `docs/SPEC_csv_datos_referencia.md`. Cada script
devuelve código de salida 0/1. Regla: cualquier cambio en `fort_analyzer.py`
o en los módulos JS puros debe dejar toda la suite (Python + node) en verde y
añadir los tests oro correspondientes.

## Semántica del dominio (no violar)

- Estructura de entrada: carpeta padre con subcarpetas, cada una con `fort.6`
  (obligatorio), `inp.5` y `DECAY.dat` (opcionales). Modo simulación única si
  `fort.6` está en la raíz.
- La columna `RESTART` del fort.6 marca el inicio del enfriamiento; la columna
  `INITIAL` es el estado pre-irradiación y se OMITE en los análisis de enfriamiento.
- Prioridad de semividas: sección `semividas` del YAML > `DECAY.dat` > tabla interna
  `DEFAULT_SEMIVIDAS` (fallback Te/I/Xe).
- Unidades: los datos internos y el cache SIEMPRE están en Bq/cm³; la
  conversión a MBq/g / actividad total es un factor por simulación aplicado
  en el FRONTEND (`static/js/units.js`), no en el backend.
- Claves de isótopo tal como aparecen en fort.6, en mayúsculas (`I131`, `XE133M`);
  `iso_label()` genera la notación Unicode para la UI.
- Datos de referencia externos (Fase 4, `reference_data.js`): el t=0 de una
  serie con `fase: enfriamiento` es el fin de la irradiación (RESTART), igual
  que en el resto de la app; se traslada sumando `T_IRR_h` de la simulación de
  referencia elegida al importar. Las series viven solo en `appState`
  (`_state.refSeries`), nunca en el cache del servidor ni en disco.

## Gotchas

- `/api/browse-folder` abre el selector nativo vía tkinter en subprocess: frágil en
  instalaciones Python sin tkinter; el campo de ruta manual es el fallback. No
  convertirlo en dependencia dura de ningún flujo.
- Respuestas JSON pasan por `_sanitize_for_json` (NaN/inf); mantener al añadir endpoints.
