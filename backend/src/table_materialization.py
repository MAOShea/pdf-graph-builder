"""Deterministic Tier-5 lookup table materialization driven by ingest-manifest.json."""

import json
import logging
from typing import Any

from langchain_core.documents import Document

from src.ingest_manifest import (
    column_names,
    load_ingest_manifest,
    spec_by_name,
)

_MAX_LABEL_LEN = 500


def _normalize_columns(columns: list[Any]) -> list[str]:
    return [str(c).strip() for c in columns]


def _parse_table_json(raw: Any) -> dict | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


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
        if idx >= len(row):
            continue
        val = row[idx]
        col_lower = col.lower()
        if col_lower.startswith("d") and col_lower[1:].isdigit():
            try:
                cells[col] = int(val)
            except (TypeError, ValueError):
                cells[col] = val
        elif col_lower == "dr":
            try:
                cells[col] = int(val)
            except (TypeError, ValueError):
                cells[col] = val
        else:
            cells[col] = str(val).strip() if val is not None else ""
    return cells


def _row_index_key(cells: dict[str, Any], columns: list[dict]) -> str:
    index_cols = sorted(
        [c for c in columns if c.get("role") == "index"],
        key=lambda c: c.get("position", 0),
    )
    if not index_cols and columns:
        index_cols = [columns[0]]
    if not index_cols:
        return "0"
    parts = [str(cells.get(col["name"], "")).replace(" ", "") for col in index_cols]
    return ":".join(parts)


def _table_matches_spec(table: dict, spec: dict) -> bool:
    if table.get("manifest_name") == spec.get("name"):
        return True
    table_cols = _normalize_columns(table.get("columns") or [])
    return table_cols == column_names(spec)


def _validate_rows(table: dict, spec: dict) -> None:
    acceptance = spec.get("acceptance_rows") or []
    if not acceptance:
        return
    cols = column_names(spec)
    if not cols:
        return
    index_col = cols[0]
    extracted = {}
    for row in table.get("rows") or []:
        cells = _row_cells(list(row), cols)
        extracted[str(cells.get(index_col))] = cells

    mismatches = 0
    for expected in acceptance:
        exp_cells = expected.get("cells") or {}
        key = str(exp_cells.get(index_col))
        if key not in extracted:
            mismatches += 1
            continue
        for col, exp_val in exp_cells.items():
            got = extracted[key].get(col)
            if col == index_col:
                continue
            if str(got).strip().lower() != str(exp_val).strip().lower():
                mismatches += 1
                logging.warning(
                    "table materialization: %s row %s label mismatch (PDF wins)",
                    spec.get("name"),
                    key,
                )
    if mismatches:
        logging.info(
            "table materialization: %s validation — %s mismatch(es) vs acceptance_rows",
            spec.get("name"),
            mismatches,
        )


