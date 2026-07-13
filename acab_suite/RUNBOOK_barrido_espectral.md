# Runbook — Barrido espectral (tipo 4) + Runner v3 (pipelines)

**Estado: pendiente.** Estado global de runbooks en README.md de esta carpeta.

**Objetivo:** cuarto tipo de barrido en la pestaña "Barrido" del INP configurator:
variar la FORMA del espectro neutrónico (tarjeta 7 / FT del COLL.inp) importando
espectros externos (formato CONDERC del OIEA, https://nds.iaea.org/conderc/spectra),
con pipeline de ejecución por simulación: COLLAPS → copiar XSECTION.dat → ACAB.
Pregunta científica: ¿en qué tipo de reactor es más eficaz la producción de ¹³¹I
a igualdad de densidad de flujo total?

**Repos:** `ACAB_inp_file_configurator` (principal), `COLLAPS_inp_file_configurator`
(sincronización de runner.py y del writer), `ACAB_fort_file_analyzer` (sin cambios
salvo verificación en Optimización).

---

## Decisiones de diseño CERRADAS (no re-debatir; derivan de la conversación de diseño)

- **D1 — inp.5 intacto.** Bloque #3 = un único valor (densidad de flujo total,
  verificado en el caso de referencia: 6.5E+13). El barrido espectral NO parchea el
  inp.5, salvo un único caso: si el usuario edita φ_ref en la pestaña (prefijado con
  el Bloque #3 del fichero base), se aplica ese MISMO valor a todas las sims (patch
  uniforme block3). XNORM no se toca (reservado al barrido de flujo; permite
  combinar espectro × flujo en el futuro).
- **D2 — Comparación a flujo igual POR CONSTRUCCIÓN.** El colapso es media
  ponderada (la magnitud de FT se cancela); con Bloque #3 idéntico en todas las
  sims, la comparación entre reactores es "a igualdad de flujo total" sin
  normalización numérica alguna. La normalización de FT a suma 1 es OPCIONAL y solo
  cosmética (comparabilidad visual de la gráfica de espectros).
- **D3 — FLUX.inf es verificador, nunca fuente.** Tras cada run de COLLAPS, el
  pipeline parsea de FLUX.inf: REAL TOTAL FLUX, AVERAGE ENERGY y el eco de
  parámetros (ILIB/IESF/NGROUP), y los anota en batch_results/manifest. No se copia
  ningún valor de FLUX.inf a ningún fichero de entrada.
- **D4 — Import = transcripción, sin rebinning.** La conversión de estructuras la hace COLLAPS (IESF=5 + CX). Del fichero CONDERC: NGROUP = ±N (signo AUTODETECTADO de la monotonía de las fronteras y mostrado en la UI), CX = N+1 fronteras (columna UPPER + última LOWER), FT = columna DATA en el orden del fichero.
  ⚠ Unidades de CX: P0.2 verificado: CX en MeV; CONDERC en eV → el import convierte las fronteras ×10⁻⁶ (los FT no se convierten: son flujos integrales por grupo, adimensionales respecto a la unidad de energía). Es la ÚNICA transformación. 
  Los espectros medidos (origen EXFOR) pueden cubrir solo un rango parcial de energía; para la comparación entre reactores solo valen espectros de rango completo — criterio operativo: la frontera inferior del fichero debe alcanzar la región térmica. La fracción térmica 0.0% en un reactor térmico es el síntoma.
  2b. Columna "Rango de energía" (E_min – E_max del fichero) en la tabla de espectros de la pestaña, junto al nº de grupos — hace visible de un vistazo el criterio de rango completo (un E_min en keV delata un espectro parcial tipo EXFOR sin necesidad de interpretar la fracción térmica).
- **D5 — Aviso direccional.** Si |N| < 211 (grupos de la librería XSBL, constante
  de configuración), badge de aviso en la fila: "espectro menos especificado que la
  librería: la expansión de grupos es la operación menos fiable". Informa, no
  bloquea (el propio MURR-G1 de CONDERC, 112 grupos, lo llevará).
- **D6 — Convención de carpetas.** La carpeta base del barrido incluye una
  subcarpeta `collaps/` (collaps.exe, XSBL.dat y un COLL.inp de partida); la copia
  recursiva existente la propaga a cada sim. El COLL.inp parcheado de cada sim se
  escribe en `<sim>/collaps/COLL.inp` (reemplaza al copiado, misma precedencia que
  el inp.5 generado).
