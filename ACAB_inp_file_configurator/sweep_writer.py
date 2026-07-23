"""sweep_writer.py — Generación de barridos paramétricos para el configurador ACAB.

Fase 2 del runbook v2.  El servidor es GENÉRICO: no conoce los tipos de
barrido.  Recibe, por simulación, un `patch` (fragmento del dict del
formulario) que fusiona (merge recursivo) sobre una copia profunda del
fichero base, escribe el inp.5 con el writer existente, verifica el
round-trip re-parseándolo, copia el contenido de la carpeta base y genera
manifest + README + scripts de lanzamiento.

Semántica del merge (deep_merge):
    - dicts       → se fusionan por clave (recursivo)
    - listas      → se REEMPLAZAN enteras
    - escalares   → se REEMPLAZAN

El writer (`_write_inp5`) y el parser (`ACABParser`) se inyectan / importan
para no crear dependencia circular con app.py.

Barrido espectral (Fase P2, D9 del RUNBOOK_barrido_espectral.md): además del
`patch` de inp.5, cada sim puede llevar un `coll_patch` (ngroup, cx, ft) que
se aplica sobre el COLL.inp de `<base_folder>/collaps/COLL.inp` y se escribe
en `<sim>/collaps/COLL.inp` (reemplaza al copiado por la base, misma
precedencia que el inp.5 generado). Requiere `collaps/COLL.inp` en la carpeta
base; 422 si falta y el barrido lleva `coll_patch`.

Excepción a "el servidor no conoce los tipos de barrido" (C4 del BACKLOG):
la copia de la carpeta base SÍ mira `sweep_type == 'spectrum'` para decidir
qué salidas viejas excluir (ver `_base_exclusion_names`) -- es la única
rama del código que distingue el tipo, porque la asimetría (el espectral
regenera XSECTION.dat/FLUX.inf por sim; los demás lo comparten a propósito)
no se puede derivar del patch.
"""

from __future__ import annotations

import copy
import csv
import io
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from acab_parser import ACABParser
from coll_writer import apply_spectrum_patch, read_coll_inp, write_coll_inp

MAX_SIMS = 200
_SAFE_SUFFIX = re.compile(r'^[A-Za-z0-9._+-]+$')

# ── Exclusión de salidas viejas al copiar la carpeta base (C4 del BACKLOG) ──
# Un fichero de salida muerto (de OTRA ejecución) dentro de la carpeta de una
# simulación es una trampa de trazabilidad (visto en el control MURR: un
# FLUX.inf de otro espectro). La exclusión depende del TIPO de barrido:
#
# Salidas de ACAB: el pipeline las regenera SIEMPRE por simulación (todo tipo
# de barrido) — se excluyen siempre.
_ACAB_OUTPUT_FILES = ('fort.6', 'run.log', 'cpu_time.txt')

# Salidas de COLLAPS: en el barrido ESPECTRAL el espectro cambia por
# simulación y el pipeline las regenera (D7/D9) -> excluirlas evita heredar
# el XSECTION.dat/FLUX.inf de OTRO espectro (la propia trampa MURR). En los
# barridos de FLUJO/MASA/TEMPORAL el espectro es COMPARTIDO a propósito (no
# se re-ejecuta COLLAPS por simulación, acab_suite/README.md): aquí se
# CONSERVAN, son la entrada real del cálculo, no una trampa.
_COLLAPS_OUTPUT_FILES = ('XSECTION.dat', 'FLUX.inf', 'XS.inf', 'REACTIONS.dat', 'XSZERO.dat')


def _base_exclusion_names(sweep_type: str) -> set[str]:
    """Nombres de fichero a excluir al copiar la carpeta base, según el tipo
    de barrido (asimetría espectral vs flujo/masa/temporal, ver arriba)."""
    if sweep_type == 'spectrum':
        return set(_ACAB_OUTPUT_FILES) | set(_COLLAPS_OUTPUT_FILES)
    return set(_ACAB_OUTPUT_FILES)


def _copy_base_folder(base_p: Path, sub: Path, exclude_names: set[str]) -> list[str]:
    """Copia ``base_p`` en ``sub`` excluyendo ``exclude_names``.

    Devuelve las rutas (relativas a ``base_p``, separador '/') EFECTIVAMENTE
    excluidas -- solo lo que existía de verdad en la base, no la lista
    teórica -- para que la limpieza quede trazada en el manifest.
    """
    excluded: list[str] = []

    def _ignore(dir_path: str, names: list[str]) -> set[str]:
        skip = set()
        for name in names:
            candidate = Path(dir_path) / name
            if name in exclude_names and candidate.is_file():
                skip.add(name)
                excluded.append(str(candidate.relative_to(base_p)).replace('\\', '/'))
        return skip

    shutil.copytree(base_p, sub, dirs_exist_ok=True, ignore=_ignore)
    return excluded


