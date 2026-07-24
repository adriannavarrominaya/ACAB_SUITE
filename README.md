# Suite ACAB — TFG optimización de producción de ¹³¹I

**Tres aplicaciones web locales que cubren el ciclo completo de trabajo con el código de activación ACAB 2008 (UPM): configurar entradas → ejecutar → analizar salidas**

**Autor:** Adrian Navarro Minaya · [adriannavarrominaya@gmail.com](mailto:adriannavarrominaya@gmail.com)

**Tutor:** Oscar Luis Cabellos de Francisco · [oscar.cabellos@upm.es](mailto:oscar.cabellos@upm.es)

**Departamento:** Departamento de Ingeniería Energética (Área Nuclear)

**Centro:** Universidad Politécnica de Madrid

**Fecha:** Julio 2026

**Códigos de simulación:** ACAB 2008 (UPM — Activation code) · COLLAPS (preprocesador de secciones eficaces)

---

Desarrollada como parte del Trabajo de Fin de Grado en Ingeniería de la Energía.

![ACAB](https://img.shields.io/badge/NucCalc-ACABv2008-orange) ![COLLAPS](https://img.shields.io/badge/NucCalc-COLLAPS-orange) ![Python](https://img.shields.io/badge/Lang-Python314-blue) ![Flask](https://img.shields.io/badge/Web-Flask313-black) ![Bootstrap](https://img.shields.io/badge/Front-Bootstrap533-purple) ![Plotly](https://img.shields.io/badge/Charts-Plotly232-3F4F75)

---

## Índice

- [Suite ACAB — TFG optimización de producción de ¹³¹I](#suite-acab--tfg-optimización-de-producción-de-¹³¹i)
  - [Índice](#índice)
  - [1. Descripción](#1-descripción)
  - [2. Caso de estudio: producción de ¹³¹I](#2-caso-de-estudio-producción-de-¹³¹i)
  - [3. Mapa de la suite](#3-mapa-de-la-suite)
  - [4. Flujo de trabajo end-to-end](#4-flujo-de-trabajo-end-to-end)
  - [5. Arranque rápido](#5-arranque-rápido)
    - [Opción A — Suite completa (recomendado)](#opción-a--suite-completa-recomendado)
    - [Opción B — Una app suelta](#opción-b--una-app-suelta)
  - [6. Estructura del repositorio](#6-estructura-del-repositorio)
  - [7. Tecnologías comunes](#7-tecnologías-comunes)
  - [8. Documentación adicional](#8-documentación-adicional)
  - [9. Organización del repositorio y contribución](#9-organización-del-repositorio-y-contribución)

---

## 1. Descripción

Este repositorio agrupa las herramientas web desarrolladas para el TFG como apoyo
al trabajo con **ACAB 2008**, el código de cálculo de activación neutrónica del
Instituto de Fusión Nuclear (UPM), y con su preprocesador **COLLAPS** (colapsado
de librerías de secciones eficaces multigrupo). Los ficheros de entrada y salida
de ambos códigos siguen un formato FORTRAN libre, organizado en bloques/tarjetas,
que resulta tedioso y propenso a errores de editar y depurar a mano.

Cada aplicación de la suite cubre una etapa del ciclo de trabajo — **configurar
entradas → ejecutar → analizar salidas** — mediante una interfaz web local
(Flask + Bootstrap, sin build step ni frameworks de frontend):

- **[COLLAPS_inp_file_configurator](COLLAPS_inp_file_configurator/)** genera el
  espectro neutrónico colapsado (`COLL.inp` → `XSECTION.dat`).
- **[ACAB_inp_file_configurator](ACAB_inp_file_configurator/)** construye el
  fichero de entrada de ACAB (`inp.5`) a partir de ese espectro y de la
  composición del blanco, y puede ejecutar la simulación y generar barridos
  paramétricos.
- **[ACAB_fort_file_analyzer](ACAB_fort_file_analyzer/)** analiza la salida
  (`fort.6`): evolución temporal de la actividad, informes por isótopo, tablas
  comparativas y métricas de optimización de producción.

Las tres son aplicaciones **monousuario**, pensadas para ejecutarse en local
(`127.0.0.1`) durante el trabajo de simulación del TFG — no hay autenticación
ni están pensadas para despliegue multiusuario.

---

## 2. Caso de estudio: producción de ¹³¹I

El TFG estudia la producción de ¹³¹I médico por irradiación neutrónica de TeO₂:

$${}^{130}\text{Te}(n,\gamma){}^{131}\text{Te} \xrightarrow{\beta^-} {}^{131}\text{I} \xrightarrow{\beta^-} {}^{131}\text{Xe}$$

Este caso guía el diseño de las herramientas (composición asistida de TeO₂ en el
configurador de `inp.5`, espectro gamma de referencia de ¹³¹I en el analizador,
métricas de saturación/rendimiento/pureza radionucleídica), pero las tres
aplicaciones son genéricas: funcionan con cualquier composición, geometría e
isótopo soportado por ACAB/COLLAPS. Los detalles del caso de estudio y de las
métricas de optimización se documentan en el
[README del analizador de fort.6](ACAB_fort_file_analyzer/README.md#pestaña-3--informe-isótopo).

---

## 3. Mapa de la suite

| Carpeta | Qué es | Puerto | Documentación |
|---|---|---|---|
| `COLLAPS_inp_file_configurator/` | Editor del fichero `COLL.inp` de COLLAPS (colapsado de espectros) | 5002 | [README](COLLAPS_inp_file_configurator/README.md) |
| `ACAB_inp_file_configurator/` | Editor/generador de ficheros de entrada `inp.5` (14 bloques) y ficheros CHAINS; ejecución y barridos paramétricos | 5000 | [README](ACAB_inp_file_configurator/README.md) |
| `ACAB_fort_file_analyzer/` | Análisis y gráficas de ficheros de salida `fort.6` (multi-simulación) | 5001 | [README](ACAB_fort_file_analyzer/README.md) |
| `acab_suite/` | Transversal: launcher de la suite, configuración común y runbooks de desarrollo | — | [README](acab_suite/README.md) |

Cada app tiene su propio README con el detalle de instalación, interfaz, API REST
y formato de fichero; este documento es solo el punto de entrada.

---

## 4. Flujo de trabajo end-to-end

```
COLLAPS                    ACAB                        Analyzer
(espectro)                 (entrada/ejecución)          (salida)

COLL.inp  ──[collaps.exe]──▶ XSECTION.dat
                                   │
                                   ▼
                    inp.5 (composición, geometría,
                    historial irr./enfriamiento)
                                   │
                            [ejecutar acab.exe]
                                   │
                                   ▼
                                fort.6  ──"Abrir en Fort Analyzer"──▶  Actividad,
                                                                        informes,
                                                                        tablas,
                                                                        optimización
```

Las tres apps están enlazadas entre sí mediante un banner de navegación común
(con indicador de qué apps están arrancadas) y, entre el configurador de `inp.5`
y el analizador, mediante un enlace directo tras ejecutar una simulación. El
configurador de `inp.5` puede además generar **barridos paramétricos** (flujo,
masa o historial temporal) que el analizador consume en su pestaña
"Optimización".

---

## 5. Arranque rápido

### Opción A — Suite completa (recomendado)

```powershell
cd acab_suite
.\setup.ps1              # una vez: crea el venv compartido C:\venv\acab-venv
C:\venv\acab-venv\Scripts\python suite_launcher.py
```

El launcher arranca las tres apps, comprueba que responden y abre una única
pestaña del navegador en el configurador de `inp.5`. Detalles, configuración de
puertos y comportamiento en [`acab_suite/README.md`](acab_suite/README.md).

### Opción B — Una app suelta

Cada app puede instalarse y arrancarse de forma independiente con su propio
`setup.ps1` y entorno virtual local — ver la sección "Instalación y Puesta en
Marcha" de su README ([COLLAPS](COLLAPS_inp_file_configurator/README.md#4-instalación-y-puesta-en-marcha),
[ACAB inp](ACAB_inp_file_configurator/README.md#4-instalación-y-puesta-en-marcha),
[ACAB fort analyzer](ACAB_fort_file_analyzer/README.md#4-instalación-y-puesta-en-marcha)).

Requisito común: Python 3.10+ (probado con 3.14) y pip.

---

## 6. Estructura del repositorio

```
ACAB_SUITE/
├── COLLAPS_inp_file_configurator/   # app Flask — puerto 5002
├── ACAB_inp_file_configurator/      # app Flask — puerto 5000
├── ACAB_fort_file_analyzer/         # app Flask — puerto 5001
├── acab_suite/                      # launcher, suite_config.json, runbooks
├── CLAUDE.md                        # reglas de trabajo en este árbol (multi-repo)
└── README.md                        # este fichero
```

**Cada subcarpeta de app es un repositorio git independiente**: no hay un único
historial de commits para la suite, y los cambios de cada app se gestionan (y
se versionan) dentro de su propio repo.

---

## 7. Tecnologías comunes

| Tecnología | Uso |
|---|---|
| **Python 3.14** | Backend de las tres apps |
| **Flask 3.1.3** + **Waitress** | Servidor web (WSGI de producción, sin avisos de servidor de desarrollo) |
| **Bootstrap 5.3.3** + **Bootstrap Icons** | Interfaz de usuario (CDN) |
| **JavaScript vanilla (ES6+)** | Lógica de frontend, sin build step ni frameworks |
| **Plotly.js 2.32** | Gráficas interactivas (solo en el analizador de `fort.6`) |

Cada app documenta su stack completo (dependencias exactas, módulos de la
biblioteca estándar usados) en la sección "Tecnologías Utilizadas" de su README.
La interfaz de las tres está disponible en **español** (por defecto) e
**inglés**, con la preferencia guardada en el navegador.

---

## 8. Documentación adicional

- Manuales de referencia de los formatos de fichero (solo lectura, fuente de
  verdad ante cualquier duda de semántica de un parámetro):
  [`ACAB_inp_file_configurator/docs/`](ACAB_inp_file_configurator/docs/) (bloques
  #1–#14, CHAINS, PROCACAB) y
  [`COLLAPS_inp_file_configurator/docs/COLLAPS.md`](COLLAPS_inp_file_configurator/docs/COLLAPS.md).
- Planes de trabajo detallados (fases, criterios de aceptación) de las mejoras
  en curso: `acab_suite/RUNBOOK_*.md`.

---

## 9. Organización del repositorio y contribución

Las reglas de trabajo en este árbol multi-repo (commits siempre dentro del repo
afectado, ficheros duplicados que hay que mantener sincronizados entre apps —
banner de navegación, `runner.py`, `install_python.ps1` — y demás convenciones)
están documentadas en [`CLAUDE.md`](CLAUDE.md).
