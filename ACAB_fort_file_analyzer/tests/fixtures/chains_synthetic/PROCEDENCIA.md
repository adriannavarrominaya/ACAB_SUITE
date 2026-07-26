# Procedencia — `tests/fixtures/chains_synthetic/`

Fixture **totalmente sintético** (no proviene de una ejecución real de
ACAB/CHAINS) para el test oro de Fase 4 de
`acab_suite/runbook_F9_analisis_cadenas.md`
(`calcular_analisis_cadenas`/`construir_diagrama_cadena` en
`fort_analyzer.py`). Los nombres de nucleido (Fe/Mn/Co) y los procesos de
las cadenas (`(N,G-g)`, `(N,G-m)`, `(IT)`, `(B-)`) usan la sintaxis real de
CHAINS pero **no representan una cadena de desintegración físicamente
válida** — el objetivo es verificar la lectura/combinación de datos
(R_i, X_z_i, Y_z_i, Σ R_i, cobertura, diagrama), no la física del ejemplo.
El caso físico real (Te130→I131) ya está cubierto por
`tests/fixtures/chains/output_chain_Te130_to_I131.txt` y
`tests/fixtures/ref_sim/` (Fase 1).

## Estructura

```
chains_synthetic/
  chains_manifest.json      # IFINAL=CO57, PCNT=0.01, NMAX=5, 2 isótopos
  reference/fort.6           # inventario inicial (FE56+MN55) + A(CO57,t) suma
  iso_FE56/fort.6             # A(CO57,t) del run monoisotópico FE56
  iso_MN55/fort.6             # A(CO57,t) del run monoisotópico MN55
  chains_FE56/output_chain.txt  # 2 cadenas (P=80/20 %)
  chains_MN55/output_chain.txt  # 1 cadena (P=100 %)
```

`chains_manifest.json.reference_folder = "reference"` (ruta RELATIVA a la
raíz del análisis, a diferencia de un manifest real generado por
`chains_analysis.py`, que siempre guarda una ruta absoluta elegida por el
usuario vía el diálogo de carpeta) — portable entre máquinas/CI.
`calcular_analisis_cadenas` resuelve una `reference_folder` relativa
contra `root` antes de leerla.

## Datos elegidos a mano (Bq/cm³ de CO57, t en horas)

Sin fase de irradiación (`T_IRR_h=0`, solo la columna `INITIAL` en la
tabla `NUMBER OF ATOMS`): los 3 instantes de enfriamiento (`SHUTDOWN`,
1 h, 2 h) son directamente los tiempos absolutos.

| t [h] | A(FE56) | A(MN55) | A(ref) = A(FE56)+A(MN55) |
|---|---|---|---|
| 0 | 15 | 25 | 40 |
| 1 | 42 | 58 | 100 |
| 2 | 25 | 35 | 60 |

Superposición lineal exacta por construcción (A_ref = A_FE56 + A_MN55 en
los 3 instantes) — verifica el control de linealidad de Bateman del
runbook (Σ R_i ≈ 1 con selección completa) SIN necesitar resolver
Bateman de verdad.

## t* por defecto = t_pico de la referencia

Máximo de A(ref) en la tabla: 100 en t=1 h ⇒ **t* = 1 h**.

## R_i (en t*=1 h)

- `A_ref(t*) = 100`
- `R_FE56 = A_FE56(t*) / A_ref(t*) = 42 / 100 = 0.42`
- `R_MN55 = A_MN55(t*) / A_ref(t*) = 58 / 100 = 0.58`
- **Σ R_i = 0.42 + 0.58 = 1.00** — cobertura completa (los 2 isótopos del
  inventario inicial de la referencia están seleccionados), Σ R_i = 1
  exacto por construcción de la tabla de arriba.

## X_z_i, Y_z_i (tabla 2, orden esperado por Y_z_i descendente)

`chains_FE56/output_chain.txt`: NCH=2, PTOT=100 — P₁=80 %, P₂=20 %.
`chains_MN55/output_chain.txt`: NCH=1, PTOT=100 — P₁=100 %.

| Isótopo | Cadena | X_z_i = P/100 | R_i | Y_z_i = R_i·X_z_i |
|---|---|---|---|---|
| MN55 | 1 (única) | 1.00 | 0.58 | **0.580** |
| FE56 | 1 (P=80 %) | 0.80 | 0.42 | **0.336** |
| FE56 | 2 (P=20 %) | 0.20 | 0.42 | **0.084** |

Orden esperado de la tabla 2 (Y_z_i descendente): MN55/1 (0.580) →
FE56/1 (0.336) → FE56/2 (0.084). Σ de las 3 filas = 1.00 = Σ R_i (coherente:
con NCH cubriendo el 100 % de PTOT en ambos isótopos, no hay cola PCNT
descartada en este fixture).

## Diagrama de cadena (Fase 5)

No usa este fixture — `construir_diagrama_cadena` se verifica contra el
fixture real `tests/fixtures/chains/output_chain_Te130_to_I131.txt` +
`tests/fixtures/ref_sim/DECAY.dat` (T½ reales de TE130/TE131/TE131M/I131,
ya verificados en la Fase 1), no hace falta un DECAY.dat sintético nuevo.
