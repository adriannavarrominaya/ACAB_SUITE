"""test_photon.py — Tests oro del espectro gamma desde PHOTON.dat (Fases 1
y 2 de runbook_B1_espectro_gamma.md).

Script autocontenido, sin framework (estilo de la suite ACAB). Ejecuta
fort_analyzer.leer_photon_dat / calcular_espectro_gamma contra el extracto
congelado tests/fixtures/ref_sim/PHOTON_extract.dat (16 nucleidos de la
cadena Te->I->Xe, formato original CRLF byte a byte, NO regenerado) y la
ref_sim congelada (Fase 2).

Uso:
    python tools/test_photon.py

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

import fort_analyzer as fa  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures"
REF_SIM = FIXTURES / "ref_sim"
PHOTON_EXTRACT = str(REF_SIM / "PHOTON_extract.dat")
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

def test_leer_photon_dat_extracto() -> None:
    section("leer_photon_dat — extracto congelado (16 nucleidos Te→I→Xe)")

    lineas = fa.leer_photon_dat(PHOTON_EXTRACT)

    nucleidos_esperados = {
        "TE131", "TE131M", "TE132",
        "I128", "I129", "I130", "I131", "I132", "I132M",
        "I133", "I133M", "I134", "I134M", "I135",
        "XE133", "XE133M",
    }
    check(set(lineas.keys()) == nucleidos_esperados,
          f"16 nucleidos parseados (obtenido {sorted(lineas.keys())})")

    # Isómero como entrada distinta del estado fundamental.
    check("TE131M" in lineas and "TE131" in lineas and lineas["TE131M"] != lineas["TE131"],
          "TE131M es una entrada distinta de TE131 (isómero)")

    # nº de líneas gamma por nucleido (cabecera del fichero).
    check(len(lineas["I131"]) == 18, f"I131 tiene 18 líneas gamma (obtenido {len(lineas['I131'])})")
    check(len(lineas["XE133"]) == 6, f"XE133 tiene 6 líneas gamma (obtenido {len(lineas['XE133'])})")
    check(len(lineas["I129"]) == 1, f"I129 tiene 1 línea gamma (obtenido {len(lineas['I129'])}) — cabecera 'n=1' con una sola línea de datos parcial")

    # Línea 364,49 keV / 81,2 % del I131 (verificada contra ENSDF, cabecera
    # del runbook B1). El fichero la da en MeV (3.6449E-01); el parser
    # convierte a keV (convención de espectrometría, decisión de diseño B1).
    linea_364 = next((l for l in lineas["I131"] if math.isclose(l[0], 364.49, rel_tol=1e-4)), None)
    check(linea_364 is not None, "línea de 364,49 keV presente en I131")
    assert linea_364 is not None
    check_close(linea_364[1], 81.2, "intensidad de la línea 364,49 keV del I131 = 81,2 %", rtol=1e-4)

    # Última línea de un bloque con nº de líneas no múltiplo de 3 (I130=47
    # líneas -> última fila de datos con solo 2 pares, no 3): el parser debe
    # parar exactamente en el nº esperado, sin arrastrar tokens del
    # siguiente bloque.
    check(len(lineas["I130"]) == 47, f"I130 tiene 47 líneas gamma (obtenido {len(lineas['I130'])})")
    check(len(lineas["I132"]) == 160, f"I132 tiene 160 líneas gamma (obtenido {len(lineas['I132'])})")

    # Todas las energías e intensidades son numéricas y positivas.
    check(all(e_kev > 0 and intensidad > 0
               for filas in lineas.values() for e_kev, intensidad in filas),
          "todas las energías e intensidades del extracto son > 0")


def test_leer_photon_dat_nucleido_ausente() -> None:
    section("leer_photon_dat — nucleido sin entrada en la librería")

    lineas = fa.leer_photon_dat(PHOTON_EXTRACT)
    # I130M (visto en el inventario del fort.6 de referencia) no está en
    # este extracto: debe simplemente no tener clave, nunca un error —
    # el caller (Fase 2) es quien decide listarlo como "sin líneas gamma".
    check("I130M" not in lineas, "I130M ausente del extracto (no rompe el parser)")


def test_calcular_espectro_gamma_cruce_de_nombres() -> None:
    section("calcular_espectro_gamma — cruce de nombres fort.6 vs PHOTON.dat (Fase 2)")

    t12 = fa.leer_decay_dat(DECAY)
    all_data, errors = fa.analizar_carpeta(str(REF_SIM), t12)
    check(len(errors) == 0, f"análisis de ref_sim sin errores (errores={errors})")
    sim = next(iter(all_data.values()))
    libreria = fa.leer_photon_dat(PHOTON_EXTRACT)

    # Los 16 nucleidos del extracto (cadena Te->I->Xe) deben cruzar EXACTOS
    # contra las claves del inventario de enfriamiento del fort.6 de
    # referencia: misma convención ACAB (I131, I132M, TE131M...), sin
    # sufijos ni mayúsculas/minúsculas distintas.
    overlap = set(libreria.keys()) & set(sim["datos_cool"].keys())
    check(overlap == set(libreria.keys()),
          f"los 16 nucleidos del extracto cruzan exactos contra datos_cool de ref_sim "
          f"(sin cruzar: {set(libreria.keys()) - overlap})")


def test_calcular_espectro_gamma_ref_sim_linea_364() -> None:
    section("calcular_espectro_gamma — caso oro ref_sim, enfriamiento tardío (Fase 2)")

    t12 = fa.leer_decay_dat(DECAY)
    all_data, errors = fa.analizar_carpeta(str(REF_SIM), t12)
    sim = next(iter(all_data.values()))
    libreria = fa.leer_photon_dat(PHOTON_EXTRACT)

    # t=4.5h = último instante de enfriamiento de ref_sim: la muestra está
    # dominada casi en exclusiva por I131 (el resto de yodos radiactivos ya
    # se han desintegrado, ver pureza ~99.9999998% en tests/fixtures/README.md).
    # tasa(364 keV) = A(I131, 4.5h) * 0.812, verificado a mano una vez y
    # congelado (decisión de diseño de la Fase 2 del runbook B1).
    espectro = fa.calcular_espectro_gamma(sim, 4.5, libreria)
    check_close(espectro["t_h"], 4.5, "timestep real más cercano a t=4.5h es 4.5h")

    a_i131_4_5h = sim["datos_cool"]["I131"][-1]
    check_close(a_i131_4_5h, 16490.0, "A(I131, 4.5h) = 16490.0 Bq/cm³ (ya verificado en F1)")

    linea_364 = [l for l in espectro["lineas"]
                 if l["nucleido"] == "I131" and math.isclose(l["E_keV"], 364.49, rel_tol=1e-4)]
    check(len(linea_364) == 1, "exactamente una línea de 364,49 keV de I131 en el espectro de t=4.5h")
    assert len(linea_364) == 1
    check_close(linea_364[0]["tasa_fotones_s_cm3"], a_i131_4_5h * 0.812,
                "tasa(364 keV) = A(I131,4.5h) * 0,812 (a mano, congelado)", rtol=1e-9)


def test_calcular_espectro_gamma_nucleido_sin_lineas() -> None:
    section("calcular_espectro_gamma — nucleido sin líneas en la librería, no rompe (Fase 2)")

    t12 = fa.leer_decay_dat(DECAY)
    all_data, errors = fa.analizar_carpeta(str(REF_SIM), t12)
    sim = next(iter(all_data.values()))
    libreria = fa.leer_photon_dat(PHOTON_EXTRACT)

    # I130M está en el inventario de enfriamiento de ref_sim (actividad no
    # nula en t=0, ver tests/fixtures/README.md / diagnóstico de F2b) pero
    # NO en el extracto de PHOTON.dat: debe aparecer en la lista
    # informativa, sin romper el cálculo del resto del espectro (caso
    # obligatorio del runbook B1).
    espectro = fa.calcular_espectro_gamma(sim, 0.0, libreria)
    check("I130M" in sim["datos_cool"] and sim["datos_cool"]["I130M"][0] > 0,
          "I130M presente con actividad no nula en t=0 (precondición del caso)")
    check("I130M" in espectro["nucleidos_sin_lineas"],
          "I130M aparece en nucleidos_sin_lineas (informativo, no rompe)")
    check(len(espectro["lineas"]) > 0,
          f"el resto del espectro en t=0 se calcula con normalidad ({len(espectro['lineas'])} líneas)")


def test_calcular_espectro_gamma_sin_enfriamiento() -> None:
    section("calcular_espectro_gamma — casos borde")

    sim_sin_cool = {"t_cool": [], "datos_cool": {}}
    espectro = fa.calcular_espectro_gamma(sim_sin_cool, 1.0, {"I131": [[364.49, 81.2]]})
    check(espectro["t_h"] is None, "sin datos de enfriamiento -> t_h = None")
    check(espectro["lineas"] == [], "sin datos de enfriamiento -> lineas vacías")
    check(espectro["nucleidos_sin_lineas"] == [], "sin datos de enfriamiento -> nucleidos_sin_lineas vacío")

    # Actividad exactamente 0 no genera líneas (ni tampoco cuenta como
    # "sin líneas en la librería": simplemente no emite en ese instante).
    sim_actividad_cero = {"t_cool": [0.0, 1.0], "datos_cool": {"I131": [0.0, 100.0]}}
    espectro0 = fa.calcular_espectro_gamma(sim_actividad_cero, 0.0, {"I131": [[364.49, 81.2]]})
    check(espectro0["lineas"] == [] and espectro0["nucleidos_sin_lineas"] == [],
          "actividad 0 en t=0 -> ni líneas ni nucleidos_sin_lineas para ese isótopo")
    espectro1 = fa.calcular_espectro_gamma(sim_actividad_cero, 1.0, {"I131": [[364.49, 81.2]]})
    check_close(espectro1["lineas"][0]["tasa_fotones_s_cm3"], 100.0 * 0.812,
                "actividad 100 en t=1h -> línea calculada con normalidad", rtol=1e-9)


def main() -> int:
    print("Tests oro del espectro gamma desde PHOTON.dat (Fases 1 y 2 de B1)")

    test_leer_photon_dat_extracto()
    test_leer_photon_dat_nucleido_ausente()
    test_calcular_espectro_gamma_cruce_de_nombres()
    test_calcular_espectro_gamma_ref_sim_linea_364()
    test_calcular_espectro_gamma_nucleido_sin_lineas()
    test_calcular_espectro_gamma_sin_enfriamiento()

    print(f"\n{'-' * 50}")
    print(f"Resultado: {_PASSED} pasados, {_FAILED} fallidos")
    return 0 if _FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
