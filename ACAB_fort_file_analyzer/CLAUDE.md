<!-- Guardar como: ACAB_fort_file_analyzer/CLAUDE.md -->

# ACAB Fort File Analyzer

App web Flask (monousuario, 127.0.0.1:5001) para analizar ficheros de salida `fort.6` de ACAB 2008: parsea múltiples simulaciones (subcarpetas), convierte átomos→actividad, grafica evolución temporal (Plotly) y genera informes y tablas comparativas por isótopo. Parte de la suite del TFG (ver CLAUDE.md de la carpeta padre).

## Arranque y stack

- `C:\venv\acab-venv\Scripts\python app.py` — puerto 5001 por defecto (`--port`/`-p` o variable `ACAB_ANALYZER_PORT`; `--host`/`ACAB_ANALYZER_HOST`, por defecto 127.0.0.1).
- Flask + waitress (con fallback al servidor de desarrollo si waitress falta).
- Dependencias: flask, waitress, pyyaml, numpy (requirements.txt). Plotly, Bootstrap y js-yaml por CDN.

## Ficheros clave

- `fort_analyzer.py` — motor de análisis, todo el conocimiento del dominio:
  - Parsers: `leer_fort6_irradiacion` (sección NUMBER OF ATOMS, átomos/cm³), `leer_fort6_enfriamiento` (sección NUCLIDE RADIOACTIVITY, Bq/cm³), `leer_inp5` (T_irr, T_cool, flujos, XNORM), `leer_decay_dat` (semividas, codificación ZZAAAS, S=1 metaestable).
  - Cálculo: conversión A = λ·N en irradiación; `calcular_pico`, `calcular_informe_isotopo`, `calcular_tablas_comparativas`.
  - Fase 5 — métricas de optimización de producción (integradas en `calcular_informe_isotopo` bajo la clave `"metricas"`, por simulación):
    `calcular_saturacion` (curva teórica A_teo=A_sat·(1−e^−λt) anclada al valor ACAB en T_irr + tabla de tiempos a 50/75/90/95 % de saturación),
    `calcular_rendimiento` (A_pico/T_irr vs. ganancia marginal del último 10 % de irradiación) y `calcular_pureza` (P = A(objetivo)/ΣA(impurezas) en t_pico, base de la tabla de contribuciones por isótopo). `isotopos_mismo_elemento` calcula el criterio POR DEFECTO de impurezas (mismo elemento que el isótopo objetivo); es el único criterio soportado como default. Editable desde la UI vía el parámetro `isotopos_impureza`.
  - F1 (`RUNBOOK_F1_pureza_temporal.md`) — `calcular_pureza_serie` (misma clave `"metricas"`, campo `pureza_serie`): pureza radionucleídica como serie temporal P(t) durante TODO el enfriamiento (t=0 = fin de irradiación), con el instante de cruce del umbral farmacéutico 99,9 % (`UMBRAL_PUREZA_PCT`; interpolación log-lineal de actividades + bisección si el cruce cae entre dos timesteps reales, nunca de P directamente), casos borde ya-alcanzado-en-t=0 / nunca-alcanzado, aviso si P vuelve a bajar del umbral tras el cruce (no se asume monotonicidad) y la ventana de administración (actividad del objetivo en t_cruce y como fracción de su pico). Coexiste con el `calcular_pureza` escalar (dominios distintos: éste cubre toda la irradiación+enfriamiento en un instante arbitrario, para la tabla de contribuciones; `pureza_serie` es solo enfriamiento). El badge de un vistazo "P = {v} %" que duplicaba a la tabla de contribuciones se retiró de la UI (absorbido por la gráfica P(t), que ya muestra el valor en el instante fisicamente relevante, t_cruce).
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
  `RUNBOOK_figuras_yaml.md` (`../acab_suite/`): ya no existe `DEFAULT_FIGURAS`
  ni el endpoint `/api/defaults` (sin otros consumidores, se retiró entero —
  ver decisión 7 del runbook). `_yaml_candidates(folder)` centraliza el orden
  de auto-descubierto (`figuras.yaml` → `figuras - multiples simulaciones.yaml`
  → `config.yaml`, en carpeta y padre) usado por `_load_yaml_config` y
  `/api/scan`. `/api/analyze` devuelve `figuras: []` (no fallback) y
  `yaml_config` (dict YAML completo tal cual, `{}` si no hay YAML) para que el
  frontend pueda hacer round-trip de secciones ajenas a `figuras` al
  guardar/descargar. `POST /api/figuras/save` `{folder, yaml_text, overwrite}`
  valida `folder` contra `_analysis_cache`, que `yaml_text` parsee con una
  clave `figuras` de tipo lista (422 si no), y escribe
  `<folder>/figuras.yaml` en UTF-8 (409 si ya existe y `overwrite` no es
  `true`).
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
  Pestaña "Actividad por Isótopo" (`RUNBOOK_figuras_yaml.md`): sin figuras
  (`analysisData.figuras.length === 0`) → `renderFigurasEmptyState` (dos
  acciones: cargar YAML por selector, crear con el editor). Badge
  `figuras-badge` (`updateFigurasBadge`) refleja `yaml_used` (auto → "carpeta",
  upload → "cargado a mano", none → "sin figuras"). Selector
  `figuras-yaml-file-input` lee el `.yaml` con `FileReader` y relanza
  `doAnalyze({ yamlContentOverride })` → `/api/analyze` con `yaml_content`
  (necesario porque `semividas` afecta al cálculo en servidor). Snapshot al
  analizar: `_state.figurasOriginal` (para el botón "Restaurar YAML cargado",
  deshabilitado si `yaml_used === 'none'`) y `_state.yamlConfigLoaded` (dict
  YAML completo, para el round-trip de `_buildFigurasYamlText()` — sustituye
  SOLO la clave `figuras`, conserva el resto). `downloadFigurasYaml()`
  (Blob) y `saveFigurasToFolder()` (`POST /api/figuras/save`, confirma y
  reintenta con `overwrite:true` si ya existe, luego re-analiza) usan
  `jsyaml.dump()` (CDN) para serializar.
