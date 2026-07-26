"""Tests de /api/chains-analysis/run (F9 del BACKLOG, Fase 3).

    C:\\venv\\acab-venv\\Scripts\\python.exe tools/test_chains_analysis_run_endpoint.py

Cubre los pre-checks (manifest/subcarpetas/ficheros faltantes, salida
previa sin overwrite, slot ocupado) mockeando runner.start_batch, y el
pipeline REAL encadenado (tape22 -> tape24 -> N x [acab, copy, copy,
chains]) con ejecutables falsos multiplataforma (patrón D1 de
tools/test_run_batch_endpoint.py) — incluyendo un chains.exe falso que lee
stdin y escribe stdout (la extensión que rompe la convención de "exe sin
argumentos", ver runner.py y acab_suite/README.md), sin mockear
runner.start_batch: verifica el encadenado real, el manejo del run IMTX=1
(tape24) que termina sin fort.6 como ÉXITO, y el contenido de
chains_batch_results.json.
"""

import base64
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
import app as app_module      # noqa: E402
import chains_analysis as ca  # noqa: E402
import runner                 # noqa: E402
from acab_parser import ACABParser  # noqa: E402
from app import _write_inp5   # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / 'tests/fixtures/chains'


def _fake_exe_name(name: str) -> str:
    return f'{name}.bat' if sys.platform == 'win32' else name


def _write_fake_launcher(directory: Path, name: str, python_body: str) -> str:
    """Ejecutable falso multiplataforma (D1 del BACKLOG) — ver
    tools/test_run_batch_endpoint.py para el detalle de por qué .bat+impl en
    Windows y script con shebang en POSIX."""
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


def _write_single_file_launcher(directory: Path, name: str, python_body: str) -> str:
    """Como _write_fake_launcher pero en UN SOLO FICHERO, sin script Python
    auxiliar: necesario para chains.exe, porque la generación (Fase 2) solo
    copia el propio ejecutable a cada chains_<isótopo>/ (no la carpeta
    entera, a diferencia de acab.exe). En Windows se codifica en base64
    para evitar cualquier problema de comillas/saltos de línea al incrustar
    el cuerpo en un `python -c`."""
    if sys.platform == 'win32':
        b64 = base64.b64encode(python_body.encode('utf-8')).decode('ascii')
        code = f"import base64;exec(base64.b64decode('{b64}').decode('utf-8'))"
        (directory / f'{name}.bat').write_text(
            '@echo off\r\n'
            f'"{sys.executable}" -c "{code}"\r\n'
            'exit /b %ERRORLEVEL%\r\n',
            encoding='utf-8')
    else:
        script = directory / name
        script.write_text('#!/usr/bin/env python3\n' + python_body, encoding='utf-8')
        script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return _fake_exe_name(name)


# Falso acab.exe: decide qué escribir según el nombre de su cwd (misma
# convención de "carpeta autocontenida" que el resto de la suite). tape22 ->
# fort.22 (pathway analysis); tape24 -> escribe fort.24 y PARA sin fort.6
# (IMTX=1, éxito igualmente); resto (iso_<isotopo>) -> fort.6 (para A_i(t)
# del analyzer).
_ACAB_PY = (
    "import os, sys\n"
    "cwd = os.path.basename(os.getcwd())\n"
    "if cwd == 'tape22':\n"
    "    open('fort.22', 'w').write('fake-fort22\\n')\n"
    "elif cwd == 'tape24':\n"
    "    open('fort.24', 'w').write('fake-fort24\\n')\n"
    "else:\n"
    "    open('fort.6', 'w').write('fake-fort6\\n')\n"
    "sys.exit(0)\n"
)

