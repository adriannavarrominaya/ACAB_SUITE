---
name: no-node-runtime
description: Node IS available on this machine as of 2026-07-08 (v24.18.0) — the earlier "no node" finding was stale
metadata:
  type: project
---

Actualización 2026-07-08: `Get-Command node.exe` encuentra node v24.18.0 en
`C:\Program Files\nodejs\node.exe`. Los `tools/test_units.js`, `tools/test_export.js`
y `tools/test_reference_data.js` corren y pasan en verde con `node tools/test_*.js`
en esta misma máquina — no hace falta esperar al tutor/CI para verificarlos.

**Why:** un hallazgo anterior de sesión (`Get-Command node/deno/bun` sin
resultados) quedó guardado como memoria permanente y ya no era cierto; instaló
node en algún momento entre sesiones. Verificar SIEMPRE con `Get-Command node`
antes de asumir esta limitación otra vez.

**How to apply:** al tocar `static/js/*.js`, ejecutar también
`node tools/test_units.js`, `node tools/test_export.js` y
`node tools/test_reference_data.js` (además de la suite Python) antes de dar
la fase por cerrada. El oráculo Python espejado en `tools/test_fort_analyzer.py`
y `tools/test_reference_data.py` (ver [[phase2-units-done]]) sigue siendo útil
como segunda verificación independiente, pero ya no es la única disponible.
