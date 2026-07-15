"""sweep_manifest_view.py — Vista de solo lectura de un barrido ya generado
(U6 del BACKLOG): lee sweep_manifest.json (y, si existe, batch_results.json)
de una carpeta raíz y construye la información que consume la pestaña
"Barrido" para CONSULTAR un barrido sin editarlo ni ejecutarlo.

Compatibilidad hacia atrás (trampa principal de U6): manifests anteriores a
C4 no tienen `excluded_base_files`; los defaults de abajo (`.get(..., ...)`)
cubren esa y cualquier otra clave ausente en barridos viejos -- la vista
nunca rompe con un manifest antiguo, solo muestra menos información.
"""

from __future__ import annotations

import json
from pathlib import Path


class ManifestCorruptError(Exception):
    """sweep_manifest.json existe pero no es JSON válido."""


def _sim_value_label(sweep_type: str, params: dict) -> str | None:
    """Etiqueta legible del valor barrido en una simulación.

    Criterio compartido con la pestaña Optimización del analyzer (U4): en el
    barrido espectral el identificador de una simulación es el NOMBRE del
    espectro, nunca un volcado de parámetros. Devuelve None si no se puede
    derivar (manifest viejo sin el campo esperado) -- el llamador cae
    entonces al nombre de carpeta, nunca a un dump de `params`.
    """
    if sweep_type == 'spectrum':
        esp = params.get('espectro')
        return esp if isinstance(esp, str) and esp.strip() else None
    if sweep_type == 'flux':
        if 'phi' in params:
            return f"φ={params['phi']}"
        if 'XNORM' in params:
            return f"XNORM={params['XNORM']}"
        return None
    if sweep_type == 'mass':
        if 'mass' in params:
            return f"{params['mass']} g"
        return None
    if sweep_type == 'time':
        parts = []
        if params.get('t_irr_fin') is not None:
            parts.append(f"T_irr={params['t_irr_fin']}h")
        if params.get('t_cool_fin') is not None:
            parts.append(f"T_cool={params['t_cool_fin']}h")
        return ', '.join(parts) if parts else None
    return None


def _read_json_or_none(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def build_manifest_view(root_p: Path) -> dict:
    """Construye la vista de solo lectura de un barrido en `root_p`.

    Lanza FileNotFoundError si no hay sweep_manifest.json y
    ManifestCorruptError si existe pero no es JSON válido. No escribe nada.
    """
    manifest_path = root_p / 'sweep_manifest.json'
    if not manifest_path.is_file():
        raise FileNotFoundError(str(manifest_path))
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestCorruptError(str(exc)) from exc

    sweep_type = manifest.get('sweep_type') or ''
    sims_raw = manifest.get('simulations') or []

    batch_results = _read_json_or_none(root_p / 'batch_results.json')
    jobs_by_folder = {}
    if batch_results:
        for job in (batch_results.get('jobs') or []):
            folder = Path(job.get('workdir') or '').name
            if folder:
                jobs_by_folder[folder] = job

    simulations = []
    for sim in sims_raw:
        folder = sim.get('folder') or ''
        params = sim.get('params') or {}
        job = jobs_by_folder.get(folder)
        simulations.append({
            'folder': folder,
            'params': params,
            'value_label': _sim_value_label(sweep_type, params),
            'fort6_exists': (root_p / folder / 'fort.6').is_file(),
            'estado': job.get('estado') if job else None,
        })

    return {
        'root': str(root_p),
        'sweep_type': sweep_type,
        'description': manifest.get('description') or '',
        'fixed_params': manifest.get('fixed_params') or {},
        'excluded_base_files': manifest.get('excluded_base_files') or [],
        'n': manifest.get('n', len(simulations)),
        'timestamp': manifest.get('timestamp'),
        'simulations': simulations,
        'has_batch_results': batch_results is not None,
        'batch_summary': (batch_results or {}).get('resumen'),
    }
