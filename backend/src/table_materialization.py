"""Deterministic Tier-5 lookup table materialization from parsed table chunks.

Layer B (briefing-3): concrete DRTable / columns / rows as :IngestNode nodes,
linked to scaffold seeds. Complements layer C (Chunk.table_json evidence).
"""

import json
import logging
from typing import Any

from langchain_core.documents import Document

# Phase 1 acceptance contract — Mörk Borg DR reference table (p.28)
DR_TABLE_NAME = "DRTable"
DR_TABLE_COLUMNS = [
    {"column_name": "DR", "role": "index", "position": 0},
    {"column_name": "label", "role": "result", "position": 1},
]
DR_TABLE_INDEX_VALUES = {6, 8, 10, 12, 14, 16, 18}


def _normalize_columns(columns: list[Any]) -> list[str]:
    return [str(c).strip() for c in columns]


def _parse_table_json(raw: Any) -> dict | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None


def is_dr_table(table: dict) -> bool:
    """True when table_json matches the DR reference table shape."""
    columns = _normalize_columns(table.get("columns") or [])
    if len(columns) != 2:
        return False
    if columns[0].lower() != "dr" or columns[1].lower() != "label":
        return False

    rows = table.get("rows") or []
    if len(rows) < len(DR_TABLE_INDEX_VALUES):
        return False

    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        try:
            dr_val = int(row[0])
        except (TypeError, ValueError):
            continue
        if dr_val in DR_TABLE_INDEX_VALUES:
            seen.add(dr_val)

    return seen == DR_TABLE_INDEX_VALUES


def _find_seed_id(scaffold_map: dict, label: str, graph=None) -> str | None:
    label_lower = label.lower()
    for entry in scaffold_map.get("seed_nodes", {}).values():
        if any(lbl.lower() == label_lower for lbl in entry.get("labels", [])):
            return entry.get("seed_id")
    if graph is not None:
        try:
            rows = graph.query(
                """
                MATCH (n:SeedNode)
                WHERE $label IN labels(n)
                RETURN coalesce(n.seed_id, n.id, n.name) AS seed_id
                LIMIT 1
                """,
                {"label": label},
            )
            if rows:
                return rows[0].get("seed_id")
        except Exception as e:
            logging.error("table materialization: seed lookup failed for %s: %s", label, e)
    return None


def _row_cells(row: list[Any], columns: list[str]) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for idx, col in enumerate(columns):
        if idx < len(row):
            val = row[idx]
            if col.lower() == "dr":
                try:
                    cells[col] = int(val)
                except (TypeError, ValueError):
                    cells[col] = val
            else:
                cells[col] = str(val).strip() if val is not None else ""
    return cells


