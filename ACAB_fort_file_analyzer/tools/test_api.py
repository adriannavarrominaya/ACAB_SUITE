"""test_api.py — Tests de la API REST (Fase 0 del runbook).

Script autocontenido, sin framework. Usa app.test_client() para ejercitar el
flujo feliz (/api/analyze → /api/isotopo_report) sobre la simulación de
referencia y comprobar los errores controlados.

Uso:
    python tools/test_api.py

Devuelve código de salida 0 si todo pasa, 1 si algún test falla.
"""
from __future__ import annotations

import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

# La salida contiene caracteres Unicode; fuerza UTF-8 para correr en verde
# también en consolas Windows con codepage cp1252.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import app as app_module  # noqa: E402

REF_SIM = REPO_ROOT / "tests" / "fixtures" / "ref_sim"

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


def check_close_local(got, expected, msg: str, rtol: float = 1e-6) -> None:
    try:
        check(math.isclose(float(got), float(expected), rel_tol=rtol), msg)
    except (TypeError, ValueError):
        _fail(f"{msg}: valor no numérico {got!r}")


def section(name: str) -> None:
    print(f"\n== {name} ==")


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_flujo_feliz(client) -> None:
    section("/api/analyze + /api/isotopo_report — flujo feliz")

    r = client.post("/api/analyze", json={"folder": str(REF_SIM)})
    check(r.status_code == 200, f"/api/analyze responde 200 (obtenido {r.status_code})")
    data = r.get_json()
    check(bool(data.get("ok")), "/api/analyze ok=True")
    check(len(data.get("simulations", {})) == 1, "una simulación en la respuesta")
    check("I131" in data.get("all_isotopes", []), "I131 en all_isotopes")
    check(bool(data.get("decay_dat_used")), "DECAY.dat usado como fuente de T½")

    # Fase 2: la densidad del material viaja en cada simulación (Bq/cm³ → MBq/g).
    sim0 = next(iter(data.get("simulations", {}).values()), {})
    dens = sim0.get("densidad_g_cm3")
    check(dens is not None and abs(dens - 0.12317) < 1e-4,
          f"densidad_g_cm3 en la respuesta (~0.12317, obtenido {dens})")

    # F13 del BACKLOG: procedencia del T½ POR SIMULACIÓN viaja en la
    # respuesta pública (t12_source/decay_dat_path); la librería completa
    # resuelta (privada, "_t12_dict") NUNCA sale por la API.
    check(sim0.get("t12_source") == "decay_dat", "sim0.t12_source = 'decay_dat' (ref_sim trae su propio DECAY.dat)")
    check(sim0.get("decay_dat_path") not in (None, ""), "sim0.decay_dat_path presente")
    check("_t12_dict" not in sim0, "_t12_dict (librería completa) no viaja en la respuesta pública")

    # Fase 5 (opcional, barrido): sin sweep_manifest.json en la carpeta →
    # el campo va como None, sin romper el flujo normal.
    check(data.get("sweep_manifest") is None,
          "sweep_manifest = None para una carpeta sin barrido")

    # RUNBOOK_figuras_yaml.md: sin YAML en REF_SIM → sin figuras (ya no hay
    # DEFAULT_FIGURAS de fallback) y yaml_used = 'none'.
    check(data.get("figuras") == [], f"figuras = [] sin YAML (obtenido {data.get('figuras')})")
    check(data.get("yaml_used") == "none", f"yaml_used = 'none' (obtenido {data.get('yaml_used')})")
    check(data.get("yaml_config") == {}, f"yaml_config = {{}} sin YAML (obtenido {data.get('yaml_config')})")

    r2 = client.post("/api/isotopo_report", json={"isotopo": "I131"})
    check(r2.status_code == 200, f"/api/isotopo_report responde 200 (obtenido {r2.status_code})")
    rep = r2.get_json()
    check(bool(rep.get("ok")), "/api/isotopo_report ok=True")
    check(rep.get("isotopo") == "I131", "isótopo devuelto = I131")

    informe = rep.get("informe", {})
    sims = informe.get("simulations", {})
    check(len(sims) == 1, "informe con una simulación")
    pico = next(iter(sims.values()))
    A = pico.get("A_pico", 0)
    check(15000 < A < 18000, f"A_pico I131 en rango oro (~1.65e4, obtenido {A})")
    check(len(informe.get("gamma_spectrum", [])) > 0, "espectro gamma de I131 presente")
    check("tabla1" in rep and "tabla2" in rep, "tablas comparativas presentes")

    # F1 Fase 2: la serie temporal de pureza (pureza_serie) viaja en metricas,
    # junto al escalar `pureza` ya existente — mismo caso oro que Fase 1
    # (verificado a mano en test_metricas.py: t_cruce=0, 19 puntos).
    metricas_sim = next(iter(informe.get("metricas", {}).values()), {})
    serie = metricas_sim.get("pureza_serie")
    check(serie is not None, "pureza_serie presente en metricas del endpoint")
    if serie is not None:
        check(len(serie.get("serie", [])) == 19,
              f"19 puntos de enfriamiento en la serie del endpoint (obtenido {len(serie.get('serie', []))})")
        check(serie.get("estado") == "alcanzado_en_fin_irradiacion",
              f"estado = alcanzado_en_fin_irradiacion (obtenido {serie.get('estado')})")
        t_cruce = serie.get("t_cruce") or {}
        check(t_cruce.get("t_h") == 0.0, f"t_cruce = 0 en la respuesta del endpoint (obtenido {t_cruce.get('t_h')})")
        ventana = serie.get("ventana_administracion") or {}
        check(15000 < (ventana.get("A_pico") or 0) < 18000,
              f"ventana_administracion.A_pico en rango oro (obtenido {ventana.get('A_pico')})")

    # F2: actividad específica del yodo (actividad_especifica_yodo_serie) viaja
    # en metricas junto a pureza_serie — mismo caso oro verificado a mano en
    # test_metricas.py (A_esp(t=0) ≈ 4.5e9 MBq/g, t_destacado_h = t_cruce = 0).
    aesp = metricas_sim.get("actividad_especifica_yodo_serie")
    check(aesp is not None, "actividad_especifica_yodo_serie presente en metricas del endpoint")
    if aesp is not None:
        check(len(aesp.get("serie", [])) == 19,
              f"19 puntos de enfriamiento en la serie de A_esp del endpoint (obtenido {len(aesp.get('serie', []))})")
        check(aesp.get("t_destacado_h") == 0.0,
              f"t_destacado_h = t_cruce de pureza = 0 (obtenido {aesp.get('t_destacado_h')})")
        v = aesp.get("valor_destacado_MBq_g") or 0
        check(4e9 < v < 5e9, f"valor_destacado_MBq_g en rango oro (~4.5e9, obtenido {v})")


