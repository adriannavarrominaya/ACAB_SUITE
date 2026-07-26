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

import fort_analyzer as fa  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures"
REF_SIM = FIXTURES / "ref_sim"
OUTPUT_CHAIN = str(FIXTURES / "chains" / "output_chain_Te130_to_I131.txt")
OUTPUT_CHAIN_SIN_CADENAS = str(FIXTURES / "chains" / "output_chain_no_pathways_O16.txt")
OUTPUT_CHAIN_TE128 = str(FIXTURES / "chains" / "output_chain_TE128_to_I131.txt")
DECAY = str(REF_SIM / "DECAY.dat")
FORT6 = str(REF_SIM / "fort.6")
CHAINS_SYNTHETIC = FIXTURES / "chains_synthetic"

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


def test_leer_output_chains_sin_cadenas() -> None:
    section("leer_output_chains — caso real O16 sin cadenas (F9d del BACKLOG, "
            "sin camino físico O->I131 en <= NMAX pasos)")

    r = fa.leer_output_chains(OUTPUT_CHAIN_SIN_CADENAS)

    check(r["iflag"] == 2, f"IFLAG=2 (obtenido {r['iflag']})")
    check(r["inicial"] == 80160, f"INITIAL=80160 = O16 (obtenido {r['inicial']})")
    check(r["ifinal"] == 531310, f"IFINAL=531310 = I131 (obtenido {r['ifinal']})")
    check(r["nmax"] == 5, f"NMAX=5 (obtenido {r['nmax']})")
    check_close(r["pcnt"], 0.01, "PCNT=0.01", rtol=1e-3)
    check(r["nchain"] == 0, f"NCHAIN=0 (ausente del fichero, obtenido {r['nchain']})")
    check(r["nch"] == 0, f"NCH=0 (ausente del fichero, obtenido {r['nch']})")
    check_close(r["ptot"], 0.0, "PTOT=0.0 (ausente del fichero)", rtol=1e-9, atol=1e-9)
    check(r["cadenas"] == [], f"cadenas=[] (obtenido {r['cadenas']})")


