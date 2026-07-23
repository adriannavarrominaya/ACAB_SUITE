# acab_suite — transversal de la suite ACAB

> Parte de la [suite ACAB del TFG](../README.md) — configurar entradas → ejecutar → analizar salidas.

Carpeta transversal de la suite del TFG: launcher, configuración común y runbooks de mejoras. No es una app; las tres apps viven en las carpetas hermanas, los pendientes no planificados viven en BACKLOG.md.

## Puertos canónicos

| App | Puerto |
| --- | --- |
| ACAB_inp_file_configurator | 5000 |
| ACAB_fort_file_analyzer | 5001 |
| COLLAPS_inp_file_configurator | 5002 |

## Instalación (primera vez / ordenador nuevo)

```powershell
.\setup.ps1
```

Crea el venv compartido en `C:\venv\acab-venv` (parametrizable con `-VenvPath`) e instala en él las dependencias de las 3 apps. Es el único setup necesario para usar la suite con `suite_launcher.py` — sustituye a ejecutar el `setup.ps1` de cada app por separado (esos siguen existiendo para arrancar una app suelta con su propio venv local).

## Launcher

```powershell
# Con el venv de la suite (o cualquier Python con flask+waitress instalados):
C:\venv\acab-venv\Scripts\python suite_launcher.py
```

Qué hace:

1. Lee `suite_config.json` (lo crea con la plantilla por defecto si no existe).
2. Lanza cada app (`app.py --port <puerto> --no-browser`) como subproceso, con la  salida redirigida a `logs/<name>.log`. Si una app ya responde en su puerto, avisa "ya en ejecución" y no la lanza de nuevo.
3. Health-check de `/api/ping` hasta 15 s e informa ✓/✗ por consola.
4. Abre UNA pestaña del navegador en `open_browser`.
5. `Ctrl+C` para las apps lanzadas por el launcher (terminate; kill a los 5 s).

### `suite_config.json`

```json
{
  "apps": [
    {"name": "inp-configurator", "path": "../ACAB_inp_file_configurator", "port": 5000},
    {"name": "fort-analyzer",    "path": "../ACAB_fort_file_analyzer",    "port": 5001},
    {"name": "collaps",          "path": "../COLLAPS_inp_file_configurator", "port": 5002}
  ],
  "open_browser": "http://127.0.0.1:5000",
  "python": null
}
```

- `python` (global u opcionalmente por app): ruta del intérprete con el que lanzar
  las apps, p. ej. `"C:/venv/acab-venv/Scripts/python.exe"`. Si es `null`, el
  launcher busca en este orden: venv local del repo (`<app>/venv/`) y, si no
  existe, el mismo Python con el que se ejecutó el launcher. Así ninguna ruta de
  venv queda hardcodeada en el código.
- `open_browser`: URL que se abre al terminar el health-check (una sola pestaña;
  las apps se lanzan con `--no-browser`).

## Banner de navegación

Cada app muestra un banner superior con enlaces a las otras dos y un punto de
estado (● verde / ○ gris) alimentado por `static/js/suite_banner.js` (fetch a
`/api/ping` al cargar y cada 15 s). El fragmento HTML del banner y ese JS son
**copias sincronizadas en los 3 repos** — si se edita una copia, replicar en las
demás (ver comentario de cabecera en los propios ficheros).

## Runbooks

Estado a 2026-07-13. Cada runbook lleva además una línea de estado en su cabecera.

- `RUNBOOK_suite_y_runner.md` — Parte A (puertos/banner/launcher): ✅ implementada.
  Su Parte B queda sustituida íntegramente por `RUNBOOK_runner_v2.md`.