def test_informe_folder_explicito(client) -> None:
    section("/api/isotopo_report — con folder explícito")
    # Requiere que test_flujo_feliz haya analizado REF_SIM antes.
    r = client.post("/api/isotopo_report", json={"isotopo": "I131", "folder": str(REF_SIM)})
    check(r.status_code == 200, f"200 con folder analizado (obtenido {r.status_code})")
    check(bool((r.get_json() or {}).get("ok")), "ok=True con folder explícito")


def test_informe_folder_no_analizado(client) -> None:
    section("/api/isotopo_report — carpeta no analizada")
    r = client.post("/api/isotopo_report",
                    json={"isotopo": "I131", "folder": str(REPO_ROOT / "carpeta_sin_analizar")})
    check(r.status_code == 404, f"404 para carpeta no analizada (obtenido {r.status_code})")
    check("error" in (r.get_json() or {}), "respuesta incluye campo 'error'")


def test_sweep_manifest(client) -> None:
    section("/api/analyze — carpeta con sweep_manifest.json (Fase 5 opcional, barrido)")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name in ("TeO2_x0.50", "TeO2_x1.00"):
            sub = root / name
            sub.mkdir()
            shutil.copy(REF_SIM / "fort.6", sub / "fort.6")
            shutil.copy(REF_SIM / "inp.5", sub / "inp.5")
            shutil.copy(REF_SIM / "DECAY.dat", sub / "DECAY.dat")

        manifest = {
            "timestamp": "2026-07-08T00:00:00+00:00",
            "sweep_type": "flux",
            "description": "Barrido de flujo x0.5/x1.0",
            "fixed_params": {},
            "n": 2,
            "simulations": [
                {"folder": "TeO2_x0.50", "params": {"XNORM": 0.5}},
                {"folder": "TeO2_x1.00", "params": {"XNORM": 1.0}},
            ],
        }
        (root / "sweep_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        r = client.post("/api/analyze", json={"folder": str(root)})
        check(r.status_code == 200, f"/api/analyze responde 200 (obtenido {r.status_code})")
        data = r.get_json()
        check(len(data.get("simulations", {})) == 2, "2 simulaciones descubiertas")

        sm = data.get("sweep_manifest")
        check(sm is not None, "sweep_manifest presente en la respuesta")
        assert sm is not None
        check(sm.get("sweep_type") == "flux", "sweep_type = 'flux'")
        folders = [s["folder"] for s in sm.get("simulations", [])]
        check(set(folders) == {"TeO2_x0.50", "TeO2_x1.00"},
              f"nombres de carpeta del manifest = subcarpetas descubiertas (obtenido {folders})")


def test_figuras_save(client) -> None:
    section("/api/figuras/save — guardado, discovery, validaciones (RUNBOOK_figuras_yaml.md)")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shutil.copy(REF_SIM / "fort.6", root / "fort.6")
        shutil.copy(REF_SIM / "inp.5", root / "inp.5")
        shutil.copy(REF_SIM / "DECAY.dat", root / "DECAY.dat")

        # Sin análisis previo de esta carpeta → 404.
        r = client.post("/api/figuras/save",
                         json={"folder": str(root), "yaml_text": "figuras: []\n"})
        check(r.status_code == 404, f"404 si la carpeta no ha sido analizada (obtenido {r.status_code})")

        r = client.post("/api/analyze", json={"folder": str(root)})
        check(r.status_code == 200, "análisis previo de la carpeta ok (puebla la cache)")

        # 422: YAML sin clave 'figuras' lista, o mal formado.
        r = client.post("/api/figuras/save",
                         json={"folder": str(root), "yaml_text": "otra_cosa: 1\n"})
        check(r.status_code == 422, f"422 sin clave 'figuras' lista (obtenido {r.status_code})")

        r = client.post("/api/figuras/save",
                         json={"folder": str(root), "yaml_text": "figuras: [not-closed\n"})
        check(r.status_code == 422, f"422 con YAML mal formado (obtenido {r.status_code})")

        # Guardado feliz — round-trip: conserva 'semividas' de un YAML de partida.
        yaml_text = (
            "figuras:\n"
            "  - num: 1\n"
            "    titulo: Figura 1\n"
            "    series:\n"
            "      - iso: I131\n"
            "        label: I131\n"
            "semividas:\n"
            "  I131: 8.0252 d\n"
        )
        r = client.post("/api/figuras/save", json={"folder": str(root), "yaml_text": yaml_text})
        check(r.status_code == 200, f"200 en guardado feliz (obtenido {r.status_code})")
        saved_path = root / "figuras.yaml"
        check(saved_path.exists(), "figuras.yaml escrito en la carpeta analizada")
        check("semividas" in saved_path.read_text(encoding="utf-8"),
              "el fichero guardado conserva la sección 'semividas' del YAML de partida")

        # 409 sin overwrite si ya existe; overwrite=True lo permite.
        r = client.post("/api/figuras/save", json={"folder": str(root), "yaml_text": yaml_text})
        check(r.status_code == 409, f"409 si ya existe y no se pide overwrite (obtenido {r.status_code})")

        r = client.post("/api/figuras/save",
                         json={"folder": str(root), "yaml_text": yaml_text, "overwrite": True})
        check(r.status_code == 200, f"200 con overwrite=True (obtenido {r.status_code})")

        # Discovery posterior: un nuevo análisis lo encuentra como 'auto'.
        r = client.post("/api/analyze", json={"folder": str(root)})
        data = r.get_json()
        check(data.get("yaml_used") == "auto",
              f"yaml_used = 'auto' tras guardar y reanalizar (obtenido {data.get('yaml_used')})")
        check(len(data.get("figuras", [])) == 1,
              "figuras.yaml guardado se descubre automáticamente en el siguiente análisis")


def test_espectro_gamma(client) -> None:
    section("/api/espectro_gamma — B1 del BACKLOG (Fase 3)")

    r = client.post("/api/analyze", json={"folder": str(REF_SIM)})
    check(r.status_code == 200, f"/api/analyze responde 200 (obtenido {r.status_code})")
    data = r.get_json()
    check(data.get("photon_dat_used") is False,
          "photon_dat_used = False sin PHOTON.dat junto al fort.6 de ref_sim "
          "(el fixture se llama PHOTON_extract.dat, no PHOTON.dat)")
    sim_name = next(iter(data.get("simulations", {})))

    # Sin librería cargada aún: el endpoint responde ok, pero sin líneas.
    r0 = client.post("/api/espectro_gamma", json={"folder": str(REF_SIM), "t_h": 4.5})
    check(r0.status_code == 200, f"200 sin librería aún cargada (obtenido {r0.status_code})")
    j0 = r0.get_json()
    check(j0.get("photon_dat_used") is False, "photon_dat_used = False antes de cargar la librería")
    check(j0.get("espectro", {}).get("lineas") == [], "sin líneas antes de cargar la librería")

    # Override explícito de photon_dat_path -> carga el extracto congelado y
    # calcula el espectro en t=4.5h (enfriamiento tardío, caso oro de
    # test_photon.py: tasa(364 keV) = A(I131,4.5h) * 0.812).
    photon_extract = str(REF_SIM / "PHOTON_extract.dat")
    r1 = client.post("/api/espectro_gamma", json={
        "folder": str(REF_SIM), "sim": sim_name, "t_h": 4.5,
        "photon_dat_path": photon_extract,
    })
    check(r1.status_code == 200, f"200 con photon_dat_path override (obtenido {r1.status_code})")
    j1 = r1.get_json()
    check(bool(j1.get("ok")), "ok=True")
    check(j1.get("photon_dat_used") is True, "photon_dat_used = True tras el override")
    check(j1.get("sim") == sim_name, "sim devuelto = simulación de ref_sim")

    espectro = j1.get("espectro", {})
    check_close_local(espectro.get("t_h"), 4.5, "t_h del espectro = 4.5 (timestep real)")
    lineas_364 = [l for l in espectro.get("lineas", [])
                  if l.get("nucleido") == "I131" and abs(l.get("E_keV", 0) - 364.49) < 0.01]
    check(len(lineas_364) == 1, "línea de 364,49 keV de I131 presente en la respuesta")
    if lineas_364:
        tasa = lineas_364[0].get("tasa_fotones_s_cm3")
        check_close_local(tasa, 16490.0 * 0.812,
                           f"tasa(364 keV) = A(I131,4.5h)*0,812 (obtenido {tasa})")
    check("I130M" in espectro.get("nucleidos_sin_lineas", []),
          "I130M en nucleidos_sin_lineas (presente en ref_sim, ausente del extracto)")

    # La librería cargada por el override queda en cache: una llamada
    # posterior SIN photon_dat_path la sigue usando (no hay que recargarla en
    # cada petición de instante).
    r2 = client.post("/api/espectro_gamma", json={"folder": str(REF_SIM), "sim": sim_name, "t_h": 0.0})
    check(r2.status_code == 200, f"200 en la siguiente petición sin override (obtenido {r2.status_code})")
    j2 = r2.get_json()
    check(j2.get("photon_dat_used") is True, "photon_dat_used sigue True (librería cacheada)")
    check(len(j2.get("espectro", {}).get("lineas", [])) > 0,
          "espectro calculado en t=0 con la librería ya cacheada")

    # Ruta de PHOTON.dat inexistente -> 404, sin romper la librería ya cacheada.
    r3 = client.post("/api/espectro_gamma", json={
        "folder": str(REF_SIM), "photon_dat_path": str(REF_SIM / "no_existe_PHOTON.dat"),
    })
    check(r3.status_code == 404, f"404 con ruta de PHOTON.dat inexistente (obtenido {r3.status_code})")

    # Carpeta no analizada -> 404 (mismo criterio que /api/isotopo_report).
    r4 = client.post("/api/espectro_gamma",
                      json={"folder": str(REPO_ROOT / "carpeta_sin_analizar"), "t_h": 0.0})
    check(r4.status_code == 404, f"404 para carpeta no analizada (obtenido {r4.status_code})")


def test_chains_report(client) -> None:
    section("/api/chains_report — F9 del BACKLOG (Fase 4)")

    chains_root = REPO_ROOT / "tests" / "fixtures" / "chains_synthetic"

    r0 = client.post("/api/chains_report", json={})
    check(r0.status_code == 400, f"400 sin 'root' (obtenido {r0.status_code})")

    r1 = client.post("/api/chains_report",
                      json={"root": str(REPO_ROOT / "carpeta_sin_manifest")})
    check(r1.status_code == 404, f"404 sin chains_manifest.json en la carpeta (obtenido {r1.status_code})")

    r2 = client.post("/api/chains_report", json={"root": str(chains_root)})
    check(r2.status_code == 200, f"200 con el análisis sintético (obtenido {r2.status_code})")
    j2 = r2.get_json()
    check(bool(j2.get("ok")), "ok=True")
    check(j2.get("ifinal") == "CO57", f"ifinal=CO57 (obtenido {j2.get('ifinal')})")
    check_close_local(j2.get("t_star_h"), 1.0, "t* por defecto = t_pico de la referencia = 1 h")
    check_close_local(j2.get("suma_r_i"), 1.0, "Σ R_i = 1.0 (mismo caso oro que test_chains.py)")
    check(len(j2.get("tabla2", [])) == 3, f"tabla2 con 3 filas (obtenido {len(j2.get('tabla2', []))})")
    check("diagrama" in j2["tabla2"][0], "cada fila de tabla2 trae su diagrama embebido")

    # Selector de instante manual, vía t_h explícito.
    r3 = client.post("/api/chains_report", json={"root": str(chains_root), "t_h": 0.0})
    check(r3.status_code == 200, f"200 con t_h manual (obtenido {r3.status_code})")
    j3 = r3.get_json()
    check(j3.get("t_star_fuente") == "manual", "t_star_fuente='manual' con t_h explícito")
    check_close_local(j3.get("a_ref"), 40.0, "A_ref(t=0) = 40 Bq/cm3 con el instante manual")

    # F9d del BACKLOG: output_chain.txt corrupto no rompe el endpoint, degrada
    # por isótopo (fila de tabla1 anotada, tabla2 sin sus filas).
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp) / "chains_analysis"
        shutil.copytree(chains_root, tmp_root)
        (tmp_root / "chains_FE56" / "output_chain.txt").write_text(
            "ESTO NO ES UN OUTPUT DE CHAINS VALIDO\n", encoding="utf-8")

        r4 = client.post("/api/chains_report", json={"root": str(tmp_root)})
        check(r4.status_code == 200,
              f"200 pese al output_chain.txt corrupto de un isótopo (obtenido {r4.status_code})")
        j4 = r4.get_json()
        tabla1_4 = {f["isotopo"]: f for f in j4.get("tabla1", [])}
        check(set(tabla1_4.keys()) == {"FE56", "MN55"},
              f"tabla1 conserva los 2 isótopos (obtenido {sorted(tabla1_4.keys())})")
        check(tabla1_4.get("FE56", {}).get("nota_cadenas") is not None,
              f"FE56 anotado en la respuesta JSON (obtenido {tabla1_4.get('FE56', {}).get('nota_cadenas')!r})")
        check(tabla1_4.get("MN55", {}).get("nota_cadenas") is None,
              "MN55 sin nota (su output_chain.txt no se tocó)")
        filas_fe56_4 = [f for f in j4.get("tabla2", []) if f["isotopo"] == "FE56"]
        check(filas_fe56_4 == [], f"tabla2 sin filas de FE56 (obtenido {len(filas_fe56_4)})")