- `static/js/units.js` — conversión pura de unidades de actividad (Bq/cm³ ↔ MBq/g / actividad total), aplicada por simulación en el frontend.
- `static/js/export_utils.js` — generación CSV pura (delimitador/decimal es-ES o internacional) para gráficas, informe y tablas comparativas.
- `static/js/reference_data.js` — parser del CSV de datos de referencia (`docs/SPEC_csv_datos_referencia.md`), interpolación lineal recortada a los extremos y métricas de desviación (Fase 4: superposición de datos experimentales/computacionales de referencia sobre la curva ACAB).
- `static/js/optim_utils.js` — puro (UMD, sin DOM): combina `sweep_manifest` (folder→params) con `informe.simulations`/`informe.metricas` YA calculados por el servidor (A_pico, t_pico, pureza, rendimiento) para la pestaña "Optimización" (Fase 5 opcional del barrido); NO recalcula ninguna fórmula física, solo combina/agrupa. `mergeSweepRows`, `paramKeys`, `groupByOtherParams` (series de color = resto de dimensiones del barrido), `yRawValue`/`yNeedsUnitConv` (selector de  variable Y: A_pico por defecto, t_pico, pureza, rendimiento). Renderizado (`renderOptimizacion` en app.js) solo se activa si `analysisData.sweep_manifest` no es `null`.
  `isSpectrumSweep`/`spectrumRowLabel` (U4 del BACKLOG): el barrido espectral tiene `params` con `n_grupos`/`frac_termica`/`frac_epitermica`/`frac_rapida` (todos numéricos), así que `groupByOtherParams` los trataba como dimensiones de color y volcaba sus valores en la leyenda — ilegible. `renderOptimizacion` detecta `isSpectrumSweep(manifest)` y delega en `renderOptimizacionSpectrum`/`_renderSpectrumOptimChart` (app.js): una SOLA serie (barras, eje X categórico) con `spectrumRowLabel` (el NOMBRE del espectro, `params.espectro` — criterio compartido con la vista de "consultar un barrido" de U6 del INP configurator; degrada al identificador de carpeta si un manifest viejo no lo trae, nunca a un volcado de parámetros). No toca el render de los otros 3 tipos de barrido (`_renderOptimChart` original, sin cambios).
- `static/js/pureza_time_utils.js` — puro (UMD, sin DOM; F1, `RUNBOOK_F1_pureza_temporal.md`): da forma (rango de eje, clase de badge, formato de fracción del pico) a `informe.metricas[sim].pureza_serie` (P(t) durante el enfriamiento, ya calculado por `fort_analyzer.calcular_pureza_serie`) para la gráfica de la pestaña "Informe Isótopo"; no recalcula pureza ni t_cruce. `purezaYRange`, `estadoBadgeClass`, `formatFraccionPico`. Renderizado (`_renderPurezaSerieChart` en app.js, dos paneles apilados P(t)/A(iso,t) con Plotly) se llama siempre tras `_renderMetricasOptimizacion`.
- `figuras.yaml` — ejemplo real de configuración de figuras (16 figuras del caso Te/Xe/I del TFG); el formato se documenta en README §7. NO se carga automáticamente salvo que la carpeta analizada coincida con esta raíz.
  `docs/ejemplo_figuras_TeO2.yaml` es una plantilla equivalente más simple (15 figuras) pensada para copiar/cargar desde cero.
- `compare_simulaciones.py` — **[LEGACY]**: la densidad de normalización ya se lee automáticamente de `CONCENTRATIONS(GRAM)` (`leer_fort6_concentraciones`) y la superposición de datos experimentales la cubre `reference_data.js`; no invertir más en este script.
- `add_report_sheet.py` — auxiliar puntual de Excel; no forma parte de la app.

## Tests

Suite de tests oro (scripts autocontenidos, sin framework, estilo de la suite):

