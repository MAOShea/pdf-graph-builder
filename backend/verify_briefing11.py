#!/usr/bin/env python3
"""Briefing 11 acceptance: CREATURES passages exclude bounty trails."""
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
                MATCH (e:IndexEntry {title: 'Goblin'})-[:MAPS_TO_PASSAGE]->(p:RulePassage)
                WHERE coalesce(p.source_format, '') = 'entity-passage'
                   OR p.id CONTAINS 'entity-passage'
                RETURN p.id AS id,
                       substring(coalesce(p.text, ''), 0, 200) AS preview,
                       p.text CONTAINS 'Head 7s' AS has_head,
                       p.text CONTAINS 'Captured 150s' AS has_captured,
                       p.text CONTAINS 'Dead 20s' AS has_dead,
                       (p.text CONTAINS 'Bent' OR p.text CONTAINS 'Scum') AS has_neighbor,
                       p.text CONTAINS 'Ropy skin' AS has_body,
                       toLower(p.text) CONTAINS 'curse' AS has_curse
                """
            ).single()
        )
        head_bleed = [
            dict(r)
            for r in s.run(
                """
                MATCH (e:IndexEntry {column: 'CREATURES'})-[:MAPS_TO_PASSAGE]->(p:RulePassage)
                WHERE coalesce(p.source_format, '') = 'entity-passage'
                  AND p.text =~ '(?s).*Head \\d+s.*'
                RETURN e.title AS title, substring(p.text, 0, 60) AS preview
                """
            )
        ]
    driver.close()
    out = {"goblin": goblin, "head_bounty_bleed": head_bleed}
    print(json.dumps(out, indent=2, default=str))
    ok = (
        goblin
        and not goblin.get("has_head")
        and not goblin.get("has_captured")
        and not goblin.get("has_dead")
        and not goblin.get("has_neighbor")
        and goblin.get("has_body")
        and goblin.get("has_curse")
        and len(head_bleed) == 0
    )
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
