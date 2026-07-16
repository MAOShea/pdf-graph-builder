"""Deprecated — use backend/ingest_tables.py instead."""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).resolve().parent / "ingest_tables.py"
    tables = [
        "TrapsTable",
        "WeatherTable",
        "OccultTreasuresTable",
        "BasilisksDemandTable",
        "ArcaneCatastrophesTable",
        "AdventureSparkTable",
        "WanderTable",
        "DwellsHereTable",
        "ImminentDangerTable",
        "DistinctiveFeatureTable",
    ]
    cmd = [sys.executable, str(script), "--tables", *tables]
    if len(sys.argv) > 1:
        cmd.extend(["--pdf", sys.argv[1]])
    raise SystemExit(subprocess.call(cmd))