class SweepError(Exception):
    """Error de barrido con código HTTP asociado (422 por defecto)."""

    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------
# Merge recursivo de patches
# ---------------------------------------------------------------------------

def deep_merge(base, patch):
    """Fusiona `patch` sobre `base`.

    dicts se fusionan por clave; listas y escalares se reemplazan enteros.
    No muta los argumentos (devuelve copias).
    """
    if isinstance(base, dict) and isinstance(patch, dict):
        out = copy.deepcopy(base)
        for key, val in patch.items():
            if key in out and isinstance(out[key], dict) and isinstance(val, dict):
                out[key] = deep_merge(out[key], val)
            else:
                out[key] = copy.deepcopy(val)
        return out
    return copy.deepcopy(patch)


# ---------------------------------------------------------------------------
# Utilidades de disco y validación
# ---------------------------------------------------------------------------

def dir_size(path: Path) -> int:
    """Tamaño total (bytes) del contenido de un directorio, recursivo."""
    total = 0
    for f in Path(path).rglob('*'):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def _suffix_issues(sims):
    """Devuelve (duplicados, inválidos) de los sufijos de las simulaciones."""
    seen, dups, invalid = set(), [], []
    for s in sims:
        suf = str(s.get('suffix', '') or '')
        if not suf or not _SAFE_SUFFIX.match(suf):
            invalid.append(suf)
        if suf in seen:
            dups.append(suf)
        seen.add(suf)
    return dups, invalid


# ---------------------------------------------------------------------------
# Preview (sin escribir nada)
# ---------------------------------------------------------------------------

def preview_sweep(root, base_folder, prefix, sims) -> dict:
    prefix = prefix or ''
    root_p = Path(root) if root else None
    base_p = Path(base_folder) if base_folder else None

    base_exists = bool(base_p and base_p.is_dir())
    base_size = dir_size(base_p) if base_exists else 0
    n = len(sims)
    dups, invalid = _suffix_issues(sims)

    collisions = []
    if root_p and root_p.exists():
        for s in sims:
            folder = f"{prefix}{s.get('suffix', '')}"
            if (root_p / folder).exists():
                collisions.append(folder)

    return {
        'root': str(root_p) if root_p else '',
        'root_exists': bool(root_p and root_p.exists()),
        'base_exists': base_exists,
        'base_size': base_size,
        'n': n,
        'est_disk': base_size * n,
        'base_has_inp5': bool(base_exists and (base_p / 'inp.5').exists()),
        'dup_suffixes': sorted(set(dups)),
        'invalid_suffixes': invalid,
        'collisions': collisions,
        'over_limit': n > MAX_SIMS,
    }


# ---------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------

def _roundtrip_check(content: str, parser: ACABParser, folder: str) -> None:
    with tempfile.NamedTemporaryFile('w', suffix='.5', delete=False,
                                     encoding='utf-8') as tf:
        tf.write(content)
        tmp = Path(tf.name)
    try:
        parser.read_inp5(tmp)
    except Exception as exc:  # noqa: BLE001 — se re-lanza como SweepError
        raise SweepError(
            f"El inp.5 generado para '{folder}' no se puede re-parsear "
            f"(round-trip fallido): {exc}", 422)
    finally:
        tmp.unlink(missing_ok=True)


def _coll_roundtrip_check(content: str, folder: str) -> None:
    with tempfile.NamedTemporaryFile('w', suffix='.inp', delete=False,
                                     encoding='utf-8') as tf:
        tf.write(content)
        tmp = Path(tf.name)
    try:
        read_coll_inp(tmp)
    except Exception as exc:  # noqa: BLE001 — se re-lanza como SweepError
        raise SweepError(
            f"El COLL.inp generado para '{folder}' no se puede re-parsear "
            f"(round-trip fallido): {exc}", 422)
    finally:
        tmp.unlink(missing_ok=True)


def _rollback(created) -> None:
    for sub in created:
        try:
            shutil.rmtree(sub, ignore_errors=True)
        except OSError:
            pass


def _manifest_json(root_p, sweep_type, description, fixed_params, sims, folders,
                    excluded_base_files):
    return {
        'timestamp': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'sweep_type': sweep_type,
        'description': description,
        'fixed_params': fixed_params,
        'n': len(sims),
        'simulations': [
            {'folder': folder, 'params': sim.get('params') or {}}
            for sim, folder in zip(sims, folders)
        ],
        'excluded_base_files': sorted(excluded_base_files),
    }


