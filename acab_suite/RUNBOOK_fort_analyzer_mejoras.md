# Runbook — Mejoras del ACAB Fort File Analyzer

Estado: fases 0–5 completadas; 6–7 pendientes de PHOTON.dat (ver 7a/7b). Estado global en README.md de esta carpeta.

**Objetivo:** llevar el analyzer de "visor de fort.6" a herramienta de análisis para
el TFG: unidades físicas relevantes (MBq/g, actividad total), exportación de datos,
validación contra datos experimentales, métricas de optimización de producción,
espectro gamma genérico, y paridad de calidad con las otras apps de la suite
(tests, i18n).

**Repositorio afectado:** `ACAB_fort_file_analyzer` únicamente.

**Cómo usarlo con Claude Code:** una sesión por fase, en orden. Las fases 2-7 son
independientes entre sí SALVO que: la 4 y la 6 dependen de la 2 (unidades), y todas
dependen de la 0 (tests) y siguen las convenciones de la 1 (i18n). No pasar de fase
sin criterios en verde.

Estado actual verificado (base del plan):
- Motor en `fort_analyzer.py`: `leer_fort6_irradiacion`, `leer_fort6_enfriamiento`,
  `leer_inp5`, `leer_decay_dat`, `descubrir_simulaciones`, `analizar_carpeta`,
  `calcular_pico`, `calcular_informe_isotopo`, `calcular_tablas_comparativas`.
- API: `/api/scan`, `/api/analyze`, `/api/isotopo_report`, `/api/gamma-spectrum`,
  `/api/defaults`, `/api/browse-folder`. Cache global `_analysis_cache` sin clave de carpeta.
- La sección `CONCENTRATIONS(GRAM)` del fort.6 NO se parsea; `compare_simulaciones.py`
  hardcodea la densidad 0.12317 g/cm³ (O=2.4688E-02 + Te=9.8478E-02) y datos
  experimentales embebidos.
- `GAMMA_I131` hardcodeado (lista [E_keV, I%]), servido solo si el isótopo es I131.
- `Z_BY_ELEM` en app.js solo cubre I, TE, XE, CS, BA. Sin i18n. Sin tests.

---

## Fase 0 — Red de seguridad: fixtures y tests oro

### Tarea humana previa (no delegar)
Elegir UNA simulación de referencia del TFG y copiar a `tests/fixtures/ref_sim/`:
`fort.6`, `inp.5`, `DECAY.dat` (y `PHOTON.dat` de la librería ACAB en
`tests/fixtures/`, para la Fase 7). Anotar en `tests/fixtures/README.md` los valores
esperados de esa simulación: A_pico de I131 (valor y t), T_irr, T_cool, y la densidad
total de CONCENTRATIONS(GRAM) si es la simulación del 0.12317.

### Tareas
1. Crear `tools/test_fort_analyzer.py` (script autocontenido, sin framework, estilo
   de la suite del configurador) con tests oro sobre los fixtures:
   - `leer_fort6_irradiacion` / `leer_fort6_enfriamiento`: nº de isótopos, nº de
     timesteps, valores puntuales de I131 (primero, pico, último), omisión de la
     columna INITIAL, detección de RESTART.
   - `leer_inp5`: T_irr, T_cool, XNORM, nº de grupos de flujo.
   - `leer_decay_dat`: semividas de I131, TE131M, XE133 (decodificación ZZAAAS, S=1).
   - `calcular_pico` de I131 contra el valor anotado en fixtures/README.md.
   - `analizar_carpeta` sobre una carpeta con la ref_sim como subcarpeta.
2. `tools/test_api.py` con `app.test_client()`: /api/analyze + /api/isotopo_report
   flujo feliz sobre los fixtures; errores controlados (carpeta inexistente).
3. Añadir los comandos al README y al CLAUDE.md del repo (sección Tests, sustituyendo
   la nota de "no hay suite").

**Criterio de aceptación:** ambos scripts en verde; a partir de aquí, TODA fase
termina con la suite completa en verde.

