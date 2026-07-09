"""app.py — COLLAPS COLL.inp File Configurator web application (Flask).

Arranque:
    python app.py             # puerto por defecto: 5002
    python app.py --port 8080
    PORT=8080 python app.py
Abre automáticamente http://127.0.0.1:<puerto> en el navegador por defecto.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import tempfile
import webbrowser
from pathlib import Path
from threading import Timer

from flask import Flask, jsonify, render_template, request, send_file

import runner
from collaps_parser import COLLAPSParser

app = Flask(__name__)

# Nombre de esta app tal como aparece en acab_suite/suite_config.json
APP_NAME = 'collaps'


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/ping')
def api_ping():
    # Fragmento común de la suite — mantener sincronizado en los 3 repos
    # (solo cambia el nombre de la app). La cabecera CORS es imprescindible:
    # el banner de las otras apps hace fetch cross-origin SOLO a este endpoint.
    resp = jsonify({'ok': True, 'app': 'collaps'})
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

    with tempfile.NamedTemporaryFile(delete=False, suffix='.inp') as tmp:
        f.save(tmp.name)
        tmp_path = Path(tmp.name)

    try:
        data = COLLAPSParser().read_coll_inp(tmp_path)
        return jsonify({'ok': True, 'data': data, 'filename': f.filename})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 422
    finally:
        tmp_path.unlink(missing_ok=True)


@app.route('/api/save', methods=['POST'])
def api_save():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        content = _write_coll_inp(payload.get('data', {}))
        buf = io.BytesIO(content.encode('utf-8'))
        buf.seek(0)
        fname = payload.get('filename', 'COLL.inp')
        return send_file(buf, as_attachment=True,
                         download_name=fname, mimetype='text/plain')
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/api/preview', methods=['POST'])
def api_preview():
    """Return the formatted COLL.inp content as a JSON string (no download)."""
    payload = request.get_json(force=True, silent=True) or {}
    try:
        content = _write_coll_inp(payload.get('data', {}))
        return jsonify({'ok': True, 'content': content})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 422


# ---------------------------------------------------------------------------
# Ejecución de COLLAPS (Fase R2 del runbook runner v2)
#
# Convención de la suite (acab_suite/README.md, sección "Invocación de los
# códigos"): simulaciones autocontenidas — el ejecutable vive EN el
# directorio de trabajo y se lanza sin argumentos con cwd=workdir. No hay
# ruta global de ejecutable.
# ---------------------------------------------------------------------------

_DEFAULT_RUNNER_CONFIG = {
    'exe_name': 'collaps.exe',
    'required_files': ['COLL.inp', 'XSBL.dat'],
    'output_file': 'XSECTION.dat',
    'timeout_s': 60,
    'default_workdir': '',
}


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
            content = _write_coll_inp(payload.get('data', {}))
            (wd_path / 'COLL.inp').write_text(content, encoding='utf-8')
        except Exception as exc:
            return jsonify({'error': f'No se pudo guardar COLL.inp: {exc}'}), 422

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

    return jsonify({'ok': True})


@app.route('/api/run/status', methods=['GET'])
def api_run_status():
    return jsonify({'ok': True, 'status': runner.status()})


@app.route('/api/run/cancel', methods=['POST'])
def api_run_cancel():
    runner.cancel()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Writer:  dict  →  COLLAPS COLL.inp text
# ---------------------------------------------------------------------------

def _gi(d: dict, k: str, default: int = 0) -> int:
    """Safe int getter."""
    v = (d or {}).get(k)
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _gf(d: dict, k: str, default: float = 0.0) -> float:
    """Safe float getter."""
    v = (d or {}).get(k)
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _floats_block_e125(vals, per_line: int = 6) -> str:
    """Format a list of floats as 6E12.5 FORTRAN block (12-char fields, 6 per line)."""
    rows, chunk = [], []
    for v in (vals or []):
        try:
            chunk.append(f'{float(v):12.5E}')
        except (TypeError, ValueError):
            chunk.append(f'{0.0:12.5E}')
        if len(chunk) == per_line:
            rows.append(''.join(chunk))
            chunk = []
    if chunk:
        rows.append(''.join(chunk))
    return '\n'.join(rows) if rows else f'{0.0:12.5E}'


def _write_coll_inp(data: dict) -> str:
    L: list[str] = []

    c1 = data.get('card1') or {}
    c2 = data.get('card2') or {}
    c3 = data.get('card3') or {}
    c4 = data.get('card4') or {}
    c5 = data.get('card5') or {}
    c6 = data.get('card6') or {}
    c7 = data.get('card7') or {}
    c8 = data.get('card8') or {}
    c9 = data.get('card9') or {}

    ilib   = _gi(c1, 'ILIB',  2)
    iesf   = _gi(c1, 'IESF',  2)
    ihead  = _gi(c2, 'IHEAD', 16)
    isfis  = _gi(c3, 'ISFIS', 0)
    igen   = _gi(c3, 'IGEN',  0)
    isoca  = _gi(c3, 'ISOCA', 1)
    ibest  = _gi(c3, 'IBEST', 1)
    ngroup = _gi(c5, 'NGROUP', -175)
    ff     = _gi(c5, 'FF',    0)
    nabs   = abs(ngroup)
    iunc3g = _gi(c8, 'IUNC3G', 0)
    istop  = _gi(c9, 'ISTOP', 0)

    # Card #1 — 2I4 fixed format
    L.append(f'{ilib:4d}{iesf:4d}')

    # Card #2
    L.append(f'{ihead:4d}')

    # Card #3
    L.append(f'   {isfis}   {igen}   {isoca}   {ibest}')

    # Card #4 (only when ISFIS != 0)
    if isfis != 0:
        eb1 = _gf(c4, 'EB1', 5e6)
        eb2 = _gf(c4, 'EB2', 2e5)
        L.append(f' {eb1:.3E}  {eb2:.3E}')

    # Card #5 — 2I4 fixed format (NGROUP preserves sign)
    L.append(f'{ngroup:4d}{ff:4d}')

    # Card #6 — CX energy boundaries (only when IESF == 5)
    if iesf == 5:
        cx = list(c6.get('CX') or [0.0] * (nabs + 1))
        # Pad or truncate to exactly nabs+1 values
        while len(cx) < nabs + 1:
            cx.append(0.0)
        L.append(_floats_block_e125(cx[:nabs + 1]))

    # Card #7 — FT flux values
    ft = list(c7.get('FT') or [0.0] * nabs)
    while len(ft) < nabs:
        ft.append(0.0)
    L.append(_floats_block_e125(ft[:nabs]))

    # Card #8
    L.append(f'{iunc3g:20d}')

    # Card #9
    L.append(f'{istop:20d}')

    return '\n'.join(L) + '\n'


# ---------------------------------------------------------------------------
# Default data
# ---------------------------------------------------------------------------

def _default_data() -> dict:
    """Return a minimal valid COLL.inp dataset (Vitamin-J 175g, flat spectrum)."""
    return {
        'card1': {'ILIB': 2, 'IESF': 2},
        'card2': {'IHEAD': 16},
        'card3': {'ISFIS': 0, 'IGEN': 0, 'ISOCA': 1, 'IBEST': 1},
        'card4': None,
        'card5': {'NGROUP': -175, 'FF': 0},
        'card6': None,
        'card7': {'FT': [1.0] * 175},
        'card8': {'IUNC3G': 0},
        'card9': {'ISTOP': 0},
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=None,
                        help='Puerto de escucha (por defecto: 5002 o variable PORT)')
    parser.add_argument('--no-browser', action='store_true',
                        help='No abrir el navegador al arrancar (lo usa suite_launcher.py; '
                             'equivale a la variable ACAB_SUITE_NO_BROWSER=1)')
    args = parser.parse_args()

    port = args.port or int(os.environ.get('PORT', 5002))
    url = f'http://127.0.0.1:{port}'

    from waitress import serve
    if not args.no_browser and not os.environ.get('ACAB_SUITE_NO_BROWSER'):
        Timer(1.2, lambda: webbrowser.open(url)).start()
    serve(app, host='127.0.0.1', port=port)
