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
import re
import shutil
import sys
import tempfile
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


def test_pureza_nodo_comun_dos_simulaciones_mesetas_distinta_longitud() -> None:
    section("calcular_pureza_nodo_comun (F16) — dos simulaciones con mesetas de "
            "distinta longitud evaluadas en el MISMO nodo")

    # simA: mismo patrón que v1b/v2/v3/v4 del experimento 2 -- meseta tied de
    # 3 nodos (t=1,2,3), t_pico reportado = 1 (F15: el primero del empate).
    simA = _sim(0.0, [0.0], {"I131": [0.0], "I130": [0.0]},
                t_cool=[1.0, 2.0, 3.0, 4.0],
                datos_cool={"I131": [100.0, 100.0, 100.0, 90.0],
                            "I130": [25.0, 25.0, 25.0, 25.0]})
    # simB: mismo patrón que v1 -- pico propio SIN empate, más tarde (t=2).
    simB = _sim(0.0, [0.0], {"I131": [0.0], "I130": [0.0]},
                t_cool=[1.0, 2.0, 3.0, 4.0],
                datos_cool={"I131": [80.0, 100.0, 90.0, 70.0],
                            "I130": [10.0, 10.0, 10.0, 10.0]})
    all_data = {"simA": simA, "simB": simB}
    impurezas = ["I131", "I130"]

    # Antes de F16 (calcular_pureza por separado, cada sim en su propio
    # pico): NO comparables entre sí -- exactamente el defecto reportado.
    pA_propio = fa.calcular_pureza(simA, "I131", fa.calcular_pico(simA, "I131")["t_pico"], impurezas)
    pB_propio = fa.calcular_pureza(simB, "I131", fa.calcular_pico(simB, "I131")["t_pico"], impurezas)
    assert pA_propio is not None and pB_propio is not None
    check_close(pA_propio["t_pico"], 1.0, "simA (sin F16): evaluada en SU pico, t=1 (primero del empate)")
    check_close(pB_propio["t_pico"], 2.0, "simB (sin F16): evaluada en SU pico, t=2 (sin empate)")

    # F16: nodo común = pico MÁS TEMPRANO entre todas las simulaciones (el de
    # simA, t=1, empatado) -- AMBAS se evalúan ahí, también simB.
    pnc = fa.calcular_pureza_nodo_comun(all_data, "I131", impurezas)
    check(pnc is not None, "pureza_nodo_comun calculada")
    assert pnc is not None
    check_close(pnc["t_comun_h"], 1.0, "nodo común = pico más temprano (simA, t=1)")
    check(pnc["sim_referencia"] == "simA", f"simulación de referencia = simA (obtenido {pnc['sim_referencia']})")
    check(pnc["empate"] is True, "el pico de referencia (simA) está empatado")
    assert pnc["intervalo_pico"] is not None
    check(pnc["intervalo_pico"] == {"t_ini_h": 1.0, "t_fin_h": 3.0, "n_nodos": 3},
          f"intervalo del empate = [1,3] con 3 nodos (obtenido {pnc['intervalo_pico']})")

    pA = pnc["por_simulacion"]["simA"]
    pB = pnc["por_simulacion"]["simB"]
    check_close(pA["P_pct"], 100.0 / (100.0 + 25.0) * 100.0, "simA en el nodo común (t=1): P = 100/(100+25)")
    check_close(pB["P_pct"], 80.0 / (80.0 + 10.0) * 100.0,
                "simB en el nodo común (t=1, NO su propio pico): P = 80/(80+10), "
                "distinto del valor evaluado en su propio pico (t=2)")

    # Override explícito de la simulación de referencia: fuerza el nodo común
    # al pico de simB (t=2, sin empate) -- ambas se reevalúan ahí.
    pnc_b = fa.calcular_pureza_nodo_comun(all_data, "I131", impurezas, sim_referencia="simB")
    assert pnc_b is not None
    check_close(pnc_b["t_comun_h"], 2.0, "override sim_referencia='simB' → nodo común = t=2")
    check(pnc_b["empate"] is False, "el pico de simB no está empatado")
    check_close(pnc_b["por_simulacion"]["simB"]["P_pct"], 100.0 / (100.0 + 10.0) * 100.0,
                "simB en su propio nodo (t=2): P = 100/(100+10)")
    check_close(pnc_b["por_simulacion"]["simA"]["P_pct"], 100.0 / (100.0 + 25.0) * 100.0,
                "simA reevaluada en t=2 (dentro de su meseta, mismo P que en t=1)")

    # Casos borde: sin datos → None, sin lista de impurezas → None.
    check(fa.calcular_pureza_nodo_comun({}, "I131", impurezas) is None,
          "sin simulaciones → None")
    check(fa.calcular_pureza_nodo_comun(all_data, "I131", []) is None,
          "sin isótopos de impureza → None")


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


