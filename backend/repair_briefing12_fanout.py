#!/usr/bin/env python3
"""Briefing 12 — strip seed_id fan-out edges; rewire table used_by by concept label.

Safe to re-run. Does not re-run LLM extract; clears polluted Chunk→SeedNode evidence
so the next full ingest can rewrite confirms cleanly. Rewires SeedNode-[:USES]->table
from ingest-manifest used_by only.
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

from src.ingest_manifest import load_ingest_manifest  # noqa: E402
from src.table_materialization import (  # noqa: E402
    _merge_seed_rel_by_label,
    _seed_label_exists,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("repair_briefing12")


def _counts(graph: Neo4jGraph) -> dict[str, int]:
    def one(q: str) -> int:
        rows = graph.query(q)
        return int(rows[0]["n"]) if rows else 0

    return {
        "creature_uses_bad": one(
            """
            MATCH (c:Creature:SeedNode)-[:USES]->(t)
            WHERE t:TrapsTable OR t:AgonyEndTable OR t:OptionalClassesTable OR t:DRTable
            RETURN count(*) AS n
            """
        ),
        "place_uses_bad": one(
            """
            MATCH (p:Place:SeedNode)-[:USES]->(t)
            WHERE t:OptionalClassesTable OR t:TrapsTable OR t:AgonyEndTable
            RETURN count(*) AS n
            """
        ),
        "trap_uses_traps": one(
            "MATCH (:Trap:SeedNode)-[:USES]->(:TrapsTable) RETURN count(*) AS n"
        ),
        "misery_uses_agony": one(
            "MATCH (:Misery:SeedNode)-[:USES]->(:AgonyEndTable) RETURN count(*) AS n"
        ),
        "creature_evidence": one(
            """
            MATCH (c:Creature:SeedNode)<-[:DOCUMENTED_BY|CONFIRMS_SEED]-(p)
            RETURN count(*) AS n
            """
        ),
        "abilities_on_creature": one(
            """
            MATCH (c:Creature:SeedNode)<-[:DOCUMENTED_BY|CONFIRMS_SEED]-(p)
            WHERE coalesce(p.page, p.page_number, p.page_number_start) = 27
               OR coalesce(p.section_id, '') = 'abilities'
            RETURN count(*) AS n
            """
        ),
    }


def repair(graph: Neo4jGraph, *, game: str, clear_chunk_seed_evidence: bool) -> None:
    before = _counts(graph)
    logger.info("before: %s", before)

    # 1) Drop all SeedNode → concrete table USES (fan-out + correct; rewire next)
    deleted = graph.query(
        """
        MATCH (s:SeedNode)-[r:USES]->(t:IngestNode)
        WHERE any(lbl IN labels(t) WHERE lbl ENDS WITH 'Table')
           OR (t.name IS NOT NULL AND t.name ENDS WITH 'Table')
        DELETE r
        RETURN count(*) AS n
        """
    )
    logger.info("deleted SeedNode-USES->table edges: %s", deleted[0]["n"] if deleted else 0)

    # Also CharacterCreation etc. may USE selector via bundle — rewire from manifest used_by
    # plus character_creation block handled by rematerialize bundles if needed.

    manifest = load_ingest_manifest(game)
    scaffold_map = {"seed_nodes": {}}  # label check falls through to graph
    for spec in manifest.get("lookup_tables") or []:
        name = spec.get("name")
        if not name:
            continue
        for user_label in spec.get("used_by") or []:
            if not _seed_label_exists(scaffold_map, user_label, graph):
                logger.warning("used_by seed missing: %s → %s", user_label, name)
                continue
            _merge_seed_rel_by_label(
                graph,
                seed_label=user_label,
                rel="USES",
                direction="seed_to_other",
                other_match=f"MATCH (other:{name} {{id: $table_id}})",
                other_params={"table_id": name},
            )
            logger.info("rewired USES %s → %s", user_label, name)

    # CharacterCreation USES OptionalClassesTable (manifest character_creation / used_by)
    oc = spec_by_name_safe(manifest, "OptionalClassesTable")
    if oc:
        for user_label in oc.get("used_by") or ["CharacterCreation"]:
            if _seed_label_exists(scaffold_map, user_label, graph):
                _merge_seed_rel_by_label(
                    graph,
                    seed_label=user_label,
                    rel="USES",
                    direction="seed_to_other",
                    other_match="MATCH (other:OptionalClassesTable {id: $table_id})",
                    other_params={"table_id": "OptionalClassesTable"},
                )

    if clear_chunk_seed_evidence:
        ev = graph.query(
            """
            MATCH (c:Chunk)-[r:DOCUMENTED_BY|CONFIRMS_SEED]->(s:SeedNode)
            DELETE r
            RETURN count(*) AS n
            """
        )
        logger.info(
            "deleted Chunk→SeedNode DOCUMENTED_BY|CONFIRMS_SEED: %s "
            "(re-ingest to restore legitimate confirms)",
            ev[0]["n"] if ev else 0,
        )

    after = _counts(graph)
    logger.info("after: %s", after)


def spec_by_name_safe(manifest: dict, name: str) -> dict | None:
    for spec in manifest.get("lookup_tables") or []:
        if spec.get("name") == name:
            return spec
    return None


def main() -> int:
    load_dotenv(_BACKEND / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", default="mork-borg")
    parser.add_argument(
        "--keep-chunk-seed-evidence",
        action="store_true",
        help="Do not delete Chunk→SeedNode DOCUMENTED_BY/CONFIRMS_SEED",
    )
    args = parser.parse_args()

    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE", "morkborg"),
        refresh_schema=False,
    )
    repair(
        graph,
        game=args.game,
        clear_chunk_seed_evidence=not args.keep_chunk_seed_evidence,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
