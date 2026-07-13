"""coll_writer.py — Lector/escritor de COLL.inp para el barrido espectral.

**Común de la suite (D9, RUNBOOK_barrido_espectral.md)**: parser y writer
sincronizados en semántica con `COLLAPS_inp_file_configurator/collaps_parser.py`
y el `_write_coll_inp` de su `app.py` (mismo formato de las 9 tarjetas; ver
`docs/COLLAPS.md` de aquel repo como fuente de verdad). Si cambia el formato
de COLL.inp allí, replicar aquí.

Limitado a lo necesario para el barrido espectral: parsear el COLL.inp base
de `<base_folder>/collaps/COLL.inp`, aplicar un patch de NGROUP/FF, CX y FT
(`apply_spectrum_patch`, función local — no existe en el repo COLLAPS) y
regenerar el fichero conservando el resto de tarjetas (ILIB, IHEAD,
ISFIS/IGEN/ISOCA/IBEST, EB1/EB2, IUNC3G, ISTOP) tal cual del base.
"""

from __future__ import annotations

import copy
import re
from collections import deque
from pathlib import Path
from typing import Any

# Mismo tokenizador FORTRAN que el resto de la suite (D-exp, bare-exp).
_NUM_RE = re.compile(r'^-?(\d+(\.\d*)?|\.\d+)([eEdD][+-]?\d+|[+-]\d+)?$')
_BARE_EXP_RE = re.compile(r'(?<=\d)([+-]\d+)$')


def _parse_fortran_float(tok: str) -> float:
    tok = tok.replace('D', 'E').replace('d', 'e')
    if 'E' not in tok and 'e' not in tok:
        tok = _BARE_EXP_RE.sub(r'E\1', tok)
    return float(tok)


class COLLAPSParser:
    """Parser de COLL.inp (copia sincronizada de collaps_parser.py, D9)."""

    def read_coll_inp(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)
        with path.open(encoding='utf-8', errors='replace') as fh:
            lines = fh.readlines()

        tokens: list[str] = []
        for raw in lines:
            for tok in raw.split():
                if _NUM_RE.match(tok):
                    tokens.append(tok)

        self._q: deque[str] = deque(tokens)

        ilib = self._read_int()
        iesf = self._read_int()
        ihead = self._read_int()
        isfis = self._read_int()
        igen = self._read_int()
        isoca = self._read_int()
        ibest = self._read_int()

        if isfis != 0:
            eb1 = self._read_float()
            eb2 = self._read_float()
            card4: dict | None = {'EB1': eb1, 'EB2': eb2}
        else:
            card4 = None

        ngroup = self._read_int()
        ff = self._read_int()
        nabs = abs(ngroup)

        if iesf == 5:
            cx = [self._read_float() for _ in range(nabs + 1)]
            card6: dict | None = {'CX': cx}
        else:
            card6 = None

        ft = [self._read_float() for _ in range(nabs)]
        iunc3g = self._read_int()
        istop = self._read_int()

        return {
            'card1': {'ILIB': ilib, 'IESF': iesf},
            'card2': {'IHEAD': ihead},
            'card3': {'ISFIS': isfis, 'IGEN': igen, 'ISOCA': isoca, 'IBEST': ibest},
            'card4': card4,
            'card5': {'NGROUP': ngroup, 'FF': ff},
            'card6': card6,
            'card7': {'FT': ft},
            'card8': {'IUNC3G': iunc3g},
            'card9': {'ISTOP': istop},
        }

    def _next_token(self) -> str:
        if not self._q:
            raise ValueError(
                "Unexpected end of token stream. "
                "The file may be truncated or malformed.")
        return self._q.popleft()

    def _read_int(self) -> int:
        return int(self._next_token())

    def _read_float(self) -> float:
        return _parse_fortran_float(self._next_token())


def read_coll_inp(file_path: str | Path) -> dict[str, Any]:
    """Atajo funcional sobre COLLAPSParser().read_coll_inp()."""
    return COLLAPSParser().read_coll_inp(file_path)