def test_carpeta_inexistente(client) -> None:
    section("/api/analyze — carpeta inexistente")
    r = client.post("/api/analyze", json={"folder": str(REPO_ROOT / "no_existe_xyz")})
    check(r.status_code >= 400, f"error HTTP para carpeta inexistente (obtenido {r.status_code})")
    check("error" in (r.get_json() or {}), "respuesta incluye campo 'error'")


def test_folder_vacio(client) -> None:
    section("/api/analyze — sin carpeta")
    r = client.post("/api/analyze", json={})
    check(r.status_code == 400, f"400 sin carpeta (obtenido {r.status_code})")


def test_isotopo_sin_analisis(client) -> None:
    section("/api/isotopo_report — sin análisis previo")
    # Reinicia la cache global (keyed por carpeta) para simular estado limpio.
    app_module._analysis_cache.clear()
    app_module._last_folder_key = None

    r = client.post("/api/isotopo_report", json={"isotopo": "I131"})
    check(r.status_code == 409, f"409 sin análisis activo (obtenido {r.status_code})")


def main() -> int:
    print("Tests de la API REST (Fase 0)")
    print(f"Fixtures: {REF_SIM}")

    if not (REF_SIM / "fort.6").exists():
        print(f"\nERROR: no se encuentra el fixture {REF_SIM / 'fort.6'}")
        return 1

    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()

    # El orden importa: el flujo feliz deja la cache poblada; el test de
    # "sin análisis previo" la reinicia explícitamente al final.
    test_folder_vacio(client)
    test_carpeta_inexistente(client)
    test_flujo_feliz(client)
    test_informe_folder_explicito(client)
    test_informe_folder_no_analizado(client)
    test_sweep_manifest(client)
    test_figuras_save(client)
    test_espectro_gamma(client)
    test_chains_report(client)
    test_isotopo_sin_analisis(client)

    print(f"\n{'-' * 50}")
    print(f"Resultado: {_PASSED} pasados, {_FAILED} fallidos")
    return 0 if _FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
