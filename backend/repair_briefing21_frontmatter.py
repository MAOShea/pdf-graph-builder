#!/usr/bin/env python3
"""Briefing 21 — strip front-matter Chunk→SeedNode evidence fan-out.

Safe to re-run. Does not delete If spines, entity passages, or Violence evidence.
Stamps Chunk.seed_evidence=false for deny-listed sections so scaffold-diff
guards apply without a full rematerialize.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from src.section_chunking import load_passage_sections  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("repair_briefing21")

# Hard fallback if contract load fails mid-repair.
_DEFAULT_DENY = (
    "occult-treasures",
    "front-matter-colophon-credits",
    "character-names",
)


def _deny_section_ids(game: str) -> list[str]:
    try:
        contract = load_passage_sections(game)
        ids = [
            s["id"]
            for s in contract.get("sections") or []
            if s.get("id") and s.get("seed_evidence", True) is False
        ]
        if ids:
            return ids
    except Exception as exc:
        logger.warning("could not load passage-sections (%s); using defaults", exc)
    return list(_DEFAULT_DENY)


def repair(graph: Neo4jGraph, *, game: str) -> dict[str, int]:
    deny = _deny_section_ids(game)
    logger.info("deny sections: %s", deny)

    preview = graph.query(
        """
        MATCH (n:SeedNode)<-[r:CONFIRMS_SEED|DOCUMENTED_BY]-(p)
        WHERE coalesce(p.section_id, '') IN $deny
        RETURN p.section_id AS section, count(r) AS edges
        ORDER BY section
        """,
        {"deny": deny},
    )
    logger.info("preview: %s", preview)

    stamped = graph.query(
        """
        MATCH (c:Chunk)
        WHERE coalesce(c.section_id, '') IN $deny
        SET c.seed_evidence = false
        RETURN count(c) AS n
        """,
        {"deny": deny},
    )
    stamp_n = int(stamped[0]["n"]) if stamped else 0

    deleted = graph.query(
        """
        MATCH (n:SeedNode)<-[r:CONFIRMS_SEED|DOCUMENTED_BY]-(p)
        WHERE coalesce(p.section_id, '') IN $deny
        DELETE r
        RETURN count(*) AS n
        """,
        {"deny": deny},
    )
    del_n = int(deleted[0]["n"]) if deleted else 0

    after = graph.query(
        """
        MATCH (n:SeedNode)<-[r:CONFIRMS_SEED|DOCUMENTED_BY]-(p)
        WHERE coalesce(p.section_id, '') IN $deny
        RETURN count(r) AS bad_edges
        """,
        {"deny": deny},
    )
    bad = int(after[0]["bad_edges"]) if after else 0

    violence = graph.query(
        """
        MATCH (n:SeedNode)<-[:CONFIRMS_SEED|DOCUMENTED_BY]-(p)
        WHERE any(lbl IN labels(n) WHERE lbl IN ['MeleeAttack', 'DefenseRoll'])
          AND coalesce(p.section_id, '') = 'violence-combat'
        RETURN count(*) AS violence_evidence
        """
    )
    spines = graph.query(
        """
        MATCH (i:If:IngestNode)
        WHERE i.id IN [
          'if:melee-hit-default',
          'if:defence-default',
          'if:crit-attack',
          'if:d3-2393b8d674143b52'
        ]
           OR i.id STARTS WITH 'if:d3-'
        RETURN count(i) AS spines
        """
    )

    out = {
        "stamped_chunks": stamp_n,
        "deleted_edges": del_n,
        "bad_edges_after": bad,
        "violence_evidence": int(violence[0]["violence_evidence"]) if violence else 0,
        "spines": int(spines[0]["spines"]) if spines else 0,
    }
    logger.info("result: %s", out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Briefing 21 front-matter evidence cleanup")
    parser.add_argument("--game", default="mork-borg")
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "morkborg"))
    args = parser.parse_args()

    load_dotenv()
    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=args.database,
    )
    out = repair(graph, game=args.game)
    ok = (
        out["bad_edges_after"] == 0
        and out["violence_evidence"] >= 1
        and out["spines"] >= 4
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