# Falso chains.exe: falla si fort.22/fort.24 no están en el cwd (verifica que
# los pasos 'copy' corrieron antes); si están, lee TODO su stdin y lo vuelca
# a stdout con un prefijo -- confirma la redirección stdin/stdout del runner.
_CHAINS_PY = (
    "import os, sys\n"
    "if not (os.path.exists('fort.22') and os.path.exists('fort.24')):\n"
    "    sys.exit(1)\n"
    "data = sys.stdin.read()\n"
    "sys.stdout.write('CHAINS OUTPUT\\n' + data)\n"
    "sys.exit(0)\n"
)

# Falso acab.exe que SIEMPRE falla (para el caso 'tape22 falla' del pipeline).
_ACAB_FAIL_PY = "import sys\nsys.exit(1)\n"


def _generate_analysis(root: Path, ref: Path, isotopes=None) -> dict:
    shutil.copy(FIXTURES / 'inp.5_original', ref / 'inp.5')
    payload = {
        'root': str(root), 'reference_folder': str(ref),
        'isotopes': isotopes or [{'name': 'TE130', 'c_i': 1.57e20}],
        'ifinal': 'I131', 'pcnt': 0.01, 'nmax': 5,
    }
    return ca.generate_chains_analysis(payload, _write_inp5)


class ChainsAnalysisRunPrechecksTestCase(unittest.TestCase):

    def setUp(self):
        self.client = app_module.app.test_client()
        self.tmp = Path(tempfile.mkdtemp(prefix='chains_run_precheck_'))
        self._suite_dir_patch = patch.object(app_module, '_suite_dir', return_value=None)
        self._suite_dir_patch.start()
        self._local_cfg_patch = patch.object(
            app_module, '_local_run_config_path', return_value=self.tmp / 'run_config.json')
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

    def test_missing_root(self):
        res = self.client.post('/api/chains-analysis/run', json={})
        self.assertEqual(res.status_code, 422)

    def test_root_does_not_exist(self):
        res = self.client.post('/api/chains-analysis/run',
                               json={'root': str(self.tmp / 'no-existe')})
        self.assertEqual(res.status_code, 422)

    def test_no_manifest_returns_404(self):
        res = self.client.post('/api/chains-analysis/run', json={'root': str(self.tmp)})
        self.assertEqual(res.status_code, 404)

    def test_missing_subfolders(self):
        root = self.tmp / 'out'
        ref = self.tmp / 'ref'
        ref.mkdir()
        root.mkdir()
        _generate_analysis(root, ref)
        shutil.rmtree(root / 'chains_TE130')

        res = self.client.post('/api/chains-analysis/run', json={'root': str(root)})
        self.assertEqual(res.status_code, 422)
        self.assertIn('chains_TE130', res.get_json()['error'])

    def test_missing_required_files(self):
        root = self.tmp / 'out'
        ref = self.tmp / 'ref'
        ref.mkdir()
        root.mkdir()
        _generate_analysis(root, ref)
        # Ningún acab.exe/chains.exe real fue copiado (la referencia no
        # tenía ninguno): deben faltar en todas las subcarpetas.
        res = self.client.post('/api/chains-analysis/run', json={'root': str(root)})
        self.assertEqual(res.status_code, 422)
        err = res.get_json()['error']
        self.assertIn('acab.exe', err)
        self.assertIn('chains.exe', err)

    def test_existing_output_requires_overwrite(self):
        root = self.tmp / 'out'
        ref = self.tmp / 'ref'
        ref.mkdir()
        (ref / 'acab.exe').write_text('fake', encoding='utf-8')
        (ref / 'chains.exe').write_text('fake', encoding='utf-8')
        res = _generate_analysis(root, ref)
        (root / res['manifest']['isotopes'][0]['iso_folder'] / 'fort.6').write_text(
            'old', encoding='utf-8')

        with patch.object(runner, 'start_batch') as mock_start:
            r = self.client.post('/api/chains-analysis/run', json={'root': str(root)})
            self.assertEqual(r.status_code, 422)
            self.assertTrue(r.get_json().get('needs_overwrite'))
            mock_start.assert_not_called()

            r = self.client.post('/api/chains-analysis/run',
                                 json={'root': str(root), 'overwrite': True})
            self.assertEqual(r.status_code, 200)
            mock_start.assert_called_once()

    def test_busy_returns_409(self):
        root = self.tmp / 'out'
        ref = self.tmp / 'ref'
        ref.mkdir()
        (ref / 'acab.exe').write_text('fake', encoding='utf-8')
        (ref / 'chains.exe').write_text('fake', encoding='utf-8')
        _generate_analysis(root, ref)

        with patch.object(runner, 'start_batch',
                          side_effect=runner.RunnerBusyError('ocupado')):
            res = self.client.post('/api/chains-analysis/run', json={'root': str(root)})
            self.assertEqual(res.status_code, 409)

    def test_happy_path_builds_jobs(self):
        root = self.tmp / 'out'
        ref = self.tmp / 'ref'
        ref.mkdir()
        (ref / 'acab.exe').write_text('fake', encoding='utf-8')
        (ref / 'chains.exe').write_text('fake', encoding='utf-8')
        res = _generate_analysis(root, ref)

        with patch.object(runner, 'start_batch') as mock_start:
            r = self.client.post('/api/chains-analysis/run', json={'root': str(root)})
            self.assertEqual(r.status_code, 200, r.get_json())
            body = r.get_json()
            self.assertTrue(body['ok'])
            self.assertEqual(body['n'], 3)  # tape22 + tape24 + 1 isótopo

            _, kwargs = mock_start.call_args
            self.assertEqual(len(kwargs['jobs']), 3)
            self.assertEqual(
                kwargs['results_path'], str(root / 'chains_batch_results.json'))
            iso_folder = res['manifest']['isotopes'][0]['iso_folder']
            self.assertEqual(kwargs['jobs'][2]['workdir'], str(root / iso_folder))


