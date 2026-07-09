"""
compare_simulaciones.py  [LEGACY]
=================================
Compara la actividad de I-131 (MBq/g TeO2) calculada por ACAB en 6 simulaciones
con los datos experimentales y computacionales de referencia.

Uso:
    python compare_simulaciones.py

LEGACY (Fase 2 del runbook): script standalone con la densidad de normalizacion
y los datos experimentales embebidos a mano. La app web ya cubre su funcion:
  - La densidad se lee automaticamente del fort.6 con
    fort_analyzer.leer_fort6_concentraciones() (seccion CONCENTRATIONS(GRAM)),
    en lugar del valor hardcodeado 0.12317 g/cm3.
  - El selector de unidades (Bq/cm3 | MBq/g | actividad total) del analyzer
    aplica la misma conversion Bq/cm3 -> MBq/g = Bq/cm3 / (densidad * 1e6).
  - La superposicion de datos experimentales sobre las curvas la sustituye la
    Fase 4 del runbook. No invertir mas en este script.

La densidad de normalizacion (0.12317 g/cm3) proviene directamente del fort.6,
seccion CONCENTRATIONS(GRAM): O=2.4688E-02 g/cm3 + Te=9.8478E-02 g/cm3.
"""
from __future__ import annotations

import io
import os
import sys

# Forzar stdout UTF-8 para evitar errores de encoding en Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator

# Añadir el directorio raíz al path para importar fort_analyzer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fort_analyzer import leer_fort6_enfriamiento

# ─────────────────────────────────────────────────────────────────────────────
# Constante de normalización
# Masa de TeO₂ por cm³ de material simulado (de la sección CONCENTRATIONS(GRAM)
# del fort.6):  O=2.4688E-02 g/cm³  +  Te=9.8478E-02 g/cm³  = 1.2317E-01 g/cm³
# ─────────────────────────────────────────────────────────────────────────────
DENSIDAD_G_PER_CM3 = 0.12317  # g TeO₂ / cm³ simulado


def bq_cm3_a_mbq_g(bq_per_cm3: np.ndarray) -> np.ndarray:
    """Convierte Bq/cm³ → MBq/g TeO₂."""
    return bq_per_cm3 / (DENSIDAD_G_PER_CM3 * 1e6)


# ─────────────────────────────────────────────────────────────────────────────
# Datos de referencia
# ─────────────────────────────────────────────────────────────────────────────
# Datos experimentales (Actividad MBq/g TeO₂ | Tiempo enfriamiento horas)
exp_t = np.array([
    0.26951859, 0.4775716,  0.71976523, 0.92890383, 1.12000271,
    1.56890423, 1.89931071, 2.08787231, 2.26834455, 2.49911054, 2.67779639,
])
exp_A = np.array([
    0.05191691, 0.07064688, 0.08823739, 0.09443323, 0.10597033,
    0.11216617, 0.115727,   0.11679525, 0.11836202, 0.11950148, 0.12042730,
])

# Datos computacionales de referencia (I-131 de la simulación v.5 "info thesis")
comp_t = np.array([
    0.2709231889, 0.4804614151, 0.7204327496, 0.9315613704, 1.121084107,
    1.571873455,  1.902275268,  2.091705142,  2.27125429,   2.50196291,
    2.682403319,
])
comp_A = np.array([
    0.04836326,   0.07389830,   0.09358229,   0.10541931,   0.11311902,
    0.12387904,   0.12793620,   0.12942901,   0.13049404,   0.13105821,
    0.13169515,
])

# ─────────────────────────────────────────────────────────────────────────────
# Rutas a los fort.6
# ─────────────────────────────────────────────────────────────────────────────
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "simulaciones")

SIMULACIONES: dict[str, str] = {
    "v.1 — Inp.5 base":          os.path.join(BASE, "Simulacion v.1 - Inp.5",                         "fort.6"),
    "v.2 — +reactions":          os.path.join(BASE, "Simulacion v.2 -inp.5 - reactions",               "fort.6"),
    "v.3 — +reactions XNORM0.85":os.path.join(BASE, "Simulacion v.3 -inp.5 - reactions - XNORM 0.85", "fort.6"),
    "v.4 — +reactions NGRP1":    os.path.join(BASE, "Simulacion v.4 -inp.5 - reactions - NGRP 1",     "fort.6"),
    "v.5 — info thesis":         os.path.join(BASE, "Simulacion v.5 - info thesis",                    "fort.6"),
    "v.6 — COLLAPS":             os.path.join(BASE, "Simulacion v.6 - COLLAPS",                        "fort.6"),
}