- **D7 — Pipeline por simulación (runner v3).** Job = lista de pasos:
  1) run `collaps.exe` con cwd=`<sim>/collaps`; 2) copy `<sim>/collaps/XSECTION.dat`
  → `<sim>/XSECTION.dat`; 3) run `acab.exe` con cwd=`<sim>`; 4) check: parsear
  `<sim>/collaps/FLUX.inf` (D3). Fallo en cualquier paso ⇒ sim 'failed' (con el
  paso culpable registrado) y la cola CONTINÚA. Los barridos tipo 1-3 siguen siendo
  jobs de un solo paso (compatibilidad total).
- **D8 — Índices espectrales al importar** (funciones puras, con test): fracción
  térmica (E < 0.625 eV), epitérmica (0.625 eV – 0.1 MeV) y rápida (> 0.1 MeV),
  calculadas de la columna DATA con reparto plano-por-letargia en el grupo que
  contiene la frontera. Van al manifest como params numéricos ⇒ la pestaña
  Optimización puede graficar A_pico vs fracción térmica sin cambios.
- **D9 — Writer de COLL.inp en el INP configurator.** El barrido necesita escribir
  COLL.inp desde el repo del INP configurator: crear `coll_writer.py` como copia
  sincronizada del writer del repo COLLAPS (mismo tratamiento que runner.py:
  comentario de cabecera "común de la suite"), limitado a lo necesario (NGROUP/FF,
  CX en 6E12.5, FT en 6E12.5, resto de tarjetas conservadas del COLL.inp base).
  Test oro: round-trip contra un COLL.inp fixture real (el de 211 grupos).

## Formato CONDERC (clavado con el fixture 112_MURR-G1.txt)

Cabecera `GROUP  UPPER  LOWER  LETHARGY  DATA  DATA/LETHARGY`; una fila por grupo;
energías en eV, orden DECRECIENTE en los ficheros vistos (pero autodetectar);
DATA = flujo integral por grupo; línea final `TOTAL <valor>` con Σ(DATA) — usar
como CHECKSUM del parser (tolerancia relativa 1e-3; si no cuadra, rechazar con
mensaje). Ceros en grupos extremos: válidos, se conservan. Guardar el fixture en
`tests/fixtures/spectra/112_MURR-G1.txt`.

---

## Fase P0 — Verificaciones humanas PREVIAS (no delegar)

1. **Control de invariancia de escala:** ejecutar COLLAPS dos veces con la misma
   forma, la segunda con FT×10 → XSECTION.dat idéntico (REAL TOTAL FLUX ×10 en
   FLUX.inf, secciones inalteradas). Confirma empíricamente D2. Anotar en el tablón.
2. **Unidades de CX:** confirmar en docs/COLLAPS.md (eV vs MeV) y anotarlo en este
   runbook antes de la Fase P2.
3. Descargar 3-4 espectros CONDERC de tipos distintos (p. ej. MURR-G1, TRIGA,
   HFIR, EBR-2 o Phénix) a una carpeta local; verificar de un vistazo que todos
   siguen el mismo formato de tabla.

## Fase P1 — Runner v3: jobs de pasos (ambos configuradores)

1. En `runner.py`: `start_batch` acepta jobs como lista de pasos
   `[{type:'run', cmd, cwd} | {type:'copy', src, dst} | {type:'check_flux', path}]`.
   Un job con `cmd` simple se normaliza a un paso 'run' (compatibilidad). `status()`
   de batch añade por job: `step_index`, `step_type`, y por sim terminada la lista
   de pasos con su resultado. `check_flux` parsea FLUX.inf (REAL TOTAL, AVERAGE
   ENERGY, eco ILIB/IESF/NGROUP) y lo adjunta al resultado del job (no falla el job
   si el parseo falla: warning).
2. Sincronizar la copia de runner.py en el repo COLLAPS (idénticos salvo constantes).
3. Tests (`tools/test_runner.py`, ampliar): pipeline de 3 pasos con ejecutable
   falso; fallo en paso 2 → job 'failed' con step_index=1 y el job siguiente se
   ejecuta; copy con src inexistente → fallo limpio; compatibilidad de jobs simples.

**Criterios:** suites de ambos configuradores en verde; los barridos tipo 1-3 y la
ejecución individual funcionan EXACTAMENTE igual que antes (regresión manual breve).

## Fase P2 — Import CONDERC + writer (INP configurator)

1. `static/js/conderc_import.js` (puro, patrón calc_utils):
   `parseConderc(text)` → `{n, boundaries_eV[n+1], data[n], total, orden}` con
   checksum contra TOTAL; `spectralIndices(boundaries, data)` → fracciones
   térmica/epitérmica/rápida (D8); `buildSpectrumPatch(parsed, collBase)` → datos
   para la tarjeta: ngroup con signo, cx (unidades según P0.2), ft.
   Tests node (`tools/test_conderc_import.js`) con el fixture MURR-G1: n=112,
   orden decreciente, checksum OK, fracción térmica del MURR ≈ valor calculado a
   mano una vez y congelado como oro; casos de error (TOTAL descuadrado, columnas
   truncadas).
