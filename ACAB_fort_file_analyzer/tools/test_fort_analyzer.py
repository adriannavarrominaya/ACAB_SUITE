"""test_fort_analyzer.py — Tests oro del motor de análisis (Fase 0 del runbook).

Script autocontenido, sin framework (estilo de la suite ACAB). Ejecuta los
parsers y cálculos de fort_analyzer.py contra la simulación de referencia
congelada en tests/fixtures/ref_sim/ y compara con los valores oro anotados en
tests/fixtures/README.md.

Uso:
    python tools/test_fort_analyzer.py

Devuelve código de salida 0 si todo pasa, 1 si algún test falla.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

# La salida contiene caracteres Unicode (→, ½, ³…); fuerza UTF-8 para que el
# script corra en verde también en consolas Windows con codepage cp1252.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Permite ejecutar el script desde cualquier directorio (importa fort_analyzer
# desde la raíz del repo, que es el padre de tools/).
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import fort_analyzer as fa  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures"
REF_SIM = FIXTURES / "ref_sim"
FORT6 = str(REF_SIM / "fort.6")
INP5 = str(REF_SIM / "inp.5")
DECAY = str(REF_SIM / "DECAY.dat")

# ref_sim_f7 (F7 del BACKLOG): misma física que ref_sim, Blocks #7/#8
# regenerados sin compactación (irr y cool nunca comparten tarjeta) -> 3 TIME
# SETs en vez de 2. Ver tests/fixtures/ref_sim_f7/PROCEDENCIA.md.
REF_SIM_F7 = FIXTURES / "ref_sim_f7"
FORT6_F7 = str(REF_SIM_F7 / "fort.6")
DECAY_F7 = str(REF_SIM_F7 / "DECAY.dat")

# ref_sim_f7_irr2sets (F7 del BACKLOG, verificación adicional): fase de
# irradiación que ocupa 2 tarjetas de Blocks #7/#8 (20 pasos, 0.25->5.00h) +
# enfriamiento multi-tarjeta (misma malla que ref_sim_f7). Expuso que
# leer_fort6_irradiacion solo leia la PRIMERA tabla NUMBER OF ATOMS. Ver
# tests/fixtures/ref_sim_f7_irr2sets/PROCEDENCIA.md.
REF_SIM_F7_IRR2 = FIXTURES / "ref_sim_f7_irr2sets"
FORT6_F7_IRR2 = str(REF_SIM_F7_IRR2 / "fort.6")
DECAY_F7_IRR2 = str(REF_SIM_F7_IRR2 / "DECAY.dat")

# ─────────────────────────────────────────────────────────────────────────────
# Mini-framework de aserciones
# ─────────────────────────────────────────────────────────────────────────────
_PASSED = 0
_FAILED = 0


def _ok(msg: str) -> None:
    global _PASSED
    _PASSED += 1
    print(f"  [PASS] {msg}")


def _fail(msg: str) -> None:
    global _FAILED
    _FAILED += 1
    print(f"  [FAIL] {msg}")


def check(cond: bool, msg: str) -> None:
    _ok(msg) if cond else _fail(msg)


def check_close(got, expected, msg: str, rtol: float = 1e-3, atol: float = 0.0) -> None:
    try:
        if math.isclose(float(got), float(expected), rel_tol=rtol, abs_tol=atol):
            _ok(f"{msg} (={got})")
        else:
            _fail(f"{msg}: obtenido {got}, esperado {expected} (rtol={rtol})")
    except (TypeError, ValueError):
        _fail(f"{msg}: valor no numérico {got!r}")


def section(name: str) -> None:
    print(f"\n== {name} ==")


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_decay_dat() -> None:
    section("leer_decay_dat — decodificación ZZAAAS")
    t12 = fa.leer_decay_dat(DECAY)

    check("I131" in t12, "I131 presente en DECAY.dat")
    check("TE131M" in t12, "TE131M presente (S=1 → sufijo M)")
    check("XE133" in t12, "XE133 presente")

    # Valores oro leídos directamente del fichero DECAY.dat:
    #   531310 → I131   T½ = 6.932E+05 s
    #   521311 → TE131M T½ = 1.080E+05 s
    #   541330 → XE133  T½ = 4.531E+05 s
    check_close(t12.get("I131"), 6.932e5, "T½ I131 = 6.932e5 s (8.0231 d)")
    check_close(t12.get("TE131M"), 1.080e5, "T½ TE131M = 1.080e5 s (30 h)")
    check_close(t12.get("XE133"), 4.531e5, "T½ XE133 = 4.531e5 s")

    # Un nucleido marcado como estable (ST=6) debe quedar como infinito.
    # H2 (código 10020, ST=6) es estable en DECAY.dat.
    check(t12.get("H2", 0.0) == math.inf, "H2 estable (ST=6) → T½ = inf")


def test_irradiacion() -> None:
    section("leer_fort6_irradiacion — NUMBER OF ATOMS")
    t_irr, datos = fa.leer_fort6_irradiacion(FORT6)

    check(len(datos) == 499, f"499 isótopos detectados (obtenido {len(datos)})")
    check("I131" in datos, "I131 presente en irradiación")

    # La columna INITIAL corresponde a t=0 (estado pre-irradiación).
    check(t_irr[0] == 0.0, "primer punto temporal = 0 (columna INITIAL)")

    # Átomos de I131 al final de la irradiación: 3.841E+07 átomos/cm³.
    check_close(datos["I131"][-1], 3.841e7, "I131 final irr = 3.841e7 átomos/cm³")


def test_enfriamiento() -> None:
    section("leer_fort6_enfriamiento — NUCLIDE RADIOACTIVITY")
    t_cool, datos = fa.leer_fort6_enfriamiento(FORT6)

    # Malla: 19 puntos, de 0.00 a 4.50 h en pasos de 0.25 h.
    check(len(t_cool) == 19, f"19 timesteps de enfriamiento (obtenido {len(t_cool)})")
    check_close(t_cool[0], 0.0, "primer t de enfriamiento = 0 (RESTART)", atol=1e-9)
    check_close(t_cool[-1], 4.50, "último t de enfriamiento = 4.50 h")

    # No duplicar timesteps pese a las secciones BY INTERVAL / BY ZONE.
    check(len(set(t_cool.tolist())) == len(t_cool), "sin timesteps duplicados")

    check("I131" in datos, "I131 presente en enfriamiento")
    # Los arrays de datos deben tener la misma longitud que la malla temporal.
    check(len(datos["I131"]) == 19, "serie I131 alineada con la malla (19 puntos)")

    # Valores oro (Bq/cm³):
    check_close(datos["I131"][0], 38.42, "I131 en RESTART (t=0) = 38.42 Bq/cm³")
    check_close(datos["I131"][1], 5690.0, "I131 en t=0.25 h = 5690 Bq/cm³")
    check_close(datos["I131"][-1], 16490.0, "I131 en t=4.50 h = 16490 Bq/cm³")


def test_enfriamiento_f7_3sets() -> None:
    section("leer_fort6_enfriamiento — F7: 3 TIME SETs, RESTART = t=0 real")
    t_cool, datos = fa.leer_fort6_enfriamiento(FORT6_F7)

    # Misma malla física que ref_sim (19 puntos, 0.00-4.50h/0.25h), pero aquí
    # la tarjeta 2 (primer TIME SET de enfriamiento) reporta el t=0 bajo el
    # token RESTART, no SHUTDOWN (la transición irr->cool cae justo en el
    # límite de tarjeta -- F7 nunca mezcla fases). Regresión del bug que
    # trataba todo RESTART como "excluir" y perdía ese punto.
    check(len(t_cool) == 19, f"19 timesteps de enfriamiento (obtenido {len(t_cool)})")
    check_close(t_cool[0], 0.0, "primer t de enfriamiento = 0 (RESTART real, no duplicado)", atol=1e-9)
    check_close(t_cool[-1], 4.50, "último t de enfriamiento = 4.50 h")
    check(len(set(t_cool.tolist())) == len(t_cool), "sin timesteps duplicados (3 TIME SETs fusionados)")

    # Mismos valores oro de I131 que ref_sim: es la MISMA física, solo cambia
    # el agrupado de tarjetas de Blocks #7/#8.
    check("I131" in datos, "I131 presente en enfriamiento")
    check(len(datos["I131"]) == 19, "serie I131 alineada con la malla (19 puntos)")
    check_close(datos["I131"][0], 38.42, "I131 en RESTART (t=0 real) = 38.42 Bq/cm³")
    check_close(datos["I131"][1], 5690.0, "I131 en t=0.25 h = 5690 Bq/cm³")
    check_close(datos["I131"][-1], 16490.0, "I131 en t=4.50 h = 16490 Bq/cm³")


def test_pico_i131_f7_3sets() -> None:
    section("analizar_carpeta + calcular_pico — F7 (3 TIME SETs), pico de I131")
    t12 = fa.leer_decay_dat(DECAY_F7)
    all_data, errors = fa.analizar_carpeta(str(REF_SIM_F7), t12)

    check(len(errors) == 0, f"análisis sin errores (errores={errors})")
    sim = next(iter(all_data.values()))
    pico = fa.calcular_pico(sim, "I131")

    # Idéntico al pico oro de ref_sim (1.6500e4 Bq/cm³ en t_global=3.753h):
    # el agrupado F7 de Blocks #7/#8 no cambia la física, solo las tarjetas.
    check_close(pico["A_pico"], 1.6500e4, "A_pico I131 = 1.6500e4 Bq/cm³ (idéntico a ref_sim)", rtol=2e-3)
    check_close(pico["t_pico"], 3.753, "t_pico I131 = 3.753 h (idéntico a ref_sim)", rtol=1e-2)
    check(pico["fase"] == "enfriamiento", "pico en fase de enfriamiento")


def test_irradiacion_f7_2sets() -> None:
    section("leer_fort6_irradiacion — F7: irradiación en 2 tarjetas (NUMBER OF ATOMS)")
    t_irr, datos = fa.leer_fort6_irradiacion(FORT6_F7_IRR2)

    # Malla: INITIAL + 20 pasos = 21 puntos, 0.00-5.00h/0.25h. La tarjeta 1
    # (10 pasos, 0.25->2.5h) y la tarjeta 2 (10 pasos, 2.75->5.0h, RESTART
    # duplicando el último de la tarjeta 1) deben fusionarse sin perder
    # puntos ni contar dos veces las tablas BY ZONE.
    check(len(t_irr) == 21, f"INITIAL + 20 puntos de irradiación (obtenido {len(t_irr)})")
    check_close(t_irr[0], 0.0, "primer t de irradiación = 0 (INITIAL)", atol=1e-9)
    check_close(t_irr[-1], 5.0, "último t de irradiación = 5.00 h")
    check(len(set(t_irr.tolist())) == len(t_irr),
          "sin timesteps duplicados (BY ZONE no se cuenta como tarjeta nueva)")
    check(all(t_irr[i] < t_irr[i + 1] for i in range(len(t_irr) - 1)),
          "tiempos estrictamente crecientes tras fusionar las 2 tarjetas")

    check("I131" in datos, "I131 presente en irradiación")
    check(len(datos["I131"]) == 21, "serie I131 alineada con la malla (21 puntos)")

    # Valor oro verificado a mano contra el texto del fort.6 (líneas 2896 y
    # 5418): I131 en t=2.50h (última columna de la tarjeta 1) es IDÉNTICO al
    # valor bajo RESTART en la tarjeta 2 -- confirma que el punto de empalme
    # no se pierde ni se duplica al fusionar.
    idx_250 = list(t_irr).index(2.5)
    check_close(datos["I131"][idx_250], 1.141e13,
                "I131 en t=2.50h (empalme tarjeta1/tarjeta2) = 1.141e13 át/cm³")
    check_close(datos["I131"][-1], 2.622e13, "I131 al final de la irradiación (t=5.00h) = 2.622e13 át/cm³")


def test_pico_f7_irr2sets_integracion() -> None:
    section("analizar_carpeta — F7: irradiación 2 tarjetas + enfriamiento multi-tarjeta")
    t12 = fa.leer_decay_dat(DECAY_F7_IRR2)
    all_data, errors = fa.analizar_carpeta(str(REF_SIM_F7_IRR2), t12)

    check(len(errors) == 0, f"análisis sin errores (errores={errors})")
    sim = next(iter(all_data.values()))

    # La irradiación completa (0->5h) debe llegar íntegra a la simulación
    # analizada, no truncada en el final de la primera tarjeta (2.5h).
    check(len(sim["t_irr"]) == 21, f"t_irr con los 21 puntos fusionados (obtenido {len(sim['t_irr'])})")
    check_close(sim["t_irr"][-1], 5.0, "t_irr llega hasta 5.00h (no se corta en la tarjeta 1)")
    check_close(sim["T_IRR_h"], 5.0, "T_IRR_h = 5.00h (leído de Block #11/Blocks #7,#8 del inp.5)")

    pico = fa.calcular_pico(sim, "I131")
    check(pico["fase"] == "enfriamiento", "pico de I131 en fase de enfriamiento")
    check_close(pico["t_pico"], 7.5, "t_pico = T_irr(5.0h) + 2.5h de enfriamiento", rtol=1e-2)


def test_inp5() -> None:
    section("leer_inp5 — parámetros de simulación")
    p = fa.leer_inp5(INP5)

    check_close(p["T_IRR_h"], 0.00278, "T_irr = 0.00278 h (pulso ~10 s)", rtol=5e-2)
    check_close(p["T_COOL_h"], 4.50, "T_cool = 4.50 h")
    check(p["ngrp"] >= 1, f"ngrp >= 1 (obtenido {p['ngrp']})")
    check(p["xnorm"] > 0, f"xnorm > 0 (obtenido {p['xnorm']})")


def test_pico_i131() -> None:
    section("analizar_carpeta + calcular_pico — pico de I131")
    t12 = fa.leer_decay_dat(DECAY)
    all_data, errors = fa.analizar_carpeta(str(REF_SIM), t12)

    check(len(errors) == 0, f"análisis sin errores (errores={errors})")
    check(len(all_data) == 1, "una simulación descubierta (modo simulación única)")

    sim = next(iter(all_data.values()))
    pico = fa.calcular_pico(sim, "I131")

    # Pico oro: 1.6500e4 Bq/cm³ en t_global = 3.753 h (fase de enfriamiento).
    check_close(pico["A_pico"], 1.6500e4, "A_pico I131 = 1.6500e4 Bq/cm³", rtol=2e-3)
    check_close(pico["t_pico"], 3.753, "t_pico I131 = 3.753 h", rtol=1e-2)
    check(pico["fase"] == "enfriamiento", "pico en fase de enfriamiento")


def test_concentraciones() -> None:
    section("leer_fort6_concentraciones — CONCENTRATIONS(GRAM)")
    conc = fa.leer_fort6_concentraciones(FORT6)

    check(conc is not None, "sección CONCENTRATIONS(GRAM) encontrada")
    assert conc is not None  # para el analizador estático

    # Valores oro (WEIGHT PERCENTAGE, columna INITIAL, g/cm³):
    #   O = 2.4688E-02 ; TE = 9.8478E-02 ; TOTAL = 1.2317E-01
    check("O" in conc["elementos"] and "TE" in conc["elementos"],
          "elementos O y TE presentes")
    check_close(conc["elementos"].get("O"), 2.4688e-2, "O = 2.4688e-2 g/cm³")
    check_close(conc["elementos"].get("TE"), 9.8478e-2, "TE = 9.8478e-2 g/cm³")
    check_close(conc["total_g_cm3"], 0.12317, "densidad total = 0.12317 g/cm³", atol=1e-4)

    # No duplicar elementos pese a las secciones BY INTERVAL / BY ZONE.
    check(len(conc["elementos"]) == 2, f"solo 2 elementos (obtenido {len(conc['elementos'])})")

    # Fichero sin la sección → None sin romper.
    check(fa.leer_fort6_concentraciones(str(REF_SIM / "inp.5")) is None,
          "fichero sin CONCENTRATIONS(GRAM) → None")


def test_densidad_en_analisis() -> None:
    section("analizar_carpeta + conversión MBq/g — acoplamiento densidad")
    t12 = fa.leer_decay_dat(DECAY)
    all_data, _ = fa.analizar_carpeta(str(REF_SIM), t12)
    sim = next(iter(all_data.values()))

    # analizar_carpeta debe adjuntar la densidad a cada simulación.
    check_close(sim.get("densidad_g_cm3"), 0.12317,
                "densidad_g_cm3 adjunta a la simulación", atol=1e-4)

    # Criterio de aceptación de la Fase 2: el pico de I131 en MBq/g reproduce el
    # valor del script legacy (compare_simulaciones.py): MBq/g = Bq/cm³ /
    # (densidad · 1e6). A_pico = 1.6500e4 Bq/cm³, densidad = 0.12317 g/cm³.
    A_pico = fa.calcular_pico(sim, "I131")["A_pico"]
    mbq_g = A_pico / (sim["densidad_g_cm3"] * 1e6)
    check_close(mbq_g, 16500.0 / (0.12317 * 1e6),
                "pico I131 en MBq/g = A_pico/(densidad·1e6) (~0.13396)", rtol=2e-3)

    # Oráculo numérico de las conversiones de actividad total (espejo de
    # static/js/units.js convertUnits; VOLUME OF ZONE de la ref_sim = 1 cm³).
    # Cubre en el harness Python las ramas que tools/test_units.js valida con
    # node (no disponible en este entorno). Mantener en sincronía con units.js.
    V = 1.0
    check_close(A_pico * V / 1e6, 16500.0 / 1e6,
                "pico I131 en MBq total = A_pico·V/1e6 (~0.0165, V=1 cm³)", rtol=2e-3)
    check_close(A_pico * V / 3.7e7, 16500.0 / 3.7e7,
                "pico I131 en mCi total = A_pico·V/3.7e7 (~4.46e-4, V=1 cm³)", rtol=2e-3)


def test_desactualizada() -> None:
    section("analizar_carpeta — detección de fort.6 desactualizado (Fase R5)")
    t12 = fa.leer_decay_dat(DECAY)

    with tempfile.TemporaryDirectory() as tmp:
        sim_dir = Path(tmp) / "sim1"
        sim_dir.mkdir()
        shutil.copy(FORT6, sim_dir / "fort.6")
        shutil.copy(INP5, sim_dir / "inp.5")

        # fort.6 más reciente que inp.5 → resultados al día.
        t_old = 1_700_000_000.0
        t_new = 1_700_000_100.0
        os.utime(sim_dir / "inp.5", (t_old, t_old))
        os.utime(sim_dir / "fort.6", (t_new, t_new))

        all_data, errors = fa.analizar_carpeta(str(tmp), t12)
        check(len(errors) == 0, f"análisis sin errores (errores={errors})")
        sim = all_data["sim1"]
        check(sim["desactualizada"] is False,
              "fort.6 más nuevo que inp.5 → desactualizada=False")

        # inp.5 tocado después del fort.6 → resultados desactualizados.
        os.utime(sim_dir / "inp.5", (t_new + 100, t_new + 100))
        all_data, errors = fa.analizar_carpeta(str(tmp), t12)
        sim = all_data["sim1"]
        check(sim["desactualizada"] is True,
              "inp.5 modificado tras el fort.6 → desactualizada=True")
        check(isinstance(sim.get("fort6_fecha"), str) and len(sim["fort6_fecha"]) > 0,
              f"fort6_fecha presente y no vacía (obtenido {sim.get('fort6_fecha')!r})")


def test_sweep_manifest() -> None:
    section("leer_sweep_manifest — barrido paramétrico (Fase 5 opcional)")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Carpeta sin sweep_manifest.json → None, sin romper (feature opcional).
        check(fa.leer_sweep_manifest(str(root)) is None,
              "sin sweep_manifest.json → None")

        manifest = {
            "timestamp": "2026-07-08T00:00:00+00:00",
            "sweep_type": "flux",
            "description": "Barrido de flujo x0.5/x1.0",
            "fixed_params": {"T_IRR_h": 24.0},
            "n": 2,
            "simulations": [
                {"folder": "TeO2_x0.50", "params": {"XNORM": 0.5}},
                {"folder": "TeO2_x1.00", "params": {"XNORM": 1.0}},
            ],
        }
        (root / "sweep_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        got = fa.leer_sweep_manifest(str(root))
        check(got is not None, "sweep_manifest.json presente → dict devuelto")
        assert got is not None
        check(got.get("sweep_type") == "flux", "sweep_type = 'flux'")
        check(len(got.get("simulations", [])) == 2, "2 simulaciones en el manifest")
        check(got["simulations"][0]["params"]["XNORM"] == 0.5,
              "params.XNORM de la primera simulación = 0.5")

        # JSON corrupto → None, no excepción.
        (root / "sweep_manifest.json").write_text("{no es json valido", encoding="utf-8")
        check(fa.leer_sweep_manifest(str(root)) is None,
              "sweep_manifest.json corrupto → None (sin excepción)")


def main() -> int:
    print("Tests oro del motor fort_analyzer.py (Fase 0)")
    print(f"Fixtures: {REF_SIM}")

    if not Path(FORT6).exists():
        print(f"\nERROR: no se encuentra el fixture {FORT6}")
        return 1
    if not Path(FORT6_F7).exists():
        print(f"\nERROR: no se encuentra el fixture {FORT6_F7}")
        return 1
    if not Path(FORT6_F7_IRR2).exists():
        print(f"\nERROR: no se encuentra el fixture {FORT6_F7_IRR2}")
        return 1

    test_decay_dat()
    test_irradiacion()
    test_enfriamiento()
    test_enfriamiento_f7_3sets()
    test_pico_i131_f7_3sets()
    test_irradiacion_f7_2sets()
    test_pico_f7_irr2sets_integracion()
    test_inp5()
    test_pico_i131()
    test_concentraciones()
    test_densidad_en_analisis()
    test_desactualizada()
    test_sweep_manifest()

    print(f"\n{'-' * 50}")
    print(f"Resultado: {_PASSED} pasados, {_FAILED} fallidos")
    return 0 if _FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
