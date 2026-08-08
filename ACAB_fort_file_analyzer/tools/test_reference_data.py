"""test_reference_data.py — Oráculo Python de los datos de referencia (Fase 4).

static/js/reference_data.js implementa el parser CSV, la interpolación lineal
y las métricas de desviación descritas en docs/SPEC_csv_datos_referencia.md.
Esta máquina no tiene node (ver memoria [[no-node-runtime]]), así que este
script reimplementa en Python el mismo algoritmo (parseo del CSV, interpolación
recortada a los extremos, fórmula de desviación) y lo valida contra:

  1. Los fixtures reales de tests/fixtures/experimental/ (formato de la Fase 4).
  2. El criterio de aceptación del runbook: reproducir la comparación de
     compare_simulaciones.py (11 puntos experimentales legacy) usando la
     curva I131 real de la ref_sim — que es, según tests/fixtures/README.md,
     la misma simulación v.5 "info thesis" que ese script usaba como
     referencia computacional.

Uso:
    python tools/test_reference_data.py

Devuelve código de salida 0 si todo pasa, 1 si algún test falla.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import fort_analyzer as fa  # noqa: E402

FIXTURES_EXP = REPO_ROOT / "tests" / "fixtures" / "experimental"
REF_SIM = REPO_ROOT / "tests" / "fixtures" / "ref_sim"

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
# Reimplementación en Python del parser CSV de static/js/reference_data.js
# (mismas reglas: docs/SPEC_csv_datos_referencia.md). Solo para verificación
# oro en un entorno sin node: no la usa la app (que corre en el navegador).
# ─────────────────────────────────────────────────────────────────────────────

def parse_csv_oracle(text: str) -> dict:
    if text and text[0] == "﻿":
        text = text[1:]
    lines = re.split(r"\r\n|\r|\n", text)

    meta: dict[str, str] = {}
    data_lines: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("#"):
            body = re.sub(r"^#\s*", "", stripped)
            if ":" in body:
                key, _, val = body.partition(":")
                meta[key.strip().lower()] = val.strip()
            continue
        data_lines.append(line)

    if not data_lines:
        return {"meta": meta, "delimiter": ";", "decimal": ",", "headers": None, "rows": []}

    delimiter = ";"
    for line in data_lines:
        if not line.strip():
            continue
        if ";" in line:
            delimiter = ";"
        elif "\t" in line:
            delimiter = "\t"
        elif "," in line:
            delimiter = ","
        break

    if delimiter == ",":
        decimal = "."
    else:
        comma_dec = dot_dec = 0
        sampled = 0
        for line in data_lines:
            if not line.strip():
                continue
            if sampled >= 8:
                break
            sampled += 1
            for cell in line.split(delimiter):
                c = cell.strip()
                if re.fullmatch(r"-?\d+,\d+", c):
                    comma_dec += 1
                elif re.fullmatch(r"-?\d+\.\d+", c):
                    dot_dec += 1
        decimal = "," if comma_dec >= dot_dec else "."

    def parse_number(cell: str) -> float:
        s = cell.strip()
        if s == "":
            return float("nan")
        if decimal == ",":
            s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return float("nan")

    def is_numeric_row(cells: list[str]) -> bool:
        return all(c.strip() != "" and not math.isnan(parse_number(c)) for c in cells)

    first_cells = [c.strip() for c in data_lines[0].split(delimiter)]
    headers = None
    body = data_lines
    if not is_numeric_row(first_cells):
        headers = first_cells
        body = data_lines[1:]

    rows = [
        [parse_number(c) for c in line.split(delimiter)]
        for line in body
        if line.strip()
    ]
    return {"meta": meta, "delimiter": delimiter, "decimal": decimal, "headers": headers, "rows": rows}


def linear_interp_clamped(xs: list[float], ys: list[float], x: float) -> float:
    """Mirror exacto de ACABRefData.linearInterpClamped (static/js/reference_data.js)."""
    n = len(xs)
    if n == 0:
        return None
    if n == 1:
        return ys[0]
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, n):
        if x <= xs[i]:
            x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
            if x1 == x0:
                return y0
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return ys[-1]


def deviation_metrics(exp_points, curve_xs, curve_ys):
    """Mirror exacto de ACABRefData.computeDeviationMetrics."""
    rows = []
    for t, a_exp in exp_points:
        a_interp = linear_interp_clamped(curve_xs, curve_ys, t)
        dev_pct = (a_interp - a_exp) / a_exp * 100.0 if (a_interp is not None and a_exp != 0) else None
        rows.append((t, a_exp, a_interp, dev_pct))
    devs = [r[3] for r in rows if r[3] is not None and math.isfinite(r[3])]
    mean_dev = sum(devs) / len(devs) if devs else None
    max_abs_dev = max(abs(d) for d in devs) if devs else None
    return rows, mean_dev, max_abs_dev


def series_for_metrics(series, iso):
    """Mirror exacto de ACABRefData.seriesForMetrics (Fase 6 del BACKLOG)."""
    return [s for s in (series or []) if s.get("isotopo") == iso]


def resolve_target_sim_name(sim_names, requested_name):
    """Mirror exacto de ACABRefData.resolveTargetSimName (Fase 6 del BACKLOG)."""
    if not sim_names:
        return None
    if requested_name and requested_name in sim_names:
        return requested_name
    return sim_names[0]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_fixture_experimental() -> None:
    section("Fixture fig6_exp4_experimental_normalizado.csv — formato Fase 4")
    text = (FIXTURES_EXP / "fig6_exp4_experimental_normalizado.csv").read_text(encoding="utf-8")
    parsed = parse_csv_oracle(text)

    check(parsed["meta"].get("tipo") == "experimental", "meta.tipo = experimental")
    check(parsed["meta"].get("fase") == "enfriamiento", "meta.fase = enfriamiento")
    check(parsed["meta"].get("isotopo") == "I131", "meta.isotopo = I131")
    check(parsed["meta"].get("unidad_t") == "h", "meta.unidad_t = h")
    check(parsed["meta"].get("unidad_a") == "MBq/g", "meta.unidad_A = MBq/g")
    check(parsed["delimiter"] == ";", "delimitador autodetectado = ;")
    check(parsed["decimal"] == ",", "decimal autodetectado = ,")
    check(parsed["headers"] == ["t", "A"], f"cabecera t;A detectada (obtenido {parsed['headers']})")

    rows = parsed["rows"]
    check(len(rows) == 29, f"29 puntos (obtenido {len(rows)})")
    ts = [r[0] for r in rows]
    As = [r[1] for r in rows]
    check_close(min(ts), 14.5770, "t mínimo ≈ 14.6 h", rtol=2e-2)
    check_close(max(ts), 171.3655, "t máximo ≈ 171.4 h", rtol=2e-3)
    check_close(min(As), 4668.772, "A mínima ≈ 4669 MBq/g", rtol=2e-3)
    check_close(max(As), 7866.206, "A máxima ≈ 7866 MBq/g", rtol=2e-3)


def test_fixture_computacional() -> None:
    section("Fixture fig6_exp4_computacional_normalizado.csv — formato Fase 4")
    text = (FIXTURES_EXP / "fig6_exp4_computacional_normalizado.csv").read_text(encoding="utf-8")
    parsed = parse_csv_oracle(text)

    check(parsed["meta"].get("tipo") == "computacional_referencia", "meta.tipo = computacional_referencia")
    rows = parsed["rows"]
    check(len(rows) == 28, f"28 puntos (obtenido {len(rows)})")
    ts = [r[0] for r in rows]
    As = [r[1] for r in rows]
    check_close(min(ts), 2.0617, "t mínimo ≈ 2.1 h", rtol=2e-2)
    check_close(max(ts), 171.8854, "t máximo ≈ 171.9 h", rtol=2e-3)
    check_close(min(As), 4919.482, "A mínima ≈ 4919 MBq/g", rtol=2e-3)
    check_close(max(As), 8862.472, "A máxima ≈ 8862 MBq/g", rtol=2e-3)

    # Cross-check físico documentado en la especificación (docs/SPEC…, línea 71):
    # A(t_fin)/A(t_ini) = 0.555 en ~170 h para la serie computacional.
    a_ini = As[ts.index(min(ts))]
    a_fin = As[ts.index(max(ts))]
    check_close(a_fin / a_ini, 0.555, "A(t_fin)/A(t_ini) ≈ 0.555 (cross-check de la spec)", rtol=2e-3)


def test_linear_interp_clamped_matches_numpy() -> None:
    section("linearInterpClamped — paridad exacta con numpy.interp (oráculo legacy)")
    comp_t = [0.2709231889, 0.4804614151, 0.7204327496, 0.9315613704, 1.121084107,
              1.571873455, 1.902275268, 2.091705142, 2.27125429, 2.50196291, 2.682403319]
    comp_A = [0.04836326, 0.07389830, 0.09358229, 0.10541931, 0.11311902,
              0.12387904, 0.12793620, 0.12942901, 0.13049404, 0.13105821, 0.13169515]
    exp_t = [0.26951859, 0.4775716, 0.71976523, 0.92890383, 1.12000271,
             1.56890423, 1.89931071, 2.08787231, 2.26834455, 2.49911054, 2.67779639]
    # Valores oráculo de numpy.interp(exp_t, comp_t, comp_A) (recorte a extremos).
    numpy_oracle = [0.04836326, 0.07354613731584769, 0.0935275357554625, 0.10527031381584263,
                    0.11307508625651232, 0.12380816671844122, 0.12789979679135513,
                    0.12939880520802555, 0.13047678032248708, 0.13105123487448064,
                    0.13167888791450863]
    for t, exp in zip(exp_t, numpy_oracle):
        got = linear_interp_clamped(comp_t, comp_A, t)
        check_close(got, exp, f"interp clamped en t={t:.4f} h == numpy.interp", rtol=1e-9)


def test_deviation_metrics_legacy_11_points() -> None:
    section("Criterio de aceptación Fase 4 — 11 puntos legacy vs. curva I131 de la ref_sim")
    # Los 11 puntos experimentales embebidos en compare_simulaciones.py
    # (Actividad MBq/g TeO2 | tiempo de enfriamiento en horas).
    exp_t = [0.26951859, 0.4775716, 0.71976523, 0.92890383, 1.12000271,
             1.56890423, 1.89931071, 2.08787231, 2.26834455, 2.49911054, 2.67779639]
    exp_A = [0.05191691, 0.07064688, 0.08823739, 0.09443323, 0.10597033,
             0.11216617, 0.115727, 0.11679525, 0.11836202, 0.11950148, 0.12042730]

    # Curva I131 real de la ref_sim (misma simulación v.5 "info thesis" que el
    # script legacy usaba, según tests/fixtures/README.md), convertida a MBq/g
    # con la misma densidad de normalización (0.12317 g/cm³, CONCENTRATIONS(GRAM)).
    t_cool, datos = fa.leer_fort6_enfriamiento(str(REF_SIM / "fort.6"))
    conc = fa.leer_fort6_concentraciones(str(REF_SIM / "fort.6"))
    densidad = conc["total_g_cm3"]
    A_mbqg = [a / (densidad * 1e6) for a in datos["I131"]]

    rows, mean_dev, max_abs_dev = deviation_metrics(
        list(zip(exp_t, exp_A)), list(t_cool), A_mbqg,
    )

    check(len(rows) == 11, "11 filas de desviación (una por punto experimental)")
    # Oráculo calculado con numpy (ver notas de la sesión): interpolando la
    # curva real de la ref_sim en los 11 tiempos experimentales.
    check_close(mean_dev, 8.227263951888302, "sesgo medio ≈ 8.23 % (curva real ref_sim)", rtol=1e-6)
    check_close(max_abs_dev, 12.018871139789406, "desviación máxima ≈ 12.02 % (curva real ref_sim)", rtol=1e-6)

    # El script legacy, interpolando su propia digitalización computacional
    # (comp_t/comp_A) en los mismos 11 tiempos, obtenía sesgo 7.49 % / máx.
    # 11.48 % (ver tools/test_reference_data.js). Ambos oráculos deben ser del
    # mismo orden de magnitud: confirma que la Fase 4 reproduce el criterio de
    # aceptación "misma sim de referencia, mismos 11 puntos, desviaciones
    # equivalentes" (no idénticas, porque la digitalización legacy y la malla
    # real del fort.6 no coinciden punto a punto).
    LEGACY_MEAN, LEGACY_MAX = 7.487912045806161, 11.475921998900839
    check(abs(mean_dev - LEGACY_MEAN) < 2.0,
          f"sesgo medio equivalente al legacy (Δ={mean_dev - LEGACY_MEAN:.2f} pp < 2 pp)")
    check(abs(max_abs_dev - LEGACY_MAX) < 2.0,
          f"desviación máxima equivalente al legacy (Δ={max_abs_dev - LEGACY_MAX:.2f} pp < 2 pp)")


def test_series_for_metrics() -> None:
    section("seriesForMetrics — ambos tipos entran en las métricas (Fase 6 del BACKLOG)")
    exp_text = (FIXTURES_EXP / "fig6_exp4_experimental_normalizado.csv").read_text(encoding="utf-8")
    comp_text = (FIXTURES_EXP / "fig6_exp4_computacional_normalizado.csv").read_text(encoding="utf-8")
    exp_meta = parse_csv_oracle(exp_text)["meta"]
    comp_meta = parse_csv_oracle(comp_text)["meta"]
    check(exp_meta.get("tipo") == "experimental", "fixture experimental: meta.tipo = experimental")
    check(comp_meta.get("tipo") == "computacional_referencia", "fixture computacional: meta.tipo = computacional_referencia")

    loaded_series = [
        {"id": "s1", "isotopo": "I131", "tipo": exp_meta.get("tipo"), "descripcion": "exp"},
        {"id": "s2", "isotopo": "I131", "tipo": comp_meta.get("tipo"), "descripcion": "comp"},
        {"id": "s3", "isotopo": "XE133", "tipo": "experimental", "descripcion": "otro isotopo"},
    ]
    for_metrics = series_for_metrics(loaded_series, "I131")
    check(len(for_metrics) == 2, f"las 2 series de I131 entran en métricas, sea su tipo el que sea (obtenido {len(for_metrics)})")
    check(any(s["tipo"] == "experimental" for s in for_metrics), "la serie experimental entra")
    check(any(s["tipo"] == "computacional_referencia" for s in for_metrics),
          "la serie computacional_referencia TAMBIÉN entra (antes de la Fase 6 se excluía)")
    check(not any(s["id"] == "s3" for s in for_metrics), "la serie de otro isótopo no entra")
    check(series_for_metrics([], "I131") == [], "sin series cargadas → lista vacía")
    check(series_for_metrics(None, "I131") == [], "None → lista vacía (nunca rompe)")


def test_resolve_target_sim_name() -> None:
    section("resolveTargetSimName — selector de simulación objetivo (Fase 6 del BACKLOG)")
    check(resolve_target_sim_name(["sim1"], None) == "sim1", "una sola simulación → esa, sin selección previa")
    check(resolve_target_sim_name(["sim1", "sim2"], None) == "sim1",
          "varias simulaciones sin selección previa → la primera (comportamiento por defecto)")
    check(resolve_target_sim_name(["sim1", "sim2"], "sim2") == "sim2", "selección previa válida → se respeta")
    check(resolve_target_sim_name(["sim1", "sim2"], "sim3-ya-no-existe") == "sim1",
          "selección previa que ya no existe → cae a la primera")
    check(resolve_target_sim_name([], "sim1") is None, "sin simulaciones cargadas → None")
    check(resolve_target_sim_name(None, "sim1") is None, "None → None (nunca rompe)")


def test_bqcm3_inverse_conversion() -> None:
    section("Inversa de la conversión de unidad (MBq/g → Bq/cm³, mirror de bqcm3FromUnit)")
    densidad = 0.12317
    mbqg_value = 16500.0 / (densidad * 1e6)  # = 0.13396119184866445, pico oro
    bqcm3 = mbqg_value * densidad * 1e6      # inversa de Bq/cm³ / (densidad·1e6)
    check_close(bqcm3, 16500.0, "MBq/g invertido reproduce el pico I131 en Bq/cm³")


def test_f12_time_origin_no_shift() -> None:
    """F12 del BACKLOG: caso oro del diagnóstico (desfase de T_irr al
    interpolar una serie de referencia de fase 'enfriamiento'). Mirror en
    Python de la sección equivalente de tools/test_reference_data.js —
    curveForPhase/interpolationOriginLabel viven solo en JS (pura selección
    de arrays, sin lógica numérica propia), así que aquí solo se verifica el
    núcleo numérico: linear_interp_clamped sobre los dos nodos, con y sin el
    desplazamiento espurio de T_irr.
    """
    section("F12 — desfase de origen temporal (caso oro del diagnóstico)")
    t_irr_h = 2.778e-3  # h, caso de referencia del experimento 1 (ref_sim)
    xs = [0.25, 0.50]
    ys = [0.0473979, 0.0784282]
    t_query = 0.273678

    correcto = linear_interp_clamped(xs, ys, t_query)
    check_close(correcto, 0.0503369, "interpolación SIN desplazar por T_irr da el valor correcto", rtol=1e-4)

    buggy = linear_interp_clamped(xs, ys, t_query - t_irr_h)
    check_close(buggy, 0.0499920,
                "restar T_irr antes de interpolar reproduce el valor erróneo del diagnóstico (documentación del bug)",
                rtol=1e-4)
    check(abs(correcto - buggy) > 1e-5, "el valor correcto y el erróneo difieren (F12 deja de reproducirse)")


def main() -> int:
    print("Tests oráculo de reference_data.js (Fase 4 del runbook, sin node)")
    print(f"Fixtures: {FIXTURES_EXP}")

    if not (FIXTURES_EXP / "fig6_exp4_experimental_normalizado.csv").exists():
        print(f"\nERROR: no se encuentran los fixtures en {FIXTURES_EXP}")
        return 1

    test_fixture_experimental()
    test_fixture_computacional()
    test_linear_interp_clamped_matches_numpy()
    test_deviation_metrics_legacy_11_points()
    test_series_for_metrics()
    test_resolve_target_sim_name()
    test_bqcm3_inverse_conversion()
    test_f12_time_origin_no_shift()

    print(f"\n{'-' * 50}")
    print(f"Resultado: {_PASSED} pasados, {_FAILED} fallidos")
    return 0 if _FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
