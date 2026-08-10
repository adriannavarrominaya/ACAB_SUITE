"""test_time_mesh_reconstruction.py — F20 del BACKLOG: reconstrucción de los
tramos REALES del historial temporal al cargar un inp.5, en vez de
colapsar la malla a un tramo por fase (los tiempos finales se conservaban,
los cortes intermedios se perdían sin ningún aviso).

Ejercita el pipeline COMPLETO cargar → reconstruir → generar tal como lo
recorre el navegador: `reconstructFasesFromBlocks78`/`buildBlocks78` de
`static/js/sweep_utils.js` (invocadas vía subprocess `node`, sin necesitar
un navegador real -- la verificación visual en Playwright cubre el caso
real de punta a punta) seguidas del writer del servidor (`_write_inp5`).

Dos niveles de control, deliberadamente distintos:
  1) `test_semantica_preservada_*`: contra los ficheros REALES
     `examples/Inp5/exp*.inp.5` -- la lista de tiempos (la malla física
     realmente simulada) sobrevive exacta a cargar+regenerar. Estos
     ficheros son anteriores a F7 (tarjetas por fase) y usan el formato
     "compactado histórico" (irr+cool mezcladas en una tarjeta); F7 ya
     cambió el troceado en tarjetas al regenerar -- eso es esperado, no
     una regresión de F20 -- así que aquí NO se exige byte-identidad del
     fichero completo, solo de los tiempos.
  2) `test_byte_identico_*`: control de aceptación MÁS FUERTE del propio
     F20 -- un fichero que esta app YA escribió (formato F7, tarjetas por
     fase) se carga y regenera sin tocar nada, byte-idéntico. Malla
     uniforme, multi-tramo (con los cortes reales del experimento 2, ver
     `EXP2_COOL_TRAMOS`) e irregular, y también desde la tarjeta sembrada
     del barrido (`baseFases`/`reconstructFasesFromBlocks78`, mismo camino).

    C:\\venv\\acab-venv\\Scripts\\python.exe tools/test_time_mesh_reconstruction.py
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from acab_parser import ACABParser   # noqa: E402
from app import _write_inp5, _default_data  # noqa: E402

EXAMPLES = ROOT / 'examples' / 'Inp5'
SWEEP_UTILS_JS = ROOT / 'static' / 'js' / 'sweep_utils.js'
NODE = shutil.which('node')

# Los 5 tramos reales del enfriamiento del experimento 2 (exp2.inp.5, ver
# también tools/test_sweep_utils.js): Δ=0.25 → 0.5 → 1.0 → 2.0 → 5.0h.
EXP2_COOL_TRAMOS = [
    {'t_fin': 0.5, 'pasos': 2}, {'t_fin': 5.0, 'pasos': 9}, {'t_fin': 6.0, 'pasos': 1},
    {'t_fin': 10.0, 'pasos': 2}, {'t_fin': 25.0, 'pasos': 3},
]


def _node_reconstruct_and_regenerate(b78: dict) -> dict:
    """Invoca reconstructFasesFromBlocks78 + buildBlocks78 (sweep_utils.js)
    en un subproceso node -- EL MISMO cálculo puro, sin duplicarlo en
    Python, que ejecuta el navegador al cargar un fichero y pulsar
    "Generar" sin tocar nada."""
    assert NODE, 'node no está en el PATH -- requerido por la suite (ver CLAUDE.md)'
    set0 = b78['sets'][0]
    script = (
        f"const {{ reconstructFasesFromBlocks78, buildBlocks78 }} = "
        f"require({json.dumps(str(SWEEP_UTILS_JS))});\n"
        f"const b78 = {json.dumps(b78)};\n"
        f"const opts = {{ iunit: {set0['IUNIT']}, iout: {set0['IOUT']}, iplot: {set0['IPLOT']} }};\n"
        f"const {{ fasesIrr, fasesCool }} = reconstructFasesFromBlocks78(b78, {{}});\n"
        f"const regen = buildBlocks78(fasesIrr, fasesCool, opts);\n"
        f"process.stdout.write(JSON.stringify({{ sets: regen.sets, times: regen.times, "
        f"fasesIrr, fasesCool }}));\n"
    )
    r = subprocess.run([NODE, '-e', script], capture_output=True, text=True)
    assert r.returncode == 0, f'node falló: {r.stderr}'
    return json.loads(r.stdout)


def _norm_times(times) -> list:
    """Normaliza tuplas/listas [t, tipo] a listas planas para comparar
    JSON (node) contra el parser de Python (tuplas)."""
    return [[t, int(k)] for t, k in times]


class SemanticaPreservadaTests(unittest.TestCase):
    """Nivel 1: la MALLA (lista de tiempos realmente simulados) sobrevive
    cargar+regenerar en los ficheros reales del repo, aunque el troceado en
    tarjetas cambie de formato (compactado histórico → F7)."""

    def _check_fixture(self, name: str):
        path = EXAMPLES / name
        data = ACABParser().read_inp5(str(path))
        b78 = data['blocks78']
        out = _node_reconstruct_and_regenerate(b78)

        orig_times = _norm_times(b78['times'])
        regen_times = out['times']
        self.assertEqual(len(orig_times), len(regen_times),
                          f'{name}: nº de tiempos reconstruidos difiere del original '
                          f'(F20: antes se colapsaba a un tramo por fase)')
        for i, ((ot, ok), (rt, rk)) in enumerate(zip(orig_times, regen_times)):
            self.assertEqual(ok, rk, f'{name}[{i}]: cambió de fase (irr/cool)')
            # Tolerancia relativa, NO igualdad exacta: exp2.inp.5 es anterior
            # a esta app y sus literales de 7 cifras no son perfectamente
            # consistentes con la fórmula lineal exacta de una racha (mismo
            # motivo por el que la reconstrucción usa tolerancia, ver
            # TIME_MESH_REL_TOL en sweep_utils.js).
            self.assertTrue(math.isclose(ot, rt, rel_tol=1e-4),
                             f'{name}[{i}]: {ot} vs {rt} (fuera de tolerancia)')

    def test_exp1_uniforme(self):
        self._check_fixture('exp1.inp.5')

    def test_exp2_multi_tramo(self):
        self._check_fixture('exp2.inp.5')

    def test_exp4_ramp(self):
        self._check_fixture('exp4.inp.5')


class ByteIdenticoTests(unittest.TestCase):
    """Nivel 2: control de aceptación de F20, el más fuerte -- un fichero
    que la app YA escribió (formato F7) se carga y regenera sin tocar nada,
    byte-idéntico. Requiere que el fichero de partida esté en el formato
    canónico actual del writer (tarjetas por fase, F7), así que se
    construye con buildBlocks78 antes de escribirlo -- exactamente como si
    un usuario lo hubiera generado y guardado con esta misma app."""

    def _roundtrip(self, fasesIrr, fasesCool, iunit=3, iout=1, iplot=0):
        set0_opts = json.dumps({'iunit': iunit, 'iout': iout, 'iplot': iplot})
        script = (
            f"const {{ buildBlocks78 }} = require({json.dumps(str(SWEEP_UTILS_JS))});\n"
            f"const b78 = buildBlocks78({json.dumps(fasesIrr)}, {json.dumps(fasesCool)}, "
            f"{set0_opts});\n"
            f"process.stdout.write(JSON.stringify({{ sets: b78.sets, times: b78.times }}));\n"
        )
        r = subprocess.run([NODE, '-e', script], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f'node falló: {r.stderr}')
        b78 = json.loads(r.stdout)
        # Blocks TIMES deben ser floats, no ints, para que _write_inp5 los
        # formatee siempre en notación E (algunos t_fin de los tests son
        # enteros en Python/JSON, p. ej. 5.0 -> 5).
        for s in b78['sets']:
            s['TIMES'] = [float(x) for x in s['TIMES']]

        data = _default_data()
        data['blocks78'] = b78
        data['block11']['NOTTS'] = len(b78['sets'])
        data['block13']['ITSO'] = [1] * len(b78['sets'])
        original_text = _write_inp5(data)

        # "Cargar": re-parsear el fichero recién escrito (como haría la app).
        with_tmp = ROOT / 'tools' / '_tmp_f20_roundtrip.inp.5'
        with_tmp.write_text(original_text, encoding='utf-8')
        try:
            reparsed = ACABParser().read_inp5(str(with_tmp))
        finally:
            with_tmp.unlink(missing_ok=True)

        # "Generar" sin tocar nada: reconstruir + volver a construir blocks78.
        out = _node_reconstruct_and_regenerate(reparsed['blocks78'])
        regen_b78 = {'sets': out['sets'], 'times': out['times']}
        for s in regen_b78['sets']:
            s['TIMES'] = [float(x) for x in s['TIMES']]

        data2 = _default_data()
        data2['blocks78'] = regen_b78
        data2['block11']['NOTTS'] = len(regen_b78['sets'])
        data2['block13']['ITSO'] = [1] * len(regen_b78['sets'])
        regenerated_text = _write_inp5(data2)

        self.assertEqual(original_text, regenerated_text,
                          'F20: cargar y regenerar sin tocar nada debe producir '
                          'un inp.5 BYTE-IDÉNTICO')

    def test_malla_uniforme(self):
        # 18 pasos Δ=0.25h (exp1.inp.5, ya en formato F7 tras 2 tramos <=10).
        self._roundtrip([{'t_fin': 2.778e-3, 'pasos': 1}],
                         [{'t_fin': 2.5, 'pasos': 10}, {'t_fin': 4.5, 'pasos': 8}])

    def test_multi_tramo_real_exp2(self):
        self._roundtrip([{'t_fin': 0.1666667, 'pasos': 2}, {'t_fin': 0.3333333, 'pasos': 1}],
                         EXP2_COOL_TRAMOS)

    def test_irregular_rampa_x2(self):
        # Rampa ×2 recomendada por docs/Block#7&#8.md: ningún tramo agrupable.
        self._roundtrip([{'t_fin': 1.0, 'pasos': 1}, {'t_fin': 3.0, 'pasos': 1},
                          {'t_fin': 7.0, 'pasos': 1}, {'t_fin': 15.0, 'pasos': 1}],
                         [{'t_fin': 20.0, 'pasos': 1}])

    def test_desde_tarjeta_sembrada_del_barrido(self):
        """Mismo camino (reconstructFasesFromBlocks78) que baseFases() en
        sweep.js -- la tarjeta 1 del barrido temporal sembrada desde un
        fichero base multi-tramo trae los tramos reales, no colapsados."""
        self._roundtrip([{'t_fin': 2.778e-3, 'pasos': 1}], EXP2_COOL_TRAMOS)


if __name__ == '__main__':
    unittest.main()
