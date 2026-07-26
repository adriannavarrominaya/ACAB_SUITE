# CONTEXTO MAESTRO — Suite ACAB (TFG producción de ¹³¹I)

Documento de traspaso para conversaciones nuevas con Claude. Resume qué es el
proyecto, qué se ha construido y validado, y dónde está cada cosa. Escrito el
2026-07-13; el estado vivo está en `acab_suite/README.md` (tablón) y
`acab_suite/BACKLOG.md`.

## El proyecto

TFG de ingeniería: **optimización de la producción de ¹³¹I** (radiofármaco) por
irradiación neutrónica de TeO₂ — cadena ¹³⁰Te(n,γ)¹³¹Te/¹³¹ᵐTe → β⁻ → ¹³¹I —
usando el código de activación **ACAB 2008 (UPM)** y su utilidad **COLLAPS**
(colapsado de secciones eficaces con un espectro). Caso de referencia: reactor
MURR (Univ. Missouri), validado contra medidas experimentales.

Los códigos son FORTRAN de 2008: entrada por ficheros de formato rígido
(`inp.5` para ACAB, 14 bloques; `COLL.inp` para COLLAPS, 9 tarjetas), salida en
ficheros de texto (`fort.6` de ACAB; `XSECTION.dat`, `FLUX.inf` de COLLAPS).
Editarlos a mano es lento y propenso a errores silenciosos.

## La suite construida

Tres aplicaciones web Flask locales (monousuario, 127.0.0.1) + una carpeta
transversal, en un monorepo:

| Componente | Función | Puerto |
|---|---|---|
| ACAB_inp_file_configurator | Editar/validar/generar `inp.5` y ficheros CHAINS; pestaña "Barrido" (4 tipos); ejecución de ACAB | 5000 |
| ACAB_fort_file_analyzer | Analizar `fort.6` (multi-simulación): gráficas, informes por isótopo, unidades físicas, métricas, pestaña "Optimización" | 5001 |
| COLLAPS_inp_file_configurator | Editar/validar/generar `COLL.inp`; ejecución de COLLAPS | 5002 |
| acab_suite/ | Launcher, config común, runbooks, tablón, backlog | — |

Flujo de trabajo cerrado: espectro (COLLAPS) → `XSECTION.dat` → `inp.5` →
ejecutar ACAB → `fort.6` → análisis, todo desde las interfaces (botones
Ejecutar con log en vivo, pipelines y deep links entre apps).

## Capacidades principales (en orden de construcción)

1. **Validación de entrada**: ~25 validaciones cruzadas (V01–V25) en el
   configurador de inp.5; equivalentes en COLLAPS. Composición asistida
   (masa+compuesto+volumen → densidades atómicas).
2. **Suites de tests oro** en los tres componentes (scripts autocontenidos,
   fixtures reales congelados con valores verificados a mano; ~200 tests).
3. **Analyzer científico**: unidades físicas (Bq/cm³ → MBq/g leyendo la
   densidad del propio fort.6; actividad total), exportación CSV, superposición
   de datos experimentales con métricas de desviación, métricas de optimización
   (curva de saturación teórica, rendimiento, pureza radionucleídica — criterio
   validado: impurezas = otros isótopos de yodo, umbral 99.9 %),
   i18n es/en, detección de resultados obsoletos (inp.5 más nuevo que fort.6).
4. **Barridos paramétricos** (pestaña del INP configurator): genera N carpetas
   de simulación autocontenidas a partir de un caso base + manifest de
   trazabilidad (`sweep_manifest.json/csv`). Cuatro tipos: flujo (XNORM), masa
   del blanco, historial temporal, y **espectral** (forma del espectro vía
   COLL.inp, importando espectros CONDERC del OIEA con índices espectrales).
