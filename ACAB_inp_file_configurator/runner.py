# runner.py — núcleo de ejecución de simulaciones (single + batch/cola)
# común de la suite — mantener sincronizado
#
# Módulo sin dependencias de Flask. Instancia única a nivel de módulo.
# Importar y usar directamente: runner.start(...), runner.status(), etc.
#
# Modelo de estados: idle | running_single | running_batch
"""Runner de ejecución de simulaciones con soporte de cola secuencial.

API pública del módulo
----------------------
start(cmd, workdir, timeout_s)      — ejecución individual
start_batch(jobs, cmd_template, timeout_s_per_sim, results_path)
                                     — cola secuencial de jobs
status()                             — dict con el estado actual
cancel()                             — cancelar la ejecución en curso
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Excepciones ──────────────────────────────────────────────────────────

class RunnerBusyError(Exception):
    """Se intentó lanzar un proceso cuando el slot ya está ocupado."""


# ── Constantes ───────────────────────────────────────────────────────────

_LOG_FILENAME = 'run.log'
_LOG_TAIL_BYTES = 16384          # 16 KB
_KILL_GRACE_SECONDS = 5.0


# ── Clase interna ────────────────────────────────────────────────────────

class _Runner:
    """Motor de ejecución: un solo slot, modos single y batch."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_state()

    # ── Estado interno ───────────────────────────────────────────────

    def _reset_state(self) -> None:
        """Reiniciar al estado idle (llamar con lock)."""
        self._mode: str = 'idle'               # idle | running_single | running_batch
        self._proc: subprocess.Popen | None = None
        self._log_file: Any = None
        self._workdir: str | None = None
        self._start_time: float | None = None
        self._timed_out: bool = False
        self._returncode: int | None = None
        self._timeout_timer: threading.Timer | None = None
        self._cancel_requested: bool = False

        # Batch-specific
        self._batch_thread: threading.Thread | None = None
        self._batch_jobs: list[dict] = []
        self._batch_results: list[dict] = []
        self._batch_current_index: int = -1
        self._batch_results_path: str | None = None

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _read_log_tail(workdir: str | Path, max_bytes: int = _LOG_TAIL_BYTES) -> str:
        """Lee los últimos *max_bytes* del run.log del workdir dado."""
        log_path = Path(workdir) / _LOG_FILENAME
        try:
            size = log_path.stat().st_size
            with open(log_path, 'rb') as f:
                if size > max_bytes:
                    f.seek(size - max_bytes)
                raw = f.read()
            return raw.decode('utf-8', errors='replace')
        except (OSError, FileNotFoundError):
            return ''

    def _open_log(self, workdir: str | Path) -> Any:
        """Abre run.log para escritura (line-buffered, encoding tolerante)."""
        log_path = Path(workdir) / _LOG_FILENAME
        # Abrir en modo binario sin buffering para flushing inmediato no
        # es práctico; usamos line_buffering con texto + errors='replace'.
        return open(log_path, 'w', encoding='utf-8', errors='replace',
                    buffering=1)  # line-buffered

    def _terminate_proc(self, proc: subprocess.Popen | None) -> None:
        """terminate + kill después de _KILL_GRACE_SECONDS."""
        if proc is None:
            return
        try:
            proc.terminate()
        except OSError:
            return
        try:
            proc.wait(timeout=_KILL_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass

    # ── start (single) ───────────────────────────────────────────────

    def start(self, cmd: list[str] | str, workdir: str,
              timeout_s: float = 60) -> None:
        """Lanza una ejecución individual.

        Parameters
        ----------
        cmd : list[str] | str
            Comando a ejecutar (se pasa a Popen tal cual).
        workdir : str
            Directorio de trabajo (cwd del proceso).
        timeout_s : float
            Segundos máximos de ejecución; 0 = sin timeout.

        Raises
        ------
        RunnerBusyError
            Si ya hay un proceso en ejecución (single o batch).
        """
        with self._lock:
            if self._mode != 'idle':
                raise RunnerBusyError(
                    f'El runner ya está ocupado (modo: {self._mode})')
            self._reset_state()
            self._mode = 'running_single'
            self._workdir = workdir
            self._start_time = time.monotonic()

        # Abrir log y lanzar proceso FUERA del lock (I/O)
        log_f = self._open_log(workdir)
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=workdir,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                # En Windows no usamos shell=True; cmd ya es una lista/str
            )
        except Exception:
            log_f.close()
            with self._lock:
                self._reset_state()
            raise

        with self._lock:
            self._proc = proc
            self._log_file = log_f

        # Hilo vigilante de timeout
        if timeout_s and timeout_s > 0:
            timer = threading.Timer(timeout_s, self._on_timeout_single)
            timer.daemon = True
            timer.start()
            with self._lock:
                self._timeout_timer = timer

        # Hilo que espera al proceso (para marcar fin)
        waiter = threading.Thread(target=self._wait_single, daemon=True)
        waiter.start()

    def _on_timeout_single(self) -> None:
        with self._lock:
            if self._mode != 'running_single' or self._proc is None:
                return
            self._timed_out = True
            proc = self._proc
        self._terminate_proc(proc)

    def _wait_single(self) -> None:
        with self._lock:
            proc = self._proc
        if proc is None:
            return
        proc.wait()
        with self._lock:
            self._returncode = proc.returncode
            self._mode = 'idle'
            if self._timeout_timer:
                self._timeout_timer.cancel()
                self._timeout_timer = None
            if self._log_file:
                try:
                    self._log_file.close()
                except Exception:
                    pass
                self._log_file = None

    # ── start_batch ──────────────────────────────────────────────────

    def start_batch(self, jobs: list[dict], cmd_template: list[str] | str,
                    timeout_s_per_sim: float = 60,
                    results_path: str | None = None) -> None:
        """Lanza una cola secuencial de jobs.

        Parameters
        ----------
        jobs : list[dict]
            Cada elemento: ``{'workdir': '<ruta>'}`` (puede llevar más campos).
        cmd_template : list[str] | str
            Comando a ejecutar.  Si es una cadena que contiene ``{workdir}``,
            se formatea con el workdir de cada job. Si es lista, se usa tal cual
            con cwd=workdir.
        timeout_s_per_sim : float
            Timeout individual por simulación.
        results_path : str | None
            Ruta donde escribir ``batch_results.json`` al acabar/cancelar.
        """
        with self._lock:
            if self._mode != 'idle':
                raise RunnerBusyError(
                    f'El runner ya está ocupado (modo: {self._mode})')
            self._reset_state()
            self._mode = 'running_batch'
            self._batch_jobs = list(jobs)
            self._batch_results = [
                {'workdir': j['workdir'], 'estado': 'pending',
                 'returncode': None, 'duracion_s': None,
                 'inicio': None, 'fin': None}
                for j in jobs
            ]
            self._batch_results_path = results_path
            self._batch_current_index = -1

        t = threading.Thread(
            target=self._batch_loop,
            args=(cmd_template, timeout_s_per_sim),
            daemon=True,
        )
        with self._lock:
            self._batch_thread = t
        t.start()

    def _batch_loop(self, cmd_template: list[str] | str,
                    timeout_s: float) -> None:
        for idx, job in enumerate(self._batch_jobs):
            with self._lock:
                if self._cancel_requested:
                    # Marcar restantes como cancelled
                    for r in self._batch_results[idx:]:
                        if r['estado'] == 'pending':
                            r['estado'] = 'cancelled'
                    break
                self._batch_current_index = idx
                self._batch_results[idx]['estado'] = 'running'

            workdir = job['workdir']
            inicio = datetime.now(timezone.utc).isoformat()
            t0 = time.monotonic()

            with self._lock:
                self._batch_results[idx]['inicio'] = inicio
                self._workdir = workdir

            # Construir comando
            if isinstance(cmd_template, str) and '{workdir}' in cmd_template:
                cmd = cmd_template.format(workdir=workdir)
            else:
                cmd = cmd_template

            log_f = self._open_log(workdir)
            timed_out = False
            returncode = None
            try:
                proc = subprocess.Popen(
                    cmd, cwd=workdir,
                    stdout=log_f, stderr=subprocess.STDOUT,
                )
                with self._lock:
                    self._proc = proc
                    self._log_file = log_f
                    self._timed_out = False
                    self._start_time = t0

                # Timeout timer for this job
                timer = None
                if timeout_s and timeout_s > 0:
                    timer = threading.Timer(
                        timeout_s, self._on_timeout_batch, args=(proc,))
                    timer.daemon = True
                    timer.start()
                    with self._lock:
                        self._timeout_timer = timer

                proc.wait()
                returncode = proc.returncode

                if timer:
                    timer.cancel()

                with self._lock:
                    timed_out = self._timed_out

            except Exception:
                returncode = -1
            finally:
                try:
                    log_f.close()
                except Exception:
                    pass
                with self._lock:
                    self._proc = None
                    self._log_file = None
                    self._timeout_timer = None

            elapsed = time.monotonic() - t0
            fin = datetime.now(timezone.utc).isoformat()

            # Determinar estado
            with self._lock:
                if self._cancel_requested:
                    estado = 'cancelled'
                elif timed_out:
                    estado = 'timeout'
                elif returncode == 0:
                    estado = 'ok'
                else:
                    estado = 'failed'

                self._batch_results[idx].update({
                    'estado': estado,
                    'returncode': returncode,
                    'duracion_s': round(elapsed, 3),
                    'fin': fin,
                })

                # Si fue cancelado, marcar pendientes restantes
                if self._cancel_requested:
                    for r in self._batch_results[idx + 1:]:
                        if r['estado'] == 'pending':
                            r['estado'] = 'cancelled'
                    break

        # Fin del batch — escribir resultados
        self._write_batch_results()
        with self._lock:
            self._mode = 'idle'

    def _on_timeout_batch(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._timed_out = True
        self._terminate_proc(proc)

    def _write_batch_results(self) -> None:
        with self._lock:
            results = list(self._batch_results)
            path = self._batch_results_path

        if not path:
            return

        total = len(results)
        ok = sum(1 for r in results if r['estado'] == 'ok')
        fallos = sum(1 for r in results if r['estado'] in ('failed', 'timeout'))
        canceladas = sum(1 for r in results if r['estado'] == 'cancelled')

        payload = {
            'resumen': {
                'total': total,
                'ok': ok,
                'fallos': fallos,
                'canceladas': canceladas,
            },
            'jobs': results,
        }
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    # ── status ───────────────────────────────────────────────────────

    def status(self) -> dict:
        """Devuelve un dict con el estado actual del runner."""
        with self._lock:
            mode = self._mode
            if mode == 'idle' and self._returncode is not None:
                # Just finished single — report final status once
                return {
                    'mode': 'single',
                    'running': False,
                    'returncode': self._returncode,
                    'elapsed_s': round(time.monotonic() - self._start_time, 3)
                                 if self._start_time else 0,
                    'timed_out': self._timed_out,
                    'log_tail': self._read_log_tail(self._workdir)
                                if self._workdir else '',
                }
            if mode == 'running_single':
                return {
                    'mode': 'single',
                    'running': True,
                    'returncode': None,
                    'elapsed_s': round(time.monotonic() - self._start_time, 3)
                                 if self._start_time else 0,
                    'timed_out': self._timed_out,
                    'log_tail': self._read_log_tail(self._workdir)
                                if self._workdir else '',
                }
            if mode == 'running_batch' or (
                    mode == 'idle' and self._batch_results):
                running = mode == 'running_batch'
                # log_tail del job en curso (o el último)
                cur_wd = None
                cur_idx = self._batch_current_index
                if 0 <= cur_idx < len(self._batch_jobs):
                    cur_wd = self._batch_jobs[cur_idx]['workdir']
                return {
                    'mode': 'batch',
                    'running': running,
                    'current_index': cur_idx,
                    'jobs': [dict(r) for r in self._batch_results],
                    'log_tail': self._read_log_tail(cur_wd)
                                if cur_wd else '',
                }
            # Pure idle
            return {'mode': 'idle', 'running': False}

    # ── cancel ───────────────────────────────────────────────────────

    def cancel(self) -> None:
        """Cancela la ejecución en curso (single o batch)."""
        with self._lock:
            if self._mode == 'idle':
                return
            self._cancel_requested = True
            proc = self._proc
            if self._timeout_timer:
                self._timeout_timer.cancel()
                self._timeout_timer = None
        # Terminate fuera del lock
        if proc:
            self._terminate_proc(proc)


# ── Instancia singleton del módulo ───────────────────────────────────────

_runner = _Runner()

start = _runner.start
start_batch = _runner.start_batch
status = _runner.status
cancel = _runner.cancel
