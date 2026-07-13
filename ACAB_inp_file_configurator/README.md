# ACAB INP File Configurator — TFG GIE-TE

> Parte de la [suite ACAB del TFG](../README.md) — configurar entradas → ejecutar → analizar salidas.

**Herramienta gráfica web para la generación y edición de ficheros de entrada de ACABv2008**

**Autores:** Adrian Navarro Minaya · Oscar Luis Cabellos de Francisco
**Centro** Escuela Universitaria de Minas y Energía — Universidad Politécnica de Madrid
**Fecha** Mayo 2026
**Código de simulación:** ACAB 2008 (UPM — Activation code)

---

Desarrollada como parte del Trabajo de Fin de Grado en Ingeniería de la Energía.

![ACAB](https://img.shields.io/badge/NucCalc-ACABv2008-orange) ![Python](https://img.shields.io/badge/Lang-Python314-blue) ![Flask](https://img.shields.io/badge/Web-Flask313-black) ![Bootstrap](https://img.shields.io/badge/Front-Bootstrap533-purple)


---

## Índice

- [ACAB INP File Configurator — TFG GIE-TE](#acab-inp-file-configurator--tfg-gie-te)
  - [Índice](#índice)
  - [1. Descripción](#1-descripción)
  - [2. Tecnologías Utilizadas](#2-tecnologías-utilizadas)
    - [Backend](#backend)
    - [Frontend](#frontend)
    - [Herramienta auxiliar](#herramienta-auxiliar)
    - [Documentación / Datos](#documentación--datos)
  - [3. Estructura del Proyecto](#3-estructura-del-proyecto)
  - [4. Instalación y Puesta en Marcha](#4-instalación-y-puesta-en-marcha)
    - [Requisitos previos](#requisitos-previos)
    - [Opción A — Script automático (recomendado)](#opción-a--script-automático-recomendado)
      - [Windows (PowerShell)](#windows-powershell)
      - [Linux / macOS (Bash)](#linux--macos-bash)
    - [Opción B — Instalación manual](#opción-b--instalación-manual)
    - [Arranque](#arranque)
  - [5. Uso de la Aplicación](#5-uso-de-la-aplicación)
    - [Secciones de la interfaz](#secciones-de-la-interfaz)
    - [Flujo de trabajo](#flujo-de-trabajo)
    - [Comentarios en el fichero](#comentarios-en-el-fichero)
    - [Vista previa del fichero](#vista-previa-del-fichero)
    - [Búsqueda de parámetros por código](#búsqueda-de-parámetros-por-código)
    - [Selector de idioma](#selector-de-idioma)
    - [Herramienta CHAINS](#herramienta-chains)
    - [Ayuda contextual](#ayuda-contextual)
  - [6. API REST](#6-api-rest)
    - [Endpoints CHAINS](#endpoints-chains)
    - [Formato de datos](#formato-de-datos)
  - [7. Módulo Parser (`acab_parser.py`)](#7-módulo-parser-acab_parserpy)
  - [8. Clasificación de los Bloques del Fichero `inp.5`](#8-clasificación-de-los-bloques-del-fichero-inp5)
    - [Sección 1 — Configuración General del Cálculo](#sección-1--configuración-general-del-cálculo)
    - [Sección 2 — Definición Geométrica y Espacial](#sección-2--definición-geométrica-y-espacial)
    - [Sección 3 — Materiales y Flujo](#sección-3--materiales-y-flujo)
    - [Sección 4 — Historial Temporal](#sección-4--historial-temporal)
    - [Sección 5 — Análisis de Incertidumbres](#sección-5--análisis-de-incertidumbres)
    - [Resumen visual](#resumen-visual)
  - [9. Ficheros de Ejemplo](#9-ficheros-de-ejemplo)

---

## 1. Descripción

ACAB (*Activation Code for Accelerator-Based neutron sources*) es un código de cálculo de activación neutrónica desarrollado por el Instituto de Fusión Nuclear (UPM). Su fichero de entrada (`inp.5`) sigue el formato libre de FORTRAN y está organizado en **14 bloques** que pueden resultar difíciles de construir y depurar manualmente.

Este proyecto proporciona:

- Un **parser** completo de ficheros `inp.5` (todos los bloques #1–#14).
- Una **aplicación web** (Flask + Bootstrap 5) que permite editar, visualizar y generar dichos ficheros mediante formularios estructurados con ayuda contextual integrada.
- Una **herramienta de escritorio** auxiliar (Tkinter) para la generación rápida de mallas temporales de irradiación/enfriamiento (Bloques #7/#8).
- Soporte integrado para el utilitario **CHAINS** (análisis de caminos de transmutación), accesible desde el menú *Herramientas* de la misma interfaz web.

---

## 2. Tecnologías Utilizadas

### Backend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Python** | 3.14 | Lenguaje principal |
| **Flask** | 3.1.3 | Framework web (servidor de la aplicación) |
| **Werkzeug** | — *(dep. Flask)* | Manejo de ficheros en uploads |

Únicamente se usan módulos de la biblioteca estándar de Python (`io`, `re`, `pathlib`, `tempfile`, `webbrowser`, `threading`) además de Flask.

### Frontend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Bootstrap** | 5.3.3 | Layout responsivo, componentes UI (cards, modales, colapsos, pestañas) |
| **Bootstrap Icons** | 1.11.3 | Iconografía (CDN) |
| **JavaScript** (Vanilla ES6+) | — | Lógica de la UI: `app.js` |

### Herramienta auxiliar

| Tecnología | Uso |
|------------|-----|
| **Tkinter** (stdlib) | GUI de escritorio para el Generador de Mallas Temporales |

### Documentación / Datos

| Recurso | Descripción |
|---------|-------------|
| `docs/Block#N.md` | Documentación de referencia de cada bloque (extraída del manual de ACAB) |
| `examples/*.5` | ficheros de entrada reales usados como casos de prueba del parser |

---

## 3. Estructura del Proyecto

```
ACAB_INO_FILE_Configurator/
│
├── app.py                  # Servidor Flask + escritor _write_inp5() + rutas CHAINS + rutas de barrido
├── acab_parser.py          # Parser completo de ficheros inp.5
├── chains_handler.py       # Parser + escritor + detección de ficheros CHAINS
├── sweep_writer.py         # Generador de barridos paramétricos (merge de patches, manifest, scripts)
│
├── templates/
│   ├── index.html          # Interfaz web principal (Bootstrap 5)
│   └── chains.html         # Página dedicada a la herramienta CHAINS
│
├── static/
│   ├── css/
│   │   └── style.css       # Estilos personalizados (sobre Bootstrap)
│   └── js/
│       ├── app.js          # Lógica del frontend principal (collectAll, populateAll, etc.)
│       ├── calc_utils.js   # Funciones puras: composición asistida y validador EGRP
│       ├── sweep_utils.js  # Funciones puras del barrido (mallas, patches, sufijos)
│       ├── sweep.js        # Lógica del frontend de la pestaña Barrido
│       └── chains.js       # Lógica del frontend CHAINS
│
├── docs/
│   ├── inp.5.md            # Descripción del formato del fichero de entrada
│   ├── PROCACAB.md         # Documentación del post-procesador PROCACAB
│   ├── chainsCode.md       # Manual de referencia del utilitario CHAINS
│   ├── Block#1.md          # Documentación de cada bloque (#1 al #14)
│   ├── Block#2.md
│   ├── ...
│   └── Block#14.md
│
├── examples/
│   └── *.5                 # ficheros inp.5 de ejemplo (casos reales)
│
├── tools/
│   ├── file_comparator.py       # Utilidad: detección de ficheros duplicados
│   ├── regression_roundtrip.py  # Regresión round-trip del parser/writer
│   ├── test_parser_robustness.py# Robustez del parser + casos negativos
│   ├── test_calc_utils.js       # Tests de calc_utils.js
│   ├── test_validate_all.js     # Tests de las validaciones cruzadas
│   ├── test_sweep_utils.js      # Tests de sweep_utils.js
│   └── test_sweep_endpoint.py   # Tests de los endpoints de barrido
│
└── README.md               # Este fichero
```

---

## 4. Instalación y Puesta en Marcha

### Requisitos previos

- Python 3.10 o superior (probado con 3.14)
- pip

### Opción A — Script automático (recomendado)

Los scripts crean un **entorno virtual fuera del proyecto** e instalan todas las dependencias definidas en `requirements.txt` (`flask`, `waitress`).

#### Windows (PowerShell)

```powershell
# Ruta del entorno por defecto: $DIR$\venv
.\setup.ps1

# Ruta personalizada:
.\setup.ps1 -VenvPath "D:\mis-entornos\acab-venv"
```

Si existe algún problema al generar el entorno porque este roto o por el motivo que sea, ejecutar previamente un borrado del env, y lanzar el setup otra vez

```powershell
# 1. Borrar el venv roto
Remove-Item -Recurse -Force C:\venvs\acab

# 2. Lanzar el setup con esa ruta
.\setup.ps1 -VenvPath C:\venvs\acab
```
> Si PowerShell bloquea la ejecución de scripts, ejecuta previamente:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

#### Linux / macOS (Bash)

```bash
# Dar permisos de ejecución (solo la primera vez)
chmod +x setup.sh

# Ruta del entorno por defecto: ~/acab-venv
./setup.sh

# Ruta personalizada:
./setup.sh /opt/acab-venv
```

### Opción B — Instalación manual

```bash
# 1. Crear entorno virtual en la ubicación deseada
python -m venv /ruta/al/entorno

# 2. Activar el entorno
# Windows:  /ruta/al/entorno/Scripts/Activate.ps1
# Linux:    source /ruta/al/entorno/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Arranque

```powershell
# Windows — usando el intérprete del entorno directamente (sin activar)
.\venv\Scripts\python app.py

# Si el entorno se creó en una ruta personalizada (p. ej. D:\mis-entornos\acab-venv):
D:\mis-entornos\acab-venv\Scripts\python app.py
```

```bash
# Linux — usando el intérprete del entorno directamente (sin activar)
~/acab-venv/bin/python app.py
```

La aplicación abre automáticamente `http://127.0.0.1:5000` en el navegador por defecto.  
El servidor es **Waitress** (WSGI de producción), sin mensajes de advertencia de servidor de desarrollo.

Para la herramienta auxiliar de mallas temporales (Tkinter, sin servidor):

```bash
python generador_acab.py
```

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

Opciones de arranque de esta app: `--port N` (o variable de entorno `ACAB_INP_PORT`;
por defecto 5000) y `--no-browser` (o `ACAB_SUITE_NO_BROWSER=1`) para suprimir la
apertura automática del navegador — es lo que usa el launcher.

---

## 5. Uso de la Aplicación

### Secciones de la interfaz

La interfaz está organizada en **seis secciones** accesibles desde la barra de navegación superior. Cada sección agrupa los bloques del fichero `inp.5` por función:

| Sección | Bloques cubiertos |
|---------|-------------------|
| **Configuración General** | #1 (parámetros globales), #4 (restart), #9 (error/normalización), #10 (productos de fisión) |
| **Definición Geométrica y Espacial** | #2 (malla, zonas, EGRP, CUTOFF, NTO) |
| **Materiales y Flujo** | #3 (flujo neutrónico), #5 (composición inicial), #6 (alimentación continua) |
| **Historial Temporal** | #7/#8 (historial irradiación/enfriamiento), #11 (tipo de cálculo y escenario), #12 (alimentación instantánea), #13 (control de salida) |
| **Análisis de Incertidumbres** | #14 (Monte Carlo, solo activo cuando IUNC = 1) |
| **Barrido paramétrico** | genera N carpetas de simulación variando un parámetro (flujo, masa o historial temporal) sobre el fichero base actual |

Dentro de cada sección, un **menú lateral** permite saltar directamente a cada bloque.

### Flujo de trabajo

```
Nuevo fichero          Cargar fichero existente
      │                        │
      ▼                        ▼
  [Nuevo]            [Cargar inp.5…] → parsea y
      │               rellena todos los formularios
      └──────────┬──────────────┘
                 │
         Editar los campos
         (formularios por bloque)
                 │
         ┌───────┼────────────┬──────────────┐
         │       │            │              │
    [Validar] [Vista previa] [Guardar como]  │
    comprueba  modal con      descarga el    │
    consistencia el fich. .5  fichero .5     │
                                             │
                                    [Búsqueda de código]
                                     navega al campo
```

- **Nuevo** (`Archivo → Nuevo`): inicializa todos los campos con valores por defecto.
- **Cargar inp.5…** (`Archivo → Cargar inp.5…`): parsea un fichero existente y rellena todos los formularios automáticamente.
- **Validar** (`Archivo → Validar`): comprueba la consistencia del fichero antes de guardarlo (grupos de energía, dimensiones de arrays, dependencias entre bloques, etc.). Muestra errores bloqueantes y advertencias no bloqueantes.
- **Guardar como…** (`Archivo → Guardar como…`): genera y descarga el fichero `inp.5` con el nombre elegido.
- **Vista previa del fichero** (`Archivo → Vista previa del fichero`): muestra el contenido completo del fichero generado en un modal, con contador de líneas y botón de copia al portapapeles.

### Comentarios en el fichero

Cada bloque dispone de un área de texto de comentarios (fondo gris, borde discontinuo). El texto introducido se escribe en el fichero resultante como líneas de comentario ACAB (prefijadas con `<`), inmediatamente antes del bloque correspondiente.

### Vista previa del fichero

El modal de vista previa permite inspeccionar el fichero completo antes de descargarlo. Incluye:
- Área de texto monoespaciada de solo lectura.
- Contador de líneas.
- Botón "Copiar al portapapeles".

### Búsqueda de parámetros por código

La barra de navegación incluye un cuadro de búsqueda ("Buscar código…"). Al escribir el nombre de cualquier parámetro ACAB (p. ej. `NGRP`, `IDOSE`, `NOTTS`) aparece un desplegable con los resultados. Al seleccionar uno, la aplicación:

1. Activa la pestaña de sección correcta.
2. Activa el pill del bloque correspondiente.
3. Resalta el campo con una animación amarilla.

Esto permite navegar directamente a cualquier parámetro sin necesidad de recordar en qué sección y bloque se encuentra.

### Selector de idioma

En la esquina superior derecha de la barra de navegación hay un selector de idioma. La aplicación está disponible en **Español** (por defecto) e **English**. La preferencia se guarda en `localStorage` y se restaura en la próxima sesión.

### Herramienta CHAINS

CHAINS es un utilitario de ACAB para el análisis de **caminos de transmutación** entre nucleidos. Sus ficheros de entrada (`input.chain.flagN.txt`) tienen un formato distinto al `inp.5` y se gestionan en una **página dedicada**, accesible desde el menú **Herramientas → CHAINS** de la barra de navegación.

#### Modos de operación (IFLAG)

- **IFLAG = 1** — Todos los caminos hasta el nucleido final (`IFINAL`) con un máximo de `NMAX` pasos.
- **IFLAG = 2** — Caminos entre un nucleido inicial (`INITIAL`) y uno final (`IFINAL`), filtrando por contribución mínima (`PCNT` %).
- **IFLAG = 3** — Todos los caminos hasta `IFINAL`; equivalente al modo 1 sin nucleido de partida fijo.

#### Identificador de nucleido

Los nucleidos se especifican mediante un identificador numérico entero con la fórmula:

```text
ID = Z × 10000 + A × 10 + IS
```

donde `Z` es el número atómico, `A` el número másico e `IS` el estado isomérico (0 = estado fundamental, 1 = isómero metaestable). La interfaz permite introducir `Z`, `A` e `IS` por separado y calcula el ID automáticamente, o bien introducir el ID directamente mediante el panel **"Introducir ID directamente"**.

#### Flujo de trabajo CHAINS

El flujo es análogo al del configurador principal:

- **Nuevo** — inicializa con valores por defecto (IFLAG = 2, Fe-53 → Na-24, NMAX = 4, PCNT = 0,1 %).
- **Cargar** — parsea un fichero `input.chain.*.txt` existente y rellena el formulario.
- **Vista previa** — muestra el fichero que se generaría antes de descargarlo.
- **Guardar como** — genera y descarga el fichero con el nombre indicado.

> **Nota:** si se intenta cargar un fichero CHAINS desde la pantalla principal (`Archivo → Cargar inp.5…`), la aplicación lo detecta automáticamente y muestra un aviso con un enlace directo a la herramienta CHAINS.

### Ayuda contextual

Cada bloque dispone de un botón **"Ayuda"** que despliega un panel con:
- Descripción breve del bloque.
- Tabla de parámetros con su significado y valores posibles.
- Notas sobre condiciones de activación del bloque.

---

## 6. API REST

El servidor Flask expone los siguientes endpoints JSON:

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Sirve la interfaz HTML (`index.html`) |
| `GET` | `/api/new` | Devuelve la estructura de datos con valores por defecto |
| `POST` | `/api/load` | Recibe un fichero `.5` (multipart), lo parsea y devuelve el dict de datos |
| `POST` | `/api/save` | Recibe el dict de datos JSON, genera el texto `inp.5` y lo devuelve como descarga |
| `POST` | `/api/preview` | Recibe el dict de datos JSON y devuelve el texto `inp.5` como string (sin descarga) |
| `POST` | `/api/browse-folder` | Abre un diálogo nativo del SO para elegir carpeta (tkinter en subproceso) y devuelve la ruta seleccionada |
| `POST` | `/api/sweep/preview` | Comprueba un barrido sin escribir nada (rutas, tamaño de la carpeta base, coste en disco, colisiones, sufijos) |
| `POST` | `/api/sweep` | Genera N carpetas de simulación (merge de patches sobre el fichero base, copia de la carpeta base, manifest y scripts) |

### Endpoints CHAINS

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/chains` | Sirve la interfaz HTML de la herramienta CHAINS |
| `GET` | `/api/chains/new` | Devuelve los valores por defecto de un fichero CHAINS |
| `POST` | `/api/chains/load` | Recibe un fichero CHAINS (multipart), lo parsea y devuelve el dict de datos |
| `POST` | `/api/chains/save` | Recibe el dict de datos JSON, genera el texto CHAINS y lo devuelve como descarga |
| `POST` | `/api/chains/preview` | Recibe el dict de datos JSON y devuelve el texto CHAINS como string (sin descarga) |

El endpoint `/api/load` (configurador principal) detecta si el fichero subido es de tipo CHAINS. En ese caso devuelve HTTP 422 con `{"error": "...", "chains": true}` en lugar de intentar parsearlo como `inp.5`.

### Formato de datos

Los endpoints `/api/save` y `/api/preview` esperan un cuerpo JSON con la estructura:

```json
{
  "data": { "block1": {...}, "block2": {...}, ..., "comments": {...} },
  "filename": "mi_calculo.5"
}
```

El campo `data.comments` es un diccionario opcional con claves `block1`, `block2`, …, `block14`, `blocks78`, cuyos valores son cadenas de texto libre que se insertan como comentarios `<` antes de cada bloque.

---

## 7. Módulo Parser (`acab_parser.py`)

Clase `ACABParser` con los métodos públicos:

```python
parser = ACABParser()

# Parsear un fichero inp.5
data = parser.read_inp5('examples/inp.5')

# Parsear un fichero de entrada del post-procesador PROCACAB
proc = parser.read_procacab('procacab_input.txt')
```

El método `read_inp5()` devuelve un diccionario con las claves:

| Clave | Contenido |
|-------|-----------|
| `block1` | `title`, `IUNC`, y 21 parámetros enteros (ITMAX, IZMAX, …, IPUN) |
| `block2` | `XRR`, `YZT`, `MA`, `NUCZO`, `ISOZO`, `EGRP`, `CUTOFF`, `NTO` |
| `block3` | `FLUX` (lista de floats), o `None` si IFLU ≠ 1 |
| `block4` | `IREST` |
| `block5` | Lista de dicts `{'INUCL': [...], 'XCOMP': [...]}` por zona |
| `block6` | Lista de dicts `{'IDNUM': [...], 'XFEED': [...]}` por zona |
| `blocks78` | `sets` (lista de conjuntos temporales con `MMN`, `MOUT`, `TIMES`, …) |
| `block9` | `ERR`, `XNORM` |
| `block10` | `IGFP`, `IWFYD`, `IFORT96` |
| `block11` | `IWP`, `IMTX`, `IDOSE`, `IDHEAT`, …, `NOPUL`, `NTSEQ`, `NOTTS`, `NVFL` |
| `block12` | `IIFD` y tarjetas adicionales si IIFD ≠ 0 |
| `block13` | `NCYO`, `IFSO`, `ICYO`, `ITSO` (o `None` si IUNC = 1) |
| `block14` | `NMOHI`, `NTIMES`, `NCYU`, `IFSU`, `NNUCU`, `ICYU`, `ITSU`, `INUCU` (o `None` si IUNC = 0) |

**Reglas del formato libre de FORTRAN** respetadas por el parser:
- Líneas con `<` en columna 1 → comentario puro (ignorado).
- `<` en cualquier otra posición → comentario en línea (se descarta desde `<` hasta fin de línea).
- Tokens no numéricos (etiquetas inline como `IUNC`, `IWP`…) → descartados silenciosamente.
- Card #1 del Bloque #1 (título) → almacenada como texto crudo, nunca tokenizada.

---

## 8. Clasificación de los Bloques del Fichero `inp.5`

Los 14 bloques del fichero de entrada se agrupan en cinco categorías funcionales, que se corresponden directamente con las cinco secciones de la interfaz:

### Sección 1 — Configuración General del Cálculo

| Bloque | Nombre / Contenido principal |
|--------|------------------------------|
| **#1** | **Cabecera y parámetros generales** — Título, modo de operación (`IUNC`), tamaños de librería (`ITMAX`, `IZMAX`), geometría (`IGE`, `IZM`, `IM`, `JM`), grupos de energía (`NOGG`, `NGRP`), flags de entrada/salida. |
| **#4** | **Opción de reinicio** — `IREST`: 0 = composición inicial de Block #5; 1 = leer de UNIT 37. |
| **#9** | **Error y normalización del flujo** — `ERR` (error de truncado, defecto 1×10⁻²⁵) y `XNORM` (factor de escala global del flujo). |
| **#10** | **Inventario de productos de fisión** — `IGFP` (activar PF), `IWFYD` y `IFORT96` (tipo de librería de rendimientos de fisión, UNIT 96). |

### Sección 2 — Definición Geométrica y Espacial

| Bloque | Nombre / Contenido principal |
|--------|------------------------------|
| **#2** | **Malla, zonas y salida** — `XRR` (límites 1D/2D o volúmenes 3D), `YZT` (límites 2D), `MA` (zona de cada intervalo), `NUCZO` (nucleidos por zona), `ISOZO` (nucleidos de alimentación), `EGRP` (grupos de energía gamma), `CUTOFF` (umbrales de tablas), `NTO` (selección de 18 tablas de salida). |

### Sección 3 — Materiales y Flujo

| Bloque | Nombre / Contenido principal |
|--------|------------------------------|
| **#3** | **Flujos multigrupo** — Flujos escalares neutrónico/protónico en n/cm²·s, dependientes de la energía y el espacio. Solo si `IFLU = 1`. Para `IUNC = 1`: un único valor de flujo total por intervalo. |
| **#5** | **Composición inicial** — `INUCL` (IDs de elementos/isótopos) y `XCOMP` (concentraciones en átomos/barn·cm o g/cc). Se repite por zona. |
| **#6** | **Alimentación continua** — `IDNUM` (IDs) y `XFEED` (tasas en g-átomo/s). Solo si `INFD > 0`. |

### Sección 4 — Historial Temporal

| Bloque | Nombre / Contenido principal |
|--------|------------------------------|
| **#7** | **Control de cada conjunto temporal** — `MMN`, `MOUT`, `NGO`, `MSUB`, `IUNIT` (unidades), `MFEED`, `IOUT`, `IPLOT`. Se repite por conjunto (máx. 10 pasos/conjunto). |
| **#8** | **Tiempos finales** — `TIMES`: hasta 10 valores reales de tiempos finales de cada paso. Se repite junto con #7. |
| **#11** | **Tipo de ejecución y respuestas** — `IWP`, `IMTX`, `IWDR`, `IDOSE`, `IPHCUT`, `IDHEAT`, `IOFFSD`, `ICEDE`, `INEMISS`, `IDAMAGE`; escenario operacional: `NOPUL`, `NTSEQ`, `NOTTS`, `NVFL`. |
| **#12** | **Alimentación instantánea** — `IIFD`, composición y calendario de aportes puntuales de material. |
| **#13** | **Control de salida** — `NCYO`, `IFSO`, `ICYO`, `ITSO`: selección de ciclos y conjuntos para los que se imprime salida por zona. No se usa si `IUNC = 1`. |

### Sección 5 — Análisis de Incertidumbres

| Bloque | Nombre / Contenido principal |
|--------|------------------------------|
| **#14** | **Cálculo Monte Carlo** — Solo si `IUNC = 1`. `NMOHI` (historias), `NTIMES` (instantes de interés), `NCYU`/`IFSU` (ciclos/serie final), `NNUCU`/`INUCU` (nucleidos para incertidumbre en concentración). Requiere la librería colapsada `XSUNC.dat`. |

### Resumen visual

```
inp.5 de ACABv2008
│
├── Configuración General       → Bloques #1, #4, #9, #10
├── Definición Geométrica       → Bloque  #2
├── Materiales y Flujo          → Bloques #3, #5, #6
├── Historial Temporal          → Bloques #7, #8, #11, #12, #13
└── Análisis de Incertidumbres  → Bloque  #14  (solo IUNC = 1)
```

> **Nota sobre el Bloque #2:** tiene carácter mixto; sus primeras tarjetas (`XRR`, `YZT`, `MA`, `NUCZO`, `EGRP`) pertenecen a la geometría, mientras que las últimas (`CUTOFF`, `NTO`) controlan la salida.

---

## 9. Ficheros de Ejemplo

El directorio `examples/` contiene **ficheros `inp.5`** reales, incluyendo casos de aplicación a la primera pared de reactores de fusión (NIF, etc.). Todos han sido parseados correctamente con `acab_parser.py` y sirven como casos de prueba de regresión.

```bash
# Verificar que el parser lee todos los ejemplos sin errores
python - <<'EOF'
from acab_parser import ACABParser
from pathlib import Path
parser = ACABParser()
for f in sorted(Path('examples').glob('*.5')):
    data = parser.read_inp5(f)
    print(f"OK  {f.name}")
EOF
```

---

## 10. Validación y mejoras (julio 2026)

### Suite de tests

```bash
# Regresión round-trip (parsear → regenerar → comparar semántica y tokens)
python tools/regression_roundtrip.py ruta/a/exp1_inp.5 [más ficheros...]

# Robustez del parser + casos negativos (usa un inp.5 de referencia)
python tools/test_parser_robustness.py ruta/a/exp1_inp.5

# Funciones puras de la composición asistida y del validador EGRP
node tools/test_calc_utils.js

# Validaciones cruzadas V23–V25 de validateAll (stubs de DOM)
node tools/test_validate_all.js

# Funciones puras del generador de barridos (mallas, patches, sufijos)
node tools/test_sweep_utils.js

# Endpoints /api/sweep y /api/sweep/preview (merge, copia, manifest, límites)
python tools/test_sweep_endpoint.py
```

### Composición asistida del Bloque #5

En la pestaña del Bloque #5 se puede alternar entre introducir las
concentraciones manualmente (comportamiento clásico) o calcularlas a partir de
la masa del blanco. Entradas: compuesto (fórmula química como `TeO2` o lista
`Te:1 O:2`), masa [g] y volumen de zona [cm³] (por defecto 1; con IGE=4 se
avisa si difiere de la componente XRR de la zona). Fórmula validada (INPT=1):
`XCOMP_i = (m·w_i/M_i)·N_A/(10²⁴·V)` en átomos/barn·cm; con INPT=3 se entrega
`m·w_i/V` en g/cc. El modo calculado no soporta INPT=2 (isótopos).
Librería de datos: `static/data/atomic_data.json` (masas atómicas estándar
CIAAW y densidades de compuestos habituales, con nota sobre las abundancias
del DECAY.dat de ACAB).

### Presets de EGRP (Bloque #2, Card #6)

Librería `static/data/egrp_presets.json` con estructuras estándar documentadas
(24 grupos del ejemplo NIF del manual de ACAB 2008 y 18 grupos del ejemplo
del Bloque #2 del mismo manual). Al
aplicar un preset se fija NOGG automáticamente en el Bloque #1. El textarea
tiene validación en vivo (NOGG+1 valores, estrictamente decreciente, última
frontera ≥ 0). Recordatorio en la interfaz: EGRP solo afecta al espectro gamma
de salida (ILIB/IPUN), no al inventario ni a las actividades.

Nota (manual ACAB 2008, Secciones IV y V): la fuente gamma procede de
PHOTON.dat, líneas discretas por nucleido que ACAB agrupa en los NOGG grupos
del usuario. No hay librería gamma multigrupo interna, por lo que EGRP no
tiene límites de energía ni granularidad mínima impuestos; las fronteras por
encima de la línea más energética solo producen grupos vacíos. Si se piden
dosis (IDOSE=1), la librería de atenuación cubre 1 keV - 20 MeV, así que
conviene mantener EGRP dentro de 0-20 MeV.

### Validaciones nuevas

- **V23**: EGRP estrictamente decreciente y última frontera ≥ 0.
- **V24**: coherencia INPT ↔ tipo de identificadores del Bloque #5.
- **V25**: reglas de los sets de Bloques #7/#8 (MOUT ∈ [1,10], MMN ≤ MOUT,
  len(TIMES) = MOUT, encadenado NGO/MSUB).

Además, el writer ya no fabrica un `0.000000E+00` silencioso ante listas de
reales vacías (error claro con el nombre del campo) y los errores del parser
incluyen el bloque en curso y el token ofensivo.

### Decisiones documentadas y cuestiones pendientes (julio 2026)

**Limitación conocida del writer (precisión de reales).** El writer formatea
los reales con `_sci(v, prec=6)`, es decir, 7 cifras significativas. Un
fichero cuyo original tenga valores con más cifras (p. ej.
`2.139394737E-02` en `examples/Activation of TeO2 Experiment 1.5`) se
regenera con esos valores redondeados (`2.139395E-02`); la herramienta
`tools/regression_roundtrip.py` lo detecta como diferencia de token. Los 4
patrones oro usan 6 decimales y no se ven afectados. Si en el futuro hiciera
falta conservar más precisión, bastaría subir `prec` en `_sci` (`app.py`) y
re-ejecutar la regresión.

### Barrido paramétrico

La pestaña **Barrido paramétrico** genera, a partir del fichero base cargado y
**válido**, N carpetas de simulación variando **un único** parámetro y dejando
fijo el resto del fichero. La pestaña re-ejecuta `validateAll()` al entrar y
antes de generar: si el fichero base tiene errores, se listan y se deshabilita
previsualizar/generar.

La carpeta raíz y la carpeta base pueden escribirse a mano o elegirse con el
botón de examinar (📁), que abre el diálogo de carpetas nativo del sistema
operativo (endpoint `/api/browse-folder`) para evitar errores de tecleo.

Tipos de barrido (excluyentes) y qué queda congelado en cada uno:

| Tipo | Qué varía | Qué queda congelado |
|------|-----------|---------------------|
| **Flujo** | `block9.XNORM` (factor multiplicativo del flujo) | composición, geometría e historial temporal. Admite dos modos de entrada: valores de XNORM directos, o flujo total objetivo (XNORM = φ_objetivo/φ_base, con φ_base = Σ Bloque #3 × XNORM base) |
| **Masa** | `XCOMP` de una zona objetivo | INUCL y la estructura de todas las zonas; compuesto y volumen fijos. Al mantener el volumen fijo, **variar la masa equivale a variar la densidad de empaquetado** del blanco. No disponible con INPT = 2 (isótopos) |
| **Temporal** | Bloques #7/#8 (historial) y `block11.NOTTS` | resto del fichero. Cada fila define fases de irradiación/enfriamiento; los campos vacíos conservan la fase del fichero base |

> **Nota física (flujo).** XNORM escala la **magnitud** del flujo, no la
> **forma** del espectro (las secciones eficaces colapsadas con COLLAPS siguen
> siendo válidas en todo el barrido). Si el escenario real cambia la forma del
> espectro, hay que regenerar con COLLAPS, no con XNORM.

**Salida.** En la carpeta raíz se crean, por simulación, subcarpetas
`<prefijo><sufijo>` (sufijo auto-propuesto y editable: `x0.75`, `m1.500g`,
`Tirr024.0h`). Cada subcarpeta recibe una copia recursiva del contenido de la
**carpeta base** (librerías y ficheros auxiliares) y su `inp.5` generado, que
**reemplaza** cualquier `inp.5` presente en la carpeta base. Además, en la raíz
se escriben:

- `sweep_manifest.json` — timestamp, tipo de barrido, descripción, parámetros
  fijos y lista `[{folder, params}]`.
- `sweep_manifest.csv` — `folder` + una columna por parámetro.
- `README.txt` — descripción y resumen legible del barrido.
- `run_all.ps1` / `run_all.sh` — bucle que entra en cada subcarpeta y ejecuta
  ACAB (`$ACAB_EXE` a rellenar), redirigiendo la salida a `run.log`.

**Límites y seguridad.** Máximo 200 simulaciones (HTTP 422); confirmación en la
interfaz si N > 30 y aviso destacado si el coste en disco estimado
(tamaño de la carpeta base × N) supera 2 GB. Las colisiones con subcarpetas
existentes devuelven HTTP 409 salvo que se confirme sobrescribir. Cada `inp.5`
generado se verifica re-parseándolo (round-trip) antes de escribir; si alguno
falla, se aborta **todo** el barrido y se limpia lo ya escrito.

### Barrido espectral (COLLAPS)

Cuarto tipo de barrido de la pestaña "Barrido": en lugar de variar un valor
del `inp.5`, varía la **forma** del espectro neutrónico que COLLAPS colapsa a
la librería de secciones eficaces (tarjeta 7/FT y tarjeta 6/CX del `COLL.inp`),
importando espectros externos publicados en formato **CONDERC** del OIEA
([https://nds.iaea.org/conderc/spectra](https://nds.iaea.org/conderc/spectra)).
Pregunta que responde: a igualdad de densidad de flujo total, ¿en qué tipo de
reactor (térmico, epitérmico, rápido…) es más eficaz la producción del
radioisótopo?

**Qué NO toca este barrido.** El `inp.5` queda intacto salvo, opcionalmente,
un único valor: si se edita el campo **φ_ref** de la pestaña (prefijado con el
Bloque #3 del fichero base), ese mismo valor se aplica como flujo total a
**todas** las simulaciones (patch uniforme). `XNORM` (Bloque #9) no se toca —
queda reservado al barrido de flujo, y permite en el futuro combinar espectro
× flujo.

**Por qué la comparación es "a flujo total igual" sin normalizar nada.** El
colapso de COLLAPS es una media ponderada por el espectro: la magnitud
absoluta del flujo (FT) se cancela en el resultado, solo importa su forma.
Con el Bloque #3 idéntico en todas las simulaciones (por construcción, salvo
que se edite φ_ref), comparar reactores entre sí ya es "a igualdad de flujo
total" sin ningún factor de normalización numérico. Normalizar el FT a suma 1
al importar es puramente **cosmético**, para que la gráfica de espectros
superpuestos sea comparable visualmente.

**`FLUX.inf` es un verificador, nunca una fuente.** Tras cada ejecución de
COLLAPS, el pipeline lee de `FLUX.inf` el flujo total real, la energía media y
el eco de los parámetros de librería (ILIB/IESF/NGROUP), y los anota en
`batch_results.json`/manifest para control. Ningún valor de `FLUX.inf` se
copia jamás a un fichero de entrada.

**Formato CONDERC importado** (fichero `.txt`/`.csv` con cabecera `GROUP UPPER
LOWER LETHARGY DATA DATA/LETHARGY`, una fila por grupo, energías en eV y una
línea final `TOTAL <valor>`): la importación es una **transcripción directa**,
sin reagrupar (rebinning) — la conversión de estructura de grupos la hace
COLLAPS internamente (IESF=5 + tarjeta CX). Del fichero se toman: `NGROUP` con
signo autodetectado según el fichero venga en energías crecientes o
decrecientes (mostrado en la UI para confirmación visual), la tarjeta `CX`
(las N+1 fronteras del fichero, columna UPPER + última LOWER) y la tarjeta
`FT` (columna DATA, en el orden del fichero). La línea `TOTAL` se usa como
checksum del parser (Σ DATA, tolerancia relativa 1×10⁻³); si no cuadra, se
rechaza el fichero con un mensaje claro. Única transformación de unidades: las
fronteras de energía se convierten de eV (CONDERC) a MeV (unidad de la
tarjeta CX de COLL.inp), multiplicando por 10⁻⁶ — los valores de FT no se
convierten (son flujos integrales por grupo, adimensionales respecto a la
unidad de energía).

**Criterio de rango completo (espectros medidos/EXFOR).** Algunos espectros
publicados en CONDERC proceden de medidas experimentales (origen EXFOR) y
pueden cubrir solo una parte del rango de energía. Para comparar reactores
entre sí solo son válidos espectros de **rango completo**: la frontera
inferior del fichero debe alcanzar la región térmica. La columna **"Rango de
energía"** (E_min–E_max) de la tabla de espectros de la pestaña hace este
criterio visible de un vistazo — un E_min en el rango de keV delata un
espectro parcial. El síntoma equivalente en los índices espectrales es una
fracción térmica del 0,0 % en lo que debería ser un reactor térmico.

**Aviso direccional.** Si el número de grupos del espectro importado (|N|) es
menor que el de la librería XSBL (211 grupos), la fila muestra un badge de
aviso: expandir un espectro con menos grupos que la librería es la operación
menos fiable de la transcripción. Es informativo, no bloquea la importación
(el propio espectro de referencia MURR-G1 de CONDERC, con 112 grupos, lo
lleva y aun así es válido).

**Índices espectrales.** Por cada espectro importado se calculan tres
fracciones (reparto plano por letargia en el grupo que contiene cada
frontera): **térmica** (E < 0,625 eV), **epitérmica** (0,625 eV – 0,1 MeV) y
**rápida** (> 0,1 MeV). Se guardan en el manifest junto con la etiqueta y el
número de grupos, de forma que la pestaña "Optimización" del Fort Analyzer
puede graficar directamente A_pico frente a la fracción térmica sin cambios.

**Ejecución (pipeline collaps → acab).** Cada simulación del barrido
espectral es un pipeline de varios pasos, no una única ejecución: 1) `collaps.exe`
sobre el `COLL.inp` parcheado con el espectro de esa fila; 2) copia de
`XSECTION.dat` generado por COLLAPS a la carpeta de la simulación;
3) `acab.exe` sobre esa carpeta; 4) lectura de verificación de `FLUX.inf`. La
carpeta base del barrido debe incluir una subcarpeta `collaps/` con
`collaps.exe`, `XSBL.dat` y un `COLL.inp` de partida. Un fallo en cualquier
paso marca esa simulación como fallida (con el paso responsable indicado) sin
detener el resto de la cola. La fila de cada simulación en curso muestra el
paso activo ("collaps / copiar / acab").