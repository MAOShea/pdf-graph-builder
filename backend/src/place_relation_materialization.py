"""Place PART_OF Place and Faction OCCURS_IN Place (Galgenbeck first pass).

Contract: games/<game>/place-relations.json. Titles must match THE_WORLD IndexEntry.
Does not pack section bodies. Does not invent Location.
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from typing import Any

from src.ingest_manifest import DEFAULT_GAME, _project_root, load_ingest_manifest
from src.shared.common_fn import execute_graph_query

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def load_place_relations(game: str = DEFAULT_GAME) -> dict[str, Any]:
    manifest = load_ingest_manifest(game)
    rel = (manifest.get("place_relations") or {}).get("file", "place-relations.json")
    path = _project_root() / "games" / game / rel
    if not path.is_file():
        logger.warning("place-relations contract not found: %s", path)
        return {"part_of": [], "occurs_in_place": []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def place_relations_for_section(game: str, section_id: str) -> dict[str, list[dict[str, Any]]]:
    contract = load_place_relations(game)
    sid = (section_id or "").strip()
    part_of = [
        row for row in (contract.get("part_of") or []) if row.get("section_id") == sid
    ]
    occurs = [
        row
        for row in (contract.get("occurs_in_place") or [])
        if row.get("section_id") == sid
    ]
    return {"part_of": part_of, "occurs_in_place": occurs}


def place_relation_operator_preview(
    row: dict[str, Any], span_text: str, *, kind: str
) -> dict[str, Any]:
    needles = [str(n) for n in (row.get("text_contains_any") or []) if n]
    hay = re.sub(r"\s+", " ", span_text or "").lower()
    if kind == "part_of":
        label = (
            f"{row.get('child_title')} PART_OF {row.get('parent_title')}"
        )
    else:
        label = (
            f"{row.get('faction_title')} OCCURS_IN {row.get('place_title')}"
        )
    return {
        "kind": kind,
        "label": label,
        "evidence": [(n, n.lower() in hay) for n in needles],
    }


def _instance_id(
    graph,
    file_name: str,
    *,
    title: str,
    entry_kind: str,
) -> str | None:
    rows = execute_graph_query(
        graph,
        """
        MATCH (e:IndexEntry)-[:DENOTES]->(x:IngestNode)
        WHERE (e.source = $file_name OR e.id STARTS WITH $file_prefix)
          AND e.entry_kind = $kind
          AND toLower(e.title) = toLower($title)
        RETURN x.id AS id
        LIMIT 1
        """,
        {
            "file_name": file_name,
            "file_prefix": f"{file_name}#index:",
            "kind": entry_kind,
            "title": title,
        },
    )
    if not rows:
        return None
    return rows[0].get("id")


def materialize_place_relations(
    graph,
    file_name: str,
    *,
    game: str = DEFAULT_GAME,
) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "part_of": 0,
        "occurs_in_place": 0,
        "warnings": [],
    }
    contract = load_place_relations(game)
    for row in contract.get("part_of") or []:
        child_title = str(row.get("child_title") or "").strip()
        parent_title = str(row.get("parent_title") or "").strip()
        kind = str(row.get("kind") or "place").strip()
        child_id = _instance_id(graph, file_name, title=child_title, entry_kind=kind)
        parent_id = _instance_id(graph, file_name, title=parent_title, entry_kind=kind)
        if not child_id or not parent_id:
            stats["warnings"].append(
                f"PART_OF missing instance: {child_title!r} -> {parent_title!r} "
                f"(child={child_id} parent={parent_id})"
            )
            continue
        execute_graph_query(
            graph,
            """
            MATCH (child:IngestNode {id: $child_id})-[:INSTANCE_OF]->(:Place:SeedNode)
            MATCH (parent:IngestNode {id: $parent_id})-[:INSTANCE_OF]->(:Place:SeedNode)
            MERGE (child)-[:PART_OF]->(parent)
            """,
            {"child_id": child_id, "parent_id": parent_id},
        )
        stats["part_of"] += 1
    for row in contract.get("occurs_in_place") or []:
        faction_title = str(row.get("faction_title") or "").strip()
        place_title = str(row.get("place_title") or "").strip()
        faction_id = _instance_id(
            graph, file_name, title=faction_title, entry_kind="faction"
        )
        place_id = _instance_id(graph, file_name, title=place_title, entry_kind="place")
        if not faction_id or not place_id:
            stats["warnings"].append(
                f"OCCURS_IN Place missing instance: {faction_title!r} -> {place_title!r} "
                f"(faction={faction_id} place={place_id})"
            )
            continue
        execute_graph_query(
            graph,
            """
            MATCH (fac:IngestNode {id: $faction_id})-[:INSTANCE_OF]->(:Faction:SeedNode)
            MATCH (place:IngestNode {id: $place_id})-[:INSTANCE_OF]->(:Place:SeedNode)
            MERGE (fac)-[:OCCURS_IN]->(place)
            """,
            {"faction_id": faction_id, "place_id": place_id},
        )
        stats["occurs_in_place"] += 1
    if stats["warnings"]:
        logger.error("place_relations warnings: %s", stats["warnings"])
    logger.info(
        "place_relations: part_of=%s occurs_in_place=%s warnings=%s",
        stats["part_of"],
        stats["occurs_in_place"],
        len(stats["warnings"]),
    )
    return stats
