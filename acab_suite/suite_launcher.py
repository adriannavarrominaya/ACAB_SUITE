"""suite_launcher.py — Arranca las tres apps de la suite ACAB y abre el navegador.

Uso:
    python suite_launcher.py              # usa/crea suite_config.json en esta carpeta
    python suite_launcher.py --config otra_config.json

Comportamiento:
  - Lee suite_config.json (lo crea con la plantilla por defecto si no existe).
  - Para cada app: si su /api/ping ya responde, avisa "ya en ejecución" y no la
    lanza; si no, la lanza como subproceso con `--port <puerto> --no-browser`,
    redirigiendo stdout+stderr a logs/<name>.log.
  - Health-check: poll a /api/ping de cada app hasta 15 s; informa ✓/✗.
  - Abre el navegador en `open_browser` cuando el poll termina (si alguna responde).
  - Ctrl+C: termina los subprocesos lanzados (terminate; kill a los 5 s).

Selección del intérprete Python de cada app (nada hardcodeado; orden de prioridad):
  1. Clave "python" del app en suite_config.json (si está definida).
  2. Clave "python" global de suite_config.json (si está definida) — p. ej. un
     venv compartido como C:/venv/acab-venv/Scripts/python.exe.
  3. venv local del repo: <app>/venv/Scripts/python.exe (Windows) o
     <app>/venv/bin/python (Linux/macOS), si existe.
  4. El mismo Python con el que se ejecuta este launcher (sys.executable).
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

SUITE_DIR = Path(__file__).resolve().parent

DEFAULT_CONFIG = {
    "apps": [
        {"name": "inp-configurator", "path": "../ACAB_inp_file_configurator", "port": 5000},
        {"name": "fort-analyzer", "path": "../ACAB_fort_file_analyzer", "port": 5001},
        {"name": "collaps", "path": "../COLLAPS_inp_file_configurator", "port": 5002},
    ],
    "open_browser": "http://127.0.0.1:5000",
    "python": None,
}

HEALTH_TIMEOUT_S = 15
KILL_GRACE_S = 5


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        config_path.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"[i] Creado {config_path.name} con la configuración por defecto.")
    with config_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def port_in_use(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def ping(port: int, timeout_s: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/ping", timeout=timeout_s
        ) as resp:
            return resp.status == 200
    except Exception:
        return False


def resolve_python(app_cfg: dict, global_python: str | None, app_dir: Path) -> Path:
    """Intérprete para lanzar app.py. Ver orden de prioridad en el docstring."""
    for configured in (app_cfg.get("python"), global_python):
        if configured:
            py = Path(configured).expanduser()
            if not py.exists():
                raise SystemExit(
                    f"[✗] El Python configurado para '{app_cfg['name']}' no existe: {py}\n"
                    f"    Corrige la clave \"python\" en suite_config.json o crea el venv\n"
                    f"    compartido con acab_suite/setup.ps1 (Windows) o setup.sh dentro\n"
                    f"    de cada repo (Linux/macOS)."
                )
            return py
    for candidate in (app_dir / "venv/Scripts/python.exe", app_dir / "venv/bin/python"):
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def launch(app_cfg: dict, global_python: str | None, logs_dir: Path):
    """Lanza una app como subproceso. Devuelve (Popen, fichero_log)."""
    app_dir = (SUITE_DIR / app_cfg["path"]).resolve()
    app_py = app_dir / "app.py"
    if not app_py.exists():
        raise SystemExit(f"[✗] No se encuentra {app_py} — revisa \"path\" en suite_config.json.")

    python = resolve_python(app_cfg, global_python, app_dir)
    log_path = logs_dir / f"{app_cfg['name']}.log"
    log_fh = log_path.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        # -u: sin buffer, para que logs/<name>.log se escriba en tiempo real.
        [str(python), "-u", "app.py", "--port", str(app_cfg["port"]), "--no-browser"],
        cwd=str(app_dir),
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    print(f"[i] {app_cfg['name']}: lanzada (PID {proc.pid}, python: {python}, log: {log_path.name})")
    return proc, log_fh


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

    cli = argparse.ArgumentParser(description="Launcher de la suite ACAB")
    cli.add_argument("--config", type=Path, default=SUITE_DIR / "suite_config.json",
                     help="Ruta del fichero de configuración (por defecto: suite_config.json)")
    args = cli.parse_args()

    config = load_config(args.config)
    apps = config["apps"]
    global_python = config.get("python")

    logs_dir = SUITE_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)

    launched: list[tuple[dict, subprocess.Popen, object]] = []
    for app_cfg in apps:
        if ping(app_cfg["port"]):
            print(f"[i] {app_cfg['name']}: ya en ejecución en el puerto {app_cfg['port']} — no se lanza.")
            continue
        if port_in_use(app_cfg["port"]):
            print(f"[!] {app_cfg['name']}: el puerto {app_cfg['port']} está ocupado por un proceso "
                  f"que no responde a /api/ping (¿una versión antigua u otra aplicación?).\n"
                  f"    Ciérralo y vuelve a ejecutar el launcher. No se lanza.")
            continue
        proc, log_fh = launch(app_cfg, global_python, logs_dir)
        launched.append((app_cfg, proc, log_fh))

    # Health-check: hasta 15 s para que todas respondan.
    print(f"[i] Esperando a que las apps respondan (máx. {HEALTH_TIMEOUT_S} s)…")
    deadline = time.monotonic() + HEALTH_TIMEOUT_S
    status = {app_cfg["name"]: False for app_cfg in apps}
    while time.monotonic() < deadline and not all(status.values()):
        for app_cfg in apps:
            if not status[app_cfg["name"]]:
                status[app_cfg["name"]] = ping(app_cfg["port"])
        if not all(status.values()):
            time.sleep(0.5)

    for app_cfg in apps:
        mark = "✓" if status[app_cfg["name"]] else "✗"
        print(f"  [{mark}] {app_cfg['name']} — http://127.0.0.1:{app_cfg['port']}")

    if any(status.values()) and config.get("open_browser"):
        webbrowser.open(config["open_browser"])
    elif not any(status.values()):
        print("[✗] Ninguna app responde; revisa los logs en acab_suite/logs/.")

    if not launched:
        print("[i] No se lanzó ningún proceso nuevo; nada que vigilar. Saliendo.")
        return

    print("[i] Suite en ejecución. Ctrl+C para parar las apps lanzadas por este launcher.")
    try:
        while True:
            time.sleep(1)
            for app_cfg, proc, _ in launched:
                if proc.poll() is not None:
                    print(f"[!] {app_cfg['name']} terminó sola (código {proc.returncode}); "
                          f"revisa logs/{app_cfg['name']}.log")
            launched = [item for item in launched if item[1].poll() is None]
            if not launched:
                print("[✗] Todos los procesos lanzados han terminado. Saliendo.")
                return
    except KeyboardInterrupt:
        print("\n[i] Parando las apps lanzadas…")
        for _, proc, _ in launched:
            proc.terminate()
        deadline = time.monotonic() + KILL_GRACE_S
        for app_cfg, proc, log_fh in launched:
            remaining = max(0.1, deadline - time.monotonic())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            log_fh.close()
            print(f"  [✓] {app_cfg['name']} parada (código {proc.returncode}).")


if __name__ == "__main__":
    main()
