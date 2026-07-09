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

# Default figure groups
DEFAULT_FIGURAS: list[dict] = [
    {"num": 1,  "titulo": "¹³¹I (irr. + enf.)",          "mostrar_irr": True,  "series": [{"iso": "I131",   "label": "¹³¹I"}]},
    {"num": 2,  "titulo": "¹³³Xe / ¹³³ᵐXe",              "mostrar_irr": False, "series": [{"iso": "XE133",  "label": "¹³³Xe"},  {"iso": "XE133M", "label": "¹³³ᵐXe"}]},
    {"num": 3,  "titulo": "¹³²Te",                        "mostrar_irr": False, "series": [{"iso": "TE132",  "label": "¹³²Te"}]},
    {"num": 4,  "titulo": "¹³¹ᵐTe / ¹³¹Te",              "mostrar_irr": False, "series": [{"iso": "TE131M", "label": "¹³¹ᵐTe"}, {"iso": "TE131", "label": "¹³¹Te"}]},
    {"num": 5,  "titulo": "¹³³I",                         "mostrar_irr": False, "series": [{"iso": "I133",   "label": "¹³³I"}]},
    {"num": 6,  "titulo": "¹³⁵Xe / ¹³⁵ᵐXe",              "mostrar_irr": False, "series": [{"iso": "XE135",  "label": "¹³⁵Xe"},  {"iso": "XE135M", "label": "¹³⁵ᵐXe"}]},
    {"num": 7,  "titulo": "¹²⁹ᵐXe",                      "mostrar_irr": False, "series": [{"iso": "XE129M", "label": "¹²⁹ᵐXe"}]},
    {"num": 8,  "titulo": "¹³¹ᵐXe",                      "mostrar_irr": False, "series": [{"iso": "XE131M", "label": "¹³¹ᵐXe"}]},
    {"num": 9,  "titulo": "¹²⁷Te",                        "mostrar_irr": False, "series": [{"iso": "TE127",  "label": "¹²⁷Te"}]},
    {"num": 10, "titulo": "¹²⁹Te / ¹²⁹ᵐTe",              "mostrar_irr": False, "series": [{"iso": "TE129",  "label": "¹²⁹Te"},  {"iso": "TE129M", "label": "¹²⁹ᵐTe"}]},
    {"num": 11, "titulo": "¹²¹Te",                        "mostrar_irr": False, "series": [{"iso": "TE121",  "label": "¹²¹Te"}]},
    {"num": 12, "titulo": "¹³²I / ¹³²ᵐI",                "mostrar_irr": False, "series": [{"iso": "I132",   "label": "¹³²I"},   {"iso": "I132M",  "label": "¹³²ᵐI"}]},
    {"num": 13, "titulo": "¹²⁸I",                         "mostrar_irr": False, "series": [{"iso": "I128",   "label": "¹²⁸I"}]},
    {"num": 14, "titulo": "¹³³ᵐTe / ¹³³Te",              "mostrar_irr": False, "series": [{"iso": "TE133M", "label": "¹³³ᵐTe"}, {"iso": "TE133", "label": "¹³³Te"}]},
    {"num": 15, "titulo": "¹³⁰ᵐI",                       "mostrar_irr": False, "series": [{"iso": "I130M",  "label": "¹³⁰ᵐI"}]},
]


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
    """Parse the NUMBER OF ATOMS section from fort.6.

    Returns:
        t_irr_h   np.ndarray   Time points [h]
        datos     dict         {iso: np.ndarray of atoms/cm³}
    """
    with open(filepath, "r", errors="ignore") as f:
        lines = f.readlines()

    bloque_inicio: Optional[int] = None
    for i, l in enumerate(lines):
        if "NUMBER OF ATOMS" in l:
            bloque_inicio = i
            break
    if bloque_inicio is None:
        raise ValueError("No se encontró NUMBER OF ATOMS en fort.6")

    header_line: Optional[int] = None
    for j in range(bloque_inicio, min(bloque_inicio + 20, len(lines))):
        if "INITIAL" in lines[j]:
            header_line = j
            break
    if header_line is None:
        raise ValueError("No se encontró la línea de cabecera de tiempos en NUMBER OF ATOMS")

    hdr_tokens = lines[header_line].strip().split()
    t_vals: list[float] = []
    for tok in hdr_tokens:
        if tok == "INITIAL":
            t_vals.append(0.0)
        else:
            try:
                t_vals.append(float(tok))
            except ValueError:
                pass
    t_irr = np.array(t_vals)
    n_cols = len(t_irr)

    datos: dict[str, np.ndarray] = {}
    i = header_line + 1
    while i < len(lines):
        l = lines[i]
        stripped = l.strip()

        # Stop at end-of-table markers
        if stripped.upper().startswith("TOTAL") or stripped.upper().startswith("SUBTOT"):
            break
        if "NUCLIDE RADIOACTIVITY" in l or "NUCLIDE IDENTIFIERS" in l:
            break
        if "2. TIME SET" in l:
            break

        parts = stripped.split()
        if parts and len(parts) >= n_cols + 1:
            iso_name = parts[0]
            if re.match(r"^[A-Z]{1,2}\d{2,3}M?$", iso_name):
                try:
                    vals = [float(v) for v in parts[1: n_cols + 1]]
                    if len(vals) == n_cols:
                        datos[iso_name] = np.array(vals)
                except (ValueError, IndexError):
                    pass
        i += 1

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
            elif tok == "SHUTDOWN":
                col_times.append(0.0)
            elif tok == "RESTART":
                col_times.append(None)
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
# Simulation discovery
# ─────────────────────────────────────────────────────────────────────────────

