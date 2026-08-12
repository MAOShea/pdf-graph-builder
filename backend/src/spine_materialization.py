"""Altitude-D operational If-spine materialization (Briefings 17–18 / D1–D2).

Deterministic MERGE of closed-vocabulary spines from
``games/<game>/operational-spines.json``. Does not invent predicates.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.ingest_manifest import DEFAULT_GAME, _project_root, load_ingest_manifest
from src.shared.common_fn import execute_graph_query

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def load_operational_spines(game: str = DEFAULT_GAME) -> dict[str, Any]:
    manifest = load_ingest_manifest(game)
    rel = (manifest.get("operational_spines") or {}).get("file", "operational-spines.json")
    path = _project_root() / "games" / game / rel
    if not path.is_file():
        logger.warning("operational spines contract not found: %s", path)
        return {"spines": []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def ensure_document(graph, file_name: str) -> None:
    """MERGE a Document stub so section chunks can PART_OF it after DB reset."""
    execute_graph_query(
        graph,
        """
        MERGE (d:Document {fileName: $file_name})
        ON CREATE SET d.status = 'Processing', d.tier = 5
        """,
        {"file_name": file_name},
    )


def _seed_exists(graph, label: str) -> bool:
    rows = execute_graph_query(
        graph,
        """
        MATCH (n:SeedNode)
        WHERE $label IN labels(n)
        RETURN 1 AS ok
        LIMIT 1
        """,
        {"label": label},
    )
    return bool(rows)


def _find_evidence_passage(
    graph,
    file_name: str,
    *,
    section_id: str,
    text_contains_any: list[str],
) -> str | None:
    rows = execute_graph_query(
        graph,
        """
        MATCH (p:RulePassage)
        WHERE p.section_id = $section_id
          AND (p.fileName = $file_name OR p.id STARTS WITH $file_prefix)
        RETURN p.id AS id, p.text AS text
        ORDER BY p.id
        """,
        {
            "section_id": section_id,
            "file_name": file_name,
            "file_prefix": f"{file_name}#",
        },
    )
    needles = [n.lower() for n in text_contains_any if n]
    scored: list[tuple[int, str]] = []
    for row in rows or []:
        text = (row.get("text") or "").lower()
        hits = sum(1 for n in needles if n in text)
        if hits:
            scored.append((hits, row["id"]))
    if scored:
        scored.sort(key=lambda x: (-x[0], x[1]))
        return scored[0][1]
    return None


def _merge_outcome(graph, outcome: dict[str, Any]) -> str:
    oid = outcome["id"]
    execute_graph_query(
        graph,
        """
        MERGE (o:IngestNode:Outcome {id: $id})
        SET o.name = $name,
            o.summary = $summary,
            o.tier = 5
        WITH o
        MATCH (seed:SeedNode)
        WHERE 'Outcome' IN labels(seed)
        MERGE (o)-[:INSTANCE_OF]->(seed)
        """,
        {
            "id": oid,
            "name": outcome.get("name") or oid,
            "summary": outcome.get("summary") or "",
        },
    )
    return oid


def _normalize_then_list(spine: dict[str, Any]) -> list[dict[str, Any]]:
    then = spine.get("then")
    if then is None:
        return []
    if isinstance(then, list):
        return then
    return [then]


def _normalize_procedures(spine: dict[str, Any]) -> list[str]:
    procs = spine.get("for_procedures")
    if procs:
        return list(procs)
    proc = spine.get("for_procedure")
    return [proc] if proc else []


def _normalize_atoms(spine: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve atom list; support D1 flat threshold fields as compare_dr."""
    if spine.get("atoms"):
        return list(spine["atoms"])
    if spine.get("atom"):
        return [spine["atom"]]
    # Legacy D1 shape: threshold + compare_id at spine root
    if spine.get("threshold") is not None or spine.get("compare_id"):
        return [
            {
                "kind": "compare_dr",
                "id": spine.get("compare_id") or f"compare:{spine['id']}",
                "threshold": int(spine.get("threshold") or 12),
            }
        ]
    return []


