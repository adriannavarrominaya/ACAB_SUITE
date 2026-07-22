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
  - F2 (BACKLOG) — `calcular_actividad_especifica_yodo_serie` (misma clave `"metricas"`, campo `actividad_especifica_yodo_serie`): actividad específica del yodo A_esp(t) = A(objetivo,t)/masa_total_yodo(t) [MBq/g] durante el enfriamiento (mismo dominio que `pureza_serie`) — el I-127 estable y el I-129 de vida larga no ensucian la pureza radionucleídica pero DILUYEN el producto. `analizar_carpeta` ahora guarda también `datos_irr_atomos` (átomos/cm³ SIN convertir a Bq, por simulación) junto a `datos_irr_Bq`: para isótopos estables (λ=0) la conversión a Bq pierde la población, así que la masa de yodo necesita el dato crudo. La masa total suma TODOS los isótopos de yodo presentes en el fort.6: `IODINE_ESTABLE_O_VIDA_LARGA` (I127, I129 — corrección F2b, ver abajo) vía el último punto de `datos_irr_atomos` (tabla NUMBER OF ATOMS al fin de irradiación) mantenido constante durante todo el enfriamiento; el resto (I128, I130, I130M, I131, I132, I132M...) con serie de enfriamiento y λ>0 vía N(t)=A(t)/λ en cada timestep (exacto, recupera la población interna de ACAB, incluida la alimentación desde precursores durante el enfriamiento — ver `tests/fixtures/README.md` para el desglose numérico de por qué A_esp DECRECE en ref_sim pese a que A(I131,t) crece). Átomos→gramos usa el número másico como masa molar (error <0.1 %). `CONCENTRATIONS(GRAM)` nunca sirve aquí: solo cubre los elementos de partida del target (O, Te), nunca un producto de decaimiento como el yodo. Solo definida si `iso_key` es un isótopo de yodo (`None` si no); `t_destacado_h` (normalmente el `t_cruce` de `pureza_serie`, ya resuelto por `calcular_informe_isotopo`) resalta el valor en ese instante — "qué actividad específica tiene el producto cuando alcanza calidad farmacéutica".
  - F2b (BACKLOG, 2026-07-21) — bug confirmado: el diseño original de F2 recuperaba N(I129,t) vía A(t)/λ igual que cualquier isótopo radiactivo, pero λ(I129) es tan diminuta (T½≈1.57e7 y) que dividir por ella amplifica el redondeo de imprenta del fort.6 (~4-5 cifras significativas) en un recuento de átomos sin precisión fiable; en irradiaciones LARGAS (donde Te127/Te129 alimentan I127/I129 durante horas de enfriamiento) esto haría que el diluyente estable dominara la masa de forma espuria. `IODINE_ESTABLE_O_VIDA_LARGA` centraliza la lista (I127 estable, I129 T½ de DECAY.dat/NNDC) que se excluye de la rama A(t)/λ. En el pulso corto de la ref_sim (T_irr≈10 s) el efecto es casi inapreciable en t=0 (A=λN es una identidad exacta en ese instante: leer la tabla de átomos o dividir por λ da lo mismo), así que el valor oro de `test_metricas.py` apenas cambia (4505547272.65 MBq/g, antes 4505514996.65); la diferencia se hace notar en t>0 y en irradiaciones largas — verificado con un escenario sintético (`test_actividad_especifica_yodo_i129_congelado_vs_creciente`) que exagera el crecimiento de A(I129,t) en el enfriamiento. Test de plausibilidad estructural nuevo: A_esp(t) nunca puede superar el techo físico sin portador λ(I131)·N_A/masa(I131)≈4.5967e9 MBq/g, en NINGÚN t ni simulación (`test_actividad_especifica_yodo_techo_fisico`). Importante: la firma numérica de F2/F2b está anclada al fixture `tests/fixtures/ref_sim` (simulación v.5 "info thesis"), NO a otras simulaciones de `simulaciones/` con poblaciones de I127/I129 muy distintas — cada fort.6 tiene su propia firma, no comparar valores entre carpetas sin releer su propia tabla NUMBER OF ATOMS.
  - `GAMMA_I131` hardcodeado (espectro ENSDF/NNDC, solo ¹³¹I por ahora); usado en `informe.gamma_spectrum` (Informe Isótopo) y como fallback de `/api/gamma-spectrum` — no reemplazado por B1, que es un cálculo GENÉRICO aparte (pestaña "Espectro gamma", cualquier nucleido con entrada en PHOTON.dat).
  - B1 del BACKLOG (`runbook_B1_espectro_gamma.md`, `acab_suite/`) — espectro gamma de emisión de la muestra desde la librería genérica PHOTON.dat de ACAB:
    - Fase 1 — `leer_photon_dat(filepath) -> {acab_key: [[E_keV, intensidad_pct], ...]}`: parsea bloques por nucleido (cabecera Z/símbolo+A[M]/nº de líneas, luego pares E[MeV]/intensidad[%] en notación científica, 3 pares por línea de texto salvo la última fila de un bloque si el nº de líneas no es múltiplo de 3), tolerante a CRLF/LF. Energías convertidas MeV→keV (convención de espectrometría) para que el resultado tenga la misma forma que `GAMMA_I131`. Nucleido sin entrada → simplemente ausente del dict, nunca error.
    - Fase 2 — `calcular_espectro_gamma(sim, t_h, libreria) -> {"t_h", "lineas": [{"E_keV","nucleido","intensidad_pct","tasa_fotones_s_cm3"}], "nucleidos_sin_lineas": [...]}`: combina el inventario de enfriamiento (`datos_cool`, Bq/cm³) en el timestep real MÁS CERCANO a *t_h* con la librería — tasa = A_nuclido(t) × intensidad/100, en fotones/(s·cm³) (mismo criterio "interno siempre en Bq/cm³" que el resto del módulo; la conversión a fotones/(s·g) es del frontend, `static/js/units.js`, no se duplica aquí). Isótopos con actividad no nula pero sin entrada en la librería van a `nucleidos_sin_lineas`, nunca rompen el resto del cálculo.
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
  B1b del BACKLOG — `POST /api/browse-file` `{title?, initial_dir?}`: variante
  de `/api/browse-folder` con `filedialog.askopenfilename` (selector nativo
  de UN fichero, no carpeta) para elegir la ruta de PHOTON.dat desde la
  propia pestaña "Espectro gamma"; mismo patrón de subprocess tkinter, sin
  test automático (el diálogo bloquea esperando al usuario).
  B1 del BACKLOG — `POST /api/espectro_gamma` `{folder, sim, t_h, photon_dat_path?}`:
  requiere `/api/analyze` previo sobre `folder` (mismo criterio 404 que
  `/api/isotopo_report`); `sim` por defecto la primera simulación, `t_h` por
  defecto el primer timestep de enfriamiento. La librería PHOTON.dat se
  autodescubre en `/api/analyze` igual que DECAY.dat (junto al fort.6 de la
  primera simulación; override en el body con `photon_dat_path`, último
  recurso la variable de entorno `ACAB_PHOTON_DAT`) y se cachea en
  `_analysis_cache[folder]["libreria_gamma"]`; `photon_dat_path` en la
  petición a este endpoint recarga la librería EN CALIENTE (sin repetir
  `/api/analyze`) y la deja cacheada para llamadas siguientes sobre la misma
  carpeta. `/api/analyze` expone `photon_dat_used`/`photon_dat_path` igual
  que `decay_dat_used`/`decay_dat_path`.