def test_actividad_especifica_yodo_ref_sim() -> None:
    section("calcular_actividad_especifica_yodo_serie — caso oro (ref_sim, F2 del BACKLOG)")

    t12 = fa.leer_decay_dat(DECAY)
    all_data, errors = fa.analizar_carpeta(str(REF_SIM), t12)
    check(len(errors) == 0, f"análisis de ref_sim sin errores (errores={errors})")
    sim_name = next(iter(all_data))
    sim = all_data[sim_name]

    serie = fa.calcular_actividad_especifica_yodo_serie(sim, "I131", t12)
    check(serie is not None, "serie calculada para ref_sim")
    assert serie is not None
    check(len(serie["serie"]) == 19, f"19 puntos de enfriamiento (obtenido {len(serie['serie'])})")

    # Valor oro en RESTART (t=0 h), comprobado a mano contra el fort.6
    # congelado (fixture v.5 "info thesis" -- NO confundir con el fort.6 v.7
    # usado para diagnosticar el bug de F2b, que es OTRA simulación con
    # población de I127/I129 muy superior; cada fixture tiene su propia
    # firma numérica, ver README.md de fixtures/). Masa total de yodo = suma
    # sobre TODOS los isótopos de yodo presentes de N_iso(0)/N_A·A_iso. En
    # t=0 (RESTART = fin de irradiación) da IGUAL leer I127/I129 de la tabla
    # NUMBER OF ATOMS (I127=1.531e5, I129=6.387e5 átomos/cm³, F2b) que vía
    # N=A(0)/λ (diseño pre-F2b): por definición A=λN, ambas fuentes
    # coinciden en ese instante exacto salvo el redondeo de imprenta del
    # fort.6 en cada tabla (~1e-5 relativo). El diseño viejo y F2b solo
    # divergen de forma apreciable para t>0 (ver
    # test_actividad_especifica_yodo_i129_congelado_vs_creciente). A(I131,0)
    # =38.42 Bq/cm³ (ya verificado en F1).
    p0 = serie["serie"][0]
    check_close(p0["t"], 0.0, "primer punto = RESTART")
    check_close(p0["A_esp_MBq_g"], 4505547272.634922,
                "A_esp(t=0) = A(I131,0)/masa_total_yodo(0), a mano del fort.6 (MBq/g) -- "
                "F2b: I129 leído de NUMBER OF ATOMS en vez de A(0)/λ, residuo <1e-5 rel. "
                "frente al valor pre-F2b (4505514996.653325)",
                rtol=1e-6)

    # "el valor destacado en t_cruce de pureza" (diseño F2, punto 2): en
    # ref_sim el cruce del umbral de pureza ya está en t=0 (F1), así que el
    # valor destacado debe coincidir con A_esp(t=0).
    informe = fa.calcular_informe_isotopo(all_data, "I131", t12)
    aesp_informe = informe["metricas"][sim_name]["actividad_especifica_yodo_serie"]
    assert aesp_informe is not None
    check_close(aesp_informe["t_destacado_h"], 0.0, "t_destacado_h = t_cruce de pureza (=0 en ref_sim)")
    check_close(aesp_informe["valor_destacado_MBq_g"], p0["A_esp_MBq_g"],
                "valor_destacado_MBq_g en t_cruce coincide con A_esp(t=0)", rtol=1e-9)


