"""Tests del runner de ejecución (Fase R3 del runbook runner v2).

    C:\\venv\\acab-venv\\Scripts\\python.exe tools/test_runner.py

Cubre: ejecución individual (feliz, rechazo de slot ocupado, timeout,
cancel), cola/batch (job fallido que no para la cola, cancelación a
mitad, log_tail del job en curso).

Usa un ejecutable falso multiplataforma: un script Python que imprime
líneas con delay y sale con el código pedido.
"""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

# ── Acceso al módulo runner (una carpeta arriba) ────────────────────────

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runner  # noqa: E402


# ── Ejecutable falso (script Python multiplataforma) ────────────────────

_FAKE_EXE_CODE = r'''#!/usr/bin/env python
"""Ejecutable falso para tests del runner.

Imprime --lines líneas (con --delay entre ellas) y sale con --exit-code.
"""
import argparse
import sys
import time

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--lines', type=int, default=5)
    p.add_argument('--delay', type=float, default=0.05)
    p.add_argument('--exit-code', type=int, default=0)
    args = p.parse_args()
    for i in range(args.lines):
        print(f'Line {i+1} of {args.lines}')
        sys.stdout.flush()
        if args.delay > 0:
            time.sleep(args.delay)
    sys.exit(args.exit_code)

if __name__ == '__main__':
    main()
'''


def _write_fake_exe(directory: Path) -> Path:
    """Escribe _fake_exe.py en *directory* y devuelve su ruta."""
    p = directory / '_fake_exe.py'
    p.write_text(_FAKE_EXE_CODE, encoding='utf-8')
    return p


def _cmd(fake_exe: Path, *, lines: int = 5, delay: float = 0.05,
         exit_code: int = 0) -> list[str]:
    """Construye el comando para el ejecutable falso."""
    return [
        sys.executable, str(fake_exe),
        '--lines', str(lines),
        '--delay', str(delay),
        '--exit-code', str(exit_code),
    ]