# ---------------------------------------------------------------------------
# Writer (copia sincronizada de _write_coll_inp / _floats_block_e125, D9)
# ---------------------------------------------------------------------------

def _gi(d: dict, k: str, default: int = 0) -> int:
    v = (d or {}).get(k)
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _gf(d: dict, k: str, default: float = 0.0) -> float:
    v = (d or {}).get(k)
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _floats_block_e125(vals, per_line: int = 6) -> str:
    """Formatea una lista de reales como bloque FORTRAN 6E12.5 (12 car./campo)."""
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


def write_coll_inp(data: dict) -> str:
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

    ilib = _gi(c1, 'ILIB', 2)
    iesf = _gi(c1, 'IESF', 2)
    ihead = _gi(c2, 'IHEAD', 16)
    isfis = _gi(c3, 'ISFIS', 0)
    igen = _gi(c3, 'IGEN', 0)
    isoca = _gi(c3, 'ISOCA', 1)
    ibest = _gi(c3, 'IBEST', 1)
    ngroup = _gi(c5, 'NGROUP', -175)
    ff = _gi(c5, 'FF', 0)
    nabs = abs(ngroup)
    iunc3g = _gi(c8, 'IUNC3G', 0)
    istop = _gi(c9, 'ISTOP', 0)

    L.append(f'{ilib:4d}{iesf:4d}')
    L.append(f'{ihead:4d}')
    L.append(f'   {isfis}   {igen}   {isoca}   {ibest}')

    if isfis != 0:
        eb1 = _gf(c4, 'EB1', 5e6)
        eb2 = _gf(c4, 'EB2', 2e5)
        L.append(f' {eb1:.3E}  {eb2:.3E}')

    L.append(f'{ngroup:4d}{ff:4d}')

    if iesf == 5:
        cx = list(c6.get('CX') or [0.0] * (nabs + 1))
        while len(cx) < nabs + 1:
            cx.append(0.0)
        L.append(_floats_block_e125(cx[:nabs + 1]))

    ft = list(c7.get('FT') or [0.0] * nabs)
    while len(ft) < nabs:
        ft.append(0.0)
    L.append(_floats_block_e125(ft[:nabs]))

    L.append(f'{iunc3g:20d}')
    L.append(f'{istop:20d}')

    return '\n'.join(L) + '\n'


# ---------------------------------------------------------------------------
# Patch de barrido espectral (D9 — no existe en el repo COLLAPS)
# ---------------------------------------------------------------------------

def apply_spectrum_patch(base: dict, patch: dict) -> dict:
    """Aplica un patch de barrido espectral (ngroup, cx, ft) sobre los datos
    parseados de un COLL.inp base, preservando el resto de tarjetas (D9).

    Si el patch incluye 'cx', la tarjeta #1 pasa a IESF=5 (custom): un
    espectro importado usa una estructura de energías propia (D4).
    """
    ngroup = patch.get('ngroup')
    ft = patch.get('ft')
    cx = patch.get('cx')

    if ngroup is None:
        raise ValueError("El patch espectral debe incluir 'ngroup'.")
    if not ft:
        raise ValueError("El patch espectral debe incluir 'ft' (no vacío).")

    ngroup = int(ngroup)
    nabs = abs(ngroup)
    if len(ft) != nabs:
        raise ValueError(f"FT tiene {len(ft)} valores; se esperaban {nabs} (|NGROUP|).")

    data = copy.deepcopy(base)
    data['card5'] = {'NGROUP': ngroup, 'FF': _gi(data.get('card5'), 'FF', 0)}
    data['card7'] = {'FT': list(ft)}

    if cx is not None:
        if len(cx) != nabs + 1:
            raise ValueError(f"CX tiene {len(cx)} valores; se esperaban {nabs + 1} (|NGROUP|+1).")
        data['card1'] = {**(data.get('card1') or {}), 'IESF': 5}
        data['card6'] = {'CX': list(cx)}

    return data
