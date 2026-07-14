"""Extract lookup tables from PDF page text when layout APIs miss them.

Mörk Borg DR table (p.28) is not a bordered PDF table — PyMuPDF find_tables()
returns 0. The content appears as inline number+label pairs after a heading.
"""

import json
import logging
import re
from typing import Any

from langchain_core.documents import Document

DR_HEADER_RE = re.compile(
    r"Difficulty Ratings?\s*\(DR\)\s*(.+?)(?:Carrying Capacity|$)",
    re.IGNORECASE | re.DOTALL,
)
DR_ROW_RE = re.compile(
    r"\b(6|8|10|12|14|16|18)\s+(.+?)(?=\s+(?:6|8|10|12|14|16|18)\s+|$)",
    re.DOTALL,
)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f]+")
_MAX_LABEL_LEN = 120


def _clean_label(raw: str) -> str:
    return " ".join(_CONTROL_CHAR_RE.sub(" ", raw).split())


def extract_dr_table_from_text(text: str) -> dict | None:
    """Parse DR reference table from PDF chunk text. Returns table_json shape."""
    if not text:
        return None
    match = DR_HEADER_RE.search(text)
    if not match:
        return None

    rows: list[list[Any]] = []
    for row_match in DR_ROW_RE.finditer(match.group(1)):
        label = _clean_label(row_match.group(2))
        if not label or len(label) > _MAX_LABEL_LEN:
            return None
        rows.append([int(row_match.group(1)), label])

    if len(rows) < 7:
        return None

    return {
        "title": "Difficulty Ratings (DR)",
        "columns": ["DR", "label"],
        "rows": rows,
    }


def _is_pdf_chunk(meta: dict) -> bool:
    if meta.get("source_format") == "structured-json":
        return False
    return meta.get("page_number") is not None or meta.get("block_type") is None


def enrich_pdf_chunks_with_tables(chunk_list: list[dict]) -> dict[str, int]:
    """Scan PDF chunks for known table patterns; set table_json on chunk metadata."""
    stats = {"chunks_scanned": 0, "tables_found": 0}

    sorted_items = sorted(
        chunk_list,
        key=lambda item: (item.get("chunk_doc") or Document(page_content="")).metadata.get(
            "page_number", 9999
        )
        or 9999,
    )

    for item in sorted_items:
        chunk_doc: Document = item.get("chunk_doc")
        if chunk_doc is None:
            continue

        meta = chunk_doc.metadata or {}
        if meta.get("table_json") or not _is_pdf_chunk(meta):
            continue

        stats["chunks_scanned"] += 1
        table = extract_dr_table_from_text(chunk_doc.page_content)
        if table is None:
            continue

        meta["table_json"] = json.dumps(table)
        meta["block_type"] = "table"
        meta["block_title"] = table.get("title", "table")
        meta["source_format"] = meta.get("source_format") or "pdf"
        chunk_doc.metadata = meta
        stats["tables_found"] += 1
        logging.info(
            "pdf table parser: found DR table on page %s",
            meta.get("page_number"),
        )
        break

    return stats


def persist_chunk_table_metadata(graph, chunk_list: list[dict]) -> int:
    """Write table_json / block_type back onto :Chunk nodes (layer C evidence)."""
    updated = 0
    for item in chunk_list:
        chunk_id = item.get("chunk_id")
        chunk_doc: Document = item.get("chunk_doc")
        if not chunk_id or chunk_doc is None:
            continue

        meta = chunk_doc.metadata or {}
        table_json = meta.get("table_json")
        if not table_json:
            continue

        try:
            graph.query(
                """
                MATCH (c:Chunk {id: $chunk_id})
                SET c.table_json = $table_json,
                    c.block_type = $block_type,
                    c.block_title = $block_title,
                    c.source_format = coalesce(c.source_format, $source_format)
                """,
                {
                    "chunk_id": chunk_id,
                    "table_json": table_json,
                    "block_type": meta.get("block_type", "table"),
                    "block_title": meta.get("block_title"),
                    "source_format": meta.get("source_format", "pdf"),
                },
            )
            updated += 1
        except Exception as e:
            logging.error("pdf table parser: failed to persist chunk %s: %s", chunk_id, e)

    return updated
