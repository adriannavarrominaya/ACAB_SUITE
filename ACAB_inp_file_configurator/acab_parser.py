"""acab_parser.py — Parser for ACAB activation code input files (.5 format).

Handles:
  - All 14 data blocks (Block #1 through Block #14).
  - Conditional and repeated blocks (Block #5, #6, #7/#8).
  - Unified time list for Blocks #7/#8 as list of (time, irradiation_type) tuples,
    where irradiation_type is 1 for irradiation and 0 for cooling.
  - PROCACAB post-processing utility input files via read_procacab().

Free-format FORTRAN input rules (as per docs/inp.5.md):
  - Lines with '<' in column 1 are pure comment lines and are skipped.
  - A '<' anywhere else in a data line marks the start of an inline comment;
    everything from that '<' to the end of the line is discarded.
  - Non-numeric tokens (inline labels such as 'IUNC', 'IWP', 'NOPUL …') are
    silently discarded by the tokeniser.
  - Block #1 Card #1 (title) is the first non-comment line and is stored as
    raw text; it is never tokenised as a number.

Usage example::

    from acab_parser import ACABParser
    parser = ACABParser()
    data = parser.read_inp5('examples/inp.5')
    print(data['block1']['title'])
    print(data['blocks78']['times'][:5])   # first 5 (time, type) tuples

    proc = parser.read_procacab('procacab_input.txt')
    print(proc['INUCL'])
"""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path
from typing import Any

# Matches any FORTRAN free-format numeric token.  Covers:
#   standard E/e exponent : 1.0E-25, 2.400E+0
#   D/d exponent (double) : 1.0D-25
#   bare exponent         : 3.2336+27, 1.5-3  (no E, used in legacy FORTRAN files)
#   leading-dot float     : .5, .00E+00
# Examples: 0, -1, 1373, 2.400E+0, 1.0E-25, 3.2336+27, 1., .5, .00E+00
_NUM_RE = re.compile(r'^-?(\d+(\.\d*)?|\.\d+)([eEdD][+-]?\d+|[+-]\d+)?$')

# Used in _parse_fortran_float to detect bare-exponent tokens (e.g. 3.2336+27)
_BARE_EXP_RE = re.compile(r'(?<=\d)([+-]\d+)$')


def _parse_fortran_float(tok: str) -> float:
    """Convert a FORTRAN real literal to a Python float.

    Handles D/d exponent markers and bare-exponent notation not understood by
    Python's built-in float().
    """
    # D/d exponent → E (Python float() only knows E)
    tok = tok.replace('D', 'E').replace('d', 'e')
    # Bare exponent: 3.2336+27 → 3.2336E+27  (only when no E/e present)
    if 'E' not in tok and 'e' not in tok:
        tok = _BARE_EXP_RE.sub(r'E\1', tok)
    return float(tok)


