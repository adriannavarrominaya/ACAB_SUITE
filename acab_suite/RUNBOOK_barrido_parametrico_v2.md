# Runbook v2 — Generador de Barridos Paramétricos (ACAB INP File Configurator)

Estado: completado (fases T0 y 1-3 implementadas, fase 5 opcional implementada en el analyzer; T0 ya existía en el código y se verificó el 2026-07-09). El estado actualizado de todos los runbooks se mantiene en README.md de esta carpeta.
Nota (2026-07-13): la malla del generador (y del barrido) es LINEAL, no geométrica como decía el caso oro original de la Fase 1; el test se congeló al comportamiento real del generador, y el control de malla (inp.5 byte-idénticos por ambas vías) valida la consistencia.

**Sustituye íntegramente al runbook v1 del barrido.**

**Objetivo:** desde el configurador, con un inp.5 base cargado y VÁLIDO, definir un barrido de UN parámetro (flujo vía XNORM / masa del blanco / historial temporal) con el resto de parámetros fijos, y generar N carpetas de simulación listas para ejecutar ACAB: cada una con su `inp.5` y con la copia del contenido de una "carpeta base" (librerías y ficheros auxiliares que ACAB necesita en el directorio de trabajo).

**Repositorio afectado:** `ACAB_inp_file_configurator` (Fase 5 opcional: analyzer).

---

## Decisiones de diseño ya tomadas (no re-debatir durante la implementación)

### Alcance y semántica

- **Un barrido = un solo tipo** (flujo XOR masa XOR temporal). Resto de parámetros   congelados tal como estén en el fichero base. El producto cartesiano es v2 futura.
- **Flujo → `block9.XNORM`.** Confirmado en docs/Block#9.md: factor multiplicativo   que escala todos los flujos; sin restricción de rango documentada; válidos los   reales > 0, incluidos > 1. Escala magnitud, NO forma del espectro (las XS   colapsadas por COLLAPS siguen siendo válidas en todo el barrido).
- **Masa → XCOMP de UNA zona objetivo** (selector si hay varias). Estructura de zonas CONGELADA en todo el barrido: IZM, NUCZO, MA, XRR y el resto del Bloque #2 no se tocan. Compuesto y volumen fijos; solo varía la masa (⇒ físicamente, la densidad de empaquetado del blanco). El volumen NO es barrible en el MVP (en
  geometrías 3-D vive también en XRR y exigiría coherencia adicional).
- **Temporal → blocks78 regenerado por simulación** reutilizando el generador de historial temporal YA EXISTENTE en la web (`generarB78` en app.js), refactorizado a función pura. Cada simulación define sus fases (t_fin, pasos) de irradiación y/o enfriamiento. OBLIGATORIO sincronizar `block11.NOTTS = nº de sets` por simulación (el generador actual ya lo hace; el barrido debe replicarlo).

### Arquitectura: patches en cliente + servidor genérico

- El frontend calcula por simulación un **patch** (fragmento del dict de datos que
  cambia) usando funciones puras JS: `{block9:{XNORM:v}}`, `{block5:{...XCOMP zona...}}`
  o `{blocks78:{...}, block11:{NOTTS:n}}`. Los cálculos reutilizan `calc_utils.js`
  (masa→XCOMP, ya testeado) y la lógica extraída de `generarB78` (mallas).
- El backend expone UN endpoint genérico que: fusiona cada patch sobre una copia
  profunda del base, escribe con el `_write_inp5()` existente, copia la carpeta base,
  y escribe manifest + README + scripts. El servidor NO conoce los tipos de barrido.

### Carpetas, nombres y ficheros de salida

- Entradas de la pestaña: **carpeta raíz** (se crean dentro las subcarpetas),
  **carpeta base** (su contenido se copia íntegro y recursivo a cada subcarpeta),
  **prefijo** común, y **descripción** del barrido (texto libre obligatorio).
- Subcarpeta por simulación: `<prefijo><sufijo>`. El sufijo se AUTO-PROPONE desde el
  valor (`x0.75`, `m1.500g`, `Tirr048h`) y es editable por fila. Validación de
  unicidad y de caracteres seguros para el sistema de ficheros.
- Si la carpeta base contiene un `inp.5`, el generado por el barrido lo REEMPLAZA
  (precedencia explícita del generado).
