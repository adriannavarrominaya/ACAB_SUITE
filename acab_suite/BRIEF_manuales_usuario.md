# BRIEF DE TAREA — Manuales de usuario de la suite

Usar junto con CONTEXTO_SUITE.md. Objetivo: documentación de USUARIO más allá de
los READMEs (que son funcionales pero orientados a quien ya conoce el proyecto).

## Audiencia y alcance

- **Audiencia**: futuros estudiantes/investigadores que continúen esta línea de
  trabajo con ACAB — saben física nuclear básica y qué es ACAB, NO conocen la
  suite ni tienen por qué saber programar. No son desarrolladores: nada de
  arquitectura interna, tests ni convenciones de código (eso ya vive en
  CLAUDE.md/READMEs).
- **Entregables** (decidir con el autor al empezar, propuesta por defecto):
  1. `docs/manual_usuario.md` en cada uno de los tres componentes (manual por
     aplicación, orientado a tareas).
  2. Una "Guía de inicio rápido de la suite" en `acab_suite/` (instalación con
     setup.ps1, arranque con el launcher, el flujo completo de un caso en 10
     pasos: espectro → COLL.inp → ejecutar COLLAPS → inp.5 → ejecutar ACAB →
     analizar).
  3. Opcional: versión Word/PDF para anexo de la memoria, generada a partir de
     los markdown.

## Principio rector: orientado a TAREAS, no a pantallas

Cada capítulo responde "cómo hago X", no "qué hay en la pestaña Y". Tareas
candidatas por aplicación (contrastar con el autor):

- **INP configurator**: crear un inp.5 desde cero / cargar y validar uno
  existente / usar la composición asistida (masa de TeO₂ → densidades) /
  generar el historial temporal / guardar y ejecutar ACAB / crear un barrido de
  cada tipo (flujo, masa, temporal, espectral con ficheros CONDERC) / ejecutar
  un barrido y abrir los resultados en el analyzer / entender el manifest.
- **Fort analyzer**: analizar una carpeta de simulaciones / interpretar la
  pestaña Simulaciones (incluido el aviso de resultados obsoletos) / cambiar
  de unidades / informe de un isótopo y sus métricas (saturación, rendimiento,
  pureza — con la interpretación física de cada una) / superponer datos
  experimentales desde CSV / configurar figuras con el editor y guardar el
  YAML / usar la pestaña Optimización con un barrido / exportar a CSV.
- **COLLAPS configurator**: crear/validar un COLL.inp / la semántica de NGROUP
  (signo=orden) e IESF=5+CX / ejecutar COLLAPS y localizar las salidas
  (XSECTION.dat, FLUX.inf) / qué verificar en FLUX.inf.

Incluir en cada manual una sección corta de "errores frecuentes y avisos" (qué
significan los avisos reales de la UI: aviso direccional de espectros, checksum
KO, resultados desactualizados, XNORM fuera de rango…).

## Cómo producirlos (recomendación de método)

- **Preferentemente con Claude Code, sesión por manual, dentro del componente**:
  puede leer `templates/*.html` y `static/i18n/es.json` y describir botones,
  pestañas y mensajes con sus NOMBRES EXACTOS (un manual que llama a los
  controles por nombres inventados es peor que ninguno). Regla para la sesión:
  toda referencia a un elemento de UI debe corresponder a una clave i18n o a un
  elemento real de las plantillas — verificarlo, no suponerlo.
- La conversación de chat sirve para: decidir estructura/índice, revisar borradores,
  redactar la guía de inicio rápido (más narrativa), y generar la versión
  Word/PDF final si se necesita.
- Capturas de pantalla: las hace el autor (Claude no puede); el manual se
  redacta dejando marcadores `[CAPTURA: pestaña Barrido con espectros cargados]`
  donde aporten, y el autor las inserta después. No abusar: una por tarea
  compleja como máximo.
- Los manuales quedan VERSIONADOS en el monorepo (docs/ de cada componente) y
  se referencian desde cada README ("manual de usuario: docs/manual_usuario.md").

## Precauciones

- Fuente de verdad del comportamiento: el código y los READMEs actuales — ante
  cualquier duda de qué hace un botón, leer la implementación, no inventar.
- No documentar funcionalidades del BACKLOG (aún no existen); no prometer nada
  "próximamente".
- Español como idioma del manual (la UI tiene es/en, pero la audiencia es local);
  terminología física consistente con el glosario del CONTEXTO.
- Empezar SIEMPRE proponiendo el índice de cada manual y validándolo con el
  autor antes de redactar capítulos.
