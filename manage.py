#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def _require_project_virtualenv():
    """Prevent Windows development commands from using global Python."""
    project_python = Path(__file__).resolve().parent / "venv" / "Scripts" / "python.exe"
    if not project_python.exists() or os.environ.get("ALLOW_NON_PROJECT_PYTHON") == "1":
        return
    try:
        using_project_python = Path(sys.executable).resolve() == project_python.resolve()
    except OSError:
        using_project_python = False
    if not using_project_python:
        command = " ".join(sys.argv[1:]) or "<command>"
        raise SystemExit(
            "\nIncorrect Python environment. This project must use its virtual environment.\n\n"
            f"Run instead:\n  .\\venv\\Scripts\\python.exe manage.py {command}\n\n"
            "Or start the local website with:\n  .\\run-dev.ps1\n"
        )


def main():
    """Run administrative tasks."""
    _require_project_virtualenv()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