def _wait_batch_done(client, timeout: float = 20.0, poll: float = 0.1) -> dict:
    t0 = time.monotonic()
    s = {}
    while time.monotonic() - t0 < timeout:
        s = client.get('/api/run/status').get_json()['status']
        if s.get('mode') == 'batch' and not s.get('running', True):
            return s
        time.sleep(poll)
    return s


class ChainsAnalysisPipelineEndToEndTestCase(unittest.TestCase):
    """Pipeline real con ejecutables falsos (D1), SIN mockear
    runner.start_batch: verifica el encadenado real tape22 -> tape24 ->
    [acab, copy fort.22, copy fort.24, chains] por isótopo."""

    def setUp(self):
        self.client = app_module.app.test_client()
        self.tmp = Path(tempfile.mkdtemp(prefix='chains_run_e2e_'))
        self._suite_dir_patch = patch.object(app_module, '_suite_dir', return_value=None)
        self._suite_dir_patch.start()
        self._local_cfg_patch = patch.object(
            app_module, '_local_run_config_path', return_value=self.tmp / 'run_config.json')
        self._local_cfg_patch.start()
        self._chains_exe_patch = patch.object(
            app_module, '_CHAINS_EXE_NAME', _fake_exe_name('chains'))
        self._chains_exe_patch.start()
        app_module._save_runner_config({'exe_name': _fake_exe_name('acab')})

    def tearDown(self):
        self._chains_exe_patch.stop()
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

    def _generate(self, acab_body=_ACAB_PY):
        ref = self.tmp / 'ref'
        ref.mkdir()
        shutil.copy(FIXTURES / 'inp.5_original', ref / 'inp.5')
        _write_fake_launcher(ref, 'acab', acab_body)
        _write_single_file_launcher(ref, 'chains', _CHAINS_PY)
        root = self.tmp / 'out'
        payload = {
            'root': str(root), 'reference_folder': str(ref),
            'isotopes': [{'name': 'TE130', 'c_i': 1.57e20}],
            'ifinal': 'I131', 'pcnt': 0.01, 'nmax': 5,
        }
        # La generación copia chains.exe (nombre fijo) de la referencia;
        # aquí el falso se llama chains.bat en Windows, así que se parchea
        # la constante del módulo igual que se hace en app_module para el
        # pre-check de /api/chains-analysis/run.
        with patch.object(ca, 'CHAINS_EXE_NAME', _fake_exe_name('chains')):
            res = ca.generate_chains_analysis(payload, _write_inp5)
        return root, res

    def test_full_pipeline_ok_tape24_succeeds_without_fort6(self):
        root, res = self._generate()

        r = self.client.post('/api/chains-analysis/run', json={'root': str(root)})
        self.assertEqual(r.status_code, 200, r.get_json())

        s = _wait_batch_done(self.client)
        self.assertFalse(s['running'])
        jobs = s['jobs']
        self.assertEqual(len(jobs), 3)
        job_tape22, job_tape24, job_iso = jobs

        # tape22: escribe fort.22 y termina ok.
        self.assertEqual(job_tape22['estado'], 'ok')
        self.assertTrue((root / 'tape22' / 'fort.22').is_file())

        # tape24: IMTX=1 -- NO genera fort.6 (ni fort.22, el fake no lo
        # escribe fuera de tape22) y AUN ASÍ es éxito (decisión de diseño F9).
        self.assertEqual(job_tape24['estado'], 'ok')
        self.assertFalse((root / 'tape24' / 'fort.6').exists())

        # job del isótopo: 4 pasos [run acab, copy fort.22, copy fort.24, run chains]
        self.assertEqual(job_iso['estado'], 'ok')
        iso_folder = res['manifest']['isotopes'][0]['iso_folder']
        chains_folder = res['manifest']['isotopes'][0]['chains_folder']
        self.assertEqual(job_iso['workdir'], str(root / iso_folder))
        steps = job_iso['steps']
        self.assertEqual([st['type'] for st in steps], ['run', 'copy', 'copy', 'run'])
        for st in steps:
            self.assertEqual(st['estado'], 'ok', st)

        self.assertTrue((root / iso_folder / 'fort.6').is_file())
        self.assertTrue((root / chains_folder / 'fort.22').is_file())
        self.assertTrue((root / chains_folder / 'fort.24').is_file())

        # chains.exe leyó stdin (input_chain.txt) y escribió stdout
        # (output_chain.txt) vía la redirección del runner.
        out = (root / chains_folder / 'output_chain.txt').read_text(encoding='utf-8')
        self.assertTrue(out.startswith('CHAINS OUTPUT\n'))
        input_chain = (root / chains_folder / 'input_chain.txt').read_text(encoding='utf-8')
        self.assertIn(input_chain, out)

        with open(root / 'chains_batch_results.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data['resumen']['total'], 3)
        self.assertEqual(data['resumen']['ok'], 3)
        self.assertEqual(data['resumen']['fallos'], 0)

    def test_tape22_failure_stops_chains_step_for_dependent_isotope(self):
        # Si acab.exe falla SIEMPRE, tape22 no escribe fort.22; el job del
        # isótopo corre igualmente (jobs independientes en la cola) pero su
        # paso 'copy' de fort.22 falla al no encontrar el origen.
        root, res = self._generate(acab_body=_ACAB_FAIL_PY)

        r = self.client.post('/api/chains-analysis/run', json={'root': str(root)})
        self.assertEqual(r.status_code, 200, r.get_json())
        s = _wait_batch_done(self.client)

        job_tape22, job_tape24, job_iso = s['jobs']
        self.assertEqual(job_tape22['estado'], 'failed')
        self.assertEqual(job_tape24['estado'], 'failed')
        # El job del isótopo también falla: su propio paso 'run' (acab.exe
        # fake que siempre falla) es el primero en fallar.
        self.assertEqual(job_iso['estado'], 'failed')
        self.assertEqual(job_iso['steps'][0]['type'], 'run')
        self.assertEqual(job_iso['steps'][0]['estado'], 'failed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
