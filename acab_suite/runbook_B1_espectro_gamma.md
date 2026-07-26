# Runbook B1 — Espectro gamma de la muestra (PHOTON.dat)

Ítem B1 del BACKLOG (analyzer), desbloqueado: PHOTON.dat recibido y validado
(librería de líneas gamma discretas de ACAB; ¹³¹I verificado contra ENSDF:
364,5 keV al 81,2 %). Actualizar la línea B1 del backlog: quitar "bloqueado",
prioridad A, esfuerzo M, y anotar "PHOTON.dat recibido 2026-07-21, formato
validado".

## Decisiones de diseño (fijadas)

- **Formato del fichero**: bloques por nucleido. Cabecera: Z (entero),
  símbolo+A con sufijo M opcional para isómeros, número de líneas gamma.
  Después pares (E [MeV], intensidad [% por desintegración]), 3 pares por
  línea física, notación científica, finales de línea CRLF. El parser debe
  tolerar CRLF/LF.
- **Física**: tasa de emisión de una línea = A_nucleido(t) × I/100, en
  fotones/(s·cm³); conversión a fotones/(s·g) reutilizando la densidad del
  fort.6 como hace F1. Energías mostradas en keV (convención de
  espectrometría), aunque el fichero las dé en MeV.
- **Cruce de nombres**: los nombres del fort.6 y de PHOTON.dat comparten la
  convención de ACAB (I131, I132M, TE131M…). Verificarlo con un test que
  cruce el inventario del caso de referencia contra la librería; si algún
  nombre no casa, resolver caso a caso, sin tabla genérica de equivalencias.
- **Nucleidos sin entrada** en PHOTON.dat (emisores beta puros, estables):
  no aportan líneas; listarlos en un desplegable informativo ("sin líneas
  gamma en la librería"), nunca error.
- **Ubicación del fichero**: PHOTON.dat es dato de la distribución de ACAB,
  no de la app — ruta configurable con default junto a los datos de ACAB.
  Para los tests, congelar como fixture un EXTRACTO (bloques de I/Te/Xe de
  la cadena del problema), no el fichero completo de ~1,2 MB.
- **Vista (pestaña nueva "Espectro gamma")**:
  - Selector de instante t (mismos timesteps del fort.6 que usan las otras
    pestañas).
  - Espectro de palotes (stick plot): E [keV] vs tasa, eje y logarítmico,
    coloreado/hover por nucleido de origen.
  - Tabla de las N líneas principales: E, nucleido, intensidad, tasa —
    exportable a CSV como las demás tablas.
  - Filtro de rango de energía y umbral de tasa mínima (los ~cientos de
    líneas débiles de I-132/I-135 ensucian la vista si no).
- **Fuera de alcance**: respuesta de detector (resolución, eficiencia,
  Compton), atenuación en la muestra, espectro continuo beta/bremsstrahlung.
  Es el espectro de EMISIÓN, y así debe rotularse en la UI.

## Fase 1 — Parser de PHOTON.dat
Parser + modelo de datos (nucleido → lista de líneas). Tests oro sobre el
extracto congelado: nº de líneas por nucleido (I131=18, XE133=6), la línea
364,49 keV / 81,2 % del I131, y un isómero (TE131M) parseado como entrada
distinta de TE131.

## Fase 2 — Cálculo del espectro
Combinar inventario del fort.6 en t con la librería. Tests: caso de
referencia en enfriamiento tardío (muestra ≈ ¹³¹I puro) → la tasa de la
línea de 364 keV = A(¹³¹I) × 0,812, verificado A MANO una vez y congelado.
Caso con nucleido sin entrada en la librería → aparece en la lista
informativa, no rompe.

## Fase 3 — Pestaña de UI
Vista descrita arriba, i18n completa (es/en), verificación visual en
navegador real (¡esta vez sí!) con el caso de referencia en dos instantes:
uno temprano (líneas de Te-131/131m visibles) y uno tardío (dominado por
364 keV). Comprobar que el filtro de umbral limpia la vista con I-132.

## Fase 4 — Cierre
Docs, commits analyzer:/suite:, marcar B1 ✅. Verificación humana (tablón):
recálculo a mano de la tasa de la línea de 364 keV en un instante del caso
de referencia (A(¹³¹I) del fort.6 × 0,812) cotejado con la tabla de la
pestaña — firma numérica.

## Valor añadido
Cierra el círculo de la aplicación: la suite pasa de "cuánto ¹³¹I y cuándo"
a "qué verá el detector" — las líneas gamma son la firma con la que se
identifica el producto y sus impurezas en la práctica. Candidata a figura:
espectro de emisión del caso de referencia en t_pico, con la línea de
364 keV dominante y las líneas residuales de impurezas etiquetadas. Mensaje
de defensa adicional si hace falta: "el espectro de emisión calculado es
directamente contrastable con una medida de espectrometría gamma".