2. `coll_writer.py` (D9) + `tools/test_coll_writer.py` con round-trip sobre el
   fixture COLL.inp de 211 grupos y sobre uno generado con IESF=5+CX.
3. Extender `/api/sweep` para que cada sim pueda llevar, además del patch de inp.5,
   un `coll_patch` (ngroup, cx, ft) que se escribe vía coll_writer sobre el
   COLL.inp base de `base_folder/collaps/` → `<sim>/collaps/COLL.inp`, con
   verificación round-trip. 422 claro si base_folder no contiene `collaps/COLL.inp`
   y el barrido es espectral. Test en `tools/test_sweep_endpoint.py`.

## Fase P3 — UI del cuarto tipo (pestaña Barrido)

1. Cuarta tarjeta "Espectro (COLLAPS)". Texto explicativo fijo (i18n): qué hace,
   que la comparación es a flujo total igual (D1/D2), y el papel de FLUX.inf (D3).
2. Campo φ_ref prefijado con el Bloque #3 del fichero base (editable; si se edita,
   patch uniforme). Constante de librería (211) visible.
3. Filas del barrido: botón "añadir espectro" → file input (.txt/.csv) → por fila:
   etiqueta (prefijada del nombre del fichero, p. ej. "MURR-G1"; el sufijo de
   carpeta se propone de ella), nº de grupos, orden detectado (⚠ confirmar
   visualmente), checksum OK/KO, fracción térmica, y badge direccional si |N|<211.
4. Gráfica Plotly superpuesta de los espectros cargados (log-log, DATA/LETHARGY vs
   energía), normalizada a suma 1 para comparabilidad visual (D2, cosmética).
5. Manifest: `params` por sim = `{espectro: label, n_grupos, frac_termica,
   frac_epitermica, frac_rapida}`; `fixed_params` añade φ_ref y librería (211).
6. i18n completo; validación y previsualización como en los tipos existentes.

## Fase P4 — Ejecución del barrido espectral

1. El batch del barrido espectral construye por sim el pipeline D7 (los exes van en
   las carpetas por la convención autocontenida; `cmd` por paso con cwd correcto).
2. `batch_results.json` incluye por sim los pasos y el resumen del check de
   FLUX.inf (REAL TOTAL, AVERAGE ENERGY).
3. UI de progreso: la fila muestra el paso en curso ("collaps / copiar / acab").
4. Tests: pipeline batch con ejecutables falsos que crean los ficheros esperados
   (falso collaps crea XSECTION.dat y FLUX.inf de juguete; falso acab exige que
   XSECTION.dat exista en su cwd y crea fort.6) — verifica el encadenado real.

## Fase P5 — Documentación y verificación en Optimización

1. README del INP configurator: sección del barrido espectral (D1-D8 en versión
   usuario, formato CONDERC, enlace a la fuente del OIEA). Los espectros medidos (origen EXFOR) pueden cubrir solo un rango parcial de energía; para la comparación entre reactores solo valen espectros de rango completo — criterio operativo: la frontera inferior del fichero debe alcanzar la región térmica. La fracción térmica 0.0% en un reactor térmico es el síntoma
2. Verificar (sin código nuevo previsto) que la pestaña Optimización del analyzer
   grafica A_pico vs `frac_termica` con un barrido espectral real; ajustar solo si
   los params categóricos (label) molestan.
3. Tablón y CLAUDE.md de los repos tocados actualizados.

---

## Controles humanos FINALES (validación científica; anotar en el tablón)

1. **Round-trip de identidad:** exportar el FT actual (211 grupos) a un fichero con
   formato CONDERC de juguete, importarlo por la pestaña → COLL.inp equivalente al
   original (NGROUP/FT idénticos).
2. **Control MURR:** barrido de un solo espectro = MURR-G1 de CONDERC (112 grupos,
   medido) vs el caso base con vuestro MURR analítico de 211 → producción de ¹³¹I
   comparable (anotar la desviación; es LA validación del barrido espectral con
   datos independientes del OIEA, y figura directa para la memoria).
3. **El barrido de la memoria:** MURR + TRIGA + HFIR + un rápido (EBR-2/Phénix)
   (+ ITER-DT si apetece el contraste extremo) a φ_ref idéntico → tabla y gráfica
   A_pico vs fracción térmica.
