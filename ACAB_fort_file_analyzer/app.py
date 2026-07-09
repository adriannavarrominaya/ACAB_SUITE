"""app.py — ACAB Fort File Analyzer web application (Flask).

Arranque:
    python app.py

Abre automáticamente http://127.0.0.1:5000 en el navegador por defecto.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from threading import Timer
from typing import Optional

import yaml
from flask import Flask, jsonify, render_template, request

from fort_analyzer import (
    DEFAULT_FIGURAS,
    DEFAULT_SEMIVIDAS,
    GAMMA_I131,
    analizar_carpeta,
    build_t12_dict,
    calcular_informe_isotopo,
    calcular_tablas_comparativas,
    descubrir_simulaciones,
    iso_label,
    leer_decay_dat,
    leer_sweep_manifest,
    parse_t12,
)

app = Flask(__name__)

# In-memory cache for successful analyses (single-user desktop app), keyed by
# normalised folder path so several browser tabs pointing at different folders
# no longer overwrite each other's data.
#   _analysis_cache[norm_folder] = {"all_data", "t12_dict", "semividas_keys"}
# Populated by /api/analyze; consumed by /api/isotopo_report.
_analysis_cache: dict[str, dict] = {}

# Most recently analysed folder key — backward-compatible fallback for callers
# that invoke /api/isotopo_report without an explicit "folder".
_last_folder_key: Optional[str] = None


def _norm_folder(folder: str) -> str:
    """Normalise a folder path for use as a cache key (case-insensitive on Windows)."""
    return os.path.normcase(os.path.abspath(folder))


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ping")
def api_ping():
    # Fragmento común de la suite — mantener sincronizado en los 3 repos
    # (solo cambia el nombre de la app). La cabecera CORS es imprescindible:
    # el banner de las otras apps hace fetch cross-origin SOLO a este endpoint.
    resp = jsonify({"ok": True, "app": "fort-analyzer"})
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """Scan a folder for simulation subfolders containing fort.6."""
    data = request.get_json(force=True, silent=True) or {}
    folder = (data.get("folder") or "").strip()
    if not folder:
        return jsonify({"error": "Debe especificar una carpeta."}), 400

    try:
        sims = descubrir_simulaciones(folder)
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    # Look for YAML config in the folder or its parent
    yaml_path: Optional[str] = None
    for candidate in [
        Path(folder) / "figuras - multiples simulaciones.yaml",
        Path(folder).parent / "figuras - multiples simulaciones.yaml",
        Path(folder) / "config.yaml",
        Path(folder).parent / "config.yaml",
    ]:
        if candidate.exists():
            yaml_path = str(candidate)
            break

    return jsonify({
        "ok":           True,
        "simulations":  [{"name": n, "fort6": p} for n, p in sims],
        "yaml_path":    yaml_path,
        "folder":       folder,
        "count":        len(sims),
    })


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Full analysis of a simulations folder. Returns all data as JSON."""
    data = request.get_json(force=True, silent=True) or {}
    folder = (data.get("folder") or "").strip()
    if not folder:
        return jsonify({"error": "Debe especificar una carpeta."}), 400

    leer_inp5_flag  = bool(data.get("leer_inp5", True))
    t_irr_override  = _safe_float(data.get("t_irr_override"))
    t_cool_override = _safe_float(data.get("t_cool_override"))
    phi_override    = _safe_float(data.get("phi_override"))

    # Load YAML config
    yaml_content: Optional[str] = data.get("yaml_content")
    if yaml_content:
        try:
            cfg = yaml.safe_load(yaml_content) or {}
        except Exception:
            cfg = {}
        yaml_used = "upload"
    else:
        cfg = _load_yaml_config(folder)
        yaml_used = "auto" if cfg else "none"

    figuras: list = cfg.get("figuras", DEFAULT_FIGURAS) if cfg else DEFAULT_FIGURAS

    # ── Build T½ dictionary ────────────────────────────────────────────────
    # Priority (highest to lowest):
    #   1. YAML "semividas" section (explicit overrides)
    #   2. DECAY.dat from the first simulation folder (authoritative library)
    #   3. DEFAULT_SEMIVIDAS built into the code (fallback)

    # Preview simulation list to locate DECAY.dat before the full parse
    decay_dat_path: Optional[str] = None
    decay_dat_used = False
    try:
        sims_preview = descubrir_simulaciones(folder)
        if sims_preview:
            candidate = Path(sims_preview[0][1]).parent / "DECAY.dat"
            if candidate.exists():
                decay_dat_path = str(candidate)
    except Exception:
        sims_preview = []

    if decay_dat_path:
        base_t12 = leer_decay_dat(decay_dat_path)
        decay_dat_used = True
    else:
        base_t12 = build_t12_dict(DEFAULT_SEMIVIDAS)

    # YAML semividas override (only the keys explicitly listed in YAML win)
    yaml_semividas: dict = cfg.get("semividas", {}) if cfg else {}
    yaml_t12_overrides = build_t12_dict(yaml_semividas)
    t12_dict = {**base_t12, **yaml_t12_overrides}

    # Run analysis
    try:
        all_data, errors = analizar_carpeta(
            folder, t12_dict, leer_inp5_flag,
            t_irr_override, t_cool_override, phi_override,
        )
    except (FileNotFoundError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    if not all_data:
        return jsonify({"error": "No se encontraron simulaciones válidas en la carpeta."}), 422

    # Fase 5 (opcional, runbook del barrido): si la carpeta analizada es la raíz
    # de un barrido paramétrico generado por el INP File Configurator, adjunta
    # sus parámetros por simulación para la pestaña "Optimización". None si no
    # hay sweep_manifest.json — comportamiento intacto para carpetas normales.
    sweep_manifest = leer_sweep_manifest(folder)

    # All simulations share the same isotope set — use the first as reference.
    # semividas_keys now covers every isotope present in the fort.6 files,
    # so comparison tables are comprehensive rather than limited to the YAML list.
    first_sim = next(iter(all_data.values()))
    all_isotopes = sorted(set(
        list(first_sim["datos_irr_Bq"].keys()) + list(first_sim["datos_cool"].keys())
    ))
    semividas_keys = all_isotopes

    # Cache analysis so /api/isotopo_report can reuse it without re-parsing.
    # Keyed by normalised folder path; also remember it as the last-analysed one.
    global _last_folder_key
    folder_key = _norm_folder(folder)
    _analysis_cache[folder_key] = {
        "all_data":       all_data,
        "t12_dict":       t12_dict,
        "semividas_keys": semividas_keys,
    }
    _last_folder_key = folder_key

    return jsonify(_sanitize_for_json({
        "ok":             True,
        "folder":         folder,
        "yaml_used":      yaml_used,
        "decay_dat_used": decay_dat_used,
        "decay_dat_path": decay_dat_path,
        "simulations":    all_data,
        "errors":         errors,
        "all_isotopes":   all_isotopes,
        "semividas_keys": semividas_keys,
        "figuras":        figuras,
        "sweep_manifest": sweep_manifest,
    }))


@app.route("/api/browse-folder", methods=["POST"])
def api_browse_folder():
    """Open a native OS folder-picker dialog and return the selected path.

    Because Flask and the browser run on the same machine, this launches a
    tkinter filedialog in a child process so we avoid main-thread constraints.
    """
    try:
        script = (
            "import sys; sys.stdout.reconfigure(encoding='utf-8'); "
            "import tkinter as tk; from tkinter import filedialog; "
            "root=tk.Tk(); root.attributes('-topmost',1); root.withdraw(); "
            "p=filedialog.askdirectory(parent=root, title='Seleccionar carpeta de simulaciones'); "
            "root.destroy(); print(p or '',end='')"
        )
        env = __import__("os").environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", env=env,
        )
        folder = result.stdout.strip()
        return jsonify({"ok": True, "folder": folder or None})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/gamma-spectrum", methods=["GET"])
