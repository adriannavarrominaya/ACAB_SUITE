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
                                     — cola secuencial de jobs (pipelines)
status()                             — dict con el estado actual
cancel()                             — cancelar la ejecución en curso

Jobs de start_batch (runner v3, RUNBOOK_barrido_espectral.md D7)
------------------------------------------------------------------
Cada job es ``{'workdir': ..., 'steps': [...]}``. Si no lleva ``steps``, se
normaliza a un único paso ``run`` con *cmd_template* (compatibilidad total
con los barridos tipo 1-3, que siguen siendo jobs de un solo paso). Tipos
de paso soportados:

- ``{'type': 'run', 'cmd': ..., 'cwd': ...}`` — ejecuta *cmd* con cwd dado;
  falla el job (y detiene el pipeline) si el proceso termina con código
  distinto de 0 o si excede el timeout. Admite además, opcionalmente,
  ``'stdin'`` (fichero del que leer stdin) y ``'stdout_file'`` (fichero
  donde escribir stdout en vez de run.log) — necesario para ejecutables
  que rompen la convención de "sin argumentos, todo por cwd", como
  ``chains.exe < input_chain.txt > output_chain.txt`` (F9 del BACKLOG, ver
  acab_suite/README.md "Invocación de los códigos"). Con ``stdout_file``
  presente, run.log sigue recibiendo stderr (nunca se pierde el
  diagnóstico si el proceso falla).
- ``{'type': 'copy', 'src': ..., 'dst': ...}`` — copia un fichero; falla el
  job si *src* no existe o la copia da error de E/S.
- ``{'type': 'check_flux', 'path': ...}`` — parsea un FLUX.inf (REAL TOTAL
  FLUX, AVERAGE ENERGY, eco ILIB/IESF/NGROUP). Nunca falla el job: un
  parseo fallido queda como aviso (``estado: 'warning'``) en el resultado.

