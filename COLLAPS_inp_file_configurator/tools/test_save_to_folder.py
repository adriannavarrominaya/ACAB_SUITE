"""Tests de /api/save-to-folder (U2 del BACKLOG — "Guardar en carpeta...").

    C:\\venv\\acab-venv\\Scripts\\python.exe tools/test_save_to_folder.py

Cubre construcción de ruta (<folder>/COLL.inp), condición de sobrescritura
(409 sin overwrite, éxito con overwrite:true) y los 400/422 de entrada
inválida. No cubre /api/browse-folder (subprocess con tkinter, igual que en
el resto de la suite: se verifica a mano).
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as app_module  # noqa: E402


class SaveToFolderTestCase(unittest.TestCase):

    def setUp(self):
        self.client = app_module.app.test_client()
        self.tmp = Path(tempfile.mkdtemp(prefix='save_to_folder_test_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def _minimal_data():
        return {
            'card1': {'ILIB': 2, 'IESF': 2},
            'card2': {'IHEAD': 16},
            'card3': {'ISFIS': 0, 'IGEN': 0, 'ISOCA': 1, 'IBEST': 1},
            'card4': None,
            'card5': {'NGROUP': -2, 'FF': 0},
            'card6': None,
            'card7': {'FT': [1.0, 1.0]},
            'card8': {'IUNC3G': 0},
            'card9': {'ISTOP': 0},
        }

    def test_missing_folder_400(self):
        res = self.client.post('/api/save-to-folder', json={'data': self._minimal_data()})
        self.assertEqual(res.status_code, 400)

    def test_folder_does_not_exist_422(self):
        res = self.client.post('/api/save-to-folder', json={
            'folder': str(self.tmp / 'no-existe'), 'data': self._minimal_data(),
        })
        self.assertEqual(res.status_code, 422)

    def test_happy_path_writes_coll_inp(self):
        res = self.client.post('/api/save-to-folder', json={
            'folder': str(self.tmp), 'data': self._minimal_data(),
        })
        self.assertEqual(res.status_code, 200)
        json_body = res.get_json()
        self.assertTrue(json_body['ok'])
        target = self.tmp / 'COLL.inp'
        self.assertEqual(json_body['path'], str(target))
        self.assertTrue(target.exists())
        # NGROUP=-2 (2I4) debe aparecer en la Card #5.
        self.assertIn('  -2   0', target.read_text(encoding='utf-8'))

    def test_existing_file_requires_overwrite(self):
        target = self.tmp / 'COLL.inp'
        target.write_text('contenido previo', encoding='utf-8')

        res = self.client.post('/api/save-to-folder', json={
            'folder': str(self.tmp), 'data': self._minimal_data(),
        })
        self.assertEqual(res.status_code, 409)
        self.assertTrue(res.get_json().get('exists'))
        self.assertEqual(target.read_text(encoding='utf-8'), 'contenido previo')

        res = self.client.post('/api/save-to-folder', json={
            'folder': str(self.tmp), 'data': self._minimal_data(), 'overwrite': True,
        })
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(target.read_text(encoding='utf-8'), 'contenido previo')


if __name__ == '__main__':
    unittest.main(verbosity=2)
