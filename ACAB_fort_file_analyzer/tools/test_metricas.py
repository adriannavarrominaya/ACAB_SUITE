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

FIXTURES = REPO_ROOT / "tests" / "fixtures"
REF_SIM = FIXTURES / "ref_sim"
DECAY = str(REF_SIM / "DECAY.dat")

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


def test_pureza_serie_ref_sim_tres_timesteps() -> None:
    section("calcular_pureza_serie — 3 timesteps verificados a mano (ref_sim, F1 Fase 1)")

    t12 = fa.leer_decay_dat(DECAY)
    all_data, errors = fa.analizar_carpeta(str(REF_SIM), t12)
    check(len(errors) == 0, f"análisis de ref_sim sin errores (errores={errors})")
    sim = next(iter(all_data.values()))

    disponibles = set(sim["datos_irr_Bq"].keys()) | set(sim["datos_cool"].keys())
    impurezas = fa.isotopos_mismo_elemento("I131", disponibles)

    serie = fa.calcular_pureza_serie(sim, "I131", impurezas)
    check(serie is not None, "serie calculada para ref_sim")
    assert serie is not None

    puntos = {round(p["t"], 4): p["P_pct"] for p in serie["serie"]}
    check(len(serie["serie"]) == 19, f"19 puntos de enfriamiento (obtenido {len(serie['serie'])})")

    # Valores oro leídos a mano del fort.6 congelado (A_I131 y A_total = suma de
    # isótopos de yodo presentes en esa fila; ver tests/fixtures/README.md para
    # el contexto físico: en esta simulación —pulso de ~10 s sobre TeO2— la
    # producción de otros isótopos de yodo es despreciable frente al I131 desde
    # el mismísimo shutdown, así que el cruce del umbral ocurre en t=0 y "cerca
    # del cruce" cae en el timestep siguiente (t=0.25 h).
    check_close(puntos[0.0],  99.999868941103, "temprano: P(t=0.00 h) = A_I131/A_tot·100, a mano del fort.6", rtol=1e-9)
    check_close(puntos[0.25], 99.999999167045, "cercano al cruce: P(t=0.25 h), a mano del fort.6", rtol=1e-9)
    check_close(puntos[4.5],  99.999999882318, "tardío: P(t=4.50 h), a mano del fort.6", rtol=1e-9)

    check(serie["estado"] == "alcanzado_en_fin_irradiacion",
          f"ya >= 99.9 % al fin de la irradiación (obtenido {serie['estado']})")
    assert serie["t_cruce"] is not None
    check_close(serie["t_cruce"]["t_h"], 0.0, "t_cruce = 0 (punto real, sin interpolar)")
    check(serie["t_cruce"]["estimado"] is False, "t_cruce=0 no está marcado como estimado")
    check(serie["aviso_no_monotono"] is None,
          f"P se mantiene >= umbral todo el enfriamiento (obtenido {serie['aviso_no_monotono']})")

    ventana = serie["ventana_administracion"]
    assert ventana is not None
    check_close(ventana["A_pico"], 1.6500e4, "ventana: A_pico I131 coincide con calcular_pico", rtol=2e-3)
    check_close(ventana["A_objetivo"], 38.42, "ventana: A(I131) en t_cruce=0 = 38.42 Bq/cm³", rtol=1e-6)