``cmd``/``cwd``/``src``/``dst``/``path``/``stdin``/``stdout_file`` admiten el
marcador ``{workdir}``, que se resuelve con el workdir del job (top-level de
la simulación).
"""

from __future__ import annotations

import json
import os
import re
import shutil
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


# ── FLUX.inf (paso 'check_flux', D3) ──────────────────────────────────────

_FLUX_ILIB_IESF_RE = re.compile(
    r'ILIB\s*,\s*IESF\s*=\s*(-?\d+)\s+(-?\d+)', re.IGNORECASE)
_FLUX_NGROUP_RE = re.compile(
    r'ngroup\s*,\s*ff\s*=\s*(-?\d+)\s+(-?\d+)', re.IGNORECASE)
_FLUX_TOTAL_HEADER_RE = re.compile(
    r'REAL TOTAL FLUX AND AVERAGE ENERGY', re.IGNORECASE)


def _parse_flux_inf(path: str | Path) -> dict:
    """Parsea REAL TOTAL FLUX, AVERAGE ENERGY y el eco ILIB/IESF/NGROUP.

    Lanza ``ValueError``/``OSError`` si el fichero no existe o no se
    encuentran los valores esperados; el llamador (paso 'check_flux') lo
    trata como aviso, nunca como fallo del job (D3).
    """
    text = Path(path).read_text(encoding='utf-8', errors='replace')
    lines = text.splitlines()

    data: dict[str, Any] = {}

    m = _FLUX_ILIB_IESF_RE.search(text)
    if m:
        data['ilib'] = int(m.group(1))
        data['iesf'] = int(m.group(2))

    m = _FLUX_NGROUP_RE.search(text)
    if m:
        data['ngroup'] = int(m.group(1))

    for i, line in enumerate(lines):
        if _FLUX_TOTAL_HEADER_RE.search(line):
            vals = []
            for j in range(i + 1, min(i + 4, len(lines))):
                s = lines[j].strip()
                if s:
                    vals.append(s)
                if len(vals) >= 2:
                    break
            if len(vals) >= 2:
                data['real_total_flux'] = float(vals[0])
                data['average_energy_mev'] = float(vals[1])
            break

    if 'real_total_flux' not in data or 'average_energy_mev' not in data:
        raise ValueError(
            f'No se pudo localizar REAL TOTAL FLUX / AVERAGE ENERGY en {path}')

    return data


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
        # cwd REAL del paso 'run' en curso (F9c): un job puede tener pasos
        # en carpetas distintas del workdir del job (p. ej. el pipeline de
        # cadenas del INP configurator: el job vive en iso_<isótopo>/ pero
        # su paso CHAINS corre en chains_<isótopo>/) -- sin esto, status()
        # solo podía enseñar el run.log del workdir de nivel job, nunca el
        # de la carpeta donde falló de verdad el paso en curso.
        self._current_step_cwd: str | None = None

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
        """Lanza una cola secuencial de jobs (pipelines de pasos, D7).

        Parameters
        ----------
        jobs : list[dict]
            Cada elemento: ``{'workdir': '<ruta>'}``, opcionalmente con
            ``'steps'`` (lista de pasos — ver docstring del módulo). Sin
            ``'steps'`` se normaliza a un único paso 'run' con *cmd_template*
            (compatibilidad total con los barridos tipo 1-3).
        cmd_template : list[str] | str
            Comando a ejecutar para jobs sin 'steps'. Si es una cadena que
            contiene ``{workdir}``, se formatea con el workdir de cada job.
            Si es lista, se usa tal cual con cwd=workdir.
        timeout_s_per_sim : float
            Timeout individual por paso 'run'.
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
                 'inicio': None, 'fin': None,
                 'step_index': None, 'step_type': None, 'steps': None}
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

    @staticmethod
    def _resolve_job_steps(job: dict, cmd_template: list[str] | str,
                           workdir: str) -> list[dict]:
        """Pasos del job: los propios si los lleva, si no un 'run' legacy."""
        steps = job.get('steps')
        if steps:
            return steps
        if isinstance(cmd_template, str) and '{workdir}' in cmd_template:
            cmd = cmd_template.format(workdir=workdir)
        else:
            cmd = cmd_template
        return [{'type': 'run', 'cmd': cmd, 'cwd': workdir}]

    @staticmethod
    def _resolve_marker(value: Any, workdir: str) -> Any:
        """Sustituye ``{workdir}`` en *value* si es una cadena que lo lleva."""
        if isinstance(value, str) and '{workdir}' in value:
            return value.format(workdir=workdir)
        return value

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
            steps = self._resolve_job_steps(job, cmd_template, workdir)
            inicio = datetime.now(timezone.utc).isoformat()
            t0 = time.monotonic()

            with self._lock:
                self._batch_results[idx]['inicio'] = inicio
                self._workdir = workdir
                self._start_time = t0

            step_results: list[dict] = []
            failing_step_index: int | None = None
            job_failed = False
            job_timed_out = False

            for step_idx, step in enumerate(steps):
                with self._lock:
                    if self._cancel_requested:
                        break
                    self._batch_results[idx]['step_index'] = step_idx
                    self._batch_results[idx]['step_type'] = step.get(
                        'type', 'run')

                step_type = step.get('type', 'run')
                if step_type == 'run':
                    result, timed_out, _rc = self._exec_run_step(
                        step, workdir, timeout_s)
                    step_results.append(result)
                    if timed_out:
                        job_timed_out = True
                        failing_step_index = step_idx
                        break
                    if result['estado'] == 'failed':
                        job_failed = True
                        failing_step_index = step_idx
                        break
                elif step_type == 'copy':
                    result = self._exec_copy_step(step, workdir)
                    step_results.append(result)
                    if result['estado'] == 'failed':
                        job_failed = True
                        failing_step_index = step_idx
                        break
                elif step_type == 'check_flux':
                    # Nunca falla el job (D3): parseo fallido → warning.
                    result = self._exec_check_flux_step(step, workdir)
                    step_results.append(result)
                else:
                    step_results.append({
                        'type': step_type, 'estado': 'failed',
                        'error': f'tipo de paso desconocido: {step_type}',
                    })
                    job_failed = True
                    failing_step_index = step_idx
                    break

            elapsed = time.monotonic() - t0
            fin = datetime.now(timezone.utc).isoformat()

            last_returncode = None
            for r in reversed(step_results):
                if r.get('type') == 'run':
                    last_returncode = r.get('returncode')
                    break

            # Determinar estado
            with self._lock:
                if self._cancel_requested:
                    estado = 'cancelled'
                elif job_timed_out:
                    estado = 'timeout'
                elif job_failed:
                    estado = 'failed'
                else:
                    estado = 'ok'

                self._batch_results[idx].update({
                    'estado': estado,
                    'returncode': last_returncode,
                    'duracion_s': round(elapsed, 3),
                    'fin': fin,
                    'steps': step_results,
                    'step_index': failing_step_index if failing_step_index
                                  is not None
                                  else (len(step_results) - 1
                                        if step_results else None),
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

    def _exec_run_step(self, step: dict, workdir: str,
                       timeout_s: float) -> tuple[dict, bool, int | None]:
        """Ejecuta un paso 'run'. Devuelve (resultado, timed_out, returncode).

        Con 'stdin'/'stdout_file' presentes en *step* (F9 del BACKLOG,
        chains.exe), el stdout del proceso va al fichero indicado en vez de
        a run.log; stderr sigue yendo a run.log por separado (nunca se
        pierde el diagnóstico de un fallo). Sin esas claves, comportamiento
        idéntico al de siempre (stdout+stderr fusionados en run.log).
        """
        cmd = self._resolve_marker(step.get('cmd'), workdir)
        cwd = self._resolve_marker(step.get('cwd'), workdir) or workdir
        stdin_path = self._resolve_marker(step.get('stdin'), workdir)
        stdout_path = self._resolve_marker(step.get('stdout_file'), workdir)
        result: dict[str, Any] = {'type': 'run', 'cmd': cmd, 'cwd': cwd}

        log_f = self._open_log(cwd)
        stdin_f = None
        stdout_f = None
        timed_out = False
        returncode = None
        with self._lock:
            self._current_step_cwd = cwd
        try:
            if stdin_path:
                stdin_f = open(stdin_path, 'rb')
            if stdout_path:
                stdout_f = open(stdout_path, 'wb')
            proc = subprocess.Popen(
                cmd, cwd=cwd,
                stdin=stdin_f,
                stdout=stdout_f if stdout_f else log_f,
                stderr=log_f if stdout_f else subprocess.STDOUT,
            )
            with self._lock:
                self._proc = proc
                self._log_file = log_f
                self._timed_out = False

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

        except Exception as exc:
            returncode = -1
            result['error'] = str(exc)
        finally:
            try:
                log_f.close()
            except Exception:
                pass
            if stdin_f:
                try:
                    stdin_f.close()
                except Exception:
                    pass
            if stdout_f:
                try:
                    stdout_f.close()
                except Exception:
                    pass
            with self._lock:
                self._proc = None
                self._log_file = None
                self._timeout_timer = None

        result['returncode'] = returncode
        result['timed_out'] = timed_out
        if timed_out:
            result['estado'] = 'timeout'
        elif returncode == 0:
            result['estado'] = 'ok'
        else:
            result['estado'] = 'failed'
        return result, timed_out, returncode

    def _exec_copy_step(self, step: dict, workdir: str) -> dict:
        """Ejecuta un paso 'copy'. Falla si *src* no existe o hay error de E/S."""
        src = self._resolve_marker(step.get('src'), workdir)
        dst = self._resolve_marker(step.get('dst'), workdir)
        result: dict[str, Any] = {'type': 'copy', 'src': src, 'dst': dst}
        try:
            src_path = Path(src)
            if not src_path.exists():
                result['estado'] = 'failed'
                result['error'] = f'origen no encontrado: {src}'
                return result
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst)
            result['estado'] = 'ok'
        except OSError as exc:
            result['estado'] = 'failed'
            result['error'] = str(exc)
        return result

    def _exec_check_flux_step(self, step: dict, workdir: str) -> dict:
        """Ejecuta un paso 'check_flux'. Nunca falla el job (D3)."""
        path = self._resolve_marker(step.get('path'), workdir)
        result: dict[str, Any] = {'type': 'check_flux', 'path': path}
        try:
            result['data'] = _parse_flux_inf(path)
            result['estado'] = 'ok'
        except (OSError, ValueError) as exc:
            result['estado'] = 'warning'
            result['warning'] = str(exc)
        return result

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
                # log_tail del PASO en curso (o el último ejecutado): usa el
                # cwd real del paso (F9c) si se conoce -- puede diferir del
                # workdir de nivel job (ver _current_step_cwd) -- y si no,
                # cae al workdir del job como antes (jobs de un solo paso).
                cur_wd = self._current_step_cwd
                cur_idx = self._batch_current_index
                if not cur_wd and 0 <= cur_idx < len(self._batch_jobs):
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

# Lectura del run.log de una carpeta arbitraria (F9c): permite a la UI
# consultar el run.log de la carpeta EXACTA donde falló un sub-paso (p. ej.
# chains_<isótopo>/, distinta del workdir de nivel job), no solo el del
# job/paso en curso que ya expone status().
read_log_tail = _Runner._read_log_tail