def api_gamma_spectrum():
    return jsonify({"ok": True, "data": GAMMA_I131})


@app.route("/api/isotopo_report", methods=["POST"])
def api_isotopo_report():
    """Generate report for a single isotope using the cached analysis data.

    Requires a prior call to /api/analyze. The caller should pass the same
    "folder" it analysed so several tabs with different folders don't collide;
    if omitted, the most recently analysed folder is used (backward compat).
    Returns the isotope report and comparison tables with the selected isotope
    as the reference anchor.
    """
    payload = request.get_json(force=True, silent=True) or {}
    isotopo = (payload.get("isotopo") or "").strip().upper()
    folder  = (payload.get("folder") or "").strip()
    # Fase 5: lista editable de isótopos considerados "impureza" para la
    # métrica de pureza radionucleídica. None → mismo-elemento (por defecto).
    impurezas_raw = payload.get("impurezas")
    impurezas = ([str(i).strip().upper() for i in impurezas_raw if str(i).strip()]
                 if isinstance(impurezas_raw, list) else None)

    if not isotopo:
        return jsonify({"error": "Debe especificar un isótopo."}), 400

    if folder:
        entry = _analysis_cache.get(_norm_folder(folder))
        if entry is None:
            return jsonify({
                "error": f"La carpeta '{folder}' no ha sido analizada. Ejecute el análisis primero."
            }), 404
    else:
        if _last_folder_key is None:
            return jsonify({"error": "No hay análisis activo. Ejecute el análisis primero."}), 409
        entry = _analysis_cache.get(_last_folder_key)
        if entry is None:
            return jsonify({"error": "No hay análisis activo. Ejecute el análisis primero."}), 409

    all_data       = entry["all_data"]
    t12_dict       = entry["t12_dict"]
    semividas_keys = entry["semividas_keys"]

    first_sim = next(iter(all_data.values()))
    known = set(first_sim["datos_irr_Bq"].keys()) | set(first_sim["datos_cool"].keys())
    if isotopo not in known:
        return jsonify({"error": f"Isótopo '{isotopo}' no encontrado en los datos."}), 404

    informe = calcular_informe_isotopo(all_data, isotopo, t12_dict, impurezas)
    tabla1, tabla2 = calcular_tablas_comparativas(all_data, semividas_keys, referencia=isotopo)

    return jsonify(_sanitize_for_json({
        "ok":      True,
        "isotopo": isotopo,
        "informe": informe,
        "tabla1":  tabla1,
        "tabla2":  tabla2,
    }))