# ─────────────────────────────────────────────────────────────────────────────
# Lectura y conversión de datos de simulación
# ─────────────────────────────────────────────────────────────────────────────
print("Leyendo archivos fort.6 ...")
sim_data: dict[str, dict] = {}

for nombre, ruta in SIMULACIONES.items():
    try:
        t_cool, datos = leer_fort6_enfriamiento(ruta)
        if "I131" not in datos:
            print(f"  AVISO: I131 no encontrado en '{nombre}'")
            continue
        A_mbq_g = bq_cm3_a_mbq_g(datos["I131"])
        sim_data[nombre] = {"t": t_cool, "A": A_mbq_g}
        print(f"  OK  {nombre}  ({len(t_cool)} puntos, "
              f"A_I131_max = {A_mbq_g.max():.5f} MBq/g)")
    except Exception as exc:
        print(f"  ERROR leyendo '{nombre}': {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# Interpolación en los tiempos experimentales y cálculo de % diferencia
# ─────────────────────────────────────────────────────────────────────────────
# Interpolar datos computacionales en tiempos experimentales
comp_interp = np.interp(exp_t, comp_t, comp_A)
comp_pct    = (comp_interp - exp_A) / exp_A * 100.0

# Interpolar cada simulación en los tiempos experimentales
interp: dict[str, np.ndarray] = {}
pct:    dict[str, np.ndarray] = {}
for nombre, d in sim_data.items():
    interp[nombre] = np.interp(exp_t, d["t"], d["A"])
    pct[nombre]    = (interp[nombre] - exp_A) / exp_A * 100.0

# ─────────────────────────────────────────────────────────────────────────────
# Tabla de resultados
# ─────────────────────────────────────────────────────────────────────────────
etiquetas_cortas = [n.split(" — ")[0] for n in SIMULACIONES.keys()]

print("\n" + "=" * 120)
print("TABLA COMPARATIVA -- Actividad I-131 (MBq/g TeO2) vs. Tiempo de enfriamiento (h)")
print("% diferencia = (A_sim - A_exp) / A_exp x 100")
print("=" * 120)

# Cabecera
col_w = 12
hdr = f"{'t_exp (h)':>{col_w}} {'A_exp':>{col_w}} {'A_comp':>{col_w}} {'%Δcomp':>{col_w}}"
for et in etiquetas_cortas:
    hdr += f" {f'A_{et}':>{col_w}} {f'%Δ{et}':>{col_w}}"
print(hdr)
print("-" * len(hdr))

for i, (t, Ae) in enumerate(zip(exp_t, exp_A)):
    fila = f"{t:{col_w}.5f} {Ae:{col_w}.5f} {comp_interp[i]:{col_w}.5f} {comp_pct[i]:{col_w}.1f}%"
    for nombre in SIMULACIONES:
        if nombre in interp:
            fila += f" {interp[nombre][i]:{col_w}.5f} {pct[nombre][i]:{col_w}.1f}%"
        else:
            fila += f" {'N/A':>{col_w}} {'N/A':>{col_w}}"
    print(fila)

print("=" * 120)

# Estadísticos resumen (RMSE y sesgo medio)
print("\nRESUMEN ESTADISTICO (respecto al experimental):")
print(f"  {'Dataset':<35} {'Sesgo medio (%)':>18} {'RMSE (%)':>12} {'|%diff| max':>12}")
print("  " + "-" * 80)

def stats(pct_arr: np.ndarray) -> tuple[float, float, float]:
    sesgo = float(np.mean(pct_arr))
    rmse  = float(np.sqrt(np.mean(pct_arr**2)))
    maximo = float(np.max(np.abs(pct_arr)))
    return sesgo, rmse, maximo

sesgo, rmse, maximo = stats(comp_pct)
print(f"  {'Computacional (ref.)':<35} {sesgo:>+18.2f} {rmse:>12.2f} {maximo:>12.2f}")

for nombre in SIMULACIONES:
    if nombre in pct:
        sesgo, rmse, maximo = stats(pct[nombre])
        et = nombre.split(" — ")[0]
        print(f"  {nombre:<35} {sesgo:>+18.2f} {rmse:>12.2f} {maximo:>12.2f}")

# ─────────────────────────────────────────────────────────────────────────────
# Gráfica
# ─────────────────────────────────────────────────────────────────────────────
colores = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#a65628"]
estilos = ["-", "--", "-.", ":", (0,(5,2)), (0,(3,1,1,1))]
marcadores = ["s", "D", "v", "^", "p", "h"]

fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=False)

