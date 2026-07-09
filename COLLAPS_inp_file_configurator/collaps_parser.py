"""collaps_parser.py — Parser for COLLAPS input files (COLL.inp format).

COLL.inp structure (9 cards):
  Card #1  (2I4)         ILIB  IESF      — group structures
  Card #2  (free)        IHEAD             — XS library heading lines
  Card #3  (free)        ISFIS IGEN ISOCA IBEST  — fission mode flags
  Card #4  (free, if ISFIS≠0)  EB1 EB2   — fission yield energy boundaries (eV)
  Card #5  (2I4)         NGROUP FF         — neutron flux group count and units
  Card #6  (6E12.5, if IESF=5)  CX[ABS(NGROUP)+1]  — custom energy boundaries
  Card #7  (6E12.5)      FT[ABS(NGROUP)]   — neutron flux values
  Card #8  (free)        IUNC3G            — uncertainty mode
  Card #9  (free)        ISTOP             — run mode

Usage::

    from collaps_parser import COLLAPSParser
    data = COLLAPSParser().read_coll_inp('examples/example1/collaps/COLL.inp')
    print(data['card1'])   # {'ILIB': 2, 'IESF': 2}
    print(data['card5'])   # {'NGROUP': -175, 'FF': 0}
"""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path
from typing import Any

# Matches FORTRAN numeric tokens: integer, float, D/d-exponent, bare exponent (.5, 3.2336+27)
_NUM_RE = re.compile(r'^-?(\d+(\.\d*)?|\.\d+)([eEdD][+-]?\d+|[+-]\d+)?$')
_BARE_EXP_RE = re.compile(r'(?<=\d)([+-]\d+)$')


def _parse_fortran_float(tok: str) -> float:
    """Convert a FORTRAN real literal to Python float (handles D-exp and bare-exp)."""
    tok = tok.replace('D', 'E').replace('d', 'e')
    if 'E' not in tok and 'e' not in tok:
        tok = _BARE_EXP_RE.sub(r'E\1', tok)
    return float(tok)


class COLLAPSParser:
    """Parser for COLLAPS COLL.inp files."""

    def read_coll_inp(self, file_path: str | Path) -> dict[str, Any]:
        """Parse a COLL.inp file and return a structured dict.

        Returns
        -------
        dict with keys: card1..card9  (card4 is None when ISFIS==0,
        card6 is None when IESF!=5).
        """
        path = Path(file_path)
        with path.open(encoding='utf-8', errors='replace') as fh:
            lines = fh.readlines()

        # Build flat token queue from all non-blank lines
        tokens: list[str] = []
        for raw in lines:
            for tok in raw.split():
                if _NUM_RE.match(tok):
                    tokens.append(tok)

        self._q: deque[str] = deque(tokens)

        # Card #1: ILIB, IESF
        ilib = self._read_int()
        iesf = self._read_int()

        # Card #2: IHEAD
        ihead = self._read_int()

        # Card #3: ISFIS, IGEN, ISOCA, IBEST (always 4 values, even when ISFIS=0)
        isfis = self._read_int()
        igen  = self._read_int()
        isoca = self._read_int()
        ibest = self._read_int()

        # Card #4: EB1, EB2 (only when ISFIS != 0)
        if isfis != 0:
            eb1 = self._read_float()
            eb2 = self._read_float()
            card4: dict | None = {'EB1': eb1, 'EB2': eb2}
        else:
            card4 = None

        # Card #5: NGROUP, FF
        ngroup = self._read_int()
        ff     = self._read_int()
        nabs   = abs(ngroup)

        # Card #6: CX[nabs+1] energy boundaries (only when IESF == 5)
        if iesf == 5:
            cx    = [self._read_float() for _ in range(nabs + 1)]
            card6: dict | None = {'CX': cx}
        else:
            card6 = None

        # Card #7: FT[nabs] flux values
        ft = [self._read_float() for _ in range(nabs)]

        # Card #8: IUNC3G
        iunc3g = self._read_int()

        # Card #9: ISTOP
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_token(self) -> str:
        if not self._q:
            raise ValueError(
                "Unexpected end of token stream. "
                "The file may be truncated or malformed."
            )
        return self._q.popleft()

    def _read_int(self) -> int:
        return int(self._next_token())

    def _read_float(self) -> float:
        return _parse_fortran_float(self._next_token())


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import json
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else 'examples/example1/collaps/COLL.inp'
    data = COLLAPSParser().read_coll_inp(target)

    c1 = data['card1']
    c5 = data['card5']
    c7 = data['card7']
    lib_names = {1:'GAM-II(100g)', 2:'Vit-J(175g)', 3:'TART-175', 4:'TART-566', 5:'Other', 12:'Vit-J+(211g)'}
    print(f"ILIB={c1['ILIB']} ({lib_names.get(c1['ILIB'], '?')})  "
          f"IESF={c1['IESF']} ({lib_names.get(c1['IESF'], '?')})")
    print(f"IHEAD={data['card2']['IHEAD']}")
    c3 = data['card3']
    print(f"ISFIS={c3['ISFIS']}  IGEN={c3['IGEN']}  ISOCA={c3['ISOCA']}  IBEST={c3['IBEST']}")
    if data['card4']:
        print(f"EB1={data['card4']['EB1']:.3E} eV  EB2={data['card4']['EB2']:.3E} eV")
    print(f"NGROUP={c5['NGROUP']}  FF={c5['FF']}")
    if data['card6']:
        print(f"CX: {len(data['card6']['CX'])} energy boundaries")
    print(f"FT: {len(c7['FT'])} flux values  (first={c7['FT'][0]:.3E}, last={c7['FT'][-1]:.3E})")
    print(f"IUNC3G={data['card8']['IUNC3G']}  ISTOP={data['card9']['ISTOP']}")