def test_pureza_serie_casos_borde_sinteticos() -> None:
    section("calcular_pureza_serie — casos borde (fort.6 sintéticos mínimos)")

    # ── Caso 1: cruce DURANTE el enfriamiento, interpolación log-lineal ──────
    # A_X1 constante = 100; A_Y1(t) = 1000·2^-t (decaimiento exacto, T½=1h en
    # estas unidades sintéticas) → P(t) es exactamente log-lineal por
    # construcción, así que la solución analítica cerrada coincide con la
    # bisección hasta la tolerancia numérica.
    t_cool = list(range(0, 21))  # 0..20 h
    A_x1 = [100.0] * len(t_cool)
    A_y1 = [1000.0 * (2.0 ** -t) for t in t_cool]
    sim_cruce = {
        "T_IRR_h": 1.0, "t_irr": [0.0, 1.0],
        "datos_irr_Bq": {"X1": [0.0, 100.0], "Y1": [0.0, 1000.0]},
        "t_cool": t_cool,
        "datos_cool": {"X1": A_x1, "Y1": A_y1},
    }
    serie_cruce = fa.calcular_pureza_serie(sim_cruce, "X1", ["X1", "Y1"])
    check(serie_cruce is not None, "serie calculada (caso cruce interpolado)")
    assert serie_cruce is not None
    check(serie_cruce["estado"] == "alcanzado_en_enfriamiento",
          f"cruce localizado dentro del enfriamiento (obtenido {serie_cruce['estado']})")
    assert serie_cruce["t_cruce"] is not None
    check(serie_cruce["t_cruce"]["estimado"] is True, "t_cruce interpolado se marca estimado=True")
    # Solución cerrada de 100/(100+1000·2^-t) = 0.999.
    t_cruce_exacto = -math.log(0.1 / 999.0) / math.log(2.0)
    check_close(serie_cruce["t_cruce"]["t_h"], t_cruce_exacto,
                "t_cruce interpolado coincide con la solución analítica", rtol=1e-6)
    check(serie_cruce["aviso_no_monotono"] is None,
          "P(t) sigue >= umbral tras el cruce (decaimiento puro, sin aviso)")

    # ── Caso 2: P ya >= 99,9 % al fin de la irradiación (t_cruce=0) ─────────
    sim_ya = {
        "T_IRR_h": 1.0, "t_irr": [0.0, 1.0],
        "datos_irr_Bq": {"X1": [0.0, 999.0], "Y1": [0.0, 1.0]},
        "t_cool": [0.0, 1.0, 2.0],
        "datos_cool": {"X1": [999.0, 999.0, 999.0], "Y1": [1.0, 1.0, 1.0]},
    }
    serie_ya = fa.calcular_pureza_serie(sim_ya, "X1", ["X1", "Y1"])
    assert serie_ya is not None
    check(serie_ya["estado"] == "alcanzado_en_fin_irradiacion",
          f"P(0) = 999/1000 = 99.9 % → ya alcanzado (obtenido {serie_ya['estado']})")
    check_close(serie_ya["t_cruce"]["t_h"], 0.0, "t_cruce = 0")

    # ── Caso 3: el umbral nunca se alcanza en la ventana simulada ───────────
    sim_nunca = {
        "T_IRR_h": 1.0, "t_irr": [0.0, 1.0],
        "datos_irr_Bq": {"X1": [0.0, 50.0], "Y1": [0.0, 50.0]},
        "t_cool": [0.0, 1.0, 2.0],
        "datos_cool": {"X1": [50.0, 50.0, 50.0], "Y1": [50.0, 50.0, 50.0]},
    }
    serie_nunca = fa.calcular_pureza_serie(sim_nunca, "X1", ["X1", "Y1"])
    assert serie_nunca is not None
    check(serie_nunca["estado"] == "no_alcanzado",
          f"P(t) = 50 % constante → nunca alcanzado (obtenido {serie_nunca['estado']})")
    check(serie_nunca["t_cruce"] is None, "sin t_cruce cuando no se alcanza (sin extrapolar)")
    check(serie_nunca["ventana_administracion"] is None,
          "sin ventana de administración cuando no se alcanza el umbral")

    # ── Caso 4: no monotonía — cruza y luego vuelve a bajar del umbral ──────
    # X1/Y1 log-lineales entre t=0 (P=0.1 %) y t=1 (P=99.9 % exacto, el cruce
    # cae justo en un timestep real) se mantienen en t=2 y se invierten en
    # t=3 (P vuelve a 0.1 %) → P(t) sube, cruza el umbral, y vuelve a bajar.
    sim_no_mono = {
        "T_IRR_h": 1.0, "t_irr": [0.0, 1.0],
        "datos_irr_Bq": {"X1": [1.0, 999.0], "Y1": [999.0, 1.0]},
        "t_cool": [0.0, 1.0, 2.0, 3.0],
        "datos_cool": {
            "X1": [1.0, 999.0, 999.0, 1.0],
            "Y1": [999.0, 1.0, 1.0,   999.0],
        },
    }
    serie_no_mono = fa.calcular_pureza_serie(sim_no_mono, "X1", ["X1", "Y1"])
    assert serie_no_mono is not None
    check(serie_no_mono["estado"] == "alcanzado_en_enfriamiento",
          f"cruce localizado en t≈1 h (obtenido {serie_no_mono['estado']})")
    assert serie_no_mono["t_cruce"] is not None
    check_close(serie_no_mono["t_cruce"]["t_h"], 1.0, "t_cruce ≈ 1 h (P=99.9 % exacto en ese punto real)",
                rtol=1e-6, atol=1e-6)
    check(serie_no_mono["aviso_no_monotono"] is not None,
          "P vuelve a bajar del umbral en t=3 h → aviso presente")
    if serie_no_mono["aviso_no_monotono"] is not None:
        check_close(serie_no_mono["aviso_no_monotono"]["t_h"], 3.0,
                    "aviso apunta al primer timestep real que vuelve a bajar")

    # ── Sin lista de impurezas / sin datos de enfriamiento → None ───────────
    check(fa.calcular_pureza_serie(sim_ya, "X1", []) is None,
          "lista de impurezas vacía → calcular_pureza_serie devuelve None")
    sim_sin_cool = {
        "T_IRR_h": 1.0, "t_irr": [0.0, 1.0],
        "datos_irr_Bq": {"X1": [0.0, 100.0]},
        "t_cool": [], "datos_cool": {},
    }
    check(fa.calcular_pureza_serie(sim_sin_cool, "X1", ["X1"]) is None,
          "sin datos de enfriamiento → calcular_pureza_serie devuelve None")


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
    # Este fixture sintético no tiene fase de enfriamiento (t_cool vacío): la
    # clave existe pero su valor es None, coherente con el dominio de F1
    # ("solo fase de enfriamiento"); la serie real se verifica con ref_sim en
    # test_pureza_serie_ref_sim_tres_timesteps.
    check("pureza_serie" in m, "clave pureza_serie (F1) presente en el informe")
    check(m["pureza_serie"] is None,
          "sin datos de enfriamiento en este fixture → pureza_serie = None (coherente)")
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
    test_pureza_serie_ref_sim_tres_timesteps()
    test_pureza_serie_casos_borde_sinteticos()
    test_informe_isotopo_incluye_metricas()

    print(f"\n{'-' * 50}")
    print(f"Resultado: {_PASSED} pasados, {_FAILED} fallidos")
    return 0 if _FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