def test_leer_output_chains_te128_hermano_de_c6() -> None:
    section("leer_output_chains — caso oro real TE128→I131 (F9e del BACKLOG: "
            "origen con espacio inicial de columna, hermano de C6)")

    r = fa.leer_output_chains(OUTPUT_CHAIN_TE128)

    check(r["iflag"] == 2, f"IFLAG=2 (obtenido {r['iflag']})")
    check(r["inicial"] == 521280, f"INITIAL=521280 = TE128 (obtenido {r['inicial']})")
    check(r["ifinal"] == 531310, f"IFINAL=531310 = I131 (obtenido {r['ifinal']})")
    check(r["nmax"] == 5, f"NMAX=5 (obtenido {r['nmax']})")
    check_close(r["pcnt"], 0.01, "PCNT=0.01", rtol=1e-3)
    check(r["nchain"] == 13, f"NCHAIN=13 (obtenido {r['nchain']})")
    check(r["nch"] == 12, f"NCH=12 (obtenido {r['nch']})")
    # OJO: aquí PTOT NO es 100 -- es la probabilidad TOTAL de alcanzar
    # IFINAL (2,3 %), muy distinta del caso TE130->I131 de arriba donde
    # PTOT=100 es una renormalización entre las cadenas supervivientes de
    # PCNT. Ambos son "PTOT" de leer_output_chains, pero de semántica
    # numérica distinta según lo que haga CHAINS -- no asumir PTOT=100 en
    # ningún sitio de la UI (ver Tabla 2 en app.py/static/js).
    check_close(r["ptot"], 0.02304, "PTOT=0.02304 (NO 100 -- ver nota arriba)", rtol=1e-3)

    check(len(r["cadenas"]) == 12, f"12 cadenas parseadas (obtenido {len(r['cadenas'])})")

    # Antes del fix (F9e), las líneas de paso cuyo ORIGEN es un elemento de
    # símbolo de una letra (yodo, "I") llevan un espacio inicial de relleno
    # de columna (" I129 (N,G-g)      I130") que _CHAIN_STEP_RE no
    # toleraba -- la cadena se truncaba silenciosamente antes de I131. Las
    # 12 cadenas detalladas del fichero real DEBEN llegar todas a I131.
    for i, c in enumerate(r["cadenas"], start=1):
        check(c["pasos"][-1]["hasta"] == "I131",
              f"cadena {i} termina en I131 (obtenido {c['pasos'][-1]['hasta']!r})")

    # Cadena 2 (P=18.61 %): 4 pasos -- antes del fix se truncaba en 2
    # (TE128->TE129->I129) por la línea " I129 (N,G-g)  I130" sin parsear.
    c2 = r["cadenas"][1]
    check_close(c2["p"], 18.61, "P de la cadena 2 = 18.61 %", rtol=1e-4)
    check(len(c2["pasos"]) == 4, f"cadena 2 tiene 4 pasos (obtenido {len(c2['pasos'])})")
    check(c2["pasos"][2]["desde"] == "I129" and c2["pasos"][2]["hasta"] == "I130",
          f"paso 3 de la cadena 2 (origen con espacio inicial): I129 -> I130 (obtenido {c2['pasos'][2]})")
    check(c2["pasos"][3]["desde"] == "I130" and c2["pasos"][3]["hasta"] == "I131",
          f"paso 4 de la cadena 2 (origen con espacio inicial): I130 -> I131 (obtenido {c2['pasos'][3]})")

    # Cadena 3 (P=8.747 %): 5 pasos, vía el isómero I130M; su cabecera de
    # ruta compacta (redundante, no se parsea) ocupa DOS líneas de texto
    # -- confirma que el header multi-línea no rompe el parseo de pasos.
    c3 = r["cadenas"][2]
    check_close(c3["p"], 8.747, "P de la cadena 3 = 8.747 %", rtol=1e-4)
    check(len(c3["pasos"]) == 5, f"cadena 3 tiene 5 pasos pese al header multi-línea (obtenido {len(c3['pasos'])})")
    check(c3["pasos"][2]["desde"] == "I129" and c3["pasos"][2]["proceso"] == "N,G-m"
          and c3["pasos"][2]["hasta"] == "I130M",
          f"paso 3 de la cadena 3: I129 --(N,G-m)--> I130M (obtenido {c3['pasos'][2]})")
    check(c3["pasos"][3]["desde"] == "I130M" and c3["pasos"][3]["proceso"] == "IT"
          and c3["pasos"][3]["hasta"] == "I130",
          f"paso 4 de la cadena 3: I130M --(IT)--> I130 (obtenido {c3['pasos'][3]})")
    check(c3["pasos"][4]["desde"] == "I130" and c3["pasos"][4]["hasta"] == "I131",
          f"paso 5 de la cadena 3: I130 -> I131 (obtenido {c3['pasos'][4]})")


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


