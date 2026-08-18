#!/usr/bin/env python3
"""Briefing 22 — live-fill SUPERSEDES from D3 overrides to D1 defaults.

Does not re-emit spines. Safe to re-run (MERGE).
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

from src.spine_materialization import link_creature_dr_supersedes  # noqa: E402

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="Briefing 22 SUPERSEDES live fill")
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "morkborg"))
    args = parser.parse_args()

    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=args.database,
    )
    stats = link_creature_dr_supersedes(graph)
    print(json.dumps(stats, indent=2))

    # Acceptance smoke
    rows = graph.query("MATCH ()-[r:SUPERSEDES]->() RETURN count(r) AS n")
    n = int(rows[0]["n"]) if rows else 0
    goblin = graph.query(
        """
        MATCH (o:If:IngestNode)-[:FOR]->(:DefenseRoll)
        MATCH (o)-[:`IF`]->(:BoolExpression)-[:HAS_ATOM]->(:Circumstance)-[:APPLIES_TO]->(c)
        WHERE toLower(coalesce(c.name, c.title, '')) = 'goblin'
        MATCH (o)-[:SUPERSEDES]->(d:If {id: 'if:defence-default'})
        RETURN o.id AS override_id, d.id AS default_id
        """
    )
    spines = graph.query(
        """
        MATCH (i:If:IngestNode)
        WHERE i.id IN ['if:melee-hit-default', 'if:defence-default']
           OR i.id STARTS WITH 'if:d3-'
        RETURN count(i) AS spines
        """
    )
    smoke = {
        "S22-P0": n,
        "S22-P1_rows": len(goblin or []),
        "S22-P3": int(spines[0]["spines"]) if spines else 0,
    }
    print(json.dumps({"acceptance_smoke": smoke}, indent=2))
    ok = n >= 3 and len(goblin or []) >= 1 and smoke["S22-P3"] >= 5
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
