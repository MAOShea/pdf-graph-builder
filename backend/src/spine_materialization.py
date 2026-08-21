"""Altitude-D operational If-spine materialization (Briefings 17–19 / D1–D3).

Deterministic MERGE of closed-vocabulary spines from
``games/<game>/operational-spines.json``. Does not invent predicates.

D3 creature DR overrides: opaque ``If.id``; creature is a graph parameter via
``Circumstance-[:APPLIES_TO]->`` fiction creature instance (not an id substring).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.ingest_manifest import DEFAULT_GAME, _project_root, load_ingest_manifest
from src.shared.common_fn import execute_graph_query

logger = logging.getLogger(__name__)

_PROC_OUTCOMES: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "MeleeAttack": (
        {
            "id": "outcome:melee-hit",
            "name": "hit",
            "summary": "Melee attack hits (test meets or beats DR).",
        },
        {
            "id": "outcome:melee-miss",
            "name": "miss",
            "summary": "Melee attack misses.",
        },
    ),
    "RangedAttack": (
        {
            "id": "outcome:ranged-hit",
            "name": "hit",
            "summary": "Ranged attack hits (test meets or beats DR).",
        },
        {
            "id": "outcome:ranged-miss",
            "name": "miss",
            "summary": "Ranged attack misses.",
        },
    ),
    "DefenseRoll": (
        {
            "id": "outcome:defence-success",
            "name": "defend",
            "summary": "Defence succeeds (test meets or beats DR).",
        },
        {
            "id": "outcome:defence-fail",
            "name": "hit-by-enemy",
            "summary": "Defence fails; enemy hits you.",
        },
    ),
}

# Briefing 22: D3 override → D1 default precedence.
_PROC_DEFAULT_IF: dict[str, str] = {
    "MeleeAttack": "if:melee-hit-default",
    "RangedAttack": "if:ranged-hit-default",
    "DefenseRoll": "if:defence-default",
}


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


def _normalize_else_list(spine: dict[str, Any]) -> list[dict[str, Any]]:
    raw = spine.get("else")
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [raw]


def _outcome_line(outcome: dict[str, Any]) -> str:
    return str(
        outcome.get("summary") or outcome.get("name") or outcome.get("id") or ""
    ).strip()


def spines_for_section(game: str, section_id: str) -> list[dict[str, Any]]:
    """Spines whose evidence.section_id cites this passage-section."""
    contract = load_operational_spines(game)
    sid = (section_id or "").strip()
    if not sid:
        return []
    out: list[dict[str, Any]] = []
    for spine in contract.get("spines") or []:
        ev = spine.get("evidence") or {}
        if ev.get("section_id") == sid:
            out.append(spine)
    return out


def spine_operator_preview(
    spine: dict[str, Any], span_text: str
) -> dict[str, Any]:
    """Contract preview for pdf-as-md: THEN/ELSE + evidence needles vs span text.

    Does not parse PDF glyphs. Needles match ingest ``text_contains_any``
    (case-insensitive substring).
    """
    ev = spine.get("evidence") or {}
    needles = [str(n) for n in (ev.get("text_contains_any") or []) if n]
    hay = (span_text or "").lower()
    return {
        "if_id": str(spine.get("id") or ""),
        "procedures": _normalize_procedures(spine),
        "evidence": [(n, n.lower() in hay) for n in needles],
        "then": [_outcome_line(o) for o in _normalize_then_list(spine) if _outcome_line(o)],
        "else": [_outcome_line(o) for o in _normalize_else_list(spine) if _outcome_line(o)],
    }


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


def _merge_compare_atom(
    graph, atom: dict[str, Any], *, compared_to_label: str | None
) -> str:
    cid = atom["id"]
    raw_threshold = atom.get("threshold")
    threshold = int(raw_threshold) if raw_threshold is not None else None
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
    # Refresh COMPARED_TO (DR, Morale, …) from atom.compared_to / compare_dr default.
    execute_graph_query(
        graph,
        """
        MATCH (c:IngestNode:Compare {id: $id})-[r:COMPARED_TO]->()
        DELETE r
        """,
        {"id": cid},
    )
    if compared_to_label:
        execute_graph_query(
            graph,
            """
            MATCH (c:IngestNode:Compare {id: $id})
            MATCH (seed:SeedNode) WHERE $label IN labels(seed)
            MERGE (c)-[:COMPARED_TO]->(seed)
            """,
            {"id": cid, "label": compared_to_label},
        )
    return cid


def _opaque_id(prefix: str, *parts: str) -> str:
    """Stable opaque merge key — never embed creature display names."""
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}{digest}"


def extract_creature_combat_dr(
    text: str, extract_rules: list[dict[str, Any]]
) -> tuple[int, list[str], str] | None:
    """Return (threshold, procedures, rule_id) from entity prose, or None.

    First matching extract_rule wins. Conservative: only attack/defence combat DR.
    """
    if not text or not extract_rules:
        return None
    for rule in extract_rules:
        pat = rule.get("pattern")
        procs = rule.get("procedures") or []
        if not pat or not procs:
            continue
        match = re.search(pat, text, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            threshold = int(match.group(1))
        except (IndexError, TypeError, ValueError):
            continue
        if threshold < 1:
            continue
        return threshold, list(procs), str(rule.get("id") or "rule")
    return None


def _merge_circumstance_atom(graph, atom: dict[str, Any]) -> str:
    cid = atom["id"]
    name = atom.get("name") or cid
    role = atom.get("role")
    execute_graph_query(
        graph,
        """
        MERGE (c:IngestNode:Circumstance {id: $id})
        SET c.name = $name, c.tier = 5, c.role = $role
        WITH c
        MATCH (cSeed:SeedNode) WHERE 'Circumstance' IN labels(cSeed)
        MERGE (c)-[:INSTANCE_OF]->(cSeed)
        """,
        {"id": cid, "name": name, "role": role},
    )
    applies_to = atom.get("applies_to_id")
    if applies_to:
        execute_graph_query(
            graph,
            """
            MATCH (c:IngestNode:Circumstance {id: $id})-[r:APPLIES_TO]->()
            DELETE r
            """,
            {"id": cid},
        )
        execute_graph_query(
            graph,
            """
            MATCH (c:IngestNode:Circumstance {id: $id})
            MATCH (target:IngestNode {id: $target_id})
            MERGE (c)-[:APPLIES_TO]->(target)
            """,
            {"id": cid, "target_id": applies_to},
        )
    return cid


def _merge_atom(graph, atom: dict[str, Any], stats: dict[str, Any]) -> str | None:
    kind = atom.get("kind") or "compare_dr"
    if kind in ("compare_dr", "compare_face", "compare"):
        if not _seed_exists(graph, "Compare"):
            stats["warnings"].append("spine SeedNodes missing: Compare")
            return None
        compared_to = atom.get("compared_to")
        if compared_to is None and kind == "compare_dr":
            compared_to = "DR"
        if compared_to and not _seed_exists(graph, compared_to):
            stats["warnings"].append(f"COMPARED_TO seed missing: {compared_to}")
            return None
        return _merge_compare_atom(graph, atom, compared_to_label=compared_to)
    if kind == "circumstance":
        if not _seed_exists(graph, "Circumstance"):
            stats["warnings"].append("spine SeedNodes missing: Circumstance")
            return None
        return _merge_circumstance_atom(graph, atom)
    stats["warnings"].append(f"unknown atom kind: {kind}")
    return None


def _link_evidence(graph, file_name: str, if_id: str, spine: dict[str, Any], stats: dict[str, Any]) -> None:
    ev = spine.get("evidence") or {}
    passage_id = ev.get("passage_id")
    if not passage_id:
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


def _list_creatures_with_passages(graph, file_name: str) -> list[dict[str, Any]]:
    rows = execute_graph_query(
        graph,
        """
        MATCH (e:IndexEntry {column: 'CREATURES'})-[:DENOTES]->(c:IngestNode)
        MATCH (e)-[:MAPS_TO_PASSAGE]->(p:RulePassage)
        WHERE c.id STARTS WITH $entity_prefix
           OR c.source = $file_name
        RETURN c.id AS creature_id,
               coalesce(c.name, e.title) AS creature_name,
               p.id AS passage_id,
               p.text AS text
        ORDER BY creature_name
        """,
        {
            "file_name": file_name,
            "entity_prefix": f"{file_name}#entity:creature:",
        },
    )
    return list(rows or [])


def materialize_creature_dr_overrides(
    graph,
    file_name: str,
    contract: dict[str, Any],
    stats: dict[str, Any],
) -> None:
    """D3: batch CREATURES attack/defence DR overrides (Briefing 19)."""
    cfg = contract.get("creature_dr_overrides") or {}
    if not cfg.get("enabled", True):
        return
    extract_rules = list(cfg.get("extract_rules") or [])
    if not extract_rules:
        stats["warnings"].append("creature_dr_overrides enabled but extract_rules empty")
        return
    role = cfg.get("circumstance_role") or "fighting"

    creatures = _list_creatures_with_passages(graph, file_name)
    stats["d3_creatures_scanned"] = len(creatures)
    emitted = 0

    for row in creatures:
        creature_id = row.get("creature_id")
        passage_id = row.get("passage_id")
        text = row.get("text") or ""
        if not creature_id or not passage_id:
            continue
        extracted = extract_creature_combat_dr(text, extract_rules)
        if not extracted:
            continue
        threshold, procedures, rule_id = extracted
        circ_id = _opaque_id("circumstance:d3-", creature_id, role)
        compare_id = _opaque_id("compare:d3-", str(threshold))

        for proc in procedures:
            outcomes = _PROC_OUTCOMES.get(proc)
            if not outcomes:
                stats["warnings"].append(f"D3: no outcome template for {proc}")
                continue
            then_o, else_o = outcomes
            if_id = _opaque_id("if:d3-", proc, creature_id, str(threshold))
            # Id hygiene: never embed creature display name (Briefing 19 D3-P1b).
            name_l = (row.get("creature_name") or "").lower()
            if name_l and name_l in if_id.lower():
                stats["warnings"].append(f"D3 id hygiene failed for {creature_id}")
                continue
            if "goblin" in if_id.lower() or "-vs-" in if_id.lower():
                stats["warnings"].append(f"D3 forbidden slug in id: {if_id}")
                continue

            spine = {
                "id": if_id,
                "for_procedure": proc,
                "combinator": "AND",
                "bool_id": _opaque_id("bool:d3-", proc, creature_id, str(threshold)),
                "atoms": [
                    {
                        "kind": "circumstance",
                        "id": circ_id,
                        "name": role,
                        "role": role,
                        "applies_to_id": creature_id,
                    },
                    {
                        "kind": "compare_dr",
                        "id": compare_id,
                        "threshold": threshold,
                        "op": ">=",
                    },
                ],
                "then": then_o,
                "else": else_o,
                "evidence": {"passage_id": passage_id},
                "notes": f"D3 override via {rule_id}",
            }
            _merge_spine(graph, file_name, spine, stats)
            emitted += 1

    stats["d3_overrides_emitted"] = emitted
    link_creature_dr_supersedes(graph, stats)
    logger.info(
        "spine_materialization D3: scanned=%s emitted=%s supersedes=%s",
        stats["d3_creatures_scanned"],
        emitted,
        stats.get("d3_supersedes_links", 0),
    )


def link_creature_dr_supersedes(graph, stats: dict[str, Any] | None = None) -> dict[str, Any]:
    """Briefing 22: each D3 Violence override SUPERSEDES the matching D1 default If.

    Safe live fill — does not recreate spines. Matches FOR procedure → default id.
    """
    stats = stats if stats is not None else {"warnings": [], "d3_supersedes_links": 0}
    if "d3_supersedes_links" not in stats:
        stats["d3_supersedes_links"] = 0
    if "warnings" not in stats:
        stats["warnings"] = []

    linked = 0
    for proc, default_id in _PROC_DEFAULT_IF.items():
        rows = execute_graph_query(
            graph,
            """
            MATCH (o:If:IngestNode)-[:FOR]->(procSeed:SeedNode)
            WHERE o.id STARTS WITH 'if:d3-'
              AND $proc IN labels(procSeed)
            MATCH (d:If {id: $default_id})
            MERGE (o)-[:SUPERSEDES]->(d)
            RETURN count(*) AS n
            """,
            {"proc": proc, "default_id": default_id},
        )
        n = int(rows[0]["n"]) if rows else 0
        if n == 0:
            # Still try: defaults / overrides may exist without SeedNode FOR match
            rows2 = execute_graph_query(
                graph,
                """
                MATCH (o:If:IngestNode)-[:FOR]->(procNode)
                WHERE o.id STARTS WITH 'if:d3-'
                  AND (
                    $proc IN labels(procNode)
                    OR coalesce(procNode.name, '') = $proc
                  )
                MATCH (d:If {id: $default_id})
                MERGE (o)-[:SUPERSEDES]->(d)
                RETURN count(*) AS n
                """,
                {"proc": proc, "default_id": default_id},
            )
            n = int(rows2[0]["n"]) if rows2 else 0
        linked += n
        if n == 0:
            stats["warnings"].append(
                f"D3 SUPERSEDES: no links for {proc} → {default_id}"
            )

    stats["d3_supersedes_links"] = linked
    logger.info("spine_materialization D3 SUPERSEDES: linked=%s", linked)
    return stats


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


def _normalize_supersedes(spine: dict[str, Any]) -> list[str]:
    raw = spine.get("supersedes")
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    return [str(raw)]


def _link_declared_supersedes(
    graph, spines: list[dict[str, Any]], stats: dict[str, Any]
) -> None:
    """Contract ``supersedes`` → ``If-[:SUPERSEDES]->If`` (situation-gated overrides)."""
    linked = 0
    for spine in spines:
        if_id = spine.get("id")
        if not if_id:
            continue
        for target_id in _normalize_supersedes(spine):
            rows = execute_graph_query(
                graph,
                """
                MATCH (a:IngestNode:If {id: $if_id})
                MATCH (b:IngestNode:If {id: $target_id})
                MERGE (a)-[:SUPERSEDES]->(b)
                RETURN 1 AS ok
                """,
                {"if_id": if_id, "target_id": target_id},
            )
            if rows:
                linked += 1
            else:
                stats["warnings"].append(
                    f"SUPERSEDES: {if_id} → {target_id} (missing If)"
                )
    stats["declared_supersedes_links"] = linked


def materialize_operational_spines(
    graph,
    file_name: str,
    *,
    game: str = DEFAULT_GAME,
) -> dict[str, Any]:
    """MERGE altitude-D If spines for the game contract (D1–D3)."""
    stats: dict[str, Any] = {
        "spines_expected": 0,
        "spines_created": 0,
        "evidence_links": 0,
        "d3_creatures_scanned": 0,
        "d3_overrides_emitted": 0,
        "d3_supersedes_links": 0,
        "declared_supersedes_links": 0,
        "warnings": [],
    }

    for label in ("If", "BoolExpression", "Compare", "Circumstance"):
        if not _seed_exists(graph, label):
            stats["warnings"].append(
                f"D0.4 incomplete: SeedNode:{label} missing — stop; do not invent types"
            )
            logger.error("spine_materialization: %s", stats["warnings"][-1])
            return stats

    load_operational_spines.cache_clear()
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

    try:
        _link_declared_supersedes(graph, spines, stats)
    except Exception as exc:
        msg = f"declared SUPERSEDES failed: {exc}"
        stats["warnings"].append(msg)
        logger.exception("spine_materialization: %s", msg)

    try:
        materialize_creature_dr_overrides(graph, file_name, contract, stats)
    except Exception as exc:
        msg = f"D3 creature DR overrides failed: {exc}"
        stats["warnings"].append(msg)
        logger.exception("spine_materialization: %s", msg)

    logger.info(
        "spine_materialization: created=%s/%s (+d3=%s) evidence=%s warnings=%s",
        stats["spines_created"],
        stats["spines_expected"],
        stats["d3_overrides_emitted"],
        stats["evidence_links"],
        len(stats["warnings"]),
    )
    return stats