def test_calcular_analisis_cadenas_sintetico() -> None:
    section("calcular_analisis_cadenas — caso sintético mínimo (2 isótopos, "
            "R/Σ/X/Y verificados a mano, ver PROCEDENCIA.md)")

    r = fa.calcular_analisis_cadenas(str(CHAINS_SYNTHETIC), t_h=None)

    check(r["ifinal"] == "CO57", f"IFINAL=CO57 (obtenido {r['ifinal']})")
    check_close(r["t_star_h"], 1.0, "t* por defecto = t_pico de la referencia = 1 h")
    check(r["t_star_fuente"] == "pico_referencia",
          f"t_star_fuente='pico_referencia' (obtenido {r['t_star_fuente']!r})")
    check_close(r["a_ref"], 100.0, "A_ref(t*) = 100 Bq/cm3")

    # ── Tabla 1: R_i por isótopo + Σ R_i ≈ 1 (cobertura completa) ──────────
    tabla1 = {f["isotopo"]: f for f in r["tabla1"]}
    check(set(tabla1.keys()) == {"FE56", "MN55"},
          f"tabla1 tiene los 2 isótopos (obtenido {sorted(tabla1.keys())})")
    check_close(tabla1["FE56"]["a_i"], 42.0, "A(FE56,t*) = 42 Bq/cm3")
    check_close(tabla1["MN55"]["a_i"], 58.0, "A(MN55,t*) = 58 Bq/cm3")
    check_close(tabla1["FE56"]["r_i"], 0.42, "R_FE56 = 42/100 = 0.42")
    check_close(tabla1["MN55"]["r_i"], 0.58, "R_MN55 = 58/100 = 0.58")
    check_close(r["suma_r_i"], 1.00, "Σ R_i = 1.00 (superposición lineal exacta del fixture)")
    check(r["cobertura"]["completa"], "cobertura completa: los 2 isótopos del inventario inicial están seleccionados")
    check(r["cobertura"]["n_seleccionados"] == 2 and r["cobertura"]["n_total_inventario"] == 2,
          f"cobertura n_seleccionados=n_total_inventario=2 (obtenido {r['cobertura']})")

    # ── Tabla 2: X_z_i, Y_z_i, orden por Y_z_i descendente ─────────────────
    check(len(r["tabla2"]) == 3, f"tabla2 tiene 3 filas (2 cadenas de FE56 + 1 de MN55, obtenido {len(r['tabla2'])})")
    fila_mn, fila_fe1, fila_fe2 = r["tabla2"]

    check(fila_mn["isotopo"] == "MN55" and fila_fe1["isotopo"] == "FE56" and fila_fe2["isotopo"] == "FE56",
          "orden esperado: MN55 (Y=0.580) -> FE56 (Y=0.336) -> FE56 (Y=0.084)")
    check_close(fila_mn["x_z_i"], 1.00, "X_z_i(MN55, única cadena) = 1.00 (P=100%)")
    check_close(fila_mn["y_z_i"], 0.580, "Y_z_i(MN55) = 0.58 * 1.00 = 0.580")
    check_close(fila_fe1["x_z_i"], 0.80, "X_z_i(FE56, cadena 1) = 0.80 (P=80%)")
    check_close(fila_fe1["y_z_i"], 0.336, "Y_z_i(FE56, cadena 1) = 0.42 * 0.80 = 0.336")
    check_close(fila_fe2["x_z_i"], 0.20, "X_z_i(FE56, cadena 2) = 0.20 (P=20%)")
    check_close(fila_fe2["y_z_i"], 0.084, "Y_z_i(FE56, cadena 2) = 0.42 * 0.20 = 0.084")
    check(fila_fe1["nmax"] == 5 and abs(fila_fe1["pcnt"] - 0.01) < 1e-6,
          f"NMAX/PCNT viajan junto a la fila (obtenido NMAX={fila_fe1['nmax']}, PCNT={fila_fe1['pcnt']})")
    # F9e: cadena_label incluye el proceso de cada paso (no solo nombres),
    # distingue cadenas que compartan secuencia de nucleidos pero difieran
    # en el proceso de algún paso.
    check(fila_fe1["cadena_label"] == "FE56->(N,G-g)->FE57->(B-)->CO57",
          f"cadena_label de la cadena 1 de FE56 incluye el proceso de cada paso (obtenido {fila_fe1['cadena_label']!r})")
    check(fila_fe2["cadena_label"] == "FE56->(N,G-m)->FE57M->(IT)->FE57->(B-)->CO57",
          f"cadena_label de la cadena 2 de FE56 (vía el isómero FE57M) incluye el proceso de cada paso (obtenido {fila_fe2['cadena_label']!r})")

    suma_y = sum(f["y_z_i"] for f in r["tabla2"])
    check_close(suma_y, r["suma_r_i"], "Σ Y_z_i = Σ R_i (sin cola PCNT descartada en este fixture: NCH cubre el 100% de PTOT)")

    # ── Selector de instante manual (t_h explícito, no el t_pico) ──────────
    r0 = fa.calcular_analisis_cadenas(str(CHAINS_SYNTHETIC), t_h=0.0)
    check(r0["t_star_fuente"] == "manual", "t_star_fuente='manual' cuando se pasa t_h explícito")
    check_close(r0["a_ref"], 40.0, "A_ref(t=0) = 40 Bq/cm3 (instante manual, no el pico)")
    tabla1_t0 = {f["isotopo"]: f for f in r0["tabla1"]}
    check_close(tabla1_t0["FE56"]["r_i"], 15.0 / 40.0, "R_FE56(t=0) = 15/40")


