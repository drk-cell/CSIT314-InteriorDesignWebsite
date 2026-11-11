"""Build the exact dataset the demonstration video was recorded on.

The stores live in process memory, so the data cannot be cloned as a database
file. Two committed scripts rebuild it: ``seed_demo.py`` for the three named
designers and the customer, ``seed_bulk.py`` for the 20 further designers, 100
customers, 100 projects, 100 requests and 100 quotes. This script runs both in
the right order against a running backend.

Usage, with the backend already started:

    APP_ADMIN_EMAIL=admin@example.com APP_ADMIN_PASSWORD=passw0rd123 \
        backend/.venv/Scripts/python.exe backend/scripts/seed_all.py

Expect about 15 seconds and the final line:

    this month: 125 accounts, 108 projects, 100 requests, 100 quotes
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
BASE = os.environ.get("DEMO_BASE", "http://127.0.0.1:8000/api")


def run(name: str) -> int:
    """Run one seed with the same environment and stream its output."""
    print(f"--- {name}")
    return subprocess.call(
        [sys.executable, str(SCRIPTS / name)],
        env={**os.environ, "DEMO_BASE": BASE},
    )


def main() -> int:
    if not os.environ.get("APP_ADMIN_EMAIL"):
        print("Set APP_ADMIN_EMAIL and APP_ADMIN_PASSWORD first.")
        return 1
    print(f"backend: {BASE}")
    for name in ("seed_demo.py", "seed_bulk.py"):
        code = run(name)
        if code != 0:
            print(f"{name} failed with exit code {code}")
            return code
    print("\nDone. The catalogue now matches the recorded demonstration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
