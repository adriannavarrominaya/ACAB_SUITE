<!-- Guardar como: ACAB_SUITE/CLAUDE.md  (carpeta padre que contiene los tres repos y acab_suite/) -->

# Suite ACAB — TFG optimización de producción de ¹³¹I

Tres aplicaciones web Flask locales (monousuario, 127.0.0.1) que forman el ciclo de trabajo con el código de activación ACAB 2008 (UPM): configurar entradas → ejecutar → analizar salidas. Caso de estudio del TFG: producción de ¹³¹I por irradiación de TeO₂ (¹³⁰Te(n,γ)¹³¹Te → β⁻ → ¹³¹I).

## Mapa de la suite

| Carpeta | Qué es | Puerto |
|---|---|---|
| `ACAB_inp_file_configurator/` | Editor/generador de ficheros de entrada `inp.5` (14 bloques) y ficheros CHAINS | 5000 |
| `ACAB_fort_file_analyzer/` | Análisis y gráficas de ficheros de salida `fort.6` (multi-simulación) | 5001 |
| `COLLAPS_inp_file_configurator/` | Editor del fichero `COLL.inp` de COLLAPS (colapsado de espectros) | 5002 |
| `acab_suite/` | Transversal: runbooks de mejoras, launcher y `suite_config.json` | — |

Flujo de trabajo del usuario: COLLAPS (espectro) → inp.5 (entrada ACAB) → ejecutar ACAB → fort.6 → analyzer.

## Glosario: dos capas deliberadas (T1–T4 del BACKLOG, 2026-08-26)

- **Lo que ve el usuario** se llama **«cálculo paramétrico»** (en inglés,
  «parametric study»), con los compuestos por tipo «cálculo paramétrico de
  flujo / de masa / de historial temporal / de espectro». Es el término de la
  UI, los manuales y las cabeceras de los ficheros generados. Y **«librería»**,
  nunca «biblioteca», para DECAY.dat/PHOTON.dat/XS y la pestaña de COLLAPS.
- **La capa de código sigue diciendo `sweep`/«barrido»**: `sweep_writer.py`,
  `sweep.js`, `sweep_manifest_view.py`, `SweepError`, `mergeSweepRows`, los
  comentarios y docstrings, y los `RUNBOOK_barrido_*.md`. No es terminología
  olvidada: se dejó así a propósito (churn alto, valor nulo).
- **Nada de lo que viaja a disco se renombró, y no debe renombrarse**:
  `sweep_manifest.json` / `sweep_manifest.csv`, la clave `sweep_type` y sus
  valores `flux`/`mass`/`time`/`spectrum`, y las claves i18n (`sweep.*`,
  `optim.type_*`). Es lo que hace que los análisis del TFG ya generados sigan
  abriéndose sin capa de compatibilidad. Anclado con tests oro contra un
  manifiesto real anterior al cambio en los dos repos que lo leen
  (`tests/fixtures/sweep_pre_renombrado/` de inp-conf y del analyzer).

## Reglas para trabajar en este árbol

- **Un único repositorio git (monorepo) en la raíz de este árbol** (no hay repos independientes por subcarpeta). Los commits se acotan a un componente siempre que sea posible, con prefijo en el mensaje según el componente tocado: `inp-conf:`, `analyzer:`, `collaps:`, `suite:`. Un cambio genuinamente transversal (p. ej. sincronizar un fragmento duplicado) puede ir en un commit único con prefijo `suite:` que lo explique.
- **Antes de tocar código de un componente:** leer su `CLAUDE.md` y dejar en verde su suite de tests (los comandos están en cada CLAUDE.md). Ningún commit con la suite en rojo.
- Los planes de trabajo detallados (fases, criterios de aceptación) están en `acab_suite/RUNBOOK_*.md`. Si una tarea corresponde a un runbook, seguir sus fases  en orden y no mezclar fases en un mismo commit.
- **Fragmentos duplicados a mantener sincronizados entre repos** (marcados con comentario de cabecera en el propio fichero): el banner de navegación de la suite y su JS; `runner.py` (en ambos configuradores); `coll_writer.py` del INP configurator, que es copia del parser/writer de COLL.inp del repo COLLAPS (`collaps_parser.py` / `_write_coll_inp`); y `chains_inventory.py` del INP configurator (F9 del BACKLOG), que es copia de `leer_concentraciones_iniciales`/`nombre_a_zzaaas` de `fort_analyzer.py` del analyzer. Si se edita una copia, replicar en las demás.
- **Forma canónica de arrancar la suite:** `acab_suite/suite_launcher.py` (lanza las tres apps, health-check y abre el navegador). Ver `acab_suite/README.md`.
- Idioma de la UI: español (con i18n es/en donde el repo lo soporte). Código y docstrings: el estilo ya existente de cada repo (mezcla es/en) — no "normalizar" idiomas en masa.
- Las tres apps ligan a 127.0.0.1 y son monousuario; no introducir dependencias de despliegue multiusuario ni autenticación.
- **Ejecución de los tests:** `acab_suite/tools/run_all_tests.ps1` lanza todos los tests de las tres apps, generando un informe final con el resultado de la ejecución.
