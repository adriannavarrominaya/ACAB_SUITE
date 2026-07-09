# Runbook — Generador de Barridos Paramétricos (ACAB INP File Configurator)

OBSOLETO: sustituido íntegramente por RUNBOOK_barrido_parametrico_v2.md. Conservado solo como histórico.

**Objetivo:** añadir al configurador la capacidad de generar N carpetas de simulación
(cada una con su `inp.5`) a partir de un fichero base y un producto cartesiano de
valores de parámetros, junto con un manifest de trazabilidad y scripts de ejecución.

**Repositorio afectado:** `ACAB_inp_file_configurator` (fase 5 opcional toca `ACAB_fort_file_analyzer`).

**Cómo usar este runbook con Claude Code:** ejecutar las fases en orden, una sesión
por fase. Cada fase incluye un prompt sugerido y criterios de aceptación. No pasar
a la siguiente fase sin que los criterios de la actual estén en verde.

---

## Decisiones de diseño ya tomadas (no re-debatir durante la implementación)

| Parámetro barrido | Mecanismo en el inp.5 | Notas |
|---|---|---|
| Flujo | Escalar `block9.XNORM` | Confirmado en `docs/Block#9.md`: XNORM escala todos los flujos. NO tocar el Bloque #3. |
| Masa del blanco | Recalcular `XCOMP` del Bloque #5 | Portar la fórmula de `static/js/calc_utils.js` a Python: `XCOMP_i = (m·w_i/M_i)·N_A/(1e24·V)`. Solo INPT=1/3 (misma limitación que la composición asistida). Datos en `static/data/atomic_data.json`. |
| T_irr | Regenerar la malla de irradiación de `blocks78` | Malla geométrica (rampa ×2) que termina en T_irr, manteniendo la malla de enfriamiento del fichero base. Lógica de referencia: `generador_acab.py` (Tkinter). Plan B si hay fricción: modo factor (escalar los tiempos de irradiación existentes). |

Otras decisiones:

- **Salida a disco** en ruta absoluta indicada por el usuario (patrón ya usado por el
  analyzer). ZIP descargable como opción secundaria, no prioritaria.
- **Manifest obligatorio**: `sweep_manifest.json` + `sweep_manifest.csv` en la carpeta raíz
  del barrido, mapeando nombre de carpeta → valores de parámetros.
- **Scripts de ejecución** `run_all.ps1` y `run_all.sh` generados (plantilla con la ruta al
  ejecutable de ACAB como variable a rellenar por el usuario; no intentamos ejecutar ACAB).
- **Reutilizar** `_write_inp5()` de `app.py` para serializar cada combo. Cero duplicación
  de lógica de formato.
- **Límites**: máx. 500 combos (HTTP 422 si se supera). El frontend pide confirmación
  si N > 50.
- **Nunca sobrescribir**: si la carpeta destino contiene subcarpetas con el mismo nombre,
  error salvo `overwrite: true` explícito.
- **Nomenclatura de carpetas**: patrón `Tirr{val}h_x{xnorm}_m{masa}g` usando solo los
  parámetros efectivamente barridos, con formato numérico estable (sin puntos flotantes
  largos; p. ej. `Tirr024h_x0.75_m1.00g`). Debe ser determinista y único por combo.

---

## Fase 0 — Preparación y verificación del terreno

**Tareas**
1. Crear rama `feature/sweep-generator`.
2. Leer y resumir (para contexto de la sesión): `app.py` (`_write_inp5`, `_sci`,
   `/api/save`), `acab_parser.py` (estructura del dict `data`, en especial `blocks78`,
   `block5`, `block9`), `static/js/calc_utils.js`, `generador_acab.py`,
   `docs/Block#7&#8.md`, `docs/Block#9.md`, `docs/Block#5.md`.
