# Mini-runbook — Figuras YAML sin defaults + selector + guardado (Fort File Analyzer)

**Estado: pendiente.** Estado global de runbooks en README.md de esta carpeta.

**Objetivo:** la pestaña "Actividad por isótopo" deja de tener figuras hardcodeadas:
las figuras SIEMPRE provienen de un YAML (auto-descubierto en la carpeta analizada o
cargado por selector) o del editor; el editor puede guardar la configuración como
YAML en la carpeta analizada (persistencia entre análisis) o descargarla.

**Repo:** `ACAB_fort_file_analyzer`. Una sesión. Punto de partida verificado:
- `_load_yaml_config(folder)` en app.py ya busca `figuras - multiples simulaciones.yaml`
  y `config.yaml` en la carpeta y en su padre; `/api/analyze` ya acepta `yaml_content`
  (rama 'upload', hoy sin uso desde el frontend); `yaml_used` ∈ upload|auto|none.
- `DEFAULT_FIGURAS` (15 figuras del caso TeO2) en fort_analyzer.py, usadas como
  fallback en /api/analyze y servidas por `/api/defaults` (botón reset del editor).
- Editor de figuras funcional en app.js (`openFigurasEditor`, `btn-add-figura`,
  `applyFigurasChanges`, `resetFigurasToDefault`).

## Decisiones de diseño (no re-debatir)

1. **Sin YAML → figuras = [] + estado vacío amable** en la pestaña: panel con
   mensaje i18n y dos acciones: "Cargar YAML de figuras" (selector) y "Crear
   figuras con el editor". Nada se dibuja; los botones de exportar CSV de figuras
   quedan ocultos/deshabilitados en estado vacío.
2. **DEFAULT_FIGURAS se retira del flujo, no del repo**: mover el contenido a
   `docs/ejemplo_figuras_TeO2.yaml` (formato YAML real, con comentario de cabecera
   explicando que es plantilla/ejemplo). Eliminar la constante de fort_analyzer.py
   y toda referencia. El README de figuras (§7) enlaza el ejemplo.
3. **Nombre canónico nuevo `figuras.yaml`**: la búsqueda automática pasa a probar,
   en orden: `figuras.yaml`, `figuras - multiples simulaciones.yaml`, `config.yaml`
   (carpeta y padre, como hoy). El guardado escribe SIEMPRE `figuras.yaml` en la
   carpeta analizada. Compatibilidad total con carpetas antiguas.
4. **Selector de fichero** en la barra de la pestaña de figuras: lee el .yaml con
   FileReader y RELANZA `/api/analyze` con `yaml_content` (mecanismo existente) —
   necesario porque la sección `semividas` del YAML afecta al cálculo servidor.
   El badge de estado muestra el origen (carpeta / cargado a mano / sin figuras).
5. **Guardar desde el editor**, dos botones:
   - "Guardar en carpeta analizada" → `POST /api/figuras/save`
     `{folder, yaml_text, overwrite}`: valida que folder es la carpeta del último
     análisis en cache, escribe `<folder>/figuras.yaml`; si existe y no overwrite →
     409 (el frontend pide confirmación y reintenta). Tras guardar, badge → estado
     "carpeta" (equivalente a auto).
   - "Descargar YAML" → descarga por navegador (Blob), sin servidor.
6. **Round-trip de secciones ajenas**: al serializar, partir del YAML cargado (si
   lo hubo) y sustituir SOLO la clave `figuras`; conservar `semividas` y cualquier
   otra clave superior. Si no había YAML, serializar `{figuras: [...]}` solo.
   Guardar el cfg cargado en `_state` para esto.
7. **Botón reset del editor**: pasa de "restaurar por defecto" a "restaurar a las
   del YAML cargado" (copia profunda en cliente tomada al cargar/analizar);
   deshabilitado con tooltip si no hay YAML de partida. ANTES de retirar
   `DEFAULT_FIGURAS` de `/api/defaults`, buscar otros consumidores del endpoint
   (sirve también semividas/labels): retirar solo la clave `figuras` si hay otros
   usos; retirar el endpoint entero solo si nadie más lo usa.

## Tareas

1. Backend: retirar DEFAULT_FIGURAS (decisiones 2 y 7); `figuras.yaml` primero en
   `_load_yaml_config`; endpoint `/api/figuras/save` (validaciones: folder existe y
   coincide con un análisis en cache, yaml_text parsea con `yaml.safe_load` y tiene
   clave `figuras` lista — 422 si no; escribir UTF-8).
2. Frontend: estado vacío con acciones; selector de fichero (accept=".yaml,.yml") →
   re-análisis con yaml_content; botones Guardar/Descargar en el editor con la
   lógica de round-trip; reset reorientado; badge de origen con los tres estados.
3. i18n: todas las cadenas nuevas en `static/i18n/es.json` y `en.json`; actualizar
   la cadena existente "Sin YAML en carpeta — usando configuración por defecto"
   (ya no hay defecto).
4. Tests: actualizar `tools/test_api.py` (analyze sin YAML → `figuras: []`,
   `yaml_used: none`); añadir tests del endpoint save (guardado feliz + discovery
   posterior lo encuentra como 'auto', 409 sin overwrite, 422 con yaml inválido,
   round-trip que conserva una sección `semividas` de un YAML de partida).
   Si `/api/defaults` cambia, ajustar sus tests.
5. Documentación: README §7 (nuevo flujo: sin defaults, nombre canónico, selector,
   guardar; enlace al ejemplo TeO2) y CLAUDE.md (retirar menciones a
   DEFAULT_FIGURAS; describir el flujo YAML y el endpoint nuevo).

## Criterios de aceptación

- Analizar una carpeta SIN yaml: pestaña con estado vacío y acciones; cero figuras;
  suite en verde.
- Colocar `figuras.yaml` en la carpeta (o el nombre antiguo) y re-analizar: figuras
  cargadas, badge "carpeta".
- Cargar por selector un yaml con sección `semividas`: figuras aplicadas Y semividas
  efectivas (verificable en el informe); badge "cargado a mano".
- Editor: crear 2 figuras desde vacío → Guardar en carpeta → re-analizar → las
  figuras vuelven solas (badge "carpeta"). Guardar sobre un yaml previo con
  `semividas` NO pierde esa sección (comprobar el fichero resultante).
- "Descargar YAML" produce un fichero re-cargable por el selector.
- Los ficheros antiguos con `figuras - multiples simulaciones.yaml` siguen
  funcionando sin cambios.

## Prompt sugerido

> Implementa el mini-runbook de figuras YAML (../acab_suite/RUNBOOK_figuras_yaml.md)
> en este repo. Antes de tocar nada: ejecuta la suite completa (Python + node) y
> confirma verde; localiza todos los consumidores de DEFAULT_FIGURAS y de
> /api/defaults y decide según la decisión 7. Sigue las decisiones de diseño tal
> cual (no re-debatir), empieza por los tests del endpoint save, y termina con la
> suite completa en verde, README y CLAUDE.md actualizados, y commit.
