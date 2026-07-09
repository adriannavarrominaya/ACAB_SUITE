---
name: phase2-units-done
description: Runbook fort_analyzer progress — Fases 0-5 done (incl. retrofit de unidades en la Sección 4 de optimización)
metadata:
  type: project
---

Progreso del `RUNBOOK_fort_analyzer_mejoras.md` (repo ACAB_fort_file_analyzer):

- **Fase 0** (fixtures + tests oro): hecha antes de esta serie de sesiones.
- **Fase 1** (i18n es/en, `Z_BY_ELEM` completo, cache keyed por carpeta): completada.
- **Fase 2** (normalización de unidades): completada 2026-07-08.
  - Parser `leer_fort6_concentraciones` (sección `CONCENTRATIONS(GRAM)`) → densidad.
  - `analizar_carpeta` adjunta `densidad_g_cm3`; `/api/analyze` la incluye.
  - Selector de unidades (Bq/cm³ | MBq/g | MBq | mCi) en `static/js/units.js`
    (función pura `ACABUnits.convertUnits`). **La conversión es un factor por
    simulación aplicado en el FRONTEND; el cache y los datos internos siguen en
    Bq/cm³.** i18n de unidades con placeholder `{unit}`.
- **Fase 3** (exportación CSV): completada 2026-07-08.
  - `static/js/export_utils.js` (`ACABExport.toCSV/slug/preset/download`, UMD puro).
  - Botones "Exportar CSV" en gráficas, informe y las 2 tablas comparativas;
    valores en la unidad activa, cabecera `#` de metadatos, nombres descriptivos.
  - Formato CSV (`;`/`,` es-ES por defecto | `,`/`.` intl) en el card Unidades,
    persistido en localStorage.
- **Fase 4** (datos de referencia externos sobre las curvas): completada 2026-07-08.
  - Especificación del CSV en `docs/SPEC_csv_datos_referencia.md` (metadatos
    `#`, columnas t;A[;A_err], delimitador/decimal autodetectados).
  - `static/js/reference_data.js` (UMD puro, depende de `units.js`): parser del
    CSV, heurística de mapeo de columnas (`guessColumnRoles` — la columna casi
    monótona es t), `linearInterpClamped` (paridad con `numpy.interp`,
    recortado a extremos) y `computeDeviationMetrics`.
  - Diálogo de importación (`modal-refdata` en `index.html` + `renderRefDataDialog`/
    `confirmRefDataImport` en `app.js`): previsualización de 5 filas con
    selector de columna por columna, campos fase/unidades/isótopo/tipo/etiqueta/
    fuente/simulación-de-referencia autorrellenados desde los metadatos y
    siempre editables. Varias series simultáneas, tipo `experimental` (huecos,
    con métricas) o `computacional_referencia` (rellenos, solo dibujo).
  - Overlay scatter en el gráfico de la Sección 3 del informe (Bq/cm³ interno →
    unidad activa vía la densidad/volumen de LA SIMULACIÓN DE REFERENCIA
    elegida al importar, no la primera simulación del análisis).
  - Métricas de desviación (`renderRefDataMetrics`, solo series `experimental`):
    interpolación de la curva ACAB combinada (irr+cool) en cada t experimental,
    `dev% = (A_ACAB − A_exp)/A_exp·100`; se computa en Bq/cm³ crudo (invariante
    de unidad) y solo se convierte para mostrar. Sesgo medio + máximo +
    exportación CSV.
  - Series en `_state.refSeries` (appState, no disco), con botón de retirada (✕).
  - `compare_simulaciones.py` queda legacy (ya lo estaba desde la Fase 2).
  - **Criterio de aceptación verificado**: interpolando la curva I131 real de
    `tests/fixtures/ref_sim/fort.6` (misma simulación v.5 "info thesis" que
    usaba el script legacy, confirmado numéricamente) en los 11 tiempos
    experimentales embebidos en `compare_simulaciones.py`, se obtiene sesgo
    medio 8.23 % / máx. 12.02 %, equivalente al 7.49 % / 11.48 % del script
    legacy (mismo orden de magnitud; no idéntico porque la digitalización
    legacy y la malla real del fort.6 no coinciden punto a punto).
  - Tests: `tools/test_reference_data.js` (node) + `tools/test_reference_data.py`
    (oráculo Python, incluye el criterio de aceptación anterior). Verificado
    además en vivo con Playwright headless (Chrome del sistema vía
    `playwright-core`, sin chromium-cli): diálogo, prefill de metadatos,
    overlay en gráfica, tabla de desviación y exportación CSV funcionan
    end-to-end sin errores de consola nuevos.
  - De paso, arreglado un bug preexistente de Fase 2 en `units.js`:
    `convertUnits(null, 'bqcm3')` devolvía `0` en vez de `null`
    (`Number(null) === 0` en JS). Revelado por `tools/test_units.js` al
    ejecutarlo con node (ver [[no-node-runtime]] — ya no aplica, node SÍ está
    instalado en esta máquina).