**Prompt sugerido:**
> Lee fort_analyzer.py y app.py. Los fixtures están en tests/fixtures/ con los
> valores esperados en su README.md. Implementa tools/test_fort_analyzer.py y
> tools/test_api.py según la Fase 0 del runbook, sin modificar el código de
> producción. Ejecuta hasta verde.

---

## Fase 1 — Paridad y robustez: i18n, Z_BY_ELEM, cache

Se hace ANTES que las fases funcionales para que todas las cadenas nuevas nazcan
conformes.

1. **i18n**: replicar el mecanismo del COLLAPS configurator (el más limpio de la
   suite): `static/i18n/es.json` + `en.json`, atributos `data-i18n` en index.html,
   loader JS con función `t()` para cadenas dinámicas de app.js, selector de idioma
   en la barra. Migrar TODAS las cadenas actuales. Español como idioma por defecto.
2. **`Z_BY_ELEM` completo**: sustituir el dict de 5 elementos por la tabla completa
   símbolo→Z (H..Og, claves en MAYÚSCULAS como aparecen en fort.6). El filtro por
   elemento y el campo Z del informe deben funcionar con cualquier material.
3. **Cache con clave**: `_analysis_cache` pasa a estar keyed por ruta de carpeta
   normalizada; `/api/isotopo_report` (y cualquier endpoint que consuma el cache)
   recibe y usa `folder` explícito. Dos pestañas con carpetas distintas ya no se
   pisan. Los endpoints devuelven 404 claro si se pide un informe de una carpeta no
   analizada.
4. Ampliar `tools/test_api.py`: informe con `folder` explícito; informe de carpeta
   no analizada → 404.

**Criterios de aceptación:** UI completa en es/en sin cadenas huérfanas; filtro por
elemento funciona con p. ej. CO o EU; suite en verde.

---

## Fase 2 — Normalización de unidades (la mejora principal)

1. **Parser nuevo** en fort_analyzer.py: `leer_fort6_concentraciones(filepath)` →
   `{'elementos': {'O': 2.4688e-2, 'TE': 9.8478e-2, ...}, 'total_g_cm3': 0.12317}`
   leyendo la sección `CONCENTRATIONS(GRAM)` del fort.6. Test oro: la ref_sim debe
   dar el total anotado en fixtures/README.md (si es la del script legacy,
   0.12317 ± 1e-4).
2. `analizar_carpeta` adjunta a cada sim `densidad_g_cm3` (None si la sección no
   existe, sin romper el análisis) y `/api/analyze` la incluye en la respuesta.
3. **Selector de unidades en la UI** (persistido en localStorage), aplicable a
   gráficas, informe y tablas comparativas:
   - `Bq/cm³` (actual, por defecto);
   - `MBq/g` = Bq/cm³ / (densidad_g_cm3 × 1e6) — deshabilitada con tooltip si la
     sim no tiene densidad;
   - `Actividad total (MBq)` y `(mCi)` = Bq/cm³ × V — requiere volumen en cm³,
     campo manual junto al selector (persistido), con nota de que debe ser el
     volumen de la zona simulada.
   La conversión es un factor por simulación aplicado en el FRONTEND; los datos
   internos y el cache siguen en Bq/cm³. Ejes, tooltips y cabeceras de tabla
   muestran SIEMPRE la unidad activa (vía i18n).
4. En simulaciones múltiples con densidades distintas, cada serie usa su propia
   densidad (mostrar la densidad de cada sim en su tarjeta/leyenda).
5. `compare_simulaciones.py`: marcar como legacy en su docstring y en el README
   (la Fase 4 lo sustituye); no invertir más en él.
6. Tests: conversión numérica (funciones puras JS si se extraen a un utils, o
   valores del informe vía API con unidad solicitada si se opta por servidor —
   decisión: FRONTEND, así que extraer `convertUnits()` puro y testearlo con node,
   creando `tools/test_units.js`).

**Criterios de aceptación:** con la ref_sim, el pico de I131 en MBq/g coincide con
el valor del script legacy (misma densidad, misma cifra); cambiar de unidad rehace
gráficas y tablas coherentemente; suite en verde.

---

## Fase 3 — Exportación CSV

