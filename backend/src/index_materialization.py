"""Rulebook index catalog (Briefing 7) and typed fiction instances (Briefing 8)."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from src.ingest_manifest import load_ingest_manifest, load_passage_sections
from src.shared.common_fn import execute_graph_query

logger = logging.getLogger(__name__)

_FICTION_ENTRY_KINDS = frozenset(
    {"place", "supporting_character", "faction", "world_lore", "creature"}
)
_WORLD_COLUMNS = frozenset({"THE_WORLD"})


def slug_title(title: str) -> str:
    """Lowercase slug for stable ids — strip punctuation, hyphenate."""
    text = unicodedata.normalize("NFKD", title)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "untitled"


def normalize_index_title(title: str) -> str:
    """Normalize publisher titles for cross-column duplicate detection."""
    text = title.lower().strip()
    text = re.sub(r",?\s*the$", "", text)
    text = re.sub(r"^the\s+", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _document_exists(graph, file_name: str) -> bool:
    rows = execute_graph_query(
        graph,
        "MATCH (d:Document {fileName: $file_name}) RETURN d.fileName AS fn LIMIT 1",
        {"file_name": file_name},
    )
    return bool(rows)


def _load_index_contract(game: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = load_ingest_manifest(game)
    rulebook_index = manifest.get("rulebook_index") or {}
    materialization = rulebook_index.get("materialization") or {}
    passage = load_passage_sections(game)
    index_source = passage.get("index_source") or {}
    return index_source, materialization, rulebook_index


def _entry_id(file_name: str, column: str, title: str) -> str:
    return f"{file_name}#index:{column}:{slug_title(title)}"


def _entity_id(file_name: str, entry_kind: str, title: str) -> str:
    return f"{file_name}#entity:{entry_kind}:{slug_title(title)}"


def _index_id(file_name: str) -> str:
    return f"{file_name}#rulebook-index"


def _iter_index_rows(
    index_source: dict[str, Any],
    column_map: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for column, array_key in column_map.items():
        for item in index_source.get(array_key) or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            page = item.get("page")
            rows.append(
                {
                    "column": column,
                    "title": title,
                    "page": int(page) if page is not None else None,
                    "entry_kind": item.get("entry_kind"),
                }
            )
    return rows


def materialize_rulebook_index(
    graph,
    file_name: str,
    *,
    game: str = "mork-borg",
) -> dict[str, Any]:
    """
    Load index_source from passage-sections.json + rulebook_index from ingest-manifest.
    MERGE RulebookIndex and IndexEntry nodes (Briefing 7).
    """
    stats: dict[str, Any] = {
        "index_created": 0,
        "entries_created": 0,
        "by_column": {},
        "also_indexed_links": 0,
        "warnings": [],
    }

    if not _document_exists(graph, file_name):
        stats["warnings"].append(f"Document {file_name!r} not found — skipped index materialization")
        return stats

    index_source, materialization, rulebook_index = _load_index_contract(game)
    if not index_source or not materialization:
        stats["warnings"].append("missing index_source or rulebook_index.materialization — skipped")
        return stats

    column_map = materialization.get("column_map") or {}
    index_page = index_source.get("page")
    layout = index_source.get("layout", "three_columns")
    index_node_id = _index_id(file_name)

    execute_graph_query(
        graph,
        """
        MATCH (d:Document {fileName: $file_name})
        MERGE (idx:IngestNode:RulebookIndex {id: $index_id})
        SET idx.index_page = $index_page,
            idx.layout = $layout,
            idx.tier = 5,
            idx.source = $file_name
        MERGE (d)-[:HAS_INDEX]->(idx)
        """,
        {
            "file_name": file_name,
            "index_id": index_node_id,
            "index_page": index_page,
            "layout": layout,
        },
    )
    stats["index_created"] = 1

    rows = _iter_index_rows(index_source, column_map)
    entry_ids: list[str] = []
    by_column: dict[str, int] = {}

    for row in rows:
        column = row["column"]
        title = row["title"]
        entry_id = _entry_id(file_name, column, title)
        entry_ids.append(entry_id)
        by_column[column] = by_column.get(column, 0) + 1

        props: dict[str, Any] = {
            "id": entry_id,
            "title": title,
            "column": column,
            "tier": 5,
            "source": file_name,
        }
        if row["page"] is not None:
            props["page"] = row["page"]
        if row.get("entry_kind"):
            props["entry_kind"] = row["entry_kind"]

        execute_graph_query(
            graph,
            """
            MATCH (d:Document {fileName: $file_name})
            MATCH (idx:RulebookIndex {id: $index_id})
            MERGE (e:IngestNode:IndexEntry {id: $entry_id})
            SET e += $props
            MERGE (idx)-[:HAS_ENTRY]->(e)
            MERGE (e)-[:INDEXED_IN]->(d)
            """,
            {
                "file_name": file_name,
                "index_id": index_node_id,
                "entry_id": entry_id,
                "props": props,
            },
        )
        stats["entries_created"] += 1

    stats["by_column"] = by_column

    also_links = _link_cross_column_duplicates(graph, file_name, rows)
    stats["also_indexed_links"] = also_links

    logger.info(
        "rulebook_index: entries=%s by_column=%s also_indexed=%s",
        stats["entries_created"],
        stats["by_column"],
        stats["also_indexed_links"],
    )
    return stats


def _link_cross_column_duplicates(
    graph,
    file_name: str,
    rows: list[dict[str, Any]],
) -> int:
    """Link IndexEntry pairs that normalize to the same concept across columns."""
    groups: dict[tuple[int | None, str], list[str]] = {}
    for row in rows:
        norm = normalize_index_title(row["title"])
        if not norm:
            continue
        key = (row.get("page"), norm)
        entry_id = _entry_id(file_name, row["column"], row["title"])
        groups.setdefault(key, []).append(entry_id)

    links = 0
    for ids in groups.values():
        if len(ids) < 2:
            continue
        unique_ids = sorted(set(ids))
        for i, left in enumerate(unique_ids):
            for right in unique_ids[i + 1 :]:
                execute_graph_query(
                    graph,
                    """
                    MATCH (a:IndexEntry {id: $left})
                    MATCH (b:IndexEntry {id: $right})
                    MERGE (a)-[:ALSO_INDEXED_AS]->(b)
                    """,
                    {"left": left, "right": right},
                )
                links += 1
                logger.info(
                    "rulebook_index: ALSO_INDEXED_AS %s <-> %s",
                    left.split(":")[-1],
                    right.split(":")[-1],
                )
    return links


def link_index_entries_to_sections(
    graph,
    file_name: str,
    *,
    game: str = "mork-borg",
    phase: int | None = None,
) -> dict[str, Any]:
    """Link RULES IndexEntry rows to section chunks via MAPS_TO_SECTION."""
    stats: dict[str, Any] = {
        "sections_with_index_title": 0,
        "links_created": 0,
        "warnings": [],
    }

    contract = load_passage_sections(game)
    sections = contract.get("sections") or []
    if phase is not None:
        sections = [s for s in sections if (s.get("phase") or 99) <= phase]

    for section in sections:
        index_title = section.get("index_title")
        section_id = section.get("id")
        if not index_title or not section_id:
            continue
        stats["sections_with_index_title"] += 1

        rows = execute_graph_query(
            graph,
            """
            MATCH (e:IndexEntry {column: 'RULES', title: $index_title})
            WHERE e.source = $file_name OR e.id STARTS WITH $file_prefix
            RETURN e.id AS entry_id
            """,
            {
                "index_title": index_title,
                "file_name": file_name,
                "file_prefix": f"{file_name}#index:RULES:",
            },
        )
        if not rows:
            msg = f"no RULES IndexEntry for index_title={index_title!r} (section {section_id})"
            stats["warnings"].append(msg)
            logger.warning("rulebook_index: %s", msg)
            continue

        chunk_rows = execute_graph_query(
            graph,
            """
            MATCH (c:Chunk {section_id: $section_id})-[:PART_OF]->(:Document {fileName: $file_name})
            RETURN c.id AS chunk_id
            LIMIT 1
            """,
            {"section_id": section_id, "file_name": file_name},
        )
        if not chunk_rows:
            msg = f"no section chunk for section_id={section_id!r}"
            stats["warnings"].append(msg)
            continue

        chunk_id = chunk_rows[0]["chunk_id"]
        for entry_row in rows:
            execute_graph_query(
                graph,
                """
                MATCH (e:IndexEntry {id: $entry_id})
                MATCH (c:Chunk {id: $chunk_id})
                MERGE (e)-[:MAPS_TO_SECTION]->(c)
                """,
                {"entry_id": entry_row["entry_id"], "chunk_id": chunk_id},
            )
            stats["links_created"] += 1

    logger.info(
        "rulebook_index: section_links=%s warnings=%s",
        stats["links_created"],
        len(stats["warnings"]),
    )
    return stats


def _find_seed_node(graph, seed_label: str) -> dict[str, Any] | None:
    rows = execute_graph_query(
        graph,
        """
        MATCH (n:SeedNode)
        WHERE $label IN labels(n)
        RETURN coalesce(n.seed_id, n.id, n.name) AS seed_id, n.name AS name
        LIMIT 1
        """,
        {"label": seed_label},
    )
    return rows[0] if rows else None


def _require_fiction_seeds(
    graph,
    entry_kind_to_seed: dict[str, str],
) -> dict[str, str]:
    """Return entry_kind -> seed_id map; raise if any required seed is missing."""
    missing: list[str] = []
    resolved: dict[str, str] = {}
    for entry_kind, seed_label in entry_kind_to_seed.items():
        if entry_kind not in _FICTION_ENTRY_KINDS:
            continue
        row = _find_seed_node(graph, seed_label)
        if not row or not row.get("seed_id"):
            missing.append(seed_label)
        else:
            resolved[entry_kind] = str(row["seed_id"])
    if missing:
        raise RuntimeError(
            "fiction instance materialization: missing scaffold SeedNodes: "
            + ", ".join(sorted(set(missing)))
            + ". Run bootstrap first (briefing-8 prerequisite)."
        )
    return resolved


def materialize_fiction_instances(
    graph,
    file_name: str,
    *,
    game: str = "mork-borg",
    setting_name: str = "Mörk Borg",
) -> dict[str, Any]:
    """
    For each WORLD/CREATURES IndexEntry with a fiction entry_kind, MERGE typed
    IngestNode instances and DENOTES / INSTANCE_OF / OCCURS_IN edges (Briefing 8).
    """
    stats: dict[str, Any] = {
        "entities_created": 0,
        "by_entry_kind": {},
        "denotes_links": 0,
        "occurs_in_links": 0,
        "warnings": [],
    }

    if not _document_exists(graph, file_name):
        stats["warnings"].append(f"Document {file_name!r} not found — skipped fiction instances")
        return stats

    _, materialization, _ = _load_index_contract(game)
    entry_kind_to_seed: dict[str, str] = materialization.get("entry_kind_to_seed") or {}
    if not entry_kind_to_seed:
        stats["warnings"].append("missing entry_kind_to_seed — skipped")
        return stats

    try:
        seed_ids = _require_fiction_seeds(graph, entry_kind_to_seed)
    except RuntimeError as exc:
        stats["warnings"].append(str(exc))
        logger.error("%s", exc)
        return stats

    setting_seed = _find_seed_node(graph, "Setting")
    setting_seed_id: str | None = None
    if not setting_seed or not setting_seed.get("seed_id"):
        stats["warnings"].append("Setting:SeedNode not found — WORLD OCCURS_IN skipped")
    else:
        setting_seed_id = str(setting_seed["seed_id"])
        execute_graph_query(
            graph,
            """
            MERGE (s:IngestNode {id: $setting_id})
            SET s.name = $setting_name, s.tier = 5, s.source = $file_name
            WITH s
            MATCH (seed:SeedNode)
            WHERE toLower(coalesce(seed.seed_id, seed.id, '')) = toLower($setting_seed_id)
            MERGE (s)-[:INSTANCE_OF]->(seed)
            """,
            {
                "setting_id": f"{file_name}#setting",
                "setting_name": setting_name,
                "file_name": file_name,
                "setting_seed_id": setting_seed_id,
            },
        )

    rows = execute_graph_query(
        graph,
        """
        MATCH (e:IndexEntry)
        WHERE (e.source = $file_name OR e.id STARTS WITH $file_prefix)
          AND e.entry_kind IN $fiction_kinds
        RETURN e.id AS entry_id, e.title AS title, e.column AS column,
               e.entry_kind AS entry_kind, e.page AS page
        ORDER BY e.column, e.title
        """,
        {
            "file_name": file_name,
            "file_prefix": f"{file_name}#index:",
            "fiction_kinds": list(_FICTION_ENTRY_KINDS),
        },
    )

    for row in rows:
        entry_kind = row.get("entry_kind")
        if entry_kind not in seed_ids:
            continue
        seed_label = entry_kind_to_seed[entry_kind]
        seed_id = seed_ids[entry_kind]
        title = row["title"]
        entity_id = _entity_id(file_name, entry_kind, title)

        props: dict[str, Any] = {
            "id": entity_id,
            "name": title,
            "tier": 5,
            "source": file_name,
            "entry_kind": entry_kind,
        }
        if row.get("page") is not None:
            props["page"] = row["page"]

        execute_graph_query(
            graph,
            """
            MERGE (entity:IngestNode {id: $entity_id})
            SET entity += $props
            WITH entity
            MATCH (e:IndexEntry {id: $entry_id})
            MERGE (e)-[:DENOTES]->(entity)
            WITH entity
            MATCH (seed:SeedNode)
            WHERE toLower(coalesce(seed.seed_id, seed.id, '')) = toLower($seed_id)
            MERGE (entity)-[:INSTANCE_OF]->(seed)
            """,
            {
                "entity_id": entity_id,
                "props": props,
                "entry_id": row["entry_id"],
                "seed_id": seed_id,
            },
        )
        stats["entities_created"] += 1
        stats["by_entry_kind"][entry_kind] = stats["by_entry_kind"].get(entry_kind, 0) + 1
        stats["denotes_links"] += 1

        if row.get("column") in _WORLD_COLUMNS and setting_seed_id:
            execute_graph_query(
                graph,
                """
                MATCH (entity:IngestNode {id: $entity_id})
                MATCH (seed:SeedNode)
                WHERE toLower(coalesce(seed.seed_id, seed.id, '')) = toLower($setting_seed_id)
                MERGE (entity)-[:OCCURS_IN]->(seed)
                """,
                {
                    "entity_id": entity_id,
                    "setting_seed_id": setting_seed_id,
                },
            )
            stats["occurs_in_links"] += 1

    logger.info(
        "fiction_instances: entities=%s by_kind=%s occurs_in=%s",
        stats["entities_created"],
        stats["by_entry_kind"],
        stats["occurs_in_links"],
    )
    return stats


def materialize_rulebook_catalog(
    graph,
    file_name: str,
    *,
    game: str = "mork-borg",
    link_sections: bool = True,
    fiction: bool = True,
    section_phase: int | None = None,
) -> dict[str, Any]:
    """Run briefing-7 catalog + optional section links + briefing-8 fiction instances."""
    result: dict[str, Any] = {"index": {}, "sections": {}, "fiction": {}}
    result["index"] = materialize_rulebook_index(graph, file_name, game=game)
    if result["index"].get("entries_created", 0) == 0:
        if link_sections:
            result["sections"] = {
                "sections_with_index_title": 0,
                "links_created": 0,
                "warnings": ["skipped — no index entries materialized"],
            }
        if fiction:
            result["fiction"] = {
                "entities_created": 0,
                "by_entry_kind": {},
                "denotes_links": 0,
                "occurs_in_links": 0,
                "warnings": ["skipped — no index entries materialized"],
            }
        return result
    if link_sections:
        result["sections"] = link_index_entries_to_sections(
            graph, file_name, game=game, phase=section_phase
        )
    if fiction:
        result["fiction"] = materialize_fiction_instances(graph, file_name, game=game)
    return result
