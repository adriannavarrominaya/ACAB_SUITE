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
    test_isotopo_sin_analisis(client)

    print(f"\n{'-' * 50}")
    print(f"Resultado: {_PASSED} pasados, {_FAILED} fallidos")
    return 0 if _FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
