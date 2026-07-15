# BACKLOG — Suite ACAB (pendientes no planificados)

Convención: este documento recoge correcciones, mejoras e ideas AÚN NO planificadas.
Cuando un ítem se aborda, se convierte en sesión/runbook y su línea pasa a ✅ con
fecha (o se mueve al tablón de README.md si genera verificaciones). El estado de
los runbooks y las verificaciones de control viven en README.md (tablón), no aquí.

Prioridad: A (hacer pronto, valor alto o corrige fricción real) · B (cuando toque) ·
C (idea registrada, decidir más adelante). Esfuerzo: S (<1 h) · M (una sesión) ·
L (varias sesiones).

---

## Correcciones y limpieza (de la revisión 2026-07-13)

| # | Comp. | Ítem | Prio/Esf |
|---|---|---|---|
| C1 | docs | Retoques CLAUDE.md: notas recíprocas en COLLAPS (parser y writer → coll_writer.py); padre a monorepo con prefijos de commit (`inp-conf:`/`analyzer:`/`collaps:`/`suite:`) y COL.inp→COLL.inp; restaurar en INP configurator las frases de `_write_inp5`/"nunca duplicar formato" y de docs/ como fuente de verdad; en analyzer, mover el párrafo de la pestaña "Actividad por Isótopo" del bullet de optim_utils.js al de app.js. **✅ (2026-07-14):** ya aplicado en el commit `7c23288` (el mismo que creó este backlog); verificados los 4 puntos contra el estado actual de los ficheros, sin cambios pendientes. | A / S |
| C2 | git | Monorepo: `.gitignore` de raíz correcto (venvs, `acab_suite/logs/`, salidas de simulación), `git rm --cached` de lo trackeado indebidamente, commit adoptando la convención de prefijos. **✅ (2026-07-14):** commit `suite:`. Fixtures de tests oro verificados como no excluidos; las salidas dentro de `examples/Simulation/Reference simulation/Simulation v.0/` se dejan trackeadas a propósito (decisión pendiente en C4). | A / S |
| C3 | analyzer | i18n: clave `optim.type_spectrum` sin traducir + errata "Barrido de expectro" → "espectro". **✅ (2026-07-14):** commit `analyzer:`, añadida la clave en es.json/en.json. La errata no se encontró en ningún sitio del repo (grep + historial completo). | A / S |
| C4 | inp-conf | Excluir/limpiar salidas viejas al copiar la carpeta base del barrido (FLUX.inf, XSECTION.dat, fort.6, run.log…): un fichero muerto con datos de OTRO espectro en la carpeta de una sim es una trampa de trazabilidad (visto en el control MURR). Alternativa mínima: documentar que las salidas de `collaps/` se regeneran. **✅ (2026-07-14):** commit `inp-conf:`. Exclusión asimétrica según `sweep_type`: espectral excluye salidas de ACAB Y de COLLAPS (se regeneran por sim); flujo/masa/temporal excluye solo las de ACAB (XSECTION.dat/FLUX.inf se conservan a propósito, espectro compartido por diseño). Lo excluido queda anotado en `sweep_manifest.json` (`excluded_base_files`). Tests oro nuevos en `tools/test_sweep_endpoint.py` (`BaseFolderExclusionTests`). | A / S-M |
| C5 | inp-conf | Baseline con 2 tests en rojo: rutas rotas tras la reorganización de `examples/` en subcarpetas (detectado en la sesión C4) + CLAUDE.md con rutas/comandos desactualizados por la misma reorg. Actualizar tests y CLAUDE.md al layout actual; criterio de cierre: suite completa en verde SIN fallos "conocidos". **✅ (2026-07-14):** commit `inp-conf:`. Los 2 fallos eran los comandos documentados en CLAUDE.md (`regression_roundtrip.py`/`test_parser_robustness.py` con rutas `examples/exp*.inp.5` de antes de la reorg); ningún test bajo `tools/` tenía rutas hardcodeadas. Corregido a `examples/Inp5/exp*.inp.5`; suite completa (Python + node) verificada en verde. | A / S |

## Mejoras de usabilidad (notas de pruebas 2026-07-13)

