# COLLAPS INP File Configurator — TFG GIE-TE

> Parte de la [suite ACAB del TFG](../README.md) — configurar entradas → ejecutar → analizar salidas.

**Herramienta gráfica web para la generación y edición de ficheros de entrada de COLLAPS**

> **Manual de usuario** (orientado a tareas, sin detalle de arquitectura ni tests): [`docs/manual_usuario.md`](docs/manual_usuario.md).

**Autores:** Adrian Navarro Minaya · Oscar Luis Cabellos de Francisco  
**Centro:** Escuela Universitaria de Minas y Energía — Universidad Politécnica de Madrid  
**Fecha:** Mayo 2026  
**Código de simulación:** COLLAPS (preprocesador de secciones eficaces para ACABv2008)

---

![NucCalc](https://img.shields.io/badge/NucCalc-COLLAPS-orange) ![Python](https://img.shields.io/badge/Lang-Python314-blue) ![Flask](https://img.shields.io/badge/Web-Flask313-black) ![Bootstrap](https://img.shields.io/badge/Front-Bootstrap533-purple)

---

## Índice

- [COLLAPS INP File Configurator — TFG GIE-TE](#collaps-inp-file-configurator--tfg-gie-te)
  - [Índice](#índice)
  - [1. Descripción](#1-descripción)
  - [2. Tecnologías Utilizadas](#2-tecnologías-utilizadas)
    - [Backend](#backend)
    - [Frontend](#frontend)
  - [3. Estructura del Proyecto](#3-estructura-del-proyecto)
  - [4. Instalación y Puesta en Marcha](#4-instalación-y-puesta-en-marcha)
    - [Requisitos previos](#requisitos-previos)
    - [Opción A — Script automático (recomendado, Windows)](#opción-a--script-automático-recomendado-windows)
    - [Opción B — Instalación manual](#opción-b--instalación-manual)
    - [Arranque](#arranque)
  - [5. Uso de la Aplicación](#5-uso-de-la-aplicación)
    - [Secciones de la interfaz](#secciones-de-la-interfaz)
    - [Flujo de trabajo](#flujo-de-trabajo)
    - [Vista previa del fichero](#vista-previa-del-fichero)
    - [Selector de idioma](#selector-de-idioma)
    - [Ayuda contextual](#ayuda-contextual)
  - [6. API REST](#6-api-rest)
    - [Formato de datos](#formato-de-datos)
  - [7. Módulo Parser (`collaps_parser.py`)](#7-módulo-parser-collaps_parserpy)
  - [8. Descripción de las Tarjetas del Fichero `COLL.inp`](#8-descripción-de-las-tarjetas-del-fichero-collinp)
    - [Tarjeta #1 — Estructura de grupos](#tarjeta-1--estructura-de-grupos)
    - [Tarjeta #2 — Cabecera de la librería](#tarjeta-2--cabecera-de-la-librería)
    - [Tarjeta #3 — Modo de fisión](#tarjeta-3--modo-de-fisión)
    - [Tarjeta #4 — Fronteras energéticas de fisión](#tarjeta-4--fronteras-energéticas-de-fisión)
    - [Tarjeta #5 — Espectro neutrónico](#tarjeta-5--espectro-neutrónico)
    - [Tarjeta #6 — Fronteras de energía personalizadas](#tarjeta-6--fronteras-de-energía-personalizadas)
    - [Tarjeta #7 — Valores del flujo](#tarjeta-7--valores-del-flujo)
    - [Tarjeta #8 — Modo de incertidumbres](#tarjeta-8--modo-de-incertidumbres)
    - [Tarjeta #9 — Modo de ejecución](#tarjeta-9--modo-de-ejecución)
    - [Resumen visual](#resumen-visual)
  - [9. Ficheros de Ejemplo](#9-ficheros-de-ejemplo)

---

## 1. Descripción

COLLAPS es el código preprocesador de secciones eficaces del sistema ACAB (*Activation Code for Accelerator-Based neutron sources*), desarrollado por el Instituto de Fusión Nuclear (UPM). Su función principal es **colapsar librerías de secciones eficaces multigrupo** (en formato EAF) a un único grupo de energía, ponderando con el espectro neutrónico del problema. Su fichero de entrada (`COLL.inp`) consta de **9 tarjetas** en formato libre FORTRAN que, aunque compacto, requiere precisión en la especificación de los parámetros.

COLLAPS opera en tres modos controlados por los parámetros `ISFIS` e `IUNC3G`:

| Modo | Parámetro | Descripción |
|------|-----------|-------------|
| **Estándar** | `ISFIS = 0` | Colapso de la librería de secciones eficaces de activación a 1 grupo. |
| **Fisión** | `ISFIS = 1` | Además del colapso estándar, procesa rendimientos de fisión y genera librerías de secciones eficaces de rendimiento de fisión efectivas. |
| **Incertidumbres** | `IUNC3G = 1` | Procesa la librería de incertidumbres de secciones eficaces junto con el espectro para generar una librería colapsada con información de incertidumbre. |

Este proyecto proporciona:

- Un **parser** completo del fichero `COLL.inp` (las 9 tarjetas, incluyendo las condicionales #4 y #6).
- Una **aplicación web** (Flask + Bootstrap 5) que permite crear, editar, visualizar y generar el fichero de entrada mediante formularios estructurados con ayuda contextual integrada.

> **Nota:** Este proyecto es **hermano** del [ACAB INP File Configurator](../ACAB_inp_file_configurator). Comparten arquitectura, look & feel (navbar oscuro, Bootstrap 5.3.3, Bootstrap Icons, i18n ES/EN) y estilo de código. La salida de COLLAPS (`XSECTION.dat`, `FYL.dat`, `XSUNC.dat`…) es la entrada de ACAB.

---

## 2. Tecnologías Utilizadas

### Backend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Python** | 3.14 | Lenguaje principal |
| **Flask** | 3.1.3 | Framework web (servidor de la aplicación) |
| **Waitress** | ≥ 3.0.2 | Servidor WSGI de producción (sin avisos de desarrollo) |

Únicamente se usan módulos de la biblioteca estándar de Python (`io`, `re`, `pathlib`, `tempfile`, `webbrowser`, `threading`, `collections`) además de Flask y Waitress.

### Frontend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Bootstrap** | 5.3.3 | Layout responsivo, componentes UI (cards, modales, pestañas) |
| **Bootstrap Icons** | 1.11.3 | Iconografía (CDN) |
| **JavaScript** (Vanilla ES6+) | — | Lógica de la UI: `app.js` |

---

## 3. Estructura del Proyecto

```
COLLAPS_inp_file_configurator/
│
├── app.py                  # Servidor Flask + escritor _write_coll_inp()
├── collaps_parser.py       # Parser completo de COLL.inp
├── requirements.txt        # flask>=3.1.3, waitress>=3.0.2
├── setup.ps1               # Script de instalación (Windows PowerShell)
│
├── templates/
│   └── index.html          # Interfaz web principal (Bootstrap 5.3.3)
│
├── static/
│   ├── css/
│   │   └── style.css       # Estilos personalizados (sobre Bootstrap)
│   ├── js/
│   │   └── app.js          # Lógica del frontend (collectUI, populateUI, etc.)
│   └── i18n/
│       ├── es.json         # Traducciones en español
│       └── en.json         # Traducciones en inglés
│
├── docs/
│   └── COLLAPS.md          # Manual de referencia de COLLAPS (extraído del manual oficial)
│
└── examples/               # 18 casos de uso reales
    ├── example1/collaps/COLL.inp
    ├── example2/collaps/COLL.inp
    ├── ...
    ├── example13/collaps_damage/COLL.inp   # caso con librería de daño
    ├── example16/collaps_neutrons/COLL.inp # caso con flujo neutrónico
    ├── example16/collaps_protons/COLL.inp  # caso con flujo protónico
    └── example18/collaps/COLL.inp
```

---

## 4. Instalación y Puesta en Marcha

### Requisitos previos

- Python 3.10 o superior (probado con 3.14)
- pip

### Opción A — Script automático (recomendado, Windows)

El script crea un **entorno virtual** e instala todas las dependencias definidas en `requirements.txt` (`flask`, `waitress`).

```powershell
# Ruta del entorno por defecto: .\venv
.\setup.ps1

# Ruta personalizada:
.\setup.ps1 -VenvPath "D:\mis-entornos\collaps-venv"
```

Si el entorno queda roto o hay que recrearlo:

```powershell
# 1. Borrar el venv roto
Remove-Item -Recurse -Force .\venv

# 2. Lanzar el setup de nuevo
.\setup.ps1
```

> Si PowerShell bloquea la ejecución de scripts, ejecuta previamente:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

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

# Si el entorno se creó en una ruta personalizada:
D:\mis-entornos\collaps-venv\Scripts\python app.py

# Puerto alternativo:
.\venv\Scripts\python app.py --port 8080
```

```bash
# Linux — usando el intérprete del entorno directamente (sin activar)
~/collaps-venv/bin/python app.py
```

La aplicación abre automáticamente `http://127.0.0.1:5002` en el navegador por defecto.  
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

Opciones de arranque de esta app: `--port N` (o variable de entorno `PORT`; por
defecto 5002) y `--no-browser` (o `ACAB_SUITE_NO_BROWSER=1`) para suprimir la
apertura automática del navegador — es lo que usa el launcher.

---

## 5. Uso de la Aplicación

### Secciones de la interfaz

La interfaz está organizada en **cuatro pestañas** accesibles desde la barra de navegación superior. Cada pestaña agrupa las tarjetas del fichero `COLL.inp` por función:

| Pestaña | Tarjetas cubiertas |
|---------|--------------------|
| **Biblioteca** | #1 (estructura de grupos de la librería XS y del flujo), #2 (cabecera de la librería) |
| **Fisión** | #3 (flags del modo de fisión: `ISFIS`, `IGEN`, `ISOCA`, `IBEST`), #4 (fronteras energéticas `EB1`/`EB2`, solo si `ISFIS ≠ 0`) |
| **Flujo Neutrónico** | #5 (número de grupos y unidades del flujo), #6 (fronteras energéticas personalizadas, solo si `IESF = 5`), #7 (valores del espectro neutrónico `FT`) |
| **Opciones** | #8 (modo de incertidumbres `IUNC3G`), #9 (modo de ejecución `ISTOP`) |

Las tarjetas condicionales **#4** y **#6** aparecen y desaparecen automáticamente según los valores de `ISFIS` e `IESF` respectivamente.

### Flujo de trabajo

```
Nuevo fichero          Cargar fichero existente
      │                        │
      ▼                        ▼
  [Nuevo]            [Cargar COLL.inp…] → parsea y
      │               rellena todos los formularios
      └──────────────┬────────────────────
                     │
             Editar los campos
             (formularios por tarjeta)
                     │
         ────────────┼──────────────────────
         │           │           │
    [Vista previa] [Guardar como…]  [Nuevo]
    modal con       descarga el     reinicia
    el fich. .inp   fichero .inp    formulario
```

- **Nuevo** (`Archivo → Nuevo`): inicializa todos los campos con valores por defecto (Vitamin-J 175 grupos, espectro plano, modo estándar).
- **Cargar COLL.inp…** (`Archivo → Cargar COLL.inp…`): parsea un fichero existente y rellena todos los formularios automáticamente, incluyendo la visibilidad de las tarjetas condicionales.
- **Guardar como…** (`Archivo → Guardar como…`): genera y descarga el fichero `COLL.inp` con el nombre elegido.
- **Vista previa del fichero** (`Archivo → Vista previa del fichero`): muestra el contenido completo del fichero generado en un modal, con contador de líneas y botón de copia al portapapeles.

### Vista previa del fichero

El modal de vista previa permite inspeccionar el fichero completo antes de descargarlo. Incluye:
- Área de texto monoespaciada de solo lectura.
- Contador de líneas.
- Botón "Copiar al portapapeles".

### Selector de idioma

En la esquina superior derecha de la barra de navegación hay un selector de idioma. La aplicación está disponible en **Español** (por defecto) e **English**. La preferencia se guarda en `localStorage` y se restaura en la próxima sesión.

### Ayuda contextual

Cada tarjeta dispone de un botón **"Ayuda"** que despliega un panel con:
- Descripción breve de la tarjeta.
- Tabla de parámetros con su significado, formato y valores posibles.
- Notas sobre las condiciones de activación de la tarjeta.

---

## 6. API REST

El servidor Flask expone los siguientes endpoints JSON:

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Sirve la interfaz HTML (`index.html`) |
| `GET` | `/api/new` | Devuelve la estructura de datos con valores por defecto |
| `POST` | `/api/load` | Recibe un fichero `.inp` (multipart), lo parsea y devuelve el dict de datos |
| `POST` | `/api/save` | Recibe el dict de datos JSON, genera el texto `COLL.inp` y lo devuelve como descarga |
| `POST` | `/api/preview` | Recibe el dict de datos JSON y devuelve el texto `COLL.inp` como string (sin descarga) |

### Formato de datos

Los endpoints `/api/save` y `/api/preview` esperan un cuerpo JSON con la estructura:

```json
{
  "data": {
    "card1": { "ILIB": 2, "IESF": 2 },
    "card2": { "IHEAD": 16 },
    "card3": { "ISFIS": 0, "IGEN": 0, "ISOCA": 1, "IBEST": 1 },
    "card4": null,
    "card5": { "NGROUP": -175, "FF": 0 },
    "card6": null,
    "card7": { "FT": [1.0, 1.0, "..."] },
    "card8": { "IUNC3G": 0 },
    "card9": { "ISTOP": 0 }
  },
  "filename": "COLL.inp"
}
```

`card4` y `card6` son `null` cuando sus tarjetas no aplican (`ISFIS = 0` y `IESF ≠ 5` respectivamente).

---

## 7. Módulo Parser (`collaps_parser.py`)

Clase `COLLAPSParser` con el método público:

```python
parser = COLLAPSParser()

# Parsear un fichero COLL.inp
data = parser.read_coll_inp('examples/example1/collaps/COLL.inp')
```

El método `read_coll_inp()` devuelve un diccionario con las claves:

| Clave | Contenido |
|-------|-----------|
| `card1` | `ILIB`, `IESF` — códigos de estructura de grupos (librería y flujo) |
| `card2` | `IHEAD` — número de líneas de cabecera de la librería de secciones eficaces |
| `card3` | `ISFIS`, `IGEN`, `ISOCA`, `IBEST` — flags del modo de fisión |
| `card4` | `EB1`, `EB2` — fronteras energéticas (eV) de las regiones de fisión, o `None` si `ISFIS = 0` |
| `card5` | `NGROUP`, `FF` — número de grupos del espectro (negativo = energía decreciente) y unidades |
| `card6` | `CX` — lista de `ABS(NGROUP)+1` fronteras energéticas, o `None` si `IESF ≠ 5` |
| `card7` | `FT` — lista de `ABS(NGROUP)` valores del flujo neutrónico |
| `card8` | `IUNC3G` — flag de modo de incertidumbres |
| `card9` | `ISTOP` — flag de modo de ejecución |

**Características del parser:**

- Parseo por **cola de tokens** (`deque`): las líneas se tokenizan y los valores se consumen secuencialmente, ignorando etiquetas de texto no numéricas.
- Soporte completo de números FORTRAN: exponente `D`/`d` (`3.5D+07`), exponente desnudo (`3.2336+27`), punto inicial (`.00E+00`).
- `_parse_fortran_float(tok)` normaliza el token antes de llamar a `float()`.

**Autotest rápido desde la línea de comandos:**

```bash
# Verificar que el parser lee todos los ejemplos sin errores
python - <<'EOF'
from collaps_parser import COLLAPSParser
from pathlib import Path
parser = COLLAPSParser()
for f in sorted(Path('examples').rglob('COLL.inp')):
    data = parser.read_coll_inp(f)
    c1, c5, c7 = data['card1'], data['card5'], data['card7']
    print(f"OK  {f}  ILIB={c1['ILIB']} NGROUP={c5['NGROUP']} FT={len(c7['FT'])}val")
EOF

# O probar un fichero concreto con salida detallada:
python collaps_parser.py examples/example1/collaps/COLL.inp
```

---

## 8. Descripción de las Tarjetas del Fichero `COLL.inp`

El fichero de entrada de COLLAPS consta de **9 tarjetas** en formato FORTRAN (libre o fijo según la tarjeta). Las tarjetas #4 y #6 son **condicionales**: solo aparecen en el fichero si se cumplen determinadas condiciones.

### Tarjeta #1 — Estructura de grupos

**Formato:** `2I4` (dos enteros de 4 caracteres cada uno)

| Parámetro | Descripción |
|-----------|-------------|
| `ILIB` | Estructura de grupos de la **librería de secciones eficaces** (EAF) |
| `IESF` | Estructura de grupos usada para el **espectro neutrónico** de entrada |

**Códigos de estructura de grupos** (válidos para `ILIB` y `IESF`):

| Código | Nombre | Grupos |
|--------|--------|--------|
| `1` | GAM-II | 100 |
| `2` | Vitamin-J | 175 |
| `3` | TART-175 | 175 |
| `4` | TART-566 | 566 |
| `5` | Otra (arbitraria) | — (requiere Tarjeta #6) |
| `12` | Vitamin-J+ | 211 |

### Tarjeta #2 — Cabecera de la librería

**Formato:** libre

| Parámetro | Descripción |
|-----------|-------------|
| `IHEAD` | Número de líneas de cabecera informativa de la librería de secciones eficaces (`XSBL.dat`) |

### Tarjeta #3 — Modo de fisión

**Formato:** libre (4 enteros)

| Parámetro | Descripción |
|-----------|-------------|
| `ISFIS` | `0` = modo estándar (sin fisión). `1` = modo fisión: procesa rendimientos de fisión y genera la librería de rendimientos efectivos. |
| `IGEN` | `0` = operación estándar de fisión. `1` = genera las librerías EFY extendidas (`EFYBL.dat`, `EFYAXSL.dat`) y detiene la ejecución (no se generan secciones eficaces de rendimiento). |
| `ISOCA` | `0` = lee la librería EFY extendida desde la unidad 18. `1` = lee y procesa la librería básica de rendimientos de fisión desde la unidad 17 (`FYBL.dat`). |
| `IBEST` | `0` = la librería de secciones eficaces de rendimiento (unidad 96) se genera para los nucleidos fisibles de la librería de rendimientos JEF-2.2/JEFF3.1. `1` = se genera para todos los nucleidos fisibles de la librería de activación. |

### Tarjeta #4 — Fronteras energéticas de fisión

**Condición:** solo presente si `ISFIS ≠ 0`  
**Formato:** libre (2 reales)

| Parámetro | Descripción |
|-----------|-------------|
| `EB1` | Frontera superior de la región de energía media (eV). Valor recomendado: `5.0E+06` (5 MeV) |
| `EB2` | Frontera superior de la región de energía baja (eV). Valor recomendado: `2.0E+05` (200 keV) |

Las tres regiones energéticas resultantes son: `E > EB1` (alta), `EB2 < E < EB1` (media), `E < EB2` (baja).

### Tarjeta #5 — Espectro neutrónico

**Formato:** `2I4` (dos enteros de 4 caracteres cada uno)

| Parámetro | Descripción |
|-----------|-------------|
| `NGROUP` | Número de grupos del espectro neutrónico. El signo indica el orden: `NGROUP < 0` → energía decreciente; `NGROUP > 0` → energía creciente. |
| `FF` | Unidades del flujo: `0` = flujo escalar total [n/cm²·s]; `1` = densidad de flujo [n/cm²·s·MeV] |

### Tarjeta #6 — Fronteras de energía personalizadas

**Condición:** solo presente si `IESF = 5`  
**Formato:** `6E12.5` (6 valores por línea, campo de 12 caracteres con 5 decimales)

| Parámetro | Descripción |
|-----------|-------------|
| `CX` | `ABS(NGROUP)+1` fronteras energéticas de la estructura de grupos del espectro. El orden sigue el signo de `NGROUP`. |

### Tarjeta #7 — Valores del flujo

**Formato:** `6E12.5` (6 valores por línea)

| Parámetro | Descripción |
|-----------|-------------|
| `FT` | `ABS(NGROUP)` valores del flujo neutrónico en cada grupo energético. Las unidades están dadas por `FF` (Tarjeta #5). |

### Tarjeta #8 — Modo de incertidumbres

**Formato:** libre

| Parámetro | Descripción |
|-----------|-------------|
| `IUNC3G` | `0` = sin procesado de incertidumbres. `1` = genera las librerías colapsadas de secciones eficaces con información de incertidumbre (`XSUNC.dat`, `XSUNC_1G.dat`) a partir de `UNCBL.dat`. |

### Tarjeta #9 — Modo de ejecución

**Formato:** libre

| Parámetro | Descripción |
|-----------|-------------|
| `ISTOP` | `0` = ejecución completa. `1` = el código solo escribe la información del espectro (`FLUX.inf`) y se detiene. |

### Resumen visual

```
COLL.inp de COLLAPS
│
├── Tarjeta #1  — ILIB, IESF          (estructura de grupos: librería y flujo)
├── Tarjeta #2  — IHEAD               (cabecera de la librería XS)
├── Tarjeta #3  — ISFIS IGEN ISOCA IBEST  (modo de fisión)
├── Tarjeta #4  — EB1 EB2             (fronteras energéticas — solo si ISFIS ≠ 0)
├── Tarjeta #5  — NGROUP FF           (grupos y unidades del espectro)
├── Tarjeta #6  — CX[NGROUP+1]        (fronteras personalizadas — solo si IESF = 5)
├── Tarjeta #7  — FT[NGROUP]          (valores del espectro neutrónico)
├── Tarjeta #8  — IUNC3G              (modo de incertidumbres)
└── Tarjeta #9  — ISTOP               (modo de ejecución)
```

```
Modos de operación de COLLAPS
│
├── Estándar        ISFIS=0, IUNC3G=0 → XSECTION.dat
├── Fisión          ISFIS=1            → XSECTION.dat + FYL.dat + FYXS.dat
├── Incertidumbres  IUNC3G=1           → XSECTION.dat + XSUNC.dat + XSUNC_1G.dat
└── Fisión + Inc.   ISFIS=1, IUNC3G=1 → todos los ficheros anteriores
```

---

## 9. Ficheros de Ejemplo

El directorio `examples/` contiene **18 casos de uso reales** organizados en subcarpetas, extraídos de casos de aplicación a reactores de fusión y fuentes de neutrones basadas en aceleradores. Todos han sido parseados correctamente con `collaps_parser.py`.

```
examples/
├── example1..example18/
│   └── collaps/COLL.inp       # caso estándar
├── example13/
│   └── collaps_damage/COLL.inp  # caso con librería de daño
└── example16/
    ├── collaps_neutrons/COLL.inp  # caso con flujo neutrónico
    └── collaps_protons/COLL.inp   # caso con flujo protónico
```

```bash
# Verificar que el parser lee todos los ejemplos sin errores
python - <<'EOF'
from collaps_parser import COLLAPSParser
from pathlib import Path
parser = COLLAPSParser()
for f in sorted(Path('examples').rglob('COLL.inp')):
    data = parser.read_coll_inp(f)
    print(f"OK  {str(f)}")
EOF
```
