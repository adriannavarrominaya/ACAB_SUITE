# BRIEF DE TAREA — Justificación de la suite en el ámbito del TFG

Usar junto con CONTEXTO_SUITE.md. Conversación destinada a producir texto para
la MEMORIA del TFG y material de DEFENSA, no código.

## Objetivo

Redactar la argumentación de por qué la suite de herramientas (acab_suite y las
tres aplicaciones) es una aportación relevante del TFG, más allá de "hice unas
webs": qué problema resuelve, qué garantías aporta al trabajo científico, y qué
capacidades nuevas habilita. Destinos posibles del texto: sección de metodología
de la memoria, sección de "herramientas desarrolladas", y guion de defensa ante
el tribunal.

## La línea argumental (desarrollar, no inventar otra)

1. **El problema de partida**: los códigos ACAB/COLLAPS (FORTRAN 2008) se
   alimentan de ficheros de formato rígido editados a mano. Errores de formato o
   de coherencia entre bloques producen fallos silenciosos o resultados
   inválidos; iterar (cambiar un parámetro → re-ejecutar → re-analizar) es lento
   y sin trazabilidad; comparar decenas de simulaciones a mano no escala.
2. **Lo que la suite aporta, en cuatro planos**:
   - *Corrección*: validación de entrada (V01–V25 y equivalentes) y round-trip
     parser↔writer testeado contra casos oro; ~200 tests automáticos.
   - *Trazabilidad y reproducibilidad*: manifests de barrido (qué parámetros
     tiene cada simulación), batch_results (qué se ejecutó, cuándo, con qué
     resultado), simulaciones autocontenidas (cada carpeta lleva su ejecutable
     y entradas), detección de resultados obsoletos.
   - *Capacidad científica nueva*: los barridos paramétricos convierten
     "optimización" de aspiración a método — el barrido espectral de 9
     reactores (experimento central) sería impracticable a mano (9× editar
     COLL.inp de cientos de valores + pipeline de 2 códigos + análisis
     comparado).
   - *Verificabilidad*: los controles con firma numérica (ver CONTEXTO,
     "Validaciones científicas") demuestran que la herramienta mide lo que dice
     medir — el control MURR (0.6385 ≈ 0.6386) es el ejemplo estrella.
3. **El cierre**: la suite no sustituye a ACAB (el motor físico validado) —
   elimina las fuentes de error humano alrededor de él y habilita el diseño de
   experiencias computacionales sistemáticas.

## Material citable (números reales, verificados en el tablón del proyecto)

- ~200 tests automáticos entre los tres componentes; 7 runbooks ejecutados.
- Control XNORM: 0.4999 vs 0.5 teórico. Control de malla: byte-idéntico.
- Control MURR: cociente producción 0.6386 = cociente σ_eff 0.6385.
- Barrido de 9 reactores: producción ×37 entre extremos; excepción Phénix
  explicada por el canal epitérmico (96.9 %).
- Validación experimental de las curvas ACAB (comparación tipo Fig. 6).

## Instrucciones de estilo y precaución

- Audiencia: tribunal de ingeniería. Tono sobrio; cada afirmación cuantitativa
  debe ser de la lista de arriba o del tablón — NO inventar métricas ni
  hinchar (p. ej. no llamar "plataforma" ni "framework" a tres apps Flask).
- Reconocer límites honestamente donde toque: apps locales monousuario, ACAB es
  el que calcula la física, la suite valida entradas y trazabilidad pero no
  sustituye el juicio del analista.
- No usar jerga de desarrollo (sprints, CI/CD) — traducir a lenguaje de
  metodología científica: verificación, reproducibilidad, trazabilidad.
- Pedir SIEMPRE la estructura antes de redactar en largo: proponer índice de la
  sección (p. ej. problema → arquitectura → verificación → capacidades →
  limitaciones) y validarlo con el autor antes de desarrollar.
- Entregables probables: sección de memoria (2-4 páginas), tabla resumen de
  controles de verificación, y 3-5 mensajes clave para la defensa oral.
