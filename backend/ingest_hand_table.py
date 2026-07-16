#!/usr/bin/env python3
"""Ingest a hand-authored table JSON file (no HTTP/curl).

Usage (from backend/):
  python ingest_hand_table.py games/mork-borg/hand-authored-overrides/corpse-plunder-d66.json

Requires Neo4j credentials in backend/.env and an existing Document node
(typically from a prior mork-borg.pdf ingest).
"""
import argparse
import os
import sys

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

from src.hand_authored_tables import ingest_hand_authored_file

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Ingest hand-authored lookup table JSON")
    parser.add_argument(
        "json_path",
        help="Path to table JSON (e.g. games/mork-borg/hand-authored-overrides/corpse-plunder-d66.json)",
    )
    parser.add_argument(
        "--document",
        default="mork-borg.pdf",
        help="Document fileName to attach chunk to (default: mork-borg.pdf)",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("NEO4J_DATABASE", "morkborg"),
        help="Neo4j database name",
    )
    args = parser.parse_args()

    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=args.database,
    )

    stats = ingest_hand_authored_file(graph, args.json_path, file_name=args.document)
    print("ingest_hand_table:", stats)
    if stats.get("tables_materialized", 0) < 1:
        sys.exit(1)


if __name__ == "__main__":
    main()
