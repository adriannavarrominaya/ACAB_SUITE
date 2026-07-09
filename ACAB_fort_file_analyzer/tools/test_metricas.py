"""test_metricas.py — Tests oro de las métricas de optimización (Fase 5).

Script autocontenido, sin framework (estilo de la suite ACAB). A diferencia de
test_fort_analyzer.py, estos tests no usan la ref_sim: construyen simulaciones
sintéticas con curvas conocidas analíticamente (saturación exponencial exacta,
crecimiento lineal, actividades constantes) para poder comprobar cada fórmula
de fort_analyzer.calcular_saturacion / calcular_rendimiento / calcular_pureza
contra su resultado exacto.

Uso:
    python tools/test_metricas.py

Devuelve código de salida 0 si todo pasa, 1 si algún test falla.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

import fort_analyzer as fa  # noqa: E402

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


def check_close(got, expected, msg: str, rtol: float = 1e-6, atol: float = 0.0) -> None:
    try:
        if math.isclose(float(got), float(expected), rel_tol=rtol, abs_tol=atol):
            _ok(f"{msg} (={got})")
        else:
            _fail(f"{msg}: obtenido {got}, esperado {expected} (rtol={rtol})")
    except (TypeError, ValueError):
        _fail(f"{msg}: valor no numérico {got!r}")


def section(name: str) -> None:
    print(f"\n== {name} ==")


def _sim(T_irr_h: float, t_irr, datos_irr_Bq: dict, t_cool=(), datos_cool: dict | None = None) -> dict:
    """Build a minimal synthetic simulation dict (only the fields the metric
    functions read)."""
    return {
        "T_IRR_h":      T_irr_h,
        "t_irr":        list(t_irr),
        "datos_irr_Bq": {k: list(v) for k, v in datos_irr_Bq.items()},
        "t_cool":       list(t_cool),
        "datos_cool":   {k: list(v) for k, v in (datos_cool or {}).items()},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_saturacion_exacta() -> None:
    section("calcular_saturacion — curva exactamente exponencial")

    # λ_h = ln2 / T12_h con T12 = 1 h (3600 s) → t_50% = T½ exactamente.
    T12_s = 3600.0
    lam_h = math.log(2) / 1.0
    A_sat_true = 1000.0
    T_irr = 5.0
    t_irr = np.arange(0, T_irr + 1e-9, 1.0)  # 0,1,2,3,4,5
    A = A_sat_true * (1.0 - np.exp(-lam_h * t_irr))

    sim = _sim(T_irr, t_irr, {"X1": A})
    t12_dict = {"X1": T12_s}

    sat = fa.calcular_saturacion(sim, "X1", t12_dict)
    check(sat is not None, "curva de saturación calculada (T½ finita, T_irr > 0)")
    assert sat is not None

    check_close(sat["A_sat"], A_sat_true, "A_sat reproduce el valor exacto", rtol=1e-6)
    check(len(sat["puntos"]) == len(t_irr), "un punto teórico por cada tiempo de irradiación")
    for (t_p, a_p), t_e, a_e in zip(sat["puntos"], t_irr, A):
        check_close(a_p, a_e, f"A_teo(t={t_e}) coincide con la curva ACAB de origen", rtol=1e-6)

    tabla = {round(row["pct"]): row for row in sat["tabla"]}
    # t_x = -ln(1-x)/λ_h; con λ_h = ln2/1h, t_50% = T½ = 1 h exactamente.
    check_close(tabla[50]["t_x_h"], 1.0, "t_50% = T½ = 1 h")
    check_close(tabla[75]["t_x_h"], 2.0, "t_75% = 2·T½ = 2 h")
    check_close(tabla[90]["t_x_h"], math.log2(10), "t_90% = log2(10)·T½ ≈ 3.3219 h")
    check_close(tabla[95]["t_x_h"], math.log2(20), "t_95% = log2(20)·T½ ≈ 4.3219 h")
    check(all(row["alcanzable"] for row in sat["tabla"]),
          "50/75/90/95 % caben dentro de T_irr = 5 h")

    # Isótopo estable (T½ = inf) → sin curva de saturación definida.
    sat_stable = fa.calcular_saturacion(sim, "X1", {"X1": math.inf})
    check(sat_stable is None, "isótopo estable → calcular_saturacion devuelve None")

    # T_irr = 0 → sin curva.
    sim_sin_irr = _sim(0.0, [], {})
    check(fa.calcular_saturacion(sim_sin_irr, "X1", t12_dict) is None,
          "T_irr = 0 → calcular_saturacion devuelve None")


def test_rendimiento_lineal_y_saturante() -> None:
    section("calcular_rendimiento — crecimiento lineal vs. curva saturante")

    # Crecimiento exactamente lineal: A(t) = 100·t → el ritmo del último tramo
    # coincide exactamente con el ritmo medio (caso límite: compensa == True).
    T_irr = 10.0
    t_irr = np.arange(0, T_irr + 1e-9, 1.0)
    A_lin = 100.0 * t_irr
    sim_lin = _sim(T_irr, t_irr, {"X1": A_lin})

    r_lin = fa.calcular_rendimiento(sim_lin, "X1")
    check(r_lin is not None, "rendimiento calculado (T_irr > 0)")
    assert r_lin is not None
    check_close(r_lin["rendimiento_medio"], 100.0, "rendimiento medio = A_pico/T_irr = 100")
    check_close(r_lin["A_fin"], 1000.0, "A_fin = A(T_irr) = 1000")
    check_close(r_lin["ganancia_marginal"], 100.0,
                "ganancia marginal = ritmo medio en crecimiento lineal exacto")
    check(r_lin["compensa_seguir"] is True,
          "crecimiento lineal exacto → compensa_seguir = True (marginal >= medio)")

    # Curva saturante (misma familia que el test anterior): el último tramo ya
    # casi no aporta actividad nueva → ganancia marginal << rendimiento medio.
    lam_h = math.log(2) / 1.0  # T½ = 1 h
    A_sat_true = 1000.0
    A_sat_curve = A_sat_true * (1.0 - np.exp(-lam_h * t_irr))
    sim_sat = _sim(T_irr, t_irr, {"X1": A_sat_curve})

    r_sat = fa.calcular_rendimiento(sim_sat, "X1")
    assert r_sat is not None
    check(r_sat["ganancia_marginal"] < r_sat["rendimiento_medio"],
          f"curva saturante → ganancia marginal ({r_sat['ganancia_marginal']:.4g}) "
          f"< rendimiento medio ({r_sat['rendimiento_medio']:.4g})")
    check(r_sat["compensa_seguir"] is False,
          "curva ya saturada → compensa_seguir = False")

    # T_irr = 0 → sin rendimiento definido.
    check(fa.calcular_rendimiento(_sim(0.0, [], {}), "X1") is None,
          "T_irr = 0 → calcular_rendimiento devuelve None")


def test_isotopos_mismo_elemento() -> None:
    section("isotopos_mismo_elemento — filtro por elemento")

    disponibles = {"I130", "I131", "I132", "TE131", "TE131M", "XE133"}
    mismos = fa.isotopos_mismo_elemento("I131", disponibles)
    check(mismos == ["I130", "I131", "I132"],
          f"solo isótopos de I, orden alfabético (obtenido {mismos})")

    mismos_te = fa.isotopos_mismo_elemento("TE131M", disponibles)
    check(set(mismos_te) == {"TE131", "TE131M"},
          f"TE131M → mismos-elemento incluye TE131 y TE131M (obtenido {mismos_te})")


def test_pureza_dos_isotopos() -> None:
    section("calcular_pureza — dos isótopos con actividades conocidas")

    # Actividades constantes (mismo valor en t=0 y t=1) para que la
    # interpolación en t_pico=1.0 devuelva exactamente el valor de la tabla,
    # sin ambigüedad de interpolación.
    T_irr = 1.0
    t_irr = [0.0, 1.0]
    sim = _sim(T_irr, t_irr, {
        "I131": [0.0, 800.0],
        "I130": [0.0, 200.0],
    })

    pureza = fa.calcular_pureza(sim, "I131", t_pico=1.0, isotopos_impureza=["I131", "I130"])
    check(pureza is not None, "pureza calculada")
    assert pureza is not None
    check_close(pureza["P_pct"], 80.0, "P = 800/(800+200)·100 = 80 %")

    contrib = {c["iso"]: c for c in pureza["contribuciones"]}
    check_close(contrib["I131"]["pct"], 80.0, "contribución I131 = 80 %")
    check_close(contrib["I130"]["pct"], 20.0, "contribución I130 = 20 %")

    # t_pico desconocido → sin pureza definida.
    check(fa.calcular_pureza(sim, "I131", None, ["I131", "I130"]) is None,
          "t_pico = None → calcular_pureza devuelve None")

    # Sin isótopos de impureza → sin pureza definida.
    check(fa.calcular_pureza(sim, "I131", 1.0, []) is None,
          "lista de impurezas vacía → calcular_pureza devuelve None")


def test_informe_isotopo_incluye_metricas() -> None:
    section("calcular_informe_isotopo — métricas Fase 5 integradas por simulación")

    T_irr = 5.0
    t_irr = np.arange(0, T_irr + 1e-9, 1.0)
    lam_h = math.log(2) / 1.0
    A_i131 = 1000.0 * (1.0 - np.exp(-lam_h * t_irr))
    A_i130 = 200.0 * (1.0 - np.exp(-lam_h * t_irr))

    all_data = {
        "simA": _sim(T_irr, t_irr, {"I131": A_i131, "I130": A_i130}),
    }
    t12_dict = {"I131": 3600.0, "I130": 3600.0}

    informe = fa.calcular_informe_isotopo(all_data, "I131", t12_dict)
    check("metricas" in informe and "simA" in informe["metricas"],
          "informe incluye metricas por simulación")
    m = informe["metricas"]["simA"]
    check(m["saturacion"] is not None, "saturación presente en el informe")
    check(m["rendimiento"] is not None, "rendimiento presente en el informe")
    check(m["pureza"] is not None, "pureza presente en el informe")
    check(informe["isotopos_impureza_default"] == ["I130", "I131"],
          f"impurezas por defecto = mismo elemento (obtenido {informe['isotopos_impureza_default']})")

    # Override explícito de la lista de impurezas (solo el propio isótopo).
    informe_solo = fa.calcular_informe_isotopo(all_data, "I131", t12_dict, isotopos_impureza=["I131"])
    check_close(informe_solo["metricas"]["simA"]["pureza"]["P_pct"], 100.0,
                "impurezas = [I131] → pureza 100 %")


def main() -> int:
    print("Tests oro de las métricas de optimización de producción (Fase 5)")

    test_saturacion_exacta()
    test_rendimiento_lineal_y_saturante()
    test_isotopos_mismo_elemento()
    test_pureza_dos_isotopos()
    test_informe_isotopo_incluye_metricas()

    print(f"\n{'-' * 50}")
    print(f"Resultado: {_PASSED} pasados, {_FAILED} fallidos")
    return 0 if _FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
