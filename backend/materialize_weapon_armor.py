"""Deprecated — use backend/ingest_tables.py --tables WeaponTable ArmorTable."""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).resolve().parent / "ingest_tables.py"
    cmd = [
        sys.executable,
        str(script),
        "--tables",
        "WeaponTable",
        "ArmorTable",
        "--start-page",
        "23",
        "--end-page",
        "23",
    ]
    raise SystemExit(subprocess.call(cmd))