def test_actividad_especifica_yodo_casos_borde() -> None:
    section("calcular_actividad_especifica_yodo_serie — casos borde (F2 del BACKLOG)")

    # ── Caso "solo I131" (sin ningún otro isótopo de yodo) ──────────────────
    # N(t) se recupera exactamente de A(t)/λ para el propio I131 (nada más
    # que diluya), así que A_esp(t) = A(t)/m(t) se simplifica analíticamente
    # a la actividad específica del isótopo PURO (λ·N_A/masa_atómica),
    # constante en el tiempo pese a que A(t) varía.
    lam_i131 = fa.lam(693200.0)  # T½ I131 real, s
    A_esp_puro_MBq_g = lam_i131 * fa.N_A / 131 / 1e6

    sim_solo = {
        "t_cool": [0.0, 1.0, 2.0, 3.0],
        "datos_cool": {"I131": [38.42, 5000.0, 12000.0, 16500.0]},
        "datos_irr_atomos": {},
    }
    serie_solo = fa.calcular_actividad_especifica_yodo_serie(sim_solo, "I131", {"I131": 693200.0})
    check(serie_solo is not None, "serie calculada (solo I131 presente)")
    assert serie_solo is not None
    for p in serie_solo["serie"]:
        check_close(p["A_esp_MBq_g"], A_esp_puro_MBq_g,
                    f"t={p['t']}: A_esp constante = actividad específica del I131 puro (sin diluyentes)",
                    rtol=1e-9)

    # ── "sin yodo estable presente" (I131 + I129 de vida larga, sin I127) ───
    # Todas las contribuciones vienen de A/λ (nunca del fallback de átomos de
    # irradiación, que solo se usa para isótopos ausentes/estables en
    # datos_cool); el I129 diluye el I131 y A_esp < A_esp_puro.
    sim_sin_estable = {
        "t_cool": [0.0],
        "datos_cool": {"I131": [1000.0], "I129": [1e-9]},
        "datos_irr_atomos": {"I131": [0.0, 1000.0], "I129": [0.0, 700000.0]},
    }
    t12_ie = {"I131": 693200.0, "I129": 5.081e14}
    serie_ie = fa.calcular_actividad_especifica_yodo_serie(sim_sin_estable, "I131", t12_ie)
    check(serie_ie is not None, "serie calculada (I131+I129, sin I127 estable)")
    assert serie_ie is not None
    check(serie_ie["serie"][0]["A_esp_MBq_g"] < A_esp_puro_MBq_g,
          "I129 diluye el I131 -> A_esp < actividad específica del I131 puro")

    # ── No aplica a isótopos que no son de yodo ─────────────────────────────
    check(fa.calcular_actividad_especifica_yodo_serie(sim_solo, "TE131", {"I131": 693200.0}) is None,
          "iso_key no es de yodo -> None")

    # ── Sin datos de enfriamiento / sin ningún isótopo de yodo -> None ──────
    sim_sin_cool = {"t_cool": [], "datos_cool": {}, "datos_irr_atomos": {}}
    check(fa.calcular_actividad_especifica_yodo_serie(sim_sin_cool, "I131", {}) is None,
          "sin datos de enfriamiento -> None")

    sim_sin_yodo = {"t_cool": [0.0, 1.0], "datos_cool": {"TE131": [10.0, 5.0]}, "datos_irr_atomos": {}}
    check(fa.calcular_actividad_especifica_yodo_serie(sim_sin_yodo, "I131", {}) is None,
          "sin ningún isótopo de yodo detectado en el fort.6 -> None")

    # ── valor_destacado_MBq_g interpola en t_destacado_h ────────────────────
    serie_dest = fa.calcular_actividad_especifica_yodo_serie(
        sim_solo, "I131", {"I131": 693200.0}, t_destacado_h=1.5)
    assert serie_dest is not None
    check_close(serie_dest["valor_destacado_MBq_g"], A_esp_puro_MBq_g,
                "valor_destacado_MBq_g en t=1.5h (interpolado) = A_esp constante", rtol=1e-9)