- **Fase 5** (métricas de optimización de producción: saturación, rendimiento,
  pureza) — backend (`calcular_saturacion/rendimiento/pureza` en
  `fort_analyzer.py`, bajo `informe.metricas` por simulación) y el frontend
  (Sección 4 "Métricas de Optimización de Producción" de `_renderMetricasOptimizacion`
  en `app.js`, dentro de la pestaña "Informe Isótopo") ya estaban implementados
  y mayormente unit-aware (usan `fmtA`/`conv`/`unitLabel()`, per-sim
  `sim.densidad_g_cm3`) antes de esta sesión — el runbook no se había
  actualizado para reflejarlo. **Retrofit de unidades 2026-07-08** (el trabajo
  real pendiente, encontrado al auditar la Sección 4 contra el gap real):
  - Bug real encontrado y arreglado: `static/i18n/en.json`
    `report.ax_activity` tenía `"Activity {label} [Bq/cm³]"` hardcodeado (sin
    `{unit}`) — el eje Y de la gráfica de la Sección 3/4 en inglés siempre
    mostraba "[Bq/cm³]" pese a tener MBq/g activo. La versión es.json ya
    usaba `{unit}` correctamente.
  - Gap real encontrado y arreglado: el gating de la opción MBq/g
    (`syncUnitControls` en `app.js`) usaba "¿ALGUNA sim tiene densidad?"
    (`anyDensity()`) para habilitarla, dejando filas/curvas en '—' o
    desaparecidas silenciosamente para las sims sin `CONCENTRATIONS(GRAM)`.
    Cambiado a "¿TODAS las sims tienen densidad?" (`allDensity()` /
    `simsMissingDensity()`): si falta en alguna, la opción se deshabilita
    (`<option disabled>`) y el tooltip/nota nombra la(s) sim(s) que faltan,
    reutilizando la clave i18n `units.no_density_series` (`{sim}`) que ya
    existía en es.json/en.json pero no se usaba desde ningún sitio en
    `app.js`. Con TODAS las sims sin densidad se mantiene el mensaje genérico
    `units.mbqg_disabled`. Solo afecta a MBq/g (por-sim); MBq/mCi totales usan
    un volumen global y no se tocan.
  - Verificado en vivo con Playwright (Chrome del sistema vía `playwright`
    Python — instalado en `C:\venv\acab-venv` en esta sesión, `playwright
    install chromium`): carpeta sintética de 2 sims (una con densidad, otra
    sin ella) → opción MBq/g deshabilitada con tooltip nombrando la sim sin
    densidad; carpeta de 1 sim con densidad → MBq/g habilitada, cambia unidad
    y la Sección 4 completa (saturación/rendimiento/pureza) y el gráfico se
    re-renderizan con los valores y cabeceras en MBq/g; en inglés el eje Y ya
    muestra `[MBq/g]` en vez de `[Bq/cm³]`. Sin errores de consola.
  - Tests oro sin cambios (no había fixture de sweep con densidad mixta en el
    repo; la verificación fue manual/Playwright, no se añadió fixture nueva
    porque no hay carpeta de barrido real con densidades mixtas a mano).

Verificación de cada fase: `tools/test_fort_analyzer.py` + `tools/test_api.py`
(Python, siempre corren) + `tools/test_reference_data.py` (Python, Fase 4) +
`tools/test_metricas.py` (Python, Fase 5). Última corrida en verde: 44 fort +
21 api + 38 metricas + 37 reference_data (Python); 14 units + 12 export + 36
reference_data (node) — node SÍ está disponible en esta máquina, ver
[[no-node-runtime]].

**Nota 2026-07-08**: durante esta sesión, `tests/fixtures/experimental/`
cambió de contenido en vivo (aparecieron `fig2_exp1_*`/`fig5_exp2_*` y
`fig6_experimental_normalizado.csv`/`fig6_computacional_normalizado.csv` se
renombraron a `fig6_exp4_*`) mientras se trabajaba — probablemente otra
sesión/el usuario tocando fixtures de la Fase 4 en paralelo (no hay repo git
en esta carpeta para confirmarlo). Esto rompe `tools/test_reference_data.py`
(espera los nombres viejos `fig6_experimental_normalizado.csv` /
`fig6_computacional_normalizado.csv`) de forma no relacionada con el retrofit
de unidades.

**Resuelto 2026-07-09**: el usuario confirmó que el rename fue intencionado
(homogeneizar nombres de fixtures con prefijo de experimento). Se actualizaron
las dos referencias en `tools/test_reference_data.py`
(`test_fixture_experimental`/`test_fixture_computacional` + el check de
`main()`) y las dos menciones en `docs/SPEC_csv_datos_referencia.md` a
`fig6_exp4_experimental_normalizado.csv` / `fig6_exp4_computacional_normalizado.csv`.
Suite en verde (37 pasados). Ver [[sweep-tab-done]] para el mismo hallazgo
anotado en paralelo.
