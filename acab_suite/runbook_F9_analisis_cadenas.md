# Runbook F9 — Análisis de contribución por cadenas (ACAB + CHAINS)

**Estado (2026-07-26): Fases 0-5 ✅ (inp-conf + analyzer). Runbook completo.**
Estado global de runbooks en README.md de `acab_suite/`.

Ítem F9 del BACKLOG (inp-conf + analyzer, A/L). Objetivo: para un caso de
referencia y un isótopo objetivo IFINAL, cuantificar la contribución de cada
isótopo inicial del blanco (R_i) y de cada cadena de reacción dentro de él
(Y_z_i = R_i · X_z_i), con visualización de la cadena seleccionada.

Tamaño L: ejecutar en 2-3 sesiones de Claude Code (Fases 0-1 / 2-3 / 4-5),
cada una con su baseline y cierre de suite en verde.

## Decisiones de diseño (fijadas — no improvisar)

- **Arquitectura**: nueva sección "Análisis de cadenas" en el inp-conf
  (configuración + orquestación, como el barrido espectral orquesta
  COLLAPS+ACAB) y pestaña nueva en el analyzer (resultados). Se construye
  sobre la fontanería de barridos: carpetas autocontenidas, cola/registro
  de ejecución, exclusiones de C4, detección de obsoletos — pero con
  manifest PROPIO (`chains_manifest.json`), no es un sweep_manifest.