3. Ejecutar la suite existente y confirmar que está en verde ANTES de tocar nada:
   - `python tools/regression_roundtrip.py <ficheros oro>`
   - `python tools/test_parser_robustness.py <inp.5 de referencia>`
   - `node tools/test_calc_utils.js`
   - `node tools/test_validate_all.js`

**Criterio de aceptación:** suite en verde documentada en un comentario del commit inicial.

**Prompt sugerido para Claude Code:**
> Lee app.py, acab_parser.py, static/js/calc_utils.js, generador_acab.py y los docs de
> los bloques 5, 7/8 y 9. Ejecuta la suite de tests existente (tools/) y confirma que
> pasa. Resume la estructura del dict que devuelve read_inp5 para blocks78, block5 y
> block9. No modifiques nada todavía.

---

## Fase 1 — Módulo backend `sweep_generator.py` (funciones puras + tests)

Crear `sweep_generator.py` en la raíz del proyecto, sin dependencias de Flask,
totalmente testeable. Funciones:

1. `expand_grid(params: dict[str, list[float]]) -> list[dict[str, float]]`
   Producto cartesiano ordenado y determinista. `params` p. ej.
   `{"t_irr_h": [12,24,48], "xnorm": [0.75,1.0], "mass_g": [0.5,1.0]}`.

2. `parse_values(spec: str | dict) -> list[float]`
   Acepta lista separada por comas (`"12, 24, 48"`) o rango
   (`{"start":12, "stop":96, "step":12}` o sintaxis `"12:96:12"`). Rechaza listas
   vacías, valores no positivos donde no proceda, y más de 100 valores por parámetro.

3. `build_folder_name(combo: dict, swept_keys: list[str]) -> str`
   Determinista, único, seguro para sistema de ficheros (sin espacios ni caracteres
   problemáticos), solo con los parámetros barridos.

4. `apply_xnorm(data: dict, xnorm: float) -> dict`
   Copia profunda del dict y asigna `block9.XNORM`. No mutar el original.

5. `compute_xcomp(formula: str, mass_g: float, volume_cm3: float, inpt: int) -> dict`
   Port fiel de `parseChemFormula` + cálculo de calc_utils.js, leyendo masas atómicas
   de `static/data/atomic_data.json`. **Test oro obligatorio:** m=0.1231 g de TeO2,
   V=1 cm³ → N(Te)=4.6450e-4, N(O)=9.2899e-4 (mismo caso que test_calc_utils.js,
   tolerancia relativa 1e-4).

6. `apply_mass(data: dict, mass_g: float, formula: str, volume_cm3: float) -> dict`
   Recalcula los XCOMP del Bloque #5 (zona única en el MVP; si hay varias zonas,
   aplicar a la zona que indique el usuario y documentarlo). Error claro si INPT=2.

7. `generate_irr_mesh(t_irr: float, n_steps: int, iunit: int) -> list[float]`
   Malla geométrica de razón 2 que termina exactamente en `t_irr`
   (t_k = t_irr · 2^(k-n) para k=1..n). n_steps ≤ 10.

8. `apply_t_irr(data: dict, t_irr_h: float, n_steps: int) -> dict`
   Sustituye la fase de irradiación de `blocks78` por la malla generada, conservando
   la fase de enfriamiento del fichero base y recomponiendo los sets (MMN, MOUT, NGO,
   MSUB) conforme a las reglas del doc Block#7&8 y las validaciones V25 del frontend.
   **Esta es la función delicada:** escribir primero sus tests con un caso construido
   a mano (p. ej. T_irr=64 h, 7 pasos → 1,2,4,8,16,32,64) y con un caso que requiera
   dos sets (>10 timesteps totales entre irradiación y enfriamiento).

9. `generate_sweep(base_data: dict, spec: dict) -> list[tuple[str, dict]]`
   Orquestador: expande el grid, aplica cada handle en orden, devuelve
   `[(folder_name, data_modificado), ...]`. Valida N ≤ 500.

