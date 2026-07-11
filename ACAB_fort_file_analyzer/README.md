# ACAB Fort File Analyzer — TFG GIE-TE

> Parte de la [suite ACAB del TFG](../README.md) — configurar entradas → ejecutar → analizar salidas.

Herramienta gráfica web para el análisis de ficheros de salida de ACABv2008

**Autores:** Adrian Navarro Minaya · Oscar Luis Cabellos de Francisco
**Centro:** Escuela Universitaria de Minas y Energía — Universidad Politécnica de Madrid
**Fecha:** Mayo 2026
**Código de simulación:** ACAB 2008 (UPM — Activation code)

---

Desarrollada como parte del Trabajo de Fin de Grado en Ingeniería de la Energía.

![ACAB](https://img.shields.io/badge/NucCalc-ACABv2008-orange) ![Python](https://img.shields.io/badge/Lang-Python314-blue) ![Flask](https://img.shields.io/badge/Web-Flask313-black) ![Bootstrap](https://img.shields.io/badge/Front-Bootstrap533-purple) ![Plotly](https://img.shields.io/badge/Charts-Plotly232-3F4F75)

---

## Índice

- [ACAB Fort File Analyzer — TFG GIE-TE](#acab-fort-file-analyzer--tfg-gie-te)
  - [Índice](#índice)
  - [1. Descripción](#1-descripción)
    - [Cadena de producción analizada en el TFG](#cadena-de-producción-analizada-en-el-tfg)
  - [2. Tecnologías Utilizadas](#2-tecnologías-utilizadas)
    - [Backend](#backend)
    - [Frontend](#frontend)
  - [3. Estructura del Proyecto](#3-estructura-del-proyecto)
  - [4. Instalación y Puesta en Marcha](#4-instalación-y-puesta-en-marcha)
    - [Requisitos previos](#requisitos-previos)
    - [Opción A — Script automático (recomendado)](#opción-a--script-automático-recomendado)
    - [Opción B — Instalación manual](#opción-b--instalación-manual)
    - [Arranque](#arranque)
    - [La suite ACAB — puertos y launcher](#la-suite-acab--puertos-y-launcher)
  - [5. Estructura de Datos de Entrada](#5-estructura-de-datos-de-entrada)
    - [Ficheros fort.6 y fort.5 (inp.5)](#ficheros-fort6-y-fort5-inp5)
    - [DECAY.dat — fuente de semividas](#decaydat--fuente-de-semividas)
  - [6. Uso de la Aplicación](#6-uso-de-la-aplicación)
    - [Flujo de trabajo](#flujo-de-trabajo)
    - [Deep link `?folder=` desde el INP Configurator](#deep-link-folder-desde-el-inp-configurator)
    - [Panel lateral — configuración del análisis](#panel-lateral--configuración-del-análisis)
    - [Idioma de la interfaz (i18n)](#idioma-de-la-interfaz-i18n)
      - [Unidades de actividad](#unidades-de-actividad)
      - [Exportación CSV](#exportación-csv)
    - [Pestaña 1 — Simulaciones](#pestaña-1--simulaciones)
      - [Detección de simulaciones desactualizadas](#detección-de-simulaciones-desactualizadas)
    - [Pestaña 2 — Actividad por Isótopo](#pestaña-2--actividad-por-isótopo)
    - [Pestaña 3 — Informe Isótopo](#pestaña-3--informe-isótopo)
      - [Validación experimental — datos de referencia externos](#validación-experimental--datos-de-referencia-externos)
      - [Métricas de optimización de producción](#métricas-de-optimización-de-producción)
    - [Pestaña 4 — Tablas Comparativas](#pestaña-4--tablas-comparativas)
    - [Pestaña 5 — Optimización (barrido paramétrico)](#pestaña-5--optimización-barrido-paramétrico)
  - [7. Configuración YAML](#7-configuración-yaml)
  - [8. API REST](#8-api-rest)
    - [Formato de `/api/analyze`](#formato-de-apianalyze)
    - [Formato de `/api/isotopo_report`](#formato-de-apiisotopo_report)
  - [9. Módulo `fort_analyzer.py`](#9-módulo-fort_analyzerpy)
    - [Parsers de ficheros](#parsers-de-ficheros)
    - [Motor de análisis](#motor-de-análisis)
    - [Métricas de optimización de producción (Fase 5)](#métricas-de-optimización-de-producción-fase-5)
  - [10. Herramientas Auxiliares](#10-herramientas-auxiliares)
  - [11. Tests](#11-tests)

---

## 1. Descripción

ACAB (_Activation Code for Accelerator-Based neutron sources_) es un código de cálculo de activación neutrónica desarrollado por el Instituto de Fusión Nuclear (UPM). Sus ficheros de salida (`fort.6`) contienen la composición isotópica y la radiactividad del material irradiado a lo largo del tiempo, organizados en bloques temporales (`TIME SET`) que resultan difíciles de procesar y visualizar manualmente.

Este proyecto proporciona una **aplicación web interactiva** (Flask + Plotly.js) que:

- **Parsea** automáticamente los ficheros `fort.6` (secciones `NUMBER OF ATOMS` e irradiación y `NUCLIDE RADIOACTIVITY` de enfriamiento) y los ficheros de entrada `inp.5` de múltiples simulaciones.
- **Lee las semividas** desde el fichero `DECAY.dat` de la biblioteca nuclear de ACAB, con posibilidad de sobreescribir o ampliar valores mediante YAML.
- **Convierte** átomos/cm³ → Bq/cm³ durante la fase de irradiación aplicando $A = \lambda \cdot N$.
- **Visualiza** la evolución temporal de la actividad de todos los isótopos presentes, con gráficas interactivas de Plotly.
- **Genera informes completos** para el isótopo que seleccione el usuario (actividad de pico, propiedades nucleares, espectro gamma para ¹³¹I).
- **Compara** simulaciones en tablas cruzadas con el isótopo seleccionado como referencia de ancla.

### Cadena de producción analizada en el TFG

El presente TFG estudia la producción de ¹³¹I médico por irradiación de TeO₂:

$${}^{130}\text{Te}(n,\gamma){}^{131}\text{Te} \xrightarrow{\beta^-} {}^{131}\text{I} \xrightarrow{\beta^-} {}^{131}\text{Xe}$$

La herramienta es completamente genérica y permite analizar **cualquier isótopo** presente en los ficheros de salida de ACABv2008.

---

## 2. Tecnologías Utilizadas

### Backend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Python** | 3.14 | Lenguaje principal |
| **Flask** | 3.1.3 | Framework web (servidor de la aplicación) |
| **Waitress** | 3.0.2 | Servidor WSGI de producción |
| **NumPy** | ≥ 1.24 | Interpolación y vectorización numérica |
| **PyYAML** | ≥ 6.0 | Lectura de configuración YAML |

Únicamente se usan módulos de la biblioteca estándar de Python (`math`, `re`, `pathlib`, `subprocess`, `threading`, `webbrowser`) además de los listados.

### Frontend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Bootstrap** | 5.3.3 | Layout responsivo, componentes UI (cards, pestañas, toasts) |
| **Bootstrap Icons** | 1.11.3 | Iconografía (CDN) |
| **Plotly.js** | 2.32.0 | Gráficas interactivas de actividad (CDN) |
| **js-yaml** | 4.1.0 | Serialización YAML del editor de figuras (guardar/descargar, CDN) |
| **JavaScript** (Vanilla ES6+) | — | Lógica de la UI: `app.js` |

---

## 3. Estructura del Proyecto

```
ACAB_fort_file_analyzer/
│
├── app.py                  # Servidor Flask + API REST
├── fort_analyzer.py        # Motor de análisis: parsers, cálculos, utilidades
├── figuras.yaml            # Configuración de figuras (ejemplo)
├── requirements.txt        # Dependencias Python
├── setup.ps1               # Script de instalación automática (Windows)
│
├── templates/
│   └── index.html          # Interfaz web principal (Bootstrap 5 + Plotly.js)
│
├── static/
│   ├── css/
│   │   └── style.css       # Estilos personalizados (sobre Bootstrap)
│   └── js/
│       └── app.js          # Lógica del frontend (análisis, gráficas, tablas)
│
├── simulaciones/           # Carpeta raíz de simulaciones (ejemplo)
│   ├── Simulacion v.1/
│   │   ├── fort.6          # Fichero de salida ACAB (obligatorio)
│   │   ├── inp.5           # Fichero de entrada ACAB (opcional, recomendado)
│   │   └── DECAY.dat       # Biblioteca nuclear de semividas (opcional)
│   ├── Simulacion v.2/
│   │   └── …
│   └── figuras.yaml         # Config YAML (opcional; nombres legacy también soportados)
│
└── compare_simulaciones.py # [LEGACY] Comparación standalone (sustituido por el
                            #  selector de unidades + la Fase 4 del runbook)
```

---

## 4. Instalación y Puesta en Marcha

### Requisitos previos

- Python 3.10 o superior (probado con 3.14)
- pip
- Navegador web moderno (Chrome, Firefox, Edge)

### Opción A — Script automático (recomendado)

El script crea un **entorno virtual local** (`venv/`) e instala todas las dependencias definidas en `requirements.txt`.

```powershell
# Instalar (Windows PowerShell)
.\setup.ps1
```

> Si PowerShell bloquea la ejecución de scripts, ejecuta previamente:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

Si el entorno queda corrupto, bórralo y relanza el script:

```powershell
Remove-Item -Recurse -Force venv
.\setup.ps1
```

### Opción B — Instalación manual

```bash
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar el entorno
# Windows:
venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Arranque

```powershell
# Windows — usando el intérprete del entorno directamente
venv\Scripts\python app.py

# Puerto por defecto: 5001
# Puerto personalizado:
venv\Scripts\python app.py --port 5100
venv\Scripts\python app.py -p 5100

# Puerto por variable de entorno:
$env:ACAB_ANALYZER_PORT = "5100"; venv\Scripts\python app.py
```

La aplicación abre automáticamente `http://127.0.0.1:5001` en el navegador por defecto.
El servidor es **Waitress** (WSGI de producción), sin mensajes de advertencia de servidor de desarrollo.

### La suite ACAB — puertos y launcher

Esta app forma parte de la suite ACAB del TFG. Puertos canónicos por defecto:

| App | Puerto |
| --- | --- |
| ACAB_inp_file_configurator | 5000 |
| ACAB_fort_file_analyzer | 5001 |
| COLLAPS_inp_file_configurator | 5002 |

El banner superior enlaza las tres apps e indica con ● verde / ○ gris si las otras
están arrancadas (endpoint `/api/ping`, único con CORS). Para arrancar la suite
completa de una vez y con una sola pestaña:
`python ..\acab_suite\suite_launcher.py` (ver README de `acab_suite/`).

Opción adicional de arranque: `--no-browser` (o `ACAB_SUITE_NO_BROWSER=1`) suprime
la apertura automática del navegador — es lo que usa el launcher.

---

## 5. Estructura de Datos de Entrada

### Ficheros fort.6 y fort.5 (inp.5)

La herramienta requiere que cada simulación esté en su propia subcarpeta con el fichero `fort.6`. El fichero `inp.5` es opcional pero muy recomendado:

```
carpeta_padre/
├── simulacion_A/
│   ├── fort.6        ← Resultados ACAB (obligatorio)
│   ├── inp.5         ← Parámetros de simulación (opcional)
│   └── DECAY.dat     ← Biblioteca de semividas (opcional)
├── simulacion_B/
│   └── …
└── figuras.yaml                            ← Configuración figuras (opcional)
```

También se acepta el modo de **simulación única**: si `fort.6` está directamente en la carpeta indicada (sin subcarpetas), se analiza como simulación individual.

| Fichero | Contenido extraído |
|---------|-------------------|
| `fort.6` — sección `NUMBER OF ATOMS` | Átomos/cm³ durante la irradiación (todos los isótopos) |
| `fort.6` — sección `NUCLIDE RADIOACTIVITY` | Bq/cm³ durante el enfriamiento (todos los isótopos) |
| `inp.5` | T_irr [h], T_cool [h], flujos multigrupo, XNORM |

La columna `RESTART` en el fort.6 marca el inicio de la fase de enfriamiento. La columna `INITIAL` corresponde al estado pre-irradiación y se omite en los análisis de enfriamiento.

### DECAY.dat — fuente de semividas

Las semividas de todos los isótopos se obtienen, **por orden de prioridad**, de:

1. **`DECAY.dat`** en la subcarpeta de la primera simulación → fuente autoritativa, cubre toda la tabla nuclear (miles de isótopos). Codificación ZZAAAS: Z número atómico, A número másico, S = 1 si estado metaestable.
2. **Sección `semividas` del YAML** → sobreescritura explícita para un subconjunto de isótopos.
3. **Tabla interna `DEFAULT_SEMIVIDAS`** en `fort_analyzer.py` → fallback si no hay `DECAY.dat` (cubre los isótopos del sistema Te/I/Xe del TFG).

Gracias a la lectura automática de `DECAY.dat`, la herramienta calcula correctamente la conversión $A = \lambda \cdot N$ para **cualquier isótopo** que aparezca en los ficheros de ACAB, sin necesidad de configuración manual de semividas.

---

## 6. Uso de la Aplicación

### Flujo de trabajo

```
Introducir ruta          Examinar carpeta
de carpeta                     ↓
      ↓                  [Botón carpeta] → selector nativo del SO
      ↓←────────────────────────────────┘
Elegir fuente de parámetros:
  ● inp.5 automático   ○ Override manual (T_irr, T_cool, φ)
      ↓
  [Analizar]
      ↓
  Resultados en 4 pestañas:
  ┌──────────────┬────────────────────┬───────────────────┬─────────────────────┐
  │ Simulaciones │ Actividad/Isótopo  │ Informe Isótopo   │ Tablas Comparativas │
  │  (resumen)   │  (gráficas Plotly) │ (tras selección)  │  (tras selección)   │
  └──────────────┴────────────────────┴───────────────────┴─────────────────────┘
```

### Deep link `?folder=` desde el INP Configurator

El botón **"Abrir en Fort Analyzer"** del **ACAB INP File Configurator** (tras
ejecutar una simulación con el runner) enlaza aquí con
`http://127.0.0.1:5001/?folder=<carpeta_de_trabajo>`. Al cargar la página, si el
query param `folder` está presente, la app rellena automáticamente el campo de
carpeta y lanza el análisis (`doAnalyze()`) sin intervención del usuario. Es
compatible con analizar varias carpetas en pestañas del navegador distintas: el
caché de análisis del servidor está indexado por carpeta normalizada, así que no
se pisan entre sí.

### Panel lateral — configuración del análisis

| Control | Descripción |
|---------|-------------|
| **Campo de carpeta** | Ruta absoluta a la carpeta padre de las simulaciones |
| **Botón examinar** | Abre el selector de carpeta nativo del SO (vía tkinter) |
| **Fuente de parámetros** | `inp.5 automático`: lee T_irr, T_cool y φ del fichero de entrada ▸ `Override manual`: permite introducir valores propios que sobreescriben los del inp.5 |
| **[Analizar]** | Lanza el análisis completo vía POST `/api/analyze` |
| **Lista de simulaciones** | Aparece tras el análisis; permite identificar las simulaciones cargadas |
| **Resumen del isótopo** | Aparece tras seleccionar un isótopo; muestra el pico de actividad para cada simulación |
| **Selector de unidades** | Unidad de actividad aplicada a gráficas, informe y tablas (persistida en el navegador) — ver abajo |

### Idioma de la interfaz (i18n)

Selector de idioma **es/en** en la barra superior (español por defecto). Las
cadenas estáticas de `templates/index.html` usan atributos `data-i18n`/
`data-i18n-*` resueltos contra `static/js/i18n/es.json` / `en.json`; las cadenas
generadas dinámicamente en `static/js/app.js` (badges, tooltips, mensajes de
error) pasan por la función `t()` del mismo mecanismo. El idioma elegido se
persiste en el navegador. Los nombres de isótopo y unidades físicas (Bq/cm³,
MBq/g…) no se traducen — son notación científica, no texto de interfaz.

#### Unidades de actividad

Los datos internos siempre están en **Bq/cm³**; el selector aplica un factor de
conversión _por simulación_ en el navegador (el cache no cambia):

| Unidad | Fórmula | Requisito |
|--------|---------|-----------|
| `Bq/cm³` | — (por defecto) | siempre |
| `MBq/g` | `Bq/cm³ / (ρ · 1e6)` | densidad ρ leída de `CONCENTRATIONS(GRAM)`; si falta, la opción se deshabilita |
| `Actividad total (MBq)` | `Bq/cm³ · V / 1e6` | volumen V [cm³] de la zona simulada (campo manual) |
| `Actividad total (mCi)` | `Bq/cm³ · V / 3.7e7` | ídem |

La densidad ρ de cada simulación se muestra en la tabla de la pestaña Simulaciones
y en el encabezado de cada simulación del informe. En análisis multi-simulación,
cada serie usa su propia densidad.

#### Exportación CSV

Botones **Exportar CSV** (todo en el navegador, sin dependencias) en cada gráfica
de series temporales, en el informe del isótopo y en cada tabla comparativa. Los
valores se exportan en la **unidad activa** y coinciden con lo mostrado; una
cabecera comentada (`# carpeta, isótopo, unidad, fecha`) precede a los datos, y el
nombre del fichero es descriptivo (p. ej. `I131_series_MBq_g_<carpeta>.csv`).

El **formato CSV** se elige junto al selector de unidades (persistido):

- **Español (Excel: ; ,)** — delimitador `;`, decimal `,` (por defecto): abre
  directamente en Excel es-ES.
- **Internacional (, .)** — delimitador `,`, decimal `.`: interoperable con
  herramientas locale-neutro.

### Pestaña 1 — Simulaciones

Vista general de todos los isótopos presentes en los datos. Para cada isótopo:

- **Badge clicable** con el nombre en notación Unicode (ej. ¹³¹I, ¹³³ᵐXe).
- Al hacer clic sobre un badge, se **selecciona el isótopo** como referencia para el Informe (pestaña 3) y las Tablas Comparativas (pestaña 4), y se lanza automáticamente la petición a `/api/isotopo_report`.
- El isótopo seleccionado queda resaltado en azul.

#### Detección de simulaciones desactualizadas

Para cada simulación con `inp.5`, el servidor compara la fecha de modificación
de `inp.5` con la de `fort.6` (`desactualizada = mtime(inp.5) > mtime(fort.6)`;
sin `inp.5` en la subcarpeta, `desactualizada = false`). Si el `inp.5` se editó
**después** de generarse ese `fort.6`, la fila de esa simulación muestra un
badge de aviso junto a la fecha del `fort.6`, con tooltip explicando que los
resultados pueden estar obsoletos; si **cualquier** simulación del análisis
está desactualizada aparece además un banner agregado en la pestaña. El
analyzer **nunca re-ejecuta nada**: solo informa; para regenerar el `fort.6`
hay que volver a lanzar la simulación desde el INP Configurator (runner).

### Pestaña 2 — Actividad por Isótopo

Gráficas interactivas de Plotly (escala logarítmica) de la evolución temporal de la actividad [Bq/cm³]:

| Control | Descripción |
|---------|-------------|
| **Toggle "Mostrar fase de irradiación"** | Activa/desactiva el tramo de irradiación en el eje temporal continuo |
| **Filtro por elemento** | Filtra las figuras por Te / Xe / I o muestra todas |
| **[Editar figuras]** | Abre el editor de grupos de figuras (ver sección YAML) |

Cada figura puede contener una o varias series (isótopos) superpuestas. Las simulaciones de diferentes carpetas se representan con colores distintos y aparecen en la leyenda. Plotly permite zoom, paneo y descarga de la imagen.

### Pestaña 3 — Informe Isótopo

Generado para el isótopo seleccionado en la pestaña Simulaciones. Contiene:

- **Propiedades nucleares**: T½ (en días, horas y segundos), constante de desintegración λ, actividad específica [Bq/g].
- **Pico de actividad** por simulación: valor máximo de Bq/cm³, instante en que se alcanza y fase (irradiación / enfriamiento).
- **Espectro gamma ENSDF/NNDC**: solo disponible para ¹³¹I (datos integrados en el código, tabla `GAMMA_I131`). Para el resto de isótopos, la sección de espectro no aparece.

> **Espectros gamma — estado actual:** por ahora solo ¹³¹I tiene espectro gamma
> (tabla ENSDF/NNDC hardcodeada). Está prevista una **Fase 6** (ver
> `acab_suite/RUNBOOK_fort_analyzer_mejoras.md`) para soporte genérico de
> cualquier isótopo leyendo `PHOTON.dat` de la biblioteca nuclear de ACAB
> (misma idea que `DECAY.dat` para semividas); pendiente de documentar el
> formato del fichero antes de implementarla.

#### Validación experimental — datos de referencia externos

Botón **[Cargar datos experimentales]** en la sección 3 del informe (evolución
de actividad). Permite superponer sobre la curva ACAB puntos experimentales o
computacionales de referencia digitalizados de un paper u otra fuente externa,
en formato CSV según [`docs/SPEC_csv_datos_referencia.md`](docs/SPEC_csv_datos_referencia.md):

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

- **Delimitador y decimal autodetectados** (`;`/`,`/tabulador; `,` o `.`);
  cabecera de columnas opcional; filas vacías y líneas `#` se ignoran; orden de
  filas libre (se ordena por t).
- **Diálogo de importación**: previsualiza las 5 primeras filas con un
  selector de columna (`t` / `A` / `A_err` / ignorar) por columna, con
  preasignación heurística (la columna casi monótona es `t`, útil cuando un
  fichero digitalizado trae las columnas invertidas). Los campos *fase*,
  *unidad de tiempo*, *unidad de actividad*, *isótopo*, *tipo* y *etiqueta* se
  autorrellenan desde los metadatos `#` del CSV si existen, y son siempre
  editables. Se indica también la **simulación de referencia** contra la que
  se convierte la unidad de actividad (usa su densidad/volumen) y se calculan
  las métricas de desviación.
- **Tipo de serie**: `experimental` (puntos huecos, entra en las métricas de
  desviación) o `computacional_referencia` (puntos rellenos, solo se dibuja).
  Se pueden cargar varias series simultáneamente.
- **Métricas de desviación** (solo series `experimental`): para cada punto se
  interpola la curva ACAB de la simulación de referencia en su instante t y se
  calcula la desviación relativa `(A_ACAB − A_exp) / A_exp · 100`; se muestran
  el sesgo medio, la desviación máxima y una tabla punto a punto, exportable a
  CSV. Las series quedan en memoria (no se guardan en disco) y se pueden
  retirar con el botón ✕ de su etiqueta.
- Sustituye a `compare_simulaciones.py` (ver sección 10, ahora legacy):
  reproduce su comparación (misma simulación de referencia, mismos puntos)
  sin densidad ni datos hardcodeados.

#### Métricas de optimización de producción

Sección **"Métricas de Optimización de Producción"** del informe (bajo la
gráfica de evolución), calculada en el servidor
(`fort_analyzer.calcular_saturacion` / `calcular_rendimiento` /
`calcular_pureza`) para cada simulación, en la unidad activa y exportable a
CSV (botón propio por bloque):

- **Curva de saturación teórica** — solo para isótopos con T½ conocida y
  T_irr > 0. Superpone sobre la gráfica de la sección 3 la curva
  `A_teo(t) = A_sat·(1−e^(−λt))` durante la irradiación, con
  `A_sat = A_ACAB(T_irr)/(1−e^(−λ·T_irr))` (ancla exacta al valor ACAB al
  final de la irradiación). Tabla de tiempos para alcanzar el 50/75/90/95 %
  de la saturación, marcando si caben dentro del T_irr de la simulación.
- **Rendimiento de producción** — rendimiento medio `A_pico/T_irr` frente a
  la ganancia marginal del último 10 % del tramo de irradiación
  `(A(T_irr)−A(0.9·T_irr))/(0.1·T_irr)`; un indicador (Sí/No) resume si
  compensa seguir irradiando (marginal ≥ medio). Para isótopos de producción
  indirecta (p. ej. ¹³¹I, cuyo pico ocurre en enfriamiento) esta comparación
  puede no ser representativa — ver la observación anotada en
  `tests/fixtures/README.md`.
  El badge de rendimiento es significativo cuando el pico ocurre al final de la irradiación; en pulsos cortos con crecimiento por precursor, ignorarlo
- **Pureza radionucleídica en el pico** —
  `P = A(isótopo objetivo) / Σ A(isótopos considerados)` en el instante del
  pico, en %. **Criterio por defecto: isótopos del mismo elemento presentes
  en el fort.6** (tras la separación radioquímica el producto contiene solo
  ese elemento — para ¹³¹I: ¹³⁰I, ¹³²I, ¹³³I… los que existan en la
  simulación). Editable desde una lista de casillas en la propia sección
  (botón **"Recalcular pureza"**), que vuelve a pedir el informe al servidor
  con la lista elegida (`impurezas` en `/api/isotopo_report`).

  > **Aviso:** el criterio por defecto (mismo elemento) es el único soportado
  > como default — ver `acab_suite/RUNBOOK_fort_analyzer_mejoras.md`. Mientras
  > siga pendiente, no cambiar el default sin esa validación; el criterio es
  > configurable por simulación desde la UI si se necesita otro mientras tanto.

### Pestaña 4 — Tablas Comparativas

Dos tablas cruzadas para todas las simulaciones, usando el isótopo seleccionado como **ancla de referencia**:

| Tabla | Contenido |
|-------|-----------|
| **Tabla 1** | Actividad de todos los isótopos en el instante del pico del isótopo de referencia, con ratio relativo al pico de referencia |
| **Tabla 2** | Pico individual de cada isótopo, con la actividad del isótopo de referencia en ese mismo instante |

Los encabezados de columna se adaptan dinámicamente al isótopo seleccionado (no son siempre "I-131").

### Pestaña 5 — Optimización (barrido paramétrico)

Fase 5 (opcional) del `RUNBOOK_barrido_parametrico_v2.md`: solo se activa cuando
la carpeta analizada contiene, en su raíz, un `sweep_manifest.json` generado
por la pestaña "Barrido" del **ACAB INP File Configurator** (barrido de flujo,
masa o historial temporal — ver el README de ese repo). Si no existe ese
fichero, la pestaña muestra un aviso y el resto de la aplicación funciona
exactamente igual que sin barrido.

Con un isótopo seleccionado, combina los parámetros del manifest
(`folder → params`) con el pico, la pureza y el rendimiento **ya calculados**
en la pestaña Informe Isótopo (Sección 4, Fase 5 de métricas) — no se repite
ninguna fórmula física:

- **Tabla**: una fila por simulación del barrido, con sus columnas de
  parámetros (p. ej. `XNORM`, `mass`, `t_irr_fin`…), A<sub>pico</sub>,
  t<sub>pico</sub>, pureza radionucleídica en el pico y rendimiento medio
  (A<sub>pico</sub>/T<sub>irr</sub>).
- **Gráfica** (Plotly): variable Y elegible — **A<sub>pico</sub>** (por
  defecto), t<sub>pico</sub>, pureza o rendimiento — frente al parámetro del
  barrido elegido como eje X; si el barrido varía más de un parámetro
  numérico (p. ej. temporal: t_irr_fin y pasos_irr), las demás dimensiones se
  muestran como series de color distintas.
- **Exportación CSV** con todas las columnas de la tabla, en la unidad
  activa.
- La descripción del barrido (campo `description` del manifest) y su tipo se
  muestran como subtítulo.

---

## 7. Configuración YAML

El fichero YAML es **opcional**. Si está presente en la carpeta de simulaciones
o en su directorio padre, se carga automáticamente. Nombre canónico:
`figuras.yaml`; también se buscan (compatibilidad con carpetas antiguas, en
este orden) `figuras - multiples simulaciones.yaml` y `config.yaml`.

**Sin YAML, la pestaña "Actividad por Isótopo" no dibuja nada**: no hay
figuras por defecto. Se muestra un estado vacío con dos acciones — cargar un
YAML de figuras por selector, o crear figuras desde cero con el editor. Un
YAML de ejemplo real (16 figuras del caso de estudio Te/Xe/I del TFG) está en
[`figuras.yaml`](figuras.yaml) (raíz del repo); una plantilla equivalente más
simple (15 figuras) está en
[`docs/ejemplo_figuras_TeO2.yaml`](docs/ejemplo_figuras_TeO2.yaml).

```yaml
# figuras.yaml

figuras:
  - num: 1
    titulo: "Figura 1: ¹³¹I (isótopo de interés)"
    mostrar_irr: true      # true → eje continuo irr.+enf.  false → solo enfriamiento
    series:
      - iso: I131          # Clave tal como aparece en fort.6 (mayúsculas)
        label: "¹³¹I"     # Etiqueta Unicode para la leyenda

  - num: 2
    titulo: "Figura 2: ¹³³Xe / ¹³³ᵐXe"
    mostrar_irr: false
    series:
      - iso: XE133
        label: "¹³³Xe"
      - iso: XE133M
        label: "¹³³ᵐXe"

semividas:                 # Sobreescritura o ampliación de semividas (opcional)
  I131:  "8.0252 d"       # Unidades: ns, µs, ms, s, m, h, d, y, .inf (estable)
  TE131: "25.0 m"
```

| Campo | Descripción |
|-------|-------------|
| `figuras[].num` | Número de figura (para ordenación; título automático si no hay `titulo`) |
| `figuras[].titulo` | Título personalizado de la figura |
| `figuras[].mostrar_irr` | `true` → muestra el tramo de irradiación en el eje temporal |
| `figuras[].series[].iso` | Clave del isótopo en mayúsculas, tal como aparece en fort.6 (ej. `I131`, `XE133M`) |
| `figuras[].series[].label` | Etiqueta en notación Unicode para la leyenda de la gráfica |
| `semividas` | Diccionario `{iso: valor}` con sobreescrituras de T½; solo los isótopos listados sobreescriben al DECAY.dat |

### Cargar, editar y guardar figuras desde la interfaz

En la pestaña "Actividad por Isótopo":

- **Selector "Cargar YAML"** — lee un `.yaml`/`.yml` del disco (sin subirlo al
  servidor más que para relanzar el análisis) y vuelve a llamar a
  `/api/analyze` con su contenido (`yaml_content`); necesario porque la
  sección `semividas` afecta al cálculo en el servidor. Un badge junto al
  selector indica el origen: **carpeta** (auto-descubierto), **cargado a
  mano** (por selector) o **sin figuras** (ninguno de los dos).
- **Editor de figuras** — añade/edita/elimina figuras y series a mano. Botón
  "Restaurar YAML cargado" revierte a la copia tomada al analizar (deshabilitado
  si no había YAML de partida — no hay ya una configuración "por defecto").
- **"Guardar en carpeta analizada"** — escribe `<carpeta>/figuras.yaml` vía
  `POST /api/figuras/save`; conserva cualquier sección ajena a `figuras`
  (p. ej. `semividas`) del YAML que estuviera cargado (round-trip). Pide
  confirmación si ya existe un `figuras.yaml` en la carpeta.
- **"Descargar YAML"** — genera el fichero en el navegador (sin servidor); el
  resultado es recargable directamente por el selector.

---

## 8. API REST

El servidor Flask expone los siguientes endpoints JSON:

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Sirve la interfaz HTML (`index.html`) |
| `POST` | `/api/scan` | Escanea una carpeta y devuelve las subcarpetas con `fort.6` y la ruta YAML detectada |
| `POST` | `/api/analyze` | Análisis completo: parsea todos los `fort.6`/`inp.5`, carga semividas, devuelve todos los datos como JSON |
| `POST` | `/api/browse-folder` | Abre el selector de carpeta nativo del SO (tkinter en subprocess) y devuelve la ruta seleccionada |
| `GET` | `/api/gamma-spectrum` | Devuelve el espectro gamma del ¹³¹I (datos ENSDF/NNDC) |
| `POST` | `/api/isotopo_report` | Genera el informe completo para el isótopo indicado, reutilizando el caché del último `/api/analyze` |
| `POST` | `/api/figuras/save` | Escribe `<folder>/figuras.yaml` con el YAML editado (round-trip de secciones ajenas a `figuras`); requiere que `folder` ya esté en caché de un `/api/analyze` previo |

### Formato de `/api/analyze`

**Request body (JSON):**
```json
{
  "folder":          "C:/ruta/a/simulaciones",
  "leer_inp5":       true,
  "t_irr_override":  null,
  "t_cool_override": null,
  "phi_override":    null,
  "yaml_content":    null
}
```

**Response (JSON):**
```json
{
  "ok":             true,
  "folder":         "C:/ruta/a/simulaciones",
  "yaml_used":      "auto",
  "decay_dat_used": true,
  "decay_dat_path": "C:/ruta/a/simulaciones/sim1/DECAY.dat",
  "simulations":    { "sim1": { … }, "sim2": { … } },
  "errors":         {},
  "all_isotopes":   ["I127", "I131", "TE130", …],
  "semividas_keys": ["I127", "I131", "TE130", …],
  "figuras":        [ … ],
  "yaml_config":    { "figuras": [ … ], "semividas": { … } },
  "sweep_manifest": null
}
```

`figuras` es `[]` si no hay YAML (auto-descubierto ni subido) — no existe una
configuración de figuras por defecto (ver sección 7). `yaml_config` es el
dict YAML completo tal como se cargó (`{}` si no había YAML); el frontend lo
usa solo para el round-trip al guardar/descargar un `figuras.yaml` editado
(conservar secciones ajenas a `figuras`, p. ej. `semividas`), no forma parte
del cálculo.

`sweep_manifest` (Fase 5 opcional, `RUNBOOK_barrido_parametrico_v2.md`) — si
la carpeta analizada contiene un `sweep_manifest.json` en su raíz (escrito
por la pestaña "Barrido" del ACAB INP File Configurator), se devuelve tal
cual: `{timestamp, sweep_type, description, fixed_params, n, simulations:
[{folder, params}, …]}`. `null` para carpetas sin barrido — no afecta al
resto de la respuesta ni al análisis. Alimenta la pestaña "Optimización"
(sección 6).

### Formato de `/api/figuras/save`

**Request body (JSON):**
```json
{
  "folder":    "C:/ruta/a/simulaciones",
  "yaml_text": "figuras:\n  - num: 1\n    …\n",
  "overwrite": false
}
```

`folder` debe corresponder a una carpeta ya analizada (presente en la caché
de `/api/analyze`); `yaml_text` debe parsear como YAML con una clave
`figuras` de tipo lista. Escribe `<folder>/figuras.yaml` en UTF-8.

**Respuestas:**

- `200 {"ok": true, "path": "C:/ruta/a/simulaciones/figuras.yaml"}` — guardado.
- `404` — `folder` no está en la caché de análisis (ejecutar `/api/analyze` primero).
- `409 {"error": "…", "exists": true}` — ya existe un `figuras.yaml` y `overwrite` no es `true`; el frontend pide confirmación y reintenta con `overwrite: true`.
- `422` — `yaml_text` no parsea o no tiene una clave `figuras` de tipo lista.

### Formato de `/api/isotopo_report`

**Request body (JSON):**
```json
{ "isotopo": "I131", "folder": "C:/ruta/a/simulaciones", "impurezas": null }
```

`impurezas` (Fase 5, opcional) — lista de claves de isótopo a usar como
denominador de la métrica de pureza radionucleídica; si se omite o es
`null`, se usa el criterio por defecto (isótopos del mismo elemento
presentes en el fort.6, ver `isotopos_mismo_elemento`).

**Response (JSON):**
```json
{
  "ok":      true,
  "isotopo": "I131",
  "informe": {
    "nuclear_props": { "T12_s": 693780, "T12_d": 8.025, "lam_s": 9.99e-7, "A_esp": 4.6e15 },
    "gamma_spectrum": [[364.489, 81.5], …],
    "simulations":   { "sim1": { "t_pico": 24.5, "A_pico": 3.2e10, "fase": "irradiación" } },
    "metricas": {
      "sim1": {
        "saturacion":  { "A_sat": 3.4e10, "puntos": [[0, 0], …], "tabla": [{ "pct": 50, "t_x_h": 12.3, "alcanzable": true }, …] },
        "rendimiento": { "rendimiento_medio": 1.3e9, "A_fin": 3.1e10, "ganancia_marginal": 2.1e8, "compensa_seguir": false },
        "pureza":      { "P_pct": 99.2, "t_pico": 24.5, "contribuciones": [{ "iso": "I131", "label": "¹³¹I", "A": 3.2e10, "pct": 99.2 }, …] }
      }
    },
    "isotopos_disponibles":      ["I127", "I130", "I131", …],
    "isotopos_impureza_default": ["I130", "I131", "I132", …],
    "isotopos_impureza_usada":   ["I130", "I131", "I132", …]
  },
  "tabla1":  { … },
  "tabla2":  { … }
}
```

---

## 9. Módulo `fort_analyzer.py`

Motor de análisis principal. Puede importarse de forma independiente al servidor Flask.

### Parsers de ficheros

```python
from fort_analyzer import (
    leer_fort6_irradiacion,   # → (t_irr [h], {iso: atoms/cm³})
    leer_fort6_enfriamiento,  # → (t_cool [h], {iso: Bq/cm³})
    leer_inp5,                # → {T_IRR_h, T_COOL_h, fluxes, xnorm, phi_total, ngrp}
    leer_decay_dat,           # → {iso: T½_s}
)

# Parsear ficheros de una simulación
t_irr, datos_irr  = leer_fort6_irradiacion("simulaciones/sim1/fort.6")
t_cool, datos_cool = leer_fort6_enfriamiento("simulaciones/sim1/fort.6")
params = leer_inp5("simulaciones/sim1/inp.5")
t12 = leer_decay_dat("simulaciones/sim1/DECAY.dat")
```

| Función | Entrada | Salida |
|---------|---------|--------|
| `leer_fort6_irradiacion(path)` | Ruta `fort.6` | `(t_irr_h: ndarray, datos: dict[iso, ndarray])` átomos/cm³ |
| `leer_fort6_enfriamiento(path)` | Ruta `fort.6` | `(t_cool_h: ndarray, datos: dict[iso, ndarray])` Bq/cm³ |
| `leer_fort6_concentraciones(path)` | Ruta `fort.6` | `{"elementos": {SYM: g/cm³}, "total_g_cm3": float}` de `CONCENTRATIONS(GRAM)`, o `None` si la sección no existe |
| `leer_inp5(path)` | Ruta `inp.5` | Dict con `T_IRR_h`, `T_COOL_h`, `phi_total`, `fluxes`, `xnorm`, `ngrp` |
| `leer_decay_dat(path)` | Ruta `DECAY.dat` | `{acab_key: T½_s}` para todos los isótopos de la biblioteca |
| `leer_sweep_manifest(folder)` | Ruta de la carpeta raíz analizada | Dict del `sweep_manifest.json` (Fase 5 opcional, barrido), o `None` si no existe |

### Motor de análisis

```python
from fort_analyzer import (
    analizar_carpeta,           # Análisis completo de una carpeta de simulaciones
    calcular_informe_isotopo,   # Informe de pico + propiedades nucleares
    calcular_tablas_comparativas, # Tablas cruzadas por isótopo de referencia
    build_t12_dict,             # {iso: T½_s} desde dict YAML
    descubrir_simulaciones,     # [(sim_name, fort6_path), …]
    iso_label,                  # "TE131M" → "¹³¹ᵐTe"
    parse_t12,                  # "8.0252 d" → 693782.88  [s]
)

# Análisis completo
all_data, errors = analizar_carpeta(
    folder="C:/simulaciones",
    t12_dict=t12_dict,
    leer_inp5_flag=True,
)

# Informe para el isótopo seleccionado
informe = calcular_informe_isotopo(all_data, "I131", t12_dict)

# Tablas comparativas con I131 como referencia
tabla1, tabla2 = calcular_tablas_comparativas(all_data, all_isotopes, referencia="I131")
```

Unidades de semivida aceptadas por `parse_t12`: `ns`, `µs`, `ms`, `s`, `m`, `h`, `d`, `y` y el valor especial `.inf` para isótopos estables.

### Métricas de optimización de producción (Fase 5)

```python
from fort_analyzer import (
    calcular_saturacion,        # Curva de saturación teórica + tabla de tiempos 50/75/90/95 %
    calcular_rendimiento,       # Rendimiento medio vs. ganancia marginal del último tramo
    calcular_pureza,            # Pureza radionucleídica en un instante dado
    isotopos_mismo_elemento,    # Filtra una lista de isótopos por elemento (criterio por defecto de pureza)
)

sat = calcular_saturacion(sim, "I131", t12_dict)          # None si T½ o T_irr no son válidas
rend = calcular_rendimiento(sim, "I131")                  # None si T_irr <= 0
impurezas = isotopos_mismo_elemento("I131", all_isotopes)  # ["I130", "I131", "I132", …]
pureza = calcular_pureza(sim, "I131", t_pico=pico["t_pico"], isotopos_impureza=impurezas)
```

`calcular_informe_isotopo(all_data, isotopo_key, t12_dict, isotopos_impureza=None)`
integra las tres métricas por simulación en la clave `"metricas"` del informe
devuelto (ver formato de `/api/isotopo_report` en la sección 8); el parámetro
`isotopos_impureza` permite pasar una lista explícita en vez del criterio por
defecto de `isotopos_mismo_elemento`.

---

## 10. Herramientas Auxiliares

| Fichero | Descripción |
|---------|-------------|
| `compare_simulaciones.py` | **[LEGACY]** Comparación standalone Bq/cm³→MBq/g con densidad y datos experimentales embebidos a mano. Reemplazado por el selector de unidades (densidad leída automáticamente) y, para la superposición experimental, por la Fase 4 del runbook |
| `figuras.yaml` | Fichero de configuración de ejemplo con las 16 figuras del análisis del TFG (isótopos de Te, Xe e I) |
| `docs/ejemplo_figuras_TeO2.yaml` | Plantilla YAML de ejemplo (15 figuras) — NO se carga automáticamente; punto de partida para copiar como `figuras.yaml` o cargar por selector |
| `tools/test_fort_analyzer.py` | Tests oro del motor de análisis (parsers y cálculos) contra la simulación de referencia |
| `tools/test_api.py` | Tests de la API REST (flujo `/api/analyze` → `/api/isotopo_report`, `/api/figuras/save` — guardado, discovery, 409/422 — y errores controlados) |
| `tools/test_metricas.py` | Tests oro de las métricas de optimización (Fase 5: saturación, rendimiento, pureza) con curvas sintéticas de solución analítica conocida |
| `tools/test_units.js` | Tests (node) de la conversión pura de unidades `static/js/units.js`. El oráculo numérico equivalente está además en `test_fort_analyzer.py` para el harness Python |
| `tools/test_export.js` | Tests (node) de la generación CSV pura `static/js/export_utils.js` (delimitadores, decimal, entrecomillado, slug) |
| `tools/test_reference_data.js` | Tests (node) del parser/interpolación de datos de referencia `static/js/reference_data.js` (Fase 4: CSV, mapeo de columnas, interpolación, desviación) |
| `tools/test_reference_data.py` | Oráculo Python equivalente: valida los fixtures CSV de `tests/fixtures/experimental/` y reproduce el criterio de aceptación de la Fase 4 (11 puntos legacy de `compare_simulaciones.py` vs. la curva real de `ref_sim`) |
| `tools/test_optim_utils.js` | Tests (node) de la combinación pura `sweep_manifest` + informe `static/js/optim_utils.js` (Fase 5 opcional, pestaña Optimización: merge, claves de parámetro, agrupado por dimensiones, selector de variable Y) |

---

## 11. Tests

La suite son scripts autocontenidos (sin framework) que validan los parsers y
cálculos contra una **simulación de referencia congelada** en
`tests/fixtures/ref_sim/` (`fort.6`, `inp.5`, `DECAY.dat`). Los valores oro
esperados están documentados en `tests/fixtures/README.md`.

```powershell
# Motor de análisis (parsers fort.6 / inp.5 / DECAY.dat + cálculo del pico,
# densidad de CONCENTRATIONS(GRAM) y conversiones de unidad)
C:\venv\acab-venv\Scripts\python tools\test_fort_analyzer.py

# API REST (test_client de Flask, sin arrancar el servidor)
C:\venv\acab-venv\Scripts\python tools\test_api.py

# Oráculo Python de los datos de referencia (Fase 4): fixtures CSV +
# reproducción del criterio de aceptación legacy sobre la ref_sim
C:\venv\acab-venv\Scripts\python tools\test_reference_data.py

# Métricas de optimización de producción (Fase 5): saturación, rendimiento,
# pureza — casos analíticos con curvas sintéticas, no dependen de la ref_sim
C:\venv\acab-venv\Scripts\python tools\test_metricas.py
```

Cada script imprime un resumen `PASS`/`FAIL` y devuelve código de salida `0` si
todo pasa, `1` si algún test falla.

Las funciones puras de frontend (conversión de unidades, exportación CSV y
datos de referencia) tienen además tests con **node**:

```powershell
node tools\test_units.js           # static/js/units.js  (conversión de unidades)
node tools\test_export.js          # static/js/export_utils.js  (generación de CSV)
node tools\test_reference_data.js  # static/js/reference_data.js  (parser CSV, interpolación, desviación)
node tools\test_optim_utils.js     # static/js/optim_utils.js  (Fase 5 opcional: sweep_manifest + informe)
```

Los oráculos numéricos equivalentes de `units.js` y `reference_data.js` están
además espejados en `test_fort_analyzer.py` / `test_reference_data.py`, de modo
que la suite Python cubre los criterios de aceptación aunque no haya node
instalado en la máquina.

**Regla del repositorio:** cualquier cambio en `fort_analyzer.py` (parsers o
cálculos) debe dejar ambas suites en verde y, si añade comportamiento nuevo,
incorporar los tests oro correspondientes usando la simulación de referencia.