def test_actividad_especifica_yodo_i129_congelado_vs_creciente() -> None:
    section("calcular_actividad_especifica_yodo_serie — F2b: I129 congelado, no vía A(t)/λ")

    # Escenario sintético tipo "irradiación larga" (el caso real donde el bug
    # de F2b importa, per el diagnóstico del BACKLOG: Te127/Te129 alimentan
    # I127/I129 durante horas de enfriamiento, y su actividad -- minúscula
    # pero no cero -- crece varios órdenes de magnitud). Con λ(I129) diminuta,
    # dividir esa actividad creciente por λ dispararía la masa de I129 muy por
    # encima de su población real; el diseño F2b lo evita leyendo I129 de la
    # tabla de átomos y manteniéndolo constante.
    lam_i129 = fa.lam(5.081e14)  # T½ I129, s (DECAY.dat 531290)
    lam_i131 = fa.lam(693200.0)  # T½ I131, s
    t12 = {"I131": 693200.0, "I129": 5.081e14}

    n_i129_final_atomos = 6.387e5  # NUMBER OF ATOMS al fin de irradiación (I129)
    sim = {
        "t_cool": [0.0, 1.0, 2.0, 3.0, 4.0],
        "datos_cool": {
            "I131": [38.42, 5000.0, 9000.0, 13000.0, 16500.0],
            # actividad de I129 creciendo ~1000x durante el enfriamiento
            # (alimentada por Te129, igual que en ref_sim pero exagerada)
            "I129": [8.7e-10, 1e-8, 1e-7, 5e-7, 9.8e-7],
        },
        "datos_irr_atomos": {"I129": [0.0, n_i129_final_atomos]},
    }
    serie = fa.calcular_actividad_especifica_yodo_serie(sim, "I131", t12)
    assert serie is not None

    masa_i129_congelada_g = n_i129_final_atomos / fa.N_A * 129
    masa_i129_via_a_sobre_lambda_ultimo_t_g = (sim["datos_cool"]["I129"][-1] / lam_i129) / fa.N_A * 129
    # La masa "vía A/λ" en el último instante es MUCHO mayor que la congelada
    # (confirma que el escenario ejercita de verdad la diferencia de diseño).
    check(masa_i129_via_a_sobre_lambda_ultimo_t_g > 50 * masa_i129_congelada_g,
          "escenario sintético: A(t)/λ de I129 habría dado una masa >>50x la congelada "
          f"(congelada={masa_i129_congelada_g:.3e} g/cm³, A/λ={masa_i129_via_a_sobre_lambda_ultimo_t_g:.3e} g/cm³)")

    for i, t in enumerate(sim["t_cool"]):
        A_i131_t = sim["datos_cool"]["I131"][i]
        N_i131_t = A_i131_t / lam_i131
        masa_i131_t = N_i131_t / fa.N_A * 131
        masa_esperada = masa_i131_t + masa_i129_congelada_g
        a_esp_esperado = A_i131_t / masa_esperada / 1e6
        check_close(serie["serie"][i]["A_esp_MBq_g"], a_esp_esperado,
                    f"t={t}: A_esp usa I129 CONGELADO (masa={masa_i129_congelada_g:.4e} g/cm³), "
                    "no A(t)/λ", rtol=1e-9)