**Tests:** `tools/test_sweep_generator.py` (estilo de los tests existentes, ejecutable
con `python tools/test_sweep_generator.py`). Cobertura mínima: grid, parse_values
(lista, rango, errores), folder names únicos, caso oro de compute_xcomp, mallas de
irradiación (los dos casos anteriores), round-trip de un combo completo: base →
apply_* → `_write_inp5` → `read_inp5` → verificar que XNORM, XCOMP y tiempos coinciden
con lo esperado.

**Criterios de aceptación**
- `python tools/test_sweep_generator.py` en verde.
- La suite previa sigue en verde (no se ha tocado código existente aún, debe ser trivial).
- Ninguna función de `sweep_generator.py` importa Flask ni toca el sistema de ficheros
  (salvo la lectura de `atomic_data.json`).

**Prompt sugerido:**
> Implementa sweep_generator.py según la Fase 1 del runbook. Empieza por los tests
> (tools/test_sweep_generator.py) de generate_irr_mesh y apply_t_irr con los casos
> especificados, y luego implementa hasta que pasen. Para compute_xcomp porta
> fielmente calc_utils.js y usa su mismo caso oro. Ejecuta también la suite existente
> al terminar.

---

## Fase 2 — Endpoints `POST /api/sweep/preview` y `POST /api/sweep`

En `app.py`:

**`POST /api/sweep/preview`** — body:
```json
{
  "data": { ...dict del formulario actual... },
  "params": {
    "t_irr_h": {"values": "12, 24, 48, 96", "n_steps": 7},
    "xnorm":   {"values": "0.75:1.25:0.25"},
    "mass_g":  {"values": "0.5, 1.0", "formula": "TeO2", "volume_cm3": 1.0}
  }
}
```
Respuesta: `{ok, n_combos, folders: [...], warnings: [...]}` sin escribir nada.
Cada parámetro es opcional (barrer solo 1 o 2 es válido).

**`POST /api/sweep`** — mismo body más `{"dest": "C:/ruta/barrido_1", "overwrite": false}`.
Comportamiento:
1. Validar dest (existe o es creable; si contiene subcarpetas en colisión y
   `overwrite` es false → 409 con la lista de colisiones).
2. Generar cada combo con `generate_sweep` + `_write_inp5` (reutilizar, no duplicar).
3. Escribir `<dest>/<folder>/inp.5` por combo.
4. Escribir `sweep_manifest.json` (con: timestamp, fichero base si se conoce, spec
   completa del barrido, y lista `[{folder, params}]`) y `sweep_manifest.csv`
   (columnas: folder + un parámetro por columna).
5. Escribir `run_all.ps1` y `run_all.sh`: bucle sobre las subcarpetas, `cd` a cada una,
   invocar `$ACAB_EXE` (variable al principio del script con comentario "rellenar"),
   redirigiendo stdout a `run.log`.
6. Respuesta: `{ok, n_written, dest, manifest: "..."}`.

Errores siempre en JSON con mensaje accionable (mismo estilo que el resto de la app).

**Criterios de aceptación**
- Test de integración (puede ser un script en tools/ que use `app.test_client()`):
  preview de 2×2×2 devuelve 8 combos; sweep escribe 8 carpetas + manifest + scripts
  en un tmpdir; los 8 inp.5 se re-parsean con `ACABParser` sin error y los valores de
  XNORM/tiempos/XCOMP coinciden con el manifest.
- Colisión sin overwrite → 409. N>500 → 422.
- Suite completa en verde.

---

## Fase 3 — UI: modal "Barrido paramétrico"

En `templates/index.html` + `static/js/app.js` (o un `sweep.js` nuevo si app.js ya
pesa demasiado — preferible, siguiendo el patrón de chains.js):