| # | Comp. | Ítem | Valoración | Prio/Esf |
|---|---|---|---|---|
| U1 | inp-conf | "Abrir en Fort Analyzer" tras el barrido: pasar de pestaña nueva a MISMA pestaña (coherencia con el banner de la suite; es el único `_blank` del sistema). Ctrl+clic sigue dando pestaña nueva de forma nativa. Coste asumido: al volver atrás se pierde el estado en memoria de la pestaña Barrido (el trabajo ya está hecho y la cola vive en servidor). **✅ (2026-07-15):** commit `inp-conf:`. Retirado `target="_blank" rel="noopener"` de `btn-sweep-run-open-analyzer` (único `_blank` del sistema); el resto del comportamiento (Ctrl+clic → pestaña nueva) es nativo del navegador, no requería cambios. Verificado en navegador real (Playwright): clic normal navega en la misma pestaña sin abrir popup, Ctrl+clic sigue abriendo pestaña nueva. | Aprobada | A / S |
| U2 | collaps + inp-conf | Guardar en carpeta en vez de descargar: botón "Guardar en carpeta…" (diálogo browse-folder patrón analyzer, con fallback de ruta manual) que escribe COLL.inp/inp.5 en la carpeta elegida; recordar la última. "Descargar" se mantiene como opción secundaria (patrón dual del editor de figuras YAML). Aplicar SIMÉTRICAMENTE en ambos configuradores. **✅ (2026-07-15):** commits `collaps:` e `inp-conf:`. Botón primario "Guardar en carpeta…" en la barra de navegación de ambas apps (`POST /api/save-to-folder`, escribe COLL.inp/inp.5); diálogo de carpeta vía `/api/browse-folder` (tkinter en subprocess, ya existente en inp-conf/analyzer, añadido en collaps) con fallback de ruta manual. Confirmación explícita antes de sobrescribir (409 + reintento con `overwrite:true`, patrón de figuras.yaml del analyzer). Última carpeta recordada en `localStorage` (por app) y ofrecida como valor inicial en el siguiente guardado. "Descargar" (antes "Guardar como…") sin cambios de lógica, relegada a opción secundaria — en inp-conf conserva su flujo `showSaveFilePicker` en Chromium. Tests nuevos `tools/test_save_to_folder.py` en ambos repos (construcción de ruta, 400/422, 409+overwrite); suites completas (Python + node en inp-conf) en verde antes y después. Verificado en navegador real (Playwright) en ambas apps: simetría confirmada — mismos textos base y misma jerarquía visual de botones. | Aprobada | A / M |
| U3 | collaps | Al ejecutar COLLAPS, prefijar el workdir con la carpeta del último guardado de COLL.inp (editable, nunca oculto); sin guardado previo, diálogo de carpeta. Depende de U2. Aplicar el mismo criterio en el INP configurator con el inp.5. **✅ (2026-07-15):** commits `collaps:` e `inp-conf:` (junto con U2). El workdir de ejecución se precarga con la carpeta del último "Guardar en carpeta…" (prioridad sobre el `default_workdir` de la última ejecución); sin guardado previo, cae al comportamiento de siempre. Campo siempre visible y editable; se le añadió su propio botón de diálogo de carpeta (mismo patrón que U2). Verificado en navegador real (Playwright) en ambas apps. | Aprobada | A / S (tras U2) |
| U4 | analyzer | Pestaña Optimización, barridos espectrales: leyenda ilegible (volcado de parámetros por serie). Mostrar una sola serie con el NOMBRE del espectro como etiqueta/hover. | Aprobada | B / S |
| U5 | inp-conf | Barrido de flujo, modo "Flujo total objetivo": placeholder y etiqueta heredados del modo XNORM inducen a error (introducir factores como si
fueran flujos → XNORM ~1e-14 sin aviso). (a) Placeholder dinámico por modo, derivado del φ_base real del fichero (×0.5/×1/×2); (b) etiqueta con unidad "Valores de flujo total [n/cm²·s]"; (c) guardarraíl en previsualización: aviso si el XNORM resultante sale de [1e-3, 1e3] (y el simétrico en modo factores).
**✅ (2026-07-15):** commit `inp-conf:`. Etiqueta y placeholder del campo de valores ahora dependen del modo (`fluxValuesPlaceholder` en `sweep_utils.js`); en modo flujo, sin fichero base cargado o φ_base ≤ 0 se usa un texto genérico con la unidad, nunca el placeholder de factores. Guardarraíl (`fluxSweepGuardrail`) en la previsualización, no bloqueante, con el mismo umbral [1e-3, 1e3] en ambas direcciones. i18n es/en completa. Tests nuevos en `tools/test_sweep_utils.js`; suite completa (Python + node) en verde antes y después. Verificado en navegador real (Playwright) con el fixture `exp1.inp.5` (φ_base=6.5000e+13): cambio de modo actualiza placeholder/etiqueta, aviso se dispara en ambas direcciones con el mensaje correcto y no se dispara con valores limpios.
| Aprobada | A / S |
| U6 | inp-conf | Cargar un barrido ya generado para CONSULTARLO (solo lectura): hoy se puede cargar para ejecutar pero no para ver qué lo compone. Vista resumen desde el manifest: tipo (los 4), parámetro barrido y valor por simulación, base, ficheros excluidos (C4), y estado de ejecución por sim si hay batch_results.json. Unificar con el flujo de carga existente: cargar muestra el contenido, y ejecutar pasa a ser una acción sobre lo cargado. Editar queda explícitamente fuera (editar = regenerar). | A / M |

