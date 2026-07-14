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

## Mejoras de usabilidad (notas de pruebas 2026-07-13)

| # | Comp. | Ítem | Valoración | Prio/Esf |
|---|---|---|---|---|
| U1 | inp-conf | "Abrir en Fort Analyzer" tras el barrido: pasar de pestaña nueva a MISMA pestaña (coherencia con el banner de la suite; es el único `_blank` del sistema). Ctrl+clic sigue dando pestaña nueva de forma nativa. Coste asumido: al volver atrás se pierde el estado en memoria de la pestaña Barrido (el trabajo ya está hecho y la cola vive en servidor). | Aprobada | A / S |
| U2 | collaps + inp-conf | Guardar en carpeta en vez de descargar: botón "Guardar en carpeta…" (diálogo browse-folder patrón analyzer, con fallback de ruta manual) que escribe COLL.inp/inp.5 en la carpeta elegida; recordar la última. "Descargar" se mantiene como opción secundaria (patrón dual del editor de figuras YAML). Aplicar SIMÉTRICAMENTE en ambos configuradores. | Aprobada | A / M |
| U3 | collaps | Al ejecutar COLLAPS, prefijar el workdir con la carpeta del último guardado de COLL.inp (editable, nunca oculto); sin guardado previo, diálogo de carpeta. Depende de U2. Aplicar el mismo criterio en el INP configurator con el inp.5. | Aprobada | A / S (tras U2) |
| U4 | analyzer | Pestaña Optimización, barridos espectrales: leyenda ilegible (volcado de parámetros por serie). Mostrar una sola serie con el NOMBRE del espectro como etiqueta/hover. | Aprobada | B / S |
| U5 | inp-conf | Barrido de flujo, modo "Flujo total objetivo": placeholder y etiqueta heredados del modo XNORM inducen a error (introducir factores como si
fueran flujos → XNORM ~1e-14 sin aviso). (a) Placeholder dinámico por modo, derivado del φ_base real del fichero (×0.5/×1/×2); (b) etiqueta con unidad "Valores de flujo total [n/cm²·s]"; (c) guardarraíl en previsualización: aviso si el XNORM resultante sale de [1e-3, 1e3] (y el simétrico en modo factores).
| Aprobada | A / S |

## Mejoras científicas

| # | Comp. | Ítem | Valoración | Prio/Esf |
|---|---|---|---|---|
| F1 | analyzer | **Pureza como serie temporal P(t) durante el enfriamiento**, desde el fin de irradiación: gráfica con línea de umbral 99.9 % (requisito validado con el tutor) y marcador del instante de cruce ("tiempo mínimo de enfriamiento para calidad farmacéutica"). Emparejar con A(t) del ¹³¹I → ventana de administración (pureza alcanzada vs actividad restante). Las impurezas de yodo decaen más rápido que el ¹³¹I ⇒ P(t) crece tras el pico. Datos por timestep ya parseados: extender `calcular_pureza` de escalar a serie. Absorbe el badge de umbral pendiente. | Aprobada — la de mayor valor para la memoria | A / M |
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
