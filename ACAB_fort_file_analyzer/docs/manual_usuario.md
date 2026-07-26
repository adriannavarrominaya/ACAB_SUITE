# Manual de usuario — ACAB Fort File Analyzer

> Manual orientado a tareas. Si buscas detalle funcional, arquitectura, la API
> REST o comandos de test, consulta el `README.md` de este repositorio y su
> `CLAUDE.md`. Este documento asume que ya conoces física de activación
> neutrónica y el código ACAB 2008 (UPM), pero no la suite de herramientas.

## Índice

1. [Introducción](#1-introducción)
2. [Primeros pasos](#2-primeros-pasos)
3. [Analizar una carpeta de simulaciones](#3-analizar-una-carpeta-de-simulaciones)
4. [Pestaña "Simulaciones"](#4-pestaña-simulaciones)
5. [Unidades y exportación CSV](#5-unidades-y-exportación-csv)
6. [Pestaña "Actividad por Isótopo"](#6-pestaña-actividad-por-isótopo)
7. [Informe de un isótopo](#7-informe-de-un-isótopo)
8. [Métricas de optimización de producción](#8-métricas-de-optimización-de-producción)
9. [Superponer datos experimentales](#9-superponer-datos-experimentales)
10. [Pestaña "Espectro gamma"](#10-pestaña-espectro-gamma)
11. [Tablas Comparativas](#11-tablas-comparativas)
12. [Pestaña "Optimización" (barrido paramétrico)](#12-pestaña-optimización-barrido-paramétrico)
13. [Pestaña "Análisis de cadenas"](#13-pestaña-análisis-de-cadenas)
14. [Errores y avisos frecuentes](#14-errores-y-avisos-frecuentes)

---

## 1. Introducción

Esta aplicación es el último eslabón del flujo de trabajo de la suite ACAB del
TFG:

```
COLLAPS (espectro → XSECTION.dat)  →  inp.5 (INP Configurator)  →  ejecutar ACAB  →  fort.6 (ESTA APP)
```

Su función es leer los ficheros de salida `fort.6` de una o varias
simulaciones de ACAB 2008, convertirlos a magnitudes físicas comprensibles
(actividad en Bq/cm³, MBq/g o actividad total) y ofrecer, sin escribir una
sola línea de código:

- Gráficas interactivas de la evolución temporal de la actividad de cada
  isótopo.
- Un informe completo por isótopo: propiedades nucleares, pico de actividad,
  espectro gamma ENSDF/NNDC (solo ¹³¹I) y métricas de optimización de
  producción (saturación, rendimiento, pureza, actividad específica de
  yodo).
- Una pestaña de **espectro gamma de toda la muestra**, para cualquier
  nucleido con datos en la librería `PHOTON.dat` de ACAB.
- Tablas comparativas entre simulaciones.
- Superposición de datos experimentales o de referencia importados desde CSV.
- Una pestaña de optimización que combina los resultados con un barrido
  paramétrico generado desde el ACAB INP File Configurator.

No necesitas conocer el código fuente para usar este manual; cada sección te
dice qué botón pulsar, qué pestaña abrir y qué significa cada aviso.

---

## 2. Primeros pasos

### Arrancar la aplicación

La forma recomendada de arrancar toda la suite (INP Configurator + esta app +
COLLAPS) es el launcher común; consulta la "Guía de inicio rápido de la
suite" en `acab_suite/` para la instalación y el arranque conjunto.

Si solo necesitas esta aplicación de forma aislada, ejecútala desde su propio
entorno virtual (`...\venv\Scripts\python app.py`) y abre
`http://127.0.0.1:5001` — se abre solo en el navegador por defecto.

### Estructura de carpetas que espera la app

```
carpeta_padre/
├── simulacion_A/
│   ├── fort.6        ← Resultados ACAB (OBLIGATORIO)
│   ├── inp.5         ← Parámetros de simulación (opcional, recomendado)
│   └── DECAY.dat     ← Biblioteca de semividas (opcional)
├── simulacion_B/
│   └── …
└── figuras.yaml      ← Configuración de figuras (opcional)
```

También se acepta el modo de **simulación única**: si `fort.6` está
directamente en la carpeta indicada (sin subcarpetas), se analiza como una
simulación individual.

- `inp.5` en cada subcarpeta permite leer automáticamente T<sub>irr</sub>,
  T<sub>cool</sub> y el flujo neutrónico. Sin él, tendrás que introducir esos
  valores a mano (sección 3).
- `DECAY.dat` en la subcarpeta de la primera simulación es la fuente
  autoritativa de semividas para cualquier isótopo; sin él, la app usa la
  sección `semividas` de un YAML (si lo cargas) y, en último caso, una tabla
  interna reducida a los isótopos de Te/I/Xe del TFG.
- `figuras.yaml` en la carpeta o en su padre configura qué gráficas se
  dibujan en la pestaña "Actividad por Isótopo" (sección 6). Sin él, esa
  pestaña arranca vacía y te ofrece crearlas desde el propio editor.

### Tour rápido de la interfaz

- **Panel lateral izquierdo** — carpeta a analizar, fuente de parámetros
  (`inp.5` automático u override manual), botón **Analizar**, selector de
  **Unidades**, y (tras analizar) la lista de simulaciones cargadas y el
  resumen del isótopo seleccionado.
- **Panel principal** — antes de analizar, muestra un panel de bienvenida con
  instrucciones rápidas; después, seis pestañas de resultados:
  **Simulaciones**, **Actividad por Isótopo**, **Informe Isótopo**,
  **Espectro gamma**, **Tablas Comparativas** y **Optimización**.
- **Selector de idioma** (esquina superior derecha, bandera) — Español/English;
  la preferencia se guarda en el navegador. Los nombres de isótopo y las
  unidades físicas (Bq/cm³, MBq/g…) no se traducen: son notación científica,
  no texto de interfaz.
- **Insignia de estado** (junto al selector de idioma) — indica cuántas
  simulaciones hay cargadas o "Sin análisis" si aún no se ha analizado nada.

---

## 3. Analizar una carpeta de simulaciones

1. En la tarjeta **"Carpeta de Simulaciones"** del panel lateral, escribe la
   ruta absoluta en el campo **Carpeta de simulaciones**, o pulsa el botón
   de **Examinar…** (icono de carpeta, junto al campo) para abrir el selector
   nativo del sistema operativo.
2. Elige la fuente de **Parámetros de simulación**:
   - **Leer de `inp.5` (automático)** — opción marcada por defecto; lee
     T<sub>irr</sub>, T<sub>cool</sub> y el flujo de cada subcarpeta que
     contenga un `inp.5`.
   - **Introducir manualmente (override)** — despliega tres campos
     (T<sub>irr</sub> [h], T<sub>cool</sub> [h], φ total [n/cm²/s]) que
     sobreescriben, para **todas** las simulaciones del análisis, lo que se
     hubiera leído del `inp.5`. Útil si no tienes `inp.5` a mano o quieres
     forzar un valor concreto.
3. Pulsa el botón **Analizar**. Mientras se procesa aparece una superposición
   de carga ("Analizando simulaciones…"); al terminar se activa el panel de
   resultados con sus seis pestañas.
4. Si la carpeta o su directorio padre contienen un YAML de figuras, se
   carga automáticamente y aparece una alerta verde bajo el botón Analizar
   indicando su origen (ver sección 6). Si no hay ninguno, aparece un aviso
   informativo azul: "Sin YAML en carpeta — sin figuras configuradas
   (edítalas o carga un YAML)".

### Deep link desde el INP Configurator

Si llegas aquí pulsando **"Abrir en Fort Analyzer"** tras ejecutar una
simulación desde el ACAB INP File Configurator, la URL trae ya el parámetro
`?folder=<carpeta>`: el campo de carpeta se rellena solo y el análisis se
lanza automáticamente, sin que tengas que pulsar nada.

---

## 4. Pestaña "Simulaciones"

Es la pestaña activa por defecto tras analizar. Muestra la tabla **"Resumen de
Simulaciones"** con una fila por simulación cargada y las columnas:
Simulación, T<sub>irr</sub> [h], T<sub>cool</sub> [h], φ [n/cm²/s] (o el
número de grupos si el flujo es multigrupo), ρ [g/cm³], NGRP, Isótopos
(irr/cool), ¹³¹I (marca si el isótopo está presente), inp.5 (si se encontró
el fichero) y Fecha fort.6.

Si una simulación tiene flujo multigrupo, debajo de la tabla aparece un
desglose **"Flujos por grupo de energía"** por simulación, con el grupo
identificado como Rápido, Térmico o Epitérmico g*n* según su posición.

Más abajo, la sección **"Isótopos detectados en fort.6"** lista todos los
isótopos presentes como insignias (badges) clicables. Al hacer clic en una,
ese isótopo queda seleccionado (resaltado en azul) como referencia para el
**Informe Isótopo** (pestaña 3), las **Tablas Comparativas** (pestaña 5) y la
**Optimización** (pestaña 6), y se lanza automáticamente la petición del
informe. La pestaña **Espectro gamma** (pestaña 4) no depende de esta
selección — ver sección 10.

### Detección de simulaciones desactualizadas

Para cada simulación con `inp.5`, el servidor compara su fecha de
modificación con la de `fort.6`. Si el `inp.5` se editó **después** de
generarse ese `fort.6`, aparece:

- Junto a la fecha del `fort.6` en esa fila, una insignia amarilla
  **"Desactualizado"** con un tooltip: "El inp.5 fue modificado después de
  generar el fort.6: los resultados pueden no corresponder a la configuración
  actual."
- Si **cualquier** simulación del análisis está en ese estado, un banner
  amarillo agregado sobre la tabla: "Una o más simulaciones tienen un fort.6
  desactualizado respecto a su inp.5. Los resultados pueden no corresponder a
  la configuración actual."

Este aviso es solo informativo: el Fort Analyzer **nunca re-ejecuta nada**.
Para regenerar el `fort.6`, vuelve al ACAB INP File Configurator y lanza de
nuevo la simulación desde el runner.

---

## 5. Unidades y exportación CSV

### Cambiar de unidades

En la tarjeta **"Unidades"** del panel lateral, el desplegable **Unidad de
actividad** ofrece:

| Opción | Requisito |
|---|---|
| **Bq/cm³** | Ninguno — es la unidad interna, disponible siempre |
| **MBq/g** | Necesita la densidad ρ de la simulación (sección `CONCENTRATIONS(GRAM)` del `fort.6`); si falta, la opción se deshabilita y aparece la nota "MBq/g no disponible: el fort.6 no incluye la sección CONCENTRATIONS(GRAM)." |
| **Actividad total (MBq)** | Requiere indicar el **Volumen simulado [cm³]** (campo que aparece al elegir esta opción o "mCi") |
| **Actividad total (mCi)** | Igual que la anterior |

El cambio de unidad se aplica **al vuelo, en el navegador**, a las gráficas,
al informe del isótopo y a las tablas comparativas — no relanza el análisis
en el servidor. En análisis multi-simulación, cada serie usa su propia
densidad; si a alguna le falta, se omite en MBq/g y aparece un aviso con su
nombre.

> El volumen que introduzcas para "Actividad total" debe ser el volumen de la
> zona simulada (mismo dato que usarías, por ejemplo, en la composición
> asistida del INP Configurator).

### Exportar a CSV

Junto al selector de unidad, el desplegable **Formato CSV** decide cómo se
generan todas las exportaciones de la app:

- **Español (Excel: ; ,)** (por defecto) — delimitador `;`, decimal `,`: abre
  directamente en Excel es-ES.
- **Internacional (, .)** — delimitador `,`, decimal `.`.

El botón **Exportar CSV** (icono de descarga) aparece en cada gráfica de la
pestaña "Actividad por Isótopo", en cada bloque de métricas del informe
(saturación, rendimiento, pureza), en la pestaña "Optimización" y en el
diálogo de métricas de desviación de datos experimentales. Todas las
exportaciones usan la **unidad activa** en ese momento, y el fichero incluye
una cabecera comentada con carpeta, isótopo, unidad y fecha.

---

## 6. Pestaña "Actividad por Isótopo"

Muestra una gráfica interactiva de Plotly (escala logarítmica) por cada
**figura** configurada, con la evolución temporal de la actividad de una o
varias series (isótopos) superpuestas. Controles disponibles en la cabecera
de la pestaña:

- **Interruptor "Mostrar fase de irradiación"** — añade el tramo de
  irradiación al eje temporal continuo (por defecto solo se ve el
  enfriamiento).
- **Desplegable de filtro** — "Todas las figuras", "Teluro (Te)", "Xenón
  (Xe)" o "Yodo (I)": muestra solo las figuras cuya primera serie pertenece a
  ese elemento.
- **Insignia junto al filtro** — indica el origen del YAML activo: "YAML:
  carpeta" (auto-descubierto), "YAML: cargado a mano" (por selector) o "sin
  figuras".
- **Botón "Cargar YAML"** — abre el selector de ficheros del sistema para
  leer un `.yaml`/`.yml` del disco y relanza el análisis con su contenido
  (necesario porque la sección `semividas` del YAML afecta al cálculo en el
  servidor).
- **Botón "Editar figuras"** — abre el modal **"Editor de Figuras"**.

Cada gráfica lleva su propio botón de exportación CSV (icono de descarga, en
la cabecera de la tarjeta).

### Si no hay figuras configuradas

Cuando la carpeta no tiene ningún YAML de figuras (ni auto-descubierto ni
cargado a mano), la pestaña muestra un estado vacío con dos acciones: cargar
un YAML por selector, o crear las figuras desde cero con el editor
("Crear figuras con el editor").

### Editor de Figuras (modal)

Cada figura es una tarjeta con un campo **Título** y una lista de
**Series**; cada serie tiene un campo para la clave del isótopo (tal como
aparece en `fort.6`, en mayúsculas — p. ej. `I131`, `XE133M`) y una etiqueta
opcional para la leyenda. Botones disponibles:

- **"Añadir serie"** dentro de cada figura, y **"Quitar serie"** en cada fila.
- **"Añadir figura"** al final del listado, y **"Eliminar figura"** en cada
  tarjeta.
- **"Restaurar YAML cargado"** (pie del modal) — revierte el editor a la
  copia del YAML tomada en el momento de analizar; deshabilitado si no había
  ningún YAML de partida.
- **"Descargar YAML"** — genera el fichero `figuras.yaml` en el navegador
  (sin tocar el servidor); es recargable directamente con "Cargar YAML".
- **"Guardar en carpeta analizada"** — escribe `<carpeta>/figuras.yaml` en el
  servidor. Si ya existe un `figuras.yaml`, pide confirmación
  ("Ya existe un figuras.yaml en la carpeta analizada. ¿Sobrescribirlo?")
  antes de sobrescribir. Conserva cualquier sección del YAML ajena a
  `figuras` (típicamente `semividas`) que estuviera cargada.
- **Cancelar** / **Aplicar** — Aplicar vuelca los cambios a la gráfica sin
  escribir nada en disco (solo persiste al pulsar "Guardar en carpeta
  analizada" o "Descargar YAML").

> La sección `semividas` del YAML no se edita desde este modal: solo se
> conserva en el round-trip. Para modificarla, edita el fichero YAML
> directamente (ver formato en el README, sección "Configuración YAML").

---

## 7. Informe de un isótopo

Se genera automáticamente al hacer clic en una insignia de isótopo en la
pestaña **Simulaciones** (sección 4), y se muestra en la pestaña **Informe
Isótopo**. Contiene, en orden:

1. **Propiedades Nucleares** — símbolo, Z/A, semivida T½ (en distintas
   unidades), constante de desintegración λ y actividad específica (isótopo
   puro).
2. **Pico de Actividad por Simulación** — tabla con, por cada simulación, el
   valor máximo de actividad (A<sub>pico</sub>), el instante en que se
   alcanza (t<sub>pico</sub>) y la fase (irradiación o enfriamiento).
3. **Evolución de Actividad** — gráfica combinada de irradiación y
   enfriamiento para el isótopo seleccionado, con el mismo interruptor de
   fase de irradiación que la pestaña de gráficas. Debajo, el botón
   **"Cargar datos experimentales"** abre el importador de datos de
   referencia (sección 9).
4. **Métricas de Optimización de Producción** (sección 8 de este manual).
5. **Datos de Actividad en fort.6 por Simulación** — tablas numéricas
   completas (irradiación y enfriamiento) del isótopo, por simulación.
6. **Espectro Gamma** (ENSDF/NNDC) — **solo aparece si el isótopo
   seleccionado es ¹³¹I**; para el resto de isótopos esta sección no se
   muestra, porque estos datos concretos (ENSDF/NNDC) solo están integrados
   para ¹³¹I. Para el espectro gamma de **toda la muestra** con cualquier
   nucleido presente en `PHOTON.dat` (la librería genérica de ACAB), usa la
   pestaña independiente **"Espectro gamma"** (sección 10).

Cada tabla y cada gráfica de esta pestaña respeta la unidad de actividad
activa (sección 5) y ofrece su propio botón de exportación CSV donde aplica.

---

## 8. Métricas de optimización de producción

Sección incluida en el Informe Isótopo (punto 4 de la sección anterior),
calculada en el servidor para cada simulación en la unidad activa. Agrupa
tres bloques, cada uno con su propio botón **Exportar CSV**:

### Curva de Saturación Teórica

Solo se calcula para isótopos con semivida conocida y T<sub>irr</sub> > 0; si
no se cumple, el bloque muestra "no aplicable (semivida desconocida o
T<sub>irr</sub> = 0)". Superpone sobre la gráfica de evolución (punto 3 del
informe) la curva teórica

```
A_teo(t) = A_sat · (1 − e^(−λt))       con   A_sat = A_ACAB(T_irr) / (1 − e^(−λ·T_irr))
```

es decir, la curva de saturación de primer orden anclada exactamente al valor
que ACAB calculó al final de la irradiación. Debajo, una tabla por simulación
indica en qué instante t<sub>x</sub> se alcanzaría el 50 %, 75 %, 90 % y 95 %
de la saturación teórica, con una columna "¿Cabe en T<sub>irr</sub>?" que
marca si ese instante cae dentro de la irradiación realmente simulada.

**Interpretación física:** si el 90-95 % de saturación cae muy por delante
del T<sub>irr</sub> simulado, alargar la irradiación seguiría aportando
actividad de forma apreciable; si cae muy por detrás, el blanco ya está casi
saturado y seguir irradiando aporta poco.

### Rendimiento de Producción

Compara, por simulación, el **rendimiento medio** A<sub>pico</sub>/T<sub>irr</sub>
frente a la **ganancia marginal** del último 10 % del tramo de irradiación,
`(A(T_irr) − A(0.9·T_irr)) / (0.1·T_irr)`. La columna "¿Compensa seguir
irradiando?" muestra **Sí** cuando la ganancia marginal es igual o mayor que
el rendimiento medio, y **No** en caso contrario. Si la simulación no tiene
T<sub>irr</sub> > 0 el bloque indica "sin T_irr > 0.".

> **Aviso de interpretación.** Este indicador es significativo cuando el pico
> de actividad ocurre al final de la irradiación. Para isótopos de producción
> **indirecta** (como ¹³¹I, cuyo pico suele ocurrir ya en enfriamiento, tras
> el decaimiento del precursor ¹³¹Te), o en pulsos cortos con crecimiento por
> precursor, esta comparación puede no ser representativa — trátalo como
> orientativo, no como criterio único.

### Pureza Radionucleídica en el Pico

Calcula `P = A(isótopo objetivo) / Σ A(isótopos considerados)` en el instante
del pico, en %. El **criterio por defecto** son los isótopos del mismo
elemento presentes en ese `fort.6` (para ¹³¹I: ¹³⁰I, ¹³²I, ¹³³I… los que
existan en la simulación) — asume que, tras la separación radioquímica, el
producto contiene solo ese elemento.

Debajo de la descripción hay una lista de casillas con todos los isótopos
disponibles en el informe; marca o desmarca las que quieras incluir como
"impurezas" y pulsa **"Recalcular pureza"** para volver a pedir el informe al
servidor con ese criterio. El resultado por simulación muestra una insignia
`P = valor %` y una tabla de contribuciones (isótopo, actividad y porcentaje)
ordenada de mayor a menor.

> El criterio por defecto (mismo elemento) es el único validado hasta la
> fecha; si necesitas otro criterio para un análisis puntual, la casilla te
> permite ajustarlo, pero no lo tomes como recomendación general sin
> revisarlo con tu tutor.

### Pureza P(t) durante el Enfriamiento

Debajo de la tabla de contribuciones, una gráfica de dos paneles apilados
extiende la pureza puntual del bloque anterior a **toda la ventana de
enfriamiento** (t = 0 = fin de irradiación), usando la misma lista de
isótopos considerados:

- **Panel superior** — P(t) = A(isótopo objetivo, t) / Σ A(isótopos
  considerados, t) en cada paso de enfriamiento, con una línea horizontal en
  el **umbral de calidad farmacéutica (99,9 %)** y una línea vertical en el
  instante de cruce, etiquetada "Tiempo mínimo de enfriamiento para calidad
  farmacéutica". Si el cruce cae entre dos timesteps reales del `fort.6`, el
  instante se interpola (marcado como "estimado, interpolado"); si el umbral
  nunca se alcanza en la ventana simulada, la gráfica lo indica sin marcador
  de cruce.
- **Panel inferior** — A(isótopo objetivo, t) en la misma escala temporal,
  para leer de un vistazo cuánta actividad queda cuando se alcanza la
  pureza.

Junto a la gráfica, por simulación: el instante t<sub>cruce</sub> (o el
aviso de umbral no alcanzado) y la **ventana de administración** — la
actividad del isótopo objetivo en ese instante y qué fracción representa de
su pico. Un aviso adicional aparece si P(t) vuelve a bajar del umbral
después de cruzarlo (la función no asume monotonicidad).

> **Por qué P(t) crece tras el pico de actividad.** En producción
> **indirecta** como la de ¹³¹I (vía el precursor ¹³¹Te), las impurezas de
> yodo suelen decaer más rápido que el isótopo objetivo: aunque la actividad
> total ya esté bajando, la pureza sigue mejorando durante el enfriamiento.
> Esta gráfica hace visible ese cruce, que la pureza puntual en el pico
> (bloque anterior) no muestra.

### Actividad Específica del Yodo A<sub>esp</sub>(t)

Bajo la gráfica de pureza, y **solo si el isótopo seleccionado es un isótopo
de yodo**, un panel adicional muestra A<sub>esp</sub>(t) = A(objetivo, t) /
masa TOTAL de yodo presente en la muestra en ese instante [MBq/g], en el
mismo dominio temporal que P(t). La sección entera queda oculta para
cualquier otro isótopo.

**Por qué no basta con la pureza radionucleídica.** El I-127 estable y el
I-129 de vida muy larga no cuentan como "impurezas" en `P(t)` (no son
isótopos radiactivos que contaminen la señal), pero sí **diluyen** el
producto: los mismos becquerels de ¹³¹I repartidos entre más gramos de yodo
total dan menos actividad específica. La masa de yodo suma **todos** los
isótopos de yodo presentes en el `fort.6` (estables, de vida larga y
radiactivos), no solo el objetivo.

- Una línea vertical y un badge destacan el valor en **t<sub>cruce</sub> de
  pureza** (el mismo instante ya resuelto en el bloque anterior) — "qué
  actividad específica tiene el producto cuando alcanza calidad
  farmacéutica". Si esa simulación no tiene t<sub>cruce</sub> resuelto
  (umbral no alcanzado), el badge lo indica en vez de un valor.
- Esta gráfica **no lleva umbral ni semáforos** (a diferencia de P(t)): es
  una magnitud de referencia para el diseño del proceso, no un criterio de
  aceptación validado.
- A<sub>esp</sub>(t) tiene un **techo físico**: no puede superar la
  actividad específica del ¹³¹I puro sin ningún diluyente,
  λ(¹³¹I)·N<sub>A</sub>/masa(¹³¹I) ≈ 4,60×10⁹ MBq/g. Un valor por encima de
  ese techo en cualquier instante indicaría un error en los datos, no un
  resultado físico válido.
- Esta variable también está disponible como **A<sub>esp</sub> yodo** en el
  selector de la pestaña Optimización (sección 12) para comparar entre
  espectros o condiciones de un barrido — el valor que se compara es siempre
  el de t<sub>cruce</sub>, no una serie completa.

> **Unidad fija.** A<sub>esp</sub>(t) siempre se expresa en MBq/g de yodo,
> independientemente de la unidad de actividad activa (sección 5) — no es
> la misma magnitud que "MBq/g" del blanco completo (p. ej. TeO₂), así que
> el selector de unidades no la reconvierte.

---

## 9. Superponer datos experimentales

Desde el punto 3 del Informe Isótopo ("Evolución de Actividad"), el botón
**"Cargar datos experimentales"** abre el modal **"Importar datos de
referencia"**. Permite superponer sobre la curva ACAB puntos experimentales o
computacionales de referencia digitalizados de un paper u otra fuente
externa, en formato CSV (especificación completa en
[`docs/SPEC_csv_datos_referencia.md`](SPEC_csv_datos_referencia.md)):

```csv
# tipo: experimental
# descripcion: Fig. 6 - Actividad I-131 medida, cuarto experimento (MURR, TeO2)
# fase: enfriamiento
# isotopo: I131
# unidad_t: h
# unidad_A: MBq/g
# fuente: digitalizado del paper de referencia
t;A;A_err
14,5975;7728,904;120,5
16,2340;7866,102;118,2
```

Pasos:

1. Pulsa **"Elegir fichero…"** y selecciona el CSV. El delimitador (`;`, `,`
   o tabulador) y el separador decimal (`,` o `.`) se detectan
   automáticamente; las líneas `#` y las filas vacías se ignoran, y el orden
   de las filas es libre (se reordenan por t).
2. El modal muestra una **vista previa** de las 5 primeras filas, con un
   selector de rol por columna (**t (tiempo)**, **A (actividad)**,
   **A_err (incertidumbre)** o **Ignorar**). La asignación se preselecciona
   heurísticamente (la columna casi monótona se asume `t`), útil cuando un
   fichero digitalizado trae las columnas invertidas — revísala antes de
   importar.
3. Completa o corrige los campos: **Tipo de serie**, **Fase**, **Isótopo**,
   **Unidad de tiempo**, **Unidad de actividad**, **Simulación de
   referencia**, **Etiqueta (leyenda)** y **Fuente (opcional)**. Si el CSV
   trae metadatos en líneas `#`, estos campos se autorrellenan pero siguen
   siendo editables.
4. La **Simulación de referencia** es la que se usa para convertir la unidad
   de actividad (con su densidad o volumen) y para calcular las métricas de
   desviación.
5. Pulsa **Importar**.

**Tipo de serie:**

- **Experimental** (puntos huecos en la gráfica) — entra en el cálculo de
  métricas de desviación.
- **Computacional de referencia** (puntos rellenos) — solo se dibuja, no
  participa en las métricas.

Puedes cargar varias series a la vez; cada una aparece en la lista **"Series
de referencia cargadas"** con un botón ✕ para retirarla. Las series viven
solo en memoria del navegador — no se guardan en disco ni en el servidor.

### Métricas de desviación

Solo para series de tipo **experimental**: para cada punto se interpola la
curva ACAB de la simulación de referencia en su instante t y se calcula la
desviación relativa `(A_ACAB − A_exp) / A_exp · 100`. Se muestran el sesgo
medio, la desviación máxima y una tabla punto a punto, con su propio botón
Exportar CSV.

---

## 10. Pestaña "Espectro gamma"

A diferencia del Informe Isótopo (secciones 7-9), esta pestaña **no depende
del isótopo seleccionado**: se activa en cuanto hay una carpeta analizada
(igual que "Actividad por Isótopo") y muestra el espectro gamma de **toda**
la muestra en un instante de enfriamiento, combinando el inventario completo
de isótopos de esa simulación con la librería genérica de líneas gamma de
ACAB (`PHOTON.dat`) — no solo el ¹³¹I del punto 6 del Informe Isótopo
(sección 7), que usa datos ENSDF/NNDC distintos y sigue existiendo tal cual.

> **Espectro de EMISIÓN, no de detección.** La gráfica muestra líneas
> discretas (energía × tasa de fotones emitidos), no la respuesta de un
> detector real: no incluye resolución energética, eficiencia de detección
> ni el continuo Compton/bremsstrahlung. Es la magnitud física de partida
> para diseñar o interpretar una medida, no una simulación de espectro
> medido.

### Cargar la librería PHOTON.dat

El servidor intenta autodescubrir `PHOTON.dat` junto al `fort.6` de la
primera simulación, igual que hace con `DECAY.dat`. Si no lo encuentra:

- El campo **"Ruta de PHOTON.dat"** admite teclear la ruta a mano o pulsar el
  botón de examinar (icono de carpeta) para abrir el selector nativo de
  **fichero** del sistema operativo (no de carpeta).
- Pulsa **"Cargar librería"** para aplicar la ruta introducida a mano.
- La **última ruta cargada con éxito** se recuerda en el navegador
  (`localStorage`) y se reintenta automáticamente y en silencio la primera
  vez que abres esta pestaña tras analizar una carpeta — solo si el servidor
  no autodescubrió ya una librería junto al `fort.6`, y sin avisos si esa
  ruta ya no existe (no es un error del usuario, simplemente no se
  precarga).
- Junto al botón de carga, un texto de estado indica la ruta activa
  ("Librería cargada: …") o "Sin librería PHOTON.dat cargada."

### Selección de instante y filtros

- **Simulación** (si hay más de una cargada) e **Instante de enfriamiento**
  — cualquiera de los timesteps reales de esa simulación (no se interpola).
- **E mín./E máx. [keV]** — recorta el rango de energía mostrado.
- **Tasa mínima [fotones/s/cm³]** — oculta líneas por debajo del umbral. Se
  rellena automáticamente con un **valor por defecto legible**: el máximo de
  tasa del instante dividido por 10⁶, para que la vista inicial no quede
  dominada por ~30 décadas de rango dinámico entre la línea más intensa y
  las más débiles. En cuanto tocas este campo a mano, tu valor manda y deja
  de recalcularse solo — teclear **0** desactiva el filtro explícitamente y
  muestra todas las líneas.

Los filtros se aplican **en el navegador** sobre lo ya recibido del
servidor; cambiar de instante o simulación sí relanza la petición al
servidor (el espectro no viaja entero en el análisis inicial, solo bajo
demanda).

### Gráfica y tabla

El stick plot de Plotly (eje Y logarítmico) colorea las líneas por
**nucleido de origen**. Para que la leyenda no se vuelva ilegible con
inventarios grandes, se acota a los **8 nucleidos de mayor tasa TOTAL**
(suma de todas sus líneas, no la línea más fuerte); el resto se agrupa en
una única traza **"otros"** de color neutro — el hover de cada punto sigue
mostrando el nucleido real, aunque esté agrupado.

Debajo, la tabla **"Líneas principales"** (hasta 50 filas, ordenadas por
tasa) lista energía, nucleido, intensidad [%] y tasa [fotones/s/cm³], con su
propio botón **Exportar CSV**. Una sección colapsable aparte lista los
**nucleidos presentes en el inventario pero sin líneas en la librería**
cargada (informativo, no bloquea el resto del espectro).

---

## 11. Tablas Comparativas

Pestaña **Tablas Comparativas**, activa tras seleccionar un isótopo. Muestra
dos tablas cruzadas para todas las simulaciones, usando el isótopo
seleccionado como **ancla de referencia**:

| Tabla | Contenido |
|---|---|
| **Tabla 1** | Para cada simulación, el instante de pico del isótopo de referencia; lista la actividad de **todos** los demás isótopos en ese mismo instante, con su ratio respecto al pico de referencia |
| **Tabla 2** | Para **cada isótopo**, su propio instante de pico de actividad, indicando cuál era la actividad del isótopo de referencia en ese mismo momento |

Los encabezados de columna se adaptan dinámicamente al isótopo elegido (no
son siempre "I-131"). Ambas tablas respetan la unidad de actividad activa.

---

## 12. Pestaña "Optimización" (barrido paramétrico)

Esta pestaña solo se activa cuando la carpeta analizada contiene, en su
raíz, un fichero `sweep_manifest.json` — generado por la pestaña "Barrido
paramétrico" del **ACAB INP File Configurator** (barrido de flujo, masa,
historial temporal o espectral). Si no existe ese fichero, la pestaña muestra
el aviso: "Esta carpeta no contiene un barrido paramétrico (no se encontró
`sweep_manifest.json` en la raíz analizada). Esta pestaña solo se activa con
carpetas generadas por el barrido del INP File Configurator." — el resto de
la aplicación funciona exactamente igual.

Con un isótopo ya seleccionado, la pestaña combina los parámetros del
manifest con el pico, la pureza y el rendimiento **ya calculados** en el
Informe Isótopo (sección 8) — no repite ninguna fórmula física, solo agrupa
datos.

1. Selecciona el **Parámetro (eje X)** — la dimensión del barrido a
   representar. En los barridos de flujo, masa y temporal es uno de los
   parámetros numéricos del `inp.5` (p. ej. `XNORM`, `mass`, `t_irr_fin`…).
   En el **barrido espectral** el selector ofrece en su lugar:
   - **"Espectro" (categórico)** — una barra por espectro importado,
     etiquetada con su nombre (opción por defecto; ver más abajo).
   - Una **fracción espectral numérica** (`frac_termica`, `frac_epitermica`,
     `frac_rapida`, en ese orden) si el manifest las incluye — nunca
     `n_grupos`, que no tiene significado físico como eje X. Con un manifest
     de una versión anterior a esta mejora, estas opciones aparecen
     deshabilitadas con una nota, y solo queda disponible la vista por
     "Espectro".
2. Selecciona la **Variable (eje Y)**: **A pico** (por defecto), **t pico**,
   **Pureza radionucleídica en t pico**, **Rendimiento (A pico / T_irr)** o
   **Actividad específica de yodo (en t cruce de pureza)** — esta última
   solo tiene valor cuando el isótopo seleccionado es un isótopo de yodo (ver
   sección 8); para el resto de isótopos las simulaciones aparecen sin dato
   en esa variable.
3. La **gráfica** de Plotly dibuja Y frente al parámetro elegido:
   - Flujo, masa y temporal: si el barrido varía más de un parámetro
     numérico (p. ej. un barrido temporal con tiempo final y número de
     pasos), las demás dimensiones se representan como series de color
     distintas.
   - Barrido espectral con eje X **"Espectro"**: **una sola** serie de
     barras (una por espectro, con su nombre en el eje X) — nunca una
     leyenda con el volcado de parámetros de cada simulación.
   - Barrido espectral con eje X **numérico** (una fracción espectral): **una
     sola** serie de dispersión, sin agrupar por parámetros, con el nombre de
     cada espectro como etiqueta de texto junto a su punto (dos puntos muy
     próximos en X se escalonan arriba/abajo para no solaparse — típico con
     varios reactores reales de fracción térmica parecida).
4. Debajo, la **tabla** lista una fila por simulación del barrido con sus
   columnas de parámetros (o el nombre del espectro, en el barrido
   espectral), A<sub>pico</sub>, t<sub>pico</sub>, pureza y rendimiento
   medio.
5. La descripción y el tipo del barrido (campo `description`/`sweep_type` del
   manifest) aparecen como subtítulo.
6. Botón **Exportar CSV** con todas las columnas de la tabla, en la unidad
   activa.

> **Por qué el barrido espectral no usa el selector de parámetro genérico.**
> Sus dimensiones (`n_grupos`, fracciones espectrales) son numéricas por
> naturaleza pero identifican reactores distintos, no una variable continua
> barrida a propósito: agruparlas como series de color produce una leyenda
> con un volcado de parámetros ilegible. El nombre del espectro (columna
> `espectro` del manifest) es el identificador visual en ambos modos de eje
> X, igual que en la vista de "Consultar un barrido ya generado" del INP
> File Configurator.

---

## 13. Pestaña "Análisis de cadenas"

Cuantifica, para un caso de referencia y un isótopo objetivo (IFINAL), **por
qué** se produce ese isótopo: la contribución de cada isótopo inicial del
blanco (R<sub>i</sub>) y, dentro de cada uno, la contribución de cada cadena
de reacción nuclear concreta (Y<sub>z,i</sub>). Cierra el salto de "cuánto se
produce" (resto de la app) a "por qué se produce".

**Requiere un análisis ya generado** (y al menos parcialmente ejecutado)
desde la sección **"Análisis de cadenas"** del **ACAB INP File
Configurator** — ver su manual de usuario para generarlo. Esta pestaña es
**independiente** de la carpeta de simulaciones analizada arriba: tiene su
propio campo de carpeta.

### Cargar un análisis

1. Introduce (o explora con el botón de carpeta) la **carpeta raíz** del
   análisis de cadenas — la que contiene `chains_manifest.json`, `iso_<isótopo>/`
   y `chains_<isótopo>/` por cada isótopo seleccionado.
2. Pulsa **Cargar**. Si algún isótopo aún no tiene su `fort.6` (pipeline no
   ejecutado), esa fila sencillamente no aparece en la tabla 1 — no rompe la
   carga del resto. Si el `fort.6` sí existe pero su `output_chain.txt` está
   ausente o no se puede leer (corrupto, forma inesperada de CHAINS), la
   fila de tabla 1 se muestra igual (R<sub>i</sub> es un dato físico válido
   con independencia de CHAINS) con una nota en la columna "Cadenas"; solo
   sus filas de tabla 2 quedan fuera. El caso de un isótopo **sin ningún
   camino de reacción** hacia IFINAL (p. ej. los isótopos de oxígeno del
   blanco TeO₂ camino de ¹³¹I: no hay ninguna cadena O→I) tampoco es un
   error — R<sub>i</sub> se muestra igual (será ≈0, coherente con la
   física: sin cadenas, sin contribución), sin ninguna nota, y la tabla 2
   simplemente no tiene filas de ese isótopo.

### Instante t*

Ambas tablas se evalúan en un único instante t*, común a todos los
isótopos. Por defecto es el **t<sub>pico</sub> de la referencia** para el
isótopo IFINAL (marcado "— pico de la referencia" en el desplegable), igual
criterio que el instante por defecto de la pestaña "Espectro gamma". Puedes
elegir cualquier otro instante real de la simulación de referencia en el
desplegable **Instante t\***; el servidor recalcula ambas tablas para ese
instante.

### Tabla 1 — contribución por isótopo inicial

| Columna | Significado |
|---|---|
| Isótopo | Isótopo inicial del blanco (del inventario `INITIAL CONCENTRATIONS` de la referencia) |
| C<sub>i</sub> | Concentración inicial de ese isótopo \[át/cm³\] |
| A<sub>i</sub>(t\*) | Actividad de IFINAL en t\*, en la simulación **monoisotópica** de ese isótopo |
| A<sub>ref</sub>(t\*) | Actividad de IFINAL en t\*, en la simulación de **referencia** (composición completa) |
| R<sub>i</sub> | R<sub>i</sub> = A<sub>i</sub>(t\*) / A<sub>ref</sub>(t\*) — fracción de la producción de IFINAL atribuible a ese isótopo inicial |
| Cadenas | Vacía en el caso normal. "salida de CHAINS ilegible/sin cadenas" si el `output_chain.txt` de ese isótopo está ausente o no se pudo leer — R<sub>i</sub> sigue siendo válido, solo faltan sus filas en la tabla 2 |

La fila **Σ R<sub>i</sub>** es el **control de linealidad de Bateman**: las
ecuaciones de Bateman son lineales en las concentraciones iniciales, así que
si se seleccionan **todos** los isótopos del inventario inicial, Σ
R<sub>i</sub> ≈ 1 (la desviación real es solo redondeo numérico). Debajo de
la tabla, una nota indica si la selección es completa o parcial — con
selección parcial, Σ R<sub>i</sub> < 1 es lo esperado (representa solo la
fracción cubierta), no un error.

### Tabla 2 — contribución por cadena

Una fila por cada cadena de CHAINS por encima de PCNT, de **todos** los
isótopos seleccionados, ordenada por **Y<sub>z,i</sub> descendente** (las
cadenas más importantes primero, sea cual sea su isótopo de origen):

| Columna | Significado |
|---|---|
| Isótopo | Isótopo inicial del que parte la cadena |
| Cadena | Secuencia de nucleidos de la cadena (p. ej. `TE130->TE131->I131`) |
| P \[%\] | Probabilidad relativa de esa cadena dentro de las cadenas de ese isótopo, tal cual la reporta CHAINS |
| X<sub>z,i</sub> | X<sub>z,i</sub> = P/100 |
| R<sub>i</sub> | El mismo R<sub>i</sub> de la tabla 1, repetido para el cálculo |
| Y<sub>z,i</sub> | Y<sub>z,i</sub> = R<sub>i</sub>·X<sub>z,i</sub> — peso real de esa cadena concreta en la producción total de IFINAL |

Los badges junto al selector de instante muestran **NMAX** y **PCNT** del
análisis — toda cifra de CHAINS depende de estos dos parámetros, así que
viajan siempre visibles junto a la tabla.

> **Nota sobre PTOT.** PTOT es la probabilidad TOTAL de que el isótopo
> inicial acabe en el isótopo objetivo — **varía** según el caso: puede ser
> ≈100 % (casi todo el isótopo inicial llega a IFINAL, p. ej. TE130→I131) o
> mucho menor (la mayoría no llega en el nº de pasos NMAX considerado, p.
> ej. TE128→I131 con PTOT≈0,023 %). No es una constante de renormalización.
> El % de cada cadena (P) sí está siempre normalizado a 100 entre las
> cadenas devueltas, así que X<sub>z,i</sub> = P/100 vale en cualquier caso;
> Σ<sub>z</sub> Y<sub>z,i</sub> puede quedar por debajo de R<sub>i</sub> si
> hay cadenas por debajo de PCNT sin detallar — no es un error. La nota
> aparece siempre bajo la tabla 2.

### Diagrama de la cadena seleccionada

Al hacer clic en una fila de la tabla 2 aparece, debajo, el **diagrama
lineal** de esa cadena: un nodo por nucleido (nombre + semivida T½, leída de
`DECAY.dat` — "estable" si T½=∞, "T½ desconocido" si el nucleido no está en
la librería) unido por flechas etiquetadas con el **proceso** ((N,G-g),
(B-), (IT)…) y su **XSEC** (capturas) o **DELTA** (decaimientos), tal cual
los reporta CHAINS. Es la cadena **ya elegida**, como secuencia; el grafo
fusionado con varias cadenas superpuestas queda fuera de esta versión.

### Exportar a CSV

Botones **Exportar tabla 1** / **Exportar tabla 2**, independientes de la
unidad de actividad activa (esta pestaña siempre trabaja en Bq/cm³, la
unidad interna del fort.6).

---

## 14. Errores y avisos frecuentes

| Aviso / mensaje | Dónde aparece | Qué significa | Qué hacer |
|---|---|---|---|
| Insignia amarilla "Desactualizado" + banner agregado | Pestaña Simulaciones | El `inp.5` de esa subcarpeta se modificó después de generarse el `fort.6` que estás analizando | Los resultados pueden no corresponder a la configuración actual; vuelve a ejecutar ACAB desde el INP Configurator antes de fiarte del análisis |
| "Sin YAML en carpeta — sin figuras configuradas (edítalas o carga un YAML)." | Panel lateral, tras analizar | No se encontró `figuras.yaml` (ni variantes legacy) en la carpeta ni en su padre | Carga un YAML con el selector o crea las figuras desde el editor (sección 6) |
| Estado vacío en "Actividad por Isótopo" | Pestaña Actividad por Isótopo | `figuras` está vacío — sin YAML no hay figuras por defecto | Igual que arriba: cargar YAML o usar el editor |
| "MBq/g no disponible: el fort.6 no incluye la sección CONCENTRATIONS(GRAM)." | Tarjeta Unidades | Esa simulación no tiene densidad calculable | Usa Bq/cm³ o actividad total (con volumen manual) para esa simulación |
| "{sim}: sin densidad, omitida en MBq/g." | Gráficas/informe en modo MBq/g | Una simulación concreta del análisis no tiene densidad | El resto de simulaciones se muestran igual; esa serie se omite solo en MBq/g |
| Sección "Espectro Gamma" (ENSDF/NNDC) ausente | Informe Isótopo | El isótopo seleccionado no es ¹³¹I — esos datos concretos solo están integrados para ese isótopo | Normal; no es un error. Para el espectro gamma de toda la muestra con cualquier nucleido, usa la pestaña independiente "Espectro gamma" (sección 10) |
| "sin datos de enfriamiento." | Bloque Pureza P(t) / Actividad Específica de Yodo (Informe Isótopo) | La simulación no tiene fase de enfriamiento | Normal para simulaciones de solo irradiación; ese bloque no aplica a esa simulación |
| Sección "Actividad Específica del Yodo" oculta | Informe Isótopo | El isótopo seleccionado no es un isótopo de yodo | Normal; selecciona un isótopo de yodo (I127, I129, I131…) para ver esta métrica |
| "Esta simulación no tiene datos de enfriamiento." | Pestaña Espectro gamma | La simulación elegida no tiene fase de enfriamiento — no hay ningún instante que mostrar | Elige otra simulación del análisis, si la hay |
| "No se ha encontrado ni cargado ningún PHOTON.dat…" | Pestaña Espectro gamma | El servidor no autodescubrió la librería junto al `fort.6` y tampoco había una ruta recordada válida | Indica la ruta de `PHOTON.dat` (campo manual o explorador) y pulsa "Cargar librería" |
| "Ninguna línea cumple el filtro de energía/tasa actual." | Pestaña Espectro gamma | Los filtros de E mín./E máx./tasa mínima excluyen todas las líneas del instante | Amplía el rango de energía o baja la tasa mínima (tecleando 0 la desactivas) |
| "no aplicable (semivida desconocida o T<sub>irr</sub> = 0)." | Bloque Saturación (Informe Isótopo) | El isótopo no tiene semivida conocida, o la simulación tiene T<sub>irr</sub> = 0 | Revisa que el isótopo tenga entrada en `DECAY.dat`/YAML `semividas`, o que la simulación incluya irradiación |
| "sin T_irr > 0." | Bloque Rendimiento | La simulación no tiene fase de irradiación | Normal para simulaciones de solo enfriamiento; ese bloque no aplica |
| "sin t<sub>pico</sub> o actividad total nula." | Bloque Pureza | El isótopo objetivo no alcanza actividad significativa en esa simulación | Revisa que el isótopo esté realmente presente en esa simulación |
| "Asigna una columna a t y otra a A antes de importar." | Modal Importar datos de referencia | El diálogo de mapeo de columnas no tiene asignado rol `t` ni `A` | Corrige los desplegables de rol de columna en la vista previa |
| "Completa fase, unidad de tiempo, unidad de actividad e isótopo antes de importar." | Modal Importar datos de referencia | Faltan campos obligatorios del formulario | Rellena los campos marcados; si el CSV traía metadatos `#` revisa que se hayan interpretado bien |
| "Esta serie usa MBq/g pero la simulación de referencia no tiene densidad…" | Modal Importar datos de referencia | La simulación de referencia elegida no tiene `CONCENTRATIONS(GRAM)` | Elige otra simulación de referencia, o cambia la unidad de actividad de la serie importada |
| "Esta serie usa actividad total pero no hay un volumen válido configurado…" | Modal Importar datos de referencia | Falta el campo Volumen en la tarjeta Unidades | Rellena el volumen en la tarjeta Unidades (sección 5) antes de importar |
| "Esta carpeta no contiene un barrido paramétrico…" | Pestaña Optimización | No hay `sweep_manifest.json` en la raíz de la carpeta analizada | Normal si no analizas un barrido; genera uno desde el INP Configurator si lo necesitas |
| "Ninguna de las simulaciones analizadas tiene una entrada en el manifest del barrido." | Pestaña Optimización | Las carpetas analizadas no coinciden con las del manifest (p. ej. se analizó una subcarpeta suelta) | Analiza la carpeta **raíz** del barrido, no una subcarpeta individual |
| "El manifest del barrido no tiene parámetros numéricos con los que graficar." | Pestaña Optimización | El barrido no varía ningún parámetro numérico reconocible | Revisa el `sweep_manifest.json`; puede indicar un barrido mal formado |
| "No se pudo abrir el selector de carpeta." | Botón Examinar (panel lateral) | El selector nativo (tkinter) falló, típico en instalaciones Python sin tkinter | Escribe la ruta manualmente en el campo de carpeta |
| "Ya existe un figuras.yaml en la carpeta analizada. ¿Sobrescribirlo?" | Editor de Figuras → Guardar en carpeta analizada | Ya hay un `figuras.yaml` en esa carpeta | Confirma si quieres sobrescribirlo, o usa "Descargar YAML" y guárdalo en otra ubicación |
| "{n} simulación(es) con errores. Ver panel de resultados." | Tras Analizar | Alguna subcarpeta falló al parsear (p. ej. `fort.6` corrupto o incompleto) | Revisa el panel de errores sobre las pestañas de resultados, que detalla la subcarpeta y el motivo |

> **Sobre los resultados desactualizados.** Este es el único aviso que cruza
> información entre aplicaciones de la suite: el Fort Analyzer detecta la
> inconsistencia, pero solo el INP File Configurator puede volver a ejecutar
> ACAB y regenerar el `fort.6`.