@app.route("/api/defaults", methods=["GET"])
def api_defaults():
    """Return default half-lives, figure config, and isotope labels."""
    labels = {iso: iso_label(iso) for iso in DEFAULT_SEMIVIDAS}
    t12_info = {}
    for iso, val in DEFAULT_SEMIVIDAS.items():
        t12_s = parse_t12(val)
        if math.isinf(t12_s):
            t12_info[iso] = {"val": val, "T12_s": None, "stable": True}
        else:
            t12_info[iso] = {"val": val, "T12_s": t12_s, "stable": False,
                             "T12_d": t12_s / 86400, "T12_h": t12_s / 3600}
    return jsonify({
        "ok":       True,
        "figuras":  DEFAULT_FIGURAS,
        "semividas": t12_info,
        "labels":   labels,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(val) -> Optional[float]:
    if val is None or val == "" or val == "null":
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _sanitize_for_json(obj):
    """Recursively replace float nan/inf with None so jsonify produces valid JSON.

    ACAB fort.6 can contain literal 'NaN' tokens (produced when a numerical
    error occurs, e.g. 0-atom isotopes with undefined activity). Python parses
    them as float('nan'), which json.dumps serialises as bare 'NaN' — not valid
    JSON. Converting to None → JSON null lets the rest of the pipeline keep
    working while marking the bad values explicitly.
    """
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return obj


def _load_yaml_config(folder: str) -> dict:
    """Try to load YAML config from the folder or its parent."""
    for candidate in [
        Path(folder) / "figuras - multiples simulaciones.yaml",
        Path(folder).parent / "figuras - multiples simulaciones.yaml",
        Path(folder) / "config.yaml",
        Path(folder).parent / "config.yaml",
    ]:
        if candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                return {}
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="ACAB Fort File Analyzer")
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=int(os.environ.get("ACAB_ANALYZER_PORT", 5001)),
        help="Puerto en el que escucha el servidor (por defecto: 5001, "
             "o variable de entorno ACAB_ANALYZER_PORT)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("ACAB_ANALYZER_HOST", "127.0.0.1"),
        help="Interfaz de red (por defecto: 127.0.0.1)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="No abrir el navegador al arrancar (lo usa suite_launcher.py; "
             "equivale a la variable ACAB_SUITE_NO_BROWSER=1)",
    )
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"

    def _open_browser():
        webbrowser.open(url)

    if not args.no_browser and not os.environ.get("ACAB_SUITE_NO_BROWSER"):
        Timer(1.2, _open_browser).start()

    try:
        from waitress import serve
        print("=" * 60)
        print("  ACAB Fort File Analyzer")
        print(f"  {url}")
        print("=" * 60)
        serve(app, host=args.host, port=args.port)
    except ImportError:
        print("waitress no instalado, usando servidor de desarrollo Flask.")
        print(f"  {url}")
        app.run(debug=False, host=args.host, port=args.port)