- `static/js/app.js` — UI + gráficas Plotly. Con i18n (`static/js/i18n/es.json` /
  `en.json`, función `t()`, atributos `data-i18n*`); español por defecto.
  Soporta deep link `?folder=<carpeta>` (Fase R3 del runbook runner v2, botón
  "Abrir en Fort Analyzer" del INP configurator): al cargar, si el query param
  está presente rellena `folder-input` y lanza `doAnalyze()` automáticamente.
  Pestaña "Espectro gamma" (B1 del BACKLOG, `renderEspectroGamma`/
  `fetchEspectroGamma`/`_renderEspectroChartAndTable`): solo depende de la
  carpeta analizada, no del isótopo seleccionado (a diferencia de Informe/
  Tablas/Optimización) — se activa al mostrar la pestaña (lazy, como
  "Actividad por Isótopo"). El espectro se pide al servidor bajo demanda
  (`POST /api/espectro_gamma`, no viaja entero en `/api/analyze`: con un
  PHOTON.dat completo podría ser enorme) por simulación + instante de
  enfriamiento elegidos; los filtros de rango de energía y tasa mínima
  (`_state.espectroFiltros`, sobrevive a rebuilds del panel — cambio de
  idioma, simulación, instante) se aplican SOLO en el cliente sobre lo ya
  recibido (`static/js/espectro_gamma_utils.js`, puro: `filtrarLineas`,
  `agruparPorNucleido`, `topLineas`, `construirTrazasStick`). Ruta de
  PHOTON.dat editable en la propia pestaña (campo + botón "Cargar
  librería", recarga en caliente vía el mismo endpoint). Sección
  informativa colapsable con los nucleidos presentes sin líneas en la
  librería (`nucleidos_sin_lineas`). Exportación CSV de la tabla de líneas
  con `ACABExport`/`emitCSV`, mismo patrón que el resto de tablas.
  B1b del BACKLOG (pulido tras primer uso real) — tres arreglos:
  (1) ruta de PHOTON.dat con explorador nativo de FICHERO (`POST
  /api/browse-file`, variante de `/api/browse-folder` que usa
  `filedialog.askopenfilename`) además del campo manual; la última ruta
  cargada con éxito se recuerda en `localStorage`
  (`PHOTON_PATH_KEY = 'fort-analyzer-photon-path'`) y se reintenta
  automáticamente y en silencio (sin toast de error si ya no existe) la
  primera vez que se abre la pestaña tras un análisis, SOLO si el servidor
  no autodescubrió ya una librería junto al fort.6 (`_state.espectroAutoLoadDone`
  evita reintentarlo en cada rebuild). (2) Umbral de tasa mínima POR DEFECTO
  relativo al máximo del instante (`ACABEspectroGamma.umbralPorDefecto`,
  máximo/1e6) para que la vista inicial sea legible sin tocar ningún filtro
  — verificado que NO había bug de escala/recorte en el eje Y (los datos y
  el autorange de Plotly ya eran correctos; el problema era puramente de
  legibilidad por el rango dinámico de ~30 décadas de las líneas más
  débiles). Se recalcula en cada instante/simulación mientras el usuario no
  toque el campo a mano (`_state.espectroTasaMinTouched`); tecleando "0" se
  desactiva el filtro explícitamente. (3) Leyenda acotada a los 8 nucleidos
  de mayor tasa TOTAL (`ACABEspectroGamma.construirTrazasStickTopN`,
  criterio de U4: nunca volcado completo); el resto se agrupa en una única
  traza "otros" con color neutro, cuyo hover sigue mostrando el nucleido
  real de cada punto vía `customdata` (no el nombre de traza compartido).
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
  F6 del BACKLOG — `seriesForMetrics(series, iso)`: TODAS las series cargadas de un isótopo generan tabla de desviación, sea su `tipo` `experimental` o `computacional_referencia` (antes solo la experimental; la distinción huecos/rellenos de la gráfica no cambia, solo se amplió qué entra en las métricas). `resolveTargetSimName(simNames, requestedName)`: con varias simulaciones cargadas, decide contra cuál se interpolan TODAS las tablas — respeta `requestedName` si sigue entre las disponibles, si no (o es la primera vez) cae a la primera; `null` sin ninguna simulación. Ambas puras, sin DOM. `app.js` (`renderRefDataMetrics`/`exportRefMetricsCSV`): usa `seriesForMetrics` en vez del filtro `tipo === 'experimental'` de antes; el desplegable `#refdata-target-sim` (solo visible con >1 simulación, estado en `_state.refMetricsTargetSim`) alimenta `resolveTargetSimName` y su resultado sustituye a `sim = sims[s.refSimName]` como simulación objetivo de TODAS las tablas — `s.refSimName` (elegida al importar cada serie) sigue existiendo pero ahora solo para la conversión de unidad (densidad/volumen), no para las métricas. Cabecera de tabla y CSV exportado muestran tipo + nombre de la simulación objetivo (claves i18n `metrics_title`/`metrics_csv_meta`).
- `static/js/optim_utils.js` — puro (UMD, sin DOM): combina `sweep_manifest` (folder→params) con `informe.simulations`/`informe.metricas` YA calculados por el servidor (A_pico, t_pico, pureza, rendimiento, actividad específica de yodo) para la pestaña "Optimización" (Fase 5 opcional del barrido); NO recalcula ninguna fórmula física, solo combina/agrupa. `mergeSweepRows`, `paramKeys`, `groupByOtherParams` (series de color = resto de dimensiones del barrido), `yRawValue`/`yNeedsUnitConv` (selector de  variable Y: A_pico por defecto, t_pico, pureza, rendimiento, `a_esp_yodo` — F2 del BACKLOG, `met.actividad_especifica_yodo_serie.valor_destacado_MBq_g`, `null` si el isótopo no es yodo o no hay t_cruce; ya viene en MBq/g del servidor, invariante como t_pico/pureza — no pasa por el selector de unidad Bq/cm³↔MBq/g↔MBq↔mCi del target). Renderizado (`renderOptimizacion` en app.js) solo se activa si `analysisData.sweep_manifest` no es `null`.
  `isSpectrumSweep`/`spectrumRowLabel` (U4 del BACKLOG): el barrido espectral tiene `params` con `n_grupos`/`frac_termica`/`frac_epitermica`/`frac_rapida` (todos numéricos), así que `groupByOtherParams` los trataba como dimensiones de color y volcaba sus valores en la leyenda — ilegible. `renderOptimizacion` detecta `isSpectrumSweep(manifest)` y delega en `renderOptimizacionSpectrum` (app.js): `spectrumRowLabel` (el NOMBRE del espectro, `params.espectro` — criterio compartido con la vista de "consultar un barrido" de U6 del INP configurator; degrada al identificador de carpeta si un manifest viejo no lo trae, nunca a un volcado de parámetros) identifica cada punto, sea cual sea el render elegido. No toca el render de los otros 3 tipos de barrido (`_renderOptimChart` original, sin cambios).
  `SPECTRUM_FRAC_KEYS`/`spectrumNumericKeys`/`spectrumTextPositions` (U4b del BACKLOG): U4 dejó el barrido espectral sin selector de eje X (solo barras por nombre de espectro), pero la figura central de la memoria es A_pico vs. `frac_termica`. `renderOptimizacionSpectrum` restaura el selector "Parámetro (eje X)" con la opción categórica "Espectro" (`_renderSpectrumOptimChart`, barras, comportamiento de U4 sin cambios) + las fracciones espectrales presentes en el manifest (`spectrumNumericKeys`, siempre `frac_termica`/`frac_epitermica`/`frac_rapida` en ese orden fijo, NUNCA `n_grupos` — sin significado físico como eje X). Con eje X numérico, `_renderSpectrumScatterChart` dibuja una SOLA serie de dispersión (nunca agrupada por parámetros — la leyenda ilegible que U4 eliminó) con el nombre del espectro como etiqueta de texto junto a cada punto (`mode: 'markers+text'`); `spectrumTextPositions` alterna la posición arriba/abajo cuando dos puntos consecutivos (ya ordenados por X) caen a menos del 4 % del rango, para que los 9 reactores reales agrupados en `frac_termica` no se solapen. Fracción ausente del manifest (versión antigua) → opción de eje X deshabilitada con nota (`optim.spectrum_x_key_disabled`/`_all_disabled`), nunca rompe; sigue disponible la vista por "Espectro".
- `static/js/pureza_time_utils.js` — puro (UMD, sin DOM; F1, `RUNBOOK_F1_pureza_temporal.md`): da forma (rango de eje, clase de badge, formato de fracción del pico) a `informe.metricas[sim].pureza_serie` (P(t) durante el enfriamiento, ya calculado por `fort_analyzer.calcular_pureza_serie`) para la gráfica de la pestaña "Informe Isótopo"; no recalcula pureza ni t_cruce. `purezaYRange`, `estadoBadgeClass`, `formatFraccionPico`. Renderizado (`_renderPurezaSerieChart` en app.js, dos paneles apilados P(t)/A(iso,t) con Plotly) se llama siempre tras `_renderMetricasOptimizacion`.
  F2 del BACKLOG — `_renderActividadEspecificaYodoChart` (app.js, llamada justo después de `_renderPurezaSerieChart`, mismo contenedor de métricas): gráfica de un solo panel de `informe.metricas[sim].actividad_especifica_yodo_serie` (`fort_analyzer.calcular_actividad_especifica_yodo_serie`), mismo dominio temporal que P(t) pero sin umbral ni semáforos (fuera de alcance del diseño F2). Línea vertical + badge en `t_destacado_h`/`valor_destacado_MBq_g` (el t_cruce de pureza, ya resuelto en el servidor). La sección `#aesp-yodo-section` se oculta entera si NINGUNA simulación trae el dato (isótopo seleccionado no es yodo — el servidor ya filtra por elemento, el frontend no repite esa lógica). No tiene módulo `_utils.js` propio: no hay lógica pura reutilizable más allá de pintar con Plotly.
- `static/js/espectro_gamma_utils.js` — puro (UMD, sin DOM; B1 del BACKLOG): da forma al espectro ya calculado por el servidor (`fort_analyzer.calcular_espectro_gamma`) para la pestaña "Espectro gamma" — `filtrarLineas` (rango de energía + tasa mínima, recorta el ruido de líneas débiles), `agruparPorNucleido`/`nucleidosOrdenados` (coloreado/leyenda por nucleido de origen), `topLineas` (tabla), `construirTrazasStick` (dos trazas de Plotly por nucleido: palotes `mode:'lines'` sin hover propio + marcadores en la punta con el hover rico, mismo `legendgroup` para que el toggle de leyenda afecte a ambas). No recalcula ninguna tasa; solo filtra/agrupa/da forma a lo ya recibido — su verificación vive únicamente en node (como `optim_utils.js`/`pureza_time_utils.js`).
  B1b del BACKLOG — `umbralPorDefecto(lineas, factor=1e6)` (máximo del instante / factor, 0 si no hay líneas o el máximo es 0); `totalTasaPorNucleido`/`topNNucleidos` (suma de tasas por nucleido, para decidir qué entra en la leyenda — NO la tasa de su línea más fuerte); `construirTrazasStickTopN` (como `construirTrazasStick` pero acota la leyenda a los N nucleidos de mayor tasa total y agrupa el resto en una única traza "otros" de color neutro, con `customdata` por punto para que el hover conserve el nucleido real de cada línea agrupada).
- `figuras.yaml` — ejemplo real de configuración de figuras (16 figuras del caso Te/Xe/I del TFG); el formato se documenta en README §7. NO se carga automáticamente salvo que la carpeta analizada coincida con esta raíz.
  `docs/ejemplo_figuras_TeO2.yaml` es una plantilla equivalente más simple (15 figuras) pensada para copiar/cargar desde cero.
- `compare_simulaciones.py` — **[LEGACY]**: la densidad de normalización ya se lee automáticamente de `CONCENTRATIONS(GRAM)` (`leer_fort6_concentraciones`) y la superposición de datos experimentales la cubre `reference_data.js`; no invertir más en este script.
- `add_report_sheet.py` — auxiliar puntual de Excel; no forma parte de la app.

## Tests

Suite de tests oro (scripts autocontenidos, sin framework, estilo de la suite):

- `C:\venv\acab-venv\Scripts\python tools\test_fort_analyzer.py` — parsers (`fort.6`, `inp.5`, `DECAY.dat`), cálculo del pico, `CONCENTRATIONS(GRAM)` y conversiones de unidad, contra la simulación de referencia. Incluye `test_desactualizada()` (Fase R5 del runbook runner v2): toca mtimes con `os.utime` sobre un fixture temporal y comprueba el flag `desactualizada` en ambos sentidos.
- `C:\venv\acab-venv\Scripts\python tools\test_api.py` — API REST vía `app.test_client()` (flujo `/api/analyze` → `/api/isotopo_report`, cache keyed por carpeta y errores controlados). Incluye `test_figuras_save()` (`RUNBOOK_figuras_yaml.md`): guardado feliz + discovery posterior como 'auto', 409 sin overwrite, 422 con YAML inválido/sin clave `figuras` lista, round-trip que conserva una sección `semividas` de un YAML de partida. También verifica que `pureza_serie` (F1) y `actividad_especifica_yodo_serie` (F2) viajan en `metricas` con el caso oro de ref_sim (19 puntos, t_cruce=0/t_destacado_h=0, ventana de administración / valor destacado ~4.5e9 MBq/g). Incluye `test_espectro_gamma()` (B1 del BACKLOG): `photon_dat_used=False` sin PHOTON.dat junto al fort.6 de ref_sim, override `photon_dat_path` con el extracto congelado carga la librería en caliente y la deja cacheada para llamadas siguientes, caso oro t=4,5h/línea 364 keV, 404 con ruta inexistente/carpeta no analizada.
- `C:\venv\acab-venv\Scripts\python tools\test_reference_data.py` — oráculo Python de `reference_data.js` (fixtures CSV de `tests/fixtures/experimental/` y criterio de aceptación de la Fase 4 contra la ref_sim). F6 del BACKLOG: `seriesForMetrics` (las series `fig6_exp4_experimental_normalizado.csv`/`fig6_exp4_computacional_normalizado.csv`, una de cada tipo, entran AMBAS al filtrar por isótopo) y `resolveTargetSimName` (selección/caída a la primera/`None` sin simulaciones, con nombres de simulación sintéticos).
- `C:\venv\acab-venv\Scripts\python tools\test_metricas.py` — métricas de optimización de producción (Fase 5: saturación, rendimiento, pureza) con curvas sintéticas de solución analítica conocida (no depende de la ref_sim). Incluye `calcular_pureza_serie` (F1): 3 timesteps de ref_sim verificados contra el texto del fort.6 + casos borde sintéticos (cruce interpolado con solución analítica cerrada, ya-alcanzado, nunca-alcanzado, no monotonía). Incluye `calcular_actividad_especifica_yodo_serie` (F2/F2b): caso oro de ref_sim (A_esp(t=0)=4505547272.634922 MBq/g tras F2b, comprobado a mano contra el desglose por isótopo del fort.6) + casos borde sintéticos ("solo I131" — invariante analítico: A_esp constante = actividad específica del isótopo puro λ·N_A/masa, independiente de A(t) — y "sin I127 estable, solo I131+I129") + F2b: `test_actividad_especifica_yodo_i129_congelado_vs_creciente` (escenario sintético tipo irradiación larga que demuestra que I129 usa la tabla de átomos congelada, no A(t)/λ) y `test_actividad_especifica_yodo_techo_fisico` (A_esp(t) nunca supera λ(I131)·N_A/masa(I131)≈4.5967e9 MBq/g, en ref_sim completo + casos sintéticos).
- Node (disponible en esta máquina — comprobar con `Get-Command node` antes de asumir lo contrario): `node tools\test_units.js`, `node tools\test_export.js`, `node tools\test_reference_data.js` — tests directos de las funciones puras de frontend. Sus oráculos numéricos también están espejados en los scripts Python de arriba.
- `node tools\test_optim_utils.js` — combinación pura `sweep_manifest` + informe de `static/js/optim_utils.js` (Fase 5 opcional, pestaña Optimización). Sin oráculo Python: no reproduce ninguna fórmula física (esas ya están cubiertas por `test_metricas.py`/`test_fort_analyzer.py`), solo combina/agrupa datos ya calculados — su verificación vive únicamente en node, como `test_export.js`.
- `node tools\test_pureza_time_utils.js` — funciones puras de `static/js/pureza_time_utils.js` (F1: rango de eje de la gráfica P(t), badge de estado, formato de fracción del pico). Sin oráculo Python: solo da forma a `pureza_serie`, ya calculado y verificado en `test_metricas.py`/`test_api.py` — su verificación vive únicamente en node.
- `C:\venv\acab-venv\Scripts\python tools\test_photon.py` — B1 del BACKLOG (Fases 1 y 2): `leer_photon_dat` contra el extracto congelado `tests/fixtures/ref_sim/PHOTON_extract.dat` (16 nucleidos I131=18 líneas/XE133=6 líneas, TE131M como entrada distinta de TE131, la línea 364,49 keV/81,2 % del I131 verificada contra ENSDF) y `calcular_espectro_gamma` contra ref_sim (cruce de nombres exacto fort.6↔PHOTON.dat, caso oro en enfriamiento tardío t=4,5 h con tasa(364 keV)=A(I131,4,5h)×0,812 comprobado a mano, I130M presente en el inventario pero ausente del extracto → `nucleidos_sin_lineas` sin romper el resto).
- `node tools\test_espectro_gamma_utils.js` — funciones puras de `static/js/espectro_gamma_utils.js` (B1: filtrado por energía/tasa, agrupación por nucleido, construcción de trazas de palotes; B1b: `umbralPorDefecto` con el caso oro real de ref_sim en t=3,750h —máximo=13398,0 fotones/(s·cm³), la línea de 364 keV—, `topNNucleidos` por tasa TOTAL no por línea más fuerte, y `construirTrazasStickTopN` —leyenda acotada + grupo "otros" con color neutro y `customdata` por punto—). Sin oráculo Python: solo filtra/agrupa/da forma a `espectro.lineas`, ya calculado y verificado en `test_photon.py` — su verificación vive únicamente en node.

Fixtures en `tests/fixtures/ref_sim/` (simulación v.5 "info thesis") y `tests/fixtures/experimental/` (CSV de la Fase 4); valores oro documentados en `tests/fixtures/README.md` y `docs/SPEC_csv_datos_referencia.md`. Cada script devuelve código de salida 0/1. Regla: cualquier cambio en `fort_analyzer.py` o en los módulos JS puros debe dejar toda la suite (Python + node) en verde y añadir los tests oro correspondientes.

## Semántica del dominio (no violar)

- Estructura de entrada: carpeta padre con subcarpetas, cada una con `fort.6` (obligatorio), `inp.5` y `DECAY.dat` (opcionales). Modo simulación única si `fort.6` está en la raíz.
- La columna `RESTART` del fort.6 marca el inicio del enfriamiento; la columna   `INITIAL` es el estado pre-irradiación y se OMITE en los análisis de enfriamiento.
- Prioridad de semividas: sección `semividas` del YAML > `DECAY.dat` > tabla interna `DEFAULT_SEMIVIDAS` (fallback Te/I/Xe).
- Unidades: los datos internos y el cache SIEMPRE están en Bq/cm³; la conversión a MBq/g / actividad total es un factor por simulación aplicado en el FRONTEND (`static/js/units.js`), no en el backend. Excepción puntual: `actividad_especifica_yodo_serie` (F2) ya viaja en MBq/g DE YODO desde el backend — no es la misma unidad/eje que el selector de arriba (ese es MBq/g del target, p. ej. TeO2), así que el frontend no lo reconvierte (`yNeedsUnitConv('a_esp_yodo') === false`).
- `datos_irr_atomos` (por simulación, junto a `datos_irr_Bq`): átomos/cm³ SIN convertir a Bq, de la sección NUMBER OF ATOMS (solo cubre la irradiación, no el enfriamiento — ver `leer_fort6_irradiacion`). Necesario para F2: convertir a Bq pierde la población de isótopos estables (λ=0 → A=0 siempre, aunque N no lo sea).
- Claves de isótopo tal como aparecen en fort.6, en mayúsculas (`I131`, `XE133M`); `iso_label()` genera la notación Unicode para la UI.
- Datos de referencia externos (Fase 4, `reference_data.js`): el t=0 de una serie con `fase: enfriamiento` es el fin de la irradiación (RESTART), igual que en el resto de la app; se traslada sumando `T_IRR_h` de la simulación de referencia elegida al importar. Las series viven solo en `appState` (`_state.refSeries`), nunca en el cache del servidor ni en disco.

## Gotchas

- `/api/browse-folder` y `/api/browse-file` (B1b del BACKLOG, variante de fichero para la ruta de PHOTON.dat) abren el selector nativo vía tkinter en subprocess: frágiles en instalaciones Python sin tkinter; el campo de ruta manual es el fallback en ambos. El diálogo BLOQUEA hasta que el usuario interactúa — no hay test automático para ninguno de los dos (mismo motivo que no hay test de `/api/browse-folder`: no se puede automatizar un diálogo nativo sin colgar la suite).
- Respuestas JSON pasan por `_sanitize_for_json` (NaN/inf); mantener al añadir endpoints.
