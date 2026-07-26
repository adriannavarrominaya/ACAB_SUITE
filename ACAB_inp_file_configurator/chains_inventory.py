"""chains_inventory.py — Inventario isotópico inicial + códec ZZAAAS (F9 del BACKLOG).

Copia sincronizada (fragmento duplicado de la suite, ver CLAUDE.md raíz) de
``leer_concentraciones_iniciales``/``nombre_a_zzaaas`` de
``ACAB_fort_file_analyzer/fort_analyzer.py`` (Fase 1 del runbook F9). Se
duplica en vez de importar entre apps porque son procesos Flask
independientes sin dependencia cruzada (mismo criterio que ``coll_writer.py``
frente a ``collaps_parser.py`` del repo COLLAPS). Si cambia el formato del
fort.6 o la tabla de elementos allí, replicar aquí.

Necesario para la sección "Análisis de cadenas" (F9 Fase 2): leer el
inventario isotópico inicial del fort.6 de referencia para la UI de
selección, y convertir nombre de isótopo -> ZZAAAS para construir INUCL del
patch monoisotópico del Bloque #5 y IINICIAL/IFINAL del input de CHAINS.
"""

from __future__ import annotations

import re
from typing import Optional

# Atomic number → ACAB element symbol (uppercase, as used in fort.6 keys).
# Copia exacta de _Z_TO_ELEM en fort_analyzer.py.
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

_ELEM_TO_Z: dict[str, int] = {v: k for k, v in _Z_TO_ELEM.items()}


def nombre_a_zzaaas(acab_key: str) -> int:
    """Nombre ACAB ('TE130', 'TE131M') -> código ZZAAAS entero (521300, 521311).

    Copia exacta de fort_analyzer.nombre_a_zzaaas. S=1 para isómeros (sufijo
    'M'). Lanza ValueError si el nombre o el elemento no se reconocen.
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


def leer_concentraciones_iniciales(filepath: str) -> dict[str, float]:
    """Inventario isotópico inicial (t=0, INITIAL CONCENTRATIONS) del fort.6.

    Copia exacta de fort_analyzer.leer_concentraciones_iniciales — ver el
    docstring de esa función (ACAB_fort_file_analyzer/fort_analyzer.py) para
    el detalle de formato de columnas. Devuelve {acab_key: C_i} en
    átomos/cm³, solo isótopos con C_i > 0.
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