def _merge_compare_atom(graph, atom: dict[str, Any], *, compared_to_dr: bool) -> str:
    cid = atom["id"]
    threshold = int(atom.get("threshold") or 0)
    op = atom.get("op")
    left = atom.get("left")
    execute_graph_query(
        graph,
        """
        MERGE (c:IngestNode:Compare {id: $id})
        SET c.name = $id,
            c.threshold = $threshold,
            c.tier = 5,
            c.op = $op,
            c.left = $left
        WITH c
        MATCH (cSeed:SeedNode) WHERE 'Compare' IN labels(cSeed)
        MERGE (c)-[:INSTANCE_OF]->(cSeed)
        """,
        {
            "id": cid,
            "threshold": threshold,
            "op": op,
            "left": left,
        },
    )
    if compared_to_dr:
        execute_graph_query(
            graph,
            """
            MATCH (c:IngestNode:Compare {id: $id})
            MATCH (dr:SeedNode) WHERE 'DR' IN labels(dr)
            MERGE (c)-[:COMPARED_TO]->(dr)
            """,
            {"id": cid},
        )
    else:
        # Face equality spines must not keep a stale COMPARED_TO from prior shapes.
        execute_graph_query(
            graph,
            """
            MATCH (c:IngestNode:Compare {id: $id})-[r:COMPARED_TO]->()
            DELETE r
            """,
            {"id": cid},
        )
    return cid


def _merge_circumstance_atom(graph, atom: dict[str, Any]) -> str:
    cid = atom["id"]
    name = atom.get("name") or cid
    execute_graph_query(
        graph,
        """
        MERGE (c:IngestNode:Circumstance {id: $id})
        SET c.name = $name, c.tier = 5
        WITH c
        MATCH (cSeed:SeedNode) WHERE 'Circumstance' IN labels(cSeed)
        MERGE (c)-[:INSTANCE_OF]->(cSeed)
        """,
        {"id": cid, "name": name},
    )
    return cid


def _merge_atom(graph, atom: dict[str, Any], stats: dict[str, Any]) -> str | None:
    kind = atom.get("kind") or "compare_dr"
    if kind == "compare_dr":
        if not _seed_exists(graph, "Compare"):
            stats["warnings"].append("spine SeedNodes missing: Compare")
            return None
        return _merge_compare_atom(graph, atom, compared_to_dr=True)
    if kind == "compare_face":
        if not _seed_exists(graph, "Compare"):
            stats["warnings"].append("spine SeedNodes missing: Compare")
            return None
        return _merge_compare_atom(graph, atom, compared_to_dr=False)
    if kind == "circumstance":
        if not _seed_exists(graph, "Circumstance"):
            stats["warnings"].append("spine SeedNodes missing: Circumstance")
            return None
        return _merge_circumstance_atom(graph, atom)
    stats["warnings"].append(f"unknown atom kind: {kind}")
    return None


def _link_evidence(graph, file_name: str, if_id: str, spine: dict[str, Any], stats: dict[str, Any]) -> None:
    ev = spine.get("evidence") or {}
    passage_id = _find_evidence_passage(
        graph,
        file_name,
        section_id=ev.get("section_id") or "violence-combat",
        text_contains_any=list(ev.get("text_contains_any") or []),
    )
    if not passage_id:
        stats["warnings"].append(f"no evidence RulePassage for {if_id}")
        return

    execute_graph_query(
        graph,
        """
        MATCH (i:IngestNode:If {id: $if_id})-[r:DOCUMENTED_BY]->(:RulePassage)
        DELETE r
        """,
        {"if_id": if_id},
    )
    execute_graph_query(
        graph,
        """
        MATCH (i:IngestNode:If {id: $if_id})
        MATCH (p:RulePassage {id: $passage_id})
        MERGE (i)-[:DOCUMENTED_BY]->(p)
        """,
        {"if_id": if_id, "passage_id": passage_id},
    )
    stats["evidence_links"] += 1


