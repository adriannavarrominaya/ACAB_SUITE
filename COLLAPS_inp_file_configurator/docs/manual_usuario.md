# Manual de usuario — COLLAPS INP File Configurator

> Manual orientado a tareas. Si buscas detalle funcional, arquitectura o
> comandos de test, consulta el `README.md` de este repositorio, su
> `CLAUDE.md` y `docs/COLLAPS.md` (manual de referencia del formato
> `COLL.inp`, extraído del manual oficial de ACAB). Este documento asume que
> ya conoces física de activación neutrónica y el código ACAB 2008 (UPM),
> pero no la suite de herramientas.

## Índice

1. [Introducción](#1-introducción)
2. [Primeros pasos](#2-primeros-pasos)
3. [Crear un COLL.inp desde cero](#3-crear-un-collinp-desde-cero)
4. [Cargar y validar un COLL.inp existente](#4-cargar-y-validar-un-collinp-existente)
5. [El espectro neutrónico: NGROUP, IESF y las tarjetas #5/#6/#7](#5-el-espectro-neutrónico-ngroup-iesf-y-las-tarjetas-567)
6. [Modo de fisión (tarjetas #3/#4)](#6-modo-de-fisión-tarjetas-34)
7. [Incertidumbres (#8) y modo de ejecución ISTOP (#9)](#7-incertidumbres-8-y-modo-de-ejecución-istop-9)
8. [Guardar y ejecutar COLLAPS sin salir del navegador](#8-guardar-y-ejecutar-collaps-sin-salir-del-navegador)
9. [Localizar y verificar las salidas](#9-localizar-y-verificar-las-salidas)
10. [Errores y avisos frecuentes](#10-errores-y-avisos-frecuentes)

---

## 1. Introducción

Esta aplicación es el primer eslabón del flujo de trabajo de la suite ACAB del
TFG:

```
COLL.inp (ESTA APP)  →  ejecutar COLLAPS  →  XSECTION.dat  →  inp.5 (INP Configurator)  →  ejecutar ACAB  →  fort.6 (Fort Analyzer)
```

COLLAPS es el código preprocesador de secciones eficaces de ACAB. Su función
es **colapsar** (promediar, ponderando con un espectro neutrónico) una
librería de secciones eficaces multigrupo (formato EAF) a un único grupo de
energía, en tres modos posibles:

| Modo | Se activa con | Qué produce además del colapso estándar |
|---|---|---|
| **Estándar** | `ISFIS = 0` | Solo `XSECTION.dat` |
| **Fisión** | `ISFIS = 1` | Rendimientos de fisión efectivos (`FYL.dat`, `FYXS.dat`) |
| **Incertidumbres** | `IUNC3G = 1` | Librería colapsada con información de incertidumbre (`XSUNC.dat`, `XSUNC_1G.dat`) |

Su fichero de entrada, `COLL.inp`, consta de **9 tarjetas** en formato libre
FORTRAN (dos de ellas, `Card #1` y `Card #5`, en formato fijo `2I4`). Dos
tarjetas son **condicionales**: `Card #4` solo existe si `ISFIS ≠ 0`, y
`Card #6` solo si `IESF = 5`. Esta app expone cada tarjeta como un
formulario, con ayuda contextual, y genera el fichero final por ti — sin
necesidad de escribirlo a mano ni de contar columnas.

No necesitas saber programar ni conocer el código fuente para usar este
manual; cada sección te dice qué botón pulsar y qué significa cada campo.

---

## 2. Primeros pasos

### Arrancar la aplicación

La forma recomendada de arrancar toda la suite (esta app + INP Configurator +
Fort Analyzer) es el launcher común; consulta la "Guía de inicio rápido de la
suite" en `acab_suite/` para la instalación y el arranque conjunto.

Si solo necesitas esta aplicación de forma aislada, ejecútala desde su propio
entorno virtual (`...\venv\Scripts\python app.py`) y abre
`http://127.0.0.1:5002` — se abre solo en el navegador por defecto.

### Tour rápido de la barra superior

- **Archivo** — Nuevo, Cargar COLL.inp…, Descargar, Validar, Vista previa
  del fichero. Es el menú que usarás en casi cada sesión (secciones 3, 4 y 8).
- **Secciones** — atajo para saltar directamente a cada una de las cuatro
  pestañas del formulario (Librería, Fisión, Flujo Neutrónico, Opciones).
- **Selector de idioma** (esquina superior derecha) — Español/English; la
  preferencia se guarda en el navegador.
- **Botón "Guardar en carpeta…"** (azul, barra superior) — acción primaria de
  guardado: escribe `COLL.inp` directamente en una carpeta del disco, sin
  pasar por la descarga del navegador (sección 8).
- **Botón Ejecutar** (verde, barra superior) — abre el modal "Ejecución de
  COLLAPS" (sección 8).
- **Estado del fichero** (texto junto al botón Ejecutar) — indica si hay un
  fichero cargado y si tiene cambios sin guardar ("modificado").

### Las cuatro pestañas

Debajo de la barra superior, las pestañas **Librería**, **Fisión**, **Flujo
Neutrónico** y **Opciones** agrupan las 9 tarjetas del fichero por función:

| Pestaña | Tarjetas |
|---|---|
| Librería | #1 (`ILIB`/`IESF`), #2 (`IHEAD`) |
| Fisión | #3 (`ISFIS`/`IGEN`/`ISOCA`/`IBEST`), #4 (`EB1`/`EB2`, solo si `ISFIS ≠ 0`) |
| Flujo Neutrónico | #5 (`NGROUP`/`FF`), #6 (`CX`, solo si `IESF = 5`), #7 (`FT`) |
| Opciones | #8 (`IUNC3G`), #9 (`ISTOP`) |

Cada tarjeta tiene un botón **Ayuda** que despliega su descripción y una
tabla de parámetros. Las tarjetas condicionales (#4 y #6) muestran, cuando
están desactivadas, un aviso "Esta tarjeta está deshabilitada cuando…" en
lugar de sus campos.

La app **autoguarda tu sesión** en el navegador cada pocos segundos: si
recargas la página, navegas a otra app de la suite con el banner superior o
cierras la pestaña sin querer, al volver a abrir la app recuperas el
formulario tal como lo dejaste (aviso "Sesión anterior restaurada").

---

## 3. Crear un COLL.inp desde cero

1. **Archivo → Nuevo**: rellena todos los formularios con un caso mínimo
   válido — Vitamin-J 175 grupos (`ILIB = 2`, `IESF = 2`), espectro plano
   (`FT` = 1.0 en los 175 grupos), modo estándar (`ISFIS = 0`, `IUNC3G = 0`,
   `ISTOP = 0`). El estado del fichero pasa a "modificado" en cuanto tocas
   cualquier campo.
2. Recorre las cuatro pestañas en orden:
   - **Librería**: fija `ILIB` (estructura de la librería de secciones
     eficaces a colapsar) e `IESF` (estructura del espectro de entrada), y
     `IHEAD` (líneas de cabecera de la librería `XSBL.dat`).
   - **Fisión**: decide si necesitas el modo fisión (sección 6 de este
     manual).
   - **Flujo Neutrónico**: el número de grupos, las unidades y los valores
     del espectro (sección 5).
   - **Opciones**: incertidumbres y modo de ejecución (sección 7).
3. Antes de guardar, pulsa **Archivo → Validar** (sección 4) para detectar
   inconsistencias entre tarjetas.

---

## 4. Cargar y validar un COLL.inp existente

1. **Archivo → Cargar COLL.inp…**: selecciona el fichero. La app lo parsea y
   rellena automáticamente las 9 tarjetas, incluida la visibilidad de las
   condicionales #4 y #6. Si el fichero no se puede interpretar (formato no
   reconocido), aparece un aviso con el error de parseo y el estado del
   fichero vuelve a "Sin fichero cargado".
2. **Archivo → Validar** abre el modal **"Resultado de la Validación"**, que
   distingue dos niveles:
   - **Errores bloqueantes** — impiden generar el fichero correctamente:
     `NGROUP = 0`, `IHEAD` no positivo, número de valores de `FT` o `CX` que
     no coincide con `|NGROUP|` (o `|NGROUP|+1` para `CX`), `|NGROUP|` que no
     coincide con el tamaño esperado de la estructura `IESF` elegida (cuando
     `IESF ≠ 5`), o `EB1`/`EB2` (Card #4) no positivos o con `EB1 ≤ EB2`.
   - **Advertencias** — no bloquean, pero conviene revisarlas: todos los
     valores de `FT` en cero, valores negativos en `FT`, la combinación
     `ISFIS=1`+`IGEN=1` (el cálculo se detiene tras generar las librerías EFY
     y no colapsa secciones eficaces), `ISFIS=1`+`ISOCA=0` (COLLAPS leerá una
     librería EFY externa que debe existir ya en el directorio de ejecución),
     o `ILIB ≠ IESF` (COLLAPS convertirá internamente el espectro antes de
     colapsar). El botón **"Continuar de todos modos"** permite seguir con
     advertencias pendientes.
   - Si todo es correcto, el modal muestra "Validación correcta. No se han
     detectado errores ni advertencias."
3. La misma validación se ejecuta automáticamente al pulsar **Guardar en
   carpeta…** o **Descargar**: si hay errores o advertencias, se muestra el
   modal antes de escribir/descargar el fichero (con la opción de continuar
   si son solo advertencias).

---

## 5. El espectro neutrónico: NGROUP, IESF y las tarjetas #5/#6/#7

Esta es la parte más delicada del fichero: define cuántos valores de flujo
hay, en qué orden y con qué fronteras energéticas.

### El signo de NGROUP importa

`NGROUP` (Card #5) es el número de grupos del espectro, **y su signo indica
el orden de la lista de valores**:

- `NGROUP < 0` → los valores de `FT` (y de `CX`, si aplica) están en orden de
  **energía decreciente** — el caso habitual.
- `NGROUP > 0` → orden de **energía creciente**.

`|NGROUP|` (el valor absoluto) determina cuántos valores se esperan en
`FT` (Card #7), y cuántas fronteras en `CX` (Card #6, si `IESF = 5`): siempre
una frontera más que grupos (`|NGROUP|+1`), porque cada grupo queda delimitado
por dos fronteras y los grupos adyacentes comparten frontera.

`FF` (también en Card #5) fija las **unidades** del flujo: `0` = flujo
escalar total (n/cm²·s); `1` = densidad de flujo espectral (n/cm²·s·MeV).

### Estructuras de grupos estándar frente a IESF = 5

`IESF` (Card #1) fija la estructura de grupos del espectro de entrada. Los
valores `1`, `2`, `3`, `4` y `12` corresponden a estructuras estándar con un
número de grupos fijo (GAM-II 100, Vitamin-J 175, TART-175 175, TART-566 566,
Vitamin-J+ 211): en esos casos, `|NGROUP|` **debe coincidir** con ese número
de grupos, y las fronteras energéticas las conoce COLLAPS internamente — no
hace falta indicarlas y la **Card #6 no aparece**.

Con `IESF = 5` ("Otra — definida en Card #6") usas una estructura arbitraria:
la **Card #6 se activa** y debes rellenar tú mismo el campo **CX** con las
`|NGROUP|+1` fronteras energéticas en eV, en el mismo orden que marca el
signo de `NGROUP`.

> La app cambia automáticamente la visibilidad de la Card #6 al modificar el
> desplegable **IESF** de la pestaña Librería: no hay que recargar nada.

### Rellenar FT (y CX)

Los campos **CX** (Card #6, si aplica) y **FT** (Card #7) son áreas de texto
donde los valores van separados por espacios o saltos de línea — no hace
falta escribir el formato fijo `6E12.5` de FORTRAN, la app lo genera al
guardar. Junto al campo `FT` hay un contador (**"N valores"**) que se
actualiza en vivo mientras escribes, útil para comprobar que coincide con
`|NGROUP|` antes de validar.

---

## 6. Modo de fisión (tarjetas #3/#4)

Actívalo (`ISFIS = 1` en Card #3) cuando el `inp.5` de ACAB que vas a generar
después necesite trabajar con productos de fisión: COLLAPS debe procesar
antes los rendimientos de fisión y generar la librería 1-grupo
correspondiente.

Con `ISFIS = 1` se activa además la **Card #4**, que fija las tres regiones
energéticas donde los rendimientos de fisión se consideran constantes:

- **EB1** — frontera superior de la región de energía media. Valor sugerido:
  `5.000E+06` eV (5 MeV).
- **EB2** — frontera superior de la región de energía baja. Valor sugerido:
  `2.000E+05` eV (200 keV).

Las tres regiones resultantes son: `E > EB1` (alta), `EB2 < E < EB1` (media),
`E < EB2` (baja). `EB1` debe ser mayor que `EB2` (si no, la validación lo
bloquea — ver sección 4).

El resto de parámetros de Card #3 controlan de dónde vienen los datos de
rendimiento y para qué nucleidos se genera la librería final:

| Parámetro | Qué decide |
|---|---|
| `IGEN` | `0` = modo estándar (genera la librería de rendimientos colapsada). `1` = solo genera las librerías EFY extendidas (`EFYBL.dat`/`EFYAXSL.dat`) y **detiene la ejecución** — no se produce colapso de secciones eficaces. |
| `ISOCA` | `0` = lee una librería EFY extendida ya generada (Unit 18 / `EFYBL.dat`). `1` = procesa la librería básica de rendimientos de fisión (Unit 17 / `FYBL.dat`) desde cero. |
| `IBEST` | `0` = librería de rendimientos generada solo para los nucleidos fisibles de JEF-2.2/JEFF3.1. `1` = para todos los nucleidos fisibles de la librería de activación. |

Si `ISFIS = 0`, la Card #4 queda deshabilitada y estos cuatro parámetros de
Card #3 son irrelevantes (COLLAPS los ignora).

---

## 7. Incertidumbres (#8) y modo de ejecución ISTOP (#9)

### Card #8 — IUNC3G

Con `IUNC3G = 1`, COLLAPS procesa la librería de incertidumbres de secciones
eficaces (`UNCBL.dat`) junto con el espectro, y genera una librería colapsada
que incluye información de incertidumbre (`XSUNC.dat`, `XSUNC_1G.dat`), en la
estructura de 3 grupos de esa librería. Es independiente del modo de fisión:
puedes combinar `ISFIS = 1` e `IUNC3G = 1` en la misma ejecución.

Con `IUNC3G = 0` (por defecto) no se procesa ninguna incertidumbre.

### Card #9 — ISTOP

Controla si COLLAPS hace el colapso completo o solo informa del espectro:

- `ISTOP = 0` — ejecución completa: colapsa las secciones eficaces y escribe
  todas las salidas correspondientes al modo activado.
- `ISTOP = 1` — el código **solo escribe `FLUX.inf`** (información del
  espectro) y se detiene, sin colapsar nada. Útil como paso de comprobación
  rápida del espectro antes de lanzar el colapso completo (por ejemplo, para
  revisar la fracción térmica o el flujo total sin esperar al cálculo
  completo).

---

## 8. Guardar y ejecutar COLLAPS sin salir del navegador

### Guardar en carpeta… (acción primaria)

El botón **"Guardar en carpeta…"** (azul, barra superior) es la forma
recomendada de guardar: valida el fichero (sección 4) y, si no hay errores
bloqueantes, abre un modal donde indicas la **carpeta de destino** — a mano o
con el botón de diálogo nativo de carpeta (icono junto al campo) — y escribe
`COLL.inp` directamente ahí, sin pasar por la descarga del navegador.

- La última carpeta usada se recuerda en el navegador (`localStorage`) y se
  ofrece como valor inicial la próxima vez que abras este modal.
- Si ya existe un `COLL.inp` en la carpeta elegida, la app pide confirmación
  explícita (cuadro de confirmación del navegador) antes de sobrescribirlo.
- Si el diálogo nativo de carpeta no está disponible en tu entorno, puedes
  escribir la ruta a mano en el mismo campo (fallback manual).

### Vista previa y descarga (opción secundaria)

- **Archivo → Vista previa del fichero** abre un modal de solo lectura con el
  `COLL.inp` completo tal como se generaría, con contador de líneas y botón
  **"Copiar al portapapeles"**. Útil para revisar el resultado antes de
  guardarlo o descargarlo.
- **Archivo → Descargar** (antes "Guardar como…") valida el fichero
  (sección 4) y, si no hay errores bloqueantes, pide un nombre (por defecto
  `COLL.inp`) y descarga el fichero generado por el navegador. Es el flujo de
  descarga clásico; para escribir directamente en disco usa "Guardar en
  carpeta…", la opción primaria.

### Ejecutar COLLAPS

El botón **Ejecutar** (verde, barra superior) abre el modal **"Ejecución de
COLLAPS"**:

1. **Directorio de trabajo**: la carpeta donde está (o estará) el ejecutable
   `collaps.exe` junto con sus ficheros auxiliares — como mínimo `COLL.inp` y
   `XSBL.dat` (la librería de secciones eficaces a colapsar), y además
   `FYBL.dat`/`UNCBL.dat` si usas modo fisión o incertidumbres. COLLAPS se
   ejecuta siempre por `cwd`, sin argumentos: todo lo que necesite debe estar
   ya en esa carpeta. Si ya has usado "Guardar en carpeta…" en esta sesión,
   el campo se precarga automáticamente con esa misma carpeta (con prioridad
   sobre el directorio de la última ejecución); sin guardado previo, cae al
   directorio de la última ejecución o queda vacío — siempre editable, y con
   su propio botón de diálogo de carpeta.
2. **Ejecutable** (por defecto `collaps.exe`) y **Timeout (s)** (por defecto
   60; súbelo si el colapso tarda más).
3. Casilla **"Guardar el fichero actual (COLL.inp) en el directorio de
   trabajo antes de ejecutar"**, marcada por defecto: sobrescribe el
   `COLL.inp` de esa carpeta con el que tienes abierto en el formulario.
4. Pulsa **Ejecutar**: si en esa carpeta ya existe un `XSECTION.dat` de una
   ejecución anterior, la app pide confirmación (cuadro de confirmación del
   navegador) antes de sobrescribirlo. El log de COLLAPS se muestra en vivo
   en el área de texto oscura, con un cronómetro y una insignia de estado (En
   ejecución… / OK / Timeout / Cancelado / Error con el código de salida).
   **Cancelar** detiene la ejecución en curso.

Si no indicas directorio de trabajo antes de pulsar Ejecutar, la app avisa
("Indica el directorio de trabajo antes de ejecutar") y no lanza nada.

---

## 9. Localizar y verificar las salidas

Al terminar con éxito (insignia **OK**), COLLAPS ha escrito sus ficheros de
salida directamente en el **directorio de trabajo** que indicaste. Esta app
no los abre automáticamente ni los recoge: consúltalos con un editor de texto
o cópialos a la carpeta de tu `inp.5` en el INP Configurator.

Los ficheros generados dependen del modo activado:

| Modo | Ficheros de salida adicionales |
|---|---|
| Siempre (todos los modos) | **`XSECTION.dat`** — la librería 1-grupo de secciones eficaces colapsadas, en formato EAF: es la que necesita ACAB (`inp.5`, tarjeta correspondiente a la librería de activación). También **`FLUX.inf`** (espectro y energía media) y `REACTIONS.dat` (tipos de reacción, usado también por CHAINS). |
| Fisión (`ISFIS = 1`) | `FYL.dat` (rendimientos efectivos `⟨γ⟩`), `FYXS.dat` (secciones eficaces de rendimiento efectivas `⟨γσ⟩`), y si `IGEN = 1`, `EFYBL.dat`/`EFYAXSL.dat` |
| Incertidumbres (`IUNC3G = 1`) | `XSUNC.dat`, `XSUNC_1G.dat` |
| `ISTOP = 1` | Solo `FLUX.inf` (no se generan las demás salidas) |

### Qué verificar en FLUX.inf

`FLUX.inf` es el fichero más rápido de revisar tras cada ejecución, porque
resume el espectro tal como lo ha interpretado COLLAPS (útil incluso con
`ISTOP = 1`, sin esperar al colapso completo):

- **Flujo total integrado** — compáralo con el que esperabas del espectro
  original; una discrepancia grande suele indicar unidades mal elegidas en
  `FF` (Card #5) o valores de `FT` introducidos en el orden equivocado
  respecto al signo de `NGROUP`.
- **Energía media del espectro** — una forma rápida de confirmar que el
  espectro corresponde al tipo de reactor/fuente que esperas (térmico,
  rápido…): un valor inesperadamente alto o bajo suele delatar un error de
  orden (creciente/decreciente) o de estructura de grupos (`IESF`).

Si el `FLUX.inf` no cuadra con lo esperado, antes de repetir la ejecución
revisa en esta app: el signo de `NGROUP`, las unidades `FF`, y — si usas
`IESF = 5` — que las fronteras `CX` estén en el mismo orden que `FT`
(sección 5 de este manual).

Una vez tienes `XSECTION.dat` verificado, el siguiente paso del flujo de
trabajo es usarlo como librería de activación en el **INP Configurator** al
construir el `inp.5` (ver el manual de usuario de esa app).

---

## 10. Errores y avisos frecuentes

| Aviso / error | Dónde aparece | Qué significa | Qué hacer |
|---|---|---|---|
| Errores en el modal de Validación | Archivo → Validar, y automáticamente al Guardar en carpeta…/Descargar | Inconsistencia que impide generar el `COLL.inp` correctamente | Corrige el campo señalado; el mensaje indica el valor esperado frente al introducido |
| "NGROUP no puede ser 0" | Validación | Falta indicar el número de grupos del espectro | Rellena `NGROUP` (Card #5) con un valor distinto de cero, con el signo correcto según el orden de tus datos |
| "Card #7 (FT) debe contener N valores… pero contiene M" | Validación | El número de valores de `FT` no coincide con `\|NGROUP\|` | Añade o quita valores en el campo FT, o corrige `NGROUP`; el contador "N valores" junto al campo ayuda a cuadrarlo |
| "Card #6 (CX) debe contener N valores… pero contiene M" | Validación, solo con `IESF = 5` | El número de fronteras de `CX` no es `\|NGROUP\|+1` | Añade o quita fronteras en el campo CX |
| "Para IESF=X se esperan N grupos; \|NGROUP\| indica M" | Validación, con `IESF ≠ 5` | El `NGROUP` introducido no coincide con el tamaño fijo de la estructura estándar elegida | Corrige `NGROUP` al tamaño de esa estructura (p. ej. 175 para Vitamin-J), o cambia `IESF` a `5` si tu espectro no encaja en ninguna estructura estándar |
| "EB1 y EB2 deben ser positivos" / "EB1 debe ser mayor que EB2" | Validación, con `ISFIS ≠ 0` | Card #4 mal rellenada | Usa los valores sugeridos (5×10⁶ y 2×10⁵ eV) o corrige los tuyos |
| "Todos los valores del espectro FT son cero" | Validación (advertencia) | Sin flujo neutrónico, COLLAPS no puede calcular secciones eficaces efectivas | Revisa que has rellenado FT con los valores reales del espectro, no con el valor por defecto |
| "Hay valores negativos en FT" | Validación (advertencia) | El flujo neutrónico debe ser no negativo | Revisa el origen de los datos del espectro |
| Aviso ISFIS=1 + IGEN=1 | Validación (advertencia) | COLLAPS solo generará las librerías EFY extendidas y se detendrá; no habrá colapso de secciones eficaces | Intencionado si solo quieres generar las librerías EFY; si buscas `XSECTION.dat`/`FYL.dat`, pon `IGEN = 0` |
| Aviso ISFIS=1 + ISOCA=0 | Validación (advertencia) | COLLAPS leerá una librería EFY externa (Unit 18 / `EFYBL.dat`) que debe existir ya en el directorio de ejecución | Asegúrate de que ese fichero está en el directorio de trabajo antes de ejecutar, o cambia `ISOCA = 1` para procesar la librería básica desde cero |
| Aviso ILIB ≠ IESF | Validación (advertencia) | La librería de secciones eficaces y el espectro usan estructuras de grupos distintas | Informativo: COLLAPS convierte internamente el espectro antes de colapsar; no bloquea, pero conviene saber que ocurre esa conversión |
| Error al cargar un fichero | Archivo → Cargar COLL.inp… | El fichero no se pudo parsear como `COLL.inp` (formato no reconocido) | Comprueba que el fichero corresponde realmente a una entrada de COLLAPS y no está truncado |
| "Ya existe un COLL.inp en esta carpeta. ¿Deseas sobrescribirlo?" | Guardar en carpeta… | La carpeta elegida ya contiene un `COLL.inp` | Confirma para sobrescribirlo, o cambia la carpeta de destino |
| "Indica el directorio de trabajo antes de ejecutar" | Modal de Ejecución de COLLAPS | No se ha rellenado el campo Directorio de trabajo | Indica la carpeta donde está `collaps.exe` junto con `XSBL.dat` y el resto de librerías que necesite el modo activado |
| "Ya existe un fichero de salida previo (XSECTION.dat)…" | Modal de Ejecución de COLLAPS, al pulsar Ejecutar | El directorio de trabajo ya tiene un `XSECTION.dat` de una ejecución anterior | Confirma para sobrescribirlo, o cambia de directorio de trabajo si quieres conservar el resultado previo |
| Ejecución con Timeout | Modal de Ejecución de COLLAPS | El cálculo no terminó dentro del tiempo indicado en "Timeout (s)" | Sube el timeout, especialmente con librerías grandes o modo incertidumbres |
| Ejecución con código de error | Modal de Ejecución de COLLAPS | `collaps.exe` terminó con código de salida distinto de 0 | Revisa el log de la ejecución (área de texto del modal) para el mensaje de error de COLLAPS; suele deberse a ficheros auxiliares (`XSBL.dat`, `FYBL.dat`, `UNCBL.dat`) ausentes del directorio de trabajo o a inconsistencias del `COLL.inp` no cubiertas por la validación del formulario |

> **Sesión restaurada.** El aviso "Sesión anterior restaurada" al abrir la
> app no es un error: indica que se ha recuperado automáticamente el
> formulario que tenías abierto en la sesión anterior (ver sección 2).
