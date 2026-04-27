#!/usr/bin/env python3
"""
Single entry point for CPSE.

Starts Django (internal, port 8000) and Next.js (public, port 3000).
Next.js rewrites API calls to Django, so only port 3000 is exposed.
Cloudflare Tunnel should point to http://localhost:3000.

Usage:
  python app.py                   # development (manage.py runserver + next dev)
  APP_ENV=prod python app.py      # production  (gunicorn + next start)

Environment variables:
  APP_ENV            dev (default) | prod
  DJANGO_PORT        internal Django port (default 8000)
  PORT               Next.js port exposed to Cloudflare (default 3000)
  GUNICORN_WORKERS   worker count for prod (default 3)
"""
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

APP_ENV = os.environ.get("APP_ENV", "dev")
DJANGO_PORT = int(os.environ.get("DJANGO_PORT", 8000))
NEXTJS_PORT = int(os.environ.get("PORT", 3000))


def _stream(proc: subprocess.Popen, label: str) -> None:
    for line in iter(proc.stdout.readline, b""):
        sys.stdout.write(f"[{label}] {line.decode(errors='replace')}")
        sys.stdout.flush()


def _build_commands() -> tuple[list[str], list[str]]:
    if APP_ENV == "dev":
        django_cmd = ["python", "manage.py", "runserver", f"0.0.0.0:{DJANGO_PORT}"]
        nextjs_cmd = ["npm", "run", "dev"]
    else:
        workers = os.environ.get("GUNICORN_WORKERS", "3")
        django_cmd = [
            "gunicorn", "core.wsgi:application",
            "--bind", f"0.0.0.0:{DJANGO_PORT}",
            "--workers", workers,
        ]
        nextjs_cmd = ["npm", "run", "start"]

    return django_cmd, nextjs_cmd


def main() -> None:
    django_cmd, nextjs_cmd = _build_commands()

    django_env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": f"core.settings.{APP_ENV}",
    }
    nextjs_env = {
        **os.environ,
        "PORT": str(NEXTJS_PORT),
        "DJANGO_INTERNAL_URL": f"http://localhost:{DJANGO_PORT}",
    }

    print(f"[app] env={APP_ENV}  django=:{DJANGO_PORT}  nextjs=:{NEXTJS_PORT}")

    django = subprocess.Popen(
        django_cmd, cwd=BACKEND, env=django_env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    nextjs = subprocess.Popen(
        nextjs_cmd, cwd=FRONTEND, env=nextjs_env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )

    procs: dict[str, subprocess.Popen] = {"django": django, "nextjs": nextjs}

    for name, proc in procs.items():
        threading.Thread(target=_stream, args=(proc, name), daemon=True).start()

    def _shutdown(sig=None, frame=None) -> None:
        print("\n[app] shutting down...")
        for proc in procs.values():
            proc.terminate()
        for proc in procs.values():
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        for name, proc in list(procs.items()):
            if proc.poll() is not None:
                print(f"[app] {name} exited with code {proc.returncode}, shutting down")
                _shutdown()
        time.sleep(1)


if __name__ == "__main__":
    main()
