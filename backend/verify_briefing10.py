#!/usr/bin/env python3
"""Briefing 10 acceptance: entity-scoped CREATURES passages."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parent / ".env")


def main() -> int:
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
    )
    with driver.session(database=os.getenv("NEO4J_DATABASE", "morkborg")) as s:
        goblin = dict(
            s.run(
                """
                MATCH (e:IndexEntry {title: 'Goblin'})-[:DENOTES]->(x)
                OPTIONAL MATCH (x)-[:DOCUMENTED_BY]->(p:RulePassage)
                OPTIONAL MATCH (e)-[:MAPS_TO_PASSAGE]->(p2:RulePassage)
                WITH x, coalesce(p, p2) AS passage
                RETURN x.name AS name,
                       passage IS NOT NULL AS has_scoped,
                       passage.page_number AS page,
                       substring(coalesce(passage.text, ''), 0, 120) AS preview,
                       coalesce(passage.text, '') CONTAINS 'Bent' AS has_bent,
                       coalesce(passage.text, '') CONTAINS 'Scum' AS has_scum,
                       coalesce(passage.text, '') CONTAINS 'Poisoned knife' AS has_poison
                """
            ).single()
        )
        others = s.run(
            """
            MATCH (e:IndexEntry {title: 'Goblin'})-[:DENOTES]->()-[:DOCUMENTED_BY]->(pg:RulePassage)
            MATCH (e2:IndexEntry)-[:DENOTES]->()-[:DOCUMENTED_BY]->(po:RulePassage)
            WHERE e2.column = 'CREATURES' AND e2.title <> 'Goblin' AND po <> pg
              AND po.source_format = 'entity-passage'
            RETURN count(DISTINCT e2) AS n
            """
        ).single()["n"]
        total = s.run(
            """
            MATCH (:IndexEntry {column: 'CREATURES'})-[:MAPS_TO_PASSAGE]->(p:RulePassage)
            WHERE p.source_format = 'entity-passage'
            RETURN count(p) AS n
            """
        ).single()["n"]
    driver.close()
    out = {
        "goblin": goblin,
        "other_creatures_with_own_passage": others,
        "creature_passages_total": total,
    }
    print(json.dumps(out, indent=2, default=str))
    ok = (
        goblin.get("has_scoped")
        and not goblin.get("has_bent")
        and not goblin.get("has_scum")
        and not goblin.get("has_poison")
        and "Goblin" in (goblin.get("preview") or "")
        and others >= 11
        and total == 12
    )
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
