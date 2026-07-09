"""Tests de /api/run/batch (Fase R4 del runbook runner v2).

    C:\\venv\\acab-venv\\Scripts\\python.exe tools/test_run_batch_endpoint.py

Cubre las validaciones y pre-checks de /api/run/batch (carpeta raíz, lectura
de sweep_manifest.json, subcarpetas/ficheros faltantes, salida previa sin
overwrite, slot ocupado, folders explícitos) y el enriquecimiento de
/api/run/status con 'root' para el modo batch. runner.start_batch se mockea
para no depender de un ejecutable real: la mecánica del runner en sí (cola,
job que falla, cancelación) ya está cubierta por tools/test_runner.py.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as app_module  # noqa: E402
import runner  # noqa: E402


def _write_manifest(root: Path, folders):
    manifest = {
        'timestamp': '2026-01-01T00:00:00+00:00',
        'sweep_type': 'flux',
        'description': 'test',
        'fixed_params': {},
        'n': len(folders),
        'simulations': [{'folder': f, 'params': {}} for f in folders],
    }
    (root / 'sweep_manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False), encoding='utf-8')


def _make_sim_folder(root: Path, folder: str, *, with_output: bool = False) -> Path:
    d = root / folder
    d.mkdir(parents=True)
    (d / 'acab.exe').write_text('fake', encoding='utf-8')
    (d / 'inp.5').write_text('x', encoding='utf-8')
    (d / 'DECAY.dat').write_text('x', encoding='utf-8')
    (d / 'XSECTION.dat').write_text('x', encoding='utf-8')
    if with_output:
        (d / 'fort.6').write_text('old output', encoding='utf-8')
    return d


class RunBatchEndpointTestCase(unittest.TestCase):

    def setUp(self):
        self.client = app_module.app.test_client()
        self.tmp = Path(tempfile.mkdtemp(prefix='run_batch_test_'))

        # Aislar la config del runner del acab_suite real que pueda existir
        # en la máquina de desarrollo (igual que test_run_endpoints.py).
        self._suite_dir_patch = patch.object(app_module, '_suite_dir', return_value=None)
        self._suite_dir_patch.start()
        self._local_cfg_patch = patch.object(
            app_module, '_local_run_config_path',
            return_value=self.tmp / 'run_config.json')
        self._local_cfg_patch.start()

    def tearDown(self):
        self._local_cfg_patch.stop()
        self._suite_dir_patch.stop()
        try:
            runner.cancel()
        except Exception:
            pass
        runner._runner._reset_state()
        app_module._last_batch_root = None
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── Pre-checks 422 / 404 ─────────────────────────────────────────

    def test_missing_root(self):
        res = self.client.post('/api/run/batch', json={})
        self.assertEqual(res.status_code, 422)

    def test_root_does_not_exist(self):
        res = self.client.post('/api/run/batch', json={
            'root': str(self.tmp / 'no-existe'),
        })
        self.assertEqual(res.status_code, 422)

    def test_no_manifest_returns_404(self):
        res = self.client.post('/api/run/batch', json={'root': str(self.tmp)})
        self.assertEqual(res.status_code, 404)

    def test_missing_subfolders(self):
        _write_manifest(self.tmp, ['sim_0', 'sim_1'])
        _make_sim_folder(self.tmp, 'sim_0')
        # sim_1 declarada en el manifest pero no existe en disco.
        res = self.client.post('/api/run/batch', json={'root': str(self.tmp)})
        self.assertEqual(res.status_code, 422)
        self.assertIn('sim_1', res.get_json()['error'])

    def test_missing_required_files(self):
        d = self.tmp / 'sim_0'
        d.mkdir()
        (d / 'acab.exe').write_text('fake', encoding='utf-8')
        _write_manifest(self.tmp, ['sim_0'])
        res = self.client.post('/api/run/batch', json={'root': str(self.tmp)})
        self.assertEqual(res.status_code, 422)
        self.assertIn('inp.5', res.get_json()['error'])

    def test_existing_output_requires_overwrite(self):
        _write_manifest(self.tmp, ['sim_0'])
        _make_sim_folder(self.tmp, 'sim_0', with_output=True)

        with patch.object(runner, 'start_batch') as mock_start:
            res = self.client.post('/api/run/batch', json={'root': str(self.tmp)})
            self.assertEqual(res.status_code, 422)
            self.assertTrue(res.get_json().get('needs_overwrite'))
            mock_start.assert_not_called()

            res = self.client.post('/api/run/batch', json={
                'root': str(self.tmp), 'overwrite': True,
            })
            self.assertEqual(res.status_code, 200)
            mock_start.assert_called_once()

    def test_busy_returns_409(self):
        _write_manifest(self.tmp, ['sim_0'])
        _make_sim_folder(self.tmp, 'sim_0')

        with patch.object(runner, 'start_batch',
                          side_effect=runner.RunnerBusyError('ocupado')):
            res = self.client.post('/api/run/batch', json={'root': str(self.tmp)})
            self.assertEqual(res.status_code, 409)

    # ── Camino feliz: jobs y cmd_template construidos correctamente ──

    def test_happy_path_builds_jobs_and_cmd_template(self):
        _write_manifest(self.tmp, ['sim_0', 'sim_1'])
        d0 = _make_sim_folder(self.tmp, 'sim_0')
        d1 = _make_sim_folder(self.tmp, 'sim_1')

        with patch.object(runner, 'start_batch') as mock_start:
            res = self.client.post('/api/run/batch', json={'root': str(self.tmp)})
            self.assertEqual(res.status_code, 200)
            body = res.get_json()
            self.assertTrue(body['ok'])
            self.assertEqual(body['n'], 2)
            self.assertEqual(body['root'], str(self.tmp))

            mock_start.assert_called_once()
            _, kwargs = mock_start.call_args
            self.assertEqual(kwargs['jobs'], [
                {'workdir': str(d0)}, {'workdir': str(d1)},
            ])
            # El template lleva el marcador '{workdir}' para formatearse
            # por-job dentro de runner._batch_loop (cada subcarpeta lleva su
            # propia copia del ejecutable), y el nombre del ejecutable
            # configurado.
            self.assertIn('{workdir}', kwargs['cmd_template'])
            self.assertIn('acab.exe', kwargs['cmd_template'])
            self.assertEqual(
                kwargs['results_path'], str(self.tmp / 'batch_results.json'))

    def test_explicit_folders_bypass_manifest(self):
        # Justo tras generar un barrido, el cliente ya tiene la lista de
        # subcarpetas (res.folders) y puede pasarla explícita sin depender
        # de releer sweep_manifest.json.
        d0 = _make_sim_folder(self.tmp, 'sim_a')
        with patch.object(runner, 'start_batch') as mock_start:
            res = self.client.post('/api/run/batch', json={
                'root': str(self.tmp), 'folders': ['sim_a'],
            })
            self.assertEqual(res.status_code, 200)
            _, kwargs = mock_start.call_args
            self.assertEqual(kwargs['jobs'], [{'workdir': str(d0)}])

    # ── /api/run/status enriquecido con 'root' para el barrido ────────

    def test_status_reports_root_for_batch(self):
        _write_manifest(self.tmp, ['sim_0'])
        _make_sim_folder(self.tmp, 'sim_0')

        with patch.object(runner, 'start_batch'):
            res = self.client.post('/api/run/batch', json={'root': str(self.tmp)})
            self.assertEqual(res.status_code, 200)

        with patch.object(runner, 'status', return_value={
                'mode': 'batch', 'running': False, 'current_index': 0,
                'jobs': [], 'log_tail': '',
        }):
            res = self.client.get('/api/run/status')
            self.assertEqual(res.get_json()['status']['root'], str(self.tmp))


if __name__ == '__main__':
    unittest.main(verbosity=2)
