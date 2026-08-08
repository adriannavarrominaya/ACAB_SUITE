"""fort_analyzer.py — Parsing and analysis engine for ACAB fort.6 / inp.5 files.

"""
from __future__ import annotations

import json
import math
import pathlib
import re
from datetime import datetime
from typing import Any, Optional

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Physical constants
# ─────────────────────────────────────────────────────────────────────────────
N_A = 6.02214076e23   # mol⁻¹
LN2 = math.log(2)

# ¹³¹I gamma spectrum – ENSDF/NNDC  [energy_keV, intensity_%]
GAMMA_I131: list[list[float]] = [
    [80.185,  2.62],
    [163.930, 0.115],
    [177.214, 0.269],
    [240.977, 2.62],
    [272.498, 0.0600],
    [284.305, 6.12],
    [325.789, 0.277],
    [358.969, 0.0610],
    [364.489, 81.5],
    [404.814, 0.0610],
    [503.004, 0.357],
    [636.989, 7.17],
    [722.911, 1.77],
    [772.908, 1.56],
]

# Time unit code → hours  (from inp.5 Block #7/#8 IUNIT field)
_IUNIT_TO_H: dict[int, float] = {
    1: 1.0 / 3600,   # seconds → hours
    2: 1.0 / 60,     # minutes → hours
    3: 1.0,          # hours
    4: 24.0,         # days → hours
    5: 8765.82,      # years → hours
    7: 8.76582e6,    # 10³ yr → hours
    8: 8.76582e9,    # 10⁶ yr → hours
    9: 8.76582e12,   # 10⁹ yr → hours
}

# Unicode superscript digits
_SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

# Atomic number → ACAB element symbol (uppercase, as used in fort.6 keys)
_Z_TO_ELEM: dict[int, str] = {
     1: "H",   2: "HE",  3: "LI",  4: "BE",  5: "B",
     6: "C",   7: "N",   8: "O",   9: "F",  10: "NE",
    11: "NA", 12: "MG", 13: "AL", 14: "SI", 15: "P",
    16: "S",  17: "CL", 18: "AR", 19: "K",  20: "CA",
    21: "SC", 22: "TI", 23: "V",  24: "CR", 25: "MN",
    26: "FE", 27: "CO", 28: "NI", 29: "CU", 30: "ZN",
    31: "GA", 32: "GE", 33: "AS", 34: "SE", 35: "BR",
    36: "KR", 37: "RB", 38: "SR", 39: "Y",  40: "ZR",
    41: "NB", 42: "MO", 43: "TC", 44: "RU", 45: "RH",
    46: "PD", 47: "AG", 48: "CD", 49: "IN", 50: "SN",
    51: "SB", 52: "TE", 53: "I",  54: "XE", 55: "CS",
    56: "BA", 57: "LA", 58: "CE", 59: "PR", 60: "ND",
    61: "PM", 62: "SM", 63: "EU", 64: "GD", 65: "TB",
    66: "DY", 67: "HO", 68: "ER", 69: "TM", 70: "YB",
    71: "LU", 72: "HF", 73: "TA", 74: "W",  75: "RE",
    76: "OS", 77: "IR", 78: "PT", 79: "AU", 80: "HG",
    81: "TL", 82: "PB", 83: "BI", 84: "PO", 85: "AT",
    86: "RN", 87: "FR", 88: "RA", 89: "AC", 90: "TH",
    91: "PA", 92: "U",  93: "NP", 94: "PU", 95: "AM",
    96: "CM",
}

# Default half-lives (from figuras - multiples simulaciones.yaml)
DEFAULT_SEMIVIDAS: dict[str, str] = {
    # Teluro
    "TE120": ".inf",  "TE121": "19.16 d",  "TE121M": "154 d",
    "TE122": ".inf",  "TE123": ".inf",     "TE123M": "119.7 d",
    "TE124": ".inf",  "TE125": ".inf",     "TE125M": "57.40 d",
    "TE126": ".inf",  "TE127": "9.35 h",  "TE127M": "109 d",
    "TE128": ".inf",  "TE129": "69.6 m",  "TE129M": "33.6 d",
    "TE130": ".inf",  "TE131": "25.0 m",  "TE131M": "33.25 h",
    "TE132": "3.204 d", "TE133": "12.5 m", "TE133M": "55.4 m",
    # Xenón
    "XE128": ".inf",  "XE129": ".inf",    "XE129M": "8.89 d",
    "XE130": ".inf",  "XE131": ".inf",    "XE131M": "11.93 d",
    "XE133": "5.247 d", "XE133M": "2.198 d", "XE134": ".inf",
    "XE134M": "0.29 ns", "XE135": "9.14 h", "XE135M": "15.29 m",
    "XE136": ".inf",
    # Yodo
    "I127": ".inf",  "I128": "24.99 m",  "I129": "15.7e6 y",
    "I130": "12.36 h", "I130M": "9.0 m", "I131": "8.0252 d",
    "I132": "2.295 h", "I132M": "83.6 m", "I133": "20.8 h",
    "I134": "52.5 m",
}

# ─────────────────────────────────────────────────────────────────────────────
# Isotope utilities
# ─────────────────────────────────────────────────────────────────────────────

def iso_label(key: str) -> str:
    """Convert ACAB key ('TE121M') to Unicode label ('¹²¹ᵐTe')."""
    m = re.match(r"^([A-Z]{1,2})(\d+)(M?)$", key.upper())
    if not m:
        return key
    elem = m.group(1).capitalize()
    mass = m.group(2).translate(_SUP)
    meta = "ᵐ" if m.group(3) else ""
    return f"{mass}{meta}{elem}"


def parse_t12(val: Any) -> float:
    """Convert half-life value from YAML/string to seconds."""
    if val is None:
        return math.inf
    if isinstance(val, float) and math.isinf(val):
        return math.inf
    s = str(val).strip().lower()
    if s in ("inf", ".inf", "infinity", "estable", "stable"):
        return math.inf
    m = re.match(r"^([0-9.eE+\-]+)\s*([a-zµ]+)$", s)
    if not m:
        raise ValueError(f"Formato de semivida no reconocido: {val!r}")
    num = float(m.group(1))
    unit = m.group(2)
    _f: dict[str, float] = {
        "ns": 1e-9, "µs": 1e-6, "us": 1e-6, "ms": 1e-3,
        "s": 1.0, "m": 60.0, "min": 60.0,
        "h": 3600.0, "d": 86400.0, "y": 365.25 * 86400.0,
    }
    if unit not in _f:
        raise ValueError(f"Unidad de semivida desconocida: {unit!r}")
    return num * _f[unit]


def lam(t12: float) -> float:
    """Decay constant λ = ln2 / T½ [s⁻¹]."""
    if t12 == math.inf or t12 == 0.0:
        return 0.0
    return LN2 / t12


def build_t12_dict(semividas: dict[str, Any]) -> dict[str, float]:
    """Build {iso: t½_s} dict from YAML semividas section."""
    return {iso: parse_t12(val) for iso, val in semividas.items()}


