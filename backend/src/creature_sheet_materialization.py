"""Altitude-D D4 creature sheet materialization (Briefings 20 / 23).

Parse bestiary lines from CREATURES entity RulePassages and MERGE closed
``HAS_HIT_POINTS`` / ``HAS_MORALE`` / ``HAS_ARMOR`` / ``HAS_ATTACK`` edges onto
creature instances. Opaque sheet-node ids — no creature name in id.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from src.ingest_manifest import DEFAULT_GAME
from src.shared.common_fn import execute_graph_query

logger = logging.getLogger(__name__)

_SHEET_RELS = (
    "HAS_HIT_POINTS",
    "HAS_MORALE",
    "HAS_ARMOR",
    "HAS_ATTACK",
)

_DIE = r"(?:\d+)?d\d+(?:\s*\+\s*\d+)?"
_REDUCE = rf"(?:-|–|—)\s*d\d+"

_HP_BLOCK = re.compile(
    r"HP\s+(\d+)\s+"
    r"Morale\s+(\d+|special|[–—\-\?]+)\s+"
    r"(.+?)(?=\n\s*Special:|\n\s*Captured|\n\s*Dead\b|\n\s*Head\b|\n\s*Trait\b|\n\s*Specialty\b|\n\s*Values\b|\Z)",
    re.IGNORECASE | re.DOTALL,
)

_ATTACK_TAIL = re.compile(
    rf"^(?P<name>.+?)\s+(?P<damage>{_DIE})(?:\s*\+\s*special)?\s*$",
    re.IGNORECASE,
)

_ARMOR_WITH_REDUCE = re.compile(
    rf"^(?P<name>.+?)\s+(?P<reduce>{_REDUCE})\s*(?P<rest>.*)$",
    re.IGNORECASE | re.DOTALL,
)

_WIELD_ROW = re.compile(
    rf"^\s*\d+\s+(?P<name>.+?)\s+(?P<damage>{_DIE})\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _opaque_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}{digest}"


def _normalize_sheet_text(text: str) -> str:
    t = text.replace("\u2003", " ").replace("\xa0", " ").replace("\u00a0", " ")
    # Broken extracts sometimes use '?' as a field separator.
    t = re.sub(r"(?<=\d)\?(?=\s*(?:Morale|Ropy|No |Hardened|Thick|Leather|Porcelain|Barrier|Clay))", " ", t)
    t = re.sub(r"\?(?=\s*(?:Knife|Poisoned|Touch|Strike|Fist|Shortsword|Claw|Claws|Wields|Long |Heavy |Chained|Huge ))", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def _parse_morale(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip()
    if re.fullmatch(r"\d+", raw):
        return {"value": int(raw), "none": False}
    return {"value": None, "none": True}


def _clean_reduce(raw: str) -> str:
    r = raw.replace("–", "-").replace("—", "-").replace(" ", "")
    return r.lower()


def _clean_die(raw: str) -> str:
    return re.sub(r"\s+", "", (raw or "").lower())


def _parse_attacks(blob: str) -> list[dict[str, str]]:
    attacks: list[dict[str, str]] = []
    if not blob or not blob.strip():
        return attacks
    # Prefer explicit "or" alternatives, then leftover lines / wields rows.
    chunks: list[str] = []
    for part in re.split(r"\s+or\s+", blob, flags=re.IGNORECASE):
        chunks.extend(p.strip() for p in part.splitlines() if p.strip())

    for chunk in chunks:
        chunk = re.sub(r"\s+", " ", chunk).strip(" .;")
        if not chunk or chunk.lower().startswith("wields"):
            continue
        if re.match(r"^\d+\s+", chunk):
            mrow = _WIELD_ROW.match(chunk)
            if mrow:
                attacks.append(
                    {
                        "name": mrow.group("name").strip(),
                        "damage": _clean_die(mrow.group("damage")),
                    }
                )
            continue
        m = _ATTACK_TAIL.match(chunk)
        if m:
            name = m.group("name").strip()
            if name.lower() in {"no armor", "wields"}:
                continue
            attacks.append({"name": name, "damage": _clean_die(m.group("damage"))})
    return attacks


def parse_creature_sheet(text: str) -> dict[str, Any] | None:
    """Extract sheet slots from entity passage prose. Returns None if no HP line."""
    if not text:
        return None
    norm = _normalize_sheet_text(text)
    match = _HP_BLOCK.search(norm)
    if not match:
        return None

    hp = int(match.group(1))
    morale = _parse_morale(match.group(2))
    body = match.group(3).strip()

    armor: dict[str, Any] | None = None
    attack_blob = body

    no_armor = re.match(r"^No\s+armor\s*(.*)$", body, re.IGNORECASE | re.DOTALL)
    if no_armor:
        armor = {"name": "No armor", "reduce": None}
        attack_blob = no_armor.group(1).strip()
    else:
        am = _ARMOR_WITH_REDUCE.match(body)
        if am:
            armor = {
                "name": am.group("name").strip(),
                "reduce": _clean_reduce(am.group("reduce")),
            }
            attack_blob = (am.group("rest") or "").strip()

    # Berserker-style weapon table in the captured block.
    wield_attacks = [
        {"name": m.group("name").strip(), "damage": _clean_die(m.group("damage"))}
        for m in _WIELD_ROW.finditer(norm)
    ]
    attacks = _parse_attacks(attack_blob)
    if not attacks and wield_attacks:
        attacks = wield_attacks
    elif wield_attacks:
        # Prefer table rows when present (named alternatives).
        names = {a["name"].lower() for a in attacks}
        for wa in wield_attacks:
            if wa["name"].lower() not in names:
                attacks.append(wa)

    return {
        "hp": hp,
        "morale": morale,
        "armor": armor,
        "attacks": attacks,
    }


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


def _clear_sheet_edges(graph, creature_id: str) -> None:
    execute_graph_query(
        graph,
        """
        MATCH (c:IngestNode {id: $cid})-[r:HAS_HIT_POINTS|HAS_MORALE|HAS_ARMOR|HAS_ATTACK]->(slot)
        DELETE r
        WITH slot
        WHERE slot:HitPoints OR slot:Morale OR slot:Armor OR slot:AttackProfile
        DETACH DELETE slot
        """,
        {"cid": creature_id},
    )


def _merge_sheet_node(
    graph,
    *,
    labels: str,
    node_id: str,
    props: dict[str, Any],
    seed_label: str,
    passage_id: str | None,
) -> None:
    execute_graph_query(
        graph,
        f"""
        MERGE (n:IngestNode:{labels} {{id: $id}})
        SET n += $props, n.tier = 5
        WITH n
        MATCH (seed:SeedNode)
        WHERE $seed_label IN labels(seed)
        MERGE (n)-[:INSTANCE_OF]->(seed)
        """,
        {"id": node_id, "props": props, "seed_label": seed_label},
    )
    if passage_id:
        execute_graph_query(
            graph,
            """
            MATCH (n:IngestNode {id: $id})
            MATCH (p:RulePassage {id: $passage_id})
            MERGE (n)-[:DOCUMENTED_BY]->(p)
            """,
            {"id": node_id, "passage_id": passage_id},
        )


def _link(graph, creature_id: str, rel: str, slot_id: str) -> None:
    execute_graph_query(
        graph,
        f"""
        MATCH (c:IngestNode {{id: $cid}})
        MATCH (s:IngestNode {{id: $sid}})
        MERGE (c)-[:{rel}]->(s)
        """,
        {"cid": creature_id, "sid": slot_id},
    )


def materialize_creature_sheets(
    graph,
    file_name: str,
    *,
    game: str = DEFAULT_GAME,
) -> dict[str, Any]:
    """Batch CREATURES entity passages → sheet slots (D4)."""
    del game  # reserved for future per-game parse profiles
    stats: dict[str, Any] = {
        "creatures_scanned": 0,
        "creatures_with_sheet": 0,
        "slots_created": 0,
        "warnings": [],
    }

    for label in ("HitPoints", "Morale", "Armor", "AttackProfile", "Creature"):
        if not _seed_exists(graph, label):
            stats["warnings"].append(
                f"D4 incomplete: SeedNode:{label} missing — stop; do not invent types"
            )
            logger.error("creature_sheets: %s", stats["warnings"][-1])
            return stats

    rows = _list_creatures_with_passages(graph, file_name)
    stats["creatures_scanned"] = len(rows)

    for row in rows:
        creature_id = row.get("creature_id")
        passage_id = row.get("passage_id")
        text = row.get("text") or ""
        if not creature_id or not passage_id:
            continue
        parsed = parse_creature_sheet(text)
        if not parsed:
            continue

        # Id hygiene — opaque hashes only.
        if "goblin" in creature_id.lower() and "goblin" in _opaque_id("x:", creature_id):
            pass  # creature_id may contain slug; sheet ids must not use display names

        _clear_sheet_edges(graph, creature_id)

        hp_id = _opaque_id("sheet:hp:", creature_id)
        _merge_sheet_node(
            graph,
            labels="HitPoints",
            node_id=hp_id,
            props={"name": "HitPoints", "value": parsed["hp"]},
            seed_label="HitPoints",
            passage_id=passage_id,
        )
        _link(graph, creature_id, "HAS_HIT_POINTS", hp_id)
        stats["slots_created"] += 1

        mor = parsed["morale"]
        mor_id = _opaque_id("sheet:morale:", creature_id)
        _merge_sheet_node(
            graph,
            labels="Morale",
            node_id=mor_id,
            props={
                "name": "Morale",
                "value": mor.get("value"),
                "none": bool(mor.get("none")),
            },
            seed_label="Morale",
            passage_id=passage_id,
        )
        _link(graph, creature_id, "HAS_MORALE", mor_id)
        stats["slots_created"] += 1

        armor = parsed.get("armor")
        if armor:
            arm_id = _opaque_id("sheet:armor:", creature_id)
            _merge_sheet_node(
                graph,
                labels="Armor",
                node_id=arm_id,
                props={
                    "name": armor.get("name"),
                    "reduce": armor.get("reduce"),
                },
                seed_label="Armor",
                passage_id=passage_id,
            )
            _link(graph, creature_id, "HAS_ARMOR", arm_id)
            stats["slots_created"] += 1

        for i, atk in enumerate(parsed.get("attacks") or []):
            atk_id = _opaque_id("sheet:atk:", creature_id, str(i), atk.get("name", ""))
            if any(bad in atk_id.lower() for bad in ("goblin", "-vs-")):
                stats["warnings"].append(f"D4 id hygiene failed for attack on {creature_id}")
                continue
            _merge_sheet_node(
                graph,
                labels="AttackProfile",
                node_id=atk_id,
                props={"name": atk.get("name"), "damage": atk.get("damage")},
                seed_label="AttackProfile",
                passage_id=passage_id,
            )
            _link(graph, creature_id, "HAS_ATTACK", atk_id)
            stats["slots_created"] += 1

        stats["creatures_with_sheet"] += 1

    logger.info(
        "creature_sheets: scanned=%s with_sheet=%s slots=%s warnings=%s",
        stats["creatures_scanned"],
        stats["creatures_with_sheet"],
        stats["slots_created"],
        len(stats["warnings"]),
    )
    return stats
