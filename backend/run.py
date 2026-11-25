"""One-command local development launcher. Production still uses separate entrypoints."""

import argparse
import os
import shutil
import signal
import socket

# Commands are fixed argv lists, never shell strings or user-supplied executable text.
import subprocess  # nosec B404
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

BACKEND = Path(__file__).resolve().parent
FRONTEND = BACKEND.parent / "frontend"


@dataclass
class Service:
    name: str
    command: list[str]
    cwd: Path
    health: str


def environment_python(directory):
    return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def execute(command, cwd=BACKEND, **kwargs):
    # Paths and arguments originate from this launcher, not HTTP/user input.
    return subprocess.run([str(arg) for arg in command], cwd=cwd, check=True, **kwargs)  # nosec B603


def modules_available(python, modules):
    if not python.is_file():
        return False
    code = "import importlib.util,sys; sys.exit(not all(importlib.util.find_spec(m) for m in sys.argv[1:]))"
    result = subprocess.run(
        [str(python), "-c", code, *modules],  # nosec B603
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def ensure_python(directory, requirements, modules, install):
    python = environment_python(directory)
    if modules_available(python, modules):
        return python
    if not install:
        raise RuntimeError(
            f"Missing dependencies in {directory.name}. Run again without --no-install."
        )
    if not python.exists():
        execute([sys.executable, "-m", "venv", directory])
    print(
        f"Installing {directory.name} dependencies (first run may take several minutes)...",
        flush=True,
    )
    execute([python, "-m", "pip", "install", "-r", requirements])
    return python


def service_plan(backend, rest_python, worker_python, node):
    frontend = backend.parent / "frontend"
    return [
        Service(
            "REST API",
            [
                str(rest_python),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            backend,
            "http://127.0.0.1:8000/ready",
        ),
        Service(
            "Whisper worker",
            [
                str(worker_python),
                "-m",
                "uvicorn",
                "transcription_worker.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8001",
                "--ws-max-size",
                "32768",
                "--ws-max-queue",
                "8",
                "--limit-concurrency",
                "32",
            ],
            backend,
            "http://127.0.0.1:8001/health",
        ),
        Service(
            "Frontend",
            [
                node,
                str(frontend / "node_modules/vite/bin/vite.js"),
                "--host",
                "127.0.0.1",
                "--port",
                "5173",
                "--strictPort",
            ],
            frontend,
            "http://127.0.0.1:5173",
        ),
    ]


def spawn_service(service, env):
    options = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    return subprocess.Popen(service.command, cwd=service.cwd, env=env, **options)  # nosec B603


def stop_process(process):
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            taskkill = Path(os.environ["SystemRoot"]) / "System32/taskkill.exe"
            subprocess.run(
                [str(taskkill), "/PID", str(process.pid), "/T", "/F"],  # nosec B603
                capture_output=True,
                timeout=10,
                check=False,
            )
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def healthy(url):
    try:
        # Only hardcoded loopback health URLs from service_plan are used here.
        with urlopen(url, timeout=1) as response:  # nosec B310
            return response.status == 200
    except (URLError, TimeoutError, OSError):
        return False


def supervise(services, env, startup_timeout=900, spawn=spawn_service, stop=stop_process):
    children = []
    ready = set()
    deadline = time.monotonic() + startup_timeout
    announced = False
    try:
        for service in services:
            print(f"Starting {service.name}...", flush=True)
            children.append((service, spawn(service, env)))
        while True:
            for service, process in children:
                code = process.poll()
                if code is not None:
                    print(
                        f"{service.name} exited ({code}); stopping the other services.", flush=True
                    )
                    return 1
                if service.name not in ready and healthy(service.health):
                    ready.add(service.name)
                    print(f"{service.name} is ready.", flush=True)
            if len(ready) == len(services):
                if not announced:
                    print(
                        "\nAll services ready. Open http://localhost:5173\nAPI docs: http://localhost:8000/docs\nPress Ctrl+C to stop everything.\n",
                        flush=True,
                    )
                    announced = True
            elif time.monotonic() >= deadline:
                print(
                    "Startup timed out. Check the service logs above (Whisper downloads its model on first startup).",
                    flush=True,
                )
                return 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping local application...", flush=True)
        return 0
    finally:
        for _, process in reversed(children):
            stop(process)


def prerequisites():
    errors = []
    for name in ("node", "npm.cmd" if os.name == "nt" else "npm", "ffmpeg"):
        if not shutil.which(name):
            errors.append(f"{name} is not on PATH. Install it and reopen the terminal.")
    for port in (8000, 8001, 5173):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                errors.append(
                    f"Port {port} is occupied. Stop the existing service before starting this launcher."
                )
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report prerequisites without installing, initializing or starting anything",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Fail instead of installing missing project dependencies",
    )
    parser.add_argument(
        "--startup-timeout",
        type=int,
        default=900,
        help="Seconds allowed for initial model loading (default: 900)",
    )
    args = parser.parse_args(argv)
    if args.startup_timeout < 1:
        parser.error("--startup-timeout must be positive")
    errors = prerequisites()
    if args.check:
        for folder, modules in [
            (".venv", ["fastapi", "sqlalchemy", "asyncpg", "pydantic_settings"]),
            (".venv-worker", ["whisper", "torch", "numpy", "uvicorn"]),
        ]:
            if not modules_available(environment_python(BACKEND / folder), modules):
                errors.append(f"{folder} needs dependencies; normal startup installs them.")
        if not (FRONTEND / "node_modules/vite/bin/vite.js").exists():
            errors.append("Frontend dependencies are missing; normal startup installs them.")
        print("\n".join(errors) if errors else "Prerequisite checks passed.")
        print(
            "Database credentials/connectivity are checked during normal startup. PostgreSQL must already be running."
        )
        return int(bool(errors))
    if errors:
        print("\n".join(errors))
        print("See backend/README.md for one-time prerequisites. No services were started.")
        return 1
    try:
        for directory in (BACKEND, FRONTEND):
            if not (directory / ".env").exists():
                shutil.copyfile(directory / ".env.example", directory / ".env")
        rest_python = ensure_python(
            BACKEND / ".venv",
            BACKEND / "requirements.txt",
            [
                "fastapi",
                "uvicorn",
                "sqlalchemy",
                "asyncpg",
                "pydantic_settings",
                "multipart",
                "httpx",
            ],
            not args.no_install,
        )
        # Validate development configuration before installing a large model runtime or touching DB.
        execute([rest_python, "-m", "scripts.configure_database"])
        execute([rest_python, "-m", "scripts.prepare_local", "--check-config"])
        worker_python = ensure_python(
            BACKEND / ".venv-worker",
            BACKEND / "transcription_worker/requirements.txt",
            ["whisper", "torch", "numpy", "fastapi", "uvicorn", "asyncpg", "pydantic_settings"],
            not args.no_install,
        )
        if not (FRONTEND / "node_modules/vite/bin/vite.js").exists():
            if args.no_install:
                raise RuntimeError("Frontend dependencies missing. Run npm ci in frontend.")
            execute([shutil.which("npm.cmd" if os.name == "nt" else "npm"), "ci"], cwd=FRONTEND)
        execute([rest_python, "-m", "scripts.prepare_local"])
        env = os.environ.copy()
        env.update(
            {
                "PYTHONUNBUFFERED": "1",
                "TRANSCRIPTION_SERVICE_URL": "http://localhost:8001",
                "TRANSCRIPTION_WEBSOCKET_URL": "ws://localhost:8001/ws/transcribe",
                "CORS_ORIGINS": '["http://localhost:5173","http://127.0.0.1:5173"]',
                "VITE_API_BASE_URL": "http://localhost:8000/api/v1",
                "VITE_WS_URL": "ws://localhost:8001/ws/transcribe",
            }
        )
        return supervise(
            service_plan(BACKEND, rest_python, worker_python, shutil.which("node")),
            env,
            args.startup_timeout,
        )
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        return 130
    except subprocess.CalledProcessError:
        print(
            "Local startup stopped. Resolve the setup error shown above, then run python run.py again.",
            file=sys.stderr,
        )
        return 1
    except (OSError, RuntimeError) as exc:
        print(f"Local startup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
