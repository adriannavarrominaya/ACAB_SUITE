# Especificación — CSV de datos de referencia (Fase 4 del runbook del analyzer)

Formato de los ficheros CSV que el analyzer importa para superponer sobre las curvas
de simulación (datos experimentales o series computacionales de referencia externas).
Este documento es la fuente de verdad para la implementación de la Fase 4: guardarlo
en `docs/` del repo ACAB_fort_file_analyzer.

## Estructura del fichero

```csv
# tipo: experimental
# descripcion: Fig. 6 - Actividad I-131 medida, cuarto experimento (MURR, TeO2)
# fase: enfriamiento
# isotopo: I131
# unidad_t: h
# unidad_A: MBq/g
# fuente: digitalizado del paper de referencia
t;A;A_err
14,5975;7728,904;120,5
16,2340;7866,102;118,2
```

## Columnas

| Columna | Obligatoria | Significado |
|---|---|---|
| 1 · t | Sí | Tiempo desde el INICIO de la fase declarada. Si `fase: enfriamiento`, t=0 es el fin de la irradiación (columna RESTART del fort.6). Si `fase: irradiacion`, t=0 es el inicio de la irradiación. |
| 2 · A | Sí | Actividad en la unidad declarada en `unidad_A`. |
| 3 · A_err | No | Incertidumbre absoluta de A (misma unidad). Se representa como barra de error. |

## Metadatos (líneas `# clave: valor`, todas opcionales)

- `tipo`: `experimental` (puntos huecos) | `computacional_referencia` (puntos
  rellenos). Distinción puramente visual en la gráfica: AMBOS tipos entran en
  las métricas de desviación, cada uno con su propia tabla (Fase 6 del
  BACKLOG). Defecto: experimental.
- `descripcion`: etiqueta de la serie en la leyenda. Defecto: nombre del fichero.
- `fase`: `irradiacion` | `enfriamiento`. Sin defecto: si falta, el diálogo pregunta.
- `isotopo`: clave estilo fort.6 (`I131`). Si falta, se asume el isótopo activo del informe.
- `unidad_t`: `s` | `min` | `h` | `d`. Sin defecto: si falta, el diálogo pregunta.
- `unidad_A`: `Bq/cm3` | `MBq/g` | `MBq` | `mCi` (las de la Fase 2). Sin defecto: si
  falta, el diálogo pregunta. La conversión a la unidad activa de la UI usa la
  densidad/volumen de la simulación contra la que se compara.
- `fuente`: texto libre de trazabilidad.

## Sintaxis

- Delimitador autodetectado: `;`, `,` o tabulador. Decimal autodetectado con regla
  sin ambigüedad: con delimitador `;`/tab el decimal puede ser `,` o `.`; con
  delimitador `,` el decimal DEBE ser `.`.
- Cabecera de columnas (`t;A` o `t;A;A_err`) opcional: se detecta por ser no numérica.
- Orden de filas libre (la herramienta ordena por t). Filas vacías y líneas `#` se ignoran.
- Codificación UTF-8 (tolerante a BOM).

## Diálogo de importación (requisitos de UX)

1. Previsualización de las primeras 5 filas con selector de asignación de columnas
   (t / A / A_err / ignorar) por columna. Pre-asignación heurística: la columna
   (casi) monótona es t. Motivo: los ficheros del mundo real (p. ej. digitalizados
   con WebPlotDigitizer) llegan con frecuencia con las columnas invertidas.
2. Campos fase / unidades / isótopo / tipo / etiqueta, autorrellenados desde los
   metadatos si existen, editables siempre.
3. Se pueden cargar VARIAS series simultáneamente (p. ej. experimental + referencia
   computacional del paper, como en la Fig. 6); cada una con su etiqueta y estilo.
   Las métricas de desviación (tabla punto a punto, media, máxima) se calculan para
   CADA serie cargada, sea del tipo que sea — una tabla independiente por serie,
   con el tipo visible en su cabecera (Fase 6 del BACKLOG). Con varias simulaciones
   cargadas, un desplegable único (fuera de este diálogo, junto a las tablas de
   desviación) elige contra qué simulación se interpolan TODAS las series; con una
   sola simulación no aparece. La gráfica sigue mostrando todas las curvas de
   simulación, independientemente de cuál sea la elegida para las métricas.

## Fixtures asociados (tests de la Fase 4)

En `tests/fixtures/experimental/`:
- `fig6_exp4_experimental_normalizado.csv` — 29 puntos, t 14.6–171.4 h, A 4669–7866 MBq/g.
- `fig6_exp4_computacional_normalizado.csv` — 28 puntos, t 2.1–171.9 h, A 4919–8862 MBq/g.
- Cross-check físico anotado: la serie computacional decae con A(t_fin)/A(t_ini)=0.555
  en ~170 h, frente a 0.543 del decaimiento puro de I-131 (T1/2=8.0231 d) — coherente
  con digitalización de una curva de decaimiento casi puro.
- OJO: estas series pertenecen al CUARTO experimento del paper (irradiación larga,
  actividades ~10^3 MBq/g), NO a la ref_sim de tests/fixtures/ref_sim (pulso de 10 s,
  ~10^-1 MBq/g tras normalizar). Sirven como fixtures del PARSER y del diálogo de
  importación. Para superponerlas con sentido físico hace falta analizar el fort.6
  del cuarto experimento. El criterio de aceptación de la Fase 4 sigue siendo el del
  runbook: los 11 puntos del script legacy sobre la ref_sim.
- Fase 6 del BACKLOG (`ACABRefData.seriesForMetrics`/`resolveTargetSimName`): como
  una de estas dos series es `experimental` y la otra `computacional_referencia`,
  el par sirve tal cual para verificar que AMBAS entran ahora en las métricas de
  desviación (antes solo la experimental).