5. **Ejecución integrada**: runner con cola; el barrido espectral ejecuta un
   pipeline por simulación (COLLAPS → copiar XSECTION.dat → ACAB → verificación
   de FLUX.inf). Resultados de ejecución trazados en `batch_results.json`.
6. **Pestaña Optimización** (analyzer): lee el manifest y grafica
   A_pico/t_pico/pureza/rendimiento frente al parámetro barrido.

## Validaciones científicas realizadas (con firma numérica)

- **Validación experimental**: las curvas ACAB reproducen las medidas del
  experimento de referencia (comparación tipo Fig. 6 del paper del grupo).
- **Control XNORM**: barrido de flujo ×0.5 → actividad ×0.4999 (linealidad).
- **Control de malla**: generador manual y barrido temporal producen inp.5
  byte-idénticos (comparten función pura y writer).
- **Invariancia de escala del colapso**: FT×10 → XSECTION.dat idéntico (solo la
  FORMA del espectro importa; comparaciones entre reactores a flujo total igual
  por construcción).
- **Control MURR** (validación del barrido espectral con datos independientes):
  espectro medido MURR-G1 (CONDERC/OIEA, 112 g) vs espectro analítico del
  grupo: cociente de producción 0.6386 = cociente de σ_eff ¹³⁰Te(n,γ) 0.6385
  (coincidencia a 4 cifras) → diferencia atribuida al 100 % a la forma
  espectral.
- **Experimento central**: barrido de 9 espectros de reactor (CONDERC) a flujo
  total idéntico → la producción de ¹³¹I crece monótonamente con la fracción
  térmica (×37 entre ²⁵²Cf puro y HFIR-VXF3), con Phénix como excepción
  explicada (96.9 % epitérmico → canal de resonancias del ¹³⁰Te).

## Sistema documental del proyecto

- `acab_suite/RUNBOOK_*.md` — planes de trabajo por mejora (fases, decisiones
  de diseño cerradas, criterios de aceptación, prompts para Claude Code).
  Cabecera con estado. Siete runbooks; todos completados salvo las fases del
  espectro gamma bloqueadas por un fichero externo (PHOTON.dat).
- `acab_suite/README.md` — **tablón**: estado de runbooks + verificaciones de
  control anotadas con fecha y valores + sección "Invocación de los códigos"
  (fuente de verdad de cómo se ejecutan ACAB/COLLAPS: exes autocontenidos en
  cada carpeta de simulación, sin argumentos, todo por cwd).
- `acab_suite/BACKLOG.md` — pendientes no planificados con prioridad/esfuerzo.
- `CLAUDE.md` por componente + uno en la raíz — convenciones para sesiones de
  Claude Code (comandos de test exactos, invariantes de dominio, fragmentos
  duplicados sincronizados entre componentes).
- READMEs por componente — documentación funcional detallada.
- Metodología de trabajo: cada mejora = runbook → sesiones de Claude Code por
  fase → suite de tests en verde antes y después → verificaciones humanas
  anotadas en el tablón.

## Glosario mínimo

ACAB (código de activación; resuelve inventario isotópico bajo irradiación) ·
COLLAPS (colapsa la librería fina de 211 grupos con un espectro → XSECTION.dat
de secciones eficaces efectivas) · inp.5 (entrada ACAB; Bloque #3 = flujo total,
Bloque #9 XNORM = factor de escala del flujo) · COLL.inp (entrada COLLAPS;
tarjeta 7 = espectro FT; NGROUP con signo = orden de energías; IESF=5+CX =
estructura arbitraria de fronteras) · fort.6 (salida ACAB: átomos y actividades
por isótopo y tiempo; secciones CONCENTRATIONS(GRAM) y RESTART) · FLUX.inf
(eco de COLLAPS: flujo total real y espectro transcrito a 211 grupos) · CONDERC
(base de espectros de reactor del OIEA, https://nds.iaea.org/conderc/spectra) ·
fracción térmica (flujo con E<0.625 eV; predictor principal de la producción).