def test_f14_diluyente_evoluciona_por_precursores() -> None:
    """F14 del BACKLOG (bug confirmado 2026-08-08): F2b congelaba I127/I129
    en su valor de EOI durante todo el enfriamiento -- falso, crecen por
    decaimiento de sus precursores (Te127/Te127M → I127; Te129/Te129M →
    I129). Escenario sintético con precursores explícitos en
    datos_irr_atomos (no disponible como fixture real en este repo: el caso
    de referencia del experimento 1 vive fuera de él, ver el BACKLOG); la
    fórmula de conservación de número másico se verifica AQUÍ de forma
    independiente (sin llamar a _evolucionar_diluyente) y se compara con la
    salida real de calcular_actividad_especifica_yodo_serie.
    """
    section("calcular_actividad_especifica_yodo_serie — F14: diluyentes evolucionan por decaimiento de precursores")

    ln2 = math.log(2)
    t_cool = [0.0, 1.0]  # h

    # Objetivo: I131, T½=1h (3600 s) -- A(t) dado directamente, no depende de
    # ningún precursor en este escenario sintético.
    t12_i131_s = 3600.0
    lam_i131_s = fa.lam(t12_i131_s)
    A_i131 = [1000.0, 500.0]

    # Precursores de A=127: TE127 (T½=1h) y TE127M (T½=3h), DOS precursores
    # del mismo isóbaro alimentando I127 -- ejercita la suma sobre varios
    # precursores, no solo uno.
    t12_te127_s, t12_te127m_s = 3600.0, 3 * 3600.0
    lam_te127_s, lam_te127m_s = fa.lam(t12_te127_s), fa.lam(t12_te127m_s)
    n0_te127, n0_te127m = 1.0e6, 2.0e5
    N_te127  = [n0_te127  * math.exp(-ln2 * t / 1.0) for t in t_cool]  # T½=1h
    N_te127m = [n0_te127m * math.exp(-ln2 * t / 3.0) for t in t_cool]  # T½=3h
    A_te127  = [lam_te127_s  * n for n in N_te127]
    A_te127m = [lam_te127m_s * n for n in N_te127m]
    n0_i127 = 1.0e4  # I127 (estable) al fin de irradiación, tabla NUMBER OF ATOMS

    # Precursor de A=129: TE129 (T½=2h).
    t12_te129_s = 2 * 3600.0
    lam_te129_s = fa.lam(t12_te129_s)
    n0_te129 = 2.0e6
    N_te129 = [n0_te129 * math.exp(-ln2 * t / 2.0) for t in t_cool]
    A_te129 = [lam_te129_s * n for n in N_te129]
    n0_i129 = 2.0e4

    sim = {
        "t_cool": t_cool,
        "datos_cool": {
            "I131": A_i131, "TE127": A_te127, "TE127M": A_te127m, "TE129": A_te129,
        },
        "datos_irr_atomos": {
            "TE127": [n0_te127], "TE127M": [n0_te127m], "TE129": [n0_te129],
            "I127": [n0_i127], "I129": [n0_i129],
        },
    }
    t12_dict = {
        "I131": t12_i131_s, "TE127": t12_te127_s, "TE127M": t12_te127m_s, "TE129": t12_te129_s,
    }

    serie = fa.calcular_actividad_especifica_yodo_serie(sim, "I131", t12_dict)
    assert serie is not None

    for i, t in enumerate(t_cool):
        # Conservación de número másico, calculada AQUÍ de forma
        # independiente (no llama a _evolucionar_diluyente): lo que pierden
        # los precursores de un isóbaro lo gana el diluyente estable/de vida
        # larga de ese isóbaro.
        n_i127_esperado = n0_i127 + (n0_te127 - N_te127[i]) + (n0_te127m - N_te127m[i])
        n_i129_esperado = n0_i129 + (n0_te129 - N_te129[i])
        n_i131_esperado = A_i131[i] / lam_i131_s
        masa_esperada = (n_i131_esperado / fa.N_A * 131
                          + n_i127_esperado / fa.N_A * 127
                          + n_i129_esperado / fa.N_A * 129)
        a_esp_esperado = A_i131[i] / masa_esperada / 1e6
        check_close(serie["serie"][i]["A_esp_MBq_g"], a_esp_esperado,
                    f"t={t}h: A_esp con I127/I129 evolucionando por sus precursores "
                    f"(N_I127={n_i127_esperado:.4e}, N_I129={n_i129_esperado:.4e})", rtol=1e-9)

    # En EOI (t=0) evolucionar y congelar coinciden (nada ha decaído aún) --
    # mismo criterio ya documentado en test_actividad_especifica_yodo_ref_sim.
    n_i127_congelado = n0_i127
    n_i129_congelado = n0_i129
    n_i131_t0 = A_i131[0] / lam_i131_s
    masa_congelada_t0 = (n_i131_t0 / fa.N_A * 131 + n_i127_congelado / fa.N_A * 127
                          + n_i129_congelado / fa.N_A * 129)
    a_esp_congelado_t0 = A_i131[0] / masa_congelada_t0 / 1e6
    check_close(serie["serie"][0]["A_esp_MBq_g"], a_esp_congelado_t0,
                "en t=0 (EOI) evolucionar y congelar coinciden (nada decaído todavía)", rtol=1e-9)

    # Test NEGATIVO (F14 del BACKLOG): en t=1h, congelar los diluyentes en su
    # valor de EOI (el diseño F2b, ya corregido) da una A_esp
    # SISTEMÁTICAMENTE MAYOR que la correcta -- menos masa en el
    # denominador, exactamente el sesgo diagnosticado (4.5928e9 MBq/g, 99.9 %
    # del techo, frente al 2.210e9 real del caso de referencia real). Aquí,
    # con el escenario sintético, se comprueba el mismo signo y una
    # magnitud comparable (factor > 1.3), no los valores absolutos del
    # experimento 1 (fuera de este repo).
    n_i131_t1 = A_i131[1] / lam_i131_s
    masa_congelada_t1 = (n_i131_t1 / fa.N_A * 131 + n0_i127 / fa.N_A * 127 + n0_i129 / fa.N_A * 129)
    a_esp_congelado_t1 = A_i131[1] / masa_congelada_t1 / 1e6
    a_esp_correcto_t1 = serie["serie"][1]["A_esp_MBq_g"]
    check(a_esp_congelado_t1 > a_esp_correcto_t1 * 1.3,
          f"test negativo: congelar los diluyentes en t=1h SOBREESTIMA A_esp "
          f"(congelado={a_esp_congelado_t1:.4e}, correcto={a_esp_correcto_t1:.4e}, "
          f"factor={a_esp_congelado_t1 / a_esp_correcto_t1:.3f})")