def _wait_done(timeout: float = 15.0, poll: float = 0.1) -> dict:
    """Espera a que el runner termine (running=False), con timeout."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        s = runner.status()
        if not s.get('running', False) and s.get('mode') != 'idle':
            return s
        # Si volvió a idle sin datos (p.ej. tras reset), seguir esperando
        if s.get('mode') == 'idle' and 'returncode' not in s and 'jobs' not in s:
            time.sleep(poll)
            continue
        if not s.get('running', False):
            return s
        time.sleep(poll)
    return runner.status()


# ── Helpers de limpieza del singleton ────────────────────────────────────

def _force_reset():
    """Forzar reset del runner entre tests."""
    # Cancelar cualquier cosa pendiente
    try:
        runner.cancel()
    except Exception:
        pass
    # Esperar brevemente a que acabe
    for _ in range(50):
        s = runner.status()
        if s.get('mode') == 'idle' or not s.get('running', False):
            break
        time.sleep(0.1)
    # Reset interno
    runner._runner._reset_state()


# ═══════════════════════════════════════════════════════════════════════
# Tests — Single
# ═══════════════════════════════════════════════════════════════════════

class TestSingleHappy(unittest.TestCase):
    """Ejecución individual feliz: lanza, espera, comprueba resultado."""

    def setUp(self):
        _force_reset()
        self.tmp = Path(tempfile.mkdtemp(prefix='runner_test_'))
        self.fake = _write_fake_exe(self.tmp)

    def tearDown(self):
        _force_reset()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_happy_path(self):
        runner.start(
            cmd=_cmd(self.fake, lines=3, delay=0.02, exit_code=0),
            workdir=str(self.tmp),
            timeout_s=10,
        )
        # Mientras corre, status debe indicar running
        s = runner.status()
        self.assertEqual(s['mode'], 'single')

        # Esperar a que termine
        s = _wait_done()
        self.assertFalse(s['running'])
        self.assertEqual(s['returncode'], 0)
        self.assertFalse(s['timed_out'])
        self.assertIn('Line 1', s['log_tail'])
        self.assertIn('Line 3', s['log_tail'])

        # run.log debe existir
        log_path = self.tmp / 'run.log'
        self.assertTrue(log_path.exists())


class TestSingleRejectBusy(unittest.TestCase):
    """Segundo start mientras el primero corre → RunnerBusyError."""

    def setUp(self):
        _force_reset()
        self.tmp = Path(tempfile.mkdtemp(prefix='runner_test_'))
        self.fake = _write_fake_exe(self.tmp)

    def tearDown(self):
        _force_reset()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reject(self):
        # Lanzar un proceso largo
        runner.start(
            cmd=_cmd(self.fake, lines=100, delay=0.1, exit_code=0),
            workdir=str(self.tmp),
            timeout_s=30,
        )
        time.sleep(0.2)  # Darle tiempo a arrancar

        # El segundo start debe fallar
        with self.assertRaises(runner.RunnerBusyError):
            runner.start(
                cmd=_cmd(self.fake, lines=1, delay=0, exit_code=0),
                workdir=str(self.tmp),
                timeout_s=10,
            )


class TestSingleTimeout(unittest.TestCase):
    """Proceso que excede el timeout → estado timeout."""

    def setUp(self):
        _force_reset()
        self.tmp = Path(tempfile.mkdtemp(prefix='runner_test_'))
        self.fake = _write_fake_exe(self.tmp)

    def tearDown(self):
        _force_reset()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_timeout(self):
        # Proceso que tardaría 10 s pero con timeout de 1 s
        runner.start(
            cmd=_cmd(self.fake, lines=200, delay=0.1, exit_code=0),
            workdir=str(self.tmp),
            timeout_s=1.0,
        )
        s = _wait_done(timeout=10.0)
        self.assertFalse(s['running'])
        self.assertTrue(s['timed_out'])


class TestSingleCancel(unittest.TestCase):
    """cancel() durante ejecución → proceso terminado."""

    def setUp(self):
        _force_reset()
        self.tmp = Path(tempfile.mkdtemp(prefix='runner_test_'))
        self.fake = _write_fake_exe(self.tmp)

    def tearDown(self):
        _force_reset()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cancel(self):
        runner.start(
            cmd=_cmd(self.fake, lines=200, delay=0.1, exit_code=0),
            workdir=str(self.tmp),
            timeout_s=60,
        )
        time.sleep(0.3)  # Dejar que empiece
        runner.cancel()
        s = _wait_done(timeout=10.0)
        self.assertFalse(s['running'])
        # El returncode no es 0 (fue killed/terminated)
        # En algunos SO puede ser negativo o != 0
        self.assertNotEqual(s.get('returncode'), 0)


# ═══════════════════════════════════════════════════════════════════════
# Tests — Batch
# ═══════════════════════════════════════════════════════════════════════

class TestBatchWithFailure(unittest.TestCase):
    """Batch de 3 jobs, el 2º falla → el 3º se ejecuta igualmente."""

    def setUp(self):
        _force_reset()
        self.tmp = Path(tempfile.mkdtemp(prefix='runner_test_'))
        self.dirs = []
        for i in range(3):
            d = self.tmp / f'sim_{i}'
            d.mkdir()
            _write_fake_exe(d)
            self.dirs.append(d)

    def tearDown(self):
        _force_reset()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_batch_continues_after_failure(self):
        results_path = str(self.tmp / 'batch_results.json')

        # Job 0: ok, Job 1: falla (exit 1), Job 2: ok
        jobs = [{'workdir': str(d)} for d in self.dirs]

        # Usamos cmd_template como lista; variamos exit code por job
        # Para esto, escribimos fake_exe con distintos exit codes
        # Re-escribir fake exe en dir 1 para que falle
        fail_code = r'''#!/usr/bin/env python
import sys, time
for i in range(3):
    print(f'Line {i+1}')
    sys.stdout.flush()
    time.sleep(0.02)
sys.exit(1)
'''
        (self.dirs[1] / '_fake_exe.py').write_text(fail_code, encoding='utf-8')

        cmd = [sys.executable, '_fake_exe.py']

        runner.start_batch(
            jobs=jobs,
            cmd_template=cmd,
            timeout_s_per_sim=10,
            results_path=results_path,
        )

        s = _wait_done(timeout=15.0)
        self.assertFalse(s['running'])

        # Verificar estados
        self.assertEqual(s['jobs'][0]['estado'], 'ok')
        self.assertEqual(s['jobs'][1]['estado'], 'failed')
        self.assertEqual(s['jobs'][2]['estado'], 'ok')

        # batch_results.json debe existir y ser coherente
        self.assertTrue(Path(results_path).exists())
        with open(results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data['resumen']['total'], 3)
        self.assertEqual(data['resumen']['ok'], 2)
        self.assertEqual(data['resumen']['fallos'], 1)
        self.assertEqual(data['resumen']['canceladas'], 0)

        # Cada job tiene duracion_s y timestamps
        for j in data['jobs']:
            self.assertIsNotNone(j['duracion_s'])
            self.assertIsNotNone(j['inicio'])
            self.assertIsNotNone(j['fin'])


class TestBatchCancel(unittest.TestCase):
    """cancel() durante job 2 → job 3 queda 'cancelled'."""

    def setUp(self):
        _force_reset()
        self.tmp = Path(tempfile.mkdtemp(prefix='runner_test_'))
        self.dirs = []
        for i in range(3):
            d = self.tmp / f'sim_{i}'
            d.mkdir()
            _write_fake_exe(d)
            self.dirs.append(d)

    def tearDown(self):
        _force_reset()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cancel_during_batch(self):
        results_path = str(self.tmp / 'batch_results.json')

        # Job 0: rápido (termina en ~0.1 s); jobs 1-2: lentos (5 s cada uno)
        fast_code = (
            '#!/usr/bin/env python\n'
            'import sys, time\n'
            'for i in range(2): print(f"fast {i}"); sys.stdout.flush()\n'
            'time.sleep(0.05)\n'
            'sys.exit(0)\n'
        )
        (self.dirs[0] / '_fake_exe.py').write_text(fast_code, encoding='utf-8')
        # dirs 1 y 2 ya tienen el fake exe lento por defecto (5 lines × 0.05)
        # Reescribirlos para que sean realmente lentos
        slow_code = (
            '#!/usr/bin/env python\n'
            'import sys, time\n'
            'for i in range(100):\n'
            '    print(f"slow {i}")\n'
            '    sys.stdout.flush()\n'
            '    time.sleep(0.05)\n'
            'sys.exit(0)\n'
        )
        (self.dirs[1] / '_fake_exe.py').write_text(slow_code, encoding='utf-8')
        (self.dirs[2] / '_fake_exe.py').write_text(slow_code, encoding='utf-8')

        jobs = [{'workdir': str(d)} for d in self.dirs]
        cmd = [sys.executable, '_fake_exe.py']

        runner.start_batch(
            jobs=jobs,
            cmd_template=cmd,
            timeout_s_per_sim=30,
            results_path=results_path,
        )

        # Esperar a que el job 0 termine y estemos en job 1 o posterior
        for _ in range(100):
            s = runner.status()
            if s.get('current_index', -1) >= 1:
                break
            time.sleep(0.1)

        # Ahora cancelar durante job 1 o 2
        runner.cancel()

        s = _wait_done(timeout=15.0)
        self.assertFalse(s['running'])

        # Job 0 debe haber terminado ok (era rápido)
        self.assertEqual(s['jobs'][0]['estado'], 'ok')
        # Al menos un job debe estar cancelled
        cancelled_count = sum(1 for j in s['jobs'] if j['estado'] == 'cancelled')
        self.assertGreaterEqual(cancelled_count, 1,
                                'Al menos un job debe quedar cancelled')

        # batch_results.json debe haberse escrito
        self.assertTrue(Path(results_path).exists())
        with open(results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertGreaterEqual(data['resumen']['canceladas'], 1)


class TestBatchLogTail(unittest.TestCase):
    """Durante batch, status() devuelve log_tail del job en curso."""

    def setUp(self):
        _force_reset()
        self.tmp = Path(tempfile.mkdtemp(prefix='runner_test_'))
        self.dirs = []
        for i in range(2):
            d = self.tmp / f'sim_{i}'
            d.mkdir()
            _write_fake_exe(d)
            self.dirs.append(d)

    def tearDown(self):
        _force_reset()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_log_tail_during_batch(self):
        results_path = str(self.tmp / 'batch_results.json')

        jobs = [{'workdir': str(d)} for d in self.dirs]
        # Job lento para dar tiempo a leer log_tail
        cmd = [sys.executable, '_fake_exe.py', '--lines', '20', '--delay', '0.1']

        runner.start_batch(
            jobs=jobs,
            cmd_template=cmd,
            timeout_s_per_sim=30,
            results_path=results_path,
        )

        # Esperar un poco para que se genere algo de log
        time.sleep(0.5)

        s = runner.status()
        self.assertEqual(s['mode'], 'batch')
        self.assertTrue(s['running'])
        # log_tail debe contener algo del job en curso
        self.assertTrue(len(s['log_tail']) > 0,
                        'log_tail debe contener output del job en curso')
        self.assertIn('Line', s['log_tail'])

        # Esperar a que termine todo
        _wait_done(timeout=15.0)


# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    unittest.main(verbosity=2)