- En la carpeta raíz se escriben además: `sweep_manifest.json` (timestamp, tipo de
  barrido, descripción, parámetros fijos clave del base —XNORM, masa/fórmula/volumen
  si se conocen, T_irr/T_cool—, y lista `[{folder, params}]`), `sweep_manifest.csv`
  (folder + una columna por parámetro), `README.txt` (descripción + resumen legible),
  y `run_all.ps1`/`run_all.sh` (bucle: cd a cada subcarpeta, invocar `$ACAB_EXE`
  —variable a rellenar—, stdout a `run.log`).
- Límites: máx. 200 simulaciones (422); confirmación en UI si N > 30. Previsualización
  muestra SIEMPRE: nº de simulaciones, tabla de sufijos/valores, y coste en disco
  estimado = tamaño(carpeta base) × N, con aviso destacado si supera 2 GB.
- Nunca sobrescribir: colisión de subcarpetas existentes → 409 con la lista, salvo
  `overwrite: true`.

### UX

- Nueva **pestaña "Barrido"** en la barra de pestañas principal (no modal).
- La pestaña siempre es accesible, pero en cabecera muestra el estado de
  `validateAll()` sobre el fichero base: si hay errores, los lista con los códigos V
  y enlace al campo (mecanismo existente) y DESHABILITA previsualizar/generar.
  La validación se re-ejecuta al entrar en la pestaña y justo antes de generar.
- Cada tipo de barrido muestra un TEXTO EXPLICATIVO fijo de qué hace y qué queda
  congelado (redacción en Fase 3). Todo con i18n es/en.

---

## Fase T0 — Verificación previa: reactividad NUCZO/IZM ↔ Bloque #5

Contexto: el usuario percibe que "al modificar NUCZO no cambian las zonas". Según el
código, `b2-NUCZO` tiene listener `change` → `rebuildBlock5()`; posibles causas de la
percepción: el evento requiere blur, o se editó IZM (que no reconstruye, solo valida V05).

**Tareas**
1. Reproducir manualmente: editar NUCZO (añadir/quitar valores, con y sin blur) y
   editar IZM, observando los paneles del Bloque #5. Documentar el comportamiento real.
2. Mejoras (si el comportamiento coincide con lo descrito):
   - Reconstruir también con evento `input` + debounce ~400 ms (conservando los datos
     ya introducidos en zonas que no cambian, comportamiento actual de rebuildBlock5).
   - Aviso reactivo visible junto a IZM y NUCZO cuando `len(NUCZO) ≠ IZM` (además de V05).
3. `node tools/test_validate_all.js` en verde.

**Criterio de aceptación:** editar NUCZO reconstruye las zonas de forma perceptible
sin necesidad de blur; discrepancia IZM/NUCZO visible de inmediato.

---

## Fase 1 — Funciones puras JS + tests node

Crear `static/js/sweep_utils.js` (puro, sin DOM, patrón calc_utils) y refactorizar:

1. **Refactor `generarB78`**: extraer de app.js la lógica a
   `buildBlocks78(fasesIrr, fasesCool, {iunit, iout, iplot})` → `{sets, times, notts}`
   (fases = listas de `{t_fin, pasos}`; troceado en sets de 10 con MMN/MOUT/NGO/MSUB
   exactamente como hoy). `generarB78` pasa a ser un wrapper que lee el DOM y llama a
   la función pura. Mover también `calcularVectorTiempos` si aún depende del DOM.
   CERO cambios de comportamiento del generador manual.