- `RUNBOOK_runner_v2.md` — runner de ejecución de ACAB/COLLAPS desde las
  interfaces. ✅ Fases R0-R5 completadas: `runner.py` (con cola) en ambos
  configuradores, paneles de ejecución individual, deep link al analyzer
  (`?folder=`), ejecución en cola del barrido (`/api/run/batch`) y detección de
  resultados desactualizados en el analyzer. Ampliado a pipelines de pasos por
  la fase P1 del barrido espectral (runner v3, compatible hacia atrás).
- `RUNBOOK_barrido_parametrico.md` — v1, ❌ OBSOLETO: sustituido por la v2;
  conservado solo como histórico.
- `RUNBOOK_barrido_parametrico_v2.md` — generador de barridos paramétricos
  (flujo/masa/temporal). ✅ Completado: T0 y fases 1-3, más la Fase 5 opcional en
  el analyzer (pestaña "Optimización", lee `sweep_manifest.json`). Nota: la malla
  temporal del generador y del barrido es lineal (ver cabecera del runbook).
- `RUNBOOK_fort_analyzer_mejoras.md` — mejoras del fort file analyzer.
  ✅ Fases 0-5 y 7a completadas (tests oro, i18n/paridad, unidades físicas,
  exportación CSV, datos experimentales, métricas de optimización, README).
  ⏸ Fases 6 y 7b pendientes de obtener `PHOTON.dat`.
- `RUNBOOK_figuras_yaml.md` — figuras de "Actividad por isótopo" sin defaults
  hardcodeados, con selector de YAML y guardado desde el editor. ✅ Completado y validado (2026-07-13).
- `RUNBOOK_barrido_espectral.md` — cuarto tipo de barrido (forma del espectro,
  COLL.inp tarjeta 7, espectros CONDERC/OIEA) + pipeline COLLAPS→ACAB.
  ✅ Completado: P0 (verificaciones: invariancia de escala ✅, unidades CX=MeV ✅,
  espectros descargados ✅), P1 (runner v3) ✅, P2 (import CONDERC + coll_writer)
  ✅, P3 (UI del cuarto tipo "Espectro (COLLAPS)" en la pestaña Barrido: tarjeta
  explicativa, φ_ref editable con patch uniforme, filas de espectros importados
  con índices/badge direccional, gráfica Plotly superpuesta, manifest con
  fracciones espectrales) ✅, P4 (`/api/run/batch` construye el pipeline D7
  por sim cuando `sweep_manifest.json` tiene `sweep_type: "spectrum"`, sin
  modificar `runner.py`; `batch_results.json` incluye los pasos y el resumen
  de FLUX.inf; UI de progreso con el paso en curso) ✅ y P5 (README del INP
  configurator con la sección de usuario del barrido espectral, columna
  "Rango de energía" en la tabla de espectros, verificación de la pestaña
  Optimización del analyzer y CLAUDE.md actualizado) ✅.

## Invocación de los códigos (fuente de verdad para el runner — fase R0)

Convención de la suite: **simulaciones autocontenidas**. Cada carpeta de simulación contiene su propio ejecutable junto a sus ficheros de entrada, y el código lee todo del directorio de trabajo actual. Esta sección prevalece sobre cualquier mención a "ruta del ejecutable" en los runbooks: NO hay ruta global de ejecutable; el runner invoca el exe de la propia carpeta.

### ACAB
- Ejecutable: `acab.exe`, presente EN la carpeta de la simulación.
- Invocación: el runner lanza `acab.exe` SIN argumentos con `cwd = carpeta de la simulación` (comando: la ruta absoluta `<workdir>\acab.exe`). Lee todas sus entradas del cwd.
- Fichero de entrada principal: `inp.5` (nombre que debe usar la opción "guardar el fichero actual en el workdir" del runner).
- Ficheros requeridos en el workdir (pre-check del runner; lista exacta de una carpeta de trabajo buena conocida): `acab.exe`, `inp.5`, `DECAY.dat`, `XSECTION.dat`.
- Salidas generadas: `fort.6` (la que consume el analyzer), fichero de tiempo de CPU (nombre: `cpu_time.txt`) y otros auxiliares.
- Duración típica: < 1 s. Timeout por defecto del runner: 60 s.
- Barridos: `acab.exe` y el resto de ficheros requeridos deben estar en la CARPETA BASE del barrido (se copian a cada subcarpeta de simulación, que así nace autocontenida).

  Nota: `XSECTION.dat` es salida de COLLAPS — si se regenera el espectro, actualizar la carpeta base de los barridos antes de generar/ejecutar.