def _merge_spine(graph, file_name: str, spine: dict[str, Any], stats: dict[str, Any]) -> None:
    procedures = _normalize_procedures(spine)
    if_id = spine["id"]
    bool_id = spine.get("bool_id") or f"bool:{if_id}"
    combinator = spine.get("combinator") or "LEAF"
    atoms = _normalize_atoms(spine)
    then_list = _normalize_then_list(spine)
    else_outcome = spine.get("else")

    if not procedures:
        stats["warnings"].append(f"no for_procedure(s) on {if_id}")
        return
    for proc in procedures:
        if not _seed_exists(graph, proc):
            stats["warnings"].append(f"procedure seed missing: {proc}")
            return
    if not _seed_exists(graph, "If") or not _seed_exists(graph, "BoolExpression"):
        stats["warnings"].append("spine SeedNodes missing (D0.4 incomplete)")
        return
    if not atoms:
        stats["warnings"].append(f"no atoms on {if_id}")
        return
    if not then_list:
        stats["warnings"].append(f"no then outcomes on {if_id}")
        return

    atom_ids: list[str] = []
    for atom in atoms:
        aid = _merge_atom(graph, atom, stats)
        if not aid:
            return
        atom_ids.append(aid)

    then_ids = [_merge_outcome(graph, o) for o in then_list]
    else_id = _merge_outcome(graph, else_outcome) if else_outcome else None

    execute_graph_query(
        graph,
        """
        MERGE (i:IngestNode:If {id: $if_id})
        SET i.name = $if_id, i.tier = 5, i.for_procedure = $proc_primary
        WITH i
        MATCH (ifSeed:SeedNode) WHERE 'If' IN labels(ifSeed)
        MERGE (i)-[:INSTANCE_OF]->(ifSeed)

        MERGE (b:IngestNode:BoolExpression {id: $bool_id})
        SET b.name = $bool_id, b.combinator = $combinator, b.tier = 5
        WITH i, b
        MATCH (bSeed:SeedNode) WHERE 'BoolExpression' IN labels(bSeed)
        MERGE (b)-[:INSTANCE_OF]->(bSeed)
        MERGE (i)-[:`IF`]->(b)
        """,
        {
            "if_id": if_id,
            "bool_id": bool_id,
            "combinator": combinator,
            "proc_primary": procedures[0],
        },
    )

    # Refresh FOR / HAS_ATOM / THEN / ELSE for this spine id (idempotent re-runs).
    execute_graph_query(
        graph,
        """
        MATCH (i:IngestNode:If {id: $if_id})-[r:FOR|THEN|ELSE]->()
        DELETE r
        """,
        {"if_id": if_id},
    )
    execute_graph_query(
        graph,
        """
        MATCH (i:IngestNode:If {id: $if_id})-[:`IF`]->(b:BoolExpression)
        OPTIONAL MATCH (b)-[r:HAS_ATOM]->()
        DELETE r
        """,
        {"if_id": if_id},
    )

    for proc in procedures:
        execute_graph_query(
            graph,
            """
            MATCH (i:IngestNode:If {id: $if_id})
            MATCH (proc:SeedNode) WHERE $proc IN labels(proc)
            MERGE (i)-[:FOR]->(proc)
            """,
            {"if_id": if_id, "proc": proc},
        )

    for aid in atom_ids:
        execute_graph_query(
            graph,
            """
            MATCH (i:IngestNode:If {id: $if_id})-[:`IF`]->(b:BoolExpression)
            MATCH (a {id: $atom_id})
            WHERE a:Compare OR a:Circumstance
            MERGE (b)-[:HAS_ATOM]->(a)
            """,
            {"if_id": if_id, "atom_id": aid},
        )

    for tid in then_ids:
        execute_graph_query(
            graph,
            """
            MATCH (i:IngestNode:If {id: $if_id})
            MATCH (t:IngestNode:Outcome {id: $then_id})
            MERGE (i)-[:THEN]->(t)
            """,
            {"if_id": if_id, "then_id": tid},
        )

    if else_id:
        execute_graph_query(
            graph,
            """
            MATCH (i:IngestNode:If {id: $if_id})
            MATCH (e:IngestNode:Outcome {id: $else_id})
            MERGE (i)-[:ELSE]->(e)
            """,
            {"if_id": if_id, "else_id": else_id},
        )

    stats["spines_created"] += 1
    _link_evidence(graph, file_name, if_id, spine, stats)


def materialize_operational_spines(
    graph,
    file_name: str,
    *,
    game: str = DEFAULT_GAME,
) -> dict[str, Any]:
    """MERGE altitude-D If spines for the game contract."""
    stats: dict[str, Any] = {
        "spines_expected": 0,
        "spines_created": 0,
        "evidence_links": 0,
        "warnings": [],
    }

    for label in ("If", "BoolExpression", "Compare", "Circumstance"):
        if not _seed_exists(graph, label):
            stats["warnings"].append(
                f"D0.4 incomplete: SeedNode:{label} missing — stop; do not invent types"
            )
            logger.error("spine_materialization: %s", stats["warnings"][-1])
            return stats

    contract = load_operational_spines(game)
    spines = contract.get("spines") or []
    stats["spines_expected"] = len(spines)
    if not spines:
        stats["warnings"].append("no spines in operational-spines.json")
        return stats

    for spine in spines:
        try:
            _merge_spine(graph, file_name, spine, stats)
        except Exception as exc:
            msg = f"spine {spine.get('id')!r} failed: {exc}"
            stats["warnings"].append(msg)
            logger.exception("spine_materialization: %s", msg)

    logger.info(
        "spine_materialization: created=%s/%s evidence=%s warnings=%s",
        stats["spines_created"],
        stats["spines_expected"],
        stats["evidence_links"],
        len(stats["warnings"]),
    )
    return stats
