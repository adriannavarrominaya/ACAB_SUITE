"""test_photon.py — Tests oro del parser de PHOTON.dat (Fase 1 de
runbook_B1_espectro_gamma.md).

Script autocontenido, sin framework (estilo de la suite ACAB). Ejecuta
fort_analyzer.leer_photon_dat contra el extracto congelado
tests/fixtures/ref_sim/PHOTON_extract.dat (16 nucleidos de la cadena
Te->I->Xe, formato original CRLF byte a byte, NO regenerado).

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


def main() -> int:
    print("Tests oro del parser de PHOTON.dat (Fase 1 de B1)")

    test_leer_photon_dat_extracto()
    test_leer_photon_dat_nucleido_ausente()

    print(f"\n{'-' * 50}")
    print(f"Resultado: {_PASSED} pasados, {_FAILED} fallidos")
    return 0 if _FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