def _safe_val(v: Any) -> Optional[float]:
    """Convert to Python float; replace nan/inf with None for JSON safety."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# DECAY.dat parser  (D2)
# ─────────────────────────────────────────────────────────────────────────────

def leer_decay_dat(filepath: str) -> dict[str, float]:
    """Parse an ACAB DECAY.dat file and return {acab_key: T½_s}.

    File structure — each nuclide occupies 2 lines:
      Line 1:  1  ZZAAAS  ST  T12_s  [other fields ...]
      Line 2:  1  [continuation data — floats, no identifier]

    ZZAAAS encoding (integer field):
      Z  = ZZAAAS // 10000        atomic number
      A  = (ZZAAAS // 10) % 1000  mass number (3 digits)
      S  = ZZAAAS % 10            0 = ground state, 1 = isomeric/metastable

    ST flag:
      6  → stable            → T½ = math.inf
      1  → radioactive       → T½ = T12_s [seconds] (first float column)

    Returns only entries whose Z is in _Z_TO_ELEM and with valid A (1–300).
    Stable nuclides (ST=6 or T12_s=0) are stored as math.inf.
    """
    t12_dict: dict[str, float] = {}

    with open(filepath, "r", errors="ignore") as f:
        for line in f:
            parts = line.split()
            # All data lines start with the record marker "1"
            if len(parts) < 4 or parts[0] != "1":
                continue

            # Second field is the integer nuclide identifier on data lines;
            # continuation lines have a float here (e.g. "0.000E+00") → skip
            try:
                code = int(parts[1])
            except ValueError:
                continue

            # Decode ZZAAAS: smallest valid code is H-1 ground state = 10010
            if code < 10010:
                continue

            S = code % 10
            A = (code // 10) % 1000
            Z = code // 10000

            if A < 1 or A > 300:
                continue

            elem = _Z_TO_ELEM.get(Z)
            if elem is None:
                continue

            acab_key = f"{elem}{A}" + ("M" if S == 1 else "")

            try:
                st    = int(parts[2])
                t12_s = float(parts[3])
            except (ValueError, IndexError):
                continue

            t12_dict[acab_key] = math.inf if (st == 6 or t12_s == 0.0) else t12_s

    return t12_dict


# Reverse of the ZZAAAS codec above (element symbol → Z), used by
# nombre_a_zzaaas (F9 del BACKLOG).
_ELEM_TO_Z: dict[str, int] = {v: k for k, v in _Z_TO_ELEM.items()}


def nombre_a_zzaaas(acab_key: str) -> int:
    """Inverse of the ZZAAAS codec of leer_decay_dat (name → code, F9 del BACKLOG).

    'TE130' -> 521300, 'TE131M' -> 521311 (S=1 para isómeros). Necesario
    para construir IINICIAL/IFINAL del input de CHAINS a partir de un
    isótopo elegido en la UI (nombre ACAB), reutilizando la misma tabla
    Z<->símbolo que la codificación directa — no se define una nueva.
    """
    m = re.match(r"^([A-Z]{1,2})(\d{1,3})(M?)$", acab_key.strip().upper())
    if not m:
        raise ValueError(f"Nombre de isótopo no reconocido: {acab_key!r}")
    elem = m.group(1)
    z = _ELEM_TO_Z.get(elem)
    if z is None:
        raise ValueError(f"Elemento desconocido: {elem!r}")
    a = int(m.group(2))
    s = 1 if m.group(3) else 0
    return z * 10000 + a * 10 + s


# Header line of a PHOTON.dat block: Z (int), symbol+A with optional M
# suffix, number of gamma lines. e.g. " 53   I132M        9".
_PHOTON_HEADER_RE = re.compile(r"^\s*\d+\s+([A-Z]{1,2}\d{1,3}M?)\s+(\d+)\s*$")


def leer_photon_dat(filepath: str) -> dict[str, list[list[float]]]:
    """Parse an ACAB PHOTON.dat gamma-line library (B1 del BACKLOG).

    File structure — blocks of one nuclide each:
      Header:  Z  SYMBOL+A[M]  n_lineas
      Data:    n_lineas pairs (E_MeV, intensidad_%_por_desintegracion),
               3 pairs per text line (last line of a block may have fewer),
               scientific notation. Line endings CRLF in the original
               distribution file; the parser tolerates CRLF/LF either way
               (universal newline mode).

    Returns {acab_key: [[E_keV, intensidad_pct], ...]} — same shape as
    ``GAMMA_I131`` (energies converted MeV→keV, the spectrometry
    convention used everywhere else in the app; intensities left as-is,
    % per decay). Isomers (e.g. "TE131M") are distinct keys from their
    ground state ("TE131"), matching the ACAB naming convention used by
    fort.6. A nuclide with 0 lines in the library (pure beta emitter,
    stable) simply has no entry — callers list it as "sin líneas gamma en
    la librería", never an error (decisión de diseño de B1).
    """
    lineas: dict[str, list[list[float]]] = {}

    with open(filepath, "r", errors="ignore", newline=None) as f:
        text = f.read()

    key: Optional[str] = None
    n_esperado = 0

    for raw_line in text.splitlines():
        m = _PHOTON_HEADER_RE.match(raw_line)
        if m:
            key = m.group(1)
            n_esperado = int(m.group(2))
            lineas[key] = []
            continue

        if key is None:
            continue

        pendientes = n_esperado - len(lineas[key])
        if pendientes <= 0:
            continue

        tokens = raw_line.split()
        for i in range(0, len(tokens) - 1, 2):
            if len(lineas[key]) >= n_esperado:
                break
            try:
                e_mev = float(tokens[i])
                intensidad_pct = float(tokens[i + 1])
            except ValueError:
                continue
            lineas[key].append([e_mev * 1000.0, intensidad_pct])

    return lineas


# ─────────────────────────────────────────────────────────────────────────────
# inp.5 parser
# ─────────────────────────────────────────────────────────────────────────────

def leer_inp5(filepath: str) -> dict:
    """Parse ACAB inp.5 file and extract simulation parameters.

    Returns dict with keys:
        T_IRR_h   float  Total irradiation time [h]
        T_COOL_h  float  Max cooling time [h]
        fluxes    list   Effective fluxes per group × XNORM [n/cm²/s]
        xnorm     float  XNORM scale factor
        phi_total float  Sum of fluxes [n/cm²/s]
        ngrp      int    Number of neutron energy groups
    """
    with open(filepath, "r", errors="ignore") as f:
        raw_lines = f.readlines()

    # Build list of (<marker, data_start, data_end) tuples
    _raw: list[tuple[str, int]] = []
    for i, ln in enumerate(raw_lines):
        if ln.strip().startswith("<"):
            _raw.append((ln.strip()[1:].strip().lower(), i + 1))

    _sections: list[tuple[str, int, int]] = []
    for k, (_marker, _dstart) in enumerate(_raw):
        _dend = _raw[k + 1][1] - 1 if k + 1 < len(_raw) else len(raw_lines)
        _sections.append((_marker, _dstart, _dend))

    def _tokens(dstart: int, dend: int, max_n: int = 300) -> list[float]:
        result: list[float] = []
        for ln in raw_lines[dstart:dend]:
            for tok in ln.split():
                if len(result) >= max_n:
                    return result
                try:
                    result.append(float(tok))
                except ValueError:
                    pass
        return result

    # NGRP from Block #1 card #3 (parameter #11, zero-indexed → index 10)
    ngrp = 2
    for _m, _ds, _de in _sections:
        if "#1" in _m and "card #3" in _m:
            _t = _tokens(_ds, _de)
            if len(_t) >= 11:
                ngrp = int(round(_t[10]))
            break

    # FLUX from Block #3
    raw_fluxes: list[float] = []
    for _m, _ds, _de in _sections:
        if "block #3" in _m or ("flux" in _m and "block" in _m):
            _t = _tokens(_ds, _de)
            raw_fluxes = _t[:ngrp] if len(_t) >= ngrp else _t
            break

    # XNORM from Block #9
    xnorm = 1.0
    for _m, _ds, _de in _sections:
        if "block #9" in _m or ("err" in _m and "xnorm" in _m):
            _t = _tokens(_ds, _de)
            if len(_t) >= 2:
                xnorm = abs(_t[1])
            break

    # Irradiation / cooling history from Blocks #7 / #8
    _B78_KW = (
        "block #7", "block #8", "blocks #7", "blocks #8",
        "block 7", "block 8", "continue",
        "irradiation", "temporal", "cooling",
    )
    _B78_STOP = (
        "block #9", "block #10", "block #11",
        "block 9", "block 10", "block 11",
    )

    t_irr_h = 0.0
    t_cool_h = 0.0

    for _m, _ds, _de in _sections:
        if any(_kw in _m for _kw in _B78_STOP):
            continue
        if not any(_kw in _m for _kw in _B78_KW):
            continue

        _t = _tokens(_ds, _de)
        if len(_t) < 5:
            continue
        try:
            _mmn = int(round(_t[0]))
            _mout = int(round(_t[1]))
            _iunit = int(round(_t[4]))
        except (ValueError, IndexError):
            continue

        _factor = _IUNIT_TO_H.get(_iunit, 1.0)
        _tvs = _t[8: 8 + _mout]

        if _mmn > 0 and len(_tvs) >= _mmn:
            t_irr_h = _tvs[_mmn - 1] * _factor

        _ncool = _mout - _mmn
        if _ncool > 0 and len(_tvs) > _mmn:
            _cool = [v * _factor for v in _tvs[_mmn: _mmn + _ncool]]
            t_cool_h = max(t_cool_h, max(_cool))

    fluxes_eff = [f * xnorm for f in raw_fluxes]
    phi_total = sum(fluxes_eff)

    return {
        "T_IRR_h":   t_irr_h,
        "T_COOL_h":  t_cool_h,
        "fluxes":    fluxes_eff,
        "xnorm":     xnorm,
        "phi_total": phi_total,
        "ngrp":      ngrp,
    }


# ─────────────────────────────────────────────────────────────────────────────
# fort.6 parser – irradiation (NUMBER OF ATOMS section)
# ─────────────────────────────────────────────────────────────────────────────

def leer_fort6_irradiacion(filepath: str) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Parse all NUMBER OF ATOMS (CONCENTRATIONS DURING IRRADIATION BY
    INTERVAL) sections from fort.6, merging every TIME SET that belongs to
    the irradiation phase.

    With F7's Blocks #7/#8 format (irradiation and cooling never share a
    card), an irradiation phase longer than 10 timesteps spans multiple
    cards/TIME SETs, each with its own NUMBER OF ATOMS table: reading only
    the first one (as a single-block parser would) truncates the curve at
    the end of the first card. Mirrors the multi-block merge that
    leer_fort6_enfriamiento already does for the cooling tables.

    Returns:
        t_irr_h   np.ndarray   Time points [h] (t=0 = INITIAL, pre-irradiation)
        datos     dict         {iso: np.ndarray of atoms/cm³}
    """
    with open(filepath, "r", errors="ignore") as f:
        lines = f.readlines()

    # Locate all CONCENTRATIONS DURING IRRADIATION BY INTERVAL / NUMBER OF
    # ATOMS sections (skip the BY ZONE duplicates, same criterion as the
    # cooling parser).
    block_starts: list[int] = []
    for i, l in enumerate(lines):
        if "NUMBER OF ATOMS" in l:
            pre = "".join(lines[max(0, i - 6): i])
            if "BY ZONE" not in pre:
                block_starts.append(i)

    if not block_starts:
        raise ValueError("No se encontró NUMBER OF ATOMS en fort.6")

    t_all: list[float] = []
    data_all: dict[str, list[float]] = {}

    _STOP = ("SUBTOT", "TOTAL")

    for bloque_inicio in block_starts:
        header_line: Optional[int] = None
        for j in range(bloque_inicio, min(bloque_inicio + 20, len(lines))):
            if "INITIAL" in lines[j]:
                header_line = j
                break
        if header_line is None:
            continue

        # Map column tokens to time values. INITIAL is the pre-irradiation
        # t=0, repeated identically at the top of every table (deduped
        # below). RESTART is always a carried-over duplicate of the
        # previous card's last timestep here: unlike cooling's RESTART,
        # the irradiation clock never resets between irradiation-only
        # cards (single-pulse scope, NOPUL=0), so it never marks a new
        # point and is safe to exclude unconditionally.
        col_times: list[Optional[float]] = []
        for tok in lines[header_line].strip().split():
            if tok == "INITIAL":
                col_times.append(0.0)
            elif tok == "RESTART":
                col_times.append(None)
            else:
                try:
                    col_times.append(float(tok))
                except ValueError:
                    col_times.append(None)

        new_idx: list[int] = []
        new_times: list[float] = []
        for k, t in enumerate(col_times):
            if t is not None and t not in t_all:
                new_idx.append(k)
                new_times.append(t)

        if not new_idx:
            continue

        n_cols = len(col_times)
        n_prev = len(t_all)
        t_all += new_times

        i = header_line + 1
        sec_data: dict[str, list[float]] = {}
        while i < len(lines):
            l_str = lines[i]
            stripped = l_str.strip()

            if any(stripped.upper().startswith(kw) for kw in _STOP):
                break
            if "NUCLIDE RADIOACTIVITY" in l_str or "NUCLIDE IDENTIFIERS" in l_str:
                break
            if ". TIME SET" in l_str:
                break
            if i > bloque_inicio + 10 and "NUMBER OF ATOMS" in l_str:
                break

            parts = stripped.split()
            if parts and len(parts) >= n_cols + 1:
                iso_name = parts[0]
                if re.match(r"^[A-Z]{1,2}\d{2,3}M?$", iso_name):
                    try:
                        all_vals = [float(v) for v in parts[1: n_cols + 1]]
                        if len(all_vals) >= n_cols:
                            sec_data[iso_name] = [all_vals[k] for k in new_idx]
                    except (ValueError, IndexError):
                        pass
            i += 1

        for iso, new_vals in sec_data.items():
            if iso not in data_all:
                data_all[iso] = [0.0] * n_prev
            data_all[iso] += new_vals

    t_irr = np.array(t_all)
    datos = {iso: np.array(vals) for iso, vals in data_all.items()}
    return t_irr, datos


# ─────────────────────────────────────────────────────────────────────────────
# fort.6 parser – cooling (NUCLIDE RADIOACTIVITY sections)
# ─────────────────────────────────────────────────────────────────────────────

def leer_fort6_enfriamiento(filepath: str) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Parse all NUCLIDE RADIOACTIVITY BY INTERVAL sections from fort.6.

    Returns:
        t_cool_h   np.ndarray   Time points [h] (t=0 = end of irradiation)
        datos      dict         {iso: np.ndarray of Bq/cm³}
    """
    with open(filepath, "r", errors="ignore") as f:
        lines = f.readlines()

    # Locate all NUCLIDE RADIOACTIVITY BY INTERVAL sections
    block_starts: list[int] = []
    for i, l in enumerate(lines):
        if "NUCLIDE RADIOACTIVITY" in l and "DISINTEGRATIONS" in l:
            pre = "".join(lines[max(0, i - 6): i])
            if "BY ZONE" not in pre:
                block_starts.append(i)

    if not block_starts:
        # Graceful fallback: return empty arrays if section not found
        return np.array([]), {}

    t_all: list[float] = []
    data_all: dict[str, list[float]] = {}

    for bloque_inicio in block_starts:
        # Find header line containing INITIAL/SHUTDOWN/RESTART
        header_line: Optional[int] = None
        for j in range(bloque_inicio + 1, min(bloque_inicio + 20, len(lines))):
            if any(kw in lines[j] for kw in ("INITIAL", "RESTART", "SHUTDOWN")):
                header_line = j
                break
        if header_line is None:
            continue

        # Map column tokens to time values (None = exclude)
        col_times: list[Optional[float]] = []
        for tok in lines[header_line].strip().split():
            if tok == "INITIAL":
                col_times.append(None)
            elif tok in ("SHUTDOWN", "RESTART"):
                # RESTART is ambiguous in ACAB's fort.6: it marks the first
                # column of a new TIME SET's cooling table, which is either
                # the genuine irr->cool transition (t=0, not yet seen -- F7:
                # cards never mix phases, so a cooling-only card right after
                # an irradiation-only card reports this as RESTART instead of
                # SHUTDOWN) or a carried-over duplicate of the previous set's
                # last cooling time (already in t_all). Mapping it to 0.0 lets
                # the dedup below ("t not in t_all") decide which case it is.
                col_times.append(0.0)
            else:
                try:
                    col_times.append(float(tok))
                except ValueError:
                    col_times.append(None)

        # Only new times not yet accumulated
        new_idx: list[int] = []
        new_times: list[float] = []
        for k, t in enumerate(col_times):
            if t is not None and t not in t_all:
                new_idx.append(k)
                new_times.append(t)

        if not new_idx:
            continue

        n_cols = len(col_times)
        n_prev = len(t_all)
        t_all += new_times

        _STOP = (
            "SUBTOT", "TOTAL", "THERMAL", "DOSE", "GAMMA",
            "COMPOSITION", "MAJOR", "NEUTRON", "CHARGED", "PHOTON",
            "GROUP ", ". TIME SET",
        )

        i = header_line + 1
        sec_data: dict[str, list[float]] = {}
        while i < len(lines):
            l_str = lines[i]
            stripped = l_str.strip()

            if any(stripped.upper().startswith(kw.upper()) for kw in _STOP):
                break
            if i > bloque_inicio + 10 and "NUCLIDE RADIOACTIVITY" in l_str:
                break

            parts = stripped.split()
            if parts and len(parts) >= n_cols + 1:
                iso_name = parts[0]
                if re.match(r"^[A-Z]{1,2}\d{2,3}M?$", iso_name):
                    try:
                        all_vals = [float(v) for v in parts[1: n_cols + 1]]
                        if len(all_vals) >= n_cols:
                            sec_data[iso_name] = [all_vals[k] for k in new_idx]
                    except (ValueError, IndexError):
                        pass
            i += 1

        # Accumulate into data_all
        n_new = len(new_times)
        for iso, new_vals in sec_data.items():
            if iso not in data_all:
                data_all[iso] = [0.0] * n_prev
            data_all[iso] += new_vals

        # Fill zeros for isotopes absent in this section
        for iso, vals in data_all.items():
            if len(vals) == n_prev:
                vals += [0.0] * n_new

    if not t_all:
        return np.array([]), {}

    order = sorted(range(len(t_all)), key=lambda k: t_all[k])
    t_cool = np.array([t_all[k] for k in order])
    datos: dict[str, np.ndarray] = {
        iso: np.array([vals[k] for k in order])
        for iso, vals in data_all.items()
        if len(vals) == len(t_all)
    }
    return t_cool, datos


def leer_fort6_concentraciones(filepath: str) -> Optional[dict]:
    """Parse the CONCENTRATIONS(GRAM) section of a fort.6 → material density.

    ACAB prints, per zone/interval, a "MAJOR COMPOSITION CHANGES, WEIGHT
    PERCENTAGE" table under a ``CONCENTRATIONS(GRAM)`` header::

                  INITIAL     COMPOSITION       SHUTDOWN     COMPOSITION
          O     2.4688E-02    2.0044E+01       2.4688E-02    2.0044E+01
         TE     9.8478E-02    7.9956E+01       9.8478E-02    7.9956E+01
         TOTAL  1.2317E-01                     1.2317E-01

    The first numeric column after each element symbol is its mass in grams per
    cm³ of simulated material (INITIAL composition — the weighed target mass,
    which is what MBq/g normalisation refers to). The explicit ``TOTAL`` line
    gives the total density; when absent we fall back to the sum of elements.

    The section is duplicated (BY INTERVAL and BY ZONE) with identical values;
    only the first occurrence is parsed so elements are not double-counted.

    Returns:
        ``{"elementos": {SYM: g_cm3, ...}, "total_g_cm3": float}`` or ``None``
        if the section is not present (older/leaner fort.6 files) — callers must
        treat ``None`` as "density unknown" and keep working.
    """
    try:
        with open(filepath, "r", errors="ignore") as f:
            lines = f.readlines()
    except OSError:
        return None

    # First CONCENTRATIONS(GRAM) header (BY INTERVAL precedes BY ZONE)
    start = next((i for i, l in enumerate(lines) if "CONCENTRATIONS(GRAM)" in l), None)
    if start is None:
        return None

    # Column header of the composition table: has both INITIAL and COMPOSITION
    header_idx = next(
        (i for i in range(start, min(start + 12, len(lines)))
         if "INITIAL" in lines[i].upper() and "COMPOSITION" in lines[i].upper()),
        None,
    )
    if header_idx is None:
        return None

    elementos: dict[str, float] = {}
    total: Optional[float] = None
    for line in lines[header_idx + 1:]:
        toks = line.split()
        if not toks:
            continue
        first = toks[0].upper()
        if first == "TOTAL":
            if len(toks) >= 2:
                try:
                    total = float(toks[1])
                except ValueError:
                    pass
            break  # TOTAL closes the table
        # Element row: 1–2 letter symbol followed by its mass in grams
        if re.fullmatch(r"[A-Za-z]{1,2}", first) and len(toks) >= 2:
            try:
                elementos[first] = float(toks[1])
            except ValueError:
                break  # non-numeric → past the table
        else:
            break  # anything else → past the table

    if not elementos and total is None:
        return None
    if total is None:
        total = float(sum(elementos.values()))
    return {"elementos": elementos, "total_g_cm3": total}


# ─────────────────────────────────────────────────────────────────────────────
# CHAINS (F9 del BACKLOG): inventario isotópico inicial + parser del output
# ─────────────────────────────────────────────────────────────────────────────

def leer_concentraciones_iniciales(filepath: str) -> dict[str, float]:
    """Inventario isotópico inicial (t=0, INITIAL CONCENTRATIONS) del fort.6.

    Es el desglose por isótopos que ACAB genera al expandir un ELEMID
    (Bloque #5) con las abundancias naturales de la librería; fuente de
    verdad para el patch monoisotópico de F9 del BACKLOG. Lee solo la
    columna INITIAL de la PRIMERA tabla NUMBER OF ATOMS (t=0, idéntica en
    todas las tarjetas del formato F7 — no hace falta fusionar varios
    bloques como leer_fort6_irradiacion, que además NO sirve aquí:
    esa función solo reconoce isótopos con símbolo+masa pegados en un único
    token ("TE130"), pero el fort.6 separa símbolo y masa en dos tokens
    para elementos de una letra ("O 16", "H  1") — se perdería el O del
    blanco TeO2. Este parser combina ambos formatos de columna.

    Returns:
        {acab_key: C_i} en átomos/cm³, solo isótopos con C_i > 0 (los que
        de verdad componen el blanco; el resto de la tabla son productos
        de activación en t=0, siempre nulos).
    """
    with open(filepath, "r", errors="ignore") as f:
        lines = f.readlines()

    inicio: Optional[int] = None
    for i, l in enumerate(lines):
        if "NUMBER OF ATOMS" in l:
            pre = "".join(lines[max(0, i - 6): i])
            if "BY ZONE" not in pre:
                inicio = i
                break
    if inicio is None:
        raise ValueError(f"fort.6 sin sección NUMBER OF ATOMS: {filepath!r}")

    header_line = next(
        (j for j in range(inicio, min(inicio + 20, len(lines))) if "INITIAL" in lines[j]),
        None,
    )
    if header_line is None:
        raise ValueError(f"fort.6 sin columna INITIAL en NUMBER OF ATOMS: {filepath!r}")

    idx_initial = lines[header_line].strip().split().index("INITIAL")

    _STOP = ("SUBTOT", "TOTAL")
    concentraciones: dict[str, float] = {}
    for i in range(header_line + 1, len(lines)):
        l_str = lines[i]
        stripped = l_str.strip()

        if any(stripped.upper().startswith(kw) for kw in _STOP):
            break
        if "NUCLIDE RADIOACTIVITY" in l_str or "NUCLIDE IDENTIFIERS" in l_str:
            break
        if ". TIME SET" in l_str:
            break
        if i > header_line + 10 and "NUMBER OF ATOMS" in l_str:
            break

        parts = stripped.split()
        if not parts:
            continue

        if (len(parts) >= 3 and re.fullmatch(r"[A-Z]{1,2}", parts[0])
                and re.fullmatch(r"\d{1,3}M?", parts[1])):
            # Elemento de UNA letra: símbolo y masa en tokens separados
            # ("O" + "16") por la anchura fija de columnas del fort.6.
            iso_name = parts[0] + parts[1]
            vals = parts[2:]
        elif re.match(r"^[A-Z]{1,2}\d{1,3}M?$", parts[0]):
            iso_name = parts[0]
            vals = parts[1:]
        else:
            continue

        if len(vals) <= idx_initial:
            continue
        try:
            c_i = float(vals[idx_initial])
        except ValueError:
            continue
        if c_i > 0.0:
            concentraciones[iso_name] = c_i

    return concentraciones


# Detalle de un paso de cadena: "NUCLIDO (PROCESO)   NUCLIDO   XSEC=valor" o
# "...DELTA=valor". El símbolo puede o no llevar espacio antes del "(" según
# la anchura fija de columnas de CHAINS (p. ej. "TE130 (N,G-g)" vs.
# "TE131M(B-)"), de ahí el \s* opcional. F9e (hermano de C6 del BACKLOG):
# el ORIGEN puede llevar además un espacio inicial de relleno de columna
# cuando el símbolo del elemento es de una letra (p. ej. " I129 (N,G-g)"
# para yodo) -- de ahí el ^\s* al principio (antes ^ sin más, que hacía
# fallar el match y truncaba la cadena justo antes de llegar a I131).
_CHAIN_STEP_RE = re.compile(
    r"^\s*(\S+?)\s*\(([^)]+)\)\s+(\S+)\s+(XSEC|DELTA)=\s*([0-9.DEde+\-]+)\s*$"
)


def leer_output_chains(filepath: str) -> dict:
    """Parsea el output de ``chains.exe`` (IFLAG=2, F9 del BACKLOG).

    Estructura del fichero:
      - Cabecera con IFLAG, INITIAL/IFINAL (códigos ZZAAAS), NMAX, PCNT.
      - NCHAIN: nº total de cadenas encontradas (antes del corte por PCNT).
      - NCH: nº de cadenas por encima de PCNT (las únicas detalladas) y
        PTOT — ver nota de normalización abajo, PTOT NO es siempre 100.
      - Un bloque por cadena superviviente, delimitado por líneas de
        asteriscos: "P=" (probabilidad relativa, %), la ruta compacta
        (redundante, no se parsea) y el detalle paso a paso
        ("NUCLIDO (PROCESO)   NUCLIDO   XSEC=..." o "...DELTA=...";
        XSEC en capturas, DELTA en decaimientos).

    OJO normalización (F9e del BACKLOG, corrige la nota original de F9 que
    asumía PTOT=100 siempre a partir de un único caso real, TE130→I131):
    PTOT es la probabilidad TOTAL (en %) de que un núcleo de INITIAL
    acabe en IFINAL por CUALQUIERA de las cadenas encontradas — NO una
    constante de renormalización. Puede ser ≈100 (TE130→I131: casi todo
    el TE130 activado acaba en I131, ``output_chain_Te130_to_I131.txt``)
    o muy pequeña (TE128→I131: PTOT=0.02304 %, ``output_chain_
    TE128_to_I131.txt`` — la mayoría del TE128 no llega a I131 en ≤ NMAX
    pasos). El "P=" de CADA cadena, en cambio, sí es SIEMPRE un porcentaje
    normalizado a 100 entre las cadenas devueltas (Σ_z P ≈ 100 en ambos
    fixtures, incluida la cola descartada por debajo de PCNT si NCH <
    NCHAIN) — por eso X_z_i = P/100 (Fase 4, ``calcular_analisis_cadenas``)
    es válido sea cual sea PTOT. No confundir ambas magnitudes en la UI.

    OJO forma sin cadenas (F9d del BACKLOG, detectado en la primera
    ejecución real: O16/O17/O18, sin camino físico O→I131 en <= NMAX
    pasos): CHAINS no escribe NCHAIN/NCH/PTOT ni ningún bloque de cadena
    en este caso, solo la cabecera y el literal "THERE ARE NO PATHWAYS FOR
    FORMATION OF NUCLIDE IFINAL" (ver tests/fixtures/chains/
    output_chain_no_pathways_O16.txt). Se detecta por ese literal y se
    devuelve nchain=nch=0, ptot=0.0, cadenas=[] — nunca lanza por los
    campos ausentes en esta forma concreta.

    Returns:
        {"iflag", "inicial", "ifinal", "nmax", "pcnt", "nchain", "nch",
         "ptot", "cadenas": [{"p": float, "pasos": [
             {"desde", "proceso", "hasta", "xsec": float|None,
              "delta": float|None}, ...]}, ...]}
    """
    with open(filepath, "r", errors="ignore") as f:
        text = f.read()

    def _num(s: str) -> float:
        return float(s.replace("D", "E").replace("d", "e"))

    def _campo(patron: str) -> float:
        m = re.search(patron, text)
        if not m:
            raise ValueError(f"Campo no encontrado en {filepath!r}: {patron!r}")
        return _num(m.group(1))

    _flt = r"([0-9.DEde+\-]+)"
    iflag   = int(round(_campo(rf"\bIFLAG\s*=\s*{_flt}")))
    inicial = int(round(_campo(rf"\bINITIAL\s*=\s*{_flt}")))
    ifinal  = int(round(_campo(rf"\bIFINAL\s*=\s*{_flt}")))
    nmax    = int(round(_campo(rf"\bNMAX\s*=\s*{_flt}")))
    pcnt    = _campo(rf"\bPCNT\s*=\s*{_flt}")

    if "NO PATHWAYS FOR FORMATION OF NUCLIDE" in text:
        return {
            "iflag": iflag, "inicial": inicial, "ifinal": ifinal,
            "nmax": nmax, "pcnt": pcnt,
            "nchain": 0, "nch": 0, "ptot": 0.0,
            "cadenas": [],
        }

    nchain  = int(round(_campo(rf"\bNCHAIN\s*=\s*{_flt}")))
    nch     = int(round(_campo(rf"\bNCH\s*=\s*{_flt}")))
    ptot    = _campo(rf"\bPTOT\s*=\s*{_flt}")

    lines = text.splitlines()
    sep_idx = [i for i, l in enumerate(lines) if re.fullmatch(r"\*{5,}", l.strip())]

    # La última cadena NO cierra con una línea separadora propia (el fichero
    # pasa directo a "****** JOB FINISHED ******", que no es una línea de
    # asteriscos puros): el último bloque llega hasta el final del fichero.
    cadenas: list[dict] = []
    for a, b in zip(sep_idx, sep_idx[1:] + [len(lines)]):
        p_val: Optional[float] = None
        pasos: list[dict] = []
        for l in lines[a + 1: b]:
            mp = re.match(r"^P=\s*([0-9.DEde+\-]+)\s*$", l.strip())
            if mp:
                p_val = _num(mp.group(1))
                continue
            ms = _CHAIN_STEP_RE.match(l.rstrip())
            if ms:
                desde, proceso, hasta, tag, val = ms.groups()
                paso = {"desde": desde, "proceso": proceso, "hasta": hasta,
                        "xsec": None, "delta": None}
                paso[tag.lower()] = _num(val)
                pasos.append(paso)
        if p_val is not None and pasos:
            cadenas.append({"p": p_val, "pasos": pasos})

    return {
        "iflag": iflag, "inicial": inicial, "ifinal": ifinal,
        "nmax": nmax, "pcnt": pcnt,
        "nchain": nchain, "nch": nch, "ptot": ptot,
        "cadenas": cadenas,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Simulation discovery
# ─────────────────────────────────────────────────────────────────────────────

_CHAINS_TAPE_FOLDERS = {"tape22", "tape24"}


def descubrir_simulaciones(folder: str) -> list[tuple[str, str]]:
    """Return list of (sim_name, fort6_path) for subfolders containing fort.6.

    Also accepts the folder itself if it directly contains fort.6 (single sim).

    F9d del BACKLOG (ruido de tapes): si *folder* es la raíz de un análisis
    de cadenas (contiene ``chains_manifest.json``), ``tape22``/``tape24``
    (los runs IWP=3/IMTX=1 de ``chains_analysis.py``) se excluyen del
    descubrimiento — su fort.6 no tiene sección NUMBER OF ATOMS (no es su
    propósito, ver DECAY.dat/fort.6 de esos runs) y su rol ya está descrito
    en el manifest, no en una tabla de simulaciones. Sin esta exclusión,
    analizar la carpeta raíz del análisis desde la pestaña normal de
    "Simulaciones" generaba el aviso "No se encontró NUMBER OF ATOMS" por
    cada una — ruido que entrena a ignorar avisos reales.
    """
    base = pathlib.Path(folder)
    if not base.exists():
        raise FileNotFoundError(f"La carpeta no existe: {folder}")

    sims: list[tuple[str, str]] = []

    # Check if fort.6 lives directly in the given folder (single-sim mode)
    if (base / "fort.6").exists():
        sims.append((base.name, str(base / "fort.6")))
        return sims

    excluir = _CHAINS_TAPE_FOLDERS if (base / "chains_manifest.json").exists() else set()

    # Otherwise scan subfolders
    for sub in sorted(base.iterdir()):
        if sub.name in excluir:
            continue
        f6 = sub / "fort.6"
        if sub.is_dir() and f6.exists():
            sims.append((sub.name, str(f6)))

    return sims


def leer_sweep_manifest(folder: str) -> Optional[dict]:
    """Read ``sweep_manifest.json`` from *folder* (the analysed root), if present.

    Written by the ACAB INP File Configurator's sweep generator (RUNBOOK_
    barrido_parametrico_v2, Fase 2): ``{timestamp, sweep_type, description,
    fixed_params, n, simulations: [{folder, params}, ...]}``. Optional feature
    — returns None (folder without a sweep behaves exactly as before) if the
    file is missing or unreadable.
    """
    path = pathlib.Path(folder) / "sweep_manifest.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Full analysis
# ─────────────────────────────────────────────────────────────────────────────

def analizar_carpeta(
    folder: str,
    t12_dict: dict[str, float],
    leer_inp5_flag: bool = True,
    t_irr_override: Optional[float] = None,
    t_cool_override: Optional[float] = None,
    phi_override: Optional[float] = None,
    yaml_t12_overrides: Optional[dict[str, float]] = None,
) -> tuple[dict, dict[str, str]]:
    """Perform full analysis of a simulations folder.

    *t12_dict* is the FALLBACK T½ library (lowest priority — typically
    DEFAULT_SEMIVIDAS), used only for isotopes a simulation's own DECAY.dat
    doesn't resolve. F13 del BACKLOG: each simulation's own ``DECAY.dat``
    (next to its ``fort.6``) is read INDEPENDENTLY and takes priority over
    *t12_dict* — before this fix, a single T½ library (the first
    simulation's ``DECAY.dat``, or the fallback) was applied to every
    simulation in the folder, even when others carried a different one
    (verified: v2/v3/v4 of the reference experiment ship 693 200 s for
    I-131, not the 693 400 s of the built-in default). *yaml_t12_overrides*
    (highest priority — explicit user overrides from the YAML ``semividas``
    section) applies identically to every simulation, same as before.
    Final priority per simulation: yaml_t12_overrides > su propio
    DECAY.dat > t12_dict (fallback).

    Returns:
        all_data   dict   {sim_name: sim_dict} with JSON-serialisable values
        errors     dict   {sim_name: error_message} for failed simulations

    Each ``sim_dict`` carries ``t12_source`` (``"decay_dat"``|``"default"``)
    and ``decay_dat_path`` (str|None) declaring where ITS T½ library came
    from, plus a private ``_t12_dict`` (the resolved per-simulation library,
    used by ``calcular_informe_isotopo`` for saturación/actividad específica
    — callers must strip it before sending a sim dict over the API, see
    app.py's ``/api/analyze``).
    """
    sims = descubrir_simulaciones(folder)
    if not sims:
        raise ValueError(f"No se encontró ninguna subcarpeta con fort.6 en '{folder}'")

    yaml_over = yaml_t12_overrides or {}

    all_data: dict = {}
    errors: dict[str, str] = {}

    for sim_name, fort6_path in sims:
        try:
            t_irr_arr, datos_irr = leer_fort6_irradiacion(fort6_path)
            t_cool_arr, datos_cool = leer_fort6_enfriamiento(fort6_path)

            # F13 del BACKLOG: T½ library resolved PER SIMULATION — this
            # sim's own DECAY.dat (next to its fort.6) wins over the
            # fallback; yaml_over (explicit, same for every sim) wins over
            # both.
            own_decay_path = pathlib.Path(fort6_path).parent / "DECAY.dat"
            own_t12: dict[str, float] = {}
            t12_source = "default"
            decay_dat_path: Optional[str] = None
            if own_decay_path.is_file():
                try:
                    own_t12 = leer_decay_dat(str(own_decay_path))
                    t12_source = "decay_dat"
                    decay_dat_path = str(own_decay_path)
                except (OSError, ValueError):
                    own_t12 = {}
            t12_sim = {**t12_dict, **own_t12, **yaml_over}

            # Material density (g/cm³) for MBq/g normalisation — None if the
            # CONCENTRATIONS(GRAM) section is missing, without breaking analysis.
            conc = leer_fort6_concentraciones(fort6_path)
            densidad_g_cm3 = conc["total_g_cm3"] if conc else None

            # Convert atoms/cm³ → Bq/cm³  (A = λ·N), with THIS simulation's
            # own T½ library (t12_sim, F13 del BACKLOG). datos_irr_atomos
            # keeps the raw atom counts too (F2 del BACKLOG: stable isotopes
            # have λ=0, so datos_irr_Bq alone loses their population — needed
            # for the iodine specific-activity dilution metric).
            datos_irr_Bq: dict[str, list[float]] = {}
            datos_irr_atomos: dict[str, list[float]] = {}
            for iso, N in datos_irr.items():
                t12 = t12_sim.get(iso, math.inf)
                datos_irr_Bq[iso] = (lam(t12) * N).tolist()
                datos_irr_atomos[iso] = N.tolist()

            # Fase R5: mtime de fort.6 y de inp.5 (si existe), para detectar
            # resultados desactualizados (inp.5 editado después de generar el fort.6).
            fort6_mtime = pathlib.Path(fort6_path).stat().st_mtime
            inp5_path = pathlib.Path(fort6_path).parent / "inp.5"
            inp5_mtime = inp5_path.stat().st_mtime if inp5_path.exists() else None
            desactualizada = bool(inp5_mtime is not None and inp5_mtime > fort6_mtime)

            # Simulation parameters
            if leer_inp5_flag and inp5_path.exists():
                p = leer_inp5(str(inp5_path))
                T_IRR_h  = t_irr_override  if t_irr_override  is not None else p["T_IRR_h"]
                T_COOL_h = t_cool_override if t_cool_override is not None else p["T_COOL_h"]
                PHI      = phi_override    if phi_override    is not None else p["phi_total"]
                fluxes   = p["fluxes"]
                ngrp     = p["ngrp"]
                xnorm    = p.get("xnorm", 1.0)
                inp5_found = True
            else:
                T_IRR_h  = t_irr_override  or (float(t_irr_arr[-1])  if len(t_irr_arr)  > 0 else 0.0)
                T_COOL_h = t_cool_override or (float(t_cool_arr[-1]) if len(t_cool_arr) > 0 else 0.0)
                PHI      = phi_override or 0.0
                fluxes   = [PHI] if PHI else []
                ngrp     = 1
                xnorm    = 1.0
                inp5_found = False

            all_data[sim_name] = {
                "t_irr":        t_irr_arr.tolist(),
                "datos_irr_Bq": datos_irr_Bq,
                "datos_irr_atomos": datos_irr_atomos,
                "t_cool":       t_cool_arr.tolist(),
                "datos_cool":   {iso: arr.tolist() for iso, arr in datos_cool.items()},
                "T_IRR_h":      float(T_IRR_h),
                "T_COOL_h":     float(T_COOL_h),
                "PHI":          float(PHI),
                "fluxes":       [float(f) for f in fluxes],
                "ngrp":         int(ngrp),
                "xnorm":        float(xnorm),
                "fort6_path":   str(fort6_path),
                "inp5_found":   bool(inp5_found),
                "densidad_g_cm3": (float(densidad_g_cm3)
                                   if densidad_g_cm3 is not None else None),
                "fort6_fecha":    datetime.fromtimestamp(fort6_mtime).isoformat(timespec="seconds"),
                "desactualizada": desactualizada,
                # F13 del BACKLOG: procedencia del T½ aplicado a ESTA simulación.
                "t12_source":     t12_source,
                "decay_dat_path": decay_dat_path,
                # Privado (nunca al frontend, ver docstring): usado por
                # calcular_informe_isotopo para saturación/actividad
                # específica con el T½ propio de esta simulación.
                "_t12_dict":      t12_sim,
            }

        except Exception as exc:
            errors[sim_name] = str(exc)

    return all_data, errors


# ─────────────────────────────────────────────────────────────────────────────
# Analysis helpers
# ─────────────────────────────────────────────────────────────────────────────

def actividad_en_t(sim: dict, t_target: float, iso_key: str) -> float:
    """Interpolate activity of iso_key at t_target [h] for a simulation."""
    T_irr = sim["T_IRR_h"]
    t_irr = np.array(sim["t_irr"])
    t_cool = np.array(sim["t_cool"])
    A_irr  = np.array(sim["datos_irr_Bq"].get(iso_key, np.zeros(len(t_irr))))
    A_cool = np.array(sim["datos_cool"].get(iso_key,   np.zeros(len(t_cool))))

    t_all = np.concatenate([t_irr, T_irr + t_cool])
    A_all = np.concatenate([A_irr, A_cool])

    if len(t_all) == 0 or math.isnan(t_target):
        return 0.0
    return float(np.interp(t_target, t_all, A_all))


def calcular_pico(sim: dict, iso_key: str) -> dict:
    """Return peak activity info for iso_key in a simulation."""
    T_irr = sim["T_IRR_h"]
    t_irr = np.array(sim["t_irr"])
    t_cool = np.array(sim["t_cool"])
    A_irr  = np.array(sim["datos_irr_Bq"].get(iso_key, np.zeros(len(t_irr))))
    A_cool = np.array(sim["datos_cool"].get(iso_key,   np.zeros(len(t_cool))))

    t_all = np.concatenate([t_irr, T_irr + t_cool])
    A_all = np.concatenate([A_irr, A_cool])

    if len(A_all) > 0 and A_all.max() > 0:
        idx = int(np.argmax(A_all))
        t_pico = float(t_all[idx])
        A_pico = float(A_all[idx])
        fase = "irradiación" if t_pico <= T_irr else "enfriamiento"
    else:
        t_pico = math.nan
        A_pico = 0.0
        fase = "n/a"

    return {"t_pico": _safe_val(t_pico), "A_pico": A_pico, "fase": fase}


_MASS_RE = re.compile(r"[A-Z]+(\d+)")
_ELEM_RE = re.compile(r"^([A-Z]{1,2})(\d+)M?$")


# ─────────────────────────────────────────────────────────────────────────────
# Production-optimisation metrics (Fase 5)
# ─────────────────────────────────────────────────────────────────────────────

def calcular_saturacion(sim: dict, iso_key: str, t12_dict: dict[str, float]) -> Optional[dict]:
    """Theoretical saturation curve during irradiation: A_teo(t) = A_sat·(1−e^(−λt)).

    ``A_sat`` is anchored so the curve matches the ACAB value at the end of
    irradiation: ``A_sat = A_ACAB(T_irr)/(1−e^(−λ·T_irr))``. Also returns the
    times to reach 50/75/90/95 % of saturation, flagging which fit within the
    simulation's actual T_irr.

    Requires a finite, positive T½ (stable isotopes / isotopes without a known
    half-life have no saturation curve) and T_irr > 0. Returns None otherwise.
    """
    t12 = t12_dict.get(iso_key, math.inf)
    lam_iso = lam(t12)
    T_irr = sim["T_IRR_h"]
    t_irr = np.array(sim["t_irr"])
    if lam_iso <= 0 or T_irr <= 0 or len(t_irr) == 0:
        return None

    lam_h = lam_iso * 3600.0  # λ was s⁻¹ (t_irr is in hours)
    denom = 1.0 - math.exp(-lam_h * T_irr)
    if denom <= 0:
        return None

    A_fin = actividad_en_t(sim, T_irr, iso_key)
    A_sat = A_fin / denom

    puntos = [[float(tv), float(A_sat * (1.0 - math.exp(-lam_h * tv)))] for tv in t_irr]

    tabla = []
    for pct in (0.50, 0.75, 0.90, 0.95):
        t_x = -math.log(1.0 - pct) / lam_h
        tabla.append({
            "pct":        pct * 100,
            "t_x_h":      _safe_val(t_x),
            "alcanzable": bool(t_x <= T_irr),
        })

    return {"A_sat": _safe_val(A_sat), "puntos": puntos, "tabla": tabla}


def calcular_rendimiento(sim: dict, iso_key: str) -> Optional[dict]:
    """Production yield: mean activity produced per hour of irradiation
    (A_pico/T_irr) and the marginal yield of the last 10 % of the irradiation
    tramo, to answer "does it pay off to keep irradiating?".

    Returns None if T_irr is not positive (nothing to divide by).
    """
    T_irr = sim["T_IRR_h"]
    if T_irr <= 0:
        return None

    A_pico = calcular_pico(sim, iso_key)["A_pico"]
    rendimiento_medio = A_pico / T_irr if A_pico > 0 else 0.0

    A_fin = actividad_en_t(sim, T_irr, iso_key)
    A_90  = actividad_en_t(sim, 0.9 * T_irr, iso_key)
    ganancia_marginal = (A_fin - A_90) / (0.1 * T_irr)

    return {
        "rendimiento_medio":  _safe_val(rendimiento_medio),
        "A_fin":              _safe_val(A_fin),
        "ganancia_marginal":  _safe_val(ganancia_marginal),
        "compensa_seguir":    bool(ganancia_marginal >= rendimiento_medio),
    }


def isotopos_mismo_elemento(iso_key: str, isotopos_disponibles) -> list[str]:
    """Isotope keys from *isotopos_disponibles* that share the element of iso_key.

    Default definition of "impurities" for the radionuclidic-purity metric:
    after radiochemical separation, the product contains only the target
    element, so the relevant impurities are its other isotopes (for I131:
    I130, I132, I133... whichever are present in the fort.6). Configurable
    from the UI — this is only the default.
    """
    m = _ELEM_RE.match(iso_key.upper())
    if not m:
        return [iso_key]
    elem = m.group(1)
    return sorted(
        k for k in isotopos_disponibles
        if (mk := _ELEM_RE.match(k.upper())) and mk.group(1) == elem
    )


def calcular_pureza(
    sim: dict,
    iso_key: str,
    t_pico: Optional[float],
    isotopos_impureza: list[str],
) -> Optional[dict]:
    """Radionuclidic purity at t_pico: P = A(target)/Σ A(isotopos_impureza), in %.

    *isotopos_impureza* is the full set of isotopes considered in the
    denominator (must include iso_key itself); by default the same-element
    isotopes present in the fort.6 (see isotopos_mismo_elemento), editable
    from the UI. Returns None if t_pico is unknown or the total activity is
    non-positive (nothing meaningful to divide by).
    """
    if t_pico is None or not isotopos_impureza:
        return None

    contribuciones = []
    total = 0.0
    A_obj = 0.0
    for iso in isotopos_impureza:
        A = actividad_en_t(sim, t_pico, iso)
        contribuciones.append({"iso": iso, "label": iso_label(iso), "A": _safe_val(A)})
        total += A
        if iso == iso_key:
            A_obj = A

    if total <= 0:
        return None

    for c in contribuciones:
        c["pct"] = _safe_val(c["A"] / total * 100.0) if c["A"] is not None else None

    return {
        "P_pct":         _safe_val(A_obj / total * 100.0),
        "t_pico":        _safe_val(t_pico),
        "contribuciones": contribuciones,
    }


# F1 (runbook_F1_pureza_temporal.md): umbral farmacéutico validado.
UMBRAL_PUREZA_PCT = 99.9


def _interp_loglinear(frac: float, a0: float, a1: float) -> float:
    """Interpolate an activity at *frac* in [0,1] between two timesteps.

    Log-linear (exponential decay/growth is linear in ln A vs t) when both
    endpoints are positive; falls back to linear when either is zero (ln
    undefined) — negligible in practice since that only happens for isotopes
    with no contribution yet.
    """
    if a0 > 0 and a1 > 0:
        return a0 * (a1 / a0) ** frac
    return a0 + (a1 - a0) * frac


def _pureza_en_frac(frac: float, iso_key: str, A0: dict[str, float], A1: dict[str, float]) -> Optional[float]:
    total = 0.0
    obj = 0.0
    for iso, a0 in A0.items():
        a = _interp_loglinear(frac, a0, A1[iso])
        total += a
        if iso == iso_key:
            obj = a
    return (obj / total * 100.0) if total > 0 else None


def _resolver_cruce_loglineal(
    t0: float, t1: float, iso_key: str,
    A0: dict[str, float], A1: dict[str, float],
    umbral_pct: float,
) -> float:
    """Bisect for the instant in [t0, t1] where P(t) == umbral_pct.

    Activities are interpolated log-linearly (see runbook decision); P(t) is
    derived from those interpolated activities at each trial point, never
    interpolated directly.
    """
    lo, hi = 0.0, 1.0
    p_hi = _pureza_en_frac(hi, iso_key, A0, A1)
    if p_hi is None or p_hi < umbral_pct:
        return t1  # no root in range (caller's bracket assumption failed) — report t1 as-is
    for _ in range(60):
        mid = (lo + hi) / 2.0
        p_mid = _pureza_en_frac(mid, iso_key, A0, A1)
        if p_mid is None or p_mid < umbral_pct:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-9:
            break
    frac_sol = (lo + hi) / 2.0
    return t0 + frac_sol * (t1 - t0)


def calcular_pureza_serie(
    sim: dict,
    iso_key: str,
    isotopos_impureza: list[str],
    umbral_pct: float = UMBRAL_PUREZA_PCT,
) -> Optional[dict]:
    """Radionuclidic purity P(t) = A(iso_key,t)/Σ A(isotopos_impureza,t) through
    the whole cooling phase (t=0 = end of irradiation, RESTART/SHUTDOWN).

    Returns the real timestep-by-timestep series plus the threshold-crossing
    instant (*t_cruce*) and the administration window (activity of iso_key at
    that instant, and as a fraction of its simulation peak). *isotopos_impureza*
    follows the same convention as calcular_pureza (full denominator set,
    normally including iso_key). Returns None if there is no impurity list or
    no cooling data at all.

    t_cruce cases:
      - already >= umbral_pct at t=0 → t_cruce=0, not interpolated (real point).
      - crossed between two real timesteps → log-linear interpolation of each
        isotope's activity (never of P directly), estimado=True.
      - never reached in the simulated cooling window → t_cruce=None,
        estado="no_alcanzado" (no extrapolation past the last timestep).

    Does not assume monotonicity: after locating the first crossing, checks
    that every later real timestep stays >= umbral_pct; the first violation
    (if any) is reported in *aviso_no_monotono* for the caller to render.
    """
    if not isotopos_impureza:
        return None
    t_cool = np.asarray(sim["t_cool"], dtype=float)
    if len(t_cool) == 0:
        return None

    A_iso = {
        iso: np.asarray(sim["datos_cool"].get(iso, np.zeros(len(t_cool))), dtype=float)
        for iso in isotopos_impureza
    }
    A_total = np.sum(list(A_iso.values()), axis=0)
    A_obj = A_iso.get(iso_key, np.zeros(len(t_cool)))

    P_vals: list[Optional[float]] = [
        (float(a_obj) / float(a_tot) * 100.0) if a_tot > 0 else None
        for a_obj, a_tot in zip(A_obj, A_total)
    ]
    serie = [
        {"t": float(t), "P_pct": _safe_val(p)}
        for t, p in zip(t_cool, P_vals)
    ]

    idx_cruce: Optional[int] = None
    for i, p in enumerate(P_vals):
        if p is not None and p >= umbral_pct:
            idx_cruce = i
            break

    estado: str
    t_cruce_info: Optional[dict] = None
    A_obj_cruce: Optional[float] = None

    if idx_cruce is None:
        estado = "no_alcanzado"
    elif idx_cruce == 0:
        estado = "alcanzado_en_fin_irradiacion"
        A_obj_cruce = float(A_obj[0])
        t_cruce_info = {"t_h": 0.0, "estimado": False}
    else:
        estado = "alcanzado_en_enfriamiento"
        t0, t1 = float(t_cool[idx_cruce - 1]), float(t_cool[idx_cruce])
        A0 = {iso: float(arr[idx_cruce - 1]) for iso, arr in A_iso.items()}
        A1 = {iso: float(arr[idx_cruce]) for iso, arr in A_iso.items()}
        t_c = _resolver_cruce_loglineal(t0, t1, iso_key, A0, A1, umbral_pct)
        frac = (t_c - t0) / (t1 - t0) if t1 > t0 else 1.0
        A_obj_cruce = _interp_loglinear(frac, A0.get(iso_key, 0.0), A1.get(iso_key, 0.0))
        t_cruce_info = {"t_h": _safe_val(t_c), "estimado": True}

    aviso_no_monotono: Optional[dict] = None
    if idx_cruce is not None:
        for j in range(idx_cruce + 1, len(P_vals)):
            if P_vals[j] is None or P_vals[j] < umbral_pct:
                aviso_no_monotono = {"t_h": float(t_cool[j]), "P_pct": _safe_val(P_vals[j])}
                break

    ventana_administracion: Optional[dict] = None
    if t_cruce_info is not None:
        A_pico = calcular_pico(sim, iso_key)["A_pico"]
        ventana_administracion = {
            "t_cruce_h":     t_cruce_info["t_h"],
            "A_objetivo":    _safe_val(A_obj_cruce),
            "A_pico":        _safe_val(A_pico),
            "fraccion_pico": _safe_val(A_obj_cruce / A_pico) if A_pico > 0 and A_obj_cruce is not None else None,
        }

    return {
        "serie":                  serie,
        "umbral_pct":             umbral_pct,
        "estado":                 estado,
        "t_cruce":                t_cruce_info,
        "aviso_no_monotono":      aviso_no_monotono,
        "ventana_administracion": ventana_administracion,
    }


#  I127 is stable (λ=0, DECAY.dat 531270 → T12=.inf) and I129 is long-lived
#  (T12≈1.57e7 y, DECAY.dat 531290 / NNDC). Neither is safe to recover via
#  N(t)=A(t)/λ FROM ITS OWN activity: fort.6 prints activities with ~4-5
#  significant figures, and dividing a value that small by a λ that tiny
#  (I129) — or by λ=0 at all (I127) — amplifies that print rounding into an
#  atom count with no reliable precision.
#
#  F2b del BACKLOG (2026-07-21, bug confirmado): froze both at their
#  end-of-irradiation NUMBER OF ATOMS count instead. F14 del BACKLOG
#  (2026-08-08, bug confirmado): that "frozen" design is itself wrong — I127
#  and I129 keep GROWING during cooling, fed by the decay of their own
#  precursors (Te127/Te127M → I127; Te129/Te129M → I129). Verified on the
#  reference case of experiment 1 (v3): I129 grows ×1077 during cooling vs.
#  the ×429 of I131, and I127 (stable, zero activity) is completely
#  invisible from the activity tables — freezing it gives a specific
#  activity of 4.5928e9 MBq/g (99.9 % of the carrier-free ceiling) at 3.75 h,
#  vs. the physically correct 2.210e9 MBq/g (48.1 %); a factor 2.1 error.
#
#  Fixed WITHOUT reviving the F2b numerical-instability problem: instead of
#  A(t)/λ on I127/I129's OWN (unreliable) activity, `_evolucionar_diluyente`
#  propagates the decay of every OTHER isotope sharing the SAME mass number
#  (isobar) from the end-of-irradiation NUMBER OF ATOMS table — Te127/
#  Te127M/Te129/Te129M all have ordinary half-lives, so N(t)=A(t)/λ on
#  THEIR cooling activity is exact and well-conditioned. Mass-number
#  conservation along a β⁻/IT decay chain (no particle emission, no more
#  neutron flux once cooling starts) makes this EXACT, not an
#  approximation: total atoms of a fixed isobar is constant, so whatever a
#  precursor loses, the stable/long-lived end of the chain gains — with no
#  need to know the branching structure (IT vs. β⁻) at all.
IODINE_ESTABLE_O_VIDA_LARGA = {"I127", "I129"}


def _evolucionar_diluyente(
    sim: dict,
    target_iso: str,
    t12_dict: dict[str, float],
    t_cool: np.ndarray,
) -> np.ndarray:
    """N(target_iso, t) during cooling for a stable/very-long-lived iodine
    isotope (F14 del BACKLOG) — its own activity is either zero (stable) or
    too small/imprecise to invert via A(t)/λ, so it is derived instead from
    mass-number conservation over every OTHER isotope sharing its mass
    number (its isobaric precursors), each recovered from ITS OWN cooling
    activity (well-conditioned — see IODINE_ESTABLE_O_VIDA_LARGA above):

        N_target(t) = N_target(EOI) + Σ_precursores [N_prec(EOI) − N_prec(t)]

    A precursor with no cooling activity series left (fully decayed away
    before RESTART, so ACAB stops tracking it) decays analytically from its
    EOI population instead — still exact, just not grounded in a printed
    ACAB value. A precursor with unknown/zero λ (its own T½ unresolved or
    itself stable) contributes nothing (nothing decays out of it).
    """
    datos_cool = sim.get("datos_cool", {})
    datos_irr_atomos = sim.get("datos_irr_atomos", {})

    m_target = _MASS_RE.search(target_iso)
    target_A = int(m_target.group(1)) if m_target else None

    n0_target = float(datos_irr_atomos[target_iso][-1]) if target_iso in datos_irr_atomos else 0.0
    N_t = np.full(len(t_cool), n0_target, dtype=float)
    if target_A is None:
        return N_t

    for prec, atomos in datos_irr_atomos.items():
        if prec == target_iso:
            continue
        m_prec = _MASS_RE.search(prec)
        if not m_prec or int(m_prec.group(1)) != target_A:
            continue  # not the same isobar — cooling has no more transmutation
        n0_prec = float(atomos[-1]) if len(atomos) else 0.0
        if n0_prec <= 0:
            continue
        lam_prec = lam(t12_dict.get(prec, math.inf))
        if lam_prec <= 0:
            continue  # precursor itself stable/unknown T½ — nothing decays out
        if prec in datos_cool:
            N_prec_t = np.asarray(datos_cool[prec], dtype=float) / lam_prec
        else:
            # λ is s⁻¹, t_cool is in HOURS (repo convention, e.g.
            # calcular_saturacion's lam_h) — convert before exp(-λt).
            lam_prec_h = lam_prec * 3600.0
            N_prec_t = n0_prec * np.exp(-lam_prec_h * t_cool)
        N_t = N_t + np.maximum(n0_prec - N_prec_t, 0.0)

    return N_t


def calcular_actividad_especifica_yodo_serie(
    sim: dict,
    iso_key: str,
    t12_dict: dict[str, float],
    t_destacado_h: Optional[float] = None,
) -> Optional[dict]:
    """Iodine specific activity A_esp(t) = A(iso_key,t) / m(yodo_total,t) [MBq/g],
    through the whole cooling phase (F2 del BACKLOG, 2026-07-09; denominador
    corregido en F2b, 2026-07-21, y de nuevo en F14, 2026-08-08). Same
    domain/family as ``calcular_pureza_serie`` (F1).

    Stable ¹²⁷I and long-lived ¹²⁹I do not spoil radionuclidic purity (they
    share no activity with the impurity isotopes counted by
    ``calcular_pureza``), but they DILUTE the product: the same becquerels of
    the target isotope spread over more grams of total iodine. m(yodo_total,t)
    sums every iodine isotope present in the fort.6:

      - ``IODINE_ESTABLE_O_VIDA_LARGA`` (I127, I129): evolved through cooling
        via ``_evolucionar_diluyente`` — mass-number conservation over their
        isobaric precursors (Te127/Te127M → I127; Te129/Te129M → I129), each
        recovered from ITS OWN cooling activity (well-conditioned, unlike
        I127/I129's). F14 del BACKLOG (2026-08-08, bug confirmado): F2b froze
        both at the end-of-irradiation NUMBER OF ATOMS value instead —
        wrong, they keep growing fed by precursor decay (verified: I129
        grows ×1077 during cooling on the reference case of experiment 1,
        vs. the ×429 of I131; freezing gave 99.9 % of the carrier-free
        ceiling at 3.75 h instead of the correct 48.1 %).
      - Every other iodine isotope with a cooling activity series and λ > 0
        (I131, I128, I130, I130M, I132, I132M...): N(t) = A(t)/λ at each
        timestep, exact recovery of ACAB's internal atom population — no
        approximation, correctly reflects feeding from parent decay.
      - Anything with neither (no cooling series and not in the atoms
        table): contributes 0.

    Atoms → grams uses the mass number as an approximate molar mass (error
    < 0.1 %, documented). ``leer_fort6_concentraciones``/CONCENTRATIONS(GRAM)
    is never usable here: it only reports the target's own starting elements
    (O, Te for TeO2), never a decay product like iodine.

    *t_destacado_h*, if given (normally ``pureza_serie``'s ``t_cruce``),
    highlights A_esp interpolated at that instant — "what specific activity
    does the product have when it reaches pharmaceutical purity". Returns
    None if iso_key is not an iodine isotope, there is no cooling data, or no
    iodine isotope at all is present in the fort.6.
    """
    m_key = _ELEM_RE.match(iso_key.upper())
    if not m_key or m_key.group(1) != "I":
        return None

    t_cool = np.asarray(sim["t_cool"], dtype=float)
    if len(t_cool) == 0:
        return None

    datos_cool = sim.get("datos_cool", {})
    datos_irr_atomos = sim.get("datos_irr_atomos", {})

    iodine_isos = {
        iso for iso in set(datos_cool) | set(datos_irr_atomos)
        if (mk := _ELEM_RE.match(iso.upper())) and mk.group(1) == "I"
    }
    if not iodine_isos:
        return None

    masa_total = np.zeros(len(t_cool))
    for iso in iodine_isos:
        mk = _ELEM_RE.match(iso.upper())
        A_num = int(mk.group(2))
        lam_iso = lam(t12_dict.get(iso, math.inf))

        if iso not in IODINE_ESTABLE_O_VIDA_LARGA and iso in datos_cool and lam_iso > 0:
            N_t = np.asarray(datos_cool[iso], dtype=float) / lam_iso
        elif iso in IODINE_ESTABLE_O_VIDA_LARGA:
            # F14 del BACKLOG: evoluciona por decaimiento de precursores,
            # nunca congelado en el valor de EOI.
            N_t = _evolucionar_diluyente(sim, iso, t12_dict, t_cool)
        else:
            atomos_irr = datos_irr_atomos.get(iso)
            n0 = float(atomos_irr[-1]) if atomos_irr else 0.0
            N_t = np.full(len(t_cool), n0)

        masa_total += N_t / N_A * A_num

    A_obj = np.asarray(datos_cool.get(iso_key, np.zeros(len(t_cool))), dtype=float)
    aesp_vals: list[Optional[float]] = [
        (float(a) / float(m) / 1e6) if m > 0 else None
        for a, m in zip(A_obj, masa_total)
    ]
    serie = [
        {"t": float(t), "A_esp_MBq_g": _safe_val(v)}
        for t, v in zip(t_cool, aesp_vals)
    ]

    valor_destacado: Optional[float] = None
    if t_destacado_h is not None and serie and all(p["A_esp_MBq_g"] is not None for p in serie):
        ts = [p["t"] for p in serie]
        vs = [p["A_esp_MBq_g"] for p in serie]
        valor_destacado = _safe_val(float(np.interp(t_destacado_h, ts, vs)))

    return {
        "serie":                serie,
        "unidad":               "MBq/g",
        "t_destacado_h":        _safe_val(t_destacado_h),
        "valor_destacado_MBq_g": valor_destacado,
    }


def calcular_espectro_gamma(sim: dict, t_h: float, libreria: dict[str, list[list[float]]]) -> dict:
    """Emission line spectrum at a cooling instant (Fase 2 de B1, espectro
    gamma de la muestra desde PHOTON.dat).

    Combines the fort.6 cooling inventory (``datos_cool``, Bq/cm³) at the
    real cooling timestep closest to *t_h* with the PHOTON.dat gamma-line
    library (``leer_photon_dat``): for every nuclide present with nonzero
    activity at that instant, each of its library lines contributes an
    emission rate tasa = A_nuclido(t) × intensidad/100 [fotones/(s·cm³)] —
    same internal per-cm³ unit as every activity in this module; converting
    to per-gram is a frontend concern (``static/js/units.js``, como en F1),
    not duplicated here.

    Nuclides with activity but no entry in *libreria* (pure beta emitters,
    stable, or simply missing from the library extract) are listed in
    ``nucleidos_sin_lineas`` — an informational fact, never an error
    (decisión de diseño B1: "sin líneas gamma en la librería").

    Returns ``{"t_h": <timestep real más cercano>, "lineas": [...],
    "nucleidos_sin_lineas": [...]}``. If the simulation has no cooling data,
    all three come back empty/None.
    """
    t_cool = np.asarray(sim.get("t_cool", []), dtype=float)
    if len(t_cool) == 0:
        return {"t_h": None, "lineas": [], "nucleidos_sin_lineas": []}

    idx = int(np.argmin(np.abs(t_cool - t_h)))
    t_real = float(t_cool[idx])

    datos_cool = sim.get("datos_cool", {})
    lineas: list[dict] = []
    sin_lineas: set[str] = set()

    for iso, serie_iso in datos_cool.items():
        if idx >= len(serie_iso):
            continue
        A_t = float(serie_iso[idx])
        if A_t <= 0:
            continue
        entradas = libreria.get(iso)
        if not entradas:
            sin_lineas.add(iso)
            continue
        for e_kev, intensidad_pct in entradas:
            lineas.append({
                "E_keV":              e_kev,
                "nucleido":           iso,
                "intensidad_pct":     intensidad_pct,
                "tasa_fotones_s_cm3": A_t * intensidad_pct / 100.0,
            })

    return {
        "t_h":                 t_real,
        "lineas":              lineas,
        "nucleidos_sin_lineas": sorted(sin_lineas),
    }


def calcular_informe_isotopo(
    all_data: dict,
    isotopo_key: str,
    t12_dict: dict[str, float],
    isotopos_impureza: Optional[list[str]] = None,
) -> dict:
    """Build full report for any isotope across all simulations.

    Returns gamma_spectrum only for I131 (ENSDF data available); empty list otherwise.
    Also returns, per simulation, the Fase 5 optimisation metrics (saturation
    curve, yield, radionuclidic purity). *isotopos_impureza*, if given,
    overrides the default same-element isotope list used for the purity
    metric (UI-editable; see isotopos_mismo_elemento).

    F13 del BACKLOG: *t12_dict* is only the REFERENCE/fallback library, used
    for the top-level ``nuclear_props`` (a single descriptive block, kept for
    backward compatibility) — every actual per-simulation computation
    (saturación, actividad específica del yodo) uses THAT simulation's own
    resolved library (``sim["_t12_dict"]``, set by ``analizar_carpeta``,
    falling back to *t12_dict* for callers that built ``all_data`` some other
    way, e.g. the synthetic sims of some tests). Each simulation's own T½ for
    *isotopo_key* — the source of the "techo sin portador" reference — is
    also exposed per simulation as ``metricas[sim].nuclear_props``.
    """
    t12_iso = t12_dict.get(isotopo_key, math.inf)
    lam_iso = lam(t12_iso)

    # Derive mass number A from key (e.g. "I131" → 131, "TE132" → 132)
    m = _MASS_RE.search(isotopo_key)
    A = int(m.group(1)) if m else 1
    A_esp = (lam_iso * N_A / A) if (A > 0 and lam_iso > 0) else 0.0

    isotopos_disponibles: set[str] = set()
    for sim in all_data.values():
        isotopos_disponibles |= set(sim["datos_irr_Bq"].keys()) | set(sim["datos_cool"].keys())
    impureza_default = isotopos_mismo_elemento(isotopo_key, isotopos_disponibles)
    impureza_list = isotopos_impureza if isotopos_impureza else impureza_default

    sim_reports: dict[str, dict] = {}
    metricas: dict[str, dict] = {}
    for sim_name, sim in all_data.items():
        # F13 del BACKLOG: T½ propio de ESTA simulación (su DECAY.dat, si lo
        # tiene) — nunca el de otra simulación de la misma carpeta.
        t12_sim = sim.get("_t12_dict") or t12_dict
        t12_iso_sim = t12_sim.get(isotopo_key, math.inf)
        lam_iso_sim = lam(t12_iso_sim)
        A_esp_sim = (lam_iso_sim * N_A / A) if (A > 0 and lam_iso_sim > 0) else 0.0

        pico = calcular_pico(sim, isotopo_key)
        sim_reports[sim_name] = pico
        pureza_serie = calcular_pureza_serie(sim, isotopo_key, impureza_list)
        t_cruce_h = (pureza_serie["t_cruce"]["t_h"]
                     if pureza_serie and pureza_serie.get("t_cruce") else None)
        metricas[sim_name] = {
            "saturacion":   calcular_saturacion(sim, isotopo_key, t12_sim),
            "rendimiento":  calcular_rendimiento(sim, isotopo_key),
            "pureza":       calcular_pureza(sim, isotopo_key, pico["t_pico"], impureza_list),
            "pureza_serie": pureza_serie,
            "actividad_especifica_yodo_serie": calcular_actividad_especifica_yodo_serie(
                sim, isotopo_key, t12_sim, t_cruce_h),
            # F13 del BACKLOG: T½/λ/A_esp ("techo sin portador") con el T½
            # propio de esta simulación — puede diferir de nuclear_props
            # (arriba, de referencia) si su DECAY.dat trae un valor distinto.
            "nuclear_props": {
                "T12_s":  _safe_val(t12_iso_sim),
                "T12_d":  _safe_val(t12_iso_sim / 86400),
                "T12_h":  _safe_val(t12_iso_sim / 3600),
                "lam_s":  _safe_val(lam_iso_sim),
                "A_esp":  _safe_val(A_esp_sim),
                "t12_source": sim.get("t12_source", "default"),
            },
        }

    return {
        "nuclear_props": {
            "T12_s":  _safe_val(t12_iso),
            "T12_d":  _safe_val(t12_iso / 86400),
            "T12_h":  _safe_val(t12_iso / 3600),
            "lam_s":  _safe_val(lam_iso),
            "A_esp":  _safe_val(A_esp),
        },
        "gamma_spectrum": GAMMA_I131 if isotopo_key == "I131" else [],
        "simulations":    sim_reports,
        "metricas":       metricas,
        "isotopos_disponibles":     sorted(isotopos_disponibles),
        "isotopos_impureza_default": impureza_default,
        "isotopos_impureza_usada":   impureza_list,
    }


def calcular_informe_i131(all_data: dict, t12_dict: dict[str, float]) -> dict:
    """Backward-compatible alias → calcular_informe_isotopo for I131."""
    return calcular_informe_isotopo(all_data, "I131", t12_dict)


def calcular_tablas_comparativas(
    all_data: dict,
    semividas_keys: list[str],
    referencia: str = "I131",
) -> tuple[dict, dict]:
    """Build comparison tables 1 and 2 using *referencia* isotope as the anchor.

    Table 1: all isotopes at the instant of *referencia* peak.
    Table 2: individual peak of each isotope + *referencia* activity at that moment.

    JSON keys use generic names ("t_pico_ref", "A_pico_ref", "A_ref_en") so the
    frontend can adapt the column headers dynamically from the isotope name.
    """
    tabla1: dict = {}
    tabla2: dict = {}

    for sim_name, sim in all_data.items():
        pk_ref = calcular_pico(sim, referencia)
        t_pico_ref = pk_ref["t_pico"]
        A_pico_ref = pk_ref["A_pico"]

        # ── Table 1 ─────────────────────────────────────────────────────────
        rows1: list[dict] = []
        for iso in semividas_keys:
            if t_pico_ref is not None:
                A_iso = actividad_en_t(sim, t_pico_ref, iso)
            else:
                A_iso = 0.0
            rows1.append({
                "iso":   iso,
                "label": iso_label(iso),
                "A":     _safe_val(A_iso),
                "ratio": _safe_val(A_iso / A_pico_ref) if A_pico_ref > 0 else None,
            })
        tabla1[sim_name] = {
            "rows":       rows1,
            "t_pico_ref": _safe_val(t_pico_ref),
            "A_pico_ref": _safe_val(A_pico_ref),
        }

        # ── Table 2 ─────────────────────────────────────────────────────────
        T_irr  = sim["T_IRR_h"]
        t_irr  = np.array(sim["t_irr"])
        t_cool = np.array(sim["t_cool"])

        rows2: list[dict] = []
        for iso in semividas_keys:
            A_irr_arr  = np.array(sim["datos_irr_Bq"].get(iso, np.zeros(len(t_irr))))
            A_cool_arr = np.array(sim["datos_cool"].get(iso,   np.zeros(len(t_cool))))
            t_all_ = np.concatenate([t_irr, T_irr + t_cool])
            A_all_ = np.concatenate([A_irr_arr, A_cool_arr])

            if len(A_all_) > 0 and A_all_.max() > 0:
                idx_p   = int(np.argmax(A_all_))
                t_pico_ = float(t_all_[idx_p])
                A_pico_ = float(A_all_[idx_p])
                A_ref_  = actividad_en_t(sim, t_pico_, referencia)
            else:
                t_pico_ = math.nan
                A_pico_ = 0.0
                A_ref_  = 0.0

            rows2.append({
                "iso":      iso,
                "label":    iso_label(iso),
                "A_pico":   _safe_val(A_pico_),
                "t_pico":   _safe_val(t_pico_),
                "A_ref_en": _safe_val(A_ref_),
            })
        tabla2[sim_name] = {"rows": rows2}

    return tabla1, tabla2


# ─────────────────────────────────────────────────────────────────────────────
# F9 del BACKLOG, Fase 4 — análisis de contribución por cadenas (tablas)
# ─────────────────────────────────────────────────────────────────────────────

def leer_chains_manifest(root: str) -> Optional[dict]:
    """Lee ``chains_manifest.json`` de *root* (carpeta del análisis de
    cadenas generada por ``ACAB_inp_file_configurator/chains_analysis.py``).

    ``None`` si no existe o no es JSON válido — mismo criterio que
    ``leer_sweep_manifest``.
    """
    path = pathlib.Path(root) / "chains_manifest.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _chain_label(cadena: dict) -> str:
    """'TE128->(N,G-m)->TE129M->(N,G-g)->TE130->(N,G-g)->TE131->(B-)->I131'
    a partir de los pasos de una cadena de CHAINS.

    F9e del BACKLOG: incluye el PROCESO de cada paso, no solo los nombres
    de nucleido — dos cadenas pueden compartir la misma secuencia de
    nucleidos y diferir solo en el proceso de algún paso (p. ej. una
    captura directa NUCLIDO(N,G-g) frente a una vía el isómero metaestable
    NUCLIDO(N,G-m)), y la etiqueta solo con nombres no las distingue en la
    Tabla 2.
    """
    pasos = cadena.get("pasos") or []
    if not pasos:
        return ""
    partes = [pasos[0]["desde"]]
    for p in pasos:
        partes.append(f"({p['proceso']})")
        partes.append(p["hasta"])
    return "->".join(partes)


def _nodo_diagrama(nombre: str, t12_dict: dict[str, float]) -> dict:
    """Info de un nodo del diagrama de cadena (Fase 5): nombre + T½.

    ``estable=True`` (T½ = math.inf en DECAY.dat) y ``conocido=False`` (el
    nucleido no está en DECAY.dat) son casos distintos: el primero muestra
    "estable" en la UI, el segundo "T½ desconocido" — no se confunden.
    """
    t12 = t12_dict.get(nombre)
    if t12 is None:
        return {"nombre": nombre, "t12_s": None, "estable": False, "conocido": False}
    if t12 == math.inf:
        return {"nombre": nombre, "t12_s": None, "estable": True, "conocido": True}
    return {"nombre": nombre, "t12_s": float(t12), "estable": False, "conocido": True}


def construir_diagrama_cadena(cadena: dict, t12_dict: dict[str, float]) -> dict:
    """F9 del BACKLOG, Fase 5 — diagrama lineal (v1) de UNA cadena ya
    seleccionada: secuencia de nodos (nombre + T½ de DECAY.dat) unidos por
    aristas etiquetadas con el proceso y su XSEC (capturas) o DELTA
    (decaimientos), tal cual del output de CHAINS (``leer_output_chains``).

    El grafo fusionado estilo Fig. 1 del paper (varias cadenas superpuestas)
    queda fuera de alcance v1 (F9b del BACKLOG) — aquí solo se representa la
    cadena YA elegida por el usuario, como secuencia lineal.
    """
    pasos = cadena.get("pasos") or []
    nombres = ([pasos[0]["desde"]] + [p["hasta"] for p in pasos]) if pasos else []
    nodos = [_nodo_diagrama(n, t12_dict) for n in nombres]
    aristas = [
        {
            "desde":   p["desde"],
            "hasta":   p["hasta"],
            "proceso": p["proceso"],
            "xsec":    _safe_val(p.get("xsec")),
            "delta":   _safe_val(p.get("delta")),
        }
        for p in pasos
    ]
    return {"nodos": nodos, "aristas": aristas, "p": cadena.get("p")}


NOTA_CHAINS_ILEGIBLE = "salida de CHAINS ilegible/sin cadenas"


def calcular_analisis_cadenas(root: str, t_h: Optional[float] = None,
                               manifest: Optional[dict] = None) -> dict:
    """F9 del BACKLOG, Fase 4 — tablas de contribución por isótopo (R_i) y
    por cadena (Y_z_i = R_i·X_z_i) de un análisis ya generado y (al menos
    parcialmente) ejecutado por ``chains_analysis.py``.

    R_i = A_i(IFINAL, t*) / A_ref(IFINAL, t*): A_i viene del fort.6
    monoisotópico de cada isótopo (``iso_<nombre>/``), A_ref del fort.6 de
    la carpeta de referencia (fuera de *root*, apuntada por el manifest).
    t* por defecto es el t_pico de IFINAL en la referencia (selector de
    instante, mismo patrón que la pestaña "Espectro gamma"). X_z_i sale del
    output de CHAINS de cada isótopo (``chains_<nombre>/output_chain.txt``,
    ``leer_output_chains``): X_z_i = P_z_i / 100.

    Degradación POR ISÓTOPO (F9d del BACKLOG, hotfix tras la primera
    ejecución real): un isótopo cuyo fort.6 monoisotópico aún no existe
    (pipeline no ejecutado) se omite ENTERO de la tabla 1 — sin ese fort.6
    no hay R_i que mostrar. Pero un isótopo con fort.6 ya listo cuyo
    ``output_chain.txt`` está ausente o no se puede parsear (corrupto,
    forma inesperada) conserva su fila de tabla 1 intacta (R_i sigue siendo
    un dato físico válido) con ``nota_cadenas`` = ``NOTA_CHAINS_ILEGIBLE``;
    solo sus filas de tabla 2 se omiten. El caso "output_chain.txt legible
    pero sin ninguna cadena por debajo de NMAX" (p. ej. O16/O17/O18: no hay
    camino físico O→I131, ``leer_output_chains`` devuelve ``cadenas=[]``)
    NO es un error — R_i se muestra igual (≈0, coherente físicamente) sin
    nota, y la tabla 2 simplemente no tiene filas de ese isótopo. Ningún
    fallo de un isótopo aislado debe impedir que se muestre el resto del
    informe.

    *manifest*, si se pasa, sustituye la lectura de ``chains_manifest.json``
    de *root* (usado por los tests oro con fixtures sintéticos, donde el
    manifest se ajusta en memoria antes de calcular).
    """
    root_p = pathlib.Path(root)
    if manifest is None:
        manifest = leer_chains_manifest(root)
    if manifest is None:
        raise ValueError(f"No se encontró chains_manifest.json en '{root}'")

    ref_folder = pathlib.Path(manifest["reference_folder"])
    if not ref_folder.is_absolute():
        ref_folder = root_p / ref_folder
    ref_fort6 = ref_folder / "fort.6"
    if not ref_fort6.is_file():
        raise ValueError(f"No se encontró fort.6 en la carpeta de referencia '{ref_folder}'")

    decay_path = ref_folder / "DECAY.dat"
    t12_dict = leer_decay_dat(str(decay_path)) if decay_path.is_file() else {}

    ifinal = str(manifest["ifinal"]).strip().upper()

    ref_all, ref_errors = analizar_carpeta(str(ref_folder), t12_dict)
    if not ref_all:
        raise ValueError(f"No se pudo analizar la referencia '{ref_folder}': {ref_errors}")
    ref_sim = next(iter(ref_all.values()))

    t_pico_ref = calcular_pico(ref_sim, ifinal)["t_pico"]
    if t_h is None:
        t_star = t_pico_ref if t_pico_ref is not None else 0.0
        t_star_fuente = "pico_referencia"
    else:
        t_star = float(t_h)
        t_star_fuente = "manual"

    a_ref = actividad_en_t(ref_sim, t_star, ifinal)

    inventario_inicial = leer_concentraciones_iniciales(str(ref_fort6))
    isotopos = manifest.get("isotopes") or []
    nombres_sel = {str(iso["name"]).strip().upper() for iso in isotopos}

    tabla1: list[dict] = []
    tabla2: list[dict] = []
    for iso in isotopos:
        name = str(iso["name"]).strip().upper()
        iso_folder = root_p / iso["iso_folder"]
        iso_fort6 = iso_folder / "fort.6"
        if not iso_fort6.is_file():
            continue

        iso_all, _ = analizar_carpeta(str(iso_folder), t12_dict)
        if not iso_all:
            continue
        iso_sim = next(iter(iso_all.values()))
        a_i = actividad_en_t(iso_sim, t_star, ifinal)
        r_i = (a_i / a_ref) if a_ref else None

        tabla1.append({
            "isotopo": name,
            "c_i":     _safe_val(iso.get("c_i")),
            "a_i":     _safe_val(a_i),
            "a_ref":   _safe_val(a_ref),
            "r_i":     _safe_val(r_i),
            "nota_cadenas": None,
        })

        chains_folder = root_p / iso["chains_folder"]
        output_path = chains_folder / "output_chain.txt"
        try:
            if not output_path.is_file():
                raise FileNotFoundError(str(output_path))
            chains_data = leer_output_chains(str(output_path))
        except (OSError, ValueError):
            tabla1[-1]["nota_cadenas"] = NOTA_CHAINS_ILEGIBLE
            continue
        for z_idx, cadena in enumerate(chains_data["cadenas"], start=1):
            x_z_i = cadena["p"] / 100.0
            y_z_i = (r_i * x_z_i) if r_i is not None else None
            tabla2.append({
                "isotopo":      name,
                "cadena_idx":   z_idx,
                "cadena_label": _chain_label(cadena),
                "p":            _safe_val(cadena["p"]),
                "x_z_i":        _safe_val(x_z_i),
                "r_i":          _safe_val(r_i),
                "y_z_i":        _safe_val(y_z_i),
                "nmax":         chains_data["nmax"],
                "pcnt":         chains_data["pcnt"],
                "ptot":         _safe_val(chains_data["ptot"]),
                "diagrama":     construir_diagrama_cadena(cadena, t12_dict),
            })

    tabla2.sort(key=lambda f: (f["y_z_i"] if f["y_z_i"] is not None else -1.0), reverse=True)

    suma_r_i = sum(f["r_i"] for f in tabla1 if f["r_i"] is not None)

    t_cool = ref_sim.get("t_cool") or []
    T_irr = ref_sim.get("T_IRR_h") or 0.0
    t_candidatos = sorted({0.0}
                           | {float(v) for v in (ref_sim.get("t_irr") or [])}
                           | {float(T_irr) + float(v) for v in t_cool})

    return {
        "root":             str(root_p),
        "reference_folder": str(ref_folder),
        "ifinal":           ifinal,
        "pcnt":             manifest.get("pcnt"),
        "nmax":             manifest.get("nmax"),
        "t_star_h":         _safe_val(t_star),
        "t_star_fuente":    t_star_fuente,
        "t_pico_referencia_h": _safe_val(t_pico_ref),
        "t_candidatos_h":   t_candidatos,
        "a_ref":            _safe_val(a_ref),
        "tabla1":           tabla1,
        "suma_r_i":         _safe_val(suma_r_i),
        "cobertura": {
            "n_seleccionados":     len(isotopos),
            "n_total_inventario":  len(inventario_inicial),
            "completa":            nombres_sel >= set(inventario_inicial.keys()),
        },
        "tabla2": tabla2,
    }