## Mejoras científicas

| # | Comp. | Ítem | Valoración | Prio/Esf |
|---|---|---|---|---|
| F1 | analyzer | **Pureza como serie temporal P(t) durante el enfriamiento**, desde el fin de irradiación: gráfica con línea de umbral 99.9 % (requisito validado con el tutor) y marcador del instante de cruce ("tiempo mínimo de enfriamiento para calidad farmacéutica"). Emparejar con A(t) del ¹³¹I → ventana de administración (pureza alcanzada vs actividad restante). Las impurezas de yodo decaen más rápido que el ¹³¹I ⇒ P(t) crece tras el pico. Datos por timestep ya parseados: extender `calcular_pureza` de escalar a serie. Absorbe el badge de umbral pendiente. **✅ (2026-07-14):** ejecutado fase a fase (`RUNBOOK_F1_pureza_temporal.md`), 4 commits `analyzer:`. `calcular_pureza` ya estaba en base actividad (verificado en Fase 1, no hizo falta parar). `calcular_pureza_serie` nueva (P(t) en todo el enfriamiento, t_cruce con interpolación log-lineal + bisección, casos borde ya-alcanzado/nunca-alcanzado, aviso de no monotonía, ventana de administración), expuesta en `/api/isotopo_report` sin tocar el endpoint (ya serializaba `informe` completo). Gráfica de dos paneles apilados (P(t) arriba con umbral y marcador de cruce, A(¹³¹I,t) abajo) en `_renderPurezaSerieChart`, utilidades puras en `pureza_time_utils.js` nuevo con tests node. Verificado a mano: 3 timesteps de ref_sim contra el fort.6 + casos borde sintéticos con solución analítica cerrada; visual en navegador real (Playwright) con el caso oro, un barrido de 2 sims y los dos casos borde inyectados. Badge escalar "P = {v} %" retirado de la UI (absorbido por la gráfica). Suite completa (Python + node) en verde. | Aprobada — la de mayor valor para la memoria | A / M |
| F2 | analyzer | Actividad específica del yodo: A(¹³¹I)/masa total de yodo, con I-127 estable e I-129 de vida larga como diluyentes (concepto del tutor, 2026-07-09; sección de átomos ya en fort.6). | Registrada | B / M |
| F3 | inp-conf | Modo geométrico opcional (rampa ×2) en el generador de mallas temporales, junto al lineal actual — recomendación del manual para transitorios rápidos al inicio de irradiaciones largas. Comentar con el tutor si algún caso lo pide. | Registrada | C / M |
| F4 | inp-conf | Asistente manual FLUX.inf → Bloque #3 (leer REAL TOTAL FLUX de un FLUX.inf y volcarlo al inp.5): útil para espectros analíticos con magnitud física, FUERA de los barridos (en barridos el Bloque #3 es fijo por diseño, decisión D1). | Registrada | C / S |
| F5 | analyzer | Badge "¿compensa seguir irradiando?" es artefacto en pulsos cortos con crecimiento por precursor (bases distintas pico-enfriamiento vs curva de irradiación). Documentado como limitación; decidir arreglo (ambos términos sobre la curva de irradiación) cuando se analice un caso de irradiación larga. | Registrada | C / S-M |

## Deuda técnica

| # | Comp. | Ítem | Prio/Esf |
|---|---|---|---|
| D1 | inp-conf | Ejecutables falsos de los tests de P4 son `.bat` (solo Windows); migrar al patrón de la suite: falsos Python multiplataforma (R1). | B / S |

## Bloqueados por externos

| # | Comp. | Ítem | Estado |
|---|---|---|---|
| B1 | analyzer | Fases 6 y 7b (espectro gamma genérico desde PHOTON.dat + cierre de docs). A la espera del fichero. **Fecha de decisión:** si no aparece, activar plan B (mini-librería ENSDF hardcodeada para los isótopos del problema: I-130…135, Te131m, Xe133 — una sesión, verificable contra NNDC). | ⏸ |

## Ideas registradas sin compromiso (del análisis inicial, no ejecutadas)

- collaps: gráfica del espectro FT en el propio configurador (la superposición ya
  existe en la pestaña Barrido del INP configurator; valorar si sigue aportando).
- collaps: presets de estructuras de grupos estándar para la tarjeta 7.
- Barridos: producto cartesiano (v2 declarada en el runbook v2) y combinación
  espectro × flujo (XNORM quedó libre a propósito, decisión D1 del espectral).
- Suite: fusión de las apps en una sola Flask con blueprints (post-TFG).
