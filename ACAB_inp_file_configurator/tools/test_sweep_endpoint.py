"""Tests del generador de barridos (Fase 2 del runbook v2).

    C:\\venv\\acab-venv\\Scripts\\python.exe tools/test_sweep_endpoint.py

Cubre: merge recursivo, flujo feliz (copia de carpeta base + reemplazo de
inp.5 + manifest coherente), colisión 409, límites 422 (N>200, sufijo
duplicado, descripción vacía), y aborto + limpieza ante un patch que produce
un inp.5 inválido / no re-parseable.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as appmod                              # noqa: E402
from acab_parser import ACABParser               # noqa: E402
from sweep_writer import SweepError, deep_merge, _roundtrip_check  # noqa: E402


class DeepMergeTests(unittest.TestCase):
    def test_scalar_replaced(self):
        self.assertEqual(deep_merge({'a': 1, 'b': 2}, {'a': 9}), {'a': 9, 'b': 2})

    def test_nested_dict_merged(self):
        self.assertEqual(
            deep_merge({'b': {'x': 1, 'y': 2}}, {'b': {'y': 9}}),
            {'b': {'x': 1, 'y': 9}})

    def test_list_replaced_whole(self):
        self.assertEqual(deep_merge({'l': [1, 2, 3]}, {'l': [9]}), {'l': [9]})

    def test_no_mutation(self):
        base = {'b': {'x': 1}}
        deep_merge(base, {'b': {'x': 2}})
        self.assertEqual(base, {'b': {'x': 1}})


class SweepEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = appmod.app.test_client()
        self.tmp = Path(tempfile.mkdtemp())
        self.base = self.tmp / 'base'
        (self.base / 'sub').mkdir(parents=True)
        (self.base / 'lib.dat').write_text('library data', encoding='utf-8')
        (self.base / 'sub' / 'aux.txt').write_text('aux', encoding='utf-8')
        (self.base / 'inp.5').write_text('OLD BASE INP', encoding='utf-8')
        self.data = appmod._default_data()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _flux_sims(self, values):
        return [{'suffix': f'x{v}', 'params': {'XNORM': v},
                 'patch': {'block9': {'XNORM': v}}} for v in values]

    def test_default_data_roundtrips(self):
        # Prerrequisito del flujo feliz: el fichero base debe re-parsear.
        _roundtrip_check(appmod._write_inp5(self.data), ACABParser(), 'default')

    def test_happy_path(self):
        root = self.tmp / 'out'
        sims = self._flux_sims([0.5, 0.75, 1.0])
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'TeO2_',
            'description': 'barrido de flujo de prueba', 'sweep_type': 'flux',
            'fixed_params': {'masa': '0.1231 g', 'T_irr': '24 h'},
            'data': self.data, 'sims': sims})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        body = r.get_json()
        self.assertTrue(body['ok'])
        self.assertEqual(body['n_written'], 3)

        for suf, xn in [('x0.5', '5.000000E-01'), ('x0.75', '7.500000E-01'),
                        ('x1.0', '1.000000E+00')]:
            d = root / f'TeO2_{suf}'
            self.assertTrue(d.is_dir())
            self.assertTrue((d / 'lib.dat').exists(), 'copió lib.dat de la base')
            self.assertTrue((d / 'sub' / 'aux.txt').exists(), 'copió subdir')
            inp = (d / 'inp.5').read_text(encoding='utf-8')
            self.assertNotIn('OLD BASE INP', inp, 'inp.5 base reemplazado')
            self.assertIn(xn, inp, 'XNORM aplicado en el inp.5')
            _roundtrip_check(inp, ACABParser(), suf)

        manifest = json.loads((root / 'sweep_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['n'], 3)
        self.assertEqual(manifest['sweep_type'], 'flux')
        self.assertEqual(len(manifest['simulations']), 3)
        self.assertEqual(manifest['simulations'][0]['folder'], 'TeO2_x0.5')
        self.assertIn('masa', manifest['fixed_params'])

        csv_txt = (root / 'sweep_manifest.csv').read_text(encoding='utf-8')
        self.assertIn('folder', csv_txt)
        self.assertIn('XNORM', csv_txt)
        self.assertTrue((root / 'README.txt').exists())
        self.assertTrue((root / 'run_all.ps1').exists())
        self.assertTrue((root / 'run_all.sh').exists())

    def test_preview(self):
        root = self.tmp / 'pv'
        r = self.client.post('/api/sweep/preview', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'sims': [{'suffix': 'a'}, {'suffix': 'b'}]})
        self.assertEqual(r.status_code, 200)
        b = r.get_json()
        self.assertTrue(b['base_exists'])
        self.assertTrue(b['base_has_inp5'])
        self.assertEqual(b['n'], 2)
        self.assertEqual(b['est_disk'], b['base_size'] * 2)
        self.assertEqual(b['collisions'], [])
        self.assertGreater(b['base_size'], 0)

    def test_collision_409(self):
        root = self.tmp / 'out2'
        (root / 'P_a').mkdir(parents=True)
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': 'd', 'data': self.data,
            'sims': [{'suffix': 'a', 'params': {}, 'patch': {}}]})
        self.assertEqual(r.status_code, 409)

    def test_overwrite_allows_existing(self):
        root = self.tmp / 'out2b'
        (root / 'P_a').mkdir(parents=True)
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': 'd', 'overwrite': True, 'data': self.data,
            'sims': [{'suffix': 'a', 'params': {}, 'patch': {}}]})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))

    def test_too_many_sims_422(self):
        root = self.tmp / 'out3'
        sims = [{'suffix': f's{i}', 'params': {}, 'patch': {}} for i in range(201)]
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': 'd', 'data': self.data, 'sims': sims})
        self.assertEqual(r.status_code, 422)

    def test_duplicate_suffix_422(self):
        root = self.tmp / 'out4'
        sims = [{'suffix': 'a', 'params': {}, 'patch': {}},
                {'suffix': 'a', 'params': {}, 'patch': {}}]
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': 'd', 'data': self.data, 'sims': sims})
        self.assertEqual(r.status_code, 422)

    def test_empty_description_422(self):
        root = self.tmp / 'out5'
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': '   ', 'data': self.data,
            'sims': [{'suffix': 'a', 'params': {}, 'patch': {}}]})
        self.assertEqual(r.status_code, 422)

    def test_abort_and_cleanup_on_bad_patch(self):
        root = self.tmp / 'out6'
        sims = [
            {'suffix': 'good', 'params': {}, 'patch': {}},
            # XCOMP vacío ⇒ el writer falla ⇒ aborta y limpia todo el barrido
            {'suffix': 'bad', 'params': {},
             'patch': {'block5': [{'INUCL': [10000], 'XCOMP': []}]}},
        ]
        r = self.client.post('/api/sweep', json={
            'root': str(root), 'base_folder': str(self.base), 'prefix': 'P_',
            'description': 'd', 'data': self.data, 'sims': sims})
        self.assertEqual(r.status_code, 422)
        self.assertFalse((root / 'P_good').exists(), 'limpió la sim ya escrita')
        self.assertFalse((root / 'P_bad').exists())
        self.assertFalse((root / 'sweep_manifest.json').exists())

    def test_roundtrip_check_rejects_garbage(self):
        with self.assertRaises(SweepError):
            _roundtrip_check('esto no es un fichero ACAB valido', ACABParser(), 'g')


if __name__ == '__main__':
    unittest.main(verbosity=2)