class ACABParser:
    """Parser for ACAB input files (.5 free-format FORTRAN).

    Instantiate once and call read_inp5() for each file.  The parser state is
    reset on every call so the same instance can be reused.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_inp5(self, file_path: str | Path) -> dict[str, Any]:
        """Read an ACAB .5 input file and return a dict keyed by block name.

        Keys:
            block1  – general run parameters (title, IUNC, 21 integers)
            block2  – geometry / zone / output setup
            block3  – neutron flux data (None if IFLU != 1)
            block4  – restart option
            block5  – list of initial material compositions per zone
                       (None if IREST == 1)
            block6  – list of continuous-feed compositions per zone
                       (None if INFD == 0)
            blocks78 – temporal history:
                        'sets'  : list of raw set dicts
                        'times' : unified list of (time, irradiation_type)
            block9  – truncation error & flux normalisation
            block10 – fission products
            block11 – run type, special responses, temporal structure
            block12 – instantaneous feed
            block13 – output control (None if IUNC == 1)
            block14 – Monte Carlo uncertainty (None if IUNC == 0)
        """
        self._load_file(file_path)

        b1 = self._parse_block1()
        b2 = self._parse_block2(b1)
        b3 = self._parse_block3(b1)
        b4 = self._parse_block4()
        b5 = self._parse_block5(b1, b2) if b4['IREST'] == 0 else None
        b6 = self._parse_block6(b1, b2) if b1['INFD'] > 0 else None
        b78 = self._parse_blocks78()
        b9 = self._parse_block9()
        b10 = self._parse_block10()
        b11 = self._parse_block11()
        b12 = self._parse_block12(b11)
        b13 = self._parse_block13(b1, b11) if b1['IUNC'] == 0 else None
        b14 = self._parse_block14(b1, b11) if b1['IUNC'] == 1 else None

        return {
            'block1':   b1,
            'block2':   b2,
            'block3':   b3,
            'block4':   b4,
            'block5':   b5,
            'block6':   b6,
            'blocks78': b78,
            'block9':   b9,
            'block10':  b10,
            'block11':  b11,
            'block12':  b12,
            'block13':  b13,
            'block14':  b14,
        }

    def read_procacab(self, file_path: str | Path) -> dict[str, Any]:
        """Read a PROCACAB utility input file.

        Format (one value per line, keyboard-style):
            FILE    – name of the binary .mon file (string)
            NNUCL   – number of nuclides (integer)
            INUCL   – nuclide identifiers, NNUCL lines (integers)
            NTIME   – number of time steps (integer)
            NTIM    – time-step indices, NTIME lines (integers)

        Returns a dict with keys: FILE, NNUCL, INUCL, NTIME, NTIM.
        """
        path = Path(file_path)
        with path.open(encoding='utf-8', errors='replace') as fh:
            raw_lines = [ln.rstrip('\n') for ln in fh]

        non_empty = [ln.strip() for ln in raw_lines if ln.strip()]
        if not non_empty:
            raise ValueError(f"PROCACAB input file '{file_path}' is empty.")

        # First non-empty line is the binary filename (a plain string)
        result: dict[str, Any] = {'FILE': non_empty[0]}

        # Tokenise the remaining lines numerically
        self._tokens = deque()
        self._token_labels: deque[frozenset[str]] = deque()
        for ln in non_empty[1:]:
            truncated = ln.split('<')[0]
            for tok in truncated.split():
                if _NUM_RE.match(tok):
                    self._tokens.append(tok)

        nnucl = self._read_int()
        result['NNUCL'] = nnucl
        result['INUCL'] = self._read_ints(nnucl)
        ntime = self._read_int()
        result['NTIME'] = ntime
        result['NTIM'] = self._read_ints(ntime)

        return result

    # ------------------------------------------------------------------
    # Tokeniser
    # ------------------------------------------------------------------

    def _load_file(self, file_path: str | Path) -> None:
        """Read the file and build the numeric token queue.

        The first non-comment line is stored separately as the title (Block #1
        Card #1) because it is free text, not a numeric field.

        Comment handling rules (from docs/inp.5.md):
          * Any line whose first character is ``<`` is a pure comment → skipped.
          * A line that immediately follows a comment line *and* starts with a
            letter (after leading spaces) is treated as a comment continuation.
            This handles real-world multi-line comments such as found in the NIF
            example file where only the first line of a block comment starts with
            ``<``.
          * A ``<`` that appears elsewhere in a data line begins an inline comment;
            everything from that ``<`` to the end of the line is discarded.
          * Non-numeric tokens on data lines (inline labels like ``IUNC``, ``IWP``)
            are silently discarded.
        """
        path = Path(file_path)
        with path.open(encoding='utf-8', errors='replace') as fh:
            lines = fh.readlines()

        # --- Pass 1: locate the title line (first non-comment, non-blank line) ---
        self._title: str = ''
        title_line_idx: int = -1
        for i, raw in enumerate(lines):
            line = raw.rstrip('\n')
            if line and line[0] == '<':
                continue
            if line.strip():
                self._title = raw.strip()
                title_line_idx = i
                break

        if title_line_idx == -1:
            raise ValueError(f"No data found in '{file_path}'.")

        # --- Pass 2: tokenise all lines after the title ---
        self._tokens: deque[str] = deque()
        # Parallel queue: for each token, the frozenset of pure-alpha uppercase
        # words found on the same data line (e.g. {'PH','BREM','TOT','RHOR'}).
        # Used by _peek_line_labels() to disambiguate optional cards.
        self._token_labels: deque[frozenset[str]] = deque()
        prev_was_comment = False

        for raw in lines[title_line_idx + 1:]:
            line = raw.rstrip('\n')

            # Pure comment line (first char is '<')
            if line and line[0] == '<':
                prev_was_comment = True
                continue

            # Comment continuation: the line immediately follows a comment line
            # AND starts with a letter.  In ACAB input files every genuine data
            # line begins with a digit (possibly after leading spaces).
            lstripped = line.lstrip()
            if prev_was_comment and lstripped and lstripped[0].isalpha():
                # Remain in "comment" state so that multi-line continuations
                # spanning more than two lines are also absorbed correctly.
                continue

            # Data line — reset comment flag
            prev_was_comment = False
            if not lstripped:
                continue  # blank line

            # Strip inline comment (everything from first '<' onwards)
            if '<' in line:
                line = line[:line.index('<')]

            # Collect pure-alpha labels from this data line (e.g. PH, BREM, NOPUL)
            words = line.split()
            labels: frozenset[str] = frozenset(
                w.upper() for w in words if w.isalpha()
            )

            # Add only valid numeric tokens to the queue
            for tok in words:
                if _NUM_RE.match(tok):
                    self._tokens.append(tok)
                    self._token_labels.append(labels)

    def _next_token(self) -> str:
        if not self._tokens:
            raise ValueError(
                "Unexpected end of token stream"
                f"{self._ctx_msg()}. "
                "The file may be truncated or malformed."
            )
        if hasattr(self, '_token_labels') and self._token_labels:
            self._token_labels.popleft()
        return self._tokens.popleft()

    def _ctx_msg(self) -> str:
        ctx = getattr(self, '_ctx', '')
        return f' while reading {ctx}' if ctx else ''

    def _peek_line_labels(self) -> frozenset[str]:
        """Return the label set of the next token without consuming it."""
        if hasattr(self, '_token_labels') and self._token_labels:
            return self._token_labels[0]
        return frozenset()

    def _read_int(self) -> int:
        tok = self._next_token()
        try:
            return int(tok)
        except ValueError:
            raise ValueError(
                f"Expected an integer but found '{tok}'{self._ctx_msg()}."
            ) from None

    def _read_float(self) -> float:
        tok = self._next_token()
        try:
            return _parse_fortran_float(tok)
        except ValueError:
            raise ValueError(
                f"Expected a real number but found '{tok}'{self._ctx_msg()}."
            ) from None

    def _read_ints(self, n: int) -> list[int]:
        return [self._read_int() for _ in range(n)]

    def _read_floats(self, n: int) -> list[float]:
        return [self._read_float() for _ in range(n)]

    # ------------------------------------------------------------------
    # Block #1 — General run parameters
    # ------------------------------------------------------------------

    def _parse_block1(self) -> dict[str, Any]:
        """Block #1, 3 cards.

        Card 1 – title string (captured by _load_file, not from token queue).
        Card 2 – IUNC: 0 = standard activation run; 1 = Monte Carlo uncertainty.
        Card 3 – 21 integers controlling library sizes, output and geometry.
        """
        self._ctx = 'Block #1 (general run parameters)'
        b: dict[str, Any] = {'title': self._title}

        # Card 2
        b['IUNC'] = self._read_int()

        # Card 3: 21 integers
        card3_keys = [
            'ITMAX', 'IZMAX', 'MPCTAB', 'IR', 'JTO', 'NTABLE', 'MSTAR',
            'INPT', 'INFD', 'NOGG', 'NGRP', 'IGRP', 'IGE', 'IZM', 'IM',
            'JM', 'IFLU', 'IPRT', 'ILIB', 'IRAD', 'IPUN',
        ]
        for key, val in zip(card3_keys, self._read_ints(21)):
            b[key] = val

        return b

    # ------------------------------------------------------------------
    # Block #2 — Geometry / zone / output setup
    # ------------------------------------------------------------------

    def _parse_block2(self, b1: dict) -> dict[str, Any]:
        """Block #2, up to 8 cards (some conditional).

        Card 1 – XRR : interval boundaries (1D/2D) or zone volumes + terminator (3D MC).
        Card 2 – YZT : 2nd-dimension boundaries; present only when JM > 0.
        Card 3 – MA  : zone ID per spatial interval.
        Card 4 – NUCZO : nuclide/element count per zone.
        Card 5 – ISOZO : same for continuous feed; present only when INFD > 0.
        Card 6 – EGRP  : gamma energy group boundaries (NOGG+1 values).
        Card 7 – CUTOFF: 6 threshold values (always present).
        Card 8 – NTO   : 18 output table flags; present only when JTO == 1.
        """
        self._ctx = 'Block #2 (geometry / zones / EGRP / CUTOFF)'
        ige  = b1['IGE']
        izm  = b1['IZM']
        im   = b1['IM']
        jm   = b1['JM']
        infd = b1['INFD']
        nogg = b1['NOGG']
        jto  = b1['JTO']

        b: dict[str, Any] = {}

        # Card 1 – XRR
        # For IGE == 4 (3-D Monte Carlo): IZM zone volumes + 1 nonzero terminator.
        # For all other geometries: IM + 1 boundary values.
        xrr_count = izm + 1 if ige == 4 else im + 1
        b['XRR'] = self._read_floats(xrr_count)

        # Card 2 – YZT (2D only)
        b['YZT'] = self._read_floats(jm + 1) if jm > 0 else None

        # Card 3 – MA
        ma_count = im * jm if jm > 0 else im
        b['MA'] = self._read_ints(ma_count)

        # Card 4 – NUCZO
        b['NUCZO'] = self._read_ints(izm)

        # Card 5 – ISOZO (continuous feed, conditional)
        b['ISOZO'] = self._read_ints(izm) if infd > 0 else None

        # Card 6 – EGRP
        b['EGRP'] = self._read_floats(nogg + 1)

        # Card 7 – CUTOFF (always 6 values)
        b['CUTOFF'] = self._read_floats(6)

        # Card 8 – NTO (conditional on JTO)
        b['NTO'] = self._read_ints(18) if jto == 1 else None

        return b

    # ------------------------------------------------------------------
    # Block #3 — Neutron flux data
    # ------------------------------------------------------------------

    def _parse_block3(self, b1: dict) -> dict[str, Any] | None:
        """Block #3: FLUX array.  Returns None when IFLU != 1.

        When IUNC == 1 : IM values (one integrated value per interval).
        When JM  >  0  : (NGRP + IGRP) * IM * JM values (2-D geometry).
        Otherwise      : (NGRP + IGRP) * IM values.
        """
        self._ctx = 'Block #3 (FLUX)'
        if b1['IFLU'] != 1:
            return None

        ngrp = b1['NGRP']
        igrp = b1['IGRP']
        im   = b1['IM']
        jm   = b1['JM']
        iunc = b1['IUNC']

        if iunc == 1:
            count = im
        elif jm > 0:
            count = (ngrp + igrp) * im * jm
        else:
            count = (ngrp + igrp) * im

        return {'FLUX': self._read_floats(count)}

    # ------------------------------------------------------------------
    # Block #4 — Restart option
    # ------------------------------------------------------------------

    def _parse_block4(self) -> dict[str, Any]:
        """Block #4: IREST — 0 = normal run; 1 = read composition from UNIT 37."""
        self._ctx = 'Block #4 (IREST)'
        return {'IREST': self._read_int()}

    # ------------------------------------------------------------------
    # Block #5 — Initial material composition (repeated per non-zero zone)
    # ------------------------------------------------------------------

    def _parse_block5(self, b1: dict, b2: dict) -> list[dict[str, Any]]:
        """Block #5: initial composition — one dict per zone with NUCZO[i] > 0.

        Each dict has:
            INUCL – list of nuclide/element identifiers  (NUCZO[i] ints)
            XCOMP – list of concentrations in atoms/barn·cm (NUCZO[i] floats)
        """
        self._ctx = 'Block #5 (initial composition)'
        zones = []
        for n in b2['NUCZO']:
            if n == 0:
                continue
            zones.append({
                'INUCL': self._read_ints(n),
                'XCOMP': self._read_floats(n),
            })
        return zones

    # ------------------------------------------------------------------
    # Block #6 — Continuous feed (repeated per non-zero zone)
    # ------------------------------------------------------------------

    def _parse_block6(self, b1: dict, b2: dict) -> list[dict[str, Any]]:
        """Block #6: continuous feed — one dict per zone with ISOZO[i] > 0.

        Each dict has:
            IDNUM – element/isotope identifiers  (ISOZO[i] ints)
            XFEED – feed rates in g-atoms/second (ISOZO[i] floats)
        """
        self._ctx = 'Block #6 (continuous feed)'
        zones = []
        for n in (b2['ISOZO'] or []):
            if n == 0:
                continue
            zones.append({
                'IDNUM': self._read_ints(n),
                'XFEED': self._read_floats(n),
            })
        return zones

    # ------------------------------------------------------------------
    # Blocks #7 and #8 — Temporal history
    # ------------------------------------------------------------------

    def _parse_blocks78(self) -> dict[str, Any]:
        """Blocks #7 and #8: irradiation and cooling temporal history.

        A *set* is one Block #7 card (8 integers) followed by one Block #8 card
        (MOUT floats).  Sets are read in a loop until the NGO flag equals 0.

        Returns
        -------
        dict with two keys:

        sets : list[dict]
            Raw set data.  Each dict has keys:
            MMN, MOUT, NGO, MSUB, IUNIT, MFEED, IOUT, IPLOT, TIMES.

        times : list[tuple[float, int]]
            Unified time/type list across *all* sets.
            Each entry is ``(time_value, irradiation_type)`` where
            ``irradiation_type = 1`` for irradiation timesteps (first MMN
            entries of each set) and ``0`` for cooling timesteps (remaining
            MOUT - MMN entries).  Consistent with the convention used in
            generador_acab.py.
        """
        self._ctx = 'Blocks #7/#8 (temporal history)'
        sets: list[dict] = []
        times: list[tuple[float, int]] = []

        while True:
            # Block #7 Card 1 — 8 integers
            mmn, mout, ngo, msub, iunit, mfeed, iout, iplot = self._read_ints(8)

            # Block #8 Card 1 — MOUT real values
            t_vals = self._read_floats(mout)

            sets.append({
                'MMN':   mmn,
                'MOUT':  mout,
                'NGO':   ngo,
                'MSUB':  msub,
                'IUNIT': iunit,
                'MFEED': mfeed,
                'IOUT':  iout,
                'IPLOT': iplot,
                'TIMES': t_vals,
            })

            # Append to unified list: first MMN entries are irradiation (1),
            # the rest are cooling (0).
            for i, t in enumerate(t_vals):
                times.append((t, 1 if i < mmn else 0))

            if ngo == 0:
                break

        return {'sets': sets, 'times': times}

    # ------------------------------------------------------------------
    # Block #9 — Truncation error & flux normalisation
    # ------------------------------------------------------------------

    def _parse_block9(self) -> dict[str, Any]:
        """Block #9: ERR (truncation error) and XNORM (flux scale factor)."""
        self._ctx = 'Block #9 (ERR/XNORM)'
        return {'ERR': self._read_float(), 'XNORM': self._read_float()}

    # ------------------------------------------------------------------
    # Block #10 — Fission products
    # ------------------------------------------------------------------

    def _parse_block10(self) -> dict[str, Any]:
        """Block #10: 3 integers — IGFP, IWFYD, IFORT96."""
        self._ctx = 'Block #10 (fission products)'
        return {
            'IGFP':    self._read_int(),
            'IWFYD':   self._read_int(),
            'IFORT96': self._read_int(),
        }

    # ------------------------------------------------------------------
    # Block #11 — Run type, special responses, and temporal structure
    # ------------------------------------------------------------------

    def _parse_block11(self) -> dict[str, Any]:
        """Block #11: run control.

        Card 1  – always: 10 integers (IWP … IDAMAGE).
        Card 2  – if IDOSE == 1: 4 integers (PH BREM TOT RHOR).
        Card 3  – if IOFFSD != 0: IOFFSD floats (DISTAN).
        Card 4  – if IOFFSD != 0: PODE (float) + ILIFR (int).
        Card 5  – if IOFFSD != 0 and ILIFR != 0: ILIFR pairs (IEL, FL).
        Card 6  – always (after optional cards 2–5): 4 integers
                  NOPUL, NTSEQ, NOTTS, NVFL.
        Card 7  – if NVFL == 1: NOTTS floats (FVAR).
        Card 8  – if NOPUL != 0: 1 integer (NMULT).
        """
        self._ctx = 'Block #11 (run type)'
        b: dict[str, Any] = {}

        # Card 1 — 10 integers
        card1_keys = [
            'IWP', 'IMTX', 'IWDR', 'IDOSE', 'IPHCUT',
            'IDHEAT', 'IOFFSD', 'ICEDE', 'INEMISS', 'IDAMAGE',
        ]
        for key, val in zip(card1_keys, self._read_ints(10)):
            b[key] = val

        # Card 2 — dose output flags.
        # Per the ACAB manual this card is only present when IDOSE == 1, but
        # some files include it even with IDOSE == 0 (non-standard but accepted).
        # We detect its presence by checking whether the upcoming data line is
        # labelled with 'PH' (a label that only appears on the dose_output card).
        if b['IDOSE'] == 1 or 'PH' in self._peek_line_labels():
            ph, brem, tot, rhor = self._read_ints(4)
            b['dose_output'] = {'PH': ph, 'BREM': brem, 'TOT': tot, 'RHOR': rhor}
        else:
            b['dose_output'] = {'PH': 0, 'BREM': 0, 'TOT': 0, 'RHOR': 0}

        # Cards 3–5 — off-site dose (conditional)
        if b['IOFFSD'] != 0:
            b['DISTAN'] = self._read_floats(b['IOFFSD'])   # Card 3
            b['PODE']   = self._read_float()                # Card 4 (part 1)
            b['ILIFR']  = self._read_int()                  # Card 4 (part 2)
            if b['ILIFR'] != 0:                             # Card 5
                b['liberation_fracs'] = [
                    (self._read_int(), self._read_float())
                    for _ in range(b['ILIFR'])
                ]
            else:
                b['liberation_fracs'] = None
        else:
            b['DISTAN'] = None
            b['PODE']   = None
            b['ILIFR']  = None
            b['liberation_fracs'] = None

        # Card 6 — temporal structure (always present)
        b['NOPUL'] = self._read_int()
        b['NTSEQ'] = self._read_int()
        b['NOTTS'] = self._read_int()
        b['NVFL']  = self._read_int()

        # Card 7 — flux scaling per set (conditional)
        b['FVAR'] = self._read_floats(b['NOTTS']) if b['NVFL'] == 1 else None

        # Card 8 — write-every-N-cycles flag (conditional)
        b['NMULT'] = self._read_int() if b['NOPUL'] != 0 else None

        return b

    # ------------------------------------------------------------------
    # Block #12 — Instantaneous feed of material
    # ------------------------------------------------------------------

    def _parse_block12(self, b11: dict) -> dict[str, Any]:
        """Block #12: instantaneous feed.

        Card 1  – IIFD: 0 = none; 1 = ≤1 feed per set; 2 = ≤9 feeds per set.

        When IIFD != 0 additional cards follow:
        Card 2  – NMAIFD : number of different feed materials (max 5).
        Card 3  – IRMAIFD[NMAIFD]: source type per material
                  (1=elements stdin, 2=isotopes stdin, 3=binary UNIT 81).
        Card 4  – NISFDTP : if any IRMAIFD == 3, isotopes per binary record.
        Cards 5,6,7 – element feed composition (if any IRMAIFD == 1).
        Cards 8,9,10 – isotope feed composition (if any IRMAIFD == 2).
        Cards 11,12 – (IIFD == 1) ITFDSET[NOTTS] and IMASET[NOTTS].
        Cards 13,14,15 – (IIFD == 2) NFDSET[NOTTS] and per-set schedules.
        """
        self._ctx = 'Block #12 (instantaneous feed)'
        b: dict[str, Any] = {}
        b['IIFD'] = self._read_int()

        if b['IIFD'] == 0:
            b.update({
                'NMAIFD': None, 'IRMAIFD': None, 'NISFDTP': None,
                'element_feed': None, 'isotope_feed': None,
                'ITFDSET': None, 'IMASET': None,
                'NFDSET': None, 'feed_schedule': None,
            })
            return b

        notts = b11['NOTTS']

        b['NMAIFD']  = self._read_int()                         # Card 2
        b['IRMAIFD'] = self._read_ints(b['NMAIFD'])             # Card 3

        # Card 4 — binary record size (only when some material uses UNIT 81)
        b['NISFDTP'] = self._read_int() if 3 in b['IRMAIFD'] else None

        # Cards 5–7 — element feed composition
        if 1 in b['IRMAIFD']:
            nelfd = self._read_int()
            b['element_feed'] = {
                'NELFD':   nelfd,
                'IELIFD':  self._read_ints(nelfd),
                'XCOMEFD': self._read_floats(nelfd),
            }
        else:
            b['element_feed'] = None

        # Cards 8–10 — isotope feed composition
        if 2 in b['IRMAIFD']:
            nisfd = self._read_int()
            b['isotope_feed'] = {
                'NISFD':    nisfd,
                'IISIFD':   self._read_ints(nisfd),
                'XCOMISFD': self._read_floats(nisfd),
            }
        else:
            b['isotope_feed'] = None

        # Feed schedule
        if b['IIFD'] == 1:
            b['ITFDSET']      = self._read_ints(notts)   # Card 11
            b['IMASET']       = self._read_ints(notts)   # Card 12
            b['NFDSET']       = None
            b['feed_schedule'] = None

        elif b['IIFD'] == 2:
            nfdset = self._read_ints(notts)               # Card 13
            b['NFDSET']  = nfdset
            b['ITFDSET'] = None
            b['IMASET']  = None
            schedule = []
            for n in nfdset:
                if n > 0:                                 # Cards 14 & 15
                    schedule.append({
                        'ITSFDSET': self._read_ints(n),
                        'IMASSET':  self._read_ints(n),
                    })
            b['feed_schedule'] = schedule if schedule else None

        return b

    # ------------------------------------------------------------------
    # Block #13 — Output control (only when IUNC == 0)
    # ------------------------------------------------------------------

    def _parse_block13(self, b1: dict, b11: dict) -> dict[str, Any]:
        """Block #13: output control.

        Card 1 – NCYO (cycles with output) + IFSO (0/1 output for final series).
        Card 2 – ICYO[NCYO]: ordinal cycle numbers; present only when NCYO != 0.
        Card 3 – ITSO[NOTTS]: 0/1 flags controlling output per set.
        """
        self._ctx = 'Block #13 (output control)'
        b: dict[str, Any] = {}
        notts = b11['NOTTS']

        b['NCYO'] = self._read_int()
        b['IFSO'] = self._read_int()

        b['ICYO'] = self._read_ints(b['NCYO']) if b['NCYO'] != 0 else None
        b['ITSO'] = self._read_ints(notts)

        return b

    # ------------------------------------------------------------------
    # Block #14 — Monte Carlo uncertainty (only when IUNC == 1)
    # ------------------------------------------------------------------

    def _parse_block14(self, b1: dict, b11: dict) -> dict[str, Any]:
        """Block #14: Monte Carlo uncertainty parameters.

        Card 1 – 5 integers: NMOHI, NTIMES, NCYU, IFSU, NNUCU.
        Card 2 – ICYU[NCYU]: cycle ordinal numbers; present only when NCYU != 0.
        Card 3 – ITSU[NOTTS]: number of times of interest per set.
        Card 4 – for each non-zero ITSU[i]: ITSU[i] timestep indices.
        Card 5 – INUCU[NNUCU]: nuclide identifiers for concentration uncertainty.
        """
        self._ctx = 'Block #14 (MC uncertainty)'
        b: dict[str, Any] = {}
        notts = b11['NOTTS']

        card1_keys = ['NMOHI', 'NTIMES', 'NCYU', 'IFSU', 'NNUCU']
        for key, val in zip(card1_keys, self._read_ints(5)):
            b[key] = val

        b['ICYU'] = self._read_ints(b['NCYU']) if b['NCYU'] != 0 else None

        itsu = self._read_ints(notts)
        b['ITSU'] = itsu

        b['time_indices'] = [self._read_ints(n) for n in itsu if n > 0]

        b['INUCU'] = self._read_ints(b['NNUCU'])

        return b


# ---------------------------------------------------------------------------
# Quick self-test (run as __main__)
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import json
    import sys

    def _serialise(obj: Any) -> Any:
        """Make tuples JSON-serialisable for pretty-printing."""
        if isinstance(obj, tuple):
            return list(obj)
        if isinstance(obj, dict):
            return {k: _serialise(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_serialise(i) for i in obj]
        return obj

    target = sys.argv[1] if len(sys.argv) > 1 else 'examples/inp.5'
    parser = ACABParser()
    data = parser.read_inp5(target)

    # Summary print
    b1 = data['block1']
    b78 = data['blocks78']
    b11 = data['block11']
    b13 = data['block13']

    print(f"Title   : {b1['title']}")
    print(f"IUNC    : {b1['IUNC']}")
    print(f"IGE     : {b1['IGE']}  IZM={b1['IZM']}  IM={b1['IM']}  JM={b1['JM']}")
    print(f"IFLU    : {b1['IFLU']}  NGRP={b1['NGRP']}  NOGG={b1['NOGG']}")
    print(f"Block 2 XRR   : {data['block2']['XRR']}")
    print(f"Block 2 NUCZO : {data['block2']['NUCZO']}")
    if data['block3']:
        print(f"Block 3 FLUX  : {len(data['block3']['FLUX'])} values")
    if data['block5']:
        for i, z in enumerate(data['block5']):
            print(f"Block 5 zone {i+1}: INUCL={z['INUCL']}")
    print(f"Blocks 7/8 sets : {len(b78['sets'])}")
    print(f"Blocks 7/8 times: {len(b78['times'])} tuples")
    print(f"  first 5 : {b78['times'][:5]}")
    irr  = sum(1 for _, t in b78['times'] if t == 1)
    cool = sum(1 for _, t in b78['times'] if t == 0)
    print(f"  irradiation={irr}  cooling={cool}")
    print(f"Block 11 NOPUL={b11['NOPUL']} NTSEQ={b11['NTSEQ']} "
          f"NOTTS={b11['NOTTS']} NVFL={b11['NVFL']}")
    if b11['FVAR']:
        print(f"Block 11 FVAR  : {len(b11['FVAR'])} values")
    if b13:
        print(f"Block 13 ITSO  : {b13['ITSO']}")