Todo en frontend (los datos ya están en el navegador), sin dependencias nuevas.

1. Utilidad pura `toCSV(rows, headers, {delimiter, decimal})` en un
   `static/js/export_utils.js` + test node (`tools/test_export.js`). Opciones:
   delimitador `;` con decimal `,` (por defecto, compatible con Excel es-ES) o
   `,` con `.`; elección persistida en localStorage junto al selector de unidades.
2. Botones "Exportar CSV" en: (a) cada gráfica de series temporales — columnas
   t + una por serie, en la unidad activa, con cabecera de metadatos comentada
   (`# carpeta, isótopo, unidad, fecha`); (b) informe del isótopo — propiedades +
   tabla por simulación; (c) las dos tablas comparativas.
3. Nombres de fichero descriptivos: `I131_series_MBq_g_<carpeta>.csv`.

**Criterios de aceptación:** los CSV abren correctamente en Excel es-ES con el
delimitador por defecto; los valores coinciden con lo mostrado (misma unidad);
suite en verde.

---

## Fase 4 — Datos experimentales sobre las curvas (sustituye a compare_simulaciones.py)

1. En la vista de gráficas/informe: botón "Cargar datos experimentales" → file input
   CSV de dos columnas (t, A) con cabecera opcional. Diálogo pide: fase a la que
   corresponden los tiempos (irradiación | enfriamiento), unidad de t (h/d/s) y
   unidad de A (debe coincidir con una de las soportadas; típicamente MBq/g).
   Parseo tolerante a `;`/`,` y decimal `,`/`.` (reutilizar convenciones de la Fase 3).
2. Overlay como serie de puntos (scatter, sin línea) en la gráfica correspondiente,
   convertida a la unidad activa. Persistencia en appState (no en disco). Los puntos
   se incluyen en la exportación CSV de la gráfica.
3. **Métricas de validación** bajo la gráfica: para cada punto experimental,
   interpolar la curva ACAB en su t y calcular desviación relativa (%); mostrar
   tabla punto a punto + desviación media y máxima. (Interpolación: reutilizar
   `actividad_en_t` vía endpoint, o interpolación lineal en frontend — decisión:
   frontend, función pura testeada.)
4. Test node de la interpolación y del parseo de CSV experimental con los datos
   embebidos en compare_simulaciones.py como caso oro (exp_t/exp_A: 11 puntos).
5. README: sección de validación experimental; compare_simulaciones.py queda
   documentado como legacy.

**Criterios de aceptación:** reproducir la comparación del script legacy (misma
sim de referencia, mismos 11 puntos) da desviaciones equivalentes; suite en verde.

---

## Fase 5 — Métricas de optimización de producción

Se añaden al informe del isótopo (endpoint `/api/isotopo_report` + sección de UI),
todas exportables (Fase 3) y en la unidad activa (Fase 2).

1. **Curva de saturación teórica** (solo fase de irradiación, isótopos con T½
   conocida): overlay `A_teo(t) = A_sat·(1−e^(−λt))` sobre la curva ACAB, con
   `A_sat = A_ACAB(t_fin_irr)/(1−e^(−λ·t_fin_irr))`. Tabla de tiempos a
   50/75/90/95 % de saturación: `t_x = −ln(1−x)/λ`, marcando cuáles caben dentro
   del T_irr actual.
2. **Rendimiento**: `A_pico/T_irr` (actividad producida por hora de irradiación) y
   ganancia marginal del último tramo: `(A(t_fin)−A(0.9·t_fin))/(0.1·t_fin)`
   comparada con el rendimiento medio — responde a "¿compensa seguir irradiando?".
3. **Pureza radionucleídica** en t_pico:
   `P = A(iso objetivo) / Σ A(isótopos del MISMO elemento presentes en el fort.6)`,
   expresada en %. Justificación de dominio (documentar en README y tooltip): tras
   la separación radioquímica el producto contiene solo el elemento objetivo, así
   que las impurezas relevantes son sus otros isótopos (para I131: I130, I132, I133,
   I134, I135... los que existan en el fort.6). Mostrar la tabla de contribuciones.
   Lista de impurezas editable en la UI (por defecto: mismos-elemento).
