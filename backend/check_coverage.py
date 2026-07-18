#!/usr/bin/env python3
"""Report ingest coverage: manifest contract vs Neo4j state.

Usage (from repo root):
  backend\\venv\\Scripts\\python.exe backend\\check_coverage.py
  backend\\venv\\Scripts\\python.exe backend\\check_coverage.py --verbose
  backend\\venv\\Scripts\\python.exe backend\\check_coverage.py --json
  backend\\venv\\Scripts\\python.exe backend\\check_coverage.py --phase 2

Requires Neo4j credentials in backend/.env.

Supersedes ad-hoc checks in check_gaps.py, verify_phase1.py, and verify_phase2.py
for summary reporting; those scripts remain for narrow debugging.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from src.ingest_coverage import format_report_text, run_coverage_report

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="Manifest-driven ingest coverage report")
    parser.add_argument("--game", default="mork-borg")
    parser.add_argument("--document", default="mork-borg.pdf")
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "morkborg"))
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"))
    parser.add_argument("--user", default=os.getenv("NEO4J_USERNAME", "neo4j"))
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD"))
    parser.add_argument("--phase", type=int, default=None, help="Only check tables for this phase")
    parser.add_argument("--verbose", action="store_true", help="List every manifest table")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON output")
    parser.add_argument(
        "--validate-acceptance",
        action="store_true",
        help="Compare materialized rows to manifest acceptance_rows",
    )
    parser.add_argument("--no-bundles", action="store_true", help="Skip bundle wiring checks")
    args = parser.parse_args()

    if not args.password:
        print("NEO4J_PASSWORD not set (env or --password)", file=sys.stderr)
        return 2

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    with driver.session(database=args.database) as session:
        report = run_coverage_report(
            session,
            game=args.game,
            document=args.document,
            validate_acceptance=args.validate_acceptance,
            phase=args.phase,
            include_bundles=not args.no_bundles,
        )
    driver.close()

    if args.as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report_text(report, verbose=args.verbose))

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
