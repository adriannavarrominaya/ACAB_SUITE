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
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as app_module  # noqa: E402
import runner  # noqa: E402


def _write_manifest(root: Path, folders, sweep_type: str = 'flux'):
    manifest = {
        'timestamp': '2026-01-01T00:00:00+00:00',
        'sweep_type': sweep_type,
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
        app_module._last_batch_pipeline_steps = None
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


# ═══════════════════════════════════════════════════════════════════════
# Barrido espectral (Fase P4, D7 del RUNBOOK_barrido_espectral.md): pipeline
# real encadenado (collaps -> copy XSECTION.dat -> acab -> check_flux) con
# ejecutables falsos Python multiplataforma (D1 del BACKLOG), SIN mockear
# runner.start_batch — verifica el encadenado real, no solo la construcción
# de jobs.
# ═══════════════════════════════════════════════════════════════════════

# Fixture de FLUX.inf (mismo formato que tools/test_runner.py): REAL TOTAL
# FLUX=6.6700E+13, AVERAGE ENERGY=6.2744E-07 MeV.
_FLUX_INF_FIXTURE = """  ILIB,IESF =            2           5
  ngroup,ff =           -3           0
 REAL TOTAL FLUX AND AVERAGE ENERGY (MeV)
 6.6700E+13
 6.2744E-07
"""

# El falso collaps: crea XSECTION.dat y copia la plantilla de FLUX.inf.
_COLLAPS_OK_PY = (
    "with open('XSECTION.dat', 'w') as f:\n"
    "    f.write('fake-xsection\\n')\n"
    "import shutil\n"
    "shutil.copyfile('_flux_template.inf', 'FLUX.inf')\n"
)
# El falso collaps que falla: no crea nada, sale con código != 0.
_COLLAPS_FAIL_PY = "import sys\nsys.exit(1)\n"
# El falso acab: falla si XSECTION.dat no existe en su cwd; si existe, crea
# fort.6 (verifica que el paso 'copy' del pipeline corrió antes).
_ACAB_PY = (
    "import os, sys\n"
    "if not os.path.exists('XSECTION.dat'):\n"
    "    sys.exit(1)\n"
    "with open('fort.6', 'w') as f:\n"
    "    f.write('fake-fort6\\n')\n"
    "sys.exit(0)\n"
)


def _fake_exe_name(name: str) -> str:
    """Nombre de fichero del ejecutable falso *name* para el SO actual --
    mismo criterio en `_write_fake_launcher` y en cualquier sitio que
    necesite construir el nombre sin escribir el fichero (p. ej. patchear
    `exe_name`/`_COLLAPS_EXE_NAME` o comprobar un mensaje de error)."""
    return f'{name}.bat' if sys.platform == 'win32' else name


def _write_fake_launcher(directory: Path, name: str, python_body: str) -> str:
    """Escribe un ejecutable falso multiplataforma en *directory* (D1 del
    BACKLOG). El runner invoca el ejecutable configurado directamente, sin
    argumentos, con cwd=workdir (ver README, "Invocación de los códigos") —
    ni un .bat ni un script Python son invocables así de forma nativa en
    ambos SO, así que:

      - Windows: `<name>.bat`, un lanzador mínimo (invocable directamente
        por `subprocess.Popen(shell=False)` — Windows delega en cmd.exe
        para .bat/.cmd) que delega en un script Python real escrito junto a
        él (`%~dp0`, no depende del cwd de invocación) y propaga su código
        de salida con `exit /b %ERRORLEVEL%`.
      - POSIX: `<name>` (sin extensión), el propio script Python con
        shebang `#!/usr/bin/env python3` y permiso de ejecución -- no hace
        falta lanzador aparte, invocable directamente como `./<name>`.

    Devuelve el nombre de fichero a usar como exe_name (ver `_fake_exe_name`).
    """
    if sys.platform == 'win32':
        impl_name = f'_{name}_impl.py'
        (directory / impl_name).write_text(python_body, encoding='utf-8')
        (directory / f'{name}.bat').write_text(
            '@echo off\r\n'
            f'"{sys.executable}" "%~dp0{impl_name}" %*\r\n'
            'exit /b %ERRORLEVEL%\r\n',
            encoding='utf-8')
    else:
        script = directory / name
        script.write_text('#!/usr/bin/env python3\n' + python_body, encoding='utf-8')
        script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return _fake_exe_name(name)


def _make_spectrum_sim_folder(root: Path, folder: str, *, collaps_ok: bool = True) -> Path:
    """Carpeta de sim del barrido espectral: ejecutable falso de acab/inp.5/
    DECAY.dat en la raíz + collaps/ con ejecutable falso de collaps/COLL.inp/
    XSBL.dat (convención D6)."""
    d = root / folder
    d.mkdir(parents=True)
    _write_fake_launcher(d, 'acab', _ACAB_PY)
    (d / 'inp.5').write_text('x', encoding='utf-8')
    (d / 'DECAY.dat').write_text('x', encoding='utf-8')

    collaps_dir = d / 'collaps'
    collaps_dir.mkdir()
    (collaps_dir / 'XSBL.dat').write_text('x', encoding='utf-8')
    (collaps_dir / 'COLL.inp').write_text('x', encoding='utf-8')
    (collaps_dir / '_flux_template.inf').write_text(
        _FLUX_INF_FIXTURE, encoding='utf-8')
    _write_fake_launcher(collaps_dir, 'collaps', _COLLAPS_OK_PY if collaps_ok else _COLLAPS_FAIL_PY)
    return d


def _wait_batch_done(client, timeout: float = 20.0, poll: float = 0.1) -> dict:
    """Sondea /api/run/status (no runner.status() directo) para recoger el
    enriquecimiento de app.py: 'root' y 'pipeline_steps' (D7)."""
    t0 = time.monotonic()
    s = {}
    while time.monotonic() - t0 < timeout:
        s = client.get('/api/run/status').get_json()['status']
        if s.get('mode') == 'batch' and not s.get('running', True):
            return s
        time.sleep(poll)
    return s


class TestSpectrumPipelineEndToEnd(unittest.TestCase):
    """Barrido espectral: no se mockea runner.start_batch, así que estos
    tests lanzan de verdad los ejecutables falsos y esperan a que la cola
    acabe (D1 del BACKLOG: fakes Python multiplataforma, ver
    _write_fake_launcher)."""

    def setUp(self):
        self.client = app_module.app.test_client()
        self.tmp = Path(tempfile.mkdtemp(prefix='run_batch_spectrum_test_'))

        self._suite_dir_patch = patch.object(app_module, '_suite_dir', return_value=None)
        self._suite_dir_patch.start()
        self._local_cfg_patch = patch.object(
            app_module, '_local_run_config_path',
            return_value=self.tmp / 'run_config.json')
        self._local_cfg_patch.start()
        # collaps.exe no es configurable en la app (constante de módulo, D7);
        # se sustituye por un ejecutable falso solo para el test.
        self._collaps_exe_patch = patch.object(
            app_module, '_COLLAPS_EXE_NAME', _fake_exe_name('collaps'))
        self._collaps_exe_patch.start()
        app_module._save_runner_config({'exe_name': _fake_exe_name('acab')})

    def tearDown(self):
        self._collaps_exe_patch.stop()
        self._local_cfg_patch.stop()
        self._suite_dir_patch.stop()
        try:
            runner.cancel()
        except Exception:
            pass
        runner._runner._reset_state()
        app_module._last_batch_root = None
        app_module._last_batch_pipeline_steps = None
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_chained_pipeline_real_execution(self):
        _write_manifest(self.tmp, ['sim_0', 'sim_1'], sweep_type='spectrum')
        # sim_0: el collaps falso FALLA -> el pipeline debe pararse en el
        # paso 0, sin copiar XSECTION.dat ni intentar ejecutar acab.
        d0 = _make_spectrum_sim_folder(self.tmp, 'sim_0', collaps_ok=False)
        # sim_1: pipeline completo, todos los pasos ok. La cola debe seguir
        # con esta sim aunque la anterior haya fallado.
        d1 = _make_spectrum_sim_folder(self.tmp, 'sim_1', collaps_ok=True)

        res = self.client.post('/api/run/batch', json={'root': str(self.tmp)})
        self.assertEqual(res.status_code, 200, res.get_json())

        s = _wait_batch_done(self.client)
        self.assertFalse(s['running'])
        self.assertEqual(
            s.get('pipeline_steps'), ['collaps', 'copy', 'acab', 'check_flux'])

        job0, job1 = s['jobs']

        self.assertEqual(job0['estado'], 'failed')
        self.assertEqual(job0['step_index'], 0)
        self.assertEqual(len(job0['steps']), 1)
        self.assertEqual(job0['steps'][0]['type'], 'run')
        self.assertEqual(job0['steps'][0]['estado'], 'failed')
        self.assertFalse((d0 / 'XSECTION.dat').exists())
        self.assertFalse((d0 / 'fort.6').exists())

        self.assertEqual(job1['estado'], 'ok')
        self.assertEqual(len(job1['steps']), 4)
        run_collaps, copy_step, run_acab, flux_step = job1['steps']

        self.assertEqual(run_collaps['type'], 'run')
        self.assertEqual(run_collaps['estado'], 'ok')
        self.assertTrue((d1 / 'collaps' / 'XSECTION.dat').exists())

        self.assertEqual(copy_step['type'], 'copy')
        self.assertEqual(copy_step['estado'], 'ok')
        self.assertTrue((d1 / 'XSECTION.dat').exists())

        self.assertEqual(run_acab['type'], 'run')
        self.assertEqual(run_acab['estado'], 'ok')
        self.assertTrue((d1 / 'fort.6').exists())

        self.assertEqual(flux_step['type'], 'check_flux')
        self.assertEqual(flux_step['estado'], 'ok')
        self.assertAlmostEqual(
            flux_step['data']['real_total_flux'], 6.6700e13, delta=1e9)
        self.assertAlmostEqual(
            flux_step['data']['average_energy_mev'], 6.2744e-07, delta=1e-10)

        with open(self.tmp / 'batch_results.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data['resumen']['total'], 2)
        self.assertEqual(data['resumen']['ok'], 1)
        self.assertEqual(data['resumen']['fallos'], 1)

    def test_missing_collaps_files_returns_422(self):
        _write_manifest(self.tmp, ['sim_0'], sweep_type='spectrum')
        d = self.tmp / 'sim_0'
        d.mkdir()
        _write_fake_launcher(d, 'acab', _ACAB_PY)
        (d / 'inp.5').write_text('x', encoding='utf-8')
        (d / 'DECAY.dat').write_text('x', encoding='utf-8')
        # Sin subcarpeta collaps/: deben faltar el ejecutable de collaps,
        # COLL.inp, XSBL.dat.

        res = self.client.post('/api/run/batch', json={'root': str(self.tmp)})
        self.assertEqual(res.status_code, 422)
        err = res.get_json()['error']
        self.assertIn(f'collaps/{_fake_exe_name("collaps")}', err)
        self.assertIn('collaps/COLL.inp', err)
        self.assertIn('collaps/XSBL.dat', err)

    def test_xsection_not_required_upfront(self):
        # A diferencia del pre-check legacy, XSECTION.dat NO se exige antes
        # de arrancar el barrido espectral: lo genera el propio pipeline.
        _write_manifest(self.tmp, ['sim_0'], sweep_type='spectrum')
        _make_spectrum_sim_folder(self.tmp, 'sim_0', collaps_ok=True)

        with patch.object(runner, 'start_batch') as mock_start:
            res = self.client.post('/api/run/batch', json={'root': str(self.tmp)})
            self.assertEqual(res.status_code, 200, res.get_json())
            mock_start.assert_called_once()
            _, kwargs = mock_start.call_args
            jobs = kwargs['jobs']
            self.assertEqual(len(jobs), 1)
            self.assertIn('steps', jobs[0])
            self.assertEqual(len(jobs[0]['steps']), 4)


if __name__ == '__main__':
    unittest.main(verbosity=2)