def test_calcular_analisis_cadenas_output_chain_corrupto() -> None:
    section("calcular_analisis_cadenas — output_chain.txt corrupto/ausente no rompe "
            "el informe (F9d del BACKLOG: degradación por isótopo)")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp) / "chains_analysis"
        shutil.copytree(CHAINS_SYNTHETIC, tmp_root)

        # FE56: output_chain.txt corrupto (forma inesperada, sin IFLAG/INITIAL/...).
        (tmp_root / "chains_FE56" / "output_chain.txt").write_text(
            "ESTO NO ES UN OUTPUT DE CHAINS VALIDO\n", encoding="utf-8")
        # MN55: output_chain.txt AUSENTE.
        (tmp_root / "chains_MN55" / "output_chain.txt").unlink()

        r = fa.calcular_analisis_cadenas(str(tmp_root), t_h=None)

    tabla1 = {f["isotopo"]: f for f in r["tabla1"]}
    check(set(tabla1.keys()) == {"FE56", "MN55"},
          f"tabla1 conserva los 2 isótopos pese al output_chain roto/ausente (obtenido {sorted(tabla1.keys())})")
    check_close(tabla1["FE56"]["r_i"], 0.42, "R_FE56 intacto pese al output_chain.txt corrupto")
    check_close(tabla1["MN55"]["r_i"], 0.58, "R_MN55 intacto pese al output_chain.txt ausente")
    check(tabla1["FE56"]["nota_cadenas"] == fa.NOTA_CHAINS_ILEGIBLE,
          f"FE56 anotado como CHAINS ilegible (obtenido {tabla1['FE56']['nota_cadenas']!r})")
    check(tabla1["MN55"]["nota_cadenas"] == fa.NOTA_CHAINS_ILEGIBLE,
          f"MN55 anotado como CHAINS ilegible/ausente (obtenido {tabla1['MN55']['nota_cadenas']!r})")
    check_close(r["suma_r_i"], 1.00, "Σ R_i sigue siendo 1.00: el fallo de CHAINS no afecta a R_i")
    check(r["tabla2"] == [],
          f"tabla2 vacía: ninguno de los 2 isótopos aporta cadenas legibles (obtenido {len(r['tabla2'])} filas)")


def test_calcular_analisis_cadenas_sin_cadenas_no_es_error() -> None:
    section("calcular_analisis_cadenas — output_chain.txt legible SIN cadenas "
            "(caso real O16/O17/O18) no es un error (F9d del BACKLOG)")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp) / "chains_analysis"
        shutil.copytree(CHAINS_SYNTHETIC, tmp_root)
        shutil.copyfile(OUTPUT_CHAIN_SIN_CADENAS,
                         tmp_root / "chains_FE56" / "output_chain.txt")

        r = fa.calcular_analisis_cadenas(str(tmp_root), t_h=None)

    tabla1 = {f["isotopo"]: f for f in r["tabla1"]}
    check(tabla1["FE56"]["nota_cadenas"] is None,
          "FE56 sin nota: el output_chain.txt es legible, solo no tiene cadenas por debajo de NMAX")
    check_close(tabla1["FE56"]["r_i"], 0.42, "R_FE56 se muestra igual que siempre (viene del fort.6, no del output_chain.txt)")
    filas_fe56 = [f for f in r["tabla2"] if f["isotopo"] == "FE56"]
    check(filas_fe56 == [], f"tabla2 sin filas de FE56: sin cadenas, sin contribución (obtenido {len(filas_fe56)})")
    filas_mn55 = [f for f in r["tabla2"] if f["isotopo"] == "MN55"]
    check(len(filas_mn55) == 1, f"tabla2 conserva la cadena de MN55, no afectada (obtenido {len(filas_mn55)})")