def test_actividad_especifica_yodo_techo_fisico() -> None:
    section("calcular_actividad_especifica_yodo_serie — techo físico sin portador (F2b)")

    # A_esp no puede superar la actividad específica del I131 puro (sin
    # portador): λ(I131)·N_A/masa_atómica(I131) ≈ 4.596e9 MBq/g. Cualquier
    # masa de yodo (portador incluido) solo puede DILUIR, nunca concentrar
    # por encima de ese límite. Se comprueba en TODO instante t y en TODA
    # simulación: ref_sim (datos reales) + los casos sintéticos ya definidos
    # arriba (borde y congelado-vs-creciente).
    lam_i131 = fa.lam(693200.0)
    techo_MBq_g = lam_i131 * fa.N_A / 131 / 1e6

    t12 = fa.leer_decay_dat(DECAY)
    all_data, errors = fa.analizar_carpeta(str(REF_SIM), t12)
    assert not errors
    sim_ref = next(iter(all_data.values()))
    serie_ref = fa.calcular_actividad_especifica_yodo_serie(sim_ref, "I131", t12)
    assert serie_ref is not None
    peores_ref = [p["A_esp_MBq_g"] for p in serie_ref["serie"] if p["A_esp_MBq_g"] is not None]
    check(all(v <= techo_MBq_g * (1 + 1e-9) for v in peores_ref),
          f"ref_sim: A_esp(t) <= techo físico ({techo_MBq_g:.6e} MBq/g) en los "
          f"{len(peores_ref)} timesteps (máximo obtenido {max(peores_ref):.6e})")

    lam_i129 = fa.lam(5.081e14)
    sim_congelado = {
        "t_cool": [0.0, 1.0, 2.0, 3.0, 4.0],
        "datos_cool": {
            "I131": [38.42, 5000.0, 9000.0, 13000.0, 16500.0],
            "I129": [8.7e-10, 1e-8, 1e-7, 5e-7, 9.8e-7],
        },
        "datos_irr_atomos": {"I129": [0.0, 6.387e5]},
    }
    serie_congelado = fa.calcular_actividad_especifica_yodo_serie(sim_congelado, "I131", {"I131": 693200.0, "I129": 5.081e14})
    assert serie_congelado is not None
    valores_congelado = [p["A_esp_MBq_g"] for p in serie_congelado["serie"]]
    check(all(v <= techo_MBq_g * (1 + 1e-9) for v in valores_congelado),
          f"caso sintético congelado-vs-creciente: A_esp(t) <= techo físico en todo t "
          f"(máximo obtenido {max(valores_congelado):.6e})")


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
    check("actividad_especifica_yodo_serie" in m, "clave actividad_especifica_yodo_serie (F2) presente en el informe")
    check(m["actividad_especifica_yodo_serie"] is None,
          "sin datos de enfriamiento en este fixture → actividad_especifica_yodo_serie = None (coherente)")
    check(informe["isotopos_impureza_default"] == ["I130", "I131"],
          f"impurezas por defecto = mismo elemento (obtenido {informe['isotopos_impureza_default']})")
    # F16 del BACKLOG: pureza_nodo_comun presente a nivel de informe (no por
    # simulación -- es inherentemente cruzada entre simulaciones).
    check("pureza_nodo_comun" in informe, "clave pureza_nodo_comun (F16) presente en el informe")
    pnc = informe["pureza_nodo_comun"]
    check(pnc is not None and pnc["sim_referencia"] == "simA",
          "con una única simulación, esa es la propia referencia")

    # Override explícito de la lista de impurezas (solo el propio isótopo).
    informe_solo = fa.calcular_informe_isotopo(all_data, "I131", t12_dict, isotopos_impureza=["I131"])
    check_close(informe_solo["metricas"]["simA"]["pureza"]["P_pct"], 100.0,
                "impurezas = [I131] → pureza 100 %")