def materialize_dr_table(
    graph,
    chunk_id: str,
    table: dict,
    chunk_doc: Document,
    file_name: str,
    scaffold_map: dict,
) -> bool:
    """Create DRTable instance, columns, rows, and semantic links. Idempotent."""
    lookup_seed = _find_seed_id(scaffold_map, "LookupTable", graph)
    dr_seed = _find_seed_id(scaffold_map, "DR", graph)
    ability_test_seed = _find_seed_id(scaffold_map, "AbilityTest", graph)

    if not lookup_seed:
        logging.warning("table materialization: LookupTable seed not found — skipping DRTable")
        return False

    meta = chunk_doc.metadata or {}
    page = meta.get("page_number")
    columns = _normalize_columns(table.get("columns") or ["DR", "label"])
    col0, col1 = columns[0], columns[1]

    table_props = {
        "id": DR_TABLE_NAME,
        "name": DR_TABLE_NAME,
        "tier": 5,
        "source": file_name,
    }
    if page is not None:
        table_props["page"] = page

    try:
        graph.query(
            """
            MERGE (t:IngestNode:DRTable {id: $table_id})
            SET t += $props
            WITH t
            MATCH (lt)
            WHERE toLower(coalesce(lt.seed_id, lt.id, '')) = toLower($lookup_seed)
            MERGE (t)-[:INSTANCE_OF]->(lt)
            WITH t
            OPTIONAL MATCH (t)-[r:HAS_ENTRY]->(:TableEntry)
            DELETE r
            """,
            {
                "table_id": DR_TABLE_NAME,
                "props": table_props,
                "lookup_seed": lookup_seed,
            },
        )

        for col_def in DR_TABLE_COLUMNS:
            col_name = col_def["column_name"]
            node_id = f"{DR_TABLE_NAME}:{col_name}"
            graph.query(
                """
                MATCH (t:DRTable {id: $table_id})
                MERGE (col:IngestNode:TableColumn {id: $col_id})
                SET col.name = $col_name_full,
                    col.column_name = $column_name,
                    col.role = $role,
                    col.position = $position,
                    col.tier = 5
                MERGE (t)-[:HAS_COLUMN]->(col)
                """,
                {
                    "table_id": DR_TABLE_NAME,
                    "col_id": node_id,
                    "col_name_full": node_id,
                    "column_name": col_name,
                    "role": col_def["role"],
                    "position": col_def["position"],
                },
            )

        for row in table.get("rows") or []:
            cells = _row_cells(list(row), columns)
            dr_val = cells.get(col0) or cells.get("DR")
            if dr_val is None:
                continue
            try:
                dr_int = int(dr_val)
            except (TypeError, ValueError):
                continue
            if dr_int not in DR_TABLE_INDEX_VALUES:
                continue

            row_id = f"{DR_TABLE_NAME}:row:{dr_int}"
            graph.query(
                """
                MATCH (t:DRTable {id: $table_id})
                MERGE (row:IngestNode:TableEntry {id: $row_id})
                SET row.name = $row_name,
                    row.cells = $cells_json,
                    row.tier = 5
                MERGE (t)-[:HAS_ENTRY]->(row)
                """,
                {
                    "table_id": DR_TABLE_NAME,
                    "row_id": row_id,
                    "row_name": row_id,
                    "cells_json": json.dumps(cells),
                },
            )

        if dr_seed:
            graph.query(
                """
                MATCH (t:DRTable {id: $table_id})
                MATCH (dr)
                WHERE toLower(coalesce(dr.seed_id, dr.id, '')) = toLower($dr_seed)
                MERGE (t)-[:APPLIES_TO]->(dr)
                """,
                {"table_id": DR_TABLE_NAME, "dr_seed": dr_seed},
            )

        if ability_test_seed:
            graph.query(
                """
                MATCH (t:DRTable {id: $table_id})
                MATCH (at)
                WHERE toLower(coalesce(at.seed_id, at.id, '')) = toLower($ability_seed)
                MERGE (at)-[:USES]->(t)
                """,
                {"table_id": DR_TABLE_NAME, "ability_seed": ability_test_seed},
            )

        graph.query(
            """
            MATCH (c:Chunk {id: $chunk_id})
            MATCH (t:DRTable {id: $table_id})
            MERGE (c)-[:DOCUMENTED_BY]->(t)
            """,
            {"chunk_id": chunk_id, "table_id": DR_TABLE_NAME},
        )

        graph.query(
            """
            MATCH (c:Chunk {id: $chunk_id})
            MATCH (lt)
            WHERE toLower(coalesce(lt.seed_id, lt.id, '')) = toLower($lookup_seed)
            MERGE (c)-[:CONFIRMS_SEED]->(lt)
            SET lt.coverage = CASE lt.coverage
                WHEN 'research-only' THEN 'ingest-confirmed'
                ELSE lt.coverage END
            """,
            {"chunk_id": chunk_id, "lookup_seed": lookup_seed},
        )

        logging.info(
            "table materialization: DRTable materialized from chunk %s (%s)",
            chunk_id[:8],
            file_name,
        )
        return True

    except Exception as e:
        logging.error("table materialization: failed for DRTable: %s", e)
        return False


def materialize_lookup_tables_from_chunks(
    graph,
    file_name: str,
    chunk_list: list[dict],
    scaffold_map: dict | None,
) -> dict[str, int]:
    """Scan chunks for table_json and materialize known lookup tables."""
    stats = {"chunks_scanned": 0, "tables_materialized": 0}

    if not scaffold_map or not chunk_list:
        return stats

    sorted_chunks = sorted(
        chunk_list,
        key=lambda item: (item.get("chunk_doc") or Document(page_content="")).metadata.get(
            "page_number", 9999
        )
        or 9999,
    )

    for item in sorted_chunks:
        chunk_id = item.get("chunk_id")
        chunk_doc: Document = item.get("chunk_doc")
        if not chunk_id or chunk_doc is None:
            continue

        meta = chunk_doc.metadata or {}
        table = _parse_table_json(meta.get("table_json"))
        is_table_block = meta.get("block_type") == "table"

        if not table and not is_table_block:
            continue

        stats["chunks_scanned"] += 1

        if table is None:
            continue

        if is_dr_table(table):
            if materialize_dr_table(
                graph, chunk_id, table, chunk_doc, file_name, scaffold_map
            ):
                stats["tables_materialized"] += 1
                break

    return stats
