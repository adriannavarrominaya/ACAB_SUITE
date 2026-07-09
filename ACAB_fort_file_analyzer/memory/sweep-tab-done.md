---
name: sweep-tab-done
description: "Pestaña Optimización" (Fase 5 opcional, RUNBOOK_barrido_parametrico_v2.md) implementada 2026-07-08
metadata:
  type: project
---

La **pestaña "Optimización"** del analyzer (Fase 5 opcional del
`acab_suite/RUNBOOK_barrido_parametrico_v2.md`, coordinada con
[[phase2-units-done]] — debía hacerse DESPUÉS de las Fases 2 y 5 de
`RUNBOOK_fort_analyzer_mejoras.md`) no existía en el repo hasta esta sesión
(2026-07-08): no había tab en `templates/index.html`, ni manejo de
`sweep_manifest.json`, ni gráfica A_pico vs parámetro. Se construyó de cero,
junto con la ampliación pedida por el usuario (selector de variable Y:
A_pico/t_pico/pureza/rendimiento) en el mismo desarrollo, tras confirmar el
alcance con el usuario (memoria de esa decisión: la pestaña base no existía
y el usuario eligió construir base + selector juntos, no por fases separadas).

**Backend**: `fort_analyzer.leer_sweep_manifest(folder)` lee
`sweep_manifest.json` de la raíz analizada (formato real confirmado leyendo
`ACAB_inp_file_configurator/sweep_writer.py`: `{sweep_type, description,
fixed_params, n, simulations: [{folder, params}]}`, sweep_type ∈
{flux, mass, time}); `None` si no existe, sin romper el análisis normal.
`/api/analyze` lo expone tal cual como `sweep_manifest` (no se cachea aparte;
se relee en cada análisis).

**Frontend**: `static/js/optim_utils.js` (puro, UMD, sin DOM) combina el
manifest con `informe.simulations`/`informe.metricas` — YA calculados por
`/api/isotopo_report`, ninguna fórmula física se repite. `renderOptimizacion`
en `app.js` (Tab 5, lazy-render igual que Tabs 3/4) construye tabla (folder ×
params × A_pico × t_pico × pureza × rendimiento) + gráfica Plotly (selector de
parámetro X + selector de variable Y, series de color = resto de dimensiones
del barrido vía `groupByOtherParams`) + export CSV.

**Verificado en vivo con Playwright** (carpeta sintética de 3 subcarpetas
copiando `tests/fixtures/ref_sim/` con `sweep_manifest.json` de barrido de
flujo XNORM 0.5/1.0/1.5): tabla con 3 filas, subtítulo con descripción +
badge de tipo de barrido, gráfica con 1 traza, los 4 valores del selector Y
cambian el eje/los datos correctamente, exportación CSV con las columnas
esperadas y nombre de fichero correcto, sin errores de consola. La agrupación
por "demás dimensiones" (color) solo se probó con datos sintéticos en
`tools/test_optim_utils.js` (barrido temporal con 2 claves numéricas) — no
hay fixture real de barrido multi-parámetro en el repo.

Tests: `tools/test_fort_analyzer.py::test_sweep_manifest`,
`tools/test_api.py::test_sweep_manifest` (Python), `tools/test_optim_utils.js`
(node, sin oráculo Python — no repite fórmulas físicas, solo combina/agrupa
datos ya testeados en `test_metricas.py`).

**Nota pendiente no relacionada — resuelta 2026-07-09**: `tools/test_reference_data.py`
estuvo en rojo por el rename de fixtures de `tests/fixtures/experimental/`
(`fig6_experimental_normalizado.csv` → `fig6_exp4_*`) ya detectado en
[[phase2-units-done]] el mismo día; no se tocó en esa sesión por ser un
problema preexistente y no relacionado con el barrido. El usuario confirmó
que el rename fue intencionado (homogeneizar nombres) y se actualizaron las
referencias en `tools/test_reference_data.py` y `docs/SPEC_csv_datos_referencia.md`
— detalle en [[phase2-units-done]]. Suite completa en verde de nuevo.
