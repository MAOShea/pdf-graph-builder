#!/usr/bin/env python3
"""CLI: materialize passage-section chunks from heading anchors (Briefing 6).

Usage (from repo root):
  backend\\venv\\Scripts\\python.exe backend\\materialize_passage_sections.py
  backend\\venv\\Scripts\\python.exe backend\\materialize_passage_sections.py --phase 1 --verbose
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

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize passage-section chunks")
    parser.add_argument("--document", default="mork-borg.pdf")
    parser.add_argument("--game", default="mork-borg")
    parser.add_argument("--phase", type=int, default=1)
    parser.add_argument("--strict-phase", action="store_true")
    parser.add_argument("--pdf", help="PDF path override")
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "morkborg"))
    args = parser.parse_args()

    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=args.database,
    )
    stats = materialize_passage_sections(
        graph,
        args.document,
        game=args.game,
        phase=args.phase,
        pdf_path=args.pdf,
        strict_phase=args.strict_phase,
    )
    print(json.dumps(stats, indent=2))
    return 0 if stats.get("sections_matched", 0) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
