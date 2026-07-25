"""test_chains.py — Tests oro de F9 del BACKLOG (Fase 1 de
runbook_F9_analisis_cadenas.md, acab_suite/): parser del output de CHAINS,
lector de INITIAL CONCENTRATIONS y códec ZZAAAS inverso.

Script autocontenido, sin framework (estilo de la suite ACAB). Ejecuta
fort_analyzer.leer_output_chains contra el caso oro congelado
tests/fixtures/chains/output_chain_Te130_to_I131.txt (copia local, ver su
PROCEDENCIA.md), fort_analyzer.leer_concentraciones_iniciales contra
tests/fixtures/ref_sim/fort.6 (mismo inp.5 byte-idéntico al del caso
manual, ver PROCEDENCIA.md de ambos fixtures) y
fort_analyzer.nombre_a_zzaaas en ida y vuelta contra leer_decay_dat.

Uso:
    python tools/test_chains.py

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
OUTPUT_CHAIN = str(FIXTURES / "chains" / "output_chain_Te130_to_I131.txt")
DECAY = str(REF_SIM / "DECAY.dat")
FORT6 = str(REF_SIM / "fort.6")

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

def test_leer_output_chains_caso_oro() -> None:
    section("leer_output_chains — caso oro Te130→I131 (3 cadenas)")

    r = fa.leer_output_chains(OUTPUT_CHAIN)

    check(r["iflag"] == 2, f"IFLAG=2 (obtenido {r['iflag']})")
    check(r["inicial"] == 521300, f"INITIAL=521300 = Te130 (obtenido {r['inicial']})")
    check(r["ifinal"] == 531310, f"IFINAL=531310 = I131 (obtenido {r['ifinal']})")
    check(r["nmax"] == 14, f"NMAX=14 (obtenido {r['nmax']})")
    check_close(r["pcnt"], 0.01, "PCNT=0.01", rtol=1e-3)
    check(r["nchain"] == 5379, f"NCHAIN=5379 (obtenido {r['nchain']})")
    check(r["nch"] == 3, f"NCH=3 (obtenido {r['nch']})")
    check_close(r["ptot"], 100.0, "PTOT=100", rtol=1e-6)

    check(len(r["cadenas"]) == 3, f"3 cadenas parseadas (obtenido {len(r['cadenas'])})")

    c1, c2, c3 = r["cadenas"]
    check_close(c1["p"], 95.79, "P de la cadena 1 = 95.79 %", rtol=1e-4)
    check_close(c2["p"], 3.119, "P de la cadena 2 = 3.119 %", rtol=1e-4)
    check_close(c3["p"], 1.090, "P de la cadena 3 = 1.090 %", rtol=1e-4)

    # Cadena dominante: TE130(N,G-g)->TE131(B-)->I131, 2 pasos.
    check(len(c1["pasos"]) == 2, f"cadena 1 tiene 2 pasos (obtenido {len(c1['pasos'])})")
    p1a, p1b = c1["pasos"]
    check(p1a["desde"] == "TE130" and p1a["proceso"] == "N,G-g" and p1a["hasta"] == "TE131",
          f"paso 1 de la cadena 1: TE130 --(N,G-g)--> TE131 (obtenido {p1a})")
    check_close(p1a["xsec"], 1.1084e-11, "XSEC del paso 1 = 1.1084E-11", rtol=1e-6)
    check(p1a["delta"] is None, "paso 1 no tiene DELTA (es una captura)")
    check(p1b["desde"] == "TE131" and p1b["proceso"] == "B-" and p1b["hasta"] == "I131",
          f"paso 2 de la cadena 1: TE131 --(B-)--> I131 (obtenido {p1b})")
    check_close(p1b["delta"], 4.6210e-04, "DELTA del paso 2 = 4.6210E-04", rtol=1e-6)
    check(p1b["xsec"] is None, "paso 2 no tiene XSEC (es un decaimiento)")

    # Cadena 2: vía el isómero TE131M, 2 pasos.
    check(len(c2["pasos"]) == 2, f"cadena 2 tiene 2 pasos (obtenido {len(c2['pasos'])})")
    check(c2["pasos"][0]["hasta"] == "TE131M" and c2["pasos"][1]["desde"] == "TE131M",
          "cadena 2 pasa por TE131M (isómero)")

    # Cadena 3: TE130 -> TE131M -(IT)-> TE131 -(B-)-> I131, 3 pasos.
    check(len(c3["pasos"]) == 3, f"cadena 3 tiene 3 pasos (obtenido {len(c3['pasos'])})")
    check(c3["pasos"][1]["proceso"] == "IT" and c3["pasos"][1]["desde"] == "TE131M"
          and c3["pasos"][1]["hasta"] == "TE131",
          f"paso intermedio de la cadena 3 es la transición isomérica TE131M--(IT)-->TE131 (obtenido {c3['pasos'][1]})")

    # Σ P de las cadenas devueltas <= PTOT: la cola por debajo de PCNT queda
    # descartada (nota de normalización del runbook F9, no se corrige aquí).
    suma_p = sum(c["p"] for c in r["cadenas"])
    check(suma_p <= r["ptot"] + 1e-6,
          f"Σ P de las 3 cadenas ({suma_p:.4f}) <= PTOT ({r['ptot']})")


def test_leer_concentraciones_iniciales_ref_sim() -> None:
    section("leer_concentraciones_iniciales — inventario inicial de ref_sim (Te+O)")

    c = fa.leer_concentraciones_iniciales(FORT6)

    # 8 isótopos de Te con abundancia natural no nula + 3 de O, ver
    # PROCEDENCIA.md de tests/fixtures/chains (ACAB_inp_file_configurator)
    # para la verificación de unidades completa contra el Bloque #5.
    te_isos = {"TE120", "TE122", "TE123", "TE124", "TE125", "TE126", "TE128", "TE130"}
    o_isos = {"O16", "O17", "O18"}
    check(te_isos <= set(c.keys()), f"los 8 isótopos de Te están presentes (obtenido {sorted(k for k in c if k.startswith('TE'))})")
    check(o_isos <= set(c.keys()), f"los 3 isótopos de O están presentes (obtenido {sorted(k for k in c if k.startswith('O'))})")

    # Ningún producto de activación (p. ej. I131) tiene concentración inicial
    # no nula: el inventario inicial es solo el material del blanco.
    check("I131" not in c, "I131 (producto de activación) ausente del inventario inicial")

    suma_te = sum(c[iso] for iso in te_isos)
    # XCOMP(Te) del Bloque #5 = 4.6448E-04 át/barn·cm (INPT=1) = 4.6448E20
    # át/cm³ (verificación de unidades completa en Fase 0, ver
    # ACAB_inp_file_configurator/tests/fixtures/chains/PROCEDENCIA.md).
    check_close(suma_te, 4.6448e20, "Σ C_i(Te) reproduce XCOMP(Te)x1e24 dentro del redondeo del fort.6", rtol=1e-3)

    suma_o = sum(c[iso] for iso in o_isos)
    check_close(suma_o, 9.2896e20, "Σ C_i(O) reproduce XCOMP(O)x1e24 dentro del redondeo del fort.6", rtol=1e-3)


def test_nombre_a_zzaaas_casos_directos() -> None:
    section("nombre_a_zzaaas — casos directos (cruce con el caso oro de CHAINS)")

    check(fa.nombre_a_zzaaas("TE130") == 521300, "TE130 -> 521300 (INITIAL del caso oro)")
    check(fa.nombre_a_zzaaas("I131") == 531310, "I131 -> 531310 (IFINAL del caso oro)")
    check(fa.nombre_a_zzaaas("TE131M") == 521311, "TE131M -> 521311 (isómero, S=1)")
    check(fa.nombre_a_zzaaas("te131m") == 521311, "minúsculas -> mismo código (521311)")

    try:
        fa.nombre_a_zzaaas("XX999")
        _fail("elemento desconocido debería lanzar ValueError")
    except ValueError:
        _ok("elemento desconocido (XX999) lanza ValueError")

    try:
        fa.nombre_a_zzaaas("no es un isotopo")
        _fail("nombre mal formado debería lanzar ValueError")
    except ValueError:
        _ok("nombre mal formado lanza ValueError")


def test_nombre_a_zzaaas_ida_y_vuelta() -> None:
    section("nombre_a_zzaaas — ida y vuelta contra leer_decay_dat (identidad)")

    t12 = fa.leer_decay_dat(DECAY)
    check(len(t12) > 100, f"DECAY.dat de ref_sim tiene >100 nucleidos (obtenido {len(t12)})")

    fallos = []
    for acab_key in t12:
        try:
            code = fa.nombre_a_zzaaas(acab_key)
        except ValueError as exc:
            fallos.append((acab_key, str(exc)))
            continue
        # Decodificación inversa con la MISMA fórmula que leer_decay_dat
        # (Z = code // 10000, A = (code // 10) % 1000, S = code % 10).
        s = code % 10
        a = (code // 10) % 1000
        z = code // 10000
        elem = fa._Z_TO_ELEM.get(z)
        reconstruido = f"{elem}{a}" + ("M" if s == 1 else "")
        if reconstruido != acab_key:
            fallos.append((acab_key, f"reconstruido {reconstruido!r} != original"))

    check(not fallos, f"identidad ida y vuelta para los {len(t12)} nucleidos de DECAY.dat"
          f" (fallos: {fallos[:5]}{'...' if len(fallos) > 5 else ''})")


def main() -> int:
    print("Tests oro de F9 del BACKLOG (Fase 1: parsers + códec)")

    test_leer_output_chains_caso_oro()
    test_leer_concentraciones_iniciales_ref_sim()
    test_nombre_a_zzaaas_casos_directos()
    test_nombre_a_zzaaas_ida_y_vuelta()

    print(f"\n{'-' * 50}")
    print(f"Resultado: {_PASSED} pasados, {_FAILED} fallidos")
    return 0 if _FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
