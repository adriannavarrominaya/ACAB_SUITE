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
  - F13 del BACKLOG (2026-08-08) — T½ resuelto POR SIMULACIÓN, no un único valor global para toda la carpeta: antes de esta corrección, `analizar_carpeta` leía el `DECAY.dat` de la PRIMERA simulación descubierta y lo aplicaba a TODAS (conversión átomos→actividad, actividad específica, techo sin portador) — silenciosamente incorrecto cuando otras simulaciones traían un `DECAY.dat` distinto (verificado: v2/v3/v4 del experimento de referencia traen T½(I-131)=693200 s, no los 693400 s de `DEFAULT_SEMIVIDAS`). `analizar_carpeta(folder, t12_dict, ..., yaml_t12_overrides=None)`: *t12_dict* pasa a ser solo el respaldo (`DEFAULT_SEMIVIDAS`, vía `build_t12_dict`); dentro del bucle por simulación, se busca `DECAY.dat` junto a SU PROPIO `fort.6` (`Path(fort6_path).parent`) y se resuelve `t12_sim = {**t12_dict, **own_t12, **yaml_t12_overrides}` (prioridad: YAML explícito > DECAY.dat propio > respaldo) — usado tanto para `datos_irr_Bq` (A=λ·N) como, vía `sim["_t12_dict"]`, por `calcular_informe_isotopo` para `calcular_saturacion`/`calcular_actividad_especifica_yodo_serie` de ESA simulación. Cada `sim_dict` expone `t12_source` (`"decay_dat"`|`"default"`) y `decay_dat_path` (str|None, procedencia pública) más `_t12_dict` (privado — la librería completa resuelta, NUNCA debe salir por la API: `app.py`/`/api/analyze` construye `public_simulations` filtrando toda clave `_`-prefijada antes de `jsonify`, mientras `_analysis_cache` conserva la versión rica para `/api/isotopo_report`). `calcular_informe_isotopo` añade `metricas[sim].nuclear_props` (T½/λ/A_esp — el "techo sin portador" — CON el T½ propio de esa simulación; el `nuclear_props` de nivel superior sigue siendo un bloque de referencia único, sin cambios, para no romper `exportReportCSV` ni tests existentes). Tests oro: `test_metricas.py::test_f13_decay_dat_por_simulacion` (copia `ref_sim` dos veces, edita el T½(I131) del `DECAY.dat` de UNA copia — Σ techos y actividad específica del yodo distintos entre ambas, ninguna hereda el de la otra); `test_api.py` verifica que `_t12_dict` nunca viaja en `/api/analyze`. UI: `app.js` (`renderIsotopoReport`) muestra una nota bajo la tarjeta "Propiedades Nucleares" con el T½ y procedencia aplicados a CADA simulación (`report.t12_source_note`); `exportReportCSV` la declara también en la cabecera del CSV.
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
  - F9 del BACKLOG (`runbook_F9_analisis_cadenas.md`, `acab_suite/`), Fase 1 — parsers y códec para el análisis de contribución por cadenas (ACAB+CHAINS):
    - `leer_concentraciones_iniciales(filepath) -> {acab_key: C_i}`: inventario isotópico inicial (t=0, INITIAL) de la PRIMERA tabla NUMBER OF ATOMS, solo isótopos con C_i > 0. Parser INDEPENDIENTE de `leer_fort6_irradiacion` (no lo reutiliza): ese parser solo reconoce isótopos con símbolo+masa pegados en un único token (`TE130`), pero el fort.6 separa símbolo y masa en dos tokens para elementos de una letra (`O 16`, `H  1`) — se perdería el oxígeno del blanco TeO2. Este parser combina ambos formatos de columna. Fuente de verdad del patch monoisotópico de F9 (Bloque #5, XCOMP copiado directamente del eco — verificación de unidades en `ACAB_inp_file_configurator/tests/fixtures/chains/PROCEDENCIA.md`). Decisión de sincronización (Fase 2 del runbook): inp-conf SÍ la necesita (UI de selección + generación del patch), duplicada como `chains_inventory.py` (fragmento sincronizado, ver CLAUDE.md raíz) en vez de importar entre apps.
    - `nombre_a_zzaaas(acab_key) -> int`: inverso del códec ZZAAAS de `leer_decay_dat` (nombre→código, p. ej. `TE130`→521300, `TE131M`→521311), reutilizando la misma tabla `_Z_TO_ELEM` (vía `_ELEM_TO_Z`) que la codificación directa — no se define una tabla nueva. Necesario para construir IINICIAL/IFINAL del input de CHAINS desde un isótopo elegido en la UI. Misma decisión de sincronización que arriba: duplicada en `chains_inventory.py` de inp-conf.
    - `leer_output_chains(filepath) -> {"iflag","inicial","ifinal","nmax","pcnt","nchain","nch","ptot","cadenas":[{"p","pasos":[{"desde","proceso","hasta","xsec","delta"}]}]}`: parsea el output de `chains.exe` (IFLAG=2) — cabecera, nº de cadenas encontradas (NCHAIN) y por encima de PCNT (NCH), y un bloque por cadena superviviente (delimitado por líneas de asteriscos; la ÚLTIMA cadena no cierra con separador propio, el fichero pasa directo a `JOB FINISHED` — el parser trata el fin de fichero como cierre implícito del último bloque). OJO normalización (corregida en F9e, ver más abajo): PTOT NO es siempre 100 — es la probabilidad TOTAL de que INITIAL acabe en IFINAL por cualquiera de las cadenas encontradas (puede ser ≈100, TE130→I131, o mucho menor, TE128→I131: PTOT=0.02304). El "P=" de CADA cadena sí está SIEMPRE normalizado a 100 entre las cadenas devueltas (Σ P ≈ 100, con la cola por debajo de PCNT descartada si NCH<NCHAIN), por eso X_z_i=P/100 vale sea cual sea PTOT — no confundir ambas magnitudes. F9d del BACKLOG (bug detectado en la primera ejecución real): cuando CHAINS no encuentra ningún camino INITIAL→IFINAL en ≤ NMAX pasos (caso real: O16/O17/O18 camino de I131, ningún isótopo de oxígeno decae a yodo), el fichero NO tiene NCHAIN/NCH/PTOT ni bloques de cadena — solo la cabecera y el literal `THERE ARE NO PATHWAYS FOR FORMATION OF NUCLIDE IFINAL`. Detectado por ese literal, devuelve `nchain=nch=0`, `ptot=0.0`, `cadenas=[]` sin lanzar (fixture congelado `tests/fixtures/chains/output_chain_no_pathways_O16.txt`, ver su `PROCEDENCIA.md`; O17/O18 tienen idéntica forma, un solo fixture cubre los tres).
    - Test oro `tools/test_chains.py` contra `tests/fixtures/chains/output_chain_Te130_to_I131.txt` (copia local — el original y su generación completa viven en `ACAB_inp_file_configurator/tests/fixtures/chains/`, ver `PROCEDENCIA.md` de ambas copias) y `tests/fixtures/ref_sim/fort.6`/`DECAY.dat` (mismo inp.5 byte-idéntico al caso manual de CHAINS).
  - F9 del BACKLOG, Fase 4 — tablas de contribución por isótopo/cadena de un análisis ya generado (y al menos parcialmente ejecutado) por `ACAB_inp_file_configurator/chains_analysis.py`:
    - `leer_chains_manifest(root) -> dict|None`: lee `chains_manifest.json` de la carpeta del análisis; mismo criterio de tolerancia que `leer_sweep_manifest` (`None` si no existe/no es JSON válido).
    - `calcular_analisis_cadenas(root, t_h=None, manifest=None) -> dict`: R_i = A_i(IFINAL,t\*)/A_ref(IFINAL,t\*) — A_i del `fort.6` monoisotópico de cada isótopo (`iso_<nombre>/`, reutiliza `analizar_carpeta` de una única carpeta, patrón "modo simulación única"), A_ref del `fort.6` de la carpeta de referencia (fuera de `root`, apuntada por el manifest; su `DECAY.dat`, si existe junto a ella, alimenta el t12_dict). t\* por defecto es el t_pico de IFINAL en la referencia (`calcular_pico`, mismo patrón de instante por defecto que la pestaña "Espectro gamma"); `t_h` explícito lo sustituye (`t_star_fuente`: `"pico_referencia"`|`"manual"`). X_z_i = P_z_i/100 del output de CHAINS de cada isótopo (`chains_<nombre>/output_chain.txt`, `leer_output_chains`); Y_z_i = R_i·X_z_i. `reference_folder` del manifest se resuelve relativa a `root` si no es absoluta (permite fixtures de test portables — un manifest real de `chains_analysis.py` siempre guarda una ruta absoluta). Degradación POR ISÓTOPO (F9d del BACKLOG, hotfix tras la primera ejecución real): un isótopo cuyo `fort.6` monoisotópico aún no existe (pipeline no ejecutado) se omite entero de `tabla1`. Un isótopo con `fort.6` listo pero `output_chain.txt` ausente/ilegible (corrupto, forma inesperada) conserva su fila de `tabla1` (R_i sigue siendo válido) con `nota_cadenas = NOTA_CHAINS_ILEGIBLE`; solo sus filas de `tabla2` se omiten — ningún fallo aislado bloquea el resto del informe. El caso "`output_chain.txt` legible pero sin ninguna cadena por debajo de NMAX" (p. ej. O16/O17/O18: sin camino físico O→I131, ver más abajo) NO es un error: `nota_cadenas=None`, R_i se muestra igual (≈0, coherente), `tabla2` sin filas de ese isótopo. Devuelve `tabla1` (`isotopo,c_i,a_i,a_ref,r_i,nota_cadenas`), `suma_r_i` (control de linealidad de Bateman — Σ R_i ≈ 1 solo con cobertura completa), `cobertura` (`n_seleccionados`,`n_total_inventario` — este último de `leer_concentraciones_iniciales` sobre la referencia —, `completa`), `tabla2` (ordenada por `y_z_i` descendente, con `nmax`/`pcnt`/`ptot` y el `diagrama` de cada cadena ya embebido — la regla del tablón "toda cifra de CHAINS cita su NMAX" se cumple porque NMAX/PCNT viajan junto a cada fila) y `t_candidatos_h` (unión ordenada de instantes reales de la referencia, para el selector de la UI).
    - `construir_diagrama_cadena(cadena, t12_dict) -> dict` (Fase 5): diagrama v1 de UNA cadena ya elegida — secuencia de `nodos` (nombre + T½ de `t12_dict`; `estable=True` si T½=inf, `conocido=False` si el nucleido no está en la librería, casos distintos) unidos por `aristas` (proceso + XSEC/DELTA tal cual de `leer_output_chains`). El grafo fusionado estilo Fig. 1 del paper queda fuera de alcance v1 (F9b). Verificado contra el caso oro real de Fase 1 (`output_chain_Te130_to_I131.txt` + `ref_sim/DECAY.dat`), sin fixture nuevo.
    - `_chain_label(cadena)`/`_nodo_diagrama(nombre, t12_dict)`: helpers privados de lo anterior (etiqueta compacta con el proceso de cada paso, `"TE128->(N,G-m)->TE129M->(N,G-g)->TE130->(N,G-g)->TE131->(B-)->I131"` — F9e del BACKLOG, antes solo nombres de nucleido, no distinguía cadenas con la misma secuencia de nucleidos y proceso distinto en algún paso — e info de un nodo del diagrama, respectivamente).
    - Tests oro nuevos en `tools/test_chains.py` contra el fixture **totalmente sintético** `tests/fixtures/chains_synthetic/` (2 isótopos ficticios FE56/MN55→CO57, ver su `PROCEDENCIA.md`: R_i/Σ R_i/X_z_i/Y_z_i verificados a mano) y contra el fixture real de Fase 1 (diagrama). `tools/test_api.py::test_chains_report` cubre el endpoint `POST /api/chains_report` (400 sin `root`, 404 sin `chains_manifest.json`, 200 con el caso sintético, selector de instante manual vía `t_h`).
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
  F9 del BACKLOG, Fase 4 — `POST /api/chains_report` `{root, t_h?}`:
  independiente del flujo `/api/analyze`/`_analysis_cache` de arriba (no
  requiere un análisis previo de "carpeta de simulaciones") — `root` es la
  carpeta de un análisis de cadenas con su propio `chains_manifest.json`.
  Sin caché propia: recalcula en cada petición
  (`fort_analyzer.calcular_analisis_cadenas`), el volumen de datos es
  pequeño y el caso de uso más frecuente (cambiar el instante t*) necesita
  releer las actividades igualmente. 404 si no hay `chains_manifest.json`
  en `root`; 422 si la referencia o algún fichero requerido no se puede
  leer (`ValueError`/`FileNotFoundError`).
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
  F9e del BACKLOG — deep link SEPARADO `?chains_root=<carpeta>` (mismo botón
  del INP configurator pero desde el panel de ejecución del análisis de
  cadenas, `static/js/chains_sweep.js`): un `chains_manifest.json` no es una
  carpeta de "Simulaciones" normal, así que `?folder=` aterrizaría en la
  pestaña equivocada; `?chains_root=` fija `_state.chainsRoot`, activa la
  pestaña "Análisis de cadenas" (`bootstrap.Tab...show()` sobre
  `tab-chains-btn`) y lanza `fetchChainsReport()` en cuanto se construye el
  panel (mismo evento `shown.bs.tab` que ya construye el panel la primera
  vez que se muestra la pestaña a mano).
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
  F9 del BACKLOG, Fase 4-5 — pestaña "Análisis de cadenas"
  (`renderChainsPanel`/`fetchChainsReport`/`_renderChainsResults`/
  `_renderChainsDiagram`): la ÚNICA pestaña independiente de
  `_state.analysisData`/`_state.folder` — tiene su propio campo de carpeta
  (`chainsRoot`) y se construye una sola vez al mostrarla por primera vez
  (`_state.chainsPanelBuilt`), sin esperar a ningún análisis previo de
  "carpeta de simulaciones". Selector de instante t* (`chains-t-select`,
  `_state.chainsTManual`) igual patrón que el de "Espectro gamma": null =
  usa el t_pico por defecto que devuelve el servidor. Clic en una fila de
  la tabla 2 (`_state.chainsSelectedRow`) pinta el diagrama lineal de esa
  cadena (`_renderChainsDiagram`, Fase 5): nodos con T½ formateado
  (`_formatT12Chains`, d/h/s según magnitud, "estable"/"T½ desconocido")
  y aristas con el proceso + XSEC/DELTA, todo ya calculado en el servidor
  (`fila.diagrama`, embebido en cada fila de `tabla2` por
  `calcular_analisis_cadenas` — sin endpoint propio). Exportación CSV de
  ambas tablas independiente del selector de unidad de actividad (esta
  pestaña trabaja siempre en Bq/cm³, la unidad interna del fort.6).
  F9f del BACKLOG (hotfix causa raíz) — hasta esta sesión la pestaña era
  "independiente" solo en el código: el HTML envolvía TODA la barra de
  pestañas (`#resultTabs`+`.tab-content`, incluida ésta) en
  `#results-panel` con `d-none` hasta el primer `/api/analyze` con éxito,
  así que ni un clic manual ni `?chains_root=` la hacían visible sin antes
  analizar una carpeta de "Simulaciones". Arreglado quitando ese `d-none`
  permanente (la barra de pestañas vive visible desde el arranque); la
  guía de bienvenida que antes era una pantalla `#welcome-panel` aparte
  ahora es el contenido inicial de `#overview-container` (pestaña
  "Simulaciones"), sustituido por `renderOverview()` tras el primer
  análisis igual que el resto de pestañas ya degradaban con un
  placeholder estático (`report.placeholder`/`tables.placeholder`/
  `optim.placeholder`/`espectro.placeholder`; `charts.placeholder` nuevo
  de esta sesión, único hueco que faltaba). Badge nuevo junto a
  NMAX/PCNT con la carpeta de referencia (`json.reference_folder` del
  manifest, ya existía en la respuesta — solo faltaba mostrarla) y nota
  `chains.reference_note`: las P de CHAINS dependen del espectro de la
  referencia (tapes fort.22/fort.24), no son una propiedad fija del par
  isótopo/IFINAL — verificado con el mismo TE130→I131 dando 95,79/3,12/
  1,09 % con una referencia y 94,550/4,303/1,144 % con otra (v.5, tapes
  reales de `C:\Simulaciones\Analisis de cadenas\chains_TE130\`,
  fuera del repo). Fixture oro positivo pendiente desde F9e ya congelado:
  `tests/fixtures/chains/iso_TE130_real/` (fort.6 real, INPT=2, el eco
  contiene SOLO TE130 con C_i=1.570E20 át/cm³, A_pico(I131)=1.6500E4 —
  ver su `PROCEDENCIA.md` y `test_leer_concentraciones_iniciales_iso_te130_real_positivo`
  en `test_chains.py`).
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
  F12 del BACKLOG (2026-08-08) — desfase de origen temporal al interpolar series de fase `enfriamiento`: antes de esta corrección, toda serie de referencia se trasladaba a un eje absoluto (`t_h = T_irr + t_local` para `enfriamiento`) para compararla contra una curva ACAB COMBINADA (irradiación+enfriamiento concatenados, `_combinedCurveBqcm3`, ya retirada) — cualquier discrepancia de T_irr entre la simulación elegida al importar y la simulación objetivo de las métricas (Fase 6) desplazaba la interpolación. `curveForPhase(sim, iso, fase)` nueva (pura): devuelve `{xs, ys}` de la MISMA fase que la serie — `sim.t_irr`/`datos_irr_Bq` para `irradiacion`, `sim.t_cool`/`datos_cool` para `enfriamiento` — nunca la curva combinada. `confirmRefDataImport` guarda `t_h` SIEMPRE en tiempo desde el inicio de la fase declarada (igual definición que `docs/SPEC_csv_datos_referencia.md`), sin desplazar por T_irr; el desplazamiento a eje absoluto para la superposición en el gráfico combinado (`_renderIsotopoTimeChart`) se calcula solo al pintar, nunca al guardar. `interpolationOriginLabel(fase)` devuelve claves puras (`metodoKey`/`origenKey`, sin texto — mismo criterio que `pureza_time_utils.js`/`estadoBadgeClass`) que `app.js` traduce vía i18n (`refdata.interp_method_*`/`refdata.origin_*`) y declara en la cabecera del CSV exportado y en una nota bajo cada tabla de métricas (`refdata.metrics_csv_origin`/`metrics_origin_note`). Caso oro verificado a mano: nodos (0,25 h → 0,0473979) y (0,50 h → 0,0784282) de una serie de enfriamiento, interpolados en t=0,273678 h dan 0,0503369 (correcto, sin desplazar) frente a 0,0499920 (el error documentado, resultado de restar T_irr antes de interpolar). Tests nuevos en `test_reference_data.js`/`.py`.
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
- `C:\venv\acab-venv\Scripts\python tools\test_api.py` — API REST vía `app.test_client()` (flujo `/api/analyze` → `/api/isotopo_report`, cache keyed por carpeta y errores controlados). Incluye `test_figuras_save()` (`RUNBOOK_figuras_yaml.md`): guardado feliz + discovery posterior como 'auto', 409 sin overwrite, 422 con YAML inválido/sin clave `figuras` lista, round-trip que conserva una sección `semividas` de un YAML de partida. También verifica que `pureza_serie` (F1) y `actividad_especifica_yodo_serie` (F2) viajan en `metricas` con el caso oro de ref_sim (19 puntos, t_cruce=0/t_destacado_h=0, ventana de administración / valor destacado ~4.5e9 MBq/g). Incluye `test_espectro_gamma()` (B1 del BACKLOG): `photon_dat_used=False` sin PHOTON.dat junto al fort.6 de ref_sim, override `photon_dat_path` con el extracto congelado carga la librería en caliente y la deja cacheada para llamadas siguientes, caso oro t=4,5h/línea 364 keV, 404 con ruta inexistente/carpeta no analizada. Incluye `test_chains_report()` (F9 del BACKLOG, Fase 4): 400 sin `root`, 404 sin `chains_manifest.json`, 200 con el análisis sintético de `tests/fixtures/chains_synthetic/` (mismo caso oro que `test_chains.py`: t\*=1h, Σ R_i=1.0, diagrama embebido en cada fila de tabla2), selector de instante manual vía `t_h`.
- `C:\venv\acab-venv\Scripts\python tools\test_reference_data.py` — oráculo Python de `reference_data.js` (fixtures CSV de `tests/fixtures/experimental/` y criterio de aceptación de la Fase 4 contra la ref_sim). F6 del BACKLOG: `seriesForMetrics` (las series `fig6_exp4_experimental_normalizado.csv`/`fig6_exp4_computacional_normalizado.csv`, una de cada tipo, entran AMBAS al filtrar por isótopo) y `resolveTargetSimName` (selección/caída a la primera/`None` sin simulaciones, con nombres de simulación sintéticos).
- `C:\venv\acab-venv\Scripts\python tools\test_metricas.py` — métricas de optimización de producción (Fase 5: saturación, rendimiento, pureza) con curvas sintéticas de solución analítica conocida (no depende de la ref_sim). Incluye `calcular_pureza_serie` (F1): 3 timesteps de ref_sim verificados contra el texto del fort.6 + casos borde sintéticos (cruce interpolado con solución analítica cerrada, ya-alcanzado, nunca-alcanzado, no monotonía). Incluye `calcular_actividad_especifica_yodo_serie` (F2/F2b): caso oro de ref_sim (A_esp(t=0)=4505547272.634922 MBq/g tras F2b, comprobado a mano contra el desglose por isótopo del fort.6) + casos borde sintéticos ("solo I131" — invariante analítico: A_esp constante = actividad específica del isótopo puro λ·N_A/masa, independiente de A(t) — y "sin I127 estable, solo I131+I129") + F2b: `test_actividad_especifica_yodo_i129_congelado_vs_creciente` (escenario sintético tipo irradiación larga que demuestra que I129 usa la tabla de átomos congelada, no A(t)/λ) y `test_actividad_especifica_yodo_techo_fisico` (A_esp(t) nunca supera λ(I131)·N_A/masa(I131)≈4.5967e9 MBq/g, en ref_sim completo + casos sintéticos).
- Node (disponible en esta máquina — comprobar con `Get-Command node` antes de asumir lo contrario): `node tools\test_units.js`, `node tools\test_export.js`, `node tools\test_reference_data.js` — tests directos de las funciones puras de frontend. Sus oráculos numéricos también están espejados en los scripts Python de arriba.
- `node tools\test_optim_utils.js` — combinación pura `sweep_manifest` + informe de `static/js/optim_utils.js` (Fase 5 opcional, pestaña Optimización). Sin oráculo Python: no reproduce ninguna fórmula física (esas ya están cubiertas por `test_metricas.py`/`test_fort_analyzer.py`), solo combina/agrupa datos ya calculados — su verificación vive únicamente en node, como `test_export.js`.
- `node tools\test_pureza_time_utils.js` — funciones puras de `static/js/pureza_time_utils.js` (F1: rango de eje de la gráfica P(t), badge de estado, formato de fracción del pico). Sin oráculo Python: solo da forma a `pureza_serie`, ya calculado y verificado en `test_metricas.py`/`test_api.py` — su verificación vive únicamente en node.
- `C:\venv\acab-venv\Scripts\python tools\test_photon.py` — B1 del BACKLOG (Fases 1 y 2): `leer_photon_dat` contra el extracto congelado `tests/fixtures/ref_sim/PHOTON_extract.dat` (16 nucleidos I131=18 líneas/XE133=6 líneas, TE131M como entrada distinta de TE131, la línea 364,49 keV/81,2 % del I131 verificada contra ENSDF) y `calcular_espectro_gamma` contra ref_sim (cruce de nombres exacto fort.6↔PHOTON.dat, caso oro en enfriamiento tardío t=4,5 h con tasa(364 keV)=A(I131,4,5h)×0,812 comprobado a mano, I130M presente en el inventario pero ausente del extracto → `nucleidos_sin_lineas` sin romper el resto).
- `node tools\test_espectro_gamma_utils.js` — funciones puras de `static/js/espectro_gamma_utils.js` (B1: filtrado por energía/tasa, agrupación por nucleido, construcción de trazas de palotes; B1b: `umbralPorDefecto` con el caso oro real de ref_sim en t=3,750h —máximo=13398,0 fotones/(s·cm³), la línea de 364 keV—, `topNNucleidos` por tasa TOTAL no por línea más fuerte, y `construirTrazasStickTopN` —leyenda acotada + grupo "otros" con color neutro y `customdata` por punto—). Sin oráculo Python: solo filtra/agrupa/da forma a `espectro.lineas`, ya calculado y verificado en `test_photon.py` — su verificación vive únicamente en node.
- `C:\venv\acab-venv\Scripts\python tools\test_chains.py` — F9 del BACKLOG. **Fase 1**: `leer_output_chains` contra el caso oro `tests/fixtures/chains/output_chain_Te130_to_I131.txt` (3 cadenas, P=95.79/3.119/1.090 %, cadena dominante TE130(N,G-g)→TE131(B-)→I131 con XSEC/DELTA verificados a mano); `leer_concentraciones_iniciales` contra `tests/fixtures/ref_sim/fort.6` (8 isótopos de Te + 3 de O, Σ C_i reproduce el XCOMP elemental del Bloque #5 del inp.5 dentro del redondeo de imprenta); `nombre_a_zzaaas` en ida y vuelta contra los 1211 nucleidos de `DECAY.dat` de ref_sim (identidad completa) más los casos directos que cruzan con INITIAL/IFINAL del caso oro de CHAINS. **Fase 4** (`test_calcular_analisis_cadenas_sintetico`): caso sintético mínimo de 2 isótopos `tests/fixtures/chains_synthetic/` (ver su `PROCEDENCIA.md` para la derivación completa a mano) — t\*=1h (pico de la referencia), A_ref(t\*)=100, R_FE56=0.42/R_MN55=0.58, Σ R_i=1.00 (cobertura completa), tabla2 de 3 filas ordenada por Y_z,i (0.580/0.336/0.084), más el selector de instante manual (t_h=0 → A_ref=40). **Fase 5** (`test_construir_diagrama_cadena_caso_real`): reutiliza el fixture real de Fase 1 (sin fixture nuevo) — nodos TE130/TE131/I131 con T½ de `ref_sim/DECAY.dat` (2.493E31/1500/6.932E5 s), aristas con proceso+XSEC/DELTA, cadena 2 vía el isómero TE131M (T½=1.08E5 s, distinto del fundamental), y el caso sin librería T½ (todos los nodos "no conocido", sin romper). **F9d (hotfix, 2026-07-26)**: `test_leer_output_chains_sin_cadenas` contra el fixture real `output_chain_no_pathways_O16.txt` (NCHAIN/NCH/PTOT ausentes, `cadenas=[]`); `test_calcular_analisis_cadenas_output_chain_corrupto` (copia temporal de `chains_synthetic/` con un `output_chain.txt` corrupto y otro ausente — ambos isótopos conservan su fila de tabla1 con `nota_cadenas`, Σ R_i intacta, tabla2 vacía) y `test_calcular_analisis_cadenas_sin_cadenas_no_es_error` (mismo fixture con el `output_chain.txt` real de O16 en `chains_FE56/` — sin nota, tabla2 sin filas de FE56, la cadena de MN55 no se ve afectada). `tools/test_api.py::test_chains_report` añade el caso corrupto vía el endpoint (200, `nota_cadenas` viaja en el JSON). `tools/test_fort_analyzer.py::test_descubrir_simulaciones_excluye_tapes_con_chains_manifest`: con `chains_manifest.json` en la raíz, `tape22`/`tape24` se excluyen del descubrimiento; sin él, comportamiento de siempre. **F9e (hotfix causa raíz, 2026-07-26)**: `test_leer_output_chains_te128_hermano_de_c6` contra el caso oro real `tests/fixtures/chains/output_chain_TE128_to_I131.txt` (13 cadenas encontradas, NCH=12, PTOT=0.02304 — confirma que PTOT NO es siempre 100) — las 12 cadenas detalladas terminan en I131 (antes del fix se truncaban en el primer nucleido de símbolo de una letra con espacio inicial de columna, p. ej. la cadena 2 se cortaba en TE128→TE129→I129); cadena 2 con 4 pasos y cadena 3 con 5 pasos (su cabecera de ruta compacta ocupa 2 líneas de texto, confirma que el header multi-línea no rompe el parseo). `test_calcular_analisis_cadenas_sintetico` actualizado: `cadena_label` ahora incluye el proceso de cada paso (`"FE56->(N,G-g)->FE57->(B-)->CO57"`, antes solo nombres).

Fixtures en `tests/fixtures/ref_sim/` (simulación v.5 "info thesis") y `tests/fixtures/experimental/` (CSV de la Fase 4); valores oro documentados en `tests/fixtures/README.md` y `docs/SPEC_csv_datos_referencia.md`. Cada script devuelve código de salida 0/1. Regla: cualquier cambio en `fort_analyzer.py` o en los módulos JS puros debe dejar toda la suite (Python + node) en verde y añadir los tests oro correspondientes.

## Semántica del dominio (no violar)

- Estructura de entrada: carpeta padre con subcarpetas, cada una con `fort.6` (obligatorio), `inp.5` y `DECAY.dat` (opcionales). Modo simulación única si `fort.6` está en la raíz. F9d del BACKLOG: si la carpeta padre contiene `chains_manifest.json` (raíz de un análisis de cadenas), `descubrir_simulaciones` excluye por nombre las subcarpetas `tape22`/`tape24` (runs IWP=3/IMTX=1 de `chains_analysis.py`, sin sección NUMBER OF ATOMS por diseño — su rol ya está en el manifest) — evita el aviso "No se encontró NUMBER OF ATOMS" al analizar esa carpeta desde la pestaña normal de "Simulaciones".
- La columna `RESTART` del fort.6 marca el inicio del enfriamiento; la columna   `INITIAL` es el estado pre-irradiación y se OMITE en los análisis de enfriamiento.
- Prioridad de semividas: sección `semividas` del YAML > `DECAY.dat` > tabla interna `DEFAULT_SEMIVIDAS` (fallback Te/I/Xe).
- Unidades: los datos internos y el cache SIEMPRE están en Bq/cm³; la conversión a MBq/g / actividad total es un factor por simulación aplicado en el FRONTEND (`static/js/units.js`), no en el backend. Excepción puntual: `actividad_especifica_yodo_serie` (F2) ya viaja en MBq/g DE YODO desde el backend — no es la misma unidad/eje que el selector de arriba (ese es MBq/g del target, p. ej. TeO2), así que el frontend no lo reconvierte (`yNeedsUnitConv('a_esp_yodo') === false`).
- `datos_irr_atomos` (por simulación, junto a `datos_irr_Bq`): átomos/cm³ SIN convertir a Bq, de la sección NUMBER OF ATOMS (solo cubre la irradiación, no el enfriamiento — ver `leer_fort6_irradiacion`). Necesario para F2: convertir a Bq pierde la población de isótopos estables (λ=0 → A=0 siempre, aunque N no lo sea).
- Claves de isótopo tal como aparecen en fort.6, en mayúsculas (`I131`, `XE133M`); `iso_label()` genera la notación Unicode para la UI.
- Datos de referencia externos (Fase 4, `reference_data.js`): el t=0 de una serie con `fase: enfriamiento` es el fin de la irradiación (RESTART), igual que en el resto de la app; se traslada sumando `T_IRR_h` de la simulación de referencia elegida al importar. Las series viven solo en `appState` (`_state.refSeries`), nunca en el cache del servidor ni en disco.

## Gotchas

- `/api/browse-folder` y `/api/browse-file` (B1b del BACKLOG, variante de fichero para la ruta de PHOTON.dat) abren el selector nativo vía tkinter en subprocess: frágiles en instalaciones Python sin tkinter; el campo de ruta manual es el fallback en ambos. El diálogo BLOQUEA hasta que el usuario interactúa — no hay test automático para ninguno de los dos (mismo motivo que no hay test de `/api/browse-folder`: no se puede automatizar un diálogo nativo sin colgar la suite).
- Respuestas JSON pasan por `_sanitize_for_json` (NaN/inf); mantener al añadir endpoints.