4. Tests: funciones puras de las tres métricas con casos analíticos (p. ej. curva
   sintética exactamente exponencial → saturación exacta; dos isótopos con
   actividades conocidas → pureza exacta) en `tools/test_metricas.py` o node según
   dónde vivan (decisión: servidor/Python, junto al resto del cálculo del informe).

**Criterios de aceptación:** con la ref_sim, la curva teórica de I131 se ajusta
visualmente a la de ACAB en irradiación (desviación esperable solo si hay quemado
del blanco — anotar la observada en fixtures/README.md); métricas visibles,
exportables y con tests en verde.

---

## Fase 6 — Espectro gamma genérico desde PHOTON.dat

La fase de mayor incertidumbre (formato no documentado en el repo): va la última.

1. **Descubrimiento** (subfase separada, sin tocar producción): inspeccionar el
   `tests/fixtures/PHOTON.dat` real y documentar su formato en
   `docs/PHOTON_format.md` (estructura por nucleido, codificación —¿ZZAAAS como
   DECAY.dat?—, unidades de energía e intensidad, nº de líneas por nucleido).
   PARADA DE VERIFICACIÓN HUMANA: revisar ese doc antes de continuar; contrastar
   las líneas de I131 del fichero con la tabla ENSDF hardcodeada (la línea de
   364.489 keV ≈ 81.5 % debe reconocerse).
2. `leer_photon_dat(filepath)` → `dict[iso_key, list[[E_keV, I_pct]]]`, reutilizando
   la decodificación ZZAAAS de `leer_decay_dat`. Localización del fichero: misma
   lógica de descubrimiento que DECAY.dat (subcarpeta de la sim y/o carpeta raíz).
3. Informe: `gamma_spectrum` disponible para CUALQUIER isótopo presente en
   PHOTON.dat. Fallback (comportamiento actual intacto): si no hay PHOTON.dat y el
   isótopo es I131, usar `GAMMA_I131`; en otro caso, espectro vacío con nota en la UI.
4. Tests: I131 desde el fixture vs tabla hardcodeada (mismas líneas principales,
   tolerancia en intensidades); un segundo isótopo (p. ej. TE131M o XE133) con
   valores anotados a mano en fixtures/README.md.

**Criterios de aceptación:** informe de XE133 (o similar) muestra su espectro desde
PHOTON.dat; informe de I131 idéntico al actual salvo fuente de datos; sin
PHOTON.dat todo funciona como hoy; suite en verde.

---

## Fase 7 — Documentación y cierre

1. README: nuevas secciones (unidades, exportación, validación experimental,
   métricas de optimización, PHOTON.dat) + capturas si procede.
2. CLAUDE.md del repo: actualizar la sección de tests (ya hay suite), añadir las
   convenciones nuevas (i18n obligatorio, conversiones de unidad en frontend,
   fixtures como casos oro) y retirar las notas de "pendiente" que ya no apliquen.
3. Suite completa en verde. Merge.

---

## Coordinación con otros runbooks

- La **pestaña "Optimización"** (Fase 5 del runbook v2 del barrido: leer
  `sweep_manifest.json` y graficar A_pico vs parámetro) encaja de forma natural
  DESPUÉS de las Fases 2 y 5 de este runbook (hereda unidades y métricas). Hacerla
  entonces, no antes.
- El **deep link `?folder=`** (Parte B del runbook de suite) es compatible con la
  cache keyed por carpeta de la Fase 1; si la Parte B se hace antes, coordinar la
  clave.

## Verificaciones humanas (no delegar)

- Elegir y congelar la simulación de referencia (Fase 0) y anotar sus valores oro.
- Confirmar que la densidad parseada de CONCENTRATIONS(GRAM) de esa sim coincide
  con la usada históricamente (0.12317 si es la misma del script legacy).
- Revisar `docs/PHOTON_format.md` antes de implementar el parser (Fase 6).
- Criterio físico de la pureza radionucleídica (¿solo isótopos del mismo elemento?
  ¿incluir algún precursor?) — la definición es configurable.