### COLLAPS
- Ejecutable: `collaps.exe`, presente EN la carpeta de trabajo, mismo modelo
  que ACAB (sin argumentos, todo por cwd).
- Fichero de entrada principal: `COLL.inp`.
- Ficheros requeridos en el workdir: `collaps.exe`, `COLL.inp`, `XSBL.dat`.
- Salidas generadas: `XSECTION.dat`, `FLUX.inf`, `XS.inf`, `REACTIONS.dat`, `XSZERO.dat`.
- Duración típica: ~2 s. Timeout por defecto del runner: 60 s.

### Configuración del runner (a implementar en las fases R1-R4)
Se persiste por app en `suite_config.json`, clave `runner` dentro de cada app: `{"exe_name": "acab.exe", "required_files": [...], "output_file": "fort.6", "timeout_s": 60, "default_workdir": "..."}`. Los pre-checks del runner leen esta configuración, no listas hardcodeadas en el código. `exe_name` es un fichero requerido más: si no está en el workdir, error 422 con mensaje indicándolo.

## Verificaciones de control (checklist)

- **Control XNORM** ✅ (2026-07-09): barrido de flujo con XNORM ∈ {0.5, 1.0} sobre el caso de pulso (T_irr=10 s). A_pico(I131): 8.6140e+3 vs 1.7230e+4 Bq/cm³ → cociente 0.4999 ≈ 0.5 teórico (régimen lineal). El barrido de flujo escala la producción linealmente como predice la teoría. Ambas sims: t_pico=3.753 h (enfr.).
- **Control de malla** ✅ (2026-07-09): mismo historial temporal (T_irr y pasos idénticos) generado por las dos vías — generador manual de la pestaña temporal vs barrido temporal de una fila — produce inp.5 BYTE-IDÉNTICOS (verificado con fc). Al compartir ambas vías buildBlocks78 (sweep_utils.js) y _write_inp5, la equivalencia de los fort.6 queda garantizada sin ejecución comparada. **Refresco U7 (2026-07-23):** tras sustituir la fila plana del barrido temporal por el acordeón de tarjetas multi-tramo (mismo componente `b78_editor.js` que el generador manual), el control se automatizó y se extendió al caso multi-tramo: `tools/test_sweep_endpoint.py::test_time_sweep_byte_identical_manual_vs_sweep_path` construye un `blocks78` de 2 tramos por fase y comprueba que el inp.5 escrito por el camino manual (`_write_inp5` directo) y por el camino del barrido (`/api/sweep`) son BYTE-IDÉNTICOS, sin intervención manual. La equivalencia de malla (JS) se verifica aparte y en el mismo commit: `buildTimePatches([...]).patch.blocks78` es estructuralmente igual a `buildBlocks78(...)` para el mismo historial (`tools/test_sweep_utils.js`).
- **Criterio de pureza radionucleídica** ✅ impurezas = otros isótopos de yodo (confirmado el default mismo-elemento);requisito del producto: pureza > 99.9 % (impurezas < 0.1 %), con atención a I-124 (emisor β+) e I-125. Fuera de alcance de la herramienta: pureza química del Te (<10 μg/dosis, se mide en proceso). Concepto adicional anotado: I-127 estable e I-129 de vida larga no penalizan la pureza radionucleídica pero reducen la ACTIVIDAD ESPECÍFICA del yodo — posible métrica futura (los datos de átomos están en el fort.6).
- **Desviación saturación teórica vs ACAB** ✅ (2026-07-09): verificada la consistencia interna de la métrica sobre la ref_sim (A_sat=4.0138e+6 Bq/cm³ y t_50=192.61 h = ln2/λ, correctos). Con el pulso de 10 s la comparación de curvas es degenerada por construcción (anclaje en t_fin), así que la medición de la desviación real queda pendiente de un caso de irradiación larga. Detalle y valores oro: `ACAB_fort_file_analyzer/tests/fixtures/README.md`.
- **Control de invariancia de escala (barrido espectral, P0.1)** ✅ (2026-07-12): COLLAPS con la misma forma espectral y FT×10 produce XSECTION.dat idéntico — confirmado empíricamente que el colapso depende solo de la FORMA del espectro (D2 del runbook espectral).
- **Unidades de CX (P0.2)** ✅ (2026-07-12): COLLAPS espera la tarjeta CX en MeV; CONDERC publica en eV → el import convierte fronteras ×1e-6. Anotado en D4.
- **Incidente suite "en rojo" (P1, resuelto)** ✅ (2026-07-12): regression_roundtrip y test_parser_robustness se reportaron en rojo tras la fase P1. Causa raíz: invocación sin argumentos (exit 2 imprimiendo el uso), no regresión — con los ficheros oro correctos (examples/exp1..exp4.inp.5), suite completa en verde. Corregido en el CLAUDE.md del INP configurator: comandos con ficheros explícitos + nota de que exit 2 sin argumentos no es fallo de tests. Lección: "exit ≠ 0" no se interpreta sin leer la salida.
- **Control MURR — pipeline (P4)** ✅ (2026-07-13): barrido espectral de 1 sim con MURR-G1 (CONDERC): COLL.inp generado con NGROUP=-112/IESF=5/CX en MeV correctos, pipeline collaps→copy→acab→check_flux OK, y eco de COLLAPS con REAL TOTAL FLUX = 1.4634e14 = Σ DATA del fichero → cadena completa verificada sin pérdidas.
- **Control MURR — física** ✅ (2026-07-13): A_pico(G1 medido)/A_pico(analítico) = 0.6386; cociente de σ_eff ¹³⁰Te(n,γ)→Te131 entre los dos XSECTION.dat = 0.6385 → diferencia atribuida al 100% a la forma espectral (coincidencia a 4 cifras). Canal Te131m: 0.660, consistente (peso 22:1 a favor del fundamental). E̅ analítico = 0.627 eV (espectro de 3 grupos, muy térmico) vs E̅ G1 medido = 0.1438 MeV. Conclusión: pipeline y barrido espectral VALIDADOS con datos independientes del OIEA; la diferencia analítico↔G1 es física de posición/representación, no error de la herramienta.
- **Optimización vs `frac_termica` (P5)** ✅ (2026-07-13): verificado en el Fort Analyzer que `paramKeys` (`static/js/optim_utils.js`) selecciona claves de `params` genéricamente por tipo (`number` finito), sin lista hardcodeada de nombres — `frac_termica` es seleccionable como eje X sin cambios y la clave categórica `espectro` (string) se descarta sola, sin crash ni ruido en el selector ni en la tabla. No hizo falta código nuevo. Detalle cosmético anotado (no corregido, fuera del alcance de P5): falta la traducción `optim.type_spectrum` en `es.json`/`en.json` del analyzer — el badge de subtítulo del barrido espectral mostraría la clave cruda.
- **Barrido espectral de 9 reactores (experimento central)** ✅ (2026-07-13): φ_ref idéntico, 9 espectros CONDERC. A_pico(¹³¹I) crece monótonamente con la fracción térmica (×37 entre Cf252 y HFIR-VXF3: 3.38e2 → 1.255e4 Bq/cm³). Excepción explicada: Phénix (0.03% térmico, 96.9% epitérmico) produce 3.32e3 vía resonancias del ¹³⁰Te — evidencia del canal de integral de resonancia. t_pico varía 3.50–4.50 h con el espectro (mezcla Te131/Te131m dependiente de la forma). Pureza 100% en todos (esperado: pulso de 10 s).
- **Runbook barrido espectral** ✅ P0–P5 completadas.
- **Control P(t) — pureza como serie temporal (F1)** ✅ (2026-07-15): sobre la ref_sim (pulso 10 s), verificado A MANO el bloque SHUTDOWN del fort.6: A(I131)=4.017e+1 Bq/cm³ y Σ(impurezas de yodo: I128/129/130/130M/132/132M/133)=9.028e-5 → P(t=0)=99.99978 % > 99.9 % ⇒ t_cruce=0, coincide con la gráfica(t_cruce=0.0000 h, A=4.0170e+1, 0.2 % del pico). Caso borde t_cruce=0 verificado a mano; el cruce a t>0 queda cubierto por los tests oro de calcular_pureza_serie. Nota física: en este pulso A(I131) CRECE en el enfriamiento (precursor Te131) hasta 1.7230e+4 en t_pico=3.753 h — la "ventana de administración" en pulsos cortos se lee por el crecimiento del I131, no por la subida de P(t) (misma familia que F5).
- **Referencia canónica de caso** (2026-07-22): `simulaciones/simulaciones 1er Exp/Simulacion v.5 - info thesis` (pulso 10 s, blanco 0,1231 g TeO2; su fort.6 es el fixture congelado del analyzer). Toda firma de caso se calcula sobre ella. El fort.6 "v.7 - DECAY" de las verificaciones originales de F1 queda documentado como variante del mismo pulso con XSECTION distinto (I127/I129 ~15-20× mayores — el cociente I129/I131 es huella espectral del cociente de capturas Te-128/Te-130).
- **Control P(t) re-anclado a v.5**: a mano en SHUTDOWN: A(I131)=3.842E+01,  Σ(yodos impuros)=5.035E-05 → P(0)=99,99987 % > 99,9 % ⇒ t_cruce=0. A_pico=1.6500E+04 (0,23 % al apagar). Pendiente: cotejar t_cruce/A en la UI cargando v.5 (un minuto).
- **Control A_esp (F2/F2b) ✅**: a mano desde la tabla de átomos de v.5: I131=3.841E+07, I129=6.387E+05, I127=1.531E+05 át/cm³ → masa yodo=8.5245E-15g/cm³ (I131 = 98,0 % másico) → A_esp(0)=4.5070E+09 MBq/g; el código da 4.5055E+09 (dif. <0,05 %, redondeo de λ). Techo físico 4.596E+09 respetado. El diseño F2b (estables desde átomos) es imprescindible en irradiaciones largas aunque en v.5 su impacto sea <0,5 %.
- **Control B1 — espectro gamma (línea de 364 keV)** ✅ (2026-07-22): sobre la referencia v.5 en t = 3.750 h (instante del pico): tasa esperada a mano = A_pico(I131) × I(364,49 keV) = 1.6500E+04 × 0.812 = 1.340E+04 fot/s·cm³. La pestaña Espectro gamma reporta: 364.49 keV / I131 / 81.200 % / 1.340e+4 — coincidencia exacta. La vista lista además 11 nucleidos del inventario sin líneas gamma en PHOTON.dat (I130M entre ellos), conforme al diseño. Observación física: en t_pico las líneas de TE131/TE131M siguen presentes (precursores activos alimentando el pico), coherente con la cinética de Bateman del caso pulso.
- **Recuento de suite** ✅ (2026-07-22): 661 tests automáticos en verde, 0 fallos, vía `acab_suite\tools\run_all_tests.ps1` (analyzer 438, inp-conf 198, collaps 25) + `regression_roundtrip.py` (OK, sin recuento numérico).
