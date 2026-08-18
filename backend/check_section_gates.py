#!/usr/bin/env python3
"""Fail-closed ingest gates: passage-sections / index hops / spine evidence.

Usage (from repo root):
  backend\\venv\\Scripts\\python.exe backend\\check_section_gates.py
  backend\\venv\\Scripts\\python.exe backend\\check_section_gates.py --verbose
  backend\\venv\\Scripts\\python.exe backend\\check_section_gates.py --json
  backend\\venv\\Scripts\\python.exe backend\\check_section_gates.py --phase 2

Requires Neo4j credentials in backend/.env.

This is ingest acceptance, not ADA chat smokes. Table coverage remains
``check_coverage.py``.
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

from src.section_gates import format_report_text, run_section_gates

load_dotenv(_BACKEND / ".env")
load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Contract-driven section / index / spine ingest gates"
    )
    parser.add_argument("--game", default="mork-borg")
    parser.add_argument("--document", default="mork-borg.pdf")
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "morkborg"))
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"))
    parser.add_argument("--user", default=os.getenv("NEO4J_USERNAME", "neo4j"))
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD"))
    parser.add_argument(
        "--phase",
        type=int,
        default=2,
        help="Max passage-sections.json phase (inclusive). Default 2.",
    )
    parser.add_argument(
        "--column",
        default="RULES",
        help="Section column to gate (RULES, THE_WORLD, or all). Default RULES.",
    )
    parser.add_argument("--verbose", action="store_true", help="List every check")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON output")
    args = parser.parse_args()

    if not args.password:
        print("NEO4J_PASSWORD not set (env or --password)", file=sys.stderr)
        return 2

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    with driver.session(database=args.database) as session:
        report = run_section_gates(
            session,
            game=args.game,
            document=args.document,
            phase=args.phase,
            column=args.column,
        )
    driver.close()

    if args.as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report_text(report, verbose=args.verbose))

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