def test_f13_decay_dat_por_simulacion() -> None:
    """F13 del BACKLOG: T½ leído del DECAY.dat de CADA simulación, no un
    único valor aplicado globalmente a toda la carpeta. Se copia ref_sim dos
    veces (mismo fort.6, misma física) y se edita el T½(I131) del DECAY.dat
    de UNA de las copias — antes de esta corrección, analizar_carpeta solo
    leía el DECAY.dat de la PRIMERA simulación descubierta y lo aplicaba a
    ambas; con la corrección, cada una resuelve el suyo propio.
    """
    section("F13 — DECAY.dat leído por simulación, no globalmente")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sim_a = root / "simA"
        sim_b = root / "simB"
        shutil.copytree(REF_SIM, sim_a)
        shutil.copytree(REF_SIM, sim_b)

        decay_b = sim_b / "DECAY.dat"
        text = decay_b.read_text(errors="ignore")
        # Línea de I131 (ZZAAAS=531310): "...531310  <ST>  <espacios>6.932E+05...".
        # T½ real de ref_sim = 693200 s; lo cambiamos a 693400 s SOLO en simB.
        nuevo_texto, n = re.subn(
            r"(531310\s+\d+\s+)6\.932E\+05",
            r"\g<1>6.934E+05",
            text,
        )
        check(n == 1, f"línea de I131 (531310, T½=6.932E+05 s) encontrada y editada en simB (obtenido {n} reemplazos)")
        decay_b.write_text(nuevo_texto)

        fallback_t12 = fa.build_t12_dict(fa.DEFAULT_SEMIVIDAS)
        all_data, errors = fa.analizar_carpeta(str(root), fallback_t12)
        check(errors == {}, f"análisis sin errores (errores={errors})")
        check(set(all_data.keys()) == {"simA", "simB"}, "las 2 simulaciones descubiertas")

        check(all_data["simA"]["t12_source"] == "decay_dat", "simA: T½ resuelto desde su propio DECAY.dat")
        check(all_data["simB"]["t12_source"] == "decay_dat", "simB: T½ resuelto desde su propio DECAY.dat")
        check_close(all_data["simA"]["_t12_dict"]["I131"], 693200.0,
                    "simA resuelve T½(I131) = 693200 s (el original, sin tocar)")
        check_close(all_data["simB"]["_t12_dict"]["I131"], 693400.0,
                    "simB resuelve T½(I131) = 693400 s (el editado) — NO hereda el de simA")

        informe = fa.calcular_informe_isotopo(all_data, "I131", fallback_t12)
        aesp_a = informe["metricas"]["simA"]["nuclear_props"]["A_esp"]
        aesp_b = informe["metricas"]["simB"]["nuclear_props"]["A_esp"]
        check(aesp_a is not None and aesp_b is not None,
              "techo sin portador (A_esp) calculado en ambas simulaciones")
        check(abs(aesp_a - aesp_b) > 1.0,
              f"techos DISTINTOS entre simulaciones con DECAY.dat distinto (simA={aesp_a}, simB={aesp_b})")
        check(aesp_a > aesp_b,
              "T½ mayor (simB) → λ menor → techo (λ·N_A/A) menor que simA, coherente")

        # F2/F2b: la actividad específica del yodo también usa N(t)=A(t)/λ con
        # el λ propio de CADA simulación durante el enfriamiento.
        serie_a = informe["metricas"]["simA"]["actividad_especifica_yodo_serie"]
        serie_b = informe["metricas"]["simB"]["actividad_especifica_yodo_serie"]
        check(serie_a is not None and serie_b is not None,
              "actividad_especifica_yodo_serie presente en ambas simulaciones")
        if serie_a and serie_b:
            va = serie_a["serie"][0]["A_esp_MBq_g"]
            vb = serie_b["serie"][0]["A_esp_MBq_g"]
            check(abs(va - vb) > 1e-3,
                  f"actividad específica del yodo distinta entre simulaciones (simA={va}, simB={vb})")


def main() -> int:
    print("Tests oro de las métricas de optimización de producción (Fase 5)")

    test_saturacion_exacta()
    test_rendimiento_lineal_y_saturante()
    test_isotopos_mismo_elemento()
    test_pureza_dos_isotopos()
    test_pureza_nodo_comun_dos_simulaciones_mesetas_distinta_longitud()
    test_pureza_serie_ref_sim_tres_timesteps()
    test_pureza_serie_casos_borde_sinteticos()
    test_actividad_especifica_yodo_ref_sim()
    test_actividad_especifica_yodo_casos_borde()
    test_actividad_especifica_yodo_i129_congelado_vs_creciente()
    test_f14_diluyente_evoluciona_por_precursores()
    test_actividad_especifica_yodo_techo_fisico()
    test_informe_isotopo_incluye_metricas()
    test_f13_decay_dat_por_simulacion()

    print(f"\n{'-' * 50}")
    print(f"Resultado: {_PASSED} pasados, {_FAILED} fallidos")
    return 0 if _FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
