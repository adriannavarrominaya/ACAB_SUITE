"""app.py — ACAB inp File Configurator web application (Flask).

Arranque:
    python app.py
Abre automáticamente http://127.0.0.1:5000 en el navegador por defecto.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path
from threading import Timer

from flask import Flask, jsonify, render_template, request, send_file

import chains_analysis
import runner
from acab_parser import ACABParser
from chains_handler import (
    default_chains_data, is_chains_file, read_chains_inp, write_chains_inp,
)
from chains_inventory import leer_concentraciones_iniciales, nombre_a_zzaaas
from sweep_manifest_view import ManifestCorruptError, build_manifest_view
from sweep_writer import SweepError, generate_sweep, preview_sweep

app = Flask(__name__)

# Nombre de esta app tal como aparece en acab_suite/suite_config.json
APP_NAME = 'inp-configurator'


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chains')
def chains():
    return render_template('chains.html')


@app.route('/api/ping')
def api_ping():
    # Fragmento común de la suite — mantener sincronizado en los 3 repos
    # (solo cambia el nombre de la app). La cabecera CORS es imprescindible:
    # el banner de las otras apps hace fetch cross-origin SOLO a este endpoint.
    resp = jsonify({'ok': True, 'app': 'inp-configurator'})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/api/new', methods=['GET'])
def api_new():
    return jsonify({'ok': True, 'data': _default_data()})


@app.route('/api/load', methods=['POST'])
def api_load():
    if 'file' not in request.files:
        return jsonify({'error': 'No se adjuntó ningún fichero.'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'Nombre de fichero vacío.'}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix='.5') as tmp:
        f.save(tmp.name)
        tmp_path = Path(tmp.name)

    try:
        if is_chains_file(tmp_path):
            return jsonify({
                'error': (
                    'Este fichero es de entrada de CHAINS, no un fichero inp.5. '
                    'Usa la herramienta CHAINS desde el menú Herramientas → CHAINS.'
                ),
                'chains': True,
            }), 422
        data = ACABParser().read_inp5(tmp_path)
        return jsonify({'ok': True, 'data': data, 'filename': f.filename})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 422
    finally:
        tmp_path.unlink(missing_ok=True)


@app.route('/api/save', methods=['POST'])
def api_save():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        content = _write_inp5(payload.get('data', {}))
        buf = io.BytesIO(content.encode('utf-8'))
        buf.seek(0)
        fname = payload.get('filename', 'output.5')
        return send_file(buf, as_attachment=True,
                         download_name=fname, mimetype='text/plain')
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/api/preview', methods=['POST'])
def api_preview():
    """Return the formatted inp.5 content as a JSON string (no download)."""
    payload = request.get_json(force=True, silent=True) or {}
    try:
        content = _write_inp5(payload.get('data', {}))
        return jsonify({'ok': True, 'content': content})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 422


@app.route('/api/save-to-folder', methods=['POST'])
def api_save_to_folder():
    """Write the current inp.5 directly into a chosen folder (U2 del BACKLOG).

    Body: {data, folder, overwrite}. 409 (con exists:true) si <folder>/inp.5
    ya existe y overwrite no es true — el frontend pide confirmación y
    reintenta con overwrite:true.
    """
    payload = request.get_json(force=True, silent=True) or {}
    folder = (payload.get('folder') or '').strip()
    overwrite = bool(payload.get('overwrite'))

    if not folder:
        return jsonify({'error': 'Debe especificar una carpeta.'}), 400

    folder_path = Path(folder)
    if not folder_path.is_dir():
        return jsonify({'error': f'La carpeta no existe: {folder}'}), 422

    try:
        content = _write_inp5(payload.get('data', {}))
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500

    target = folder_path / 'inp.5'
    if target.exists() and not overwrite:
        return jsonify({
            'error': f"Ya existe '{target}'. Confirma para sobrescribir.",
            'exists': True,
        }), 409

    try:
        target.write_text(content, encoding='utf-8')
    except OSError as exc:
        return jsonify({'error': f"No se pudo escribir '{target}': {exc}"}), 500

    return jsonify({'ok': True, 'path': str(target)})


# ---------------------------------------------------------------------------
# CHAINS routes
# ---------------------------------------------------------------------------

@app.route('/api/chains/new', methods=['GET'])
def api_chains_new():
    return jsonify({'ok': True, 'data': default_chains_data()})


@app.route('/api/chains/load', methods=['POST'])
def api_chains_load():
    if 'file' not in request.files:
        return jsonify({'error': 'No se adjuntó ningún fichero.'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'Nombre de fichero vacío.'}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
        f.save(tmp.name)
        tmp_path = Path(tmp.name)

    try:
        data = read_chains_inp(tmp_path)
        return jsonify({'ok': True, 'data': data, 'filename': f.filename})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 422
    finally:
        tmp_path.unlink(missing_ok=True)


@app.route('/api/chains/save', methods=['POST'])
def api_chains_save():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        content = write_chains_inp(payload.get('data', {}))
        buf = io.BytesIO(content.encode('utf-8'))
        buf.seek(0)
        fname = payload.get('filename', 'input.chain.txt')
        return send_file(buf, as_attachment=True,
                         download_name=fname, mimetype='text/plain')
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/api/chains/preview', methods=['POST'])
def api_chains_preview():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        content = write_chains_inp(payload.get('data', {}))
        return jsonify({'ok': True, 'content': content})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 422


# ---------------------------------------------------------------------------
# Sweep routes  (parametric sweep generator)
# ---------------------------------------------------------------------------

@app.route('/api/browse-folder', methods=['POST'])
def api_browse_folder():
    """Open a native OS folder-picker dialog and return the selected path.

    Flask and the browser run on the same machine, so we launch a tkinter
    filedialog in a child process (avoids main-thread constraints of the
    server). The dialog title is passed via an environment variable to avoid
    any code injection in the inline script.
    """
    payload = request.get_json(force=True, silent=True) or {}
    title = (payload.get('title') or 'Seleccionar carpeta').strip() or 'Seleccionar carpeta'
    try:
        script = (
            "import os, sys; sys.stdout.reconfigure(encoding='utf-8'); "
            "import tkinter as tk; from tkinter import filedialog; "
            "root=tk.Tk(); root.attributes('-topmost',1); root.withdraw(); "
            "p=filedialog.askdirectory(parent=root, "
            "title=os.environ.get('ACAB_PICK_TITLE','Seleccionar carpeta')); "
            "root.destroy(); print(p or '', end='')"
        )
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['ACAB_PICK_TITLE'] = title
        result = subprocess.run(
            [sys.executable, '-c', script],
            capture_output=True, text=True, timeout=120,
            encoding='utf-8', env=env,
        )
        folder = (result.stdout or '').strip()
        return jsonify({'ok': True, 'folder': folder or None})
    except Exception as exc:  # noqa: BLE001
        return jsonify({'error': str(exc)}), 500


@app.route('/api/sweep/preview', methods=['POST'])
def api_sweep_preview():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        res = preview_sweep(
            payload.get('root'), payload.get('base_folder'),
            payload.get('prefix') or '', payload.get('sims') or [])
        return jsonify({'ok': True, **res})
    except SweepError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), exc.status
    except Exception as exc:  # noqa: BLE001
        return jsonify({'ok': False, 'error': str(exc)}), 500


@app.route('/api/sweep/manifest', methods=['GET'])
def api_sweep_manifest():
    """Vista de solo lectura de un barrido ya generado (U6 del BACKLOG):
    NO escribe nada, solo lee sweep_manifest.json (+ batch_results.json si
    existe) de `root`. Unifica el flujo de "cargar un barrido" con el de
    "ejecutarlo": cargar siempre muestra el contenido; ejecutar es una
    acción posterior sobre lo ya cargado (ver static/js/sweep.js)."""
    root = (request.args.get('root') or '').strip()
    if not root:
        return jsonify({'ok': False, 'error': 'Falta la carpeta raíz del barrido.'}), 422
    root_p = Path(root)
    if not root_p.is_dir():
        return jsonify({'ok': False, 'error': f'La carpeta no existe: {root}'}), 422
    try:
        view = build_manifest_view(root_p)
    except FileNotFoundError:
        return jsonify({'ok': False, 'error':
            'Esta carpeta no contiene un barrido generado por la suite '
            '(no se encontró sweep_manifest.json).'}), 404
    except ManifestCorruptError as exc:
        return jsonify({'ok': False, 'error':
            f'sweep_manifest.json no se pudo leer (JSON inválido): {exc}'}), 422
    return jsonify({'ok': True, **view})


@app.route('/api/sweep', methods=['POST'])
def api_sweep():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        res = generate_sweep(payload, _write_inp5)
        return jsonify({'ok': True, **res})
    except SweepError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), exc.status
    except Exception as exc:  # noqa: BLE001
        return jsonify({'ok': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Análisis de contribución por cadenas (F9 del BACKLOG, Fase 2)
#
# Sección nueva, análoga en fontanería al barrido (deep_merge, copia de la
# carpeta base con exclusión C4) pero con manifest PROPIO
# (chains_manifest.json, no un sweep_manifest) — ver chains_analysis.py.
# ---------------------------------------------------------------------------

@app.route('/api/chains-analysis/inventory', methods=['GET'])
def api_chains_analysis_inventory():
    """Inventario isotópico inicial (t=0) del fort.6 de una carpeta de
    referencia, para la UI de selección (checkboxes con C_i)."""
    reference_folder = (request.args.get('reference_folder') or '').strip()
    if not reference_folder:
        return jsonify({'ok': False, 'error': 'Falta la carpeta de referencia.'}), 422
    ref_p = Path(reference_folder)
    fort6 = ref_p / 'fort.6'
    if not fort6.is_file():
        return jsonify({'ok': False, 'error':
            f"No se encontró 'fort.6' en la carpeta de referencia: {reference_folder}"}), 422
    try:
        concentraciones = leer_concentraciones_iniciales(str(fort6))
    except Exception as exc:  # noqa: BLE001
        return jsonify({'ok': False, 'error': str(exc)}), 422

    isotopos = []
    for name, c_i in concentraciones.items():
        try:
            zzaaas = nombre_a_zzaaas(name)
        except ValueError:
            continue  # nombre no codificable (no debería pasar, defensivo)
        isotopos.append({'name': name, 'c_i': c_i, 'zzaaas': zzaaas})
    isotopos.sort(key=lambda d: d['name'])
    return jsonify({'ok': True, 'isotopos': isotopos})


@app.route('/api/chains-analysis/preview', methods=['POST'])
def api_chains_analysis_preview():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        res = chains_analysis.preview_chains_analysis(
            payload.get('root'), payload.get('reference_folder'),
            payload.get('isotopes') or [])
        return jsonify({'ok': True, **res})
    except SweepError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), exc.status
    except Exception as exc:  # noqa: BLE001
        return jsonify({'ok': False, 'error': str(exc)}), 500


@app.route('/api/chains-analysis', methods=['POST'])
def api_chains_analysis_generate():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        res = chains_analysis.generate_chains_analysis(payload, _write_inp5)
        return jsonify({'ok': True, **res})
    except SweepError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), exc.status
    except Exception as exc:  # noqa: BLE001
        return jsonify({'ok': False, 'error': str(exc)}), 500


@app.route('/api/chains-analysis/manifest', methods=['GET'])
def api_chains_analysis_manifest():
    """Vista de solo lectura de un análisis ya generado: lee
    chains_manifest.json (+ chains_batch_results.json si existe, escrito
    por /api/chains-analysis/run) de `root`. Nunca escribe nada."""
    root = (request.args.get('root') or '').strip()
    if not root:
        return jsonify({'ok': False, 'error': 'Falta la carpeta raíz del análisis.'}), 422
    root_p = Path(root)
    if not root_p.is_dir():
        return jsonify({'ok': False, 'error': f'La carpeta no existe: {root}'}), 422

    manifest_path = root_p / 'chains_manifest.json'
    if not manifest_path.is_file():
        return jsonify({'ok': False, 'error':
            'Esta carpeta no contiene un análisis de cadenas generado por la '
            'suite (no se encontró chains_manifest.json).'}), 404
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return jsonify({'ok': False, 'error':
            f'chains_manifest.json no se pudo leer (JSON inválido): {exc}'}), 422

    batch_results = None
    results_path = root_p / 'chains_batch_results.json'
    if results_path.is_file():
        try:
            with open(results_path, 'r', encoding='utf-8') as f:
                batch_results = json.load(f)
        except (OSError, json.JSONDecodeError):
            batch_results = None

    return jsonify({'ok': True, 'manifest': manifest, 'batch_results': batch_results})


# ---------------------------------------------------------------------------
# Ejecución de ACAB (Fase R3 del runbook runner v2)
#
# Convención de la suite (acab_suite/README.md, sección "Invocación de los
# códigos"): simulaciones autocontenidas — el ejecutable vive EN el
# directorio de trabajo y se lanza sin argumentos con cwd=workdir. No hay
# ruta global de ejecutable.
# ---------------------------------------------------------------------------

_DEFAULT_RUNNER_CONFIG = {
    'exe_name': 'acab.exe',
    'required_files': ['acab.exe', 'inp.5', 'DECAY.dat', 'XSECTION.dat'],
    'output_file': 'fort.6',
    'timeout_s': 60,
    'default_workdir': '',
}

# Pipeline del barrido espectral (Fase P4, D7 del RUNBOOK_barrido_espectral.md):
# run collaps (cwd=<sim>/collaps) → copy XSECTION.dat → run acab (cwd=<sim>) →
# check_flux sobre <sim>/collaps/FLUX.inf. El nombre de collaps.exe no es
# configurable en esta app (a diferencia de acab.exe vía cfg['exe_name']):
# es una convención fija de la suite (acab_suite/README.md).
_COLLAPS_EXE_NAME = 'collaps.exe'
_SPECTRUM_SIM_REQUIRED_FILES = ('inp.5', 'DECAY.dat')  # XSECTION.dat lo genera el pipeline
_SPECTRUM_COLLAPS_REQUIRED_FILES = ('COLL.inp', 'XSBL.dat')

# chains.exe: misma convención fija que collaps.exe (F9 del BACKLOG, no
# configurable vía suite_config.json).
_CHAINS_EXE_NAME = chains_analysis.CHAINS_EXE_NAME

# Recordados por /api/run para que /api/run/status pueda informar si el
# fichero de salida (fort.6) quedó generado tras el último run individual
# (botón "Abrir en Fort Analyzer" del R3 — el runner común no conoce este
# concepto, así que el chequeo vive aquí).
_last_run_workdir: str | None = None
_last_run_output_file: str | None = None


def _suite_dir() -> Path | None:
    d = Path(__file__).resolve().parent.parent / 'acab_suite'
    return d if d.is_dir() else None


def _local_run_config_path() -> Path:
    return Path(__file__).resolve().parent / 'run_config.json'


def _load_runner_config() -> dict:
    """Lee la config del runner: acab_suite/suite_config.json (clave 'runner'
    de esta app) o, si no existe esa carpeta/entrada, el fichero local
    run_config.json."""
    cfg = dict(_DEFAULT_RUNNER_CONFIG)
    suite = _suite_dir()
    if suite is not None:
        try:
            with open(suite / 'suite_config.json', 'r', encoding='utf-8') as f:
                suite_cfg = json.load(f)
            for entry in suite_cfg.get('apps', []):
                if entry.get('name') == APP_NAME:
                    cfg.update(entry.get('runner') or {})
                    return cfg
        except (OSError, json.JSONDecodeError):
            pass
    try:
        with open(_local_run_config_path(), 'r', encoding='utf-8') as f:
            cfg.update(json.load(f))
    except (OSError, json.JSONDecodeError):
        pass
    return cfg


def _save_runner_config(partial: dict) -> dict:
    """Persiste (merge) los campos de *partial* reconocidos en la config del
    runner, en la misma ubicación que _load_runner_config()."""
    cfg = _load_runner_config()
    cfg.update({k: v for k, v in partial.items() if k in _DEFAULT_RUNNER_CONFIG})

    suite = _suite_dir()
    if suite is not None:
        suite_cfg_path = suite / 'suite_config.json'
        try:
            with open(suite_cfg_path, 'r', encoding='utf-8') as f:
                suite_cfg = json.load(f)
            for entry in suite_cfg.get('apps', []):
                if entry.get('name') == APP_NAME:
                    entry['runner'] = cfg
                    with open(suite_cfg_path, 'w', encoding='utf-8') as f:
                        json.dump(suite_cfg, f, indent=2, ensure_ascii=False)
                    return cfg
        except (OSError, json.JSONDecodeError):
            pass

    with open(_local_run_config_path(), 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return cfg


@app.route('/api/run/config', methods=['GET', 'POST'])
def api_run_config():
    if request.method == 'GET':
        return jsonify({'ok': True, 'config': _load_runner_config()})
    payload = request.get_json(force=True, silent=True) or {}
    cfg = _save_runner_config(payload)
    return jsonify({'ok': True, 'config': cfg})


@app.route('/api/run', methods=['POST'])
def api_run():
    payload = request.get_json(force=True, silent=True) or {}
    workdir = (payload.get('workdir') or '').strip()
    save_current = bool(payload.get('save_current', True))
    overwrite = bool(payload.get('overwrite', False))

    if not workdir:
        return jsonify({'error': 'Debes indicar el directorio de trabajo.'}), 422
    wd_path = Path(workdir)
    if not wd_path.is_dir():
        return jsonify({'error': f'El directorio de trabajo no existe: {workdir}'}), 422

    cfg = _load_runner_config()
    exe_name = (payload.get('exe_name') or cfg['exe_name']).strip()
    timeout_s = payload.get('timeout_s') or cfg['timeout_s']
    required_files = payload.get('required_files') or cfg['required_files']
    output_file = payload.get('output_file') or cfg['output_file']

    exe_path = wd_path / exe_name
    if not exe_path.is_file():
        return jsonify({'error':
            f'No se encontró el ejecutable "{exe_name}" en el directorio de '
            'trabajo.'}), 422

    if save_current:
        try:
            content = _write_inp5(payload.get('data', {}))
            (wd_path / 'inp.5').write_text(content, encoding='utf-8')
        except Exception as exc:
            return jsonify({'error': f'No se pudo guardar inp.5: {exc}'}), 422

    missing = [f for f in required_files if not (wd_path / f).exists()]
    if missing:
        return jsonify({'error':
            'Faltan ficheros requeridos en el directorio de trabajo: '
            + ', '.join(missing)}), 422

    output_path = wd_path / output_file
    if output_path.exists() and not overwrite:
        return jsonify({
            'error': f'Ya existe un fichero de salida previo ({output_file}) '
                     'en el directorio de trabajo. Confirma para sobrescribir.',
            'needs_overwrite': True,
        }), 422

    try:
        runner.start(cmd=[str(exe_path)], workdir=str(wd_path),
                     timeout_s=float(timeout_s))
    except runner.RunnerBusyError as exc:
        return jsonify({'error': str(exc)}), 409

    # Recordar workdir/ejecutable/timeout usados para la próxima vez.
    _save_runner_config({
        'default_workdir': workdir,
        'exe_name': exe_name,
        'timeout_s': timeout_s,
    })

    global _last_run_workdir, _last_run_output_file
    _last_run_workdir = str(wd_path)
    _last_run_output_file = output_file

    return jsonify({'ok': True})


@app.route('/api/run/status', methods=['GET'])
def api_run_status():
    status = runner.status()
    # Enriquecer el estado single ya terminado con si el fichero de salida
    # (fort.6) quedó generado, para que la UI pueda ofrecer el botón
    # "Abrir en Fort Analyzer" (Fase R3).
    if (status.get('mode') == 'single' and not status.get('running')
            and status.get('returncode') == 0 and _last_run_workdir):
        output_path = Path(_last_run_workdir) / (_last_run_output_file or 'fort.6')
        status['output_exists'] = output_path.is_file()
        status['workdir'] = _last_run_workdir
    # Enriquecer el estado batch con la carpeta raíz del barrido (botón
    # "Abrir en Fort Analyzer" del R4 — el runner común no conoce este
    # concepto, así que el chequeo vive aquí, igual que para single) y, si es
    # un barrido espectral, la lista de pasos del pipeline (D7) para que la
    # UI traduzca step_index/step_type en la etiqueta del paso en curso.
    if status.get('mode') == 'batch':
        if _last_batch_root:
            status['root'] = _last_batch_root
        status['pipeline_steps'] = _last_batch_pipeline_steps
    return jsonify({'ok': True, 'status': status})


@app.route('/api/run/cancel', methods=['POST'])
def api_run_cancel():
    runner.cancel()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Ejecución en cola del barrido (Fase R4 del runbook runner v2)
# ---------------------------------------------------------------------------

_last_batch_root: str | None = None
# Etiquetas de los pasos del pipeline D7 del último batch lanzado, en orden de
# step_index (None si el batch no es un barrido espectral). Ver api_run_status.
_last_batch_pipeline_steps: list[str] | None = None


def _read_sweep_manifest(root_p: Path) -> dict:
    manifest_path = root_p / 'sweep_manifest.json'
    if not manifest_path.is_file():
        raise FileNotFoundError(f'No se encontró sweep_manifest.json en {root_p}.')
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _build_spectrum_pipeline_jobs(root_p: Path, folders: list[str],
                                  acab_exe_name: str, collaps_exe_name: str) -> list[dict]:
    """Jobs del barrido espectral: pipeline D7 por simulación (runner v3).

    1) run collaps.exe con cwd=<sim>/collaps; 2) copy XSECTION.dat →
    <sim>/XSECTION.dat; 3) run acab.exe con cwd=<sim>; 4) check_flux sobre
    <sim>/collaps/FLUX.inf.
    """
    jobs = []
    for folder in folders:
        wd = root_p / folder
        collaps_dir = wd / 'collaps'
        jobs.append({
            'workdir': str(wd),
            'steps': [
                {'type': 'run', 'cmd': [str(collaps_dir / collaps_exe_name)],
                 'cwd': str(collaps_dir)},
                {'type': 'copy', 'src': str(collaps_dir / 'XSECTION.dat'),
                 'dst': str(wd / 'XSECTION.dat')},
                {'type': 'run', 'cmd': [str(wd / acab_exe_name)], 'cwd': str(wd)},
                {'type': 'check_flux', 'path': str(collaps_dir / 'FLUX.inf')},
            ],
        })
    return jobs


@app.route('/api/run/batch', methods=['POST'])
def api_run_batch():
    payload = request.get_json(force=True, silent=True) or {}
    root = (payload.get('root') or '').strip()
    overwrite = bool(payload.get('overwrite', False))
    folders = payload.get('folders')

    if not root:
        return jsonify({'error': 'Debes indicar la carpeta raíz del barrido.'}), 422
    root_p = Path(root)
    if not root_p.is_dir():
        return jsonify({'error': f'La carpeta raíz no existe: {root}'}), 422

    # El manifest se lee siempre que exista (best-effort si folders viene
    # explícito) para saber el sweep_type y así decidir el pipeline de
    # ejecución (D7, espectral vs tipos 1-3). Si folders no viene, el
    # manifest es obligatorio (404 si falta, como antes).
    manifest = None
    if not folders:
        try:
            manifest = _read_sweep_manifest(root_p)
        except FileNotFoundError as exc:
            return jsonify({'error': str(exc)}), 404
        except (OSError, json.JSONDecodeError) as exc:
            return jsonify({'error': f'No se pudo leer sweep_manifest.json: {exc}'}), 422
        folders = [sim['folder'] for sim in manifest.get('simulations', [])]
    else:
        try:
            manifest = _read_sweep_manifest(root_p)
        except (OSError, json.JSONDecodeError, FileNotFoundError):
            manifest = None

    if not folders:
        return jsonify({'error': 'El barrido no tiene simulaciones que ejecutar.'}), 422

    is_spectrum = bool(manifest) and manifest.get('sweep_type') == 'spectrum'

    cfg = _load_runner_config()
    exe_name = cfg['exe_name']
    timeout_s = cfg['timeout_s']
    output_file = cfg['output_file']

    missing_dirs, missing_files, existing_outputs = [], {}, []
    if is_spectrum:
        for folder in folders:
            wd = root_p / folder
            if not wd.is_dir():
                missing_dirs.append(folder)
                continue
            missing = [f for f in (exe_name, *_SPECTRUM_SIM_REQUIRED_FILES)
                      if not (wd / f).exists()]
            collaps_dir = wd / 'collaps'
            missing += [f'collaps/{f}' for f
                       in (_COLLAPS_EXE_NAME, *_SPECTRUM_COLLAPS_REQUIRED_FILES)
                       if not (collaps_dir / f).exists()]
            if missing:
                missing_files[folder] = missing
            if (wd / output_file).exists():
                existing_outputs.append(folder)
    else:
        required_files = cfg['required_files']
        for folder in folders:
            wd = root_p / folder
            if not wd.is_dir():
                missing_dirs.append(folder)
                continue
            missing = [f for f in required_files if not (wd / f).exists()]
            if missing:
                missing_files[folder] = missing
            if (wd / output_file).exists():
                existing_outputs.append(folder)

    if missing_dirs:
        return jsonify({'error':
            'No existen estas subcarpetas del barrido: ' + ', '.join(missing_dirs)}), 422
    if missing_files:
        detail = '; '.join(f'{f}: {", ".join(fs)}' for f, fs in missing_files.items())
        return jsonify({'error':
            'Faltan ficheros requeridos en algunas subcarpetas: ' + detail}), 422
    if existing_outputs and not overwrite:
        return jsonify({
            'error': f'Ya existe un fichero de salida previo ({output_file}) en '
                     f'{len(existing_outputs)} subcarpeta(s). Confirma para sobrescribir.',
            'needs_overwrite': True,
            'existing_outputs': existing_outputs,
        }), 422

    results_path = str(root_p / 'batch_results.json')

    if is_spectrum:
        jobs = _build_spectrum_pipeline_jobs(root_p, folders, exe_name, _COLLAPS_EXE_NAME)
        cmd_template = ''  # no usado: cada job del pipeline lleva sus propios 'steps'
    else:
        jobs = [{'workdir': str(root_p / folder)} for folder in folders]
        # Cada subcarpeta lleva su propia copia del ejecutable (la sweep copia el
        # contenido de la carpeta base). El comando se formatea por-job con el
        # workdir de cada uno (soporte '{workdir}' de runner.start_batch); se
        # entrecomilla en Windows para tolerar espacios en la ruta (en POSIX las
        # comillas formarían parte literal del nombre de fichero, así que no se
        # añaden).
        exe_join = str(Path('{workdir}') / exe_name)
        cmd_template = f'"{exe_join}"' if os.name == 'nt' else exe_join

    try:
        runner.start_batch(jobs=jobs, cmd_template=cmd_template,
                           timeout_s_per_sim=float(timeout_s),
                           results_path=results_path)
    except runner.RunnerBusyError as exc:
        return jsonify({'error': str(exc)}), 409

    global _last_batch_root, _last_batch_pipeline_steps
    _last_batch_root = str(root_p)
    _last_batch_pipeline_steps = (
        ['collaps', 'copy', 'acab', 'check_flux'] if is_spectrum else None)

    return jsonify({'ok': True, 'n': len(folders), 'root': str(root_p)})


# ---------------------------------------------------------------------------
# Ejecución del análisis de cadenas (F9 del BACKLOG, Fase 3)
#
# Pipeline propio (no reutiliza /api/run/batch: el manifest no es un
# sweep_manifest.json): tape22 -> tape24 (runs de ACAB compartidos) seguidos
# de un job por isótopo (ACAB monoisotópico + copiar fort.22/24 + CHAINS con
# redirección stdin/stdout). Ver chains_analysis.build_chains_pipeline_jobs
# y acab_suite/README.md "Invocación de los códigos".
# ---------------------------------------------------------------------------

@app.route('/api/chains-analysis/run', methods=['POST'])
def api_chains_analysis_run():
    payload = request.get_json(force=True, silent=True) or {}
    root = (payload.get('root') or '').strip()
    overwrite = bool(payload.get('overwrite', False))

    if not root:
        return jsonify({'error': 'Debes indicar la carpeta raíz del análisis.'}), 422
    root_p = Path(root)
    if not root_p.is_dir():
        return jsonify({'error': f'La carpeta raíz no existe: {root}'}), 422

    manifest_path = root_p / 'chains_manifest.json'
    if not manifest_path.is_file():
        return jsonify({'error':
            f'No se encontró chains_manifest.json en {root}.'}), 404
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return jsonify({'error': f'No se pudo leer chains_manifest.json: {exc}'}), 422

    cfg = _load_runner_config()
    acab_exe_name = cfg['exe_name']
    timeout_s = cfg['timeout_s']

    tape22_dir = root_p / manifest['tape22_folder']
    tape24_dir = root_p / manifest['tape24_folder']
    isotopes = manifest.get('isotopes') or []

    required_dirs = [tape22_dir, tape24_dir]
    for iso in isotopes:
        required_dirs += [root_p / iso['iso_folder'], root_p / iso['chains_folder']]
    missing_dirs = [str(d.relative_to(root_p)) for d in required_dirs if not d.is_dir()]
    if missing_dirs:
        return jsonify({'error': 'No existen estas subcarpetas del análisis: '
                                 + ', '.join(missing_dirs)}), 422

    missing_files: dict[str, list[str]] = {}
    for d, needed in ((tape22_dir, (acab_exe_name, 'inp.5')),
                      (tape24_dir, (acab_exe_name, 'inp.5'))):
        miss = [f for f in needed if not (d / f).exists()]
        if miss:
            missing_files[str(d.relative_to(root_p))] = miss
    for iso in isotopes:
        iso_dir = root_p / iso['iso_folder']
        chains_dir = root_p / iso['chains_folder']
        miss = [f for f in (acab_exe_name, 'inp.5') if not (iso_dir / f).exists()]
        if miss:
            missing_files[str(iso_dir.relative_to(root_p))] = miss
        miss = [f for f in (_CHAINS_EXE_NAME, 'input_chain.txt') if not (chains_dir / f).exists()]
        if miss:
            missing_files[str(chains_dir.relative_to(root_p))] = miss
    if missing_files:
        detail = '; '.join(f'{f}: {", ".join(fs)}' for f, fs in missing_files.items())
        return jsonify({'error': 'Faltan ficheros requeridos: ' + detail}), 422

    existing_outputs = [
        str((root_p / iso['iso_folder']).relative_to(root_p)) for iso in isotopes
        if (root_p / iso['iso_folder'] / 'fort.6').exists()
    ]
    if existing_outputs and not overwrite:
        return jsonify({
            'error': f'Ya existe un fort.6 previo en {len(existing_outputs)} carpeta(s). '
                     'Confirma para sobrescribir.',
            'needs_overwrite': True,
            'existing_outputs': existing_outputs,
        }), 422

    jobs = chains_analysis.build_chains_pipeline_jobs(
        root_p, manifest, acab_exe_name, _CHAINS_EXE_NAME)
    results_path = str(root_p / 'chains_batch_results.json')

    try:
        runner.start_batch(jobs=jobs, cmd_template='',
                           timeout_s_per_sim=float(timeout_s),
                           results_path=results_path)
    except runner.RunnerBusyError as exc:
        return jsonify({'error': str(exc)}), 409

    global _last_batch_root, _last_batch_pipeline_steps
    _last_batch_root = str(root_p)
    # Etiquetas orientativas: válidas para los jobs por isótopo (4 pasos);
    # los jobs de tapes tienen un único paso 'run' que también es 'acab'
    # (step_index 0 coincide en ambos casos).
    _last_batch_pipeline_steps = ['acab', 'copy', 'copy', 'chains']

    return jsonify({'ok': True, 'n': len(jobs), 'root': str(root_p)})


# ---------------------------------------------------------------------------
# Writer:  dict  →  ACAB .5 free-format text
# ---------------------------------------------------------------------------

def _sci(v, prec: int = 6) -> str:
    """Float → ACAB scientific notation string, e.g. 1.000000E-25."""
    try:
        return f'{float(v):.{prec}E}'
    except (TypeError, ValueError):
        return f'0.{"0" * prec}E+00'


def _floats_block(vals, per_line: int = 5, field: str = '') -> str:
    """Render a list of floats, *per_line* values per output line.

    Raises ValueError on an empty list instead of silently emitting a
    spurious ``0.000000E+00`` token that would corrupt the file.
    """
    rows, chunk = [], []
    for v in (vals or []):
        chunk.append(_sci(v))
        if len(chunk) == per_line:
            rows.append(' '.join(chunk))
            chunk = []
    if chunk:
        rows.append(' '.join(chunk))
    if not rows:
        raise ValueError(
            f"Lista de reales vacía al escribir el campo '{field or 'desconocido'}': "
            "el fichero resultante sería inválido."
        )
    return '\n'.join(rows)


def _ints(vals) -> str:
    return ' '.join(str(int(v)) for v in (vals or []))


def _gi(d: dict, k: str, default: int = 0) -> int:
    """Safe int getter from dict (handles None)."""
    v = (d or {}).get(k)
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _write_inp5(data: dict) -> str:
    L: list[str] = []
    add = L.append
    cmt = lambda s: add(f'<{s}')

    b1  = data.get('block1') or {}
    b2  = data.get('block2') or {}
    b3  = data.get('block3')
    b4  = data.get('block4') or {}
    b5  = data.get('block5') or []
    b6  = data.get('block6') or []
    b78 = data.get('blocks78') or {}
    b9  = data.get('block9') or {}
    b10 = data.get('block10') or {}
    b11 = data.get('block11') or {}
    b12 = data.get('block12') or {}
    b13 = data.get('block13')
    b14 = data.get('block14')

    # User comments per block (optional free text prefixed with '<')
    _user_cmts = data.get('comments') or {}

    def user_cmt(key: str) -> None:
        text = (_user_cmts.get(key) or '').strip()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                add(f'< {stripped}')

    # shortcuts from block1
    ige   = _gi(b1, 'IGE',  4)
    izm   = _gi(b1, 'IZM',  1)
    im    = _gi(b1, 'IM',   1)
    jm    = _gi(b1, 'JM',   0)
    infd  = _gi(b1, 'INFD', 0)
    nogg  = _gi(b1, 'NOGG', 1)
    jto   = _gi(b1, 'JTO',  0)
    iflu  = _gi(b1, 'IFLU', 0)
    iunc  = _gi(b1, 'IUNC', 0)

    # ── Block #1 ──────────────────────────────────────────────────────────
    user_cmt('block1')
    add(b1.get('title') or 'ACAB input file')
    cmt('Block #1, card #2')
    add(f" {_gi(b1,'IUNC')}  IUNC")
    cmt('Block #1, card #3')
    k3 = ['ITMAX','IZMAX','MPCTAB','IR','JTO','NTABLE','MSTAR',
           'INPT','INFD','NOGG','NGRP','IGRP','IGE','IZM','IM',
           'JM','IFLU','IPRT','ILIB','IRAD','IPUN']
    add(' ' + ' '.join(str(_gi(b1, k)) for k in k3))

    # ── Block #2 ──────────────────────────────────────────────────────────
    user_cmt('block2')
    cmt('Block #2, card #1  XRR')
    add(_floats_block(b2.get('XRR') or ([1.0] * izm + [1.0]), field='XRR'))

    if jm > 0:
        cmt('Block #2, card #2  YZT')
        add(_floats_block(b2.get('YZT') or [0.0] * (jm + 1), field='YZT'))

    cmt('Block #2, card #3  MA')
    add(' ' + _ints(b2.get('MA') or [1] * (im * jm if jm > 0 else im)))

    cmt('Block #2, card #4  NUCZO')
    nuczo = list(b2.get('NUCZO') or [1] * izm)
    add(' ' + _ints(nuczo))

    if infd > 0:
        cmt('Block #2, card #5  ISOZO')
        add(' ' + _ints(b2.get('ISOZO') or [0] * izm))

    cmt('Block #2, card #6  EGRP')
    add(_floats_block(b2.get('EGRP') or [1e-6, 1e-11], per_line=8, field='EGRP'))

    cmt('Block #2, card #7  CUTOFF')
    add(' '.join(_sci(v) for v in (b2.get('CUTOFF') or [0.0] * 6)))

    if jto == 1:
        cmt('Block #2, card #8  NTO')
        add(' '.join(str(int(v)) for v in (b2.get('NTO') or [0] * 18)))

    # ── Block #3 ──────────────────────────────────────────────────────────
    if iflu == 1 and b3:
        user_cmt('block3')
        cmt('Block #3  FLUX')
        add(_floats_block(b3.get('FLUX') or [0.0], per_line=6, field='FLUX'))

    # ── Block #4 ──────────────────────────────────────────────────────────
    cmt('Block #4  Restart option')
    add(f" {_gi(b4,'IREST')}  IREST")

    # ── Block #5 ──────────────────────────────────────────────────────────
    for i, zone in enumerate(b5):
        if i == 0:
            user_cmt('block5')
        cmt(f'Block #5  Initial material composition  zone {i + 1}')
        add(_ints(zone.get('INUCL') or []))
        add(_floats_block(zone.get('XCOMP') or [], field=f'XCOMP zona {i + 1}'))

    # ── Block #6 ──────────────────────────────────────────────────────────
    if infd > 0:
        for i, zone in enumerate(b6):
            if i == 0:
                user_cmt('block6')
            cmt(f'Block #6  Continuous feed  zone {i + 1}')
            add(_ints(zone.get('IDNUM') or []))
            add(_floats_block(zone.get('XFEED') or [], field=f'XFEED zona {i + 1}'))

    # ── Blocks #7/#8 ──────────────────────────────────────────────────────
    sets = b78.get('sets') or []
    if sets:
        user_cmt('blocks78')
        cmt('Blocks #7,#8  Irradiation and cooling temporal history')
        for i, s in enumerate(sets):
            if i > 0:
                cmt('continue')
            add(f" {_gi(s,'MMN'):2d} {_gi(s,'MOUT'):2d}   {_gi(s,'NGO')} "
                f"{_gi(s,'MSUB'):2d}  {_gi(s,'IUNIT')} {_gi(s,'MFEED')}"
                f"   {_gi(s,'IOUT')} {_gi(s,'IPLOT')}   ")
            add(_floats_block(s.get('TIMES') or [], field=f'TIMES set {i + 1}'))

    # ── Block #9 ──────────────────────────────────────────────────────────
    user_cmt('block9')
    cmt('Block #9 ERR XNORM')
    add(f" {_sci(b9.get('ERR', 1e-25))} {_sci(b9.get('XNORM', 1.0))}")

    # ── Block #10 ─────────────────────────────────────────────────────────
    user_cmt('block10')
    cmt('Block #10 Fission product inventory')
    add(f" {_gi(b10,'IGFP')}   {_gi(b10,'IWFYD')}   {_gi(b10,'IFORT96')}")

    # ── Block #11 ─────────────────────────────────────────────────────────
    user_cmt('block11')
    cmt('Block #11 Type of run')
    k11 = ['IWP','IMTX','IWDR','IDOSE','IPHCUT',
            'IDHEAT','IOFFSD','ICEDE','INEMISS','IDAMAGE']
    add(' ' + ' '.join(str(_gi(b11, k)) for k in k11)
        + '  IWP IMTX IWDR IDOSE IPHCUT IDHEAT IOFFSD ICEDE INEMISS IDAMAGE')

    idose  = _gi(b11, 'IDOSE')
    ioffsd = _gi(b11, 'IOFFSD')
    nopul  = _gi(b11, 'NOPUL')
    ntseq  = _gi(b11, 'NTSEQ')
    notts  = _gi(b11, 'NOTTS', 1)
    nvfl   = _gi(b11, 'NVFL')

    if idose == 1:
        do = b11.get('dose_output') or {}
        add(f" {_gi(do,'PH')} {_gi(do,'BREM')} {_gi(do,'TOT')} {_gi(do,'RHOR')}"
            f"  PH BREM TOT RHOR")

    if ioffsd != 0:
        add(_floats_block(b11.get('DISTAN') or [], field='DISTAN'))
        ilifr = _gi(b11, 'ILIFR')
        add(f" {_sci(b11.get('PODE') or 0)} {ilifr}")
        if ilifr != 0:
            for el, fl in (b11.get('liberation_fracs') or []):
                add(f' {int(el)} {_sci(fl)}')

    add(f' {nopul} {ntseq} {notts} {nvfl}  NOPUL NTSEQ NOTTS NVFL')

    if nvfl == 1:
        add(_floats_block(b11.get('FVAR') or [1.0] * notts, field='FVAR'))

    if nopul != 0:
        add(f" {_gi(b11,'NMULT')}  NMULT")

    # ── Block #12 ─────────────────────────────────────────────────────────
    cmt('Block #12 Instantaneous feed of material')
    iifd = _gi(b12, 'IIFD')
    add(f' {iifd}  IIFD')

    if iifd != 0:
        nmaifd  = _gi(b12, 'NMAIFD')
        irmaifd = list(b12.get('IRMAIFD') or [])
        add(str(nmaifd))
        add(_ints(irmaifd))
        if 3 in irmaifd:
            add(str(_gi(b12, 'NISFDTP')))
        if 1 in irmaifd and b12.get('element_feed'):
            ef = b12['element_feed']
            add(str(_gi(ef, 'NELFD')))
            add(_ints(ef.get('IELIFD') or []))
            add(_floats_block(ef.get('XCOMEFD') or [], field='XCOMEFD'))
        if 2 in irmaifd and b12.get('isotope_feed'):
            isf = b12['isotope_feed']
            add(str(_gi(isf, 'NISFD')))
            add(_ints(isf.get('IISIFD') or []))
            add(_floats_block(isf.get('XCOMISFD') or [], field='XCOMISFD'))
        if iifd == 1:
            add(_ints(b12.get('ITFDSET') or [0] * notts))
            add(_ints(b12.get('IMASET')  or [0] * notts))
        elif iifd == 2:
            nfdset = b12.get('NFDSET') or [0] * notts
            add(_ints(nfdset))
            for s in (b12.get('feed_schedule') or []):
                add(_ints(s.get('ITSFDSET') or []))
                add(_ints(s.get('IMASSET')  or []))

    # ── Block #13 / #14 ───────────────────────────────────────────────────
    if iunc == 0 and b13:
        user_cmt('block13')
        cmt('Block #13 Output control')
        ncyo = _gi(b13, 'NCYO')
        ifso = _gi(b13, 'IFSO', 1)
        add(f' {ncyo}   {ifso}  NCYO IFSO')
        if ncyo != 0:
            add(_ints(b13.get('ICYO') or []))
        add(_ints(b13.get('ITSO') or [1] * notts))
    elif iunc == 1 and b14:
        user_cmt('block14')
        cmt('Block #14 Monte Carlo uncertainty')
        k14 = ['NMOHI', 'NTIMES', 'NCYU', 'IFSU', 'NNUCU']
        add(' '.join(str(_gi(b14, k)) for k in k14))
        if _gi(b14, 'NCYU') != 0:
            add(_ints(b14.get('ICYU') or []))
        itsu = b14.get('ITSU') or [0] * notts
        add(_ints(itsu))
        for tidx in (b14.get('time_indices') or []):
            add(_ints(tidx))
        add(_ints(b14.get('INUCU') or []))

    return '\n'.join(L) + '\n'


# ---------------------------------------------------------------------------
# Default data (simple 1-zone 3D-MC case, similar to examples/inp.5)
# ---------------------------------------------------------------------------

def _default_data() -> dict:
    return {
        'block1': {
            'title': 'Nuevo fichero ACAB',
            'IUNC': 0,
            'ITMAX': 2232, 'IZMAX': 250000,
            'MPCTAB': 0, 'IR': 0, 'JTO': 0, 'NTABLE': 0, 'MSTAR': 1,
            'INPT': 1, 'INFD': 0,
            'NOGG': 1, 'NGRP': 1, 'IGRP': 0,
            'IGE': 4, 'IZM': 1, 'IM': 1, 'JM': 0,
            'IFLU': 1, 'IPRT': 0, 'ILIB': 0, 'IRAD': 0, 'IPUN': 0,
        },
        'block2': {
            'XRR': [1.0, 1.0], 'YZT': None,
            'MA': [1], 'NUCZO': [1], 'ISOZO': None,
            'EGRP': [1e-6, 1e-11], 'CUTOFF': [0.0] * 6, 'NTO': None,
        },
        'block3':  {'FLUX': [1.0e10]},
        'block4':  {'IREST': 0},
        'block5':  [{'INUCL': [10000], 'XCOMP': [1.0e-2]}],
        'block6':  None,
        'blocks78': {
            'sets': [{
                'MMN': 10, 'MOUT': 10, 'NGO': 0, 'MSUB': 0,
                'IUNIT': 3, 'MFEED': 0, 'IOUT': 1, 'IPLOT': 0,
                'TIMES': [2.4, 4.8, 7.2, 9.6, 12.0, 14.4, 16.8, 19.2, 21.6, 24.0],
            }],
            'times': [[t, 1] for t in
                      [2.4, 4.8, 7.2, 9.6, 12.0, 14.4, 16.8, 19.2, 21.6, 24.0]],
        },
        'block9':  {'ERR': 1e-25, 'XNORM': 1.0},
        'block10': {'IGFP': 0, 'IWFYD': 0, 'IFORT96': 0},
        'block11': {
            'IWP': 1, 'IMTX': 0, 'IWDR': 0, 'IDOSE': 0, 'IPHCUT': 0,
            'IDHEAT': 0, 'IOFFSD': 0, 'ICEDE': 0, 'INEMISS': 0, 'IDAMAGE': 0,
            'dose_output': None, 'DISTAN': None, 'PODE': None, 'ILIFR': None,
            'liberation_fracs': None,
            'NOPUL': 0, 'NTSEQ': 0, 'NOTTS': 1, 'NVFL': 0,
            'FVAR': None, 'NMULT': None,
        },
        'block12': {
            'IIFD': 0, 'NMAIFD': None, 'IRMAIFD': None, 'NISFDTP': None,
            'element_feed': None, 'isotope_feed': None,
            'ITFDSET': None, 'IMASET': None, 'NFDSET': None, 'feed_schedule': None,
        },
        'block13': {'NCYO': 0, 'IFSO': 1, 'ICYO': None, 'ITSO': [1]},
        'block14': None,
        'comments': {},
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import argparse
    import os

    cli = argparse.ArgumentParser(description='ACAB inp File Configurator')
    cli.add_argument('--port', type=int,
                     default=int(os.environ.get('ACAB_INP_PORT', 5000)),
                     help='Puerto de escucha (por defecto: 5000 o variable ACAB_INP_PORT)')
    cli.add_argument('--no-browser', action='store_true',
                     help='No abrir el navegador al arrancar (lo usa suite_launcher.py; '
                          'equivale a la variable ACAB_SUITE_NO_BROWSER=1)')
    args = cli.parse_args()

    from waitress import serve
    if not args.no_browser and not os.environ.get('ACAB_SUITE_NO_BROWSER'):
        Timer(1.2, lambda: webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
    serve(app, host='127.0.0.1', port=args.port)