def _csv_cell(v):
    """Valores no escalares (listas/dicts, p. ej. el historial multi-tramo
    de U7) se vuelcan como JSON válido en la celda, no como repr de Python
    -- el manifest CSV es un entregable de trazabilidad, no un debug dump."""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return v


def _manifest_csv(sims, folders) -> str:
    keys = []
    for sim in sims:
        for k in (sim.get('params') or {}):
            if k not in keys:
                keys.append(k)
    buf = io.StringIO()
    # lineterminator='\n': el valor por defecto de csv.writer es '\r\n', que
    # al pasar por Path.write_text en modo texto (traduce '\n'->os.linesep
    # sin tocar los '\r' ya presentes) duplica el salto de línea en Windows
    # ('\r\n' -> '\r\r\n') y deja una fila en blanco entre cada registro --
    # bug preexistente e inadvertido (ningún test parseaba el CSV fila a
    # fila hasta el caso oro de U7). '\n' evita la doble traducción.
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(['folder'] + keys)
    for sim, folder in zip(sims, folders):
        params = sim.get('params') or {}
        w.writerow([folder] + [_csv_cell(params.get(k, '')) for k in keys])
    return buf.getvalue()


def _readme(sweep_type, description, fixed_params, sims, folders) -> str:
    lines = [
        'Barrido paramétrico ACAB — generado por ACAB INP File Configurator',
        '=' * 66,
        '',
        f'Tipo de barrido : {sweep_type}',
        f'Simulaciones    : {len(sims)}',
        f'Fecha (UTC)     : {datetime.now(timezone.utc).isoformat(timespec="seconds")}',
        '',
        'Descripción:',
        (description or '(sin descripción)'),
        '',
        'Parámetros fijos (del fichero base):',
    ]
    if fixed_params:
        for k, v in fixed_params.items():
            lines.append(f'  - {k}: {v}')
    else:
        lines.append('  (no especificados)')
    lines += ['', 'Simulaciones:']
    for sim, folder in zip(sims, folders):
        params = sim.get('params') or {}
        pstr = ', '.join(f'{k}={v}' for k, v in params.items())
        lines.append(f'  - {folder}: {pstr}')
    lines += [
        '',
        'Ejecución: usa run_all.ps1 (Windows) o run_all.sh (Unix); ajusta',
        'primero la ruta al ejecutable de ACAB dentro del script.',
        '',
    ]
    return '\n'.join(lines)


def _run_all_ps1(folders) -> str:
    arr = ',\n  '.join(f"'{f}'" for f in folders)
    return (
        '# run_all.ps1 — lanza ACAB en cada subcarpeta del barrido.\n'
        '# Ajusta $ACAB_EXE a la ruta del ejecutable de ACAB.\n'
        '$ACAB_EXE = "acab.exe"\n'
        f'$dirs = @(\n  {arr}\n)\n'
        'foreach ($d in $dirs) {\n'
        '  Push-Location (Join-Path $PSScriptRoot $d)\n'
        '  & $ACAB_EXE *> run.log\n'
        '  Pop-Location\n'
        '}\n'
    )


def _run_all_sh(folders) -> str:
    arr = ' '.join(f'"{f}"' for f in folders)
    return (
        '#!/usr/bin/env bash\n'
        '# run_all.sh — lanza ACAB en cada subcarpeta del barrido.\n'
        '# Ajusta ACAB_EXE a la ruta del ejecutable de ACAB.\n'
        'set -u\n'
        'ACAB_EXE="${ACAB_EXE:-acab}"\n'
        'cd "$(dirname "$0")"\n'
        f'for d in {arr}; do\n'
        '  (cd "$d" && "$ACAB_EXE" > run.log 2>&1)\n'
        'done\n'
    )


