"""test_parser_robustness.py — Robustez del parser y casos negativos.

Uso:
    python tools/test_parser_robustness.py fichero_referencia.inp.5

Genera variantes del fichero de referencia (CRLF, comentarios inline, arrays
partidos, minúsculas, notación FORTRAN D/desnuda, comentarios multilínea) que
deben parsearse idénticas, y ficheros malformados (truncado, vacío, tipos
erróneos, cadena NGO sin cerrar) que deben producir ValueError con mensaje
claro. Código de salida 0 si todo pasa.
"""
import sys, tempfile, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from acab_parser import ACABParser

if len(sys.argv) < 2:
    print(__doc__); raise SystemExit(2)
BASE = open(sys.argv[1]).read()

def parse_text(txt):
    with tempfile.NamedTemporaryFile('w', suffix='.5', delete=False, newline='') as t:
        t.write(txt)
        name = t.name
    return ACABParser().read_inp5(name)

ref = parse_text(BASE)

def norm(o):
    if isinstance(o, (list, tuple)): return [norm(x) for x in o]
    if isinstance(o, dict): return {k: norm(v) for k, v in o.items()}
    return o

def same(a, b): return norm(a) == norm(b)

results = []

# 1. CRLF
crlf = BASE.replace('\n', '\r\n')
results.append(('CRLF (\\r\\n)', same(parse_text(crlf), ref)))

# 2. Comentarios inline añadidos a líneas de datos
inline = BASE.replace(' 0  IREST', ' 0  IREST  < comentario inline anadido')
inline = inline.replace('520000 80000', '520000 80000 < INUCL Te y O')
results.append(('comentarios inline extra', same(parse_text(inline), ref)))

# 3. Array EGRP partido en una frontera por línea (25 líneas)
lines = BASE.splitlines()
out = []
i = 0
while i < len(lines):
    if lines[i].startswith('<Block #2, card #6'):
        out.append(lines[i]); i += 1
        vals = []
        while i < len(lines) and not lines[i].startswith('<'):
            vals += lines[i].split(); i += 1
        out += vals  # una por línea
    else:
        out.append(lines[i]); i += 1
split_egrp = '\n'.join(out) + '\n'
results.append(('EGRP una frontera por línea', same(parse_text(split_egrp), ref)))

# 4. Etiquetas en minúsculas (iunc, irest...)
lower = BASE.replace('IUNC', 'iunc').replace('IREST', 'irest').replace('NOPUL NTSEQ NOTTS NVFL', 'nopul ntseq notts nvfl')
results.append(('etiquetas en minúsculas', same(parse_text(lower), ref)))

# 5. Línea en blanco intercalada + espacios iniciales
blank = BASE.replace('<Block #4  Restart option', '\n   \n<Block #4  Restart option')
results.append(('líneas en blanco intercaladas', same(parse_text(blank), ref)))

# 6. Notación FORTRAN: D-exponente y exponente desnudo
fortran = BASE.replace('6.500000E+13', '6.5D+13')
fortran = fortran.replace('1.000000E-25', '1.0-25')
d = parse_text(fortran)
ok6 = math.isclose(d['block3']['FLUX'][0], 6.5e13) and math.isclose(d['block9']['ERR'], 1e-25)
results.append(('D-exp y exponente desnudo', ok6))

# 7. Comentario multilinea sin < en continuación (heurística)
multi = BASE.replace('<Block #9 ERR XNORM',
                     '<Block #9 ERR XNORM primera linea\nsegunda linea del comentario sin marcador\ntercera linea tambien texto')
results.append(('comentario multilínea sin <', same(parse_text(multi), ref)))

# --- Casos negativos: deben producir error claro ---
neg = []

# 8. Fichero truncado (se corta a la mitad)
half = '\n'.join(BASE.splitlines()[:20]) + '\n'
try:
    parse_text(half); neg.append(('fichero truncado', False, 'NO lanzó error'))
except ValueError as e:
    neg.append(('fichero truncado', True, str(e)[:70]))
except Exception as e:
    neg.append(('fichero truncado', False, f'excepción no controlada: {type(e).__name__}: {e}'[:80]))

# 9. Fichero vacío
try:
    parse_text('');  neg.append(('fichero vacío', False, 'NO lanzó error'))
except ValueError as e:
    neg.append(('fichero vacío', True, str(e)[:70]))
except Exception as e:
    neg.append(('fichero vacío', False, f'{type(e).__name__}: {e}'[:80]))

# 10. Real donde se espera entero (IREST = 0.5)
bad = BASE.replace(' 0  IREST', ' 0.5  IREST')
try:
    parse_text(bad); neg.append(('IREST=0.5 (real por entero)', False, 'NO lanzó error'))
except Exception as e:
    neg.append(('IREST=0.5 (real por entero)', True, f'{type(e).__name__}: {e}'[:80]))

# 11. Último set con NGO=1 (cadena sin cerrar) → debe fallar por falta de tokens
badngo = BASE.replace('  0  9   0 10  3 0   1 0', '  0  9   1 10  3 0   1 0')
try:
    parse_text(badngo); neg.append(('NGO sin cerrar', False, 'NO lanzó error'))
except ValueError as e:
    neg.append(('NGO sin cerrar', True, str(e)[:70]))
except Exception as e:
    neg.append(('NGO sin cerrar', False, f'{type(e).__name__}: {e}'[:80]))

print('--- Robustez (deben ser True) ---')
for name, ok in results:
    print(f'{"OK " if ok else "FALLO"}  {name}')
print('\n--- Negativos (deben lanzar ValueError claro) ---')
for name, ok, msg in neg:
    print(f'{"OK " if ok else "FALLO"}  {name}: {msg}')

n_fail = sum(1 for _, ok in results if not ok) + sum(1 for _, ok, _ in neg if not ok)
raise SystemExit(0 if n_fail == 0 else 1)