- `C:\venv\acab-venv\Scripts\python tools\test_fort_analyzer.py` — parsers (`fort.6`, `inp.5`, `DECAY.dat`), cálculo del pico, `CONCENTRATIONS(GRAM)` y conversiones de unidad, contra la simulación de referencia. Incluye `test_desactualizada()` (Fase R5 del runbook runner v2): toca mtimes con `os.utime` sobre un fixture temporal y comprueba el flag `desactualizada` en ambos sentidos.
- `C:\venv\acab-venv\Scripts\python tools\test_api.py` — API REST vía `app.test_client()` (flujo `/api/analyze` → `/api/isotopo_report`, cache keyed por carpeta y errores controlados). Incluye `test_figuras_save()` (`RUNBOOK_figuras_yaml.md`): guardado feliz + discovery posterior como 'auto', 409 sin overwrite, 422 con YAML inválido/sin clave `figuras` lista, round-trip que conserva una sección `semividas` de un YAML de partida. También verifica que `pureza_serie` (F1) viaja en `metricas` con el caso oro de ref_sim (19 puntos, t_cruce=0, ventana de administración).
- `C:\venv\acab-venv\Scripts\python tools\test_reference_data.py` — oráculo Python de `reference_data.js` (fixtures CSV de `tests/fixtures/experimental/` y criterio de aceptación de la Fase 4 contra la ref_sim).
- `C:\venv\acab-venv\Scripts\python tools\test_metricas.py` — métricas de optimización de producción (Fase 5: saturación, rendimiento, pureza) con curvas sintéticas de solución analítica conocida (no depende de la ref_sim). Incluye `calcular_pureza_serie` (F1): 3 timesteps de ref_sim verificados contra el texto del fort.6 + casos borde sintéticos (cruce interpolado con solución analítica cerrada, ya-alcanzado, nunca-alcanzado, no monotonía).
- Node (disponible en esta máquina — comprobar con `Get-Command node` antes de asumir lo contrario): `node tools\test_units.js`, `node tools\test_export.js`, `node tools\test_reference_data.js` — tests directos de las funciones puras de frontend. Sus oráculos numéricos también están espejados en los scripts Python de arriba.
- `node tools\test_optim_utils.js` — combinación pura `sweep_manifest` + informe de `static/js/optim_utils.js` (Fase 5 opcional, pestaña Optimización). Sin oráculo Python: no reproduce ninguna fórmula física (esas ya están cubiertas por `test_metricas.py`/`test_fort_analyzer.py`), solo combina/agrupa datos ya calculados — su verificación vive únicamente en node, como `test_export.js`.
- `node tools\test_pureza_time_utils.js` — funciones puras de `static/js/pureza_time_utils.js` (F1: rango de eje de la gráfica P(t), badge de estado, formato de fracción del pico). Sin oráculo Python: solo da forma a `pureza_serie`, ya calculado y verificado en `test_metricas.py`/`test_api.py` — su verificación vive únicamente en node.

Fixtures en `tests/fixtures/ref_sim/` (simulación v.5 "info thesis") y `tests/fixtures/experimental/` (CSV de la Fase 4); valores oro documentados en `tests/fixtures/README.md` y `docs/SPEC_csv_datos_referencia.md`. Cada script devuelve código de salida 0/1. Regla: cualquier cambio en `fort_analyzer.py` o en los módulos JS puros debe dejar toda la suite (Python + node) en verde y añadir los tests oro correspondientes.

## Semántica del dominio (no violar)

- Estructura de entrada: carpeta padre con subcarpetas, cada una con `fort.6` (obligatorio), `inp.5` y `DECAY.dat` (opcionales). Modo simulación única si `fort.6` está en la raíz.
- La columna `RESTART` del fort.6 marca el inicio del enfriamiento; la columna   `INITIAL` es el estado pre-irradiación y se OMITE en los análisis de enfriamiento.
- Prioridad de semividas: sección `semividas` del YAML > `DECAY.dat` > tabla interna `DEFAULT_SEMIVIDAS` (fallback Te/I/Xe).
- Unidades: los datos internos y el cache SIEMPRE están en Bq/cm³; la conversión a MBq/g / actividad total es un factor por simulación aplicado en el FRONTEND (`static/js/units.js`), no en el backend.
- Claves de isótopo tal como aparecen en fort.6, en mayúsculas (`I131`, `XE133M`); `iso_label()` genera la notación Unicode para la UI.
- Datos de referencia externos (Fase 4, `reference_data.js`): el t=0 de una serie con `fase: enfriamiento` es el fin de la irradiación (RESTART), igual que en el resto de la app; se traslada sumando `T_IRR_h` de la simulación de referencia elegida al importar. Las series viven solo en `appState` (`_state.refSeries`), nunca en el cache del servidor ni en disco.

## Gotchas

- `/api/browse-folder` abre el selector nativo vía tkinter en subprocess: frágil en instalaciones Python sin tkinter; el campo de ruta manual es el fallback. No convertirlo en dependencia dura de ningún flujo.
- Respuestas JSON pasan por `_sanitize_for_json` (NaN/inf); mantener al añadir endpoints.
