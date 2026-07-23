# Manual de usuario — ACAB INP File Configurator

> Manual orientado a tareas. Si buscas detalle funcional, arquitectura o
> comandos de test, consulta el `README.md` de este repositorio y su
> `CLAUDE.md`. Este documento asume que ya conoces física de activación
> neutrónica y el código ACAB 2008 (UPM), pero no la suite de herramientas.

## Índice

1. [Introducción](#1-introducción)
2. [Primeros pasos](#2-primeros-pasos)
3. [Crear un inp.5 desde cero](#3-crear-un-inp5-desde-cero)
4. [Cargar y validar un inp.5 existente](#4-cargar-y-validar-un-inp5-existente)
5. [Composición asistida del blanco](#5-composición-asistida-del-blanco)
6. [Generar el historial temporal](#6-generar-el-historial-temporal)
7. [Guardar y ejecutar ACAB](#7-guardar-y-ejecutar-acab)
8. [Herramienta CHAINS](#8-herramienta-chains)
9. [Barridos paramétricos](#9-barridos-paramétricos)
10. [Errores y avisos frecuentes](#10-errores-y-avisos-frecuentes)

---

## 1. Introducción

Esta aplicación es el primer eslabón del flujo de trabajo de la suite ACAB del
TFG:

```
COLLAPS (espectro → XSECTION.dat)  →  inp.5 (ESTA APP)  →  ejecutar ACAB  →  fort.6 (Fort Analyzer)
```

Su función es construir, cargar, validar y generar el fichero de entrada
`inp.5` de ACAB 2008 sin escribirlo a mano. El fichero `inp.5` es FORTRAN de
formato libre organizado en **14 bloques**; esta app expone cada bloque como
un formulario, con ayuda contextual y validación cruzada, y genera el fichero
final por ti.

Además incluye:

- Una herramienta separada para ficheros **CHAINS** (análisis de caminos de
  transmutación).
- Una pestaña de **barridos paramétricos**, que genera automáticamente varias
  carpetas de simulación variando un único parámetro (flujo, masa, historial
  temporal o forma del espectro).
- Ejecución integrada de ACAB (y, para el barrido espectral, también de
  COLLAPS) sin salir del navegador.

No necesitas saber programar ni conocer el código fuente para usar este
manual; cada sección te dice qué botón pulsar y qué significa cada campo.

---

## 2. Primeros pasos

### Arrancar la aplicación

La forma recomendada de arrancar toda la suite (esta app + Fort Analyzer +
COLLAPS) es el launcher común; consulta la "Guía de inicio rápido de la
suite" en `acab_suite/` para la instalación y el arranque conjunto.

Si solo necesitas esta aplicación de forma aislada, ejecútala desde su propio
entorno virtual (`...\venv\Scripts\python app.py`) y abre
`http://127.0.0.1:5000` — se abre solo en el navegador por defecto.

### Tour rápido de la barra superior

- **Archivo** — Nuevo, Cargar inp.5…, Guardar como…, Validar, Vista previa del
  fichero. Es el menú que usarás en casi cada sesión (secciones 3, 4 y 7).
- **Herramientas → CHAINS — Análisis de caminos** — abre la página dedicada a
  ficheros CHAINS (sección 8).
- **Secciones** — atajo para saltar directamente a cada una de las cinco
  secciones del formulario (Configuración General, Definición Geométrica y
  Espacial, Materiales y Flujo, Historial Temporal, Análisis de
  Incertidumbres).
- **Buscar código…** (cuadro de búsqueda de la barra superior) — escribe el
  nombre de cualquier parámetro ACAB (p. ej. `NGRP`, `IDOSE`, `XNORM`) y
  selecciona el resultado: la app cambia de pestaña, activa el bloque
  correspondiente y resalta el campo con una animación amarilla. Es la forma
  más rápida de encontrar un parámetro sin memorizar en qué sección vive.
- **Selector de idioma** (esquina superior derecha, bandera) — Español/English;
  la preferencia se guarda en el navegador.
- **Botón Ejecutar** (verde, junto al estado del fichero) — abre el modal de
  ejecución de ACAB (sección 7).
- **Estado del fichero** (texto junto al botón Ejecutar) — indica si hay un
  fichero cargado y si tiene cambios sin guardar ("modificado").

Dentro de cada sección, un **menú lateral** (los "pills" a la izquierda del
formulario) salta directamente a cada bloque de esa sección. Cada bloque tiene
un botón **Ayuda** que despliega su descripción, la tabla de parámetros y las
condiciones que activan o desactivan el bloque.

Cada bloque tiene también un área de **comentario** (fondo gris, borde
discontinuo): el texto que escribas ahí se inserta en el `inp.5` generado como
líneas `<` justo antes del bloque. Es útil para dejar constancia de por qué
elegiste un valor, sin que ACAB lo interprete.

---

## 3. Crear un inp.5 desde cero

1. **Archivo → Nuevo**: rellena todos los formularios con valores por
   defecto razonables. El estado del fichero pasa a "modificado" en cuanto
   tocas cualquier campo.
2. Recorre las cinco secciones en orden (el menú **Secciones** o las pestañas
   superiores). Cada sección agrupa bloques que se usan juntos:

   | Sección | Bloques | Qué decides ahí |
   |---|---|---|
   | Configuración General | #1, #4, #9, #10 | Título, `IUNC` (activación estándar o Monte Carlo), tamaños de librería, geometría, grupos de energía, reinicio, `XNORM`, productos de fisión |
   | Definición Geométrica y Espacial | #2 | Malla espacial (`XRR`/`YZT`), zona de cada intervalo (`MA`), nucleidos por zona (`NUCZO`/`ISOZO`), grupos gamma de salida (`EGRP`), umbrales y tablas de salida |
   | Materiales y Flujo | #3, #5, #6 | Flujo neutrónico multigrupo, composición inicial del blanco, alimentación continua |
   | Historial Temporal | #7/#8, #11, #12, #13 | Fases de irradiación/enfriamiento, tipo de cálculo, escenario operacional, control de salida |
   | Análisis de Incertidumbres | #14 | Solo si `IUNC = 1`: parámetros del cálculo Monte Carlo |

3. Un campo típico de arranque es el **Bloque #1**: fija primero `IUNC`
   (0 = activación estándar; 1 = Monte Carlo, que activa el Bloque #14), la
   geometría (`IGE`) y los tamaños de librería. Estos valores condicionan qué
   campos de otros bloques son relevantes (p. ej. `IUNC = 1` exige `NGRP = 1`).
4. Para la composición del blanco (Bloque #5) puedes escribir las
   concentraciones a mano o usar la composición asistida (sección 5 de este
   manual).
5. Para el historial de irradiación/enfriamiento (Bloques #7/#8) usa el
   generador dedicado en vez de escribir tiempos a mano (sección 6).
6. Antes de guardar, pulsa **Archivo → Validar** (sección 4) para detectar
   inconsistencias entre bloques.

> **INPT condiciona el Bloque #5.** El valor de `INPT` en el Bloque #1 decide
> si la composición se interpreta como elementos o isótopos, y en qué
> unidades (átomos/barn·cm o g/cc). Cambiar `INPT` después de rellenar el
> Bloque #5 no convierte los valores ya introducidos — revísalos.

---

## 4. Cargar y validar un inp.5 existente

1. **Archivo → Cargar inp.5…**: selecciona el fichero. La app lo parsea y
   rellena automáticamente los 14 bloques.
   - Si el fichero es en realidad un fichero **CHAINS** (formato distinto),
     la app lo detecta y muestra un aviso con un enlace directo a la
     herramienta CHAINS (sección 8) en vez de intentar interpretarlo como
     `inp.5`.
2. **Archivo → Validar** abre el modal **"Resultado de la Validación"**, que
   distingue dos niveles:
   - **Errores** ("el fichero no se puede generar correctamente") — bloquean
     el guardado hasta corregirlos: dimensiones de array que no coinciden
     (p. ej. `NUCZO` con más o menos valores que zonas `IZM`), dependencias
     entre bloques incumplidas (p. ej. `IUNC = 1` sin datos en el Bloque #14),
     valores fuera de rango.
   - **Advertencias** ("posibles inconsistencias") — no bloquean, pero
     conviene revisarlas antes de ejecutar ACAB. El botón **"Continuar de
     todos modos"** permite seguir con advertencias pendientes.
   - Si todo es correcto, el modal muestra "Sin errores ni advertencias. El
     fichero es consistente."
3. Estas ~25 comprobaciones (numeradas V01–V25 en el código, no visibles como
   tales en la interfaz) cubren, entre otras: coherencia `IUNC`/`NGRP`,
   dimensiones de `EGRP`/`FLUX`/`NUCZO`/`XRR`/`MA`/`ISOZO`, rangos de `MSTAR`,
   `NTSEQ`, `NCYO`/`ICYO`/`ITSO` (Bloque #13) y `NCYU`/`ICYU`/`ITSU`/`INUCU`
   (Bloque #14), consistencia del historial temporal (Bloques #7/#8) con
   `NOTTS`, orden estrictamente decreciente de `EGRP`, y coherencia entre
   `INPT` y el tipo de identificador usado en el Bloque #5.

La misma validación se ejecuta automáticamente al entrar en la pestaña
**Barrido** (sección 9): un fichero base con errores no permite previsualizar
ni generar barridos.

---

## 5. Composición asistida del blanco

En el **Bloque #5** (Composición inicial) puedes alternar entre dos modos:

- **Introducir concentraciones manualmente** — comportamiento clásico:
  rellenas `INUCL`/`XCOMP` fila a fila.
- **Calcular a partir de la masa del blanco** — rellena:
  1. **Compuesto / estequiometría**: fórmula química (`TeO2`) o lista
     explícita (`Te:1 O:2`).
  2. **Masa del blanco [g]**.
  3. **Volumen zona [cm³]** (por defecto 1; con geometría `IGE = 4` la app
     avisa si no coincide con la componente `XRR` de esa zona en el Bloque #2,
     porque en esa geometría `XRR` es el volumen de cada zona).
  4. **Zona destino**.
  5. Pulsa **Calcular** para ver la tabla de elementos con su fracción másica
     `wᵢ` y el `XCOMP` resultante, y **"Aplicar a la zona (ajusta NUCZO si es
     necesario)"** para volcarlo al Bloque #5 (ajusta automáticamente
     `NUCZO` en el Bloque #2 si el número de especies cambia).

Fórmulas usadas (visibles también en la nota de la propia interfaz):

- Con `INPT = 1` (elementos, átomos/barn·cm):
  `XCOMPᵢ = (m·wᵢ/Mᵢ)·N_A / (10²⁴·V)`.
- Con `INPT = 3` (elementos, g/cc): `XCOMPᵢ = m·wᵢ/V`.

**Limitación conocida:** el modo calculado **no soporta `INPT = 2`**
(isótopos) — en ese caso, introduce las concentraciones manualmente.

La librería de datos (`static/data/atomic_data.json`) usa masas atómicas
estándar CIAAW. Nota importante: ACAB expande los identificadores elementales
con las abundancias isotópicas de **su propia** librería `DECAY.dat`, que
pueden no coincidir con las abundancias modernas CIAAW; si la composición
isotópica es crítica para tu cálculo, comprueba las abundancias de la
`DECAY.dat` que estés usando.

---

## 6. Generar el historial temporal

Los Bloques #7/#8 (fases de irradiación y enfriamiento) se generan con un
formulario dedicado en vez de escribir tiempos acumulados a mano:

1. Fija la **unidad de tiempo (`IUNIT`)** aplicable a todo el historial
   (segundos, minutos, horas, días, años, ka, Ma o Ga).
2. Añade tramos de **irradiación** con **"Añadir tramo de irradiación"**: cada
   fila pide el **tiempo final acumulado** (en la unidad `IUNIT`) y el
   **número de pasos** (1–10) de ese tramo.
3. Añade tramos de **enfriamiento** de la misma forma con **"Añadir tramo de
   enfriamiento"** (los tiempos se cuentan desde el fin de la irradiación).
4. Marca, si procede, las opciones de salida por conjunto: `IOUT = 1` (salida
   por intervalo) e `IPLOT = 1` (datos para gráfica).
5. Pulsa **"Generar y actualizar datos"**: la app calcula la malla temporal
   completa y muestra la vista previa de los Bloques #7/#8 generados, además
   de fijar automáticamente `NOTTS` (Bloque #11) e `ITSO` (Bloque #13):
   `NOTTS` e `ITSO` se sincronizan automáticamente.

Errores típicos de este formulario: un tiempo final que no es estrictamente
mayor que el anterior, o un número de pasos fuera de 1–10 — ambos se señalan
con un mensaje junto a la fila afectada, y no se genera nada hasta
corregirlos.

> Esta misma malla es la que usa el barrido de tipo **Historial temporal**
> (sección 9.3): comparten la función de cálculo, así que un barrido temporal
> y una malla generada a mano con los mismos parámetros producen inp.5
> idénticos.

---

## 7. Guardar y ejecutar ACAB

### Vista previa y guardado

- **Archivo → Vista previa del fichero** abre un modal de solo lectura con el
  `inp.5` completo tal como se generaría, con contador de líneas y botón
  **"Copiar al portapapeles"**. Útil para revisar el resultado antes de
  descargarlo.
- **Archivo → Guardar como…** pide un nombre de fichero (por defecto
  `output.5`) y descarga el `inp.5` generado.

### Ejecutar ACAB sin salir del navegador

El botón **Ejecutar** (verde, barra superior) abre el modal **"Ejecución de
ACAB"**:

1. **Directorio de trabajo**: la carpeta donde está (o estará) el ejecutable
   `acab.exe` y sus ficheros auxiliares. ACAB se ejecuta siempre por `cwd`,
   sin argumentos — todos los ficheros que necesite deben estar ya en esa
   carpeta.
2. **Ejecutable** (por defecto `acab.exe`) y **Timeout (s)** (por defecto 60;
   súbelo para cálculos largos).
3. Casilla **"Guardar el fichero actual (inp.5) en el directorio de trabajo
   antes de ejecutar"**, marcada por defecto: sobrescribe el `inp.5` de esa
   carpeta con el que tienes abierto en el formulario.
4. Pulsa **Ejecutar**: el log de ACAB se muestra en vivo en el área de texto
   oscura, con un cronómetro y una insignia de estado (En ejecución… / OK /
   Timeout / Cancelado / Error con el código de salida). **Cancelar** detiene
   la ejecución en curso.
5. Al terminar con éxito aparece el botón **"Abrir en Fort Analyzer"**, que
   lleva directamente esa carpeta de resultados al analizador de `fort.6`.

Si no indicas directorio de trabajo antes de pulsar Ejecutar, la app avisa y
no lanza nada.

---

## 8. Herramienta CHAINS

CHAINS es el utilitario de ACAB para analizar **caminos de transmutación**
entre nucleidos. Requiere que ACAB haya generado previamente `UNIT 22` y
`UNIT 24` (Bloque #11: `IWP = 1`, `IMTX = 1` ó `2`). Se accede desde
**Herramientas → CHAINS — Análisis de caminos**; es una página independiente
del configurador principal, con su propio flujo **Nuevo / Cargar fichero
CHAINS… / Vista previa del fichero / Guardar como…** en el menú **Archivo**.

### Modo de operación — IFLAG

| IFLAG | Qué calcula |
|---|---|
| **1** | Todos los caminos posibles que producen el nucleido `IFINAL` en ≤ `NMAX` pasos. No se especifica nucleido inicial. |
| **2** | Todos los caminos desde el nucleido `INITIAL` hasta `IFINAL` en ≤ `NMAX` pasos, ordenados por importancia relativa (pseudo-probabilidad). Solo se imprimen los que superen `PCNT` %. |
| **3** | Caminos cíclicos ("bucles") que pasan por `IFINAL` en ≤ `NMAX` pasos. |

El campo **Nucleido inicial (`INITIAL`)** solo es relevante y editable con
`IFLAG = 2`; el campo **`PCNT`** también.

### Identificador de nucleido

Cada nucleido se especifica con un identificador entero:

```
ID = Z × 10000 + A × 10 + IS
```

donde `Z` es el número atómico, `A` el número másico e `IS` el estado
isomérico (0 = fundamental, 1 = metaestable). El formulario permite
introducir `Z`, `A`, `IS` por separado (calcula el ID automáticamente) o el
ID directamente en el panel correspondiente ("INITIAL (ID directo)" /
"IFINAL (ID directo)").

**Archivo → Nuevo** parte de un caso por defecto (`IFLAG = 2`, camino
Fe-53 → Na-24, `NMAX = 4`, `PCNT = 0,1 %`) que puedes editar campo a campo.

---

## 9. Barridos paramétricos

La pestaña **Barrido paramétrico** genera, a partir del `inp.5` actualmente
cargado (que debe ser **válido**: la pestaña re-ejecuta la validación al
entrar y antes de generar; si hay errores, quedan listados y se deshabilitan
Previsualizar/Generar), **N carpetas de simulación** que varían **un único**
parámetro y dejan fijo el resto del fichero.

### Configuración común (a todos los tipos)

- **Carpeta raíz de salida** — dónde se crean las subcarpetas, una por
  simulación.
- **Carpeta base a copiar** — su contenido completo (librerías, ejecutables,
  ficheros auxiliares) se copia íntegro a cada subcarpeta; el `inp.5`
  generado **reemplaza** cualquier `inp.5` que hubiera en la carpeta base.
- **Prefijo** — antepuesto al sufijo autogenerado de cada carpeta
  (`<prefijo><sufijo>`, p. ej. `TeO2_x0.75`).
- **Descripción del barrido** (obligatoria) — texto libre que queda en el
  manifest.

Ambos campos de carpeta tienen un botón de examinar (icono de carpeta) que
abre el selector nativo del sistema operativo, para evitar errores de
tecleo en las rutas.

### 9.1 Barrido de flujo (XNORM)

Varía `block9.XNORM` (factor multiplicativo del flujo) manteniendo fija la
**forma** del espectro; composición, geometría e historial temporal quedan
congelados. Dos modos de entrada, seleccionables con un radio:

- **Valores de XNORM (factores)** — introduces directamente los factores.
- **Flujo total objetivo** — introduces el flujo total deseado; la app
  calcula `XNORM = φ_objetivo / φ_base`, mostrando el **flujo total base**
  (Σ Bloque #3 × XNORM del fichero base) como referencia.

En ambos casos, los **valores** se escriben separados por comas.

> **Nota física.** `XNORM` escala la magnitud del flujo, no la forma del
> espectro: las secciones eficaces colapsadas con COLLAPS siguen siendo
> válidas en todo el barrido. Si el escenario real cambia la forma del
> espectro, hace falta regenerar con COLLAPS — usa el barrido espectral
> (sección 9.4), no este.

### 9.2 Barrido de masa

Varía `XCOMP` de una **zona objetivo**, dejando fija la estructura de zonas
(`INUCL`), el compuesto y el volumen. Como el volumen no cambia, variar la
masa equivale a variar la **densidad de empaquetado** del blanco. Campos:
zona objetivo, compuesto (fórmula), volumen de zona [cm³] y las masas [g] a
barrer (separadas por comas).

**No disponible con `INPT = 2`** (isótopos) — la app muestra un aviso y
deshabilita este tipo de barrido si el fichero base usa ese modo.

### 9.3 Barrido temporal

Cada simulación es una **tarjeta** de un acordeón, y cada tarjeta lleva su
propio historial temporal **completo** — el mismo editor de tramos del
generador manual (sección 6): mismo cálculo, misma validación, mismos
mensajes de error. No se repite aquí la semántica (tiempo final acumulado,
pasos 1–10, tiempos estrictamente crecientes, enfriamiento relativo al fin
de la irradiación); consulta la sección 6. Cada tarjeta fija también su
propio `IUNIT`/`IOUT`/`IPLOT`, independiente de las demás.

- **Tarjeta plegada** — resumen compacto: número de tramos y tiempo final
  de cada fase (p. ej. "irr: 3 tramos hasta 40 · cool: 2 tramos hasta
  168"). **Tarjeta desplegada** — el editor de tramos completo, igual que
  en la sección 6.
- **La primera tarjeta se siembra** con el historial del fichero base
  cargado, con un aviso visible en la propia tarjeta: el `inp.5` solo
  guarda la lista plana de pasos ya calculados, no los tramos originales
  que los produjeron, así que la siembra **colapsa la malla a un único
  tramo por fase** (conservando el tiempo final de cada una). Si
  necesitas reproducir la malla intermedia original con varios tramos,
  edítala a mano en esa tarjeta antes de generar — el aviso te lo recuerda
  cada vez que se siembra.
- **Duplicar** (icono junto al título de la tarjeta) inserta una copia
  idéntica justo a continuación; útil para variar solo un tramo entre
  simulaciones parecidas. **Eliminar** quita la tarjeta.
- **"Añadir simulación"** duplica la **última** tarjeta del acordeón.
- Cada tarjeta es un historial **completo y explícito**: a diferencia de
  los demás tipos de barrido, aquí no existe "deja el campo vacío para
  conservar la fase del fichero base" — si una fase debe quedar igual que
  la de otra simulación, cópiala con **Duplicar**.

`NOTTS` (Bloque #11) e `ITSO` (Bloque #13) se sincronizan automáticamente
por simulación, igual que en el generador manual.

> **Sufijos de carpeta.** El sufijo de cada simulación deriva del tiempo
> final de irradiación (p. ej. `Tirr040.0h`). Si dos simulaciones comparten
> el mismo tiempo final de irradiación pero tramos distintos (misma
> duración total, distinta segmentación), la app añade un índice al
> sufijo (`_2`, `_3`…) para que no colisionen de carpeta.
>
> **En el manifest.** Además de `t_irr_fin`/`t_cool_fin` (el valor que
> sigue consumiendo la pestaña Optimización del Fort Analyzer como eje X,
> sin cambios), cada simulación guarda su historial completo
> (`historial_irr`/`historial_cool`, la lista de tramos de cada fase) en
> `sweep_manifest.json`, para trazabilidad. En `sweep_manifest.csv` ese
> historial aparece como JSON dentro de la celda correspondiente, no como
> un volcado de texto de Python.

### 9.4 Barrido espectral (COLLAPS)

En lugar de tocar un valor del `inp.5`, varía la **forma** del espectro
neutrónico que COLLAPS colapsa a secciones eficaces (tarjetas `FT`/`CX` del
`COLL.inp`), importando espectros de reactores reales publicados en formato
**CONDERC** del OIEA. Responde a la pregunta: a igualdad de flujo total, ¿en
qué tipo de reactor (térmico, epitérmico, rápido…) es más eficaz la
producción del radioisótopo?

**Qué no toca este barrido.** El `inp.5` queda intacto salvo, opcionalmente,
el campo **φ_ref** (prefijado con el Bloque #3 del fichero base): si lo
editas, ese mismo valor de flujo total se aplica a **todas** las
simulaciones. `XNORM` no se toca en este tipo de barrido.

**Importar espectros.** Botón **"Añadir espectro"** para cargar uno o varios
ficheros `.txt`/`.csv` en formato CONDERC (cabecera `GROUP UPPER LOWER
LETHARGY DATA DATA/LETHARGY`, energías en eV, línea final `TOTAL` como
checksum). Por cada espectro importado, la tabla muestra:

| Columna | Significado |
|---|---|
| Etiqueta | Nombre identificativo del espectro |
| Nº grupos | Número de grupos de energía del fichero importado |
| Rango de energía | E_min–E_max del fichero. Un E_mín en keV delata un espectro de **rango parcial** (origen EXFOR/medida experimental): para comparar reactores entre sí, la frontera inferior debe alcanzar la región térmica |
| Orden | Creciente/decreciente, autodetectado — confirma visualmente que coincide con el fichero original |
| Checksum | OK si la suma de `DATA` cuadra con la línea `TOTAL` del fichero (tolerancia relativa 10⁻³); si no cuadra, el fichero se rechaza con un mensaje de error |
| Frac. térmica | Fracción del flujo con E < 0,625 eV — el predictor principal de la producción de ¹³¹I |

También se muestra el número de **grupos de la librería (XSBL)** de
referencia (211): si el espectro importado tiene menos grupos que la
librería, la fila lleva un badge de aviso — expandir un espectro con menos
grupos que la librería es la operación menos fiable de la conversión; es
informativo, no bloquea la importación.

**Ejecución.** Cada fila del barrido espectral, al ejecutarse, es un
**pipeline de varios pasos** (no una única ejecución): `collaps` → `copiar`
(el `XSECTION.dat` generado a la carpeta de la simulación) → `acab` →
`comprobar flujo` (lectura de verificación de `FLUX.inf`). La carpeta base
debe incluir una subcarpeta `collaps/` con `collaps.exe`, `XSBL.dat` y un
`COLL.inp` de partida. Un fallo en cualquier paso marca esa simulación como
fallida (indicando el paso responsable) sin detener el resto de la cola.

### Previsualizar y generar

- **Previsualizar** comprueba el barrido sin escribir nada: muestra el número
  de simulaciones, el patrón de nombre de carpeta, el coste en disco
  estimado y una tabla con los valores, el **sufijo** (editable) y la carpeta
  resultante de cada simulación.
  - Avisos posibles: la carpeta base no existe o no es accesible; la carpeta
    base ya contiene un `inp.5` (será reemplazado); ya existen subcarpetas
    con el mismo nombre (se pedirá confirmar sobrescritura); el coste en
    disco estimado supera 2 GB.
- **Generar barrido** escribe las carpetas. Con más de 30 simulaciones pide
  confirmación explícita; el límite duro es **200 simulaciones** (por encima,
  error HTTP 422). Cada `inp.5` generado se verifica re-parseándolo antes de
  escribir (round-trip); si alguno falla, se aborta **todo** el barrido y se
  limpia lo ya escrito — nunca queda un barrido a medias por un fallo aislado.

En la carpeta raíz quedan, además de las subcarpetas de simulación:
`sweep_manifest.json`, `sweep_manifest.csv`, `README.txt` y los scripts
`run_all.ps1`/`run_all.sh` (útiles si prefieres ejecutar el barrido fuera de
la app).

### Entender el manifest

- **`sweep_manifest.json`** — timestamp, tipo de barrido, descripción,
  parámetros que quedaron fijos, y la lista `[{folder, params}]` con la
  carpeta y los parámetros concretos de cada simulación. Es el fichero que
  lee tanto el ejecutor de barridos de esta app como la pestaña
  **Optimización** del Fort Analyzer.
- **`sweep_manifest.csv`** — la misma información en formato tabular
  (`folder` + una columna por parámetro), cómodo para abrir en una hoja de
  cálculo.
- **`README.txt`** — descripción legible del barrido para quien abra la
  carpeta sin contexto.

### Ejecutar un barrido y abrir los resultados en el analyzer

Tras generar un barrido aparece el panel **"Ejecución del barrido"**:

1. Pulsa **"Ejecutar barrido"**.
2. La tabla muestra, por carpeta: **Estado** (Pendiente / En ejecución / OK /
   Fallo / Timeout / Cancelada), **Paso** actual (para el barrido espectral:
   `collaps` / `copiar` / `acab` / `comprobar flujo`) y **Duración**. Un
   contador global resume el progreso (`k/n · ok ok · fallos fallos`).
3. Cada subcarpeta lleva su propia copia del ejecutable (la carpeta base se
   copió entera al generar el barrido), así que las simulaciones se ejecutan
   en cola de forma autocontenida.
4. Al terminar, los resultados quedan en `batch_results.json` (raíz del
   barrido) y cada subcarpeta tiene su `fort.6` — ábrelas desde el **Fort
   Analyzer** apuntando a la carpeta raíz del barrido para comparar todas las
   simulaciones a la vez (pestaña **Optimización** del analyzer: gráfica de
   A_pico/t_pico/pureza/rendimiento/actividad específica de yodo frente al
   parámetro barrido).

Este mismo panel de ejecución es el que se dispara desde la tarjeta
**"Cargar un barrido generado"** de más abajo cuando pulsas **"Ejecutar
barrido"** sobre un barrido ya cargado.

### Consultar un barrido ya generado

La tarjeta **"Cargar un barrido generado"**, al final de la pestaña Barrido,
permite abrir **cualquier** barrido generado por la suite (en esta sesión o
en una anterior) para ver de qué se compone, sin necesidad de regenerarlo.
Es el único camino de carga: cargar una carpeta siempre muestra este
resumen; **"Ejecutar"** es una acción posterior sobre lo ya cargado, no un
segundo flujo independiente.

1. Indica la **carpeta raíz** del barrido (la que contiene
   `sweep_manifest.json`), escribiéndola o con el botón de examinar, y pulsa
   **Cargar**.
2. La app muestra una vista de **solo lectura** con:
   - **Tipo de barrido** (uno de los 4 de la sección 9) y su **descripción**.
   - **Datos de la base** — los parámetros que quedaron fijos en toda la
     barrida.
   - **Ficheros excluidos de la copia** — las salidas de ejecuciones previas
     que se excluyeron al copiar la carpeta base a cada subcarpeta (según el
     tipo de barrido, ver sección 9); "—" si el manifest es de una versión
     anterior a esta mejora, sin romper la carga.
   - Una tabla con una fila por simulación: **Carpeta**, **Valor** (el valor
     concreto de esa simulación — en el barrido espectral, el **nombre del
     espectro**, el mismo criterio que usa la pestaña Optimización del Fort
     Analyzer), **fort.6** (Existe / No existe) y **Estado de ejecución**
     (Pendiente / En ejecución / OK / Fallo / Timeout / Cancelada si ya
     existe `batch_results.json`, o un guion si el barrido aún no se ha
     ejecutado).
   - Si ya se ejecutó, un resumen agregado (`k OK · f fallo(s) de n`); si no,
     el aviso "Este barrido todavía no se ha ejecutado."
3. **Editar queda fuera de esta vista a propósito**: para cambiar cualquier
   parámetro del barrido, regenéralo (secciones anteriores) — cargar aquí es
   solo para consultar y, si procede, ejecutar lo que ya existe en disco.

---

## 10. Errores y avisos frecuentes

| Aviso / error | Dónde aparece | Qué significa | Qué hacer |
|---|---|---|---|
| Errores en el modal de Validación | Archivo → Validar, y automáticamente en la pestaña Barrido | Inconsistencia que impide generar el `inp.5` correctamente (dimensiones de array, dependencias entre bloques, valores fuera de rango) | Corrige el campo señalado; el mensaje indica el bloque y, cuando aplica, el valor esperado frente al introducido |
| Advertencias en el modal de Validación | Igual que arriba | Posible inconsistencia que no impide guardar | Revísalas antes de ejecutar ACAB; puedes continuar con "Continuar de todos modos" si sabes que son intencionadas |
| Aviso de fichero CHAINS al cargar | Archivo → Cargar inp.5… | El fichero subido no es un `inp.5`, es un fichero CHAINS | Sigue el enlace que ofrece el aviso a la herramienta CHAINS (sección 8) |
| "No hay densidad en la librería para esta fórmula" | Composición asistida (Bloque #5) | El compuesto/elemento no está en `atomic_data.json` para calcular V = m/ρ | Introduce el volumen de zona manualmente |
| Aviso de volumen vs. XRR | Composición asistida, con `IGE = 4` | El volumen introducido no coincide con la componente `XRR` de la zona en el Bloque #2 | Corrige uno de los dos valores para mantener la coherencia geométrica |
| "El barrido de masa no está disponible" | Pestaña Barrido, tipo Masa | El fichero base usa `INPT = 2` (isótopos), no soportado por este tipo de barrido | Usa `INPT = 1` o `3`, o barre otro parámetro |
| Checksum de espectro KO | Barrido espectral, al importar un fichero CONDERC | La suma de `DATA` no coincide con la línea `TOTAL` del fichero (tolerancia 10⁻³) | El fichero CONDERC probablemente está truncado o corrupto; descárgalo de nuevo desde el OIEA |
| Badge de aviso direccional | Tabla de espectros del barrido espectral | El espectro importado tiene menos grupos que la librería XSBL (211); expandirlo es la operación menos fiable de la transcripción | Informativo, no bloquea; ten en cuenta esta limitación al interpretar resultados de ese espectro en concreto |
| E_min en keV en "Rango de energía" | Tabla de espectros del barrido espectral | El espectro es de rango parcial (típico de medidas EXFOR): no llega a la región térmica | No lo uses para comparar reactores entre sí — solo espectros de rango completo son comparables. El síntoma equivalente en los índices espectrales es una fracción térmica de 0,0 % en un reactor que debería ser térmico |
| "Esta carpeta no contiene un barrido generado por la suite" (HTTP 404) | Cargar un barrido generado | La carpeta indicada no tiene `sweep_manifest.json` en su raíz | Indica la carpeta **raíz** del barrido (donde se generó), no una subcarpeta de simulación |
| "sweep_manifest.json no se pudo leer (JSON inválido)" (HTTP 422) | Cargar un barrido generado | El manifest está corrupto o truncado | Revisa que la carpeta no se haya movido/editado a mano; regenera el barrido si no se puede recuperar |
| Colisión de carpetas (HTTP 409) | Generar barrido | Ya existen subcarpetas con el mismo nombre en la carpeta raíz | Confirma sobrescribir si es intencionado, o cambia el prefijo/carpeta raíz |
| Límite de simulaciones (HTTP 422) | Generar barrido | Se ha pedido generar más de 200 simulaciones | Reduce el rango de valores del barrido |
| Aviso de coste en disco | Previsualizar barrido | El tamaño estimado (carpeta base × N simulaciones) supera 2 GB | Confirma si tienes espacio suficiente, o reduce N/el tamaño de la carpeta base |
| "Indica el directorio de trabajo antes de ejecutar" | Modal de Ejecución de ACAB | No se ha rellenado el campo Directorio de trabajo | Indica la carpeta donde está `acab.exe` |
| Ejecución con Timeout | Modal de Ejecución de ACAB / ejecución de barrido | El cálculo no terminó dentro del tiempo indicado en "Timeout (s)" | Sube el timeout para cálculos largos (Monte Carlo, muchos pasos temporales) |

> **Resultados obsoletos.** Si el Fort Analyzer avisa de que el `inp.5` es más
> reciente que el `fort.6` que estás analizando, significa que has editado la
> entrada después de la última ejecución de ACAB: vuelve a ejecutar desde
> esta app antes de fiarte del análisis. El detalle de ese aviso está en el
> manual de usuario del Fort Analyzer.