def materialize_lookup_table(
    graph,
    chunk_id: str,
    table: dict,
    spec: dict,
    chunk_doc: Document,
    file_name: str,
    scaffold_map: dict,
) -> bool:
    """Create one lookup table instance from manifest spec. Idempotent."""
    table_name = spec["name"]
    lookup_label = spec.get("instance_of", "LookupTable")
    lookup_seed = _find_seed_id(scaffold_map, lookup_label, graph)

    if not lookup_seed:
        logging.warning(
            "table materialization: %s seed not found — skipping %s",
            lookup_label,
            table_name,
        )
        return False

    meta = chunk_doc.metadata or {}
    page = meta.get("page_number")
    columns = column_names(spec)
    col_defs = spec.get("columns") or []

    table_props: dict[str, Any] = {
        "id": table_name,
        "name": table_name,
        "tier": 5,
        "source": file_name,
    }
    if page is not None:
        table_props["page"] = page

    try:
        graph.query(
            f"""
            MERGE (t:IngestNode:{table_name} {{id: $table_id}})
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
                "table_id": table_name,
                "props": table_props,
                "lookup_seed": lookup_seed,
            },
        )

        for col_def in col_defs:
            col_name = col_def["name"]
            node_id = f"{table_name}:{col_name}"
            graph.query(
                f"""
                MATCH (t:{table_name} {{id: $table_id}})
                MERGE (col:IngestNode:TableColumn {{id: $col_id}})
                SET col.name = $col_name_full,
                    col.column_name = $column_name,
                    col.role = $role,
                    col.position = $position,
                    col.tier = 5
                MERGE (t)-[:HAS_COLUMN]->(col)
                """,
                {
                    "table_id": table_name,
                    "col_id": node_id,
                    "col_name_full": node_id,
                    "column_name": col_name,
                    "role": col_def.get("role", "data"),
                    "position": col_def.get("position", 0),
                },
            )

        for row in table.get("rows") or []:
            cells = _row_cells(list(row), columns)
            row_key = _row_index_key(cells, col_defs)
            row_id = f"{table_name}:row:{row_key}"
            graph.query(
                f"""
                MATCH (t:{table_name} {{id: $table_id}})
                MERGE (row:IngestNode:TableEntry {{id: $row_id}})
                SET row.name = $row_name,
                    row.cells = $cells_json,
                    row.tier = 5
                MERGE (t)-[:HAS_ENTRY]->(row)
                """,
                {
                    "table_id": table_name,
                    "row_id": row_id,
                    "row_name": row_id,
                    "cells_json": json.dumps(cells),
                },
            )

        applies_to = spec.get("applies_to")
        if applies_to:
            target_seed = _find_seed_id(scaffold_map, applies_to, graph)
            if target_seed:
                graph.query(
                    f"""
                    MATCH (t:{table_name} {{id: $table_id}})
                    MATCH (target)
                    WHERE toLower(coalesce(target.seed_id, target.id, '')) = toLower($target_seed)
                    MERGE (t)-[:APPLIES_TO]->(target)
                    """,
                    {"table_id": table_name, "target_seed": target_seed},
                )

        for user_label in spec.get("used_by") or []:
            user_seed = _find_seed_id(scaffold_map, user_label, graph)
            if user_seed:
                graph.query(
                    f"""
                    MATCH (t:{table_name} {{id: $table_id}})
                    MATCH (user)
                    WHERE toLower(coalesce(user.seed_id, user.id, '')) = toLower($user_seed)
                    MERGE (user)-[:USES]->(t)
                    """,
                    {"table_id": table_name, "user_seed": user_seed},
                )

        graph.query(
            f"""
            MATCH (c:Chunk {{id: $chunk_id}})
            MATCH (t:{table_name} {{id: $table_id}})
            MERGE (c)-[:DOCUMENTED_BY]->(t)
            """,
            {"chunk_id": chunk_id, "table_id": table_name},
        )

        if table_name == "DRTable":
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

        _validate_rows(table, spec)
        logging.info(
            "table materialization: %s materialized from chunk %s (%s)",
            table_name,
            chunk_id[:8],
            file_name,
        )
        return True

    except Exception as e:
        logging.error("table materialization: failed for %s: %s", table_name, e)
        return False


def materialize_lookup_tables_from_chunks(
    graph,
    file_name: str,
    chunk_list: list[dict],
    scaffold_map: dict | None,
    *,
    game: str = "mork-borg",
    pdf_path: str | None = None,
    merged_file_path: str | None = None,
) -> dict[str, int]:
    """Deprecated: use run_lookup_table_pipeline() — PDF on disk is the text source.

    When pdf_path or merged_file_path is supplied, delegates to the unified pipeline.
    Otherwise logs a warning and returns empty stats (Neo4j chunk text is not used).
    """
    from src.table_pipeline import run_lookup_table_pipeline

    if pdf_path or merged_file_path:
        stats = run_lookup_table_pipeline(
            graph,
            file_name,
            scaffold_map or {},
            pdf_path=pdf_path,
            merged_file_path=merged_file_path,
            game=game,
            hand_authored=False,
            bundles=False,
        )
        return {
            "chunks_scanned": stats.get("pdf_tables_parsed", 0),
            "tables_materialized": stats.get("pdf_tables_materialized", 0),
        }

    logging.warning(
        "materialize_lookup_tables_from_chunks: no pdf_path — skipped "
        "(Neo4j chunk text is not used for table parsing; call run_lookup_table_pipeline)"
    )
    return {"chunks_scanned": 0, "tables_materialized": 0}