# ── Panel superior: Actividad vs. Tiempo ─────────────────────────────────────
ax1 = axes[0]

# Experimental (negro, círculos rellenos)
ax1.plot(exp_t, exp_A, "ko-", lw=2, ms=7, zorder=10, label="Experimental")
# Computacional de referencia (negro, triángulos punteado)
ax1.plot(comp_t, comp_A, "k^--", lw=2, ms=7, zorder=10, label="Computacional (ref.)")

# Simulaciones
for (nombre, d), col, ls, mk in zip(sim_data.items(), colores, estilos, marcadores):
    t_plot = d["t"]
    A_plot = d["A"]
    mask = (t_plot >= 0.0) & (t_plot <= exp_t.max() + 0.3)
    et = nombre.split(" — ")[0]
    ax1.plot(t_plot[mask], A_plot[mask], color=col, ls=ls, marker=mk,
             ms=5, lw=1.8, label=f"Sim {et} — {nombre.split(' — ')[1]}")

ax1.set_ylabel(r"Actividad $^{131}$I  (MBq/g TeO$_2$)", fontsize=12)
ax1.set_title(
    r"Comparación simulaciones ACAB vs. experimento""\n"
    r"Actividad de $^{131}$I tras irradiación de TeO$_2$ (10 s, $\varphi$ = 6.67×10$^{13}$ n/cm²/s)",
    fontsize=13,
)
ax1.legend(loc="lower right", fontsize=8.5, framealpha=0.9)
ax1.grid(True, alpha=0.3)
ax1.set_xlim(0.0, exp_t.max() + 0.15)
ax1.set_ylim(bottom=0.0)
ax1.xaxis.set_minor_locator(MultipleLocator(0.1))
ax1.yaxis.set_minor_locator(MultipleLocator(0.005))
ax1.tick_params(which="both", direction="in")

# ── Panel inferior: % Diferencia vs. Tiempo ──────────────────────────────────
ax2 = axes[1]

ax2.axhline(0, color="black", lw=2, label="Experimental (0 %)")
ax2.plot(exp_t, comp_pct, "k^--", lw=2, ms=7, label="Computacional (ref.)")

for (nombre, _), col, ls, mk in zip(sim_data.items(), colores, estilos, marcadores):
    if nombre in pct:
        et = nombre.split(" — ")[0]
        ax2.plot(exp_t, pct[nombre], color=col, ls=ls, marker=mk,
                 ms=6, lw=1.8, label=f"Sim {et}")

ax2.set_xlabel("Tiempo de enfriamiento (h)", fontsize=12)
ax2.set_ylabel("Diferencia relativa vs. experimental (%)", fontsize=12)
ax2.set_title("Diferencia porcentual respecto al experimental", fontsize=13)
ax2.legend(loc="best", fontsize=8.5, framealpha=0.9, ncol=2)
ax2.grid(True, alpha=0.3)
ax2.set_xlim(0.0, exp_t.max() + 0.15)
ax2.xaxis.set_minor_locator(MultipleLocator(0.1))
ax2.yaxis.set_minor_locator(MultipleLocator(1))
ax2.tick_params(which="both", direction="in")

plt.tight_layout(h_pad=3)

out_png = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "comparacion_simulaciones.png")
plt.savefig(out_png, dpi=180, bbox_inches="tight")
print(f"\nGráfica guardada en: {out_png}")
plt.show()
