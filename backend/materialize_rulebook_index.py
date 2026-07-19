#!/usr/bin/env python3
"""CLI: materialize p.75 rulebook index catalog + fiction instances (Briefings 7+8).

Usage (from repo root):
  backend\\venv\\Scripts\\python.exe backend\\materialize_rulebook_index.py
  backend\\venv\\Scripts\\python.exe backend\\materialize_rulebook_index.py --no-fiction
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

from src.index_materialization import materialize_rulebook_catalog

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize rulebook index catalog")
    parser.add_argument("--document", default="mork-borg.pdf")
    parser.add_argument("--game", default="mork-borg")
    parser.add_argument("--phase", type=int, default=None, help="Max section phase for MAPS_TO_SECTION")
    parser.add_argument("--no-sections", action="store_true", help="Skip MAPS_TO_SECTION links")
    parser.add_argument("--no-fiction", action="store_true", help="Skip fiction instance materialization")
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "morkborg"))
    args = parser.parse_args()

    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=args.database,
    )
    stats = materialize_rulebook_catalog(
        graph,
        args.document,
        game=args.game,
        link_sections=not args.no_sections,
        fiction=not args.no_fiction,
        section_phase=args.phase,
    )
    print(json.dumps(stats, indent=2))
    index_entries = stats.get("index", {}).get("entries_created", 0)
    return 0 if index_entries > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