def generate_sweep(payload: dict, write_fn: Callable[[dict], str]) -> dict:
    data = payload.get('data') or {}
    sims = payload.get('sims') or []
    root = payload.get('root')
    base_folder = payload.get('base_folder')
    prefix = payload.get('prefix') or ''
    description = payload.get('description') or ''
    sweep_type = payload.get('sweep_type') or ''
    fixed_params = payload.get('fixed_params') or {}
    overwrite = bool(payload.get('overwrite'))

    # ── Validación de entradas ────────────────────────────────────────────
    if not root:
        raise SweepError('Falta la carpeta raíz de salida.', 422)
    if not base_folder:
        raise SweepError('Falta la carpeta base a copiar.', 422)
    if not description.strip():
        raise SweepError('La descripción del barrido es obligatoria.', 422)

    n = len(sims)
    if n == 0:
        raise SweepError('No hay simulaciones que generar.', 422)
    if n > MAX_SIMS:
        raise SweepError(f'{n} simulaciones exceden el máximo de {MAX_SIMS}.', 422)

    base_p = Path(base_folder)
    if not base_p.is_dir():
        raise SweepError('La carpeta base no existe o no es un directorio.', 422)

    # ── Barrido espectral (D9): requiere collaps/COLL.inp en la base ───────
    has_coll_patch = any(s.get('coll_patch') for s in sims)
    coll_base_data = None
    if has_coll_patch:
        coll_base_path = base_p / 'collaps' / 'COLL.inp'
        if not coll_base_path.is_file():
            raise SweepError(
                "El barrido espectral requiere 'collaps/COLL.inp' en la carpeta base "
                f"('{coll_base_path}' no existe).", 422)
        try:
            coll_base_data = read_coll_inp(coll_base_path)
        except Exception as exc:  # noqa: BLE001
            raise SweepError(f"No se pudo parsear el COLL.inp base: {exc}", 422)

    dups, invalid = _suffix_issues(sims)
    if invalid:
        raise SweepError('Sufijos inválidos o vacíos: ' + ', '.join(repr(s) for s in invalid), 422)
    if dups:
        raise SweepError('Sufijos duplicados: ' + ', '.join(dups), 422)

    root_p = Path(root)
    folders = [f"{prefix}{s.get('suffix', '')}" for s in sims]

    if not overwrite:
        collisions = [f for f in folders if (root_p / f).exists()]
        if collisions:
            raise SweepError('Ya existen estas subcarpetas (usa overwrite): '
                             + ', '.join(collisions), 409)

    # ── Escritura ─────────────────────────────────────────────────────────
    root_p.mkdir(parents=True, exist_ok=True)
    parser = ACABParser()
    created = []
    exclude_names = _base_exclusion_names(sweep_type)
    excluded_base_files: set[str] = set()
    try:
        for sim, folder in zip(sims, folders):
            merged = deep_merge(data, sim.get('patch') or {})
            try:
                content = write_fn(merged)
            except SweepError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise SweepError(f"Error al escribir el inp.5 de '{folder}': {exc}", 422)

            _roundtrip_check(content, parser, folder)

            sub = root_p / folder
            existed = sub.exists()
            sub.mkdir(parents=True, exist_ok=True)
            if not existed:
                created.append(sub)
            # Copiar el contenido de la carpeta base (recursivo), excluyendo
            # salidas viejas (C4: la trampa de trazabilidad tipo MURR)…
            excluded_base_files.update(_copy_base_folder(base_p, sub, exclude_names))
            # …y escribir el inp.5 generado DESPUÉS (reemplaza el de la base)
            (sub / 'inp.5').write_text(content, encoding='utf-8')

            coll_patch = sim.get('coll_patch')
            if coll_patch:
                try:
                    coll_data = apply_spectrum_patch(coll_base_data, coll_patch)
                    coll_content = write_coll_inp(coll_data)
                except SweepError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    raise SweepError(f"Error al escribir el COLL.inp de '{folder}': {exc}", 422)
                _coll_roundtrip_check(coll_content, folder)
                coll_dir = sub / 'collaps'
                coll_dir.mkdir(parents=True, exist_ok=True)
                (coll_dir / 'COLL.inp').write_text(coll_content, encoding='utf-8')
    except SweepError:
        _rollback(created)
        raise
    except Exception as exc:  # noqa: BLE001
        _rollback(created)
        raise SweepError(f'Error inesperado durante la generación: {exc}', 500)

    # ── Manifest + README + scripts en la raíz ────────────────────────────
    manifest = _manifest_json(root_p, sweep_type, description, fixed_params, sims, folders,
                               excluded_base_files)
    (root_p / 'sweep_manifest.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    (root_p / 'sweep_manifest.csv').write_text(
        _manifest_csv(sims, folders), encoding='utf-8')
    (root_p / 'README.txt').write_text(
        _readme(sweep_type, description, fixed_params, sims, folders), encoding='utf-8')
    (root_p / 'run_all.ps1').write_text(_run_all_ps1(folders), encoding='utf-8')
    (root_p / 'run_all.sh').write_text(_run_all_sh(folders), encoding='utf-8')

    return {'n_written': n, 'root': str(root_p), 'folders': folders}
