#!/usr/bin/env python3
"""CLI: materialize manifest lookup tables from PDF on disk → Neo4j.

Usage (from repo root):
  backend\\venv\\Scripts\\python.exe backend\\ingest_tables.py
  backend\\venv\\Scripts\\python.exe backend\\ingest_tables.py --pdf mork-borg.pdf --tables WeaponTable ArmorTable
  backend\\venv\\Scripts\\python.exe backend\\ingest_tables.py --start-page 4 --end-page 5

Requires Neo4j credentials in backend/.env and a Document node for --document (default mork-borg.pdf).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

from src.graphDB_dataAccess import graphDBdataAccess
from src.table_pipeline import run_lookup_table_pipeline

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize ingest-manifest lookup tables from PDF (CLI flavour)"
    )
    parser.add_argument(
        "--pdf",
        help="Path to PDF on disk (default: resolve from --document at repo root)",
    )
    parser.add_argument(
        "--document",
        default="mork-borg.pdf",
        help="Document fileName in Neo4j (default: mork-borg.pdf)",
    )
    parser.add_argument(
        "--game",
        default="mork-borg",
        help="Game id for ingest-manifest.json",
    )
    parser.add_argument(
        "--tables",
        nargs="*",
        help="Only these manifest table names (default: all PDF-extractable)",
    )
    parser.add_argument("--start-page", type=int, default=None)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument(
        "--no-hand-authored",
        action="store_true",
        help="Skip hand-authored manifest tables",
    )
    parser.add_argument(
        "--no-bundles",
        action="store_true",
        help="Skip character-creation bundle wiring",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("NEO4J_DATABASE", "morkborg"),
    )
    args = parser.parse_args()

    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=args.database,
    )
    scaffold_map = graphDBdataAccess(graph).fetch_scaffold_node_map()

    stats = run_lookup_table_pipeline(
        graph,
        args.document,
        scaffold_map,
        pdf_path=args.pdf,
        game=args.game,
        table_names=args.tables or None,
        start_page=args.start_page,
        end_page=args.end_page,
        hand_authored=not args.no_hand_authored,
        bundles=not args.no_bundles,
    )
    print(json.dumps(stats, indent=2))

    if stats.get("pdf_tables_failed", 0) > 0 and stats.get("pdf_tables_materialized", 0) == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
