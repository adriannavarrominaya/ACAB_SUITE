"""Tests de los endpoints de ejecución (Fase R3 del runbook runner v2).

    C:\\venv\\acab-venv\\Scripts\\python.exe tools/test_run_endpoints.py

Cubre /api/run, /api/run/config, /api/run/status y /api/run/cancel con el
test_client de Flask: pre-checks 422 (workdir/ejecutable/ficheros requeridos
ausentes, salida previa sin overwrite), 409 (slot ocupado) y camino feliz.
runner.start se mockea para no depender de un ejecutable real: el
comportamiento del runner en sí (subprocesos, timeout, cola…) ya está
cubierto por tools/test_runner.py.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as app_module  # noqa: E402
import runner  # noqa: E402


class RunEndpointsTestCase(unittest.TestCase):

    def setUp(self):
        self.client = app_module.app.test_client()
        self.tmp = Path(tempfile.mkdtemp(prefix='run_endpoint_test_'))

        # Aislar la config del runner del acab_suite real que pueda existir
        # en la máquina de desarrollo: forzar fallback al fichero local, y
        # apuntar ese fichero local dentro del directorio temporal del test.
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
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── /api/run/config ──────────────────────────────────────────────

    def test_config_roundtrip(self):
        res = self.client.get('/api/run/config')
        self.assertEqual(res.status_code, 200)
        cfg = res.get_json()['config']
        self.assertEqual(cfg['exe_name'], 'acab.exe')
        self.assertEqual(cfg['output_file'], 'fort.6')

        res = self.client.post('/api/run/config', json={'timeout_s': 90})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['config']['timeout_s'], 90)

        # Debe persistir entre peticiones
        res = self.client.get('/api/run/config')
        self.assertEqual(res.get_json()['config']['timeout_s'], 90)

    # ── Pre-checks 422 ───────────────────────────────────────────────

    def test_missing_workdir_field(self):
        res = self.client.post('/api/run', json={})
        self.assertEqual(res.status_code, 422)

    def test_workdir_does_not_exist(self):
        res = self.client.post('/api/run', json={
            'workdir': str(self.tmp / 'no-existe'), 'save_current': False,
        })
        self.assertEqual(res.status_code, 422)

    def test_missing_executable(self):
        res = self.client.post('/api/run', json={
            'workdir': str(self.tmp), 'save_current': False,
        })
        self.assertEqual(res.status_code, 422)
        self.assertIn('acab.exe', res.get_json()['error'])

    def test_missing_required_files(self):
        (self.tmp / 'acab.exe').write_text('fake', encoding='utf-8')
        res = self.client.post('/api/run', json={
            'workdir': str(self.tmp), 'save_current': False,
        })
        self.assertEqual(res.status_code, 422)
        self.assertIn('inp.5', res.get_json()['error'])
        self.assertIn('DECAY.dat', res.get_json()['error'])
        self.assertIn('XSECTION.dat', res.get_json()['error'])

    def test_output_exists_requires_overwrite(self):
        (self.tmp / 'acab.exe').write_text('fake', encoding='utf-8')
        (self.tmp / 'inp.5').write_text('x', encoding='utf-8')
        (self.tmp / 'DECAY.dat').write_text('x', encoding='utf-8')
        (self.tmp / 'XSECTION.dat').write_text('x', encoding='utf-8')
        (self.tmp / 'fort.6').write_text('old output', encoding='utf-8')

        with patch.object(runner, 'start') as mock_start:
            res = self.client.post('/api/run', json={
                'workdir': str(self.tmp), 'save_current': False,
            })
            self.assertEqual(res.status_code, 422)
            self.assertTrue(res.get_json().get('needs_overwrite'))
            mock_start.assert_not_called()

            res = self.client.post('/api/run', json={
                'workdir': str(self.tmp), 'save_current': False, 'overwrite': True,
            })
            self.assertEqual(res.status_code, 200)
            mock_start.assert_called_once()

    # ── Camino feliz ─────────────────────────────────────────────────

    def test_happy_path_saves_current_and_starts(self):
        (self.tmp / 'acab.exe').write_text('fake', encoding='utf-8')
        (self.tmp / 'DECAY.dat').write_text('x', encoding='utf-8')
        (self.tmp / 'XSECTION.dat').write_text('x', encoding='utf-8')

        with patch.object(runner, 'start') as mock_start:
            res = self.client.post('/api/run', json={
                'workdir': str(self.tmp),
                'save_current': True,
                'data': app_module._default_data(),
            })
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.get_json()['ok'])
            mock_start.assert_called_once()
            _, kwargs = mock_start.call_args
            self.assertEqual(kwargs['workdir'], str(self.tmp))
            self.assertEqual(kwargs['cmd'], [str(self.tmp / 'acab.exe')])

        self.assertTrue((self.tmp / 'inp.5').exists())

        # El workdir/exe/timeout usados quedan persistidos.
        cfg = self.client.get('/api/run/config').get_json()['config']
        self.assertEqual(cfg['default_workdir'], str(self.tmp))

    # ── 409 slot ocupado ─────────────────────────────────────────────

    def test_busy_returns_409(self):
        (self.tmp / 'acab.exe').write_text('fake', encoding='utf-8')
        (self.tmp / 'inp.5').write_text('x', encoding='utf-8')
        (self.tmp / 'DECAY.dat').write_text('x', encoding='utf-8')
        (self.tmp / 'XSECTION.dat').write_text('x', encoding='utf-8')

        with patch.object(runner, 'start', side_effect=runner.RunnerBusyError('ocupado')):
            res = self.client.post('/api/run', json={
                'workdir': str(self.tmp), 'save_current': False,
            })
            self.assertEqual(res.status_code, 409)

    # ── status / cancel ──────────────────────────────────────────────

    def test_status_and_cancel_endpoints(self):
        res = self.client.get('/api/run/status')
        self.assertEqual(res.status_code, 200)
        self.assertIn('status', res.get_json())

        res = self.client.post('/api/run/cancel')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['ok'])

    # ── output_exists / deep link al analyzer (Fase R3) ───────────────

    def test_status_reports_output_exists_after_ok_run(self):
        """Tras un run real con returncode 0 y fort.6 generado, /api/run/status
        debe incluir output_exists=True y el workdir (botón 'Abrir en Fort
        Analyzer')."""
        (self.tmp / 'acab.exe').write_text('fake', encoding='utf-8')
        (self.tmp / 'inp.5').write_text('x', encoding='utf-8')
        (self.tmp / 'DECAY.dat').write_text('x', encoding='utf-8')
        (self.tmp / 'XSECTION.dat').write_text('x', encoding='utf-8')

        fake_exe_code = (
            "import sys\n"
            "open('fort.6', 'w').write('OUTPUT')\n"
            "sys.exit(0)\n"
        )

        def _fake_start(cmd, workdir, timeout_s):
            (Path(workdir) / '_fake.py').write_text(fake_exe_code, encoding='utf-8')
            subprocess.run(
                [sys.executable, str(Path(workdir) / '_fake.py')],
                cwd=workdir, check=True)
            # Simula el estado final que dejaría el runner real tras un
            # proceso terminado con éxito.
            runner._runner._mode = 'idle'
            runner._runner._returncode = 0
            runner._runner._workdir = workdir
            runner._runner._start_time = 0
            runner._runner._timed_out = False

        with patch.object(runner, 'start', side_effect=_fake_start):
            res = self.client.post('/api/run', json={
                'workdir': str(self.tmp), 'save_current': False,
            })
            self.assertEqual(res.status_code, 200)

        res = self.client.get('/api/run/status')
        s = res.get_json()['status']
        self.assertTrue(s.get('output_exists'))
        self.assertEqual(s.get('workdir'), str(self.tmp))


if __name__ == '__main__':
    unittest.main(verbosity=2)
