"""chains_handler.py — Parser and writer for CHAINS utility input files.

CHAINS input format (3–5 cards, depending on IFLAG):

  Card 1: IFLAG (I3)    — operation mode:
                          1 = all paths to produce IFINAL
                          2 = paths from INITIAL to IFINAL (ranked by importance)
                          3 = cyclic paths involving IFINAL
  Card 2: INITIAL (I6)  — initial nuclide; only if IFLAG = 2
  Card 3: IFINAL (I6)   — target nuclide
  Card 4: NMAX (I3)     — max chain length (steps), NMAX ≤ 10
  Card 5: PCNT (F6.2)   — min importance % to print; only if IFLAG = 2

Nuclide identifier: Z*10000 + A*10 + IS   (IS=0 ground, IS=1 metastable)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# ── Element symbols Z=1..103 ──────────────────────────────────────────────
_SYMBOLS: list[str] = [
    '',                                                         # 0 placeholder
    'H',  'He', 'Li', 'Be', 'B',  'C',  'N',  'O',  'F',  'Ne',  # 1-10
    'Na', 'Mg', 'Al', 'Si', 'P',  'S',  'Cl', 'Ar', 'K',  'Ca',  # 11-20
    'Sc', 'Ti', 'V',  'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',  # 21-30
    'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y',  'Zr',  # 31-40
    'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',  # 41-50
    'Sb', 'Te', 'I',  'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',  # 51-60
    'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',  # 61-70
    'Lu', 'Hf', 'Ta', 'W',  'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',  # 71-80
    'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',  # 81-90
    'Pa', 'U',  'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm',  # 91-100
    'Md', 'No', 'Lr',                                               # 101-103
]


def nuclide_label(nid: int) -> str:
    """Return human-readable label for an ACAB nuclide ID (e.g. 260540 → 'Fe-54')."""
    z   = nid // 10000
    a   = (nid % 10000) // 10
    iso = nid % 10
    sym = _SYMBOLS[z] if 0 < z < len(_SYMBOLS) else f'Z{z}'
    return f'{sym}-{a}{"m" if iso else ""}'


def nuclide_id(z: int, a: int, is_meta: bool = False) -> int:
    """Compute ACAB nuclide identifier from Z, A and metastable flag."""
    return z * 10000 + a * 10 + (1 if is_meta else 0)


# ── CHAINS file detection ─────────────────────────────────────────────────
_IFLAG_RE = re.compile(r'\bIFLAG\b', re.IGNORECASE)


def is_chains_file(path) -> bool:
    """Return True when the first ~512 bytes of *path* contain the IFLAG token."""
    try:
        text = Path(path).read_text(encoding='utf-8', errors='replace')[:512]
    except OSError:
        return False
    return bool(_IFLAG_RE.search(text))


# ── Parser ────────────────────────────────────────────────────────────────
def _line_value_label(line: str):
    """Split one CHAINS input line into (numeric_value, UPPERCASE_LABEL)."""
    tokens = line.split()
    if not tokens:
        return None, ''
    raw = tokens[0]
    try:
        val: int | float = float(raw) if '.' in raw else int(raw)
    except ValueError:
        return None, ''
    label = tokens[1].upper() if len(tokens) > 1 else ''
    return val, label


def read_chains_inp(file_path) -> dict[str, Any]:
    """Parse a CHAINS input file.

    Returns a dict with keys: IFLAG, IFINAL, NMAX, and optionally INITIAL, PCNT.
    Raises ValueError when the file cannot be recognised as a valid CHAINS input.
    """
    path = Path(file_path)
    with path.open(encoding='utf-8', errors='replace') as fh:
        lines = [ln.rstrip() for ln in fh if ln.strip()]

    data: dict[str, Any] = {}
    for line in lines:
        val, label = _line_value_label(line)
        if val is None:
            continue
        if label == 'IFLAG':
            data['IFLAG'] = int(val)
        elif label == 'INITIAL':
            data['INITIAL'] = int(val)
        elif label == 'IFINAL':
            data['IFINAL'] = int(val)
        elif label == 'NMAX':
            data['NMAX'] = int(val)
        elif label in ('PCNT', 'PCNTF'):
            data['PCNT'] = float(val)

    if 'IFLAG' not in data:
        raise ValueError(
            "No se encontró el campo IFLAG. ¿Es este un fichero CHAINS válido?"
        )

    # Mode 3: some CHAINS versions write INITIAL where other versions write IFINAL
    if data['IFLAG'] == 3 and 'INITIAL' in data and 'IFINAL' not in data:
        data['IFINAL'] = data.pop('INITIAL')

    if 'IFINAL' not in data:
        raise ValueError(
            f"No se encontró IFINAL en el fichero CHAINS (IFLAG={data['IFLAG']})."
        )

    return data


# ── Writer ────────────────────────────────────────────────────────────────
def write_chains_inp(data: dict) -> str:
    """Generate a CHAINS input file string from *data*."""
    iflag   = int(data.get('IFLAG',   2))
    ifinal  = int(data.get('IFINAL',  0))
    initial = int(data.get('INITIAL', 0))
    nmax    = int(data.get('NMAX',    4))
    pcnt    = float(data.get('PCNT',  0.1))

    lbl_f = nuclide_label(ifinal)  if ifinal  else ''
    lbl_i = nuclide_label(initial) if initial else ''

    lines = [f'  {iflag}    IFLAG']

    if iflag == 2:
        lines.append(f'{initial:6d} INITIAL  {lbl_i}'.rstrip())

    lines.append(f'{ifinal:6d} IFINAL  {lbl_f}'.rstrip())
    lines.append(f'  {nmax}    NMAX')

    if iflag == 2:
        lines.append(f'  {pcnt}    PCNT')

    return '\n'.join(lines) + '\n'


# ── Default data ──────────────────────────────────────────────────────────
def default_chains_data() -> dict[str, Any]:
    """Return a sensible default CHAINS dataset (Al-27 → Na-24, mode 2)."""
    return {
        'IFLAG':   2,
        'INITIAL': nuclide_id(13, 27),   # Al-27  = 130270
        'IFINAL':  nuclide_id(11, 24),   # Na-24  = 110240
        'NMAX':    4,
        'PCNT':    0.1,
    }


# ── Quick self-test ───────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        d = read_chains_inp(sys.argv[1])
    else:
        d = default_chains_data()

    print(f"IFLAG  = {d['IFLAG']}")
    if 'INITIAL' in d:
        print(f"INITIAL= {d['INITIAL']}  ({nuclide_label(d['INITIAL'])})")
    print(f"IFINAL = {d['IFINAL']}  ({nuclide_label(d['IFINAL'])})")
    print(f"NMAX   = {d['NMAX']}")
    if 'PCNT' in d:
        print(f"PCNT   = {d['PCNT']}")
    print()
    print("─── generated file ───")
    print(write_chains_inp(d), end='')
