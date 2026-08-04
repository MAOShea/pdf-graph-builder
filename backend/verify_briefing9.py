#!/usr/bin/env python3
"""Briefing 9 acceptance Cypher against morkborg."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

_BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND))
load_dotenv()


def main() -> int:
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
    )
    out: dict = {}
    with driver.session(database=os.getenv("NEO4J_DATABASE", "morkborg")) as s:
        out["multi_seed"] = [
            dict(r)
            for r in s.run(
                """
                MATCH (e:IndexEntry)-[:DENOTES]->(x)-[:INSTANCE_OF]->(seed:SeedNode)
                WHERE e.entry_kind IN ['place','supporting_character','faction','world_lore','creature']
                WITH x, e.entry_kind AS kind, count(seed) AS n
                WHERE n <> 1
                RETURN x.name AS name, kind, n ORDER BY n DESC
                """
            )
        ]
        out["galgenbeck"] = [
            dict(r)
            for r in s.run(
                """
                MATCH (e:IndexEntry {title:'Galgenbeck'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(seed:SeedNode)
                RETURN x.name AS name, labels(seed) AS labels
                """
            )
        ]
        out["places"] = s.run(
            """
            MATCH (e:IndexEntry)-[:DENOTES]->(x)-[:INSTANCE_OF]->(seed:SeedNode)
            WHERE e.entry_kind = 'place' AND seed:Place
            RETURN count(DISTINCT x) AS n
            """
        ).single()["n"]
        out["creatures"] = s.run(
            """
            MATCH (e:IndexEntry)-[:DENOTES]->(x)-[:INSTANCE_OF]->(seed:SeedNode)
            WHERE e.entry_kind = 'creature' AND seed:Creature
            RETURN count(DISTINCT x) AS n
            """
        ).single()["n"]
        out["place_cross"] = s.run(
            """
            MATCH (e:IndexEntry {entry_kind:'place'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(seed:SeedNode)
            WHERE NOT seed:Place
            RETURN count(*) AS n
            """
        ).single()["n"]
        out["creature_cross"] = s.run(
            """
            MATCH (e:IndexEntry {entry_kind:'creature'})-[:DENOTES]->(x)-[:INSTANCE_OF]->(seed:SeedNode)
            WHERE NOT seed:Creature
            RETURN count(*) AS n
            """
        ).single()["n"]
        out["instance_of_total"] = s.run(
            """
            MATCH (e:IndexEntry)-[:DENOTES]->(x)-[:INSTANCE_OF]->(:SeedNode)
            WHERE e.entry_kind IN ['place','supporting_character','faction','world_lore','creature']
            RETURN count(*) AS n
            """
        ).single()["n"]
    driver.close()
    print(json.dumps(out, indent=2, default=str))
    ok = (
        len(out["multi_seed"]) == 0
        and len(out["galgenbeck"]) == 1
        and "Place" in (out["galgenbeck"][0].get("labels") or [])
        and out["places"] == 13
        and out["creatures"] == 12
        and out["place_cross"] == 0
        and out["creature_cross"] == 0
        and out["instance_of_total"] == 40
    )
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