def descubrir_simulaciones(folder: str) -> list[tuple[str, str]]:
    """Return list of (sim_name, fort6_path) for subfolders containing fort.6.

    Also accepts the folder itself if it directly contains fort.6 (single sim).
    """
    base = pathlib.Path(folder)
    if not base.exists():
        raise FileNotFoundError(f"La carpeta no existe: {folder}")

    sims: list[tuple[str, str]] = []

    # Check if fort.6 lives directly in the given folder (single-sim mode)
    if (base / "fort.6").exists():
        sims.append((base.name, str(base / "fort.6")))
        return sims

    # Otherwise scan subfolders
    for sub in sorted(base.iterdir()):
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
) -> tuple[dict, dict[str, str]]:
    """Perform full analysis of a simulations folder.

    Returns:
        all_data   dict   {sim_name: sim_dict} with JSON-serialisable values
        errors     dict   {sim_name: error_message} for failed simulations
    """
    sims = descubrir_simulaciones(folder)
    if not sims:
        raise ValueError(f"No se encontró ninguna subcarpeta con fort.6 en '{folder}'")

    all_data: dict = {}
    errors: dict[str, str] = {}

    for sim_name, fort6_path in sims:
        try:
            t_irr_arr, datos_irr = leer_fort6_irradiacion(fort6_path)
            t_cool_arr, datos_cool = leer_fort6_enfriamiento(fort6_path)

            # Material density (g/cm³) for MBq/g normalisation — None if the
            # CONCENTRATIONS(GRAM) section is missing, without breaking analysis.
            conc = leer_fort6_concentraciones(fort6_path)
            densidad_g_cm3 = conc["total_g_cm3"] if conc else None

            # Convert atoms/cm³ → Bq/cm³  (A = λ·N)
            datos_irr_Bq: dict[str, list[float]] = {}
            for iso, N in datos_irr.items():
                t12 = t12_dict.get(iso, math.inf)
                datos_irr_Bq[iso] = (lam(t12) * N).tolist()

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
        pico = calcular_pico(sim, isotopo_key)
        sim_reports[sim_name] = pico
        metricas[sim_name] = {
            "saturacion":  calcular_saturacion(sim, isotopo_key, t12_dict),
            "rendimiento": calcular_rendimiento(sim, isotopo_key),
            "pureza":      calcular_pureza(sim, isotopo_key, pico["t_pico"], impureza_list),
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
