#!/usr/bin/env python3
"""CLI: materialize altitude-D If operational rules (Briefings 17–19 / D1–D3).

Usage (from repo root):
  backend\\venv\\Scripts\\python.exe backend\\materialize_operational_rules.py
  backend\\venv\\Scripts\\python.exe backend\\materialize_operational_rules.py --ensure-sections
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from src.section_chunking import materialize_passage_sections
from src.operational_rule_materialization import (
    ensure_document,
    load_operational_rules,
    materialize_operational_rules,
)

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize altitude-D If operational rules")
    parser.add_argument("--document", default="mork-borg.pdf")
    parser.add_argument("--game", default="mork-borg")
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "morkborg"))
    parser.add_argument(
        "--ensure-sections",
        action="store_true",
        help="MERGE Document + materialize passage sections phase 2 before operational rules",
    )
    parser.add_argument("--section-phase", type=int, default=2)
    args = parser.parse_args()

    load_operational_rules.cache_clear()

    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=args.database,
    )

    out: dict = {}
    if args.ensure_sections:
        ensure_document(graph, args.document)
        out["sections"] = materialize_passage_sections(
            graph,
            args.document,
            game=args.game,
            phase=args.section_phase,
        )

    out["operational_rules"] = materialize_operational_rules(
        graph, args.document, game=args.game
    )
    print(json.dumps(out, indent=2))
    rules = out["operational_rules"]
    ok = (
        rules.get("operational_rules_created", 0) >= rules.get("operational_rules_expected", 1)
        and rules.get("evidence_links", 0) >= rules.get("operational_rules_expected", 1)
        and not any("D0.4" in w for w in rules.get("warnings") or [])
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