- **Fuente del inventario isotópico inicial**: la sección INITIAL
  CONCENTRATIONS del `fort.6` de referencia. Motivo (manual, Block #5): el
  inp.5 admite ELEMENTOS (ELEMID=10000·Z) que ACAB expande a isótopos con
  abundancias naturales de la librería — el desglose por isótopos solo
  existe en el eco del fort.6.
- **inp.5 monoisotópico**: patch del Bloque #5 → INUCL = ZZAAAS del isótopo
  i, XCOMP = C_i copiado DIRECTAMENTE del eco (sin viaje por masa). Todo lo
  demás byte-idéntico a la referencia (XSECTION, historial, XNORM,
  NOTTS/ITSO). La coherencia de unidades se confirma empíricamente en
  Fase 0 y queda de red el control Σ R_i ≈ 1.
- **Tapes (una sola pareja por análisis, con la composición de referencia)**:
  run A: Bloque #11 con IWP=3 → escribe fort.22 (pathway analysis). Run B:
  IMTX=1 → escribe fort.24 y ACAB SE DETIENE tras escribirlo (run barato;
  no esperar fort.6 de él). Los `inp.5_tape22`/`inp.5_tape24` que ya
  funcionan a mano se congelan como plantillas; el delta exacto contra el
  original se confirma por diff en Fase 0.
- **CHAINS**: `chains.exe < input_chain.txt > output_chain.txt`, con
  fort.22 y fort.24 presentes en cwd. ROMPE la convención del runner (exe
  sin argumentos): la extensión con redirección stdin/stdout se documenta
  en la sección "Invocación de los códigos" del README (fuente de verdad).
  input_chain: IFLAG=2, IINICIAL (ZZAAAS de i), IFINAL (ZZAAAS, isómeros
  soportados: S=1), NMAX, PCNT.
- **Parámetros de usuario**: selección de N isótopos del inventario inicial
  (lista con C_i), IFINAL, PCNT (defecto 0.01), NMAX (defecto 5).
- **Códec ZZAAAS**: reutilizar el del parser de DECAY.dat, en sentido
  inverso (nombre → código). No escribir uno nuevo.
- **R_i = A_i(IFINAL,t*) / A_ref(IFINAL,t*)** evaluado en un instante t*
  común: defecto t_pico de la referencia, selector de instante como en la
  pestaña de espectro gamma. (R_i(t) como serie: fuera de alcance v1.)
- **Control de linealidad integrado**: fila Σ R_i en la tabla. Bateman es
  lineal en las concentraciones iniciales (misma matriz de transición en
  los N runs) ⇒ Σ R_i ≈ 1 si se seleccionan TODOS los isótopos iniciales;
  con selección parcial, la fila indica "cobertura" y lo dice en una nota.
- **X_z_i**: del output de CHAINS. OJO normalización: PTOT=100 renormaliza
  entre las cadenas que superan PCNT ⇒ Σ_z Y_z_i < R_i por la cola
  descartada. Se documenta en la UI (nota al pie), no se "corrige".
- **Tablas**: (1) |Isótopo i|C_i|A_i|A_ref|R_i| + fila Σ; (2) |Cadena z de
  i|X_z_i|R_i|Y_z_i| ordenada por Y descendente. Ambas exportables a CSV.
- **Diagrama v1**: la cadena SELECCIONADA como secuencia lineal — nodos con
  nombre y T½ (de DECAY.dat, ya parseado), aristas etiquetadas con el
  proceso ((N,G-g), (B-), (IT)…) y su XSEC/DELTA del output de CHAINS.
  El grafo fusionado estilo Fig. 1 del paper: iteración futura (F9b),
  fuera de alcance.
- **Fuera de alcance v1**: R_i(t) como serie, grafo fusionado, varios
  IFINAL simultáneos, casos pulsados (NOPUL>0).

## Fase 0 — Baseline y confirmaciones empíricas (sin escribir feature)

- Suite completa (run_all_tests.ps1) en verde.
- Diff `inp.5_original` vs `inp.5_tape22` y `inp.5_tape24` del caso manual
  que ya funciona: confirmar que los deltas son exactamente IWP 0→3 e
  IMTX 0→1 (o documentar qué más cambia). Congelar los tres como fixtures
  con PROCEDENCIA.md.
- Verificación de unidades: en el fort.6 de referencia, Σ(C_i de isótopos
  de Te del eco INITIAL CONCENTRATIONS) debe reproducir el XCOMP elemental
  del Te en el Bloque #5 del inp.5 de referencia. Anotar el resultado.
- Smoke test manual de la cadena completa de invocación con los ficheros
  del usuario (ya hecho a mano una vez — repetir limpio y anotar).

## Fase 1 — Parsers y códec (analyzer)

- Parser del output de CHAINS: cadenas, P por cadena, pasos con proceso y
  XSEC/DELTA, PTOT, NCHAIN/NCH. Caso oro: `output_chain_Te130_to_I131.txt`
  congelado VERBATIM (3 cadenas; P = 95.79 / 3.119 / 1.090; dominante
  TE130(N,G-g)→TE131(B-)→I131; XSEC=1.1084E-11 y DELTA=4.6210E-04 del
  primer paso, verificados a mano).
- Lector de INITIAL CONCENTRATIONS del fort.6 (isótopo → C_i). Si inp-conf
  también lo necesita para la UI de selección (lo necesita), decidir según
  la convención existente de fragmentos sincronizados entre repos, y
  documentar la decisión.
- Códec ZZAAAS inverso (nombre→código) con isómeros (TE131M→521311).
  Tests contra el códec directo existente (ida y vuelta identidad).

## Fase 2 — Configuración y generación (inp-conf)

- Sección nueva: elegir carpeta de referencia (browse de U2) → leer fort.6
  → lista de isótopos iniciales con C_i (checkboxes) + IFINAL + PCNT +
  NMAX → previsualizar → generar.
- Estructura generada: carpeta del análisis con subcarpetas por run
  (tape22/, tape24/, iso_<nombre>/ × N, chains_<nombre>/ × N),
  `chains_manifest.json` (referencia, parámetros, isótopos, estado por
  run, ficheros excluidos — patrón C4).
- Escritura: inp.5 monoisotópicos (patch Bloque #5) y de tapes (patch
  Bloque #11) con EL MISMO writer de siempre; tests de bytes contra casos
  oro construidos a mano.

## Fase 3 — Orquestación de ejecución (inp-conf)

- Pipeline: tape22 → tape24 → copiar fort.22/24 a las carpetas chains_* →
  N runs ACAB → N runs CHAINS (redirección). Estados por run en el
  manifest; log en vivo como los barridos.
- Manejar la parada temprana del run IMTX=1 (éxito sin fort.6 = éxito).
- README "Invocación de los códigos": añadir el caso CHAINS.
- Tests de endpoint con ejecutables falsos (patrón D1) incluyendo un
  chains.exe falso que lea stdin y escriba stdout.

## Fase 4 — Análisis y tablas (analyzer)

- Pestaña nueva: cargar carpeta de análisis (chains_manifest) → tabla 1
  con fila Σ y nota de cobertura → tabla 2 ordenada por Y → selector de
  instante t* (defecto t_pico de la referencia) → exports CSV.
- Tests oro sobre un análisis sintético mínimo (2 isótopos, manifests y
  fort.6/output_chain de fixture) con R, Σ, X, Y verificados a mano.

## Fase 5 — Diagrama, i18n y cierre

- Diagrama lineal de la cadena seleccionada (nodos+T½, aristas+proceso).
- i18n completa (es/en) de TODO lo nuevo en ambas apps; docs de usuario de
  ambas apps; BACKLOG F9 ✅; recuento de suite refrescado en el tablón.

## Verificación humana (tablón)

1. **Control de linealidad Σ R_i**: análisis real sobre la referencia con
   TODOS los isótopos iniciales seleccionados → anotar Σ R_i con su firma
   numérica (esperado ≈ 1; desviación = numérica + cola PCNT).
2. **Control CHAINS**: la pestaña reproduce el caso manual Te130→I131:
   3 cadenas con P = 95.79 / 3.12 / 1.09 %, dominante la de la Fig. 1 del
   paper (Te130(n,γ)Te131(β⁻)I131).
3. Cotejo cualitativo del diagrama de la cadena dominante contra la Fig. 1
   (T½: Te131 25 min, Te131m 33.25 h, I131 8.025 d).

## Valor para la memoria

Cierra el salto de "cuánto se produce" a "POR QUÉ se produce": el índice
Y_z_i jerarquiza las reacciones nucleares por su importancia real en la
producción de ¹³¹I. Conexiones directas: cuantifica el peso de la vía
Te131m (isómero) frente a la directa; y ejecutado sobre un caso de espectro
duro, puede poner números a la explicación de Phénix (capturas resonantes)
que hoy es cualitativa. El control Σ R_i ≈ 1 es además la demostración
elegante de la linealidad de Bateman — séptimo control con firma numérica
candidato a la Tabla N-2.
