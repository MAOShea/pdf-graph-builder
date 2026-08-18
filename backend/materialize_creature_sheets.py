#!/usr/bin/env python3
"""CLI: materialize D4 creature sheets (Briefings 20 / 23).

Usage (from repo root):
  backend\\venv\\Scripts\\python.exe backend\\materialize_creature_sheets.py
  backend\\venv\\Scripts\\python.exe backend\\materialize_creature_sheets.py --ensure-fiction
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

from src.creature_sheet_materialization import materialize_creature_sheets
from src.index_materialization import materialize_rulebook_catalog
from src.section_chunking import materialize_passage_sections
from src.spine_materialization import (
    ensure_document,
    materialize_operational_spines,
)

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize D4 creature sheets")
    parser.add_argument("--document", default="mork-borg.pdf")
    parser.add_argument("--game", default="mork-borg")
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "morkborg"))
    parser.add_argument(
        "--ensure-fiction",
        action="store_true",
        help="MERGE Document + sections + catalog/entity passages + spines before sheets",
    )
    parser.add_argument("--section-phase", type=int, default=2)
    args = parser.parse_args()

    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=args.database,
    )

    out: dict = {}
    if args.ensure_fiction:
        ensure_document(graph, args.document)
        out["sections"] = materialize_passage_sections(
            graph,
            args.document,
            game=args.game,
            phase=args.section_phase,
        )
        out["catalog"] = materialize_rulebook_catalog(
            graph,
            args.document,
            game=args.game,
            link_sections=True,
            fiction=True,
            entity_passages=True,
            section_phase=args.section_phase,
        )
        out["spines"] = materialize_operational_spines(
            graph, args.document, game=args.game
        )

    out["sheets"] = materialize_creature_sheets(
        graph, args.document, game=args.game
    )
    print(json.dumps(out, indent=2, default=str))
    sheets = out["sheets"]
    ok = (
        sheets.get("creatures_with_sheet", 0) >= 5
        and not any("D4 incomplete" in w for w in sheets.get("warnings") or [])
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
