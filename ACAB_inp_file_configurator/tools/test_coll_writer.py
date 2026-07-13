"""Tests de coll_writer.py (Fase P2 del RUNBOOK_barrido_espectral.md).

    C:\\venv\\acab-venv\\Scripts\\python.exe tools/test_coll_writer.py

Cubre: round-trip (parsear → regenerar → re-parsear → comparar) contra el
fixture COLL.inp de 211 grupos (IESF=12, sin CX) y contra un caso sintético
IESF=5+CX; apply_spectrum_patch (fuerza IESF=5 al incluir CX, preserva el
resto de tarjetas, valida dimensiones NGROUP/FT/CX) y sus rechazos.
"""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coll_writer import (                          # noqa: E402
    COLLAPSParser, apply_spectrum_patch, read_coll_inp, write_coll_inp,
)

FIXTURE_211 = Path(__file__).resolve().parents[1] / 'tests/fixtures/spectra/COLL.inp'


def _roundtrip(data: dict) -> dict:
    content = write_coll_inp(data)
    with tempfile.NamedTemporaryFile('w', suffix='.inp', delete=False, encoding='utf-8') as tf:
        tf.write(content)
        tmp = Path(tf.name)
    try:
        return COLLAPSParser().read_coll_inp(tmp), content
    finally:
        tmp.unlink(missing_ok=True)


class RoundtripTests(unittest.TestCase):
    def test_fixture_211_groups_roundtrips(self):
        base = read_coll_inp(FIXTURE_211)
        self.assertEqual(base['card1'], {'ILIB': 12, 'IESF': 12})
        self.assertEqual(base['card5']['NGROUP'], -211)
        self.assertIsNone(base['card6'])  # IESF != 5 → sin CX
        self.assertEqual(len(base['card7']['FT']), 211)

        reparsed, content = _roundtrip(base)
        self.assertEqual(reparsed, base)
        self.assertIn('  12  12', content.splitlines()[0])

    def test_synthetic_iesf5_cx_roundtrips(self):
        data = {
            'card1': {'ILIB': 2, 'IESF': 5},
            'card2': {'IHEAD': 16},
            'card3': {'ISFIS': 0, 'IGEN': 0, 'ISOCA': 0, 'IBEST': 0},
            'card4': None,
            'card5': {'NGROUP': -5, 'FF': 0},
            'card6': {'CX': [2.0e7, 1.0e7, 1.0e6, 1.0e5, 1.0e3, 1.0e-3]},
            'card7': {'FT': [1.1e10, 2.2e10, 3.3e10, 4.4e10, 5.5e10]},
            'card8': {'IUNC3G': 0},
            'card9': {'ISTOP': 0},
        }
        reparsed, _content = _roundtrip(data)
        self.assertEqual(reparsed, data)

    def test_isfis_nonzero_card4_roundtrips(self):
        data = {
            'card1': {'ILIB': 2, 'IESF': 12},
            'card2': {'IHEAD': 16},
            'card3': {'ISFIS': 1, 'IGEN': 0, 'ISOCA': 1, 'IBEST': 1},
            'card4': {'EB1': 5.0e6, 'EB2': 2.0e5},
            'card5': {'NGROUP': 3, 'FF': 1},
            'card6': None,
            'card7': {'FT': [1.0, 2.0, 3.0]},
            'card8': {'IUNC3G': 1},
            'card9': {'ISTOP': 0},
        }
        reparsed, _content = _roundtrip(data)
        self.assertEqual(reparsed, data)


class ApplySpectrumPatchTests(unittest.TestCase):
    def setUp(self):
        self.base = read_coll_inp(FIXTURE_211)

    def test_patch_with_cx_forces_iesf5(self):
        patch = {'ngroup': -3, 'cx': [20.0, 10.0, 1.0, 0.1], 'ft': [1e10, 2e10, 3e10]}
        patched = apply_spectrum_patch(self.base, patch)
        self.assertEqual(patched['card1']['IESF'], 5)
        self.assertEqual(patched['card1']['ILIB'], self.base['card1']['ILIB'], 'ILIB se conserva')
        self.assertEqual(patched['card5']['NGROUP'], -3)
        self.assertEqual(patched['card5']['FF'], self.base['card5']['FF'], 'FF se conserva del base')
        self.assertEqual(patched['card6']['CX'], [20.0, 10.0, 1.0, 0.1])
        self.assertEqual(patched['card7']['FT'], [1e10, 2e10, 3e10])
        # Resto de tarjetas intactas
        self.assertEqual(patched['card2'], self.base['card2'])
        self.assertEqual(patched['card3'], self.base['card3'])
        self.assertEqual(patched['card8'], self.base['card8'])
        self.assertEqual(patched['card9'], self.base['card9'])

    def test_patch_roundtrips_after_write(self):
        patch = {'ngroup': -3, 'cx': [20.0, 10.0, 1.0, 0.1], 'ft': [1.1e10, 2.2e10, 3.3e10]}
        patched = apply_spectrum_patch(self.base, patch)
        reparsed, _content = _roundtrip(patched)
        self.assertEqual(reparsed, patched)

    def test_patch_without_cx_keeps_base_card6(self):
        # Un patch sin 'cx' no toca IESF ni card6 (p.ej. si el base ya usa IESF=5).
        base_iesf5 = copy.deepcopy(self.base)
        base_iesf5['card1']['IESF'] = 5
        base_iesf5['card6'] = {'CX': [1.0, 0.5, 0.0]}
        patch = {'ngroup': -2, 'ft': [1.0, 2.0]}
        patched = apply_spectrum_patch(base_iesf5, patch)
        self.assertEqual(patched['card1']['IESF'], 5)
        self.assertEqual(patched['card6'], {'CX': [1.0, 0.5, 0.0]}, 'card6 preservada tal cual del base')

    def test_missing_ngroup_rejected(self):
        with self.assertRaises(ValueError):
            apply_spectrum_patch(self.base, {'ft': [1.0, 2.0]})

    def test_missing_ft_rejected(self):
        with self.assertRaises(ValueError):
            apply_spectrum_patch(self.base, {'ngroup': -2})

    def test_ft_length_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            apply_spectrum_patch(self.base, {'ngroup': -3, 'ft': [1.0, 2.0]})

    def test_cx_length_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            apply_spectrum_patch(self.base, {'ngroup': -3, 'cx': [1.0, 2.0], 'ft': [1.0, 2.0, 3.0]})


if __name__ == '__main__':
    unittest.main(verbosity=2)