2. `sweep_utils.js`:
   - `parseSweepValues(txt)` → lista de números desde texto separado por comas
     (validaciones: no vacía, numéricos, ≤ 200).
   - `proposeSuffix(tipo, valor)` → `x0.75` / `m1.500g` / `Tirr048.0h` (formato
     estable, sin caracteres inválidos).
   - `buildFluxPatches(valores, modo, phiBase)` → lista de
     `{params:{XNORM}, patch:{block9:{XNORM}}}`. `modo`: 'xnorm' (valores directos) o
     'phi' (valores = flujo total objetivo; XNORM = φ_objetivo/φ_base). `phiBase` =
     Σ(flujos Bloque #3 del base) × XNORM_base.
   - `buildMassPatches(masas, formula, volumen, zoneIdx, baseBlock5)` → recalcula
     INUCL/XCOMP de esa zona con las funciones de calc_utils.js; INUCL no cambia
     (mismo compuesto), solo XCOMP. Error claro si INPT=2.
   - `buildTimePatches(filas, opts)` → por fila `{t_irr_fin, pasos_irr, t_cool_fin,
     pasos_cool}` llama a `buildBlocks78` y devuelve
     `{params, patch:{blocks78, block11:{NOTTS}}}`. Campos vacíos ⇒ se conserva la
     fase del fichero base (p. ej. barrer solo T_irr con enfriamiento del base).
3. Tests: `tools/test_sweep_utils.js` (node, estilo test_calc_utils.js):
   - buildBlocks78 caso oro: irr (t_fin=64, pasos=7) → tiempos 1,2,4,8,16,32,64
     (verificar contra el generador actual antes del refactor); caso >10 timesteps →
     2 sets con NGO/MSUB correctos y notts=2.
   - buildMassPatches con el caso oro de calc_utils (0.1231 g TeO2 → 4.6450e-4 / 9.2899e-4).
   - buildFluxPatches modo 'phi' (φ_base=2e14, objetivo=1e14 → XNORM=0.5).
   - parseSweepValues y proposeSuffix (casos límite).

**Criterios de aceptación:** tests nuevos en verde; `test_calc_utils.js` y
`test_validate_all.js` en verde; el generador manual de la pestaña temporal se
comporta EXACTAMENTE igual que antes del refactor (probar a mano un caso).

**Prompt sugerido:**
> Implementa la Fase 1 del runbook v2 del barrido. Primero escribe
> tools/test_sweep_utils.js con los casos oro indicados, verificando el caso de
> buildBlocks78 contra la salida actual de generarB78 ANTES de refactorizar; luego
> extrae la función pura y crea sweep_utils.js hasta que todo pase. Ejecuta toda la
> suite del repo al terminar.

---

## Fase 2 — Endpoint genérico de generación

En `app.py` (+ funciones auxiliares en un `sweep_writer.py` si app.py crece demasiado):

**`POST /api/sweep/preview`** — body:
```json
{
  "root": "C:/TFG/barridos/flujo_1",
  "base_folder": "C:/TFG/acab_base",
  "prefix": "TeO2_",
  "sims": [ {"suffix": "x0.50"}, {"suffix": "x0.75"} ]
}
```
Sin escribir nada, devuelve: existencia/accesibilidad de root y base_folder, tamaño
de base_folder, coste estimado (× N), colisiones de subcarpetas existentes, sufijos
duplicados o inválidos, y si base_folder contiene inp.5 (aviso de reemplazo).

**`POST /api/sweep`** — body añade `data` (dict completo del formulario base),
`sweep_type`, `description`, `fixed_params` (dict informativo para el manifest),
y en cada sim: `params` (valores para el manifest) y `patch`. Más `overwrite: false`.

Comportamiento:
1. Re-validar límites (N ≤ 200, sufijos únicos/seguros, rutas). Colisión sin
   overwrite → 409.
2. Por sim: deep-copy de `data` + **merge recursivo** del patch (dicts se fusionan
   por clave; listas y escalares se reemplazan enteros) → `_write_inp5()` →
   verificación round-trip inmediata (re-parsear con ACABParser; si falla, abortar
   TODO el barrido con mensaje indicando la sim culpable, y borrar lo ya escrito).
3. Copiar contenido de base_folder (recursivo, `shutil.copytree` con
   dirs_exist_ok) a cada subcarpeta; escribir después el inp.5 generado (reemplaza).
4. Escribir manifest JSON+CSV, README.txt y run_all.ps1/.sh en root.
5. Respuesta `{ok, n_written, root}`.

**Tests** (`tools/test_sweep_endpoint.py`, con `app.test_client()` y tmpdir):
merge recursivo (casos: escalar, dict anidado, lista reemplazada); flujo feliz 3 sims
con base_folder de juguete (2 ficheros + subdir) verificando copia + reemplazo de
inp.5 + manifest coherente; 409 por colisión; 422 por N>200 y sufijo duplicado;
aborto y limpieza si un patch produce un inp.5 no re-parseable.

**Criterios de aceptación:** tests nuevos + suite completa en verde.

---

## Fase 3 — Pestaña "Barrido"

`templates/index.html` + `static/js/sweep.js` (nuevo, siguiendo el patrón chains.js):

1. **Cabecera de la pestaña:** estado de validación del fichero base (re-ejecutar
   `validateAll()` al entrar). Con errores: lista de códigos V con enlace al campo,
   botones de acción deshabilitados.
2. **Configuración común:** carpeta raíz, carpeta base, prefijo, descripción
   (obligatoria). Persistir los dos últimos valores usados en localStorage.
3. **Selector de tipo** (3 tarjetas radio) y panel específico:
   - **Flujo:** texto explicativo (XNORM multiplica el flujo manteniendo la forma
     del espectro; todo lo demás congelado). Mostrar φ_base calculado del fichero
     (Σ Bloque #3 × XNORM base). Toggle de modo de entrada: valores XNORM | flujo
     total objetivo. Campo de valores separados por comas.
   - **Masa:** texto explicativo (volumen y compuesto fijos ⇒ varía la densidad de
     empaquetado; estructura de zonas congelada). Selector de zona objetivo (de las
     zonas actuales del Bloque #5), compuesto y volumen (prefijados desde la
     composición asistida si se usó), campo de masas. Bloquear con mensaje si INPT=2.
   - **Temporal:** texto explicativo. Tabla editable de N filas con columnas
     t_irr_fin / pasos_irr / t_cool_fin / pasos_cool (vacío = conservar fase del
     base) + botón "añadir fila". Reutiliza buildTimePatches.
4. **Tabla de simulaciones** (común, se rellena al pulsar "Previsualizar"): fila por
   sim con valores, sufijo editable, carpeta resultante; encima: nº de simulaciones,
   patrón `<prefijo><sufijo>` y coste en disco estimado (de /api/sweep/preview),
   con aviso si > 2 GB. Confirmación adicional si N > 30.
5. **Generar:** llama a /api/sweep; spinner; al terminar, resumen con la ruta raíz.
   Errores del servidor mostrados íntegros.
6. i18n completo (es.json + en.json) de todas las cadenas, textos explicativos incluidos.

**Criterios de aceptación (manuales):**
- Flujo: barrido de 4 XNORM sobre un ejemplo → 4 carpetas; cada inp.5 recargado en el
  configurador muestra su XNORM y NADA más cambiado (comparar con el base).
- Masa: barrido de 3 masas → XCOMP de la zona objetivo cambia según el caso oro; las
  demás zonas intactas.
- Temporal: barrido de 3 T_irr → mallas correctas y NOTTS coherente en cada inp.5;
  el generador manual de la pestaña temporal sigue funcionando igual.
- Con un fichero base con errores de validación, imposible previsualizar/generar.

---

## Fase 4 — Documentación y regresión final

1. README: sección "Barrido paramétrico" (tipos, qué queda congelado en cada uno,
   estructura de salida, manifest, límites, y las dos notas de dominio: XNORM escala
   magnitud y no forma; masa a volumen fijo = densidad de empaquetado).
2. Comandos de test nuevos añadidos a la sección de suite y al CLAUDE.md del repo.
3. Suite COMPLETA en verde + round-trip con ficheros oro. Merge de la rama.

---

## Fase 5 (opcional, repo analyzer) — Pestaña "Optimización"

Sin cambios respecto al v1: si la carpeta analizada contiene `sweep_manifest.json`,
adjuntar parámetros a cada simulación; pestaña con tabla folder × params × A_pico ×
t_pico y gráfica A_pico vs parámetro; exportación CSV. La descripción del barrido
(manifest) se muestra como subtítulo.

---

## Verificaciones humanas (no delegar a Claude Code)

- **Control XNORM (antes de fiarse del barrido de flujo):** dos ejecuciones reales,
  XNORM=1 y XNORM=0.5, con t_irr corto (régimen lineal): la actividad debe escalar
  ≈ ×0.5. Confirmar en fort.6 el eco del flujo normalizado. Documentar el resultado
  (sirve además para la memoria del TFG).
- **Control de malla:** un inp.5 con historial regenerado por el barrido vs el mismo
  generado a mano con la pestaña temporal → fort.6 idénticos.
- **Aclaración física para la memoria:** el barrido de flujo asume espectro de forma
  fija (MURR colapsado con COLLAPS); si el escenario real cambia la forma del
  espectro, se debe regenerar con COLLAPS, no con XNORM.
- **Carpeta base:** decidir su contenido canónico (librerías, DECAY.dat, etc.) y
  mantenerla como plantilla estable del TFG.
