"""chains_analysis.py — Generación y orquestación del análisis de
contribución por cadenas (F9 del BACKLOG): ACAB monoisotópico + tapes 22/24
+ CHAINS.

Fases 2 (generación) y 3 (jobs de ejecución) de
``acab_suite/runbook_F9_analisis_cadenas.md``. Se apoya en la misma
fontanería que el barrido paramétrico (``sweep_writer``: ``deep_merge``,
copia de la carpeta base con exclusión de salidas viejas C4) pero con
manifest PROPIO (``chains_manifest.json``, no un ``sweep_manifest.json``)
porque el dominio es distinto: dos runs de "tapes" COMPARTIDOS (mismo
blanco de referencia, sin patch de composición) + un run monoisotópico y un
run de CHAINS POR isótopo seleccionado, no N variaciones de un mismo patch.

Decisiones de diseño (ver runbook, Fase 0 y Fase 2):
  - Solo referencias de UNA zona activa (Block #5 con una única zona no
    nula) sin alimentación continua (INFD=0, Block #6): el patch
    monoisotópico sustituye ESA zona por un único nucleido y ajusta Block #2
    NUCZO de esa zona a 1. El runbook no menciona este ajuste de NUCZO
    explícitamente, pero es un invariante del formato (NUCZO fija cuántos
    INUCL/XCOMP tiene cada zona, ver docs/Block#2.md): sin él, ACAB
    desalinearía la lectura de todo lo que sigue a Block #5. Referencias
    multi-zona o con alimentación continua quedan fuera de alcance v1.
  - Conversión de unidades (confirmada empíricamente en Fase 0,
    ``tests/fixtures/chains/PROCEDENCIA.md``): XCOMP_i = C_i (át/cm³, eco
    INITIAL CONCENTRATIONS del fort.6) × 1e-24 (INPT=1 ⇒ XCOMP en
    át/barn·cm).
  - Tapes: UN ÚNICO patch de Block #11 cada uno (IWP=3 / IMTX=1) sobre la
    composición de referencia SIN modificar — son propiedades de la matriz
    de transición del blanco completo, compartidas por todos los isótopos,
    no de un isótopo aislado.
  - CHAINS: ejecutable fijo ``chains.exe`` (misma convención que
    ``collaps.exe``, no configurable), se copia desde la carpeta de
    referencia a cada ``chains_<isótopo>/`` si está presente allí.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from acab_parser import ACABParser
from chains_handler import write_chains_inp
from chains_inventory import nombre_a_zzaaas
from sweep_writer import (
    SweepError, _base_exclusion_names, _copy_base_folder, _rollback, deep_merge, dir_size,
)

MAX_ISOTOPES = 100
CHAINS_EXE_NAME = 'chains.exe'
UNIT_FACTOR_ATOMS_TO_XCOMP = 1e-24  # át/cm³ -> át/barn·cm (INPT=1, Fase 0)

_SAFE_ISO_NAME = re.compile(r'^[A-Z]{1,2}\d{1,3}M?$')


def _validate_isotope_name(name) -> str:
    n = str(name or '').strip().upper()
    if not _SAFE_ISO_NAME.match(n):
        raise SweepError(f"Nombre de isótopo no válido: {name!r}", 422)
    return n


def _isotope_folder_names(name: str) -> tuple[str, str]:
    return f'iso_{name}', f'chains_{name}'


def _single_active_zone(base_data: dict) -> tuple[int, list]:
    """Índice y NUCZO de la única zona activa de Block #5 de la referencia.

    Lanza SweepError (422) si la referencia tiene 0 o más de una zona
    activa, o alimentación continua (INFD>0, Block #6) — fuera de alcance
    v1 (ver docstring del módulo).
    """
    b1 = base_data.get('block1') or {}
    if (b1.get('INFD') or 0) > 0:
        raise SweepError(
            'El análisis de cadenas no soporta referencias con '
            'alimentación continua (INFD>0, Block #6).', 422)
    block5 = base_data.get('block5') or []
    if len(block5) != 1:
        raise SweepError(
            'El análisis de cadenas requiere una referencia con una única '
            f'zona activa en Block #5 (encontradas: {len(block5)}).', 422)
    nuczo = list((base_data.get('block2') or {}).get('NUCZO') or [])
    idx = next((i for i, v in enumerate(nuczo) if v != 0), None)
    if idx is None:
        raise SweepError('NUCZO de la referencia no tiene ninguna zona activa.', 422)
    return idx, nuczo


def _monoisotopic_patch(nuczo_idx: int, nuczo: list, zzaaas: int, xcomp: float) -> dict:
    new_nuczo = list(nuczo)
    new_nuczo[nuczo_idx] = 1
    return {
        'block2': {'NUCZO': new_nuczo},
        'block5': [{'INUCL': [zzaaas], 'XCOMP': [xcomp]}],
    }


def _tape_patch(field: str, value: int) -> dict:
    return {'block11': {field: value}}


# ---------------------------------------------------------------------------
# Preview (sin escribir nada)
# ---------------------------------------------------------------------------

def preview_chains_analysis(root, reference_folder, isotopes) -> dict:
    root_p = Path(root) if root else None
    ref_p = Path(reference_folder) if reference_folder else None
    ref_exists = bool(ref_p and ref_p.is_dir())
    ref_size = dir_size(ref_p) if ref_exists else 0
    n = len(isotopes)

    folders = ['tape22', 'tape24']
    for iso in isotopes:
        name = _validate_isotope_name((iso or {}).get('name'))
        folders += list(_isotope_folder_names(name))

    collisions = []
    if root_p and root_p.exists():
        collisions = [f for f in folders if (root_p / f).exists()]

    return {
        'root': str(root_p) if root_p else '',
        'root_exists': bool(root_p and root_p.exists()),
        'reference_exists': ref_exists,
        'reference_has_inp5': bool(ref_exists and (ref_p / 'inp.5').exists()),
        'reference_size': ref_size,
        'n_isotopes': n,
        'folders': folders,
        # tape22/tape24/iso_* copian la carpeta de referencia completa;
        # chains_* solo lleva chains.exe + input_chain.txt (coste marginal).
        'est_disk': ref_size * (2 + n),
        'collisions': collisions,
        'over_limit': n > MAX_ISOTOPES,
    }


# ---------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------

def generate_chains_analysis(payload: dict, write_fn: Callable[[dict], str]) -> dict:
    root = payload.get('root')
    reference_folder = payload.get('reference_folder')
    isotopes_in = payload.get('isotopes') or []
    ifinal_name = payload.get('ifinal')
    pcnt = payload.get('pcnt')
    nmax = payload.get('nmax')
    overwrite = bool(payload.get('overwrite'))

    if not root:
        raise SweepError('Falta la carpeta raíz del análisis.', 422)
    if not reference_folder:
        raise SweepError('Falta la carpeta de referencia.', 422)
    ref_p = Path(reference_folder)
    if not ref_p.is_dir():
        raise SweepError('La carpeta de referencia no existe o no es un directorio.', 422)
    ref_inp5 = ref_p / 'inp.5'
    if not ref_inp5.is_file():
        raise SweepError("No se encontró 'inp.5' en la carpeta de referencia.", 422)

    n = len(isotopes_in)
    if n == 0:
        raise SweepError('Selecciona al menos un isótopo inicial.', 422)
    if n > MAX_ISOTOPES:
        raise SweepError(f'{n} isótopos exceden el máximo de {MAX_ISOTOPES}.', 422)

    if not ifinal_name:
        raise SweepError('Falta el isótopo objetivo (IFINAL).', 422)
    try:
        ifinal_zzaaas = nombre_a_zzaaas(ifinal_name)
    except ValueError as exc:
        raise SweepError(str(exc), 422)

    try:
        pcnt = float(pcnt)
        nmax = int(nmax)
    except (TypeError, ValueError):
        raise SweepError('PCNT/NMAX inválidos.', 422)
    if pcnt <= 0:
        raise SweepError('PCNT debe ser positivo.', 422)
    if nmax <= 0:
        raise SweepError('NMAX debe ser positivo.', 422)

    isotopes: list[dict] = []
    seen_names: set[str] = set()
    for iso in isotopes_in:
        name = _validate_isotope_name((iso or {}).get('name'))
        if name in seen_names:
            raise SweepError(f'Isótopo repetido: {name}', 422)
        seen_names.add(name)
        try:
            c_i = float(iso.get('c_i'))
        except (TypeError, ValueError):
            raise SweepError(f'C_i inválido para {name}.', 422)
        if c_i <= 0:
            raise SweepError(f'C_i debe ser positivo para {name}.', 422)
        try:
            zzaaas = nombre_a_zzaaas(name)
        except ValueError as exc:
            raise SweepError(str(exc), 422)
        isotopes.append({'name': name, 'c_i': c_i, 'zzaaas': zzaaas})

    parser = ACABParser()
    try:
        base_data = parser.read_inp5(ref_inp5)
    except Exception as exc:  # noqa: BLE001
        raise SweepError(f'No se pudo parsear el inp.5 de referencia: {exc}', 422)

    nuczo_idx, nuczo = _single_active_zone(base_data)

    root_p = Path(root)
    folders = ['tape22', 'tape24']
    for iso in isotopes:
        folders += list(_isotope_folder_names(iso['name']))

    if not overwrite:
        collisions = [f for f in folders if (root_p / f).exists()]
        if collisions:
            raise SweepError('Ya existen estas subcarpetas (usa overwrite): '
                             + ', '.join(collisions), 409)

    root_p.mkdir(parents=True, exist_ok=True)
    exclude_names = _base_exclusion_names('')
    excluded_base_files: set[str] = set()
    created: list[Path] = []

    def _write_patched(sub: Path, patch: dict, label: str) -> None:
        merged = deep_merge(base_data, patch)
        try:
            content = write_fn(merged)
        except Exception as exc:  # noqa: BLE001
            raise SweepError(f"Error al escribir el inp.5 de '{label}': {exc}", 422)
        existed = sub.exists()
        sub.mkdir(parents=True, exist_ok=True)
        if not existed:
            created.append(sub)
        excluded_base_files.update(_copy_base_folder(ref_p, sub, exclude_names))
        (sub / 'inp.5').write_text(content, encoding='utf-8')

    try:
        # ── Tapes (compartidos, composición de referencia sin modificar) ──
        _write_patched(root_p / 'tape22', _tape_patch('IWP', 3), 'tape22')
        _write_patched(root_p / 'tape24', _tape_patch('IMTX', 1), 'tape24')

        # ── Un run monoisotópico + una carpeta CHAINS por isótopo ─────────
        chains_exe_src = ref_p / CHAINS_EXE_NAME
        for iso in isotopes:
            xcomp = iso['c_i'] * UNIT_FACTOR_ATOMS_TO_XCOMP
            iso_folder, chains_folder = _isotope_folder_names(iso['name'])
            patch = _monoisotopic_patch(nuczo_idx, nuczo, iso['zzaaas'], xcomp)
            _write_patched(root_p / iso_folder, patch, iso_folder)

            chains_sub = root_p / chains_folder
            existed = chains_sub.exists()
            chains_sub.mkdir(parents=True, exist_ok=True)
            if not existed:
                created.append(chains_sub)
            if chains_exe_src.is_file():
                shutil.copy2(chains_exe_src, chains_sub / CHAINS_EXE_NAME)
            input_chain = write_chains_inp({
                'IFLAG': 2, 'INITIAL': iso['zzaaas'], 'IFINAL': ifinal_zzaaas,
                'NMAX': nmax, 'PCNT': pcnt,
            })
            (chains_sub / 'input_chain.txt').write_text(input_chain, encoding='utf-8')

            iso['xcomp'] = xcomp
            iso['iso_folder'] = iso_folder
            iso['chains_folder'] = chains_folder
    except SweepError:
        _rollback(created)
        raise
    except Exception as exc:  # noqa: BLE001
        _rollback(created)
        raise SweepError(f'Error inesperado durante la generación: {exc}', 500)

    manifest = {
        'timestamp': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'reference_folder': str(ref_p),
        'ifinal': str(ifinal_name).strip().upper(),
        'ifinal_zzaaas': ifinal_zzaaas,
        'pcnt': pcnt,
        'nmax': nmax,
        'tape22_folder': 'tape22',
        'tape24_folder': 'tape24',
        'isotopes': isotopes,
        'excluded_base_files': sorted(excluded_base_files),
    }
    (root_p / 'chains_manifest.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')

    return {
        'root': str(root_p),
        'n_isotopes': len(isotopes),
        'folders': folders,
        'manifest': manifest,
    }