1. Botón en la barra de herramientas (junto a Validar/Guardar): "Barrido paramétrico".
2. Modal Bootstrap con:
   - Tres secciones activables por checkbox (T_irr / Flujo (XNORM) / Masa), cada una
     con su campo de valores (placeholder mostrando ambas sintaxis: `12, 24, 48` o
     `12:96:12`). La sección de masa muestra fórmula (prefijada con lo que haya en la
     composición asistida si se usó) y volumen. La de T_irr muestra nº de pasos
     (defecto 7) y la unidad IUNIT detectada del fichero base (solo lectura en el MVP).
   - Campo "Carpeta destino" (texto, ruta absoluta).
   - Botón "Previsualizar" → llama a `/api/sweep/preview` y muestra tabla de combos
     (nombre de carpeta + valores). Si N > 50, aviso destacado.
   - Botón "Generar" (deshabilitado hasta que haya preview OK) → `/api/sweep`,
     spinner, y al terminar toast con "N ficheros generados en <dest>".
3. Antes de previsualizar, ejecutar `validateAll()` sobre el fichero base y bloquear
   si hay errores (mismo patrón que Guardar).
4. i18n: todas las cadenas nuevas en `static/i18n/es.json` y `en.json` con `data-i18n`.

**Criterios de aceptación**
- Flujo manual completo: cargar un inp.5 de examples → barrido 2×2 → carpetas
  generadas y re-cargables una a una en el propio configurador sin errores.
- `node tools/test_validate_all.js` sigue en verde (no romper el validador).
- Sin cadenas hardcodeadas fuera de i18n.

---

## Fase 4 — Documentación y regresión final

1. Sección nueva en README.md: qué hace, sintaxis de valores, estructura de salida,
   manifest, límites (500 combos, INPT=2 no soportado en masa, T_irr regenera malla
   geométrica ×2), y ejemplo completo con TeO2.
2. Añadir los comandos de test nuevos a la sección "Suite de tests".
3. Ejecutar TODA la suite (vieja + nueva) y la regresión round-trip con los ficheros oro.
4. Commit final + merge de la rama.

**Criterio de aceptación:** suite completa en verde y README actualizado.

---

## Fase 5 (opcional, repo del analyzer) — Pestaña "Optimización"

Separable; hacer solo cuando el generador esté estable.

1. En `fort_analyzer.py`: si la carpeta analizada contiene `sweep_manifest.json`,
   cargarlo y adjuntar los parámetros a cada simulación en la respuesta de
   `/api/analyze`.
2. En el frontend: pestaña nueva que, con un isótopo seleccionado (p. ej. I131),
   muestre (a) tabla folder × parámetros × A_pico × t_pico, y (b) gráfica Plotly de
   A_pico vs un parámetro elegido, con las demás dimensiones como series de color.
3. Botón de exportación CSV de esa tabla.

**Criterio de aceptación:** con un barrido 4×2 generado en la Fase 2-3 y ejecutado en
ACAB, la pestaña muestra 8 puntos correctamente etiquetados.

---

## Riesgos y puntos de verificación humana (no delegar a Claude Code)

- **Verificar con el manual de ACAB 2008** que XNORM escala el flujo en el sentido
  esperado para vuestro caso de uso (Block#9.md lo indica, pero confirmad con una
  simulación de control: XNORM=0.5 debe ≈ halvar la tasa de producción en régimen
  lineal, lejos de saturación).
- **Caso de control de la malla:** regenerar a mano un inp.5 con T_irr distinto,
  ejecutar ACAB con él y con el generado por la herramienta, y comparar fort.6.
  Un solo caso basta para dar confianza a toda la fase 1.
- **Precisión del writer:** los ficheros generados heredan `_sci(prec=6)` (7 cifras
  significativas), ya documentado en el README. Irrelevante para ficheros nuevos.
- **Zona única en Bloque #5:** el MVP asume una zona para el recálculo de masa. Si
  vuestros casos usan varias, decidir explícitamente a cuál aplica antes de la Fase 1.