def test_construir_diagrama_cadena_caso_real() -> None:
    section("construir_diagrama_cadena — cadena dominante Te130->Te131->I131 "
            "(caso oro real, T½ de DECAY.dat)")

    r = fa.leer_output_chains(OUTPUT_CHAIN)
    t12 = fa.leer_decay_dat(DECAY)
    c1, c2, c3 = r["cadenas"]

    d1 = fa.construir_diagrama_cadena(c1, t12)
    check([n["nombre"] for n in d1["nodos"]] == ["TE130", "TE131", "I131"],
          f"nodos de la cadena dominante: TE130 -> TE131 -> I131 (obtenido {[n['nombre'] for n in d1['nodos']]})")
    check_close(d1["nodos"][0]["t12_s"], 2.493e31, "T½(TE130) = 2.493E31 s (DECAY.dat)")
    check_close(d1["nodos"][1]["t12_s"], 1500.0, "T½(TE131) = 1500 s = 25 min (DECAY.dat)")
    check_close(d1["nodos"][2]["t12_s"], 6.932e5, "T½(I131) = 6.932E5 s (DECAY.dat)")
    check(all(n["conocido"] and not n["estable"] for n in d1["nodos"]),
          "los 3 nucleidos están en DECAY.dat y ninguno es estable (T½ finita)")

    check(len(d1["aristas"]) == 2, f"2 aristas (obtenido {len(d1['aristas'])})")
    a1, a2 = d1["aristas"]
    check(a1["desde"] == "TE130" and a1["proceso"] == "N,G-g" and a1["hasta"] == "TE131",
          f"arista 1: TE130 --(N,G-g)--> TE131 (obtenido {a1})")
    check_close(a1["xsec"], 1.1084e-11, "XSEC de la arista 1 = 1.1084E-11")
    check(a1["delta"] is None, "arista 1 (captura) no tiene DELTA")
    check(a2["desde"] == "TE131" and a2["proceso"] == "B-" and a2["hasta"] == "I131",
          f"arista 2: TE131 --(B-)--> I131 (obtenido {a2})")
    check_close(a2["delta"], 4.6210e-04, "DELTA de la arista 2 = 4.6210E-04")
    check(a2["xsec"] is None, "arista 2 (decaimiento) no tiene XSEC")

    # Cadena 2: pasa por el isómero TE131M -- T½ distinto del fundamental.
    d2 = fa.construir_diagrama_cadena(c2, t12)
    check([n["nombre"] for n in d2["nodos"]] == ["TE130", "TE131M", "I131"],
          f"cadena 2 pasa por TE131M (obtenido {[n['nombre'] for n in d2['nodos']]})")
    check_close(d2["nodos"][1]["t12_s"], 1.08e5, "T½(TE131M) = 1.08E5 s (isómero, distinto de TE131)")

    # Nucleido ausente de la librería (t12_dict vacío): no rompe, marca "no conocido".
    d_vacio = fa.construir_diagrama_cadena(c1, {})
    check(all(not n["conocido"] and n["t12_s"] is None for n in d_vacio["nodos"]),
          "sin librería T½, los 3 nodos quedan como 'no conocido' sin romper")


def main() -> int:
    print("Tests oro de F9 del BACKLOG (Fase 1: parsers + códec; Fase 4: tablas; Fase 5: diagrama)")

    test_leer_output_chains_caso_oro()
    test_leer_output_chains_te128_hermano_de_c6()
    test_leer_output_chains_sin_cadenas()
    test_leer_concentraciones_iniciales_ref_sim()
    test_nombre_a_zzaaas_casos_directos()
    test_nombre_a_zzaaas_ida_y_vuelta()
    test_calcular_analisis_cadenas_sintetico()
    test_calcular_analisis_cadenas_output_chain_corrupto()
    test_calcular_analisis_cadenas_sin_cadenas_no_es_error()
    test_construir_diagrama_cadena_caso_real()

    print(f"\n{'-' * 50}")
    print(f"Resultado: {_PASSED} pasados, {_FAILED} fallidos")
    return 0 if _FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
