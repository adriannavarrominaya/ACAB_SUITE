"""regression_roundtrip.py — Regresión round-trip del parser + writer.

Uso:
    python tools/regression_roundtrip.py fichero1.inp.5 [fichero2 ...]

Para cada fichero comprueba:
  A) Semántica: parse(orig) == parse(write(parse(orig)))  — los dicts deben ser
     idénticos (floats con tolerancia relativa 1e-9).
  B) Tokens: la secuencia de tokens numéricos del fichero regenerado es
     idéntica en valor a la del original (la tolerancia es solo de formato de
     reales y espaciado, nunca de valor).

Código de salida 0 si todo pasa; 1 si hay fallos.
"""
from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from acab_parser import ACABParser, _NUM_RE, _parse_fortran_float  # noqa: E402
from app import _write_inp5                                        # noqa: E402


def norm(o):
    if isinstance(o, (tuple, list)):
        return [norm(x) for x in o]
    if isinstance(o, dict):
        return {k: norm(v) for k, v in o.items()}
    return o


def deep_eq(a, b, path=''):
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b:
                diffs.append(f'{path}.{k}: falta clave')
                continue
            diffs += deep_eq(a[k], b[k], f'{path}.{k}')
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append(f'{path}: longitud {len(a)} vs {len(b)}')
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diffs += deep_eq(x, y, f'{path}[{i}]')
    elif isinstance(a, float) or isinstance(b, float):
        if not math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-30):
            diffs.append(f'{path}: {a} != {b}')
    else:
        if a != b:
            diffs.append(f'{path}: {a!r} != {b!r}')
    return diffs


def tokens_of(text: str) -> list[str]:
    """Réplica de la lógica del tokenizador del parser (título excluido)."""
    toks = []
    title_seen = False
    prev_comment = False
    for line in text.splitlines():
        if line and line[0] == '<':
            prev_comment = True
            continue
        ls = line.lstrip()
        if not title_seen:
            if ls:
                title_seen = True
            continue
        if prev_comment and ls and ls[0].isalpha():
            continue
        prev_comment = False
        if not ls:
            continue
        if '<' in line:
            line = line[:line.index('<')]
        for tok in line.split():
            if _NUM_RE.match(tok):
                toks.append(tok)
    return toks


def main(files: list[str]) -> int:
    if not files:
        print(__doc__)
        return 2
    ok_all = True
    for f in files:
        d1 = norm(ACABParser().read_inp5(f))
        out = _write_inp5(d1)
        with tempfile.NamedTemporaryFile('w', suffix='.5', delete=False) as t:
            t.write(out)
            tp = t.name
        d2 = norm(ACABParser().read_inp5(tp))
        Path(tp).unlink(missing_ok=True)

        diffs = deep_eq(d1, d2, Path(f).name)
        t1, t2 = tokens_of(Path(f).read_text()), tokens_of(out)
        tok_diffs = []
        if len(t1) != len(t2):
            tok_diffs.append(f'nº tokens: {len(t1)} vs {len(t2)}')
        else:
            for i, (a, b) in enumerate(zip(t1, t2)):
                va, vb = _parse_fortran_float(a), _parse_fortran_float(b)
                if not math.isclose(va, vb, rel_tol=1e-9, abs_tol=1e-30):
                    tok_diffs.append(f'token {i}: {a} vs {b}')

        if diffs or tok_diffs:
            ok_all = False
        print(f'{Path(f).name}: semántica {"OK" if not diffs else "FALLO"}, '
              f'tokens {"OK" if not tok_diffs else "FALLO"}')
        for x in (diffs + tok_diffs)[:10]:
            print('   ', x)

    print('\nRESULTADO GLOBAL:', 'TODO OK' if ok_all else 'HAY FALLOS')
    return 0 if ok_all else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
